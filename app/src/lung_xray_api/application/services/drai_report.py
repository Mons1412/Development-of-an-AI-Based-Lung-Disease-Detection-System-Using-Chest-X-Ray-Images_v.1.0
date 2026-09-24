"""Validated clinical content and deterministic, locally assembled Dr.AI report.

General warning-sign and diagnostic-uncertainty references (checked 2026-09-22):
https://www.nhs.uk/conditions/pneumonia/
https://www.nhs.uk/symptoms/shortness-of-breath/
https://www.cdc.gov/tb/testing/diagnosing-tuberculosis.html
The qualitative risk labels are not derived from a validated clinical score.
"""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

from lung_xray_api.application.services.drai_context_builder import DrAIContext, DrAIReportMetadata

DISCLAIMER_VI = "<!> ỨNG DỤNG CHỈ CÓ TÍNH CHẤT THAM KHẢO VÀ KHÔNG THAY THẾ CHẨN ĐOÁN HOẶC QUYẾT ĐỊNH ĐIỀU TRỊ CỦA CHUYÊN GIA Y TẾ."
DISCLAIMER_EN = "<!> THIS APPLICATION IS FOR REFERENCE ONLY AND DOES NOT REPLACE DIAGNOSIS OR TREATMENT DECISIONS BY A QUALIFIED HEALTHCARE PROFESSIONAL."


