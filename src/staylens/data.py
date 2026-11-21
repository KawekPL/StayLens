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
    if bucket < 70:
        return "train"
    if bucket < 85:
        return "validation"
    return "test"


def load_development(path: Path):
    if sha256(path) != SOURCE_SHA256:
        raise ValueError("Pinned source checksum mismatch")
    records = []
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
    return train, validation
