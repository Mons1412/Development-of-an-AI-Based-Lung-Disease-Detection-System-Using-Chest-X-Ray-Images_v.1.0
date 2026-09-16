from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lung_xray_api.api.dependencies.auth import (
    get_current_user,
)
from lung_xray_api.api.v1 import (
    admin as admin_api,
)
from lung_xray_api.infrastructure.persistence.database import (
    get_db,
)


class FakeDashboardService:

    def __init__(self):
        self.calls = []

    def get_dashboard(
        self,
        db,
        *,
        recent_limit,
    ):
        self.calls.append(
            {
                "db": db,
                "recent_limit":
                    recent_limit,
            }
        )

        return {
            "overview": {
                "total_users": 1,
                "active_users": 1,
                "total_patients": 1,
                "total_analyses": 1,
                "completed_analyses": 1,
                "failed_analyses": 0,
                "total_medical_advices": 0,
                "total_reports": 0,
            },
            "prediction_distribution": [],
            "model_usage": [],
            "recent_analyses": [],
        }


@pytest.fixture
def dashboard_app(
    monkeypatch,
):
    fake_service = (
        FakeDashboardService()
    )

    monkeypatch.setattr(
        admin_api,
        "admin_dashboard_service",
        fake_service,
    )

    app = FastAPI()

    app.include_router(
        admin_api.router
    )

    database_marker = object()

    def override_db():
        yield database_marker

    app.dependency_overrides[
        get_db
    ] = override_db

    yield (
        app,
        fake_service,
        database_marker,
    )

    app.dependency_overrides.clear()


def test_admin_can_access_dashboard(
    dashboard_app,
):
    (
        app,
        service,
        database_marker,
    ) = dashboard_app

    app.dependency_overrides[
        get_current_user
    ] = lambda: SimpleNamespace(
        id=1,
        role="ADMIN",
        is_active=True,
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/admin/dashboard",
            params={
                "recent_limit": 8,
            },
        )

    assert (
        response.status_code
        == 200
    )

    assert len(
        service.calls
    ) == 1

    assert (
        service.calls[0]["db"]
        is database_marker
    )

    assert (
        service.calls[0][
            "recent_limit"
        ]
        == 8
    )


def test_user_cannot_access_dashboard(
    dashboard_app,
):
    (
        app,
        service,
        _,
    ) = dashboard_app

    app.dependency_overrides[
        get_current_user
    ] = lambda: SimpleNamespace(
        id=2,
        role="USER",
        is_active=True,
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/admin/dashboard"
        )

    assert (
        response.status_code
        == 403
    )

    assert response.json() == {
        "detail":
            "Administrator permission required."
    }

    assert service.calls == []


def test_unsupported_role_cannot_access_dashboard(
    dashboard_app,
):
    (
        app,
        service,
        _,
    ) = dashboard_app

    app.dependency_overrides[
        get_current_user
    ] = lambda: SimpleNamespace(
        id=3,
        role="STAFF",
        is_active=True,
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/admin/dashboard"
        )

    assert (
        response.status_code
        == 403
    )

    assert response.json() == {
        "detail":
            "Administrator permission required."
    }

    assert service.calls == []


def test_dashboard_requires_authentication(
    dashboard_app,
):
    (
        app,
        service,
        _,
    ) = dashboard_app

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/admin/dashboard"
        )

    assert (
        response.status_code
        == 401
    )

    assert service.calls == []
