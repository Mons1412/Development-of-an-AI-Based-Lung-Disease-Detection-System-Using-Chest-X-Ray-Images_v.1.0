"""Contract tests for the versioned, offline demo frontend."""

from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from lung_xray_api.core.config import load_settings
from lung_xray_api.main import create_app
from lung_xray_api.web.assets import FRONTEND_ASSET_VERSION, FRONTEND_STATIC_BASE
from tests.conftest import FakePredictionService


APP_MODULE = (
    Path(__file__).resolve().parents[2]
    / "src/lung_xray_api/web/static/js/app.js"
)


def test_demo_page_uses_one_versioned_es_module_application(test_client: TestClient) -> None:
    response = test_client.get("/demo")

    assert response.status_code == 200
    assert FRONTEND_ASSET_VERSION == "20260728.6"
    assert f'<meta name="frontend-build" content="{FRONTEND_ASSET_VERSION}">' in response.text
    assert f'<meta name="frontend-static-base" content="{FRONTEND_STATIC_BASE}">' in response.text
    assert f'href="{FRONTEND_STATIC_BASE}/demo.css"' in response.text
    assert f'<script type="module" src="{FRONTEND_STATIC_BASE}/js/app.js"></script>' in response.text
    assert response.text.count('<script type="module"') == 1

    # Compatibility wrappers may remain on disk, but the document must not execute them.
    assert "/static/demo.js" not in response.text
    assert "/static/assistant.js" not in response.text
    assert "/static/report_export.js" not in response.text


def test_application_entry_logs_the_rendered_frontend_build() -> None:
    app_module = APP_MODULE.read_text(encoding="utf-8")

    assert f'export const FRONTEND_BUILD = "{FRONTEND_ASSET_VERSION}";' in app_module
    assert "[LungXrayUI] frontend build ${FRONTEND_BUILD}" in app_module


def test_demo_page_keeps_the_expected_offline_workspace_content(test_client: TestClient) -> None:
    response = test_client.get("/demo")

    assert response.status_code == 200
    assert "Lung X-ray AI Classification System" in response.text
    assert "Logo Đại học Nguyễn Tất Thành" in response.text
    assert "Kết quả phân loại của mô hình" in response.text
    assert "Trợ lý thông tin X-quang phổi" in response.text
    assert "Ngoại tuyến" in response.text
    assert "Xem trước báo cáo PDF" in response.text
    assert "Kết quả chỉ phục vụ mục đích học thuật" in response.text


def test_development_demo_and_versioned_assets_are_not_cached(test_client: TestClient) -> None:
    for path, content_type in [
        ("/demo", "text/html"),
        (f"{FRONTEND_STATIC_BASE}/demo.css", "text/css"),
        (f"{FRONTEND_STATIC_BASE}/js/app.js", "javascript"),
        (f"{FRONTEND_STATIC_BASE}/assets/favicon.svg", "image/svg+xml"),
        (f"{FRONTEND_STATIC_BASE}/assets/nttu_logo.png", "image/png"),
    ]:
        response = test_client.get(path)

        assert response.status_code == 200, path
        assert content_type in response.headers["content-type"]
        assert response.headers["cache-control"] == "no-store"
        assert response.content


def test_production_uses_versioned_static_cache_policy(tmp_path) -> None:
    settings = replace(
        load_settings(),
        app_env="production",
        history_db_path=tmp_path / "data" / "lung_xray_history.db",
        thumbnail_dir=tmp_path / "data" / "thumbnails",
    )
    app = create_app(settings=settings, prediction_service=FakePredictionService())

    with TestClient(app) as client:
        demo = client.get("/demo")
        versioned_asset = client.get(f"{FRONTEND_STATIC_BASE}/js/app.js")
        legacy_asset = client.get("/static/js/app.js")

    assert demo.headers["cache-control"] == "public, max-age=0, must-revalidate"
    assert versioned_asset.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert legacy_asset.headers["cache-control"] == "public, max-age=0, must-revalidate"
