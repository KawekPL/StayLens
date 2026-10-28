"""One explicit, target-free feature contract for offline training and serving."""

import json
import math
import re

import numpy as np
import pandas as pd

CATEGORICAL = ["district", "room_type", "property_type"]
AMENITIES = [
    "wifi",
    "kitchen",
    "washer",
    "air_conditioning",
    "elevator",
    "parking",
    "workspace",
    "self_check_in",
]
NUMERIC = [
    "latitude",
    "longitude",
    "accommodates",
    "bedrooms",
    "beds",
    "bathrooms",
    "minimum_nights",
    *AMENITIES,
]
FEATURES = CATEGORICAL + NUMERIC


def number(value):
    try:
        parsed = float(str(value).replace("$", "").replace(",", ""))
        return parsed if math.isfinite(parsed) else np.nan
    except (TypeError, ValueError):
        return np.nan


def bathrooms(row):
    numeric = number(row.get("bathrooms"))
    if math.isfinite(numeric):
        return numeric
    text = str(row.get("bathrooms_text", "")).casefold()
    match = re.search(r"\d+(?:\.\d+)?", text)
    if match:
        return float(match.group())
    return 0.5 if "half-bath" in text else np.nan


def amenity_flags(raw):
    try:
        values = json.loads(raw)
    except (ValueError, TypeError):
        values = None
    if not isinstance(values, list) or not all(isinstance(x, str) for x in values):
        return dict.fromkeys(AMENITIES, np.nan)
    values = [x.casefold().strip() for x in values]
    # Word boundaries avoid e.g. dishwasher being interpreted as a clothes washer.
    patterns = {
        "wifi": r"\bwi-?fi\b",
        "kitchen": r"\bkitchen\b",
        "washer": r"\bwasher\b",
        "air_conditioning": r"\bair conditioning\b",
        "elevator": r"\belevator\b",
        "parking": r"\bparking\b",
        "workspace": r"\bdedicated workspace\b",
        "self_check_in": r"\bself check-in\b",
    }
    return {
        key: float(any(re.search(pattern, v) for v in values)) for key, pattern in patterns.items()
    }


def source_features(row):
    return {
        "district": row.get("neighbourhood_group_cleansed")
        or row.get("neighbourhood_cleansed")
        or "unknown",
        "room_type": row.get("room_type") or "unknown",
        "property_type": row.get("property_type") or "unknown",
        **{key: number(row.get(key)) for key in NUMERIC if key not in AMENITIES},
        "bathrooms": bathrooms(row),
        **amenity_flags(row.get("amenities")),
    }


def feature_frame(records):
    """Project to allowlisted features, preserving unknown numeric values as NaN."""
    frame = pd.DataFrame(records).reindex(columns=FEATURES).copy()
    for column in CATEGORICAL:
        frame[column] = frame[column].astype("string").fillna("unknown").astype(str)
    for column in NUMERIC:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").astype(float)
    return frame
