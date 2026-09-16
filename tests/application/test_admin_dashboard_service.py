import pytest

from lung_xray_api.application.services.admin_dashboard_service import (
    AdminDashboardService,
)


class FakeDashboardRepository:

    def __init__(self):
        self.recent_limit = None

    def get_overview(
        self,
        db,
    ):
        del db

        return {
            "total_users": 2,
            "active_users": 1,
            "total_patients": 1,
            "total_analyses": 3,
            "completed_analyses": 2,
            "failed_analyses": 1,
            "total_medical_advices": 1,
            "total_reports": 1,
        }

    def get_prediction_distribution(
        self,
        db,
    ):
        del db

        return [
            {
                "class_name":
                    "normal",
                "count": 2,
            }
        ]

    def get_model_usage(
        self,
        db,
    ):
        del db

        return [
            {
                "model_key":
                    "mobilenetv2",
                "display_name":
                    "MobileNetV2",
                "version":
                    "1.1.0",
                "analysis_count":
                    3,
            }
        ]

    def list_recent_analyses(
        self,
        db,
        *,
        limit,
    ):
        del db

        self.recent_limit = limit

        return []


def test_service_builds_dashboard_contract():
    repository = (
        FakeDashboardRepository()
    )

    service = AdminDashboardService(
        repository
    )

    response = (
        service.get_dashboard(
            object(),
            recent_limit=7,
        )
    )

    assert (
        response.overview
        .total_analyses
        == 3
    )

    assert (
        response
        .prediction_distribution[
            0
        ]
        .class_name
        == "normal"
    )

    assert (
        response.model_usage[
            0
        ].analysis_count
        == 3
    )

    assert (
        repository.recent_limit
        == 7
    )


@pytest.mark.parametrize(
    "limit",
    [
        0,
        51,
    ],
)
def test_service_rejects_invalid_recent_limit(
    limit,
):
    service = AdminDashboardService(
        FakeDashboardRepository()
    )

    with pytest.raises(
        ValueError,
        match=(
            "Recent analysis limit "
            "must be between 1 and 50"
        ),
    ):
        service.get_dashboard(
            object(),
            recent_limit=limit,
        )
