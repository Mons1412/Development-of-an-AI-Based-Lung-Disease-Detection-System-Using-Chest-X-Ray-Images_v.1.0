"""Confirmed metadata, inference, and all-or-fail local persistence workflow."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, timezone
from time import perf_counter
from typing import Protocol, cast

from lung_xray_api.application.analysis_history_service import AnalysisHistoryService
from lung_xray_api.application.filename_metadata_parser import (
    FILENAME_PATTERN_ID,
    FilenameMetadataParser,
)
from lung_xray_api.application.prediction_service import PredictionResult
from lung_xray_api.core.exceptions import PersistenceError
from lung_xray_api.domain.probabilities import normalize_probabilities, predicted_label
from lung_xray_api.infrastructure.ml.image_validator import ValidatedImage
from lung_xray_api.infrastructure.persistence.records import AnalysisHistoryRecord, PredictedLabel
from lung_xray_api.schemas.analysis_history import AnalysisHistoryCreate
from lung_xray_api.schemas.case_metadata import CaseMetadataInput

_DEFAULT_SOURCE_IDS = ("MODEL_ARTIFACT_1_1_0", "PROJECT_SOURCE_V1_0_0")


class AnalysisPredictionServiceProtocol(Protocol):
    def validate_upload(
        self,
        content: bytes,
        filename: str,
        content_type: str | None = None,
    ) -> ValidatedImage:
        ...

    def predict_validated_image(self, validated: ValidatedImage) -> PredictionResult:
        ...


class CaseMetadataValidationError(ValueError):
    """Metadata is invalid for the selected filename."""


@dataclass(frozen=True)
class PersistedAnalysis:
    prediction: PredictionResult
    record: AnalysisHistoryRecord


class AnalysisService:
    def __init__(
        self,
        prediction_service: AnalysisPredictionServiceProtocol,
        history_service: AnalysisHistoryService,
        knowledge_base_version: str | None,
        filename_parser: FilenameMetadataParser | None = None,
    ) -> None:
        self._prediction_service = prediction_service
        self._history_service = history_service
        self._knowledge_base_version = (
            knowledge_base_version.strip() if knowledge_base_version else None
        )
        self._filename_parser = filename_parser or FilenameMetadataParser()

    def analyze_upload(
        self,
        *,
        content: bytes,
        filename: str,
        content_type: str | None,
        metadata: CaseMetadataInput,
    ) -> PersistedAnalysis:
        parsed_date = self._validate_filename_metadata(filename, metadata)
        started_at = perf_counter()
        validated_image = self._prediction_service.validate_upload(
            content,
            filename,
            content_type,
        )
        prediction = self._prediction_service.predict_validated_image(validated_image)
        normalized = normalize_probabilities(prediction.probabilities)
        label = predicted_label(normalized)
        prediction = replace(
            prediction,
            prediction=label,
            model_probability=normalized[label],
            probabilities=dict(normalized),
            processing_time_ms=int((perf_counter() - started_at) * 1000),
        )
        record = self._persist_success(
            prediction=prediction,
            validated_image=validated_image,
            metadata=metadata,
            parsed_filename_date=parsed_date,
        )
        return PersistedAnalysis(prediction=prediction, record=record)

    def _validate_filename_metadata(
        self,
        filename: str,
        metadata: CaseMetadataInput,
    ) -> date | None:
        if metadata.is_anonymous_sample or metadata.patient_name_source == "manual":
            return None
        parsed = self._filename_parser.parse(filename)
        if (
            not parsed.matched
            or parsed.patient_code != metadata.patient_code
            or parsed.patient_display_name != metadata.patient_display_name
        ):
            raise CaseMetadataValidationError(
                "Filename-derived metadata must match the approved filename"
            )
        return parsed.parsed_date

    def _persist_success(
        self,
        *,
        prediction: PredictionResult,
        validated_image: ValidatedImage,
        metadata: CaseMetadataInput,
        parsed_filename_date: date | None,
    ) -> AnalysisHistoryRecord:
        try:
            if prediction.prediction not in {"normal", "pneumonia", "tuberculosis"}:
                raise ValueError("prediction label is unsupported")
            payload = AnalysisHistoryCreate(
                patient_code=metadata.patient_code,
                patient_display_name=metadata.patient_display_name,
                patient_name_source=metadata.patient_name_source,
                patient_info_confirmed=metadata.patient_info_confirmed,
                is_anonymous_sample=metadata.is_anonymous_sample,
                filename_pattern_id=(
                    FILENAME_PATTERN_ID
                    if metadata.patient_name_source == "filename"
                    else None
                ),
                parsed_filename_date=parsed_filename_date,
                original_filename=validated_image.filename,
                predicted_label=cast(PredictedLabel, prediction.prediction),
                normal_probability=prediction.probabilities["normal"],
                pneumonia_probability=prediction.probabilities["pneumonia"],
                tuberculosis_probability=prediction.probabilities["tuberculosis"],
                model_version=prediction.model_version,
                knowledge_base_version=self._knowledge_base_version,
                prediction_disclaimer=prediction.disclaimer,
                reference_source_ids=_DEFAULT_SOURCE_IDS,
                processing_time_ms=prediction.processing_time_ms,
                analyzed_at=datetime.now(timezone.utc),
            )
            return self._history_service.create(payload, validated_image)
        except (KeyError, ValueError) as error:
            raise PersistenceError(
                "Could not construct a safe analysis history record"
            ) from error
