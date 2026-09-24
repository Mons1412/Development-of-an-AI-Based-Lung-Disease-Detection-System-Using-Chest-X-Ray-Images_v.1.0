from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lung_xray_api.infrastructure.persistence.orm.base import Base


class AnalysisModel(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(primary_key=True)

    analysis_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    patient_id: Mapped[int] = mapped_column(
        ForeignKey(
            "patient_profiles.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    model_id: Mapped[int] = mapped_column(
        ForeignKey(
            "ai_models.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    input_source: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="UPLOAD",
    )

    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    stored_image_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="PENDING",
        index=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    patient = relationship(
        "PatientProfileModel",
        back_populates="analyses",
    )

    ai_model = relationship(
        "AIModel",
        back_populates="analyses",
    )

    prediction = relationship(
        "PredictionModel",
        back_populates="analysis",
        uselist=False,
        cascade="all, delete-orphan",
    )

    medical_advices = relationship(
        "MedicalAdviceModel",
        back_populates="analysis",
        cascade="all, delete-orphan",
    )

    reports = relationship(
        "ReportModel",
        back_populates="analysis",
        cascade="all, delete-orphan",
    )