"""Two predeclared rich-input candidates and mandatory empty-new-fields stress test."""

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.model_selection import GroupKFold
from threadpoolctl import threadpool_limits

from staylens.data import sha256
from staylens.evaluation import cluster_bootstrap
from staylens.models import predict_prices
from staylens.research_models import gate, summary_segments
from staylens.rich_models import INPUTS, NEW_INPUTS, load_rich, make_rich_models

ROOT = Path(__file__).resolve().parents[1]


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def stress_gate(candidate, control, rules):
    checks = {
        "mae": candidate["mae_eur"] <= control["mae_eur"] * rules["max_mae_ratio_to_s02"],
        "within20": candidate["within_20_percent"]
        >= control["within_20_percent"] + rules["min_within20_difference_to_s02"],
    }
    return {"passed": all(checks.values()), "checks": checks}


def main():
    out, reports = ROOT / "artifacts/s03c-v1", ROOT / "reports/s03c"
    out.mkdir(parents=True, exist_ok=False)
    protocol = json.loads((ROOT / "configs/s03c_protocol.json").read_text(encoding="utf-8"))
    rules = json.loads((ROOT / "configs/s03b_protocol.json").read_text(encoding="utf-8"))[
        "selection"
    ]
    start = {
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_sha256": sha256(ROOT / "configs/s03c_protocol.json"),
        "gates_protocol_sha256": sha256(ROOT / "configs/s03b_protocol.json"),
        "research_lock_sha256": sha256(ROOT / "requirements-research.lock.txt"),
        "code_sha256": {
            str(path.relative_to(ROOT)).replace("\\", "/"): sha256(path)
            for path in [
                Path(__file__),
                ROOT / "src/staylens/rich_models.py",
                ROOT / "src/staylens/research_models.py",
                ROOT / "src/staylens/engineering.py",
                ROOT / "src/staylens/enrichment.py",
                ROOT / "src/staylens/scope_audit.py",
            ]
        },
        "test_evaluated": False,
    }
    write(out / "run_started.json", start)
    write(out / "protocol.json", protocol)
    data, flags = load_rich(ROOT / "data/raw/listings.csv.gz", "train")
    x, y = data[INPUTS], data.price.to_numpy()
    missing = x.copy()
    missing[NEW_INPUTS] = np.nan
    source_pred = pd.read_csv(
        ROOT / "artifacts/s02-v1/cv_predictions.csv", dtype={"listing_id": str}
    ).set_index("listing_id")
    assert np.array_equal(source_pred.loc[data.listing_id, "price"], y)
    control = source_pred.loc[data.listing_id, "hist_gradient_boosting"].to_numpy()
    models = make_rich_models(protocol)
    oof = {key: np.full(len(data), np.nan) for key in models}
    masked = {key: np.full(len(data), np.nan) for key in models}
    folds = []
    fold_ids = np.zeros(len(data), dtype=int)
    for fold, (fit, score) in enumerate(
        GroupKFold(**protocol["cv"]).split(x, groups=data.host_id), 1
    ):
        assert not set(data.host_id.iloc[fit]) & set(data.host_id.iloc[score])
        fold_ids[score] = fold
        fold_result = {"fold": fold, "fit_rows": len(fit), "score_rows": len(score), "models": {}}
        baseline = summary_segments(data.iloc[score], control[score], flags[score])
        for name, template in models.items():
            print(f"Rich CV {fold}/3: {name}", flush=True)
            fitted = clone(template).fit(x.iloc[fit], y[fit])
            oof[name][score] = predict_prices(fitted, x.iloc[score])
            masked[name][score] = predict_prices(fitted, missing.iloc[score])
            evaluated = summary_segments(data.iloc[score], oof[name][score], flags[score])
            fold_result["models"][name] = {
                "mae": evaluated["all"]["mae_eur"],
                "control_mae": baseline["all"]["mae_eur"],
            }
            print(json.dumps(fold_result["models"][name]), flush=True)
        folds.append(fold_result)
    predictions = data[["listing_id", "host_id", "price"]].copy()
    predictions["fold"], predictions["s02_control"] = fold_ids, control
    for name in models:
        predictions[name], predictions[f"{name}_missing_new"] = oof[name], masked[name]
    predictions.to_csv(out / "cv_predictions.csv", index=False)
    data[["listing_id", "host_id", *INPUTS]].to_csv(out / "train_features.csv", index=False)
    scores = {
        "s02_control": summary_segments(data, control, flags),
        **{key: summary_segments(data, value, flags) for key, value in oof.items()},
    }
    stress = {key: summary_segments(data, value, flags) for key, value in masked.items()}
    gates, empty_gates = {}, {}
    for name in models:
        pairs = [(row["models"][name]["mae"], row["models"][name]["control_mae"]) for row in folds]
        gates[name] = gate(scores[name], scores["s02_control"], rules, "cv", pairs)
        empty_gates[name] = stress_gate(
            stress[name]["all"], scores["s02_control"]["all"], protocol["missing_new_inputs_gate"]
        )
    eligible = [name for name in models if gates[name]["passed"] and empty_gates[name]["passed"]]
    selected = (
        min(eligible, key=lambda name: (scores[name]["all"]["mae_eur"], name)) if eligible else None
    )
    decision = {
        "selected": selected,
        "gates": gates,
        "empty_fields_gates": empty_gates,
        "decided_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    write(out / "cv_decision.json", decision)
    report = {
        **start,
        "rows": len(data),
        "feature_count": 40,
        "new_inputs": NEW_INPUTS,
        "observed_new_inputs": data[NEW_INPUTS].notna().sum().astype(int).to_dict(),
        "cv": scores,
        "missing_new_fields": stress,
        "folds": folds,
        "decision": decision,
        "validation_evaluated": False,
        "promoted": False,
    }
    best = min(models, key=lambda name: scores[name]["all"]["mae_eur"])
    report["best_cv_bootstrap"] = cluster_bootstrap(
        data, {"segment_median": control, "hist_gradient_boosting": oof[best]}, 1000, 42
    )
    if selected:
        print(f"Rich validation: {selected}", flush=True)
        fitted = clone(models[selected]).fit(x, y)
        validation, vf = load_rich(ROOT / "data/raw/listings.csv.gz", "validation")
        assert not set(data.host_id) & set(validation.host_id)
        original = pd.read_csv(
            ROOT / "artifacts/s02-v1/validation_predictions.csv", dtype={"listing_id": str}
        ).set_index("listing_id")
        base = original.loc[validation.listing_id, "hist_gradient_boosting"].to_numpy()
        pred = predict_prices(fitted, validation[INPUTS])
        empty = validation[INPUTS].copy()
        empty[NEW_INPUTS] = np.nan
        pred_empty = predict_prices(fitted, empty)
        baseline = summary_segments(validation, base, vf)
        full = summary_segments(validation, pred, vf)
        unknown = summary_segments(validation, pred_empty, vf)
        final_gate = gate(full, baseline, rules, "validation")
        unknown_gate = stress_gate(
            unknown["all"], baseline["all"], protocol["missing_new_inputs_gate"]
        )
        report.update(
            {
                "validation_evaluated": True,
                "validation": {
                    "s02_control": baseline,
                    selected: full,
                    "missing_new_fields": unknown,
                },
                "validation_gate": final_gate,
                "validation_missing_gate": unknown_gate,
                "promoted": final_gate["passed"] and unknown_gate["passed"],
            }
        )
        vp = validation[["listing_id", "host_id", "price"]].copy()
        vp["s02_control"], vp[selected], vp["missing_new_fields"] = base, pred, pred_empty
        vp.to_csv(out / "validation_predictions.csv", index=False)
        joblib.dump(fitted, out / "candidate.joblib", compress=3)
        assert np.array_equal(
            pred, predict_prices(joblib.load(out / "candidate.joblib"), validation[INPUTS])
        )
    report["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
    report["outputs_sha256"] = {path.name: sha256(path) for path in out.iterdir() if path.is_file()}
    write(reports / "comparison.json", report)
    print(
        json.dumps(
            {
                "selected": selected,
                "promoted": report["promoted"],
                "best_mae": scores[best]["all"]["mae_eur"],
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    with threadpool_limits(limits=2):
        main()
