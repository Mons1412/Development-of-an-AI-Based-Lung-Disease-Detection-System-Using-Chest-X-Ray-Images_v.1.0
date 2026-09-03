from sqlalchemy.orm import Session

from lung_xray_api.infrastructure.persistence.orm import AIModel
from lung_xray_api.infrastructure.persistence.repositories.ai_model_repository import (
    AIModelRepository,
)


class AIModelService:

    def __init__(self) -> None:
        self.repository = AIModelRepository()

    def list_available_models(
        self,
        db: Session,
    ) -> list[AIModel]:

        return self.repository.list_active(db)

    def get_available_model(
        self,
        db: Session,
        model_id: int,
    ) -> AIModel:

        model = self.repository.get_by_id(
            db,
            model_id,
        )

        if model is None:
            raise LookupError(
                "AI model not found."
            )

        if not model.is_active:
            raise LookupError(
                "AI model is not available."
            )

        return model

    def get_default_model(
        self,
        db: Session,
    ) -> AIModel:

        model = self.repository.get_default(db)

        if model is None:
            raise LookupError(
                "Default AI model not found."
            )

        return model


ai_model_service = AIModelService()