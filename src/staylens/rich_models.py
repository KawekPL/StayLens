"""S03c: richer public attributes, no external commercial data or hidden text inputs."""

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin, TransformerMixin
from sklearn.compose import TransformedTargetRegressor
from sklearn.pipeline import Pipeline
from sklearn.utils.validation import check_is_fitted

from staylens.engineering import EXTRA_AMENITIES, load_partition
from staylens.enrichment import AREA_FEATURES, area_from_text
from staylens.features import CATEGORICAL, FEATURES
from staylens.research_models import FormFeatures, PositiveRegressor
from staylens.scope_audit import load_scope

NEW_INPUTS = EXTRA_AMENITIES + ["bathroom_shared"] + AREA_FEATURES
INPUTS = FEATURES + NEW_INPUTS
RICH_CATEGORIES = CATEGORICAL + ["coordinate_grid"]


class RichFeatures(TransformerMixin, BaseEstimator):
    def fit(self, X, y=None):
        return self

    def transform(self, X):
        frame = pd.DataFrame(X).reindex(columns=INPUTS).copy()
        result = FormFeatures(True).transform(frame)
        for name in NEW_INPUTS:
            result[name] = pd.to_numeric(frame[name], errors="coerce").astype(float)
        lat = np.floor(result.latitude * 50).astype("Int64").astype("string")
        lon = np.floor(result.longitude * 50).astype("Int64").astype("string")
        result["coordinate_grid"] = (lat + ":" + lon).fillna("unknown").astype(str)
        return result


class RichCatBoost(RegressorMixin, BaseEstimator):
    def __init__(self, parameters):
        self.parameters = parameters

    def fit(self, X, y):
        from catboost import CatBoostRegressor

        self.model_ = CatBoostRegressor(cat_features=RICH_CATEGORIES, **self.parameters)
        self.model_.fit(X, y)
        return self

    def predict(self, X):
        check_is_fitted(self, "model_")
        return self.model_.predict(X)


def make_rich_models(protocol):
    result = {}
    for variant in protocol["variants"]:
        estimator = Pipeline(
            [
                ("features", RichFeatures()),
                (
                    "model",
                    RichCatBoost(
                        {**protocol["catboost_parameters"], "loss_function": variant["loss"]}
                    ),
                ),
            ]
        )
        if variant["target"] == "log1p":
            estimator = TransformedTargetRegressor(
                regressor=estimator, func=np.log1p, inverse_func=np.expm1
            )
        result[variant["name"]] = PositiveRegressor(estimator)
    return result


def load_rich(path, subset):
    data = load_partition(path, subset)
    scope = load_scope(path, subset)
    areas = []
    for row in data.itertuples():
        text = scope[row.listing_id]
        area, _ = area_from_text(text["title"], text["description"], row.room_type)
        areas.append(area)
    for key in AREA_FEATURES:
        data[key] = [area[key] for area in areas]
    flags = data.listing_id.map(lambda key: bool(scope[key]["flags"])).to_numpy()
    return data, flags
