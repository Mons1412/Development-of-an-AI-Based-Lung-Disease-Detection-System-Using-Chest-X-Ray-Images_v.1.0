"""Deterministic local fallback for Dr.AI medical advice."""

from __future__ import annotations

from lung_xray_api.application.services.drai_context_builder import (
    DrAIContext,
    DrAIMedicalHistoryContext,
)
from lung_xray_api.application.services.drai_report import (
    DrAIClinicalContent,
    render_drai_report,
)
from lung_xray_api.application.services.medical_advice_provider import (
    MedicalAdviceProviderResult,
)


class LocalDeterministicMedicalAdviceProvider:
    """Generate cautious Dr.AI advice without an external AI service.

    This provider is intentionally deterministic. It does not diagnose,
    prescribe medication, or infer facts that are absent from DrAIContext.
    """

    PROVIDER_NAME = "local-fallback"
    MODEL_NAME = "drai-deterministic-v1"

    _VI_RED_FLAGS = (
        "khó thở",
        "kho tho",
        "ho ra máu",
        "ho ra mau",
        "đau ngực dữ dội",
        "dau nguc du doi",
        "tím tái",
        "tim tai",
        "ngất",
        "ngat",
    )

    _EN_RED_FLAGS = (
        "shortness of breath",
        "difficulty breathing",
        "coughing blood",
        "coughing up blood",
        "severe chest pain",
        "cyanosis",
        "fainting",
    )

    @staticmethod
    def _clean(value: object | None) -> str | None:
        if value is None:
            return None

        text = " ".join(str(value).split())
        return text or None

    @classmethod
    def _display(
        cls,
        value: object | None,
        *,
        missing: str,
    ) -> str:
        return cls._clean(value) or missing

    @staticmethod
    def _latest_history(
        context: DrAIContext,
    ) -> DrAIMedicalHistoryContext | None:
        if not context.medical_histories:
            return None

        return context.medical_histories[0]

    @classmethod
    def _all_text(
        cls,
        context: DrAIContext,
    ) -> str:
        parts: list[str] = []

        for history in context.medical_histories:
            values = (
                history.current_complaint_hpi,
                history.past_medical_history,
                history.past_medication_history,
                history.allergy_history,
                history.notes,
                history.habits,
            )

            for value in values:
                text = cls._clean(value)

                if text:
                    parts.append(text.lower())

            for collection in (
                history.diseases,
                history.medications,
                history.allergies,
            ):
                parts.extend(
                    item.lower()
                    for item in collection
                    if cls._clean(item)
                )

        return " ".join(parts)

    @staticmethod
    def _contains_unnegated_term(
        text: str,
        term: str,
    ) -> bool:
        """Best-effort negation guard for deterministic symptom matching."""

        negations = (
            "kh\u00f4ng",
            "khong",
            "ko",
            "kh\u00f4ng c\u00f3",
            "khong co",
            "kh\u00f4ng b\u1ecb",
            "khong bi",
            "kh\u00f4ng c\u00f2n",
            "khong con",
            "kh\u00f4ng ghi nh\u1eadn",
            "khong ghi nhan",
            "ph\u1ee7 nh\u1eadn",
            "phu nhan",
            "no",
            "not",
            "without",
            "denies",
            "denied",
            "denies any",
        )

        separators = (
            ".",
            ",",
            ";",
            ":",
            "\n",
            " nh\u01b0ng ",
            " nhung ",
            " but ",
            " however ",
        )

        normalized_text = text.casefold()
        normalized_term = term.casefold()

        start = 0

        while True:
            index = normalized_text.find(
                normalized_term,
                start,
            )

            if index < 0:
                return False

            prefix = normalized_text[
                max(0, index - 80):index
            ]

            last_separator = -1
            separator_length = 0

            for separator in separators:
                position = prefix.rfind(
                    separator.casefold()
                )

                if position > last_separator:
                    last_separator = position
                    separator_length = len(
                        separator
                    )

            if last_separator >= 0:
                clause_prefix = prefix[
                    last_separator
                    + separator_length:
                ]
            else:
                clause_prefix = prefix

            clause_prefix = " ".join(
                clause_prefix.split()
            ).strip()

            is_negated = any(
                clause_prefix.endswith(
                    negation.casefold()
                )
                for negation in negations
            )

            if not is_negated:
                return True

            start = index + len(
                normalized_term
            )

    @classmethod
    def _has_red_flags(
        cls,
        context: DrAIContext,
    ) -> bool:
        text = cls._all_text(context)

        if not text:
            return False

        return any(
            cls._contains_unnegated_term(
                text,
                term,
            )
            for term in (
                *cls._VI_RED_FLAGS,
                *cls._EN_RED_FLAGS,
            )
        )

    @staticmethod
    def _probabilities(
        context: DrAIContext,
    ) -> dict[str, float]:
        return {
            item.class_name.lower(): float(
                item.probability
            )
            for item in context.prediction.probabilities
        }

    @classmethod
    def _risk_level(
        cls,
        context: DrAIContext,
    ) -> str:
        probabilities = cls._probabilities(context)

        normal = probabilities.get("normal", 0.0)
        pneumonia = probabilities.get(
            "pneumonia",
            0.0,
        )
        tuberculosis = probabilities.get(
            "tuberculosis",
            0.0,
        )

        abnormal = max(
            pneumonia,
            tuberculosis,
        )

        predicted = (
            context.prediction.predicted_class
            .strip()
            .lower()
        )

        latest = cls._latest_history(context)

        has_hpi = bool(
            latest
            and cls._clean(
                latest.current_complaint_hpi
            )
        )

        if cls._has_red_flags(context):
            return "HIGH"

        if (
            predicted in {
                "pneumonia",
                "tuberculosis",
            }
            and abnormal >= 0.75
        ):
            return "HIGH"

        if predicted != "normal":
            return "MEDIUM"

        if abnormal >= 0.35:
            return "MEDIUM"

        if (
            normal >= 0.80
            and has_hpi
        ):
            return "LOW"

        return "MEDIUM"

    @classmethod
    def _collect_unique(
        cls,
        context: DrAIContext,
        field_name: str,
    ) -> list[str]:
        values: list[str] = []

        for history in context.medical_histories:
            raw = getattr(
                history,
                field_name,
                (),
            )

            for item in raw:
                text = cls._clean(item)

                if text and text not in values:
                    values.append(text)

        return values

    @classmethod
    def _build_vi(
        cls,
        context: DrAIContext,
    ) -> DrAIClinicalContent:
        missing = "Chưa ghi nhận"

        patient = context.patient
        latest = cls._latest_history(context)
        probabilities = cls._probabilities(context)
        risk = cls._risk_level(context)

        normal = probabilities.get("normal", 0.0)
        pneumonia = probabilities.get(
            "pneumonia",
            0.0,
        )
        tuberculosis = probabilities.get(
            "tuberculosis",
            0.0,
        )

        predicted = cls._display(
            context.prediction.predicted_class,
            missing=missing,
        )

        confidence = (
            float(context.prediction.confidence)
            * 100
        )

        age = cls._display(
            patient.age,
            missing=missing,
        )
        weight = cls._display(
            patient.weight_kg,
            missing=missing,
        )
        height = cls._display(
            patient.height_cm,
            missing=missing,
        )

        hpi = (
            cls._display(
                latest.current_complaint_hpi,
                missing=missing,
            )
            if latest
            else missing
        )

        diseases = cls._collect_unique(
            context,
            "diseases",
        )
        medications = cls._collect_unique(
            context,
            "medications",
        )
        allergies = cls._collect_unique(
            context,
            "allergies",
        )

        if latest:
            allergy_history = cls._clean(
                latest.allergy_history
            )

            if (
                allergy_history
                and allergy_history
                not in allergies
            ):
                allergies.append(
                    allergy_history
                )

        if risk == "LOW":
            summary_conclusion = (
                "AI đánh giá hình ảnh phổi có xu hướng "
                f"bình thường ({normal * 100:.2f}%)."
            )
            summary_recommendation = (
                "Tiếp tục theo dõi sức khỏe và tái khám "
                "khi có triệu chứng bất thường."
            )

        elif risk == "HIGH":
            summary_conclusion = (
                "AI ghi nhận xác suất bất thường đáng chú ý "
                "trên phim X-quang."
            )
            summary_recommendation = (
                "Nên được nhân viên y tế đánh giá trong "
                "thời gian sớm nhất, đặc biệt nếu triệu chứng tăng."
            )

        else:
            summary_conclusion = (
                "Kết quả AI có một số dấu hiệu cần được "
                "đối chiếu thêm với triệu chứng và bệnh sử."
            )
            summary_recommendation = (
                "Khuyến nghị trao đổi với bác sĩ để được "
                "đánh giá lâm sàng và theo dõi phù hợp."
            )

        disease_text = (
            "; ".join(diseases)
            if diseases
            else missing
        )

        clinical_assessment = (
            f"Thông tin hiện có: tuổi {age}, cân nặng "
            f"{weight} kg, chiều cao {height} cm. "
            f"Triệu chứng/lý do khám gần nhất: {hpi}. "
            f"Bệnh sử đã ghi nhận: {disease_text}. "
            "Đánh giá này chỉ tổng hợp dữ liệu đã được cung cấp "
            "và không thay thế thăm khám lâm sàng."
        )

        xray_interpretation = (
            f"Mô hình phân loại dự đoán lớp '{predicted}' "
            f"với độ tin cậy {confidence:.2f}%. "
            f"Phân bố xác suất: Normal {normal * 100:.2f}%, "
            f"Pneumonia {pneumonia * 100:.2f}%, "
            f"Tuberculosis {tuberculosis * 100:.2f}%. "
            "Dr.AI local fallback không trực tiếp đọc lại pixel "
            "của ảnh X-quang; nội dung này dựa trên kết quả "
            "phân loại đã có của hệ thống và cần được bác sĩ "
            "đối chiếu với lâm sàng."
        )

        symptom_guidance = (
            "Theo dõi diễn tiến các triệu chứng hô hấp và toàn thân. "
            "Nghỉ ngơi, uống đủ nước nếu không có chống chỉ định, "
            "và tránh tự kết luận bệnh chỉ dựa trên kết quả AI. "
            "Nếu triệu chứng kéo dài hoặc nặng hơn, cần được "
            "nhân viên y tế đánh giá."
        )

        if allergies:
            allergy_text = "; ".join(
                allergies
            )

            allergy_note = (
                "Dị ứng đã ghi nhận: "
                f"{allergy_text}. "
                "Cần thông báo thông tin này cho nhân viên y tế "
                "trước khi dùng thuốc."
            )
        else:
            allergy_note = (
                "Chưa có đủ thông tin dị ứng; cần xác nhận "
                "dị ứng thuốc/thực phẩm trước khi sử dụng."
            )

        if medications:
            medication_text = "; ".join(
                medications
            )

            medication_note = (
                "Thuốc hiện đã ghi nhận: "
                f"{medication_text}. "
                "Tiếp tục sử dụng theo đúng hướng dẫn của "
                "người kê đơn và không tự thay đổi liều."
            )
        else:
            medication_note = (
                "Chưa ghi nhận thuốc đang sử dụng."
            )

        medication_precautions = (
            f"{allergy_note} {medication_note} "
            "Không tự khởi trị kháng sinh, thuốc điều trị lao "
            "hoặc thuốc kê đơn chỉ dựa trên kết quả AI."
        )

        diet = (
            cls._display(
                latest.diet,
                missing=missing,
            )
            if latest
            else missing
        )
        appetite = (
            cls._display(
                latest.appetite,
                missing=missing,
            )
            if latest
            else missing
        )

        nutrition = (
            f"Chế độ ăn đã ghi nhận: {diet}. "
            f"Tình trạng ăn uống/khẩu vị: {appetite}. "
            "Ưu tiên chế độ ăn cân đối, đủ năng lượng và nước; "
            "điều chỉnh theo bệnh nền, dị ứng và hướng dẫn "
            "của chuyên gia y tế nếu có."
        )

        sleep = (
            cls._display(
                latest.sleep,
                missing=missing,
            )
            if latest
            else missing
        )
        exercise = (
            cls._display(
                latest.exercise,
                missing=missing,
            )
            if latest
            else missing
        )
        smoking = (
            cls._display(
                latest.smoking_status,
                missing=missing,
            )
            if latest
            else missing
        )
        alcohol = (
            cls._display(
                latest.alcohol_status,
                missing=missing,
            )
            if latest
            else missing
        )

        activity_and_rest = (
            f"Giấc ngủ: {sleep}. Vận động: {exercise}. "
            f"Hút thuốc: {smoking}. Rượu bia: {alcohol}. "
            "Nên duy trì nghỉ ngơi hợp lý, vận động nhẹ theo "
            "khả năng và hạn chế khói thuốc, rượu bia hoặc "
            "các chất kích thích có thể làm triệu chứng khó chịu hơn."
        )

        urgent_signs = (
            "Cần tìm trợ giúp y tế khẩn cấp nếu xuất hiện khó thở "
            "tăng nhanh, đau ngực dữ dội, ho ra máu, tím tái, "
            "ngất, lú lẫn hoặc tình trạng toàn thân xấu đi rõ rệt."
        )

        if risk == "HIGH":
            follow_up = (
                "Nên được đánh giá y tế sớm để đối chiếu kết quả "
                "X-quang AI với khám lâm sàng và các xét nghiệm "
                "cần thiết. Nếu có dấu hiệu cảnh báo, cần đi cấp cứu."
            )
        elif risk == "MEDIUM":
            follow_up = (
                "Nên trao đổi với bác sĩ/chuyên khoa phù hợp để "
                "đối chiếu kết quả AI với triệu chứng và bệnh sử, "
                "đặc biệt nếu triệu chứng còn kéo dài hoặc tăng."
            )
        else:
            follow_up = (
                "Có thể tiếp tục theo dõi sức khỏe; tái khám nếu "
                "xuất hiện triệu chứng mới, triệu chứng kéo dài "
                "hoặc tình trạng hiện tại nặng hơn."
            )

        return DrAIClinicalContent(
            risk_level=risk,
            summary_conclusion=summary_conclusion,
            summary_recommendation=summary_recommendation,
            clinical_assessment=clinical_assessment,
            xray_interpretation=xray_interpretation,
            symptom_guidance=symptom_guidance,
            medication_precautions=medication_precautions,
            nutrition=nutrition,
            activity_and_rest=activity_and_rest,
            urgent_signs=urgent_signs,
            follow_up=follow_up,
        )

    @classmethod
    def _build_en(
        cls,
        context: DrAIContext,
    ) -> DrAIClinicalContent:
        probabilities = cls._probabilities(context)
        risk = cls._risk_level(context)

        normal = probabilities.get("normal", 0.0)
        pneumonia = probabilities.get(
            "pneumonia",
            0.0,
        )
        tuberculosis = probabilities.get(
            "tuberculosis",
            0.0,
        )

        predicted = cls._display(
            context.prediction.predicted_class,
            missing="Not recorded",
        )

        confidence = (
            float(context.prediction.confidence)
            * 100
        )

        if risk == "LOW":
            conclusion = (
                "The AI result tends toward a normal lung "
                f"classification ({normal * 100:.2f}%)."
            )
            recommendation = (
                "Continue health monitoring and seek medical "
                "assessment if new or worsening symptoms occur."
            )
        elif risk == "HIGH":
            conclusion = (
                "The AI classifier shows a notable probability "
                "of an abnormal chest X-ray category."
            )
            recommendation = (
                "Medical assessment is recommended promptly, "
                "especially if symptoms are worsening."
            )
        else:
            conclusion = (
                "The AI result requires additional correlation "
                "with symptoms and medical history."
            )
            recommendation = (
                "Discuss the result with a clinician for "
                "appropriate clinical assessment and follow-up."
            )

        latest = cls._latest_history(context)

        hpi = (
            cls._display(
                latest.current_complaint_hpi,
                missing="Not recorded",
            )
            if latest
            else "Not recorded"
        )

        allergies = cls._collect_unique(
            context,
            "allergies",
        )
        medications = cls._collect_unique(
            context,
            "medications",
        )

        allergy_text = (
            "; ".join(allergies)
            if allergies
            else "Not recorded"
        )

        medication_text = (
            "; ".join(medications)
            if medications
            else "Not recorded"
        )

        return DrAIClinicalContent(
            risk_level=risk,
            summary_conclusion=conclusion,
            summary_recommendation=recommendation,
            clinical_assessment=(
                "Available clinical information was reviewed from "
                f"the supplied patient profile and history. "
                f"Latest complaint/history: {hpi}. "
                "Missing information is not interpreted as absence "
                "of disease or symptoms."
            ),
            xray_interpretation=(
                f"The classifier predicted '{predicted}' with "
                f"{confidence:.2f}% confidence. Probabilities: "
                f"Normal {normal * 100:.2f}%, "
                f"Pneumonia {pneumonia * 100:.2f}%, "
                f"Tuberculosis {tuberculosis * 100:.2f}%. "
                "The local fallback does not independently inspect "
                "the X-ray pixels and this result is not a diagnosis."
            ),
            symptom_guidance=(
                "Monitor respiratory and general symptoms. Rest, "
                "maintain appropriate hydration when not medically "
                "restricted, and seek clinical assessment for "
                "persistent or worsening symptoms."
            ),
            medication_precautions=(
                f"Recorded allergies: {allergy_text}. "
                f"Recorded medications: {medication_text}. "
                "Follow existing clinician instructions and do not "
                "start antibiotics, tuberculosis treatment, change "
                "doses, or stop prescribed therapy based only on "
                "the AI result."
            ),
            nutrition=(
                "Maintain a balanced diet and adequate hydration, "
                "taking recorded allergies, underlying conditions, "
                "and clinician instructions into account."
            ),
            activity_and_rest=(
                "Maintain adequate rest and gentle activity as "
                "tolerated. Avoid smoking and limit alcohol or "
                "other factors that may worsen respiratory symptoms."
            ),
            urgent_signs=(
                "Seek urgent medical care for rapidly worsening "
                "shortness of breath, severe chest pain, coughing "
                "up blood, cyanosis, fainting, confusion, or marked "
                "general deterioration."
            ),
            follow_up=(
                "Clinical follow-up should be based on symptoms, "
                "medical history, and the AI classification. "
                "Abnormal or worsening findings should be reviewed "
                "by an appropriate clinician."
            ),
        )

    def generate(
        self,
        *,
        context: DrAIContext,
        language: str,
    ) -> MedicalAdviceProviderResult:
        normalized_language = (
            str(language or "")
            .strip()
            .lower()
        )

        if normalized_language == "vi":
            content = self._build_vi(
                context
            )
        elif normalized_language == "en":
            content = self._build_en(
                context
            )
        else:
            raise ValueError(
                "Unsupported Dr.AI language."
            )

        advice_text = render_drai_report(
            context,
            content,
            normalized_language,
        )

        return MedicalAdviceProviderResult(
            provider=self.PROVIDER_NAME,
            model_name=self.MODEL_NAME,
            advice_text=advice_text,
        )


local_medical_advice_provider = (
    LocalDeterministicMedicalAdviceProvider()
)