from sqlalchemy import select
from sqlalchemy.orm import Session

from lung_xray_api.infrastructure.persistence.orm import (
    MedicalHistoryModel,
)


class MedicalHistoryRepository:

    def list_by_patient_id(
        self,
        db: Session,
        patient_id: int,
    ) -> list[MedicalHistoryModel]:
        statement = (
            select(
                MedicalHistoryModel
            )
            .where(
                MedicalHistoryModel.patient_id
                == patient_id
            )
            .order_by(
                MedicalHistoryModel.recorded_at
                .desc(),
                MedicalHistoryModel.id.desc(),
            )
        )

        return list(
            db.scalars(
                statement
            ).all()
        )

    def get_by_id_for_patient(
        self,
        db: Session,
        *,
        history_id: int,
        patient_id: int,
    ) -> MedicalHistoryModel | None:
        statement = select(
            MedicalHistoryModel
        ).where(
            MedicalHistoryModel.id
            == history_id,
            MedicalHistoryModel.patient_id
            == patient_id,
        )

        return db.scalar(
            statement
        )

    def create(
        self,
        db: Session,
        *,
        patient_id: int,
        current_complaint_hpi: str,
        past_medical_history: str,
        past_medication_history: str,
        allergy_history: str,
        diseases: list[str] | None,
        smoking_status: str | None,
        alcohol_status: str | None,
        occupational_exposure: str | None,
        diet: str,
        appetite: str,
        sleep: str,
        exercise: str,
        bowel_bladder: str,
        habits: str,
        family_history: str,
    ) -> MedicalHistoryModel:
        history = MedicalHistoryModel(
            patient_id=patient_id,
            current_complaint_hpi=(
                current_complaint_hpi
            ),
            past_medical_history=(
                past_medical_history
            ),
            past_medication_history=(
                past_medication_history
            ),
            allergy_history=(
                allergy_history
            ),
            diseases=diseases,
            smoking_status=smoking_status,
            alcohol_status=alcohol_status,
            occupational_exposure=(
                occupational_exposure
            ),
            diet=diet,
            appetite=appetite,
            sleep=sleep,
            exercise=exercise,
            bowel_bladder=(
                bowel_bladder
            ),
            habits=habits,
            family_history=(
                family_history
            ),
        )

        try:
            db.add(
                history
            )

            db.commit()

            db.refresh(
                history
            )

            return history

        except Exception:
            db.rollback()
            raise

    def update(
        self,
        db: Session,
        history: MedicalHistoryModel,
        changes: dict,
    ) -> MedicalHistoryModel:
        for field, value in changes.items():
            setattr(
                history,
                field,
                value,
            )

        try:
            db.commit()

            db.refresh(
                history
            )

            return history

        except Exception:
            db.rollback()
            raise
