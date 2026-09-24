from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from lung_xray_api.application.services.admin_dashboard_service import (
    AdminDashboardService,
)
from lung_xray_api.infrastructure.persistence.orm import (
    AIModel,
    AnalysisModel,
    PatientProfileModel,
    PredictionModel,
    UserModel,
)
from lung_xray_api.infrastructure.persistence.orm.base import (
    Base,
)
from lung_xray_api.infrastructure.persistence.repositories.admin_dashboard_repository import (
    AdminDashboardRepository,
)


@pytest.fixture
def empty_database():
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
        yield db

    Base.metadata.drop_all(
        engine
    )

    engine.dispose()


@pytest.fixture
def populated_dashboard_database(
    empty_database,
):
    db = empty_database

    active_user = UserModel(
        username="m13_integrity_active",
        email="m13_integrity_active@example.com",
        password_hash="hash",
        role="USER",
        is_active=True,
    )

    inactive_user = UserModel(
        username="m13_integrity_inactive",
        email="m13_integrity_inactive@example.com",
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

    patient_one = PatientProfileModel(
        user_id=active_user.id,
        patient_code="PXM13I001",
        full_name="Integrity Patient One",
        phone="0900000001",
        address="Private Address One",
    )

    patient_two = PatientProfileModel(
        user_id=inactive_user.id,
        patient_code="PXM13I002",
        full_name="Integrity Patient Two",
        phone="0900000002",
        address="Private Address Two",
    )

    model_a = AIModel(
        model_key="model_a",
        display_name="Model A",
        architecture="TestNetA",
        version="1.0.0",
        artifact_path="private/model-a.keras",
        class_names=[
            "normal",
            "pneumonia",
            "tuberculosis",
        ],
        is_active=True,
        is_default=True,
    )

    model_b = AIModel(
        model_key="model_b",
        display_name="Model B",
        architecture="TestNetB",
        version="2.0.0",
        artifact_path="private/model-b.keras",
        class_names=[
            "normal",
            "pneumonia",
            "tuberculosis",
        ],
        is_active=True,
        is_default=False,
    )

    db.add_all(
        [
            patient_one,
            patient_two,
            model_a,
            model_b,
        ]
    )

    db.flush()

    analyses = [
        AnalysisModel(
            analysis_code="AN-I-001",
            patient_id=patient_one.id,
            model_id=model_a.id,
            input_source="UPLOAD",
            original_filename="one.png",
            stored_image_path="private/one.png",
            status="COMPLETED",
            created_at=datetime(
                2026,
                9,
                17,
                1,
                0,
            ),
        ),
        AnalysisModel(
            analysis_code="AN-I-002",
            patient_id=patient_one.id,
            model_id=model_a.id,
            input_source="UPLOAD",
            original_filename="two.png",
            stored_image_path="private/two.png",
            status="COMPLETED",
            created_at=datetime(
                2026,
                9,
                17,
                2,
                0,
            ),
        ),
        AnalysisModel(
            analysis_code="AN-I-003",
            patient_id=patient_two.id,
            model_id=model_b.id,
            input_source="UPLOAD",
            original_filename="three.png",
            stored_image_path="private/three.png",
            status="FAILED",
            error_message="Internal failure detail",
            created_at=datetime(
                2026,
                9,
                17,
                3,
                0,
            ),
        ),
        AnalysisModel(
            analysis_code="AN-I-004",
            patient_id=patient_two.id,
            model_id=model_b.id,
            input_source="UPLOAD",
            original_filename="four.png",
            stored_image_path="private/four.png",
            status="PENDING",
            created_at=datetime(
                2026,
                9,
                17,
                4,
                0,
            ),
        ),
        AnalysisModel(
            analysis_code="AN-I-005",
            patient_id=patient_one.id,
            model_id=model_b.id,
            input_source="UPLOAD",
            original_filename="five.png",
            stored_image_path="private/five.png",
            status="COMPLETED",
            created_at=datetime(
                2026,
                9,
                17,
                5,
                0,
            ),
        ),
        AnalysisModel(
            analysis_code="AN-I-006",
            patient_id=patient_one.id,
            model_id=model_a.id,
            input_source="UPLOAD",
            original_filename="six.png",
            stored_image_path="private/six.png",
            status="COMPLETED",
            created_at=datetime(
                2026,
                9,
                17,
                5,
                0,
            ),
        ),
    ]

    db.add_all(
        analyses
    )

    db.flush()

    db.add_all(
        [
            PredictionModel(
                analysis_id=analyses[0].id,
                predicted_class="normal",
                confidence=0.91,
            ),
            PredictionModel(
                analysis_id=analyses[1].id,
                predicted_class="pneumonia",
                confidence=0.82,
            ),
            PredictionModel(
                analysis_id=analyses[4].id,
                predicted_class="tuberculosis",
                confidence=0.88,
            ),
            PredictionModel(
                analysis_id=analyses[5].id,
                predicted_class="normal",
                confidence=0.95,
            ),
        ]
    )

    db.commit()

    return db


def test_empty_database_returns_zero_dashboard(
    empty_database,
):
    repository = (
        AdminDashboardRepository()
    )

    assert repository.get_overview(
        empty_database
    ) == {
        "total_users": 0,
        "active_users": 0,
        "total_patients": 0,
        "total_analyses": 0,
        "completed_analyses": 0,
        "failed_analyses": 0,
        "total_medical_advices": 0,
        "total_reports": 0,
    }

    assert (
        repository
        .get_prediction_distribution(
            empty_database
        )
        == []
    )

    assert (
        repository.get_model_usage(
            empty_database
        )
        == []
    )

    assert (
        repository.list_recent_analyses(
            empty_database
        )
        == []
    )


def test_overview_counts_statuses_without_counting_pending_as_failed(
    populated_dashboard_database,
):
    repository = (
        AdminDashboardRepository()
    )

    overview = (
        repository.get_overview(
            populated_dashboard_database
        )
    )

    assert overview[
        "total_users"
    ] == 2

    assert overview[
        "active_users"
    ] == 1

    assert overview[
        "total_patients"
    ] == 2

    assert overview[
        "total_analyses"
    ] == 6

    assert overview[
        "completed_analyses"
    ] == 4

    assert overview[
        "failed_analyses"
    ] == 1


def test_prediction_distribution_groups_all_classes(
    populated_dashboard_database,
):
    repository = (
        AdminDashboardRepository()
    )

    rows = (
        repository
        .get_prediction_distribution(
            populated_dashboard_database
        )
    )

    assert rows == [
        {
            "class_name":
                "normal",
            "count": 2,
        },
        {
            "class_name":
                "pneumonia",
            "count": 1,
        },
        {
            "class_name":
                "tuberculosis",
            "count": 1,
        },
    ]


def test_model_usage_handles_multiple_models(
    populated_dashboard_database,
):
    repository = (
        AdminDashboardRepository()
    )

    rows = (
        repository.get_model_usage(
            populated_dashboard_database
        )
    )

    assert rows == [
        {
            "model_key":
                "model_a",
            "display_name":
                "Model A",
            "version":
                "1.0.0",
            "analysis_count":
                3,
        },
        {
            "model_key":
                "model_b",
            "display_name":
                "Model B",
            "version":
                "2.0.0",
            "analysis_count":
                3,
        },
    ]


def test_recent_analysis_order_uses_id_as_tie_breaker_and_limit(
    populated_dashboard_database,
):
    repository = (
        AdminDashboardRepository()
    )

    rows = (
        repository.list_recent_analyses(
            populated_dashboard_database,
            limit=3,
        )
    )

    assert [
        row["analysis_code"]
        for row in rows
    ] == [
        "AN-I-006",
        "AN-I-005",
        "AN-I-004",
    ]


def test_recent_analysis_keeps_missing_prediction_as_none(
    populated_dashboard_database,
):
    repository = (
        AdminDashboardRepository()
    )

    rows = (
        repository.list_recent_analyses(
            populated_dashboard_database,
            limit=10,
        )
    )

    row_by_code = {
        row["analysis_code"]: row
        for row in rows
    }

    failed = row_by_code[
        "AN-I-003"
    ]

    pending = row_by_code[
        "AN-I-004"
    ]

    assert (
        failed["predicted_class"]
        is None
    )

    assert (
        failed["confidence"]
        is None
    )

    assert (
        pending["predicted_class"]
        is None
    )

    assert (
        pending["confidence"]
        is None
    )


class PiiInjectionRepository:

    def get_overview(
        self,
        db,
    ):
        del db

        return {
            "total_users": 1,
            "active_users": 1,
            "total_patients": 1,
            "total_analyses": 1,
            "completed_analyses": 1,
            "failed_analyses": 0,
            "total_medical_advices": 0,
            "total_reports": 0,
        }

    def get_prediction_distribution(
        self,
        db,
    ):
        del db
        return []

    def get_model_usage(
        self,
        db,
    ):
        del db
        return []

    def list_recent_analyses(
        self,
        db,
        *,
        limit,
    ):
        del db
        del limit

        return [
            {
                "analysis_id": 1,
                "analysis_code":
                    "AN-PII-001",
                "patient_code":
                    "PXPII001",
                "status":
                    "COMPLETED",
                "model_key":
                    "model_a",
                "model_version":
                    "1.0.0",
                "predicted_class":
                    "normal",
                "confidence":
                    0.9,
                "created_at":
                    datetime(
                        2026,
                        9,
                        17,
                        6,
                        0,
                    ),

                "full_name":
                    "Should Not Leak",
                "phone":
                    "0900000000",
                "address":
                    "Private Address",
                "password_hash":
                    "private-hash",
                "stored_image_path":
                    "private/image.png",
                "error_message":
                    "internal",
                "advice_text":
                    "private advice",
                "artifact_path":
                    "private/model.keras",
            }
        ]


def test_dashboard_contract_filters_pii_and_internal_fields():
    service = AdminDashboardService(
        PiiInjectionRepository()
    )

    response = (
        service.get_dashboard(
            object()
        )
    )

    payload = response.model_dump(
        mode="json"
    )

    recent = payload[
        "recent_analyses"
    ][0]

    assert recent[
        "patient_code"
    ] == "PXPII001"

    forbidden_fields = {
        "full_name",
        "phone",
        "address",
        "password_hash",
        "stored_image_path",
        "error_message",
        "advice_text",
        "artifact_path",
    }

    assert (
        forbidden_fields
        .isdisjoint(
            recent.keys()
        )
    )
