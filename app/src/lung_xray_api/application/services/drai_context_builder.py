from dataclasses import dataclass
from datetime import date, datetime
from uuid import uuid4
from decimal import Decimal

from sqlalchemy.orm import Session

from lung_xray_api.infrastructure.persistence.orm import (
    AnalysisModel,
    PatientProfileModel,
)
from lung_xray_api.infrastructure.persistence.repositories.medical_history_repository import (
    MedicalHistoryRepository,
)


MAX_MEDICAL_HISTORY_RECORDS = 10


@dataclass(
    frozen=True,
    slots=True,
)
class DrAIPatientContext:
    birth_year: int | None
    gender: str | None
    age: int | None = None
    height_cm: float | None = None
    weight_kg: float | None = None


@dataclass(
    frozen=True,
    slots=True,
)
class DrAIMedicalHistoryContext:
    recorded_at: datetime
    diseases: tuple[str, ...]
    medications: tuple[str, ...]
    allergies: tuple[str, ...]
    smoking_status: str | None
    alcohol_status: str | None
    occupational_exposure: str | None
    notes: str | None
    current_complaint_hpi: str | None = None
    past_medical_history: str | None = None
    past_medication_history: str | None = None
    allergy_history: str | None = None
    diet: str | None = None
    appetite: str | None = None
    sleep: str | None = None
    exercise: str | None = None
    bowel_bladder: str | None = None
    habits: str | None = None
    family_history: str | None = None


@dataclass(
    frozen=True,
    slots=True,
)
class DrAIModelContext:
    model_key: str
    display_name: str
    architecture: str
    version: str


@dataclass(
    frozen=True,
    slots=True,
)
class DrAIProbabilityContext:
    class_name: str
    probability: float


@dataclass(
    frozen=True,
    slots=True,
)
class DrAIPredictionContext:
    predicted_class: str
    confidence: float
    probabilities: tuple[
        DrAIProbabilityContext,
        ...,
    ]


@dataclass(frozen=True, slots=True)
class DrAIReportMetadata:
    full_name: str | None = None
    phone: str | None = None
    patient_code: str | None = None
    analysis_code: str | None = None
    original_filename: str | None = None
    input_source: str | None = None
    analyzed_at: datetime | None = None
    report_code: str | None = None
    generated_on: date | None = None


@dataclass(
    frozen=True,
    slots=True,
)
class DrAIContext:
    patient: DrAIPatientContext
    medical_histories: tuple[
        DrAIMedicalHistoryContext,
        ...,
    ]
    model: DrAIModelContext
    prediction: DrAIPredictionContext
    report_metadata: DrAIReportMetadata | None = None


