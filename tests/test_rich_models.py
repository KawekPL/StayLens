import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone

from staylens.features import feature_frame
from staylens.rich_models import INPUTS, NEW_INPUTS, RichFeatures, make_rich_models

ROOT = Path(__file__).resolve().parents[1]


def test_rich_features_do_not_require_new_fields_and_never_accept_hidden_inputs():
    data = feature_frame(
        [{"latitude": 52.52, "longitude": 13.405, "accommodates": 2, "bedrooms": 1}]
    )
    data["external_guest_favourite"] = 1
    data["neighbourhood"] = "untrusted"
    data["price"] = 999
    transformed = RichFeatures().fit_transform(data)
    assert transformed.shape == (1, 40)
    assert transformed[NEW_INPUTS].isna().all().all()
    assert "price" not in transformed and "external_guest_favourite" not in transformed
    assert "neighbourhood" not in transformed
    assert transformed.coordinate_grid.iloc[0] == "2626:670"


def test_rich_candidates_score_when_all_new_fields_are_unknown():
    protocol = json.loads((ROOT / "configs/s03c_protocol.json").read_text())
    protocol["catboost_parameters"]["iterations"] = 3
    data = feature_frame(
        [
            {
                "district": "Mitte",
                "room_type": "Private room",
                "property_type": "Private room in rental unit",
                "latitude": 52.5 + i * 0.0001,
                "longitude": 13.4,
                "accommodates": 1 + i % 3,
                "beds": 1,
            }
            for i in range(30)
        ]
    ).reindex(columns=INPUTS)
    for key in NEW_INPUTS:
        data[key] = np.arange(30) % 2
    original = data.copy(deep=True)
    empty = data.iloc[:3].copy()
    empty[NEW_INPUTS] = np.nan
    for template in make_rich_models(protocol).values():
        fitted = clone(template).fit(data, np.arange(30) + 80)
        prices = fitted.predict(empty)
        assert np.isfinite(prices).all() and (prices > 0).all()
        pd.testing.assert_frame_equal(data, original)
