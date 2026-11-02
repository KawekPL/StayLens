"""Independently recalculate metrics from saved final predictions; never call fit/predict."""

import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

from staylens.data import host_split, sha256

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main():
    report = json.loads((ROOT / "reports/s05/test_evaluation.json").read_text())
    saved = ROOT / "artifacts/s05-final/test_predictions.csv"
    if sha256(saved) != report["predictions_sha256"]:
        raise ValueError("Predictions changed")
    rows = pd.read_csv(saved, dtype={"host_id": str, "listing_id": str})
    assert len(rows) == 1235 and rows.host_id.nunique() == 624
    assert all(rows.host_id.map(host_split) == "test")
    assert rows.listing_id.is_unique
    for split in ["cv", "validation"]:
        other = pd.read_csv(ROOT / f"artifacts/s02-v1/{split}_predictions.csv", dtype=str)
        assert not set(rows.host_id) & set(other.host_id)
        assert not set(rows.listing_id) & set(other.listing_id)
    for name, expected in report["model_hashes"].items():
        assert sha256(ROOT / f"artifacts/s02-v1/{name}.joblib") == expected
        residuals = np.abs(rows.price - rows[name]).to_numpy()
        computed = {
            "rows": len(rows),
            "mae_eur": np.mean(residuals),
            "median_absolute_error_eur": np.median(residuals),
            "rmse_eur": np.sqrt(np.mean(residuals**2)),
            "within_20_percent": np.mean(residuals / rows.price <= 0.2),
            "within_30_eur": np.mean(residuals <= 30),
            "p90_absolute_error_eur": np.percentile(residuals, 90),
        }
        for metric, result in computed.items():
            assert np.isclose(result, report["test_metrics"][name][metric], rtol=1e-12)
    assert sha256(ROOT / "configs/s05_final_protocol.json") == report["protocol_sha256"]
    assert sha256(ROOT / "scripts/run_final_evaluation.py") == report["runner_sha256"]
    integrity = json.loads((ROOT / "artifacts/s05-final/artifact_integrity.json").read_text())
    assert integrity["before"] == integrity["after"]
    verification = {
        "all_six_metrics_independently_recomputed": True,
        "saved_predictions_checksum_matches": True,
        "test_rows": 1235,
        "test_hosts": 624,
        "no_host_or_listing_overlap": True,
        "original_models_and_artifacts_unchanged": True,
        "protocol_and_runner_unchanged": True,
        "no_training_or_new_predictions_in_verification": True,
    }
    (ROOT / "reports/s05/verification.json").write_text(json.dumps(verification, indent=2) + "\n")
    names = ["segment_median", "hist_gradient_boosting"]
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.6))
    for ax, metric, title in zip(
        axes,
        ["mae_eur", "median_absolute_error_eur", "rmse_eur"],
        ["Średni błąd (MAE)", "Mediana błędu", "RMSE"],
        strict=True,
    ):
        values = [report["test_metrics"][name][metric] for name in names]
        bars = ax.bar(["Mediana segmentu", "Model S02"], values, color=["#a4b4af", "#167466"])
        ax.bar_label(bars, labels=[f"{v:.2f} €" for v in values], padding=4)
        ax.set_ylim(0, max(values) * 1.22)
        ax.set_title(title)
        ax.set_ylabel("EUR za noc")
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("StayLens · test końcowy: 1235 ofert, 624 innych gospodarzy", fontsize=15)
    fig.text(
        0.5,
        0.025,
        "Berlin 19.09.2026 · ceny ofertowe · model bez zmian · niższy błąd = lepiej",
        ha="center",
    )
    fig.tight_layout(rect=(0, 0.07, 1, 0.94))
    fig.savefig(ROOT / "reports/s05/test_comparison.png", dpi=160)
    plt.close(fig)
    print(json.dumps(verification, indent=2))


if __name__ == "__main__":
    main()
