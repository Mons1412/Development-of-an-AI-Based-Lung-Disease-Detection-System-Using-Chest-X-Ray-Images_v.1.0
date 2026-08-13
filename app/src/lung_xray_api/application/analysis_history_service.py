"""Application boundary coordinating records and derivative thumbnails."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

from lung_xray_api.core.config import Settings
from lung_xray_api.core.exceptions import ThumbnailCleanupError
from lung_xray_api.infrastructure.ml.image_validator import ValidatedImage
from lung_xray_api.infrastructure.persistence.analysis_repository import AnalysisHistoryRepository
from lung_xray_api.infrastructure.persistence.connection import SQLiteConnectionFactory
from lung_xray_api.infrastructure.persistence.migrations import initialize_database
from lung_xray_api.infrastructure.persistence.normalization import normalize_search_key
from lung_xray_api.infrastructure.persistence.records import (
    AnalysisDeletionResult,
    AnalysisHistoryFilters,
    AnalysisHistoryPage,
    AnalysisHistoryRecord,
)
from lung_xray_api.infrastructure.persistence.thumbnail_store import ThumbnailStore
from lung_xray_api.schemas.analysis_history import AnalysisHistoryCreate

logger = logging.getLogger(__name__)


class AnalysisHistoryService:
    def __init__(
        self,
        repository: AnalysisHistoryRepository,
        thumbnail_store: ThumbnailStore,
        default_page_size: int,
    ) -> None:
        if not 1 <= default_page_size <= 100:
            raise ValueError("history_page_size must be between 1 and 100")
        self.repository = repository
        self.thumbnail_store = thumbnail_store
        self.default_page_size = default_page_size

    @classmethod
    def from_settings(cls, settings: Settings) -> "AnalysisHistoryService":
        if settings.history_db_path is None or settings.thumbnail_dir is None:
            raise ValueError("History database and thumbnail paths are required")
        connection_factory = SQLiteConnectionFactory(
            settings.history_db_path,
            settings.history_busy_timeout_ms,
        )
        initialize_database(connection_factory)
        thumbnail_store = ThumbnailStore(
            settings.thumbnail_dir,
            settings.thumbnail_max_dimension,
        )
        thumbnail_store.ensure_directory()
        service = cls(
            repository=AnalysisHistoryRepository(connection_factory),
            thumbnail_store=thumbnail_store,
            default_page_size=settings.history_page_size,
        )
        service.process_cleanup_queue()
        return service

    def create(
        self,
        payload: AnalysisHistoryCreate,
        validated_image: ValidatedImage | None = None,
    ) -> AnalysisHistoryRecord:
        analysis_id = str(uuid4())
        thumbnail_relative_path: str | None = None
        if validated_image is not None:
            thumbnail_relative_path = self.thumbnail_store.write_thumbnail(
                analysis_id,
                validated_image,
            )
        record = AnalysisHistoryRecord(
            id=analysis_id,
            patient_code=payload.patient_code,
            patient_display_name=payload.patient_display_name,
            patient_name_search_key=normalize_search_key(payload.patient_display_name),
            patient_name_source=payload.patient_name_source,
            patient_info_confirmed=payload.patient_info_confirmed,
            is_anonymous_sample=payload.is_anonymous_sample,
            filename_pattern_id=payload.filename_pattern_id,
            parsed_filename_date=payload.parsed_filename_date,
            original_filename=payload.original_filename,
            thumbnail_relative_path=thumbnail_relative_path,
            predicted_label=payload.predicted_label,
            normal_probability=payload.normal_probability,
            pneumonia_probability=payload.pneumonia_probability,
            tuberculosis_probability=payload.tuberculosis_probability,
            model_version=payload.model_version,
            knowledge_base_version=payload.knowledge_base_version,
            prediction_disclaimer=payload.prediction_disclaimer,
            reference_source_ids=payload.reference_source_ids,
            processing_time_ms=payload.processing_time_ms,
            analyzed_at=payload.analyzed_at,
            created_at=datetime.now(timezone.utc),
        )
        try:
            return self.repository.create(record)
        except Exception:
            self.thumbnail_store.delete_thumbnail(thumbnail_relative_path)
            raise

    def get(self, analysis_id: str) -> AnalysisHistoryRecord | None:
        return self.repository.get_by_id(analysis_id)

    def list(
        self,
        *,
        page: int = 1,
        page_size: int | None = None,
        filters: AnalysisHistoryFilters | None = None,
    ) -> AnalysisHistoryPage:
        return self.repository.list_records(
            page=page,
            page_size=page_size or self.default_page_size,
            filters=filters,
        )

    def count(self, filters: AnalysisHistoryFilters | None = None) -> int:
        return self.repository.count_records(filters)

    def schema_version(self) -> int:
        return self.repository.schema_version()

    def delete(self, analysis_id: str) -> AnalysisDeletionResult:
        record = self.repository.delete_and_enqueue_cleanup(analysis_id)
        cleanup_pending = not self._delete_cleanup_job_for_record(record)
        return AnalysisDeletionResult(record=record, cleanup_pending=cleanup_pending)

    def process_cleanup_queue(self) -> None:
        """Retry orphan derivative deletion without risking surviving records."""

        for job in self.repository.list_cleanup_jobs():
            try:
                self.thumbnail_store.delete_thumbnail(job.relative_path)
            except ThumbnailCleanupError:
                self.repository.fail_cleanup_job(job.id, "thumbnail_delete_failed")
                logger.warning(
                    "Thumbnail cleanup remains pending for analysis %s",
                    job.analysis_id,
                )
            else:
                self.repository.complete_cleanup_job(job.id)

    def _delete_cleanup_job_for_record(self, record: AnalysisHistoryRecord) -> bool:
        if record.thumbnail_relative_path is None:
            return True
        for job in self.repository.list_cleanup_jobs():
            if job.analysis_id != record.id:
                continue
            try:
                self.thumbnail_store.delete_thumbnail(job.relative_path)
            except ThumbnailCleanupError:
                self.repository.fail_cleanup_job(job.id, "thumbnail_delete_failed")
                return False
            self.repository.complete_cleanup_job(job.id)
            return True
        return True
