"""FastAPI dependencies that resolve application services from app.state."""

from __future__ import annotations

from ipaddress import ip_address
from typing import Annotated

from fastapi import Header, HTTPException, Request, status

from lung_xray_api.application.analysis_history_service import AnalysisHistoryService
from lung_xray_api.application.knowledge_metadata import KnowledgeMetadata
from lung_xray_api.application.prediction_service import PredictionServiceProtocol
from lung_xray_api.assistant.hybrid_service import HybridAssistantService
from lung_xray_api.core.config import Settings
from lung_xray_api.core.security import is_authorized


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def require_api_key(
    request: Request,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    if not is_authorized(get_settings(request), x_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key không hợp lệ",
        )


def get_prediction_service(request: Request) -> PredictionServiceProtocol:
    service = getattr(request.app.state, "prediction_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model service chưa ready",
        )
    return service


def get_assistant_service(request: Request) -> HybridAssistantService:
    service = getattr(request.app.state, "assistant_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Assistant service chưa sẵn sàng",
        )
    return service


def get_analysis_history_service(request: Request) -> AnalysisHistoryService:
    service = getattr(request.app.state, "analysis_history_service", None)
    if service is None or not getattr(request.app.state, "history_ready", False):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Local analysis history is unavailable",
        )
    return service


def get_knowledge_metadata(request: Request) -> KnowledgeMetadata:
    metadata = getattr(request.app.state, "knowledge_metadata", None)
    if isinstance(metadata, KnowledgeMetadata):
        return metadata
    return KnowledgeMetadata(version=None, source_titles={})


def get_production_knowledge_base_version(request: Request) -> str | None:
    """Compatibility dependency; persistence no longer requires assistant startup."""

    return get_knowledge_metadata(request).version


def require_local_history_access(request: Request) -> None:
    """Contain patient metadata to local clients until an account model exists."""

    settings = get_settings(request)
    configured_host = settings.host.strip().lower().strip("[]")
    if configured_host not in {"127.0.0.1", "::1", "localhost"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Local history API is available only on a loopback host",
        )

    client_host = request.client.host if request.client is not None else ""
    if settings.app_env == "test" and client_host == "testclient":
        return
    try:
        if not ip_address(client_host).is_loopback:
            raise ValueError
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Local history API accepts loopback clients only",
        ) from error
