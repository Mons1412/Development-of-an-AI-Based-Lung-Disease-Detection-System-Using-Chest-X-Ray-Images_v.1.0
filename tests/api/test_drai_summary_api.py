from datetime import datetime
from types import SimpleNamespace
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lung_xray_api.api.v1 import medical_advices as routes
from lung_xray_api.api.dependencies.auth import get_current_user
from lung_xray_api.infrastructure.persistence.database import get_db


@pytest.mark.parametrize('legacy', [False, True])
def test_advice_summary_is_identical_on_create_get_and_history(monkeypatch, legacy):
    text = 'Previous plain text advice.' if legacy else (
        'Risk level: MEDIUM\nSummary conclusion: Needs clinical correlation.\n'
        'Summary recommendation: Arrange a clinical review.\n')
    advice = SimpleNamespace(id=7, analysis_id=123, language='vi', provider='gemini',
        model_name='test', advice_text=text, created_at=datetime(2026,9,22))
    class Service:
        def generate_advice(self, db, user, *, analysis_id, language):
            assert analysis_id == 123
            return advice
        def get_advice(self, db, user, *, advice_id):
            assert advice_id == 7
            return advice
        def list_analysis_advices(self, db, user, *, analysis_id):
            assert analysis_id == 123
            return [advice]
    monkeypatch.setattr(routes, 'medical_advice_service', Service())
    app = FastAPI(); app.include_router(routes.router); app.include_router(routes.analysis_router)
    app.dependency_overrides[get_db] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1,role='USER')
    with TestClient(app) as client:
        created = client.post('/api/v1/medical-advices',json={'analysis_id':123,'language':'vi'})
        fetched = client.get('/api/v1/medical-advices/7')
        history = client.get('/api/v1/analyses/123/medical-advices')
    assert created.status_code == 201
    assert fetched.status_code == history.status_code == 200
    bodies = [created.json(), fetched.json(), history.json()[0]]
    for body in bodies:
        assert body['analysis_id'] == 123
        assert body['advice_text'] == text
        if legacy:
            assert body['summary'] is None
        else:
            assert body['summary'] == dict(risk_level='MEDIUM',conclusion='Needs clinical correlation.',recommendation='Arrange a clinical review.')
