"""Verify rich-input experiment without fitting or accessing final test data."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from staylens.data import host_split, sha256
from staylens.rich_models import INPUTS, NEW_INPUTS, RichFeatures

ROOT = Path(__file__).resolve().parents[1]


def mae(actual, predicted):
    return float(np.abs(np.asarray(actual) - np.asarray(predicted)).mean())


def main():
    out, reports = ROOT / "artifacts/s03c-v1", ROOT / "reports/s03c"
    result = json.loads((reports / "comparison.json").read_text(encoding="utf-8"))
    protocol = json.loads((ROOT / "configs/s03c_protocol.json").read_text(encoding="utf-8"))
    for key, rel in [
        ("protocol_sha256", "configs/s03c_protocol.json"),
        ("gates_protocol_sha256", "configs/s03b_protocol.json"),
        ("research_lock_sha256", "requirements-research.lock.txt"),
    ]:
        assert sha256(ROOT / rel) == result[key]
    for rel, digest in result["code_sha256"].items():
        assert sha256(ROOT / rel) == digest, rel
    for rel, digest in result["outputs_sha256"].items():
        assert sha256(out / rel) == digest, rel
    dtype = {"listing_id": str, "host_id": str}
    predictions = pd.read_csv(out / "cv_predictions.csv", dtype=dtype)
    features = pd.read_csv(out / "train_features.csv", dtype=dtype)
    assert len(predictions) == len(features) == 5814
    assert predictions.listing_id.is_unique and predictions.listing_id.equals(features.listing_id)
    assert predictions.host_id.equals(features.host_id)
    assert predictions.host_id.map(host_split).eq("train").all()
    original = pd.read_csv(ROOT / "artifacts/s02-v1/cv_predictions.csv", dtype=dtype).set_index(
        "listing_id"
    )
    assert np.array_equal(predictions.price, original.loc[predictions.listing_id, "price"])
    assert np.allclose(
        predictions.s02_control,
        original.loc[predictions.listing_id, "hist_gradient_boosting"],
        rtol=0,
        atol=1e-10,
    )
    assert RichFeatures().transform(features[INPUTS]).shape[1] == 40
    for key, count in result["observed_new_inputs"].items():
        assert features[key].notna().sum() == count
    assert not any("external_" in key for key in features)
    for fold, (fit, score) in enumerate(
        GroupKFold(**protocol["cv"]).split(features, groups=features.host_id), 1
    ):
        assert predictions.fold.iloc[score].eq(fold).all()
        assert not set(features.host_id.iloc[fit]) & set(features.host_id.iloc[score])
        for variant in protocol["variants"]:
            name = variant["name"]
            assert np.isclose(
                mae(predictions.price.iloc[score], predictions[name].iloc[score]),
                result["folds"][fold - 1]["models"][name]["mae"],
            )
    for variant in protocol["variants"]:
        name = variant["name"]
        for suffix, recorded in [
            ("", result["cv"][name]["all"]),
            ("_missing_new", result["missing_new_fields"][name]["all"]),
        ]:
            values = predictions[name + suffix]
            assert np.isfinite(values).all() and values.gt(0).all()
            assert np.isclose(mae(predictions.price, values), recorded["mae_eur"], atol=1e-10)
            within = float((np.abs(predictions.price - values) <= 0.2 * predictions.price).mean())
            assert np.isclose(within, recorded["within_20_percent"])
    decision = result["decision"]
    rules = json.loads((ROOT / "configs/s03b_protocol.json").read_text())["selection"]
    base_error = np.abs(predictions.price - predictions.s02_control)
    for variant in protocol["variants"]:
        name = variant["name"]
        error = np.abs(predictions.price - predictions[name])
        checks = decision["gates"][name]["checks"]
        assert checks["mae"] == (error.mean() <= base_error.mean() * rules["cv_mae_max_ratio"])
        assert checks["median"] == (
            error.median() <= base_error.median() * rules["cv_median_max_ratio"]
        )
        assert checks["within20"] == (
            (error <= predictions.price * 0.2).mean()
            >= (base_error <= predictions.price * 0.2).mean()
            + rules["cv_within20_min_absolute_gain"]
        )
    accepted = [
        variant["name"]
        for variant in protocol["variants"]
        if all(decision["gates"][variant["name"]]["checks"].values())
        and all(decision["empty_fields_gates"][variant["name"]]["checks"].values())
    ]
    expected = (
        min(accepted, key=lambda key: (mae(predictions.price, predictions[key]), key))
        if accepted
        else None
    )
    assert expected == decision["selected"]
    if expected is None:
        assert not result["validation_evaluated"] and not result["promoted"]
        assert not list(out.glob("*validation*"))
    else:
        vp = pd.read_csv(out / "validation_predictions.csv", dtype=dtype)
        assert vp.host_id.map(host_split).eq("validation").all()
        assert not set(vp.host_id) & set(predictions.host_id)
        assert np.isclose(
            mae(vp.price, vp[expected]), result["validation"][expected]["all"]["mae_eur"]
        )
    assert not result["test_evaluated"]
    verified = {
        "passed": True,
        "rows": 5814,
        "new_inputs": len(NEW_INPUTS),
        "feature_count": 40,
        "same_targets_and_host_folds": True,
        "original_control": True,
        "full_and_empty_new_field_metrics_checked": True,
        "frozen_code_and_outputs": True,
        "validation_evaluated": result["validation_evaluated"],
        "test_evaluated": False,
        "promoted": result["promoted"],
    }
    (reports / "verification.json").write_text(
        json.dumps(verified, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(verified, indent=2))


if __name__ == "__main__":
    main()
