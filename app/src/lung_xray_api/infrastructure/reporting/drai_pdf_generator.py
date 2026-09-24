"""Professional medical PDF rendering for persisted Dr.AI advice."""

from __future__ import annotations

from html import escape
from io import BytesIO

from PIL import Image as PILImage
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    Flowable,
    HRFlowable,
    Image as RLImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from lung_xray_api.infrastructure.reporting.reportlab_pdf_generator import (
    BOLD_FONT_NAME,
    REGULAR_FONT_NAME,
    register_report_fonts,
)


TITLE_COLOR = HexColor("#1A365D")
SECTION_COLOR = HexColor("#2B6CB0")
SUBTITLE_COLOR = HexColor("#4A5568")
BODY_COLOR = HexColor("#2D3748")
AUDIT_BORDER_COLOR = HexColor("#A0AEC0")
AUDIT_TEXT_COLOR = HexColor("#718096")
DISCLAIMER_COLOR = HexColor("#C53030")
BAR_BACKGROUND_COLOR = HexColor("#E2E8F0")
VISUAL_BORDER_COLOR = HexColor("#CBD5E0")

DISCLAIMER_VI = (
    "<!> ỨNG DỤNG CHỈ CÓ TÍNH CHẤT THAM KHẢO "
    "VÀ KHÔNG THAY THẾ CHẨN ĐOÁN HOẶC QUYẾT ĐỊNH "
    "ĐIỀU TRỊ CỦA CHUYÊN GIA Y TẾ."
)

DISCLAIMER_EN = (
    "<!> THIS APPLICATION IS FOR REFERENCE ONLY AND DOES NOT "
    "REPLACE DIAGNOSIS OR TREATMENT DECISIONS BY A QUALIFIED "
    "HEALTHCARE PROFESSIONAL."
)


class _BottomAlignedFooter(Flowable):
    """Place the final audit/disclaimer block at the bottom of the last page."""

    def __init__(
        self,
        table: Table,
    ) -> None:
        super().__init__()

        self.table = table
        self._table_height = 0.0

    def wrap(
        self,
        avail_width,
        avail_height,
    ):
        _width, height = self.table.wrap(
            avail_width,
            avail_height,
        )

        self._table_height = height

        if height <= avail_height:
            # Consume all remaining frame height.
            # draw() will place the table at the bottom.
            return avail_width, avail_height

        # Force the flowable to the next page when the footer
        # cannot fit in the remaining space.
        return avail_width, height

    def draw(self) -> None:
        self.table.drawOn(
            self.canv,
            0,
            0,
        )


class _ProbabilityBars(Flowable):
    """Compact deterministic probability bar visualization."""

    ORDER = (
        ("tuberculosis", "Tuberculosis"),
        ("normal", "Normal"),
        ("pneumonia", "Pneumonia"),
    )

    def __init__(
        self,
        probabilities: dict[str, float],
        *,
        width: float = 245,
    ) -> None:
        super().__init__()

        lookup = {
            str(key).strip().casefold(): float(value)
            for key, value in probabilities.items()
        }

        self.rows = []

        for key, label in self.ORDER:
            value = lookup.get(
                key,
                0.0,
            )

            value = max(
                0.0,
                min(
                    1.0,
                    value,
                ),
            )

            self.rows.append(
                (
                    label,
                    value,
                )
            )

        self.width = width
        self.height = 108

    def wrap(
        self,
        avail_width,
        avail_height,
    ):
        del avail_height

        return (
            min(
                self.width,
                avail_width,
            ),
            self.height,
        )

    def draw(self) -> None:
        canvas = self.canv

        width = self.width
        y = self.height - 17

        for label, probability in self.rows:
            percent = (
                probability
                * 100.0
            )

            canvas.setFillColor(
                BODY_COLOR
            )

            canvas.setFont(
                REGULAR_FONT_NAME,
                7.5,
            )

            canvas.drawString(
                0,
                y,
                label,
            )

            canvas.setFont(
                BOLD_FONT_NAME,
                7.5,
            )

            canvas.drawRightString(
                width,
                y,
                f"{percent:.2f}%",
            )

            bar_y = (
                y
                - 11
            )

            canvas.setFillColor(
                BAR_BACKGROUND_COLOR
            )

            canvas.roundRect(
                0,
                bar_y,
                width,
                6,
                3,
                fill=1,
                stroke=0,
            )

            fill_width = (
                width
                * probability
            )

            if fill_width > 0:
                canvas.setFillColor(
                    SECTION_COLOR
                )

                canvas.roundRect(
                    0,
                    bar_y,
                    fill_width,
                    6,
                    3,
                    fill=1,
                    stroke=0,
                )

            y -= 34


