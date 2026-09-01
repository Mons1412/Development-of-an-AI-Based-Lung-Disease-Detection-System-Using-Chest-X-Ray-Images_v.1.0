from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from lung_xray_api.api.dependencies.auth import require_user
from lung_xray_api.application.services.patient_profile_service import (
    patient_profile_service,
)
from lung_xray_api.infrastructure.persistence.database import get_db
from lung_xray_api.infrastructure.persistence.orm import UserModel
from lung_xray_api.schemas.patient_profile import (
    PatientProfileCreate,
    PatientProfileResponse,
    PatientProfileUpdate,
)


router = APIRouter(
    prefix="/api/v1/patient-profile",
    tags=["Patient Profile"],
)


@router.post(
    "",
    response_model=PatientProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_patient_profile(
    request: PatientProfileCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_user),
):
    try:
        return patient_profile_service.create_profile(
            db,
            current_user,
            request,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )


@router.get(
    "/me",
    response_model=PatientProfileResponse,
)
def get_my_patient_profile(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_user),
):
    try:
        return patient_profile_service.get_my_profile(
            db,
            current_user,
        )

    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.patch(
    "/me",
    response_model=PatientProfileResponse,
)
def update_my_patient_profile(
    request: PatientProfileUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_user),
):
    try:
        return patient_profile_service.update_my_profile(
            db,
            current_user,
            request,
        )

    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )