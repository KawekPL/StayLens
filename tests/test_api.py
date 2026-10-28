import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from staylens.api import PriceRequest, create_app, load_artifact
from staylens.features import feature_frame
from staylens.models import predict_prices

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts" / "s02-v1"
EXAMPLE = {
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
    "wifi": True,
    "kitchen": True,
    "washer": True,
    "air_conditioning": False,
    "elevator": True,
    "parking": False,
    "workspace": True,
    "self_check_in": True,
}


@pytest.fixture
def client():
    if not (ARTIFACT / "manifest.json").exists():
        pytest.skip("Run scripts/run_s02.py to produce integration-test artifacts")
    with TestClient(create_app(ARTIFACT)) as value:
        yield value


def test_api_matches_serialized_offline_model(client):
    model, _ = load_artifact(ARTIFACT)
    expected = predict_prices(model, feature_frame([EXAMPLE]))[0]
    response = client.post("/api/predict", json=EXAMPLE)
    assert response.status_code == 200
    assert response.json()["estimated_price_eur"] == round(expected, 2)
    assert response.json()["currency"] == "EUR"
    assert client.get("/health").json()["status"] == "ok"
    info = client.get("/api/model").json()
    assert info["test_evaluated"] is False
    assert "host_id" not in info["features"]
    assert client.get("/api/schema").status_code == 200
    assert client.get("/openapi.json").status_code == 200


@pytest.mark.parametrize(
    "change",
    [
        {"price": 100},
        {"host_id": "123"},
        {"latitude": 50.0},
        {"accommodates": 17},
        {"accommodates": "2"},
        {"wifi": "yes"},
        {"district": "Warszawa"},
        {"room_type": "spaceship"},
        {"minimum_nights": 0},
        {"bedrooms": -1.0},
    ],
)
def test_reject_bad_or_leaky_input(client, change):
    assert client.post("/api/predict", json={**EXAMPLE, **change}).status_code == 422


def test_reject_nonfinite_input():
    with pytest.raises(ValueError):
        PriceRequest(**{**EXAMPLE, "latitude": np.inf})


def test_unknown_property_and_missing_features_are_safe(client):
    request = {
        key: EXAMPLE[key]
        for key in [
            "district",
            "room_type",
            "property_type",
            "latitude",
            "longitude",
            "accommodates",
        ]
    }
    request["property_type"] = "unseen property type"
    response = client.post("/api/predict", json=request)
    assert response.status_code == 200
    assert response.json()["estimated_price_eur"] > 0
    assert len(response.json()["warnings"]) >= 2


def test_model_is_not_reloaded_or_fitted_on_request(client, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("No artifact load / model fit during prediction")

    monkeypatch.setattr("staylens.api.load_artifact", forbidden)
    monkeypatch.setattr(client.app.state.model, "fit", forbidden)
    for _ in range(2):
        assert client.post("/api/predict", json=EXAMPLE).status_code == 200


def test_missing_artifact_prevents_start(tmp_path):
    with pytest.raises(FileNotFoundError), TestClient(create_app(tmp_path)):
        pass


def test_corrupt_model_rejected_before_deserialization(tmp_path, monkeypatch):
    manifest = {"model_file": "broken.joblib", "model_sha256": "0" * 64}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    (tmp_path / "broken.joblib").write_bytes(b"not a model")

    def forbidden(*args, **kwargs):
        raise AssertionError("Deserialization must not be attempted")

    monkeypatch.setattr("staylens.api.joblib.load", forbidden)
    with pytest.raises(ValueError, match="checksum"):
        load_artifact(tmp_path)


def test_saved_metrics_recomputed_independently():
    if not (ARTIFACT / "manifest.json").exists():
        pytest.skip("S02 artifacts required")
    report = json.loads((ROOT / "reports/s02/comparison.json").read_text(encoding="utf-8"))
    for name, key in [("validation", "validation"), ("cv", "cv_pooled")]:
        data = pd.read_csv(ARTIFACT / f"{name}_predictions.csv")
        for model in ["segment_median", "hist_gradient_boosting"]:
            error = np.abs(data.price.to_numpy() - data[model].to_numpy())
            assert float(error.mean()) == pytest.approx(report[key][model]["mae_eur"])
            assert float(np.median(error)) == pytest.approx(
                report[key][model]["median_absolute_error_eur"]
            )
            assert float(np.sqrt((error**2).mean())) == pytest.approx(
                report[key][model]["rmse_eur"]
            )
    assert report["test_evaluated"] is False
    assert all(fold["host_overlap"] == 0 for fold in report["cv_folds"])
