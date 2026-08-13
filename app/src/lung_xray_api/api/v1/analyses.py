"""Persisted analysis and loopback-only local history endpoints."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from pydantic import ValidationError

from lung_xray_api.api.dependencies import (
    get_analysis_history_service,
    get_knowledge_metadata,
    get_prediction_service,
    require_api_key,
    require_local_history_access,
)
from lung_xray_api.api.upload import read_upload_bounded
from lung_xray_api.application.analysis_history_service import AnalysisHistoryService
from lung_xray_api.application.analysis_service import (
    AnalysisPredictionServiceProtocol,
    AnalysisService,
    CaseMetadataValidationError,
)
from lung_xray_api.application.filename_metadata_parser import FilenameMetadataParser
from lung_xray_api.application.knowledge_metadata import KnowledgeMetadata
from lung_xray_api.application.prediction_service import PredictionServiceProtocol
from lung_xray_api.core.exceptions import AnalysisNotFoundError, PersistenceError
from lung_xray_api.infrastructure.persistence.records import AnalysisHistoryFilters, AnalysisHistoryRecord
from lung_xray_api.schemas.analyses import (
    AnalysisDeletionResponse,
    AnalysisDetail,
    AnalysisHistoryPageResponse,
    AnalysisStorageStatus,
    AnalysisSummary,
    PersistedAnalysisResponse,
)
from lung_xray_api.schemas.case_metadata import (
    CaseMetadataInput,
    CaseMetadataResponse,
    FilenameParseRequest,
    FilenameParseResponse,
)

router = APIRouter(prefix="/api/v1/analyses", tags=["analyses"])
_PARSER = FilenameMetadataParser()


@router.post("/parse-filename", response_model=FilenameParseResponse)
async def parse_filename(
    payload: FilenameParseRequest,
    _authorized: Annotated[None, Depends(require_api_key)],
    _local_only: Annotated[None, Depends(require_local_history_access)],
) -> FilenameParseResponse:
    parsed = await run_in_threadpool(_PARSER.parse, payload.filename)
    return FilenameParseResponse(
        matched=parsed.matched,
        patient_code=parsed.patient_code,
        patient_display_name=parsed.patient_display_name,
        parsed_date=parsed.parsed_date,
        source="filename",
        validation_warnings=list(parsed.validation_warnings),
    )


@router.post("", response_model=PersistedAnalysisResponse, status_code=status.HTTP_201_CREATED)
async def create_analysis(
    request: Request,
    file: Annotated[UploadFile, File(...)],
    prediction_service: Annotated[PredictionServiceProtocol, Depends(get_prediction_service)],
    history_service: Annotated[AnalysisHistoryService, Depends(get_analysis_history_service)],
    knowledge_metadata: Annotated[KnowledgeMetadata, Depends(get_knowledge_metadata)],
    _authorized: Annotated[None, Depends(require_api_key)],
    _local_only: Annotated[None, Depends(require_local_history_access)],
    patient_code: Annotated[str | None, Form()] = None,
    patient_display_name: Annotated[str | None, Form()] = None,
    patient_name_source: Annotated[str | None, Form()] = None,
    patient_info_confirmed: Annotated[str | None, Form()] = None,
    is_anonymous_sample: Annotated[str | None, Form()] = None,
) -> dict[str, object]:
    try:
        metadata = CaseMetadataInput.model_validate(
            {
                "patient_code": patient_code,
                "patient_display_name": patient_display_name,
                "patient_name_source": patient_name_source,
                "patient_info_confirmed": patient_info_confirmed,
                "is_anonymous_sample": is_anonymous_sample,
            }
        )
    except ValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=_case_metadata_validation_detail(error),
        ) from error

    if not _supports_persisted_analysis(prediction_service):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persisted analysis service is unavailable",
        )

    content = await read_upload_bounded(file, request.app.state.settings.max_upload_bytes)
    analysis_service = AnalysisService(
        prediction_service=cast(AnalysisPredictionServiceProtocol, prediction_service),
        history_service=history_service,
        knowledge_base_version=knowledge_metadata.version,
        filename_parser=_PARSER,
    )
    try:
        persisted = await run_in_threadpool(
            analysis_service.analyze_upload,
            content=content,
            filename=file.filename or "upload",
            content_type=file.content_type,
            metadata=metadata,
        )
    except CaseMetadataValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "filename_metadata_mismatch",
                "message": (
                    "Thông tin nhận từ tên tệp không còn khớp. "
                    "Vui lòng kiểm tra lại hoặc nhập thủ công."
                ),
                "field_errors": {
                    "patient_name_source": (
                        "Thông tin tự nhận từ tên tệp đã thay đổi hoặc không đúng quy tắc."
                    )
                },
            },
        ) from error

    response = persisted.prediction.to_response()
    response.update(
        {
            "analysis_id": persisted.record.id,
            "analyzed_at": persisted.record.analyzed_at,
            "created_at": persisted.record.created_at,
            "case_metadata": _case_metadata_response(persisted.record).model_dump(),
            "storage": AnalysisStorageStatus().model_dump(),
        }
    )
    return response


@router.get("", response_model=AnalysisHistoryPageResponse)
async def list_analyses(
    history_service: Annotated[AnalysisHistoryService, Depends(get_analysis_history_service)],
    _authorized: Annotated[None, Depends(require_api_key)],
    _local_only: Annotated[None, Depends(require_local_history_access)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int | None, Query(ge=1, le=100)] = None,
    patient_query: Annotated[str | None, Query(max_length=80)] = None,
    predicted_label: Literal["normal", "pneumonia", "tuberculosis"] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    timezone_offset_minutes: Annotated[int, Query(ge=-840, le=840)] = 420,
    sort_order: Literal["asc", "desc"] = "desc",
) -> AnalysisHistoryPageResponse:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="date_from must not be after date_to",
        )
    normalized_query = _normalize_history_query(patient_query)
    filters = AnalysisHistoryFilters(
        patient_query=normalized_query,
        predicted_label=predicted_label,
        analyzed_at_from=_local_day_boundary(date_from, timezone_offset_minutes),
        analyzed_at_to=_local_next_day_boundary(date_to, timezone_offset_minutes),
        sort_order=sort_order,
    )
    result = await run_in_threadpool(
        history_service.list,
        page=page,
        page_size=page_size,
        filters=filters,
    )
    return AnalysisHistoryPageResponse(
        items=[_summary_response(item) for item in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@router.get("/{analysis_id}", response_model=AnalysisDetail)
async def get_analysis(
    analysis_id: UUID,
    history_service: Annotated[AnalysisHistoryService, Depends(get_analysis_history_service)],
    _authorized: Annotated[None, Depends(require_api_key)],
    _local_only: Annotated[None, Depends(require_local_history_access)],
) -> AnalysisDetail:
    record = await run_in_threadpool(history_service.get, str(analysis_id))
    if record is None:
        raise HTTPException(status_code=404, detail="Analysis was not found")
    return _detail_response(record)


@router.delete("/{analysis_id}", response_model=AnalysisDeletionResponse)
async def delete_analysis(
    analysis_id: UUID,
    history_service: Annotated[AnalysisHistoryService, Depends(get_analysis_history_service)],
    _authorized: Annotated[None, Depends(require_api_key)],
    _local_only: Annotated[None, Depends(require_local_history_access)],
) -> AnalysisDeletionResponse:
    try:
        result = await run_in_threadpool(history_service.delete, str(analysis_id))
    except AnalysisNotFoundError as error:
        raise HTTPException(status_code=404, detail="Analysis was not found") from error
    return AnalysisDeletionResponse(
        analysis_id=analysis_id,
        cleanup_pending=result.cleanup_pending,
    )


@router.get("/{analysis_id}/thumbnail")
async def get_analysis_thumbnail(
    analysis_id: UUID,
    history_service: Annotated[AnalysisHistoryService, Depends(get_analysis_history_service)],
    _authorized: Annotated[None, Depends(require_api_key)],
    _local_only: Annotated[None, Depends(require_local_history_access)],
) -> Response:
    record = await run_in_threadpool(history_service.get, str(analysis_id))
    if record is None or record.thumbnail_relative_path is None:
        raise HTTPException(status_code=404, detail="Analysis thumbnail was not found")
    try:
        content, media_type = await run_in_threadpool(
            history_service.thumbnail_store.read_thumbnail,
            record.thumbnail_relative_path,
        )
    except PersistenceError as error:
        raise HTTPException(
            status_code=404,
            detail="Analysis thumbnail was not found",
        ) from error
    return Response(
        content=content,
        media_type=media_type,
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"},
    )



_METADATA_FIELD_MESSAGES = {
    "patient_code": (
        "Mã bệnh nhân/mã ca chỉ gồm chữ, số và dấu gạch ngang; "
        "có thể để trống."
    ),
    "patient_display_name": (
        "Tên hiển thị chỉ gồm chữ, khoảng trắng, dấu gạch ngang "
        "hoặc dấu nháy đơn."
    ),
    "patient_name_source": "Nguồn thông tin ca phân tích chưa hợp lệ.",
    "patient_info_confirmed": "Bạn cần xác nhận thông tin trước khi phân tích.",
    "is_anonymous_sample": "Trạng thái ảnh ẩn danh/demo chưa hợp lệ.",
}


def _case_metadata_validation_detail(error: ValidationError) -> dict[str, object]:
    """Return safe field errors without echoing patient-entered values."""

    field_errors: dict[str, str] = {}
    for item in error.errors(include_input=False):
        location = tuple(str(part) for part in item.get("loc", ()))
        field = next(
            (part for part in reversed(location) if part in _METADATA_FIELD_MESSAGES),
            None,
        )
        if field is None:
            message = str(item.get("msg", "")).lower()
            if "confirmed" in message:
                field = "patient_info_confirmed"
            elif "anonymous" in message:
                field = "is_anonymous_sample"
            elif "identified cases" in message or "name and source" in message:
                field = "patient_display_name"
        if field is not None:
            field_errors.setdefault(field, _METADATA_FIELD_MESSAGES[field])

    if not field_errors:
        field_errors["patient_info_confirmed"] = (
            "Thông tin ca phân tích chưa hợp lệ. Vui lòng kiểm tra lại."
        )

    return {
        "code": "invalid_case_metadata",
        "message": (
            "Thông tin ca phân tích chưa hợp lệ. "
            "Vui lòng kiểm tra các trường được đánh dấu."
        ),
        "field_errors": field_errors,
    }

def _supports_persisted_analysis(service: object) -> bool:
    return callable(getattr(service, "validate_upload", None)) and callable(
        getattr(service, "predict_validated_image", None)
    )


def _case_metadata_response(record: AnalysisHistoryRecord) -> CaseMetadataResponse:
    return CaseMetadataResponse(
        patient_code=record.patient_code,
        patient_display_name=record.patient_display_name,
        patient_name_source=record.patient_name_source,
        patient_info_confirmed=record.patient_info_confirmed,
        is_anonymous_sample=record.is_anonymous_sample,
    )


def _summary_response(record: AnalysisHistoryRecord) -> AnalysisSummary:
    probabilities = {
        "normal": record.normal_probability,
        "pneumonia": record.pneumonia_probability,
        "tuberculosis": record.tuberculosis_probability,
    }
    return AnalysisSummary(
        analysis_id=UUID(record.id),
        **_case_metadata_response(record).model_dump(),
        original_filename=record.original_filename,
        predicted_label=record.predicted_label,
        model_probability=probabilities[record.predicted_label],
        model_version=record.model_version,
        processing_time_ms=record.processing_time_ms,
        analyzed_at=record.analyzed_at,
        thumbnail_available=record.thumbnail_relative_path is not None,
    )


def _detail_response(record: AnalysisHistoryRecord) -> AnalysisDetail:
    summary = _summary_response(record)
    return AnalysisDetail(
        **summary.model_dump(),
        normal_probability=record.normal_probability,
        pneumonia_probability=record.pneumonia_probability,
        tuberculosis_probability=record.tuberculosis_probability,
        knowledge_base_version=record.knowledge_base_version,
        prediction_disclaimer=record.prediction_disclaimer,
        reference_source_ids=list(record.reference_source_ids),
        filename_pattern_id=record.filename_pattern_id,
        parsed_filename_date=record.parsed_filename_date,
        created_at=record.created_at,
        thumbnail_url=(
            f"/api/v1/analyses/{record.id}/thumbnail"
            if summary.thumbnail_available
            else None
        ),
        report_url=f"/api/v1/analyses/{record.id}/report.pdf",
    )


def _normalize_history_query(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.strip().split())
    if not normalized:
        return None
    if any(character in normalized for character in ("<", ">", "&", "/", "\\")):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="patient_query contains unsupported characters",
        )
    return normalized


def _local_day_boundary(value: date | None, offset_minutes: int) -> datetime | None:
    if value is None:
        return None
    local_timezone = timezone(timedelta(minutes=offset_minutes))
    return datetime.combine(value, time.min, tzinfo=local_timezone).astimezone(timezone.utc)


def _local_next_day_boundary(value: date | None, offset_minutes: int) -> datetime | None:
    if value is None:
        return None
    return _local_day_boundary(value + timedelta(days=1), offset_minutes)
