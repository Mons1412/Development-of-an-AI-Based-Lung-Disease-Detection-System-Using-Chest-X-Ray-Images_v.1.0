from datetime import datetime

from lung_xray_api.application.services.drai_context_builder import (
    DrAIContext,
    DrAIMedicalHistoryContext,
    DrAIModelContext,
    DrAIPatientContext,
    DrAIPredictionContext,
    DrAIProbabilityContext,
    DrAIReportMetadata,
)
from lung_xray_api.infrastructure.ml.local_medical_advice_provider import (
    LocalDeterministicMedicalAdviceProvider,
)


def make_history(
    *,
    hpi="Ho nhẹ 2 ngày, không khó thở.",
    diseases=(),
    medications=(),
    allergies=(),
    allergy_history=None,
):
    return DrAIMedicalHistoryContext(
        recorded_at=datetime(
            2026,
            9,
            22,
            9,
            0,
        ),
        diseases=tuple(diseases),
        medications=tuple(medications),
        allergies=tuple(allergies),
        smoking_status="Không hút thuốc",
        alcohol_status="Không thường xuyên",
        occupational_exposure=None,
        notes=None,
        current_complaint_hpi=hpi,
        past_medical_history=None,
        past_medication_history=None,
        allergy_history=allergy_history,
        diet="Ăn uống bình thường",
        appetite="Bình thường",
        sleep="7 giờ mỗi ngày",
        exercise="Đi bộ nhẹ",
        bowel_bladder=None,
        habits=None,
        family_history=None,
    )


def make_context(
    *,
    predicted_class="normal",
    normal=0.90,
    pneumonia=0.05,
    tuberculosis=0.05,
    history=None,
    include_history=True,
):
    probabilities = (
        DrAIProbabilityContext(
            class_name="normal",
            probability=normal,
        ),
        DrAIProbabilityContext(
            class_name="pneumonia",
            probability=pneumonia,
        ),
        DrAIProbabilityContext(
            class_name="tuberculosis",
            probability=tuberculosis,
        ),
    )

    confidence = max(
        normal,
        pneumonia,
        tuberculosis,
    )

    if include_history:
        histories = (
            history or make_history(),
        )
    else:
        histories = ()

    return DrAIContext(
        patient=DrAIPatientContext(
            birth_year=2004,
            gender="MALE",
            age=22,
            height_cm=174.0,
            weight_kg=62.0,
        ),
        medical_histories=histories,
        model=DrAIModelContext(
            model_key="mobilenet_v2",
            display_name="MobileNetV2",
            architecture="MobileNetV2",
            version="1.1.0",
        ),
        prediction=DrAIPredictionContext(
            predicted_class=predicted_class,
            confidence=confidence,
            probabilities=probabilities,
        ),
        report_metadata=DrAIReportMetadata(
            full_name="Nguyễn Văn A",
            phone="0900000000",
            patient_code="PT0001",
            analysis_code="AN0001",
            original_filename="xray.png",
            input_source="UPLOAD",
            report_code="DRTEST0001",
        ),
    )


def test_low_risk_normal_with_clinical_history():
    provider = (
        LocalDeterministicMedicalAdviceProvider()
    )

    context = make_context(
        predicted_class="normal",
        normal=0.90,
        pneumonia=0.06,
        tuberculosis=0.04,
        history=make_history(
            hpi=(
                "Ho nhẹ 2 ngày, "
                "không khó thở, "
                "không ho ra máu."
            )
        ),
    )

    result = provider.generate(
        context=context,
        language="vi",
    )

    assert result.provider == "local-fallback"
    assert (
        result.model_name
        == "drai-deterministic-v1"
    )
    assert "Risk level: LOW" in result.advice_text
    assert "Normal: 90.00%" in result.advice_text
    assert "62.0 kg" in result.advice_text
    assert "174.0 cm" in result.advice_text


