from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from lung_xray_api.application.services.ai_model_service import (
    ai_model_service,
)
from lung_xray_api.infrastructure.imaging.image_validator import (
    image_validator,
)
from lung_xray_api.infrastructure.ml.image_preprocessor import (
    image_preprocessor,
)
from lung_xray_api.infrastructure.ml.runtime_manager import (
    runtime_manager,
)
from lung_xray_api.infrastructure.persistence.orm import (
    AnalysisModel,
    PatientProfileModel,
    UserModel,
)
from lung_xray_api.infrastructure.persistence.repositories.analysis_repository import (
    AnalysisRepository,
)
from lung_xray_api.infrastructure.persistence.repositories.patient_profile_repository import (
    PatientProfileRepository,
)
from lung_xray_api.infrastructure.persistence.repositories.prediction_repository import (
    PredictionRepository,
)
from lung_xray_api.infrastructure.storage.image_storage import (
    image_storage,
)


class AnalysisService:

    def __init__(self) -> None:
        self.analysis_repository = (
            AnalysisRepository()
        )

        self.patient_repository = (
            PatientProfileRepository()
        )

        self.prediction_repository = (
            PredictionRepository()
        )

    def _get_patient(
        self,
        db: Session,
        current_user: UserModel,
    ) -> PatientProfileModel:

        profile = (
            self.patient_repository
            .get_by_user_id(
                db,
                current_user.id,
            )
        )

        if profile is None:
            raise LookupError(
                "Patient profile not found. "
                "Create a patient profile first."
            )

        return profile

    def _select_model(
        self,
        db: Session,
        model_id: int | None,
    ):

        if model_id is None:
            return (
                ai_model_service
                .get_default_model(db)
            )

        return (
            ai_model_service
            .get_available_model(
                db,
                model_id,
            )
        )

    def _generate_analysis_code(
        self,
    ) -> str:

        timestamp = datetime.now(
            timezone.utc
        ).strftime(
            "%Y%m%d%H%M%S"
        )

        random_part = (
            uuid4().hex[:10].upper()
        )

        return (
            f"AN{timestamp}{random_part}"
        )

    def _to_response(
        self,
        analysis: AnalysisModel,
        patient_code: str,
    ) -> dict:

        prediction = (
            analysis.prediction
        )

        if prediction is None:
            predicted_class = None
            confidence = None
            probabilities = None

        else:
            predicted_class = (
                prediction.predicted_class
            )

            confidence = float(
                prediction.confidence
            )

            probabilities = {
                row.class_name:
                    float(row.probability)
                for row
                in prediction.probabilities
            }

        return {
            "id": analysis.id,
            "analysis_code":
                analysis.analysis_code,
            "patient_code":
                patient_code,
            "model_id":
                analysis.ai_model.id,
            "model_key":
                analysis.ai_model.model_key,
            "model_version":
                analysis.ai_model.version,
            "input_source":
                analysis.input_source,
            "original_filename":
                analysis.original_filename,
            "status":
                analysis.status,
            "predicted_class":
                predicted_class,
            "confidence":
                confidence,
            "probabilities":
                probabilities,
            "created_at":
                analysis.created_at,
            "completed_at":
                analysis.completed_at,
        }

    def analyze_image(
        self,
        db: Session,
        current_user: UserModel,
        *,
        image_bytes: bytes,
        original_filename: str,
        content_type: str | None,
        model_id: int | None,
    ) -> dict:

        patient = self._get_patient(
            db,
            current_user,
        )

        model_record = (
            self._select_model(
                db,
                model_id,
            )
        )

        validated = (
            image_validator.validate(
                image_bytes,
                content_type,
            )
        )

        stored_image_path = (
            image_storage.save(
                image_bytes,
                validated.extension,
            )
        )

        analysis_code = (
            self._generate_analysis_code()
        )

        try:
            analysis = (
                self.analysis_repository
                .create_pending(
                    db,
                    analysis_code=(
                        analysis_code
                    ),
                    patient_id=patient.id,
                    model_id=(
                        model_record.id
                    ),
                    input_source="UPLOAD",
                    original_filename=(
                        original_filename
                    ),
                    stored_image_path=(
                        stored_image_path
                    ),
                )
            )

        except Exception:
            image_storage.delete(
                stored_image_path
            )
            raise

        try:
            batch = (
                image_preprocessor
                .preprocess(
                    image_bytes
                )
            )

            runtime = (
                runtime_manager
                .get_runtime(
                    model_record
                )
            )

            runtime_prediction = (
                runtime.predict(
                    batch
                )
            )

            self.prediction_repository.stage_prediction(
                db,
                analysis_id=analysis.id,
                predicted_class=(
                    runtime_prediction
                    .predicted_class
                ),
                confidence=(
                    runtime_prediction
                    .confidence
                ),
                probabilities=(
                    runtime_prediction
                    .probabilities
                ),
            )

            self.analysis_repository.mark_completed(
                db,
                analysis,
            )

        except Exception as exc:
            db.rollback()

            self.analysis_repository.mark_failed(
                db,
                analysis.id,
                str(exc),
            )

            raise RuntimeError(
                "AI analysis failed."
            ) from exc

        completed_analysis = (
            self.analysis_repository
            .get_by_id_for_patient(
                db,
                analysis_id=analysis.id,
                patient_id=patient.id,
            )
        )

        if completed_analysis is None:
            raise RuntimeError(
                "Completed analysis could not "
                "be loaded."
            )

        return self._to_response(
            completed_analysis,
            patient.patient_code,
        )

    def list_my_analyses(
        self,
        db: Session,
        current_user: UserModel,
    ) -> list[dict]:

        patient = self._get_patient(
            db,
            current_user,
        )

        analyses = (
            self.analysis_repository
            .list_by_patient_id(
                db,
                patient.id,
            )
        )

        return [
            self._to_response(
                analysis,
                patient.patient_code,
            )
            for analysis in analyses
        ]

    def get_my_analysis(
        self,
        db: Session,
        current_user: UserModel,
        analysis_id: int,
    ) -> dict:

        patient = self._get_patient(
            db,
            current_user,
        )

        analysis = (
            self.analysis_repository
            .get_by_id_for_patient(
                db,
                analysis_id=analysis_id,
                patient_id=patient.id,
            )
        )

        if analysis is None:
            raise LookupError(
                "Analysis not found."
            )

        return self._to_response(
            analysis,
            patient.patient_code,
        )


analysis_service = AnalysisService()