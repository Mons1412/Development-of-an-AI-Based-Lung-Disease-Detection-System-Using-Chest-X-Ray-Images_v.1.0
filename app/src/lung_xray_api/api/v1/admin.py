from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.orm import Session

from lung_xray_api.api.dependencies.auth import (
    require_admin,
)
from lung_xray_api.application.services.analysis_service import (
    analysis_service,
)
from lung_xray_api.infrastructure.persistence.database import (
    get_db,
)
from lung_xray_api.infrastructure.persistence.orm import (
    UserModel,
)
from lung_xray_api.infrastructure.persistence.repositories.user_repository import (
    UserRepository,
)
from lung_xray_api.schemas.analysis import (
    AnalysisResponse,
)
from lung_xray_api.schemas.auth import (
    UserResponse,
)


router = APIRouter(
    prefix="/api/v1/admin",
    tags=["Admin"],
)


user_repository = UserRepository()


@router.get(
    "/users",
    response_model=list[UserResponse],
)
def list_users(
    db: Session = Depends(get_db),
    current_admin: UserModel = Depends(
        require_admin
    ),
):
    del current_admin

    return user_repository.list_all(
        db
    )


@router.get(
    "/analyses",
    response_model=list[AnalysisResponse],
)
def list_patient_analyses(
    patient_code: Annotated[
        str,
        Query(
            min_length=1,
            max_length=64,
            description=(
                "Patient code whose analysis "
                "history should be returned."
            ),
        ),
    ],
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=100,
            description=(
                "Maximum number of analyses "
                "to return."
            ),
        ),
    ] = 20,
    offset: Annotated[
        int,
        Query(
            ge=0,
            description=(
                "Number of analyses to skip."
            ),
        ),
    ] = 0,
    db: Session = Depends(get_db),
    current_admin: UserModel = Depends(
        require_admin
    ),
):
    del current_admin

    try:
        return (
            analysis_service
            .list_patient_analyses_for_admin(
                db,
                patient_code=patient_code,
                limit=limit,
                offset=offset,
            )
        )

    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc