from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime
from html import escape
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import (
    ParagraphStyle,
    getSampleStyleSheet,
)
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Image as RLImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


REGULAR_FONT_NAME = "LungXrayReportRegular"
BOLD_FONT_NAME = "LungXrayReportBold"


TITLE_COLOR = colors.HexColor("#1A365D")
SECTION_COLOR = colors.HexColor("#2B6CB0")
BODY_COLOR = colors.HexColor("#2D3748")
MUTED_COLOR = colors.HexColor("#718096")
BORDER_COLOR = colors.HexColor("#CBD5E1")
HEADER_BACKGROUND = colors.HexColor("#EDF2F7")
NOTICE_BACKGROUND = colors.HexColor("#F7FAFC")
DISCLAIMER_COLOR = colors.HexColor("#C53030")


DISCLAIMER_VI = (
    "<!> KẾT QUẢ CHỈ MANG TÍNH CHẤT THAM KHẢO "
    "VÀ KHÔNG THAY THẾ CHẨN ĐOÁN, TƯ VẤN "
    "HOẶC QUYẾT ĐỊNH ĐIỀU TRỊ CỦA CHUYÊN GIA Y TẾ."
)

DISCLAIMER_EN = (
    "<!> THIS RESULT IS FOR REFERENCE ONLY AND DOES NOT "
    "REPLACE PROFESSIONAL MEDICAL DIAGNOSIS, ADVICE, "
    "OR TREATMENT DECISIONS."
)


@dataclass(slots=True)
class ReportPdfData:
    report_code: str
    language: str
    generated_at: datetime

    patient_code: str
    full_name: str
    birth_year: int | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    phone: str | None = None
    address: str | None = None

    analysis_code: str = ""
    original_filename: str = ""
    input_source: str = ""

    model_key: str = ""
    model_display_name: str = ""
    model_version: str = ""

    analysis_created_at: datetime | None = None
    xray_image_path: str | None = None

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

    current_complaint_hpi: str | None = None
    allergy_history: str | None = None
    diet: str | None = None
    appetite: str | None = None
    sleep: str | None = None
    exercise: str | None = None
    habits: str | None = None


@dataclass(
    frozen=True,
    slots=True,
)
class ReportFontPaths:
    regular: Path
    bold: Path


def _existing_path(
    value: str | None,
) -> Path | None:

    if not value:
        return None

    path = Path(
        value
    )

    return (
        path
        if path.is_file()
        else None
    )


def resolve_report_font_paths(
) -> ReportFontPaths:

    environment_regular = (
        _existing_path(
            os.getenv(
                "LUNGXRAY_REPORT_FONT_REGULAR"
            )
        )
    )

    environment_bold = (
        _existing_path(
            os.getenv(
                "LUNGXRAY_REPORT_FONT_BOLD"
            )
        )
    )

    if (
        environment_regular
        and environment_bold
    ):
        return ReportFontPaths(
            regular=environment_regular,
            bold=environment_bold,
        )

    candidate_pairs = [
        (
            Path(
                r"C:\Windows\Fonts\arial.ttf"
            ),
            Path(
                r"C:\Windows\Fonts\arialbd.ttf"
            ),
        ),
        (
            Path(
                r"C:\Windows\Fonts\tahoma.ttf"
            ),
            Path(
                r"C:\Windows\Fonts\tahomabd.ttf"
            ),
        ),
        (
            Path(
                "/usr/share/fonts/truetype/"
                "dejavu/DejaVuSans.ttf"
            ),
            Path(
                "/usr/share/fonts/truetype/"
                "dejavu/DejaVuSans-Bold.ttf"
            ),
        ),
    ]

    for regular, bold in candidate_pairs:

        if (
            regular.is_file()
            and bold.is_file()
        ):
            return ReportFontPaths(
                regular=regular,
                bold=bold,
            )

    raise RuntimeError(
        "No Unicode report font was found."
    )


