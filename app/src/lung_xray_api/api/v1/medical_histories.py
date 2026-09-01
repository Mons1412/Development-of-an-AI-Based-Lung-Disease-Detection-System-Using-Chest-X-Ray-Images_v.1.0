from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from lung_xray_api.api.dependencies.auth import require_user
from lung_xray_api.application.services.medical_history_service import (
    medical_history_service,
)
from lung_xray_api.infrastructure.persistence.database import get_db
from lung_xray_api.infrastructure.persistence.orm import UserModel
from lung_xray_api.schemas.medical_history import (
    MedicalHistoryCreate,
    MedicalHistoryResponse,
    MedicalHistoryUpdate,
)


router = APIRouter(
    prefix="/api/v1/medical-histories",
    tags=["Medical History"],
)


@router.post(
    "",
    response_model=MedicalHistoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_medical_history(
    request: MedicalHistoryCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_user),
):
    try:
        return medical_history_service.create_history(
            db,
            current_user,
            request,
        )

    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.get(
    "",
    response_model=list[MedicalHistoryResponse],
)
def list_my_medical_histories(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_user),
):
    try:
        return medical_history_service.list_my_histories(
            db,
            current_user,
        )

    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.get(
    "/{history_id}",
    response_model=MedicalHistoryResponse,
)
def get_my_medical_history(
    history_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_user),
):
    try:
        return medical_history_service.get_my_history(
            db,
            current_user,
            history_id,
        )

    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.patch(
    "/{history_id}",
    response_model=MedicalHistoryResponse,
)
def update_my_medical_history(
    history_id: int,
    request: MedicalHistoryUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_user),
):
    try:
        return medical_history_service.update_my_history(
            db,
            current_user,
            history_id,
            request,
        )

    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )