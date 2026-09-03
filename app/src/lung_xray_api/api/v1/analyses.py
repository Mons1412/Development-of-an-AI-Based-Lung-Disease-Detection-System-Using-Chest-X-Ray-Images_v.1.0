from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from lung_xray_api.api.dependencies.auth import (
    require_user,
)
from lung_xray_api.application.services.analysis_service import (
    analysis_service,
)
from lung_xray_api.infrastructure.imaging.image_validator import (
    MAX_IMAGE_BYTES,
)
from lung_xray_api.infrastructure.persistence.database import (
    get_db,
)
from lung_xray_api.infrastructure.persistence.orm import (
    UserModel,
)
from lung_xray_api.schemas.analysis import (
    AnalysisResponse,
)


router = APIRouter(
    prefix="/api/v1/analyses",
    tags=["Analyses"],
)


@router.post(
    "",
    response_model=AnalysisResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_analysis(
    file: UploadFile = File(...),
    model_id: int | None = Form(
        default=None
    ),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(
        require_user
    ),
):

    image_bytes = file.file.read(
        MAX_IMAGE_BYTES + 1
    )

    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image file is empty.",
        )

    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image is too large.",
        )

    try:
        return analysis_service.analyze_image(
            db,
            current_user,
            image_bytes=image_bytes,
            original_filename=(
                file.filename
                or "uploaded_image"
            ),
            content_type=file.content_type,
            model_id=model_id,
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

    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.get(
    "",
    response_model=list[AnalysisResponse],
)
def list_my_analyses(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(
        require_user
    ),
):
    try:
        return (
            analysis_service
            .list_my_analyses(
                db,
                current_user,
            )
        )

    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.get(
    "/{analysis_id}",
    response_model=AnalysisResponse,
)
def get_my_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(
        require_user
    ),
):
    try:
        return (
            analysis_service
            .get_my_analysis(
                db,
                current_user,
                analysis_id,
            )
        )

    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )