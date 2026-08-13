from __future__ import annotations

from types import SimpleNamespace

import pytest

from lung_xray_api.assistant.gemini_provider import GeminiProvider
from lung_xray_api.assistant.online_provider import (
    ApprovedKnowledgeChunk,
    OnlineAIConfigurationError,
    OnlineAIError,
    OnlineAIRequest,
    OnlinePredictionContext,
)


class FakeHttpError(RuntimeError):
    def __init__(self, code: int, retry_after: str | None = None):
        super().__init__(f"provider failure {code}")
        self.code = code
        self.response = SimpleNamespace(
            status_code=code,
            headers={"Retry-After": retry_after} if retry_after is not None else {},
        )


class FakeInteractions:
    def __init__(self, outcomes: list[object]):
        self.outcomes = list(outcomes)
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeClient:
    def __init__(self, interactions: FakeInteractions):
        self.interactions = interactions


def _request() -> OnlineAIRequest:
    return OnlineAIRequest(
        request_id="request-123",
        question="Giải thích kết quả phân loại hiện tại.",
        intent="explain_current_prediction",
        prediction_context=OnlinePredictionContext(
            predicted_label="pneumonia",
            probabilities={
                "normal": 0.1,
                "pneumonia": 0.8,
                "tuberculosis": 0.1,
            },
            model_version="1.1.0",
        ),
        knowledge_chunks=(
            ApprovedKnowledgeChunk(
                item_id="KB_OUTPUT_CLASSES",
                title="Các lớp đầu ra",
                content="Đây là xác suất đầu ra của mô hình.",
                source_ids=("MODEL_ARTIFACT_1_1_0",),
            ),
        ),
        source_ids=("MODEL_ARTIFACT_1_1_0",),
        safety_instructions=("Không chẩn đoán.",),
    )


def _provider(
    outcomes: list[object],
    *,
    delays: list[float] | None = None,
) -> tuple[GeminiProvider, FakeInteractions]:
    interactions = FakeInteractions(outcomes)
    provider = GeminiProvider(
        api_key="test-key",
        model_name="gemini-3.5-flash",
        temperature=None,
        client=FakeClient(interactions),
        sleep=(delays.append if delays is not None else lambda _delay: None),
        random_value=lambda: 0.0,
    )
    return provider, interactions


def test_gemini_provider_uses_structured_request_and_no_identity_fields():
    provider, interactions = _provider(
        [SimpleNamespace(output_text="Câu trả lời an toàn.")]
    )

    response = provider.generate(_request())

    assert response.answer == "Câu trả lời an toàn."
    call = interactions.calls[0]
    assert call["store"] is False
    assert call["model"] == "gemini-3.5-flash"
    assert "generation_config" not in call
    assert "RESOLVED INTENT" in str(call["input"])
    assert "CURRENT MODEL OUTPUT" in str(call["input"])
    assert "patient_name" not in str(call["input"])
    assert "patient_code" not in str(call["input"])
    assert "raw_image" not in str(call["input"])
    assert "test-key" not in str(call["input"])


def test_empty_gemini_response_is_rejected():
    provider, _ = _provider([SimpleNamespace(output_text="")])

    with pytest.raises(OnlineAIError) as caught:
        provider.generate(_request())

    assert caught.value.category == "invalid_response"


@pytest.mark.parametrize(
    ("error", "category"),
    [
        (TimeoutError("timed out"), "timeout"),
        (FakeHttpError(429), "rate_limit"),
        (FakeHttpError(503), "service_unavailable"),
    ],
)
def test_transient_errors_retry_once(error: Exception, category: str):
    delays: list[float] = []
    provider, interactions = _provider(
        [error, SimpleNamespace(output_text="Đã phục hồi.")],
        delays=delays,
    )

    response = provider.generate(_request())

    assert response.answer == "Đã phục hồi."
    assert len(interactions.calls) == 2
    assert len(delays) == 1
    assert delays[0] >= 0.25


def test_retry_after_is_respected_for_rate_limit():
    delays: list[float] = []
    provider, _ = _provider(
        [FakeHttpError(429, retry_after="2"), SimpleNamespace(output_text="OK")],
        delays=delays,
    )

    provider.generate(_request())

    assert delays == [2.0]


@pytest.mark.parametrize(
    ("status_code", "category"),
    [
        (401, "authentication"),
        (403, "permission"),
        (404, "invalid_model"),
    ],
)
def test_non_retryable_provider_errors_are_classified(
    status_code: int,
    category: str,
):
    provider, interactions = _provider([FakeHttpError(status_code)])

    with pytest.raises(OnlineAIError) as caught:
        provider.generate(_request())

    assert caught.value.category == category
    assert caught.value.retryable is False
    assert len(interactions.calls) == 1


def test_error_logs_contain_category_but_not_api_key(caplog):
    provider, _ = _provider([FakeHttpError(401)])

    with pytest.raises(OnlineAIConfigurationError):
        provider.generate(_request())

    assert "error_category=authentication" in caplog.text
    assert "test-key" not in caplog.text


def test_gemini_provider_rejects_empty_key():
    with pytest.raises(OnlineAIConfigurationError):
        GeminiProvider(api_key=" ", model_name="gemini-3.5-flash")
