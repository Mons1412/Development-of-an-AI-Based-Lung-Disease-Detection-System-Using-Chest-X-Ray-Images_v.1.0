from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from lung_xray_api.infrastructure.persistence.orm import UserModel
from lung_xray_api.infrastructure.persistence.orm.analysis_model import (
    AnalysisModel,
)
from lung_xray_api.infrastructure.persistence.orm.medical_history_model import (
    MedicalHistoryModel,
)
from lung_xray_api.infrastructure.persistence.orm.patient_profile_model import (
    PatientProfileModel,
)
from lung_xray_api.infrastructure.persistence.orm.report_model import (
    ReportModel,
)
from lung_xray_api.infrastructure.persistence.repositories.analysis_repository import (
    AnalysisRepository,
)
from lung_xray_api.infrastructure.persistence.repositories.medical_history_repository import (
    MedicalHistoryRepository,
)
from lung_xray_api.infrastructure.persistence.repositories.patient_profile_repository import (
    PatientProfileRepository,
)
from lung_xray_api.infrastructure.persistence.repositories.report_repository import (
    ReportRepository,
)
from lung_xray_api.infrastructure.reporting.reportlab_pdf_generator import (
    ReportLabPdfGenerator,
    ReportPdfData,
    report_pdf_generator,
)


PROJECT_ROOT = Path(
    __file__
).resolve().parents[5]

REPORT_DIRECTORY = (
    PROJECT_ROOT
    / "app"
    / "var"
    / "reports"
)

SUPPORTED_REPORT_LANGUAGES = {
    "vi",
    "en",
}


