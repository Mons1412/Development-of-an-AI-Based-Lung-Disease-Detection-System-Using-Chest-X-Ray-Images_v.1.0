from sqlalchemy.orm import Session

from lung_xray_api.core.security import (
    hash_password,
    verify_password,
)
from lung_xray_api.infrastructure.persistence.orm import UserModel
from lung_xray_api.infrastructure.persistence.repositories.user_repository import (
    UserRepository,
)
from lung_xray_api.schemas.auth import RegisterRequest


class AuthService:

    def __init__(self) -> None:
        self.user_repository = UserRepository()

    def register_user(
        self,
        db: Session,
        request: RegisterRequest,
    ) -> UserModel:

        username = request.username.strip()
        email = str(request.email).strip().lower()

        existing_username = self.user_repository.get_by_username(
            db,
            username,
        )

        if existing_username is not None:
            raise ValueError("Username already exists.")

        existing_email = self.user_repository.get_by_email(
            db,
            email,
        )

        if existing_email is not None:
            raise ValueError("Email already exists.")

        hashed_password = hash_password(request.password)

        return self.user_repository.create(
            db,
            username=username,
            email=email,
            password_hash=hashed_password,
            role="USER",
        )

    def authenticate_user(
        self,
        db: Session,
        username: str,
        password: str,
    ) -> UserModel | None:

        user = self.user_repository.get_by_username(
            db,
            username.strip(),
        )

        if user is None:
            return None

        if not user.is_active:
            return None

        if not verify_password(
            password,
            user.password_hash,
        ):
            return None

        return user


auth_service = AuthService()