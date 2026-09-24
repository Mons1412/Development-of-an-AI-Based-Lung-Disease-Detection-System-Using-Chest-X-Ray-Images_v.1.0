from types import SimpleNamespace

import pytest

from lung_xray_api.application.services.drai_context_builder import (
    DrAIContextBuilder,
)


def test_rejects_analysis_patient_mismatch():
    builder = DrAIContextBuilder()

    analysis = SimpleNamespace(
        patient_id=100,
    )

    patient = SimpleNamespace(
        id=200,
    )

    with pytest.raises(
        ValueError,
        match=(
            "Analysis does not belong "
            "to patient"
        ),
    ):
        builder.build(
            object(),
            analysis=analysis,
            patient=patient,
        )