def register_report_fonts(
) -> ReportFontPaths:

    paths = (
        resolve_report_font_paths()
    )

    if (
        REGULAR_FONT_NAME
        not in pdfmetrics.getRegisteredFontNames()
    ):
        pdfmetrics.registerFont(
            TTFont(
                REGULAR_FONT_NAME,
                str(
                    paths.regular
                ),
            )
        )

    if (
        BOLD_FONT_NAME
        not in pdfmetrics.getRegisteredFontNames()
    ):
        pdfmetrics.registerFont(
            TTFont(
                BOLD_FONT_NAME,
                str(
                    paths.bold
                ),
            )
        )

    return paths


def _plain(
    value: object | None,
    *,
    missing: str,
) -> str:

    if value is None:
        return missing

    text = " ".join(
        str(value).split()
    )

    return (
        text
        if text
        else missing
    )


def _list_plain(
    values: list[str] | None,
    *,
    missing: str,
) -> str:

    if not values:
        return missing

    cleaned = [
        " ".join(
            str(value).split()
        )
        for value in values
        if (
            value
            and str(value).strip()
        )
    ]

    return (
        ", ".join(
            cleaned
        )
        if cleaned
        else missing
    )


def _percent(
    value: float | None,
) -> str:

    if value is None:
        return "N/A"

    number = float(
        value
    )

    if number <= 1:
        number *= 100

    number = max(
        0.0,
        min(
            number,
            100.0,
        ),
    )

    return (
        f"{number:.2f}%"
    )


def _date_time(
    value: datetime | None,
    *,
    missing: str,
) -> str:

    if value is None:
        return missing

    return value.strftime(
        "%d/%m/%Y %H:%M:%S"
    )


def _age(
    data: ReportPdfData,
    *,
    missing: str,
) -> str:

    reference = (
        data.analysis_created_at.date()
        if data.analysis_created_at
        else data.generated_at.date()
    )

    if data.date_of_birth:
        born = (
            data.date_of_birth
        )

        years = (
            reference.year
            - born.year
            - (
                (
                    reference.month,
                    reference.day,
                )
                <
                (
                    born.month,
                    born.day,
                )
            )
        )

        return str(
            years
        )

    if data.birth_year:
        return str(
            reference.year
            - int(
                data.birth_year
            )
        )

    return missing


def _gender(
    value: str | None,
    *,
    vi: bool,
    missing: str,
) -> str:

    normalized = str(
        value or ""
    ).strip().upper()

    if normalized == "MALE":
        return (
            "Nam"
            if vi
            else "Male"
        )

    if normalized == "FEMALE":
        return (
            "Nữ"
            if vi
            else "Female"
        )

    return _plain(
        value,
        missing=missing,
    )