class ReportService:

    def __init__(
        self,
        *,
        pdf_generator: ReportLabPdfGenerator = report_pdf_generator,
    ) -> None:

        self.analysis_repository = AnalysisRepository()
        self.patient_repository = PatientProfileRepository()
        self.history_repository = MedicalHistoryRepository()
        self.report_repository = ReportRepository()

        self.pdf_generator = pdf_generator

    def _normalize_language(
        self,
        language: str,
    ) -> str:

        normalized_language = (
            language
            .strip()
            .lower()
        )

        if normalized_language not in SUPPORTED_REPORT_LANGUAGES:
            raise ValueError(
                "Report language must be 'vi' or 'en'."
            )

        return normalized_language

    def _generate_report_code(
        self,
        db: Session,
    ) -> str:

        for _ in range(10):
            now = datetime.now(
                timezone.utc
            )

            code = (
                f"RP{now:%Y%m%d}"
                f"{uuid4().hex[:12].upper()}"
            )

            existing = (
                self.report_repository
                .get_by_report_code(
                    db,
                    code,
                )
            )

            if existing is None:
                return code

        raise RuntimeError(
            "Could not generate a unique report code."
        )

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

    def _get_latest_medical_history(
        self,
        db: Session,
        *,
        patient_id: int,
    ) -> MedicalHistoryModel | None:

        histories = (
            self.history_repository
            .list_by_patient_id(
                db,
                patient_id,
            )
        )

        if not histories:
            return None

        return histories[0]

    def _build_pdf_data(
        self,
        *,
        analysis: AnalysisModel,
        patient: PatientProfileModel,
        history: MedicalHistoryModel | None,
        report_code: str,
        language: str,
        generated_at: datetime,
    ) -> ReportPdfData:

        prediction = analysis.prediction

        if prediction is None:
            raise ValueError(
                "Completed analysis has no prediction."
            )

        if analysis.ai_model is None:
            raise ValueError(
                "Analysis model information is unavailable."
            )

        probabilities = {
            row.class_name: float(
                row.probability
            )
            for row in prediction.probabilities
        }

        xray_image_path = None

        stored_image_path = getattr(
            analysis,
            "stored_image_path",
            None,
        )

        if stored_image_path:
            candidate = Path(
                stored_image_path
            )

            if not candidate.is_absolute():
                candidate = (
                    PROJECT_ROOT
                    / candidate
                )

            candidate = (
                candidate.resolve()
            )

            if (
                candidate.is_file()
                and candidate.suffix.lower()
                in {
                    ".jpg",
                    ".jpeg",
                    ".png",
                }
            ):
                xray_image_path = str(
                    candidate
                )


        return ReportPdfData(
            report_code=report_code,
            language=language,
            generated_at=generated_at,

            patient_code=patient.patient_code,
            full_name=patient.full_name,
            birth_year=patient.birth_year,
            date_of_birth=getattr(
                patient,
                "date_of_birth",
                None,
            ),
            gender=patient.gender,
            phone=patient.phone,
            address=patient.address,

            analysis_code=analysis.analysis_code,
            original_filename=analysis.original_filename,
            input_source=analysis.input_source,
            model_key=analysis.ai_model.model_key,
            model_display_name=analysis.ai_model.display_name,
            model_version=analysis.ai_model.version,
            analysis_created_at=analysis.created_at,
            xray_image_path=xray_image_path,

            predicted_class=prediction.predicted_class,
            confidence=float(
                prediction.confidence
            ),
            probabilities=probabilities,

            diseases=(
                history.diseases
                if history is not None
                else None
            ),
            medications=(
                history.medications
                if history is not None
                else None
            ),
            allergies=(
                history.allergies
                if history is not None
                else None
            ),
            smoking_status=(
                history.smoking_status
                if history is not None
                else None
            ),
            alcohol_status=(
                history.alcohol_status
                if history is not None
                else None
            ),
            occupational_exposure=(
                history.occupational_exposure
                if history is not None
                else None
            ),
            notes=(
                history.notes
                if history is not None
                else None
            ),

            current_complaint_hpi=(
                getattr(
                    history,
                    "current_complaint_hpi",
                    None,
                )
                if history is not None
                else None
            ),
            allergy_history=(
                getattr(
                    history,
                    "allergy_history",
                    None,
                )
                if history is not None
                else None
            ),
            diet=(
                getattr(
                    history,
                    "diet",
                    None,
                )
                if history is not None
                else None
            ),
            appetite=(
                getattr(
                    history,
                    "appetite",
                    None,
                )
                if history is not None
                else None
            ),
            sleep=(
                getattr(
                    history,
                    "sleep",
                    None,
                )
                if history is not None
                else None
            ),
            exercise=(
                getattr(
                    history,
                    "exercise",
                    None,
                )
                if history is not None
                else None
            ),
            habits=(
                getattr(
                    history,
                    "habits",
                    None,
                )
                if history is not None
                else None
            ),
        )

    def generate_report(
        self,
        db: Session,
        current_user: UserModel,
        *,
        analysis_id: int,
        language: str,
    ) -> ReportModel:

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
                "Only completed analyses can be exported."
            )

        if analysis.prediction is None:
            raise ValueError(
                "Completed analysis has no prediction."
            )

        history = (
            self._get_latest_medical_history(
                db,
                patient_id=patient.id,
            )
        )

        report_code = (
            self._generate_report_code(
                db
            )
        )

        generated_at = datetime.now(
            timezone.utc
        ).replace(
            tzinfo=None
        )

        pdf_data = self._build_pdf_data(
            analysis=analysis,
            patient=patient,
            history=history,            report_code=report_code,
            language=normalized_language,
            generated_at=generated_at,
        )

        REPORT_DIRECTORY.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path = (
            REPORT_DIRECTORY
            / f"{report_code}.pdf"
        )

        try:
            self.pdf_generator.generate(
                output_path=output_path,
                data=pdf_data,
            )

            relative_file_path = (
                output_path
                .relative_to(
                    PROJECT_ROOT
                )
                .as_posix()
            )

            return (
                self.report_repository
                .create(
                    db,
                    analysis_id=analysis.id,
                    report_code=report_code,
                    language=normalized_language,
                    file_path=relative_file_path,
                )
            )

        except Exception:
            if output_path.is_file():
                output_path.unlink()

            raise

    def get_report(
        self,
        db: Session,
        current_user: UserModel,
        *,
        report_id: int,
    ) -> ReportModel:

        report = (
            self.report_repository
            .get_by_id(
                db,
                report_id,
            )
        )

        if report is None:
            raise LookupError(
                "Report not found."
            )

        role = (
            str(current_user.role)
            .strip()
            .upper()
        )

        if role == "ADMIN":
            return report

        if role != "USER":
            raise PermissionError(
                "Unsupported user role."
            )

        analysis = report.analysis

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
                "Report not found."
            )

        return report

    def resolve_report_file(
        self,
        db: Session,
        current_user: UserModel,
        *,
        report_id: int,
    ) -> tuple[
        ReportModel,
        Path,
    ]:

        report = self.get_report(
            db,
            current_user,
            report_id=report_id,
        )

        report_root = (
            REPORT_DIRECTORY
            .resolve()
        )

        file_path = (
            PROJECT_ROOT
            / report.file_path
        ).resolve()

        if not file_path.is_relative_to(
            report_root
        ):
            raise RuntimeError(
                "Report file path is outside report storage."
            )

        if not file_path.is_file():
            raise FileNotFoundError(
                "Report file not found."
            )

        return (
            report,
            file_path,
        )


report_service = ReportService()
