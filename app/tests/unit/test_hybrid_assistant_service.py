from __future__ import annotations

from dataclasses import dataclass, field
import time

from lung_xray_api.assistant.hybrid_service import HybridAssistantService
from lung_xray_api.assistant.knowledge_base import KnowledgeItem
from lung_xray_api.assistant.online_provider import (
    OnlineAIError,
    OnlineAIRequest,
    OnlineAIResponse,
)
from lung_xray_api.assistant.service import AssistantResolution
from lung_xray_api.schemas.assistant import AssistantAnswer, AssistantQuery, PredictionContext


_ITEM = KnowledgeItem(
    id="KB_OUTPUT_CLASSES",
    title="Các lớp đầu ra",
    domain="model",
    intent="output_classes",
    stages=("after_analysis",),
    sample_questions=("Kết quả hiện tại có nghĩa gì?",),
    answer_short="Ba lớp đầu ra.",
    answer_detailed="Nội dung local đã duyệt.",
    source_ids=("MODEL_ARTIFACT_1_1_0",),
)


class FakeOffline:
    def __init__(self, resolution: AssistantResolution):
        self.resolution = resolution
        self.render_calls = 0

    def resolve(self, query: AssistantQuery) -> AssistantResolution:
        return self.resolution

    def render(self, resolution: AssistantResolution) -> AssistantAnswer:
        self.render_calls += 1
        return AssistantAnswer(
            status="medical_refusal" if resolution.outcome == "safety_refusal" else "answered",
            mode="offline",
            intent=resolution.intent,
            answer="Nội dung local đã duyệt.",
            sources=list(resolution.source_ids),
            disclaimer="Không thay thế đánh giá của bác sĩ.",
            suggested_questions=[],
            confidence=1.0,
        )


@dataclass
class FakeProvider:
    failures: list[OnlineAIError] = field(default_factory=list)
    probe_failure: OnlineAIError | None = None
    provider_name: str = "gemini"
    model_name: str = "gemini-3.5-flash"
    response_text: str = "Diễn giải trực tuyến an toàn."
    requests: list[OnlineAIRequest] = field(default_factory=list)
    probe_calls: int = 0

    def generate(self, request: OnlineAIRequest) -> OnlineAIResponse:
        self.requests.append(request)
        if self.failures:
            raise self.failures.pop(0)
        return OnlineAIResponse(
            answer=self.response_text,
            provider=self.provider_name,
            model=self.model_name,
        )

    def probe(self, request_id: str) -> None:
        self.probe_calls += 1
        if self.probe_failure is not None:
            raise self.probe_failure

    def close(self) -> None:
        return None


def _context() -> PredictionContext:
    return PredictionContext(
        predicted_label="pneumonia",
        probabilities={"normal": 0.1, "pneumonia": 0.8, "tuberculosis": 0.1},
        model_version="1.1.0",
    )


def _resolution(
    *,
    outcome: str = "prediction",
    intent: str = "explain_current_prediction",
) -> AssistantResolution:
    return AssistantResolution(
        normalized_message="giai thich ket qua",
        application_stage="after_analysis",
        intent=intent,
        outcome=outcome,  # type: ignore[arg-type]
        prediction_context=_context() if outcome == "prediction" else None,
        knowledge_items=(_ITEM,) if outcome in {"prediction", "knowledge"} else (),
    )


def _query(message: str = "Ảnh tôi vừa upload ấy") -> AssistantQuery:
    return AssistantQuery(
        message=message,
        application_stage="after_analysis",
        prediction_context=_context(),
    )


def test_hybrid_returns_online_answer_and_marks_provider_verified():
    offline = FakeOffline(_resolution())
    service = HybridAssistantService(
        offline_service=offline,
        online_provider=FakeProvider(),
        online_enabled=True,
        background_probe=False,
    )

    answer = service.answer(_query())
    status = service.status()

    assert answer.mode == "online"
    assert answer.provider == "gemini"
    assert answer.model == "gemini-3.5-flash"
    assert answer.intent == "explain_current_prediction"
    assert answer.fallback_used is False
    assert offline.render_calls == 0
    assert status.state == "online_verified"
    assert status.verified is True


def test_hybrid_fallback_uses_same_resolution_and_does_not_pre_render_offline():
    offline = FakeOffline(_resolution())
    provider = FakeProvider(
        failures=[
            OnlineAIError(
                "temporary",
                category="service_unavailable",
                retryable=True,
            )
        ]
    )
    service = HybridAssistantService(
        offline_service=offline,
        online_provider=provider,
        online_enabled=True,
        background_probe=False,
    )

    answer = service.answer(_query())

    assert answer.mode == "offline"
    assert answer.intent == "explain_current_prediction"
    assert answer.fallback_used is True
    assert answer.fallback_reason == "temporary_online_failure"
    assert offline.render_calls == 1
    assert provider.requests[0].intent == answer.intent
    assert not hasattr(provider.requests[0], "approved_answer")


