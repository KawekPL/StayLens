"""S03b estimators with the same public input contract as S02. No hidden inputs."""

import numpy as np
from catboost import CatBoostRegressor
from sklearn.base import BaseEstimator, RegressorMixin, TransformerMixin, clone
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder
from sklearn.utils.validation import check_is_fitted

from staylens.features import CATEGORICAL, NUMERIC, feature_frame
from staylens.models import make_models

DERIVED = [
    "guests_per_bedroom",
    "beds_per_guest",
    "bathrooms_per_guest",
    "reference_distance_km",
    "missing_basic_count",
]


class FormFeatures(TransformerMixin, BaseEstimator):
    def __init__(self, derived=False):
        self.derived = derived

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        result = feature_frame(X)
        if self.derived:
            guests = result.accommodates.where(result.accommodates > 0)
            bedrooms = result.bedrooms.where(result.bedrooms != 0, 1)
            result["guests_per_bedroom"] = guests / bedrooms
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
        return result


class PositiveRegressor(RegressorMixin, BaseEstimator):
    def __init__(self, estimator, floor=0.01):
        self.estimator = estimator
        self.floor = floor

    def fit(self, X, y):
        self.estimator_ = clone(self.estimator).fit(X, y)
        return self

    def predict(self, X):
        check_is_fitted(self, "estimator_")
        values = np.asarray(self.estimator_.predict(X), dtype=float)
        if not np.isfinite(values).all():
            raise ValueError("Non-finite predictions")
        return np.maximum(self.floor, values)


class NativeCatBoost(RegressorMixin, BaseEstimator):
    """Construct CatBoost inside fit: its list-valued params fail sklearn 1.9 clone."""

    def __init__(self, parameters):
        self.parameters = parameters

    def fit(self, X, y):
        self.model_ = CatBoostRegressor(cat_features=CATEGORICAL, **self.parameters)
        self.model_.fit(X, y)
        return self

    def predict(self, X):
        check_is_fitted(self, "model_")
        return self.model_.predict(X)


class FixedBlend(RegressorMixin, BaseEstimator):
    def __init__(self, estimators, weights):
        self.estimators = estimators
        self.weights = weights

    def fit(self, X, y):
        self.estimators_ = [clone(model).fit(X, y) for model in self.estimators]
        return self

    def predict(self, X):
        check_is_fitted(self, "estimators_")
        return np.average(
            [model.predict(X) for model in self.estimators_], axis=0, weights=self.weights
        )


def make_research_models(protocol, original):
    models = {}
    for variant in protocol["variants"]:
        name, family = variant["name"], variant["family"]
        if family == "s02":
            models[name] = make_models(original)["hist_gradient_boosting"]
            continue
        if family == "blend":
            models[name] = FixedBlend(
                [models[key] for key in variant["members"]], variant["weights"]
            )
            continue
        numeric = NUMERIC + (DERIVED if variant["derived"] else [])
        steps = [("contract", FormFeatures(variant["derived"]))]
        if family == "catboost":
            regressor = NativeCatBoost(
                {**protocol["catboost_parameters"], "loss_function": variant["loss"]}
            )
        elif family == "hgb":
            steps.append(
                (
                    "encoding",
                    ColumnTransformer(
                        [
                            (
                                "categories",
                                OrdinalEncoder(
                                    handle_unknown="use_encoded_value", unknown_value=-1
                                ),
                                CATEGORICAL,
                            ),
                            ("numbers", "passthrough", numeric),
                        ]
                    ),
                )
            )
            regressor = HistGradientBoostingRegressor(
                categorical_features=list(range(len(CATEGORICAL))), **protocol["hgb_log_parameters"]
            )
        elif family == "extra_trees":
            steps.append(
                (
                    "encoding",
                    ColumnTransformer(
                        [
                            (
                                "categories",
                                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                                CATEGORICAL,
                            ),
                            (
                                "numbers",
                                SimpleImputer(
                                    strategy="median", add_indicator=True, keep_empty_features=True
                                ),
                                numeric,
                            ),
                        ]
                    ),
                )
            )
            regressor = ExtraTreesRegressor(**protocol["extra_trees_parameters"])
        else:
            raise ValueError(f"Unknown family: {family}")
        steps.append(("regressor", regressor))
        estimator = Pipeline(steps)
        if variant["target"] == "log1p":
            estimator = TransformedTargetRegressor(
                regressor=estimator, func=np.log1p, inverse_func=np.expm1
            )
        models[name] = PositiveRegressor(estimator, protocol["prediction_floor_eur"])
    return models


def summary_segments(data, prediction, flags):
    from staylens.evaluation import metrics

    price = data.price.to_numpy()
    masks = {
        "all": np.ones(len(data), dtype=bool),
        "up_to_100": price <= 100,
        "100_to_200": (price > 100) & (price <= 200),
        "200_to_400": (price > 200) & (price <= 400),
        "over_400": price > 400,
        "purpose_flag": np.asarray(flags, dtype=bool),
        "no_purpose_flag": ~np.asarray(flags, dtype=bool),
        "minimum_up_to_14": data.minimum_nights.le(14).to_numpy(),
        "minimum_28_or_more": data.minimum_nights.ge(28).to_numpy(),
    }
    for key in ["room_type", "district"]:
        for value in sorted(data[key].unique()):
            masks[f"{key}:{value}"] = data[key].eq(value).to_numpy()
    return {
        key: metrics(price[mask], np.asarray(prediction)[mask])
        for key, mask in masks.items()
        if mask.any()
    }


def gate(candidate, control, rules, stage, folds=None):
    c, b = candidate["all"], control["all"]
    checks = {
        "mae": c["mae_eur"] <= rules[f"{stage}_mae_max_ratio"] * b["mae_eur"],
        "within20": c["within_20_percent"]
        >= b["within_20_percent"] + rules[f"{stage}_within20_min_absolute_gain"],
        "median": c["median_absolute_error_eur"]
        <= rules[f"{stage}_median_max_ratio"] * b["median_absolute_error_eur"],
        "tail": candidate["over_400"]["mae_eur"]
        <= rules[f"{stage}_tail_mae_max_ratio"] * control["over_400"]["mae_eur"],
        "rmse": c["rmse_eur"] <= rules[f"{stage}_rmse_max_ratio"] * b["rmse_eur"],
    }
    for room in ["Entire home/apt", "Private room"]:
        key = f"room_type:{room}"
        checks[key] = (
            candidate[key]["mae_eur"]
            <= rules["common_room_mae_max_ratio"] * control[key]["mae_eur"]
        )
    if folds is not None:
        checks["fold_wins"] = sum(c < b for c, b in folds) >= rules["minimum_fold_mae_wins"]
        checks["fold_worst"] = all(
            c <= b * rules["maximum_single_fold_mae_ratio"] for c, b in folds
        )
    return {
        "passed": all(checks.values()),
        "checks": {key: bool(value) for key, value in checks.items()},
    }
