"""Non-destructive ordered migrations for local analysis history."""

from __future__ import annotations

from datetime import datetime, timezone
import sqlite3

from lung_xray_api.core.exceptions import PersistenceError, SchemaVersionError
from lung_xray_api.infrastructure.persistence.connection import SQLiteConnectionFactory
from lung_xray_api.infrastructure.persistence.normalization import normalize_search_key

LATEST_SCHEMA_VERSION = 2
_DEFAULT_DISCLAIMER = (
    "Kết quả chỉ phục vụ mục đích học thuật và không thay thế chẩn đoán của bác sĩ."
)
_DEFAULT_SOURCE_IDS = '["MODEL_ARTIFACT_1_1_0","PROJECT_SOURCE_V1_0_0"]'


def initialize_database(connection_factory: SQLiteConnectionFactory) -> int:
    """Create or upgrade the local store while preserving existing records."""

    try:
        with connection_factory.transaction() as connection:
            _create_migration_table(connection)
            current_version = _schema_version(connection)
            if current_version > LATEST_SCHEMA_VERSION:
                raise SchemaVersionError(
                    "SQLite history database uses a newer schema version than this application"
                )
            for version in range(current_version + 1, LATEST_SCHEMA_VERSION + 1):
                _apply_migration(connection, version)
                connection.execute(
                    "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                    (version, _utc_now()),
                )
            _backfill_search_keys(connection)
            if connection.execute("PRAGMA foreign_key_check").fetchall():
                raise PersistenceError("SQLite history database failed foreign-key validation")
            _verify_schema(connection)
            return _schema_version(connection)
    except sqlite3.Error as error:
        raise PersistenceError("SQLite history database migration failed") from error


def inspect_schema_version(connection_factory: SQLiteConnectionFactory) -> int:
    if not connection_factory.database_path.is_file():
        return 0
    try:
        with connection_factory.read_connection() as connection:
            exists = connection.execute(
                "SELECT 1 FROM sqlite_master "
                "WHERE type = 'table' AND name = 'schema_migrations'"
            ).fetchone()
            return _schema_version(connection) if exists is not None else 0
    except sqlite3.Error as error:
        raise PersistenceError("Could not inspect SQLite history schema version") from error


def _create_migration_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
        """
    )


def _schema_version(connection: sqlite3.Connection) -> int:
    row = connection.execute(
        "SELECT COALESCE(MAX(version), 0) AS version FROM schema_migrations"
    ).fetchone()
    return int(row["version"])


def _apply_migration(connection: sqlite3.Connection, version: int) -> None:
    if version == 1:
        _migration_v1(connection)
        return
    if version == 2:
        _migration_v2(connection)
        return
    raise SchemaVersionError(f"Unknown SQLite history migration version: {version}")


def _migration_v1(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS analysis_history (
            id TEXT PRIMARY KEY,
            patient_code TEXT NULL,
            patient_display_name TEXT NULL,
            patient_name_source TEXT NOT NULL
                CHECK (patient_name_source IN ('filename', 'manual', 'anonymous')),
            patient_info_confirmed INTEGER NOT NULL CHECK (patient_info_confirmed IN (0, 1)),
            is_anonymous_sample INTEGER NOT NULL CHECK (is_anonymous_sample IN (0, 1)),
            original_filename TEXT NOT NULL,
            thumbnail_relative_path TEXT NULL,
            predicted_label TEXT NOT NULL
                CHECK (predicted_label IN ('normal', 'pneumonia', 'tuberculosis')),
            normal_probability REAL NOT NULL CHECK (normal_probability BETWEEN 0 AND 1),
            pneumonia_probability REAL NOT NULL CHECK (pneumonia_probability BETWEEN 0 AND 1),
            tuberculosis_probability REAL NOT NULL CHECK (tuberculosis_probability BETWEEN 0 AND 1),
            model_version TEXT NOT NULL,
            knowledge_base_version TEXT NOT NULL,
            processing_time_ms INTEGER NOT NULL CHECK (processing_time_ms >= 0),
            analyzed_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            CHECK (
                (is_anonymous_sample = 1
                    AND patient_code IS NULL
                    AND patient_display_name IS NULL
                    AND patient_name_source = 'anonymous')
                OR
                (is_anonymous_sample = 0
                    AND patient_code IS NOT NULL
                    AND patient_display_name IS NOT NULL
                    AND patient_name_source IN ('filename', 'manual'))
            ),
            CHECK (
                ABS((normal_probability + pneumonia_probability
                    + tuberculosis_probability) - 1.0) <= 0.0001
            )
        )
        """
    )
    _create_v1_indexes(connection)


