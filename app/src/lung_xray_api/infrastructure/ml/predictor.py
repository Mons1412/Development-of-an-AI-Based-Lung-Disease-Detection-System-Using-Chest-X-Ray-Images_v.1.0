"""Validate and map model output to the public prediction contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from lung_xray_api.core.exceptions import ModelRuntimeError
from lung_xray_api.domain.probabilities import (
    CLASS_ORDER,
    PROBABILITY_SUM_TOLERANCE,
    normalize_probabilities,
)
from lung_xray_api.infrastructure.ml.artifact_bundle import ArtifactBundle


@dataclass(frozen=True)
class PredictionOutput:
    prediction: str
    model_probability: float
    probabilities: dict[str, float]


class ModelRuntimeProtocol(Protocol):
    def predict_batch(self, batch: np.ndarray) -> np.ndarray:
        ...


class Predictor:
    def __init__(
        self,
        bundle: ArtifactBundle,
        runtime: ModelRuntimeProtocol,
        sum_tolerance: float = PROBABILITY_SUM_TOLERANCE,
    ) -> None:
        if not np.isclose(sum_tolerance, PROBABILITY_SUM_TOLERANCE):
            raise ValueError("Predictor must use the shared probability tolerance")
        self.bundle = bundle
        self.runtime = runtime

    def predict(self, batch: np.ndarray) -> PredictionOutput:
        if tuple(self.bundle.class_names) != CLASS_ORDER:
            raise ModelRuntimeError("Artifact class order does not match the API contract")

        output = self.runtime.predict_batch(batch)
        raw_label, probabilities = self._validate_output(output)
        return PredictionOutput(
            prediction=raw_label,
            model_probability=probabilities[raw_label],
            probabilities=dict(probabilities),
        )

    @staticmethod
    def _validate_output(output: np.ndarray) -> tuple[str, dict[str, float]]:
        if output.shape != (1, 3):
            raise ModelRuntimeError(f"Output shape sai: {output.shape}")

        raw_values = np.asarray(output[0], dtype=np.float64)
        # Preserve Phase 1 inference parity: the public class is selected from
        # the raw model vector before any floating-point normalization used for
        # storage and display. np.argmax also preserves the original first-class
        # tie behavior.
        raw_class_index = int(np.argmax(raw_values))
        raw_label = CLASS_ORDER[raw_class_index]
        raw_probabilities = {
            label: float(raw_values[index])
            for index, label in enumerate(CLASS_ORDER)
        }
        normalized = normalize_probabilities(raw_probabilities)
        return str(raw_label), {
            str(label): probability
            for label, probability in normalized.items()
        }
