"""Cấu hình runtime cho Phase 02.

Module này chỉ đọc environment và suy ra đường dẫn tương đối repository.
Không hard-code absolute path cá nhân để cùng source chạy được trên máy khác.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from pydantic import SecretStr


def _project_root() -> Path:
    """Trả về root của `02_fastapi_inference` từ vị trí file trong src-layout."""

    return Path(__file__).resolve().parents[3]


def _environment_values(root: Path) -> Mapping[str, str]:
    """Read the local .env without mutating process environment variables.

    A process-level environment variable intentionally wins over the local file,
    which keeps launcher/CI configuration deterministic and prevents a checked-out
    .env from overriding an explicit deployment setting.
    """

    dotenv_path = root / ".env"
    dotenv = {
        name: value
        for name, value in dotenv_values(dotenv_path).items()
        if isinstance(name, str) and isinstance(value, str)
    }
    return {**dotenv, **os.environ}


def _env_bool(environment: Mapping[str, str], name: str, default: bool) -> bool:
    value = environment.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Cấu hình bất biến sau khi app khởi động.

    Invariant quan trọng: `artifact_dir` luôn trỏ đến bundle model đã giải nén,
    không trỏ ngược sang notebook, evidence archive hoặc Phase 01.
    """

    app_env: str
    log_level: str
    host: str
    port: int
    artifact_dir: Path
    api_key_enabled: bool
    api_key: str | None
    max_upload_mb: int
    knowledge_base_path: Path | None = None
    history_db_path: Path | None = None
    thumbnail_dir: Path | None = None
    thumbnail_max_dimension: int = 512
    history_page_size: int = 25
    history_busy_timeout_ms: int = 5000
    online_ai_enabled: bool = False
    ai_primary_provider: str = "gemini"
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-3.5-flash"
    online_ai_timeout_seconds: float = 30.0
    online_ai_temperature: float | None = None
    online_ai_max_answer_characters: int = 6000
    ai_offline_fallback_enabled: bool = True

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def online_ai_provider(self) -> str:
        """Backward-compatible read alias for the pre-stability field name."""

        return self.ai_primary_provider

    @property
    def online_ai_fallback_enabled(self) -> bool:
        """Backward-compatible read alias for the pre-stability field name."""

        return self.ai_offline_fallback_enabled

    def safe_online_ai_summary(self) -> dict[str, Any]:
        """Return diagnostics that are safe to log or expose to local operators."""

        return {
            "online_enabled": self.online_ai_enabled,
            "provider": self.ai_primary_provider,
            "key_configured": self.gemini_api_key is not None,
            "model": self.gemini_model,
            "timeout_seconds": self.online_ai_timeout_seconds,
            "offline_fallback_enabled": self.ai_offline_fallback_enabled,
        }


def load_settings() -> Settings:
    root = _project_root()
    environment = _environment_values(root)
    artifact_dir = Path(
        environment.get("ARTIFACT_DIR", "artifacts/lung_classifier/1.1.0")
    )
    if not artifact_dir.is_absolute():
        artifact_dir = root / artifact_dir

    knowledge_base_path = Path(
        environment.get(
            "KNOWLEDGE_BASE_PATH",
            "knowledge_base/compiled/knowledge_base.production.vi.json",
        )
    )
    if not knowledge_base_path.is_absolute():
        knowledge_base_path = root / knowledge_base_path

    history_db_path = Path(
        environment.get("HISTORY_DB_PATH", "var/data/lung_xray_history.db")
    )
    if not history_db_path.is_absolute():
        history_db_path = root / history_db_path

    thumbnail_dir = Path(environment.get("THUMBNAIL_DIR", "var/data/thumbnails"))
    if not thumbnail_dir.is_absolute():
        thumbnail_dir = root / thumbnail_dir

    thumbnail_max_dimension = int(environment.get("THUMBNAIL_MAX_DIMENSION", "512"))
    history_page_size = int(environment.get("HISTORY_PAGE_SIZE", "25"))
    history_busy_timeout_ms = int(environment.get("HISTORY_BUSY_TIMEOUT_MS", "5000"))
    if thumbnail_max_dimension <= 0:
        raise ValueError("THUMBNAIL_MAX_DIMENSION must be greater than zero")
    if history_page_size <= 0:
        raise ValueError("HISTORY_PAGE_SIZE must be greater than zero")
    if history_busy_timeout_ms <= 0:
        raise ValueError("HISTORY_BUSY_TIMEOUT_MS must be greater than zero")

    api_key_enabled = _env_bool(environment, "API_KEY_ENABLED", False)
    api_key = environment.get("API_KEY") or None

    online_ai_timeout_seconds = float(environment.get("ONLINE_AI_TIMEOUT_SECONDS", "30"))
    raw_temperature = environment.get("ONLINE_AI_TEMPERATURE", "").strip()
    online_ai_temperature = float(raw_temperature) if raw_temperature else None
    online_ai_max_answer_characters = int(
        environment.get("ONLINE_AI_MAX_ANSWER_CHARACTERS", "6000")
    )
    if online_ai_timeout_seconds <= 0:
        raise ValueError("ONLINE_AI_TIMEOUT_SECONDS must be greater than zero")
    if online_ai_temperature is not None and not 0 <= online_ai_temperature <= 2:
        raise ValueError("ONLINE_AI_TEMPERATURE must be inside [0, 2]")
    if online_ai_max_answer_characters < 500:
        raise ValueError("ONLINE_AI_MAX_ANSWER_CHARACTERS must be at least 500")

    ai_primary_provider = environment.get("AI_PRIMARY_PROVIDER", "gemini").strip().lower()
    if ai_primary_provider != "gemini":
        raise ValueError("AI_PRIMARY_PROVIDER must be 'gemini'")

    raw_gemini_api_key = environment.get("GEMINI_API_KEY", "").strip()

    return Settings(
        app_env=environment.get("APP_ENV", "development"),
        log_level=environment.get("LOG_LEVEL", "info"),
        host=environment.get("HOST", "127.0.0.1"),
        port=int(environment.get("PORT", "8000")),
        artifact_dir=artifact_dir,
        api_key_enabled=api_key_enabled,
        api_key=api_key,
        max_upload_mb=int(environment.get("MAX_UPLOAD_MB", "10")),
        knowledge_base_path=knowledge_base_path,
        history_db_path=history_db_path,
        thumbnail_dir=thumbnail_dir,
        thumbnail_max_dimension=thumbnail_max_dimension,
        history_page_size=history_page_size,
        history_busy_timeout_ms=history_busy_timeout_ms,
        online_ai_enabled=_env_bool(environment, "ONLINE_AI_ENABLED", False),
        ai_primary_provider=ai_primary_provider,
        gemini_api_key=SecretStr(raw_gemini_api_key) if raw_gemini_api_key else None,
        gemini_model=environment.get("GEMINI_MODEL", "gemini-3.5-flash").strip(),
        online_ai_timeout_seconds=online_ai_timeout_seconds,
        online_ai_temperature=online_ai_temperature,
        online_ai_max_answer_characters=online_ai_max_answer_characters,
        ai_offline_fallback_enabled=_env_bool(
            environment,
            "AI_OFFLINE_FALLBACK_ENABLED",
            True,
        ),
    )


def get_settings() -> Settings:
    """Compatibility alias cho import gate và scripts kiểm chứng."""

    return load_settings()
