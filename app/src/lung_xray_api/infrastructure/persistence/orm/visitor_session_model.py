from datetime import datetime

from sqlalchemy import (
    DateTime,
    String,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from lung_xray_api.infrastructure.persistence.orm.base import Base


class VisitorSessionModel(Base):
    __tablename__ = "visitor_sessions"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    visitor_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )

    session_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        unique=True,
    )

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        index=True,
    )
