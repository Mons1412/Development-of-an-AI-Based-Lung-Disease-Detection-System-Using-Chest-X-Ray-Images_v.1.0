from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lung_xray_api.infrastructure.persistence.orm.base import Base


class PredictionProbabilityModel(Base):
    __tablename__ = "prediction_probabilities"

    __table_args__ = (
        UniqueConstraint(
            "prediction_id",
            "class_name",
            name="uq_prediction_probability_class",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    prediction_id: Mapped[int] = mapped_column(
        ForeignKey(
            "predictions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    class_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    probability: Mapped[Decimal] = mapped_column(
        Numeric(8, 7),
        nullable=False,
    )

    prediction = relationship(
        "PredictionModel",
        back_populates="probabilities",
    )