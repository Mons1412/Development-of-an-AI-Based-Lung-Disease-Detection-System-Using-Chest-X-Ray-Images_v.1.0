"""Static checks for the modular floating hybrid assistant."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = PROJECT_ROOT / "src/lung_xray_api/web/templates/partials/floating_assistant.html"
CONTROLLER = PROJECT_ROOT / "src/lung_xray_api/web/static/js/assistant/assistant-controller.js"
API = PROJECT_ROOT / "src/lung_xray_api/web/static/js/assistant/assistant-api.js"
APP = PROJECT_ROOT / "src/lung_xray_api/web/static/js/app.js"


def test_demo_uses_a_floating_assistant_partial_and_local_assets() -> None:
    demo = (PROJECT_ROOT / "src/lung_xray_api/web/templates/demo.html").read_text(
        encoding="utf-8"
    )
    template = TEMPLATE.read_text(encoding="utf-8")

    assert '{% include "partials/floating_assistant.html" %}' in demo
    assert 'id="assistant-launcher"' in template
    assert 'id="assistant-panel"' in template
    assert 'id="assistant-mode-badge"' in template
    assert 'id="assistant-online-notice"' in template
    assert "Ngoại tuyến" in template
    assert 'type="module" src="{{ frontend_asset_url(\'js/app.js\') }}"' in demo
    assert "/static/assistant.js" not in demo


def test_assistant_client_uses_hybrid_endpoints_and_safe_dom_rendering() -> None:
    api = API.read_text(encoding="utf-8")
    controller = CONTROLLER.read_text(encoding="utf-8")

    assert '"/api/v1/assistant/query"' in api
    assert '"/api/v1/assistant/status"' in api
    assert api.count("apiRequest(") == 2
    assert "application_stage" in controller
    assert "prediction_context" in controller
    assert "fallback_used" in controller
    assert "setOnlineNotice" in controller
    assert "configured_unverified" in controller
    assert "online_verified" in controller
    assert "degraded_offline" in controller
    assert "requestSequence" in controller
    assert "AbortController" in controller
    assert "innerHTML" not in controller
    renderer = (
        PROJECT_ROOT
        / "src/lung_xray_api/web/static/js/assistant/message-animation.js"
    ).read_text(encoding="utf-8")
    assert "textContent" in renderer
    assert "api_key" not in controller
    assert "GEMINI_API_KEY" not in controller


def test_prediction_context_comes_from_the_single_application_store() -> None:
    controller = CONTROLLER.read_text(encoding="utf-8")
    app = APP.read_text(encoding="utf-8")

    assert "store.getState()" in controller
    assert "predicted_label" in controller
    assert "probabilities" in controller
    assert "model_version" in controller
    assert "currentPrediction" in controller
    assert "processing_time_ms" not in controller
    assert "window.lungXrayAssistantContext" not in controller
    assert "createAppStore" in app
    assert "EVENTS.ANALYSIS_RESET" in controller
