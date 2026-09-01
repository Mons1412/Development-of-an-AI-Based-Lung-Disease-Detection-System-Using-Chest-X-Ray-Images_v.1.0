from uuid import uuid4

from sqlalchemy.orm import Session

from lung_xray_api.infrastructure.persistence.orm import (
    PatientProfileModel,
    UserModel,
)
from lung_xray_api.infrastructure.persistence.repositories.patient_profile_repository import (
    PatientProfileRepository,
)
from lung_xray_api.schemas.patient_profile import (
    PatientProfileCreate,
    PatientProfileUpdate,
)


class PatientProfileService:

    def __init__(self) -> None:
        self.repository = PatientProfileRepository()

    def _generate_patient_code(
        self,
        db: Session,
    ) -> str:

        for _ in range(10):
            code = f"PX{uuid4().hex[:10].upper()}"

            existing = self.repository.get_by_patient_code(
                db,
                code,
            )

            if existing is None:
                return code

        raise RuntimeError(
            "Could not generate a unique patient code."
        )

    def create_profile(
        self,
        db: Session,
        current_user: UserModel,
        request: PatientProfileCreate,
    ) -> PatientProfileModel:

        existing = self.repository.get_by_user_id(
            db,
            current_user.id,
        )

        if existing is not None:
            raise ValueError(
                "Patient profile already exists."
            )

        patient_code = self._generate_patient_code(db)

        return self.repository.create(
            db,
            user_id=current_user.id,
            patient_code=patient_code,
            full_name=request.full_name.strip(),
            birth_year=request.birth_year,
            gender=request.gender,
            phone=request.phone,
            address=request.address,
        )

    def get_my_profile(
        self,
        db: Session,
        current_user: UserModel,
    ) -> PatientProfileModel:

        profile = self.repository.get_by_user_id(
            db,
            current_user.id,
        )

        if profile is None:
            raise LookupError(
                "Patient profile not found."
            )

        return profile

    def update_my_profile(
        self,
        db: Session,
        current_user: UserModel,
        request: PatientProfileUpdate,
    ) -> PatientProfileModel:

        profile = self.repository.get_by_user_id(
            db,
            current_user.id,
        )

        if profile is None:
            raise LookupError(
                "Patient profile not found."
            )

        changes = request.model_dump(
            exclude_unset=True
        )

        if "full_name" in changes:
            if changes["full_name"] is None:
                raise ValueError(
                    "Full name cannot be null."
                )

            changes["full_name"] = (
                changes["full_name"].strip()
            )

        return self.repository.update(
            db,
            profile,
            changes,
        )


patient_profile_service = PatientProfileService()