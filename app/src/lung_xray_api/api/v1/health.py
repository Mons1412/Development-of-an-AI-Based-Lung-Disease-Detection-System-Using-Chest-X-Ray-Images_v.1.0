"""Health endpoints."""

from fastapi import APIRouter, Request

from lung_xray_api.application.prediction_service import PredictionServiceProtocol
from lung_xray_api.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health/live")
def liveness() -> HealthResponse:
    return HealthResponse(status="ok", service="lung-xray-api")


@router.get("/health/ready")
def readiness(request: Request) -> HealthResponse:
    service: PredictionServiceProtocol | None = getattr(request.app.state, "prediction_service", None)
    if service is None:
        return HealthResponse(status="not_ready", service="lung-xray-api", model_ready=False)
    return HealthResponse(
        status="ready",
        service="lung-xray-api",
        model_ready=True,
        model_version=service.bundle.model_version,
    )
