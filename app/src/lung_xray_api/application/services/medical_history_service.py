from sqlalchemy.orm import Session

from lung_xray_api.infrastructure.persistence.orm import (
    MedicalHistoryModel,
    PatientProfileModel,
    UserModel,
)
from lung_xray_api.infrastructure.persistence.repositories.medical_history_repository import (
    MedicalHistoryRepository,
)
from lung_xray_api.infrastructure.persistence.repositories.patient_profile_repository import (
    PatientProfileRepository,
)
from lung_xray_api.schemas.medical_history import (
    MedicalHistoryCreate,
    MedicalHistoryUpdate,
)


class MedicalHistoryService:

    def __init__(self) -> None:
        self.history_repository = MedicalHistoryRepository()
        self.patient_repository = PatientProfileRepository()

    def _get_patient_profile(
        self,
        db: Session,
        current_user: UserModel,
    ) -> PatientProfileModel:

        profile = self.patient_repository.get_by_user_id(
            db,
            current_user.id,
        )

        if profile is None:
            raise LookupError(
                "Patient profile not found. "
                "Create a patient profile first."
            )

        return profile

    def create_history(
        self,
        db: Session,
        current_user: UserModel,
        request: MedicalHistoryCreate,
    ) -> MedicalHistoryModel:

        profile = self._get_patient_profile(
            db,
            current_user,
        )

        return self.history_repository.create(
            db,
            patient_id=profile.id,
            diseases=request.diseases,
            medications=request.medications,
            allergies=request.allergies,
            smoking_status=request.smoking_status,
            alcohol_status=request.alcohol_status,
            occupational_exposure=request.occupational_exposure,
            notes=request.notes,
        )

    def list_my_histories(
        self,
        db: Session,
        current_user: UserModel,
    ) -> list[MedicalHistoryModel]:

        profile = self._get_patient_profile(
            db,
            current_user,
        )

        return self.history_repository.list_by_patient_id(
            db,
            profile.id,
        )

    def get_my_history(
        self,
        db: Session,
        current_user: UserModel,
        history_id: int,
    ) -> MedicalHistoryModel:

        profile = self._get_patient_profile(
            db,
            current_user,
        )

        history = (
            self.history_repository.get_by_id_for_patient(
                db,
                history_id=history_id,
                patient_id=profile.id,
            )
        )

        if history is None:
            raise LookupError(
                "Medical history not found."
            )

        return history

    def update_my_history(
        self,
        db: Session,
        current_user: UserModel,
        history_id: int,
        request: MedicalHistoryUpdate,
    ) -> MedicalHistoryModel:

        history = self.get_my_history(
            db,
            current_user,
            history_id,
        )

        changes = request.model_dump(
            exclude_unset=True
        )

        return self.history_repository.update(
            db,
            history,
            changes,
        )


medical_history_service = MedicalHistoryService()