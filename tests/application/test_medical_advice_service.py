from types import SimpleNamespace

import pytest

from lung_xray_api.application.services.medical_advice_provider import (
    MedicalAdviceProviderError,
    MedicalAdviceProviderResult,
)
from lung_xray_api.application.services.medical_advice_service import (
    MedicalAdviceService,
)


class FakeAnalysisRepository:

    def __init__(
        self,
        *,
        admin_analysis=None,
        patient_analysis=None,
    ):
        self.admin_analysis = admin_analysis
        self.patient_analysis = patient_analysis
        self.admin_calls = []
        self.patient_calls = []

    def get_by_id(
        self,
        db,
        analysis_id,
    ):
        self.admin_calls.append(
            analysis_id
        )

        return self.admin_analysis

    def get_by_id_for_patient(
        self,
        db,
        *,
        analysis_id,
        patient_id,
    ):
        self.patient_calls.append(
            (
                analysis_id,
                patient_id,
            )
        )

        return self.patient_analysis


class FakePatientRepository:

    def __init__(
        self,
        patient=None,
    ):
        self.patient = patient
        self.calls = []

    def get_by_user_id(
        self,
        db,
        user_id,
    ):
        self.calls.append(user_id)

        return self.patient


class FakeAdviceRepository:

    def __init__(
        self,
        *,
        advice=None,
        advice_list=None,
        events=None,
    ):
        self.advice = advice
        self.advice_list = (
            list(advice_list)
            if advice_list is not None
            else []
        )

        self.events = (
            events
            if events is not None
            else []
        )

        self.create_calls = []
        self.get_calls = []
        self.list_calls = []

    def create(
        self,
        db,
        **kwargs,
    ):
        self.events.append(
            "persist"
        )

        self.create_calls.append(
            kwargs
        )

        return SimpleNamespace(
            id=99,
            **kwargs,
        )

    def get_by_id(
        self,
        db,
        advice_id,
    ):
        self.get_calls.append(
            advice_id
        )

        return self.advice

    def list_by_analysis_id(
        self,
        db,
        analysis_id,
    ):
        self.list_calls.append(
            analysis_id
        )

        return list(
            self.advice_list
        )


class FakeContextBuilder:

    def __init__(
        self,
        *,
        events=None,
    ):
        self.events = (
            events
            if events is not None
            else []
        )

        self.calls = []

    def build(
        self,
        db,
        *,
        analysis,
        patient,
    ):
        self.events.append(
            "context"
        )

        self.calls.append(
            (
                analysis,
                patient,
            )
        )

        return SimpleNamespace(
            trusted=True
        )


class FakeProvider:

    def __init__(
        self,
        *,
        events=None,
        error=None,
    ):
        self.events = (
            events
            if events is not None
            else []
        )

        self.error = error
        self.calls = []

    def generate(
        self,
        *,
        context,
        language,
    ):
        self.events.append(
            "provider"
        )

        self.calls.append(
            (
                context,
                language,
            )
        )

        if self.error is not None:
            raise self.error

        return MedicalAdviceProviderResult(
            provider="gemini",
            model_name="gemini-test",
            advice_text="Generated advice",
        )


def make_patient(
    *,
    patient_id=7,
    user_id=10,
):
    return SimpleNamespace(
        id=patient_id,
        user_id=user_id,
    )


def make_analysis(
    *,
    patient=None,
    status="COMPLETED",
    prediction=True,
):
    if patient is None:
        patient = make_patient()

    return SimpleNamespace(
        id=42,
        patient=patient,
        status=status,
        prediction=(
            SimpleNamespace()
            if prediction
            else None
        ),
    )


def make_user(
    *,
    user_id=10,
    role="USER",
):
    return SimpleNamespace(
        id=user_id,
        role=role,
    )


def make_service(
    *,
    analysis=None,
    patient=None,
    advice=None,
    advice_list=None,
    provider_error=None,
    events=None,
):
    if events is None:
        events = []

    analysis_repository = (
        FakeAnalysisRepository(
            admin_analysis=analysis,
            patient_analysis=analysis,
        )
    )

    patient_repository = (
        FakePatientRepository(
            patient
        )
    )

    advice_repository = (
        FakeAdviceRepository(
            advice=advice,
            advice_list=advice_list,
            events=events,
        )
    )

    context_builder = (
        FakeContextBuilder(
            events=events
        )
    )

    provider = FakeProvider(
        events=events,
        error=provider_error,
    )

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
        context_builder=context_builder,
        provider=provider,
    )

    return (
        service,
        analysis_repository,
        patient_repository,
        advice_repository,
        context_builder,
        provider,
    )


def test_user_generates_and_persists_after_provider():
    events = []

    patient = make_patient()
    analysis = make_analysis(
        patient=patient
    )

    (
        service,
        analysis_repository,
        _,
        advice_repository,
        _,
        provider,
    ) = make_service(
        analysis=analysis,
        patient=patient,
        events=events,
    )

    result = service.generate_advice(
        object(),
        make_user(
            role=" user "
        ),
        analysis_id=42,
        language=" VI ",
    )

    assert (
        analysis_repository.patient_calls
        == [(42, 7)]
    )

    assert provider.calls[0][1] == "vi"

    assert events == [
        "context",
        "provider",
        "persist",
    ]

    assert result.language == "vi"
    assert result.provider == "gemini"

    assert (
        advice_repository
        .create_calls[0]["analysis_id"]
        == 42
    )


