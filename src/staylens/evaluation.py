"""Błędy prognoz oraz porównanie boostingu z prostą medianą."""

import numpy as np


def metrics(actual, predicted):
    actual, predicted = np.asarray(actual), np.asarray(predicted)
    error = np.abs(actual - predicted)
    return {
        "rows": len(actual),
        "mae_eur": float(error.mean()),
        "median_absolute_error_eur": float(np.median(error)),
        "rmse_eur": float(np.sqrt(np.mean(error**2))),
        "within_20_percent": float(np.mean(error / actual <= 0.2)),
        "within_30_eur": float(np.mean(error <= 30)),
        "p90_absolute_error_eur": float(np.quantile(error, 0.9)),
    }


def select_model(validation_metrics, cv_metrics):
    base, candidate = (
        validation_metrics[key] for key in ["segment_median", "hist_gradient_boosting"]
    )
    reduction = 1 - candidate["mae_eur"] / base["mae_eur"]
    checks = {
        "validation_mae_reduction": reduction >= 0.10,
        "validation_rmse": candidate["rmse_eur"] <= 1.10 * base["rmse_eur"],
        "validation_median_error": candidate["median_absolute_error_eur"]
        <= base["median_absolute_error_eur"],
        "cv_mae": cv_metrics["hist_gradient_boosting"]["mae_eur"]
        < cv_metrics["segment_median"]["mae_eur"],
    }
    return {
        "selected": "hist_gradient_boosting" if all(checks.values()) else "segment_median",
        "checks": checks,
        "validation_mae_reduction_fraction": reduction,
    }
