from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class MedicalHistoryIntakeCreate(
    BaseModel
):
    current_complaint_hpi: str | None = Field(
        default=None,
        max_length=5000,
    )

    past_medical_history: str | None = Field(
        default=None,
        max_length=5000,
    )

    past_medication_history: str | None = Field(
        default=None,
        max_length=5000,
    )

    allergy_history: str | None = Field(
        default=None,
        max_length=5000,
    )

    diseases: list[str] | None = Field(
        default=None,
        max_length=50,
    )

    smoking_status: str | None = Field(
        default=None,
        max_length=30,
    )

    alcohol_status: str | None = Field(
        default=None,
        max_length=30,
    )

    occupational_exposure: str | None = Field(
        default=None,
        max_length=5000,
    )

    diet: str | None = Field(
        default=None,
        max_length=5000,
    )

    appetite: str | None = Field(
        default=None,
        max_length=5000,
    )

    sleep: str | None = Field(
        default=None,
        max_length=5000,
    )

    exercise: str | None = Field(
        default=None,
        max_length=5000,
    )

    bowel_bladder: str | None = Field(
        default=None,
        max_length=5000,
    )

    habits: str | None = Field(
        default=None,
        max_length=5000,
    )

    family_history: str | None = Field(
        default=None,
        max_length=5000,
    )


class MedicalHistoryIntakeResponse(
    BaseModel
):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int

    recorded_at: datetime

    current_complaint_hpi: str | None

    past_medical_history: str | None

    past_medication_history: str | None

    allergy_history: str | None

    diseases: list[str] | None

    smoking_status: str | None

    alcohol_status: str | None

    occupational_exposure: str | None

    diet: str | None

    appetite: str | None

    sleep: str | None

    exercise: str | None

    bowel_bladder: str | None

    habits: str | None

    family_history: str | None


class MedicalHistoryIntakePage(
    BaseModel
):
    items: list[
        MedicalHistoryIntakeResponse
    ]

    limit: int

    offset: int

    has_more: bool