def test_safety_refusal_occurs_before_gemini():
    provider = FakeProvider()
    service = HybridAssistantService(
        offline_service=FakeOffline(
            _resolution(outcome="safety_refusal", intent="dosage_request")
        ),
        online_provider=provider,
        online_enabled=True,
        background_probe=False,
    )

    answer = service.answer(_query("Liều thuốc bao nhiêu?"))

    assert answer.mode == "offline"
    assert answer.status == "medical_refusal"
    assert provider.requests == []


def test_identity_is_withheld_and_raw_question_never_reaches_provider():
    provider = FakeProvider()
    service = HybridAssistantService(
        offline_service=FakeOffline(_resolution()),
        online_provider=provider,
        online_enabled=True,
        background_probe=False,
    )

    answer = service.answer(
        _query("Tên bệnh nhân Nguyễn Văn A, ảnh tôi vừa upload ấy")
    )

    assert answer.mode == "offline"
    assert answer.fallback_reason == "privacy_guard"
    assert provider.requests == []

    safe_answer = service.answer(_query())
    assert safe_answer.mode == "online"
    assert provider.requests[0].question != "Ảnh tôi vừa upload ấy"
    assert "Nguyễn Văn A" not in str(provider.requests[0])


def test_hybrid_rejects_unsafe_online_output_and_uses_local_answer():
    provider = FakeProvider(response_text="Bạn bị viêm phổi, hãy uống thuốc ngay.")
    service = HybridAssistantService(
        offline_service=FakeOffline(_resolution()),
        online_provider=provider,
        online_enabled=True,
        background_probe=False,
    )

    answer = service.answer(_query())

    assert answer.mode == "offline"
    assert answer.fallback_reason == "unsafe_online_response"
    assert answer.answer == "Nội dung local đã duyệt."
    assert len(provider.requests) == 1


def test_hybrid_accepts_non_diagnostic_negated_safety_language():
    provider = FakeProvider(
        response_text=(
            "K\u1ebft qu\u1ea3 n\u00e0y kh\u00f4ng kh\u1eb3ng \u0111\u1ecbnh "
            "b\u1ec7nh nh\u00e2n m\u1eafc b\u1ec7nh."
        )
    )
    service = HybridAssistantService(
        offline_service=FakeOffline(_resolution()),
        online_provider=provider,
        online_enabled=True,
        background_probe=False,
    )

    answer = service.answer(_query())

    assert answer.mode == "online"
    assert answer.fallback_used is False
    assert answer.answer == provider.response_text


def test_configured_provider_starts_unverified_and_probe_is_cached():
    provider = FakeProvider()
    service = HybridAssistantService(
        offline_service=FakeOffline(_resolution()),
        online_provider=provider,
        online_enabled=True,
        probe_ttl_seconds=60,
        background_probe=True,
    )
    try:
        first = service.status()
        second = first
        for _ in range(40):
            second = service.status()
            if second.state == "online_verified":
                break
            time.sleep(0.005)
    finally:
        service.close()

    assert first.state == "configured_unverified"
    assert first.online_available is False
    assert second.state == "online_verified"
    assert provider.probe_calls == 1


def test_failed_request_marks_degraded_state():
    provider = FakeProvider(
        failures=[OnlineAIError("network", category="network", retryable=True)]
    )
    service = HybridAssistantService(
        offline_service=FakeOffline(_resolution()),
        online_provider=provider,
        online_enabled=True,
        background_probe=False,
    )

    service.answer(_query())

    assert service.status().state == "degraded_offline"


def test_circuit_breaker_opens_and_recovers_after_cooldown():
    def transient() -> OnlineAIError:
        return OnlineAIError(
            "network",
            category="network",
            retryable=True,
        )

    provider = FakeProvider(failures=[transient(), transient()])
    service = HybridAssistantService(
        offline_service=FakeOffline(_resolution()),
        online_provider=provider,
        online_enabled=True,
        circuit_failure_threshold=2,
        circuit_cooldown_seconds=0.01,
        background_probe=False,
    )

    service.answer(_query())
    service.answer(_query())
    circuit_answer = service.answer(_query())
    request_count_while_open = len(provider.requests)
    time.sleep(0.02)
    recovered = service.answer(_query())

    assert circuit_answer.fallback_reason == "circuit_open"
    assert request_count_while_open == 2
    assert recovered.mode == "online"
    assert service.status().state == "online_verified"
