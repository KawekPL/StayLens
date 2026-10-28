import json
import shutil
from pathlib import Path
from statistics import median

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from staylens.application import create_application
from staylens.catalog import Listing, locate_district, ring_contains
from staylens.data import sha256

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data/prepared/s03"
REQUEST = {
    "district": "Mitte",
    "room_type": "Entire home/apt",
    "property_type": "Entire rental unit",
    "latitude": 52.52,
    "longitude": 13.405,
    "accommodates": 2,
    "bedrooms": 1.0,
    "beds": 1.0,
    "bathrooms": 1.0,
    "minimum_nights": 2,
}


@pytest.fixture(scope="module")
def client():
    with TestClient(create_application()) as value:
        yield value


def test_all_catalog_estimates_are_saved_oof_not_training_predictions(client):
    predictions = pd.read_csv(
        ROOT / "artifacts/s02-v1/cv_predictions.csv", dtype={"listing_id": str}
    ).set_index("listing_id")
    rows = client.app.state.catalog
    assert len(rows) == 5814 and {r["id"] for r in rows} == set(predictions.index)
    for row in rows:
        Listing.model_validate(row)
        assert row["model"]["method"] == "host_oof"
        assert row["model"]["estimatedPrice"] == round(
            predictions.loc[row["id"], "hist_gradient_boosting"], 2
        )
        assert row["price"] == predictions.loc[row["id"], "price"]
        assert "host_id" not in json.dumps(row)
    meta = client.get("/api/catalog/meta").json()
    assert meta["testEvaluated"] is False and meta["previewRows"] == len(rows)


def test_pagination_filters_and_all_match_statistics(client):
    params = {"district": "Mitte", "query": "", "sort": "price-asc", "limit": 12}
    first = client.get("/api/catalog/listings", params=params).json()
    second = client.get("/api/catalog/listings", params={**params, "offset": 12}).json()
    assert len(first["items"]) == len(second["items"]) == 12
    assert not {r["id"] for r in first["items"]} & {r["id"] for r in second["items"]}
    expected = [
        r
        for r in client.app.state.catalog
        if r["district"] == "Mitte"
        and r["roomType"] == "Entire home/apt"
        and r["guests"] >= 2
        and r["price"] <= 300
    ]
    assert first["total"] == len(expected) > 60
    assert first["summary"]["median"] == median(r["price"] for r in expected)
    assert sum(b["count"] for b in first["summary"]["histogram"]) == len(expected)
    assert len(first["mapItems"]) == 60
    assert first["items"][-1]["price"] <= second["items"][0]["price"]
    assert (
        client.get("/api/catalog/listings", params={"query": "NoSuchListing983572"}).json()["total"]
        == 0
    )


@pytest.mark.parametrize(
    "params",
    [
        {"limit": 61},
        {"offset": -1},
        {"guests": 0},
        {"max_price": "nan"},
        {"query": "a" * 121},
        {"district": "Warszawa"},
        {"sort": "bad"},
    ],
)
def test_query_validation(client, params):
    assert client.get("/api/catalog/listings", params=params).status_code == 422


def test_detail_compare_and_invalid_ids(client):
    ids = list(client.app.state.by_id)[:3]
    first = client.get(f"/api/catalog/listings/{ids[0]}").json()
    assert first["id"] == ids[0]
    comparison = client.get("/api/catalog/compare", params=[("ids", i) for i in ids]).json()
    assert [r["id"] for r in comparison["items"]] == ids
    assert comparison["items"][0] == first
    assert client.get("/api/catalog/listings/not-present").status_code == 404
    assert (
        client.get("/api/catalog/compare", params=[("ids", i) for i in ids + [ids[0]]]).status_code
        == 422
    )
    assert (
        client.get("/api/catalog/compare", params=[("ids", ids[0]), ("ids", ids[0])]).status_code
        == 422
    )
    peers = [
        r["price"]
        for r in client.app.state.catalog
        if r["id"] != first["id"]
        and r["roomType"] == first["roomType"]
        and r["district"] == first["district"]
    ]
    assert first["reference"] == {"n": len(peers), "median": median(peers)}


def test_catalog_does_not_call_full_training_model(client, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Catalog must never infer on the full training model")

    monkeypatch.setattr(client.app.state.model, "predict", forbidden)
    assert client.get("/api/catalog/listings").status_code == 200
    first = next(iter(client.app.state.by_id))
    assert client.get(f"/api/catalog/listings/{first}").status_code == 200
    assert client.get("/api/catalog/compare", params={"ids": first}).status_code == 200


def test_estimator_same_prediction_as_frozen_api_and_no_fit(client, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("No online fitting")

    monkeypatch.setattr(client.app.state.model, "fit", forbidden)
    result = client.post("/api/estimate", json=REQUEST)
    assert result.status_code == 200
    assert (
        result.json()["estimated_price_eur"]
        == client.post("/api/predict", json=REQUEST).json()["estimated_price_eur"]
    )
    assert result.json()["method"] == "full_train" and result.json()["warnings"]
    assert client.post("/api/estimate", json={**REQUEST, "price": 1}).status_code == 422
    assert client.post("/api/estimate", json={**REQUEST, "district": "Pankow"}).status_code == 422
    assert (
        client.post(
            "/api/estimate", json={**REQUEST, "property_type": "Private room in rental unit"}
        ).status_code
        == 422
    )
    assert client.get("/api/location", params={"latitude": 52.52, "longitude": 13.405}).json() == {
        "district": "Mitte"
    }
    assert (
        client.get("/api/location", params={"latitude": 52.301, "longitude": 13.051}).status_code
        == 422
    )


def test_expensive_and_rare_rows_carry_warnings(client):
    for row in client.app.state.catalog:
        assert ("high_price" in row["model"]["warnings"]) == (row["price"] > 400)
        assert ("small_sample" in row["model"]["warnings"]) == (
            row["roomType"] in {"Hotel room", "Shared room"}
        )


def test_ring_and_polygon_holes():
    ring = [[0, 0], [4, 0], [4, 4], [0, 4], [0, 0]]
    assert ring_contains(ring, 0, 2) and ring_contains(ring, 2, 2)
    assert not ring_contains(ring, 5, 2)
    geo = {
        "features": [
            {
                "properties": {"neighbourhood_group": "A"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [ring, [[1, 1], [3, 1], [3, 3], [1, 3], [1, 1]]],
                },
            }
        ]
    }
    assert locate_district(geo, 0.5, 0.5) == "A"
    assert locate_district(geo, 2, 2) is None


def test_catalog_tampering_or_identity_fields_fail_startup(tmp_path):
    for name in ["manifest.json", "catalog.json", "neighbourhoods.geojson"]:
        shutil.copyfile(CATALOG / name, tmp_path / name)
    data = json.loads((tmp_path / "catalog.json").read_text(encoding="utf-8"))
    data["listings"][0]["host_id"] = "must-not-be-served"
    (tmp_path / "catalog.json").write_text(json.dumps(data), encoding="utf-8")
    with (
        pytest.raises(ValueError, match="checksum"),
        TestClient(create_application(catalog_dir=tmp_path)),
    ):
        pass
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    manifest["catalog_sha256"] = sha256(tmp_path / "catalog.json")
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with (
        pytest.raises(ValueError, match="host_id"),
        TestClient(create_application(catalog_dir=tmp_path)),
    ):
        pass