class DrAIPdfGenerator:
    """Render persisted Dr.AI report content into a medical PDF."""

    def __init__(self) -> None:
        register_report_fonts()

    @staticmethod
    def _build_styles() -> dict[str, ParagraphStyle]:
        return {
            "title": ParagraphStyle(
                "DrAITitle",
                fontName=BOLD_FONT_NAME,
                fontSize=14,
                leading=17,
                alignment=TA_CENTER,
                textColor=TITLE_COLOR,
                spaceAfter=4,
            ),
            "subtitle": ParagraphStyle(
                "DrAISubtitle",
                fontName=REGULAR_FONT_NAME,
                fontSize=9,
                leading=12,
                alignment=TA_CENTER,
                textColor=SUBTITLE_COLOR,
                spaceAfter=5,
            ),
            "section": ParagraphStyle(
                "DrAISection",
                fontName=BOLD_FONT_NAME,
                fontSize=10,
                leading=13,
                textColor=SECTION_COLOR,
                spaceBefore=9,
                spaceAfter=5,
                keepWithNext=True,
            ),
            "subsection": ParagraphStyle(
                "DrAISubsection",
                fontName=BOLD_FONT_NAME,
                fontSize=9,
                leading=13,
                textColor=BODY_COLOR,
                spaceBefore=5,
                spaceAfter=2,
                keepWithNext=True,
            ),
            "body": ParagraphStyle(
                "DrAIBody",
                fontName=REGULAR_FONT_NAME,
                fontSize=9,
                leading=13,
                textColor=BODY_COLOR,
                spaceAfter=4,
            ),
            "important": ParagraphStyle(
                "DrAIImportant",
                fontName=BOLD_FONT_NAME,
                fontSize=9,
                leading=13,
                textColor=BODY_COLOR,
                spaceAfter=4,
            ),
            "bullet": ParagraphStyle(
                "DrAIBullet",
                fontName=REGULAR_FONT_NAME,
                fontSize=9,
                leading=13,
                textColor=BODY_COLOR,
                leftIndent=12,
                firstLineIndent=-7,
                spaceAfter=3,
            ),
            "admin_label": ParagraphStyle(
                "DrAIAdminLabel",
                fontName=BOLD_FONT_NAME,
                fontSize=7.5,
                leading=9.5,
                textColor=SUBTITLE_COLOR,
                spaceAfter=1,
            ),
            "admin_value": ParagraphStyle(
                "DrAIAdminValue",
                fontName=REGULAR_FONT_NAME,
                fontSize=8.7,
                leading=11.5,
                textColor=BODY_COLOR,
            ),
            "visual_title": ParagraphStyle(
                "DrAIVisualTitle",
                fontName=BOLD_FONT_NAME,
                fontSize=8.5,
                leading=11,
                textColor=TITLE_COLOR,
                spaceAfter=4,
            ),
            "visual_meta": ParagraphStyle(
                "DrAIVisualMeta",
                fontName=REGULAR_FONT_NAME,
                fontSize=7.3,
                leading=9.5,
                textColor=AUDIT_TEXT_COLOR,
                spaceAfter=1,
            ),
            "audit_title": ParagraphStyle(
                "DrAIAuditTitle",
                fontName=BOLD_FONT_NAME,
                fontSize=8,
                leading=10,
                textColor=SUBTITLE_COLOR,
                spaceAfter=2,
            ),
            "audit_body": ParagraphStyle(
                "DrAIAuditBody",
                fontName=REGULAR_FONT_NAME,
                fontSize=7.5,
                leading=9.5,
                textColor=AUDIT_TEXT_COLOR,
                spaceAfter=1,
            ),
            "disclaimer": ParagraphStyle(
                "DrAIDisclaimer",
                fontName=BOLD_FONT_NAME,
                fontSize=8,
                leading=10.5,
                alignment=TA_CENTER,
                textColor=DISCLAIMER_COLOR,
            ),
        }

    @staticmethod
    def _is_section(
        line: str,
    ) -> bool:
        upper = line.upper()

        return (
            upper.startswith("PHẦN ")
            or upper.startswith("PART ")
        )

    @staticmethod
    def _is_technical_section(
        line: str,
    ) -> bool:
        upper = line.upper()

        return (
            "THÔNG TIN TRUY XUẤT KỸ THUẬT HỆ THỐNG"
            in upper
            or "TECHNICAL AUDIT METADATA"
            in upper
        )

    @staticmethod
    def _is_subsection(
        line: str,
    ) -> bool:
        if len(line) < 3:
            return False

        first, dot, rest = line.partition(".")

        return bool(
            dot
            and first.isdigit()
            and rest.strip()
        )

    @staticmethod
    def _split_label_value(
        line: str,
    ) -> tuple[str, str]:
        label, separator, value = line.partition(":")

        if not separator:
            return line.strip(), ""

        return (
            label.strip(),
            value.strip(),
        )

    @staticmethod
    def _find_admin_value(
        admin_lines: list[str],
        *labels: str,
    ) -> str:
        normalized_labels = {
            item.casefold()
            for item in labels
        }

        for line in admin_lines:
            label, value = (
                DrAIPdfGenerator
                ._split_label_value(line)
            )

            if label.casefold() in normalized_labels:
                return value or "Chưa cung cấp"

        return "Chưa cung cấp"

    @staticmethod
    def _admin_cell(
        label: str,
        value: str,
        styles: dict[str, ParagraphStyle],
    ):
        return [
            Paragraph(
                escape(label),
                styles["admin_label"],
            ),
            Paragraph(
                escape(value),
                styles["admin_value"],
            ),
        ]

    def _build_admin_table(
        self,
        *,
        admin_lines: list[str],
        styles: dict[str, ParagraphStyle],
        width: float,
        vietnamese: bool,
    ) -> Table:
        if vietnamese:
            full_name = self._find_admin_value(
                admin_lines,
                "Họ và tên",
            )
            age = self._find_admin_value(
                admin_lines,
                "Tuổi/Năm sinh",
            )
            gender = self._find_admin_value(
                admin_lines,
                "Giới tính",
            )
            phone = self._find_admin_value(
                admin_lines,
                "Số điện thoại",
            )
            body_stats = self._find_admin_value(
                admin_lines,
                "Thể trạng (Cân nặng/Chiều cao)",
            )
            department = self._find_admin_value(
                admin_lines,
                "Khoa",
            )
            exam_date = self._find_admin_value(
                admin_lines,
                "Ngày khám",
            )
            diagnosis = self._find_admin_value(
                admin_lines,
                "Chẩn đoán sơ bộ",
            )

            labels = {
                "full_name": "Họ và tên bệnh nhân",
                "age": "Tuổi / Năm sinh",
                "gender": "Giới tính",
                "phone": "Số điện thoại",
                "body_stats": "Thể trạng",
                "department": "Khoa",
                "exam_date": "Ngày khám",
                "support": "Hỗ trợ chuyên môn",
                "diagnosis": "Chẩn đoán sơ bộ",
            }

            support = "Dr.AI"

        else:
            full_name = self._find_admin_value(
                admin_lines,
                "Full name",
            )
            age = self._find_admin_value(
                admin_lines,
                "Age/Year of birth",
            )
            gender = self._find_admin_value(
                admin_lines,
                "Sex",
            )
            phone = self._find_admin_value(
                admin_lines,
                "Phone",
            )
            body_stats = self._find_admin_value(
                admin_lines,
                "Weight/Height",
            )
            department = self._find_admin_value(
                admin_lines,
                "Department",
            )
            exam_date = self._find_admin_value(
                admin_lines,
                "Examination date",
            )
            diagnosis = self._find_admin_value(
                admin_lines,
                "Preliminary diagnosis",
            )

            labels = {
                "full_name": "Patient name",
                "age": "Age / Year of birth",
                "gender": "Sex",
                "phone": "Phone",
                "body_stats": "Body statistics",
                "department": "Department",
                "exam_date": "Examination date",
                "support": "Professional support",
                "diagnosis": "Preliminary diagnosis",
            }

            support = "Dr.AI"

        column_width = width / 3.0

        rows = [
            [
                self._admin_cell(
                    labels["full_name"],
                    full_name,
                    styles,
                ),
                self._admin_cell(
                    labels["age"],
                    age,
                    styles,
                ),
                self._admin_cell(
                    labels["gender"],
                    gender,
                    styles,
                ),
            ],
            [
                self._admin_cell(
                    labels["phone"],
                    phone,
                    styles,
                ),
                self._admin_cell(
                    labels["body_stats"],
                    body_stats,
                    styles,
                ),
                self._admin_cell(
                    labels["department"],
                    department,
                    styles,
                ),
            ],
            [
                self._admin_cell(
                    labels["exam_date"],
                    exam_date,
                    styles,
                ),
                self._admin_cell(
                    labels["support"],
                    support,
                    styles,
                ),
                "",
            ],
            [
                self._admin_cell(
                    labels["diagnosis"],
                    diagnosis,
                    styles,
                ),
                "",
                "",
            ],
        ]

        table = Table(
            rows,
            colWidths=[
                column_width,
                column_width,
                column_width,
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
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        0,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        10,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        2,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),
                    (
                        "SPAN",
                        (0, 3),
                        (2, 3),
                    ),
                ]
            )
        )

        return table

    @staticmethod
    def _display_section(
        line: str,
        *,
        vietnamese: bool,
    ) -> str:
        upper = line.upper()

        if upper.startswith(
            (
                "PHẦN II:",
                "PART II:",
            )
        ):
            return (
                "II. TÓM TẮT TÌNH TRẠNG VÀ KẾT QUẢ"
                if vietnamese
                else "II. CONDITION SUMMARY AND FINDINGS"
            )

        if upper.startswith(
            (
                "PHẦN III:",
                "PART III:",
            )
        ):
            return (
                "III. HƯỚNG DẪN ĐIỀU TRỊ VÀ DÙNG THUỐC"
                if vietnamese
                else "III. TREATMENT AND MEDICATION GUIDANCE"
            )

        if upper.startswith(
            (
                "PHẦN IV:",
                "PART IV:",
            )
        ):
            return (
                "IV. HƯỚNG DẪN CHẾ ĐỘ DINH DƯỠNG & SINH HOẠT"
                if vietnamese
                else "IV. NUTRITION AND DAILY ACTIVITIES"
            )

        if upper.startswith(
            (
                "PHẦN V:",
                "PART V:",
            )
        ):
            return (
                "V. DẤU HIỆU CẦN TÁI KHÁM NGAY LẬP TỨC"
                if vietnamese
                else "V. SIGNS REQUIRING URGENT MEDICAL REVIEW"
            )

        return line

    @staticmethod
    def _normalize_important_line(
        line: str,
        *,
        vietnamese: bool,
    ) -> str:
        if not vietnamese:
            return line

        if line.startswith("Risk level:"):
            return (
                "Mức cảnh báo AI:"
                + line[len("Risk level:"):]
            )

        if line.startswith("Summary conclusion:"):
            return (
                "Kết luận tóm tắt:"
                + line[len("Summary conclusion:"):]
            )

        if line.startswith("Summary recommendation:"):
            return (
                "Khuyến nghị tóm tắt:"
                + line[
                    len("Summary recommendation:"):
                ]
            )

        return line

    @staticmethod
    def _normalize_metadata_label(
        label: str,
        *,
        vietnamese: bool,
    ) -> str:
        if vietnamese:
            mapping = {
                "Mã báo cáo tư vấn": "Mã báo cáo",
                "Nguồn đầu vào": "Nguồn",
                "Mô hình phân tích": "Model",
            }
        else:
            mapping = {
                "Advice report code": "Report code",
                "Input source": "Source",
                "Analysis model": "Model",
            }

        return mapping.get(
            label,
            label,
        )

    def _build_footer(
        self,
        *,
        metadata_lines: list[str],
        styles: dict[str, ParagraphStyle],
        width: float,
        vietnamese: bool,
    ) -> _BottomAlignedFooter:
        metadata_items: list[str] = []

        for line in metadata_lines:
            label, value = self._split_label_value(
                line
            )

            if not value:
                continue

            label = self._normalize_metadata_label(
                label,
                vietnamese=vietnamese,
            )

            metadata_items.append(
                f"{label}: {value}"
            )

        first_line = " | ".join(
            metadata_items[:3]
        )

        second_line = " | ".join(
            metadata_items[3:6]
        )

        if vietnamese:
            audit_title = (
                "THÔNG TIN TRUY XUẤT KỸ THUẬT HỆ THỐNG "
                "(Technical Audit Metadata)"
            )
            disclaimer = DISCLAIMER_VI
        else:
            audit_title = (
                "SYSTEM TECHNICAL AUDIT METADATA "
                "(Technical Audit Metadata)"
            )
            disclaimer = DISCLAIMER_EN

        rows = [
            [
                Paragraph(
                    escape(audit_title),
                    styles["audit_title"],
                )
            ],
        ]

        if first_line:
            rows.append(
                [
                    Paragraph(
                        escape(first_line),
                        styles["audit_body"],
                    )
                ]
            )

        if second_line:
            rows.append(
                [
                    Paragraph(
                        escape(second_line),
                        styles["audit_body"],
                    )
                ]
            )

        rows.append(
            [
                Paragraph(
                    escape(disclaimer),
                    styles["disclaimer"],
                )
            ]
        )

        footer_table = Table(
            rows,
            colWidths=[width],
        )

        footer_table.setStyle(
            TableStyle(
                [
                    (
                        "LINEABOVE",
                        (0, 0),
                        (-1, 0),
                        0.6,
                        AUDIT_BORDER_COLOR,
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        0,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        0,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, 0),
                        5,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -2),
                        2,
                    ),
                    (
                        "TOPPADDING",
                        (0, -1),
                        (-1, -1),
                        6,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, -1),
                        (-1, -1),
                        0,
                    ),
                ]
            )
        )

        return _BottomAlignedFooter(
            footer_table
        )

    @staticmethod
    def _prepare_xray_preview(
        image_bytes: bytes | None,
    ) -> tuple[bytes, int, int] | None:
        if not image_bytes:
            return None

        try:
            with PILImage.open(
                BytesIO(image_bytes)
            ) as source:
                image = source.convert(
                    "RGB"
                )

                image.thumbnail(
                    (900, 900),
                    PILImage.Resampling.LANCZOS,
                )

                width, height = (
                    image.size
                )

                output = BytesIO()

                image.save(
                    output,
                    format="JPEG",
                    quality=88,
                    optimize=True,
                )

                return (
                    output.getvalue(),
                    width,
                    height,
                )

        except OSError:
            return None

    def _build_section_ii_visual_block(
        self,
        *,
        xray_image_bytes: bytes | None,
        xray_filename: str | None,
        analysis_code: str | None,
        analysis_timestamp: str | None,
        probabilities: dict[str, float] | None,
        styles: dict[str, ParagraphStyle],
        width: float,
        vietnamese: bool,
    ) -> Table | None:
        has_image = bool(
            xray_image_bytes
        )

        has_probabilities = bool(
            probabilities
        )

        if (
            not has_image
            and not has_probabilities
            and not analysis_code
            and not analysis_timestamp
            and not xray_filename
        ):
            return None

        left_width = (
            width
            * 0.41
        )

        right_width = (
            width
            - left_width
        )

        left_story: list[object] = [
            Paragraph(
                (
                    "\u1ea2nh X-quang"
                    if vietnamese
                    else "X-ray preview"
                ),
                styles["visual_title"],
            )
        ]

        preview = (
            self._prepare_xray_preview(
                xray_image_bytes
            )
        )

        if preview is not None:
            (
                preview_bytes,
                image_width,
                image_height,
            ) = preview

            max_width = (
                left_width
                - 12
            )

            max_height = 150

            scale = min(
                max_width
                / image_width,
                max_height
                / image_height,
            )

            xray_image = RLImage(
                BytesIO(
                    preview_bytes
                ),
                width=(
                    image_width
                    * scale
                ),
                height=(
                    image_height
                    * scale
                ),
            )

            left_story.append(
                xray_image
            )

        else:
            left_story.append(
                Paragraph(
                    (
                        "Kh\u00f4ng c\u00f3 "
                        "\u1ea3nh X-quang "
                        "\u0111\u1ec3 xem tr\u01b0\u1edbc."
                        if vietnamese
                        else (
                            "No X-ray preview "
                            "is available."
                        )
                    ),
                    styles["visual_meta"],
                )
            )

        metadata_parts = []

        if analysis_code:
            metadata_parts.append(
                (
                    "M\u00e3 ph\u00e2n t\u00edch"
                    if vietnamese
                    else "Analysis"
                )
                + ": "
                + str(
                    analysis_code
                )
            )

        if analysis_timestamp:
            metadata_parts.append(
                (
                    "Th\u1eddi gian"
                    if vietnamese
                    else "Time"
                )
                + ": "
                + str(
                    analysis_timestamp
                )
            )

        if xray_filename:
            metadata_parts.append(
                (
                    "T\u1ec7p"
                    if vietnamese
                    else "File"
                )
                + ": "
                + str(
                    xray_filename
                )
            )

        for item in metadata_parts:
            left_story.append(
                Paragraph(
                    escape(item),
                    styles["visual_meta"],
                )
            )

        right_story: list[object] = [
            Paragraph(
                (
                    "X\u00e1c su\u1ea5t "
                    "ph\u00e2n lo\u1ea1i "
                    "(Probabilities)"
                    if vietnamese
                    else "Probabilities"
                ),
                styles["visual_title"],
            )
        ]

        if probabilities:
            right_story.append(
                _ProbabilityBars(
                    probabilities,
                    width=(
                        right_width
                        - 14
                    ),
                )
            )

            right_story.append(
                Paragraph(
                    (
                        "Thanh bi\u1ec3u di\u1ec5n "
                        "x\u00e1c su\u1ea5t "
                        "\u0111\u1ea7u ra c\u1ee7a "
                        "m\u00f4 h\u00ecnh; "
                        "kh\u00f4ng ph\u1ea3i "
                        "x\u00e1c su\u1ea5t "
                        "m\u1eafc b\u1ec7nh."
                        if vietnamese
                        else (
                            "Bars represent model "
                            "output probabilities, "
                            "not probabilities of disease."
                        )
                    ),
                    styles["visual_meta"],
                )
            )

        else:
            right_story.append(
                Paragraph(
                    (
                        "Ch\u01b0a c\u00f3 "
                        "d\u1eef li\u1ec7u "
                        "x\u00e1c su\u1ea5t."
                        if vietnamese
                        else (
                            "Probability data "
                            "is unavailable."
                        )
                    ),
                    styles["visual_meta"],
                )
            )

        table = Table(
            [
                [
                    left_story,
                    right_story,
                ]
            ],
            colWidths=[
                left_width,
                right_width,
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
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.6,
                        VISUAL_BORDER_COLOR,
                    ),
                    (
                        "LINEAFTER",
                        (0, 0),
                        (0, -1),
                        0.5,
                        VISUAL_BORDER_COLOR,
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        8,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        8,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        7,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        7,
                    ),
                ]
            )
        )

        return table

    def generate_bytes(
        self,
        *,
        advice_text: str,
        xray_image_bytes: bytes | None = None,
        xray_filename: str | None = None,
        analysis_code: str | None = None,
        analysis_timestamp: str | None = None,
        probabilities: dict[str, float] | None = None,
    ) -> bytes:
        text = str(
            advice_text or ""
        ).strip()

        if not text:
            raise ValueError(
                "Dr.AI advice text cannot be empty."
            )

        lines = [
            item.strip()
            for item in text.splitlines()
        ]

        if not lines:
            raise ValueError(
                "Dr.AI advice text cannot be empty."
            )

        vietnamese = (
            lines[0]
            .upper()
            .startswith("PHIẾU")
        )

        styles = self._build_styles()

        buffer = BytesIO()

        document = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=35,
            leftMargin=35,
            topMargin=35,
            bottomMargin=35,
            title=(
                "Phiếu Tư Vấn và Hướng Dẫn "
                "Y Tế Sau Khám"
            ),
            author="Lung X-ray AI / Dr.AI",
        )

        story: list[object] = []

        title = lines[0]

        subtitle = (
            (
                "(D\u00f9ng cho b\u1ec7nh nh\u00e2n "
                "ngo\u1ea1i tr\u00fa / sau khi "
                "k\u1ebft th\u00fac bu\u1ed5i kh\u00e1m)"
            )
            if vietnamese
            else (
                "(For outpatients / "
                "after completion of the visit)"
            )
        )

        story.append(
            Paragraph(
                escape(title),
                styles["title"],
            )
        )

        story.append(
            Paragraph(
                escape(subtitle),
                styles["subtitle"],
            )
        )

        story.append(
            HRFlowable(
                width="100%",
                thickness=1.5,
                color=SECTION_COLOR,
                spaceBefore=1,
                spaceAfter=8,
            )
        )

        admin_start = None
        body_start = None
        technical_start = None
        disclaimer_index = None

        for index, line in enumerate(lines):
            upper = line.upper()

            if (
                admin_start is None
                and (
                    "PHẦN I:" in upper
                    or "PART I:" in upper
                )
            ):
                admin_start = index
                continue

            if (
                body_start is None
                and (
                    "PHẦN II:" in upper
                    or "PART II:" in upper
                )
            ):
                body_start = index
                continue

            if (
                technical_start is None
                and self._is_technical_section(
                    line
                )
            ):
                technical_start = index
                continue

            if line.startswith("<!>"):
                disclaimer_index = index

        if (
            admin_start is not None
            and body_start is not None
        ):
            admin_lines = [
                line
                for line in lines[
                    admin_start + 1:
                    body_start
                ]
                if line
            ]
        else:
            admin_lines = []

        story.append(
            Paragraph(
                (
                    "I. THÔNG TIN HÀNH CHÍNH"
                    if vietnamese
                    else (
                        "I. ADMINISTRATIVE "
                        "INFORMATION"
                    )
                ),
                styles["section"],
            )
        )

        story.append(
            self._build_admin_table(
                admin_lines=admin_lines,
                styles=styles,
                width=document.width,
                vietnamese=vietnamese,
            )
        )

        if body_start is None:
            body_start = 2

        body_end = (
            technical_start
            if technical_start is not None
            else (
                disclaimer_index
                if disclaimer_index is not None
                else len(lines)
            )
        )

        follow_up_section_added = False

        for raw_line in lines[
            body_start:
            body_end
        ]:
            line = raw_line.strip()

            if not line:
                story.append(
                    Spacer(
                        1,
                        3,
                    )
                )
                continue

            if self._is_technical_section(
                line
            ):
                continue

            if self._is_section(
                line
            ):
                display = self._display_section(
                    line,
                    vietnamese=vietnamese,
                )

                story.append(
                    Paragraph(
                        escape(display),
                        styles["section"],
                    )
                )

                if display.startswith("II."):
                    visual_block = (
                        self._build_section_ii_visual_block(
                            xray_image_bytes=(
                                xray_image_bytes
                            ),
                            xray_filename=(
                                xray_filename
                            ),
                            analysis_code=(
                                analysis_code
                            ),
                            analysis_timestamp=(
                                analysis_timestamp
                            ),
                            probabilities=(
                                probabilities
                            ),
                            styles=styles,
                            width=document.width,
                            vietnamese=vietnamese,
                        )
                    )

                    if visual_block is not None:
                        story.append(
                            visual_block
                        )

                        story.append(
                            Spacer(
                                1,
                                6,
                            )
                        )

                continue

            is_follow_up = (
                line.startswith(
                    "Mốc tái khám đề xuất"
                )
                or line.startswith(
                    "Suggested follow-up timing"
                )
            )

            if (
                is_follow_up
                and not follow_up_section_added
            ):
                follow_up_section_added = True

                story.append(
                    Paragraph(
                        (
                            "VI. LỊCH HẸN CẬP NHẬT "
                            "SỨC KHỎE"
                            if vietnamese
                            else (
                                "VI. HEALTH UPDATE "
                                "AND FOLLOW-UP"
                            )
                        ),
                        styles["section"],
                    )
                )

                _label, value = (
                    self._split_label_value(
                        line
                    )
                )

                if vietnamese:
                    line = (
                        "Ngày / mốc cập nhật dự kiến: "
                        + (
                            value
                            or "Chưa cung cấp"
                        )
                    )

                story.append(
                    Paragraph(
                        escape(line),
                        styles["body"],
                    )
                )

                continue

            if self._is_subsection(
                line
            ):
                story.append(
                    Paragraph(
                        escape(line),
                        styles["subsection"],
                    )
                )

                continue

            if line.startswith("- "):
                story.append(
                    Paragraph(
                        "• "
                        + escape(line[2:]),
                        styles["bullet"],
                    )
                )

                continue

            if line.startswith("•"):
                story.append(
                    Paragraph(
                        escape(line),
                        styles["bullet"],
                    )
                )

                continue

            if line.startswith(
                (
                    "Risk level:",
                    "Summary conclusion:",
                    "Summary recommendation:",
                )
            ):
                display = (
                    self._normalize_important_line(
                        line,
                        vietnamese=vietnamese,
                    )
                )

                story.append(
                    Paragraph(
                        escape(display),
                        styles["important"],
                    )
                )

                continue

            story.append(
                Paragraph(
                    escape(line),
                    styles["body"],
                )
            )

        if (
            technical_start is not None
        ):
            technical_end = (
                disclaimer_index
                if disclaimer_index is not None
                else len(lines)
            )

            metadata_lines = [
                line
                for line in lines[
                    technical_start + 1:
                    technical_end
                ]
                if line
            ]
        else:
            metadata_lines = []

        story.append(
            self._build_footer(
                metadata_lines=metadata_lines,
                styles=styles,
                width=document.width,
                vietnamese=vietnamese,
            )
        )

        document.build(
            story
        )

        pdf_bytes = buffer.getvalue()
        buffer.close()

        if not pdf_bytes.startswith(
            b"%PDF-"
        ):
            raise RuntimeError(
                "Dr.AI PDF generation produced "
                "invalid data."
            )

        return pdf_bytes


drai_pdf_generator = DrAIPdfGenerator()