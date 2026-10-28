"""Training-only repeated or masked observations, with explicit parent provenance."""

import math

import numpy as np
import pandas as pd

from staylens.engineering import MASKABLE


def augment_fit(data, mode, settings, seed, forbidden_hosts=()):
    if mode not in {"none", "repeat", "masked"}:
        raise ValueError("Unknown augmentation mode")
    if not data["split"].eq("train").all():
        raise ValueError("Augmentation requires real training rows")
    if "is_augmented" in data and data.is_augmented.any():
        raise ValueError("Do not recursively augment generated observations")
    if set(data.host_id) & set(forbidden_hosts):
        raise ValueError("Held-out host passed to augmentation")
    real = data.copy().reset_index(drop=True)
    real["is_augmented"] = False
    real["augmentation_kind"] = "real"
    real["parent_listing_id"] = real.listing_id
    real["masked_features"] = ""
    if mode == "none":
        return real
    if settings["copies_per_tail_row"] != 1:
        raise ValueError("Frozen protocol permits exactly one added view per tail row")
    added = real[real.price > settings["tail_threshold_eur"]].copy()
    added["is_augmented"] = True
    added["augmentation_kind"] = mode
    added["listing_id"] = "aug:s02b:" + mode + ":" + str(seed) + ":" + added.parent_listing_id
    if mode == "masked":
        rng = np.random.default_rng(seed)
        for index in added.index:
            known = [key for key in MASKABLE if pd.notna(added.at[index, key])]
            count = min(
                len(known), max(1, math.ceil(len(known) * settings["masked_amenity_fraction"]))
            )
            chosen = rng.choice(known, size=count, replace=False).tolist()
            # Preserve logical consistency when removing general outdoor-space information.
            if "outdoor_space" in chosen and "private_outdoor_space" not in chosen:
                chosen.append("private_outdoor_space")
            added.loc[index, chosen] = np.nan
            added.at[index, "masked_features"] = ",".join(sorted(chosen))
    return pd.concat([real, added], ignore_index=True)
