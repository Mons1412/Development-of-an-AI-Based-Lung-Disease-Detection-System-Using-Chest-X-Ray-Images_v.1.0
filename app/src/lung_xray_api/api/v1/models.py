from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from lung_xray_api.api.dependencies.auth import get_current_user
from lung_xray_api.application.services.ai_model_service import (
    ai_model_service,
)
from lung_xray_api.infrastructure.persistence.database import get_db
from lung_xray_api.infrastructure.persistence.orm import UserModel
from lung_xray_api.schemas.ai_model import AIModelResponse


router = APIRouter(
    prefix="/api/v1/models",
    tags=["AI Models"],
)


@router.get(
    "",
    response_model=list[AIModelResponse],
)
def list_models(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    return ai_model_service.list_available_models(db)


@router.get(
    "/default",
    response_model=AIModelResponse,
)
def get_default_model(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    try:
        return ai_model_service.get_default_model(db)

    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.get(
    "/{model_id}",
    response_model=AIModelResponse,
)
def get_model(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    try:
        return ai_model_service.get_available_model(
            db,
            model_id,
        )

    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )