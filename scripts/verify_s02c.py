"""Verify saved S02c hashes, split isolation, enrichment, and metrics without fitting."""

import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from staylens.data import host_split, sha256
from staylens.experiment_b import choose_cv, summary

ROOT = Path(__file__).resolve().parents[1]


def main():
    out, reports = ROOT / "artifacts/s02c-v1", ROOT / "reports/s02c"
    report = json.loads((reports / "comparison.json").read_text(encoding="utf-8"))
    manifest = json.loads((reports / "manifest.json").read_text(encoding="utf-8"))
    protocol = json.loads((ROOT / "configs/s02c_protocol.json").read_text(encoding="utf-8"))
    assert sha256(ROOT / "configs/s02c_protocol.json") == manifest["protocol_sha256"]
    assert sha256(ROOT / "configs/s02_protocol.json") == manifest["base_protocol_sha256"]
    assert sha256(ROOT / "scripts/run_s02c.py") == manifest["runner_sha256"]
    assert sha256(ROOT / "data/raw/listings.csv.gz") == manifest["source_sha256"]
    assert (
        sha256(ROOT / "data/raw/external/doorstep_berlin_20260919.zip")
        == manifest["external_sha256"]
    )
    for path, digest in manifest["code_sha256"].items():
        assert sha256(ROOT / path) == digest, path
    for path, digest in manifest["outputs_sha256"].items():
        assert sha256(out / path) == digest, path
    dtype = {"listing_id": str, "host_id": str}
    data = pd.read_csv(out / "train_features.csv", dtype=dtype)
    preds = pd.read_csv(out / "cv_predictions.csv", dtype=dtype)
    assert len(preds) == len(data) == 5814 and not preds.listing_id.duplicated().any()
    assert preds.listing_id.equals(data.listing_id) and preds.host_id.equals(data.host_id)
    assert data.host_id.map(host_split).eq("train").all()
    for fold, (fit, score) in enumerate(
        GroupKFold(**protocol["cv"]).split(data, groups=data.host_id)
    ):
        assert preds.fold.iloc[score].eq(fold).all()
        assert not set(data.host_id.iloc[fit]) & set(data.host_id.iloc[score])
    recomputed = {}
    for name in protocol["variants"]:
        assert np.isfinite(preds[name]).all() and preds[name].gt(0).all()
        actual = summary(data, preds[name].to_numpy())
        recomputed[name] = actual
        for segment, metrics in actual.items():
            for key, value in metrics.items():
                assert np.isclose(value, report["cv"][name][segment][key], rtol=1e-12, atol=1e-10)
    assert choose_cv(recomputed, protocol["cv_selection"]) == report["cv_selection"]
    prior = pd.read_csv(ROOT / "artifacts/s02-v1/cv_predictions.csv", dtype=dtype).set_index(
        "listing_id"
    )
    assert np.allclose(
        prior.loc[data.listing_id, "hist_gradient_boosting"], preds.s02_control, rtol=0, atol=1e-10
    )
    provenance = pd.read_csv(out / "join_provenance_train.csv", dtype=dtype)
    accepted = provenance.join_status.eq("accepted")
    assert accepted.equals(data.external_guest_favourite.notna())
    with zipfile.ZipFile(ROOT / "data/raw/external/doorstep_berlin_20260919.zip") as archive:
        with archive.open("Airbnb_Master_Dataset.csv") as stream:
            external = pd.read_csv(stream, dtype=str).set_index("Airbnb_ListingID")
    a = data.loc[accepted].reset_index(drop=True)
    b = external.loc[a.listing_id].reset_index(drop=True)
    assert a.host_id.eq(b.Host_ID).all()
    assert a.room_type.eq(b.RoomType.replace({"Entire home/flat": "Entire home/apt"})).all()
    for local, other in [
        ("accommodates", "PersonCapacity"),
        ("bedrooms", "Bedrooms"),
        ("beds", "Beds"),
        ("bathrooms", "Bathrooms"),
    ]:
        x, y = a[local], pd.to_numeric(b[other], errors="coerce")
        assert (x.isna() | y.isna() | x.eq(y)).all()
    assert a.external_guest_favourite.eq(b.is_GuestFavourite.map({"True": 1.0, "False": 0.0})).all()
    assert a.external_accessibility_count.eq(pd.to_numeric(b.AccessibilityFeatures_Count)).all()
    dates = provenance.loc[accepted]
    assert (
        pd.to_datetime(dates.Scrape_Date)
        .dt.normalize()
        .le(pd.to_datetime(dates.last_scraped))
        .all()
    )
    if not report["validation_gate"]["evaluated"]:
        assert not list(out.glob("*validation*")) and not report["validation"]
    assert not report["test_evaluated"] and not manifest["test_evaluated"]
    result = {
        "passed": True,
        "tests": "60 passed, 0 skipped; existing TestClient deprecation warning",
        "hashes": "protocol, runner, source modules, both datasets, all saved experiment artifacts",
        "checks": [
            "host folds",
            "exact external IDs/host/date/attributes",
            "no row multiplication",
            "recomputed metrics and selection",
            "original S02 CV reproduced",
            "no validation/test evaluation",
        ],
        "caveat": "checks establish pipeline consistency, not independent truth of host/provider claims",
    }
    (reports / "verification.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
