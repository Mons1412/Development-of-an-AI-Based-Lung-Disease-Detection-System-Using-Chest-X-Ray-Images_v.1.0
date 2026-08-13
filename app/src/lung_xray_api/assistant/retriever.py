"""Dependency-free Vietnamese-friendly TF-IDF retrieval for approved KB items."""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

from lung_xray_api.assistant.knowledge_base import KnowledgeBase, KnowledgeItem

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_STOP_WORDS = frozenset(
    {
        "anh",
        "ban",
        "cho",
        "co",
        "cua",
        "duoc",
        "gi",
        "hay",
        "hom",
        "khong",
        "la",
        "mot",
        "nao",
        "nay",
        "nhu",
        "sao",
        "the",
        "thoi",
        "tiet",
        "toi",
        "va",
        "voi",
    }
)


def normalize_text(text: str) -> str:
    """Normalize Vietnamese text for local matching without any network dependency."""

    normalized = unicodedata.normalize("NFKD", text.lower()).replace("đ", "d")
    without_marks = "".join(char for char in normalized if not unicodedata.combining(char))
    return " ".join(_TOKEN_PATTERN.findall(without_marks))


def tokenize(text: str) -> list[str]:
    return [token for token in normalize_text(text).split() if len(token) > 1 and token not in _STOP_WORDS]


@dataclass(frozen=True)
class RetrievalResult:
    item: KnowledgeItem
    score: float


class TfidfRetriever:
    """Small deterministic cosine-similarity retriever over approved KB text."""

    def __init__(self, knowledge_base: KnowledgeBase) -> None:
        self._knowledge_base = knowledge_base
        document_tokens = [tokenize(self._item_text(item)) for item in knowledge_base.items]
        self._document_frequency: Counter[str] = Counter()
        for tokens in document_tokens:
            self._document_frequency.update(set(tokens))
        self._document_count = max(len(document_tokens), 1)
        self._vectors = [self._vector(tokens) for tokens in document_tokens]

    @staticmethod
    def _item_text(item: KnowledgeItem) -> str:
        return " ".join(
            [item.title, item.intent, *item.sample_questions, item.answer_short, item.answer_detailed]
        )

    def _vector(self, tokens: list[str]) -> dict[str, float]:
        counts = Counter(tokens)
        if not counts:
            return {}
        values = {
            token: (1.0 + math.log(count))
            * (math.log((1.0 + self._document_count) / (1.0 + self._document_frequency[token])) + 1.0)
            for token, count in counts.items()
        }
        magnitude = math.sqrt(sum(value * value for value in values.values()))
        return {token: value / magnitude for token, value in values.items()} if magnitude else {}

    @staticmethod
    def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
        if len(left) > len(right):
            left, right = right, left
        return sum(value * right.get(token, 0.0) for token, value in left.items())

    def search(self, query: str, application_stage: str, top_k: int = 3) -> list[RetrievalResult]:
        query_vector = self._vector(tokenize(query))
        if not query_vector:
            return []
        results = [
            RetrievalResult(item=item, score=self._cosine(query_vector, vector))
            for item, vector in zip(self._knowledge_base.items, self._vectors)
            if application_stage in item.stages
        ]
        return sorted(results, key=lambda result: result.score, reverse=True)[:top_k]
