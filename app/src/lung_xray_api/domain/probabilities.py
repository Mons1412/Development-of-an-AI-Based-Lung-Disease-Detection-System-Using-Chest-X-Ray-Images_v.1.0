"""One probability contract for inference, persistence, UI, and reports."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Final, Literal, cast

from lung_xray_api.core.exceptions import ModelRuntimeError

ClassLabel = Literal["normal", "pneumonia", "tuberculosis"]
CLASS_ORDER: Final[tuple[ClassLabel, ...]] = (
    "normal",
    "pneumonia",
    "tuberculosis",
)
PROBABILITY_SUM_TOLERANCE: Final[float] = 1e-4


def normalize_probabilities(
    probabilities: Mapping[str, float],
) -> dict[ClassLabel, float]:
    """Validate and normalize a three-class distribution.

    Normalization happens after the raw model output is accepted so every
    downstream layer persists and renders exactly the same distribution.
    """

    if set(probabilities) != set(CLASS_ORDER):
        raise ModelRuntimeError(
            "Probability output must contain normal, pneumonia and tuberculosis"
        )

    values: dict[ClassLabel, float] = {}
    for label in CLASS_ORDER:
        raw_value = probabilities[label]
        if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
            raise ModelRuntimeError("Probability output must be numeric")
        value = float(raw_value)
        if not math.isfinite(value):
            raise ModelRuntimeError("Probability output must be finite")
        if value < 0.0 or value > 1.0:
            raise ModelRuntimeError("Probability output must stay inside [0, 1]")
        values[label] = value

    total = math.fsum(values.values())
    if total <= 0.0 or not math.isclose(
        total,
        1.0,
        rel_tol=0.0,
        abs_tol=PROBABILITY_SUM_TOLERANCE,
    ):
        raise ModelRuntimeError("Probability output must sum to one")

    normalized = {label: values[label] / total for label in CLASS_ORDER}
    # Force the final component to absorb binary floating-point drift.
    first_two = math.fsum(normalized[label] for label in CLASS_ORDER[:-1])
    normalized[CLASS_ORDER[-1]] = max(0.0, min(1.0, 1.0 - first_two))
    return cast(dict[ClassLabel, float], normalized)


def predicted_label(probabilities: Mapping[ClassLabel, float]) -> ClassLabel:
    """Return the first class in stable class order when probabilities tie."""

    return max(CLASS_ORDER, key=probabilities.__getitem__)
