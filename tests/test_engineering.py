import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from staylens.augmentation import augment_fit
from staylens.engineering import (
    ENGINEERED_FEATURES,
    MASKABLE,
    EngineerFeatures,
    extra_amenity_flags,
    load_partition,
)
from staylens.experiment_b import choose_cv

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = json.loads((ROOT / "configs/s02b_protocol.json").read_text(encoding="utf-8"))


def fixture_rows():
    return pd.DataFrame(
        [
            {
                "listing_id": "a",
                "host_id": "fit1",
                "split": "train",
                "price": 600.0,
                "latitude": 52.52,
                "longitude": 13.405,
                "accommodates": 2,
                "bedrooms": 0,
                "beds": 1,
                "bathrooms": 1,
                **dict.fromkeys(MASKABLE, 1.0),
            },
            {
                "listing_id": "b",
                "host_id": "fit2",
                "split": "train",
                "price": 100.0,
                "latitude": 52.53,
                "longitude": 13.405,
                "accommodates": 1,
                "bedrooms": 1,
                "beds": 1,
                "bathrooms": 1,
                **dict.fromkeys(MASKABLE, 0.0),
            },
        ]
    )


def test_semantic_amenity_parsing():
    flags = extra_amenity_flags(
        '["Hair dryer", "Pool table", "Pool view", "Fireplace guards", "Whirlpool refrigerator"]'
    )
    assert all(v == 0 for v in flags.values())
    positive = extra_amenity_flags(
        '["Free dryer – In unit", "Private pool", "Private patio or balcony", "Free driveway parking on premises – 1 space"]'
    )
    assert (
        positive["clothes_dryer"]
        == positive["swimming_pool"]
        == positive["private_outdoor_space"]
        == positive["free_onsite_parking"]
        == 1
    )
    assert np.isnan(extra_amenity_flags("")["sauna"])
    assert extra_amenity_flags("[]")["sauna"] == 0


def test_derived_features_are_finite_for_studios_and_drop_metadata():
    data = EngineerFeatures().transform(fixture_rows())
    assert data.loc[0, "guests_per_bedroom"] == 2
    assert data.loc[0, "reference_distance_km"] == pytest.approx(0)
    assert data.loc[1, "reference_distance_km"] == pytest.approx(1.112, abs=0.01)
    assert list(data) == ENGINEERED_FEATURES
    assert "price" not in data and "host_id" not in data and "is_augmented" not in data


@pytest.mark.parametrize("mode", ["repeat", "masked"])
def test_augmentation_preserves_parent_label_and_real_rows(mode):
    data = fixture_rows()
    result = augment_fit(data, mode, PROTOCOL["augmentation"], 42, ["heldout"])
    assert len(result) == 3
    pd.testing.assert_frame_equal(result.iloc[:2][data.columns], data)
    added = result[result.is_augmented].iloc[0]
    assert added.parent_listing_id == "a" and added.host_id == "fit1"
    assert added.price == 600 and added.latitude == data.iloc[0].latitude
    assert result.listing_id.is_unique
    if mode == "masked":
        assert len(added.masked_features.split(",")) >= 6
        assert added[MASKABLE].isna().sum() >= 6
    else:
        assert added.masked_features == ""


def test_reproducible_masking():
    a = augment_fit(fixture_rows(), "masked", PROTOCOL["augmentation"], 42)
    b = augment_fit(fixture_rows(), "masked", PROTOCOL["augmentation"], 42)
    pd.testing.assert_frame_equal(a, b)


def test_heldout_hosts_and_recursive_generation_are_rejected():
    with pytest.raises(ValueError, match="Held-out"):
        augment_fit(fixture_rows(), "masked", PROTOCOL["augmentation"], 42, ["fit1"])
    generated = augment_fit(fixture_rows(), "masked", PROTOCOL["augmentation"], 42)
    with pytest.raises(ValueError, match="recursively"):
        augment_fit(generated, "masked", PROTOCOL["augmentation"], 42)


@pytest.mark.parametrize("partition", ["validation", "test"])
def test_never_augment_validation_or_test(partition):
    data = fixture_rows()
    data["split"] = partition
    with pytest.raises(ValueError, match="training"):
        augment_fit(data, "masked", PROTOCOL["augmentation"], 42)


def test_loader_cannot_request_test_even_with_nonexistent_source():
    with pytest.raises(ValueError, match="never test"):
        load_partition(Path("nonexistent.csv.gz"), "test")


def test_selection_rejects_tail_gain_at_expense_of_common_offers():
    def score(overall, common, tail):
        return {
            "all": {"mae_eur": overall, "rmse_eur": 100, "median_absolute_error_eur": 20},
            "up_to_400": {"mae_eur": common},
            "over_400": {"mae_eur": tail},
        }

    values = {
        "s02_control": score(50, 30, 400),
        "bad": score(49, 40, 200),
        "good": score(47, 29, 390),
    }
    result = choose_cv(values, PROTOCOL["cv_selection"])
    assert result["winner"] == "good"
    assert not result["checks"]["bad"]["common_mae"]
