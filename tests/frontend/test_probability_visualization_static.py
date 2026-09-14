from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

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


SCRIPT_SOURCE = SCRIPT_PATH.read_text(
    encoding="utf-8"
)

STYLE_SOURCE = STYLE_PATH.read_text(
    encoding="utf-8"
)


def test_probability_normalization_has_one_shared_pipeline():
    assert SCRIPT_SOURCE.count(
        "function probabilityToPercent("
    ) == 1

    assert SCRIPT_SOURCE.count(
        "probabilityToPercent("
    ) == 2

    assert SCRIPT_SOURCE.count(
        "function formatProbabilityClassName("
    ) == 1

    assert SCRIPT_SOURCE.count(
        "formatProbabilityClassName("
    ) == 2

    assert SCRIPT_SOURCE.count(
        "function normalizeProbabilityEntries("
    ) == 1

    assert SCRIPT_SOURCE.count(
        "normalizeProbabilityEntries("
    ) == 3

    for field_name in (
        "className:",
        "displayName:",
        "value:",
        "percent,",
        "formattedPercent:",
    ):
        assert field_name in SCRIPT_SOURCE

    assert "entries.sort(" in SCRIPT_SOURCE


def test_probability_renderers_are_reused_through_switcher():
    assert SCRIPT_SOURCE.count(
        "createProbabilityVisualizationSwitcher("
    ) == 3

    assert SCRIPT_SOURCE.count(
        "createProbabilityBarChart("
    ) == 2

    assert SCRIPT_SOURCE.count(
        "createProbabilityColumnChart("
    ) == 2

    assert SCRIPT_SOURCE.count(
        "createProbabilityDonutChart("
    ) == 2

    assert SCRIPT_SOURCE.count(
        "createProbabilityTable("
    ) == 2

    assert SCRIPT_SOURCE.count(
        "createProbabilityRow("
    ) == 0

    assert SCRIPT_SOURCE.count(
        "createHistoryProbabilityRow("
    ) == 0


def test_probability_switcher_view_order_and_state_contract():
    function_start = SCRIPT_SOURCE.index(
        "function createProbabilityVisualizationSwitcher("
    )

    next_function = SCRIPT_SOURCE.find(
        "\nfunction ",
        function_start + 1,
    )

    if next_function == -1:
        switcher_source = SCRIPT_SOURCE[
            function_start:
        ]
    else:
        switcher_source = SCRIPT_SOURCE[
            function_start:next_function
        ]

    view_keys = (
        'key: "bar"',
        'key: "column"',
        'key: "donut"',
        'key: "table"',
    )

    positions = [
        switcher_source.index(
            view_key
        )
        for view_key in view_keys
    ]

    assert positions == sorted(
        positions
    )

    assert (
        '"Probability visualization type"'
        in switcher_source
    )

    assert (
        '"aria-pressed"'
        in switcher_source
    )

    assert (
        "index === 0"
        in switcher_source
    )

    assert (
        ".hidden ="
        in switcher_source
    )

    assert (
        'button.type ='
        in switcher_source
    )


def test_probability_visualizations_keep_accessibility_contract():
    assert SCRIPT_SOURCE.count(
        '"progressbar"'
    ) == 2

    assert SCRIPT_SOURCE.count(
        '"aria-valuemin"'
    ) == 2

    assert SCRIPT_SOURCE.count(
        '"aria-valuemax"'
    ) == 2

    assert SCRIPT_SOURCE.count(
        '"aria-valuenow"'
    ) == 2

    assert (
        '"Class probability donut chart"'
        in SCRIPT_SOURCE
    )

    assert (
        '"Class probability table"'
        in SCRIPT_SOURCE
    )

    assert (
        '"Probability table"'
        in SCRIPT_SOURCE
    )

    assert (
        "cell.scope ="
        in SCRIPT_SOURCE
    )

    assert (
        '"Predicted"'
        in SCRIPT_SOURCE
    )


def test_probability_visualization_css_contract():
    expected_selector_counts = {
        ".probability-view-switcher {": 2,
        ".probability-view-button {": 1,
        (
            '.probability-view-button'
            '[aria-pressed="true"] {'
        ): 1,
        (
            ".probability-view-button"
            ":focus-visible {"
        ): 1,
        ".probability-view-panel[hidden] {": 1,
        ".probability-bar-chart {": 1,
        ".probability-row {": 1,
        ".probability-column-chart {": 1,
        ".probability-donut-chart {": 2,
        ".probability-table-wrapper {": 1,
    }

    for (
        selector,
        expected_count,
    ) in expected_selector_counts.items():
        assert STYLE_SOURCE.count(
            selector
        ) == expected_count

    assert (
        "overflow-x: auto;"
        in STYLE_SOURCE
    )

    assert (
        "@media (max-width: 600px)"
        in STYLE_SOURCE
    )