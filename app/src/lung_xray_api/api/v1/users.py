from fastapi import APIRouter, Depends

from lung_xray_api.api.dependencies.auth import get_current_user
from lung_xray_api.infrastructure.persistence.orm import UserModel
from lung_xray_api.schemas.auth import UserResponse


router = APIRouter(
    prefix="/api/v1/users",
    tags=["Users"],
)


@router.get(
    "/me",
    response_model=UserResponse,
)
def get_me(
    current_user: UserModel = Depends(get_current_user),
):
    return current_user