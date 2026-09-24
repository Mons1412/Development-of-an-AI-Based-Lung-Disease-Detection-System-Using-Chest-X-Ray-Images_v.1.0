from datetime import date, datetime
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator



class AdminLatestMedicalHistoryUpdate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    id: int = Field(gt=0)

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

    diet: str | None = Field(
        default=None,
        max_length=2000,
    )
    appetite: str | None = Field(
        default=None,
        max_length=2000,
    )
    sleep: str | None = Field(
        default=None,
        max_length=2000,
    )
    exercise: str | None = Field(
        default=None,
        max_length=2000,
    )
    bowel_bladder: str | None = Field(
        default=None,
        max_length=2000,
    )
    habits: str | None = Field(
        default=None,
        max_length=3000,
    )
    family_history: str | None = Field(
        default=None,
        max_length=5000,
    )

    diseases: list[str] | None = None
    medications: list[str] | None = None
    allergies: list[str] | None = None

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
    notes: str | None = Field(
        default=None,
        max_length=5000,
    )

    @field_validator(
        "current_complaint_hpi",
        "past_medical_history",
        "past_medication_history",
        "allergy_history",
        "diet",
        "appetite",
        "sleep",
        "exercise",
        "bowel_bladder",
        "habits",
        "family_history",
        "smoking_status",
        "alcohol_status",
        "occupational_exposure",
        "notes",
    )
    @classmethod
    def empty_text_to_none(
        cls,
        value,
    ):
        if value is None:
            return None

        value = value.strip()

        return value or None

    @field_validator(
        "diseases",
        "medications",
        "allergies",
    )
    @classmethod
    def normalize_list(
        cls,
        value,
    ):
        if value is None:
            return None

        normalized = [
            item.strip()
            for item in value
            if item
            and item.strip()
        ]

        return normalized or None


class AdminPatientUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    full_name: str = Field(min_length=2, max_length=150)
    phone: str = Field(min_length=8, max_length=30)
    email: EmailStr = Field(max_length=255)
    address: str | None = Field(default=None, max_length=500)
    date_of_birth: date | None = None
    sex: Literal["MALE", "FEMALE"] | None = None
    is_active: bool = True

    latest_medical_history: (
        AdminLatestMedicalHistoryUpdate
        | None
    ) = None

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value):
        if not re.fullmatch(r"\+?[0-9\s().-]+", value):
            raise ValueError("Phone contains invalid characters.")
        digits = re.sub(r"[^0-9]", "", value)
        if digits.startswith("84") and (value.startswith("+84") or len(digits) == 11):
            digits = "0" + digits[2:]
        if not 8 <= len(digits) <= 15:
            raise ValueError("Phone must contain 8 to 15 digits.")
        return digits

    @field_validator("date_of_birth")
    @classmethod
    def validate_birth_date(cls, value):
        if value and value > date.today():
            raise ValueError("Date of birth cannot be in the future.")
        return value


class AdminPatientResponse(BaseModel):
    user_id: int
    patient_code: str
    username: str
    full_name: str
    phone: str | None
    email: str
    address: str | None
    date_of_birth: date | None
    sex: str | None
    is_active: bool


class AdminPatientPage(BaseModel):
    items: list[AdminPatientResponse]
    total: int
    page: int
    limit: int



class AdminPatientProfileDetail(BaseModel):
    user_id: int
    patient_id: int
    patient_code: str
    username: str
    full_name: str
    phone: str | None
    email: str
    address: str | None
    date_of_birth: date | None
    birth_year: int | None
    sex: str | None
    height_cm: float | None
    weight_kg: float | None
    is_active: bool


class AdminPatientAnalysisResponse(BaseModel):
    analysis_id: int
    analysis_code: str
    status: str
    input_source: str
    original_filename: str

    model_key: str | None
    model_name: str | None
    model_version: str | None

    predicted_class: str | None
    confidence: float | None

    has_image: bool

    report_id: int | None
    report_code: str | None
    report_language: str | None
    report_created_at: datetime | None

    created_at: datetime
    completed_at: datetime | None



class AdminPatientMedicalHistoryResponse(BaseModel):
    id: int
    recorded_at: datetime

    current_complaint_hpi: str | None
    past_medical_history: str | None
    past_medication_history: str | None
    allergy_history: str | None

    diet: str | None
    appetite: str | None
    sleep: str | None
    exercise: str | None
    bowel_bladder: str | None
    habits: str | None
    family_history: str | None

    diseases: list[str] | None
    medications: list[str] | None
    allergies: list[str] | None

    smoking_status: str | None
    alcohol_status: str | None
    occupational_exposure: str | None
    notes: str | None

    created_at: datetime
    updated_at: datetime


class AdminPatientDetailResponse(BaseModel):
    patient_profile: AdminPatientProfileDetail
    medical_history: list[AdminPatientMedicalHistoryResponse]
    analysis_history: list[AdminPatientAnalysisResponse]
