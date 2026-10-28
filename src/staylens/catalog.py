"""Read-only S03 catalogue. Public rows are allowlisted and contain host-held-out estimates."""

import json
from statistics import median

from pydantic import BaseModel, ConfigDict, Field

from staylens.data import sha256


class StrictRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Estimate(StrictRecord):
    estimatedPrice: float = Field(gt=0)
    deltaPercent: float
    method: str
    modelVersion: str
    warnings: list[str]


class Reference(StrictRecord):
    median: float | None
    n: int


class Listing(StrictRecord):
    id: str
    title: str
    district: str
    neighbourhood: str
    lat: float
    lon: float
    price: float = Field(gt=0)
    roomType: str
    guests: float
    bedrooms: float | None
    beds: float | None
    bathrooms: float | None
    rating: float | None
    reviews: float
    minNights: float | None
    image: str
    url: str
    model: Estimate
    reference: Reference


def load_catalog(directory, model_manifest):
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    path = directory / "catalog.json"
    if sha256(path) != manifest["catalog_sha256"]:
        raise ValueError("Catalog checksum mismatch")
    if manifest["model_sha256"] != model_manifest["model_sha256"]:
        raise ValueError("Catalog/model mismatch")
    if manifest["source_sha256"] != model_manifest["source_sha256"]:
        raise ValueError("Catalog/source mismatch")
    content = json.loads(path.read_text(encoding="utf-8"))
    rows = [Listing.model_validate(row).model_dump() for row in content["listings"]]
    if len(rows) != model_manifest["training_rows"] or len({row["id"] for row in rows}) != len(
        rows
    ):
        raise ValueError("Unexpected catalog size or duplicate IDs")
    for row in rows:
        if (
            row["model"]["method"] != "host_oof"
            or row["model"]["modelVersion"] != model_manifest["model_version"]
        ):
            raise ValueError("Catalog predictions must be host-held-out S02 estimates")
    geo_path = directory / "neighbourhoods.geojson"
    if sha256(geo_path) != manifest["geo_sha256"]:
        raise ValueError("Geographic checksum mismatch")
    return rows, content["meta"], json.loads(geo_path.read_text(encoding="utf-8"))


def filtered_page(
    rows,
    *,
    district="",
    room_type="",
    guests=2,
    max_price=300,
    query="",
    sort="reviewed",
    offset=0,
    limit=12,
):
    search = query.strip().casefold()
    result = [
        row
        for row in rows
        if (not district or row["district"] == district)
        and (not room_type or row["roomType"] == room_type)
        and row["guests"] >= guests
        and row["price"] <= max_price
        and (
            not search
            or search in f"{row['title']} {row['district']} {row['neighbourhood']}".casefold()
        )
    ]
    keys = {
        "reviewed": lambda r: (-r["reviews"], -(r["rating"] or 0), r["id"]),
        "price-asc": lambda r: (r["price"], r["id"]),
        "price-desc": lambda r: (-r["price"], r["id"]),
    }
    result.sort(key=keys[sort])
    prices = [row["price"] for row in result]
    bins = []
    if prices:
        low, high = min(prices), max(prices)
        step = (high - low or 1) / 18
        bins = [{"start": low + i * step, "count": 0} for i in range(18)]
        for value in prices:
            bins[min(17, int((value - low) / step))]["count"] += 1
    return {
        "items": result[offset : offset + limit],
        "total": len(result),
        "offset": offset,
        "limit": limit,
        "hasMore": offset + limit < len(result),
        "mapItems": result[:60],
        "summary": {
            "median": median(prices) if prices else None,
            "min": min(prices) if prices else None,
            "histogram": bins,
        },
    }


def ring_contains(ring, x, y):
    """Ray casting, including ring edges. Coordinates are lon/lat, not lat/lon."""
    inside = False
    for (ax, ay), (bx, by) in zip(ring, ring[1:] + ring[:1], strict=True):
        cross = (x - ax) * (by - ay) - (y - ay) * (bx - ax)
        if (
            abs(cross) < 1e-12
            and min(ax, bx) <= x <= max(ax, bx)
            and min(ay, by) <= y <= max(ay, by)
        ):
            return True
        if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
            inside = not inside
    return inside


def locate_district(geo, latitude, longitude):
    for feature in geo["features"]:
        geometry = feature["geometry"]
        polygons = (
            geometry["coordinates"]
            if geometry["type"] == "MultiPolygon"
            else [geometry["coordinates"]]
        )
        for polygon in polygons:
            if ring_contains(polygon[0], longitude, latitude) and not any(
                ring_contains(hole, longitude, latitude) for hole in polygon[1:]
            ):
                return feature["properties"]["neighbourhood_group"]
    return None
