"""Real HTTP checks for the same image locally, in CI, and on Azure; no model fitting."""

import argparse
import json
import math
import time
import urllib.error
import urllib.request
from pathlib import Path

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
    "wifi": True,
    "kitchen": True,
    "washer": True,
    "air_conditioning": False,
    "elevator": True,
    "parking": False,
    "workspace": True,
    "self_check_in": True,
}


def run(base, revision=None):
    def request(path, payload=None, status=200):
        data = None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request(
            base.rstrip("/") + path, data=data, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                code, body = response.status, response.read()
        except urllib.error.HTTPError as error:
            code, body = error.code, error.read()
        assert code == status, (path, code, body[:300])
        return body

    for attempt in range(24):
        try:
            health = json.loads(request("/health"))
            break
        except (OSError, AssertionError):
            if attempt == 23:
                raise
            time.sleep(5)
    assert health == {"status": "ok", "model_version": "s02-v1"}
    assert b"StayLens" in request("/")
    release = json.loads(request("/api/release"))
    if revision:
        assert release["revision"] == revision, release
    model = json.loads(request("/api/model"))
    assert model["test_evaluated"] is True and model["training_rows"] == 5814
    final = model["final_evaluation"]
    assert final["test_rows"] == 1235 and final["test_hosts"] == 624
    assert math.isclose(final["metrics"]["mae_eur"], 56.100734965797365)
    assert (
        final["model_sha256"] == "47ed42c9c8ccec4db103da7ec437ea240d5045191eaf20df9e9e4bd85265d7bf"
    )
    assert math.isclose(model["validation_metrics"]["mae_eur"], 53.610766, abs_tol=0.00001)
    page = json.loads(request("/api/catalog/listings"))
    assert page["total"] == 3438 and len(page["items"]) == 12
    ids = [row["id"] for row in page["items"][:3]]
    assert all(row["model"]["method"] == "host_oof" for row in page["items"])
    assert b"host_id" not in json.dumps(page).encode()
    request("/api/catalog/listings/" + ids[0])
    comparison = json.loads(request("/api/catalog/compare?" + "&".join("ids=" + i for i in ids)))
    assert [row["id"] for row in comparison["items"]] == ids
    estimate = json.loads(request("/api/estimate", REQUEST))
    assert estimate["estimated_price_eur"] == 181.30 and estimate["method"] == "full_train"
    request("/api/estimate", {**REQUEST, "price": 1}, 422)
    request("/api/catalog/listings?limit=61", status=422)
    request("/api/catalog/listings/missing", status=404)
    for path in [
        "/.env",
        "/runtime/model/manifest.json",
        "/data/raw/listings.csv.gz",
        "/api/not-a-route",
    ]:
        request(path, status=404)
    return {
        "base_url": base,
        "release": release,
        "health": health,
        "catalog_total": page["total"],
        "estimate_eur": estimate["estimated_price_eur"],
        "model_unchanged": True,
        "test_evaluated": True,
        "test_mae_eur": final["metrics"]["mae_eur"],
        "http_checks": "passed",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("--revision")
    parser.add_argument("--output")
    args = parser.parse_args()
    result = run(args.url, args.revision)
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding="utf-8")
    print(rendered)
