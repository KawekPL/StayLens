"""Verify real-only scoring, parent provenance, fold isolation and S02 preservation."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from staylens.data import SOURCE_SHA256, host_split, sha256
from staylens.engineering import MASKABLE, RAW_FEATURES, load_partition
from staylens.experiment_b import choose_cv, summary

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/s02b-v1"
PREPARED = ROOT / "data/prepared/s02b-v1"
ID_TYPES = {"listing_id": str, "host_id": str, "parent_listing_id": str}


def read(path):
    return pd.read_csv(path, dtype=ID_TYPES, keep_default_na=True)


def main():
    report = json.loads((ROOT / "reports/s02b/comparison.json").read_text(encoding="utf-8"))
    protocol = json.loads((ROOT / "configs/s02b_protocol.json").read_text(encoding="utf-8"))
    assert sha256(ROOT / "data/raw/listings.csv.gz") == SOURCE_SHA256
    assert sha256(ROOT / "configs/s02b_protocol.json") == report["protocol_sha256"]
    assert sha256(ROOT / "configs/s02_protocol.json") == report["base_protocol_sha256"]
    assert sha256(ROOT / "scripts/run_s02b.py") == report["runner_sha256"]
    for name, expected in report["source_code_sha256"].items():
        assert sha256(ROOT / name) == expected
    for part, expected in report["parent_prediction_sha256"].items():
        assert sha256(ROOT / f"artifacts/s02-v1/{part}_predictions.csv") == expected
    train = load_partition(ROOT / "data/raw/listings.csv.gz", "train")
    parents = train.set_index("listing_id")
    generated_checks = {}
    for mode in ["repeat", "masked"]:
        data = read(PREPARED / f"train_{mode}.csv")
        real, added = data[~data.is_augmented], data[data.is_augmented]
        assert real.listing_id.tolist() == train.listing_id.tolist()
        pd.testing.assert_frame_equal(real[RAW_FEATURES], train[RAW_FEATURES], check_dtype=False)
        assert len(added) == int(train.price.gt(400).sum()) == 263
        assert added.parent_listing_id.is_unique
        assert set(added.parent_listing_id) == set(train.loc[train.price.gt(400), "listing_id"])
        for _, row in added.iterrows():
            parent = parents.loc[row.parent_listing_id]
            assert row.host_id == parent.host_id and row.price == parent.price
            assert row["split"] == "train" and row.augmentation_kind == mode
            masked = (
                set(str(row.masked_features).split(",")) if pd.notna(row.masked_features) else set()
            )
            assert masked <= set(MASKABLE)
            if mode == "masked":
                assert len(masked) >= 6
            else:
                assert not masked
            for key in RAW_FEATURES:
                if key in masked:
                    assert pd.isna(row[key])
                elif pd.isna(parent[key]):
                    assert pd.isna(row[key])
                else:
                    assert row[key] == parent[key]
        generated_checks[mode] = {
            "real_rows": len(real),
            "added_rows": len(added),
            "new_hosts": 0,
            "price_or_coordinate_changes": 0,
            "parent_provenance_verified": True,
        }
    cv = read(ARTIFACT / "cv_predictions.csv")
    assert cv.listing_id.tolist() == train.listing_id.tolist()
    assert cv.host_id.tolist() == train.host_id.tolist()
    np.testing.assert_array_equal(cv.price, train.price)
    assert cv.host_id.map(host_split).eq("train").all()
    independent = {}
    for variant in protocol["variants"]:
        name = variant["name"]
        error = np.abs(cv.price - cv[name])
        expected = report["cv"][name]
        assert np.isclose(error.mean(), expected["all"]["mae_eur"])
        assert np.isclose(np.sqrt(np.mean(error**2)), expected["all"]["rmse_eur"])
        for group, mask in [("up_to_400", cv.price.le(400)), ("over_400", cv.price.gt(400))]:
            assert np.isclose(error[mask].mean(), expected[group]["mae_eur"])
        independent[name] = summary(train, cv[name].to_numpy())
    assert (
        choose_cv(independent, protocol["cv_selection"])["winner"]
        == report["cv_selection"]["winner"]
    )
    for fold, (fit_index, score_index) in enumerate(
        GroupKFold(**protocol["cv"]).split(train, train.price, train.host_id), 1
    ):
        assert cv.iloc[score_index]["fold"].eq(fold).all()
        heldout = set(train.host_id.iloc[score_index])
        fit_parents = set(train.listing_id.iloc[fit_index])
        for name in ["engineered_repeat", "engineered_masked"]:
            generated = read(ARTIFACT / f"fold{fold}_{name}_provenance.csv")
            assert not set(generated.host_id) & heldout
            assert set(generated.parent_listing_id) <= fit_parents
            assert generated.is_augmented.all()
            for _, row in generated.iterrows():
                assert row.price == parents.loc[row.parent_listing_id, "price"]
                assert row.host_id == parents.loc[row.parent_listing_id, "host_id"]
    val = read(ARTIFACT / "validation_predictions.csv")
    original = read(ROOT / "artifacts/s02-v1/validation_predictions.csv")
    assert val.listing_id.tolist() == original.listing_id.tolist()
    assert val.host_id.map(host_split).eq("validation").all()
    assert not set(val.host_id) & set(cv.host_id)
    assert len(val) == 1108 and not val.listing_id.str.startswith("aug:").any()
    np.testing.assert_allclose(val.s02_control, original.hist_gradient_boosting, rtol=0, atol=1e-10)
    selection = json.loads((ARTIFACT / "cv_selection.json").read_text(encoding="utf-8"))
    assert selection == report["cv_selection"]
    assert set(val.columns) == {
        "listing_id",
        "host_id",
        "price",
        "s02_control",
        selection["winner"],
    }
    manifest = json.loads((ARTIFACT / "manifest.json").read_text(encoding="utf-8"))
    assert sha256(ARTIFACT / manifest["model_file"]) == manifest["model_sha256"]
    checks = {
        "source_protocol_and_code_hashes_match": True,
        "s02_prediction_files_unchanged": True,
        "augmentation": generated_checks,
        "fold_parent_isolation_verified": True,
        "real_cv_rows": len(cv),
        "real_validation_rows": len(val),
        "augmented_scoring_rows": 0,
        "test_evaluated": False,
        "cv_metrics_recomputed": True,
        "selection_recomputed": True,
        "selected_variant": selection["winner"],
        "candidate_validation_not_run": selection["winner"] == "s02_control",
        "manifest_model_hash_matches": True,
    }
    (ROOT / "reports/s02b/verification.json").write_text(
        json.dumps(checks, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
