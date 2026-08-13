
"""Test Gemini without printing or persisting the API key."""

from __future__ import annotations

from uuid import uuid4

from lung_xray_api.assistant.gemini_provider import GeminiProvider
from lung_xray_api.core.config import load_settings


def main() -> None:
    settings = load_settings()
    if not settings.online_ai_enabled:
        raise SystemExit("ONLINE_AI_ENABLED chưa bật trong .env")
    if not settings.gemini_api_key:
        raise SystemExit("GEMINI_API_KEY chưa có trong .env")

    provider = GeminiProvider(
        api_key=settings.gemini_api_key.get_secret_value(),
        model_name=settings.gemini_model,
        timeout_seconds=settings.online_ai_timeout_seconds,
        temperature=settings.online_ai_temperature,
        max_answer_characters=settings.online_ai_max_answer_characters,
    )
    try:
        provider.probe(str(uuid4()))
        print(f"[PASS] Provider: {provider.provider_name}")
        print(f"[PASS] Model: {provider.model_name}")
        print("[PASS] Response: live probe completed")
    finally:
        provider.close()


if __name__ == "__main__":
    main()
