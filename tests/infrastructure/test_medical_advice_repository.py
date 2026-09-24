from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from lung_xray_api.infrastructure.persistence.orm import (
    AnalysisModel,
    MedicalAdviceModel,
    PatientProfileModel,
)
from lung_xray_api.infrastructure.persistence.orm.base import (
    Base,
)
from lung_xray_api.infrastructure.persistence.repositories.medical_advice_repository import (
    MedicalAdviceRepository,
)
from lung_xray_api.schemas.medical_advice import (
    MedicalAdviceResponse,
)


@pytest.fixture
def database():
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
        owner_patient = (
            PatientProfileModel(
                user_id=10,
                patient_code="PXREPO001",
                full_name="Repository Owner",
            )
        )

        other_patient = (
            PatientProfileModel(
                user_id=20,
                patient_code="PXREPO002",
                full_name="Repository Other",
            )
        )

        db.add_all(
            [
                owner_patient,
                other_patient,
            ]
        )

        db.flush()

        owner_analysis = AnalysisModel(
            analysis_code="AN-REPO-001",
            patient_id=owner_patient.id,
            model_id=1,
            original_filename=(
                "owner.png"
            ),
            stored_image_path=(
                "tests/owner.png"
            ),
            status="COMPLETED",
        )

        other_analysis = AnalysisModel(
            analysis_code="AN-REPO-002",
            patient_id=other_patient.id,
            model_id=1,
            original_filename=(
                "other.png"
            ),
            stored_image_path=(
                "tests/other.png"
            ),
            status="COMPLETED",
        )

        db.add_all(
            [
                owner_analysis,
                other_analysis,
            ]
        )

        db.commit()

        seed = SimpleNamespace(
            owner_analysis_id=(
                owner_analysis.id
            ),
            other_analysis_id=(
                other_analysis.id
            ),
            owner_user_id=(
                owner_patient.user_id
            ),
        )

        yield db, seed

    Base.metadata.drop_all(
        engine
    )

    engine.dispose()


def create_advice(
    repository,
    db,
    *,
    analysis_id,
    language="vi",
    model_name="gemini-test",
    text="Repository advice",
):
    return repository.create(
        db,
        analysis_id=analysis_id,
        language=language,
        provider="gemini",
        model_name=model_name,
        advice_text=text,
    )


def test_create_persists_and_serializes_nullable_model_name(
    database,
):
    db, seed = database

    repository = (
        MedicalAdviceRepository()
    )

    created = create_advice(
        repository,
        db,
        analysis_id=(
            seed.owner_analysis_id
        ),
        model_name=None,
    )

    created_id = created.id

    db.expunge_all()

    stored = db.get(
        MedicalAdviceModel,
        created_id,
    )

    assert stored is not None
    assert stored.provider == "gemini"
    assert stored.model_name is None
    assert (
        stored.advice_text
        == "Repository advice"
    )

    response = (
        MedicalAdviceResponse
        .model_validate(
            stored
        )
    )

    assert response.id == created_id
    assert response.model_name is None


def test_get_by_id_eager_loads_analysis_and_patient(
    database,
):
    db, seed = database

    repository = (
        MedicalAdviceRepository()
    )

    created = create_advice(
        repository,
        db,
        analysis_id=(
            seed.owner_analysis_id
        ),
    )

    advice_id = created.id

    db.expunge_all()

    loaded = repository.get_by_id(
        db,
        advice_id,
    )

    assert loaded is not None

    db.expunge_all()

    assert (
        loaded.analysis.patient.user_id
        == seed.owner_user_id
    )


def test_get_by_id_returns_none_for_unknown_id(
    database,
):
    db, _ = database

    repository = (
        MedicalAdviceRepository()
    )

    assert (
        repository.get_by_id(
            db,
            999999,
        )
        is None
    )


def test_list_by_analysis_id_returns_latest_only(
    database,
):
    db, seed = database

    repository = (
        MedicalAdviceRepository()
    )

    first = create_advice(
        repository,
        db,
        analysis_id=(
            seed.owner_analysis_id
        ),
        text="First",
    )

    second = create_advice(
        repository,
        db,
        analysis_id=(
            seed.owner_analysis_id
        ),
        text="Second",
    )

    rows = (
        repository
        .list_by_analysis_id(
            db,
            seed.owner_analysis_id,
        )
    )

    assert [
        row.id
        for row in rows
    ] == [
        second.id,
    ]


def test_list_by_analysis_id_isolates_analysis(
    database,
):
    db, seed = database

    repository = (
        MedicalAdviceRepository()
    )

    owner_advice = create_advice(
        repository,
        db,
        analysis_id=(
            seed.owner_analysis_id
        ),
    )

    create_advice(
        repository,
        db,
        analysis_id=(
            seed.other_analysis_id
        ),
    )

    rows = (
        repository
        .list_by_analysis_id(
            db,
            seed.owner_analysis_id,
        )
    )

    assert [
        row.id
        for row in rows
    ] == [
        owner_advice.id
    ]


def test_list_by_analysis_id_can_be_empty(
    database,
):
    db, seed = database

    repository = (
        MedicalAdviceRepository()
    )

    rows = (
        repository
        .list_by_analysis_id(
            db,
            seed.owner_analysis_id,
        )
    )

    assert rows == []


def test_create_rolls_back_when_commit_fails():
    repository = (
        MedicalAdviceRepository()
    )

    class FailingSession:

        def __init__(self):
            self.added = None
            self.rollback_called = False

        def add(
            self,
            value,
        ):
            self.added = value

        def commit(self):
            raise RuntimeError(
                "commit failed"
            )

        def refresh(
            self,
            value,
        ):
            raise AssertionError(
                "refresh must not run"
            )

        def rollback(self):
            self.rollback_called = True

    db = FailingSession()

    with pytest.raises(
        RuntimeError,
        match="commit failed",
    ):
        repository.create(
            db,
            analysis_id=1,
            language="vi",
            provider="gemini",
            model_name="gemini-test",
            advice_text="Advice",
        )

    assert db.added is not None
    assert db.rollback_called is True
