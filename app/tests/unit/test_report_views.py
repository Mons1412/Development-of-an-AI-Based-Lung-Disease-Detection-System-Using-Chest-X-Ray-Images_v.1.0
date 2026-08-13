import pytest

from lung_xray_api.application.report_views import (
    DEFAULT_REPORT_VIEW_IDS,
    normalize_report_view_ids,
)


def test_report_views_use_safe_canonical_order_and_legacy_default() -> None:
    assert normalize_report_view_ids(None) == DEFAULT_REPORT_VIEW_IDS
    assert normalize_report_view_ids(()) == DEFAULT_REPORT_VIEW_IDS
    assert normalize_report_view_ids(
        ("donut-chart", "probability-bars", "donut-chart", "column-chart")
    ) == ("probability-bars", "column-chart", "donut-chart")


@pytest.mark.parametrize(
    "values",
    [
        ("unknown",),
        ("",),
        ("probability-bars", "column-chart", "donut-chart", "data-table", "data-table"),
        ("x" * 33,),
    ],
)
def test_report_views_reject_unknown_or_unbounded_values(values: tuple[str, ...]) -> None:
    with pytest.raises(ValueError):
        normalize_report_view_ids(values)
