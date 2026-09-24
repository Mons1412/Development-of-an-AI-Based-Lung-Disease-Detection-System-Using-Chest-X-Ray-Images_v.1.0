from types import SimpleNamespace

import pytest
from fastapi import (
    FastAPI,
    HTTPException,
    status,
)
from fastapi.testclient import TestClient

from lung_xray_api.api.dependencies.auth import (
    require_admin,
    require_user,
)
from lung_xray_api.api.v1.admin import (
    router as admin_router,
)
from lung_xray_api.api.v1.analyses import (
    router as analyses_router,
)
from lung_xray_api.application.services.analysis_service import (
    analysis_service,
)
from lung_xray_api.infrastructure.persistence.database import (
    get_db,
)


@pytest.fixture
def app():
    test_app = FastAPI()

    test_app.include_router(
        analyses_router
    )

    test_app.include_router(
        admin_router
    )

    return test_app


@pytest.fixture
def user():
    return SimpleNamespace(
        id=10,
        role="USER",
    )


@pytest.fixture
def admin():
    return SimpleNamespace(
        id=99,
        role="ADMIN",
    )


def test_user_history_defaults(
    app,
    user,
    monkeypatch,
):
    fake_db = object()
    captured = {}

    def override_db():
        return fake_db

    def override_user():
        return user

    def fake_list(
        db,
        current_user,
        *,
        patient_code=None,
        limit=20,
        offset=0,
    ):
        captured["db"] = db
        captured["user"] = current_user
        captured["patient_code"] = patient_code
        captured["limit"] = limit
        captured["offset"] = offset

        return []

    app.dependency_overrides[
        get_db
    ] = override_db

    app.dependency_overrides[
        require_user
    ] = override_user

    monkeypatch.setattr(
        analysis_service,
        "list_my_analyses",
        fake_list,
    )

    client = TestClient(
        app
    )

    response = client.get(
        "/api/v1/analyses"
    )

    assert response.status_code == 200
    assert response.json() == []

    assert captured[
        "db"
    ] is fake_db

    assert captured[
        "user"
    ] is user

    assert captured[
        "patient_code"
    ] is None

    assert captured[
        "limit"
    ] == 20

    assert captured[
        "offset"
    ] == 0


def test_user_history_query_parameters(
    app,
    user,
    monkeypatch,
):
    captured = {}

    app.dependency_overrides[
        get_db
    ] = lambda: object()

    app.dependency_overrides[
        require_user
    ] = lambda: user

    def fake_list(
        db,
        current_user,
        *,
        patient_code=None,
        limit=20,
        offset=0,
    ):
        captured["patient_code"] = (
            patient_code
        )
        captured["limit"] = limit
        captured["offset"] = offset

        return []

    monkeypatch.setattr(
        analysis_service,
        "list_my_analyses",
        fake_list,
    )

    client = TestClient(
        app
    )

    response = client.get(
        "/api/v1/analyses",
        params={
            "patient_code": "PXTEST001",
            "limit": 5,
            "offset": 2,
        },
    )

    assert response.status_code == 200

    assert captured == {
        "patient_code": "PXTEST001",
        "limit": 5,
        "offset": 2,
    }


def test_user_other_patient_maps_to_404(
    app,
    user,
    monkeypatch,
):
    app.dependency_overrides[
        get_db
    ] = lambda: object()

    app.dependency_overrides[
        require_user
    ] = lambda: user

    def fake_list(
        db,
        current_user,
        **kwargs,
    ):
        raise LookupError(
            "Patient not found."
        )

    monkeypatch.setattr(
        analysis_service,
        "list_my_analyses",
        fake_list,
    )

    client = TestClient(
        app
    )

    response = client.get(
        "/api/v1/analyses",
        params={
            "patient_code": "PXOTHER",
        },
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Patient not found."
    }


