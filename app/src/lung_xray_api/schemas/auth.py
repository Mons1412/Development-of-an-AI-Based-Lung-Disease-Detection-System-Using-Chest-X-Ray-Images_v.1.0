from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)


class RegisterRequest(BaseModel):
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

    password: str = Field(
        min_length=8,
        max_length=128,
    )

    confirm_password: str = Field(
        min_length=8,
        max_length=128,
    )

    @field_validator(
        "date_of_birth",
        mode="before",
    )
    @classmethod
    def parse_date_of_birth(
        cls,
        value,
    ):
        if isinstance(
            value,
            str,
        ):
            candidate = value.strip()

            try:
                return datetime.strptime(
                    candidate,
                    "%d/%m/%Y",
                ).date()

            except ValueError:
                return candidate

        return value

    @field_validator(
        "full_name",
        "phone",
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
    )
    @classmethod
    def strip_required_text(
        cls,
        value: str,
    ) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError(
                "Field cannot be blank."
            )

        return normalized

    @model_validator(
        mode="after"
    )
    def validate_registration(
        self,
    ) -> Self:
        if (
            self.date_of_birth
            > date.today()
        ):
            raise ValueError(
                "Date of birth cannot "
                "be in the future."
            )

        if (
            self.password
            != self.confirm_password
        ):
            raise ValueError(
                "Passwords do not match."
            )

        return self


class UserResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    username: str
    phone: str | None
    email: EmailStr
    role: str
    is_active: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
