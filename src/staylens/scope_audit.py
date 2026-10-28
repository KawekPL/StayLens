"""Conservative use-purpose flags. Never infer suitability from price or residuals."""

import csv
import gzip
import html
import re

from staylens.data import SOURCE_SHA256, host_split, sha256
from staylens.features import number

# Title-only matching avoids rejecting accommodation near an event venue or with
# house rules such as 'no parties / photoshoots'. A flag means review, not deletion.
TITLE_PATTERNS = {
    "event_venue": r"\b(?:event[ -]?space|event[ -]?location|veranstaltungsraum|veranstaltungslocation|seminarraum|meeting[ -]?room)\b",
    "photo_film_use": r"\b(?:for (?:a )?(?:photo[ -]?shoots?|filming)|f[üu]r (?:foto[ -]?shootings?|dreharbeiten)|foto[ -]?studio|photo[ -]?studio)\b",
}


def purpose_flags(title):
    text = html.unescape(title or "").casefold()
    return [key for key, pattern in TITLE_PATTERNS.items() if re.search(pattern, text)]


def load_scope(path, subset="train"):
    if subset not in {"train", "validation"}:
        raise ValueError("Final test is forbidden in this research stage")
    if sha256(path) != SOURCE_SHA256:
        raise ValueError("Source checksum mismatch")
    result = {}
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if not row.get("host_id") or host_split(row["host_id"]) != subset:
                continue
            price, lat, lon = (number(row.get(k)) for k in ["price", "latitude", "longitude"])
            if not (price > 0 and 52.3 < lat < 52.7 and 13.05 < lon < 13.8):
                continue
            result[row["id"]] = {
                "flags": purpose_flags(row.get("name")),
                "title": row.get("name", ""),
                "description": html.unescape(re.sub(r"<[^>]+>", " ", row.get("description", ""))),
            }
    return result
