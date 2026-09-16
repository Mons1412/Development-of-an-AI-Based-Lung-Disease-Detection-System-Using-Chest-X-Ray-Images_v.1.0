from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import lung_xray_api.api.v1.medical_advices as medical_advices_api
from lung_xray_api.api.dependencies.auth import (
    get_current_user,
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


def make_client():

    app.dependency_overrides[
        get_db
    ] = override_db

    app.dependency_overrides[
        get_current_user
    ] = override_current_user

    return TestClient(app)


def make_advice(
    *,
    advice_id=15,
    analysis_id=123,
    language="vi",
):

    return SimpleNamespace(
        id=advice_id,
        analysis_id=analysis_id,
        language=language,
        provider="gemini",
        model_name="gemini-test",
        advice_text=(
            f"Advice {advice_id}"
        ),
        created_at=datetime(
            2026,
            9,
            17,
            2,
            0,
            0,
        ),
    )


def test_get_medical_advice_returns_200(
    monkeypatch,
):

    def fake_get(
        db,
        current_user,
        *,
        advice_id,
    ):
        assert advice_id == 15

        return make_advice(
            advice_id=15
        )

    monkeypatch.setattr(
        medical_advices_api
        .medical_advice_service,
        "get_advice",
        fake_get,
    )

    with make_client() as client:
        response = client.get(
            "/api/v1/medical-advices/15"
        )

    assert response.status_code == 200

    body = response.json()

    assert body["id"] == 15
    assert body["analysis_id"] == 123
    assert body["provider"] == "gemini"


def test_list_analysis_advices_returns_200(
    monkeypatch,
):

    expected = [
        make_advice(
            advice_id=21
        ),
        make_advice(
            advice_id=20,
            language="en",
        ),
    ]

    def fake_list(
        db,
        current_user,
        *,
        analysis_id,
    ):
        assert analysis_id == 123

        return expected

    monkeypatch.setattr(
        medical_advices_api
        .medical_advice_service,
        "list_analysis_advices",
        fake_list,
    )

    with make_client() as client:
        response = client.get(
            "/api/v1/analyses/"
            "123/medical-advices"
        )

    assert response.status_code == 200

    body = response.json()

    assert len(body) == 2
    assert body[0]["id"] == 21
    assert body[1]["id"] == 20


def test_list_analysis_advices_can_be_empty(
    monkeypatch,
):

    def fake_list(
        db,
        current_user,
        *,
        analysis_id,
    ):
        return []

    monkeypatch.setattr(
        medical_advices_api
        .medical_advice_service,
        "list_analysis_advices",
        fake_list,
    )

    with make_client() as client:
        response = client.get(
            "/api/v1/analyses/"
            "123/medical-advices"
        )

    assert response.status_code == 200
    assert response.json() == []


def test_get_unknown_advice_maps_to_404(
    monkeypatch,
):

    def fake_get(
        db,
        current_user,
        *,
        advice_id,
    ):
        raise LookupError(
            "Medical advice not found."
        )

    monkeypatch.setattr(
        medical_advices_api
        .medical_advice_service,
        "get_advice",
        fake_get,
    )

    with make_client() as client:
        response = client.get(
            "/api/v1/medical-advices/999"
        )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "Medical advice not found."
    )


def test_foreign_analysis_list_maps_to_404(
    monkeypatch,
):

    def fake_list(
        db,
        current_user,
        *,
        analysis_id,
    ):
        raise LookupError(
            "Analysis not found."
        )

    monkeypatch.setattr(
        medical_advices_api
        .medical_advice_service,
        "list_analysis_advices",
        fake_list,
    )

    with make_client() as client:
        response = client.get(
            "/api/v1/analyses/"
            "999/medical-advices"
        )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "Analysis not found."
    )


def test_retrieval_requires_authentication():

    app.dependency_overrides[
        get_db
    ] = override_db

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/medical-advices/15"
        )

    assert response.status_code == 401
