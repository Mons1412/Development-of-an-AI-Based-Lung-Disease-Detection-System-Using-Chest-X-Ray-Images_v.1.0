from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lung_xray_api.api.dependencies.auth import get_current_user
from lung_xray_api.api.v1 import admin as admin_api
from lung_xray_api.application.services.admin_dashboard_service import AdminDashboardService
from lung_xray_api.infrastructure.persistence.database import get_db


class SummaryRepository:
    def get_overview(self, db):
        return dict(total_users=5, active_users=4, total_patients=3,
                    total_analyses=2, completed_analyses=1, failed_analyses=1,
                    total_medical_advices=0, total_reports=0)

    def get_prediction_distribution(self, db):
        return []

    def get_model_usage(self, db):
        return []

    def list_recent_analyses(self, *args, **kwargs):
        raise AssertionError('Summary must never read patient analysis records')


@pytest.fixture
def summary_app(monkeypatch):
    monkeypatch.setattr(admin_api, 'admin_dashboard_service',
                        AdminDashboardService(SummaryRepository()))
    app = FastAPI()
    app.include_router(admin_api.router)
    app.dependency_overrides[get_db] = lambda: None
    return app


@pytest.mark.parametrize('role', ['USER', 'ADMIN'])
def test_summary_contains_only_aggregate_data(summary_app, role):
    summary_app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=1, role=role, is_active=True)
    with TestClient(summary_app) as client:
        response = client.get('/api/v1/admin/dashboard/summary')
    assert response.status_code == 200
    assert response.json() == {
        'overview': dict(total_users=5, active_users=4, total_patients=3, total_analyses=2),
        'prediction_distribution': [], 'model_usage': [],
    }


def test_guest_cannot_read_summary(summary_app):
    with TestClient(summary_app) as client:
        assert client.get('/api/v1/admin/dashboard/summary').status_code == 401


def test_user_cannot_search_other_patients(summary_app):
    summary_app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=1, role='USER', is_active=True)
    with TestClient(summary_app) as client:
        assert client.get('/api/v1/admin/analyses',
                          params={'patient_code': 'PX123'}).status_code == 403
