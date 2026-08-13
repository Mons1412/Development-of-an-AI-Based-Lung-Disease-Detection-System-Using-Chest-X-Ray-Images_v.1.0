"""Versioned asset URLs for the offline Jinja2 demo."""

from __future__ import annotations

from pathlib import PurePosixPath


FRONTEND_ASSET_VERSION = "20260728.6"
FRONTEND_STATIC_BASE = f"/static/v/{FRONTEND_ASSET_VERSION}"


def frontend_asset_url(relative_path: str) -> str:
    """Return a versioned static URL for a known template asset path."""

    path = PurePosixPath(relative_path.lstrip("/"))
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("frontend asset path must stay inside the static directory")
    return f"{FRONTEND_STATIC_BASE}/{path.as_posix()}"
