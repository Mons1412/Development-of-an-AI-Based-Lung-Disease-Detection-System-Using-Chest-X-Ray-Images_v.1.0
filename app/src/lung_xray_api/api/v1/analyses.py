from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
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
from lung_xray_api.application.services.batch_analysis_service import (
    BatchImageInput,
    batch_analysis_service,
)
from lung_xray_api.core.batch_limits import (
    MAX_BATCH_FILES,
    MAX_BATCH_TOTAL_BYTES,
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
from lung_xray_api.schemas.batch_analysis import (
    BatchAnalysisResponse,
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
    file: Annotated[
        UploadFile,
        File(
            description="Chest X-ray image file."
        ),
    ],
    model_id: Annotated[
        int | None,
        Form(),
    ] = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(
        require_user
    ),
):
    try:
        image_bytes = file.file.read(
            MAX_IMAGE_BYTES + 1
        )

    finally:
        file.file.close()

    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image file is empty.",
        )

    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            ),
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
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=str(exc),
        )


@router.post(
    "/batch",
    response_model=BatchAnalysisResponse,
    status_code=status.HTTP_200_OK,
)
def create_batch_analysis(
    files: Annotated[
        list[UploadFile],
        File(
            description=(
                "Select multiple image files "
                "for batch analysis."
            )
        ),
    ],
    model_id: Annotated[
        int | None,
        Form(),
    ] = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(
        require_user
    ),
):
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "At least one image is required."
            ),
        )

    if len(files) > MAX_BATCH_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Too many files in batch. "
                f"Maximum is {MAX_BATCH_FILES}."
            ),
        )

    images: list[BatchImageInput] = []

    total_bytes = 0

    for index, file in enumerate(
        files,
        start=1,
    ):
        try:
            image_bytes = file.file.read(
                MAX_IMAGE_BYTES + 1
            )

        finally:
            file.file.close()

        total_bytes += len(
            image_bytes
        )

        if total_bytes > MAX_BATCH_TOTAL_BYTES:
            max_mb = (
                MAX_BATCH_TOTAL_BYTES
                // 1024
                // 1024
            )

            raise HTTPException(
                status_code=(
                    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
                ),
                detail=(
                    "Batch size is too large. "
                    f"Maximum total size is "
                    f"{max_mb} MB."
                ),
            )

        original_filename = (
            file.filename
            or f"uploaded_image_{index}"
        )

        images.append(
            BatchImageInput(
                image_bytes=image_bytes,
                original_filename=(
                    original_filename
                ),
                content_type=file.content_type,
            )
        )

    try:
        return (
            batch_analysis_service
            .analyze_images(
                db,
                current_user,
                images=images,
                model_id=model_id,
            )
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
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=str(exc),
        )

@router.get(
    "",
    response_model=list[AnalysisResponse],
)
def list_my_analyses(
    patient_code: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=64,
            description=(
                "Optional patient code. "
                "USER can only query their "
                "own patient profile."
            ),
        ),
    ] = None,
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
                patient_code=patient_code,
                limit=limit,
                offset=offset,
            )
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