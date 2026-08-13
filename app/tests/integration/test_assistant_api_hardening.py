from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def _valid_prediction_context() -> dict[str, object]:
    return {
        "predicted_label": "pneumonia",
        "probabilities": {"normal": 0.08, "pneumonia": 0.87, "tuberculosis": 0.05},
        "model_version": "1.1.0",
    }


@pytest.mark.parametrize(
    "payload",
    [
        {"message": "   "},
        {"message": "a" * 1501},
        {
            "message": "Giải thích kết quả",
            "application_stage": "after_analysis",
            "prediction_context": {
                **_valid_prediction_context(),
                "predicted_label": "unsupported_label",
            },
        },
        {
            "message": "Giải thích kết quả",
            "application_stage": "after_analysis",
            "prediction_context": {
                **_valid_prediction_context(),
                "probabilities": {"normal": 0.1, "pneumonia": 0.8},
            },
        },
        {
            "message": "Giải thích kết quả",
            "application_stage": "after_analysis",
            "prediction_context": {
                **_valid_prediction_context(),
                "probabilities": {"normal": 0.1, "pneumonia": 0.8, "tuberculosis": 0.0998},
            },
        },
        {
            "message": "Giải thích kết quả",
            "application_stage": "after_analysis",
            "prediction_context": {
                **_valid_prediction_context(),
                "probabilities": {"normal": "not-a-number", "pneumonia": 0.8, "tuberculosis": 0.1},
            },
        },
        {
            "message": "Giải thích kết quả",
            "application_stage": "after_analysis",
            "prediction_context": {
                **_valid_prediction_context(),
                "probabilities": {"normal": True, "pneumonia": 0.0, "tuberculosis": 0.0},
            },
        },
        {
            "message": "Giải thích kết quả",
            "application_stage": "after_analysis",
            "prediction_context": {
                **_valid_prediction_context(),
                "predicted_label": "normal",
            },
        },
        {
            "message": "Giải thích kết quả",
            "application_stage": "after_analysis",
            "prediction_context": {
                **_valid_prediction_context(),
                "patient_code": "MUST_NOT_BE_ACCEPTED",
            },
        },
    ],
)
def test_assistant_api_rejects_blank_oversized_or_malformed_input(
    test_client: TestClient,
    payload: dict[str, object],
):
    response = test_client.post("/api/v1/assistant/query", json=payload)

    assert response.status_code == 422


def test_assistant_api_accepts_unicode_vietnamese_input(test_client: TestClient):
    response = test_client.post(
        "/api/v1/assistant/query",
        json={"message": "HỆ THỐNG NHẬN FILE GÌ?", "application_stage": "before_analysis"},
    )

    assert response.status_code == 200
    assert response.json()["intent"] == "supported_formats"


def test_assistant_api_returns_deterministic_response_for_repeated_requests(test_client: TestClient):
    payload = {"message": "Hệ thống nhận file gì?", "application_stage": "before_analysis"}
    responses = [test_client.post("/api/v1/assistant/query", json=payload) for _ in range(3)]

    assert [response.status_code for response in responses] == [200, 200, 200]
    payloads = [response.json() for response in responses]
    request_ids = {payload.pop("request_id") for payload in payloads}
    assert len(request_ids) == 3
    assert payloads[0] == payloads[1] == payloads[2]


def test_assistant_api_handles_after_analysis_missing_context_and_failed_analysis(test_client: TestClient):
    missing_context = test_client.post(
        "/api/v1/assistant/query",
        json={"message": "Giải thích kết quả", "application_stage": "after_analysis"},
    )
    failed_analysis = test_client.post(
        "/api/v1/assistant/query",
        json={
            "message": "Giải thích kết quả",
            "application_stage": "analysis_failed",
            "prediction_context": _valid_prediction_context(),
        },
    )

    assert missing_context.status_code == 200
    assert failed_analysis.status_code == 200
    assert missing_context.json()["status"] == "needs_prediction"
    assert failed_analysis.json()["status"] == "needs_prediction"


def test_assistant_api_does_not_reuse_context_after_client_resets_to_before_analysis(
    test_client: TestClient,
):
    completed = test_client.post(
        "/api/v1/assistant/query",
        json={
            "message": "Giải thích kết quả và xác suất",
            "application_stage": "after_analysis",
            "prediction_context": _valid_prediction_context(),
        },
    )
    reset = test_client.post(
        "/api/v1/assistant/query",
        json={"message": "Giải thích kết quả và xác suất", "application_stage": "before_analysis"},
    )

    assert completed.status_code == 200
    assert completed.json()["intent"] == "explain_current_prediction"
    assert reset.status_code == 200
    assert reset.json()["status"] == "needs_prediction"
    assert reset.json()["intent"] == "no_prediction"


def test_assistant_handles_basic_conversation_without_external_ai(test_client: TestClient):
    greeting = test_client.post(
        "/api/v1/assistant/query",
        json={"message": "hi bạn", "application_stage": "before_analysis"},
    )
    capabilities = test_client.post(
        "/api/v1/assistant/query",
        json={"message": "bạn hỗ trợ gì?", "application_stage": "before_analysis"},
    )

    assert greeting.status_code == 200
    assert greeting.json()["status"] == "answered"
    assert greeting.json()["intent"] == "greeting"
    assert capabilities.status_code == 200
    assert capabilities.json()["status"] == "answered"
    assert capabilities.json()["mode"] == "offline"
