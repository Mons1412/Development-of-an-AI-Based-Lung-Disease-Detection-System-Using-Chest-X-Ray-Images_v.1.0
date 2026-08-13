"""Legacy report-preview input retained for backward compatibility."""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from lung_xray_api.domain.probabilities import normalize_probabilities, predicted_label

ClassLabel = Literal["normal", "pneumonia", "tuberculosis"]
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")
_UNSAFE_FILENAME_CHARACTERS = re.compile(r"[^\w.() -]+", flags=re.UNICODE)
_MODEL_VERSION_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"


class ReportPrediction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    predicted_label: ClassLabel
    probabilities: dict[ClassLabel, float]
    model_version: str = Field(min_length=1, max_length=128, pattern=_MODEL_VERSION_PATTERN)
    processing_time_ms: int = Field(ge=0)
    analysis_timestamp: datetime

    @field_validator("probabilities", mode="before")
    @classmethod
    def reject_non_numeric_probability_values(cls, value: object) -> object:
        if not isinstance(value, dict):
            raise ValueError("probabilities phải là object")
        if any(
            not isinstance(probability, (int, float)) or isinstance(probability, bool)
            for probability in value.values()
        ):
            raise ValueError("probabilities phải là số")
        return value

    @field_validator("processing_time_ms", mode="before")
    @classmethod
    def require_integer_processing_time(cls, value: object) -> object:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("processing_time_ms phải là số nguyên")
        return value

    @model_validator(mode="after")
    def validate_prediction_distribution(self) -> "ReportPrediction":
        normalized = normalize_probabilities(
            cast(Mapping[str, float], self.probabilities)
        )
        self.probabilities = normalized
        if self.predicted_label != predicted_label(normalized):
            raise ValueError("predicted_label phải khớp class có xác suất cao nhất")
        if self.analysis_timestamp.tzinfo is None:
            raise ValueError("analysis_timestamp phải có timezone")
        return self


class ReportPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str = Field(min_length=1, max_length=255)
    prediction: ReportPrediction

    @field_validator("filename", mode="before")
    @classmethod
    def sanitize_filename(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("filename phải là chuỗi")
        basename = value.replace("\\", "/").split("/")[-1]
        without_controls = _CONTROL_CHARACTERS.sub("", basename)
        sanitized = _UNSAFE_FILENAME_CHARACTERS.sub("_", without_controls)
        sanitized = re.sub(r"\s+", " ", sanitized).strip(" .")
        if not sanitized:
            raise ValueError("filename không chứa ký tự hợp lệ")
        return sanitized
