from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lung_xray_api.infrastructure.persistence.orm.base import Base


class MedicalHistoryModel(Base):
    __tablename__ = "medical_histories"

    id: Mapped[int] = mapped_column(primary_key=True)

    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patient_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    diseases: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )

    medications: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )

    allergies: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )

    smoking_status: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    alcohol_status: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    occupational_exposure: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    patient = relationship(
        "PatientProfileModel",
        back_populates="medical_histories",
    )