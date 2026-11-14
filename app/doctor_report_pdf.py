from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    KeepTogether,
    LongTable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.pdf_export import _build_pdf_header, _format_money, _register_fonts


def _decimal(row: Mapping[str, Any], key: str) -> Decimal:
    value = Decimal(str(row[key] or 0))
    if not value.is_finite():
        raise ValueError(f"Giá trị không hợp lệ cho {key}: {value!r}")
    return value


def _build_horizontal_bar_charts(
    rows: Sequence[Mapping[str, Any]], width: float
) -> list[Drawing]:
    sorted_rows = sorted(
        rows,
        key=lambda row: _decimal(row, "tong_gia_tri"),
        reverse=True,
    )
    max_visits = max(
        (int(row["so_luot_kham"] or 0) for row in sorted_rows), default=0
    )
    max_value = max(
        (_decimal(row, "tong_gia_tri") for row in sorted_rows),
        default=Decimal("0"),
    )
    visit_color = colors.HexColor("#168AAD")
    value_color = colors.HexColor("#E58A2B")
    label_width, value_width = 140, 96
    bar_width = max(1, width - label_width - value_width - 12)
    header_height, row_height, rows_per_chart = 36, 28, 4
    charts: list[Drawing] = []

    for offset in range(0, len(sorted_rows), rows_per_chart):
        chart_rows = sorted_rows[offset : offset + rows_per_chart]
        chart_header_height = header_height if offset == 0 else 0
        height = chart_header_height + len(chart_rows) * row_height
        chart = Drawing(width, height)
        if offset == 0:
            chart.add(
                Rect(0, height - 11, 8, 8, fillColor=visit_color, strokeColor=None)
            )
            chart.add(
                String(
                    12,
                    height - 9,
                    f"Số lượt khám (tối đa: {max_visits})",
                    fontName="NotoSans",
                    fontSize=8,
                    fillColor=colors.HexColor("#111827"),
                )
            )
            chart.add(
                Rect(0, height - 25, 8, 8, fillColor=value_color, strokeColor=None)
            )
            chart.add(
                String(
                    12,
                    height - 23,
                    f"Tổng giá trị ghi nhận (tối đa: {_format_money(max_value)})",
                    fontName="NotoSans",
                    fontSize=8,
                    fillColor=colors.HexColor("#111827"),
                )
            )

        for index, row in enumerate(chart_rows):
            top = height - chart_header_height - index * row_height
            visits = int(row["so_luot_kham"] or 0)
            amount = _decimal(row, "tong_gia_tri")
            name = str(row["ten_bac_si"])
            if len(name) > 31:
                name = name[:28] + "..."
            chart.add(
                String(
                    0,
                    top - 11,
                    name,
                    fontName="NotoSans",
                    fontSize=8,
                    fillColor=colors.HexColor("#111827"),
                )
            )
            for value, maximum, color, y, label in (
                (
                    Decimal(visits),
                    Decimal(max_visits),
                    visit_color,
                    top - 9,
                    str(visits),
                ),
                (
                    amount,
                    max_value,
                    value_color,
                    top - 19,
                    _format_money(amount),
                ),
            ):
                chart.add(
                    Rect(
                        label_width,
                        y,
                        bar_width,
                        5,
                        fillColor=colors.HexColor("#E2E8F0"),
                        strokeColor=None,
                    )
                )
                scaled_width = (
                    max(1, bar_width * float(value / maximum))
                    if value > 0 and maximum > 0
                    else 0
                )
                if scaled_width:
                    chart.add(
                        Rect(
                            label_width,
                            y,
                            scaled_width,
                            5,
                            fillColor=color,
                            strokeColor=None,
                        )
                    )
                chart.add(
                    String(
                        width - 2,
                        y - 1,
                        label,
                        fontName="NotoSans",
                        fontSize=8,
                        fillColor=colors.HexColor("#111827"),
                        textAnchor="end",
                    )
                )
            if index < len(chart_rows) - 1:
                chart.add(
                    Rect(
                        0,
                        top - row_height + 2,
                        width,
                        0.35,
                        fillColor=colors.HexColor("#E2E8F0"),
                        strokeColor=None,
                    )
                )
        charts.append(chart)
    return charts