def test_medium_risk_when_normal_confidence_is_insufficient():
    provider = (
        LocalDeterministicMedicalAdviceProvider()
    )

    context = make_context(
        predicted_class="normal",
        normal=0.65,
        pneumonia=0.25,
        tuberculosis=0.10,
    )

    result = provider.generate(
        context=context,
        language="vi",
    )

    assert (
        "Risk level: MEDIUM"
        in result.advice_text
    )


def test_high_risk_for_high_confidence_abnormal_prediction():
    provider = (
        LocalDeterministicMedicalAdviceProvider()
    )

    context = make_context(
        predicted_class="pneumonia",
        normal=0.10,
        pneumonia=0.82,
        tuberculosis=0.08,
    )

    result = provider.generate(
        context=context,
        language="vi",
    )

    assert "Risk level: HIGH" in result.advice_text
    assert (
        "Pneumonia: 82.00%"
        in result.advice_text
    )


def test_red_flag_symptom_escalates_to_high_risk():
    provider = (
        LocalDeterministicMedicalAdviceProvider()
    )

    context = make_context(
        predicted_class="normal",
        normal=0.91,
        pneumonia=0.05,
        tuberculosis=0.04,
        history=make_history(
            hpi=(
                "Bệnh nhân khó thở tăng nhanh "
                "trong vài giờ gần đây."
            )
        ),
    )

    result = provider.generate(
        context=context,
        language="vi",
    )

    assert "Risk level: HIGH" in result.advice_text


def test_negated_red_flags_do_not_escalate_low_risk():
    provider = (
        LocalDeterministicMedicalAdviceProvider()
    )

    context = make_context(
        predicted_class="normal",
        normal=0.92,
        pneumonia=0.05,
        tuberculosis=0.03,
        history=make_history(
            hpi=(
                "Ho nhẹ. "
                "Không khó thở. "
                "Không ghi nhận ho ra máu."
            )
        ),
    )

    result = provider.generate(
        context=context,
        language="vi",
    )

    assert "Risk level: LOW" in result.advice_text


def test_allergy_and_existing_medication_are_preserved():
    provider = (
        LocalDeterministicMedicalAdviceProvider()
    )

    context = make_context(
        history=make_history(
            allergies=(
                "Penicillin",
            ),
            medications=(
                "Paracetamol",
            ),
            allergy_history=(
                "Từng nổi mề đay sau dùng Penicillin"
            ),
        ),
    )

    result = provider.generate(
        context=context,
        language="vi",
    )

    assert "Penicillin" in result.advice_text
    assert "Paracetamol" in result.advice_text

    assert (
        "không tự thay đổi liều"
        in result.advice_text.lower()
    )

    assert (
        "không tự khởi trị kháng sinh"
        in result.advice_text.lower()
    )


def test_missing_history_is_not_treated_as_low_risk():
    provider = (
        LocalDeterministicMedicalAdviceProvider()
    )

    context = make_context(
        predicted_class="normal",
        normal=0.94,
        pneumonia=0.04,
        tuberculosis=0.02,
        include_history=False,
    )

    result = provider.generate(
        context=context,
        language="vi",
    )

    assert (
        "Risk level: MEDIUM"
        in result.advice_text
    )

    assert (
        "Chưa ghi nhận"
        in result.advice_text
        or "Chưa cung cấp"
        in result.advice_text
    )


def test_english_generation_uses_same_provider_contract():
    provider = (
        LocalDeterministicMedicalAdviceProvider()
    )

    context = make_context(
        predicted_class="normal",
        normal=0.90,
        pneumonia=0.06,
        tuberculosis=0.04,
    )

    result = provider.generate(
        context=context,
        language="en",
    )

    assert result.provider == "local-fallback"

    assert (
        result.model_name
        == "drai-deterministic-v1"
    )

    assert "Risk level: LOW" in result.advice_text

    assert (
        "Normal: 90.00%"
        in result.advice_text
    )