"""Independent saved-output audit: identity, folds, metrics, selection, immutable inputs."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from staylens.data import host_split, sha256
from staylens.engineering import load_partition
from staylens.scope_audit import load_scope

ROOT = Path(__file__).resolve().parents[1]


def independent_metrics(actual, predicted):
    error = np.abs(np.asarray(actual) - np.asarray(predicted))
    return {
        "rows": len(error),
        "mae_eur": float(np.sum(error) / len(error)),
        "median_absolute_error_eur": float(np.percentile(error, 50)),
        "rmse_eur": float(np.sqrt(np.dot(error, error) / len(error))),
        "within_20_percent": float(
            np.count_nonzero(error <= np.asarray(actual) * 0.2) / len(error)
        ),
        "within_30_eur": float(np.count_nonzero(error <= 30) / len(error)),
        "p90_absolute_error_eur": float(np.percentile(error, 90)),
    }


def verify_values(actual, recorded):
    for key, value in actual.items():
        assert np.isclose(value, recorded[key], rtol=1e-12, atol=1e-10), (key, value, recorded[key])


def main():
    out, reports = ROOT / "artifacts/s03b-v1", ROOT / "reports/s03b"
    report = json.loads((reports / "comparison.json").read_text(encoding="utf-8"))
    protocol = json.loads((ROOT / "configs/s03b_protocol.json").read_text(encoding="utf-8"))
    assert sha256(ROOT / "configs/s03b_protocol.json") == report["protocol_sha256"]
    assert sha256(ROOT / "requirements-research.lock.txt") == report["research_lock_sha256"]
    assert sha256(ROOT / "data/raw/listings.csv.gz") == report["source_sha256"]
    for path, digest in report["source_code_sha256"].items():
        assert sha256(ROOT / path) == digest, path
    for path, digest in report["artifacts"].items():
        assert sha256(out / path) == digest, path
    dtype = {"listing_id": str, "host_id": str}
    predictions = pd.read_csv(out / "cv_predictions.csv", dtype=dtype)
    train = load_partition(ROOT / "data/raw/listings.csv.gz", "train")
    scope = load_scope(ROOT / "data/raw/listings.csv.gz")
    flags = train.listing_id.map(lambda key: bool(scope[key]["flags"])).to_numpy()
    assert len(predictions) == len(train) == 5814
    assert predictions.listing_id.is_unique
    assert predictions.listing_id.equals(train.listing_id)
    assert predictions.host_id.equals(train.host_id)
    assert np.array_equal(predictions.price, train.price)
    assert np.array_equal(predictions.purpose_flag, flags)
    assert predictions.host_id.map(host_split).eq("train").all()
    names = [variant["name"] for variant in protocol["variants"]]
    for fold, (fit, score) in enumerate(
        GroupKFold(**protocol["cv"]).split(train, groups=train.host_id), 1
    ):
        assert predictions.fold.iloc[score].eq(fold).all()
        assert not set(train.host_id.iloc[fit]) & set(train.host_id.iloc[score])
        for variant in protocol["variants"]:
            name = variant["name"]
            expected_fit = len(fit) - (
                int(flags[fit].sum()) if variant.get("exclude_flagged_fit") else 0
            )
            recorded = report["folds"][fold - 1]["models"][name]
            assert recorded["fit_rows"] == expected_fit
            verify_values(
                independent_metrics(predictions.price.iloc[score], predictions[name].iloc[score]),
                recorded["score"],
            )
    for name in names:
        assert np.isfinite(predictions[name]).all() and predictions[name].gt(0).all()
        verify_values(
            independent_metrics(predictions.price, predictions[name]), report["cv"][name]["all"]
        )
        if name != "s02_control":
            actual = independent_metrics(predictions.price, predictions[name])
            base = independent_metrics(predictions.price, predictions.s02_control)
            checks = report["selection"]["cv_gates"][name]["checks"]
            rules = protocol["selection"]
            assert checks["mae"] == (
                actual["mae_eur"] <= base["mae_eur"] * rules["cv_mae_max_ratio"]
            )
            assert checks["median"] == (
                actual["median_absolute_error_eur"]
                <= base["median_absolute_error_eur"] * rules["cv_median_max_ratio"]
            )
            assert checks["within20"] == (
                actual["within_20_percent"]
                >= base["within_20_percent"] + rules["cv_within20_min_absolute_gain"]
            )
    assert np.allclose(
        predictions.catboost_fixed_blend,
        0.5 * predictions.catboost_derived_mae + 0.5 * predictions.catboost_derived_log,
        rtol=0,
        atol=1e-10,
    )
    old = pd.read_csv(ROOT / "artifacts/s02-v1/cv_predictions.csv", dtype=dtype).set_index(
        "listing_id"
    )
    assert np.allclose(
        predictions.s02_control,
        old.loc[predictions.listing_id, "hist_gradient_boosting"],
        rtol=0,
        atol=1e-8,
    )
    accepted = [
        key
        for key, value in report["selection"]["cv_gates"].items()
        if all(value["checks"].values())
    ]
    expected = (
        min(accepted, key=lambda k: (float(np.abs(predictions.price - predictions[k]).mean()), k))
        if accepted
        else None
    )
    assert report["selection"]["cv_selected"] == expected
    decision = json.loads((out / "cv_decision.json").read_text(encoding="utf-8"))
    assert decision == report["selection"]
    if expected is None:
        assert not report["validation_evaluated"] and not report["promoted"]
        assert not list(out.glob("*validation*")) and not (out / "manifest.json").exists()
    else:
        vp = pd.read_csv(out / "validation_predictions.csv", dtype=dtype)
        assert vp.host_id.map(host_split).eq("validation").all()
        assert not set(vp.host_id) & set(predictions.host_id)
        for name in ["s02_control", expected]:
            verify_values(
                independent_metrics(vp.price, vp[name]), report["validation"][name]["all"]
            )
        assert report["promoted"] == all(report["validation_gate"]["checks"].values())
    # Original research history stays byte-identical.
    for rel in [
        "reports/s02/comparison.json",
        "reports/s02b/comparison.json",
        "reports/s02c/manifest.json",
    ]:
        previous = json.loads((ROOT / rel).read_text(encoding="utf-8"))
        for key in ["source_code_sha256", "code_sha256"]:
            for path, digest in previous.get(key, {}).items():
                assert sha256(ROOT / path.replace("\\", "/")) == digest, path
    assert not report["test_evaluated"]
    result = {
        "passed": True,
        "rows": len(predictions),
        "same_real_rows_and_targets": True,
        "host_isolation": True,
        "independent_all_and_fold_metrics": True,
        "original_s02_predictions_reproduced": True,
        "frozen_inputs_and_artifact_hashes": True,
        "validation_evaluated": report["validation_evaluated"],
        "promoted": report["promoted"],
        "test_evaluated": False,
    }
    (reports / "verification.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
