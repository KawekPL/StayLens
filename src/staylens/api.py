"""Serwer aplikacji: katalog ofert, wycena modelem i pliki frontendu."""

import importlib.metadata
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Literal

import joblib
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.gzip import GZipMiddleware
from threadpoolctl import threadpool_limits

from staylens.catalog import filtered_page, load_catalog, locate_district
from staylens.data import sha256
from staylens.features import FEATURES, feature_frame
from staylens.models import predict_prices

ROOT = Path(__file__).resolve().parents[2]
LOGGER = logging.getLogger("uvicorn.error")


class PriceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    district: Annotated[str, Field(min_length=1, max_length=100)]
    room_type: Literal["Entire home/apt", "Private room", "Shared room", "Hotel room"]
    property_type: Annotated[str, Field(min_length=1, max_length=100)]
    latitude: Annotated[float, Field(gt=52.3, lt=52.7)]
    longitude: Annotated[float, Field(gt=13.05, lt=13.8)]
    accommodates: Annotated[int, Field(ge=1, le=16)]
    bedrooms: Annotated[float | None, Field(ge=0, le=50)] = None
    beds: Annotated[float | None, Field(ge=0, le=100)] = None
    bathrooms: Annotated[float | None, Field(ge=0, le=50)] = None
    minimum_nights: Annotated[int | None, Field(ge=1, le=3650)] = None
    wifi: bool | None = None
    kitchen: bool | None = None
    washer: bool | None = None
    air_conditioning: bool | None = None
    elevator: bool | None = None
    parking: bool | None = None
    workspace: bool | None = None
    self_check_in: bool | None = None


def load_artifact(directory):
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    filename = manifest["model_file"]
    if Path(filename).name != filename or not filename.endswith(".joblib"):
        raise ValueError("Invalid artifact filename")
    path = directory / filename
    if sha256(path) != manifest["model_sha256"]:
        raise ValueError("Model checksum mismatch")
    if manifest["features"] != FEATURES:
        raise ValueError("Feature contract mismatch")
    for package in ["scikit-learn", "numpy", "pandas", "joblib"]:
        if importlib.metadata.version(package) != manifest["packages"][package]:
            raise ValueError(f"Artifact runtime version mismatch: {package}")
    return joblib.load(path), manifest  # Never accept an artifact from an API caller.


def create_app(artifact_dir=None, catalog_dir=None, static_dir=None):
    model_directory = Path(
        artifact_dir or os.environ.get("STAYLENS_ARTIFACT_DIR", ROOT / "runtime/model")
    )
    catalog_directory = Path(
        catalog_dir or os.environ.get("STAYLENS_CATALOG_DIR", ROOT / "runtime/catalog")
    )
    directory = Path(static_dir or os.environ.get("STAYLENS_STATIC_DIR", ROOT / "frontend/dist"))
    if not (directory / "index.html").is_file():
        raise RuntimeError("Built frontend is missing; run npm run build first")
    evaluation = json.loads((directory / "final-evaluation.json").read_text(encoding="utf-8"))

    @asynccontextmanager
    async def lifespan(app):
        # Wczytujemy model i katalog raz, przy uruchamianiu serwera.
        app.state.model, app.state.manifest = load_artifact(model_directory)
        if evaluation["model_sha256"] != app.state.manifest["model_sha256"]:
            raise ValueError("Final evaluation belongs to a different model")
        rows, meta, geo = load_catalog(catalog_directory, app.state.manifest)
        app.state.catalog = rows
        app.state.catalog_meta = meta
        app.state.geo = geo
        with threadpool_limits(limits=2):
            yield

    app = FastAPI(title="StayLens", version="0.7.0", lifespan=lifespan)

    @app.get("/health")
    def health():
        return {"status": "ok", "model_version": app.state.manifest["model_version"]}

    @app.get("/api/model")
    def model_info():
        fields = [
            "model_version",
            "selected_model",
            "snapshot",
            "city",
            "currency",
            "target",
            "features",
            "training_rows",
            "validation_rows",
            "test_evaluated",
            "validation_metrics",
            "cv_metrics",
            "limitations",
        ]
        info = {key: app.state.manifest[key] for key in fields}
        return {
            **info,
            "test_evaluated": True,
            "final_evaluation": evaluation,
            "limitations": [
                value
                for value in info["limitations"]
                if not value.startswith("Not a final test result")
            ]
            + [
                "Final test covers other hosts in the same Berlin snapshot, not future or geographic drift"
            ],
        }

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
        values = request.model_dump()
        manifest = app.state.manifest
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
        # Formularz -> tabela z cechami -> gotowy model -> cena w EUR.
        predicted = predict_prices(app.state.model, feature_frame([values]))[0]
        return {
            "estimated_price_eur": round(float(predicted), 2),
            "currency": "EUR",
            "unit": "night",
            "model_version": manifest["model_version"],
            "model_name": manifest["selected_model"],
            "snapshot": manifest["snapshot"],
            "development_mae_eur": round(manifest["validation_metrics"]["mae_eur"], 2),
            "warnings": warnings,
            "explanation": "Cena ofertowa za noc dla historycznego Berlina. Błąd walidacyjny dotyczy całego zbioru, nie jest przedziałem pewności tej oferty. Brak informacji o terminie i dostępności.",
            "method": "full_train",
        }

    app.add_middleware(GZipMiddleware, minimum_size=1000)

    @app.middleware("http")
    async def response_metadata(request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if request.url.path.startswith("/assets/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            response.headers["Cache-Control"] = "no-cache"
        route = getattr(request.scope.get("route"), "path", "static_or_unknown")
        if request.url.path != "/health":
            # Logujemy czas i szablon adresu, bez treści formularza i parametrów URL.
            duration_ms = (time.perf_counter() - started) * 1000
            LOGGER.info("%s: HTTP %s, %.1f ms", route, response.status_code, duration_ms)
        return response

    @app.get("/api/release")
    def release():
        return {
            "revision": os.environ.get("STAYLENS_REVISION", "local"),
            "app_version": app.version,
            "model_version": "s02-v1",
        }

    # Only the compiled frontend is public. Model/catalogue directories are outside it.
    app.mount("/", StaticFiles(directory=directory, html=True), name="frontend")
    return app
