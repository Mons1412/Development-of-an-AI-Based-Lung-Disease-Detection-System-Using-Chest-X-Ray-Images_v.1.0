from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from lung_xray_api.api.dependencies.auth import (
    get_current_user,
)
from lung_xray_api.application.services.report_service import (
    report_service,
)
from lung_xray_api.infrastructure.persistence.database import (
    get_db,
)
from lung_xray_api.infrastructure.persistence.orm import (
    UserModel,
)
from lung_xray_api.schemas.report import (
    ReportCreate,
    ReportResponse,
)


router = APIRouter(
    prefix="/api/v1/reports",
    tags=["Reports"],
)


def _raise_report_http_exception(
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
        FileNotFoundError,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    raise exc


@router.post(
    "",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_report(
    request: ReportCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(
        get_current_user
    ),
):
    try:
        return report_service.generate_report(
            db,
            current_user,
            analysis_id=request.analysis_id,
            language=request.language,
        )

    except (
        LookupError,
        ValueError,
        PermissionError,
    ) as exc:
        _raise_report_http_exception(
            exc
        )


@router.get(
    "/{report_id}",
    response_model=ReportResponse,
)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(
        get_current_user
    ),
):
    try:
        return report_service.get_report(
            db,
            current_user,
            report_id=report_id,
        )

    except (
        LookupError,
        PermissionError,
    ) as exc:
        _raise_report_http_exception(
            exc
        )


@router.get(
    "/{report_id}/preview",
)
def preview_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(
        get_current_user
    ),
):
    try:
        report, file_path = (
            report_service.resolve_report_file(
                db,
                current_user,
                report_id=report_id,
            )
        )

    except (
        LookupError,
        PermissionError,
        FileNotFoundError,
    ) as exc:
        _raise_report_http_exception(
            exc
        )

    filename = (
        f"{report.report_code}.pdf"
    )

    return FileResponse(
        path=str(
            file_path
        ),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'inline; filename="{filename}"'
            )
        },
    )


@router.get(
    "/{report_id}/download",
)
def download_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(
        get_current_user
    ),
):
    try:
        report, file_path = (
            report_service.resolve_report_file(
                db,
                current_user,
                report_id=report_id,
            )
        )

    except (
        LookupError,
        PermissionError,
        FileNotFoundError,
    ) as exc:
        _raise_report_http_exception(
            exc
        )

    filename = (
        f"{report.report_code}.pdf"
    )

    return FileResponse(
        path=str(
            file_path
        ),
        media_type="application/pdf",
        filename=filename,
    )
