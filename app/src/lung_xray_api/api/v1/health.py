from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from lung_xray_api.infrastructure.persistence.database import (
    check_database_connection,
)


router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.get("/live")
def health_live():
    return {
        "status": "ok",
        "service": "LungXrayAI",
	"version": "1.5.0-dev",
    }


@router.get("/ready")
def health_ready():
    try:
        if not check_database_connection():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database is not ready.",
            )

        return {
            "status": "ready",
            "database": "connected",
        }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not ready.",
        )