from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
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
from lung_xray_api.infrastructure.reporting.drai_pdf_generator import (
    drai_pdf_generator,
)
from lung_xray_api.infrastructure.persistence.database import (
    get_db,
)
from lung_xray_api.infrastructure.persistence.orm import (
    UserModel,
)
from lung_xray_api.infrastructure.persistence.repositories.analysis_repository import (
    AnalysisRepository,
)
from lung_xray_api.schemas.medical_advice import (
    MedicalAdviceCreate,
    MedicalAdviceResponse,
)


analysis_repository = AnalysisRepository()


def _read_analysis_image_bytes(
    analysis,
) -> bytes | None:
    stored_path = getattr(
        analysis,
        "stored_image_path",
        None,
    )

    if not stored_path:
        return None

    file_path = Path(
        stored_path
    )

    if not file_path.is_absolute():
        file_path = (
            Path.cwd()
            / file_path
        )

    file_path = file_path.resolve()

    if (
        not file_path.is_file()
        or file_path.suffix.lower()
        not in {
            ".jpg",
            ".jpeg",
            ".png",
        }
    ):
        return None

    try:
        return file_path.read_bytes()

    except OSError:
        return None


def _format_analysis_timestamp(
    value,
) -> str | None:
    if value is None:
        return None

    time_text = (
        value.strftime(
            "%I:%M:%S %p"
        )
        .lstrip("0")
    )

    return (
        f"{value.month}/"
        f"{value.day}/"
        f"{value.year}, "
        f"{time_text}"
    )


def _extract_analysis_probabilities(
    analysis,
) -> dict[str, float] | None:
    prediction = getattr(
        analysis,
        "prediction",
        None,
    )

    if prediction is None:
        return None

    rows = getattr(
        prediction,
        "probabilities",
        None,
    )

    if not rows:
        return None

    result = {
        str(row.class_name): float(
            row.probability
        )
        for row in rows
    }

    return result or None


router = APIRouter(
    prefix="/api/v1/medical-advices",
    tags=["Medical Advices"],
)


analysis_router = APIRouter(
    prefix="/api/v1/analyses",
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


@router.get(
    "/{advice_id}",
    response_model=MedicalAdviceResponse,
)
def get_medical_advice(
    advice_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(
        get_current_user
    ),
):
    try:
        return (
            medical_advice_service
            .get_advice(
                db,
                current_user,
                advice_id=advice_id,
            )
        )

    except (
        LookupError,
        PermissionError,
    ) as exc:
        _raise_medical_advice_http_exception(
            exc
        )


@router.get(
    "/{advice_id}/download",
)
def download_medical_advice_pdf(
    advice_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(
        get_current_user
    ),
):
    try:
        advice = (
            medical_advice_service
            .get_advice(
                db,
                current_user,
                advice_id=advice_id,
            )
        )

        analysis = (
            analysis_repository
            .get_by_id(
                db,
                advice.analysis_id,
            )
        )

        if analysis is None:
            raise LookupError(
                "Analysis not found."
            )

        xray_image_bytes = (
            _read_analysis_image_bytes(
                analysis
            )
        )

        probabilities = (
            _extract_analysis_probabilities(
                analysis
            )
        )

        analysis_timestamp = (
            _format_analysis_timestamp(
                analysis.created_at
            )
        )

        pdf_bytes = (
            drai_pdf_generator
            .generate_bytes(
                advice_text=(
                    advice.advice_text
                ),
                xray_image_bytes=(
                    xray_image_bytes
                ),
                xray_filename=(
                    analysis.original_filename
                ),
                analysis_code=(
                    analysis.analysis_code
                ),
                analysis_timestamp=(
                    analysis_timestamp
                ),
                probabilities=(
                    probabilities
                ),
            )
        )

        filename = (
            f"DrAI-analysis-"
            f"{advice.analysis_id}-"
            f"advice-{advice.id}-"
            f"{advice.language}.pdf"
        )

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{filename}"'
                ),
                "Cache-Control": "no-store",
            },
        )

    except (
        LookupError,
        ValueError,
        PermissionError,
    ) as exc:
        _raise_medical_advice_http_exception(
            exc
        )


@analysis_router.get(
    "/{analysis_id}/medical-advices",
    response_model=list[
        MedicalAdviceResponse
    ],
)
def list_analysis_medical_advices(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(
        get_current_user
    ),
):
    try:
        return (
            medical_advice_service
            .list_analysis_advices(
                db,
                current_user,
                analysis_id=analysis_id,
            )
        )

    except (
        LookupError,
        PermissionError,
    ) as exc:
        _raise_medical_advice_http_exception(
            exc
        )

