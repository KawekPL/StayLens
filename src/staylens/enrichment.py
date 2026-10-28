"""S02c: conservative declared areas and an audited, exact-ID external join.

These research features do not change the deployed S02 contract. Text is data,
never instructions. Unknown/ambiguous information remains missing.
"""

import csv
import gzip
import html
import re
import zipfile

import numpy as np
import pandas as pd

from staylens.data import SOURCE_SHA256, host_split, sha256
from staylens.engineering import load_partition

EXTERNAL_SHA256 = "02ad47102440ca7094613c4568b905dd52eaef4446f501adfdb7686e98809dc9"
AREA_FEATURES = ["declared_entire_area_m2", "declared_room_area_m2"]
QUALITY_FEATURES = ["external_guest_favourite", "external_accessibility_count"]
AREA = re.compile(
    r"(?<![\d.,])\b(\d{1,4}(?:[.,]\d{1,2})?)\s*"
    r"(m[²2]|qm\b|sq\.?\s*m\b|sqm\b|square\s*met(?:re|er)s?\b|"
    r"square\s*feet\b|sq\.?\s*ft\b|ft[²2])",
    re.I,
)
NOUNS = {
    "entire": re.compile(
        r"\b(?:apartments?|appartments?|apartment|flat|studio|loft|penthouse|wohnung|"
        r"wohnfläche|living space|living area|accommodation)\b",
        re.I,
    ),
    "room": re.compile(r"\b(?:rooms?|bedrooms?|zimmer|schlafzimmer)\b", re.I),
    "outdoor": re.compile(
        r"\b(?:garden|garten|terrace|terrasse|balcony|balkon|patio|pool|plot|grundstück)\b",
        re.I,
    ),
}


def area_from_text(name, description, room_type):
    """Return explicit, scope-matched host claims plus auditable local evidence.

    No learned parser and no target-dependent rules. Ranges, conflicting values,
    outdoor areas and shared-room listings are deliberately not filled.
    """
    accepted = {"entire": [], "room": []}
    evidence = []
    expected = {"Entire home/apt": "entire", "Private room": "room", "Hotel room": "room"}.get(
        room_type
    )
    for field, raw in [("name", name), ("description", description)]:
        text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", " ", raw or "")))
        for match in AREA.finditer(text):
            value = float(match[1].replace(",", "."))
            imperial = "feet" in match[2].lower() or "ft" in match[2].lower()
            value *= 0.09290304 if imperial else 1
            start, end = match.span()
            before, after = text[max(0, start - 60) : start], text[end : end + 60]
            snippet = before + match[0] + after
            reason, scope = "no_explicit_scope", None
            # Units may be present only on the second number of a range.
            ranged = bool(
                re.search(
                    r"\d\s*(?:qm|m[²2]|sqm)?\s*(?:[-–—+]|to|and|bis)\s*$",
                    before,
                    re.I,
                )
            )
            ranged |= bool(re.match(r"\s*(?:[-–—+]|to|bis)\s*\d", after, re.I))
            if ranged:
                reason = "range_or_sum"
            elif not expected:
                reason = "unsupported_room_type"
            elif not 8 <= value <= (1000 if expected == "entire" else 150):
                reason = "outside_scope_bounds"
            else:
                labels = []
                for label, pattern in NOUNS.items():
                    for noun in pattern.finditer(text[max(0, start - 60) : end + 60]):
                        a, b = noun.start() + max(0, start - 60), noun.end() + max(0, start - 60)
                        distance = max(start - b, a - end, 0)
                        if distance <= 35:
                            labels.append((distance, label))
                if labels:
                    scope = sorted(labels)[0][1]
                elif field == "name" and expected == "entire":
                    scope = "entire"
                if scope == expected:
                    reason = "accepted_candidate"
                    accepted[scope].append((value, imperial))
                elif scope:
                    reason = "different_scope"
            evidence.append(
                {
                    "field": field,
                    "value_m2": value,
                    "scope": scope,
                    "reason": reason,
                    "snippet": snippet,
                }
            )
    output = dict.fromkeys(AREA_FEATURES, np.nan)
    for scope, values in accepted.items():
        if not values:
            continue
        numbers = [v[0] for v in values]
        # Small unit-conversion/rounding discrepancy allowed; retain an observed value.
        consistent = max(numbers) - min(numbers) <= max(1, 0.03 * np.median(numbers))
        if consistent:
            output[f"declared_{scope}_area_m2"] = sorted(values, key=lambda v: v[1])[0][0]
        else:
            for item in evidence:
                if item["scope"] == scope and item["reason"] == "accepted_candidate":
                    item["reason"] = "conflicting_area_claims"
    return output, evidence


