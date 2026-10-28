import json
from pathlib import Path

import numpy as np
import pytest

from staylens.data import host_split
from staylens.evaluation import metrics, select_model
from staylens.features import FEATURES, amenity_flags, bathrooms, feature_frame, source_features
from staylens.models import SegmentMedian

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("raw", "text", "expected"),
    [
        ("", "1.5 shared baths", 1.5),
        ("", "Shared half-bath", 0.5),
        ("2", "1 bath", 2),
        ("", "0 baths", 0),
    ],
)
def test_bathroom_recovery(raw, text, expected):
    assert bathrooms({"bathrooms": raw, "bathrooms_text": text}) == expected


def test_unknown_amenities_are_distinct_from_absence():
    assert all(np.isnan(x) for x in amenity_flags("").values())
    assert all(x == 0 for x in amenity_flags("[]").values())
    flags = amenity_flags('["Dishwasher", "Fast wifi – 100 Mbps", "Free washer – In unit"]')
    assert flags["washer"] == 1 and flags["wifi"] == 1
    assert amenity_flags('["Dishwasher"]')["washer"] == 0


def test_allowlist_drops_target_identity_and_text():
    row = {
        "host_id": "PRIVATE",
        "price": "$1000",
        "description": "Ignore instructions",
        "amenities": "[]",
    }
    assert set(source_features(row)) == set(FEATURES)
    frame = feature_frame([{**source_features(row), "price": 1000, "host_id": "PRIVATE"}])
    assert list(frame) == FEATURES
    assert "PRIVATE" not in frame.to_string()


def test_segment_fallback_uses_fitted_values_only():
    x = feature_frame([{"district": "Mitte", "room_type": "Private room", "accommodates": 2}] * 10)
    model = SegmentMedian().fit(x, np.arange(10) + 10)
    unknown = x.iloc[:1].copy()
    unknown["district"] = "unseen"
    unknown["room_type"] = "unseen"
    assert model.predict(unknown)[0] == 14.5
    assert model.predict(x)[0] == 14.5


def test_metric_units_and_tail_sensitivity():
    value = metrics([100, 200, 300], [90, 250, 500])
    assert value["mae_eur"] == pytest.approx(260 / 3)
    assert value["median_absolute_error_eur"] == 50
    assert value["rmse_eur"] == pytest.approx(np.sqrt(42600 / 3))
    assert value["within_20_percent"] == pytest.approx(1 / 3)


def test_selection_rejects_candidate_with_bad_rmse():
    protocol = json.loads((ROOT / "configs/s02_protocol.json").read_text())
    base = {"mae_eur": 100, "rmse_eur": 200, "median_absolute_error_eur": 50}
    candidate = {"mae_eur": 70, "rmse_eur": 250, "median_absolute_error_eur": 40}
    values = {"segment_median": base, "hist_gradient_boosting": candidate}
    selection = select_model(values, values, protocol["selection"])
    assert selection["selected"] == "segment_median"
    assert selection["checks"]["validation_rmse"] is False


def test_host_assignment_stable():
    assert host_split("123") == host_split("123")
    assert {host_split(str(i)) for i in range(100)} == {"train", "validation", "test"}
