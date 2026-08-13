"""Validated contract for persisted local analysis history."""

from __future__ import annotations

from datetime import date, datetime, timezone
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from lung_xray_api.domain.probabilities import normalize_probabilities, predicted_label
from lung_xray_api.schemas.case_metadata import (
    normalize_patient_code,
    normalize_patient_display_name,
)

PatientNameSource = Literal["filename", "manual", "anonymous"]
PredictedLabel = Literal["normal", "pneumonia", "tuberculosis"]
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")
_UNSAFE_FILENAME_CHARACTERS = re.compile(r"[^\w.() -]+", flags=re.UNICODE)
_SOURCE_ID_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._-]{1,127}$")


class AnalysisHistoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patient_code: str | None = Field(default=None, max_length=32)
    patient_display_name: str | None = Field(default=None, max_length=80)
    patient_name_source: PatientNameSource
    patient_info_confirmed: bool
    is_anonymous_sample: bool
    filename_pattern_id: str | None = Field(default=None, max_length=128)
    parsed_filename_date: date | None = None
    original_filename: str = Field(min_length=1, max_length=255)
    predicted_label: PredictedLabel
    normal_probability: float = Field(ge=0.0, le=1.0)
    pneumonia_probability: float = Field(ge=0.0, le=1.0)
    tuberculosis_probability: float = Field(ge=0.0, le=1.0)
    model_version: str = Field(min_length=1, max_length=128)
    knowledge_base_version: str | None = Field(default=None, max_length=128)
    prediction_disclaimer: str = Field(
        default="Kết quả chỉ phục vụ mục đích học thuật và không thay thế chẩn đoán của bác sĩ.",
        min_length=1,
        max_length=1000,
    )
    reference_source_ids: tuple[str, ...] = (
        "MODEL_ARTIFACT_1_1_0",
        "PROJECT_SOURCE_V1_0_0",
    )
    processing_time_ms: int = Field(ge=0)
    analyzed_at: datetime

    @field_validator("patient_code", mode="before")
    @classmethod
    def validate_patient_code(cls, value: object) -> str | None:
        return normalize_patient_code(value)

    @field_validator("patient_display_name", mode="before")
    @classmethod
    def validate_patient_display_name(cls, value: object) -> str | None:
        return normalize_patient_display_name(value)

    @field_validator("original_filename", mode="before")
    @classmethod
    def sanitize_original_filename(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("original_filename must be text")
        basename = value.replace("\\", "/").split("/")[-1]
        sanitized = _UNSAFE_FILENAME_CHARACTERS.sub(
            "_",
            _CONTROL_CHARACTERS.sub("", basename),
        )
        sanitized = re.sub(r"\s+", " ", sanitized).strip(" .")
        if not sanitized:
            raise ValueError("original_filename has no valid characters")
        return sanitized

    @field_validator("reference_source_ids")
    @classmethod
    def validate_source_ids(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(values) > 20:
            raise ValueError("too many report provenance source IDs")
        normalized: list[str] = []
        for value in values:
            if not _SOURCE_ID_PATTERN.fullmatch(value):
                raise ValueError("reference source ID is invalid")
            if value not in normalized:
                normalized.append(value)
        return tuple(normalized)

    @field_validator("analyzed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("analyzed_at must include a timezone")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_history_invariants(self) -> "AnalysisHistoryCreate":
        probabilities = normalize_probabilities(
            {
                "normal": self.normal_probability,
                "pneumonia": self.pneumonia_probability,
                "tuberculosis": self.tuberculosis_probability,
            }
        )
        self.normal_probability = probabilities["normal"]
        self.pneumonia_probability = probabilities["pneumonia"]
        self.tuberculosis_probability = probabilities["tuberculosis"]
        if self.predicted_label != predicted_label(probabilities):
            raise ValueError("predicted_label must match the highest probability")
        if not self.patient_info_confirmed:
            raise ValueError("patient information must be confirmed before persistence")
        if self.is_anonymous_sample:
            if (
                self.patient_code is not None
                or self.patient_display_name is not None
                or self.patient_name_source != "anonymous"
            ):
                raise ValueError("anonymous samples cannot store patient identifiers")
            if self.filename_pattern_id is not None or self.parsed_filename_date is not None:
                raise ValueError("anonymous samples cannot store parsed patient metadata")
        elif self.patient_display_name is None or self.patient_name_source == "anonymous":
            raise ValueError("identified records require a patient name and source")
        if self.patient_name_source == "filename" and self.filename_pattern_id is None:
            raise ValueError("filename-derived records require a filename pattern ID")
        return self
