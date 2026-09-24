from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from lung_xray_api.application.services.drai_context_builder import (
    DrAIContextBuilder,
)


class StubHistoryRepository:

    def __init__(
        self,
        histories,
    ):
        self.histories = histories
        self.patient_ids = []

    def list_by_patient_id(
        self,
        db,
        patient_id,
    ):
        self.patient_ids.append(
            patient_id
        )

        return list(
            self.histories
        )


def make_history(
    index: int,
):
    return SimpleNamespace(
        recorded_at=datetime(
            2026,
            9,
            min(index + 1, 28),
            12,
            0,
            0,
        ),
        diseases=[
            " asthma ",
            "",
        ],
        medications=[
            "medicine-a",
        ],
        allergies=None,
        smoking_status=" never ",
        alcohol_status=None,
        occupational_exposure=(
            " dust "
        ),
        notes=" stable ",
    )


def make_patient():
    return SimpleNamespace(
        id=77,
        user_id=123,
        patient_code="PXSECRET",
        full_name="Private Name",
        birth_year=2004,
        gender=" male ",
        phone="0900000000",
        address="Private Address",
    )


def make_analysis(
    *,
    status="COMPLETED",
    include_prediction=True,
    include_probabilities=True,
):
    model = SimpleNamespace(
        model_key="mobilenetv2",
        display_name="MobileNetV2",
        architecture="MobileNetV2",
        version="1.1.0",
    )

    probabilities = []

    if include_probabilities:
        probabilities = [
            SimpleNamespace(
                class_name="tuberculosis",
                probability=Decimal(
                    "0.0500000"
                ),
            ),
            SimpleNamespace(
                class_name="normal",
                probability=Decimal(
                    "0.1500000"
                ),
            ),
            SimpleNamespace(
                class_name="pneumonia",
                probability=Decimal(
                    "0.8000000"
                ),
            ),
        ]

    prediction = None

    if include_prediction:
        prediction = SimpleNamespace(
            predicted_class="pneumonia",
            confidence=Decimal(
                "0.8000000"
            ),
            probabilities=probabilities,
        )

    return SimpleNamespace(
        patient_id=77,
        status=status,
        ai_model=model,
        prediction=prediction,
    )


def test_builds_trusted_context_without_direct_pii():
    repository = StubHistoryRepository(
        [
            make_history(1),
        ]
    )

    builder = DrAIContextBuilder(
        repository
    )

    context = builder.build(
        object(),
        analysis=make_analysis(),
        patient=make_patient(),
    )

    assert repository.patient_ids == [
        77
    ]

    assert context.patient.birth_year == 2004
    assert context.patient.gender == "male"

    assert not hasattr(
        context.patient,
        "full_name",
    )

    assert not hasattr(
        context.patient,
        "patient_code",
    )

    assert not hasattr(
        context.patient,
        "phone",
    )

    assert not hasattr(
        context.patient,
        "address",
    )

    assert context.model.model_key == (
        "mobilenetv2"
    )

    assert (
        context.prediction.predicted_class
        == "pneumonia"
    )

    assert context.prediction.confidence == (
        0.8
    )

    assert [
        item.class_name
        for item
        in context.prediction.probabilities
    ] == [
        "normal",
        "pneumonia",
        "tuberculosis",
    ]

    history = context.medical_histories[0]

    assert history.diseases == (
        "asthma",
    )

    assert history.allergies == ()
    assert history.smoking_status == "never"
    assert history.occupational_exposure == (
        "dust"
    )
    assert history.notes == "stable"


def test_limits_medical_history_records():
    repository = StubHistoryRepository(
        [
            make_history(index)
            for index in range(12)
        ]
    )

    builder = DrAIContextBuilder(
        repository,
        max_history_records=10,
    )

    context = builder.build(
        object(),
        analysis=make_analysis(),
        patient=make_patient(),
    )

    assert len(
        context.medical_histories
    ) == 10


def test_rejects_non_completed_analysis():
    builder = DrAIContextBuilder(
        StubHistoryRepository([])
    )

    with pytest.raises(
        ValueError,
        match="completed analysis",
    ):
        builder.build(
            object(),
            analysis=make_analysis(
                status="FAILED"
            ),
            patient=make_patient(),
        )


def test_rejects_missing_prediction():
    builder = DrAIContextBuilder(
        StubHistoryRepository([])
    )

    with pytest.raises(
        ValueError,
        match="Prediction is missing",
    ):
        builder.build(
            object(),
            analysis=make_analysis(
                include_prediction=False
            ),
            patient=make_patient(),
        )


def test_rejects_missing_probabilities():
    builder = DrAIContextBuilder(
        StubHistoryRepository([])
    )

    with pytest.raises(
        ValueError,
        match=(
            "Prediction probabilities "
            "are missing"
        ),
    ):
        builder.build(
            object(),
            analysis=make_analysis(
                include_probabilities=False
            ),
            patient=make_patient(),
        )


def test_includes_anthropometrics_and_new_clinical_history_fields():
    from datetime import date
    from dataclasses import asdict
    patient = make_patient()
    patient.date_of_birth = date(2004, 12, 31)
    patient.weight_kg = Decimal("65.5")
    patient.height_cm = Decimal("170.0")
    history = make_history(1)
    history.current_complaint_hpi = "Ho kéo dài"
    history.allergy_history = "Vỏ tôm"
    history.appetite = "Chán ăn"
    history.sleep = "Khó ngủ"
    context = DrAIContextBuilder(StubHistoryRepository([history])).build(
        object(), analysis=make_analysis(), patient=patient)
    today = date.today()
    assert context.patient.age == today.year - 2004 - ((today.month, today.day) < (12, 31))
    assert context.patient.weight_kg == 65.5
    assert context.patient.height_cm == 170.0
    latest = asdict(context.medical_histories[0])
    assert latest["current_complaint_hpi"] == "Ho kéo dài"
    assert latest["allergy_history"] == "Vỏ tôm"
    assert latest["appetite"] == "Chán ăn"
    assert latest["sleep"] == "Khó ngủ"
    assert context.report_metadata.patient_code == "PXSECRET"
