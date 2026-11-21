"""Porównaj dwa modele na train/validation. Nie odczytuje końcowego testu."""

import argparse
import importlib.metadata
import json
from pathlib import Path

import joblib
from sklearn.model_selection import GroupKFold, cross_val_predict
from threadpoolctl import threadpool_limits

from staylens.data import SOURCE_SHA256, load_development, sha256
from staylens.evaluation import metrics, select_model
from staylens.features import CATEGORICAL, FEATURES, NUMERIC, feature_frame
from staylens.models import make_models, predict_prices

ROOT = Path(__file__).resolve().parents[1]


def write_json(path, value):
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8"
    )


def train_models(train, validation, output):
    if set(train["host_id"]) & set(validation["host_id"]):
        raise ValueError("Ten sam gospodarz występuje w treningu i walidacji")
    output.mkdir(parents=True, exist_ok=False)
    x_train = feature_frame(train)
    y_train = train["price"].to_numpy()
    x_validation = feature_frame(validation)
    y_validation = validation["price"].to_numpy()
    cv = GroupKFold(n_splits=3, shuffle=True, random_state=42)
    cv_predictions = train[["listing_id", "host_id", "price"]].copy()
    validation_predictions = validation[["listing_id", "host_id", "price"]].copy()
    train_metrics, cv_metrics, validation_metrics = {}, {}, {}

    for name, model in make_models().items():
        print(f"Trening i walidacja: {name}", flush=True)
        # Oferty jednego gospodarza zawsze trafiają do tej samej części CV.
        cv_predictions[name] = cross_val_predict(
            model, x_train, y_train, groups=train["host_id"], cv=cv, n_jobs=1
        )
        cv_metrics[name] = metrics(y_train, cv_predictions[name])

        # Dopiero po CV uczymy model na całym train i oceniamy osobną walidację.
        model.fit(x_train, y_train)
        validation_predictions[name] = predict_prices(model, x_validation)
        train_metrics[name] = metrics(y_train, predict_prices(model, x_train))
        validation_metrics[name] = metrics(y_validation, validation_predictions[name])
        joblib.dump(model, output / f"{name}.joblib", compress=3)

    cv_predictions.to_csv(output / "cv_predictions.csv", index=False)
    validation_predictions.to_csv(output / "validation_predictions.csv", index=False)
    selection = select_model(validation_metrics, cv_metrics)
    report = {
        "training_rows": len(train),
        "validation_rows": len(validation),
        "test_evaluated": False,
        "train": train_metrics,
        "cv": cv_metrics,
        "validation": validation_metrics,
        "selection": selection,
    }
    write_json(output / "comparison.json", report)

    # Manifest opisuje zapisany model i dane, z którymi wolno go uruchamiać.
    selected = selection["selected"]
    manifest = {
        "model_version": "training-run",
        "selected_model": selected,
        "model_file": f"{selected}.joblib",
        "model_sha256": sha256(output / f"{selected}.joblib"),
        "oof_predictions_sha256": sha256(output / "cv_predictions.csv"),
        "source_sha256": SOURCE_SHA256,
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
        "categories": {column: x_train[column].value_counts().to_dict() for column in CATEGORICAL},
        "numeric_ranges": {
            column: {"min": float(x_train[column].min()), "max": float(x_train[column].max())}
            for column in NUMERIC
        },
        "packages": {
            name: importlib.metadata.version(name)
            for name in ["scikit-learn", "numpy", "pandas", "joblib"]
        },
        "limitations": [
            "Historical Berlin snapshot; no booking dates or current availability",
            "Offered prices, not paid prices or revenue",
            "Small hotel/shared-room samples; high-price predictions need caution",
            "Not a final test result; no per-listing prediction interval",
        ],
    }
    write_json(output / "manifest.json", manifest)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/training-run")
    args = parser.parse_args()
    train, validation = load_development(ROOT / "data/raw/listings.csv.gz")
    with threadpool_limits(limits=2):
        result = train_models(train, validation, args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
