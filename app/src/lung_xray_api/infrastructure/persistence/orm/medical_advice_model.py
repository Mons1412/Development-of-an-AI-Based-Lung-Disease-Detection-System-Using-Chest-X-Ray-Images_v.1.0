from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lung_xray_api.infrastructure.persistence.orm.base import Base


class MedicalAdviceModel(Base):
    __tablename__ = "medical_advices"

    id: Mapped[int] = mapped_column(primary_key=True)

    analysis_id: Mapped[int] = mapped_column(
        ForeignKey(
            "analyses.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="vi",
    )

    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    model_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    advice_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    analysis = relationship(
        "AnalysisModel",
        back_populates="medical_advices",
    )