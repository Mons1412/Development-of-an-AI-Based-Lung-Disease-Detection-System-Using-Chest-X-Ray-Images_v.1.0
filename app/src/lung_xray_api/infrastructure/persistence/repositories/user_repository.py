from sqlalchemy import select
from sqlalchemy.orm import Session

from lung_xray_api.infrastructure.persistence.orm import UserModel


class UserRepository:

    def get_by_id(
        self,
        db: Session,
        user_id: int,
    ) -> UserModel | None:
        return db.get(UserModel, user_id)

    def get_by_username(
        self,
        db: Session,
        username: str,
    ) -> UserModel | None:
        statement = select(UserModel).where(
            UserModel.username == username
        )

        return db.scalar(statement)

    def get_by_email(
        self,
        db: Session,
        email: str,
    ) -> UserModel | None:
        statement = select(UserModel).where(
            UserModel.email == email
        )

        return db.scalar(statement)

    def create(
        self,
        db: Session,
        *,
        username: str,
        email: str,
        password_hash: str,
        role: str = "USER",
    ) -> UserModel:

        user = UserModel(
            username=username,
            email=email,
            password_hash=password_hash,
            role=role,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user