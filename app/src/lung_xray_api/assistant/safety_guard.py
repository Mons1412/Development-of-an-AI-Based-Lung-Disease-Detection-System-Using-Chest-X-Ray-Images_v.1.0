"""Deterministic safety rules evaluated before any retrieval."""

from __future__ import annotations

from dataclasses import dataclass

from lung_xray_api.assistant.retriever import normalize_text


@dataclass(frozen=True)
class GuardDecision:
    """A pre-retrieval safety decision, if one is required."""

    intent: str | None = None


class SafetyGuard:
    """Reject clinical and privacy requests that this academic assistant cannot answer."""

    _RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
        (
            "dosage_request",
            (
                "lieu thuoc",
                "lieu dung",
                "lieu bao nhieu",
                "bao nhieu mg",
                "lan ngay",
                "moi ngay",
                "may ngay",
            ),
        ),
        (
            "medication_request",
            ("ke thuoc", "uong thuoc gi", "nen uong thuoc", "khang sinh nao", "don thuoc"),
        ),
        (
            "treatment_change_request",
            ("ngung thuoc", "doi thuoc", "doi phac do", "thay doi dieu tri", "tiep tuc thuoc"),
        ),
        (
            "definitive_diagnosis_request",
            (
                "hay chan doan",
                "chan doan benh nhan",
                "chan doan cho toi",
                "chot luon",
                "ket luan benh",
                "ket luan cuoi cung",
                "xac nhan benh",
                "chac chan bi",
                "chac chan mac",
                "chac chan benh",
                "co phai bi",
                "co phai mac",
                "dam bao bi",
                "100% bi",
            ),
        ),
        (
            "guaranteed_interpretation",
            (
                "chac chan dung",
                "tin tuyet doi",
                "bo qua bac si",
                "bo qua han che",
                "bo qua quy tac",
                "bo qua quy dinh",
                "ignore safety",
                "dam bao ket qua",
            ),
        ),
        (
            "emergency_symptoms",
            ("kho tho nang", "ho ra mau", "tim tai", "mat y thuc", "dau nguc du doi"),
        ),
        (
            "insufficient_information",
            ("tu van ca nay", "benh nhan nen", "huong dan cho benh nhan", "xem ca benh"),
        ),
        (
            "unavailable_patient_data",
            (
                "benh an",
                "ho so benh nhan",
                "du lieu cua toi",
                "xet nghiem cua toi",
                "trieu chung cua toi",
                "ten benh nhan",
                "ma benh nhan",
                "ma ho so",
                "so dien thoai",
            ),
        ),
        (
            "unsupported_disease",
            (
                "ung thu",
                "covid",
                "copd",
                "tran dich",
                "tran khi",
                "xo phoi",
                "hen suyen",
            ),
        ),
    )
    _RESULT_TERMS = ("ket qua", "prediction", "du doan", "xac suat", "phan tram", "anh nay")

    def evaluate(self, message: str, application_stage: str) -> GuardDecision:
        normalized = normalize_text(message)
        for intent, phrases in self._RULES:
            if any(phrase in normalized for phrase in phrases):
                return GuardDecision(intent=intent)

        if application_stage != "after_analysis" and any(
            phrase in normalized for phrase in self._RESULT_TERMS
        ):
            return GuardDecision(intent="no_prediction")
        return GuardDecision()
