"""HTML previews and downloadable PDF reports for persisted analyses.

The ReportLab backend is imported lazily inside the PDF endpoint. This keeps the
main application bootable when the optional PDF dependency has not yet been
installed, while the endpoint returns a precise 503 installation message.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Callable
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from lung_xray_api.api.dependencies import (
    get_analysis_history_service,
    get_knowledge_metadata,
    require_api_key,
    require_local_history_access,
)
from lung_xray_api.application.analysis_history_service import AnalysisHistoryService
from lung_xray_api.application.knowledge_metadata import KnowledgeMetadata
from lung_xray_api.application.report_views import normalize_report_view_ids
from lung_xray_api.application.report_filename import (
    REPORT_TITLE,
    as_vietnam_time,
    build_content_disposition,
    build_report_filename,
    format_vietnam_datetime,
    patient_source_label,
    report_case_label,
)
from lung_xray_api.core.exceptions import PersistenceError
from lung_xray_api.infrastructure.persistence.records import AnalysisHistoryRecord
from lung_xray_api.schemas.report import ReportPreviewRequest

router = APIRouter(tags=["report"])
_WEB_DIR = Path(__file__).resolve().parents[2] / "web"
_templates = Jinja2Templates(directory=str(_WEB_DIR / "templates"))
_CLASS_LABELS = {
    "normal": "Bình thường",
    "pneumonia": "Viêm phổi",
    "tuberculosis": "Lao phổi",
}
_TEAM_MEMBERS = (
    "Lê Đoàn Anh Tuấn · 2200010939",
    "Võ Nhật Nguyên · 2200004486",
    "Vô Văn Nghĩa · 2200000318",
)
_DEFAULT_SOURCES = (
    "MODEL_ARTIFACT_1_1_0",
    "PROJECT_SOURCE_V1_0_0",
)
_DEFAULT_DISCLAIMER = (
    "Kết quả phân loại của mô hình chỉ phục vụ mục đích học thuật và tham khảo; "
    "không thay thế đánh giá, chẩn đoán hoặc điều trị của nhân viên y tế."
)
_REFERENCE_NOTICE = (
    "Nội dung chuyên môn đang chờ duyệt. Bản production hiện chỉ cung cấp "
    "thông tin về đầu ra mô hình, không bao gồm hướng dẫn thuốc, liều lượng "
    "hoặc thay đổi điều trị."
)
_PDF_INSTALL_COMMAND = (
    '.\\.venv\\Scripts\\python.exe -m pip install "reportlab>=4.2,<5.0"'
)


@dataclass(frozen=True)
class BinaryAsset:
    """Small in-memory asset passed to the PDF renderer."""

    content: bytes
    media_type: str


@router.get("/api/v1/analyses/{analysis_id}/report", response_class=HTMLResponse)
async def render_persisted_report(
    request: Request,
    analysis_id: UUID,
    history_service: Annotated[AnalysisHistoryService, Depends(get_analysis_history_service)],
    knowledge_metadata: Annotated[KnowledgeMetadata, Depends(get_knowledge_metadata)],
    _authorized: Annotated[None, Depends(require_api_key)],
    _local_only: Annotated[None, Depends(require_local_history_access)],
    view: Annotated[list[str] | None, Query()] = None,
) -> HTMLResponse:
    """Render a browser preview while keeping the PDF download separate."""

    selected_views = _selected_report_views(view)
    record = await run_in_threadpool(history_service.get, str(analysis_id))
    if record is None:
        raise HTTPException(status_code=404, detail="Analysis was not found")

    thumbnail_data_uri = await run_in_threadpool(
        _thumbnail_data_uri,
        history_service,
        record,
    )
    return _render_report(
        request=request,
        record=record,
        thumbnail_data_uri=thumbnail_data_uri,
        source_titles=knowledge_metadata.source_titles,
        selected_views=selected_views,
    )


@router.get("/api/v1/analyses/{analysis_id}/report.pdf")
async def download_persisted_report_pdf(
    analysis_id: UUID,
    history_service: Annotated[AnalysisHistoryService, Depends(get_analysis_history_service)],
    knowledge_metadata: Annotated[KnowledgeMetadata, Depends(get_knowledge_metadata)],
    _authorized: Annotated[None, Depends(require_api_key)],
    _local_only: Annotated[None, Depends(require_local_history_access)],
    view: Annotated[list[str] | None, Query()] = None,
) -> Response:
    """Generate and download a real PDF from SQLite-backed analysis data."""

    selected_views = _selected_report_views(view)
    record = await run_in_threadpool(history_service.get, str(analysis_id))
    if record is None:
        raise HTTPException(status_code=404, detail="Analysis was not found")

    generate_analysis_pdf, generation_error_type = _load_pdf_backend()
    thumbnail = await run_in_threadpool(_thumbnail_asset, history_service, record)
    logo = await run_in_threadpool(
        _file_asset,
        _WEB_DIR / "static" / "assets" / "nttu_logo.png",
        "image/png",
    )

    try:
        pdf_bytes = await run_in_threadpool(
            generate_analysis_pdf,
            record=record,
            source_titles=knowledge_metadata.source_titles,
            logo=logo,
            thumbnail=thumbnail,
            selected_views=selected_views,
        )
    except generation_error_type as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PDF report generation is unavailable",
        ) from exc

    filename = build_report_filename(record)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": build_content_disposition(filename),
            "Content-Length": str(len(pdf_bytes)),
            "X-Content-Type-Options": "nosniff",
            "X-Report-Naming-Version": "patient-result-v3",
        },
    )


@router.post("/api/v1/report/preview", response_class=HTMLResponse, deprecated=True)
def render_legacy_report_preview(
    request: Request,
    payload: ReportPreviewRequest,
    _authorized: Annotated[None, Depends(require_api_key)],
) -> HTMLResponse:
    """Compatibility preview; the current UI exports by persisted analysis_id."""

    prediction = payload.prediction
    pseudo_record = AnalysisHistoryRecord(
        id="00000000-0000-0000-0000-000000000000",
        patient_code=None,
        patient_display_name=None,
        patient_name_search_key=None,
        patient_name_source="anonymous",
        patient_info_confirmed=True,
        is_anonymous_sample=True,
        filename_pattern_id=None,
        parsed_filename_date=None,
        original_filename=payload.filename,
        thumbnail_relative_path=None,
        predicted_label=prediction.predicted_label,
        normal_probability=prediction.probabilities["normal"],
        pneumonia_probability=prediction.probabilities["pneumonia"],
        tuberculosis_probability=prediction.probabilities["tuberculosis"],
        model_version=prediction.model_version,
        knowledge_base_version=None,
        prediction_disclaimer=_DEFAULT_DISCLAIMER,
        reference_source_ids=_DEFAULT_SOURCES,
        processing_time_ms=prediction.processing_time_ms,
        analyzed_at=prediction.analysis_timestamp.astimezone(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    return _render_report(
        request=request,
        record=pseudo_record,
        thumbnail_data_uri=None,
        source_titles={},
        selected_views=None,
    )


def _load_pdf_backend() -> tuple[Callable[..., bytes], type[Exception]]:
    """Import the ReportLab renderer only when a PDF is requested."""

    try:
        from lung_xray_api.application.report_pdf_service import (
            ReportPdfGenerationError,
            generate_analysis_pdf,
        )
    except ModuleNotFoundError as exc:
        if exc.name == "reportlab" or (exc.name or "").startswith("reportlab."):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "PDF support is not installed. Stop the server and run: "
                    f"{_PDF_INSTALL_COMMAND}"
                ),
            ) from exc
        raise

    return generate_analysis_pdf, ReportPdfGenerationError


def _render_report(
    *,
    request: Request,
    record: AnalysisHistoryRecord,
    thumbnail_data_uri: str | None,
    source_titles: dict[str, str],
    selected_views: tuple[str, ...] | None,
) -> HTMLResponse:
    normalized_views = _selected_report_views(selected_views)
    cumulative_percentage = 0.0
    probability_items = []
    for label in ("normal", "pneumonia", "tuberculosis"):
        percentage = getattr(record, f"{label}_probability") * 100
        cumulative_percentage += percentage
        probability_items.append(
            {
                "api_label": label,
                "label": _CLASS_LABELS[label],
                "percentage": percentage,
                "cumulative_percentage": cumulative_percentage,
            }
        )
    probabilities = tuple(probability_items)
    sources = tuple(
        (source_id, source_titles.get(source_id, "Nguồn tham chiếu kỹ thuật đã ghi nhận"))
        for source_id in record.reference_source_ids
    )
    logo_data_uri = _file_data_uri(
        _WEB_DIR / "static" / "assets" / "nttu_logo.png",
        "image/png",
    )
    generated_at = datetime.now(timezone.utc)
    top_probability = getattr(record, f"{record.predicted_label}_probability") * 100

    return _templates.TemplateResponse(
        request=request,
        name="report.html",
        context={
            "request": request,
            "report_title": REPORT_TITLE,
            "project_name": "Hệ thống phân loại ảnh X-quang phổi bằng MobileNetV2",
            "university_name": "Đại học Nguyễn Tất Thành",
            "logo_url": logo_data_uri,
            "stylesheet_url": str(request.url_for("static", path="css/pages/report.css")),
            "pdf_download_url": _report_pdf_url(record.id, normalized_views),
            "analysis_id": record.id,
            "filename": record.original_filename,
            "patient_code": record.patient_code,
            "patient_display_name": record.patient_display_name,
            "patient_name_source": patient_source_label(record.patient_name_source),
            "case_display_label": report_case_label(record),
            "is_anonymous_sample": record.is_anonymous_sample,
            "thumbnail_data_uri": thumbnail_data_uri,
            "prediction_label": _CLASS_LABELS[record.predicted_label],
            "api_label": record.predicted_label,
            "top_probability": top_probability,
            "probabilities": probabilities,
            "selected_views": normalized_views,
            "model_version": record.model_version,
            "knowledge_base_version": record.knowledge_base_version,
            "processing_time_ms": record.processing_time_ms,
            "analysis_timestamp": as_vietnam_time(record.analyzed_at),
            "analysis_timestamp_text": format_vietnam_datetime(record.analyzed_at),
            "generated_at": as_vietnam_time(generated_at),
            "generated_at_text": format_vietnam_datetime(generated_at),
            "reference_notice": _REFERENCE_NOTICE,
            "sources": sources,
            "disclaimer": record.prediction_disclaimer or _DEFAULT_DISCLAIMER,
            "team_members": _TEAM_MEMBERS,
        },
        headers={"Cache-Control": "no-store"},
    )


def _selected_report_views(values: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    try:
        return normalize_report_view_ids(values)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unsupported report visualization",
        ) from exc


def _report_pdf_url(analysis_id: str, selected_views: tuple[str, ...]) -> str:
    query = "&".join(f"view={view}" for view in selected_views)
    return f"/api/v1/analyses/{analysis_id}/report.pdf?{query}"


def _thumbnail_asset(
    history_service: AnalysisHistoryService,
    record: AnalysisHistoryRecord,
) -> BinaryAsset | None:
    if record.thumbnail_relative_path is None:
        return None
    try:
        content, media_type = history_service.thumbnail_store.read_thumbnail(
            record.thumbnail_relative_path
        )
    except PersistenceError:
        return None
    return BinaryAsset(content=content, media_type=media_type)


def _thumbnail_data_uri(
    history_service: AnalysisHistoryService,
    record: AnalysisHistoryRecord,
) -> str | None:
    asset = _thumbnail_asset(history_service, record)
    if asset is None:
        return None
    encoded = base64.b64encode(asset.content).decode("ascii")
    return f"data:{asset.media_type};base64,{encoded}"


def _file_asset(path: Path, media_type: str) -> BinaryAsset | None:
    try:
        content = path.read_bytes()
    except OSError:
        return None
    return BinaryAsset(content=content, media_type=media_type)


def _file_data_uri(path: Path, media_type: str) -> str:
    asset = _file_asset(path, media_type)
    if asset is None:
        return ""
    encoded = base64.b64encode(asset.content).decode("ascii")
    return f"data:{asset.media_type};base64,{encoded}"
