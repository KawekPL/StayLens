"""S02b features, derived without target values. The original S02 stays frozen."""

import csv
import gzip
import json
import re

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

from staylens.data import SOURCE_SHA256, host_split, sha256
from staylens.features import AMENITIES, CATEGORICAL, NUMERIC, number, source_features

EXTRA_AMENITIES = [
    "dishwasher",
    "clothes_dryer",
    "outdoor_space",
    "private_outdoor_space",
    "bathtub",
    "hot_tub",
    "sauna",
    "waterfront",
    "water_view",
    "gym",
    "fireplace",
    "free_onsite_parking",
    "swimming_pool",
]
ENGINEERED_CATEGORICAL = CATEGORICAL + ["neighbourhood"]
RAW_NUMERIC = NUMERIC + EXTRA_AMENITIES + ["bathroom_shared"]
RAW_FEATURES = ENGINEERED_CATEGORICAL + RAW_NUMERIC
DERIVED = [
    "guests_per_bedroom",
    "beds_per_guest",
    "bathrooms_per_guest",
    "reference_distance_km",
    "missing_basic_count",
]
ENGINEERED_NUMERIC = RAW_NUMERIC + DERIVED
ENGINEERED_FEATURES = ENGINEERED_CATEGORICAL + ENGINEERED_NUMERIC
MASKABLE = AMENITIES + EXTRA_AMENITIES


def extra_amenity_flags(raw):
    try:
        values = json.loads(raw)
    except (ValueError, TypeError):
        values = None
    if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
        return dict.fromkeys(EXTRA_AMENITIES, np.nan)
    values = [v.casefold().strip() for v in values]
    patterns = {
        "dishwasher": r"\bdishwasher\b",
        "clothes_dryer": r"^(?:(?:free|paid) )?dryer\b",
        "outdoor_space": r"\b(?:patio|balcony|terrace)\b",
        "private_outdoor_space": r"\bprivate (?:patio|balcony|terrace)\b",
        "bathtub": r"\bbathtub\b",
        "hot_tub": r"\bhot tub\b",
        "sauna": r"\bsauna\b",
        "waterfront": r"\bwaterfront\b",
        "water_view": r"\b(?:canal|river|lake|bay|marina|sea) view\b",
        "gym": r"\bgym\b",
        "fireplace": r"^indoor fireplace\b",
        "free_onsite_parking": r"^free (?:.* )?parking.*on premises\b",
        "swimming_pool": r"\bpool\b(?!\s+(?:table|view))",
    }
    return {
        key: float(any(re.search(pattern, v) for v in values)) for key, pattern in patterns.items()
    }


def enriched_source_features(row):
    text = (row.get("bathrooms_text") or "").casefold()
    return {
        **source_features(row),
        "neighbourhood": row.get("neighbourhood_cleansed") or "unknown",
        **extra_amenity_flags(row.get("amenities")),
        "bathroom_shared": float("shared" in text) if text else np.nan,
    }


def load_partition(path, subset):
    if subset not in {"train", "validation"}:
        raise ValueError("S02b permits only train and validation, never test")
    if sha256(path) != SOURCE_SHA256:
        raise ValueError("Pinned source checksum mismatch")
    records = []
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if not row.get("host_id") or host_split(row["host_id"]) != subset:
                continue
            price, lat, lon = (number(row.get(key)) for key in ["price", "latitude", "longitude"])
            if not (price > 0 and 52.3 < lat < 52.7 and 13.05 < lon < 13.8):
                continue
            records.append(
                {
                    **enriched_source_features(row),
                    "price": price,
                    "listing_id": row["id"],
                    "host_id": row["host_id"],
                    "split": subset,
                }
            )
    result = pd.DataFrame(records)
    if (
        len(result) != {"train": 5814, "validation": 1108}[subset]
        or result.listing_id.duplicated().any()
    ):
        raise ValueError("Unexpected partition size or duplicate source listing IDs")
    return result


class EngineerFeatures(TransformerMixin, BaseEstimator):
    """Stateless engineering, kept inside the saved inference pipeline."""

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        result = pd.DataFrame(X).reindex(columns=RAW_FEATURES).copy()
        for key in ENGINEERED_CATEGORICAL:
            result[key] = result[key].astype("string").fillna("unknown").astype(str)
        for key in RAW_NUMERIC:
            result[key] = pd.to_numeric(result[key], errors="coerce").astype(float)
        guests = result.accommodates.where(result.accommodates > 0)
        # A studio (0 bedrooms) is a valid single sleeping space, not a zero divisor.
        rooms = result.bedrooms.clip(lower=1)
        result["guests_per_bedroom"] = guests / rooms
        result["beds_per_guest"] = result.beds / guests
        result["bathrooms_per_guest"] = result.bathrooms / guests
        lat, lon = np.radians(result.latitude), np.radians(result.longitude)
        ref_lat, ref_lon = np.radians([52.52, 13.405])
        a = (
            np.sin((lat - ref_lat) / 2) ** 2
            + np.cos(lat) * np.cos(ref_lat) * np.sin((lon - ref_lon) / 2) ** 2
        )
        result["reference_distance_km"] = 6371 * 2 * np.arcsin(np.sqrt(a.clip(0, 1)))
        result["missing_basic_count"] = (
            result[["bedrooms", "beds", "bathrooms", "minimum_nights"]]
            .isna()
            .sum(axis=1)
            .astype(float)
        )
        return result.reindex(columns=ENGINEERED_FEATURES)
