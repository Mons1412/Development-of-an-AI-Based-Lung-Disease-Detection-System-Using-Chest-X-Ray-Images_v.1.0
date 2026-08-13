"""Composition checks for the optional online assistant runtime."""

from __future__ import annotations

from dataclasses import replace

from pydantic import SecretStr

from lung_xray_api.assistant.online_provider import OnlineAIRequest, OnlineAIResponse
from lung_xray_api.assistant.service import AssistantResolution
from lung_xray_api.core import lifespan
from lung_xray_api.core.config import load_settings
from lung_xray_api.schemas.assistant import AssistantAnswer, AssistantQuery


class FakeOfflineAssistant:
    def resolve(self, query: AssistantQuery) -> AssistantResolution:
        return AssistantResolution(
            normalized_message=query.message,
            application_stage=query.application_stage,
            intent="application_purpose",
            outcome="conversational",
        )

    def render(self, resolution: AssistantResolution) -> AssistantAnswer:
        return AssistantAnswer(
            status="answered",
            intent=resolution.intent,
            answer="Nội dung local đã duyệt.",
            sources=[],
            disclaimer="Thông tin học thuật.",
            suggested_questions=[],
            confidence=1.0,
        )


class FakeGeminiProvider:
    provider_name = "gemini"

    def __init__(self, *, model_name: str, **_kwargs):
        self.model_name = model_name

    def generate(self, request: OnlineAIRequest) -> OnlineAIResponse:
        return OnlineAIResponse("OK", self.provider_name, self.model_name)

    def probe(self, request_id: str) -> None:
        return None

    def close(self) -> None:
        return None


def test_configured_gemini_runtime_starts_unverified_without_blocking(
    monkeypatch,
) -> None:
    monkeypatch.setattr(lifespan, "GeminiProvider", FakeGeminiProvider)
    settings = replace(
        load_settings(),
        online_ai_enabled=True,
        ai_primary_provider="gemini",
        gemini_api_key=SecretStr("test-key-not-used-for-network"),
        gemini_model="gemini-3.5-flash",
    )

    service = lifespan.build_hybrid_assistant_service(
        settings,
        FakeOfflineAssistant(),
    )
    try:
        status = service.status()
    finally:
        service.close()

    assert status.online_enabled is True
    assert status.configured is True
    assert status.verified is False
    assert status.state == "configured_unverified"
    assert status.online_available is False
    assert status.active_mode == "offline"
    assert status.provider == "gemini"
    assert status.model == "gemini-3.5-flash"


def test_enabled_runtime_without_key_is_misconfigured() -> None:
    settings = replace(
        load_settings(),
        online_ai_enabled=True,
        ai_primary_provider="gemini",
        gemini_api_key=None,
    )

    service = lifespan.build_hybrid_assistant_service(
        settings,
        FakeOfflineAssistant(),
    )
    try:
        status = service.status()
    finally:
        service.close()

    assert status.configured is False
    assert status.state == "misconfigured"
    assert status.active_mode == "offline"


def test_disabled_runtime_remains_offline_only() -> None:
    settings = replace(
        load_settings(),
        online_ai_enabled=False,
        gemini_api_key=None,
    )

    service = lifespan.build_hybrid_assistant_service(
        settings,
        FakeOfflineAssistant(),
    )
    try:
        status = service.status()
    finally:
        service.close()

    assert status.state == "disabled"
    assert status.configured is False
    assert status.provider == "local-retrieval"
