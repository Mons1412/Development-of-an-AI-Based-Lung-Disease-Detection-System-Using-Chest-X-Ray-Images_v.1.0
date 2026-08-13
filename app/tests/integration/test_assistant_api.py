from dataclasses import replace

from fastapi.testclient import TestClient

from lung_xray_api.core.config import load_settings
from lung_xray_api.main import create_app
from tests.conftest import FakePredictionService, make_image_bytes


def _prediction_context() -> dict[str, object]:
    return {
        "predicted_label": "pneumonia",
        "probabilities": {"normal": 0.08, "pneumonia": 0.87, "tuberculosis": 0.05},
        "model_version": "1.1.0",
    }


def test_assistant_query_uses_offline_production_knowledge_base(test_client: TestClient):
    response = test_client.post(
        "/api/v1/assistant/query",
        json={"message": "Hệ thống nhận file gì?", "application_stage": "before_analysis"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "answered"
    assert payload["mode"] == "offline"
    assert payload["intent"] == "supported_formats"
    assert payload["sources"] == ["PROJECT_SOURCE_V1_0_0", "MODEL_ARTIFACT_1_1_0"]
    assert 0.0 <= payload["confidence"] <= 1.0


def test_assistant_query_returns_422_for_malformed_request(test_client: TestClient):
    response = test_client.post(
        "/api/v1/assistant/query",
        json={
            "message": "Giải thích kết quả",
            "application_stage": "after_analysis",
            "prediction_context": {
                "predicted_label": "pneumonia",
                "probabilities": {"normal": 0.2, "pneumonia": 0.8},
                "model_version": "1.1.0",
            },
        },
    )

    assert response.status_code == 422


def test_missing_knowledge_base_does_not_break_prediction_endpoints(tmp_path):
    settings = replace(
        load_settings(),
        knowledge_base_path=tmp_path / "knowledge_base.production.vi.json",
        history_db_path=tmp_path / "data" / "lung_xray_history.db",
        thumbnail_dir=tmp_path / "data" / "thumbnails",
    )
    app = create_app(settings=settings, prediction_service=FakePredictionService())

    with TestClient(app) as client:
        assistant_response = client.post(
            "/api/v1/assistant/query",
            json={"message": "Ứng dụng dùng để làm gì?", "application_stage": "before_analysis"},
        )
        prediction_response = client.post(
            "/api/v1/predict",
            files={"file": ("sample.jpg", make_image_bytes("JPEG"), "image/jpeg")},
        )

    assert assistant_response.status_code == 503
    assert prediction_response.status_code == 200
    assert prediction_response.json()["prediction"] == "pneumonia"



def test_assistant_status_reports_offline_by_default(test_client: TestClient):
    response = test_client.get("/api/v1/assistant/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["active_mode"] == "offline"
    assert payload["online_available"] is False
    assert payload["provider"] == "local-retrieval"
    assert payload["state"] == "disabled"
    assert payload["configured"] is False
    assert payload["verified"] is False
