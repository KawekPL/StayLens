"""Mała próba techniczna na sztucznych rekordach; nie zmienia modelu aplikacji."""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import GroupKFold
from threadpoolctl import threadpool_limits

from scripts import train as training
from staylens.features import AMENITIES, feature_frame
from staylens.models import make_models


def test_training_saves_consistent_results_without_host_leakage(tmp_path, monkeypatch):
    rows = []
    for i in range(84):
        rows.append(
            {
                "listing_id": str(i),
                "host_id": str(i // 4),
                "price": 100 + i % 30,
                "district": "Mitte",
                "room_type": "Entire home/apt",
                "property_type": "Entire rental unit",
                "latitude": 52.52,
                "longitude": 13.405,
                "accommodates": 2,
                "bedrooms": 1,
                "beds": 1,
                "bathrooms": 1,
                "minimum_nights": 2,
                **dict.fromkeys(AMENITIES, 0),
            }
        )
    data = pd.DataFrame(rows)
    train = data.iloc[:72].reset_index(drop=True)
    validation = data.iloc[72:].reset_index(drop=True)
    checked_folds = []

    class CheckedGroupKFold(GroupKFold):
        def split(self, X, y=None, groups=None):
            for fit, score in super().split(X, y, groups):
                assert not set(groups.iloc[fit]) & set(groups.iloc[score])
                checked_folds.append(score)
                yield fit, score

    monkeypatch.setattr(training, "GroupKFold", CheckedGroupKFold)
    output = tmp_path / "training"
    with threadpool_limits(limits=2):
        report = training.train_models(train, validation, output)
        predictions = pd.read_csv(output / "validation_predictions.csv")
        for name in ["segment_median", "hist_gradient_boosting"]:
            model = joblib.load(output / f"{name}.joblib")
            actual = model.predict(feature_frame(validation))
            np.testing.assert_allclose(actual, predictions[name], rtol=1e-12)
            assert report["validation"][name]["mae_eur"] == mean_absolute_error(
                validation.price, actual
            )
    assert len(checked_folds) == 6
    assert sorted(np.concatenate(checked_folds[:3]).tolist()) == list(range(len(train)))
    assert sorted(np.concatenate(checked_folds[3:]).tolist()) == list(range(len(train)))
    assert report["test_evaluated"] is False
    assert json.loads((output / "comparison.json").read_text()) == report


def test_explicit_model_parameters_match_the_deployed_model():
    root = Path(__file__).resolve().parents[1]
    saved = joblib.load(root / "runtime/model/hist_gradient_boosting.joblib")
    fresh = make_models()["hist_gradient_boosting"]
    assert fresh["regressor"].get_params() == saved["regressor"].get_params()
    fresh_encoder = fresh["features"].transformers[0][1].get_params()
    saved_encoder = saved["features"].transformers[0][1].get_params()
    # NaN oznacza ten sam brak danych, ale NaN == NaN zwraca False.
    assert np.isnan(fresh_encoder.pop("encoded_missing_value"))
    assert np.isnan(saved_encoder.pop("encoded_missing_value"))
    assert fresh_encoder == saved_encoder
