from datetime import datetime

from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.orm import Session

from lung_xray_api.infrastructure.persistence.orm.visitor_session_model import (
    VisitorSessionModel,
)


class VisitorStatsRepository:

    def touch_session(
        self,
        db: Session,
        *,
        visitor_id: str,
        session_id: str,
        now: datetime,
    ) -> None:

        session = db.scalar(
            select(
                VisitorSessionModel
            )
            .where(
                VisitorSessionModel.session_id
                == session_id
            )
        )

        if session is None:
            session = VisitorSessionModel(
                visitor_id=visitor_id,
                session_id=session_id,
                first_seen_at=now,
                last_seen_at=now,
            )

            db.add(
                session
            )

        else:
            session.last_seen_at = now

        db.flush()

    def count_online_now(
        self,
        db: Session,
        *,
        cutoff: datetime,
    ) -> int:

        value = db.scalar(
            select(
                func.count(
                    func.distinct(
                        VisitorSessionModel.visitor_id
                    )
                )
            )
            .where(
                VisitorSessionModel.last_seen_at
                >= cutoff
            )
        )

        return int(
            value or 0
        )

    def count_online_today(
        self,
        db: Session,
        *,
        start_at: datetime,
        end_at: datetime,
    ) -> int:

        value = db.scalar(
            select(
                func.count(
                    func.distinct(
                        VisitorSessionModel.visitor_id
                    )
                )
            )
            .where(
                VisitorSessionModel.last_seen_at
                >= start_at
            )
            .where(
                VisitorSessionModel.last_seen_at
                < end_at
            )
        )

        return int(
            value or 0
        )

    def count_total_visits(
        self,
        db: Session,
    ) -> int:

        value = db.scalar(
            select(
                func.count(
                    VisitorSessionModel.id
                )
            )
        )

        return int(
            value or 0
        )


visitor_stats_repository = (
    VisitorStatsRepository()
)
