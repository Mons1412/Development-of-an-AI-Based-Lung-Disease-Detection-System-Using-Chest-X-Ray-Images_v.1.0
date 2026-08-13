"""Model metadata endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends

from lung_xray_api.api.dependencies import get_prediction_service, require_api_key
from lung_xray_api.application.prediction_service import PredictionServiceProtocol
from lung_xray_api.schemas.model_info import ModelInfoResponse

router = APIRouter(tags=["model"])


@router.get(
    "/api/v1/model-info",
    response_model=ModelInfoResponse,
)
def model_info(
    service: Annotated[PredictionServiceProtocol, Depends(get_prediction_service)],
    _authorized: Annotated[None, Depends(require_api_key)],
) -> dict[str, object]:
    return service.model_info()