def load_texts(path, subset, ids):
    if subset not in {"train", "validation"}:
        raise ValueError("Final test is prohibited")
    if sha256(path) != SOURCE_SHA256:
        raise ValueError("Source checksum mismatch")
    selected = set(ids)
    rows = []
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            # Do not inspect held-out text before the split filter.
            if not row.get("host_id") or host_split(row["host_id"]) != subset:
                continue
            if row["id"] in selected:
                rows.append({k: row[k] for k in ["id", "name", "description", "last_scraped"]})
    return pd.DataFrame(rows).rename(columns={"id": "listing_id"})


def read_external(path):
    if sha256(path) != EXTERNAL_SHA256:
        raise ValueError("External source checksum mismatch")
    with zipfile.ZipFile(path) as archive:
        with archive.open("Airbnb_Master_Dataset.csv") as stream:
            data = pd.read_csv(stream, dtype=str)
    if data.Airbnb_ListingID.isna().any() or data.Airbnb_ListingID.duplicated().any():
        raise ValueError("Missing or duplicate external IDs")
    if not data.Country.eq("Germany").all() or not data.Location.eq("Berlin").all():
        raise ValueError("Unexpected geography")
    return data


def join_external(base, external):
    """One row stays one row. No fuzzy IDs, coordinate matching, or target features."""
    joined = base.merge(
        external,
        left_on="listing_id",
        right_on="Airbnb_ListingID",
        how="left",
        validate="one_to_one",
        sort=False,
    )
    status = pd.Series("accepted", index=joined.index)
    checks = {
        "no_exact_id": joined.Airbnb_ListingID.isna(),
        "host_mismatch": joined.host_id.ne(joined.Host_ID),
        "room_type_mismatch": joined.room_type.ne(
            joined.RoomType.replace({"Entire home/flat": "Entire home/apt"})
        ),
    }
    observed = pd.to_datetime(joined.Scrape_Date, errors="coerce").dt.normalize()
    target_date = pd.to_datetime(joined.last_scraped, errors="coerce").dt.normalize()
    checks["date_missing_or_future"] = (
        observed.isna() | target_date.isna() | observed.gt(target_date)
    )
    # Known contradictions trigger quarantine, even if one upstream field is buggy.
    for local, other in [
        ("accommodates", "PersonCapacity"),
        ("bedrooms", "Bedrooms"),
        ("beds", "Beds"),
        ("bathrooms", "Bathrooms"),
    ]:
        a, b = (
            pd.to_numeric(joined[local], errors="coerce"),
            pd.to_numeric(joined[other], errors="coerce"),
        )
        checks[f"{local}_conflict"] = a.notna() & b.notna() & a.ne(b)
    for reason, mask in checks.items():
        status.loc[status.eq("accepted") & mask] = reason
    good = status.eq("accepted")
    features = pd.DataFrame(index=base.index)
    features[QUALITY_FEATURES[0]] = joined.is_GuestFavourite.map({"True": 1.0, "False": 0.0}).where(
        good
    )
    count = pd.to_numeric(joined.AccessibilityFeatures_Count, errors="coerce")
    features[QUALITY_FEATURES[1]] = count.where(good & count.between(0, 100) & count.mod(1).eq(0))
    audit = {
        "base_rows": len(base),
        "external_rows": len(external),
        "exact_id_matches": int(joined.Airbnb_ListingID.notna().sum()),
        "exclusive_status_counts": {str(k): int(v) for k, v in status.value_counts().items()},
        "accepted": int(good.sum()),
        "known_features": {c: int(features[c].notna().sum()) for c in QUALITY_FEATURES},
        "no_extra_training_rows": len(joined) == len(base),
        "date_granularity": "calendar day; intraday order unknown",
    }
    provenance = joined[["listing_id", "host_id", "Scrape_Date", "last_scraped"]].copy()
    provenance["join_status"] = status
    return features, audit, provenance


def enriched_partition(source, external_path, subset):
    base = load_partition(source, subset)
    texts = load_texts(source, subset, base.listing_id)
    base = base.merge(texts, on="listing_id", validate="one_to_one", sort=False)
    extracted, evidence = [], []
    for row in base.itertuples(index=False):
        features, claims = area_from_text(row.name, row.description, row.room_type)
        extracted.append(features)
        for claim in claims:
            evidence.append({"listing_id": row.listing_id, **claim})
    area = pd.DataFrame(extracted)
    quality, audit, provenance = join_external(base, read_external(external_path))
    base = pd.concat(
        [base.drop(columns=["name", "description", "last_scraped"]), area, quality], axis=1
    )
    audit["area_known"] = {c: int(area[c].notna().sum()) for c in AREA_FEATURES}
    audit["area_any"] = int(area.notna().any(axis=1).sum())
    audit["area_provenance"] = "existing Inside Airbnb host descriptions, not external measurements"
    return base, audit, pd.DataFrame(evidence), provenance
