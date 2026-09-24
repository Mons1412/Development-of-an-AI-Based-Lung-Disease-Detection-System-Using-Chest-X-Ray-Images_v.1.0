from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class MedicalHistoryCreate(BaseModel):
    current_complaint_hpi: str = Field(
        min_length=1,
        max_length=5000,
    )

    past_medical_history: str = Field(
        min_length=1,
        max_length=5000,
    )

    past_medication_history: str = Field(
        min_length=1,
        max_length=5000,
    )

    allergy_history: str = Field(
        min_length=1,
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

    diet: str = Field(
        min_length=1,
        max_length=2000,
    )

    appetite: str = Field(
        min_length=1,
        max_length=2000,
    )

    sleep: str = Field(
        min_length=1,
        max_length=2000,
    )

    exercise: str = Field(
        min_length=1,
        max_length=2000,
    )

    bowel_bladder: str = Field(
        min_length=1,
        max_length=2000,
    )

    habits: str = Field(
        min_length=1,
        max_length=3000,
    )

    family_history: str = Field(
        min_length=1,
        max_length=5000,
    )


class MedicalHistoryUpdate(BaseModel):
    current_complaint_hpi: str | None = Field(
        default=None,
        min_length=1,
        max_length=5000,
    )

    past_medical_history: str | None = Field(
        default=None,
        min_length=1,
        max_length=5000,
    )

    past_medication_history: str | None = Field(
        default=None,
        min_length=1,
        max_length=5000,
    )

    allergy_history: str | None = Field(
        default=None,
        min_length=1,
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
        min_length=1,
        max_length=2000,
    )

    appetite: str | None = Field(
        default=None,
        min_length=1,
        max_length=2000,
    )

    sleep: str | None = Field(
        default=None,
        min_length=1,
        max_length=2000,
    )

    exercise: str | None = Field(
        default=None,
        min_length=1,
        max_length=2000,
    )

    bowel_bladder: str | None = Field(
        default=None,
        min_length=1,
        max_length=2000,
    )

    habits: str | None = Field(
        default=None,
        min_length=1,
        max_length=3000,
    )

    family_history: str | None = Field(
        default=None,
        min_length=1,
        max_length=5000,
    )


class MedicalHistoryResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    patient_id: int
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

    created_at: datetime
    updated_at: datetime