class DrAIClinicalContent(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    summary_conclusion: str = Field(min_length=1, max_length=500)
    summary_recommendation: str = Field(min_length=1, max_length=500)
    clinical_assessment: str = Field(min_length=1, max_length=4000)
    xray_interpretation: str = Field(min_length=1, max_length=2000)
    symptom_guidance: str = Field(min_length=1, max_length=3000)
    medication_precautions: str = Field(min_length=1, max_length=3000)
    nutrition: str = Field(min_length=1, max_length=3000)
    activity_and_rest: str = Field(min_length=1, max_length=3000)
    urgent_signs: str = Field(min_length=1, max_length=2000)
    follow_up: str = Field(min_length=1, max_length=2000)

    @field_validator("summary_conclusion", "summary_recommendation")
    @classmethod
    def single_line(cls, value):
        return " ".join(value.split())


def render_drai_report(context: DrAIContext, content: DrAIClinicalContent, language: str) -> str:
    vi = language == "vi"
    missing = "Chưa cung cấp" if vi else "Not provided"
    def value(item):
        return " ".join(str(item).split()) if item is not None and str(item).strip() else missing
    def choose(vietnamese, english):
        return vietnamese if vi else english
    patient = context.patient
    metadata = context.report_metadata or DrAIReportMetadata()
    age = value(patient.age)
    age_birth = f"{age} / {value(patient.birth_year)}"
    model = f"{value(context.model.display_name)} ({value(context.model.model_key)}), {value(context.model.version)}"
    gender = {"MALE": choose("Nam", "Male"), "FEMALE": choose("Nữ", "Female")}.get(
        str(patient.gender).upper(), value(patient.gender))
    probs = {item.class_name.lower(): item.probability for item in context.prediction.probabilities}
    probability_lines = []
    for key in ("tuberculosis", "normal", "pneumonia"):
        percent = f"{probs[key] * 100:.2f}%" if key in probs else missing
        probability_lines.append(f"- {key.title()}: {percent}")
    allergies = []
    for history in context.medical_histories:
        for item in (*history.allergies, history.allergy_history):
            if item and value(item) not in allergies:
                allergies.append(value(item))
    allergy_text = "; ".join(allergies) if allergies else choose(
        "Chưa có thông tin dị ứng; cần xác nhận trước khi dùng thuốc/thực phẩm.",
        "Allergy information is missing; confirm before using medicines or foods.")
    # Avoid reassurance from a normal classifier result when clinical history is absent.
    risk = content.risk_level
    latest_hpi = context.medical_histories[0].current_complaint_hpi if context.medical_histories else None
    if risk == "LOW" and (context.prediction.predicted_class.lower() != "normal" or not latest_hpi):
        risk = "MEDIUM"
        conclusion = choose("Kết quả AI cần được đối chiếu thêm với triệu chứng và bệnh sử.",
                            "The AI result needs further correlation with symptoms and medical history.")
        recommendation = choose("Trao đổi với bác sĩ để đánh giá lâm sàng và bổ sung thông tin còn thiếu.",
                                "Discuss the result with a clinician and complete the missing clinical information.")
    else:
        conclusion = content.summary_conclusion
        recommendation = content.summary_recommendation
    lines = [
        choose("PHIẾU TƯ VẤN VÀ HƯỚNG DẪN Y TẾ SAU KHÁM", "POST-VISIT MEDICAL ADVICE AND GUIDANCE"),
        choose("(Dùng cho bệnh nhân ngoại trú / Hỗ trợ chuyên môn bởi Dr.AI)", "(For outpatients / Supported by Dr.AI)"), "",
        choose("PHẦN I: THÔNG TIN HÀNH CHÍNH", "PART I: ADMINISTRATIVE INFORMATION"),
        f"{choose('Họ và tên', 'Full name')}: {value(metadata.full_name)}",
        f"{choose('Tuổi/Năm sinh', 'Age/Year of birth')}: {age_birth}",
        f"{choose('Giới tính', 'Sex')}: {gender}",
        f"{choose('Số điện thoại', 'Phone')}: {value(metadata.phone)}",
        f"{choose('Thể trạng (Cân nặng/Chiều cao)', 'Weight/Height')}: {value(patient.weight_kg)} kg / {value(patient.height_cm)} cm",
        f"{choose('Khoa', 'Department')}: {missing}",
        f"{choose('Ngày khám', 'Examination date')}: {missing}",
        f"{choose('Ngày phân tích ảnh', 'Image analysis date')}: {value(metadata.analyzed_at)}",
        f"{choose('Ngày tạo tư vấn', 'Advice generation date')}: {value(metadata.generated_on)}",
        choose("Chẩn đoán sơ bộ: Chưa có chẩn đoán lâm sàng được xác nhận; xem kết quả AI định hướng ở Phần II.",
               "Preliminary diagnosis: No confirmed clinical diagnosis is available; see the AI classification in Part II."), "",
        choose("PHẦN II: TÓM TẮT TÌNH TRẠNG VÀ KẾT QUẢ KHÁM", "PART II: CONDITION AND FINDINGS"),
        f"Risk level: {risk}",
        f"Summary conclusion: {conclusion}",
        f"Summary recommendation: {recommendation}",
        choose("Mức cảnh báo do AI hỗ trợ tổng hợp, không phải thang nguy cơ lâm sàng đã được thẩm định.",
               "This AI-assisted warning level is not a validated clinical risk score."),
        choose("1. Kết luận chính", "1. Main assessment"), content.clinical_assessment,
        choose("2. Kết quả X-quang phổi - AI", "2. Chest X-ray AI result"),
        f"{choose('Mô hình', 'Model')}: {model}", *probability_lines,
        f"{choose('Lớp dự đoán', 'Predicted class')}: {value(context.prediction.predicted_class)}",
        choose("Các tỷ lệ trên là xác suất đầu ra của mô hình, không phải xác suất mắc bệnh. Dr.AI nhận kết quả phân loại, không trực tiếp đọc lại ảnh X-quang.",
               "These are model output probabilities, not probabilities of disease. Dr.AI receives classification results and does not independently read the X-ray image."),
        content.xray_interpretation, "",
        choose("PHẦN III: HƯỚNG DẪN ĐIỀU TRỊ VÀ LƯU Ý DÙNG THUỐC", "PART III: TREATMENT GUIDANCE AND MEDICATION PRECAUTIONS"),
        content.symptom_guidance,
        f"{choose('Cảnh báo dị ứng (Allergy Warning) - theo hồ sơ', 'Allergy Warning - as recorded')}: {allergy_text}",
        content.medication_precautions,
        choose("Không tự dùng kháng sinh, thuốc điều trị lao hoặc thay đổi liều/ngừng thuốc đã kê. Xác nhận với bác sĩ hoặc dược sĩ và tuân thủ y lệnh.",
               "Do not self-start antibiotics or TB medicines, change doses, or stop prescribed treatment. Confirm with your clinician or pharmacist and follow their instructions."), "",
        choose("PHẦN IV: HƯỚNG DẪN CHẾ ĐỘ DINH DƯỠNG & SINH HOẠT", "PART IV: NUTRITION AND DAILY ACTIVITIES"),
        choose("1. Dinh dưỡng", "1. Nutrition"), content.nutrition,
        choose("2. Vận động và nghỉ ngơi", "2. Activity and rest"), content.activity_and_rest, "",
        choose("PHẦN V: DẤU HIỆU CẦN TÁI KHÁM NGAY & LỊCH HẸN", "PART V: URGENT WARNING SIGNS AND FOLLOW-UP"),
        choose("Cấp cứu ngay nếu khó thở nặng, đau ngực dữ dội, tím tái hoặc lú lẫn. Cần khám khẩn khi ho ra máu, khó thở tăng, sốt cao hoặc tình trạng xấu đi; không chờ lịch hẹn.",
               "Seek emergency care for severe breathing difficulty, severe chest pain, blue/grey lips, or confusion. Seek urgent assessment for coughing blood, worsening breathlessness, high fever, or deterioration; do not wait for an appointment."),
        content.urgent_signs,
        f"{choose('Mốc tái khám đề xuất', 'Suggested follow-up timing')}: {content.follow_up}",
        choose("Đây là mốc đề xuất để trao đổi với bác sĩ, không phải lịch hẹn đã được xác nhận.",
               "This is proposed timing to discuss with a clinician, not a confirmed appointment."), "",
        choose("PHẦN VI: THÔNG TIN TRUY XUẤT KỸ THUẬT HỆ THỐNG", "PART VI: TECHNICAL AUDIT METADATA"),
        f"{choose('Mã bệnh nhân', 'Patient code')}: {value(metadata.patient_code)}",
        f"{choose('Mã báo cáo tư vấn', 'Advice report code')}: {value(metadata.report_code)}",
        f"{choose('Mã phân tích', 'Analysis code')}: {value(metadata.analysis_code)}",
        f"{choose('Tên tệp gốc', 'Original filename')}: {value(metadata.original_filename)}",
        f"{choose('Nguồn đầu vào', 'Input source')}: {value(metadata.input_source)}",
        f"{choose('Mô hình phân tích', 'Analysis model')}: {model}", "",
        DISCLAIMER_VI if vi else DISCLAIMER_EN,
    ]
    return "\n".join(lines)


def extract_advice_summary(text: str) -> dict[str, str] | None:
    # Old free-text advice deliberately has no inferred risk label.
    lines = text.splitlines()
    prefixes = {"risk_level": "Risk level: ", "conclusion": "Summary conclusion: ",
                "recommendation": "Summary recommendation: "}
    result = {}
    for key, prefix in prefixes.items():
        matches = [line[len(prefix):].strip() for line in lines if line.startswith(prefix)]
        if len(matches) != 1 or not matches[0]:
            return None
        result[key] = matches[0]
    return result if result["risk_level"] in {"LOW", "MEDIUM", "HIGH"} else None
