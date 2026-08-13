"""Small deterministic intent rules that complement local TF-IDF retrieval."""

from __future__ import annotations

from lung_xray_api.assistant.retriever import normalize_text


class IntentRouter:
    """Route unambiguous product/model questions without a probabilistic guess."""

    _CONVERSATIONAL_ROUTES: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("greeting", ("xin chao", "chao ban", "hello", "hi", "hey")),
        ("thanks", ("cam on", "thank you", "thanks")),
        ("goodbye", ("tam biet", "hen gap lai", "goodbye", "bye")),
        ("help", ("giup toi", "huong dan", "help")),
        ("capabilities", ("ban lam duoc gi", "ho tro gi", "chuc nang tro ly")),
        ("start_over", ("bat dau lai", "hoi lai", "xoa hoi thoai")),
    )
    _ROUTES: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("confusion_matrix", ("confusion matrix", "nham giua cac lop")),
        (
            "output_classes",
            ("thu tu ba class", "thu tu ba lop", "thu tu cac lop", "model output", "output gom gi"),
        ),
        ("what_is_cnn", ("cnn la gi", "mang tich chap")),
        ("what_is_mobilenetv2", ("mobilenetv2 la gi", "kien truc nao")),
        ("why_mobilenetv2", ("tai sao chon mobilenet", "sao khong dung model lon")),
        ("input_format", ("kich thuoc nao", "bao nhieu pixel", "224")),
        ("preprocessing", ("tien xu ly", "chuan hoa", "preprocess_input", "normalize")),
        ("explain_accuracy", ("accuracy", "chinh xac bao nhieu")),
        ("explain_precision", ("precision",)),
        ("explain_recall", ("recall",)),
        ("explain_f1", ("f1", "macro f1")),
        ("transfer_learning", ("transfer learning", "train tu dau")),
        ("application_purpose", ("muc dich", "dung de lam gi", "chuc nang gi")),
        ("upload_help", ("tai anh", "upload", "keo tha", "chon tep")),
        (
            "supported_formats",
            ("dinh dang", "nhan file", "nhan tep", "jpg", "jpeg", "png", "dicom", "pdf"),
        ),
        ("max_file_size", ("toi da", "bao nhieu mb", "dung luong", "file lon")),
        ("supported_classes", ("bao nhieu lop", "class", "phan loai nhung gi")),
        ("start_analysis", ("chay model", "bam phan tich", "phan tich anh")),
        ("reset_analysis", ("anh khac", "phan tich lai", "xoa ket qua", "chon lai")),
    )
    _PREDICTION_TERMS = ("ket qua", "prediction", "du doan", "xac suat", "phan tram", "nhan")
    _CURRENT_RESULT_PHRASES = (
        "anh nay",
        "anh vua roi",
        "anh vua tai",
        "anh vua upload",
        "anh vua phan tich",
        "ket qua nay",
        "ket qua hien tai",
        "ket qua vua roi",
        "tinh trang hien tai",
        "sau khi phan tich",
        "model nghieng ve lop nao",
        "giai thich ket qua",
    )
    _DISEASE_TERMS = ("viem phoi", "lao phoi", "tuberculosis", "pneumonia")
    _PRIVACY_TERMS = ("du lieu", "luu", "luu tru", "quyen rieng tu", "privacy", "database")
    _LIMITATION_TERMS = ("han che", "gioi han", "limitations", "dang tin")

    def route(
        self,
        message: str,
        application_stage: str,
        *,
        has_prediction: bool = False,
    ) -> str | None:
        normalized = normalize_text(message)
        for intent, phrases in self._CONVERSATIONAL_ROUTES:
            if normalized in phrases or any(
                normalized.startswith(f"{phrase} ") for phrase in phrases
            ):
                return intent
        if self._references_current_result(normalized):
            return "explain_current_prediction"
        if any(term in normalized for term in self._PRIVACY_TERMS):
            return "privacy_storage"
        if any(term in normalized for term in self._LIMITATION_TERMS):
            return "model_limitations"
        if (has_prediction or application_stage == "after_analysis") and any(
            term in normalized for term in self._PREDICTION_TERMS
        ):
            return "explain_current_prediction"
        for intent, phrases in self._ROUTES:
            if any(phrase in normalized for phrase in phrases):
                return intent
        if any(term in normalized for term in self._DISEASE_TERMS):
            return "disease_information"
        return None

    @classmethod
    def _references_current_result(cls, normalized: str) -> bool:
        if any(phrase in normalized for phrase in cls._CURRENT_RESULT_PHRASES):
            return True
        tokens = set(normalized.split())
        image_reference = (
            "anh" in tokens
            and "vua" in tokens
            and bool(tokens.intersection({"roi", "tai", "upload", "phan", "tich"}))
        )
        result_reference = (
            bool(tokens.intersection({"ket", "qua", "prediction"}))
            and bool(tokens.intersection({"nay", "hien", "tai", "vua", "roi"}))
        )
        return image_reference or result_reference
