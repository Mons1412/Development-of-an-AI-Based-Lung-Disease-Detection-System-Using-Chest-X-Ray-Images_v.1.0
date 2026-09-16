from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from lung_xray_api.infrastructure.persistence.orm import (
    AIModel,
    AnalysisModel,
    MedicalAdviceModel,
    PatientProfileModel,
    PredictionModel,
    ReportModel,
    UserModel,
)
from lung_xray_api.infrastructure.persistence.orm.base import (
    Base,
)
from lung_xray_api.infrastructure.persistence.repositories.admin_dashboard_repository import (
    AdminDashboardRepository,
)


@pytest.fixture
def dashboard_database():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )

    Base.metadata.create_all(
        engine
    )

    with Session(engine) as db:
        active_user = UserModel(
            username="m13active",
            email="m13active@example.com",
            password_hash="hash",
            role="USER",
            is_active=True,
        )

        inactive_user = UserModel(
            username="m13inactive",
            email="m13inactive@example.com",
            password_hash="hash",
            role="USER",
            is_active=False,
        )

        db.add_all(
            [
                active_user,
                inactive_user,
            ]
        )

        db.flush()

        patient_one = (
            PatientProfileModel(
                user_id=active_user.id,
                patient_code="PXM13001",
                full_name="M13 Patient 1",
            )
        )

        patient_two = (
            PatientProfileModel(
                user_id=inactive_user.id,
                patient_code="PXM13002",
                full_name="M13 Patient 2",
            )
        )

        model = AIModel(
            model_key="mobilenetv2",
            display_name="MobileNetV2",
            architecture="MobileNetV2",
            version="1.1.0",
            artifact_path="tests/model.keras",
            class_names=[
                "normal",
                "pneumonia",
                "tuberculosis",
            ],
            is_active=True,
            is_default=True,
        )

        db.add_all(
            [
                patient_one,
                patient_two,
                model,
            ]
        )

        db.flush()

        completed = AnalysisModel(
            analysis_code="AN-M13-001",
            patient_id=patient_one.id,
            model_id=model.id,
            input_source="UPLOAD",
            original_filename="one.png",
            stored_image_path="tests/one.png",
            status="COMPLETED",
            created_at=datetime(
                2026,
                9,
                17,
                1,
                0,
            ),
        )

        failed = AnalysisModel(
            analysis_code="AN-M13-002",
            patient_id=patient_two.id,
            model_id=model.id,
            input_source="UPLOAD",
            original_filename="two.png",
            stored_image_path="tests/two.png",
            status="FAILED",
            created_at=datetime(
                2026,
                9,
                17,
                2,
                0,
            ),
        )

        pending = AnalysisModel(
            analysis_code="AN-M13-003",
            patient_id=patient_one.id,
            model_id=model.id,
            input_source="UPLOAD",
            original_filename="three.png",
            stored_image_path="tests/three.png",
            status="PENDING",
            created_at=datetime(
                2026,
                9,
                17,
                3,
                0,
            ),
        )

        db.add_all(
            [
                completed,
                failed,
                pending,
            ]
        )

        db.flush()

        prediction = PredictionModel(
            analysis_id=completed.id,
            predicted_class="pneumonia",
            confidence=0.91,
        )

        advice = MedicalAdviceModel(
            analysis_id=completed.id,
            language="vi",
            provider="gemini",
            model_name="gemini-test",
            advice_text="Test advice",
        )

        report = ReportModel(
            analysis_id=completed.id,
            report_code="RP-M13-001",
            language="vi",
            file_path="tests/m13.pdf",
        )

        db.add_all(
            [
                prediction,
                advice,
                report,
            ]
        )

        db.commit()

        yield db

    Base.metadata.drop_all(
        engine
    )

    engine.dispose()


def test_dashboard_overview_counts(
    dashboard_database,
):
    repository = (
        AdminDashboardRepository()
    )

    overview = (
        repository.get_overview(
            dashboard_database
        )
    )

    assert overview == {
        "total_users": 2,
        "active_users": 1,
        "total_patients": 2,
        "total_analyses": 3,
        "completed_analyses": 1,
        "failed_analyses": 1,
        "total_medical_advices": 1,
        "total_reports": 1,
    }


def test_prediction_distribution_uses_predictions(
    dashboard_database,
):
    repository = (
        AdminDashboardRepository()
    )

    rows = (
        repository
        .get_prediction_distribution(
            dashboard_database
        )
    )

    assert rows == [
        {
            "class_name":
                "pneumonia",
            "count": 1,
        }
    ]


def test_model_usage_counts_analyses(
    dashboard_database,
):
    repository = (
        AdminDashboardRepository()
    )

    rows = (
        repository.get_model_usage(
            dashboard_database
        )
    )

    assert rows == [
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


def test_recent_analyses_are_newest_first(
    dashboard_database,
):
    repository = (
        AdminDashboardRepository()
    )

    rows = (
        repository
        .list_recent_analyses(
            dashboard_database,
            limit=10,
        )
    )

    assert [
        row["analysis_code"]
        for row in rows
    ] == [
        "AN-M13-003",
        "AN-M13-002",
        "AN-M13-001",
    ]

    assert (
        rows[0][
            "predicted_class"
        ]
        is None
    )

    assert (
        rows[1][
            "predicted_class"
        ]
        is None
    )

    assert (
        rows[2][
            "predicted_class"
        ]
        == "pneumonia"
    )

    assert (
        float(
            rows[2]["confidence"]
        )
        == pytest.approx(
            0.91
        )
    )


def test_recent_analyses_respects_limit(
    dashboard_database,
):
    repository = (
        AdminDashboardRepository()
    )

    rows = (
        repository
        .list_recent_analyses(
            dashboard_database,
            limit=2,
        )
    )

    assert len(rows) == 2

    assert [
        row["analysis_code"]
        for row in rows
    ] == [
        "AN-M13-003",
        "AN-M13-002",
    ]
