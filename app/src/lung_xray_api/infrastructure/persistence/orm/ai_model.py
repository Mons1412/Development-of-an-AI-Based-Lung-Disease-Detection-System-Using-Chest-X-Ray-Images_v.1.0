from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    JSON,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lung_xray_api.infrastructure.persistence.orm.base import Base


class AIModel(Base):
    __tablename__ = "ai_models"

    __table_args__ = (
        UniqueConstraint(
            "model_key",
            "version",
            name="uq_ai_models_key_version",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    model_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    display_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    architecture: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    artifact_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    class_names: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    analyses = relationship(
        "AnalysisModel",
        back_populates="ai_model",
    )