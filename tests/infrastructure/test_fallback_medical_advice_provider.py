import pytest

from lung_xray_api.application.services.medical_advice_provider import (
    MedicalAdviceProviderConfigurationError,
    MedicalAdviceProviderError,
    MedicalAdviceProviderResult,
)
from lung_xray_api.infrastructure.ml.fallback_medical_advice_provider import (
    FallbackMedicalAdviceProvider,
)


class StubProvider:

    def __init__(
        self,
        *,
        result=None,
        error=None,
    ):
        self.result = result
        self.error = error
        self.calls = 0

    def generate(
        self,
        *,
        context,
        language,
    ):
        self.calls += 1

        if self.error is not None:
            raise self.error

        return self.result


def make_result(
    provider,
    model_name,
):
    return MedicalAdviceProviderResult(
        provider=provider,
        model_name=model_name,
        advice_text="report",
    )


def test_primary_success_does_not_use_fallback():
    primary_result = make_result(
        "openai",
        "gpt-test",
    )

    fallback_result = make_result(
        "local-fallback",
        "drai-deterministic-v1",
    )

    primary = StubProvider(
        result=primary_result,
    )

    fallback = StubProvider(
        result=fallback_result,
    )

    provider = FallbackMedicalAdviceProvider(
        primary=primary,
        fallback=fallback,
    )

    result = provider.generate(
        context=object(),
        language="vi",
    )

    assert result is primary_result
    assert primary.calls == 1
    assert fallback.calls == 0


@pytest.mark.parametrize(
    "error",
    [
        MedicalAdviceProviderError(
            "provider failed"
        ),
        MedicalAdviceProviderConfigurationError(
            "provider config failed"
        ),
    ],
)
def test_provider_failure_uses_local_fallback(
    error,
):
    fallback_result = make_result(
        "local-fallback",
        "drai-deterministic-v1",
    )

    primary = StubProvider(
        error=error,
    )

    fallback = StubProvider(
        result=fallback_result,
    )

    provider = FallbackMedicalAdviceProvider(
        primary=primary,
        fallback=fallback,
    )

    result = provider.generate(
        context=object(),
        language="vi",
    )

    assert result is fallback_result
    assert primary.calls == 1
    assert fallback.calls == 1


def test_value_error_is_not_hidden_by_fallback():
    primary = StubProvider(
        error=ValueError(
            "invalid internal data"
        ),
    )

    fallback = StubProvider(
        result=make_result(
            "local-fallback",
            "drai-deterministic-v1",
        ),
    )

    provider = FallbackMedicalAdviceProvider(
        primary=primary,
        fallback=fallback,
    )

    with pytest.raises(
        ValueError,
        match="invalid internal data",
    ):
        provider.generate(
            context=object(),
            language="vi",
        )

    assert primary.calls == 1
    assert fallback.calls == 0


def test_fallback_error_is_not_swallowed():
    primary = StubProvider(
        error=MedicalAdviceProviderError(
            "OpenAI unavailable"
        ),
    )

    fallback = StubProvider(
        error=RuntimeError(
            "local fallback failed"
        ),
    )

    provider = FallbackMedicalAdviceProvider(
        primary=primary,
        fallback=fallback,
    )

    with pytest.raises(
        RuntimeError,
        match="local fallback failed",
    ):
        provider.generate(
            context=object(),
            language="vi",
        )

    assert primary.calls == 1
    assert fallback.calls == 1