"""Frozen feature/augmentation ablation. Never load or evaluate final test data."""

import argparse
import importlib.metadata
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import matplotlib
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold
from threadpoolctl import threadpool_limits

from staylens.augmentation import augment_fit
from staylens.data import SOURCE_SHA256, sha256
from staylens.engineering import (
    DERIVED,
    ENGINEERED_CATEGORICAL,
    ENGINEERED_FEATURES,
    EXTRA_AMENITIES,
    RAW_FEATURES,
    EngineerFeatures,
    load_partition,
)
from staylens.evaluation import cluster_bootstrap, metrics
from staylens.experiment_b import choose_cv, eligibility, make_variant, predict, summary
from staylens.features import FEATURES

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
NAMES = {
    "s02_control": "S02 — punkt odniesienia",
    "engineered": "Rozbudowane cechy",
    "engineered_leaf15": "Cechy + mniejsze liście",
    "engineered_squared": "Cechy + błąd kwadratowy",
    "engineered_repeat": "Cechy + powtórzone drogie oferty",
    "engineered_masked": "Cechy + sztuczne wersje z brakami",
}


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def provenance(data):
    generated = data[data.is_augmented]
    return {
        "real_rows": int((~data.is_augmented).sum()),
        "added_rows": len(generated),
        "real_hosts": int(data[~data.is_augmented].host_id.nunique()),
        "new_hosts_added": len(set(generated.host_id) - set(data[~data.is_augmented].host_id)),
        "new_price_labels": 0,
        "evaluation_contains_augmented_rows": False,
    }


def plot_comparison(results, destination):
    names = list(results)
    fig, axes = plt.subplots(1, 3, figsize=(14, 5), sharey=True)
    for ax, group, title in zip(
        axes,
        ["all", "up_to_400", "over_400"],
        ["Wszystkie oferty", "Cena do 400 EUR", "Cena powyżej 400 EUR"],
        strict=True,
    ):
        values = [results[name][group]["mae_eur"] for name in names]
        bars = ax.barh(
            range(len(names)),
            values,
            color=["#9ba9a5" if name == "s02_control" else "#167466" for name in names],
        )
        ax.bar_label(bars, labels=[f"{v:.2f}" for v in values], padding=3, fontsize=10)
        ax.set_xlim(0, max(values) * 1.22)
        ax.set_title(title)
        ax.set_xlabel("MAE [EUR / noc] — mniej = lepiej")
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_yticks(range(len(names)), [NAMES[name] for name in names])
    axes[0].invert_yaxis()
    fig.suptitle("StayLens S02b · grupowana CV na prawdziwych ofertach", fontsize=15)
    fig.text(
        0.5,
        0.015,
        "5814 ocenianych ofert • augmentacja wyłącznie w treningu • CV służy wyborowi, test końcowy odłożony",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.94))
    fig.savefig(destination, dpi=150)
    plt.close(fig)


