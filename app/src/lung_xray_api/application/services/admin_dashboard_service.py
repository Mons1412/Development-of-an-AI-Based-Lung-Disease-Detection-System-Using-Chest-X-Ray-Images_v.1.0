from sqlalchemy.orm import Session

from lung_xray_api.infrastructure.persistence.repositories.admin_dashboard_repository import (
    AdminDashboardRepository,
)
from lung_xray_api.schemas.admin_dashboard import (
    AdminDashboardResponse,
)


class AdminDashboardService:

    def __init__(
        self,
        repository: (
            AdminDashboardRepository
            | None
        ) = None,
    ):
        self.repository = (
            repository
            or AdminDashboardRepository()
        )

    def get_dashboard(
        self,
        db: Session,
        *,
        recent_limit: int = 10,
    ) -> AdminDashboardResponse:

        if (
            recent_limit < 1
            or recent_limit > 50
        ):
            raise ValueError(
                "Recent analysis limit "
                "must be between 1 and 50."
            )

        payload = {
            "overview":
                self.repository
                .get_overview(db),
            "prediction_distribution":
                self.repository
                .get_prediction_distribution(
                    db
                ),
            "model_usage":
                self.repository
                .get_model_usage(db),
            "recent_analyses":
                self.repository
                .list_recent_analyses(
                    db,
                    limit=recent_limit,
                ),
        }

        return (
            AdminDashboardResponse
            .model_validate(payload)
        )


admin_dashboard_service = (
    AdminDashboardService()
)
