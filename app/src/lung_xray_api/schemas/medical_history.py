from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MedicalHistoryCreate(BaseModel):
    diseases: list[str] | None = Field(
        default=None,
        max_length=50,
    )

    medications: list[str] | None = Field(
        default=None,
        max_length=50,
    )

    allergies: list[str] | None = Field(
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
        max_length=2000,
    )

    notes: str | None = Field(
        default=None,
        max_length=5000,
    )


class MedicalHistoryUpdate(BaseModel):
    diseases: list[str] | None = Field(
        default=None,
        max_length=50,
    )

    medications: list[str] | None = Field(
        default=None,
        max_length=50,
    )

    allergies: list[str] | None = Field(
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
        max_length=2000,
    )

    notes: str | None = Field(
        default=None,
        max_length=5000,
    )


class MedicalHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int

    recorded_at: datetime

    diseases: list[str] | None
    medications: list[str] | None
    allergies: list[str] | None

    smoking_status: str | None
    alcohol_status: str | None
    occupational_exposure: str | None
    notes: str | None

    created_at: datetime
    updated_at: datetime