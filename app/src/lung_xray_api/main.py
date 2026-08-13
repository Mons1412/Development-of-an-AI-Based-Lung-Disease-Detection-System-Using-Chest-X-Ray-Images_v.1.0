"""FastAPI application factory cho Phase 02."""

from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from lung_xray_api.api.v1.router import router
from lung_xray_api.application.prediction_service import PredictionServiceProtocol
from lung_xray_api.core.config import Settings, load_settings
from lung_xray_api.core.exceptions import (
    ArtifactError,
    ImageValidationError,
    ModelRuntimeError,
    PersistenceError,
)
from lung_xray_api.core.lifespan import create_lifespan
from lung_xray_api.core.logging import configure_logging
from lung_xray_api.web.assets import FRONTEND_STATIC_BASE


def create_app(
    settings: Settings | None = None,
    prediction_service: PredictionServiceProtocol | None = None,
    load_model: bool = True,
) -> FastAPI:
    settings = settings or load_settings()
    configure_logging(settings.log_level)
    app = FastAPI(
        title="Lung X-ray AI Inference API",
        version="1.2.0",
        lifespan=create_lifespan(settings, prediction_service, load_model=load_model),
    )
    app.include_router(router)

    static_dir = Path(__file__).resolve().parent / "web" / "static"
    app.mount(
        FRONTEND_STATIC_BASE,
        StaticFiles(directory=static_dir),
        name="frontend-versioned-static",
    )
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.middleware("http")
    async def response_headers(request: Request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path.startswith(("/api/v1/analyses", "/api/v1/report", "/api/v1/assistant")):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"
        elif path == "/demo":
            response.headers["Cache-Control"] = (
                "public, max-age=0, must-revalidate"
                if settings.app_env == "production"
                else "no-store"
            )
        elif path.startswith("/static/"):
            if settings.app_env != "production":
                response.headers["Cache-Control"] = "no-store"
            elif path.startswith(f"{FRONTEND_STATIC_BASE}/"):
                response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            else:
                response.headers["Cache-Control"] = "public, max-age=0, must-revalidate"
        return response

    @app.get("/")
    def root() -> dict[str, str]:
        return {
            "service": "lung-xray-api",
            "version": "1.2.0",
            "status": "running",
        }

    @app.exception_handler(ImageValidationError)
    async def image_validation_handler(
        request: Request,
        exc: ImageValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"status": "error", "code": "invalid_image", "message": str(exc)},
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """Do not reflect patient/case values embedded in FastAPI validation errors."""

        safe_details = [
            {
                "loc": list(error.get("loc", ())),
                "msg": "Invalid request data",
                "type": str(error.get("type", "value_error")),
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": safe_details},
        )

    @app.exception_handler(PersistenceError)
    async def persistence_handler(request: Request, exc: PersistenceError) -> JSONResponse:
        """Persistence failures are observable without exposing SQLite or file details."""

        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "error",
                "code": "analysis_storage_unavailable",
                "message": "Local analysis storage is temporarily unavailable",
            },
        )

    @app.exception_handler(ArtifactError)
    @app.exception_handler(ModelRuntimeError)
    async def runtime_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "error", "code": "model_not_ready", "message": str(exc)},
        )

    return app


app = create_app()
