"""Zbuduj katalog z train i zapisanych prognoz CV. Nie trenuje modelu."""

import argparse
import csv
import gzip
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import median

import pandas as pd

from staylens.catalog import Listing
from staylens.data import SOURCE_SHA256, host_split, sha256
from staylens.features import number, source_features

ROOT = Path(__file__).resolve().parents[1]


def nullable(value):
    value = number(value)
    return value if math.isfinite(value) else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, default=ROOT / "artifacts/training-run")
    parser.add_argument("--output", type=Path, default=ROOT / "data/prepared/catalog")
    args = parser.parse_args()
    source = ROOT / "data/raw/listings.csv.gz"
    artifact = args.artifact_dir
    cv_path = artifact / "cv_predictions.csv"
    if sha256(source) != SOURCE_SHA256:
        raise ValueError("Pinned source changed")
    model = json.loads((artifact / "manifest.json").read_text(encoding="utf-8"))
    if sha256(cv_path) != model["oof_predictions_sha256"]:
        raise ValueError("OOF predictions do not belong to this training run")
    predictions = pd.read_csv(cv_path, dtype={"listing_id": str, "host_id": str}).set_index(
        "listing_id"
    )
    if not predictions.index.is_unique:
        raise ValueError("Duplicate OOF listing IDs")
    rows, groups, pairs = [], defaultdict(list), defaultdict(set)
    with gzip.open(source, "rt", encoding="utf-8-sig", newline="") as stream:
        for record in csv.DictReader(stream):
            if not record.get("host_id") or host_split(record["host_id"]) != "train":
                continue
            price, lat, lon = (number(record[key]) for key in ["price", "latitude", "longitude"])
            if not (price > 0 and 52.3 < lat < 52.7 and 13.05 < lon < 13.8):
                continue
            predicted = predictions.loc[record["id"]]
            if predicted.host_id != record["host_id"] or predicted.price != price:
                raise ValueError("OOF/source identity or target mismatch")
            estimate = float(predicted[model["selected_model"]])
            if not math.isfinite(estimate) or estimate <= 0:
                raise ValueError("Invalid saved prediction")
            features = source_features(record)
            warnings = []
            if price > 400:
                warnings.append("high_price")
            if record["room_type"] in {"Hotel room", "Shared room"}:
                warnings.append("small_sample")
            if any(
                not math.isfinite(features[k])
                for k in ["bedrooms", "beds", "bathrooms", "minimum_nights"]
            ):
                warnings.append("missing_features")
            row = {
                "id": record["id"],
                "title": record.get("name") or "Nocleg w Berlinie",
                "district": features["district"],
                "neighbourhood": record["neighbourhood_cleansed"],
                "lat": lat,
                "lon": lon,
                "price": price,
                "roomType": record["room_type"],
                "guests": features["accommodates"],
                "bedrooms": nullable(record.get("bedrooms")),
                "beds": nullable(record.get("beds")),
                "bathrooms": features["bathrooms"]
                if math.isfinite(features["bathrooms"])
                else None,
                "rating": nullable(record.get("review_scores_rating")),
                "reviews": nullable(record.get("number_of_reviews")) or 0,
                "minNights": features["minimum_nights"]
                if math.isfinite(features["minimum_nights"])
                else None,
                "image": record["picture_url"]
                if record.get("picture_url", "").startswith("https://")
                else "",
                "url": f"https://www.airbnb.com/rooms/{record['id']}",
                "model": {
                    "estimatedPrice": round(estimate, 2),
                    "deltaPercent": round((price / estimate - 1) * 100, 1),
                    "method": "host_oof",
                    "modelVersion": model["model_version"],
                    "warnings": warnings,
                },
            }
            rows.append(row)
            groups[(row["district"], row["roomType"])].append(row)
            pairs[row["roomType"]].add(record["property_type"])
    if len(rows) != model["training_rows"] or {r["id"] for r in rows} != set(predictions.index):
        raise ValueError("Catalog must cover exactly the real train rows")
    for row in rows:
        peers = [
            r["price"] for r in groups[(row["district"], row["roomType"])] if r["id"] != row["id"]
        ]
        row["reference"] = {"n": len(peers), "median": median(peers) if peers else None}
        Listing.model_validate(row)
    rows.sort(key=lambda r: r["id"])
    meta = {
        "city": "Berlin",
        "snapshot": model["snapshot"],
        "currency": "EUR",
        "source": "Inside Airbnb",
        "sourceUrl": "https://insideairbnb.com/get-the-data/",
        "license": "CC BY 4.0",
        "subset": "train",
        "previewRows": len(rows),
        "districts": sorted({r["district"] for r in rows}),
        "propertyTypesByRoom": {key: sorted(value) for key, value in pairs.items()},
        "modelVersion": model["model_version"],
        "catalogPredictionMethod": "host_oof",
        "formPredictionMethod": "full_train",
        "maeEur": model["validation_metrics"]["mae_eur"],
        "cvMaeEur": model["cv_metrics"]["mae_eur"],
        "testEvaluated": False,
    }
    out = args.output
    out.mkdir(parents=True, exist_ok=False)
    (out / "catalog.json").write_text(
        json.dumps(
            {"meta": meta, "listings": rows},
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
        newline="\n",
    )
    geo = ROOT / "data/raw/neighbourhoods.geojson"
    if sha256(geo) != "b2941e38593025425d23209ff457e17a3da2afd45502fd288675bec1727708bd":
        raise ValueError("Pinned geography changed")
    (out / "neighbourhoods.geojson").write_bytes(geo.read_bytes())
    manifest = {
        "catalog_sha256": sha256(out / "catalog.json"),
        "source_sha256": SOURCE_SHA256,
        "geo_sha256": sha256(geo),
        "model_sha256": model["model_sha256"],
        "oof_predictions_sha256": sha256(cv_path),
        "builder_sha256": sha256(Path(__file__)),
        "rows": len(rows),
        "scope": "train only; host_oof, not full-train predictions",
        "public_host_ids": False,
        "test_evaluated": False,
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
