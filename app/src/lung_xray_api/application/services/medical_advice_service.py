from sqlalchemy.orm import Session

from lung_xray_api.application.services.drai_context_builder import (
    DrAIContextBuilder,
    drai_context_builder,
)
from lung_xray_api.application.services.medical_advice_provider import (
    MedicalAdviceProvider,
)
from lung_xray_api.core.config import settings
from lung_xray_api.infrastructure.ml.gemini_medical_advice_provider import (
    GeminiMedicalAdviceProvider,
)
from lung_xray_api.infrastructure.persistence.orm import (
    AnalysisModel,
    MedicalAdviceModel,
    PatientProfileModel,
    UserModel,
)
from lung_xray_api.infrastructure.persistence.repositories.analysis_repository import (
    AnalysisRepository,
)
from lung_xray_api.infrastructure.persistence.repositories.medical_advice_repository import (
    MedicalAdviceRepository,
)
from lung_xray_api.infrastructure.persistence.repositories.patient_profile_repository import (
    PatientProfileRepository,
)


SUPPORTED_MEDICAL_ADVICE_LANGUAGES = {
    "vi",
    "en",
}


class MedicalAdviceService:

    def __init__(
        self,
        *,
        analysis_repository: (
            AnalysisRepository | None
        ) = None,
        patient_repository: (
            PatientProfileRepository | None
        ) = None,
        advice_repository: (
            MedicalAdviceRepository | None
        ) = None,
        context_builder: (
            DrAIContextBuilder | None
        ) = None,
        provider: (
            MedicalAdviceProvider | None
        ) = None,
    ) -> None:

        self.analysis_repository = (
            analysis_repository
            if analysis_repository is not None
            else AnalysisRepository()
        )

        self.patient_repository = (
            patient_repository
            if patient_repository is not None
            else PatientProfileRepository()
        )

        self.advice_repository = (
            advice_repository
            if advice_repository is not None
            else MedicalAdviceRepository()
        )

        self.context_builder = (
            context_builder
            if context_builder is not None
            else drai_context_builder
        )

        self.provider = (
            provider
            if provider is not None
            else GeminiMedicalAdviceProvider(
                api_key=settings.gemini_api_key,
                model_name=settings.gemini_model,
            )
        )

    @staticmethod
    def _normalize_language(
        language: str,
    ) -> str:

        normalized = (
            language
            .strip()
            .lower()
        )

        if (
            normalized
            not in
            SUPPORTED_MEDICAL_ADVICE_LANGUAGES
        ):
            raise ValueError(
                "Medical advice language "
                "must be 'vi' or 'en'."
            )

        return normalized

    def _load_analysis_for_user(
        self,
        db: Session,
        current_user: UserModel,
        *,
        analysis_id: int,
    ) -> tuple[
        AnalysisModel,
        PatientProfileModel,
    ]:

        role = (
            str(current_user.role)
            .strip()
            .upper()
        )

        if role == "ADMIN":
            analysis = (
                self.analysis_repository
                .get_by_id(
                    db,
                    analysis_id,
                )
            )

            if (
                analysis is None
                or analysis.patient is None
            ):
                raise LookupError(
                    "Analysis not found."
                )

            return (
                analysis,
                analysis.patient,
            )

        if role != "USER":
            raise PermissionError(
                "Unsupported user role."
            )

        patient = (
            self.patient_repository
            .get_by_user_id(
                db,
                current_user.id,
            )
        )

        if patient is None:
            raise LookupError(
                "Analysis not found."
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

        return (
            analysis,
            patient,
        )

    def generate_advice(
        self,
        db: Session,
        current_user: UserModel,
        *,
        analysis_id: int,
        language: str,
    ) -> MedicalAdviceModel:

        normalized_language = (
            self._normalize_language(
                language
            )
        )

        (
            analysis,
            patient,
        ) = self._load_analysis_for_user(
            db,
            current_user,
            analysis_id=analysis_id,
        )

        if analysis.status != "COMPLETED":
            raise ValueError(
                "Only completed analyses "
                "can generate medical advice."
            )

        if analysis.prediction is None:
            raise ValueError(
                "Completed analysis has "
                "no prediction."
            )

        context = self.context_builder.build(
            db,
            analysis=analysis,
            patient=patient,
        )

        result = self.provider.generate(
            context=context,
            language=normalized_language,
        )

        return self.advice_repository.create(
            db,
            analysis_id=analysis.id,
            language=normalized_language,
            provider=result.provider,
            model_name=result.model_name,
            advice_text=result.advice_text,
        )

    def get_advice(
        self,
        db: Session,
        current_user: UserModel,
        *,
        advice_id: int,
    ) -> MedicalAdviceModel:

        advice = (
            self.advice_repository
            .get_by_id(
                db,
                advice_id,
            )
        )

        if advice is None:
            raise LookupError(
                "Medical advice not found."
            )

        role = (
            str(current_user.role)
            .strip()
            .upper()
        )

        if role == "ADMIN":
            return advice

        if role != "USER":
            raise PermissionError(
                "Unsupported user role."
            )

        analysis = advice.analysis

        patient = (
            analysis.patient
            if analysis is not None
            else None
        )

        if (
            patient is None
            or patient.user_id
            != current_user.id
        ):
            raise LookupError(
                "Medical advice not found."
            )

        return advice

    def list_analysis_advices(
        self,
        db: Session,
        current_user: UserModel,
        *,
        analysis_id: int,
    ) -> list[MedicalAdviceModel]:

        self._load_analysis_for_user(
            db,
            current_user,
            analysis_id=analysis_id,
        )

        return (
            self.advice_repository
            .list_by_analysis_id(
                db,
                analysis_id,
            )
        )


medical_advice_service = MedicalAdviceService()
