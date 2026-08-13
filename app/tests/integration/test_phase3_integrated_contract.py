from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from lung_xray_api.application.prediction_service import PredictionResult
from lung_xray_api.core.config import load_settings
from lung_xray_api.core.exceptions import ThumbnailCleanupError
from lung_xray_api.main import create_app
from tests.conftest import FakePredictionService, make_image_bytes


def _settings(tmp_path: Path, **overrides):
    settings = replace(
        load_settings(),
        app_env="test",
        host="127.0.0.1",
        max_upload_mb=1,
        knowledge_base_path=tmp_path / "missing-production-kb.json",
        history_db_path=tmp_path / "data" / "history.db",
        thumbnail_dir=tmp_path / "data" / "thumbnails",
    )
    return replace(settings, **overrides)


def _manual_metadata(name: str = "Nguyễn Văn An") -> dict[str, str]:
    return {
        "patient_display_name": name,
        "patient_name_source": "manual",
        "patient_info_confirmed": "true",
        "is_anonymous_sample": "false",
    }


def test_identified_analysis_allows_optional_patient_code_and_missing_kb(tmp_path: Path) -> None:
    app = create_app(settings=_settings(tmp_path), prediction_service=FakePredictionService())
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/analyses",
            data=_manual_metadata(),
            files={"file": ("scan.png", make_image_bytes("PNG"), "image/png")},
        )
        detail = client.get(f"/api/v1/analyses/{response.json()['analysis_id']}")

    assert response.status_code == 201
    assert response.json()["case_metadata"]["patient_code"] is None
    assert detail.status_code == 200
    assert detail.json()["knowledge_base_version"] is None


def test_sensitive_history_and_report_responses_are_not_cacheable(tmp_path: Path) -> None:
    app = create_app(settings=_settings(tmp_path), prediction_service=FakePredictionService())
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/analyses",
            data=_manual_metadata(),
            files={"file": ("scan.png", make_image_bytes("PNG"), "image/png")},
        )
        analysis_id = created.json()["analysis_id"]
        responses = [
            client.post("/api/v1/analyses/parse-filename", json={"filename": "scan.png"}),
            client.get("/api/v1/analyses"),
            client.get(f"/api/v1/analyses/{analysis_id}"),
            client.get(f"/api/v1/analyses/{analysis_id}/thumbnail"),
            client.get(f"/api/v1/analyses/{analysis_id}/report"),
        ]

    assert all(response.status_code == 200 for response in responses)
    assert all(response.headers.get("cache-control") == "no-store" for response in responses)


def test_persisted_report_uses_patient_record_and_derived_thumbnail(tmp_path: Path) -> None:
    app = create_app(settings=_settings(tmp_path), prediction_service=FakePredictionService())
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/analyses",
            data=_manual_metadata("Trần Thị Bình"),
            files={"file": ("xray.png", make_image_bytes("PNG"), "image/png")},
        )
        response = client.get(f"/api/v1/analyses/{created.json()['analysis_id']}/report")

    assert response.status_code == 200
    assert "Trần Thị Bình" in response.text
    assert "Mã lần phân tích" in response.text
    assert "data:image/" in response.text
    assert "hệ thống không lưu ảnh gốc đầy đủ" in response.text


def test_report_preview_and_pdf_accept_only_selected_safe_visualizations(tmp_path: Path) -> None:
    app = create_app(settings=_settings(tmp_path), prediction_service=FakePredictionService())
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/analyses",
            data=_manual_metadata(),
            files={"file": ("xray.png", make_image_bytes("PNG"), "image/png")},
        )
        analysis_id = created.json()["analysis_id"]
        preview = client.get(
            f"/api/v1/analyses/{analysis_id}/report",
            params=[
                ("view", "donut-chart"),
                ("view", "column-chart"),
                ("view", "probability-bars"),
                ("view", "donut-chart"),
            ],
        )
        pdf = client.get(
            f"/api/v1/analyses/{analysis_id}/report.pdf",
            params=[("view", "column-chart"), ("view", "donut-chart"), ("view", "probability-bars")],
        )
        unsupported = client.get(
            f"/api/v1/analyses/{analysis_id}/report",
            params={"view": "untrusted-html"},
        )

    assert preview.status_code == 200
    assert preview.text.count('class="report-visualization"') == 3
    assert 'id="report-column-title"' in preview.text
    assert 'id="report-donut-title"' in preview.text
    assert 'id="report-bars-title"' in preview.text
    assert "/report.pdf?view=probability-bars&amp;view=column-chart&amp;view=donut-chart" in preview.text
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF-")
    assert unsupported.status_code == 422
    assert unsupported.json()["detail"] == "Unsupported report visualization"


