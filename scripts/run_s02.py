"""Run the frozen S02 comparison once per output directory; never evaluate test."""

import argparse
import importlib.metadata
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import joblib
import matplotlib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.model_selection import GroupKFold
from threadpoolctl import threadpool_limits

from staylens.data import SOURCE_SHA256, load_development, sha256, training_audit
from staylens.evaluation import cluster_bootstrap, grouped_metrics, metrics, select_model
from staylens.features import CATEGORICAL, FEATURES, NUMERIC, feature_frame
from staylens.models import make_models, predict_prices

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


def comparison_plot(results, destination):
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.2))
    fig.patch.set_facecolor("#f7faf9")
    for ax, metric, title in zip(
        axes,
        ["mae_eur", "median_absolute_error_eur", "rmse_eur"],
        ["Średni błąd (MAE)", "Mediana błędu", "RMSE — wrażliwe na skrajności"],
        strict=True,
    ):
        values = [results[name][metric] for name in ["segment_median", "hist_gradient_boosting"]]
        bars = ax.bar(
            ["Mediana segmentu", "Boosting"], values, color=["#a4b4af", "#167466"], width=0.58
        )
        ax.bar_label(bars, labels=[f"{v:.2f} €" for v in values], padding=5, fontsize=12)
        ax.set_ylim(0, max(values) * 1.25)
        ax.set_title(title, fontsize=11, pad=15)
        ax.set_ylabel("EUR / noc")
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("StayLens · walidacja na 1108 ofertach nowych gospodarzy", fontsize=15, y=0.99)
    fig.text(
        0.5,
        0.015,
        "Berlin 19.09.2026 • ceny ofertowe • test końcowy nieoceniany • niższy błąd = lepiej",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.05, 1, 0.93))
    fig.savefig(destination, dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "s02-v1")
    parser.add_argument("--report-dir", type=Path, default=ROOT / "reports" / "s02")
    args = parser.parse_args()
    protocol_path = ROOT / "configs" / "s02_protocol.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if protocol["source_sha256"] != SOURCE_SHA256 or protocol["features"] != {
        "categorical": CATEGORICAL,
        "numeric": NUMERIC,
    }:
        raise ValueError("Protocol and implementation contracts disagree")
    args.output.mkdir(parents=True, exist_ok=False)
    args.report_dir.mkdir(parents=True, exist_ok=True)
    start = {
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_sha256": sha256(protocol_path),
        "source_sha256": SOURCE_SHA256,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": {
            name: importlib.metadata.version(name)
            for name in [
                "numpy",
                "pandas",
                "scipy",
                "scikit-learn",
                "joblib",
                "fastapi",
                "pydantic",
                "threadpoolctl",
            ]
        },
        "source_code_sha256": {
            str(p.relative_to(ROOT)): sha256(p)
            for p in sorted((ROOT / "src" / "staylens").glob("*.py"))
        },
        "runner_sha256": sha256(Path(__file__)),
        "threads": 2,
        "test_evaluated": False,
    }
    write_json(args.output / "run_started.json", start)
    write_json(args.output / "protocol.json", protocol)
    train, validation, audit_extra = load_development(ROOT / "data" / "raw" / "listings.csv.gz")
    x, xv = feature_frame(train), feature_frame(validation)
    y, yv = train.price.to_numpy(), validation.price.to_numpy()
    audit = training_audit(train, FEATURES, audit_extra)
    # Feature matches are a diagnostic, not proof that two listings are the same property.
    train_hashes = set(pd.util.hash_pandas_object(x, index=False))
    audit["validation_rows_matching_train_features"] = int(
        pd.util.hash_pandas_object(xv, index=False).isin(train_hashes).sum()
    )
    write_json(args.report_dir / "feature_audit.json", audit)
    models = make_models(protocol)
    cv = GroupKFold(**{key: protocol["cv"][key] for key in ["n_splits", "shuffle", "random_state"]})
    out_of_fold = {name: np.full(len(train), np.nan) for name in models}
    folds = []
    for fold, (fit_index, score_index) in enumerate(cv.split(x, y, train.host_id), start=1):
        fit_hosts, score_hosts = (
            set(train.host_id.iloc[fit_index]),
            set(train.host_id.iloc[score_index]),
        )
        if fit_hosts & score_hosts:
            raise ValueError("CV host leakage")
        fold_result = {
            "fold": fold,
            "fit_rows": len(fit_index),
            "score_rows": len(score_index),
            "fit_hosts": len(fit_hosts),
            "score_hosts": len(score_hosts),
            "host_overlap": 0,
            "models": {},
        }
        for name, template in models.items():
            print(f"CV {fold}/3: {name}", flush=True)
            model = clone(template).fit(x.iloc[fit_index], y[fit_index])
            pred = predict_prices(model, x.iloc[score_index])
            out_of_fold[name][score_index] = pred
            fold_result["models"][name] = metrics(y[score_index], pred)
        folds.append(fold_result)
    cv_metrics = {name: metrics(y, pred) for name, pred in out_of_fold.items()}
    predictions, train_metrics = {}, {}
    for name, model in models.items():
        print(f"Train fit + validation: {name}", flush=True)
        model.fit(x, y)
        predictions[name] = predict_prices(model, xv)
        train_metrics[name] = metrics(y, predict_prices(model, x))
        path = args.output / f"{name}.joblib"
        joblib.dump(model, path, compress=3)
        restored = joblib.load(path)  # Only our locally generated, trusted artifact.
        np.testing.assert_allclose(predictions[name], predict_prices(restored, xv), rtol=0, atol=0)
    validation_metrics = {name: metrics(yv, pred) for name, pred in predictions.items()}
    selection = select_model(validation_metrics, cv_metrics, protocol["selection"])
    report = {
        **start,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiment_id": protocol["experiment_id"],
        "counts": {
            "train": len(train),
            "train_hosts": int(train.host_id.nunique()),
            "validation": len(validation),
            "validation_hosts": int(validation.host_id.nunique()),
            "train_validation_host_overlap": 0,
        },
        "train": train_metrics,
        "cv_pooled": cv_metrics,
        "cv_folds": folds,
        "validation": validation_metrics,
        "selection": selection,
        "validation_segments": grouped_metrics(
            validation, predictions, FEATURES, protocol["diagnostics"]["price_bands_eur"]
        ),
        "bootstrap": cluster_bootstrap(
            validation,
            predictions,
            protocol["diagnostics"]["host_cluster_bootstrap_replicates"],
            protocol["diagnostics"]["bootstrap_seed"],
        ),
        "artifact_roundtrip_exact": True,
    }
    for name, data, preds in [("validation", validation, predictions), ("cv", train, out_of_fold)]:
        output = data[["listing_id", "host_id", "price"]].copy()
        for model_name, pred in preds.items():
            output[model_name] = pred
        output.to_csv(args.output / f"{name}_predictions.csv", index=False)
    selected = selection["selected"]
    manifest = {
        "model_version": "s02-v1",
        "selected_model": selected,
        "model_file": f"{selected}.joblib",
        "model_sha256": sha256(args.output / f"{selected}.joblib"),
        "source_sha256": SOURCE_SHA256,
        "protocol_sha256": start["protocol_sha256"],
        "snapshot": "2026-09-19",
        "city": "Berlin",
        "currency": "EUR",
        "target": "offered nightly listing price",
        "features": FEATURES,
        "training_rows": len(train),
        "validation_rows": len(validation),
        "test_evaluated": False,
        "validation_metrics": validation_metrics[selected],
        "cv_metrics": cv_metrics[selected],
        "categories": {key: x[key].value_counts().astype(int).to_dict() for key in CATEGORICAL},
        "numeric_ranges": audit["numeric_ranges"],
        "packages": start["packages"],
        "limitations": [
            "Historical Berlin snapshot; no booking dates or current availability",
            "Offered prices, not paid prices or revenue",
            "No per-listing confidence interval",
            "Small hotel/shared-room samples; high-price predictions need caution",
            "Not a final test result; no proof against future or geographic drift",
            "Public preview listings belong to training; in-sample predictions must be labelled in the UI",
        ],
    }
    write_json(args.output / "manifest.json", manifest)
    write_json(args.report_dir / "model_manifest.json", manifest)
    write_json(args.report_dir / "comparison.json", report)
    comparison_plot(validation_metrics, args.report_dir / "comparison.png")
    print(
        json.dumps(
            {
                "validation": validation_metrics,
                "cv_pooled": cv_metrics,
                "selection": selection,
                "bootstrap": report["bootstrap"],
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    with threadpool_limits(limits=2):
        main()
