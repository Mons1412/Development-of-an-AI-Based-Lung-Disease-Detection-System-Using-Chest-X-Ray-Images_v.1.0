"""Offline assistant resolution and rendering over the production Knowledge Base."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from lung_xray_api.assistant.intent_router import IntentRouter
from lung_xray_api.assistant.knowledge_base import KnowledgeBase, KnowledgeBaseError, KnowledgeItem
from lung_xray_api.assistant.response_renderer import ResponseRenderer
from lung_xray_api.assistant.retriever import TfidfRetriever, normalize_text
from lung_xray_api.assistant.safety_guard import SafetyGuard
from lung_xray_api.assistant.state_validator import StateValidator
from lung_xray_api.core.config import Settings
from lung_xray_api.schemas.assistant import AssistantAnswer, AssistantQuery, PredictionContext

HIGH_SCORE = 0.18
MEDIUM_SCORE = 0.08

ResolutionOutcome = Literal[
    "knowledge",
    "prediction",
    "conversational",
    "safety_refusal",
    "needs_prediction",
    "out_of_scope",
    "clarification",
]


@dataclass(frozen=True, slots=True)
class AssistantResolution:
    """One authoritative intent/context/retrieval decision for online and offline."""

    normalized_message: str
    application_stage: str
    intent: str
    outcome: ResolutionOutcome
    prediction_context: PredictionContext | None = None
    knowledge_items: tuple[KnowledgeItem, ...] = ()
    confidence: float = 1.0
    clarification_suggestions: tuple[str, ...] = ()

    @property
    def source_ids(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                source_id
                for item in self.knowledge_items
                for source_id in item.source_ids
            )
        )

    @property
    def suggested_questions(self) -> tuple[str, ...]:
        if self.clarification_suggestions:
            return self.clarification_suggestions[:3]
        return tuple(
            dict.fromkeys(
                question
                for item in self.knowledge_items
                for question in item.sample_questions
            )
        )[:3]

    @property
    def online_eligible(self) -> bool:
        return self.outcome in {"knowledge", "prediction"}


class AssistantService:
    """Stable local assistant backed solely by the production Knowledge Base."""

    def __init__(self, knowledge_base: KnowledgeBase) -> None:
        self.knowledge_base = knowledge_base
        self._intent_router = IntentRouter()
        self._retriever = TfidfRetriever(knowledge_base)
        self._renderer = ResponseRenderer()
        self._safety_guard = SafetyGuard()
        self._state_validator = StateValidator()

    @classmethod
    def from_path(cls, knowledge_base_path: Path) -> "AssistantService":
        return cls(KnowledgeBase.load(knowledge_base_path))

    @classmethod
    def from_settings(cls, settings: Settings) -> "AssistantService":
        if settings.knowledge_base_path is None:
            raise KnowledgeBaseError("Thiếu đường dẫn production Knowledge Base")
        return cls.from_path(settings.knowledge_base_path)

    def resolve(self, query: AssistantQuery) -> AssistantResolution:
        """Normalize, validate, guard, route and retrieve exactly once."""

        normalized_message = normalize_text(query.message)
        state = self._state_validator.validate(
            query.application_stage,
            query.prediction_context,
        )
        guard = self._safety_guard.evaluate(query.message, query.application_stage)

        if guard.intent in {
            "dosage_request",
            "medication_request",
            "treatment_change_request",
            "definitive_diagnosis_request",
            "guaranteed_interpretation",
            "emergency_symptoms",
            "insufficient_information",
            "unavailable_patient_data",
        }:
            return AssistantResolution(
                normalized_message,
                query.application_stage,
                guard.intent,
                "safety_refusal",
                prediction_context=state.context,
            )
        if guard.intent == "unsupported_disease":
            return AssistantResolution(
                normalized_message,
                query.application_stage,
                guard.intent,
                "out_of_scope",
                prediction_context=state.context,
            )
        if guard.intent == "no_prediction" or state.forced_intent == "no_prediction":
            return self._needs_prediction(normalized_message, query.application_stage)
        if query.application_stage in {"analysis_running", "analysis_failed"}:
            return self._needs_prediction(normalized_message, query.application_stage)

        routed_intent = self._intent_router.route(
            query.message,
            query.application_stage,
            has_prediction=state.context is not None,
        )
        if routed_intent in {
            "greeting",
            "thanks",
            "goodbye",
            "help",
            "capabilities",
            "start_over",
        }:
            return AssistantResolution(
                normalized_message,
                query.application_stage,
                routed_intent,
                "conversational",
                prediction_context=state.context,
            )
        if routed_intent == "explain_current_prediction":
            if state.context is None:
                return self._needs_prediction(normalized_message, query.application_stage)
            source_item = self.knowledge_base.by_intent.get("output_classes")
            return AssistantResolution(
                normalized_message,
                query.application_stage,
                routed_intent,
                "prediction",
                prediction_context=state.context,
                knowledge_items=(source_item,) if source_item is not None else (),
            )
        if routed_intent in {"disease_information", "privacy_storage", "model_limitations"}:
            return AssistantResolution(
                normalized_message,
                query.application_stage,
                routed_intent,
                "out_of_scope",
                prediction_context=state.context,
            )
        if routed_intent is not None:
            item = self.knowledge_base.by_intent.get(routed_intent)
            if item is not None and query.application_stage in item.stages:
                return AssistantResolution(
                    normalized_message,
                    query.application_stage,
                    routed_intent,
                    "knowledge",
                    prediction_context=state.context,
                    knowledge_items=(item,),
                )

        results = self._retriever.search(query.message, query.application_stage)
        if not results:
            return AssistantResolution(
                normalized_message,
                query.application_stage,
                "out_of_scope",
                "out_of_scope",
                prediction_context=state.context,
                confidence=0.0,
            )

        best = results[0]
        if best.score >= HIGH_SCORE:
            return AssistantResolution(
                normalized_message,
                query.application_stage,
                best.item.intent,
                "knowledge",
                prediction_context=state.context,
                knowledge_items=(best.item,),
                confidence=best.score,
            )
        if best.score >= MEDIUM_SCORE:
            suggestions = tuple(
                dict.fromkeys(
                    question
                    for result in results
                    for question in result.item.sample_questions
                )
            )
            return AssistantResolution(
                normalized_message,
                query.application_stage,
                "needs_clarification",
                "clarification",
                prediction_context=state.context,
                knowledge_items=tuple(result.item for result in results),
                confidence=best.score,
                clarification_suggestions=suggestions,
            )
        return AssistantResolution(
            normalized_message,
            query.application_stage,
            "out_of_scope",
            "out_of_scope",
            prediction_context=state.context,
            confidence=best.score,
        )

    def render(self, resolution: AssistantResolution) -> AssistantAnswer:
        """Render one resolution without re-running intent or retrieval."""

        if resolution.outcome == "safety_refusal":
            return self._renderer.safety_refusal(resolution.intent)
        if resolution.outcome == "needs_prediction":
            item = resolution.knowledge_items[0] if resolution.knowledge_items else None
            return self._renderer.needs_prediction(item)
        if resolution.outcome == "conversational":
            return self._renderer.conversational(resolution.intent)
        if resolution.outcome == "prediction" and resolution.prediction_context is not None:
            item = resolution.knowledge_items[0] if resolution.knowledge_items else None
            return self._renderer.prediction_explanation(
                resolution.prediction_context,
                item,
            )
        if resolution.outcome == "knowledge" and resolution.knowledge_items:
            return self._renderer.from_item(
                resolution.knowledge_items[0],
                confidence=resolution.confidence,
            )
        if resolution.outcome == "clarification":
            return self._renderer.clarification(
                list(resolution.clarification_suggestions),
                confidence=resolution.confidence,
            )
        return self._renderer.out_of_scope(
            resolution.intent,
            confidence=resolution.confidence,
        )

    def answer(self, query: AssistantQuery) -> AssistantAnswer:
        return self.render(self.resolve(query))

    def _needs_prediction(
        self,
        normalized_message: str,
        application_stage: str,
    ) -> AssistantResolution:
        item = self.knowledge_base.by_intent.get("no_prediction")
        return AssistantResolution(
            normalized_message,
            application_stage,
            "no_prediction",
            "needs_prediction",
            knowledge_items=(item,) if item is not None else (),
        )
