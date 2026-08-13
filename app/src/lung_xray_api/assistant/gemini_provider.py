"""Google Gemini provider using the official Google GenAI SDK."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from email.utils import parsedate_to_datetime
import logging
import random
import re
import threading
import time
from typing import Any

from lung_xray_api.assistant.gemini_prompt import SYSTEM_INSTRUCTION, build_gemini_input
from lung_xray_api.assistant.online_provider import (
    OnlineAIConfigurationError,
    OnlineAIError,
    OnlineAIErrorCategory,
    OnlineAIProvider,
    OnlineAIQuotaError,
    OnlineAIRequest,
    OnlineAIResponse,
    OnlineAITimeoutError,
)

logger = logging.getLogger(__name__)

_HTTP_STATUS_PATTERN = re.compile(r"(?<!\d)(400|401|403|404|408|429|500|502|503|504)(?!\d)")
_PROMPT_LEAK_MARKERS = (
    "system role",
    "additional safety instructions",
    "approved knowledge context",
    "response format",
)


class GeminiProvider(OnlineAIProvider):
    """Reusable Gemini client with bounded retry and safe error classification."""

    provider_name = "gemini"

    def __init__(
        self,
        *,
        api_key: str,
        model_name: str,
        timeout_seconds: float = 30.0,
        temperature: float | None = None,
        max_answer_characters: int = 6000,
        client: Any | None = None,
        sleep: Callable[[float], None] = time.sleep,
        random_value: Callable[[], float] = random.random,
    ) -> None:
        normalized_key = api_key.strip()
        if not normalized_key:
            raise OnlineAIConfigurationError(
                "GEMINI_API_KEY chưa được cấu hình",
                category="authentication",
            )
        if not model_name.strip():
            raise OnlineAIConfigurationError(
                "GEMINI_MODEL chưa được cấu hình",
                category="invalid_model",
            )
        if timeout_seconds <= 0:
            raise OnlineAIConfigurationError("ONLINE_AI_TIMEOUT_SECONDS phải lớn hơn 0")
        if temperature is not None and not 0 <= temperature <= 2:
            raise OnlineAIConfigurationError("ONLINE_AI_TEMPERATURE phải nằm trong [0, 2]")
        if max_answer_characters < 500:
            raise OnlineAIConfigurationError("ONLINE_AI_MAX_ANSWER_CHARACTERS quá nhỏ")

        self.model_name = model_name.strip()
        self._temperature = temperature
        self._max_answer_characters = max_answer_characters
        self._owns_client = client is None
        self._sleep = sleep
        self._random_value = random_value
        self._request_lock = threading.Lock()
        self._client: Any

        if client is not None:
            self._client = client
            return

        try:
            from google import genai
            from google.genai import types
        except ImportError as error:
            raise OnlineAIConfigurationError(
                'Thiếu dependency google-genai. Chạy: python -m pip install "google-genai==2.14.0"'
            ) from error

        self._client = genai.Client(
            api_key=normalized_key,
            http_options=types.HttpOptions(timeout=int(timeout_seconds * 1000)),
        )

    def generate(self, request: OnlineAIRequest) -> OnlineAIResponse:
        answer = self._request_text(request)
        return OnlineAIResponse(
            answer=answer,
            provider=self.provider_name,
            model=self.model_name,
        )

    def probe(self, request_id: str) -> None:
        """Perform one cached health request when the runtime asks for verification."""

        probe_request = OnlineAIRequest(
            request_id=request_id,
            question="Chỉ trả lời: Kết nối sẵn sàng.",
            intent="runtime_probe",
            prediction_context=None,
            knowledge_chunks=(),
            source_ids=(),
            safety_instructions=("Không thêm thông tin y khoa.",),
        )
        self._request_text(probe_request)

    def close(self) -> None:
        if not self._owns_client:
            return
        close = getattr(self._client, "close", None)
        if callable(close):
            close()

    def _request_text(self, request: OnlineAIRequest) -> str:
        generation_config = (
            {"temperature": self._temperature}
            if self._temperature is not None
            else None
        )
        kwargs: dict[str, object] = {
            "model": self.model_name,
            "store": False,
            "system_instruction": SYSTEM_INSTRUCTION,
            "input": build_gemini_input(request),
        }
        if generation_config is not None:
            kwargs["generation_config"] = generation_config

        interaction = self._execute_with_retry(request.request_id, kwargs)
        answer = self._extract_text(interaction).replace("\x00", "").strip()
        if not answer:
            raise OnlineAIError(
                "Gemini không trả về nội dung văn bản",
                category="invalid_response",
            )
        normalized_answer = answer.lower()
        if any(marker in normalized_answer for marker in _PROMPT_LEAK_MARKERS):
            raise OnlineAIError(
                "Gemini response failed output validation",
                category="invalid_response",
            )
        return self._truncate_text(answer)

    def _execute_with_retry(self, request_id: str, kwargs: dict[str, object]) -> Any:
        for attempt in (1, 2):
            started = time.perf_counter()
            try:
                with self._request_lock:
                    interactions: Any = self._client.interactions
                    interaction = interactions.create(**kwargs)
            except Exception as raw_error:  # SDK error types vary by transport.
                error = self._map_error(raw_error)
                latency_ms = round((time.perf_counter() - started) * 1000)
                logger.warning(
                    "online_ai_failure request_id=%s provider=%s model=%s attempt=%d "
                    "latency_ms=%d error_category=%s fallback_used=%s",
                    request_id,
                    self.provider_name,
                    self.model_name,
                    attempt,
                    latency_ms,
                    error.category,
                    attempt == 2 or not error.retryable,
                )
                if attempt == 2 or not error.retryable:
                    raise error from raw_error
                self._sleep(self._retry_delay(error))
                continue

            latency_ms = round((time.perf_counter() - started) * 1000)
            logger.info(
                "online_ai_success request_id=%s provider=%s model=%s attempt=%d "
                "latency_ms=%d error_category=none fallback_used=false",
                request_id,
                self.provider_name,
                self.model_name,
                attempt,
                latency_ms,
            )
            return interaction
        raise AssertionError("bounded retry loop exhausted")

    def _retry_delay(self, error: OnlineAIError) -> float:
        if error.retry_after_seconds is not None:
            return max(0.0, min(error.retry_after_seconds, 30.0))
        base_delay = 0.25
        return base_delay + (self._random_value() * base_delay)

    def _truncate_text(self, answer: str) -> str:
        if len(answer) <= self._max_answer_characters:
            return answer
        limit = self._max_answer_characters - 1
        truncated = answer[:limit]
        boundary = max(truncated.rfind(" "), truncated.rfind("\n"))
        if boundary >= limit // 2:
            truncated = truncated[:boundary]
        return f"{truncated.rstrip()}…"

    @staticmethod
    def _extract_text(interaction: Any) -> str:
        output_text = getattr(interaction, "output_text", None)
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        steps = getattr(interaction, "steps", None) or []
        if not steps:
            return ""
        last_step = steps[-1]
        content = getattr(last_step, "content", None) or []
        fragments: list[str] = []
        for item in content:
            value = getattr(item, "text", None)
            if isinstance(value, str):
                fragments.append(value)
        return "\n".join(fragments).strip()

    @classmethod
    def _map_error(cls, error: Exception) -> OnlineAIError:
        status_code = cls._status_code(error)
        message = str(error).lower()
        retry_after = cls._retry_after_seconds(error)

        if status_code == 401:
            return OnlineAIConfigurationError(
                "Gemini authentication failed",
                category="authentication",
            )
        if status_code == 403 or "permission_denied" in message:
            return OnlineAIConfigurationError(
                "Gemini permission denied",
                category="permission",
            )
        if status_code == 404:
            return OnlineAIConfigurationError(
                "Gemini model is unavailable",
                category="invalid_model",
            )
        if status_code == 429:
            category: OnlineAIErrorCategory = (
                "quota" if "quota" in message or "resource_exhausted" in message else "rate_limit"
            )
            return OnlineAIQuotaError(
                "Gemini quota or rate limit reached",
                category=category,
                retry_after_seconds=retry_after,
            )
        if status_code in {408, 504} or cls._is_timeout(error, message):
            timeout_error = OnlineAITimeoutError()
            timeout_error.retry_after_seconds = retry_after
            return timeout_error
        if status_code in {500, 502, 503}:
            return OnlineAIError(
                "Gemini service is temporarily unavailable",
                category="service_unavailable",
                retryable=True,
                retry_after_seconds=retry_after,
            )
        if cls._is_network_error(error, message):
            return OnlineAIError(
                "Gemini network connection failed",
                category="network",
                retryable=True,
                retry_after_seconds=retry_after,
            )
        if status_code == 400:
            return OnlineAIError(
                "Gemini rejected the request",
                category="invalid_response",
            )
        return OnlineAIError(
            "Gemini request failed",
            category="unknown",
        )

    @staticmethod
    def _status_code(error: Exception) -> int | None:
        for candidate in (
            getattr(error, "status_code", None),
            getattr(error, "code", None),
            getattr(getattr(error, "response", None), "status_code", None),
        ):
            if isinstance(candidate, int):
                return candidate
            if isinstance(candidate, str) and candidate.isdigit():
                return int(candidate)
        match = _HTTP_STATUS_PATTERN.search(str(error))
        return int(match.group(1)) if match else None

    @staticmethod
    def _is_timeout(error: Exception, message: str) -> bool:
        class_name = type(error).__name__.lower()
        return (
            isinstance(error, TimeoutError)
            or "timeout" in class_name
            or "timeout" in message
            or "deadline_exceeded" in message
        )

    @staticmethod
    def _is_network_error(error: Exception, message: str) -> bool:
        class_name = type(error).__name__.lower()
        return (
            isinstance(error, ConnectionError)
            or "connect" in class_name
            or "network" in class_name
            or "connection" in message
        )

    @staticmethod
    def _retry_after_seconds(error: Exception) -> float | None:
        response = getattr(error, "response", None)
        headers = getattr(response, "headers", None)
        if not isinstance(headers, Mapping):
            return None
        raw_value = headers.get("Retry-After") or headers.get("retry-after")
        if raw_value is None:
            return None
        try:
            return max(0.0, float(raw_value))
        except (TypeError, ValueError):
            try:
                retry_at = parsedate_to_datetime(str(raw_value))
                return max(0.0, retry_at.timestamp() - time.time())
            except (TypeError, ValueError, OverflowError):
                return None