def test_user_history_limit_validation(
    app,
    user,
):
    app.dependency_overrides[
        get_db
    ] = lambda: object()

    app.dependency_overrides[
        require_user
    ] = lambda: user

    client = TestClient(
        app
    )

    response = client.get(
        "/api/v1/analyses",
        params={
            "limit": 101,
        },
    )

    assert response.status_code == 422


def test_user_history_offset_validation(
    app,
    user,
):
    app.dependency_overrides[
        get_db
    ] = lambda: object()

    app.dependency_overrides[
        require_user
    ] = lambda: user

    client = TestClient(
        app
    )

    response = client.get(
        "/api/v1/analyses",
        params={
            "offset": -1,
        },
    )

    assert response.status_code == 422


def test_admin_can_query_patient_history(
    app,
    admin,
    monkeypatch,
):
    captured = {}

    app.dependency_overrides[
        get_db
    ] = lambda: object()

    app.dependency_overrides[
        require_admin
    ] = lambda: admin

    def fake_admin_list(
        db,
        *,
        patient_code,
        limit=20,
        offset=0,
    ):
        captured["patient_code"] = (
            patient_code
        )
        captured["limit"] = limit
        captured["offset"] = offset

        return []

    monkeypatch.setattr(
        analysis_service,
        "list_patient_analyses_for_admin",
        fake_admin_list,
    )

    client = TestClient(
        app
    )

    response = client.get(
        "/api/v1/admin/analyses",
        params={
            "patient_code": "PXADMIN001",
            "limit": 10,
            "offset": 3,
        },
    )

    assert response.status_code == 200
    assert response.json() == []

    assert captured == {
        "patient_code": "PXADMIN001",
        "limit": 10,
        "offset": 3,
    }


def test_admin_unknown_patient_maps_to_404(
    app,
    admin,
    monkeypatch,
):
    app.dependency_overrides[
        get_db
    ] = lambda: object()

    app.dependency_overrides[
        require_admin
    ] = lambda: admin

    def fake_admin_list(
        db,
        **kwargs,
    ):
        raise LookupError(
            "Patient not found."
        )

    monkeypatch.setattr(
        analysis_service,
        "list_patient_analyses_for_admin",
        fake_admin_list,
    )

    client = TestClient(
        app
    )

    response = client.get(
        "/api/v1/admin/analyses",
        params={
            "patient_code": "PXUNKNOWN",
        },
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Patient not found."
    }


def test_admin_endpoint_requires_admin_dependency(
    app,
    monkeypatch,
):
    called = False

    app.dependency_overrides[
        get_db
    ] = lambda: object()

    def deny_admin():
        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
            ),
            detail="Admin access required.",
        )

    app.dependency_overrides[
        require_admin
    ] = deny_admin

    def fake_admin_list(
        db,
        **kwargs,
    ):
        nonlocal called

        called = True

        return []

    monkeypatch.setattr(
        analysis_service,
        "list_patient_analyses_for_admin",
        fake_admin_list,
    )

    client = TestClient(
        app
    )

    response = client.get(
        "/api/v1/admin/analyses",
        params={
            "patient_code": "PXADMIN001",
        },
    )

    assert response.status_code == 403
    assert called is False


def test_admin_limit_validation(
    app,
    admin,
):
    app.dependency_overrides[
        get_db
    ] = lambda: object()

    app.dependency_overrides[
        require_admin
    ] = lambda: admin

    client = TestClient(
        app
    )

    response = client.get(
        "/api/v1/admin/analyses",
        params={
            "patient_code": "PXADMIN001",
            "limit": 101,
        },
    )

    assert response.status_code == 422


def test_admin_offset_validation(
    app,
    admin,
):
    app.dependency_overrides[
        get_db
    ] = lambda: object()

    app.dependency_overrides[
        require_admin
    ] = lambda: admin

    client = TestClient(
        app
    )

    response = client.get(
        "/api/v1/admin/analyses",
        params={
            "patient_code": "PXADMIN001",
            "offset": -1,
        },
    )

    assert response.status_code == 422