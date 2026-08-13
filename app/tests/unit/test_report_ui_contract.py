"""Static contract tests for analysis-id based real PDF export."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULT_TEMPLATE = PROJECT_ROOT / "src/lung_xray_api/web/templates/partials/result_panel.html"
UPLOAD_TEMPLATE = PROJECT_ROOT / "src/lung_xray_api/web/templates/partials/upload_panel.html"
PATIENT_TEMPLATE = PROJECT_ROOT / "src/lung_xray_api/web/templates/partials/patient_form.html"
PREFERENCES_TEMPLATE = (
    PROJECT_ROOT / "src/lung_xray_api/web/templates/partials/result_view_preferences.html"
)
REPORT_CONTROLLER = PROJECT_ROOT / "src/lung_xray_api/web/static/js/report/report-controller.js"
REPORT_TEMPLATE = PROJECT_ROOT / "src/lung_xray_api/web/templates/report.html"
REPORT_ROUTE = PROJECT_ROOT / "src/lung_xray_api/api/v1/report.py"
PDF_SERVICE = PROJECT_ROOT / "src/lung_xray_api/application/report_pdf_service.py"
RESULT_VIEWS = PROJECT_ROOT / "src/lung_xray_api/web/static/js/core/result-views.js"
APP_STORE = PROJECT_ROOT / "src/lung_xray_api/web/static/js/core/app-store.js"
PREDICTION_CONTROLLER = (
    PROJECT_ROOT / "src/lung_xray_api/web/static/js/prediction/prediction-controller.js"
)
PREFERENCES_CONTROLLER = (
    PROJECT_ROOT / "src/lung_xray_api/web/static/js/prediction/result-view-preferences-controller.js"
)
PREDICTION_RENDERER = (
    PROJECT_ROOT / "src/lung_xray_api/web/static/js/prediction/prediction-renderer.js"
)
CHART_MODULE = PROJECT_ROOT / "src/lung_xray_api/web/static/js/visualization/result-chart.js"
RESULT_STYLES = PROJECT_ROOT / "src/lung_xray_api/web/static/css/components/result.css"
CHART_STYLES = PROJECT_ROOT / "src/lung_xray_api/web/static/css/components/charts.css"


def test_export_action_is_hidden_until_a_persisted_analysis_exists() -> None:
    template = RESULT_TEMPLATE.read_text(encoding="utf-8")
    controller = REPORT_CONTROLLER.read_text(encoding="utf-8")

    assert 'id="preview-report-button"' in template
    assert 'id="export-report-button"' in template
    start = template.index('id="export-report-button"')
    assert "hidden" in template[start:template.index("</button>", start)]
    assert "store.getState().analysisId" in controller
    assert "buildReportUrl" in controller
    assert "response.blob()" in controller
    assert "Content-Disposition" in controller
    assert "filenameFromContentDisposition" in controller
    assert "URL.createObjectURL" in controller
    assert "openReportPreview" in controller
    assert "buildReportUrl" in controller
    assert "selectedResultViews" in controller


def test_pdf_is_generated_from_sqlite_analysis_id_not_frontend_result_payload() -> None:
    controller = REPORT_CONTROLLER.read_text(encoding="utf-8")
    route = REPORT_ROUTE.read_text(encoding="utf-8")
    pdf_service = PDF_SERVICE.read_text(encoding="utf-8")

    assert "probabilities" not in controller
    assert '@router.get("/api/v1/analyses/{analysis_id}/report.pdf")' in route
    assert "history_service.get" in route
    assert "generate_analysis_pdf" in route
    assert "AnalysisHistoryRecord" in pdf_service
    assert "SimpleDocTemplate" in pdf_service
    assert "selected_views" in pdf_service
    assert "column-chart" in pdf_service
    assert "donut-chart" in pdf_service


def test_report_preview_contains_direct_download_and_optional_print_actions() -> None:
    template = REPORT_TEMPLATE.read_text(encoding="utf-8")

    assert "patient_display_name" in template
    assert "analysis_id" in template
    assert "thumbnail_data_uri" in template
    assert "reference_notice" in template
    assert "pdf_download_url" in template
    assert "selected_views" in template
    assert "Tải báo cáo PDF" in template
    assert "In bản xem trước" in template
    assert "window.print()" in template


def test_result_views_use_clear_teacher_visualization_language() -> None:
    template = RESULT_TEMPLATE.read_text(encoding="utf-8")

    assert "Thanh xác suất" in template
    assert "Biểu đồ cột" in template
    assert "Bảng số liệu" in template
    assert "XÁC SUẤT ĐẦU RA CAO NHẤT" in template
    assert "Xem trước báo cáo PDF" in template
    assert "Tải PDF ngay" in template


def test_result_view_preferences_are_a_separate_accessible_multiselect_partial() -> None:
    upload_template = UPLOAD_TEMPLATE.read_text(encoding="utf-8")
    patient_template = PATIENT_TEMPLATE.read_text(encoding="utf-8")
    preferences_template = PREFERENCES_TEMPLATE.read_text(encoding="utf-8")

    assert '{% include "partials/result_view_preferences.html" %}' in upload_template
    assert 'name="result-view-preference"' not in patient_template
    assert "<fieldset" in preferences_template
    assert "<legend>" in preferences_template
    assert 'aria-describedby="result-view-preferences-help result-view-preferences-status"' in preferences_template
    assert 'id="result-view-preferences-status"' in preferences_template
    assert 'aria-live="polite"' in preferences_template
    assert 'type="radio"' not in preferences_template
    assert preferences_template.count('type="checkbox" name="result-view-preference"') == 4

    for view_id in ("probability-bars", "column-chart", "donut-chart", "data-table"):
        assert f'value="{view_id}"' in preferences_template
        assert f'data-result-view-card="{view_id}"' in preferences_template

    assert (
        '<label class="visualization-option is-selected" '
        'data-result-view-card="probability-bars">'
    ) in preferences_template
    assert 'value="probability-bars" checked' in preferences_template
    assert (
        '<label class="visualization-option is-selected" '
        'data-result-view-card="column-chart">'
    ) in preferences_template
    assert 'value="column-chart" checked' in preferences_template
    assert 'value="summary"' not in preferences_template
    assert 'value="chart"' not in preferences_template
    assert 'value="donut"' not in preferences_template
    assert 'value="table"' not in preferences_template


def test_result_sections_follow_the_shared_result_view_ids() -> None:
    result_template = RESULT_TEMPLATE.read_text(encoding="utf-8")
    chart_module = CHART_MODULE.read_text(encoding="utf-8")

    assert 'id="result-content"' in result_template
    assert 'class="result-view-grid"' in result_template
    assert 'role="tablist"' not in result_template
    for view_id in ("probability-bars", "column-chart", "donut-chart", "data-table"):
        assert f'id="result-view-{view_id}"' in result_template

    for obsolete_id in ("result-view-summary", "result-view-chart", "result-view-donut", "result-view-table"):
        assert f'id="{obsolete_id}"' not in result_template

    assert 'id="result-donut"' in result_template
    assert 'id="result-table-body"' in result_template
    assert "renderResultDonut" in chart_module
    assert '"data-class": label' in chart_module
    assert '"data-probability": value.toFixed(8)' in chart_module
    assert 'preserveAspectRatio: "xMidYMid meet"' in chart_module


def test_result_view_state_uses_one_shared_contract_and_renderer_owns_visibility() -> None:
    result_views = RESULT_VIEWS.read_text(encoding="utf-8")
    store = APP_STORE.read_text(encoding="utf-8")
    controller = PREDICTION_CONTROLLER.read_text(encoding="utf-8")
    preferences_controller = PREFERENCES_CONTROLLER.read_text(encoding="utf-8")
    renderer = PREDICTION_RENDERER.read_text(encoding="utf-8")

    assert "RESULT_VIEW_IDS" in result_views
    assert "DEFAULT_RESULT_VIEWS" in result_views
    assert "RESULT_VIEW_LABELS" in result_views
    assert "normalizeResultViews" in result_views
    assert '"probability-bars"' in result_views
    assert '"column-chart"' in result_views
    assert '"donut-chart"' in result_views
    assert '"data-table"' in result_views

    assert 'from "./result-views.js"' in store
    assert "selectedResultViews" in store
    assert "setSelectedResultViews" in store
    assert "resultViews:" not in store
    assert "setResultViews" not in store

    assert "normalizeResultViews" not in controller
    assert "setSelectedResultViews" not in controller
    assert 'byId(`result-view-${view}`).hidden' not in controller

    assert "createResultViewPreferencesController" in preferences_controller
    assert "setSelectedResultViews" in preferences_controller
    assert "normalizeResultViews" in preferences_controller
    assert "LAST_SELECTION_MESSAGE" in preferences_controller
    assert 'classList.toggle("is-selected", checked)' in preferences_controller

    assert "RESULT_VIEW_SECTION_IDS" in renderer
    assert "normalizeResultViews" in renderer
    assert ".hidden =" in renderer


def test_column_chart_layout_uses_its_available_card_height() -> None:
    chart_module = CHART_MODULE.read_text(encoding="utf-8")
    result_styles = RESULT_STYLES.read_text(encoding="utf-8")
    chart_styles = CHART_STYLES.read_text(encoding="utf-8")

    result_grid_rules = result_styles.split(".result-view-grid {", 1)[1].split("}", 1)[0]
    result_view_rules = result_styles.split(".result-view {", 1)[1].split("}", 1)[0]
    column_chart_rules = chart_styles.split(".chart-container--column {", 1)[1].split("}", 1)[0]

    assert 'viewBox: "0 0 420 390"' in chart_module
    assert "aspect-ratio: 420 / 390;" in chart_styles
    assert "align-items: start;" in result_grid_rules
    assert "align-self: start;" in result_view_rules
    assert "min-height" not in column_chart_rules