def markdown_report(report, path):
    selected = report["cv_selection"]["winner"]
    lines = [
        "# S02b — data engineering i eksperyment z augmentacją",
        "",
        f"Wybór na CV: **{NAMES[selected]}**. Przeszedł bramkę walidacyjną: **{report['validation_gate']['passed']}**.",
        "",
        "Sześć wariantów i warunki wyboru zamrożono przed treningiem. Historyczna walidacja S02 była już wcześniej oglądana; to etap rozwojowy, nie nowy niezależny test. Test końcowy nie został odczytany do oceny.",
        "",
        "## Dane i cechy",
        "",
        f"5814 rzeczywistych ofert treningowych, 3114 gospodarzy. Rozbudowano kontrakt z 18 do {len(ENGINEERED_FEATURES)} cech. Dodano mniejszy obszar miasta, 13 flag udogodnień, informację o wspólnej łazience, proporcje pojemności noclegu, odległość od stałego punktu referencyjnego (52.52, 13.405) i liczbę braków podstawowych cech.",
        "",
        "Punkt referencyjny nie jest deklaracją oficjalnego centrum. Odległość to odległość geograficzna, nie czas dojazdu. Dla studia liczba sypialni=0 daje mianownik 1 w proporcji gości; brak pozostaje brakiem. Brak metrażu nie został uzupełniony zmyślonymi wartościami. Nie użyto cen jako cech, tekstów, zdjęć, opinii ani target encodingu.",
        "",
        "## Co oznaczają sztuczne dane",
        "",
        "Dodatkowy rekord jest niepełną wersją prawdziwej oferty, z ukrytymi około 25% flag udogodnień. Nie zmieniamy ceny, współrzędnych ani liczby pokoi. To trening odporności na brak informacji i zwiększenie wagi rzadkich cen, a nie nowe obserwacje rynku. Każdy rekord ma parent_listing_id, host_id, is_augmented, rodzaj przekształcenia i listę ukrytych pól.",
        "",
        "Dla pełnego train powstały 263 dodatkowe wersje z brakami oraz osobny zbiór kontrolny z 263 dokładnymi powtórzeniami drogich ofert. Warianty mają po 6077 wierszy, ale nadal tylko 5814 oryginalnych obserwacji. W CV augmentacja wykonywana osobno PO podziale gospodarzy i wyłącznie z części dopasowania. Wszystkie oceniane rekordy są prawdziwe. Żadne sztuczne rekordy nie trafiają do publicznego katalogu.",
        "",
        "## Grupowana walidacja krzyżowa",
        "",
        "Każda z 5814 rzeczywistych ofert jest oceniana raz poza grupą dopasowania. Wynik służy wyborowi modelu, więc nie jest bezstronną oceną wybranego zwycięzcy.",
        "",
        "| Wariant | MAE wszystkie | MAE do 400 EUR | MAE ponad 400 EUR |",
        "| --- | ---: | ---: | ---: |",
    ]
    for name, value in report["cv"].items():
        lines.append(
            f"| {NAMES[name]} | {value['all']['mae_eur']:.2f} | {value['up_to_400']['mae_eur']:.2f} | {value['over_400']['mae_eur']:.2f} |"
        )
    lines += [
        "",
        "![Porównanie CV](comparison.png)",
        "",
        "## Walidacja wyłącznie wcześniej wybranego kandydata",
        "",
        "1108 prawdziwych ofert, 680 gospodarzy; 61 ofert ma cenę ponad 400 EUR. Najpierw zapisano wybór CV do pliku, dopiero potem załadowano validation. Pozostałych kandydatów nie oceniano na validation. Nie wybieramy drugiego kandydata po odrzuceniu pierwszego.",
        "",
        "| Wariant | MAE wszystkie | Mediana błędu | RMSE | MAE do 400 EUR | MAE ponad 400 EUR |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, value in report["validation"].items():
        lines.append(
            f"| {NAMES[name]} | {value['all']['mae_eur']:.2f} | {value['all']['median_absolute_error_eur']:.2f} | {value['all']['rmse_eur']:.2f} | {value['up_to_400']['mae_eur']:.2f} | {value['over_400']['mae_eur']:.2f} |"
        )
    lines += [
        "",
        "## Kryteria i ograniczenia",
        "",
        "Kandydat musi na CV nie pogorszyć MAE ogólnego ani MAE drogich ofert, ograniczyć pogorszenie dla tańszych do 3%, spełnić limity RMSE/mediany błędu i poprawić MAE ogólne co najmniej o 3% lub drogich ofert o 10%. Spośród spełniających warunki wygrywa najniższe MAE ogólne. Bramka validation wymaga m.in. co najmniej 5% poprawy drogich ofert i nie więcej niż 2% pogorszenia MAE ogólnego. Szczegóły: [protokół](../../configs/s02b_protocol.json) i [pełne wyniki](comparison.json).",
        "",
        "Sztuczna wersja nie dostarcza niezależnej informacji o nowej cenie. Powtarzanie może zwiększyć przeuczenie i pogorszyć zwykłe oferty; dlatego ocena pozostaje na naturalnym rozkładzie prawdziwych danych. Nie jest to badanie skuteczności wszystkich metod syntetyzacji: badamy konkretną maskowaną augmentację oraz kontrolne powtórzenia.",
        "",
        "Cena to historyczna cena ofertowa, nie cena transakcji ani dowód jakości. Segment >400 EUR nie oznacza automatycznie luksusu. Podział gospodarzy ogranicza przeciek, ale nie gwarantuje generalizacji w czasie. Nie generujemy przedziałów pewności ani obietnic okazji. Zachowano skrajne ceny. Wyniki próby hotel/shared pozostają mało pewne.",
        "",
        "Dotychczasowy endpoint S02 i jego pliki pozostają zachowane. Artefakt kandydata jest gotowy do integracji w S03, jeśli przeszedł bramkę. Formularz musi dostarczać zgodne nowe cechy lub jawne braki; nie może zamieniać nieznanych udogodnień na brak.",
        "",
        "## Odtwarzanie",
        "",
        "```powershell",
        ".\\.venv\\Scripts\\python.exe scripts/run_s02b.py",
        "```",
        "",
        "Runner odmawia nadpisania katalogów artefaktów i raportów. Dla powtórzenia podaj nowe --output, --report-dir i --prepared-dir. Źródło i stare wyniki S02 są przypięte hashami; kontrola powtórzyła zapisane przewidywania S02. Wersje, protokół, kod, pochodzenie augmentacji i wybór zapisane w manifestach.",
        "",
        "Metodyka: [oddzielanie resamplingu od oceny](https://imbalanced-learn.org/stable/common_pitfalls.html), [parametry modelu](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html). Zasada podziału ma zastosowanie także tutaj; nie używamy SMOTE klasyfikacyjnego do cen i nie instalujemy imbalanced-learn.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/s02b-v1")
    parser.add_argument("--report-dir", type=Path, default=ROOT / "reports/s02b")
    parser.add_argument("--prepared-dir", type=Path, default=ROOT / "data/prepared/s02b-v1")
    args = parser.parse_args()
    config_path = ROOT / "configs/s02b_protocol.json"
    protocol = json.loads(config_path.read_text(encoding="utf-8"))
    base_path = ROOT / "configs/s02_protocol.json"
    base = json.loads(base_path.read_text(encoding="utf-8"))
    assert protocol["source_sha256"] == SOURCE_SHA256
    assert protocol["feature_engineering"]["additional_amenities"] == EXTRA_AMENITIES
    assert protocol["feature_engineering"]["derived"] == DERIVED
    for path in [args.output, args.report_dir, args.prepared_dir]:
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite experiment output: {path}")
    for path in [args.output, args.report_dir, args.prepared_dir]:
        path.mkdir(parents=True)
    started = {
        "experiment_id": protocol["experiment_id"],
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_sha256": SOURCE_SHA256,
        "protocol_sha256": sha256(config_path),
        "base_protocol_sha256": sha256(base_path),
        "runner_sha256": sha256(Path(__file__)),
        "source_code_sha256": {
            p.relative_to(ROOT).as_posix(): sha256(p)
            for p in sorted((ROOT / "src/staylens").glob("*.py"))
        },
        "packages": {
            name: importlib.metadata.version(name)
            for name in ["numpy", "pandas", "scikit-learn", "scipy", "joblib", "threadpoolctl"]
        },
        "parent_prediction_sha256": {
            part: sha256(ROOT / f"artifacts/s02-v1/{part}_predictions.csv")
            for part in ["cv", "validation"]
        },
        "test_evaluated": False,
    }
    write_json(args.output / "run_started.json", started)
    write_json(args.output / "protocol.json", protocol)
    train = load_partition(ROOT / "data/raw/listings.csv.gz", "train")
    engineered = EngineerFeatures().transform(train)
    audit = {
        "scope": "train only",
        "real_rows": len(train),
        "hosts": int(train.host_id.nunique()),
        "features_before": len(FEATURES),
        "features_after": len(ENGINEERED_FEATURES),
        "feature_names": ENGINEERED_FEATURES,
        "missing_by_feature": engineered.isna().sum().astype(int).to_dict(),
        "extra_amenity_present_rows": train[EXTRA_AMENITIES].sum().astype(int).to_dict(),
        "categorical_cardinality": {
            key: int(engineered[key].nunique()) for key in ENGINEERED_CATEGORICAL
        },
        "tail_rows": int(train.price.gt(400).sum()),
        "test_evaluated": False,
    }
    write_json(args.report_dir / "feature_audit.json", audit)
    train.to_csv(args.prepared_dir / "real_train.csv", index=False)
    variants = {v["name"]: v for v in protocol["variants"]}
    cv = GroupKFold(**protocol["cv"])
    splits = list(cv.split(train, train.price, train.host_id))
    predictions = {name: np.full(len(train), np.nan) for name in variants}
    fold_assignment = np.zeros(len(train), dtype=int)
    fold_results = []
    for fold, (fit_index, score_index) in enumerate(splits, 1):
        fit_data, score_data = train.iloc[fit_index], train.iloc[score_index]
        heldout_hosts = set(score_data.host_id)
        assert not set(fit_data.host_id) & heldout_hosts
        fold_assignment[score_index] = fold
        fold_info = {
            "fold": fold,
            "fit_rows": len(fit_data),
            "score_real_rows": len(score_data),
            "host_overlap": 0,
            "variants": {},
        }
        for name, variant in variants.items():
            print(f"CV {fold}/3: {name}", flush=True)
            fit = augment_fit(
                fit_data,
                variant["augmentation"],
                protocol["augmentation"],
                protocol["augmentation"]["seed"] + fold,
                heldout_hosts,
            )
            model = make_variant(base, variant).fit(fit, fit.price.to_numpy())
            pred, clipped = predict(model, score_data, protocol["prediction_floor_eur"])
            predictions[name][score_index] = pred
            fold_info["variants"][name] = {
                "metrics": summary(score_data, pred),
                "augmentation": provenance(fit),
                "clipped_predictions": clipped,
            }
            if variant["augmentation"] != "none":
                fit.loc[
                    fit.is_augmented,
                    [
                        "listing_id",
                        "host_id",
                        "parent_listing_id",
                        "price",
                        "is_augmented",
                        "augmentation_kind",
                        "masked_features",
                    ],
                ].to_csv(args.output / f"fold{fold}_{name}_provenance.csv", index=False)
        fold_results.append(fold_info)
    original_cv = pd.read_csv(
        ROOT / "artifacts/s02-v1/cv_predictions.csv", dtype={"listing_id": str}
    )
    assert original_cv.listing_id.tolist() == train.listing_id.tolist()
    np.testing.assert_allclose(
        predictions["s02_control"], original_cv.hist_gradient_boosting, rtol=0, atol=1e-10
    )
    cv_metrics = {name: summary(train, pred) for name, pred in predictions.items()}
    selection = choose_cv(cv_metrics, protocol["cv_selection"])
    selection["locked_at_utc"] = datetime.now(timezone.utc).isoformat()
    write_json(args.output / "cv_selection.json", selection)
    output = train[["listing_id", "host_id", "price"]].copy()
    output["fold"] = fold_assignment
    for name, pred in predictions.items():
        output[name] = pred
    output.to_csv(args.output / "cv_predictions.csv", index=False)
    print("Locked CV winner: " + selection["winner"], flush=True)
    generated_audit = {}
    for mode in ["repeat", "masked"]:
        generated = augment_fit(
            train, mode, protocol["augmentation"], protocol["augmentation"]["seed"]
        )
        generated.to_csv(args.prepared_dir / f"train_{mode}.csv", index=False)
        generated_audit[mode] = provenance(generated)
    write_json(args.report_dir / "augmentation_audit.json", generated_audit)
    # Validation is first loaded AFTER candidate selection has been persisted.
    validation = load_partition(ROOT / "data/raw/listings.csv.gz", "validation")
    assert not set(train.host_id) & set(validation.host_id)
    val_predictions, train_scores, fitted_models = {}, {}, {}
    for name in dict.fromkeys(["s02_control", selection["winner"]]):
        print("Full fit and validation: " + name, flush=True)
        variant = variants[name]
        fit = augment_fit(
            train,
            variant["augmentation"],
            protocol["augmentation"],
            protocol["augmentation"]["seed"],
            set(validation.host_id),
        )
        model = make_variant(base, variant).fit(fit, fit.price.to_numpy())
        val_predictions[name], _ = predict(model, validation, protocol["prediction_floor_eur"])
        train_scores[name] = summary(
            train, predict(model, train, protocol["prediction_floor_eur"])[0]
        )
        path = args.output / f"{name}.joblib"
        joblib.dump(model, path, compress=3)
        restored = joblib.load(path)  # Trusted artifact generated above, never user input.
        np.testing.assert_array_equal(
            val_predictions[name],
            predict(restored, validation, protocol["prediction_floor_eur"])[0],
        )
        fitted_models[name] = model
    original_val = pd.read_csv(
        ROOT / "artifacts/s02-v1/validation_predictions.csv", dtype={"listing_id": str}
    )
    assert original_val.listing_id.tolist() == validation.listing_id.tolist()
    np.testing.assert_allclose(
        val_predictions["s02_control"], original_val.hist_gradient_boosting, rtol=0, atol=1e-10
    )
    val_metrics = {name: summary(validation, pred) for name, pred in val_predictions.items()}
    winner = selection["winner"]
    gate_checks = (
        eligibility(
            val_metrics[winner], val_metrics["s02_control"], protocol["validation_gate"], cv=False
        )
        if winner != "s02_control"
        else {"candidate_selected": False}
    )
    passed = all(gate_checks.values())
    recommended = winner if passed else "s02_control"
    val_output = validation[["listing_id", "host_id", "price"]].copy()
    for name, pred in val_predictions.items():
        val_output[name] = pred
    val_output.to_csv(args.output / "validation_predictions.csv", index=False)
    bootstrap = cluster_bootstrap(
        validation,
        {
            "segment_median": val_predictions["s02_control"],
            "hist_gradient_boosting": val_predictions[winner],
        },
        protocol["evaluation"]["bootstrap_host_replicates"],
        protocol["evaluation"]["bootstrap_seed"],
    )
    bootstrap["compared_models"] = ["s02_control", winner]
    segments = {}
    for key in ["district", "room_type"]:
        segments[key] = {}
        for category in sorted(validation[key].unique()):
            mask = validation[key].eq(category)
            segments[key][category] = {
                name: metrics(validation.price[mask], pred[mask])
                for name, pred in val_predictions.items()
            }
    reduced = validation[FEATURES].copy()
    reduced_input = summary(
        validation, predict(fitted_models[winner], reduced, protocol["prediction_floor_eur"])[0]
    )
    report = {
        **started,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "features": audit,
        "cv": cv_metrics,
        "cv_folds": fold_results,
        "cv_selection": selection,
        "validation": val_metrics,
        "validation_gate": {"passed": passed, "checks": gate_checks},
        "recommended_variant": recommended,
        "train_in_sample": train_scores,
        "augmentation": generated_audit,
        "validation_segments": segments,
        "bootstrap": bootstrap,
        "selected_candidate_with_new_fields_missing": reduced_input,
        "s02_control_matches_saved_predictions": True,
        "artifact_roundtrip_exact": True,
        "api_currently_serves": "s02-v1; integration deferred to S03",
    }
    manifest = {
        "model_version": "s02b-v1",
        "variant": recommended,
        "candidate": winner,
        "promotion_gate_passed": passed,
        "serving_contract": "s02b-research; explicit S03 API integration required",
        "model_file": f"{recommended}.joblib",
        "model_sha256": sha256(args.output / f"{recommended}.joblib"),
        "prediction_floor_eur": protocol["prediction_floor_eur"],
        "source_sha256": SOURCE_SHA256,
        "protocol_sha256": started["protocol_sha256"],
        "raw_input_features": RAW_FEATURES if recommended != "s02_control" else FEATURES,
        "model_features": ENGINEERED_FEATURES if recommended != "s02_control" else FEATURES,
        "snapshot": "2026-09-19",
        "currency": "EUR",
        "test_evaluated": False,
        "cv_metrics": cv_metrics[recommended],
        "validation_metrics": val_metrics[recommended],
        "packages": started["packages"],
        "augmentation": variants[recommended]["augmentation"],
        "real_train_rows": len(train),
        "real_validation_rows": len(validation),
    }
    write_json(args.output / "manifest.json", manifest)
    write_json(args.report_dir / "model_manifest.json", manifest)
    write_json(args.report_dir / "comparison.json", report)
    plot_comparison(cv_metrics, args.report_dir / "comparison.png")
    markdown_report(report, args.report_dir / "REPORT.md")
    print(
        json.dumps(
            {
                "cv": cv_metrics,
                "selection": selection,
                "validation": val_metrics,
                "gate": report["validation_gate"],
                "recommended": recommended,
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    with threadpool_limits(limits=2):
        main()
