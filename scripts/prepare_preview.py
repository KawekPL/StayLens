"""Fetch a pinned public snapshot and prepare a privacy-reduced TRAIN-only UI preview.

Uses only Python's standard library. No model is fitted by this command.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import shutil
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = "2026-09-19"
BASE = f"https://data.insideairbnb.com/germany/be/berlin/{SNAPSHOT}"
URLS = {
    "listings.csv.gz": f"{BASE}/data/listings.csv.gz",
    "neighbourhoods.geojson": f"{BASE}/visualisations/neighbourhoods.geojson",
}
EXPECTED_SHA256 = {
    "listings.csv.gz": "657ea25841a3f9a5be45dd1db011804f8b29dd7e4d8143b961f4704ee6bf7673",
    "neighbourhoods.geojson": "b2941e38593025425d23209ff457e17a3da2afd45502fd288675bec1727708bd",
}


def download(url: str, destination: Path) -> None:
    if destination.exists():
        return
    temporary = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "StayLens-course-project/0.1"})
    with urllib.request.urlopen(request, timeout=90) as response, temporary.open("wb") as output:
        shutil.copyfileobj(response, output)
    temporary.replace(destination)


def number(value: str):
    try:
        parsed = float(value.replace("$", "").replace(",", ""))
        return parsed if math.isfinite(parsed) else None
    except (ValueError, AttributeError):
        return None


def split(host_id: str) -> str:
    # A host and every listing belonging to it always have the same assignment.
    digest = hashlib.sha256(f"staylens-v1:{host_id}".encode()).hexdigest()
    bucket = int(digest[:8], 16) % 100
    return "train" if bucket < 70 else "validation" if bucket < 85 else "test"


def main() -> None:
    raw = ROOT / "data" / "raw"
    public = ROOT / "frontend" / "public" / "data"
    raw.mkdir(parents=True, exist_ok=True)
    public.mkdir(parents=True, exist_ok=True)
    for name, url in URLS.items():
        download(url, raw / name)
        if hashlib.sha256((raw / name).read_bytes()).hexdigest() != EXPECTED_SHA256[name]:
            raise ValueError(f"Source checksum mismatch: {name}. Investigate before replacing the pin.")
    with gzip.open(raw / "listings.csv.gz", "rt", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError("Source contains no listings")
    required = {"id", "host_id", "price", "latitude", "longitude", "room_type", "accommodates"}
    if not required.issubset(rows[0]):
        raise ValueError("Source schema does not match the declared contract")
    reasons = Counter()
    counts = Counter()
    records = []
    seen = set()
    for row in rows:
        if row["id"] in seen:
            raise ValueError("Duplicate listing ID in the snapshot")
        seen.add(row["id"])
        price = number(row["price"])
        lat, lon = number(row["latitude"]), number(row["longitude"])
        if price is None or price <= 0:
            reasons["missing_or_nonpositive_price"] += 1
            continue
        if lat is None or lon is None or not (52.3 < lat < 52.7 and 13.05 < lon < 13.8):
            reasons["invalid_berlin_coordinates"] += 1
            continue
        if not row["host_id"]:
            reasons["missing_host_id"] += 1
            continue
        subset = split(row["host_id"])
        counts[subset] += 1
        if subset != "train":
            continue
        records.append({
            "id": row["id"], "title": row.get("name", "Nocleg w Berlinie"),
            "district": row.get("neighbourhood_group_cleansed") or row["neighbourhood_cleansed"],
            "neighbourhood": row["neighbourhood_cleansed"],
            "lat": lat, "lon": lon, "price": price,
            "roomType": row["room_type"], "guests": number(row["accommodates"]),
            "bedrooms": number(row.get("bedrooms", "")), "beds": number(row.get("beds", "")),
            "bathrooms": number(row.get("bathrooms", "")),
            "rating": number(row.get("review_scores_rating", "")),
            "reviews": number(row.get("number_of_reviews", "")) or 0,
            "minNights": number(row.get("minimum_nights", "")),
            "image": row.get("picture_url", "") if row.get("picture_url", "").startswith("https://") else "",
            "url": f"https://www.airbnb.com/rooms/{row['id']}",
        })
    records.sort(key=lambda record: record["id"])
    geo = json.loads((raw / "neighbourhoods.geojson").read_text(encoding="utf-8"))
    if geo.get("type") != "FeatureCollection":
        raise ValueError("Unexpected geographic data")
    (public / "neighbourhoods.geojson").write_text(json.dumps(geo, ensure_ascii=False), encoding="utf-8")
    source_files = [{"file": name, "url": url,
                     "sha256": hashlib.sha256((raw / name).read_bytes()).hexdigest(),
                     "bytes": (raw / name).stat().st_size} for name, url in URLS.items()]
    metadata = {
        "city": "Berlin", "snapshot": SNAPSHOT, "currency": "EUR",
        "source": "Inside Airbnb", "sourceUrl": "https://insideairbnb.com/get-the-data/",
        "license": "CC BY 4.0", "subset": "train", "rawRows": len(rows),
        "previewRows": len(records), "splitCounts": dict(counts),
        "excluded": dict(reasons), "districts": sorted({r["district"] for r in records}),
        "mlStatus": "not_trained",
    }
    (public / "listings.json").write_text(json.dumps({"meta": metadata, "listings": records}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    report = {
        **metadata, "createdAt": datetime.now(timezone.utc).isoformat(), "files": source_files,
        "sourceColumns": list(rows[0]), "geographicFeatures": len(geo["features"]),
        "splitMethod": "SHA256(staylens-v1:host_id), first 8 hex chars modulo 100; 70/15/15 buckets",
        "priceUnits": "Local currency EUR; $ in CSV is an export artifact (source data dictionary)",
        "images": "Remote references only; image copyrights are not asserted to be covered by dataset license",
        "limitations": ["Listing prices, not completed transaction prices", "Historical snapshot, not current availability", "Public preview contains only training groups", "No fitted ML model or evaluation results yet"],
    }
    (ROOT / "reports" / "data_preflight.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"rawRows": len(rows), "previewRows": len(records), "splits": counts, "excluded": reasons, "districts": metadata["districts"], "snapshot": SNAPSHOT}, ensure_ascii=False))


if __name__ == "__main__":
    main()
