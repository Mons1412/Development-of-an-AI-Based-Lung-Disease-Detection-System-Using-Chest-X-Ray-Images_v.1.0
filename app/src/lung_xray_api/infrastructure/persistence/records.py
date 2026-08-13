"""Typed persistence records; original image bytes are never stored."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

PatientNameSource = Literal["filename", "manual", "anonymous"]
PredictedLabel = Literal["normal", "pneumonia", "tuberculosis"]


@dataclass(frozen=True)
class AnalysisHistoryRecord:
    id: str
    patient_code: str | None
    patient_display_name: str | None
    patient_name_search_key: str | None
    patient_name_source: PatientNameSource
    patient_info_confirmed: bool
    is_anonymous_sample: bool
    filename_pattern_id: str | None
    parsed_filename_date: date | None
    original_filename: str
    thumbnail_relative_path: str | None
    predicted_label: PredictedLabel
    normal_probability: float
    pneumonia_probability: float
    tuberculosis_probability: float
    model_version: str
    knowledge_base_version: str | None
    prediction_disclaimer: str
    reference_source_ids: tuple[str, ...]
    processing_time_ms: int
    analyzed_at: datetime
    created_at: datetime


@dataclass(frozen=True)
class AnalysisHistoryFilters:
    patient_code: str | None = None
    patient_display_name: str | None = None
    patient_query: str | None = None
    predicted_label: PredictedLabel | None = None
    is_anonymous_sample: bool | None = None
    analyzed_at_from: datetime | None = None
    analyzed_at_to: datetime | None = None
    sort_order: Literal["asc", "desc"] = "desc"


@dataclass(frozen=True)
class AnalysisHistoryPage:
    items: tuple[AnalysisHistoryRecord, ...]
    total: int
    page: int
    page_size: int


@dataclass(frozen=True)
class ThumbnailCleanupJob:
    id: int
    analysis_id: str
    relative_path: str
    retry_count: int
    last_error: str | None


@dataclass(frozen=True)
class AnalysisDeletionResult:
    record: AnalysisHistoryRecord
    cleanup_pending: bool

    @property
    def id(self) -> str:
        """Compatibility accessor for callers that previously received the record."""

        return self.record.id
