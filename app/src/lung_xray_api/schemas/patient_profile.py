from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
)


class PatientProfileCreate(BaseModel):
    full_name: str = Field(
        min_length=2,
        max_length=150,
    )

    date_of_birth: date

    sex: Literal[
        "MALE",
        "FEMALE",
    ]

    phone: str = Field(
        min_length=8,
        max_length=20,
    )

    email: EmailStr

    height_cm: Decimal = Field(
        ge=30,
        le=300,
    )

    weight_kg: Decimal = Field(
        ge=2,
        le=500,
    )


class PatientProfileUpdate(BaseModel):
    full_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )

    date_of_birth: date | None = None

    sex: Literal[
        "MALE",
        "FEMALE",
    ] | None = None

    phone: str | None = Field(
        default=None,
        min_length=8,
        max_length=20,
    )

    email: EmailStr | None = None

    height_cm: Decimal | None = Field(
        default=None,
        ge=30,
        le=300,
    )

    weight_kg: Decimal | None = Field(
        default=None,
        ge=2,
        le=500,
    )


class PatientProfileResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    user_id: int
    patient_code: str

    full_name: str
    date_of_birth: date | None
    sex: str | None

    phone: str | None
    email: EmailStr

    height_cm: Decimal | None
    weight_kg: Decimal | None

    created_at: datetime
    updated_at: datetime
