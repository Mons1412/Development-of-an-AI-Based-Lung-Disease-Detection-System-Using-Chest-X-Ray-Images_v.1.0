from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import lung_xray_api.api.v1.medical_advices as medical_advices_api
from lung_xray_api.api.dependencies.auth import (
    get_current_user,
)
from lung_xray_api.application.services.medical_advice_service import (
    MedicalAdviceService,
)
from lung_xray_api.infrastructure.persistence.database import (
    get_db,
)
from lung_xray_api.main import app


OWNER_USER = SimpleNamespace(
    id=10,
    role="USER",
    is_active=True,
)

FOREIGN_USER = SimpleNamespace(
    id=20,
    role="USER",
    is_active=True,
)

ADMIN_USER = SimpleNamespace(
    id=99,
    role="ADMIN",
    is_active=True,
)

UNSUPPORTED_USER = SimpleNamespace(
    id=30,
    role="STAFF",
    is_active=True,
)


OWNER_PATIENT = SimpleNamespace(
    id=100,
    user_id=OWNER_USER.id,
)

FOREIGN_PATIENT = SimpleNamespace(
    id=200,
    user_id=FOREIGN_USER.id,
)


OWNER_ANALYSIS = SimpleNamespace(
    id=1000,
    patient_id=OWNER_PATIENT.id,
    patient=OWNER_PATIENT,
    status="COMPLETED",
    prediction=SimpleNamespace(
        predicted_class="normal",
        confidence=0.91,
        probabilities=[],
    ),
)

FOREIGN_ANALYSIS = SimpleNamespace(
    id=2000,
    patient_id=FOREIGN_PATIENT.id,
    patient=FOREIGN_PATIENT,
    status="COMPLETED",
    prediction=SimpleNamespace(
        predicted_class="pneumonia",
        confidence=0.87,
        probabilities=[],
    ),
)


def make_advice(
    *,
    advice_id,
    analysis,
    language="vi",
):
    return SimpleNamespace(
        id=advice_id,
        analysis_id=analysis.id,
        analysis=analysis,
        language=language,
        provider="gemini",
        model_name="gemini-test",
        advice_text=(
            f"Advice for analysis "
            f"{analysis.id}"
        ),
        created_at=datetime(
            2026,
            9,
            17,
            3,
            0,
            0,
        ),
    )


OWNER_ADVICE = make_advice(
    advice_id=5001,
    analysis=OWNER_ANALYSIS,
)

FOREIGN_ADVICE = make_advice(
    advice_id=6001,
    analysis=FOREIGN_ANALYSIS,
)


class FakePatientRepository:

    def get_by_user_id(
        self,
        db,
        user_id,
    ):
        if user_id == OWNER_USER.id:
            return OWNER_PATIENT

        if user_id == FOREIGN_USER.id:
            return FOREIGN_PATIENT

        return None


class FakeAnalysisRepository:

    def __init__(self):
        self.analyses = {
            OWNER_ANALYSIS.id:
                OWNER_ANALYSIS,
            FOREIGN_ANALYSIS.id:
                FOREIGN_ANALYSIS,
        }

    def get_by_id(
        self,
        db,
        analysis_id,
    ):
        return self.analyses.get(
            analysis_id
        )

    def get_by_id_for_patient(
        self,
        db,
        *,
        analysis_id,
        patient_id,
    ):
        analysis = self.analyses.get(
            analysis_id
        )

        if analysis is None:
            return None

        if (
            analysis.patient_id
            != patient_id
        ):
            return None

        return analysis


class FakeAdviceRepository:

    def __init__(self):
        self.created = []

        self.advices = {
            OWNER_ADVICE.id:
                OWNER_ADVICE,
            FOREIGN_ADVICE.id:
                FOREIGN_ADVICE,
        }

        self.analysis_advices = {
            OWNER_ANALYSIS.id: [
                OWNER_ADVICE
            ],
            FOREIGN_ANALYSIS.id: [
                FOREIGN_ADVICE
            ],
        }

    def create(
        self,
        db,
        *,
        analysis_id,
        language,
        provider,
        model_name,
        advice_text,
    ):
        advice = SimpleNamespace(
            id=7000 + len(
                self.created
            ),
            analysis_id=analysis_id,
            analysis=None,
            language=language,
            provider=provider,
            model_name=model_name,
            advice_text=advice_text,
            created_at=datetime(
                2026,
                9,
                17,
                4,
                0,
                0,
            ),
        )

        self.created.append(
            advice
        )

        return advice

    def get_by_id(
        self,
        db,
        advice_id,
    ):
        return self.advices.get(
            advice_id
        )

    def list_by_analysis_id(
        self,
        db,
        analysis_id,
    ):
        return list(
            self.analysis_advices.get(
                analysis_id,
                [],
            )
        )


class FakeContextBuilder:

    def build(
        self,
        db,
        *,
        analysis,
        patient,
    ):
        assert (
            analysis.patient_id
            == patient.id
        )

        return SimpleNamespace(
            analysis_id=analysis.id,
        )


class FakeProvider:

    def __init__(self):
        self.calls = []

    def generate(
        self,
        *,
        context,
        language,
    ):
        self.calls.append(
            (
                context.analysis_id,
                language,
            )
        )

        return SimpleNamespace(
            provider="gemini",
            model_name="gemini-test",
            advice_text=(
                "Generated Dr.AI advice."
            ),
        )


@pytest.fixture
def authorization_stack(
    monkeypatch,
):
    analysis_repository = (
        FakeAnalysisRepository()
    )

    patient_repository = (
        FakePatientRepository()
    )

    advice_repository = (
        FakeAdviceRepository()
    )

    provider = FakeProvider()

    service = MedicalAdviceService(
        analysis_repository=(
            analysis_repository
        ),
        patient_repository=(
            patient_repository
        ),
        advice_repository=(
            advice_repository
        ),
        context_builder=(
            FakeContextBuilder()
        ),
        provider=provider,
    )

    monkeypatch.setattr(
        medical_advices_api,
        "medical_advice_service",
        service,
    )

    yield SimpleNamespace(
        service=service,
        provider=provider,
        advice_repository=(
            advice_repository
        ),
    )

    app.dependency_overrides.clear()


def override_db():
    yield object()


def make_client(
    current_user,
):
    def override_current_user():
        return current_user

    app.dependency_overrides.clear()

    app.dependency_overrides[
        get_db
    ] = override_db

    app.dependency_overrides[
        get_current_user
    ] = override_current_user

    return TestClient(app)


def test_owner_user_can_generate_for_own_analysis(
    authorization_stack,
):
    with make_client(
        OWNER_USER
    ) as client:
        response = client.post(
            "/api/v1/medical-advices",
            json={
                "analysis_id":
                    OWNER_ANALYSIS.id,
                "language": "vi",
            },
        )

    assert response.status_code == 201

    assert (
        response.json()["analysis_id"]
        == OWNER_ANALYSIS.id
    )

    # An existing Dr.AI advice is reused.
    # The provider must not create a second advice.
    assert (
        authorization_stack
        .provider
        .calls
        == []
    )


def test_foreign_user_cannot_generate_for_other_analysis(
    authorization_stack,
):
    with make_client(
        FOREIGN_USER
    ) as client:
        response = client.post(
            "/api/v1/medical-advices",
            json={
                "analysis_id":
                    OWNER_ANALYSIS.id,
                "language": "vi",
            },
        )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "Analysis not found."
    )

    assert (
        authorization_stack
        .provider
        .calls
        == []
    )

    assert (
        authorization_stack
        .advice_repository
        .created
        == []
    )


def test_admin_can_generate_for_other_patient(
    authorization_stack,
):
    with make_client(
        ADMIN_USER
    ) as client:
        response = client.post(
            "/api/v1/medical-advices",
            json={
                "analysis_id":
                    FOREIGN_ANALYSIS.id,
                "language": "en",
            },
        )

    assert response.status_code == 201

    assert (
        response.json()["analysis_id"]
        == FOREIGN_ANALYSIS.id
    )


def test_owner_user_can_get_own_advice(
    authorization_stack,
):
    with make_client(
        OWNER_USER
    ) as client:
        response = client.get(
            "/api/v1/medical-advices/"
            + str(
                OWNER_ADVICE.id
            )
        )

    assert response.status_code == 200
    assert response.json()["id"] == (
        OWNER_ADVICE.id
    )


def test_foreign_user_cannot_get_other_advice(
    authorization_stack,
):
    with make_client(
        FOREIGN_USER
    ) as client:
        response = client.get(
            "/api/v1/medical-advices/"
            + str(
                OWNER_ADVICE.id
            )
        )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "Medical advice not found."
    )


def test_admin_can_get_other_patient_advice(
    authorization_stack,
):
    with make_client(
        ADMIN_USER
    ) as client:
        response = client.get(
            "/api/v1/medical-advices/"
            + str(
                FOREIGN_ADVICE.id
            )
        )

    assert response.status_code == 200

    assert response.json()["id"] == (
        FOREIGN_ADVICE.id
    )


def test_owner_user_can_list_own_analysis_advices(
    authorization_stack,
):
    with make_client(
        OWNER_USER
    ) as client:
        response = client.get(
            "/api/v1/analyses/"
            + str(
                OWNER_ANALYSIS.id
            )
            + "/medical-advices"
        )

    assert response.status_code == 200

    body = response.json()

    assert len(body) == 1

    assert body[0]["id"] == (
        OWNER_ADVICE.id
    )


def test_foreign_user_cannot_list_other_analysis_advices(
    authorization_stack,
):
    with make_client(
        FOREIGN_USER
    ) as client:
        response = client.get(
            "/api/v1/analyses/"
            + str(
                OWNER_ANALYSIS.id
            )
            + "/medical-advices"
        )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "Analysis not found."
    )


def test_admin_can_list_other_patient_advices(
    authorization_stack,
):
    with make_client(
        ADMIN_USER
    ) as client:
        response = client.get(
            "/api/v1/analyses/"
            + str(
                FOREIGN_ANALYSIS.id
            )
            + "/medical-advices"
        )

    assert response.status_code == 200

    body = response.json()

    assert len(body) == 1

    assert body[0]["id"] == (
        FOREIGN_ADVICE.id
    )


def test_unsupported_role_is_rejected_before_generation(
    authorization_stack,
):
    with make_client(
        UNSUPPORTED_USER
    ) as client:
        response = client.post(
            "/api/v1/medical-advices",
            json={
                "analysis_id":
                    OWNER_ANALYSIS.id,
                "language": "vi",
            },
        )

    assert response.status_code == 403

    assert (
        response.json()["detail"]
        == "Unsupported user role."
    )

    assert (
        authorization_stack
        .provider
        .calls
        == []
    )
