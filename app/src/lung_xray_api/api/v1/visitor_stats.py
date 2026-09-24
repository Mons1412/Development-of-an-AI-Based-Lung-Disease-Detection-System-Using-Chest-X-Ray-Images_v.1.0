from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from lung_xray_api.application.services.visitor_stats_service import (
    visitor_stats_service,
)
from lung_xray_api.infrastructure.persistence.database import (
    get_db,
)
from lung_xray_api.schemas.visitor_stats import (
    VisitorHeartbeatRequest,
    VisitorStatsResponse,
)


router = APIRouter(
    prefix="/api/v1/visitor-stats",
    tags=[
        "Visitor Stats",
    ],
)


@router.get(
    "",
    response_model=VisitorStatsResponse,
)
def get_visitor_stats(
    db: Session = Depends(
        get_db
    ),
):
    try:
        return (
            visitor_stats_service
            .get_stats(
                db
            )
        )

    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=(
                "Visitor statistics "
                "are temporarily unavailable."
            ),
        ) from exc


@router.post(
    "/heartbeat",
    response_model=VisitorStatsResponse,
)
def visitor_heartbeat(
    request: VisitorHeartbeatRequest,
    db: Session = Depends(
        get_db
    ),
):
    try:
        return (
            visitor_stats_service
            .heartbeat(
                db,
                visitor_id=(
                    request.visitor_id
                ),
                session_id=(
                    request.session_id
                ),
            )
        )

    except SQLAlchemyError as exc:
        db.rollback()

        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=(
                "Visitor statistics "
                "are temporarily unavailable."
            ),
        ) from exc
