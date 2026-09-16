from dataclasses import dataclass
from datetime import datetime
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

        return DrAIContext(
            patient=DrAIPatientContext(
                birth_year=patient.birth_year,
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
