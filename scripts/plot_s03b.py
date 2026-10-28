"""Render saved experiment results, without training or selecting another model."""

import json
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LABELS = {
    "s02_control": "Obecny S02",
    "catboost_mae": "CatBoost · MAE",
    "catboost_log": "CatBoost · log ceny",
    "catboost_derived_mae": "CatBoost · cechy + MAE",
    "catboost_derived_log": "CatBoost · cechy + log",
    "catboost_scope_sensitivity": "CatBoost · filtr celu użycia",
    "extra_trees_log": "ExtraTrees · log ceny",
    "hgb_log": "HistBoost · log ceny",
    "catboost_fixed_blend": "Średnia dwóch CatBoost",
}


def main():
    report = json.loads((ROOT / "reports/s03b/comparison.json").read_text(encoding="utf-8"))
    names = ["s02_control", *report["selection"]["ranking"]]
    colors = ["#9baaa5"] + ["#19796b"] * (len(names) - 1)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.7), layout="constrained")
    fig.patch.set_facecolor("#f6f7f3")
    for ax, key, title, multiplier in zip(
        axes,
        ["mae_eur", "within_20_percent"],
        ["Średni błąd — mniej znaczy lepiej", "W granicy 20% ceny — więcej znaczy lepiej"],
        [1, 100],
        strict=True,
    ):
        values = [report["cv"][name]["all"][key] * multiplier for name in names]
        bars = ax.barh([LABELS[name] for name in names], values, color=colors)
        ax.bar_label(
            bars, labels=[f"{v:.2f} {'€' if multiplier == 1 else '%'}" for v in values], padding=5
        )
        ax.invert_yaxis()
        ax.set_xlim(0, max(values) * 1.21)
        ax.set_title(title, fontsize=11, pad=14)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle(
        "StayLens · 5814 tych samych ofert · walidacja grupowana po gospodarzach\nPorównanie rozwojowe; test końcowy nadal nieoceniany",
        fontsize=13,
    )
    fig.savefig(ROOT / "reports/s03b/comparison.png", dpi=160)
    plt.close(fig)
    curve = report["learning_curve"]
    fractions = sorted({row["host_fraction"] for row in curve["rows"]})
    fig, ax = plt.subplots(figsize=(8, 4.8), layout="constrained")
    for part, label, color in [
        ("train", "Błąd na własnym treningu", "#9baaa5"),
        ("score", "Błąd na innych gospodarzach", "#19796b"),
    ]:
        points = []
        for fraction in fractions:
            rows = [row for row in curve["rows"] if row["host_fraction"] == fraction]
            counts = [row["fit_rows"] if part == "train" else row["score_rows"] for row in rows]
            points.append(np.average([row[part]["mae_eur"] for row in rows], weights=counts))
        ax.plot(np.array(fractions) * 100, points, "o-", label=label, color=color, linewidth=2)
        for x, y in zip(np.array(fractions) * 100, points, strict=True):
            ax.annotate(f"{y:.1f}", (x, y), xytext=(0, 8), textcoords="offset points", ha="center")
    ax.set(
        xlabel="Udział gospodarzy części treningowej każdego podziału (%)",
        ylabel="MAE w EUR",
        title=f"Krzywa uczenia · {LABELS[curve['candidate']]}\nTe same grupy oceny; diagnostyka, bez strojenia po wyniku",
    )
    ax.legend(loc="best")
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(ROOT / "reports/s03b/learning_curve.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    main()
