from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
from typing import Literal
from uuid import uuid4

from PIL import Image
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient

from lung_xray_api.application.analysis_history_service import AnalysisHistoryService
from lung_xray_api.core.config import Settings
from lung_xray_api.core.exceptions import DatabaseBusyError, PersistenceError, SchemaVersionError
from lung_xray_api.infrastructure.ml.image_validator import ImageValidator
from lung_xray_api.infrastructure.persistence.connection import SQLiteConnectionFactory
from lung_xray_api.infrastructure.persistence.migrations import (
    LATEST_SCHEMA_VERSION,
    initialize_database,
    inspect_schema_version,
)
from lung_xray_api.infrastructure.persistence.records import AnalysisHistoryFilters
from lung_xray_api.infrastructure.persistence.thumbnail_store import ThumbnailStore
from lung_xray_api.schemas.analysis_history import AnalysisHistoryCreate
from lung_xray_api.main import create_app
from tests.conftest import FakePredictionService, make_image_bytes


def _settings(tmp_path: Path, *, busy_timeout_ms: int = 100) -> Settings:
    return Settings(
        app_env="test",
        log_level="warning",
        host="127.0.0.1",
        port=8000,
        artifact_dir=tmp_path / "artifacts",
        api_key_enabled=False,
        api_key=None,
        max_upload_mb=10,
        history_db_path=tmp_path / "data" / "lung_xray_history.db",
        thumbnail_dir=tmp_path / "data" / "thumbnails",
        thumbnail_max_dimension=512,
        history_page_size=2,
        history_busy_timeout_ms=busy_timeout_ms,
    )


def _service(tmp_path: Path, *, busy_timeout_ms: int = 100) -> AnalysisHistoryService:
    return AnalysisHistoryService.from_settings(_settings(tmp_path, busy_timeout_ms=busy_timeout_ms))


def _payload(
    *,
    analyzed_at: datetime | None = None,
    predicted_label: Literal["normal", "pneumonia", "tuberculosis"] = "pneumonia",
    patient_code: str | None = None,
    patient_display_name: str | None = None,
    original_filename: str = "case_xray.jpg",
) -> AnalysisHistoryCreate:
    anonymous = patient_code is None and patient_display_name is None
    probabilities = {
        "normal": 0.1,
        "pneumonia": 0.8,
        "tuberculosis": 0.1,
    }
    if predicted_label == "normal":
        probabilities = {"normal": 0.8, "pneumonia": 0.1, "tuberculosis": 0.1}
    elif predicted_label == "tuberculosis":
        probabilities = {"normal": 0.1, "pneumonia": 0.1, "tuberculosis": 0.8}
    return AnalysisHistoryCreate(
        patient_code=patient_code,
        patient_display_name=patient_display_name,
        patient_name_source="anonymous" if anonymous else "manual",
        patient_info_confirmed=True,
        is_anonymous_sample=anonymous,
        original_filename=original_filename,
        predicted_label=predicted_label,
        normal_probability=probabilities["normal"],
        pneumonia_probability=probabilities["pneumonia"],
        tuberculosis_probability=probabilities["tuberculosis"],
        model_version="1.1.0",
        knowledge_base_version="1.0.0",
        processing_time_ms=17,
        analyzed_at=analyzed_at or datetime.now(timezone.utc),
    )


def _validated_image():
    content = make_image_bytes("JPEG")
    return ImageValidator(max_upload_bytes=1024 * 1024).validate(
        content,
        filename="case_xray.jpg",
        content_type="image/jpeg",
    )


def test_first_and_repeated_initialization_are_idempotent(tmp_path: Path) -> None:
    database_path = tmp_path / "nested" / "data" / "history.db"
    factory = SQLiteConnectionFactory(database_path)

    assert inspect_schema_version(factory) == 0
    assert initialize_database(factory) == LATEST_SCHEMA_VERSION
    assert initialize_database(factory) == LATEST_SCHEMA_VERSION
    assert database_path.is_file()
    assert inspect_schema_version(factory) == LATEST_SCHEMA_VERSION

    with factory.read_connection() as connection:
        versions = connection.execute("SELECT version FROM schema_migrations").fetchall()
    assert [row["version"] for row in versions] == list(range(1, LATEST_SCHEMA_VERSION + 1))


