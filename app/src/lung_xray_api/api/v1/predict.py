"""Backward-compatible non-persistent prediction endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.concurrency import run_in_threadpool

from lung_xray_api.api.dependencies import get_prediction_service, require_api_key
from lung_xray_api.api.upload import read_upload_bounded
from lung_xray_api.application.prediction_service import PredictionServiceProtocol
from lung_xray_api.schemas.prediction import PredictionResponse

router = APIRouter(tags=["prediction"])


async def _predict_upload(
    request: Request,
    file: UploadFile,
    service: PredictionServiceProtocol,
) -> dict[str, object]:
    content = await read_upload_bounded(file, request.app.state.settings.max_upload_bytes)
    result = await run_in_threadpool(
        service.predict_bytes,
        content,
        file.filename or "upload",
        file.content_type,
    )
    return result.to_response()


@router.post("/api/v1/predict", response_model=PredictionResponse)
async def predict(
    request: Request,
    file: Annotated[UploadFile, File(...)],
    service: Annotated[PredictionServiceProtocol, Depends(get_prediction_service)],
    _authorized: Annotated[None, Depends(require_api_key)],
) -> dict[str, object]:
    return await _predict_upload(request, file, service)


@router.post("/predict", response_model=PredictionResponse)
async def predict_compatibility_alias(
    request: Request,
    file: Annotated[UploadFile, File(...)],
    service: Annotated[PredictionServiceProtocol, Depends(get_prediction_service)],
    _authorized: Annotated[None, Depends(require_api_key)],
) -> dict[str, object]:
    return await _predict_upload(request, file, service)
