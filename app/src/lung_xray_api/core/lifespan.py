"""Composition root và lifecycle cho FastAPI app.

Lifespan tạo model runtime đúng một lần, đưa `prediction_service` vào
`app.state`, và cleanup runtime khi shutdown. Endpoint không tự tạo model trong
request.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from typing import AsyncIterator

from fastapi import FastAPI

from lung_xray_api.assistant.knowledge_base import KnowledgeBaseError
from lung_xray_api.assistant.gemini_provider import GeminiProvider
from lung_xray_api.assistant.hybrid_service import HybridAssistantService, OfflineAssistant
from lung_xray_api.assistant.online_provider import OnlineAIConfigurationError
from lung_xray_api.assistant.service import AssistantService
from lung_xray_api.application.analysis_history_service import AnalysisHistoryService
from lung_xray_api.application.knowledge_metadata import KnowledgeMetadataProvider
from lung_xray_api.application.prediction_service import PredictionService, PredictionServiceProtocol
from lung_xray_api.core.config import Settings
from lung_xray_api.core.exceptions import PersistenceError
from lung_xray_api.infrastructure.ml.artifact_bundle import ArtifactBundle
from lung_xray_api.infrastructure.ml.image_preprocessor import ImagePreprocessor
from lung_xray_api.infrastructure.ml.image_validator import ImageValidator
from lung_xray_api.infrastructure.ml.model_runtime import ModelRuntime
from lung_xray_api.infrastructure.ml.predictor import Predictor

logger = logging.getLogger(__name__)


def build_prediction_service(settings: Settings, warm_up: bool = True) -> tuple[PredictionService, ModelRuntime]:
    bundle = ArtifactBundle.load(settings.artifact_dir, verify_checksum=True)
    runtime = ModelRuntime(bundle)
    runtime.load(warm_up=warm_up)
    service = PredictionService(
        bundle=bundle,
        validator=ImageValidator(settings.max_upload_bytes),
        preprocessor=ImagePreprocessor(bundle),
        predictor=Predictor(bundle, runtime),
    )
    return service, runtime


def build_assistant_service(settings: Settings) -> AssistantService:
    """Build the local assistant once at startup from the production KB path."""

    if settings.knowledge_base_path is None:
        raise KnowledgeBaseError("Thiếu đường dẫn production Knowledge Base")
    return AssistantService.from_settings(settings)


def build_hybrid_assistant_service(
    settings: Settings,
    offline_service: OfflineAssistant,
) -> HybridAssistantService:
    """Add Gemini only when enabled and correctly configured."""

    provider = None
    if settings.online_ai_enabled:
        if not settings.gemini_api_key:
            logger.warning(
                "ONLINE_AI_ENABLED=true but GEMINI_API_KEY is missing; using offline assistant"
            )
        elif not settings.gemini_model:
            logger.warning(
                "ONLINE_AI_ENABLED=true but GEMINI_MODEL is missing; using offline assistant"
            )
        else:
            try:
                provider = GeminiProvider(
                    api_key=settings.gemini_api_key.get_secret_value(),
                    model_name=settings.gemini_model,
                    timeout_seconds=settings.online_ai_timeout_seconds,
                    temperature=settings.online_ai_temperature,
                    max_answer_characters=settings.online_ai_max_answer_characters,
                )
            except OnlineAIConfigurationError:
                logger.warning("Gemini provider disabled due to configuration or dependency error")

    return HybridAssistantService(
        offline_service=offline_service,
        online_provider=provider,
        online_enabled=settings.online_ai_enabled,
        fallback_enabled=settings.ai_offline_fallback_enabled,
    )


def build_analysis_history_service(settings: Settings) -> AnalysisHistoryService:
    """Initialize the local history store without coupling it to inference."""

    if settings.history_db_path is None or settings.thumbnail_dir is None:
        raise PersistenceError("Thiếu cấu hình SQLite analysis history hoặc thumbnail")
    return AnalysisHistoryService.from_settings(settings)


def create_lifespan(
    settings: Settings,
    prediction_service: PredictionServiceProtocol | None = None,
    load_model: bool = True,
):
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        runtime: ModelRuntime | None = None
        if prediction_service is not None:
            app.state.prediction_service = prediction_service
            app.state.model_ready = True
        elif load_model:
            service, runtime = build_prediction_service(settings)
            app.state.prediction_service = service
            app.state.model_ready = True
        else:
            app.state.prediction_service = None
            app.state.model_ready = False

        app.state.settings = settings
        app.state.knowledge_metadata = KnowledgeMetadataProvider(
            settings.knowledge_base_path
        ).load()
        try:
            offline_assistant = build_assistant_service(settings)
            app.state.assistant_service = build_hybrid_assistant_service(
                settings,
                offline_assistant,
            )
        except KnowledgeBaseError as error:
            # The assistant is optional for Phase 02 inference availability. The
            # endpoint returns 503 while all prediction endpoints keep running.
            logger.warning("Offline assistant disabled because production KB is unavailable: %s", error)
            app.state.assistant_service = None
        try:
            app.state.analysis_history_service = build_analysis_history_service(settings)
            app.state.history_ready = True
        except (PersistenceError, ValueError) as error:
            # History is not yet part of the prediction request path. Keep the
            # established API available while exposing the failed foundation in
            # application state for later, explicit history work.
            logger.error("Local analysis history is unavailable: %s", error)
            app.state.analysis_history_service = None
            app.state.history_ready = False
        try:
            yield
        finally:
            assistant_service = getattr(app.state, "assistant_service", None)
            if assistant_service is not None:
                assistant_service.close()
            if runtime is not None:
                runtime.close()

    return lifespan