class DrAIContextBuilder:

    def __init__(
        self,
        history_repository: (
            MedicalHistoryRepository | None
        ) = None,
        *,
        max_history_records: int = (
            MAX_MEDICAL_HISTORY_RECORDS
        ),
    ) -> None:

        if max_history_records <= 0:
            raise ValueError(
                "max_history_records must be positive."
            )

        self.history_repository = (
            history_repository
            or MedicalHistoryRepository()
        )

        self.max_history_records = (
            max_history_records
        )

    @staticmethod
    def _clean_text(
        value: object | None,
    ) -> str | None:

        if value is None:
            return None

        text = str(value).strip()

        return text or None

    @classmethod
    def _normalize_list(
        cls,
        values: list | None,
    ) -> tuple[str, ...]:

        if not values:
            return ()

        normalized: list[str] = []

        for value in values:
            text = cls._clean_text(value)

            if text is not None:
                normalized.append(text)

        return tuple(normalized)

    @staticmethod
    def _to_float(
        value: Decimal | float | int,
    ) -> float:

        return float(value)

    def build(
        self,
        db: Session,
        *,
        analysis: AnalysisModel,
        patient: PatientProfileModel,
    ) -> DrAIContext:

        if analysis.patient_id != patient.id:
            raise ValueError(
                "Analysis does not belong to patient."
            )

        if analysis.status != "COMPLETED":
            raise ValueError(
                "Dr.AI context requires a "
                "completed analysis."
            )

        ai_model = analysis.ai_model

        if ai_model is None:
            raise ValueError(
                "AI model information is missing."
            )

        prediction = analysis.prediction

        if prediction is None:
            raise ValueError(
                "Prediction is missing."
            )

        probability_rows = list(
            prediction.probabilities
        )

        if not probability_rows:
            raise ValueError(
                "Prediction probabilities are missing."
            )

        probability_rows.sort(
            key=lambda item: (
                item.class_name.lower()
            )
        )

        histories = (
            self.history_repository
            .list_by_patient_id(
                db,
                patient.id,
            )
        )

        histories = histories[
            :self.max_history_records
        ]

        history_contexts = tuple(
            DrAIMedicalHistoryContext(
                recorded_at=history.recorded_at,
                current_complaint_hpi=self._clean_text(getattr(history, "current_complaint_hpi", None)),
                past_medical_history=self._clean_text(getattr(history, "past_medical_history", None)),
                past_medication_history=self._clean_text(getattr(history, "past_medication_history", None)),
                allergy_history=self._clean_text(getattr(history, "allergy_history", None)),
                diet=self._clean_text(getattr(history, "diet", None)),
                appetite=self._clean_text(getattr(history, "appetite", None)),
                sleep=self._clean_text(getattr(history, "sleep", None)),
                exercise=self._clean_text(getattr(history, "exercise", None)),
                bowel_bladder=self._clean_text(getattr(history, "bowel_bladder", None)),
                habits=self._clean_text(getattr(history, "habits", None)),
                family_history=self._clean_text(getattr(history, "family_history", None)),

                diseases=self._normalize_list(
                    history.diseases
                ),
                medications=self._normalize_list(
                    history.medications
                ),
                allergies=self._normalize_list(
                    history.allergies
                ),
                smoking_status=self._clean_text(
                    history.smoking_status
                ),
                alcohol_status=self._clean_text(
                    history.alcohol_status
                ),
                occupational_exposure=(
                    self._clean_text(
                        history.occupational_exposure
                    )
                ),
                notes=self._clean_text(
                    history.notes
                ),
            )
            for history in histories
        )

        probabilities = tuple(
            DrAIProbabilityContext(
                class_name=self._clean_text(
                    item.class_name
                )
                or "unknown",
                probability=self._to_float(
                    item.probability
                ),
            )
            for item in probability_rows
        )

        today = date.today()
        birthday = getattr(patient, "date_of_birth", None)
        age = None
        if birthday is not None and birthday <= today:
            age = today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))
        return DrAIContext(
            report_metadata=DrAIReportMetadata(
                full_name=self._clean_text(getattr(patient, "full_name", None)),
                phone=self._clean_text(getattr(patient, "phone", None)),
                patient_code=self._clean_text(getattr(patient, "patient_code", None)),
                analysis_code=self._clean_text(getattr(analysis, "analysis_code", None)),
                original_filename=self._clean_text(getattr(analysis, "original_filename", None)),
                input_source=self._clean_text(getattr(analysis, "input_source", None)),
                analyzed_at=getattr(analysis, "created_at", None),
                report_code="DA" + uuid4().hex[:16].upper(), generated_on=today,
            ),
            patient=DrAIPatientContext(
                birth_year=birthday.year if birthday else patient.birth_year,
                age=age,
                height_cm=float(patient.height_cm) if getattr(patient, "height_cm", None) is not None else None,
                weight_kg=float(patient.weight_kg) if getattr(patient, "weight_kg", None) is not None else None,
                gender=self._clean_text(
                    patient.gender
                ),
            ),
            medical_histories=(
                history_contexts
            ),
            model=DrAIModelContext(
                model_key=ai_model.model_key,
                display_name=(
                    ai_model.display_name
                ),
                architecture=(
                    ai_model.architecture
                ),
                version=ai_model.version,
            ),
            prediction=DrAIPredictionContext(
                predicted_class=(
                    prediction.predicted_class
                ),
                confidence=self._to_float(
                    prediction.confidence
                ),
                probabilities=probabilities,
            ),
        )


drai_context_builder = DrAIContextBuilder()
