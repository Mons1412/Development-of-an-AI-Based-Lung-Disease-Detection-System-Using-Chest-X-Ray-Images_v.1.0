import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from lung_xray_api.api.v1 import (
    health as health_api,
)


@pytest.fixture
def health_app():
    app = FastAPI()

    app.include_router(
        health_api.router
    )

    return app


def test_liveness_does_not_probe_database(
    health_app,
    monkeypatch,
):
    def forbidden_database_probe():
        raise AssertionError(
            "Liveness must not probe "
            "the database."
        )

    monkeypatch.setattr(
        health_api,
        "check_database_connection",
        forbidden_database_probe,
    )

    with TestClient(
        health_app
    ) as client:
        response = client.get(
            "/health/live"
        )

    assert (
        response.status_code
        == 200
    )

    payload = response.json()

    assert (
        payload["status"]
        == "ok"
    )

    assert (
        payload["service"]
        == "LungXrayAI"
    )


def test_readiness_returns_200_when_database_is_ready(
    health_app,
    monkeypatch,
):
    calls = []

    def successful_database_probe():
        calls.append(
            "called"
        )
        return True

    monkeypatch.setattr(
        health_api,
        "check_database_connection",
        successful_database_probe,
    )

    with TestClient(
        health_app
    ) as client:
        response = client.get(
            "/health/ready"
        )

    assert (
        response.status_code
        == 200
    )

    assert response.json() == {
        "status": "ready",
        "database": "connected",
    }

    assert calls == [
        "called"
    ]


def test_readiness_returns_503_when_database_probe_returns_false(
    health_app,
    monkeypatch,
):
    monkeypatch.setattr(
        health_api,
        "check_database_connection",
        lambda: False,
    )

    with TestClient(
        health_app
    ) as client:
        response = client.get(
            "/health/ready"
        )

    assert (
        response.status_code
        == 503
    )

    assert response.json() == {
        "detail":
            "Database is not ready."
    }


def test_readiness_returns_503_and_hides_database_error_details(
    health_app,
    monkeypatch,
):
    secret_marker = (
        "M14_SECRET_MUST_NOT_LEAK"
    )

    def failed_database_probe():
        raise SQLAlchemyError(
            "Database connection failed: "
            + secret_marker
        )

    monkeypatch.setattr(
        health_api,
        "check_database_connection",
        failed_database_probe,
    )

    with TestClient(
        health_app
    ) as client:
        response = client.get(
            "/health/ready"
        )

    assert (
        response.status_code
        == 503
    )

    assert response.json() == {
        "detail":
            "Database is not ready."
    }

    assert (
        secret_marker
        not in response.text
    )


def test_readiness_does_not_hide_unexpected_programming_errors(
    health_app,
    monkeypatch,
):
    def unexpected_failure():
        raise RuntimeError(
            "Unexpected application bug"
        )

    monkeypatch.setattr(
        health_api,
        "check_database_connection",
        unexpected_failure,
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "Unexpected application bug"
        ),
    ):
        with TestClient(
            health_app
        ) as client:
            client.get(
                "/health/ready"
            )


@pytest.mark.skipif(
    os.getenv(
        "RUN_MYSQL_INTEGRATION"
    ) != "1",
    reason=(
        "Real MySQL readiness test "
        "requires "
        "RUN_MYSQL_INTEGRATION=1."
    ),
)
def test_readiness_with_real_mysql(
    health_app,
):
    with TestClient(
        health_app
    ) as client:
        response = client.get(
            "/health/ready"
        )

    assert (
        response.status_code
        == 200
    )

    assert response.json() == {
        "status": "ready",
        "database": "connected",
    }
