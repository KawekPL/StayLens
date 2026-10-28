import json
import zipfile

import pytest
from fastapi.testclient import TestClient

from staylens.production import create_production_app


def test_production_serves_only_static_allowlist_and_keeps_model(tmp_path):
    (tmp_path / "index.html").write_text("<title>StayLens</title>")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets/app-123.js").write_text("console.log('ok')")
    with TestClient(create_production_app(tmp_path)) as client:
        assert client.get("/").text == "<title>StayLens</title>"
        assert client.get("/").headers["x-content-type-options"] == "nosniff"
        assert "immutable" in client.get("/assets/app-123.js").headers["cache-control"]
        assert client.get("/health").json()["model_version"] == "s02-v1"
        assert client.get("/api/catalog/listings").json()["total"] == 3438
        for path in ["/.env", "/runtime/model/manifest.json", "/api/unknown", "/../pyproject.toml"]:
            assert client.get(path).status_code == 404


def test_missing_frontend_fails_fast(tmp_path):
    with pytest.raises(RuntimeError, match="frontend"):
        create_production_app(tmp_path)


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