class ReportLabPdfGenerator:

    def __init__(
        self,
    ) -> None:

        self.font_paths = (
            register_report_fonts()
        )

    def generate(
        self,
        *,
        output_path: Path,
        data: ReportPdfData,
    ) -> Path:

        output_path = Path(
            output_path
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        vi = (
            data.language == "vi"
        )

        missing = (
            "Chưa cung cấp"
            if vi
            else "Not provided"
        )

        styles = (
            self._build_styles()
        )

        document = SimpleDocTemplate(
            str(
                output_path
            ),
            pagesize=A4,
            rightMargin=16 * mm,
            leftMargin=16 * mm,
            topMargin=15 * mm,
            bottomMargin=15 * mm,
            title=data.report_code,
            author="Lung X-ray AI",
        )

        story: list[object] = []

        # ====================================================
        # HEADER
        # ====================================================

        title = (
            "PHIẾU KẾT QUẢ PHÂN TÍCH "
            "X-QUANG PHỔI BẰNG AI"
            if vi
            else
            "AI CHEST X-RAY ANALYSIS RESULT"
        )

        subtitle = (
            "Kết quả phân loại hình ảnh bằng "
            "mô hình học máy"
            if vi
            else
            "Image classification result "
            "generated by a machine-learning model"
        )

        story.append(
            Paragraph(
                escape(
                    title
                ),
                styles[
                    "report_title"
                ],
            )
        )

        story.append(
            Paragraph(
                escape(
                    subtitle
                ),
                styles[
                    "subtitle"
                ],
            )
        )

        story.append(
            HRFlowable(
                width="100%",
                thickness=1.3,
                color=SECTION_COLOR,
                spaceBefore=2,
                spaceAfter=7,
            )
        )

        # ====================================================
        # I. PATIENT
        # ====================================================

        self._section(
            story,
            styles,
            (
                "I. THÔNG TIN BỆNH NHÂN"
                if vi
                else
                "I. PATIENT INFORMATION"
            ),
        )

        self._table(
            story,
            styles,
            [
                (
                    (
                        "Họ và tên"
                        if vi
                        else "Full name"
                    ),
                    data.full_name,
                ),
                (
                    (
                        "Mã bệnh nhân"
                        if vi
                        else "Patient code"
                    ),
                    data.patient_code,
                ),
                (
                    (
                        "Tuổi"
                        if vi
                        else "Age"
                    ),
                    _age(
                        data,
                        missing=missing,
                    ),
                ),
                (
                    (
                        "Năm sinh"
                        if vi
                        else "Birth year"
                    ),
                    data.birth_year,
                ),
                (
                    (
                        "Giới tính"
                        if vi
                        else "Sex"
                    ),
                    _gender(
                        data.gender,
                        vi=vi,
                        missing=missing,
                    ),
                ),
                (
                    (
                        "Số điện thoại"
                        if vi
                        else "Phone"
                    ),
                    data.phone,
                ),
            ],
            missing=missing,
        )

        # ====================================================
        # II. ANALYSIS
        # ====================================================

        self._section(
            story,
            styles,
            (
                "II. THÔNG TIN PHÂN TÍCH"
                if vi
                else
                "II. ANALYSIS INFORMATION"
            ),
        )

        model_name = (
            _plain(
                data.model_display_name,
                missing=(
                    _plain(
                        data.model_key,
                        missing=missing,
                    )
                ),
            )
        )

        self._table(
            story,
            styles,
            [
                (
                    (
                        "Mã phân tích"
                        if vi
                        else "Analysis code"
                    ),
                    data.analysis_code,
                ),
                (
                    (
                        "Ngày phân tích"
                        if vi
                        else "Analysis time"
                    ),
                    _date_time(
                        data.analysis_created_at,
                        missing=missing,
                    ),
                ),
                (
                    (
                        "Tên tệp ảnh"
                        if vi
                        else "Original filename"
                    ),
                    data.original_filename,
                ),
                (
                    (
                        "Nguồn đầu vào"
                        if vi
                        else "Input source"
                    ),
                    data.input_source,
                ),
                (
                    (
                        "Mô hình AI"
                        if vi
                        else "AI model"
                    ),
                    model_name,
                ),
                (
                    (
                        "Phiên bản mô hình"
                        if vi
                        else "Model version"
                    ),
                    data.model_version,
                ),
            ],
            missing=missing,
        )

        # ====================================================
        # III. AI CLASSIFICATION
        # ====================================================

        self._section(
            story,
            styles,
            (
                "III. KẾT QUẢ PHÂN LOẠI AI"
                if vi
                else
                "III. AI CLASSIFICATION RESULT"
            ),
        )
        self._append_xray_image(
            story=story,
            data=data,
        )


        result_rows = [
            (
                (
                    "Lớp dự đoán"
                    if vi
                    else "Predicted class"
                ),
                data.predicted_class,
            ),
            (
                "Confidence",
                _percent(
                    data.confidence
                ),
            ),
        ]

        self._table(
            story,
            styles,
            result_rows,
            missing=missing,
        )

        story.append(
            Spacer(
                1,
                3 * mm,
            )
        )

        story.append(
            Paragraph(
                (
                    "Phân bố xác suất đầu ra"
                    if vi
                    else
                    "Model output probability distribution"
                ),
                styles[
                    "subheading"
                ],
            )
        )

        probabilities = (
            data.probabilities
            or {}
        )

        probability_rows = [
            [
                Paragraph(
                    (
                        "<b>Lớp</b>"
                        if vi
                        else "<b>Class</b>"
                    ),
                    styles[
                        "body"
                    ],
                ),
                Paragraph(
                    (
                        "<b>Xác suất đầu ra</b>"
                        if vi
                        else "<b>Output probability</b>"
                    ),
                    styles[
                        "body"
                    ],
                ),
            ]
        ]

        sorted_probabilities = sorted(
            probabilities.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        if sorted_probabilities:

            for (
                class_name,
                probability,
            ) in sorted_probabilities:

                probability_rows.append(
                    [
                        Paragraph(
                            escape(
                                str(
                                    class_name
                                ).title()
                            ),
                            styles[
                                "body"
                            ],
                        ),
                        Paragraph(
                            _percent(
                                probability
                            ),
                            styles[
                                "body"
                            ],
                        ),
                    ]
                )

        else:

            probability_rows.append(
                [
                    Paragraph(
                        missing,
                        styles[
                            "body"
                        ],
                    ),
                    Paragraph(
                        missing,
                        styles[
                            "body"
                        ],
                    ),
                ]
            )

        probability_table = Table(
            probability_rows,
            colWidths=[
                84 * mm,
                84 * mm,
            ],
            hAlign="LEFT",
        )

        probability_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        HEADER_BACKGROUND,
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.35,
                        BORDER_COLOR,
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

        story.append(
            probability_table
        )

        story.append(
            Spacer(
                1,
                3 * mm,
            )
        )

        probability_note = (
            "Các tỷ lệ trên là xác suất đầu ra "
            "của mô hình phân loại, không phải "
            "xác suất bệnh nhân mắc bệnh."
            if vi
            else
            "The percentages above are classifier "
            "output probabilities, not probabilities "
            "that the patient has a disease."
        )

        story.append(
            Paragraph(
                escape(
                    probability_note
                ),
                styles[
                    "notice"
                ],
            )
        )

        # ====================================================
        # IV. CLINICAL CONTEXT
        # ====================================================

        self._section(
            story,
            styles,
            (
                "IV. THÔNG TIN HỒ SƠ Y KHOA KÈM THEO"
                if vi
                else
                "IV. ACCOMPANYING MEDICAL RECORD INFORMATION"
            ),
        )

        self._table(
            story,
            styles,
            [
                (
                    (
                        "Triệu chứng hiện tại"
                        if vi
                        else "Current complaint"
                    ),
                    data.current_complaint_hpi,
                ),
                (
                    (
                        "Bệnh sử"
                        if vi
                        else "Diseases"
                    ),
                    _list_plain(
                        data.diseases,
                        missing=missing,
                    ),
                ),
                (
                    (
                        "Thuốc đang sử dụng"
                        if vi
                        else "Medications"
                    ),
                    _list_plain(
                        data.medications,
                        missing=missing,
                    ),
                ),
                (
                    (
                        "Dị ứng"
                        if vi
                        else "Allergies"
                    ),
                    (
                        _list_plain(
                            data.allergies,
                            missing=missing,
                        )
                        if data.allergies
                        else _plain(
                            data.allergy_history,
                            missing=missing,
                        )
                    ),
                ),
                (
                    (
                        "Tình trạng hút thuốc"
                        if vi
                        else "Smoking status"
                    ),
                    data.smoking_status,
                ),
                (
                    (
                        "Sử dụng rượu bia"
                        if vi
                        else "Alcohol status"
                    ),
                    data.alcohol_status,
                ),
                (
                    (
                        "Phơi nhiễm nghề nghiệp"
                        if vi
                        else "Occupational exposure"
                    ),
                    data.occupational_exposure,
                ),
                (
                    (
                        "Ghi chú"
                        if vi
                        else "Notes"
                    ),
                    data.notes,
                ),
            ],
            missing=missing,
        )

        # ====================================================
        # V. INTERPRETATION NOTE
        # ====================================================

        self._section(
            story,
            styles,
            (
                "V. GHI CHÚ VỀ KẾT QUẢ AI"
                if vi
                else
                "V. NOTES ABOUT THE AI RESULT"
            ),
        )

        notes = (
            [
                (
                    "Kết quả trong phiếu này được tạo "
                    "từ mô hình phân loại MobileNetV2."
                ),
                (
                    "Lớp dự đoán và Confidence là đầu ra "
                    "của mô hình máy học, không phải "
                    "chẩn đoán y khoa được xác nhận."
                ),
                (
                    "Kết quả thuộc lớp Normal không đồng nghĩa "
                    "với việc loại trừ hoàn toàn bệnh lý."
                ),
                (
                    "Việc diễn giải kết quả cần được kết hợp "
                    "với triệu chứng, bệnh sử, thăm khám "
                    "và đánh giá của chuyên gia y tế."
                ),
            ]
            if vi
            else
            [
                (
                    "This report is generated from the "
                    "MobileNetV2 classification model."
                ),
                (
                    "The predicted class and confidence are "
                    "machine-learning outputs and are not "
                    "a confirmed medical diagnosis."
                ),
                (
                    "A Normal classification does not by itself "
                    "exclude disease."
                ),
                (
                    "Interpretation should be combined with "
                    "symptoms, medical history, clinical "
                    "examination, and professional assessment."
                ),
            ]
        )

        for note in notes:

            story.append(
                Paragraph(
                    "\u2022 "
                    + escape(
                        note
                    ),
                    styles[
                        "bullet"
                    ],
                )
            )

        # ====================================================
        # VI. TRACEABILITY
        # ====================================================

        self._section(
            story,
            styles,
            (
                "VI. THÔNG TIN TRUY XUẤT"
                if vi
                else
                "VI. TRACEABILITY INFORMATION"
            ),
        )

        self._table(
            story,
            styles,
            [
                (
                    (
                        "Mã báo cáo"
                        if vi
                        else "Report code"
                    ),
                    data.report_code,
                ),
                (
                    (
                        "Mã phân tích"
                        if vi
                        else "Analysis code"
                    ),
                    data.analysis_code,
                ),
                (
                    (
                        "Mô hình"
                        if vi
                        else "Model"
                    ),
                    model_name,
                ),
                (
                    (
                        "Phiên bản"
                        if vi
                        else "Version"
                    ),
                    data.model_version,
                ),
                (
                    (
                        "Thời điểm tạo báo cáo"
                        if vi
                        else "Report generated at"
                    ),
                    _date_time(
                        data.generated_at,
                        missing=missing,
                    ),
                ),
            ],
            missing=missing,
        )

        story.append(
            Spacer(
                1,
                4 * mm,
            )
        )

        story.append(
            HRFlowable(
                width="100%",
                thickness=0.8,
                color=BORDER_COLOR,
                spaceBefore=2,
                spaceAfter=6,
            )
        )

        story.append(
            Paragraph(
                escape(
                    (
                        DISCLAIMER_VI
                        if vi
                        else DISCLAIMER_EN
                    )
                ),
                styles[
                    "disclaimer"
                ],
            )
        )

        document.build(
            story
        )

        return output_path

    @staticmethod
    def _build_styles(
    ) -> dict[str, ParagraphStyle]:

        sample = (
            getSampleStyleSheet()
        )

        return {
            "report_title": ParagraphStyle(
                "ReportTitle",
                parent=sample[
                    "Title"
                ],
                fontName=BOLD_FONT_NAME,
                fontSize=15,
                leading=19,
                alignment=TA_CENTER,
                textColor=TITLE_COLOR,
                spaceAfter=4,
            ),

            "subtitle": ParagraphStyle(
                "Subtitle",
                parent=sample[
                    "BodyText"
                ],
                fontName=REGULAR_FONT_NAME,
                fontSize=9,
                leading=12,
                alignment=TA_CENTER,
                textColor=MUTED_COLOR,
                spaceAfter=4,
            ),

            "section_title": ParagraphStyle(
                "SectionTitle",
                parent=sample[
                    "Heading2"
                ],
                fontName=BOLD_FONT_NAME,
                fontSize=11,
                leading=14,
                textColor=SECTION_COLOR,
                spaceBefore=8,
                spaceAfter=5,
            ),

            "subheading": ParagraphStyle(
                "Subheading",
                parent=sample[
                    "BodyText"
                ],
                fontName=BOLD_FONT_NAME,
                fontSize=9.5,
                leading=12,
                textColor=BODY_COLOR,
                spaceAfter=4,
            ),

            "body": ParagraphStyle(
                "Body",
                parent=sample[
                    "BodyText"
                ],
                fontName=REGULAR_FONT_NAME,
                fontSize=9,
                leading=12.5,
                textColor=BODY_COLOR,
            ),

            "bullet": ParagraphStyle(
                "Bullet",
                parent=sample[
                    "BodyText"
                ],
                fontName=REGULAR_FONT_NAME,
                fontSize=9,
                leading=12.5,
                leftIndent=10,
                firstLineIndent=-7,
                textColor=BODY_COLOR,
                spaceAfter=3,
            ),

            "notice": ParagraphStyle(
                "Notice",
                parent=sample[
                    "BodyText"
                ],
                fontName=REGULAR_FONT_NAME,
                fontSize=8.5,
                leading=12,
                textColor=MUTED_COLOR,
                backColor=NOTICE_BACKGROUND,
                borderPadding=6,
                spaceBefore=3,
                spaceAfter=4,
            ),

            "disclaimer": ParagraphStyle(
                "Disclaimer",
                parent=sample[
                    "BodyText"
                ],
                fontName=BOLD_FONT_NAME,
                fontSize=8.3,
                leading=11,
                alignment=TA_CENTER,
                textColor=DISCLAIMER_COLOR,
            ),
        }

    @staticmethod
    def _append_xray_image(
        *,
        story: list[object],
        data: ReportPdfData,
    ) -> None:

        if not data.xray_image_path:
            return

        image_path = Path(
            data.xray_image_path
        )

        if (
            not image_path.is_file()
            or image_path.suffix.lower()
            not in {
                ".jpg",
                ".jpeg",
                ".png",
            }
        ):
            return

        try:
            with PILImage.open(
                image_path
            ) as source_image:
                source_image.verify()

            image = RLImage(
                str(image_path)
            )

            source_width = float(
                image.imageWidth
            )

            source_height = float(
                image.imageHeight
            )

            if (
                source_width <= 0
                or source_height <= 0
            ):
                return

            max_width = 105 * mm
            max_height = 105 * mm

            scale = min(
                max_width
                / source_width,
                max_height
                / source_height,
            )

            image.drawWidth = (
                source_width
                * scale
            )

            image.drawHeight = (
                source_height
                * scale
            )

            image.hAlign = "CENTER"

        except Exception:
            return

        story.append(
            image
        )

        story.append(
            Spacer(
                1,
                3 * mm,
            )
        )


    @staticmethod
    def _section(
        story: list[object],
        styles: dict[str, ParagraphStyle],
        title: str,
    ) -> None:

        story.append(
            Paragraph(
                escape(
                    title
                ),
                styles[
                    "section_title"
                ],
            )
        )

    @staticmethod
    def _table(
        story: list[object],
        styles: dict[str, ParagraphStyle],
        rows: list[
            tuple[
                str,
                object | None,
            ]
        ],
        *,
        missing: str,
    ) -> None:

        table_data = []

        for label, value in rows:

            table_data.append(
                [
                    Paragraph(
                        escape(
                            str(
                                label
                            )
                        ),
                        ParagraphStyle(
                            "InlineLabel",
                            parent=styles[
                                "body"
                            ],
                            fontName=BOLD_FONT_NAME,
                        ),
                    ),
                    Paragraph(
                        escape(
                            _plain(
                                value,
                                missing=missing,
                            )
                        ),
                        styles[
                            "body"
                        ],
                    ),
                ]
            )

        table = Table(
            table_data,
            colWidths=[
                54 * mm,
                114 * mm,
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
                        HEADER_BACKGROUND,
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.30,
                        BORDER_COLOR,
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

        story.append(
            table
        )


report_pdf_generator = (
    ReportLabPdfGenerator()
)
