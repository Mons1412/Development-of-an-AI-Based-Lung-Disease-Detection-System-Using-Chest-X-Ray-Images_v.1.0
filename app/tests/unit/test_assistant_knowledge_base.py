import json
from pathlib import Path

import pytest

from lung_xray_api.assistant.knowledge_base import KnowledgeBase, KnowledgeBaseError


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_PATH = PROJECT_ROOT / "knowledge_base" / "compiled" / "knowledge_base.production.vi.json"


def test_knowledge_base_loads_only_published_production_items():
    knowledge_base = KnowledgeBase.load(PRODUCTION_PATH)

    assert knowledge_base.version == "1.0.0"
    assert len(knowledge_base.items) == 21
    assert knowledge_base.by_intent["supported_formats"].id == "product.supported_formats"
    assert all(item.domain != "clinical" for item in knowledge_base.items)


def test_knowledge_base_rejects_development_filename(tmp_path: Path):
    development_path = tmp_path / "knowledge_base.development.vi.json"
    development_path.write_text("{}", encoding="utf-8")

    with pytest.raises(KnowledgeBaseError, match="production"):
        KnowledgeBase.load(development_path)


def test_knowledge_base_rejects_pending_item_even_with_production_filename(tmp_path: Path):
    production_path = tmp_path / "knowledge_base.production.vi.json"
    production_path.write_text(
        json.dumps(
            {
                "mode": "production",
                "knowledge_base_version": "1.0.0",
                "item_count": 1,
                "items": [
                    {
                        "id": "clinical.pending",
                        "title": "Pending",
                        "domain": "clinical",
                        "intent": "pending",
                        "stages": ["before_analysis"],
                        "publication_status": "published_internal",
                        "clinical_review_required": True,
                        "clinical_review_status": "pending",
                        "sample_questions": ["Question"],
                        "answer_short": "Short answer",
                        "answer_detailed": "Detailed answer",
                        "source_ids": ["SOURCE_1"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(KnowledgeBaseError, match="clinical review"):
        KnowledgeBase.load(production_path)
