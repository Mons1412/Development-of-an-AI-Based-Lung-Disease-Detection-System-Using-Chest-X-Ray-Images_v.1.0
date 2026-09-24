from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

INDEX = (
    ROOT
    / "frontend"
    / "index.html"
).read_text(
    encoding="utf-8-sig"
)

SCRIPT = (
    ROOT
    / "frontend"
    / "script.js"
).read_text(
    encoding="utf-8-sig"
)

STYLE = (
    ROOT
    / "frontend"
    / "style.css"
).read_text(
    encoding="utf-8-sig"
)


def test_admin_dashboard_html_exists_before_search():
    dashboard_index = INDEX.index(
        'id="admin-dashboard-section"'
    )

    search_index = INDEX.index(
        'id="admin-search-section"'
    )

    assert dashboard_index < search_index

    for element_id in [
        "admin-dashboard-status",
        "admin-dashboard-overview",
        "admin-dashboard-predictions",
        "admin-dashboard-model-usage",
    ]:
        assert (
            f'id="{element_id}"'
            in INDEX
        )


def test_admin_dashboard_fetch_contract_exists():
    assert (
        "async function loadAdminDashboard("
        in SCRIPT
    )

    assert (
        '"/api/v1/admin/dashboard/summary"'
        in SCRIPT
    )

    for removed_id in ["admin-dashboard-recent-limit", "admin-dashboard-refresh-button",
                       "admin-dashboard-recent-analyses"]:
        assert f'id="{removed_id}"' not in INDEX

    assert (
        "Authorization:"
        in SCRIPT
    )

    assert (
        "`Bearer ${token}`"
        in SCRIPT
    )


def test_admin_dashboard_rendering_is_plain_text():
    start = SCRIPT.index(
        "function resetAdminDashboardView("
    )

    end = SCRIPT.index(
        "async function analyzeBatch()"
    )

    block = SCRIPT[
        start:end
    ]

    assert "innerHTML" not in block

    assert ".textContent" in block

    for forbidden_field in [
        "full_name",
        "phone",
        "address",
        "password_hash",
        "stored_image_path",
        "error_message",
        "advice_text",
    ]:
        assert (
            forbidden_field
            not in block
        )


def test_admin_dashboard_has_user_role_gate():
    assert (
        "function getAdminDashboardTokenRole("
        in SCRIPT
    )

    assert (
        "if (tokenRole) return loadAdminDashboard();"
        in SCRIPT
    )

    assert (
        "function initializeAdminDashboard()"
        in SCRIPT
    )

    assert (
        "initializeAdminDashboard();"
        in SCRIPT
    )


def test_admin_dashboard_css_and_old_search_remain():
    for css_marker in [
        ".admin-dashboard-overview",
        ".admin-dashboard-columns",
        ".admin-dashboard-bar-track",
        ".admin-dashboard-bar-fill",
        ".admin-dashboard-recent-card",
    ]:
        assert css_marker in STYLE

    assert (
        'id="admin-search-section"'
        in INDEX
    )

    assert (
        'id="admin-patient-query"'
        in INDEX
    )
