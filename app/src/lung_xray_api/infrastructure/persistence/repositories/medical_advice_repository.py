from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from lung_xray_api.infrastructure.persistence.orm.analysis_model import (
    AnalysisModel,
)
from lung_xray_api.infrastructure.persistence.orm.medical_advice_model import (
    MedicalAdviceModel,
)


class MedicalAdviceRepository:

    def create(
        self,
        db: Session,
        *,
        analysis_id: int,
        language: str,
        provider: str,
        model_name: str | None,
        advice_text: str,
    ) -> MedicalAdviceModel:

        advice = MedicalAdviceModel(
            analysis_id=analysis_id,
            language=language,
            provider=provider,
            model_name=model_name,
            advice_text=advice_text,
        )

        try:
            db.add(advice)
            db.commit()
            db.refresh(advice)

            return advice

        except Exception:
            db.rollback()
            raise

    def get_by_id(
        self,
        db: Session,
        advice_id: int,
    ) -> MedicalAdviceModel | None:

        statement = (
            select(MedicalAdviceModel)
            .where(
                MedicalAdviceModel.id
                == advice_id
            )
            .options(
                selectinload(
                    MedicalAdviceModel.analysis
                ).selectinload(
                    AnalysisModel.patient
                )
            )
        )

        return db.scalar(statement)

    def list_by_analysis_id(
        self,
        db: Session,
        analysis_id: int,
    ) -> list[MedicalAdviceModel]:

        statement = (
            select(MedicalAdviceModel)
            .where(
                MedicalAdviceModel.analysis_id
                == analysis_id
            )
            .order_by(
                MedicalAdviceModel.created_at.desc(),
                MedicalAdviceModel.id.desc(),
            )
        )

        return list(
            db.scalars(statement).all()
        )
