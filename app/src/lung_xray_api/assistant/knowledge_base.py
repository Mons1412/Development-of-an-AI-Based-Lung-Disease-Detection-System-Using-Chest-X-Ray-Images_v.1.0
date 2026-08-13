"""Load only the reviewed production Knowledge Base runtime index."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PRODUCTION_FILENAME = "knowledge_base.production.vi.json"
SUPPORTED_STAGES = frozenset(
    {"before_analysis", "analysis_running", "after_analysis", "analysis_failed"}
)
PUBLISHED_STATUSES = frozenset({"published", "published_internal"})


class KnowledgeBaseError(RuntimeError):
    """Raised when the production runtime index is unavailable or unsafe to use."""


@dataclass(frozen=True)
class KnowledgeItem:
    """Approved runtime item exposed to deterministic retrieval only."""

    id: str
    title: str
    domain: str
    intent: str
    stages: tuple[str, ...]
    sample_questions: tuple[str, ...]
    answer_short: str
    answer_detailed: str
    source_ids: tuple[str, ...]


class KnowledgeBase:
    """Immutable in-memory index built from the production JSON file only."""

    def __init__(self, items: tuple[KnowledgeItem, ...], version: str) -> None:
        self.items = items
        self.version = version
        self.by_intent = {item.intent: item for item in items}
        self.by_id = {item.id: item for item in items}

    @classmethod
    def load(cls, path: Path) -> "KnowledgeBase":
        resolved_path = path.resolve()
        if resolved_path.name != PRODUCTION_FILENAME:
            raise KnowledgeBaseError(
                f"Assistant chỉ chấp nhận {PRODUCTION_FILENAME}, không dùng development Knowledge Base"
            )
        if not resolved_path.is_file():
            raise KnowledgeBaseError(f"Không tìm thấy production Knowledge Base: {resolved_path}")

        try:
            payload = json.loads(resolved_path.read_text(encoding="utf-8"))
        except OSError as error:
            raise KnowledgeBaseError(f"Không đọc được production Knowledge Base: {resolved_path}") from error
        except json.JSONDecodeError as error:
            raise KnowledgeBaseError(f"Production Knowledge Base không phải JSON hợp lệ: {resolved_path}") from error

        if not isinstance(payload, dict) or payload.get("mode") != "production":
            raise KnowledgeBaseError("Knowledge Base runtime phải có mode=production")

        raw_items = payload.get("items")
        if not isinstance(raw_items, list) or not raw_items:
            raise KnowledgeBaseError("Production Knowledge Base không có item hợp lệ")
        if payload.get("item_count") != len(raw_items):
            raise KnowledgeBaseError("item_count không khớp số item trong production Knowledge Base")

        items = tuple(cls._parse_item(raw_item) for raw_item in raw_items)
        if len({item.id for item in items}) != len(items):
            raise KnowledgeBaseError("Production Knowledge Base có item ID trùng lặp")
        if len({item.intent for item in items}) != len(items):
            raise KnowledgeBaseError("Production Knowledge Base có intent trùng lặp")

        source_status_by_id = cls._parse_source_registry(payload.get("sources"))
        for item in items:
            for source_id in item.source_ids:
                source_status = source_status_by_id.get(source_id)
                if source_status is None:
                    raise KnowledgeBaseError(
                        f"Knowledge Base item {item.id} tham chiếu source ID không tồn tại: {source_id}"
                    )
                if source_status == "deprecated":
                    raise KnowledgeBaseError(
                        f"Knowledge Base item {item.id} tham chiếu source đã deprecated: {source_id}"
                    )

        version = payload.get("knowledge_base_version")
        if not isinstance(version, str) or not version.strip():
            raise KnowledgeBaseError("Production Knowledge Base thiếu knowledge_base_version")
        return cls(items=items, version=version)

    @staticmethod
    def _parse_item(raw_item: Any) -> KnowledgeItem:
        if not isinstance(raw_item, dict):
            raise KnowledgeBaseError("Mỗi Knowledge Base item phải là object")

        publication_status = raw_item.get("publication_status")
        if publication_status not in PUBLISHED_STATUSES:
            raise KnowledgeBaseError("Production Knowledge Base chứa item chưa publish")
        if raw_item.get("clinical_review_required") or raw_item.get("clinical_review_status") in {
            "pending",
            "pending_clinical_review",
        }:
            raise KnowledgeBaseError("Production Knowledge Base không được chứa item cần clinical review")

        required_strings = ("id", "title", "domain", "intent", "answer_short", "answer_detailed")
        values: dict[str, str] = {}
        for key in required_strings:
            value = raw_item.get(key)
            if not isinstance(value, str) or not value.strip():
                raise KnowledgeBaseError(f"Knowledge Base item thiếu trường text hợp lệ: {key}")
            values[key] = value.strip()

        stages = KnowledgeBase._string_tuple(raw_item.get("stages"), "stages")
        if not set(stages).issubset(SUPPORTED_STAGES):
            raise KnowledgeBaseError(f"Knowledge Base item có application stage không hỗ trợ: {stages}")

        return KnowledgeItem(
            id=values["id"],
            title=values["title"],
            domain=values["domain"],
            intent=values["intent"],
            stages=stages,
            sample_questions=KnowledgeBase._string_tuple(
                raw_item.get("sample_questions"), "sample_questions"
            ),
            answer_short=values["answer_short"],
            answer_detailed=values["answer_detailed"],
            source_ids=KnowledgeBase._string_tuple(raw_item.get("source_ids"), "source_ids"),
        )

    @staticmethod
    def _parse_source_registry(raw_sources: Any) -> dict[str, str]:
        if not isinstance(raw_sources, list) or not raw_sources:
            raise KnowledgeBaseError("Production Knowledge Base không có source registry hợp lệ")

        source_status_by_id: dict[str, str] = {}
        for raw_source in raw_sources:
            if not isinstance(raw_source, dict):
                raise KnowledgeBaseError("Mỗi source registry entry phải là object")
            source_id = raw_source.get("source_id")
            status = raw_source.get("status")
            if not isinstance(source_id, str) or not source_id.strip():
                raise KnowledgeBaseError("Source registry thiếu source_id hợp lệ")
            if not isinstance(status, str) or not status.strip():
                raise KnowledgeBaseError(f"Source registry thiếu status hợp lệ: {source_id}")
            normalized_source_id = source_id.strip()
            if normalized_source_id in source_status_by_id:
                raise KnowledgeBaseError(f"Source registry có source_id trùng lặp: {normalized_source_id}")
            source_status_by_id[normalized_source_id] = status.strip()
        return source_status_by_id

    @staticmethod
    def _string_tuple(value: Any, field_name: str) -> tuple[str, ...]:
        if not isinstance(value, list) or not value or not all(
            isinstance(item, str) and item.strip() for item in value
        ):
            raise KnowledgeBaseError(f"Knowledge Base item thiếu danh sách {field_name} hợp lệ")
        return tuple(item.strip() for item in value)