def _migration_v2(connection: sqlite3.Connection) -> None:
    # Rebuild is required because SQLite cannot remove the old patient-code
    # CHECK constraint with ALTER TABLE. Data is copied in one transaction.
    connection.execute(
        """
        CREATE TABLE analysis_history_v2 (
            id TEXT PRIMARY KEY,
            patient_code TEXT NULL,
            patient_display_name TEXT NULL,
            patient_name_search_key TEXT NULL,
            patient_name_source TEXT NOT NULL
                CHECK (patient_name_source IN ('filename', 'manual', 'anonymous')),
            patient_info_confirmed INTEGER NOT NULL CHECK (patient_info_confirmed IN (0, 1)),
            is_anonymous_sample INTEGER NOT NULL CHECK (is_anonymous_sample IN (0, 1)),
            filename_pattern_id TEXT NULL,
            parsed_filename_date TEXT NULL,
            original_filename TEXT NOT NULL,
            thumbnail_relative_path TEXT NULL,
            predicted_label TEXT NOT NULL
                CHECK (predicted_label IN ('normal', 'pneumonia', 'tuberculosis')),
            normal_probability REAL NOT NULL CHECK (normal_probability BETWEEN 0 AND 1),
            pneumonia_probability REAL NOT NULL CHECK (pneumonia_probability BETWEEN 0 AND 1),
            tuberculosis_probability REAL NOT NULL CHECK (tuberculosis_probability BETWEEN 0 AND 1),
            model_version TEXT NOT NULL,
            knowledge_base_version TEXT NULL,
            prediction_disclaimer TEXT NOT NULL,
            reference_source_ids_json TEXT NOT NULL DEFAULT '[]',
            processing_time_ms INTEGER NOT NULL CHECK (processing_time_ms >= 0),
            analyzed_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            CHECK (
                (is_anonymous_sample = 1
                    AND patient_code IS NULL
                    AND patient_display_name IS NULL
                    AND patient_name_source = 'anonymous')
                OR
                (is_anonymous_sample = 0
                    AND patient_display_name IS NOT NULL
                    AND patient_name_source IN ('filename', 'manual'))
            ),
            CHECK (
                ABS((normal_probability + pneumonia_probability
                    + tuberculosis_probability) - 1.0) <= 0.0001
            )
        )
        """
    )
    connection.execute(
        """
        INSERT INTO analysis_history_v2 (
            id, patient_code, patient_display_name, patient_name_search_key,
            patient_name_source, patient_info_confirmed, is_anonymous_sample,
            filename_pattern_id, parsed_filename_date, original_filename,
            thumbnail_relative_path, predicted_label, normal_probability,
            pneumonia_probability, tuberculosis_probability, model_version,
            knowledge_base_version, prediction_disclaimer,
            reference_source_ids_json, processing_time_ms, analyzed_at, created_at
        )
        SELECT
            id, patient_code, patient_display_name, patient_display_name,
            patient_name_source, patient_info_confirmed, is_anonymous_sample,
            CASE WHEN patient_name_source = 'filename'
                THEN 'patient_code__patient_name__yyyymmdd_v1' ELSE NULL END,
            NULL, original_filename, thumbnail_relative_path, predicted_label,
            normal_probability, pneumonia_probability, tuberculosis_probability,
            model_version, knowledge_base_version, ?, ?, processing_time_ms,
            analyzed_at, created_at
        FROM analysis_history
        """,
        (_DEFAULT_DISCLAIMER, _DEFAULT_SOURCE_IDS),
    )
    connection.execute("DROP TABLE analysis_history")
    connection.execute("ALTER TABLE analysis_history_v2 RENAME TO analysis_history")
    _create_v2_indexes(connection)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS thumbnail_cleanup_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_id TEXT NOT NULL,
            relative_path TEXT NOT NULL,
            retry_count INTEGER NOT NULL DEFAULT 0 CHECK (retry_count >= 0),
            last_error TEXT NULL,
            created_at TEXT NOT NULL,
            UNIQUE (relative_path)
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_thumbnail_cleanup_created_at "
        "ON thumbnail_cleanup_queue (created_at, id)"
    )


