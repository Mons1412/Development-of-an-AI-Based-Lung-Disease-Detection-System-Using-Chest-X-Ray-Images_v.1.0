"""Safe Vietnamese report names and local-time formatting.

The download name intentionally identifies the case and model classification in
human-readable Vietnamese. The HTTP header also carries an ASCII fallback for
older Windows/browser combinations while ``filename*`` preserves accents.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
import unicodedata
from urllib.parse import quote

from lung_xray_api.infrastructure.persistence.records import AnalysisHistoryRecord

REPORT_TITLE = "Báo cáo kết quả phân loại ảnh X-quang phổi"
DOWNLOAD_FILENAME_PREFIX = "Báo cáo phân loại X-quang phổi"
VIETNAM_TIMEZONE = timezone(timedelta(hours=7), name="UTC+7")

_CLASS_LABELS = {
    "normal": "Bình thường",
    "pneumonia": "Viêm phổi",
    "tuberculosis": "Lao phổi",
}
_SOURCE_LABELS = {
    "filename": "Nhận từ tên tệp và đã được người dùng xác nhận",
    "manual": "Người dùng nhập và xác nhận thủ công",
    "anonymous": "Người dùng xác nhận ca ẩn danh / ảnh minh họa",
}
_INVALID_FILENAME_CHARACTERS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WHITESPACE = re.compile(r"\s+")
_ASCII_SEPARATORS = re.compile(r"[^A-Za-z0-9._-]+")


def as_vietnam_time(value: datetime) -> datetime:
    """Return an aware UTC+7 datetime without relying on OS timezone data."""

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(VIETNAM_TIMEZONE)


def format_vietnam_datetime(value: datetime) -> str:
    """Format a report timestamp in the application's local academic context."""

    return as_vietnam_time(value).strftime("%d/%m/%Y %H:%M:%S UTC+7")


def patient_source_label(source: str) -> str:
    """Map internal metadata sources to controlled Vietnamese labels."""

    return _SOURCE_LABELS.get(source, "Nguồn thông tin không xác định")


def report_case_label(record: AnalysisHistoryRecord) -> str:
    """Create a stable human-facing label for identified or anonymous cases."""

    if record.is_anonymous_sample:
        return "Ca ẩn danh"

    parts = [part for part in (record.patient_code, record.patient_display_name) if part]
    return " - ".join(parts) if parts else "Ca chưa định danh"


def build_report_filename(record: AnalysisHistoryRecord) -> str:
    """Build the UTF-8 download filename requested by the product UI.

    The model output is included because the report is explicitly a
    classification report. This can expose sensitive information in a shared
    Downloads folder, so the release privacy guide must document that risk.
    """

    timestamp = as_vietnam_time(record.analyzed_at).strftime("%Y%m%d-%H%M%S")
    result_label = _CLASS_LABELS[record.predicted_label]
    case_label = _clean_component(report_case_label(record), max_length=72)
    short_id = record.id.split("-", 1)[0]

    if record.is_anonymous_sample:
        raw_name = (
            f"{DOWNLOAD_FILENAME_PREFIX} - {case_label} - {result_label} - "
            f"{timestamp} - {short_id}.pdf"
        )
    else:
        raw_name = (
            f"{DOWNLOAD_FILENAME_PREFIX} - {case_label} - {result_label} - "
            f"{timestamp}.pdf"
        )

    return _limit_filename(raw_name, extension=".pdf", max_length=190)


def build_content_disposition(filename: str) -> str:
    """Return an RFC 6266/RFC 5987 attachment header with UTF-8 support."""

    safe_utf8 = _limit_filename(filename, extension=".pdf", max_length=190)
    ascii_fallback = _ascii_filename(safe_utf8)
    encoded = quote(safe_utf8, safe="")
    return (
        f'attachment; filename="{ascii_fallback}"; '
        f"filename*=UTF-8''{encoded}"
    )


def _clean_component(value: str, *, max_length: int) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    normalized = _INVALID_FILENAME_CHARACTERS.sub(" ", normalized)
    normalized = _WHITESPACE.sub(" ", normalized).strip(" .-")
    return (normalized or "Không xác định")[:max_length].rstrip(" .-")


def _limit_filename(filename: str, *, extension: str, max_length: int) -> str:
    normalized = unicodedata.normalize("NFKC", filename)
    normalized = normalized.replace("\r", " ").replace("\n", " ")
    normalized = _INVALID_FILENAME_CHARACTERS.sub("-", normalized)
    normalized = _WHITESPACE.sub(" ", normalized).strip(" .")
    if not normalized.lower().endswith(extension):
        normalized = f"{normalized}{extension}"

    stem = normalized[: -len(extension)].rstrip(" .")
    allowed_stem_length = max(1, max_length - len(extension))
    stem = stem[:allowed_stem_length].rstrip(" .-")
    return f"{stem or 'Bao-cao-X-quang-phoi'}{extension}"


def _ascii_filename(filename: str) -> str:
    decomposed = unicodedata.normalize("NFKD", filename)
    ascii_text = decomposed.encode("ascii", "ignore").decode("ascii")
    ascii_text = _ASCII_SEPARATORS.sub("_", ascii_text)
    ascii_text = re.sub(r"_+", "_", ascii_text).strip("._-")
    if not ascii_text.lower().endswith(".pdf"):
        ascii_text = f"{ascii_text}.pdf"
    return _limit_filename(ascii_text, extension=".pdf", max_length=170)
