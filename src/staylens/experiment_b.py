"""Factories and frozen selection rules for S02b, separate from S02 artifacts."""

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder

from staylens.engineering import ENGINEERED_CATEGORICAL, ENGINEERED_NUMERIC, EngineerFeatures
from staylens.evaluation import metrics
from staylens.models import make_models


def make_variant(base_protocol, variant):
    if variant["features"] == "original":
        return make_models(base_protocol)["hist_gradient_boosting"]
    params = {
        key: value
        for key, value in base_protocol["candidate"].items()
        if key not in {"name", "target_transform", "categorical_encoding"}
    }
    params.update(variant["overrides"])
    transform = ColumnTransformer(
        [
            (
                "categories",
                OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1, dtype=float),
                ENGINEERED_CATEGORICAL,
            ),
            ("numbers", "passthrough", ENGINEERED_NUMERIC),
        ]
    )
    return Pipeline(
        [
            ("engineer", EngineerFeatures()),
            ("encode", transform),
            (
                "regressor",
                HistGradientBoostingRegressor(
                    categorical_features=list(range(len(ENGINEERED_CATEGORICAL))), **params
                ),
            ),
        ]
    )


def predict(model, data, floor):
    values = np.asarray(model.predict(data), dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Non-finite prediction")
    return np.maximum(values, floor), int((values < floor).sum())


def summary(data, predicted):
    groups = {
        "all": np.ones(len(data), dtype=bool),
        "up_to_400": data.price.le(400),
        "over_400": data.price.gt(400),
        "over_1000": data.price.gt(1000),
    }
    result = {}
    for name, mask in groups.items():
        if not np.any(mask):
            result[name] = None
            continue
        actual, pred = data.price.to_numpy()[mask], np.asarray(predicted)[mask]
        result[name] = {
            **metrics(actual, pred),
            "mean_signed_error_eur": float(np.mean(pred - actual)),
            "underpredicted_fraction": float(np.mean(pred < actual)),
            "median_relative_absolute_error": float(np.median(np.abs(pred - actual) / actual)),
        }
    return result


def eligibility(candidate, control, rules, cv=True):
    checks = {
        "overall_mae": candidate["all"]["mae_eur"]
        <= rules["all_mae_max_ratio"] * control["all"]["mae_eur"],
        "common_mae": candidate["up_to_400"]["mae_eur"]
        <= rules["common_mae_max_ratio"] * control["up_to_400"]["mae_eur"],
        "tail_mae": candidate["over_400"]["mae_eur"]
        <= rules["tail_mae_max_ratio"] * control["over_400"]["mae_eur"],
        "rmse": candidate["all"]["rmse_eur"]
        <= rules["rmse_max_ratio"] * control["all"]["rmse_eur"],
        "median_error": candidate["all"]["median_absolute_error_eur"]
        <= rules["median_error_max_ratio"] * control["all"]["median_absolute_error_eur"],
    }
    if cv:
        all_gain = 1 - candidate["all"]["mae_eur"] / control["all"]["mae_eur"]
        tail_gain = 1 - candidate["over_400"]["mae_eur"] / control["over_400"]["mae_eur"]
        checks["meaningful_improvement"] = (
            all_gain >= rules["minimum_all_mae_improvement"]
            or tail_gain >= rules["or_minimum_tail_mae_improvement"]
        )
    return checks


def choose_cv(results, rules):
    checks = {
        name: eligibility(value, results["s02_control"], rules)
        for name, value in results.items()
        if name != "s02_control"
    }
    eligible = [name for name, passed in checks.items() if all(passed.values())]
    winner = (
        min(eligible, key=lambda name: (results[name]["all"]["mae_eur"], name))
        if eligible
        else "s02_control"
    )
    return {
        "winner": winner,
        "checks": checks,
        "eligible": eligible,
        "basis": "CV on real train rows only; locked before validation load",
    }
