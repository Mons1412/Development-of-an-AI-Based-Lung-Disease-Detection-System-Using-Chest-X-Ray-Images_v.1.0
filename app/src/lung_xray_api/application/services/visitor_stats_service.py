from datetime import (
    datetime,
    timedelta,
    timezone,
)
from uuid import UUID

from sqlalchemy.orm import Session

from lung_xray_api.infrastructure.persistence.repositories.visitor_stats_repository import (
    VisitorStatsRepository,
    visitor_stats_repository,
)
from lung_xray_api.schemas.visitor_stats import (
    VisitorStatsResponse,
)


APPLICATION_TIMEZONE = timezone(
    timedelta(
        hours=7,
    )
)

ONLINE_WINDOW = timedelta(
    minutes=5,
)


class VisitorStatsService:

    def __init__(
        self,
        *,
        repository: VisitorStatsRepository = (
            visitor_stats_repository
        ),
    ) -> None:

        self.repository = repository

    @staticmethod
    def _utc_naive(
        value: datetime,
    ) -> datetime:

        return (
            value
            .astimezone(
                timezone.utc
            )
            .replace(
                tzinfo=None
            )
        )

    def _today_bounds(
        self,
        now_utc: datetime,
    ) -> tuple[
        datetime,
        datetime,
    ]:

        local_now = (
            now_utc
            .astimezone(
                APPLICATION_TIMEZONE
            )
        )

        local_start = (
            local_now
            .replace(
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
        )

        local_end = (
            local_start
            + timedelta(
                days=1
            )
        )

        return (
            self._utc_naive(
                local_start
            ),
            self._utc_naive(
                local_end
            ),
        )

    def _build_stats(
        self,
        db: Session,
        *,
        now_utc: datetime,
    ) -> VisitorStatsResponse:

        now_naive = (
            self._utc_naive(
                now_utc
            )
        )

        today_start, today_end = (
            self._today_bounds(
                now_utc
            )
        )

        online_cutoff = (
            now_naive
            - ONLINE_WINDOW
        )

        return VisitorStatsResponse(
            online_now=(
                self.repository
                .count_online_now(
                    db,
                    cutoff=online_cutoff,
                )
            ),
            online_today=(
                self.repository
                .count_online_today(
                    db,
                    start_at=today_start,
                    end_at=today_end,
                )
            ),
            total_visits=(
                self.repository
                .count_total_visits(
                    db
                )
            ),
        )

    def heartbeat(
        self,
        db: Session,
        *,
        visitor_id: UUID,
        session_id: UUID,
    ) -> VisitorStatsResponse:

        now_utc = datetime.now(
            timezone.utc
        )

        now_naive = (
            self._utc_naive(
                now_utc
            )
        )

        self.repository.touch_session(
            db,
            visitor_id=str(
                visitor_id
            ),
            session_id=str(
                session_id
            ),
            now=now_naive,
        )

        db.commit()

        return self._build_stats(
            db,
            now_utc=now_utc,
        )

    def get_stats(
        self,
        db: Session,
    ) -> VisitorStatsResponse:

        return self._build_stats(
            db,
            now_utc=datetime.now(
                timezone.utc
            ),
        )


visitor_stats_service = (
    VisitorStatsService()
)