def test_newer_schema_is_rejected_without_deleting_existing_data(tmp_path: Path) -> None:
    factory = SQLiteConnectionFactory(tmp_path / "data" / "history.db")
    initialize_database(factory)
    with factory.transaction() as connection:
        connection.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (LATEST_SCHEMA_VERSION + 1, datetime.now(timezone.utc).isoformat()),
        )

    with pytest.raises(SchemaVersionError):
        initialize_database(factory)
    assert inspect_schema_version(factory) == LATEST_SCHEMA_VERSION + 1


def test_lifespan_initializes_local_history_without_changing_prediction_service(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    app = create_app(settings=settings, prediction_service=FakePredictionService())

    with TestClient(app) as client:
        assert client.get("/health/ready").status_code == 200
        assert app.state.history_ready is True
        assert app.state.analysis_history_service.schema_version() == LATEST_SCHEMA_VERSION
    assert settings.history_db_path is not None
    assert settings.history_db_path.is_file()


def test_create_get_list_filter_and_delete_record_with_thumbnail(tmp_path: Path) -> None:
    service = _service(tmp_path)
    record = service.create(_payload(), _validated_image())

    assert record.thumbnail_relative_path is not None
    thumbnail_path = service.thumbnail_store.thumbnail_directory / record.thumbnail_relative_path
    assert thumbnail_path.is_file()
    assert service.get(record.id) == record
    page = service.list(filters=AnalysisHistoryFilters(predicted_label="pneumonia"))
    assert page.total == 1
    assert page.items == (record,)

    deleted = service.delete(record.id)
    assert deleted.id == record.id
    assert service.get(record.id) is None
    assert not thumbnail_path.exists()
    assert service.count() == 0


def test_pagination_and_bounded_filters(tmp_path: Path) -> None:
    service = _service(tmp_path)
    now = datetime.now(timezone.utc)
    service.create(_payload(analyzed_at=now - timedelta(minutes=2), predicted_label="normal"))
    service.create(
        _payload(
            analyzed_at=now - timedelta(minutes=1),
            patient_code="BN-001",
            patient_display_name="Nguyễn Thị Ánh",
        )
    )
    newest = service.create(_payload(analyzed_at=now, predicted_label="tuberculosis"))

    first_page = service.list(page=1, page_size=2)
    second_page = service.list(page=2, page_size=2)
    assert first_page.total == 3
    assert [item.id for item in first_page.items] == [newest.id, first_page.items[1].id]
    assert len(second_page.items) == 1
    assert service.count(AnalysisHistoryFilters(patient_code="BN-001")) == 1
    assert service.count(AnalysisHistoryFilters(patient_display_name="nguyễn")) == 1
    assert service.count(AnalysisHistoryFilters(predicted_label="normal")) == 1


def test_search_input_is_parameterized_and_unicode_patient_text_is_preserved(tmp_path: Path) -> None:
    service = _service(tmp_path)
    stored = service.create(
        _payload(patient_code="BN-ĐẶC-01", patient_display_name="Nguyễn Thị Ánh")
    )

    assert service.count(AnalysisHistoryFilters(patient_display_name="Thị Ánh")) == 1
    assert service.count(AnalysisHistoryFilters(patient_code="' OR 1=1 --")) == 0
    retrieved = service.get(stored.id)
    assert retrieved is not None
    assert retrieved.patient_display_name == "Nguyễn Thị Ánh"


def test_filename_is_sanitized_and_does_not_persist_original_image_bytes(tmp_path: Path) -> None:
    service = _service(tmp_path)
    image = _validated_image()
    record = service.create(_payload(original_filename=r"..\\sensitive/CT:case?.jpg"), image)

    assert record.original_filename == "CT_case_.jpg"
    with service.repository._connection_factory.read_connection() as connection:  # noqa: SLF001
        columns = connection.execute("PRAGMA table_info('analysis_history')").fetchall()
        stored_types = connection.execute(
            "SELECT typeof(original_filename) AS filename_type, "
            "typeof(thumbnail_relative_path) AS thumbnail_type FROM analysis_history"
        ).fetchone()
    column_names = {str(column["name"]) for column in columns}
    assert {"image", "image_bytes", "original_image", "original_image_bytes"}.isdisjoint(column_names)
    assert stored_types["filename_type"] == "text"
    assert stored_types["thumbnail_type"] == "text"
    assert image.content not in service.repository._connection_factory.database_path.read_bytes()  # noqa: SLF001


def test_thumbnail_generation_is_bounded_and_path_traversal_is_rejected(tmp_path: Path) -> None:
    service = _service(tmp_path)
    record = service.create(_payload(), _validated_image())
    assert record.thumbnail_relative_path is not None
    thumbnail_path = service.thumbnail_store.thumbnail_directory / record.thumbnail_relative_path

    with Image.open(thumbnail_path) as thumbnail:
        assert max(thumbnail.size) <= 512
    with pytest.raises(PersistenceError):
        service.thumbnail_store.delete_thumbnail("../outside.webp")
    with pytest.raises(PersistenceError):
        service.thumbnail_store.delete_thumbnail(r"C:\\outside.webp")


def test_failed_thumbnail_write_cleans_temporary_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = ThumbnailStore(tmp_path / "thumbnails", max_dimension=512)
    image = _validated_image()

    def fail_replace(_: object, __: object) -> None:
        raise OSError("simulated write failure")

    monkeypatch.setattr("lung_xray_api.infrastructure.persistence.thumbnail_store.os.replace", fail_replace)
    with pytest.raises(PersistenceError, match="Could not write analysis thumbnail"):
        store.write_thumbnail(str(uuid4()), image)

    assert list((tmp_path / "thumbnails").glob("*.tmp")) == []
    assert list((tmp_path / "thumbnails").glob("*.webp")) == []
    assert list((tmp_path / "thumbnails").glob("*.jpg")) == []


def test_database_busy_is_reported_without_silent_retry(tmp_path: Path) -> None:
    service = _service(tmp_path, busy_timeout_ms=25)
    database_path = service.repository._connection_factory.database_path  # noqa: SLF001
    lock_connection = sqlite3.connect(database_path, isolation_level=None)
    try:
        lock_connection.execute("BEGIN EXCLUSIVE")
        with pytest.raises(DatabaseBusyError):
            service.count()
    finally:
        lock_connection.rollback()
        lock_connection.close()


def test_database_delete_failure_preserves_record_and_thumbnail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service = _service(tmp_path)
    record = service.create(_payload(), _validated_image())
    assert record.thumbnail_relative_path is not None
    thumbnail_path = service.thumbnail_store.thumbnail_directory / record.thumbnail_relative_path

    def fail_delete(_: str):
        raise PersistenceError("simulated database delete failure")

    monkeypatch.setattr(service.repository, "delete_and_enqueue_cleanup", fail_delete)
    with pytest.raises(PersistenceError, match="simulated database delete failure"):
        service.delete(record.id)

    assert service.get(record.id) == record
    assert thumbnail_path.is_file()


def test_unconfirmed_or_inconsistent_case_metadata_is_not_persistable() -> None:
    with pytest.raises(ValidationError, match="patient information must be confirmed"):
        AnalysisHistoryCreate(
            **{**_payload().model_dump(), "patient_info_confirmed": False}
        )
    with pytest.raises(ValidationError, match="anonymous samples cannot store patient identifiers"):
        AnalysisHistoryCreate(
            **{
                **_payload().model_dump(),
                "patient_code": "BN-1",
                "patient_display_name": "Le A",
            },
        )
