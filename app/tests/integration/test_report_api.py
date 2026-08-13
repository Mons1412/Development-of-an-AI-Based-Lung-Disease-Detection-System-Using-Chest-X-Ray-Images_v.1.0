"""Integration tests for the non-persistent browser-print report preview."""

from fastapi.testclient import TestClient


def _report_payload(**overrides: object) -> dict[str, object]:
    prediction: dict[str, object] = {
        "predicted_label": "pneumonia",
        "probabilities": {
            "normal": 0.08,
            "pneumonia": 0.87,
            "tuberculosis": 0.05,
        },
        "model_version": "1.1.0",
        "processing_time_ms": 720,
        "analysis_timestamp": "2026-07-27T00:00:00+00:00",
    }
    payload: dict[str, object] = {
        "filename": "xray_01.png",
        "prediction": prediction,
    }
    payload.update(overrides)
    return payload


def test_report_preview_contains_only_controlled_current_prediction_data(
    test_client: TestClient,
) -> None:
    response = test_client.post("/api/v1/report/preview", json=_report_payload())

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Báo cáo kết quả phân loại ảnh X-quang phổi" in response.text
    assert "Hệ thống phân loại ảnh X-quang phổi bằng MobileNetV2" in response.text
    assert "Đại học Nguyễn Tất Thành" in response.text
    assert "27/07/2026 07:00:00 UTC+7" in response.text
    assert "xray_01.png" in response.text
    assert "Viêm phổi" in response.text
    assert "pneumonia" in response.text
    assert "87.00%" in response.text
    assert "MODEL_ARTIFACT_1_1_0" in response.text
    assert "PROJECT_SOURCE_V1_0_0" in response.text
    assert "Nội dung chuyên môn đang chờ duyệt" in response.text
    assert "Lê Đoàn Anh Tuấn" in response.text


def test_report_preview_rejects_missing_prediction(test_client: TestClient) -> None:
    response = test_client.post(
        "/api/v1/report/preview",
        json={"filename": "xray_01.png"},
    )

    assert response.status_code == 422


def test_report_preview_sanitizes_malicious_filename_and_rejects_content_injection(
    test_client: TestClient,
) -> None:
    response = test_client.post(
        "/api/v1/report/preview",
        json=_report_payload(filename=r"..\\..\\<img src=x onerror=alert(1)>.png"),
    )

    assert response.status_code == 200
    assert "<img src=x onerror=alert(1)>.png" not in response.text
    assert "img src_x onerror_alert(1)_.png" in response.text

    content_injection = test_client.post(
        "/api/v1/report/preview",
        json=_report_payload(disclaimer="<script>alert(1)</script>"),
    )
    assert content_injection.status_code == 422

    invalid_model_version_payload = _report_payload(
        prediction={
            "predicted_label": "pneumonia",
            "probabilities": {
                "normal": 0.08,
                "pneumonia": 0.87,
                "tuberculosis": 0.05,
            },
            "model_version": "<script>alert(1)</script>",
            "processing_time_ms": 720,
            "analysis_timestamp": "2026-07-27T00:00:00+00:00",
        }
    )
    invalid_model_version = test_client.post(
        "/api/v1/report/preview",
        json=invalid_model_version_payload,
    )
    assert invalid_model_version.status_code == 422

    inconsistent_prediction = test_client.post(
        "/api/v1/report/preview",
        json=_report_payload(
            prediction={
                "predicted_label": "normal",
                "probabilities": {
                    "normal": 0.08,
                    "pneumonia": 0.87,
                    "tuberculosis": 0.05,
                },
                "model_version": "1.1.0",
                "processing_time_ms": 720,
                "analysis_timestamp": "2026-07-27T00:00:00+00:00",
            }
        ),
    )
    assert inconsistent_prediction.status_code == 422


def test_report_preview_supports_repeated_export_without_server_state(
    test_client: TestClient,
) -> None:
    first = test_client.post("/api/v1/report/preview", json=_report_payload())
    second = test_client.post("/api/v1/report/preview", json=_report_payload())

    assert first.status_code == 200
    assert second.status_code == 200
    assert "set-cookie" not in first.headers
    assert "set-cookie" not in second.headers
    assert "/tmp/" not in first.text
    assert "/tmp/" not in second.text
