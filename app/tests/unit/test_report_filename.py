from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import quote

from lung_xray_api.application.report_filename import (
    build_content_disposition,
    build_report_filename,
)
from lung_xray_api.infrastructure.persistence.records import AnalysisHistoryRecord


def _record(**overrides: object) -> AnalysisHistoryRecord:
    values: dict[str, object] = {
        "id": "e5c0ae27-1d2f-450b-ba34-e912ed94295c",
        "patient_code": "BN001",
        "patient_display_name": "Nguyễn Văn An",
        "patient_name_search_key": "nguyen van an",
        "patient_name_source": "manual",
        "patient_info_confirmed": True,
        "is_anonymous_sample": False,
        "filename_pattern_id": None,
        "parsed_filename_date": None,
        "original_filename": "xray.png",
        "thumbnail_relative_path": "e5c0ae27.webp",
        "predicted_label": "pneumonia",
        "normal_probability": 0.08,
        "pneumonia_probability": 0.9,
        "tuberculosis_probability": 0.02,
        "model_version": "1.1.0",
        "knowledge_base_version": "1.0.0",
        "prediction_disclaimer": "Kết quả học thuật, không thay thế chẩn đoán.",
        "reference_source_ids": ("MODEL_ARTIFACT_1_1_0",),
        "processing_time_ms": 438,
        "analyzed_at": datetime(2026, 7, 27, 5, 38, 40, tzinfo=timezone.utc),
        "created_at": datetime(2026, 7, 27, 5, 38, 41, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return AnalysisHistoryRecord(**values)  # type: ignore[arg-type]


def test_identified_report_filename_is_vietnamese_and_case_specific() -> None:
    filename = build_report_filename(_record())

    assert filename.startswith("Báo cáo phân loại X-quang phổi")
    assert "BN001 - Nguyễn Văn An" in filename
    assert " - Viêm phổi - " in filename
    assert "20260727-123840" in filename
    assert filename.endswith(".pdf")


def test_anonymous_report_filename_is_stable_and_not_patient_like() -> None:
    record = _record(
        patient_code=None,
        patient_display_name=None,
        patient_name_search_key=None,
        patient_name_source="anonymous",
        is_anonymous_sample=True,
        predicted_label="normal",
        normal_probability=0.8,
        pneumonia_probability=0.1,
        tuberculosis_probability=0.1,
    )

    filename = build_report_filename(record)

    assert "Ca ẩn danh" in filename
    assert " - Bình thường - " in filename
    assert "e5c0ae27" in filename
    assert "Người bệnh ẩn danh" not in filename


def test_content_disposition_has_ascii_fallback_and_utf8_filename() -> None:
    filename = build_report_filename(_record())
    header = build_content_disposition(filename)

    assert header.startswith('attachment; filename="')
    assert "filename*=UTF-8''" in header
    assert quote(filename, safe="") in header
    assert "\r" not in header
    assert "\n" not in header
