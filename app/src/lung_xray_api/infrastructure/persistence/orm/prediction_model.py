from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lung_xray_api.infrastructure.persistence.orm.base import Base


class PredictionModel(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True)

    analysis_id: Mapped[int] = mapped_column(
        ForeignKey(
            "analyses.id",
            ondelete="CASCADE",
        ),
        unique=True,
        nullable=False,
        index=True,
    )

    predicted_class: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    confidence: Mapped[Decimal] = mapped_column(
        Numeric(8, 7),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    analysis = relationship(
        "AnalysisModel",
        back_populates="prediction",
    )

    probabilities = relationship(
        "PredictionProbabilityModel",
        back_populates="prediction",
        cascade="all, delete-orphan",
    )