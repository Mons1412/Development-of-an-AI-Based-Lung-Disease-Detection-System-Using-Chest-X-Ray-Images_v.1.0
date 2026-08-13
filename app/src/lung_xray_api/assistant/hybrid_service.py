"""Safety-controlled Gemini orchestration with deterministic offline fallback."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import re
import threading
import time
from typing import Protocol
from uuid import uuid4

from lung_xray_api.assistant.online_provider import (
    ApprovedKnowledgeChunk,
    OnlineAIError,
    OnlineAIErrorCategory,
    OnlineAIProvider,
    OnlineAIRequest,
    OnlinePredictionContext,
)
from lung_xray_api.assistant.response_renderer import DISCLAIMER
from lung_xray_api.assistant.retriever import normalize_text
from lung_xray_api.assistant.service import AssistantResolution
from lung_xray_api.domain.probabilities import CLASS_ORDER
from lung_xray_api.schemas.assistant import (
    AssistantAnswer,
    AssistantFallbackReason,
    AssistantQuery,
    AssistantRuntimeState,
    AssistantRuntimeStatus,
)

logger = logging.getLogger(__name__)

_LOCAL_PROVIDER = "local-retrieval"
_PERSONAL_DATA_MARKERS = (
    "ten benh nhan",
    "ma benh nhan",
    "ma ca",
    "ho ten",
    "ngay sinh",
    "dia chi",
    "so dien thoai",
    "email cua",
    "cccd",
    "can cuoc",
    "patient name",
    "patient code",
    "medical record",
)
_UNSAFE_ONLINE_OUTPUT_PATTERNS = (
    re.compile(r"\b(?:chan doan|ket luan)(?: cua (?:ban|benh nhan))? la\b"),
    re.compile(r"\b(?:ban|benh nhan) (?:dang )?(?:bi|mac)\b"),
    re.compile(r"\b(?:hay|nen|can) (?:ke|uong|dung) thuoc\b"),
    re.compile(r"\blieu dung (?:la|nen la)\b"),
    re.compile(r"\buong \d+(?:[.,]\d+)? ?mg\b"),
    re.compile(r"\b(?:hay|nen|can) (?:ngung|doi) thuoc\b"),
    re.compile(r"\b(?:hay|nen|can) thay doi (?:dieu tri|phac do)\b"),
)
_SAFE_NEGATION_SUFFIXES = (
    "khong khang dinh",
    "khong co nghia la",
    "khong phai",
    "khong the ket luan",
    "khong duoc",
    "khong nen",
    "khong can",
)
_EMAIL_PATTERN = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
_PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?84|0)(?:[\s().-]?\d){8,10}(?!\d)")
_IDENTIFIER_PATTERN = re.compile(r"(?<!\d)\d{9}(?:\d{3})?(?!\d)")
_CONFIGURATION_ERROR_CATEGORIES = {
    "authentication",
    "permission",
    "invalid_model",
}
_SAFETY_INSTRUCTIONS = (
    "Không chẩn đoán hoặc khẳng định người bệnh mắc bệnh.",
    "Không kê thuốc, nêu liều hoặc đề nghị thay đổi điều trị.",
    "Không thay đổi nhãn hay xác suất MobileNetV2.",
    "Không tuyên bố đã xem ảnh; nhà cung cấp trực tuyến không nhận ảnh.",
    "Gọi các số là xác suất đầu ra của mô hình, không phải xác suất mắc bệnh.",
)


class OfflineAssistant(Protocol):
    """Resolution/render boundary shared by online and local response paths."""

    def resolve(self, query: AssistantQuery) -> AssistantResolution:
        ...

    def render(self, resolution: AssistantResolution) -> AssistantAnswer:
        ...


@dataclass(slots=True)
class _RuntimeHealth:
    configured: bool
    verified: bool = False
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    consecutive_failures: int = 0
    last_error_category: OnlineAIErrorCategory | None = None
    circuit_open_until: float = 0.0
    last_probe_started_at: float | None = None


class HybridAssistantService:
    """Resolve once, then use Gemini or render the same resolution offline."""

    def __init__(
        self,
        *,
        offline_service: OfflineAssistant,
        online_provider: OnlineAIProvider | None,
        online_enabled: bool,
        fallback_enabled: bool = True,
        probe_ttl_seconds: float = 60.0,
        circuit_failure_threshold: int = 3,
        circuit_cooldown_seconds: float = 30.0,
        background_probe: bool = True,
    ) -> None:
        self._offline_service = offline_service
        self._online_provider = online_provider
        self._online_enabled = online_enabled
        self._fallback_enabled = fallback_enabled
        self._probe_ttl_seconds = probe_ttl_seconds
        self._circuit_failure_threshold = circuit_failure_threshold
        self._circuit_cooldown_seconds = circuit_cooldown_seconds
        self._background_probe = background_probe
        self._health = _RuntimeHealth(configured=online_provider is not None)
        self._health_lock = threading.Lock()
        self._probe_future: Future[None] | None = None
        self._executor = (
            ThreadPoolExecutor(max_workers=1, thread_name_prefix="gemini-probe")
            if background_probe and online_provider is not None
            else None
        )

    def answer(self, query: AssistantQuery) -> AssistantAnswer:
        request_id = str(uuid4())
        resolution = self._offline_service.resolve(query)

        if not resolution.online_eligible:
            return self._offline_answer(resolution, request_id=request_id)
        if not self._online_enabled or self._online_provider is None:
            return self._offline_answer(resolution, request_id=request_id)
        if self._contains_personal_data(query.message):
            logger.info(
                "online_ai_withheld request_id=%s provider=%s model=%s "
                "attempt=0 latency_ms=0 error_category=privacy fallback_used=true",
                request_id,
                self._online_provider.provider_name,
                self._online_provider.model_name,
            )
            return self._offline_answer(
                resolution,
                request_id=request_id,
                fallback_used=True,
                fallback_reason="privacy_guard",
            )
        if not self._can_attempt_online():
            return self._offline_answer(
                resolution,
                request_id=request_id,
                fallback_used=True,
                fallback_reason="circuit_open",
            )

        provider_request = self._build_online_request(
            query,
            resolution,
            request_id=request_id,
        )
        try:
            online_answer = self._online_provider.generate(provider_request)
        except OnlineAIError as error:
            self._record_failure(error)
            logger.warning(
                "online_ai_fallback request_id=%s provider=%s model=%s "
                "attempt=2 latency_ms=0 error_category=%s fallback_used=true",
                request_id,
                self._online_provider.provider_name,
                self._online_provider.model_name,
                error.category,
            )
            return self._offline_answer(
                resolution,
                request_id=request_id,
                fallback_used=True,
                fallback_reason="temporary_online_failure",
            )

        if self._contains_unsafe_online_output(online_answer.answer):
            self._record_failure(
                OnlineAIError(
                    "Online response failed safety validation",
                    category="invalid_response",
                )
            )
            logger.warning(
                "online_ai_fallback request_id=%s provider=%s model=%s "
                "attempt=1 latency_ms=0 error_category=invalid_response fallback_used=true",
                request_id,
                online_answer.provider,
                online_answer.model,
            )
            return self._offline_answer(
                resolution,
                request_id=request_id,
                fallback_used=True,
                fallback_reason="unsafe_online_response",
            )

        self._record_success()
        return AssistantAnswer(
            status="answered",
            mode="online",
            provider=online_answer.provider,
            model=online_answer.model,
            fallback_used=False,
            fallback_reason=None,
            intent=resolution.intent,
            answer=online_answer.answer,
            sources=list(resolution.source_ids),
            disclaimer=DISCLAIMER,
            suggested_questions=list(resolution.suggested_questions),
            confidence=max(0.0, min(resolution.confidence, 1.0)),
            request_id=request_id,
        )

    def status(self) -> AssistantRuntimeStatus:
        """Return immediately and schedule at most one cached background probe."""

        status = self._status_snapshot()
        self._schedule_probe()
        return status

    def close(self) -> None:
        if self._executor is not None:
            self._executor.shutdown(wait=True, cancel_futures=True)
        if self._online_provider is not None:
            self._online_provider.close()

    def _status_snapshot(self) -> AssistantRuntimeStatus:
        with self._health_lock:
            state = self._state_locked()
            configured = self._health.configured
            verified = self._health.verified and state == "online_verified"
        provider = (
            self._online_provider.provider_name
            if self._online_provider is not None
            else ("gemini" if self._online_enabled else _LOCAL_PROVIDER)
        )
        model = (
            self._online_provider.model_name
            if self._online_provider is not None
            else None
        )
        return AssistantRuntimeStatus(
            configured=configured,
            verified=verified,
            state=state,
            fallback_available=self._fallback_enabled,
            online_enabled=self._online_enabled,
            online_available=verified,
            active_mode="online" if verified else "offline",
            provider=provider,
            model=model,
            fallback_enabled=self._fallback_enabled,
        )

    def _state_locked(self) -> AssistantRuntimeState:
        if not self._online_enabled:
            return "disabled"
        if not self._health.configured:
            return "misconfigured"
        latest_failure = (
            self._health.last_failure_at is not None
            and (
                self._health.last_success_at is None
                or self._health.last_failure_at > self._health.last_success_at
            )
        )
        if latest_failure and self._health.last_error_category in _CONFIGURATION_ERROR_CATEGORIES:
            return "misconfigured"
        if latest_failure:
            return "degraded_offline"
        if self._health.verified:
            return "online_verified"
        return "configured_unverified"

    def _schedule_probe(self) -> None:
        if self._executor is None or self._online_provider is None:
            return
        now = time.monotonic()
        with self._health_lock:
            if self._probe_future is not None and not self._probe_future.done():
                return
            if (
                self._health.last_probe_started_at is not None
                and now - self._health.last_probe_started_at < self._probe_ttl_seconds
            ):
                return
            if self._circuit_open_locked(now):
                return
            self._health.last_probe_started_at = now
            self._probe_future = self._executor.submit(self._run_probe)

    def _run_probe(self) -> None:
        if self._online_provider is None:
            return
        request_id = str(uuid4())
        try:
            self._online_provider.probe(request_id)
        except OnlineAIError as error:
            self._record_failure(error)
            return
        self._record_success()

    def _can_attempt_online(self) -> bool:
        with self._health_lock:
            return not self._circuit_open_locked(time.monotonic())

    def _circuit_open_locked(self, now: float) -> bool:
        if self._health.circuit_open_until <= 0:
            return False
        if now < self._health.circuit_open_until:
            return True
        self._health.circuit_open_until = 0.0
        return False

    def _record_success(self) -> None:
        with self._health_lock:
            self._health.verified = True
            self._health.last_success_at = datetime.now(timezone.utc)
            self._health.consecutive_failures = 0
            self._health.circuit_open_until = 0.0

    def _record_failure(self, error: OnlineAIError) -> None:
        with self._health_lock:
            self._health.last_failure_at = datetime.now(timezone.utc)
            self._health.last_error_category = error.category
            self._health.consecutive_failures += 1
            if (
                error.retryable
                and self._health.consecutive_failures >= self._circuit_failure_threshold
            ):
                self._health.circuit_open_until = (
                    time.monotonic() + self._circuit_cooldown_seconds
                )

    def _offline_answer(
        self,
        resolution: AssistantResolution,
        *,
        request_id: str,
        fallback_used: bool = False,
        fallback_reason: AssistantFallbackReason | None = None,
    ) -> AssistantAnswer:
        answer = self._offline_service.render(resolution)
        return answer.model_copy(
            update={
                "mode": "offline",
                "provider": _LOCAL_PROVIDER,
                "model": None,
                "fallback_used": fallback_used,
                "fallback_reason": fallback_reason,
                "request_id": request_id,
            }
        )

    @staticmethod
    def _build_online_request(
        query: AssistantQuery,
        resolution: AssistantResolution,
        *,
        request_id: str,
    ) -> OnlineAIRequest:
        context = resolution.prediction_context
        online_context = (
            OnlinePredictionContext(
                predicted_label=context.predicted_label,
                probabilities={
                    label: context.probabilities[label]
                    for label in CLASS_ORDER
                },
                model_version=context.model_version,
            )
            if context is not None
            else None
        )
        chunks = tuple(
            ApprovedKnowledgeChunk(
                item_id=item.id,
                title=item.title,
                content=item.answer_detailed,
                source_ids=item.source_ids,
            )
            for item in resolution.knowledge_items
        )
        return OnlineAIRequest(
            request_id=request_id,
            # Never send raw free text after routing; this makes identity leakage
            # impossible even when a name does not match the local PII heuristics.
            question=HybridAssistantService._canonical_question(query, resolution),
            intent=resolution.intent,
            prediction_context=online_context,
            knowledge_chunks=chunks,
            source_ids=resolution.source_ids,
            safety_instructions=_SAFETY_INSTRUCTIONS,
        )

    @staticmethod
    def _canonical_question(
        query: AssistantQuery,
        resolution: AssistantResolution,
    ) -> str:
        if resolution.intent == "explain_current_prediction":
            return "Giải thích kết quả phân loại hiện tại và các xác suất đầu ra của mô hình."
        if resolution.knowledge_items:
            item = resolution.knowledge_items[0]
            return item.sample_questions[0] if item.sample_questions else item.title
        return f"Trả lời intent học thuật đã xác định: {resolution.intent}."

    @staticmethod
    def _contains_personal_data(message: str) -> bool:
        normalized = normalize_text(message)
        return (
            any(marker in normalized for marker in _PERSONAL_DATA_MARKERS)
            or bool(_EMAIL_PATTERN.search(message))
            or bool(_PHONE_PATTERN.search(message))
            or bool(_IDENTIFIER_PATTERN.search(message))
        )

    @staticmethod
    def _contains_unsafe_online_output(answer: str) -> bool:
        normalized = normalize_text(answer)
        for pattern in _UNSAFE_ONLINE_OUTPUT_PATTERNS:
            for match in pattern.finditer(normalized):
                prefix = normalized[max(0, match.start() - 48) : match.start()].rstrip()
                if any(prefix.endswith(negation) for negation in _SAFE_NEGATION_SUFFIXES):
                    continue
                return True
        return False
