"""Single-process production entrypoint; the S02 model and contract remain frozen."""

import json
import logging
import os
import time
from pathlib import Path

from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware

from staylens.application import create_application

LOGGER = logging.getLogger("uvicorn.error")


def create_production_app(static_dir=None, artifact_dir=None, catalog_dir=None):
    directory = Path(static_dir or os.environ.get("STAYLENS_STATIC_DIR", "frontend/dist"))
    if not (directory / "index.html").is_file():
        raise RuntimeError("Built frontend is missing; run npm run build first")
    app = create_application(artifact_dir, catalog_dir)
    app.version = "0.5.0"
    evaluation = json.loads((directory / "final-evaluation.json").read_text(encoding="utf-8"))
    if (
        evaluation["model_sha256"]
        != "47ed42c9c8ccec4db103da7ec437ea240d5045191eaf20df9e9e4bd85265d7bf"
    ):
        raise ValueError("Final evaluation belongs to a different model")
    original_info = next(
        route.endpoint for route in app.routes if getattr(route, "path", None) == "/api/model"
    )
    app.router.routes = [
        route for route in app.router.routes if getattr(route, "path", None) != "/api/model"
    ]

    @app.get("/api/model")
    def final_model_info():
        # Preserve the historical artifact manifest; expose the later assessment separately.
        info = original_info()
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
            # No bodies, query strings, listing IDs, IP addresses or user text in logs.
            LOGGER.info(
                json.dumps(
                    {
                        "event": "http",
                        "route": route,
                        "status": response.status_code,
                        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                    },
                    ensure_ascii=True,
                )
            )
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
