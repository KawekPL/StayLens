"""Train-only diagnostics of what the present form can and cannot distinguish."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from staylens.engineering import load_partition
from staylens.features import feature_frame
from staylens.scope_audit import load_scope

ROOT = Path(__file__).resolve().parents[1]


def main():
    train = load_partition(ROOT / "data/raw/listings.csv.gz", "train")
    x = feature_frame(train)
    identity = pd.util.hash_pandas_object(x, index=False)
    analysis = train[["listing_id", "host_id", "price"]].copy()
    analysis["feature_hash"] = identity
    groups = analysis.groupby("feature_hash").price.agg(["size", "min", "max", "median"])
    repeated = groups[groups["size"] > 1]
    ideal = analysis.feature_hash.map(groups["median"])
    errors = np.abs(analysis.price - ideal)
    repeated_mask = analysis.feature_hash.isin(repeated.index)
    scope = load_scope(ROOT / "data/raw/listings.csv.gz")
    flagged = train.listing_id.map(lambda key: bool(scope[key]["flags"]))
    output = {
        "scope": "train only; descriptive diagnostics, not validation or a performance claim",
        "rows": len(train),
        "unique_form_feature_vectors": len(groups),
        "repeated_feature_groups": len(repeated),
        "rows_in_repeated_feature_groups": int(repeated_mask.sum()),
        "repeated_groups_with_different_prices": int((repeated["min"] != repeated["max"]).sum()),
        "median_price_range_inside_repeated_groups_eur": float(
            (repeated["max"] - repeated["min"]).median()
        ),
        "minimum_training_mae_for_deterministic_same_18_inputs_eur": float(errors.mean()),
        "minimum_mae_within_repeated_rows_eur": float(errors[repeated_mask].mean()),
        "lower_bound_caveat": "In-sample exact-collision lower bound only. Does not estimate irreducible error on new properties, and does not prove that better models or features cannot improve.",
        "minimum_nights_counts": {
            "up_to_14": int(train.minimum_nights.le(14).sum()),
            "15_to_27": int(train.minimum_nights.between(15, 27).sum()),
            "28_or_more": int(train.minimum_nights.ge(28).sum()),
            "missing": int(train.minimum_nights.isna().sum()),
        },
        "title_purpose_flags": int(flagged.sum()),
        "flags_are_review_signals_not_proven_invalid_records": True,
        "no_rows_removed_or_labels_changed": True,
        "test_evaluated": False,
    }
    examples = analysis[repeated_mask].copy()
    examples["title"] = examples.listing_id.map(lambda key: scope[key]["title"])
    destination = ROOT / "artifacts/s03b-v1"
    examples.to_csv(destination / "same_features_different_offers.csv", index=False)
    report = ROOT / "reports/s03b/signal_audit.json"
    report.parent.mkdir(exist_ok=True, parents=True)
    report.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
