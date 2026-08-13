"""Provider-neutral contracts for the optional online assistant."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from lung_xray_api.domain.probabilities import ClassLabel

OnlineAIErrorCategory = Literal[
    "authentication",
    "permission",
    "invalid_model",
    "quota",
    "rate_limit",
    "timeout",
    "network",
    "service_unavailable",
    "invalid_response",
    "unknown",
]


class OnlineAIError(RuntimeError):
    """Safe provider failure with machine-readable retry metadata."""

    def __init__(
        self,
        message: str = "Online AI request failed",
        *,
        category: OnlineAIErrorCategory = "unknown",
        retryable: bool = False,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(message)
        self.category: OnlineAIErrorCategory = category
        self.retryable: bool = retryable
        self.retry_after_seconds: float | None = retry_after_seconds


class OnlineAIConfigurationError(OnlineAIError):
    """Provider configuration or dependency is unavailable."""

    def __init__(self, message: str, *, category: OnlineAIErrorCategory = "unknown") -> None:
        super().__init__(message, category=category, retryable=False)


class OnlineAITimeoutError(OnlineAIError):
    """Provider did not respond within the configured timeout."""

    def __init__(self, message: str = "Online AI request timed out") -> None:
        super().__init__(message, category="timeout", retryable=True)


class OnlineAIQuotaError(OnlineAIError):
    """Provider quota or rate limit was reached."""

    def __init__(
        self,
        message: str = "Online AI quota or rate limit reached",
        *,
        category: Literal["quota", "rate_limit"] = "rate_limit",
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(
            message,
            category=category,
            retryable=True,
            retry_after_seconds=retry_after_seconds,
        )


@dataclass(frozen=True, slots=True)
class OnlinePredictionContext:
    """Prediction-only data approved to leave the local process."""

    predicted_label: ClassLabel
    probabilities: dict[ClassLabel, float]
    model_version: str


@dataclass(frozen=True, slots=True)
class ApprovedKnowledgeChunk:
    """Production Knowledge Base content selected for one resolved intent."""

    item_id: str
    title: str
    content: str
    source_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OnlineAIRequest:
    """Only non-identifying, approved context may cross this boundary."""

    request_id: str
    question: str
    intent: str
    prediction_context: OnlinePredictionContext | None
    knowledge_chunks: tuple[ApprovedKnowledgeChunk, ...]
    source_ids: tuple[str, ...]
    safety_instructions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OnlineAIResponse:
    answer: str
    provider: str
    model: str


class OnlineAIProvider(Protocol):
    """One reusable provider/client created and closed by application lifespan."""

    provider_name: str
    model_name: str

    def generate(self, request: OnlineAIRequest) -> OnlineAIResponse:
        ...

    def probe(self, request_id: str) -> None:
        ...

    def close(self) -> None:
        ...
