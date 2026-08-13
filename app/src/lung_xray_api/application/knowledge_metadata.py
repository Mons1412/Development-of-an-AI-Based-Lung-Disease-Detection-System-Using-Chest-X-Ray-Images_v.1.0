"""Read optional production Knowledge Base metadata without assistant coupling."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class KnowledgeMetadata:
    version: str | None
    source_titles: dict[str, str]


class KnowledgeMetadataProvider:
    """Best-effort metadata provider for analysis provenance.

    Prediction and persistence remain available when the optional assistant or
    Knowledge Base cannot be loaded.
    """

    def __init__(self, production_path: Path | None) -> None:
        self._production_path = production_path

    def load(self) -> KnowledgeMetadata:
        path = self._production_path
        if path is None or not path.is_file():
            return KnowledgeMetadata(version=None, source_titles={})
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return KnowledgeMetadata(version=None, source_titles={})
        if not isinstance(payload, dict) or payload.get("mode") != "production":
            return KnowledgeMetadata(version=None, source_titles={})

        version = payload.get("knowledge_base_version")
        safe_version = version.strip() if isinstance(version, str) and version.strip() else None
        source_titles: dict[str, str] = {}
        raw_sources = payload.get("sources")
        if isinstance(raw_sources, list):
            for source in raw_sources:
                if not isinstance(source, dict):
                    continue
                source_id = source.get("source_id")
                title = source.get("title")
                status = source.get("status")
                if (
                    isinstance(source_id, str)
                    and source_id.strip()
                    and isinstance(title, str)
                    and title.strip()
                    and status != "deprecated"
                ):
                    source_titles[source_id.strip()] = title.strip()
        return KnowledgeMetadata(version=safe_version, source_titles=source_titles)
