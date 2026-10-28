import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.base import clone

from staylens.features import FEATURES, NUMERIC, feature_frame
from staylens.research_models import FormFeatures, gate, make_research_models
from staylens.scope_audit import load_scope, purpose_flags

ROOT = Path(__file__).resolve().parents[1]


def test_purpose_flags_do_not_reject_nearby_venues_or_house_rules():
    assert purpose_flags("250 qm penthouse for photoshoot") == ["photo_film_use"]
    assert purpose_flags("BUSINESS EVENT LOCATION – keine Privatfeiern") == ["event_venue"]
    assert not purpose_flags("Loft near a concert hall")
    assert not purpose_flags("Family apartment – no parties or photoshoots")
    assert not purpose_flags("Luxurious penthouse with terrace")
    with pytest.raises(ValueError, match="test"):
        load_scope(Path("missing"), "test")


def test_derived_features_use_only_form_fields_and_preserve_unknowns():
    data = pd.DataFrame(
        [
            {
                "latitude": 52.52,
                "longitude": 13.405,
                "accommodates": 2,
                "bedrooms": 0,
                "beds": 1,
                "bathrooms": None,
                "price": 999999,
                "host_id": "secret",
            }
        ]
    )
    transformed = FormFeatures(True).fit_transform(data)
    assert transformed.loc[0, "guests_per_bedroom"] == 2
    assert transformed.loc[0, "beds_per_guest"] == 0.5
    assert transformed.loc[0, "reference_distance_km"] == 0
    assert np.isnan(transformed.loc[0, "bathrooms_per_guest"])
    assert "price" not in transformed and "host_id" not in transformed
    assert list(FormFeatures(False).transform(data)) == FEATURES


def test_models_fit_missing_numeric_and_unseen_category_without_input_mutation():
    protocol = json.loads((ROOT / "configs/s03b_protocol.json").read_text())
    original = json.loads((ROOT / "configs/s02_protocol.json").read_text())
    protocol["catboost_parameters"]["iterations"] = 3
    protocol["hgb_log_parameters"]["max_iter"] = 3
    protocol["extra_trees_parameters"]["n_estimators"] = 3
    rows = [
        {
            **{key: (None if i % 5 == 0 else float(i % 2)) for key in NUMERIC},
            "district": "A" if i % 2 else "B",
            "room_type": "Private room",
            "property_type": "Private room in rental unit",
            "latitude": 52.5 + i / 10000,
            "longitude": 13.4,
            "accommodates": i % 4 + 1,
            "beds": i % 3 + 1,
            "bedrooms": 1,
            "wifi": i % 2,
        }
        for i in range(50)
    ]
    x = feature_frame(rows)
    before = x.copy(deep=True)
    y = np.arange(50, 100, dtype=float)
    unseen = x.iloc[:2].copy()
    unseen["district"] = "unseen"
    for name, template in make_research_models(protocol, original).items():
        model = clone(template).fit(x, y)
        result = model.predict(unseen)
        assert np.isfinite(result).all() and (result > 0).all(), name
        pd.testing.assert_frame_equal(x, before)


def test_gate_rejects_lower_mae_with_worse_practical_accuracy():
    rules = json.loads((ROOT / "configs/s03b_protocol.json").read_text())["selection"]

    def segments(mae, within):
        metrics = {
            "mae_eur": mae,
            "within_20_percent": within,
            "median_absolute_error_eur": mae / 2,
            "rmse_eur": mae * 2,
        }
        return {
            key: dict(metrics)
            for key in ["all", "over_400", "room_type:Entire home/apt", "room_type:Private room"]
        }

    control = segments(50, 0.45)
    candidate = segments(45, 0.44)
    result = gate(candidate, control, rules, "cv", [(45, 50)] * 3)
    assert not result["passed"] and not result["checks"]["within20"]
    candidate["all"]["within_20_percent"] = 0.50
    assert gate(candidate, control, rules, "cv", [(45, 50)] * 3)["passed"]
