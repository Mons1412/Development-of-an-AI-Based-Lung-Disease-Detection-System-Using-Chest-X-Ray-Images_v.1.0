from datetime import datetime
from types import SimpleNamespace

import pytest

from lung_xray_api.application.services.drai_context_builder import (
    DrAIContext, DrAIModelContext, DrAIMedicalHistoryContext,
    DrAIPatientContext, DrAIPredictionContext, DrAIProbabilityContext,
)
from lung_xray_api.application.services.medical_advice_provider import (
    MedicalAdviceProviderConfigurationError, MedicalAdviceProviderError,
)
from lung_xray_api.infrastructure.ml.openai_medical_advice_provider import (
    OpenAIMedicalAdviceProvider,
)


def context():
    return DrAIContext(
        patient=DrAIPatientContext(birth_year=2004, gender="MALE", age=21,
                                   height_cm=170, weight_kg=60),
        medical_histories=(DrAIMedicalHistoryContext(
            recorded_at=datetime(2026, 9, 22), diseases=(), medications=(),
            allergies=("shellfish",), smoking_status="never", alcohol_status=None,
            occupational_exposure=None, notes=None, current_complaint_hpi="cough"),),
        model=DrAIModelContext("mobilenetv2", "MobileNetV2", "MobileNetV2", "1.1.0"),
        prediction=DrAIPredictionContext("pneumonia", 0.8, (
            DrAIProbabilityContext("normal", 0.15),
            DrAIProbabilityContext("pneumonia", 0.8),
            DrAIProbabilityContext("tuberculosis", 0.05),)),
    )


def content(**overrides):
    data = dict(risk_level="MEDIUM", summary_conclusion="Cần đối chiếu lâm sàng.",
        summary_recommendation="Trao đổi với bác sĩ.", clinical_assessment="Có ho được ghi nhận.",
        xray_interpretation="Kết quả AI cần được đối chiếu.", symptom_guidance="Theo dõi triệu chứng.",
        medication_precautions="Xác nhận dị ứng.", nutrition="Ăn phù hợp.",
        activity_and_rest="Nghỉ ngơi phù hợp.", urgent_signs="Khám khẩn nếu nặng lên.",
        follow_up="Liên hệ bác sĩ trong thời gian phù hợp.")
    data.update(overrides)
    return SimpleNamespace(**data)


class FakeResponses:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls = result, error, []
    def parse(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(output_parsed=self.result)


def provider(result=None, error=None):
    responses = FakeResponses(result, error)
    return OpenAIMedicalAdviceProvider(client=SimpleNamespace(responses=responses)), responses


def test_generates_structured_report():
    subject, responses = provider(content())
    result = subject.generate(context=context(), language="vi")
    assert result.provider == "openai"
    assert "PHẦN VI:" in result.advice_text
    assert "Pneumonia: 80.00%" in result.advice_text
    call = responses.calls[0]
    assert call["text_format"].__name__ == "DrAIClinicalContent"
    assert "shellfish" in call["input"][1]["content"]


def test_configuration_and_api_errors_are_safe():
    with pytest.raises(MedicalAdviceProviderConfigurationError, match="OpenAI API key"):
        OpenAIMedicalAdviceProvider().generate(context=context(), language="vi")
    subject, _ = provider(error=RuntimeError("network"))
    with pytest.raises(MedicalAdviceProviderError, match="generation failed"):
        subject.generate(context=context(), language="vi")


@pytest.mark.parametrize("result", [None, SimpleNamespace(risk_level="LOW")])
def test_rejects_empty_or_invalid_structured_output(result):
    subject, _ = provider(result)
    with pytest.raises(MedicalAdviceProviderError):
        subject.generate(context=context(), language="vi")


def test_prompt_excludes_administrative_metadata():
    subject, responses = provider(content())
    subject.generate(context=context(), language="en")
    assert "report_metadata" not in responses.calls[0]["input"][1]["content"]
