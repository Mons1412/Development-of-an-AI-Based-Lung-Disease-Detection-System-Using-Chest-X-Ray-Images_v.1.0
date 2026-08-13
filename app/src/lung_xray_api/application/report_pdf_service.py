"""Generate downloadable PDF reports from persisted analysis records.

The service intentionally builds the document from a persisted analysis record
and its derived thumbnail. It never accepts prediction values from the browser,
and it never reads the original full-resolution upload.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Any, cast
from xml.sax.saxutils import escape

from PIL import Image as PillowImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Circle, Drawing, Line, Rect, String, Wedge
from reportlab.platypus import (
    Image,
    Flowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from lung_xray_api.application.report_filename import (
    REPORT_TITLE,
    format_vietnam_datetime,
    patient_source_label,
    report_case_label,
)
from lung_xray_api.application.report_views import normalize_report_view_ids
from lung_xray_api.infrastructure.persistence.records import AnalysisHistoryRecord

_CLASS_LABELS = {
    "normal": "Bình thường",
    "pneumonia": "Viêm phổi",
    "tuberculosis": "Lao phổi",
}

_TEAM_MEMBERS = (
    "Lê Đoàn Anh Tuấn - 2200010939",
    "Võ Nhật Nguyên - 2200004486",
    "Vô Văn Nghĩa - 2200000318",
)

_REFERENCE_NOTICE = (
    "Nội dung chuyên môn đang chờ duyệt. Bản production hiện chỉ cung cấp "
    "thông tin về đầu ra mô hình, không bao gồm hướng dẫn thuốc, liều lượng "
    "hoặc thay đổi điều trị."
)

_DEFAULT_DISCLAIMER = (
    "Kết quả phân loại của mô hình chỉ phục vụ mục đích học thuật và tham khảo; "
    "không thay thế đánh giá, chẩn đoán hoặc điều trị của nhân viên y tế."
)

_BLUE = colors.HexColor("#1D4ED8")
_BLUE_SOFT = colors.HexColor("#EEF5FF")
_BORDER = colors.HexColor("#D6E0EE")
_TEXT = colors.HexColor("#142033")
_MUTED = colors.HexColor("#667085")
_WARNING_BG = colors.HexColor("#FFF8EB")
_WARNING_BORDER = colors.HexColor("#E8C98E")
_TABLE_HEADER = colors.HexColor("#EAF2FF")
_CLASS_COLORS = {
    "normal": colors.HexColor("#16866B"),
    "pneumonia": colors.HexColor("#D98200"),
    "tuberculosis": colors.HexColor("#D24B45"),
}


@dataclass(frozen=True)
class PdfAsset:
    content: bytes
    media_type: str


class ReportPdfGenerationError(RuntimeError):
    """A PDF could not be generated safely in the local runtime."""


def generate_analysis_pdf(
    *,
    record: AnalysisHistoryRecord,
    source_titles: dict[str, str],
    logo: PdfAsset | None,
    thumbnail: PdfAsset | None,
    selected_views: tuple[str, ...] | None = None,
) -> bytes:
    """Build a real application/pdf document fully in memory."""

    regular_font, bold_font = _register_unicode_fonts()
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=17 * mm,
        rightMargin=17 * mm,
        topMargin=15 * mm,
        bottomMargin=16 * mm,
        title=REPORT_TITLE,
        author="Đồ án Lung X-ray AI - Đại học Nguyễn Tất Thành",
        subject="Báo cáo học thuật - không dùng để chẩn đoán",
        creator="Hệ thống phân loại ảnh X-quang phổi bằng MobileNetV2",
    )

    styles = _build_styles(regular_font, bold_font)
    story: list[object] = []
    story.extend(_build_header(styles, logo))
    story.append(Spacer(1, 4 * mm))
    story.extend(_build_case_section(record, styles))
    story.append(Spacer(1, 4 * mm))
    story.extend(_build_thumbnail_section(thumbnail, styles))
    story.append(Spacer(1, 4 * mm))
    story.extend(
        _build_result_section(
            record,
            styles,
            bold_font,
            regular_font,
            normalize_report_view_ids(selected_views),
        )
    )
    story.append(Spacer(1, 4 * mm))
    story.extend(_build_reference_section(record, source_titles, styles))
    story.append(Spacer(1, 3.5 * mm))
    story.extend(_build_disclaimer(record, styles))
    story.append(Spacer(1, 4 * mm))
    story.extend(_build_team_section(styles))

    try:
        document.build(
            cast(list[Flowable], story),
            onFirstPage=lambda canvas, doc: _draw_page_footer(
                canvas, doc, regular_font, record.id
            ),
            onLaterPages=lambda canvas, doc: _draw_page_footer(
                canvas, doc, regular_font, record.id
            ),
        )
    except Exception as exc:  # ReportLab raises several backend-specific exceptions.
        raise ReportPdfGenerationError("Không thể tạo file PDF") from exc

    pdf_bytes = buffer.getvalue()
    if not pdf_bytes.startswith(b"%PDF-"):
        raise ReportPdfGenerationError("Nội dung PDF được tạo không hợp lệ")
    return pdf_bytes


def _build_styles(regular_font: str, bold_font: str) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "eyebrow": ParagraphStyle(
            "ReportEyebrow",
            parent=base["Normal"],
            fontName=bold_font,
            fontSize=8.5,
            leading=11,
            textColor=_BLUE,
            spaceAfter=1.5 * mm,
        ),
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base["Title"],
            fontName=bold_font,
            fontSize=16.5,
            leading=20,
            textColor=_TEXT,
            alignment=TA_LEFT,
            spaceAfter=1.5 * mm,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle",
            parent=base["Normal"],
            fontName=regular_font,
            fontSize=9.5,
            leading=12,
            textColor=_MUTED,
        ),
        "section": ParagraphStyle(
            "ReportSection",
            parent=base["Heading2"],
            fontName=bold_font,
            fontSize=12.5,
            leading=16,
            textColor=_TEXT,
            spaceAfter=2.2 * mm,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "ReportBody",
            parent=base["BodyText"],
            fontName=regular_font,
            fontSize=9.2,
            leading=13,
            textColor=_TEXT,
        ),
        "body_bold": ParagraphStyle(
            "ReportBodyBold",
            parent=base["BodyText"],
            fontName=bold_font,
            fontSize=9.2,
            leading=13,
            textColor=_TEXT,
        ),
        "small": ParagraphStyle(
            "ReportSmall",
            parent=base["BodyText"],
            fontName=regular_font,
            fontSize=7.8,
            leading=10.5,
            textColor=_MUTED,
        ),
        "callout": ParagraphStyle(
            "ReportCallout",
            parent=base["BodyText"],
            fontName=regular_font,
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#704600"),
        ),
        "disclaimer": ParagraphStyle(
            "ReportDisclaimer",
            parent=base["BodyText"],
            fontName=regular_font,
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#214C91"),
        ),
        "center_small": ParagraphStyle(
            "ReportCenterSmall",
            parent=base["BodyText"],
            fontName=regular_font,
            fontSize=7.8,
            leading=10.5,
            textColor=_MUTED,
            alignment=TA_CENTER,
        ),
    }


def _build_header(styles: dict[str, ParagraphStyle], logo: PdfAsset | None) -> list[object]:
    logo_flowable: object = Spacer(18 * mm, 18 * mm)
    if logo is not None:
        logo_flowable = _reportlab_image(logo.content, max_width=18 * mm, max_height=18 * mm)

    heading = [
        Paragraph("BÁO CÁO HỌC THUẬT - KHÔNG DÙNG ĐỂ CHẨN ĐOÁN", styles["eyebrow"]),
        Paragraph(REPORT_TITLE, styles["title"]),
        Paragraph("Hệ thống phân loại ảnh X-quang phổi bằng MobileNetV2 · Đại học Nguyễn Tất Thành", styles["subtitle"]),
    ]
    header = Table(
        [[logo_flowable, heading]],
        colWidths=[24 * mm, 148 * mm],
        hAlign="LEFT",
    )
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
                ("LINEBELOW", (0, 0), (-1, -1), 1.3, _BLUE),
            ]
        )
    )
    return [header]


def _build_case_section(
    record: AnalysisHistoryRecord,
    styles: dict[str, ParagraphStyle],
) -> list[object]:
    rows: list[list[object]] = []

    def row(left_label: str, left_value: object, right_label: str, right_value: object) -> None:
        rows.append(
            [
                _label_value(left_label, left_value, styles),
                _label_value(right_label, right_value, styles),
            ]
        )

    row(
        "Mã lần phân tích",
        record.id,
        "Thời điểm phân tích",
        format_vietnam_datetime(record.analyzed_at),
    )
    if record.is_anonymous_sample:
        row(
            "Loại ca",
            "Ca ẩn danh / ảnh minh họa",
            "Nguồn thông tin",
            patient_source_label(record.patient_name_source),
        )
    else:
        row(
            "Tên người bệnh / tên ca",
            record.patient_display_name or "Không cung cấp",
            "Mã người bệnh / mã ca",
            record.patient_code or "Không cung cấp",
        )
        row(
            "Nguồn thông tin",
            patient_source_label(record.patient_name_source),
            "Tệp ảnh ban đầu",
            record.original_filename,
        )

    if record.is_anonymous_sample:
        row("Tệp ảnh ban đầu", record.original_filename, "Phiên bản mô hình", record.model_version)
    else:
        row(
            "Phiên bản mô hình",
            record.model_version,
            "Phiên bản kho tri thức",
            record.knowledge_base_version or "Không khả dụng",
        )

    if record.is_anonymous_sample:
        row(
            "Phiên bản kho tri thức",
            record.knowledge_base_version or "Không khả dụng",
            "Thời gian xử lý",
            f"{record.processing_time_ms} ms",
        )
    else:
        row(
            "Thời gian xử lý",
            f"{record.processing_time_ms} ms",
            "Nhãn ca báo cáo",
            report_case_label(record),
        )

    table = Table(rows, colWidths=[86 * mm, 86 * mm], hAlign="LEFT")
    table.setStyle(_metadata_table_style())
    return [Paragraph("Thông tin ca phân tích", styles["section"]), table]

def _build_thumbnail_section(
    thumbnail: PdfAsset | None,
    styles: dict[str, ParagraphStyle],
) -> list[object]:
    elements: list[object] = [Paragraph("Ảnh X-quang đã phân tích", styles["section"])]
    if thumbnail is None:
        elements.append(
            Paragraph(
                "Thumbnail không khả dụng. Báo cáo vẫn sử dụng dữ liệu phân tích đã lưu trong SQLite.",
                styles["small"],
            )
        )
        return elements

    image = _reportlab_image(thumbnail.content, max_width=78 * mm, max_height=52 * mm)
    caption = Paragraph(
        "Ảnh xem trước đã được tái mã hóa và giảm kích thước; hệ thống không lưu ảnh gốc đầy đủ.",
        styles["center_small"],
    )
    frame = Table([[image], [caption]], colWidths=[92 * mm], hAlign="CENTER")
    frame.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BOX", (0, 0), (-1, 0), 0.7, _BORDER),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F7FAFE")),
                ("TOPPADDING", (0, 0), (-1, 0), 3 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 3 * mm),
                ("TOPPADDING", (0, 1), (-1, 1), 2 * mm),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 0),
            ]
        )
    )
    elements.append(KeepTogether(frame))
    return elements


def _build_result_section(
    record: AnalysisHistoryRecord,
    styles: dict[str, ParagraphStyle],
    bold_font: str,
    regular_font: str,
    selected_views: tuple[str, ...],
) -> list[object]:
    top_probability = getattr(record, f"{record.predicted_label}_probability") * 100
    result_cards = Table(
        [
            [
                _label_value(
                    "Kết quả phân loại của mô hình",
                    _CLASS_LABELS[record.predicted_label],
                    styles,
                ),
                _label_value(
                    "Xác suất đầu ra cao nhất",
                    f"{top_probability:.2f}%",
                    styles,
                ),
            ],
            [
                _label_value("Nhãn kỹ thuật (API)", record.predicted_label, styles),
                _label_value(
                    "Phạm vi",
                    "Phân loại học thuật trong ba lớp đã công bố",
                    styles,
                ),
            ],
        ],
        colWidths=[86 * mm, 86 * mm],
    )
    result_cards.setStyle(_metadata_table_style())

    probability_rows: list[list[object]] = [
        [
            Paragraph("Lớp phân loại", styles["body_bold"]),
            Paragraph("Nhãn kỹ thuật", styles["body_bold"]),
            Paragraph("Xác suất đầu ra", styles["body_bold"]),
        ]
    ]
    bar_rows: list[list[object]] = []
    for label in ("normal", "pneumonia", "tuberculosis"):
        probability = getattr(record, f"{label}_probability")
        probability_rows.append(
            [
                Paragraph(escape(_CLASS_LABELS[label]), styles["body"]),
                Paragraph(escape(label), styles["body"]),
                Paragraph(f"{probability * 100:.2f}%", styles["body"]),
            ]
        )
        filled = max(0.6 * mm, 78 * mm * probability)
        remaining = max(0.6 * mm, 78 * mm - filled)
        bar = Table([["", ""]], colWidths=[filled, remaining], rowHeights=[4.2 * mm])
        bar.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, 0), _CLASS_COLORS[label]),
                    ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#E7EDF5")),
                    ("BOX", (0, 0), (-1, -1), 0.3, _BORDER),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        bar_rows.append(
            [
                Paragraph(escape(_CLASS_LABELS[label]), styles["small"]),
                bar,
                Paragraph(f"{probability * 100:.2f}%", styles["body_bold"]),
            ]
        )

    bar_table = Table(bar_rows, colWidths=[38 * mm, 80 * mm, 28 * mm], hAlign="LEFT")
    bar_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 1.2 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.2 * mm),
            ]
        )
    )

    probability_table = Table(
        probability_rows,
        colWidths=[66 * mm, 50 * mm, 56 * mm],
        repeatRows=1,
    )
    probability_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _TABLE_HEADER),
                ("TEXTCOLOR", (0, 0), (-1, -1), _TEXT),
                ("FONTNAME", (0, 0), (-1, 0), bold_font),
                ("FONTNAME", (0, 1), (-1, -1), regular_font),
                ("FONTSIZE", (0, 0), (-1, -1), 8.8),
                ("GRID", (0, 0), (-1, -1), 0.55, _BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 2.2 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2 * mm),
            ]
        )
    )

    elements: list[object] = [
        Paragraph("Kết quả phân loại ảnh X-quang phổi", styles["section"]),
        result_cards,
        Spacer(1, 2.6 * mm),
    ]
    if "probability-bars" in selected_views:
        elements.extend(
            [
                Paragraph("Thanh xác suất đầu ra", styles["body_bold"]),
                Spacer(1, 1.2 * mm),
                bar_table,
                Spacer(1, 3 * mm),
            ]
        )
    if "column-chart" in selected_views:
        elements.extend(
            [
                Paragraph("Biểu đồ cột", styles["body_bold"]),
                Spacer(1, 1.2 * mm),
                _build_column_chart(record, bold_font, regular_font),
                Spacer(1, 3 * mm),
            ]
        )
    if "donut-chart" in selected_views:
        elements.extend(
            [
                Paragraph("Biểu đồ tròn", styles["body_bold"]),
                Spacer(1, 1.2 * mm),
                _build_donut_chart(record, styles, bold_font, regular_font),
                Spacer(1, 3 * mm),
            ]
        )
    if "data-table" in selected_views:
        elements.extend(
            [
                Paragraph("Bảng số liệu của ba lớp", styles["body_bold"]),
                Spacer(1, 1.2 * mm),
                probability_table,
            ]
        )
    return elements


def _probability_entries(record: AnalysisHistoryRecord) -> tuple[tuple[str, float], ...]:
    return tuple(
        (label, max(0.0, min(1.0, getattr(record, f"{label}_probability"))))
        for label in ("normal", "pneumonia", "tuberculosis")
    )


def _build_column_chart(
    record: AnalysisHistoryRecord,
    bold_font: str,
    regular_font: str,
) -> Drawing:
    width = 172 * mm
    height = 76 * mm
    drawing = Drawing(width, height)
    baseline = 15 * mm
    plot_height = 46 * mm
    left = 20 * mm
    plot_width = 136 * mm
    bar_width = 24 * mm
    spacing = (plot_width - 3 * bar_width) / 4

    drawing.add(Line(left, baseline, left + plot_width, baseline, strokeColor=_BORDER, strokeWidth=1))
    for index, (label, probability) in enumerate(_probability_entries(record)):
        bar_height = probability * plot_height
        x = left + spacing + index * (bar_width + spacing)
        drawing.add(
            Rect(
                x,
                baseline,
                bar_width,
                bar_height,
                rx=2 * mm,
                ry=2 * mm,
                fillColor=cast(Any, _CLASS_COLORS[label]),
                strokeColor=cast(Any, None),
            )
        )
        drawing.add(
            String(
                x + bar_width / 2,
                baseline + bar_height + 3 * mm,
                f"{probability * 100:.2f}%",
                textAnchor="middle",
                fontName=bold_font,
                fontSize=8.2,
                fillColor=_TEXT,
            )
        )
        drawing.add(
            String(
                x + bar_width / 2,
                7 * mm,
                _CLASS_LABELS[label],
                textAnchor="middle",
                fontName=regular_font,
                fontSize=7.5,
                fillColor=_MUTED,
            )
        )
    return drawing


def _build_donut_chart(
    record: AnalysisHistoryRecord,
    styles: dict[str, ParagraphStyle],
    bold_font: str,
    regular_font: str,
) -> Table:
    drawing = Drawing(78 * mm, 72 * mm)
    center_x = 36 * mm
    center_y = 36 * mm
    outer_radius = 25 * mm
    drawing.add(
        Circle(
            center_x,
            center_y,
            outer_radius,
            fillColor=colors.HexColor("#E7EDF5"),
            strokeColor=None,
        )
    )
    start_angle = 90.0
    entries = _probability_entries(record)
    for label, probability in entries:
        end_angle = start_angle - probability * 360
        if probability > 0:
            drawing.add(
                Wedge(
                    center_x,
                    center_y,
                    outer_radius,
                    outer_radius,
                    end_angle,
                    start_angle,
                    fillColor=_CLASS_COLORS[label],
                    strokeColor=colors.white,
                    strokeWidth=0.8,
                )
            )
        start_angle = end_angle
    drawing.add(Circle(center_x, center_y, 14 * mm, fillColor=colors.white, strokeColor=None))
    predicted_probability = getattr(record, f"{record.predicted_label}_probability") * 100
    drawing.add(
        String(
            center_x,
            center_y + 3 * mm,
            _CLASS_LABELS[record.predicted_label],
            textAnchor="middle",
            fontName=regular_font,
            fontSize=7.4,
            fillColor=_MUTED,
        )
    )
    drawing.add(
        String(
            center_x,
            center_y - 3.5 * mm,
            f"{predicted_probability:.2f}%",
            textAnchor="middle",
            fontName=bold_font,
            fontSize=10,
            fillColor=_TEXT,
        )
    )

    legend_rows: list[list[object]] = []
    for label, probability in entries:
        legend_rows.append(
            [
                "",
                Paragraph(escape(_CLASS_LABELS[label]), styles["body_bold"]),
                Paragraph(f"{probability * 100:.2f}%", styles["body_bold"]),
            ]
        )
    legend = Table(legend_rows, colWidths=[5 * mm, 47 * mm, 22 * mm])
    legend_style = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.45, _BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, _BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 2.4 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2.4 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 2.2 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2 * mm),
        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
    ]
    for index, (label, _probability) in enumerate(entries):
        legend_style.append(("BACKGROUND", (0, index), (0, index), _CLASS_COLORS[label]))
    legend.setStyle(TableStyle(legend_style))

    layout = Table([[drawing, legend]], colWidths=[82 * mm, 90 * mm])
    layout.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return layout

def _build_reference_section(
    record: AnalysisHistoryRecord,
    source_titles: dict[str, str],
    styles: dict[str, ParagraphStyle],
) -> list[object]:
    notice = Table(
        [[Paragraph(escape(_REFERENCE_NOTICE), styles["callout"])]],
        colWidths=[172 * mm],
    )
    notice.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _WARNING_BG),
                ("BOX", (0, 0), (-1, -1), 0.7, _WARNING_BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
            ]
        )
    )

    elements: list[object] = [
        Paragraph("Nguồn dữ liệu và thông tin tham chiếu", styles["section"]),
        notice,
        Spacer(1, 3 * mm),
        Paragraph("Nguồn tham chiếu kỹ thuật đã ghi nhận", styles["body_bold"]),
        Spacer(1, 1.5 * mm),
    ]
    if not record.reference_source_ids:
        elements.append(Paragraph("Không có mã nguồn tham chiếu được ghi nhận.", styles["body"]))
        return elements

    for source_id in record.reference_source_ids:
        title = source_titles.get(source_id, "Nguồn tham chiếu kỹ thuật đã ghi nhận")
        elements.append(
            Paragraph(
                f"• <b>{escape(source_id)}</b> - {escape(title)}",
                styles["body"],
            )
        )
    return elements


def _build_disclaimer(
    record: AnalysisHistoryRecord,
    styles: dict[str, ParagraphStyle],
) -> list[object]:
    disclaimer = record.prediction_disclaimer or _DEFAULT_DISCLAIMER
    table = Table(
        [[Paragraph(escape(disclaimer), styles["disclaimer"])]],
        colWidths=[172 * mm],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _BLUE_SOFT),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#AFCBFF")),
                ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
            ]
        )
    )
    return [table]


def _build_team_section(styles: dict[str, ParagraphStyle]) -> list[object]:
    members = "<br/>".join(f"• {escape(member)}" for member in _TEAM_MEMBERS)
    table = Table(
        [
            [
                Paragraph("<b>Nhóm thực hiện</b><br/>" + members, styles["small"]),
                Paragraph(
                    "Báo cáo được tạo tự động từ dữ liệu phân tích đã lưu cục bộ.",
                    styles["small"],
                ),
            ]
        ],
        colWidths=[96 * mm, 76 * mm],
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEABOVE", (0, 0), (-1, -1), 0.6, _BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return [table]


def _label_value(
    label: str,
    value: object,
    styles: dict[str, ParagraphStyle],
) -> Paragraph:
    return Paragraph(
        f'<font color="#667085" size="7.5">{escape(label)}</font><br/>'
        f"<b>{escape(str(value))}</b>",
        styles["body"],
    )


def _metadata_table_style() -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FBFF")),
            ("BOX", (0, 0), (-1, -1), 0.55, _BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.45, _BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 3.2 * mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3.2 * mm),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 * mm),
        ]
    )


def _reportlab_image(content: bytes, *, max_width: float, max_height: float) -> Image:
    try:
        with PillowImage.open(BytesIO(content)) as source:
            width_px, height_px = source.size
    except Exception as exc:
        raise ReportPdfGenerationError("Asset ảnh không hợp lệ") from exc
    if width_px <= 0 or height_px <= 0:
        raise ReportPdfGenerationError("Asset ảnh có kích thước không hợp lệ")
    scale = min(max_width / width_px, max_height / height_px)
    return Image(BytesIO(content), width=width_px * scale, height=height_px * scale)


def _draw_page_footer(canvas, document, font_name: str, analysis_id: str) -> None:
    canvas.saveState()
    canvas.setStrokeColor(_BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(17 * mm, 12 * mm, A4[0] - 17 * mm, 12 * mm)
    canvas.setFont(font_name, 7)
    canvas.setFillColor(_MUTED)
    canvas.drawString(17 * mm, 8 * mm, f"Mã lần phân tích: {analysis_id}")
    canvas.drawRightString(
        A4[0] - 17 * mm,
        8 * mm,
        f"Trang {document.page}",
    )
    canvas.restoreState()


@lru_cache(maxsize=1)
def _register_unicode_fonts() -> tuple[str, str]:
    regular_path, bold_path = _resolve_unicode_font_paths()
    regular_name = "LungXrayUnicodeRegular"
    bold_name = "LungXrayUnicodeBold"
    if regular_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(regular_name, str(regular_path)))
    if bold_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(bold_name, str(bold_path)))
    return regular_name, bold_name


def _resolve_unicode_font_paths() -> tuple[Path, Path]:
    candidate_pairs = (
        # Windows target runtime: Arial and Segoe UI both support Vietnamese.
        (Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/arialbd.ttf")),
        (Path("C:/Windows/Fonts/segoeui.ttf"), Path("C:/Windows/Fonts/segoeuib.ttf")),
        # Linux CI/audit fallbacks.
        (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ),
        (
            Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
            Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"),
        ),
        # macOS development fallback.
        (Path("/Library/Fonts/Arial.ttf"), Path("/Library/Fonts/Arial Bold.ttf")),
    )
    for regular, bold in candidate_pairs:
        if regular.is_file() and bold.is_file():
            return regular, bold
    raise ReportPdfGenerationError(
        "Không tìm thấy font Unicode hệ thống để tạo PDF tiếng Việt"
    )
