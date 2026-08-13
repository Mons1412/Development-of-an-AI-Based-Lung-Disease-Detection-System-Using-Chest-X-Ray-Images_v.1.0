"""Verify the current result-tab and selected-view PDF integration."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CHECKS = {
    "visualization preferences": (
        ROOT / "src/lung_xray_api/web/templates/partials/result_view_preferences.html",
        'name="result-view-preference"',
    ),
    "result tablist": (
        ROOT / "src/lung_xray_api/web/templates/partials/result_panel.html",
        'role="tablist"',
    ),
    "result tab controller": (
        ROOT / "src/lung_xray_api/web/static/js/prediction/result-view-tabs-controller.js",
        "createResultViewTabsController",
    ),
    "donut renderer": (
        ROOT / "src/lung_xray_api/web/static/js/visualization/result-chart.js",
        "renderResultDonut",
    ),
    "report preview control": (
        ROOT / "src/lung_xray_api/web/static/js/report/report-controller.js",
        "openReportPreview",
    ),
    "server report-view validation": (
        ROOT / "src/lung_xray_api/api/v1/report.py",
        "normalize_report_view_ids",
    ),
    "selected-view PDF renderer": (
        ROOT / "src/lung_xray_api/application/report_pdf_service.py",
        "selected_views",
    ),
    "PDF naming prefix": (
        ROOT / "src/lung_xray_api/application/report_filename.py",
        'DOWNLOAD_FILENAME_PREFIX = "Báo cáo phân loại X-quang phổi"',
    ),
    "PDF naming header": (
        ROOT / "src/lung_xray_api/api/v1/report.py",
        '"X-Report-Naming-Version": "patient-result-v3"',
    ),
}


def main() -> int:
    failed: list[str] = []
    for label, (path, marker) in CHECKS.items():
        content = path.read_text(encoding="utf-8") if path.exists() else ""
        if marker not in content:
            failed.append(f"{label}: missing marker in {path.relative_to(ROOT)}")
        else:
            print(f"[PASS] {label}")
    if failed:
        for message in failed:
            print(f"[FAIL] {message}")
        return 1
    print("[PASS] Result tabs and selected-view PDF integration are installed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
