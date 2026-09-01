from sqlalchemy import select
from sqlalchemy.orm import Session

from lung_xray_api.infrastructure.persistence.orm import MedicalHistoryModel


class MedicalHistoryRepository:

    def list_by_patient_id(
        self,
        db: Session,
        patient_id: int,
    ) -> list[MedicalHistoryModel]:

        statement = (
            select(MedicalHistoryModel)
            .where(
                MedicalHistoryModel.patient_id == patient_id
            )
            .order_by(
                MedicalHistoryModel.recorded_at.desc(),
                MedicalHistoryModel.id.desc(),
            )
        )

        return list(
            db.scalars(statement).all()
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
            MedicalHistoryModel.id == history_id,
            MedicalHistoryModel.patient_id == patient_id,
        )

        return db.scalar(statement)

    def create(
        self,
        db: Session,
        *,
        patient_id: int,
        diseases: list[str] | None,
        medications: list[str] | None,
        allergies: list[str] | None,
        smoking_status: str | None,
        alcohol_status: str | None,
        occupational_exposure: str | None,
        notes: str | None,
    ) -> MedicalHistoryModel:

        history = MedicalHistoryModel(
            patient_id=patient_id,
            diseases=diseases,
            medications=medications,
            allergies=allergies,
            smoking_status=smoking_status,
            alcohol_status=alcohol_status,
            occupational_exposure=occupational_exposure,
            notes=notes,
        )

        try:
            db.add(history)
            db.commit()
            db.refresh(history)

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
            db.refresh(history)

            return history

        except Exception:
            db.rollback()
            raise