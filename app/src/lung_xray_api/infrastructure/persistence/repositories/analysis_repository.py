from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import (
    Session,
    selectinload,
)

from lung_xray_api.infrastructure.persistence.orm import (
    AnalysisModel,
    PredictionModel,
)


class AnalysisRepository:

    def create_pending(
        self,
        db: Session,
        *,
        analysis_code: str,
        patient_id: int,
        model_id: int,
        input_source: str,
        original_filename: str,
        stored_image_path: str,
    ) -> AnalysisModel:

        analysis = AnalysisModel(
            analysis_code=analysis_code,
            patient_id=patient_id,
            model_id=model_id,
            input_source=input_source,
            original_filename=original_filename,
            stored_image_path=stored_image_path,
            status="PENDING",
        )

        try:
            db.add(analysis)
            db.commit()
            db.refresh(analysis)

            return analysis

        except Exception:
            db.rollback()
            raise

    def get_by_id_for_patient(
        self,
        db: Session,
        *,
        analysis_id: int,
        patient_id: int,
    ) -> AnalysisModel | None:

        statement = (
            select(AnalysisModel)
            .where(
                AnalysisModel.id
                == analysis_id,
                AnalysisModel.patient_id
                == patient_id,
            )
            .options(
                selectinload(
                    AnalysisModel.ai_model
                ),
                selectinload(
                    AnalysisModel.prediction
                ).selectinload(
                    PredictionModel.probabilities
                ),
            )
        )

        return db.scalar(statement)

    def list_by_patient_id(
        self,
        db: Session,
        patient_id: int,
    ) -> list[AnalysisModel]:

        statement = (
            select(AnalysisModel)
            .where(
                AnalysisModel.patient_id
                == patient_id
            )
            .options(
                selectinload(
                    AnalysisModel.ai_model
                ),
                selectinload(
                    AnalysisModel.prediction
                ).selectinload(
                    PredictionModel.probabilities
                ),
            )
            .order_by(
                AnalysisModel.created_at.desc(),
                AnalysisModel.id.desc(),
            )
        )

        return list(
            db.scalars(statement).all()
        )

    def mark_completed(
        self,
        db: Session,
        analysis: AnalysisModel,
    ) -> None:

        analysis.status = "COMPLETED"

        analysis.completed_at = (
            datetime.now(
                timezone.utc
            ).replace(
                tzinfo=None
            )
        )

        analysis.error_message = None

        try:
            db.commit()

        except Exception:
            db.rollback()
            raise

    def mark_failed(
        self,
        db: Session,
        analysis_id: int,
        error_message: str,
    ) -> None:

        analysis = db.get(
            AnalysisModel,
            analysis_id,
        )

        if analysis is None:
            return

        analysis.status = "FAILED"

        analysis.error_message = (
            error_message[:2000]
        )

        analysis.completed_at = (
            datetime.now(
                timezone.utc
            ).replace(
                tzinfo=None
            )
        )

        try:
            db.commit()

        except Exception:
            db.rollback()
            raise