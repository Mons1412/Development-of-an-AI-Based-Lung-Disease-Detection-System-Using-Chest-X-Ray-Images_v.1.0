"""Validated presentation choices for locally generated analysis reports."""

from __future__ import annotations

from collections.abc import Iterable

REPORT_VIEW_IDS = (
    "probability-bars",
    "column-chart",
    "donut-chart",
    "data-table",
)

# Keep direct/history report URLs backward compatible with the original report.
DEFAULT_REPORT_VIEW_IDS = ("probability-bars", "data-table")


def normalize_report_view_ids(values: Iterable[str] | None) -> tuple[str, ...]:
    """Return a canonical, bounded list of server-approved report views.

    This only controls presentation. Prediction, patient, source, and thumbnail
    values continue to come solely from the persisted analysis record.
    """

    if values is None:
        return DEFAULT_REPORT_VIEW_IDS
    requested = tuple(values)
    if not requested:
        return DEFAULT_REPORT_VIEW_IDS
    if len(requested) > len(REPORT_VIEW_IDS):
        raise ValueError("too many report views")
    if any(not isinstance(view, str) or len(view) > 32 for view in requested):
        raise ValueError("invalid report view")
    requested_set = set(requested)
    if not requested_set.issubset(REPORT_VIEW_IDS):
        raise ValueError("unsupported report view")
    return tuple(view for view in REPORT_VIEW_IDS if view in requested_set)
