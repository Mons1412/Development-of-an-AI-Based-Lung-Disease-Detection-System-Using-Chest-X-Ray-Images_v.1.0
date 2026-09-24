from pathlib import Path


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

SCRIPT_PATH = (
    PROJECT_ROOT
    / "frontend"
    / "script.js"
)

STYLE_PATH = (
    PROJECT_ROOT
    / "frontend"
    / "style.css"
)


SCRIPT_SOURCE = (
    SCRIPT_PATH.read_text(
        encoding="utf-8"
    )
)

STYLE_SOURCE = (
    STYLE_PATH.read_text(
        encoding="utf-8"
    )
)


def test_report_controls_are_shared_and_completed_only():
    assert SCRIPT_SOURCE.count(
        "function createReportControls("
    ) == 1

    assert SCRIPT_SOURCE.count(
        "createReportControls("
    ) == 3

    assert (
        'analysisStatus !== "COMPLETED"'
        in SCRIPT_SOURCE
    )

    assert (
        "return null;"
        in SCRIPT_SOURCE
    )

    assert (
        '"No PDF generated yet."'
        in SCRIPT_SOURCE
    )


def test_report_frontend_keeps_generate_preview_download_flow():
    assert (
        '"/api/v1/reports"'
        in SCRIPT_SOURCE
    )

    assert SCRIPT_SOURCE.count(
        "fetchReportPdf("
    ) == 3

    report_controls_start = (
        SCRIPT_SOURCE.index(
            "function createReportControls("
        )
    )

    report_controls_end = (
        SCRIPT_SOURCE.index(
            "async function parseResponse(",
            report_controls_start,
        )
    )

    report_controls_source = (
        SCRIPT_SOURCE[
            report_controls_start:
            report_controls_end
        ]
    )

    assert report_controls_source.count(
        "URL.createObjectURL("
    ) == 2

    assert (
        'window.open('
        in SCRIPT_SOURCE
    )

    assert (
        "link.download ="
        in SCRIPT_SOURCE
    )

    assert (
        '"PDF preview opened."'
        in SCRIPT_SOURCE
    )

    assert (
        '"PDF download started."'
        in SCRIPT_SOURCE
    )


def test_report_controls_css_contract():
    expected_selector_counts = {
        ".report-actions {": 1,
        ".report-actions-title {": 1,
        ".report-actions-row {": 2,
        ".report-language-select {": 2,
        ".report-action-status {": 1,
    }

    for (
        selector,
        expected_count,
    ) in expected_selector_counts.items():
        assert STYLE_SOURCE.count(
            selector
        ) == expected_count

    assert (
        "overflow-wrap: anywhere;"
        in STYLE_SOURCE
    )
