from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lung_xray_api.api.dependencies.auth import (
    require_admin,
)
from lung_xray_api.api.v1 import (
    admin as admin_api,
)
from lung_xray_api.infrastructure.persistence.database import (
    get_db,
)


class FakeAdminDashboardService:

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
                "total_users": 5,
                "active_users": 4,
                "total_patients": 3,
                "total_analyses": 20,
                "completed_analyses": 17,
                "failed_analyses": 2,
                "total_medical_advices": 6,
                "total_reports": 8,
            },
            "prediction_distribution": [
                {
                    "class_name":
                        "pneumonia",
                    "count":
                        8,
                }
            ],
            "model_usage": [
                {
                    "model_key":
                        "mobilenetv2",
                    "display_name":
                        "MobileNetV2",
                    "version":
                        "1.1.0",
                    "analysis_count":
                        20,
                }
            ],
            "recent_analyses": [
                {
                    "analysis_id":
                        100,
                    "analysis_code":
                        "AN-M13-001",
                    "patient_code":
                        "PXM13001",
                    "status":
                        "COMPLETED",
                    "model_key":
                        "mobilenetv2",
                    "model_version":
                        "1.1.0",
                    "predicted_class":
                        "pneumonia",
                    "confidence":
                        0.91,
                    "created_at":
                        datetime(
                            2026,
                            9,
                            17,
                            2,
                            0,
                        ),
                }
            ],
        }


@pytest.fixture
def dashboard_client(
    monkeypatch,
):
    fake_service = (
        FakeAdminDashboardService()
    )

    monkeypatch.setattr(
        admin_api,
        "admin_dashboard_service",
        fake_service,
    )

    test_app = FastAPI()

    test_app.include_router(
        admin_api.router
    )

    database_marker = object()

    def override_db():
        yield database_marker

    test_app.dependency_overrides[
        get_db
    ] = override_db

    test_app.dependency_overrides[
        require_admin
    ] = lambda: SimpleNamespace(
        id=99,
        role="ADMIN",
    )

    with TestClient(
        test_app
    ) as client:
        yield (
            client,
            fake_service,
            database_marker,
        )

    test_app.dependency_overrides.clear()


def test_admin_dashboard_returns_200(
    dashboard_client,
):
    (
        client,
        service,
        database_marker,
    ) = dashboard_client

    response = client.get(
        "/api/v1/admin/dashboard",
        params={
            "recent_limit": 7,
        },
    )

    assert (
        response.status_code
        == 200
    )

    body = response.json()

    assert (
        body["overview"][
            "total_analyses"
        ]
        == 20
    )

    assert (
        body[
            "prediction_distribution"
        ][0]["class_name"]
        == "pneumonia"
    )

    assert (
        body["model_usage"][
            0
        ]["model_key"]
        == "mobilenetv2"
    )

    assert (
        body["recent_analyses"][
            0
        ]["patient_code"]
        == "PXM13001"
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
        == 7
    )


def test_admin_dashboard_uses_default_recent_limit(
    dashboard_client,
):
    (
        client,
        service,
        _,
    ) = dashboard_client

    response = client.get(
        "/api/v1/admin/dashboard"
    )

    assert (
        response.status_code
        == 200
    )

    assert (
        service.calls[0][
            "recent_limit"
        ]
        == 10
    )


@pytest.mark.parametrize(
    "recent_limit",
    [
        0,
        51,
    ],
)
def test_admin_dashboard_validates_recent_limit(
    dashboard_client,
    recent_limit,
):
    (
        client,
        service,
        _,
    ) = dashboard_client

    response = client.get(
        "/api/v1/admin/dashboard",
        params={
            "recent_limit":
                recent_limit,
        },
    )

    assert (
        response.status_code
        == 422
    )

    assert service.calls == []
