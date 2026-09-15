from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


REGULAR_FONT_NAME = "LungXrayReportRegular"
BOLD_FONT_NAME = "LungXrayReportBold"


@dataclass(slots=True)
class ReportPdfData:
    report_code: str
    language: str
    generated_at: datetime

    patient_code: str
    full_name: str
    birth_year: int | None = None
    gender: str | None = None
    phone: str | None = None
    address: str | None = None

    analysis_code: str = ""
    original_filename: str = ""
    input_source: str = ""
    model_key: str = ""
    model_version: str = ""
    analysis_created_at: datetime | None = None

    predicted_class: str | None = None
    confidence: float | None = None
    probabilities: dict[str, float] | None = None

    diseases: list[str] | None = None
    medications: list[str] | None = None
    allergies: list[str] | None = None
    smoking_status: str | None = None
    alcohol_status: str | None = None
    occupational_exposure: str | None = None
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class ReportFontPaths:
    regular: Path
    bold: Path


def _existing_path(value: str | None) -> Path | None:
    if not value:
        return None

    path = Path(value)

    if path.is_file():
        return path

    return None


def resolve_report_font_paths() -> ReportFontPaths:
    environment_regular = _existing_path(
        os.getenv("LUNGXRAY_REPORT_FONT_REGULAR")
    )
    environment_bold = _existing_path(
        os.getenv("LUNGXRAY_REPORT_FONT_BOLD")
    )

    if environment_regular and environment_bold:
        return ReportFontPaths(
            regular=environment_regular,
            bold=environment_bold,
        )

    candidate_pairs = [
        (
            Path(r"C:\Windows\Fonts\arial.ttf"),
            Path(r"C:\Windows\Fonts\arialbd.ttf"),
        ),
        (
            Path(r"C:\Windows\Fonts\tahoma.ttf"),
            Path(r"C:\Windows\Fonts\tahomabd.ttf"),
        ),
        (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ),
        (
            Path("/usr/share/fonts/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
        ),
    ]

    for regular_path, bold_path in candidate_pairs:
        if regular_path.is_file() and bold_path.is_file():
            return ReportFontPaths(
                regular=regular_path,
                bold=bold_path,
            )

    raise RuntimeError(
        "No Unicode report font was found. "
        "Set LUNGXRAY_REPORT_FONT_REGULAR and "
        "LUNGXRAY_REPORT_FONT_BOLD to valid TTF files."
    )


def register_report_fonts() -> ReportFontPaths:
    font_paths = resolve_report_font_paths()

    if REGULAR_FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(
            TTFont(
                REGULAR_FONT_NAME,
                str(font_paths.regular),
            )
        )

    if BOLD_FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(
            TTFont(
                BOLD_FONT_NAME,
                str(font_paths.bold),
            )
        )

    return font_paths


def _text(value: object | None) -> str:
    if value is None:
        return "N/A"

    string_value = str(value).strip()

    if not string_value:
        return "N/A"

    return escape(string_value)


def _list_text(values: list[str] | None) -> str:
    if not values:
        return "N/A"

    cleaned_values = [
        value.strip()
        for value in values
        if value and value.strip()
    ]

    if not cleaned_values:
        return "N/A"

    return escape(", ".join(cleaned_values))


def _datetime_text(value: datetime | None) -> str:
    if value is None:
        return "N/A"

    return value.strftime("%Y-%m-%d %H:%M:%S")


def _probability_percent(value: float | None) -> float | None:
    if value is None:
        return None

    number = float(value)

    if number <= 1:
        number *= 100

    return max(
        0.0,
        min(
            number,
            100.0,
        ),
    )


def _percent_text(value: float | None) -> str:
    percent = _probability_percent(value)

    if percent is None:
        return "N/A"

    return f"{percent:.2f}%"


class ReportLabPdfGenerator:
    def __init__(self) -> None:
        self.font_paths = register_report_fonts()

    def generate(
        self,
        *,
        output_path: Path,
        data: ReportPdfData,
    ) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        styles = self._build_styles()

        document = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=18 * mm,
            leftMargin=18 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
            title=data.report_code,
            author="Lung X-ray AI",
        )

        story: list[object] = []

        title = (
            "BÁO CÁO PHÂN TÍCH X-QUANG PHỔI"
            if data.language == "vi"
            else "LUNG X-RAY AI ANALYSIS REPORT"
        )

        story.append(
            Paragraph(
                title,
                styles["report_title"],
            )
        )
        story.append(
            Spacer(
                1,
                8 * mm,
            )
        )

        self._append_section(
            story=story,
            styles=styles,
            title=(
                "Thông tin báo cáo"
                if data.language == "vi"
                else "Report Information"
            ),
            rows=[
                ("Report code", data.report_code),
                ("Generated at", _datetime_text(data.generated_at)),
                ("Language", data.language),
            ],
        )

        self._append_section(
            story=story,
            styles=styles,
            title=(
                "Thông tin bệnh nhân"
                if data.language == "vi"
                else "Patient Information"
            ),
            rows=[
                ("Patient code", data.patient_code),
                ("Full name", data.full_name),
                ("Birth year", data.birth_year),
                ("Gender", data.gender),
                ("Phone", data.phone),
                ("Address", data.address),
            ],
        )

        self._append_section(
            story=story,
            styles=styles,
            title=(
                "Thông tin phân tích"
                if data.language == "vi"
                else "Analysis Information"
            ),
            rows=[
                ("Analysis code", data.analysis_code),
                ("Original filename", data.original_filename),
                ("Input source", data.input_source),
                ("Model", data.model_key),
                ("Model version", data.model_version),
                (
                    "Analysis time",
                    _datetime_text(data.analysis_created_at),
                ),
            ],
        )

        self._append_section(
            story=story,
            styles=styles,
            title=(
                "Kết quả AI"
                if data.language == "vi"
                else "AI Prediction"
            ),
            rows=[
                ("Predicted class", data.predicted_class),
                ("Confidence", _percent_text(data.confidence)),
            ],
        )

        self._append_probability_section(
            story=story,
            styles=styles,
            data=data,
        )

        self._append_section(
            story=story,
            styles=styles,
            title=(
                "Tiền sử y khoa"
                if data.language == "vi"
                else "Medical History"
            ),
            rows=[
                ("Diseases", _list_text(data.diseases)),
                ("Medications", _list_text(data.medications)),
                ("Allergies", _list_text(data.allergies)),
                ("Smoking status", data.smoking_status),
                ("Alcohol status", data.alcohol_status),
                (
                    "Occupational exposure",
                    data.occupational_exposure,
                ),
                ("Notes", data.notes),
            ],
        )

        disclaimer = (
            "Kết quả này được tạo bởi hệ thống AI hỗ trợ phân tích "
            "X-quang phổi và không thay thế chẩn đoán, tư vấn hoặc "
            "quyết định điều trị của chuyên gia y tế."
            if data.language == "vi"
            else
            "This report was generated by an AI-assisted chest X-ray "
            "analysis system and is not a substitute for professional "
            "medical diagnosis, advice, or treatment decisions."
        )

        story.append(
            Paragraph(
                (
                    "Lưu ý"
                    if data.language == "vi"
                    else "Disclaimer"
                ),
                styles["section_title"],
            )
        )

        story.append(
            Paragraph(
                escape(disclaimer),
                styles["body"],
            )
        )

        document.build(story)

        return output_path

    def _build_styles(self) -> dict[str, ParagraphStyle]:
        sample_styles = getSampleStyleSheet()

        return {
            "report_title": ParagraphStyle(
                "ReportTitle",
                parent=sample_styles["Title"],
                fontName=BOLD_FONT_NAME,
                fontSize=17,
                leading=22,
                alignment=TA_CENTER,
                spaceAfter=8,
            ),
            "section_title": ParagraphStyle(
                "SectionTitle",
                parent=sample_styles["Heading2"],
                fontName=BOLD_FONT_NAME,
                fontSize=12,
                leading=15,
                spaceBefore=8,
                spaceAfter=6,
            ),
            "body": ParagraphStyle(
                "Body",
                parent=sample_styles["BodyText"],
                fontName=REGULAR_FONT_NAME,
                fontSize=9.5,
                leading=13,
            ),
            "label": ParagraphStyle(
                "Label",
                parent=sample_styles["BodyText"],
                fontName=BOLD_FONT_NAME,
                fontSize=9.5,
                leading=13,
            ),
        }

    def _append_section(
        self,
        *,
        story: list[object],
        styles: dict[str, ParagraphStyle],
        title: str,
        rows: list[tuple[str, object | None]],
    ) -> None:
        story.append(
            Paragraph(
                escape(title),
                styles["section_title"],
            )
        )

        table_data = [
            [
                Paragraph(
                    escape(label),
                    styles["label"],
                ),
                Paragraph(
                    _text(value),
                    styles["body"],
                ),
            ]
            for label, value in rows
        ]

        table = Table(
            table_data,
            colWidths=[
                52 * mm,
                120 * mm,
            ],
            hAlign="LEFT",
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),
                    (
                        "BACKGROUND",
                        (0, 0),
                        (0, -1),
                        colors.HexColor("#F1F5F9"),
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.35,
                        colors.HexColor("#CBD5E1"),
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),
                ]
            )
        )

        story.append(table)

    def _append_probability_section(
        self,
        *,
        story: list[object],
        styles: dict[str, ParagraphStyle],
        data: ReportPdfData,
    ) -> None:
        story.append(
            Paragraph(
                (
                    "Phân bố xác suất"
                    if data.language == "vi"
                    else "Probability Distribution"
                ),
                styles["section_title"],
            )
        )

        probabilities = data.probabilities or {}

        rows = [
            [
                Paragraph(
                    "Class",
                    styles["label"],
                ),
                Paragraph(
                    "Probability",
                    styles["label"],
                ),
            ]
        ]

        if probabilities:
            sorted_probabilities = sorted(
                probabilities.items(),
                key=lambda item: item[1],
                reverse=True,
            )

            for class_name, probability in sorted_probabilities:
                rows.append(
                    [
                        Paragraph(
                            escape(str(class_name)),
                            styles["body"],
                        ),
                        Paragraph(
                            _percent_text(probability),
                            styles["body"],
                        ),
                    ]
                )
        else:
            rows.append(
                [
                    Paragraph(
                        "N/A",
                        styles["body"],
                    ),
                    Paragraph(
                        "N/A",
                        styles["body"],
                    ),
                ]
            )

        table = Table(
            rows,
            colWidths=[
                86 * mm,
                86 * mm,
            ],
            hAlign="LEFT",
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#E2E8F0"),
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.35,
                        colors.HexColor("#CBD5E1"),
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),
                ]
            )
        )

        story.append(table)


report_pdf_generator = ReportLabPdfGenerator()
