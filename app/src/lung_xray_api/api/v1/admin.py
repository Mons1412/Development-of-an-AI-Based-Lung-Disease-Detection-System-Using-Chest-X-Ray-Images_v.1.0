from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from lung_xray_api.api.dependencies.auth import require_admin
from lung_xray_api.infrastructure.persistence.database import get_db
from lung_xray_api.infrastructure.persistence.orm import UserModel
from lung_xray_api.infrastructure.persistence.repositories.user_repository import (
    UserRepository,
)
from lung_xray_api.schemas.auth import UserResponse


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
    current_admin: UserModel = Depends(require_admin),
):
    return user_repository.list_all(db)