"""Public contracts for persisted analyses and local history."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from lung_xray_api.schemas.case_metadata import CaseMetadataResponse
from lung_xray_api.schemas.prediction import PredictionResponse

ClassLabel = Literal["normal", "pneumonia", "tuberculosis"]


class AnalysisStorageStatus(BaseModel):
    status: Literal["persisted"] = "persisted"
    persisted: Literal[True] = True


class PersistedAnalysisResponse(PredictionResponse):
    analysis_id: UUID
    analyzed_at: datetime
    created_at: datetime
    case_metadata: CaseMetadataResponse
    storage: AnalysisStorageStatus = Field(default_factory=AnalysisStorageStatus)


class AnalysisSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_id: UUID
    patient_code: str | None
    patient_display_name: str | None
    patient_name_source: Literal["filename", "manual", "anonymous"]
    patient_info_confirmed: bool
    is_anonymous_sample: bool
    original_filename: str
    predicted_label: ClassLabel
    model_probability: float = Field(ge=0.0, le=1.0)
    model_version: str
    processing_time_ms: int = Field(ge=0)
    analyzed_at: datetime
    thumbnail_available: bool


class AnalysisDetail(AnalysisSummary):
    normal_probability: float = Field(ge=0.0, le=1.0)
    pneumonia_probability: float = Field(ge=0.0, le=1.0)
    tuberculosis_probability: float = Field(ge=0.0, le=1.0)
    knowledge_base_version: str | None
    prediction_disclaimer: str
    reference_source_ids: list[str]
    filename_pattern_id: str | None
    parsed_filename_date: date | None
    created_at: datetime
    thumbnail_url: str | None = None
    report_url: str


class AnalysisHistoryPageResponse(BaseModel):
    items: list[AnalysisSummary]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)


class AnalysisDeletionResponse(BaseModel):
    status: Literal["deleted"] = "deleted"
    analysis_id: UUID
    cleanup_pending: bool = False
