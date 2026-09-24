from pathlib import Path

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from lung_xray_api.infrastructure.persistence.repositories.admin_patient_repository import AdminPatientRepository
from lung_xray_api.infrastructure.persistence.repositories.analysis_repository import AnalysisRepository
from lung_xray_api.infrastructure.persistence.repositories.report_repository import ReportRepository
from lung_xray_api.infrastructure.persistence.repositories.medical_history_repository import MedicalHistoryRepository
from lung_xray_api.schemas.admin_patient import (
    AdminPatientAnalysisResponse,
    AdminPatientDetailResponse,
    AdminPatientMedicalHistoryResponse,
    AdminPatientPage,
    AdminPatientProfileDetail,
    AdminPatientResponse,
    AdminPatientUpdate,
)


class PatientConflictError(Exception):
    pass


class AdminPatientService:
    def __init__(self):
        self.repository = AdminPatientRepository()
        self.analysis_repository = AnalysisRepository()
        self.report_repository = ReportRepository()
        self.history_repository = MedicalHistoryRepository()

    @staticmethod
    def response(user, profile):
        return AdminPatientResponse(
            user_id=user.id, patient_code=profile.patient_code, username=user.username,
            full_name=profile.full_name, phone=user.phone or profile.phone,
            email=user.email, address=profile.address, date_of_birth=profile.date_of_birth,
            sex=profile.gender, is_active=user.is_active,
        )

    def search(self, db: Session, *, query: str, page: int, limit: int):
        rows, total = self.repository.search(db, query=query.strip(), page=page, limit=limit)
        return AdminPatientPage(items=[self.response(*row) for row in rows],
                                total=total, page=page, limit=limit)


    def detail(
        self,
        db: Session,
        user_id: int,
    ) -> AdminPatientDetailResponse:

        row = self.repository.get(
            db,
            user_id,
        )

        if row is None:
            raise LookupError(
                "Patient USER account not found."
            )

        user, profile = row

        analyses = (
            self.analysis_repository
            .list_by_patient_id(
                db,
                profile.id,
            )
        )

        histories = (
            self.history_repository
            .list_by_patient_id(
                db,
                profile.id,
            )
        )

        profile_response = (
            AdminPatientProfileDetail(
                user_id=user.id,
                patient_id=profile.id,
                patient_code=profile.patient_code,
                username=user.username,
                full_name=profile.full_name,
                phone=(
                    user.phone
                    or profile.phone
                ),
                email=user.email,
                address=profile.address,
                date_of_birth=getattr(
                    profile,
                    "date_of_birth",
                    None,
                ),
                birth_year=getattr(
                    profile,
                    "birth_year",
                    None,
                ),
                sex=getattr(
                    profile,
                    "gender",
                    None,
                ),
                height_cm=(
                    float(profile.height_cm)
                    if getattr(
                        profile,
                        "height_cm",
                        None,
                    )
                    is not None
                    else None
                ),
                weight_kg=(
                    float(profile.weight_kg)
                    if getattr(
                        profile,
                        "weight_kg",
                        None,
                    )
                    is not None
                    else None
                ),
                is_active=user.is_active,
            )
        )


        medical_history = []

        for item in histories:
            medical_history.append(
                AdminPatientMedicalHistoryResponse(
                    id=item.id,
                    recorded_at=item.recorded_at,

                    current_complaint_hpi=(
                        item.current_complaint_hpi
                    ),
                    past_medical_history=(
                        item.past_medical_history
                    ),
                    past_medication_history=(
                        item.past_medication_history
                    ),
                    allergy_history=(
                        item.allergy_history
                    ),

                    diet=item.diet,
                    appetite=item.appetite,
                    sleep=item.sleep,
                    exercise=item.exercise,
                    bowel_bladder=(
                        item.bowel_bladder
                    ),
                    habits=item.habits,
                    family_history=(
                        item.family_history
                    ),

                    diseases=item.diseases,
                    medications=item.medications,
                    allergies=item.allergies,

                    smoking_status=(
                        item.smoking_status
                    ),
                    alcohol_status=(
                        item.alcohol_status
                    ),
                    occupational_exposure=(
                        item.occupational_exposure
                    ),
                    notes=item.notes,

                    created_at=item.created_at,
                    updated_at=item.updated_at,
                )
            )

        history = []

        for analysis in analyses:

            model = analysis.ai_model
            prediction = analysis.prediction

            reports = (
                self.report_repository
                .list_by_analysis_id(
                    db,
                    analysis.id,
                )
            )

            latest_report = (
                reports[0]
                if reports
                else None
            )

            history.append(
                AdminPatientAnalysisResponse(
                    analysis_id=analysis.id,
                    analysis_code=(
                        analysis.analysis_code
                    ),
                    status=analysis.status,
                    input_source=(
                        analysis.input_source
                    ),
                    original_filename=(
                        analysis.original_filename
                    ),
                    model_key=(
                        model.model_key
                        if model is not None
                        else None
                    ),
                    model_name=(
                        model.display_name
                        if model is not None
                        else None
                    ),
                    model_version=(
                        model.version
                        if model is not None
                        else None
                    ),
                    predicted_class=(
                        prediction.predicted_class
                        if prediction is not None
                        else None
                    ),
                    confidence=(
                        float(
                            prediction.confidence
                        )
                        if prediction is not None
                        else None
                    ),

                    has_image=bool(
                        getattr(
                            analysis,
                            "stored_image_path",
                            None,
                        )
                    ),

                    report_id=(
                        latest_report.id
                        if latest_report is not None
                        else None
                    ),
                    report_code=(
                        latest_report.report_code
                        if latest_report is not None
                        else None
                    ),
                    report_language=(
                        latest_report.language
                        if latest_report is not None
                        else None
                    ),
                    report_created_at=(
                        latest_report.created_at
                        if latest_report is not None
                        else None
                    ),

                    created_at=(
                        analysis.created_at
                    ),
                    completed_at=(
                        analysis.completed_at
                    ),
                )
            )

        return AdminPatientDetailResponse(
            patient_profile=profile_response,
            medical_history=medical_history,
            analysis_history=history,
        )


    def resolve_analysis_image(
        self,
        db: Session,
        *,
        user_id: int,
        analysis_id: int,
    ) -> Path:

        row = self.repository.get(
            db,
            user_id,
        )

        if row is None:
            raise LookupError(
                "Patient USER account not found."
            )

        _, profile = row

        analysis = (
            self.analysis_repository
            .get_by_id_for_patient(
                db,
                analysis_id=analysis_id,
                patient_id=profile.id,
            )
        )

        if analysis is None:
            raise LookupError(
                "Analysis not found for this patient."
            )

        stored_path = getattr(
            analysis,
            "stored_image_path",
            None,
        )

        if not stored_path:
            raise FileNotFoundError(
                "Analysis image not found."
            )

        file_path = Path(
            stored_path
        )

        if not file_path.is_absolute():
            file_path = (
                Path.cwd()
                / file_path
            )

        file_path = file_path.resolve()

        if (
            not file_path.is_file()
            or file_path.suffix.lower()
            not in {
                ".jpg",
                ".jpeg",
                ".png",
            }
        ):
            raise FileNotFoundError(
                "Analysis image not found."
            )

        return file_path

    def update(
        self,
        db: Session,
        user_id: int,
        payload: AdminPatientUpdate,
    ):
        row = self.repository.get(
            db,
            user_id,
        )

        if row is None:
            raise LookupError(
                "Patient USER account not found."
            )

        user, profile = row

        latest_history = None

        if (
            payload.latest_medical_history
            is not None
        ):
            histories = (
                self.history_repository
                .list_by_patient_id(
                    db,
                    profile.id,
                )
            )

            if not histories:
                raise LookupError(
                    "Latest medical history not found."
                )

            latest_history = histories[0]

            if (
                latest_history.id
                != payload.latest_medical_history.id
            ):
                raise PatientConflictError(
                    "Latest medical history has changed. "
                    "Reopen Edit before saving."
                )

            medical_changes = (
                payload.latest_medical_history
                .model_dump(
                    exclude={"id"},
                )
            )

            for (
                field_name,
                value,
            ) in medical_changes.items():
                setattr(
                    latest_history,
                    field_name,
                    value,
                )

        user.phone = payload.phone
        profile.phone = payload.phone

        user.email = str(
            payload.email
        ).lower()

        user.is_active = (
            payload.is_active
        )

        profile.full_name = (
            payload.full_name
        )

        profile.address = (
            payload.address
            or None
        )

        profile.date_of_birth = (
            payload.date_of_birth
        )

        profile.birth_year = (
            payload.date_of_birth.year
            if payload.date_of_birth
            else None
        )

        profile.gender = payload.sex

        try:
            db.commit()

        except IntegrityError as exc:
            db.rollback()

            raise PatientConflictError(
                "Phone or email is already used "
                "by another account."
            ) from exc

        except Exception:
            db.rollback()
            raise

        db.refresh(user)
        db.refresh(profile)

        if latest_history is not None:
            db.refresh(
                latest_history
            )

        return self.response(
            user,
            profile,
        )

    def delete(self, db: Session, user_id: int):
        row = self.repository.get(db, user_id)
        if row is None:
            raise LookupError("Patient USER account not found.")
        db.delete(row[0])
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise PatientConflictError("Patient could not be deleted because linked records prevent deletion.") from exc


admin_patient_service = AdminPatientService()
