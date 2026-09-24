from datetime import datetime
from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class PatientProfileMeasurementUpdate(
    BaseModel
):
    height_cm: Decimal = Field(
        gt=0,
        le=300,
    )

    weight_kg: Decimal = Field(
        gt=0,
        le=500,
    )


class PatientProfileMeasurementUpdateResponse(
    BaseModel
):
    changed: bool

    height_cm: Decimal | None

    weight_kg: Decimal | None

    recorded_at: datetime | None


class PatientProfileHistoryResponse(
    BaseModel
):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int

    height_cm: Decimal | None

    weight_kg: Decimal | None

    recorded_at: datetime
