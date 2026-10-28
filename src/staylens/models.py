"""Fixed S02 estimators. All learned transforms belong inside each training fold."""

import numpy as np
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder
from sklearn.utils.validation import check_is_fitted

from staylens.features import CATEGORICAL, NUMERIC


class SegmentMedian(RegressorMixin, BaseEstimator):
    def __init__(self, min_segment_size=10, hierarchy=None, capacity_buckets=(2, 4, 6, 16)):
        self.min_segment_size = min_segment_size
        self.hierarchy = hierarchy
        self.capacity_buckets = capacity_buckets

    def _segments(self, x):
        data = x.copy()
        data["capacity_bucket"] = np.searchsorted(
            self.capacity_buckets, data["accommodates"], side="left"
        )
        return data

    def fit(self, X, y):
        data = self._segments(X)
        data["target"] = np.asarray(y)
        self.global_median_ = float(np.median(y))
        self.hierarchy_ = self.hierarchy or [
            ["district", "room_type", "capacity_bucket"],
            ["district", "room_type"],
            ["room_type", "capacity_bucket"],
            ["room_type"],
        ]
        self.tables_ = []
        for columns in self.hierarchy_:
            table = data.groupby(columns, dropna=False)["target"].agg(["median", "size"])
            lookup = {}
            for key, row in table.iterrows():
                if row["size"] >= self.min_segment_size:
                    lookup[key if isinstance(key, tuple) else (key,)] = float(row["median"])
            self.tables_.append(lookup)
        return self

    def predict(self, X):
        check_is_fitted(self, "tables_")
        data = self._segments(X)
        predictions = np.full(len(data), self.global_median_)
        pending = np.ones(len(data), dtype=bool)
        for columns, lookup in zip(self.hierarchy_, self.tables_, strict=True):
            for index, key in enumerate(data[columns].itertuples(index=False, name=None)):
                if pending[index] and key in lookup:
                    predictions[index] = lookup[key]
                    pending[index] = False
        return predictions


def make_models(protocol):
    baseline = protocol["baseline"]
    parameters = {
        key: value
        for key, value in protocol["candidate"].items()
        if key not in {"name", "target_transform", "categorical_encoding"}
    }
    encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1, dtype=float)
    transform = ColumnTransformer(
        [("categories", encoder, CATEGORICAL), ("numbers", "passthrough", NUMERIC)]
    )
    return {
        "segment_median": SegmentMedian(
            baseline["min_segment_size"], baseline["hierarchy"], baseline["capacity_buckets"]
        ),
        "hist_gradient_boosting": Pipeline(
            [
                ("features", transform),
                (
                    "regressor",
                    HistGradientBoostingRegressor(
                        categorical_features=list(range(len(CATEGORICAL))), **parameters
                    ),
                ),
            ]
        ),
    }


def predict_prices(model, x):
    values = np.asarray(model.predict(x), dtype=float)
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("Model returned a non-finite or non-positive price")
    return values
