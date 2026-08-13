"""Schemas for the local/offline assistant API."""

from __future__ import annotations

from typing import Literal, cast
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from lung_xray_api.core.exceptions import ModelRuntimeError
from lung_xray_api.domain.probabilities import normalize_probabilities, predicted_label

ApplicationStage = Literal["before_analysis", "analysis_running", "after_analysis", "analysis_failed"]
ClassLabel = Literal["normal", "pneumonia", "tuberculosis"]
AssistantStatus = Literal[
    "answered",
    "needs_prediction",
    "needs_clarification",
    "out_of_scope",
    "medical_refusal",
]
AssistantRuntimeState = Literal[
    "disabled",
    "misconfigured",
    "configured_unverified",
    "online_verified",
    "degraded_offline",
]
AssistantFallbackReason = Literal[
    "temporary_online_failure",
    "circuit_open",
    "privacy_guard",
    "unsafe_online_response",
]


class PredictionContext(BaseModel):
    """Normalized model metadata that a later UI may provide after successful prediction."""

    model_config = ConfigDict(extra="forbid")

    predicted_label: ClassLabel
    probabilities: dict[str, float]
    model_version: str = Field(min_length=1, max_length=128)

    @field_validator("probabilities", mode="before")
    @classmethod
    def reject_non_numeric_probability_values(cls, value: object) -> object:
        if not isinstance(value, dict):
            raise ValueError("probabilities phải là object")
        if any(
            not isinstance(probability, (int, float))
            or isinstance(probability, bool)
            for probability in value.values()
        ):
            raise ValueError("probabilities phải là số")
        return value

    @model_validator(mode="after")
    def validate_probability_distribution(self) -> "PredictionContext":
        try:
            normalized = normalize_probabilities(self.probabilities)
        except ModelRuntimeError as error:
            message = str(error)
            if "finite" in message:
                message = "probabilities phải là số hữu hạn"
            elif "sum to one" in message:
                message = "tổng probabilities phải bằng 1 trong sai số cho phép"
            elif "inside [0, 1]" in message:
                message = "probabilities phải nằm trong [0, 1]"
            elif "contain normal" in message:
                message = "probabilities phải có đúng normal, pneumonia và tuberculosis"
            raise ValueError(message) from error
        self.probabilities = cast(dict[str, float], dict(normalized))
        if self.predicted_label != predicted_label(normalized):
            raise ValueError("predicted_label phải khớp class có xác suất cao nhất")
        return self



class AssistantQuery(BaseModel):
    """Offline query. Raw images and unspecified fields are rejected at this boundary."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=1500)
    application_stage: ApplicationStage = "before_analysis"
    prediction_context: PredictionContext | None = None

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("message không được chỉ gồm khoảng trắng")
        return normalized


class AssistantAnswer(BaseModel):
    """Controlled response from local rules and approved production Knowledge Base content."""

    status: AssistantStatus
    mode: Literal["offline", "online"] = "offline"
    provider: str = "local-retrieval"
    model: str | None = None
    fallback_used: bool = False
    fallback_reason: AssistantFallbackReason | None = None
    intent: str
    answer: str
    sources: list[str] = Field(default_factory=list)
    disclaimer: str
    suggested_questions: list[str] = Field(default_factory=list, max_length=3)
    confidence: float = Field(ge=0.0, le=1.0)
    request_id: str = Field(default_factory=lambda: str(uuid4()))


class AssistantRuntimeStatus(BaseModel):
    """Non-sensitive runtime status for the assistant UI."""

    configured: bool
    verified: bool
    state: AssistantRuntimeState
    fallback_available: bool
    online_enabled: bool
    online_available: bool
    active_mode: Literal["offline", "online"]
    provider: str
    model: str | None = None
    fallback_enabled: bool
