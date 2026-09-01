from pydantic import BaseModel, ConfigDict, Field


class PatientProfileCreate(BaseModel):
    full_name: str = Field(
        min_length=2,
        max_length=150,
    )

    birth_year: int | None = Field(
        default=None,
        ge=1900,
        le=2100,
    )

    gender: str | None = Field(
        default=None,
        max_length=20,
    )

    phone: str | None = Field(
        default=None,
        max_length=30,
    )

    address: str | None = Field(
        default=None,
        max_length=500,
    )


class PatientProfileUpdate(BaseModel):
    full_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )

    birth_year: int | None = Field(
        default=None,
        ge=1900,
        le=2100,
    )

    gender: str | None = Field(
        default=None,
        max_length=20,
    )

    phone: str | None = Field(
        default=None,
        max_length=30,
    )

    address: str | None = Field(
        default=None,
        max_length=500,
    )


class PatientProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    patient_code: str
    full_name: str
    birth_year: int | None
    gender: str | None
    phone: str | None
    address: str | None