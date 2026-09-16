from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import lung_xray_api.api.v1.medical_advices as medical_advices_api
from lung_xray_api.api.dependencies.auth import (
    get_current_user,
)
from lung_xray_api.application.services.medical_advice_provider import (
    MedicalAdviceProviderConfigurationError,
    MedicalAdviceProviderError,
)
from lung_xray_api.infrastructure.persistence.database import (
    get_db,
)
from lung_xray_api.main import app


TEST_USER = SimpleNamespace(
    id=10,
    role="USER",
    is_active=True,
)


def override_db():
    yield object()


def override_current_user():
    return TEST_USER


@pytest.fixture(
    autouse=True,
)
def reset_dependency_overrides():
    app.dependency_overrides.clear()

    yield

    app.dependency_overrides.clear()


def install_generate_result(
    monkeypatch,
    outcome,
):
    def fake_generate(
        db,
        current_user,
        *,
        analysis_id,
        language,
    ):
        if isinstance(
            outcome,
            BaseException,
        ):
            raise outcome

        return outcome

    monkeypatch.setattr(
        medical_advices_api
        .medical_advice_service,
        "generate_advice",
        fake_generate,
    )


def make_authenticated_client():
    app.dependency_overrides[
        get_db
    ] = override_db

    app.dependency_overrides[
        get_current_user
    ] = override_current_user

    return TestClient(app)


def test_create_medical_advice_returns_201(
    monkeypatch,
):
    result = SimpleNamespace(
        id=15,
        analysis_id=123,
        language="vi",
        provider="gemini",
        model_name="gemini-test",
        advice_text="Generated advice",
        created_at=datetime(
            2026,
            9,
            17,
            1,
            30,
            0,
        ),
    )

    install_generate_result(
        monkeypatch,
        result,
    )

    with make_authenticated_client() as client:
        response = client.post(
            "/api/v1/medical-advices",
            json={
                "analysis_id": 123,
                "language": "vi",
            },
        )

    assert response.status_code == 201

    body = response.json()

    assert body["id"] == 15
    assert body["analysis_id"] == 123
    assert body["language"] == "vi"
    assert body["provider"] == "gemini"
    assert body["model_name"] == "gemini-test"

    assert (
        body["advice_text"]
        == "Generated advice"
    )


def test_create_medical_advice_maps_value_error_to_400(
    monkeypatch,
):
    install_generate_result(
        monkeypatch,
        ValueError(
            "Only completed analyses "
            "can generate medical advice."
        ),
    )

    with make_authenticated_client() as client:
        response = client.post(
            "/api/v1/medical-advices",
            json={
                "analysis_id": 123,
                "language": "vi",
            },
        )

    assert response.status_code == 400

    assert (
        "completed"
        in response.json()["detail"]
    )


def test_create_medical_advice_maps_lookup_error_to_404(
    monkeypatch,
):
    install_generate_result(
        monkeypatch,
        LookupError(
            "Analysis not found."
        ),
    )

    with make_authenticated_client() as client:
        response = client.post(
            "/api/v1/medical-advices",
            json={
                "analysis_id": 999,
                "language": "vi",
            },
        )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "Analysis not found."
    )


def test_create_medical_advice_maps_provider_error_to_502(
    monkeypatch,
):
    install_generate_result(
        monkeypatch,
        MedicalAdviceProviderError(
            "Gemini medical advice "
            "generation failed."
        ),
    )

    with make_authenticated_client() as client:
        response = client.post(
            "/api/v1/medical-advices",
            json={
                "analysis_id": 123,
                "language": "vi",
            },
        )

    assert response.status_code == 502


def test_create_medical_advice_maps_missing_config_to_503(
    monkeypatch,
):
    install_generate_result(
        monkeypatch,
        MedicalAdviceProviderConfigurationError(
            "Gemini API key is not configured."
        ),
    )

    with make_authenticated_client() as client:
        response = client.post(
            "/api/v1/medical-advices",
            json={
                "analysis_id": 123,
                "language": "vi",
            },
        )

    assert response.status_code == 503


def test_create_medical_advice_requires_authentication():
    app.dependency_overrides[
        get_db
    ] = override_db

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/medical-advices",
            json={
                "analysis_id": 123,
                "language": "vi",
            },
        )

    assert response.status_code == 401
