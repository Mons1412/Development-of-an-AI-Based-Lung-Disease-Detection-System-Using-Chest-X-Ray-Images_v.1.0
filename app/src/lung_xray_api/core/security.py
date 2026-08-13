"""Security helpers cho API key local.

API key chỉ kiểm soát truy cập local, không liên quan chất lượng AI. Khi bật,
so sánh dùng `secrets.compare_digest` để tránh timing leak đơn giản và không
log giá trị key.
"""

from __future__ import annotations

import secrets

from lung_xray_api.core.config import Settings


def is_authorized(settings: Settings, provided_key: str | None) -> bool:
    if not settings.api_key_enabled:
        return True
    if not settings.api_key:
        return False
    if provided_key is None:
        return False
    return secrets.compare_digest(provided_key, settings.api_key)
