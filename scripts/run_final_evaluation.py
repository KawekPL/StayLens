"""Final authorized holdout evaluation. Frozen artifacts only; no training or model selection."""

import argparse
import csv
import gzip
import importlib.metadata
import json
import math
import subprocess
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder
from threadpoolctl import threadpool_limits

from staylens.data import SOURCE_SHA256, host_split, load_development, sha256
from staylens.evaluation import cluster_bootstrap, grouped_metrics, metrics
from staylens.features import FEATURES, feature_frame, number, source_features
from staylens.models import SegmentMedian, predict_prices

ROOT = Path(__file__).resolve().parents[1]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8"
    )


def load_final_test(path):
    if sha256(path) != SOURCE_SHA256:
        raise ValueError("Pinned source checksum mismatch")
    records = []
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if not row.get("host_id") or host_split(row["host_id"]) != "test":
                continue
            price = number(row.get("price"))
            lat, lon = number(row.get("latitude")), number(row.get("longitude"))
            if not (
                math.isfinite(price) and price > 0 and 52.3 < lat < 52.7 and 13.05 < lon < 13.8
            ):
                continue
            records.append(
                {
                    **source_features(row),
                    "listing_id": row["id"],
                    "host_id": row["host_id"],
                    "price": price,
                }
            )
    data = pd.DataFrame(records)
    if len(data) != 1235 or data.listing_id.duplicated().any():
        raise ValueError("Unexpected test size or duplicate IDs")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-final-holdout", action="store_true")
    args = parser.parse_args()
    if not args.confirm_final_holdout:
        parser.error("Explicit --confirm-final-holdout is required; never run this in CI")
    protocol_path = ROOT / "configs/s05_final_protocol.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    artifact = ROOT / "artifacts/s02-v1"
    output = ROOT / "artifacts/s05-final"
    report_path = ROOT / "reports/s05/test_evaluation.json"
    if output.exists() or report_path.exists():
        raise FileExistsError("Final evaluation already started; verify saved outputs instead")
    manifest = json.loads((artifact / "manifest.json").read_text(encoding="utf-8"))
    start = json.loads((artifact / "run_started.json").read_text(encoding="utf-8"))
    for name, expected in start["source_code_sha256"].items():
        if sha256(ROOT / name.replace("\\", "/")) != expected:
            raise ValueError(f"Frozen source changed: {name}")
    if sha256(ROOT / "configs/s02_protocol.json") != start["protocol_sha256"]:
        raise ValueError("S02 protocol changed")
    for name, expected in protocol["models"].items():
        if sha256(artifact / f"{name}.joblib") != expected:
            raise ValueError(f"Frozen model checksum mismatch: {name}")
    for name, version in manifest["packages"].items():
        if importlib.metadata.version(name) != version:
            raise ValueError(f"Package version mismatch: {name}")
    if protocol["source_sha256"] != SOURCE_SHA256 or manifest["features"] != FEATURES:
        raise ValueError("Source or feature contract changed")
    output.mkdir(parents=True, exist_ok=False)
    pre_hashes = {p.name: sha256(p) for p in artifact.iterdir() if p.is_file()}
    provenance = {
        "evaluation_id": protocol["evaluation_id"],
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_sha256": sha256(protocol_path),
        "runner_sha256": sha256(Path(__file__)),
        "git_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "source_sha256": SOURCE_SHA256,
        "model_hashes": protocol["models"],
        "packages": manifest["packages"],
    }
    write_json(output / "started.json", provenance)
    source = ROOT / "data/raw/listings.csv.gz"
    train, validation, _ = load_development(source)
    test = load_final_test(source)
    parts = {"train": train, "validation": validation, "test": test}
    if {name: len(part) for name, part in parts.items()} != protocol["expected_rows"]:
        raise ValueError("Partition counts changed")
    for a, b in [("train", "validation"), ("train", "test"), ("validation", "test")]:
        for key in ["host_id", "listing_id"]:
            if set(parts[a][key]) & set(parts[b][key]):
                raise ValueError(f"Overlap in {key}: {a}/{b}")
    x = feature_frame(test)
    models = {name: joblib.load(artifact / f"{name}.joblib") for name in protocol["models"]}
    with ExitStack() as stack:
        for cls in [
            Pipeline,
            ColumnTransformer,
            OrdinalEncoder,
            HistGradientBoostingRegressor,
            SegmentMedian,
        ]:
            stack.enter_context(
                patch.object(cls, "fit", side_effect=AssertionError("Fitting forbidden"))
            )
        predictions = {name: predict_prices(model, x) for name, model in models.items()}
    saved = test[["listing_id", "host_id", "price"]].copy()
    for name, predicted in predictions.items():
        saved[name] = predicted
    saved_path = output / "test_predictions.csv"
    saved.to_csv(saved_path, index=False)
    scores = {name: metrics(test.price, pred) for name, pred in predictions.items()}
    bootstrap = cluster_bootstrap(
        test, predictions, protocol["bootstrap"]["replicates"], protocol["bootstrap"]["seed"]
    )
    bootstrap["method"] = (
        "paired bootstrap of final-test hosts, row-weighted MAE, percentile 95% interval"
    )
    feature_matches = {}
    test_hashes = pd.util.hash_pandas_object(x, index=False)
    for name, part in [("train", train), ("validation", validation)]:
        hashes = set(pd.util.hash_pandas_object(feature_frame(part), index=False))
        feature_matches[name] = int(test_hashes.isin(hashes).sum())
    post_hashes = {p.name: sha256(p) for p in artifact.iterdir() if p.is_file()}
    if pre_hashes != post_hashes:
        raise ValueError("S02 artifacts changed during evaluation")
    report = {
        **provenance,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "test_evaluated": True,
        "model_version": "s02-v1",
        "selected_before_test": "hist_gradient_boosting",
        "fit_calls": 0,
        "s02_artifacts_unchanged": True,
        "partitions": {
            name: {"rows": len(part), "hosts": int(part.host_id.nunique())}
            for name, part in parts.items()
        },
        "pairwise_host_and_listing_overlap": 0,
        "test_metrics": scores,
        "mae_reduction_fraction": 1
        - scores["hist_gradient_boosting"]["mae_eur"] / scores["segment_median"]["mae_eur"],
        "test_segments": grouped_metrics(test, predictions, FEATURES, protocol["price_bands_eur"]),
        "bootstrap": bootstrap,
        "identical_test_feature_rows_in_development": feature_matches,
        "predictions_sha256": sha256(saved_path),
        "test_price_quantiles_eur": {
            str(q): float(test.price.quantile(q)) for q in [0, 0.5, 0.95, 0.99, 1]
        },
        "decision": protocol["decision"],
        "limits": [
            "Historical offered prices, not transaction prices",
            "New hosts in the same city/snapshot, not temporal or geographic validation",
            "No individual prediction interval",
            "Do not tune this model using these test results",
        ],
    }
    write_json(report_path, report)
    write_json(output / "artifact_integrity.json", {"before": pre_hashes, "after": post_hashes})
    print(
        json.dumps(
            {
                "metrics": scores,
                "reduction": report["mae_reduction_fraction"],
                "hosts": report["partitions"]["test"]["hosts"],
                "bootstrap": bootstrap,
                "unchanged": True,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    with threadpool_limits(limits=2):
        main()
