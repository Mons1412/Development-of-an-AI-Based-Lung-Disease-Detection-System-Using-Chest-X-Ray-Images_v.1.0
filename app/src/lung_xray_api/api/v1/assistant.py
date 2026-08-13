"""Hybrid assistant endpoints with controlled Gemini and offline fallback."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool

from lung_xray_api.api.dependencies import get_assistant_service, require_api_key
from lung_xray_api.assistant.hybrid_service import HybridAssistantService
from lung_xray_api.schemas.assistant import (
    AssistantAnswer,
    AssistantQuery,
    AssistantRuntimeStatus,
)

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])


@router.get("/status", response_model=AssistantRuntimeStatus)
def assistant_status(
    service: Annotated[HybridAssistantService, Depends(get_assistant_service)],
    _authorized: Annotated[None, Depends(require_api_key)],
) -> AssistantRuntimeStatus:
    """Expose provider availability without exposing credentials."""

    return service.status()


@router.post("/query", response_model=AssistantAnswer)
async def query_assistant(
    payload: AssistantQuery,
    service: Annotated[HybridAssistantService, Depends(get_assistant_service)],
    _authorized: Annotated[None, Depends(require_api_key)],
) -> AssistantAnswer:
    """Use Gemini for approved explanations and local retrieval as the fallback."""

    return await run_in_threadpool(service.answer, payload)
