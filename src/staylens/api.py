"""Offline-trained price model API. Local trusted artifacts only; no online fitting."""

import importlib.metadata
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Literal

import joblib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from threadpoolctl import threadpool_limits

from staylens.data import sha256
from staylens.features import AMENITIES, CATEGORICAL, FEATURES, NUMERIC, feature_frame
from staylens.models import predict_prices

DEFAULT_ARTIFACT = Path(__file__).resolve().parents[2] / "artifacts" / "s02-v1"


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


class PriceResponse(BaseModel):
    estimated_price_eur: float
    currency: Literal["EUR"] = "EUR"
    unit: Literal["night"] = "night"
    model_version: str
    model_name: str
    snapshot: str
    development_mae_eur: float
    warnings: list[str]
    explanation: str


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


def create_app(artifact_dir=None):
    directory = Path(artifact_dir or os.environ.get("STAYLENS_ARTIFACT_DIR", DEFAULT_ARTIFACT))

    @asynccontextmanager
    async def lifespan(app):
        app.state.model, app.state.manifest = load_artifact(directory)
        with threadpool_limits(limits=2):
            yield

    app = FastAPI(title="StayLens price API", version="0.2.0", lifespan=lifespan)

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
        return {key: app.state.manifest[key] for key in fields}

    @app.get("/api/schema")
    def schema():
        return {
            "input": PriceRequest.model_json_schema(),
            "training_categories": app.state.manifest["categories"],
            "training_numeric_ranges": app.state.manifest["numeric_ranges"],
            "amenities": AMENITIES,
            "missing_value_rule": "null = unknown; false = declared absent; true = declared present",
            "unknown_category_rule": "Unknown district rejected; unknown property type accepted with warning and treated as missing",
        }

    @app.post("/api/predict", response_model=PriceResponse)
    def predict(request: PriceRequest):
        manifest = app.state.manifest
        if request.district not in manifest["categories"]["district"]:
            raise HTTPException(422, "Unknown Berlin district; use /api/schema")
        values = request.model_dump()
        warnings = []
        missing = [key for key in NUMERIC if values[key] is None]
        if missing:
            warnings.append(
                "Brak części cech: " + ", ".join(missing) + ". Oszacowanie wymaga ostrożności."
            )
        for key in CATEGORICAL:
            count = manifest["categories"][key].get(values[key], 0)
            if count < 50:
                warnings.append(f"Mało przykładów dla {key}={values[key]}: {count} w treningu.")
        for key, bounds in manifest["numeric_ranges"].items():
            value = values[key]
            if value is not None and not bounds["min"] <= value <= bounds["max"]:
                warnings.append(
                    f"{key} poza zakresem danych treningowych; model nie gwarantuje ekstrapolacji."
                )
        predicted = float(predict_prices(app.state.model, feature_frame([values]))[0])
        return PriceResponse(
            estimated_price_eur=round(predicted, 2),
            model_version=manifest["model_version"],
            model_name=manifest["selected_model"],
            snapshot=manifest["snapshot"],
            development_mae_eur=round(manifest["validation_metrics"]["mae_eur"], 2),
            warnings=warnings,
            explanation="Cena ofertowa za noc dla historycznego Berlina. Błąd walidacyjny dotyczy całego zbioru, nie jest przedziałem pewności tej oferty. Brak informacji o terminie i dostępności.",
        )

    return app


app = create_app()
