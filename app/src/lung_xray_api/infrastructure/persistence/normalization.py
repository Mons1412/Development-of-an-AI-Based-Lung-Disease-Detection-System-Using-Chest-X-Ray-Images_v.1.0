"""Stable Unicode search normalization for local patient history."""

from __future__ import annotations

import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")


def normalize_search_key(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = unicodedata.normalize("NFKD", value).casefold().replace("đ", "d")
    without_marks = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    compact = _WHITESPACE.sub(" ", without_marks).strip()
    return compact or None
