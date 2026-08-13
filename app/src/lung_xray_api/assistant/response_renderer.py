"""Render controlled offline assistant responses without generative AI."""

from __future__ import annotations

from lung_xray_api.assistant.knowledge_base import KnowledgeItem
from lung_xray_api.schemas.assistant import AssistantAnswer, PredictionContext

DISCLAIMER = (
    "Thông tin chỉ phục vụ mục đích học thuật và tham khảo; không thay thế đánh giá "
    "chuyên môn của bác sĩ."
)
_CLASS_ORDER = ("normal", "pneumonia", "tuberculosis")
_CLASS_LABELS_VI = {
    "normal": "Bình thường",
    "pneumonia": "Viêm phổi",
    "tuberculosis": "Lao phổi",
}


class ResponseRenderer:
    """Keeps safety wording and KB rendering in one deterministic output boundary."""

    def from_item(self, item: KnowledgeItem, confidence: float) -> AssistantAnswer:
        return AssistantAnswer(
            status="answered",
            mode="offline",
            intent=item.intent,
            answer=item.answer_detailed,
            sources=list(item.source_ids),
            disclaimer=DISCLAIMER,
            suggested_questions=list(item.sample_questions[:3]),
            confidence=self._confidence(confidence),
        )

    def needs_prediction(self, item: KnowledgeItem | None) -> AssistantAnswer:
        answer = (
            item.answer_detailed
            if item is not None
            else "Chưa có prediction context hợp lệ. Hãy hoàn tất phân tích ảnh trước."
        )
        return AssistantAnswer(
            status="needs_prediction",
            mode="offline",
            intent="no_prediction",
            answer=answer,
            sources=list(item.source_ids) if item is not None else [],
            disclaimer=DISCLAIMER,
            suggested_questions=list(item.sample_questions[:3]) if item is not None else [],
            confidence=1.0,
        )

    def safety_refusal(self, intent: str) -> AssistantAnswer:
        messages = {
            "dosage_request": "Tôi không thể hướng dẫn liều dùng thuốc. Hãy trao đổi trực tiếp với bác sĩ hoặc dược sĩ.",
            "medication_request": "Tôi không thể kê hoặc chọn thuốc. Cần có đánh giá chuyên môn trực tiếp trước khi điều trị.",
            "treatment_change_request": "Tôi không thể khuyến nghị thay đổi hoặc ngừng điều trị. Hãy liên hệ bác sĩ điều trị.",
            "definitive_diagnosis_request": (
                "Tôi không thể xác nhận chẩn đoán. Nhãn và xác suất của mô hình chỉ là đầu ra "
                "học thuật, không khẳng định một người có bệnh."
            ),
            "guaranteed_interpretation": (
                "Tôi không thể coi đầu ra mô hình là chắc chắn, bỏ qua các giới hạn an toàn, hoặc dùng nó "
                "để thay thế đánh giá của bác sĩ."
            ),
            "emergency_symptoms": (
                "Tình trạng bạn mô tả có thể cần đánh giá khẩn cấp. Không chờ chatbot hoặc mô hình phân tích; "
                "hãy liên hệ dịch vụ y tế khẩn cấp hoặc làm theo quy trình khẩn cấp của cơ sở."
            ),
            "insufficient_information": (
                "Tôi không thể tư vấn quyết định cho một ca cá thể vì không có dữ liệu lâm sàng đầy đủ và "
                "không được suy đoán thay cho đánh giá chuyên môn."
            ),
            "unavailable_patient_data": (
                "Tôi không có và không nên suy luận từ hồ sơ, triệu chứng, xét nghiệm hoặc dữ liệu nhận dạng của bệnh nhân."
            ),
        }
        return AssistantAnswer(
            status="medical_refusal",
            mode="offline",
            intent=intent,
            answer=messages[intent],
            sources=[],
            disclaimer=DISCLAIMER,
            suggested_questions=["Mô hình hiện hỗ trợ những lớp nào?", "Làm sao tải ảnh để phân tích?"],
            confidence=1.0,
        )


    def conversational(self, intent: str) -> AssistantAnswer:
        messages = {
            "greeting": (
                "Xin chào. Tôi có thể hướng dẫn sử dụng ứng dụng, giải thích "
                "đầu ra mô hình và giới hạn của hệ thống trong phạm vi kho kiến thức ngoại tuyến."
            ),
            "thanks": "Rất vui được hỗ trợ. Bạn có thể tiếp tục hỏi về cách dùng ứng dụng hoặc kết quả mô hình.",
            "goodbye": "Tạm biệt. Hãy luôn xem kết quả này là thông tin học thuật, không phải chẩn đoán.",
            "help": (
                "Bạn có thể hỏi cách tải ảnh, định dạng hỗ trợ, các lớp của mô hình, "
                "ý nghĩa xác suất hoặc cách đọc kết quả sau phân tích."
            ),
            "capabilities": (
                "Tôi tra cứu kho kiến thức ngoại tuyến để hướng dẫn sử dụng, giải thích "
                "MobileNetV2, đầu ra ba lớp, xác suất và giới hạn an toàn."
            ),
            "start_over": "Đã sẵn sàng cho một câu hỏi mới trong phạm vi hỗ trợ của ứng dụng.",
        }
        return AssistantAnswer(
            status="answered",
            mode="offline",
            intent=intent,
            answer=messages[intent],
            sources=[],
            disclaimer=DISCLAIMER,
            suggested_questions=[
                "Ứng dụng hỗ trợ những lớp nào?",
                "Xác suất của mô hình có ý nghĩa gì?",
                "Làm sao phân tích một ảnh mới?",
            ],
            confidence=1.0,
        )

    def out_of_scope(self, intent: str, confidence: float = 0.0) -> AssistantAnswer:
        messages = {
            "unsupported_disease": (
                "Mô hình chỉ hỗ trợ ba lớp normal, pneumonia và tuberculosis; nó không cung cấp "
                "kết luận cho bệnh được hỏi."
            ),
            "disease_information": (
                "Production Knowledge Base hiện không có nội dung bệnh học đã được clinical review cho câu hỏi này, "
                "nên tôi không thể cung cấp diễn giải lâm sàng."
            ),
            "model_limitations": (
                "Đây là nguyên mẫu học thuật ba lớp. Production Knowledge Base không có diễn giải lâm sàng chi tiết "
                "về giới hạn; kết quả không thay thế đánh giá chuyên môn hoặc clinical validation."
            ),
            "privacy_storage": (
                "Mặc định, ứng dụng xử lý cục bộ và có thể lưu metadata ca phân tích cùng thumbnail "
                "dẫn xuất trong database SQLite local; ảnh gốc không được lưu mặc định. Khi quản trị viên bật Gemini trực tuyến, "
                "chỉ câu hỏi và ngữ cảnh dự đoán không định danh được gửi tới dịch vụ bên ngoài; ảnh gốc, tên, mã ca và "
                "thumbnail không được gửi tự động. Không nhập thông tin nhận dạng vào ô chat."
            ),
            "out_of_scope": "Câu hỏi này nằm ngoài Knowledge Base production đã được duyệt. Tôi không suy đoán câu trả lời.",
        }
        return AssistantAnswer(
            status="out_of_scope",
            mode="offline",
            intent=intent,
            answer=messages[intent],
            sources=[],
            disclaimer=DISCLAIMER,
            suggested_questions=["Ứng dụng dùng để làm gì?", "Model hỗ trợ những lớp nào?"],
            confidence=self._confidence(confidence),
        )

    def clarification(self, suggestions: list[str], confidence: float) -> AssistantAnswer:
        return AssistantAnswer(
            status="needs_clarification",
            mode="offline",
            intent="needs_clarification",
            answer="Tôi chưa đủ chắc chắn để chọn một nội dung Knowledge Base. Bạn có thể hỏi rõ hơn theo các gợi ý sau.",
            sources=[],
            disclaimer=DISCLAIMER,
            suggested_questions=suggestions[:3],
            confidence=self._confidence(confidence),
        )

    def prediction_explanation(
        self,
        context: PredictionContext,
        source_item: KnowledgeItem | None,
    ) -> AssistantAnswer:
        predicted_probability = context.probabilities[context.predicted_label]
        predicted_percentage = self._percentage(predicted_probability)
        probabilities = "; ".join(
            (
                f"{_CLASS_LABELS_VI[label]} ({label}): "
                f"{self._percentage(context.probabilities[label])}"
            )
            for label in _CLASS_ORDER
        )
        answer = (
            f"Model phân loại ảnh vào lớp {_CLASS_LABELS_VI[context.predicted_label]} "
            f"với xác suất đầu ra cao nhất {predicted_percentage}. "
            f"Ba xác suất đầu ra của mô hình là: {probabilities}. "
            "Đây là đầu ra phân loại học thuật, không phải chẩn đoán hoặc xác suất lâm sàng "
            "một người mắc bệnh."
        )
        return AssistantAnswer(
            status="answered",
            mode="offline",
            intent="explain_current_prediction",
            answer=answer,
            sources=list(source_item.source_ids) if source_item is not None else [],
            disclaimer=DISCLAIMER,
            suggested_questions=["Làm sao chọn ảnh khác?", "Thứ tự ba lớp của model là gì?"],
            confidence=1.0,
        )

    @staticmethod
    def _confidence(value: float) -> float:
        return max(0.0, min(value, 1.0))

    @staticmethod
    def _percentage(value: float) -> str:
        return f"{value * 100:.2f}%".replace(".", ",")
