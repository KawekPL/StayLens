"""Bounded real-data enrichment experiment; freeze hashes before any fit."""

import argparse
import importlib.metadata
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import matplotlib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder
from threadpoolctl import threadpool_limits

from staylens.data import sha256
from staylens.enrichment import AREA_FEATURES, QUALITY_FEATURES, enriched_partition
from staylens.experiment_b import choose_cv, eligibility, predict, summary
from staylens.features import CATEGORICAL, NUMERIC

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def write_json(path, data):
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def make_model(base, extra):
    params = {
        k: v
        for k, v in base["candidate"].items()
        if k not in {"name", "target_transform", "categorical_encoding"}
    }
    return Pipeline(
        [
            (
                "features",
                ColumnTransformer(
                    [
                        (
                            "categories",
                            OrdinalEncoder(
                                handle_unknown="use_encoded_value", unknown_value=-1, dtype=float
                            ),
                            CATEGORICAL,
                        ),
                        ("numbers", "passthrough", NUMERIC + extra),
                    ]
                ),
            ),
            (
                "regressor",
                HistGradientBoostingRegressor(
                    categorical_features=list(range(len(CATEGORICAL))), **params
                ),
            ),
        ]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/s02c-v1")
    parser.add_argument("--report-dir", type=Path, default=ROOT / "reports/s02c")
    args = parser.parse_args()
    if args.output.exists() or args.report_dir.exists():
        raise FileExistsError("Refusing to overwrite experiment output")
    args.output.mkdir(parents=True)
    args.report_dir.mkdir(parents=True)
    protocol_path = ROOT / "configs/s02c_protocol.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    base_path = ROOT / "configs/s02_protocol.json"
    base = json.loads(base_path.read_text(encoding="utf-8"))
    source, external = (
        ROOT / "data/raw/listings.csv.gz",
        ROOT / "data/raw/external/doorstep_berlin_20260919.zip",
    )
    assert sha256(source) == protocol["source_sha256"]
    assert sha256(external) == protocol["external_sha256"]
    frozen = {
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_sha256": sha256(protocol_path),
        "base_protocol_sha256": sha256(base_path),
        "runner_sha256": sha256(Path(__file__)),
        "source_sha256": sha256(source),
        "external_sha256": sha256(external),
        "code_sha256": {
            p.relative_to(ROOT).as_posix(): sha256(p)
            for p in sorted((ROOT / "src/staylens").glob("*.py"))
        },
        "packages": {
            p: importlib.metadata.version(p)
            for p in ["numpy", "pandas", "scikit-learn", "scipy", "joblib", "threadpoolctl"]
        },
        "test_evaluated": False,
    }
    write_json(args.output / "run_started.json", frozen)
    write_json(args.output / "protocol.json", protocol)
    train, audit, evidence, joins = enriched_partition(source, external, "train")
    evidence.to_csv(args.output / "area_evidence_train.csv", index=False)
    joins.to_csv(args.output / "join_provenance_train.csv", index=False)
    train.to_csv(args.output / "train_features.csv", index=False)
    cv = GroupKFold(**protocol["cv"])
    predictions = {name: np.full(len(train), np.nan) for name in protocol["variants"]}
    fold_ids, fold_metrics = np.zeros(len(train), dtype=int), []
    with threadpool_limits(limits=2):
        for fold, (fit, score) in enumerate(cv.split(train, groups=train.host_id)):
            assert not set(train.iloc[fit].host_id) & set(train.iloc[score].host_id)
            fold_ids[score] = fold
            for name, extra in protocol["variants"].items():
                model = make_model(base, extra)
                model.fit(train.iloc[fit], train.price.iloc[fit])
                values, clipped = predict(
                    model, train.iloc[score], protocol["prediction_floor_eur"]
                )
                predictions[name][score] = values
                fold_metrics.append(
                    {
                        "fold": fold,
                        "variant": name,
                        "clipped": clipped,
                        "metrics": summary(train.iloc[score], values),
                    }
                )
                print(
                    f"fold={fold} {name} MAE={fold_metrics[-1]['metrics']['all']['mae_eur']:.3f}",
                    flush=True,
                )
        results = {k: summary(train, v) for k, v in predictions.items()}
        prior = pd.read_csv(
            ROOT / "artifacts/s02-v1/cv_predictions.csv", dtype={"listing_id": str, "host_id": str}
        ).set_index("listing_id")
        assert np.allclose(
            prior.loc[train.listing_id, "hist_gradient_boosting"].to_numpy(),
            predictions["s02_control"],
            rtol=0,
            atol=1e-10,
        )
        selected = choose_cv(results, protocol["cv_selection"])
        # Persist CV decision before any validation data is loaded.
        write_json(args.output / "cv_selection.json", selected)
        scored = train[["listing_id", "host_id", "price"]].copy()
        scored["fold"] = fold_ids
        for name, values in predictions.items():
            scored[name] = values
        scored.to_csv(args.output / "cv_predictions.csv", index=False)
        validation, val_gate = (
            {},
            {"evaluated": False, "passed": False, "reason": "No new candidate passed CV"},
        )
        if selected["winner"] != "s02_control":
            valid, val_audit, val_evidence, val_joins = enriched_partition(
                source, external, "validation"
            )
            val_evidence.to_csv(args.output / "area_evidence_validation.csv", index=False)
            val_joins.to_csv(args.output / "join_provenance_validation.csv", index=False)
            val_predictions = valid[["listing_id", "host_id", "price"]].copy()
            for name in ["s02_control", selected["winner"]]:
                model = make_model(base, protocol["variants"][name])
                model.fit(train, train.price)
                values, _ = predict(model, valid, protocol["prediction_floor_eur"])
                validation[name] = summary(valid, values)
                val_predictions[name] = values
                joblib.dump(model, args.output / f"{name}.joblib")
            val_predictions.to_csv(args.output / "validation_predictions.csv", index=False)
            checks = eligibility(
                validation[selected["winner"]],
                validation["s02_control"],
                protocol["validation_gate"],
                cv=False,
            )
            val_gate = {
                "evaluated": True,
                "passed": all(checks.values()),
                "checks": checks,
                "audit": val_audit,
            }
    coverage = {}
    for segment, mask in {
        "all": np.ones(len(train), dtype=bool),
        "over_400": train.price.gt(400),
    }.items():
        coverage[segment] = {
            "rows": int(np.sum(mask)),
            **{c: int(train.loc[mask, c].notna().sum()) for c in AREA_FEATURES + QUALITY_FEATURES},
        }
    report = {
        "experiment_id": protocol["experiment_id"],
        "audit": audit,
        "coverage": coverage,
        "cv": results,
        "folds": fold_metrics,
        "cv_selection": selected,
        "validation": validation,
        "validation_gate": val_gate,
        "control_reproduces_s02": True,
        "test_evaluated": False,
        "active_model": "s02-v1",
    }
    write_json(args.report_dir / "comparison.json", report)
    write_json(
        args.report_dir / "manifest.json",
        {
            **frozen,
            "outputs_sha256": {
                p.name: sha256(p) for p in sorted(args.output.iterdir()) if p.is_file()
            },
        },
    )
    names = list(results)
    labels = ["S02 — obecny", "+ metraż", "+ sygnały jakości", "+ oba dodatki"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
    for ax, segment, title in zip(
        axes, ["all", "over_400"], ["Wszystkie oferty", "Oferty powyżej 400 EUR"], strict=True
    ):
        values = [results[n][segment]["mae_eur"] for n in names]
        bars = ax.barh(labels, values, color=["#879c96", "#167466", "#167466", "#167466"])
        ax.bar_label(bars, labels=[f"{v:.2f}" for v in values], padding=4)
        ax.set_xlim(0, max(values) * 1.2)
        ax.set_title(title)
        ax.set_xlabel("MAE [EUR / noc] — mniej = lepiej")
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].invert_yaxis()
    fig.suptitle("StayLens S02c · rzeczywiste dodatkowe informacje · CV po gospodarzach")
    fig.tight_layout()
    fig.savefig(args.report_dir / "comparison.png", dpi=150)
    plt.close(fig)
    print(
        json.dumps({"audit": audit, "selection": selected, "validation_gate": val_gate}, indent=2)
    )


if __name__ == "__main__":
    main()
