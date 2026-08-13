"""Application-stage checks for untrusted prediction context supplied by a client."""

from __future__ import annotations

from dataclasses import dataclass

from lung_xray_api.schemas.assistant import ApplicationStage, PredictionContext


@dataclass(frozen=True)
class StateDecision:
    """The effective context for the request, or a controlled response intent."""

    context: PredictionContext | None
    forced_intent: str | None = None


class StateValidator:
    """Prevent stale or absent context from being used as a current prediction."""

    def validate(
        self,
        application_stage: ApplicationStage,
        prediction_context: PredictionContext | None,
    ) -> StateDecision:
        if application_stage == "after_analysis":
            if prediction_context is None:
                return StateDecision(context=None, forced_intent="no_prediction")
            return StateDecision(context=prediction_context)

        # Any context before a completed analysis is intentionally ignored so a stale
        # client payload cannot be presented as the result of the current image.
        return StateDecision(context=None)

