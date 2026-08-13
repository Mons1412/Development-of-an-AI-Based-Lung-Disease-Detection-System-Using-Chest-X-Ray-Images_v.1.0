"""Regression tests for local runtime configuration loading."""

from __future__ import annotations

import os

import pytest

from lung_xray_api.core import config


_SETTING_NAMES = (
    "APP_ENV",
    "HOST",
    "PORT",
    "ARTIFACT_DIR",
    "KNOWLEDGE_BASE_PATH",
    "MAX_UPLOAD_MB",
    "ONLINE_AI_ENABLED",
    "AI_PRIMARY_PROVIDER",
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "ONLINE_AI_TIMEOUT_SECONDS",
    "ONLINE_AI_TEMPERATURE",
    "ONLINE_AI_MAX_ANSWER_CHARACTERS",
    "AI_OFFLINE_FALLBACK_ENABLED",
)


def _clear_setting_environment(monkeypatch) -> None:
    for name in _SETTING_NAMES:
        monkeypatch.delenv(name, raising=False)


def test_load_settings_reads_local_dotenv_without_mutating_process_environment(
    tmp_path, monkeypatch
) -> None:
    (tmp_path / ".env").write_text(
        "\n".join(
            (
                "APP_ENV=testing",
                "HOST=127.0.0.1",
                "PORT=8011",
                "ARTIFACT_DIR=artifacts/test-model",
                "KNOWLEDGE_BASE_PATH=knowledge_base/test-production.json",
                "MAX_UPLOAD_MB=11",
                "ONLINE_AI_ENABLED=true",
                "AI_PRIMARY_PROVIDER=gemini",
                "GEMINI_API_KEY=test-local-key",
                "GEMINI_MODEL=gemini-3.5-flash",
                "ONLINE_AI_TIMEOUT_SECONDS=17",
                "ONLINE_AI_TEMPERATURE=0.3",
                "ONLINE_AI_MAX_ANSWER_CHARACTERS=1200",
                "AI_OFFLINE_FALLBACK_ENABLED=true",
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "_project_root", lambda: tmp_path)
    _clear_setting_environment(monkeypatch)

    settings = config.load_settings()

    assert settings.app_env == "testing"
    assert settings.port == 8011
    assert settings.artifact_dir == tmp_path / "artifacts" / "test-model"
    assert settings.knowledge_base_path == tmp_path / "knowledge_base" / "test-production.json"
    assert settings.online_ai_enabled is True
    assert settings.ai_primary_provider == "gemini"
    assert settings.online_ai_provider == "gemini"
    assert settings.gemini_api_key is not None
    assert settings.gemini_api_key.get_secret_value() == "test-local-key"
    assert settings.gemini_model == "gemini-3.5-flash"
    assert settings.online_ai_timeout_seconds == 17
    assert settings.online_ai_temperature == 0.3
    assert settings.online_ai_max_answer_characters == 1200
    assert settings.online_ai_fallback_enabled is True
    assert "GEMINI_API_KEY" not in os.environ
    assert "test-local-key" not in repr(settings)
    assert "test-local-key" not in str(settings.safe_online_ai_summary())
    assert settings.safe_online_ai_summary()["key_configured"] is True


def test_process_environment_overrides_local_dotenv(tmp_path, monkeypatch) -> None:
    (tmp_path / ".env").write_text(
        "\n".join(
            (
                "ONLINE_AI_ENABLED=false",
                "GEMINI_API_KEY=file-key",
                "GEMINI_MODEL=gemini-3.5-flash",
                "PORT=8011",
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "_project_root", lambda: tmp_path)
    _clear_setting_environment(monkeypatch)
    monkeypatch.setenv("ONLINE_AI_ENABLED", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "process-key")
    monkeypatch.setenv("PORT", "8123")

    settings = config.load_settings()

    assert settings.online_ai_enabled is True
    assert settings.gemini_api_key is not None
    assert settings.gemini_api_key.get_secret_value() == "process-key"
    assert settings.port == 8123


def test_provider_name_is_normalized_and_temperature_is_optional(
    tmp_path,
    monkeypatch,
) -> None:
    (tmp_path / ".env").write_text(
        "\n".join(
            (
                "AI_PRIMARY_PROVIDER=GeMiNi",
                "ONLINE_AI_TEMPERATURE=",
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "_project_root", lambda: tmp_path)
    _clear_setting_environment(monkeypatch)

    settings = config.load_settings()

    assert settings.ai_primary_provider == "gemini"
    assert settings.online_ai_temperature is None


def test_missing_gemini_key_does_not_crash_settings_load(
    tmp_path,
    monkeypatch,
) -> None:
    (tmp_path / ".env").write_text(
        "ONLINE_AI_ENABLED=true\nAI_PRIMARY_PROVIDER=gemini\nGEMINI_API_KEY=\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "_project_root", lambda: tmp_path)
    _clear_setting_environment(monkeypatch)

    settings = config.load_settings()

    assert settings.online_ai_enabled is True
    assert settings.gemini_api_key is None
    assert settings.safe_online_ai_summary()["key_configured"] is False


def test_unsupported_provider_is_rejected_with_clear_error(
    tmp_path,
    monkeypatch,
) -> None:
    (tmp_path / ".env").write_text(
        "AI_PRIMARY_PROVIDER=unsupported\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "_project_root", lambda: tmp_path)
    _clear_setting_environment(monkeypatch)

    with pytest.raises(ValueError, match="AI_PRIMARY_PROVIDER"):
        config.load_settings()