def _create_v1_indexes(connection: sqlite3.Connection) -> None:
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_analysis_history_analyzed_at "
        "ON analysis_history (analyzed_at DESC, id DESC)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_analysis_history_patient_code "
        "ON analysis_history (patient_code)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_analysis_history_patient_display_name "
        "ON analysis_history (patient_display_name)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_analysis_history_predicted_label "
        "ON analysis_history (predicted_label)"
    )


def _create_v2_indexes(connection: sqlite3.Connection) -> None:
    _create_v1_indexes(connection)
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_analysis_history_patient_search_key "
        "ON analysis_history (patient_name_search_key)"
    )


def _backfill_search_keys(connection: sqlite3.Connection) -> None:
    columns = {
        str(row["name"])
        for row in connection.execute("PRAGMA table_info('analysis_history')").fetchall()
    }
    if "patient_name_search_key" not in columns:
        return
    rows = connection.execute(
        "SELECT id, patient_display_name FROM analysis_history "
        "WHERE patient_display_name IS NOT NULL"
    ).fetchall()
    for row in rows:
        connection.execute(
            "UPDATE analysis_history SET patient_name_search_key = ? WHERE id = ?",
            (normalize_search_key(row["patient_display_name"]), row["id"]),
        )


def _verify_schema(connection: sqlite3.Connection) -> None:
    expected_tables = {"schema_migrations", "analysis_history", "thumbnail_cleanup_queue"}
    actual_tables = {
        str(row["name"])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    missing_tables = expected_tables - actual_tables
    if missing_tables:
        raise PersistenceError(
            "SQLite history database is missing required tables: "
            + ", ".join(sorted(missing_tables))
        )

    expected_columns = {
        "id",
        "patient_code",
        "patient_display_name",
        "patient_name_search_key",
        "patient_name_source",
        "patient_info_confirmed",
        "is_anonymous_sample",
        "filename_pattern_id",
        "parsed_filename_date",
        "original_filename",
        "thumbnail_relative_path",
        "predicted_label",
        "normal_probability",
        "pneumonia_probability",
        "tuberculosis_probability",
        "model_version",
        "knowledge_base_version",
        "prediction_disclaimer",
        "reference_source_ids_json",
        "processing_time_ms",
        "analyzed_at",
        "created_at",
    }
    actual_columns = {
        str(row["name"])
        for row in connection.execute("PRAGMA table_info('analysis_history')").fetchall()
    }
    missing_columns = expected_columns - actual_columns
    if missing_columns:
        raise PersistenceError(
            "SQLite history database is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    expected_indexes = {
        "idx_analysis_history_analyzed_at",
        "idx_analysis_history_patient_code",
        "idx_analysis_history_patient_display_name",
        "idx_analysis_history_patient_search_key",
        "idx_analysis_history_predicted_label",
        "idx_thumbnail_cleanup_created_at",
    }
    actual_indexes = {
        str(row["name"])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index'"
        ).fetchall()
    }
    missing_indexes = expected_indexes - actual_indexes
    if missing_indexes:
        raise PersistenceError(
            "SQLite history database is missing required indexes: "
            + ", ".join(sorted(missing_indexes))
        )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
