"""Fixed S03b comparison; select on train CV before optional validation, never test."""

import argparse
import importlib.metadata
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.model_selection import GroupKFold
from threadpoolctl import threadpool_limits

from staylens.data import sha256
from staylens.engineering import load_partition
from staylens.evaluation import cluster_bootstrap, metrics
from staylens.features import CATEGORICAL, FEATURES, NUMERIC, feature_frame
from staylens.models import predict_prices
from staylens.research_models import gate, make_research_models, summary_segments
from staylens.scope_audit import load_scope

ROOT = Path(__file__).resolve().parents[1]


def write_json(path, data):
    path.parent.mkdir(exist_ok=True, parents=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/s03b-v1")
    parser.add_argument("--report-dir", type=Path, default=ROOT / "reports/s03b")
    args = parser.parse_args()
    protocol_path = ROOT / "configs/s03b_protocol.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    original = json.loads((ROOT / "configs/s02_protocol.json").read_text(encoding="utf-8"))
    args.output.mkdir(parents=True, exist_ok=False)
    args.report_dir.mkdir(parents=True, exist_ok=True)
    freeze = {
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_sha256": sha256(protocol_path),
        "source_sha256": protocol["source_sha256"],
        "python": platform.python_version(),
        "packages": {
            key: importlib.metadata.version(key)
            for key in ["numpy", "pandas", "scikit-learn", "catboost", "joblib", "scipy"]
        },
        "source_code_sha256": {
            str(path.relative_to(ROOT)).replace("\\", "/"): sha256(path)
            for path in [
                Path(__file__),
                ROOT / "src/staylens/research_models.py",
                ROOT / "src/staylens/scope_audit.py",
            ]
        },
        "research_lock_sha256": sha256(ROOT / "requirements-research.lock.txt"),
        "test_evaluated": False,
    }
    write_json(args.output / "run_started.json", freeze)
    write_json(args.output / "protocol.json", protocol)
    train = load_partition(ROOT / "data/raw/listings.csv.gz", "train")
    scope = load_scope(ROOT / "data/raw/listings.csv.gz")
    flags = train.listing_id.map(lambda key: bool(scope[key]["flags"])).to_numpy()
    write_json(
        args.output / "purpose_review.json",
        {key: value for key, value in scope.items() if value["flags"]},
    )
    x, y = feature_frame(train), train.price.to_numpy()
    templates = make_research_models(protocol, original)
    variants = {v["name"]: v for v in protocol["variants"]}
    splitter = GroupKFold(**protocol["cv"])
    splits = list(splitter.split(x, y, train.host_id))
    oof = {name: np.full(len(train), np.nan) for name in templates}
    fold_ids = np.zeros(len(train), dtype=int)
    fold_reports = []
    for fold, (fit, score) in enumerate(splits, 1):
        assert not set(train.host_id.iloc[fit]) & set(train.host_id.iloc[score])
        fold_ids[score] = fold
        result = {
            "fold": fold,
            "fit_rows": len(fit),
            "score_rows": len(score),
            "host_overlap": 0,
            "models": {},
        }
        for name, template in templates.items():
            variant = variants[name]
            fit_used = fit[~flags[fit]] if variant.get("exclude_flagged_fit") else fit
            started = time.monotonic()
            print(f"CV {fold}/3: {name} ({len(fit_used)} fit / {len(score)} score)", flush=True)
            if variant["family"] == "blend":
                prediction = np.average(
                    [oof[member][score] for member in variant["members"]],
                    axis=0,
                    weights=variant["weights"],
                )
                own_metrics = None
            else:
                model = clone(template).fit(x.iloc[fit_used], y[fit_used])
                prediction = predict_prices(model, x.iloc[score])
                own_metrics = metrics(y[fit_used], predict_prices(model, x.iloc[fit_used]))
            oof[name][score] = prediction
            result["models"][name] = {
                "score": metrics(y[score], prediction),
                "train": own_metrics,
                "fit_rows": len(fit_used),
                "seconds": round(time.monotonic() - started, 3),
            }
            print(json.dumps(result["models"][name]["score"]), flush=True)
        fold_reports.append(result)
        write_json(args.output / f"fold_{fold}.json", result)
    for prediction in oof.values():
        assert np.isfinite(prediction).all() and (prediction > 0).all()
    old = pd.read_csv(
        ROOT / "artifacts/s02-v1/cv_predictions.csv", dtype={"listing_id": str}
    ).set_index("listing_id")
    old_values = old.loc[train.listing_id, "hist_gradient_boosting"].to_numpy()
    maximum_control_difference = float(np.max(np.abs(old_values - oof["s02_control"])))
    assert maximum_control_difference < 1e-8
    frame = train[["listing_id", "host_id", "price", "room_type", "minimum_nights"]].copy()
    frame["fold"], frame["purpose_flag"] = fold_ids, flags
    for name, prediction in oof.items():
        frame[name] = prediction
    frame.to_csv(args.output / "cv_predictions.csv", index=False)
    scores = {name: summary_segments(train, prediction, flags) for name, prediction in oof.items()}
    gates = {}
    for name in templates:
        if name == "s02_control":
            continue
        fold_pairs = [
            (r["models"][name]["score"]["mae_eur"], r["models"]["s02_control"]["score"]["mae_eur"])
            for r in fold_reports
        ]
        gates[name] = gate(
            scores[name], scores["s02_control"], protocol["selection"], "cv", fold_pairs
        )
    ranking = sorted(gates, key=lambda name: (scores[name]["all"]["mae_eur"], name))
    eligible = [name for name in ranking if gates[name]["passed"]]
    selected = eligible[0] if eligible else None
    # Persist choice before even loading validation features or labels.
    decision = {
        "cv_selected": selected,
        "diagnostic_best": ranking[0],
        "cv_gates": gates,
        "ranking": ranking,
        "decided_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_json(args.output / "cv_decision.json", decision)
    write_json(args.report_dir / "cv_decision.json", decision)
    report = {
        **freeze,
        "counts": {
            "train": len(train),
            "hosts": int(train.host_id.nunique()),
            "purpose_flags": int(flags.sum()),
        },
        "control_max_difference": maximum_control_difference,
        "cv": scores,
        "folds": fold_reports,
        "selection": decision,
        "validation_evaluated": False,
        "promoted": False,
    }
    # Pointwise prediction provenance is private. Report aggregated scope statistics.
    report["scope_audit"] = {
        "title_rule_sha256": sha256(ROOT / "src/staylens/scope_audit.py"),
        "flagged_train_rows": int(flags.sum()),
        "assistant_review": "Five train title/description matches reviewed without prices; mixed event use is not proof that overnight use is impossible",
        "main_evaluation_excludes_nothing": True,
    }
    report["cv_bootstrap_best_vs_s02"] = cluster_bootstrap(
        train,
        {"segment_median": oof["s02_control"], "hist_gradient_boosting": oof[ranking[0]]},
        protocol["diagnostics"]["bootstrap_host_replicates"],
        protocol["diagnostics"]["bootstrap_seed"],
    )
    write_json(args.report_dir / "comparison.json", report)
    if selected:
        print(f"Validation of preselected candidate only: {selected}", flush=True)
        chosen_variant = variants[selected]
        fit_used = (
            np.flatnonzero(~flags)
            if chosen_variant.get("exclude_flagged_fit")
            else np.arange(len(train))
        )
        model = clone(templates[selected]).fit(x.iloc[fit_used], y[fit_used])
        validation = load_partition(ROOT / "data/raw/listings.csv.gz", "validation")
        assert not set(train.host_id) & set(validation.host_id)
        vscope = load_scope(ROOT / "data/raw/listings.csv.gz", "validation")
        vflags = validation.listing_id.map(lambda key: bool(vscope[key]["flags"])).to_numpy()
        xv = feature_frame(validation)
        prediction = predict_prices(model, xv)
        old_validation = pd.read_csv(
            ROOT / "artifacts/s02-v1/validation_predictions.csv", dtype={"listing_id": str}
        ).set_index("listing_id")
        control = old_validation.loc[validation.listing_id, "hist_gradient_boosting"].to_numpy()
        v_scores = {
            "s02_control": summary_segments(validation, control, vflags),
            selected: summary_segments(validation, prediction, vflags),
        }
        vgate = gate(
            v_scores[selected], v_scores["s02_control"], protocol["selection"], "validation"
        )
        report.update(
            {
                "validation_evaluated": True,
                "validation": v_scores,
                "validation_gate": vgate,
                "promoted": vgate["passed"],
                "validation_bootstrap": cluster_bootstrap(
                    validation,
                    {"segment_median": control, "hist_gradient_boosting": prediction},
                    1000,
                    42,
                ),
            }
        )
        validation_output = validation[["listing_id", "host_id", "price"]].copy()
        validation_output["s02_control"], validation_output[selected] = control, prediction
        validation_output.to_csv(args.output / "validation_predictions.csv", index=False)
        joblib.dump(model, args.output / "candidate.joblib", compress=3)
        reloaded = joblib.load(args.output / "candidate.joblib")
        assert np.array_equal(prediction, predict_prices(reloaded, xv))
        if vgate["passed"]:
            old_manifest = json.loads(
                (ROOT / "artifacts/s02-v1/manifest.json").read_text(encoding="utf-8")
            )
            manifest = {
                **old_manifest,
                "model_version": protocol["experiment_id"],
                "selected_model": selected,
                "model_file": "candidate.joblib",
                "model_sha256": sha256(args.output / "candidate.joblib"),
                "features": FEATURES,
                "training_rows": len(fit_used),
                "catalog_rows": len(train),
                "validation_rows": len(validation),
                "packages": freeze["packages"],
                "validation_metrics": v_scores[selected]["all"],
                "cv_metrics": scores[selected]["all"],
                "test_evaluated": False,
                "protocol_sha256": freeze["protocol_sha256"],
                "oof_file": "cv_predictions.csv",
                "oof_prediction_column": selected,
                "oof_sha256": sha256(args.output / "cv_predictions.csv"),
                "validation_segments": v_scores[selected],
                "cv_segments": scores[selected],
            }
            manifest["categories"] = {
                key: train.iloc[fit_used][key].value_counts().astype(int).to_dict()
                for key in CATEGORICAL
            }
            manifest["numeric_ranges"] = {
                key: {
                    "min": float(x.iloc[fit_used][key].min()),
                    "max": float(x.iloc[fit_used][key].max()),
                }
                for key in NUMERIC
            }
            manifest["limitations"] = [
                "Historyczne ceny ofertowe Berlina; brak terminu, dostępności i pełnych informacji o standardzie.",
                "Rozwojowe wyniki po wielokrotnym wykorzystaniu CV; finalny test nieoceniany.",
                "Małe próby hotel/shared, duże błędy drogich ofert. MAE nie jest indywidualnym przedziałem.",
            ]
            write_json(args.output / "manifest.json", manifest)
        write_json(args.report_dir / "comparison.json", report)
    best = ranking[0]
    print(f"Diagnostic learning curve: {best}", flush=True)
    curve = []
    fractions = protocol["diagnostics"]["learning_curve_host_fractions"]
    for fold, (fit, score) in enumerate(splits, 1):
        hosts = np.array(sorted(train.host_id.iloc[fit].unique()))
        rng = np.random.default_rng(
            protocol["diagnostics"]["learning_curve_host_sampling_seed"] + fold
        )
        rng.shuffle(hosts)
        for fraction in fractions:
            keep = set(hosts[: max(1, int(len(hosts) * fraction))])
            used = fit[train.host_id.iloc[fit].isin(keep).to_numpy()]
            if variants[best].get("exclude_flagged_fit"):
                used = used[~flags[used]]
            if fraction == 1.0 and variants[best]["family"] != "blend":
                own = fold_reports[fold - 1]["models"][best]["train"]
                evaluated = fold_reports[fold - 1]["models"][best]["score"]
            else:
                print(f"Curve fold {fold}: {fraction:.0%} hosts / {len(used)} rows", flush=True)
                model = clone(templates[best]).fit(x.iloc[used], y[used])
                own = metrics(y[used], predict_prices(model, x.iloc[used]))
                evaluated = metrics(y[score], predict_prices(model, x.iloc[score]))
            curve.append(
                {
                    "fold": fold,
                    "host_fraction": fraction,
                    "fit_rows": len(used),
                    "score_rows": len(score),
                    "train": own,
                    "score": evaluated,
                }
            )
    report["learning_curve"] = {"candidate": best, "rows": curve, "diagnostic_only": True}
    report["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
    report["artifacts"] = {
        path.name: sha256(path) for path in args.output.iterdir() if path.is_file()
    }
    write_json(args.report_dir / "comparison.json", report)
    print(
        json.dumps(
            {
                "selected": selected,
                "promoted": report["promoted"],
                "best_cv_mae": scores[best]["all"]["mae_eur"],
                "test_evaluated": False,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    with threadpool_limits(limits=2):
        main()