def test_bounded_upload_rejects_payload_before_image_validation(tmp_path: Path) -> None:
    app = create_app(settings=_settings(tmp_path), prediction_service=FakePredictionService())
    oversized = b"x" * (1024 * 1024 + 1)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/analyses",
            data=_manual_metadata(),
            files={"file": ("large.png", oversized, "image/png")},
        )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_image"
    assert app.state.analysis_history_service.count() == 0


def test_probability_drift_is_normalized_once_for_api_and_persistence(tmp_path: Path) -> None:
    class DriftPredictionService(FakePredictionService):
        def predict_validated_image(self, validated_image):
            return PredictionResult(
                status="success",
                prediction="pneumonia",
                model_probability=0.79995,
                probabilities={"normal": 0.1, "pneumonia": 0.79995, "tuberculosis": 0.1},
                model_version="1.1.0",
                processing_time_ms=1,
                disclaimer="Kết quả học thuật, không thay thế chẩn đoán.",
            )

    app = create_app(settings=_settings(tmp_path), prediction_service=DriftPredictionService())
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/analyses",
            data=_manual_metadata(),
            files={"file": ("scan.png", make_image_bytes("PNG"), "image/png")},
        )
        record = app.state.analysis_history_service.get(response.json()["analysis_id"])

    assert response.status_code == 201
    assert sum(response.json()["probabilities"].values()) == pytest.approx(1.0)
    assert record is not None
    assert sum(
        (record.normal_probability, record.pneumonia_probability, record.tuberculosis_probability)
    ) == pytest.approx(1.0)
    assert response.json()["probabilities"]["pneumonia"] == pytest.approx(
        record.pneumonia_probability
    )


def test_failed_thumbnail_cleanup_is_queued_and_retried(tmp_path: Path, monkeypatch) -> None:
    app = create_app(settings=_settings(tmp_path), prediction_service=FakePredictionService())
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/analyses",
            data=_manual_metadata(),
            files={"file": ("scan.png", make_image_bytes("PNG"), "image/png")},
        )
        analysis_id = created.json()["analysis_id"]
        service = app.state.analysis_history_service
        record = service.get(analysis_id)
        assert record is not None and record.thumbnail_relative_path is not None
        thumbnail_path = service.thumbnail_store.thumbnail_directory / record.thumbnail_relative_path
        original_delete = service.thumbnail_store.delete_thumbnail

        def fail_once(_relative_path):
            raise ThumbnailCleanupError("simulated cleanup failure")

        monkeypatch.setattr(service.thumbnail_store, "delete_thumbnail", fail_once)
        deleted = client.delete(f"/api/v1/analyses/{analysis_id}")
        assert deleted.status_code == 200
        assert deleted.json()["cleanup_pending"] is True
        assert thumbnail_path.exists()
        assert len(service.repository.list_cleanup_jobs()) == 1

        monkeypatch.setattr(service.thumbnail_store, "delete_thumbnail", original_delete)
        service.process_cleanup_queue()
        assert not thumbnail_path.exists()
        assert service.repository.list_cleanup_jobs() == ()


def test_persisted_pdf_download_is_real_pdf_and_attachment(tmp_path: Path) -> None:
    app = create_app(settings=_settings(tmp_path), prediction_service=FakePredictionService())
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/analyses",
            data=_manual_metadata("Nguyễn Văn An"),
            files={"file": ("xray.png", make_image_bytes("PNG"), "image/png")},
        )
        analysis_id = created.json()["analysis_id"]
        response = client.get(f"/api/v1/analyses/{analysis_id}/report.pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["content-disposition"].startswith("attachment;")
    disposition = response.headers["content-disposition"]
    assert "filename*=UTF-8''" in disposition
    assert "Bao_cao_phan_loai_X-quang_phoi" in disposition
    assert "Nguyen_Van_An" in disposition
    assert "Viem_phoi" in disposition
    assert response.content.startswith(b"%PDF-")
    assert len(response.content) > 5_000


def test_pdf_download_returns_not_found_for_unknown_analysis(tmp_path: Path) -> None:
    app = create_app(settings=_settings(tmp_path), prediction_service=FakePredictionService())
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/analyses/00000000-0000-0000-0000-000000000001/report.pdf"
        )

    assert response.status_code == 404
