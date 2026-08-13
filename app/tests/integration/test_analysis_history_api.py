from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from lung_xray_api.core.config import load_settings
from lung_xray_api.core.exceptions import ModelRuntimeError, PersistenceError
from lung_xray_api.main import create_app
from tests.conftest import FakePredictionService, make_image_bytes


def _settings(tmp_path: Path, *, host: str = "127.0.0.1"):
    data_root = tmp_path / "data"
    return replace(
        load_settings(),
        app_env="test",
        host=host,
        history_db_path=data_root / "lung_xray_history.db",
        thumbnail_dir=data_root / "thumbnails",
    )


@pytest.fixture
def analysis_app(tmp_path: Path):
    app = create_app(settings=_settings(tmp_path), prediction_service=FakePredictionService())
    with TestClient(app) as client:
        yield app, client


def _filename_metadata(
    *,
    patient_code: str = "BN001",
    patient_display_name: str = "NGUYEN VAN A",
    source: str = "filename",
) -> dict[str, str]:
    return {
        "patient_code": patient_code,
        "patient_display_name": patient_display_name,
        "patient_name_source": source,
        "patient_info_confirmed": "true",
        "is_anonymous_sample": "false",
    }


def _create_analysis(
    client: TestClient,
    *,
    filename: str = "BN001__NGUYEN_VAN_A__20260726.png",
    metadata: dict[str, str] | None = None,
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/analyses",
        data=metadata if metadata is not None else _filename_metadata(),
        files={"file": (filename, make_image_bytes("PNG"), "image/png")},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_parse_filename_endpoint_is_strict_and_requires_confirmation(analysis_app) -> None:
    _, client = analysis_app

    response = client.post(
        "/api/v1/analyses/parse-filename",
        json={"filename": "PT-0007__TRẦN_THỊ_B__20260726.jpg"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "matched": True,
        "patient_code": "PT-0007",
        "patient_display_name": "TRẦN THỊ B",
        "parsed_date": "2026-07-26",
        "source": "filename",
        "validation_warnings": [],
        "requires_confirmation": True,
    }

    invalid = client.post(
        "/api/v1/analyses/parse-filename",
        json={"filename": "image_001.png"},
    )
    assert invalid.status_code == 200
    assert invalid.json()["matched"] is False
    assert invalid.json()["patient_code"] is None


def test_successful_filename_analysis_persists_only_a_thumbnail(analysis_app) -> None:
    app, client = analysis_app
    payload = _create_analysis(client)

    assert payload["analysis_id"]
    assert payload["storage"] == {"status": "persisted", "persisted": True}
    assert payload["case_metadata"] == {
        "patient_code": "BN001",
        "patient_display_name": "NGUYEN VAN A",
        "patient_name_source": "filename",
        "patient_info_confirmed": True,
        "is_anonymous_sample": False,
    }

    record = app.state.analysis_history_service.get(payload["analysis_id"])
    assert record is not None
    assert record.thumbnail_relative_path is not None
    assert record.original_filename == "BN001__NGUYEN_VAN_A__20260726.png"
    assert (app.state.analysis_history_service.thumbnail_store.thumbnail_directory / record.thumbnail_relative_path).is_file()


def test_manual_override_is_preserved_and_anonymous_case_stores_no_identifiers(analysis_app) -> None:
    _, client = analysis_app
    manual = _create_analysis(
        client,
        metadata=_filename_metadata(
            patient_display_name="Trần Thị B",
            source="manual",
        ),
    )
    anonymous = _create_analysis(
        client,
        filename="demo_image.png",
        metadata={
            "patient_name_source": "anonymous",
            "patient_info_confirmed": "true",
            "is_anonymous_sample": "true",
        },
    )

    assert manual["case_metadata"]["patient_display_name"] == "Trần Thị B"
    assert manual["case_metadata"]["patient_name_source"] == "manual"
    assert anonymous["case_metadata"] == {
        "patient_code": None,
        "patient_display_name": None,
        "patient_name_source": "anonymous",
        "patient_info_confirmed": True,
        "is_anonymous_sample": True,
    }


def test_invalid_or_unconfirmed_metadata_never_starts_persisted_analysis(analysis_app) -> None:
    app, client = analysis_app
    invalid = client.post(
        "/api/v1/analyses",
        data={
            **_filename_metadata(),
            "patient_info_confirmed": "false",
        },
        files={"file": ("BN001__NGUYEN_VAN_A__20260726.png", make_image_bytes("PNG"), "image/png")},
    )
    missing_confirmation = client.post(
        "/api/v1/analyses",
        data={
            "patient_code": "BN001",
            "patient_display_name": "NGUYEN VAN A",
            "patient_name_source": "manual",
            "is_anonymous_sample": "false",
        },
        files={"file": ("sample.png", make_image_bytes("PNG"), "image/png")},
    )
    markup = client.post(
        "/api/v1/analyses",
        data=_filename_metadata(patient_display_name="<b>NGUYEN VAN A</b>", source="manual"),
        files={"file": ("sample.png", make_image_bytes("PNG"), "image/png")},
    )

    assert invalid.status_code == 422
    assert missing_confirmation.status_code == 422
    assert markup.status_code == 422
    assert app.state.analysis_history_service.count() == 0
    assert "NGUYEN" not in invalid.text
    assert "<b>" not in markup.text


def test_filename_source_must_match_server_parser_without_overwriting_manual_values(analysis_app) -> None:
    app, client = analysis_app
    response = client.post(
        "/api/v1/analyses",
        data=_filename_metadata(patient_display_name="NGUYEN VAN B"),
        files={"file": ("BN001__NGUYEN_VAN_A__20260726.png", make_image_bytes("PNG"), "image/png")},
    )

    assert response.status_code == 422
    assert app.state.analysis_history_service.count() == 0


def test_history_list_filter_pagination_detail_thumbnail_and_delete(analysis_app) -> None:
    _, client = analysis_app
    first = _create_analysis(client, metadata=_filename_metadata(patient_code="BN001"))
    second = _create_analysis(
        client,
        filename="PT-0007__TRAN_THI_B__20260726.png",
        metadata=_filename_metadata(patient_code="PT-0007", patient_display_name="TRAN THI B"),
    )

    page = client.get("/api/v1/analyses", params={"page": 1, "page_size": 1, "sort_order": "asc"})
    filtered = client.get("/api/v1/analyses", params={"patient_query": "PT-0007"})
    label_filtered = client.get("/api/v1/analyses", params={"predicted_label": "pneumonia"})
    vietnam_timezone = timezone(timedelta(hours=7))
    record_local_date = (
        datetime.fromisoformat(first["analyzed_at"])
        .astimezone(vietnam_timezone)
        .date()
    )
    today = record_local_date.isoformat()
    tomorrow = (record_local_date + timedelta(days=1)).isoformat()
    date_filtered = client.get("/api/v1/analyses", params={"date_from": today, "date_to": today})
    future_filtered = client.get("/api/v1/analyses", params={"date_from": tomorrow, "date_to": tomorrow})
    injection_shaped = client.get("/api/v1/analyses", params={"patient_query": "' OR 1=1 --"})
    detail = client.get(f"/api/v1/analyses/{first['analysis_id']}")
    thumbnail = client.get(f"/api/v1/analyses/{first['analysis_id']}/thumbnail")

    assert page.status_code == 200
    assert page.json()["total"] == 2
    assert len(page.json()["items"]) == 1
    assert filtered.status_code == 200
    assert [item["analysis_id"] for item in filtered.json()["items"]] == [second["analysis_id"]]
    assert label_filtered.status_code == 200
    assert label_filtered.json()["total"] == 2
    assert date_filtered.status_code == 200
    assert date_filtered.json()["total"] == 2
    assert future_filtered.status_code == 200
    assert future_filtered.json()["total"] == 0
    assert injection_shaped.status_code == 200
    assert injection_shaped.json()["total"] == 0
    assert detail.status_code == 200
    assert detail.json()["thumbnail_url"] == f"/api/v1/analyses/{first['analysis_id']}/thumbnail"
    assert thumbnail.status_code == 200
    assert thumbnail.headers["x-content-type-options"] == "nosniff"
    assert thumbnail.headers["cache-control"] == "no-store"
    assert thumbnail.headers["content-type"].startswith("image/")

    deleted = client.delete(f"/api/v1/analyses/{first['analysis_id']}")
    assert deleted.status_code == 200
    assert deleted.json() == {"status": "deleted", "analysis_id": first["analysis_id"], "cleanup_pending": False}
    assert client.get(f"/api/v1/analyses/{first['analysis_id']}").status_code == 404
    assert client.get(f"/api/v1/analyses/{first['analysis_id']}/thumbnail").status_code == 404


def test_inference_and_storage_failures_do_not_create_records(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class FailingPredictionService(FakePredictionService):
        def predict_validated_image(self, validated_image):
            raise ModelRuntimeError("simulated inference failure")

    app = create_app(settings=_settings(tmp_path), prediction_service=FailingPredictionService())
    with TestClient(app) as client:
        inference_failure = client.post(
            "/api/v1/analyses",
            data=_filename_metadata(),
            files={"file": ("BN001__NGUYEN_VAN_A__20260726.png", make_image_bytes("PNG"), "image/png")},
        )
        assert inference_failure.status_code == 503
        assert app.state.analysis_history_service.count() == 0

    app = create_app(settings=_settings(tmp_path / "storage"), prediction_service=FakePredictionService())
    with TestClient(app) as client:
        def fail_thumbnail(*_args, **_kwargs):
            raise PersistenceError("simulated storage failure")

        monkeypatch.setattr(app.state.analysis_history_service.thumbnail_store, "write_thumbnail", fail_thumbnail)
        storage_failure = client.post(
            "/api/v1/analyses",
            data=_filename_metadata(),
            files={"file": ("BN001__NGUYEN_VAN_A__20260726.png", make_image_bytes("PNG"), "image/png")},
        )
        assert storage_failure.status_code == 503
        assert storage_failure.json()["code"] == "analysis_storage_unavailable"
        assert app.state.analysis_history_service.count() == 0


def test_legacy_prediction_remains_non_persistent_and_path_attempts_are_rejected(analysis_app) -> None:
    app, client = analysis_app
    legacy = client.post(
        "/api/v1/predict",
        files={"file": ("xray.jpg", make_image_bytes("JPEG"), "image/jpeg")},
    )
    invalid_identifier = client.get("/api/v1/analyses/not-a-uuid/thumbnail")
    traversal = client.get("/api/v1/analyses/%2E%2E%2F%2E%2E%2Fvar%2Fdata")

    assert legacy.status_code == 200
    assert "analysis_id" not in legacy.json()
    assert app.state.analysis_history_service.count() == 0
    assert invalid_identifier.status_code == 422
    assert "not-a-uuid" not in invalid_identifier.text
    assert traversal.status_code in {404, 422}


def test_history_is_not_available_when_configured_for_a_non_loopback_host(tmp_path: Path) -> None:
    app = create_app(
        settings=_settings(tmp_path, host="0.0.0.0"),
        prediction_service=FakePredictionService(),
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/analyses/parse-filename",
            json={"filename": "BN001__NGUYEN_VAN_A__20260726.png"},
        )
    assert response.status_code == 403


def test_invalid_patient_code_returns_safe_field_error(analysis_app) -> None:
    app, client = analysis_app
    response = client.post(
        "/api/v1/analyses",
        data={
            "patient_code": "văn A",
            "patient_display_name": "Văn A",
            "patient_name_source": "manual",
            "patient_info_confirmed": "true",
            "is_anonymous_sample": "false",
        },
        files={"file": ("image_2026-07-27.png", make_image_bytes("PNG"), "image/png")},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "invalid_case_metadata"
    assert "patient_code" in detail["field_errors"]
    assert "văn A" not in response.text
    assert app.state.analysis_history_service.count() == 0
