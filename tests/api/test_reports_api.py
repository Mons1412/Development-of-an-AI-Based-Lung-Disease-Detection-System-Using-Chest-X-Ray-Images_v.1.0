from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from lung_xray_api.api.dependencies.auth import (
    get_current_user,
)
from lung_xray_api.application.services.report_service import (
    report_service,
)
from lung_xray_api.infrastructure.persistence.database import (
    get_db,
)
from lung_xray_api.main import app


FIXED_CREATED_AT = datetime(
    2026,
    9,
    15,
    10,
    0,
    0,
)


def make_report():
    return SimpleNamespace(
        id=21,
        analysis_id=272,
        report_code="RP20260915TEST",
        language="vi",
        created_at=FIXED_CREATED_AT,
        file_path=(
            "app/var/reports/"
            "RP20260915TEST.pdf"
        ),
    )


@pytest.fixture
def client():
    fake_db = object()

    fake_user = SimpleNamespace(
        id=1,
        role="USER",
        is_active=True,
    )

    def override_db():
        return fake_db

    def override_current_user():
        return fake_user

    app.dependency_overrides[
        get_db
    ] = override_db

    app.dependency_overrides[
        get_current_user
    ] = override_current_user

    try:
        with TestClient(app) as test_client:
            yield test_client

    finally:
        app.dependency_overrides.pop(
            get_db,
            None,
        )

        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


def test_create_report_success_does_not_expose_file_path(
    client,
    monkeypatch,
):
    captured = {}

    def fake_generate_report(
        db,
        current_user,
        *,
        analysis_id,
        language,
    ):
        captured["analysis_id"] = (
            analysis_id
        )
        captured["language"] = (
            language
        )

        return make_report()

    monkeypatch.setattr(
        report_service,
        "generate_report",
        fake_generate_report,
    )

    response = client.post(
        "/api/v1/reports",
        json={
            "analysis_id": 272,
            "language": "vi",
        },
    )

    assert response.status_code == 201

    payload = response.json()

    assert payload["id"] == 21
    assert payload["analysis_id"] == 272
    assert payload["report_code"] == (
        "RP20260915TEST"
    )
    assert payload["language"] == "vi"

    assert "file_path" not in payload

    assert captured == {
        "analysis_id": 272,
        "language": "vi",
    }


@pytest.mark.parametrize(
    (
        "domain_error",
        "expected_status",
    ),
    [
        (
            LookupError(
                "Analysis not found."
            ),
            404,
        ),
        (
            ValueError(
                "Only completed analyses "
                "can be exported."
            ),
            400,
        ),
        (
            PermissionError(
                "Unsupported user role."
            ),
            403,
        ),
    ],
)
def test_create_report_maps_domain_errors(
    client,
    monkeypatch,
    domain_error,
    expected_status,
):
    def fake_generate_report(
        db,
        current_user,
        *,
        analysis_id,
        language,
    ):
        raise domain_error

    monkeypatch.setattr(
        report_service,
        "generate_report",
        fake_generate_report,
    )

    response = client.post(
        "/api/v1/reports",
        json={
            "analysis_id": 272,
            "language": "vi",
        },
    )

    assert (
        response.status_code
        == expected_status
    )


def test_get_report_metadata_does_not_expose_file_path(
    client,
    monkeypatch,
):
    def fake_get_report(
        db,
        current_user,
        *,
        report_id,
    ):
        assert report_id == 21

        return make_report()

    monkeypatch.setattr(
        report_service,
        "get_report",
        fake_get_report,
    )

    response = client.get(
        "/api/v1/reports/21"
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["id"] == 21
    assert "file_path" not in payload


def test_preview_returns_inline_pdf(
    client,
    monkeypatch,
    tmp_path,
):
    pdf_path = (
        tmp_path
        / "preview.pdf"
    )

    pdf_path.write_bytes(
        b"%PDF-1.4\nM11 preview test\n"
    )

    def fake_resolve_report_file(
        db,
        current_user,
        *,
        report_id,
    ):
        assert report_id == 21

        return (
            make_report(),
            pdf_path,
        )

    monkeypatch.setattr(
        report_service,
        "resolve_report_file",
        fake_resolve_report_file,
    )

    response = client.get(
        "/api/v1/reports/21/preview"
    )

    assert response.status_code == 200

    assert response.headers[
        "content-type"
    ].startswith(
        "application/pdf"
    )

    assert response.headers[
        "content-disposition"
    ].lower().startswith(
        "inline"
    )

    assert response.content.startswith(
        b"%PDF-"
    )


def test_download_returns_attachment_pdf(
    client,
    monkeypatch,
    tmp_path,
):
    pdf_path = (
        tmp_path
        / "download.pdf"
    )

    pdf_path.write_bytes(
        b"%PDF-1.4\nM11 download test\n"
    )

    def fake_resolve_report_file(
        db,
        current_user,
        *,
        report_id,
    ):
        assert report_id == 21

        return (
            make_report(),
            pdf_path,
        )

    monkeypatch.setattr(
        report_service,
        "resolve_report_file",
        fake_resolve_report_file,
    )

    response = client.get(
        "/api/v1/reports/21/download"
    )

    assert response.status_code == 200

    assert response.headers[
        "content-type"
    ].startswith(
        "application/pdf"
    )

    assert response.headers[
        "content-disposition"
    ].lower().startswith(
        "attachment"
    )

    assert response.content.startswith(
        b"%PDF-"
    )
