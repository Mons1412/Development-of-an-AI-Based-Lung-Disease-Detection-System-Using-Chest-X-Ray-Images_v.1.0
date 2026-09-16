from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from lung_xray_api.api.dependencies.auth import (
    get_current_user,
)
from lung_xray_api.application.services.medical_advice_provider import (
    MedicalAdviceProviderConfigurationError,
    MedicalAdviceProviderError,
)
from lung_xray_api.application.services.medical_advice_service import (
    medical_advice_service,
)
from lung_xray_api.infrastructure.persistence.database import (
    get_db,
)
from lung_xray_api.infrastructure.persistence.orm import (
    UserModel,
)
from lung_xray_api.schemas.medical_advice import (
    MedicalAdviceCreate,
    MedicalAdviceResponse,
)


router = APIRouter(
    prefix="/api/v1/medical-advices",
    tags=["Medical Advices"],
)


def _raise_medical_advice_http_exception(
    exc: Exception,
) -> None:

    if isinstance(
        exc,
        LookupError,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    if isinstance(
        exc,
        ValueError,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    if isinstance(
        exc,
        PermissionError,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )

    if isinstance(
        exc,
        MedicalAdviceProviderConfigurationError,
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=str(exc),
        )

    if isinstance(
        exc,
        MedicalAdviceProviderError,
    ):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )

    raise exc


@router.post(
    "",
    response_model=MedicalAdviceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_medical_advice(
    request: MedicalAdviceCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(
        get_current_user
    ),
):
    try:
        return (
            medical_advice_service
            .generate_advice(
                db,
                current_user,
                analysis_id=(
                    request.analysis_id
                ),
                language=request.language,
            )
        )

    except (
        LookupError,
        ValueError,
        PermissionError,
        MedicalAdviceProviderConfigurationError,
        MedicalAdviceProviderError,
    ) as exc:
        _raise_medical_advice_http_exception(
            exc
        )
