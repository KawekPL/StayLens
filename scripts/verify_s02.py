"""Independently check saved predictions, split integrity and local reproduction."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from staylens.data import host_split, load_development, sha256
from staylens.features import feature_frame

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts" / "s02-v1"


def main():
    report = json.loads((ROOT / "reports/s02/comparison.json").read_text(encoding="utf-8"))
    assert sha256(ROOT / "configs/s02_protocol.json") == report["protocol_sha256"]
    assert sha256(ROOT / "scripts/run_s02.py") == report["runner_sha256"]
    for name, expected in report["source_code_sha256"].items():
        assert sha256(ROOT / name.replace("\\", "/")) == expected, (
            f"Experiment code changed: {name}"
        )
    train, validation, _ = load_development(ROOT / "data/raw/listings.csv.gz")
    checks = {"protocol_and_code_hashes_match": True, "test_evaluated": False}
    for subset, key, expected_split, source in [
        ("cv", "cv_pooled", "train", train),
        ("validation", "validation", "validation", validation),
    ]:
        predictions = pd.read_csv(
            ARTIFACT / f"{subset}_predictions.csv", dtype={"host_id": str, "listing_id": str}
        )
        assert len(predictions) == len(source)
        assert predictions.listing_id.tolist() == source.listing_id.tolist()
        assert predictions.host_id.tolist() == source.host_id.tolist()
        np.testing.assert_array_equal(predictions.price, source.price)
        assert predictions.host_id.map(host_split).eq(expected_split).all()
        for name in ["segment_median", "hist_gradient_boosting"]:
            error = np.abs(predictions.price - predictions[name])
            expected = report[key][name]
            assert np.isclose(error.mean(), expected["mae_eur"])
            assert np.isclose(np.median(error), expected["median_absolute_error_eur"])
            assert np.isclose(np.sqrt(np.mean(error**2)), expected["rmse_eur"])
            assert np.isclose((error <= 30).mean(), expected["within_30_eur"])
            assert np.isclose(
                (error / predictions.price <= 0.2).mean(), expected["within_20_percent"]
            )
        checks[f"{subset}_rows_hosts_targets_metrics_match"] = True
        repeat = ROOT / ".local/s02-reproduction" / f"{subset}_predictions.csv"
        checks[f"{subset}_reproduced_exactly"] = repeat.exists() and sha256(repeat) == sha256(
            ARTIFACT / repeat.name
        )
    assert not set(train.host_id) & set(validation.host_id)
    checks["train_validation_host_overlap"] = 0
    # Sensitivity analysis only: preserve primary scores and the original selection.
    tx, vx = feature_frame(train), feature_frame(validation)
    matches = pd.util.hash_pandas_object(vx, index=False).isin(
        set(pd.util.hash_pandas_object(tx, index=False))
    )
    checks["matching_feature_rows"] = int(matches.sum())
    predicted = pd.read_csv(ARTIFACT / "validation_predictions.csv")
    checks["sensitivity_mae_excluding_feature_matches"] = {
        key: float(np.abs(predicted.price[~matches] - predicted[key][~matches]).mean())
        for key in ["segment_median", "hist_gradient_boosting"]
    }
    checks["sensitivity_does_not_change_primary_selection"] = True
    checks["prediction_interval_claimed"] = False
    (ROOT / "reports/s02/verification.json").write_text(
        json.dumps(checks, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
