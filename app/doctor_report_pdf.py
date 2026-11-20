from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
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
    period_style = ParagraphStyle(
        "DoctorReportPeriod",
        parent=summary_style,
        fontSize=15,
        leading=19,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1D4ED8"),
    )
    header_style = ParagraphStyle(
        "DoctorReportHeader",
        parent=body_style,
        fontName="NotoSans-Bold",
        fontSize=8,
        leading=10,
        alignment=TA_CENTER,
        textColor=colors.white,
    )
    right_style = ParagraphStyle(
        "DoctorReportRight",
        parent=body_style,
        alignment=TA_RIGHT,
    )
    centered_style = ParagraphStyle(
        "DoctorReportCentered",
        parent=body_style,
        alignment=TA_CENTER,
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
            cell_style = (
                right_style
                if kind == "money"
                else centered_style
                if kind == "int"
                else body_style
            )
            formatted.append(
                Paragraph(escape(text), cell_style)
            )
        detail_data.append(formatted)
    detail_widths = [58, 130, 62, 62, 91, 91, 91, 110]
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
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    period_banner = Table(
        [[Paragraph(f"Kỳ báo cáo: Tháng {thang}/{nam}", period_style)]],
        colWidths=[page_width],
    )
    period_banner.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#93C5FD")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    story: list[Any] = [
        _build_pdf_header(),
        Spacer(1, 3 * mm),
        Paragraph("BÁO CÁO KHÁM THEO BÁC SĨ", title_style),
        period_banner,
        Spacer(1, 3 * mm),
        summary,
    ]
    story.extend([Paragraph("Chi tiết báo cáo", section_style), details])

    def draw_page_number(canvas: Canvas, _document: SimpleDocTemplate) -> None:
        canvas.saveState()
        canvas.setFont("NotoSans", 9)
        canvas.setFillColor(colors.HexColor("#475569"))
        canvas.drawRightString(page_size[0] - 12 * mm, 8 * mm, f"Trang {_document.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=draw_page_number, onLaterPages=draw_page_number)
    return duong_dan
