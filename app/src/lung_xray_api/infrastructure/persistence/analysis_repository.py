"""Parameterized SQLite queries for local analysis-history records."""

from __future__ import annotations

from datetime import date, datetime, timezone
import json
import sqlite3
from typing import cast

from lung_xray_api.core.exceptions import AnalysisNotFoundError, PersistenceError
from lung_xray_api.infrastructure.persistence.connection import SQLiteConnectionFactory
from lung_xray_api.infrastructure.persistence.migrations import inspect_schema_version
from lung_xray_api.infrastructure.persistence.normalization import normalize_search_key
from lung_xray_api.infrastructure.persistence.records import (
    AnalysisHistoryFilters,
    AnalysisHistoryPage,
    AnalysisHistoryRecord,
    PatientNameSource,
    PredictedLabel,
    ThumbnailCleanupJob,
)


class AnalysisHistoryRepository:
    """Own SQL only; file coordination belongs to the application service."""

    def __init__(self, connection_factory: SQLiteConnectionFactory) -> None:
        self._connection_factory = connection_factory

    def create(self, record: AnalysisHistoryRecord) -> AnalysisHistoryRecord:
        try:
            with self._connection_factory.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO analysis_history (
                        id, patient_code, patient_display_name,
                        patient_name_search_key, patient_name_source,
                        patient_info_confirmed, is_anonymous_sample,
                        filename_pattern_id, parsed_filename_date,
                        original_filename, thumbnail_relative_path,
                        predicted_label, normal_probability,
                        pneumonia_probability, tuberculosis_probability,
                        model_version, knowledge_base_version,
                        prediction_disclaimer, reference_source_ids_json,
                        processing_time_ms, analyzed_at, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    self._record_values(record),
                )
        except sqlite3.IntegrityError as error:
            raise PersistenceError("Could not create analysis history record") from error
        return record

    def get_by_id(self, analysis_id: str) -> AnalysisHistoryRecord | None:
        with self._connection_factory.read_connection() as connection:
            row = connection.execute(
                "SELECT * FROM analysis_history WHERE id = ?",
                (analysis_id,),
            ).fetchone()
        return self._to_record(row) if row is not None else None

    def require_by_id(self, analysis_id: str) -> AnalysisHistoryRecord:
        record = self.get_by_id(analysis_id)
        if record is None:
            raise AnalysisNotFoundError("Analysis history record was not found")
        return record

    def list_records(
        self,
        *,
        page: int,
        page_size: int,
        filters: AnalysisHistoryFilters | None = None,
    ) -> AnalysisHistoryPage:
        if page < 1 or not 1 <= page_size <= 100:
            raise ValueError("page and page_size are outside the supported range")
        filters = filters or AnalysisHistoryFilters()
        where_sql, parameters = self._where_clause(filters)
        direction = self._sort_direction(filters.sort_order)
        offset = (page - 1) * page_size
        with self._connection_factory.read_connection() as connection:
            total_row = connection.execute(
                f"SELECT COUNT(*) AS total FROM analysis_history {where_sql}",
                parameters,
            ).fetchone()
            rows = connection.execute(
                f"SELECT * FROM analysis_history {where_sql} "
                f"ORDER BY analyzed_at {direction}, id {direction} LIMIT ? OFFSET ?",
                (*parameters, page_size, offset),
            ).fetchall()
        return AnalysisHistoryPage(
            items=tuple(self._to_record(row) for row in rows),
            total=int(total_row["total"]),
            page=page,
            page_size=page_size,
        )

    def count_records(self, filters: AnalysisHistoryFilters | None = None) -> int:
        where_sql, parameters = self._where_clause(filters or AnalysisHistoryFilters())
        with self._connection_factory.read_connection() as connection:
            row = connection.execute(
                f"SELECT COUNT(*) AS total FROM analysis_history {where_sql}",
                parameters,
            ).fetchone()
        return int(row["total"])

    def delete_and_enqueue_cleanup(self, analysis_id: str) -> AnalysisHistoryRecord:
        try:
            with self._connection_factory.transaction() as connection:
                row = connection.execute(
                    "SELECT * FROM analysis_history WHERE id = ?",
                    (analysis_id,),
                ).fetchone()
                if row is None:
                    raise AnalysisNotFoundError("Analysis history record was not found")
                record = self._to_record(row)
                if record.thumbnail_relative_path is not None:
                    connection.execute(
                        """
                        INSERT OR IGNORE INTO thumbnail_cleanup_queue (
                            analysis_id, relative_path, retry_count, last_error, created_at
                        ) VALUES (?, ?, 0, NULL, ?)
                        """,
                        (analysis_id, record.thumbnail_relative_path, datetime.now(timezone.utc).isoformat()),
                    )
                connection.execute("DELETE FROM analysis_history WHERE id = ?", (analysis_id,))
                return record
        except sqlite3.IntegrityError as error:
            raise PersistenceError("Could not delete analysis history record") from error

    def list_cleanup_jobs(self, limit: int = 100) -> tuple[ThumbnailCleanupJob, ...]:
        with self._connection_factory.read_connection() as connection:
            rows = connection.execute(
                "SELECT * FROM thumbnail_cleanup_queue ORDER BY created_at, id LIMIT ?",
                (limit,),
            ).fetchall()
        return tuple(
            ThumbnailCleanupJob(
                id=int(row["id"]),
                analysis_id=str(row["analysis_id"]),
                relative_path=str(row["relative_path"]),
                retry_count=int(row["retry_count"]),
                last_error=row["last_error"],
            )
            for row in rows
        )

    def complete_cleanup_job(self, job_id: int) -> None:
        with self._connection_factory.transaction() as connection:
            connection.execute("DELETE FROM thumbnail_cleanup_queue WHERE id = ?", (job_id,))

    def fail_cleanup_job(self, job_id: int, safe_error: str) -> None:
        with self._connection_factory.transaction() as connection:
            connection.execute(
                """
                UPDATE thumbnail_cleanup_queue
                SET retry_count = retry_count + 1, last_error = ?
                WHERE id = ?
                """,
                (safe_error[:200], job_id),
            )

    def schema_version(self) -> int:
        return inspect_schema_version(self._connection_factory)

    @staticmethod
    def _record_values(record: AnalysisHistoryRecord) -> tuple[object, ...]:
        return (
            record.id,
            record.patient_code,
            record.patient_display_name,
            record.patient_name_search_key,
            record.patient_name_source,
            int(record.patient_info_confirmed),
            int(record.is_anonymous_sample),
            record.filename_pattern_id,
            record.parsed_filename_date.isoformat() if record.parsed_filename_date else None,
            record.original_filename,
            record.thumbnail_relative_path,
            record.predicted_label,
            record.normal_probability,
            record.pneumonia_probability,
            record.tuberculosis_probability,
            record.model_version,
            record.knowledge_base_version,
            record.prediction_disclaimer,
            json.dumps(record.reference_source_ids, ensure_ascii=False, separators=(",", ":")),
            record.processing_time_ms,
            record.analyzed_at.isoformat(),
            record.created_at.isoformat(),
        )

    @staticmethod
    def _where_clause(filters: AnalysisHistoryFilters) -> tuple[str, tuple[object, ...]]:
        clauses: list[str] = []
        parameters: list[object] = []
        if filters.patient_code is not None:
            clauses.append("patient_code = ?")
            parameters.append(filters.patient_code)
        if filters.patient_display_name is not None:
            clauses.append("patient_name_search_key LIKE ? ESCAPE '\\'")
            search_key = normalize_search_key(filters.patient_display_name) or ""
            parameters.append(f"%{_escape_like(search_key)}%")
        if filters.patient_query is not None:
            search_key = normalize_search_key(filters.patient_query) or ""
            escaped = _escape_like(search_key)
            clauses.append(
                "(patient_name_search_key LIKE ? ESCAPE '\\' "
                "OR lower(patient_code) LIKE ? ESCAPE '\\')"
            )
            parameters.extend((f"%{escaped}%", f"%{escaped}%"))
        if filters.predicted_label is not None:
            clauses.append("predicted_label = ?")
            parameters.append(filters.predicted_label)
        if filters.is_anonymous_sample is not None:
            clauses.append("is_anonymous_sample = ?")
            parameters.append(int(filters.is_anonymous_sample))
        if filters.analyzed_at_from is not None:
            clauses.append("analyzed_at >= ?")
            parameters.append(filters.analyzed_at_from.isoformat())
        if filters.analyzed_at_to is not None:
            clauses.append("analyzed_at < ?")
            parameters.append(filters.analyzed_at_to.isoformat())
        return (f"WHERE {' AND '.join(clauses)}" if clauses else "", tuple(parameters))

    @staticmethod
    def _sort_direction(sort_order: str) -> str:
        if sort_order == "asc":
            return "ASC"
        if sort_order == "desc":
            return "DESC"
        raise ValueError("sort_order must be asc or desc")

    @staticmethod
    def _to_record(row: sqlite3.Row) -> AnalysisHistoryRecord:
        try:
            source_ids_raw = json.loads(str(row["reference_source_ids_json"]))
        except json.JSONDecodeError as error:
            raise PersistenceError("Analysis source provenance is invalid") from error
        if not isinstance(source_ids_raw, list) or not all(
            isinstance(value, str) for value in source_ids_raw
        ):
            raise PersistenceError("Analysis source provenance is invalid")
        parsed_date_raw = row["parsed_filename_date"]
        return AnalysisHistoryRecord(
            id=str(row["id"]),
            patient_code=row["patient_code"],
            patient_display_name=row["patient_display_name"],
            patient_name_search_key=row["patient_name_search_key"],
            patient_name_source=cast(PatientNameSource, str(row["patient_name_source"])),
            patient_info_confirmed=bool(row["patient_info_confirmed"]),
            is_anonymous_sample=bool(row["is_anonymous_sample"]),
            filename_pattern_id=row["filename_pattern_id"],
            parsed_filename_date=(date.fromisoformat(str(parsed_date_raw)) if parsed_date_raw else None),
            original_filename=str(row["original_filename"]),
            thumbnail_relative_path=row["thumbnail_relative_path"],
            predicted_label=cast(PredictedLabel, str(row["predicted_label"])),
            normal_probability=float(row["normal_probability"]),
            pneumonia_probability=float(row["pneumonia_probability"]),
            tuberculosis_probability=float(row["tuberculosis_probability"]),
            model_version=str(row["model_version"]),
            knowledge_base_version=row["knowledge_base_version"],
            prediction_disclaimer=str(row["prediction_disclaimer"]),
            reference_source_ids=tuple(source_ids_raw),
            processing_time_ms=int(row["processing_time_ms"]),
            analyzed_at=_parse_datetime(str(row["analyzed_at"])),
            created_at=_parse_datetime(str(row["created_at"])),
        )


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise PersistenceError("Analysis history timestamp is missing timezone information")
    return parsed