def xuat_bao_cao_bac_si_pdf(
    duong_dan: Path,
    thang: int,
    nam: int,
    rows: Sequence[Mapping[str, Any]],
) -> Path:
    if not isinstance(duong_dan, Path):
        raise TypeError("duong_dan phải là pathlib.Path.")
    if isinstance(thang, bool) or not isinstance(thang, int) or not 1 <= thang <= 12:
        raise ValueError("Tháng phải từ 1 đến 12.")
    if isinstance(nam, bool) or not isinstance(nam, int) or not 1 <= nam <= 9998:
        raise ValueError("Năm không hợp lệ.")
    required = {
        "ma_bac_si",
        "ten_bac_si",
        "so_luot_kham",
        "so_benh_nhan",
        "gia_kham",
        "gia_xet_nghiem",
        "gia_thuoc",
        "tong_gia_tri",
    }
    for row in rows:
        missing = required - row.keys()
        if missing:
            raise ValueError("Thiếu dữ liệu: " + ", ".join(sorted(missing)))

    _register_fonts()
    duong_dan.parent.mkdir(parents=True, exist_ok=True)
    page_size = landscape(A4)
    document = SimpleDocTemplate(
        str(duong_dan),
        pagesize=page_size,
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=13 * mm,
        bottomMargin=15 * mm,
        title="Báo cáo bác sĩ",
        author="Hệ thống quản lý khám bệnh ngoại trú",
    )
    base = getSampleStyleSheet()["BodyText"]
    title_style = ParagraphStyle(
        "DoctorReportTitle",
        parent=base,
        fontName="NotoSans-Bold",
        fontSize=18,
        leading=23,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#111827"),
        spaceAfter=3 * mm,
    )
    section_style = ParagraphStyle(
        "DoctorReportSection",
        parent=base,
        fontName="NotoSans-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#111827"),
        spaceBefore=3 * mm,
        spaceAfter=2 * mm,
    )
    body_style = ParagraphStyle(
        "DoctorReportBody",
        parent=base,
        fontName="NotoSans",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#111827"),
        wordWrap="CJK",
    )
    summary_style = ParagraphStyle(
        "DoctorReportSummary",
        parent=body_style,
        fontName="NotoSans-Bold",
        fontSize=14,
        leading=17,
    )
    header_style = ParagraphStyle(
        "DoctorReportHeader",
        parent=body_style,
        fontName="NotoSans-Bold",
        alignment=TA_CENTER,
        textColor=colors.white,
    )
    right_style = ParagraphStyle(
        "DoctorReportRight",
        parent=body_style,
        alignment=TA_RIGHT,
    )
    page_width = page_size[0] - 24 * mm
    visits_total = sum(int(row["so_luot_kham"] or 0) for row in rows)
    value_total = sum((_decimal(row, "tong_gia_tri") for row in rows), Decimal("0"))
    summary = Table(
        [
            [
                Paragraph(f"Số bác sĩ: {len(rows)}", summary_style),
                Paragraph(f"Tổng lượt khám: {visits_total}", summary_style),
                Paragraph(
                    f"Tổng giá trị khám: {_format_money(value_total)}",
                    summary_style,
                ),
            ]
        ],
        colWidths=[page_width / 3] * 3,
    )
    summary.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    charts = _build_horizontal_bar_charts(rows, page_width)

    detail_columns = [
        ("Mã bác sĩ", "ma_bac_si", "text"),
        ("Bác sĩ", "ten_bac_si", "text"),
        ("Lượt khám", "so_luot_kham", "int"),
        ("Bệnh nhân", "so_benh_nhan", "int"),
        ("Tiền khám", "gia_kham", "money"),
        ("Xét nghiệm", "gia_xet_nghiem", "money"),
        ("Tiền thuốc", "gia_thuoc", "money"),
        ("Tổng giá trị", "tong_gia_tri", "money"),
    ]
    detail_data: list[list[Paragraph]] = [
        [Paragraph(label, header_style) for label, _key, _kind in detail_columns]
    ]
    for row in rows:
        formatted: list[Paragraph] = []
        for _label, key, kind in detail_columns:
            value = row[key]
            if kind == "money":
                text = _format_money(value or 0)
            elif kind == "int":
                text = str(int(value or 0))
            else:
                text = str(value)
            formatted.append(
                Paragraph(escape(text), right_style if kind == "money" else body_style)
            )
        detail_data.append(formatted)
    detail_widths = [58, 130, 48, 54, 91, 91, 91, 110]
    details = LongTable(
        detail_data,
        colWidths=detail_widths,
        repeatRows=1,
        hAlign="LEFT",
    )
    details.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#34495E")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    story: list[Any] = [
        _build_pdf_header(),
        Spacer(1, 3 * mm),
        Paragraph("BÁO CÁO KHÁM THEO BÁC SĨ", title_style),
        Paragraph(f"Kỳ báo cáo: Tháng {thang}/{nam}", body_style),
        Spacer(1, 3 * mm),
        summary,
    ]
    if charts:
        story.append(
            KeepTogether(
                [
                    Paragraph("Biểu đồ thể hiện số lượt khám và doanh thu của bác sĩ theo tháng", section_style),
                    charts[0],
                ]
            )
        )
        story.extend(charts[1:])
    else:
        story.extend(
            [
                Paragraph("Biểu đồ cột ghép theo toàn bộ bác sĩ", section_style),
                Paragraph("Không có dữ liệu cho kỳ báo cáo.", body_style),
            ]
        )
    story.extend([Paragraph("Chi tiết báo cáo", section_style), details])

    def draw_page_number(canvas: Canvas, _document: SimpleDocTemplate) -> None:
        canvas.saveState()
        canvas.setFont("NotoSans", 9)
        canvas.setFillColor(colors.HexColor("#475569"))
        canvas.drawRightString(page_size[0] - 12 * mm, 8 * mm, f"Trang {_document.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=draw_page_number, onLaterPages=draw_page_number)
    return duong_dan
