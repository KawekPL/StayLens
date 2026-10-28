"""Check prepared catalogue provenance and real HTTP, without fitting/evaluating test."""

import json
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

from staylens.data import host_split, sha256

ROOT = Path(__file__).resolve().parents[1]


def request(path, payload=None):
    body = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:5174" + path,
        data=body,
        headers={"Content-Type": "application/json"} if body else {},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


def main():
    directory = ROOT / "data/prepared/s03"
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    data = json.loads((directory / "catalog.json").read_text(encoding="utf-8"))
    assert sha256(directory / "catalog.json") == manifest["catalog_sha256"]
    assert sha256(ROOT / "scripts/build_catalog.py") == manifest["builder_sha256"]
    cv_path = ROOT / "artifacts/s02-v1/cv_predictions.csv"
    assert sha256(cv_path) == manifest["oof_predictions_sha256"]
    cv = pd.read_csv(cv_path, dtype={"listing_id": str, "host_id": str}).set_index("listing_id")
    assert cv.host_id.map(host_split).eq("train").all()
    assert len(data["listings"]) == len(cv) == 5814
    for row in data["listings"]:
        assert row["model"]["estimatedPrice"] == round(
            cv.loc[row["id"], "hist_gradient_boosting"], 2
        )
        assert row["price"] == cv.loc[row["id"], "price"]
        assert "host_id" not in json.dumps(row)
    assert not (ROOT / "frontend/public/data/listings.json").exists()
    status, meta = request("/api/catalog/meta")
    assert status == 200 and meta["catalogPredictionMethod"] == "host_oof"
    status, page = request("/api/catalog/listings")
    assert status == 200 and len(page["items"]) == 12 and page["total"] == 3438
    first = page["items"][0]
    status, detail = request(f"/api/catalog/listings/{first['id']}")
    assert status == 200 and detail == first
    status, compare = request(f"/api/catalog/compare?ids={first['id']}")
    assert status == 200 and compare["items"] == [first]
    payload = {
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
    status, estimate = request("/api/estimate", payload)
    assert status == 200 and estimate["method"] == "full_train"
    status, original = request("/api/predict", payload)
    assert status == 200 and estimate["estimated_price_eur"] == original["estimated_price_eur"]
    assert request("/api/estimate", {**payload, "price": 10})[0] == 422
    assert request("/api/catalog/listings?limit=1000")[0] == 422
    assert request("/api/catalog/listings/unknown")[0] == 404
    # Earlier experiments retain their original source hashes, even after serving integration.
    s02 = json.loads((ROOT / "reports/s02/comparison.json").read_text(encoding="utf-8"))
    for name, digest in s02["source_code_sha256"].items():
        assert sha256(ROOT / name.replace("\\", "/")) == digest
    checks = {
        "passed": True,
        "catalog_rows": 5814,
        "only_train_hosts": True,
        "oof_prices_verified_for_every_row": True,
        "original_s02_code_unchanged": True,
        "static_bulk_catalog_removed": True,
        "proxy_http": {
            "meta": 200,
            "page": 200,
            "detail": 200,
            "compare": 200,
            "estimate": 200,
            "bad_payload": 422,
            "oversized_page": 422,
            "unknown_id": 404,
            "default_total": page["total"],
            "estimate_matches_frozen_api": True,
        },
        "test_evaluated": False,
        "cloud_deployed": False,
    }
    (ROOT / "reports/s03/verification.json").write_text(
        json.dumps(checks, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
