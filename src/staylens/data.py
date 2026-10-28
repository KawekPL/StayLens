"""Pinned snapshot loading. S02 cannot request the final test partition."""

import csv
import gzip
import hashlib
import math
from pathlib import Path

import pandas as pd

from staylens.features import number, source_features

SOURCE_SHA256 = "657ea25841a3f9a5be45dd1db011804f8b29dd7e4d8143b961f4704ee6bf7673"


def sha256(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def host_split(host_id):
    digest = hashlib.sha256(f"staylens-v1:{host_id}".encode()).hexdigest()
    bucket = int(digest[:8], 16) % 100
    return "train" if bucket < 70 else "validation" if bucket < 85 else "test"


def load_development(path: Path):
    if sha256(path) != SOURCE_SHA256:
        raise ValueError("Pinned source checksum mismatch")
    records = []
    raw_bathrooms_missing = 0
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if not row.get("host_id"):
                continue
            subset = host_split(row["host_id"])
            if subset == "test":
                # Do not inspect test target/features, even for diagnostics.
                continue
            price = number(row.get("price"))
            lat, lon = number(row.get("latitude")), number(row.get("longitude"))
            if not (
                math.isfinite(price) and price > 0 and 52.3 < lat < 52.7 and 13.05 < lon < 13.8
            ):
                continue
            if subset == "train" and not math.isfinite(number(row.get("bathrooms"))):
                raw_bathrooms_missing += 1
            records.append(
                {
                    **source_features(row),
                    "listing_id": row["id"],
                    "host_id": row["host_id"],
                    "split": subset,
                    "price": price,
                }
            )
    data = pd.DataFrame(records)
    if data["listing_id"].duplicated().any():
        raise ValueError("Duplicate listing IDs")
    train = data[data["split"] == "train"].reset_index(drop=True)
    validation = data[data["split"] == "validation"].reset_index(drop=True)
    if set(train["host_id"]) & set(validation["host_id"]):
        raise ValueError("Host leakage")
    if len(train) != 5814 or len(validation) != 1108:
        raise ValueError("Unexpected development partition size")
    return train, validation, {"train_raw_bathrooms_missing": raw_bathrooms_missing}


def training_audit(train, features, extra):
    x = train[features]
    return {
        "scope": "train only",
        "rows": len(train),
        "hosts": int(train.host_id.nunique()),
        **extra,
        "missing_features": x.isna().sum().astype(int).to_dict(),
        "price_quantiles_eur": {
            str(q): float(train.price.quantile(q)) for q in [0, 0.5, 0.95, 0.99, 1]
        },
        "room_type_counts": train.room_type.value_counts().astype(int).to_dict(),
        "identical_feature_rows_beyond_first": int(x.duplicated().sum()),
        "numeric_ranges": {
            key: {"min": float(x[key].min()), "max": float(x[key].max())}
            for key in features
            if pd.api.types.is_numeric_dtype(x[key])
        },
        "excluded_features": [
            "price",
            "host_id",
            "listing_id",
            "name",
            "description",
            "picture_url",
            "reviews",
            "ratings",
            "revenue",
            "occupancy",
            "availability",
        ],
    }
