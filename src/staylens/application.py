"""S03 application around the frozen S02 inference contract."""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Literal

from fastapi import HTTPException, Query

from staylens.api import PriceRequest, create_app
from staylens.catalog import filtered_page, load_catalog, locate_district

ROOT = Path(__file__).resolve().parents[2]


def create_application(artifact_dir=None, catalog_dir=None):
    app = create_app(artifact_dir)
    app.version = "0.3.0"
    original_lifespan = app.router.lifespan_context
    directory = Path(
        catalog_dir or os.environ.get("STAYLENS_CATALOG_DIR", ROOT / "data/prepared/s03")
    )

    @asynccontextmanager
    async def lifespan(application):
        async with original_lifespan(application):
            rows, meta, geo = load_catalog(directory, application.state.manifest)
            application.state.catalog = rows
            application.state.by_id = {r["id"]: r for r in rows}
            application.state.catalog_meta, application.state.geo = meta, geo
            yield

    app.router.lifespan_context = lifespan
    original_predict = next(
        route.endpoint for route in app.routes if getattr(route, "path", None) == "/api/predict"
    )

    @app.get("/api/catalog/meta")
    def meta():
        return app.state.catalog_meta

    @app.get("/api/catalog/listings")
    def listings(
        district: Annotated[str, Query(max_length=100)] = "",
        room_type: Literal[
            "", "Entire home/apt", "Private room", "Shared room", "Hotel room"
        ] = "Entire home/apt",
        guests: Annotated[int, Query(ge=1, le=16)] = 2,
        max_price: Annotated[float, Query(gt=0, le=20000, allow_inf_nan=False)] = 300,
        query: Annotated[str, Query(max_length=120)] = "",
        sort: Literal["reviewed", "price-asc", "price-desc"] = "reviewed",
        offset: Annotated[int, Query(ge=0, le=10000)] = 0,
        limit: Annotated[int, Query(ge=1, le=60)] = 12,
    ):
        if district and district not in app.state.catalog_meta["districts"]:
            raise HTTPException(422, "Wybierz dzielnicę Berlina z listy.")
        return filtered_page(
            app.state.catalog,
            district=district,
            room_type=room_type,
            guests=guests,
            max_price=max_price,
            query=query,
            sort=sort,
            offset=offset,
            limit=limit,
        )

    @app.get("/api/catalog/compare")
    def compare(ids: Annotated[list[str], Query(min_length=1, max_length=3)]):
        if len(set(ids)) != len(ids) or any(i not in app.state.by_id for i in ids):
            raise HTTPException(422, "Wybierz od jednej do trzech różnych ofert z katalogu.")
        return {"items": [app.state.by_id[i] for i in ids]}

    @app.get("/api/catalog/listings/{listing_id}")
    def detail(listing_id: str):
        if listing_id not in app.state.by_id:
            raise HTTPException(404, "Nie znaleziono oferty w katalogu.")
        return app.state.by_id[listing_id]

    @app.get("/api/location")
    def location(
        latitude: Annotated[float, Query(gt=52.3, lt=52.7, allow_inf_nan=False)],
        longitude: Annotated[float, Query(gt=13.05, lt=13.8, allow_inf_nan=False)],
    ):
        district = locate_district(app.state.geo, latitude, longitude)
        if not district:
            raise HTTPException(422, "Wskaż punkt wewnątrz granic Berlina.")
        return {"district": district}

    @app.post("/api/estimate")
    def estimate(request: PriceRequest):
        district = locate_district(app.state.geo, request.latitude, request.longitude)
        if district is None or district != request.district:
            raise HTTPException(
                422, "Dzielnica nie odpowiada lokalizacji. Wskaż punkt na mapie ponownie."
            )
        allowed = app.state.catalog_meta["propertyTypesByRoom"][request.room_type]
        if request.property_type not in allowed:
            raise HTTPException(422, "Wybierz typ obiektu pasujący do rodzaju noclegu.")
        result = original_predict(request).model_dump()
        # Keep full warnings in the frozen API; the UI endpoint uses actionable Polish copy.
        warnings = []
        if any(value is None for value in request.model_dump().values()):
            warnings.append(
                "Część parametrów jest nieznana. Model uwzględnia braki, ale wynik wymaga większej ostrożności."
            )
        if request.room_type in {"Hotel room", "Shared room"}:
            warnings.append(
                "Bardzo mała próba oceny: 8 pokoi hotelowych i 4 współdzielone. Wynik dla tego rodzaju noclegu jest mniej pewny."
            )
        if app.state.manifest["categories"]["property_type"].get(request.property_type, 0) < 50:
            warnings.append(
                "Ten typ obiektu jest rzadki w danych treningowych. Traktuj wynik orientacyjnie."
            )
        for field, bounds in app.state.manifest["numeric_ranges"].items():
            value = getattr(request, field)
            if value is not None and not bounds["min"] <= value <= bounds["max"]:
                warnings.append(
                    "Niektóre parametry wykraczają poza obserwacje treningowe. Model może słabo odzwierciedlać taki nocleg."
                )
                break
        result["warnings"] = warnings
        result["method"] = "full_train"
        return result

    return app


app = create_application()
