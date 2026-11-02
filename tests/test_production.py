import json
import shutil
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from staylens.production import create_production_app


def test_production_serves_only_static_allowlist_and_keeps_model(tmp_path):
    shutil.copyfile(
        Path(__file__).resolve().parents[1] / "frontend/public/final-evaluation.json",
        tmp_path / "final-evaluation.json",
    )
    (tmp_path / "index.html").write_text("<title>StayLens</title>")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets/app-123.js").write_text("console.log('ok')")
    with TestClient(create_production_app(tmp_path)) as client:
        assert client.get("/").text == "<title>StayLens</title>"
        assert client.get("/").headers["x-content-type-options"] == "nosniff"
        assert "immutable" in client.get("/assets/app-123.js").headers["cache-control"]
        assert client.get("/health").json()["model_version"] == "s02-v1"
        info = client.get("/api/model").json()
        assert info["test_evaluated"] is True
        assert info["final_evaluation"]["test_rows"] == 1235
        assert info["validation_metrics"]["mae_eur"] == 53.61076632292413
        assert client.get("/api/catalog/listings").json()["total"] == 3438
        for path in ["/.env", "/runtime/model/manifest.json", "/api/unknown", "/../pyproject.toml"]:
            assert client.get(path).status_code == 404


def test_missing_frontend_fails_fast(tmp_path):
    with pytest.raises(RuntimeError, match="frontend"):
        create_production_app(tmp_path)


def test_production_rejects_evaluation_for_another_model(tmp_path):
    (tmp_path / "index.html").write_text("StayLens")
    (tmp_path / "final-evaluation.json").write_text(json.dumps({"model_sha256": "wrong"}))
    with pytest.raises(ValueError, match="different model"):
        create_production_app(tmp_path)


def test_public_evaluation_matches_frozen_final_report():
    root = Path(__file__).resolve().parents[1]
    public = json.loads((root / "frontend/public/final-evaluation.json").read_text())
    report = json.loads((root / "reports/s05/test_evaluation.json").read_text())
    assert public["metrics"] == report["test_metrics"]["hist_gradient_boosting"]
    assert public["baseline_metrics"] == report["test_metrics"]["segment_median"]
    assert public["model_sha256"] == report["model_hashes"]["hist_gradient_boosting"]


def test_release_rejects_tampering_and_unexpected_members(tmp_path):
    from scripts.release_artifacts import archive, validated_contents

    path = tmp_path / "test.zip"
    spec = archive(path, {"safe.json": json.dumps({"safe": True}).encode()})
    assert validated_contents(path, spec, {"safe.json"})["safe.json"]
    with pytest.raises(ValueError, match="members"):
        validated_contents(path, spec, {"../unsafe.json"})
    with zipfile.ZipFile(path, "a") as out:
        out.writestr("../outside", "bad")
    with pytest.raises(ValueError, match="checksum"):
        validated_contents(path, spec, {"safe.json"})
