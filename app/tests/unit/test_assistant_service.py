from pathlib import Path

import pytest

from lung_xray_api.assistant.service import AssistantService
from lung_xray_api.schemas.assistant import AssistantQuery, PredictionContext


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_PATH = PROJECT_ROOT / "knowledge_base" / "compiled" / "knowledge_base.production.vi.json"


def _service() -> AssistantService:
    return AssistantService.from_path(PRODUCTION_PATH)


def _prediction_context() -> PredictionContext:
    return PredictionContext(
        predicted_label="pneumonia",
        probabilities={"normal": 0.08, "pneumonia": 0.87, "tuberculosis": 0.05},
        model_version="1.1.0",
    )


def test_before_analysis_answers_approved_application_purpose():
    answer = _service().answer(
        AssistantQuery(message="Phần mềm này dùng để làm gì?", application_stage="before_analysis")
    )

    assert answer.status == "answered"
    assert answer.mode == "offline"
    assert answer.intent == "application_purpose"
    assert answer.sources == ["PROJECT_SOURCE_V1_0_0", "MODEL_ARTIFACT_1_1_0", "WHO_AI_ETHICS_2021"]


def test_before_analysis_does_not_explain_a_prediction():
    answer = _service().answer(
        AssistantQuery(message="Kết quả ảnh này là gì?", application_stage="before_analysis")
    )

    assert answer.status == "needs_prediction"
    assert answer.intent == "no_prediction"
    assert answer.sources == ["PROJECT_SOURCE_V1_0_0"]


def test_after_analysis_requires_prediction_context():
    answer = _service().answer(
        AssistantQuery(message="Giải thích kết quả hiện tại", application_stage="after_analysis")
    )

    assert answer.status == "needs_prediction"
    assert answer.intent == "no_prediction"


def test_after_analysis_explains_only_supplied_model_output_context():
    answer = _service().answer(
        AssistantQuery(
            message="Giải thích kết quả và xác suất",
            application_stage="after_analysis",
            prediction_context=_prediction_context(),
        )
    )

    assert answer.status == "answered"
    assert answer.intent == "explain_current_prediction"
    assert "Viêm phổi" in answer.answer
    assert "87,00%" in answer.answer
    assert answer.sources == ["MODEL_ARTIFACT_1_1_0"]


@pytest.mark.parametrize(
    "message",
    [
        "ảnh này",
        "ảnh vừa rồi thế nào",
        "ảnh vừa tải",
        "ảnh tôi vừa upload ấy",
        "tình trạng hiện tại sau khi phân tích là gì",
        "kết quả này có nghĩa gì",
        "model nghiêng về lớp nào",
        "giải thích kết quả",
    ],
)
def test_current_prediction_phrases_use_current_model_output(message: str):
    answer = _service().answer(
        AssistantQuery(
            message=message,
            application_stage="after_analysis",
            prediction_context=_prediction_context(),
        )
    )

    assert answer.status == "answered"
    assert answer.intent == "explain_current_prediction"
    assert "Viêm phổi" in answer.answer
    assert "87,00%" in answer.answer
    assert "không phải chẩn đoán" in answer.answer


def test_current_prediction_phrase_without_context_asks_for_analysis_first():
    answer = _service().answer(
        AssistantQuery(
            message="ảnh tôi vừa upload ấy",
            application_stage="before_analysis",
        )
    )

    assert answer.status == "needs_prediction"
    assert answer.intent == "no_prediction"


def test_safety_guard_refuses_definitive_diagnosis_request():
    answer = _service().answer(
        AssistantQuery(
            message="Kết quả này có chắc chắn bị viêm phổi không?",
            application_stage="after_analysis",
            prediction_context=_prediction_context(),
        )
    )

    assert answer.status == "medical_refusal"
    assert answer.intent == "definitive_diagnosis_request"
    assert answer.sources == []


@pytest.mark.parametrize(
    ("message", "expected_intent"),
    [
        ("Kê thuốc gì cho tôi?", "medication_request"),
        ("Liều bao nhiêu mg?", "dosage_request"),
        ("Tôi có nên ngừng thuốc không?", "treatment_change_request"),
        ("Dựa vào bệnh án của tôi được không?", "unavailable_patient_data"),
    ],
)
def test_safety_guard_refuses_other_medical_or_patient_data_requests(message: str, expected_intent: str):
    answer = _service().answer(
        AssistantQuery(message=message, application_stage="after_analysis")
    )

    assert answer.status == "medical_refusal"
    assert answer.intent == expected_intent


def test_unsupported_disease_gets_controlled_out_of_scope_response():
    answer = _service().answer(
        AssistantQuery(message="Ứng dụng có phát hiện ung thư phổi không?", application_stage="before_analysis")
    )

    assert answer.status == "out_of_scope"
    assert answer.intent == "unsupported_disease"


def test_source_mapping_comes_from_the_retrieved_approved_item():
    service = _service()
    answer = service.answer(
        AssistantQuery(message="Hệ thống nhận file gì?", application_stage="before_analysis")
    )

    assert answer.status == "answered"
    assert answer.intent == "supported_formats"
    assert answer.sources == list(service.knowledge_base.by_intent["supported_formats"].source_ids)


def test_unrelated_question_has_controlled_out_of_scope_response():
    answer = _service().answer(
        AssistantQuery(message="Thời tiết hôm nay thế nào?", application_stage="before_analysis")
    )

    assert answer.status == "out_of_scope"
    assert answer.intent == "out_of_scope"


def test_privacy_question_uses_a_controlled_current_application_scope_response():
    answer = _service().answer(
        AssistantQuery(message="Ứng dụng có lưu dữ liệu bệnh nhân không?", application_stage="before_analysis")
    )

    assert answer.status == "out_of_scope"
    assert answer.intent == "privacy_storage"
    assert "database" in answer.answer
