from sqlalchemy import select
from sqlalchemy.orm import Session

from lung_xray_api.infrastructure.persistence.orm import PatientProfileModel


class PatientProfileRepository:

    def get_by_id(
        self,
        db: Session,
        profile_id: int,
    ) -> PatientProfileModel | None:
        return db.get(PatientProfileModel, profile_id)

    def get_by_user_id(
        self,
        db: Session,
        user_id: int,
    ) -> PatientProfileModel | None:
        statement = select(PatientProfileModel).where(
            PatientProfileModel.user_id == user_id
        )

        return db.scalar(statement)

    def get_by_patient_code(
        self,
        db: Session,
        patient_code: str,
    ) -> PatientProfileModel | None:
        statement = select(PatientProfileModel).where(
            PatientProfileModel.patient_code == patient_code
        )

        return db.scalar(statement)

    def create(
        self,
        db: Session,
        *,
        user_id: int,
        patient_code: str,
        full_name: str,
        birth_year: int | None,
        gender: str | None,
        phone: str | None,
        address: str | None,
    ) -> PatientProfileModel:

        profile = PatientProfileModel(
            user_id=user_id,
            patient_code=patient_code,
            full_name=full_name,
            birth_year=birth_year,
            gender=gender,
            phone=phone,
            address=address,
        )

        try:
            db.add(profile)
            db.commit()
            db.refresh(profile)

            return profile

        except Exception:
            db.rollback()
            raise

    def update(
        self,
        db: Session,
        profile: PatientProfileModel,
        changes: dict,
    ) -> PatientProfileModel:

        for field, value in changes.items():
            setattr(profile, field, value)

        try:
            db.commit()
            db.refresh(profile)

            return profile

        except Exception:
            db.rollback()
            raise