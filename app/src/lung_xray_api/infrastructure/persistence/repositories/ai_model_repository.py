from sqlalchemy import select
from sqlalchemy.orm import Session

from lung_xray_api.infrastructure.persistence.orm import AIModel


class AIModelRepository:

    def list_active(
        self,
        db: Session,
    ) -> list[AIModel]:

        statement = (
            select(AIModel)
            .where(
                AIModel.is_active.is_(True)
            )
            .order_by(
                AIModel.is_default.desc(),
                AIModel.display_name.asc(),
                AIModel.version.desc(),
            )
        )

        return list(
            db.scalars(statement).all()
        )

    def get_by_id(
        self,
        db: Session,
        model_id: int,
    ) -> AIModel | None:

        return db.get(
            AIModel,
            model_id,
        )

    def get_by_key_version(
        self,
        db: Session,
        *,
        model_key: str,
        version: str,
    ) -> AIModel | None:

        statement = select(AIModel).where(
            AIModel.model_key == model_key,
            AIModel.version == version,
        )

        return db.scalar(statement)

    def get_default(
        self,
        db: Session,
    ) -> AIModel | None:

        statement = select(AIModel).where(
            AIModel.is_active.is_(True),
            AIModel.is_default.is_(True),
        )

        return db.scalar(statement)

    def create(
        self,
        db: Session,
        *,
        model_key: str,
        display_name: str,
        architecture: str,
        version: str,
        artifact_path: str,
        class_names: list[str],
        is_active: bool = True,
        is_default: bool = False,
    ) -> AIModel:

        model = AIModel(
            model_key=model_key,
            display_name=display_name,
            architecture=architecture,
            version=version,
            artifact_path=artifact_path,
            class_names=class_names,
            is_active=is_active,
            is_default=is_default,
        )

        try:
            db.add(model)
            db.commit()
            db.refresh(model)

            return model

        except Exception:
            db.rollback()
            raise