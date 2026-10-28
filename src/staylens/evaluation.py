"""Development-only metrics and paired host-cluster bootstrap."""

import numpy as np
import pandas as pd


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


def grouped_metrics(data, predictions, feature_names, price_bands):
    segments = data[["room_type", "district"]].copy()
    segments["price_band"] = pd.cut(data.price, price_bands, right=True).astype(str)
    segments["missing_feature_count"] = data[feature_names].isna().sum(axis=1).astype(str)
    results = {}
    for column in segments:
        results[column] = {}
        for value in sorted(segments[column].unique()):
            mask = segments[column] == value
            results[column][value] = {
                name: metrics(data.price[mask], pred[mask]) for name, pred in predictions.items()
            }
    return results


def cluster_bootstrap(data, predictions, repetitions, seed):
    errors = pd.DataFrame(
        {
            "host_id": data.host_id,
            "baseline": np.abs(data.price - predictions["segment_median"]),
            "candidate": np.abs(data.price - predictions["hist_gradient_boosting"]),
        }
    )
    grouped = errors.groupby("host_id").agg(
        baseline=("baseline", "sum"), candidate=("candidate", "sum"), count=("baseline", "size")
    )
    rng = np.random.default_rng(seed)
    difference, fraction = [], []
    for _ in range(repetitions):
        sample = grouped.iloc[rng.integers(0, len(grouped), size=len(grouped))].sum()
        difference.append((sample.baseline - sample.candidate) / sample["count"])
        fraction.append(1 - sample.candidate / sample.baseline)
    return {
        "method": "paired bootstrap of validation hosts, row-weighted MAE, percentile 95% interval",
        "hosts": len(grouped),
        "replicates": repetitions,
        "seed": seed,
        "mae_improvement_eur_95ci": np.quantile(difference, [0.025, 0.975]).tolist(),
        "mae_reduction_fraction_95ci": np.quantile(fraction, [0.025, 0.975]).tolist(),
        "not_a_prediction_interval": True,
    }


def select_model(validation_metrics, cv_metrics, rules):
    base, candidate = (
        validation_metrics[key] for key in ["segment_median", "hist_gradient_boosting"]
    )
    reduction = 1 - candidate["mae_eur"] / base["mae_eur"]
    checks = {
        "validation_mae_reduction": reduction >= rules["minimum_validation_mae_reduction_fraction"],
        "validation_rmse": candidate["rmse_eur"]
        <= rules["maximum_validation_rmse_ratio"] * base["rmse_eur"],
        "validation_median_error": candidate["median_absolute_error_eur"]
        <= base["median_absolute_error_eur"],
        "cv_mae": cv_metrics["hist_gradient_boosting"]["mae_eur"]
        < cv_metrics["segment_median"]["mae_eur"],
    }
    return {
        "selected": "hist_gradient_boosting" if all(checks.values()) else rules["fallback"],
        "checks": checks,
        "validation_mae_reduction_fraction": reduction,
    }
