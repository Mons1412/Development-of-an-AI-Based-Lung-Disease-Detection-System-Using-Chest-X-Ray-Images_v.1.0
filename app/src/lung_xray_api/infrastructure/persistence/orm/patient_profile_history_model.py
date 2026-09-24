from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Numeric,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from lung_xray_api.infrastructure.persistence.orm.base import (
    Base,
)


class PatientProfileHistoryModel(Base):
    __tablename__ = (
        "patient_profile_histories"
    )

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    patient_id: Mapped[int] = mapped_column(
        ForeignKey(
            "patient_profiles.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    height_cm: Mapped[
        Decimal | None
    ] = mapped_column(
        Numeric(
            5,
            2,
        ),
        nullable=True,
    )

    weight_kg: Mapped[
        Decimal | None
    ] = mapped_column(
        Numeric(
            6,
            2,
        ),
        nullable=True,
    )

    recorded_at: Mapped[
        datetime
    ] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
