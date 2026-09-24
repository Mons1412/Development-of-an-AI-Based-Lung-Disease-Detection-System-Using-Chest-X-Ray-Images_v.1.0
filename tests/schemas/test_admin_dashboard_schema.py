from datetime import datetime

from lung_xray_api.schemas.admin_dashboard import (
    AdminDashboardResponse,
)


def test_admin_dashboard_response_contract():
    payload = {
        "overview": {
            "total_users": 5,
            "active_users": 4,
            "total_patients": 3,
            "total_analyses": 20,
            "completed_analyses": 17,
            "failed_analyses": 2,
            "total_medical_advices": 6,
            "total_reports": 8,
        },
        "prediction_distribution": [
            {
                "class_name": "normal",
                "count": 7,
            },
            {
                "class_name": "pneumonia",
                "count": 6,
            },
            {
                "class_name": "tuberculosis",
                "count": 4,
            },
        ],
        "model_usage": [
            {
                "model_key": "mobilenetv2",
                "display_name": "MobileNetV2",
                "version": "1.1.0",
                "analysis_count": 20,
            }
        ],
        "recent_analyses": [
            {
                "analysis_id": 100,
                "analysis_code": "AN-M13-001",
                "patient_code": "PXM13001",
                "status": "COMPLETED",
                "model_key": "mobilenetv2",
                "model_version": "1.1.0",
                "predicted_class": "pneumonia",
                "confidence": 0.91,
                "created_at": datetime(
                    2026,
                    9,
                    17,
                    1,
                    30,
                ),
            }
        ],
    }

    response = (
        AdminDashboardResponse
        .model_validate(payload)
    )

    assert (
        response.overview.total_users
        == 5
    )

    assert (
        response.overview.active_users
        == 4
    )

    assert (
        response.prediction_distribution[
            1
        ].class_name
        == "pneumonia"
    )

    assert (
        response.model_usage[
            0
        ].analysis_count
        == 20
    )

    recent = (
        response.recent_analyses[
            0
        ]
    )

    assert (
        recent.patient_code
        == "PXM13001"
    )

    assert (
        recent.confidence
        == 0.91
    )


def test_recent_analysis_allows_missing_prediction():
    response = (
        AdminDashboardResponse
        .model_validate(
            {
                "overview": {
                    "total_users": 0,
                    "active_users": 0,
                    "total_patients": 0,
                    "total_analyses": 1,
                    "completed_analyses": 0,
                    "failed_analyses": 1,
                    "total_medical_advices": 0,
                    "total_reports": 0,
                },
                "prediction_distribution": [],
                "model_usage": [],
                "recent_analyses": [
                    {
                        "analysis_id": 1,
                        "analysis_code":
                            "AN-FAILED",
                        "patient_code":
                            "PXFAILED",
                        "status":
                            "FAILED",
                        "model_key":
                            "mobilenetv2",
                        "model_version":
                            "1.1.0",
                        "predicted_class":
                            None,
                        "confidence":
                            None,
                        "created_at":
                            datetime(
                                2026,
                                9,
                                17,
                                1,
                                45,
                            ),
                    }
                ],
            }
        )
    )

    recent = (
        response.recent_analyses[
            0
        ]
    )

    assert (
        recent.predicted_class
        is None
    )

    assert (
        recent.confidence
        is None
    )