def test_admin_generates_for_any_patient():
    patient = make_patient(
        user_id=999
    )

    analysis = make_analysis(
        patient=patient
    )

    (
        service,
        analysis_repository,
        patient_repository,
        advice_repository,
        _,
        _,
    ) = make_service(
        analysis=analysis,
        patient=None,
    )

    result = service.generate_advice(
        object(),
        make_user(
            user_id=1,
            role="ADMIN",
        ),
        analysis_id=42,
        language="en",
    )

    assert (
        analysis_repository.admin_calls
        == [42]
    )

    assert patient_repository.calls == []

    assert len(
        advice_repository.create_calls
    ) == 1

    assert result.language == "en"


def test_foreign_user_gets_analysis_not_found():
    patient = make_patient()

    (
        service,
        _,
        _,
        advice_repository,
        _,
        provider,
    ) = make_service(
        analysis=None,
        patient=patient,
    )

    with pytest.raises(
        LookupError,
        match="Analysis not found",
    ):
        service.generate_advice(
            object(),
            make_user(),
            analysis_id=999,
            language="vi",
        )

    assert provider.calls == []

    assert (
        advice_repository.create_calls
        == []
    )


def test_rejects_non_completed_analysis():
    patient = make_patient()

    analysis = make_analysis(
        patient=patient,
        status="FAILED",
    )

    (
        service,
        _,
        _,
        advice_repository,
        _,
        provider,
    ) = make_service(
        analysis=analysis,
        patient=patient,
    )

    with pytest.raises(
        ValueError,
        match="completed analyses",
    ):
        service.generate_advice(
            object(),
            make_user(),
            analysis_id=42,
            language="vi",
        )

    assert provider.calls == []

    assert (
        advice_repository.create_calls
        == []
    )


def test_rejects_completed_analysis_without_prediction():
    patient = make_patient()

    analysis = make_analysis(
        patient=patient,
        prediction=False,
    )

    (
        service,
        _,
        _,
        advice_repository,
        _,
        provider,
    ) = make_service(
        analysis=analysis,
        patient=patient,
    )

    with pytest.raises(
        ValueError,
        match="no prediction",
    ):
        service.generate_advice(
            object(),
            make_user(),
            analysis_id=42,
            language="vi",
        )

    assert provider.calls == []

    assert (
        advice_repository.create_calls
        == []
    )


def test_provider_failure_does_not_persist():
    patient = make_patient()

    analysis = make_analysis(
        patient=patient
    )

    (
        service,
        _,
        _,
        advice_repository,
        _,
        _,
    ) = make_service(
        analysis=analysis,
        patient=patient,
        provider_error=(
            MedicalAdviceProviderError(
                "provider failed"
            )
        ),
    )

    with pytest.raises(
        MedicalAdviceProviderError,
        match="provider failed",
    ):
        service.generate_advice(
            object(),
            make_user(),
            analysis_id=42,
            language="vi",
        )

    assert (
        advice_repository.create_calls
        == []
    )


def test_rejects_unsupported_language_before_generation():
    patient = make_patient()

    analysis = make_analysis(
        patient=patient
    )

    (
        service,
        analysis_repository,
        _,
        advice_repository,
        _,
        provider,
    ) = make_service(
        analysis=analysis,
        patient=patient,
    )

    with pytest.raises(
        ValueError,
        match="vi.*en",
    ):
        service.generate_advice(
            object(),
            make_user(),
            analysis_id=42,
            language="fr",
        )

    assert (
        analysis_repository.patient_calls
        == []
    )

    assert provider.calls == []

    assert (
        advice_repository.create_calls
        == []
    )


def test_owner_can_get_advice():
    patient = make_patient()

    advice = SimpleNamespace(
        id=5,
        analysis=SimpleNamespace(
            patient=patient
        ),
    )

    (
        service,
        _,
        _,
        _,
        _,
        _,
    ) = make_service(
        patient=patient,
        advice=advice,
    )

    result = service.get_advice(
        object(),
        make_user(),
        advice_id=5,
    )

    assert result is advice


def test_foreign_user_cannot_get_advice():
    advice = SimpleNamespace(
        id=5,
        analysis=SimpleNamespace(
            patient=make_patient(
                user_id=999
            )
        ),
    )

    (
        service,
        _,
        _,
        _,
        _,
        _,
    ) = make_service(
        advice=advice,
    )

    with pytest.raises(
        LookupError,
        match="Medical advice not found",
    ):
        service.get_advice(
            object(),
            make_user(),
            advice_id=5,
        )


def test_admin_can_get_any_advice():
    advice = SimpleNamespace(
        id=5,
        analysis=None,
    )

    (
        service,
        _,
        _,
        _,
        _,
        _,
    ) = make_service(
        advice=advice,
    )

    result = service.get_advice(
        object(),
        make_user(
            role="ADMIN"
        ),
        advice_id=5,
    )

    assert result is advice


def test_user_lists_advice_for_owned_analysis():
    patient = make_patient()

    analysis = make_analysis(
        patient=patient
    )

    expected = [
        SimpleNamespace(id=1),
        SimpleNamespace(id=2),
    ]

    (
        service,
        _,
        _,
        advice_repository,
        _,
        _,
    ) = make_service(
        analysis=analysis,
        patient=patient,
        advice_list=expected,
    )

    result = (
        service.list_analysis_advices(
            object(),
            make_user(),
            analysis_id=42,
        )
    )

    assert result == expected

    assert (
        advice_repository.list_calls
        == [42]
    )
