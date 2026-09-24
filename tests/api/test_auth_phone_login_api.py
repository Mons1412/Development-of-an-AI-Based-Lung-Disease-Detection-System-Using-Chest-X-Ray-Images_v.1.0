from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from lung_xray_api.api.v1 import (
    auth as auth_api,
)
from lung_xray_api.infrastructure.persistence.database import (
    get_db,
)


def override_get_db():
    yield object()


def make_client():
    app = FastAPI()

    app.include_router(
        auth_api.router
    )

    app.dependency_overrides[
        get_db
    ] = override_get_db

    return TestClient(
        app
    )


def test_login_passes_phone_as_identifier(
    monkeypatch,
):
    calls = []

    user = SimpleNamespace(
        id=42,
        role="USER",
    )

    def fake_authenticate(
        db,
        identifier,
        password,
    ):
        del db

        calls.append(
            (
                identifier,
                password,
            )
        )

        return user

    monkeypatch.setattr(
        auth_api.auth_service,
        "authenticate_user",
        fake_authenticate,
    )

    monkeypatch.setattr(
        auth_api,
        "create_access_token",
        lambda **kwargs: (
            "test-access-token"
        ),
    )

    with make_client() as client:
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username":
                    "0901234567",
                "password":
                    "StrongPassword123!",
            },
        )

    assert response.status_code == 200

    assert response.json() == {
        "access_token":
            "test-access-token",
        "token_type":
            "bearer",
    }

    assert calls == [
        (
            "0901234567",
            "StrongPassword123!",
        )
    ]


def test_invalid_phone_or_password_returns_401(
    monkeypatch,
):
    def fake_authenticate(
        db,
        identifier,
        password,
    ):
        del db
        del identifier
        del password

        return None

    monkeypatch.setattr(
        auth_api.auth_service,
        "authenticate_user",
        fake_authenticate,
    )

    with make_client() as client:
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username":
                    "0901234567",
                "password":
                    "WrongPassword123!",
            },
        )

    assert response.status_code == 401

    assert response.json() == {
        "detail":
            "Incorrect phone or password."
    }
