from datetime import datetime
from pathlib import Path
from typing import Sequence
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus.doctemplate import BaseDocTemplate
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle


def _register_vietnamese_font() -> str:
    if "DejaVu" in pdfmetrics.getRegisteredFontNames():
        return "DejaVu"

    candidates = (
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/dejavu/DejaVuSans.ttf"),
    )
    for font_path in candidates:
        if font_path.is_file():
            pdfmetrics.registerFont(TTFont("DejaVu", str(font_path)))
            return "DejaVu"

    raise FileNotFoundError(
        "No Vietnamese-capable TrueType font found. Install Arial, Segoe UI, "
        "or DejaVu Sans before exporting PDF reports."
    )


def export_report_pdf(
    output_path: str | Path,
    title: str,
    headers: Sequence[str],
    rows: Sequence[Sequence[object]],
) -> Path:
    """Export a tabular report to a paginated, Vietnamese-capable PDF."""
    if not headers:
        raise ValueError("A report must contain at least one column header.")
    if any(len(row) != len(headers) for row in rows):
        raise ValueError("Every report row must have the same number of columns.")

    destination = Path(output_path)
    if not destination.parent.is_dir():
        raise FileNotFoundError(
            f"Output directory does not exist: {destination.parent}"
        )

    font_name = _register_vietnamese_font()
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName=font_name,
        alignment=TA_CENTER,
        fontSize=16,
        leading=20,
        spaceAfter=8 * mm,
    )
    cell_style = ParagraphStyle(
        "ReportCell",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=8,
        leading=10,
        wordWrap="CJK",
    )
    header_style = ParagraphStyle(
        "ReportHeader",
        parent=cell_style,
        textColor=colors.white,
        alignment=TA_CENTER,
    )

    table_data = [
        [Paragraph(escape(str(header)), header_style) for header in headers]
    ]
    for row in rows:
        table_data.append(
            [
                Paragraph(
                    escape("" if value is None else str(value)).replace("\n", "<br/>"),
                    cell_style,
                )
                for value in row
            ]
        )

    document = SimpleDocTemplate(
        str(destination),
        pagesize=landscape(A4),
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=title,
    )
    column_width = document.width / len(headers)
    table = LongTable(
        table_data,
        colWidths=[column_width] * len(headers),
        repeatRows=1,
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#24527A")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B8C5D1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#F1F5F9")],
                ),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    def draw_page_number(canvas: Canvas, _document: BaseDocTemplate) -> None:
        canvas.saveState()
        canvas.setFont(font_name, 8)
        canvas.drawRightString(
            landscape(A4)[0] - 15 * mm,
            9 * mm,
            f"Trang {_document.page}",
        )
        canvas.restoreState()

    document.build(
        [
            Paragraph(escape(title), title_style),
            Paragraph(
                f"Ngày xuất: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                cell_style,
            ),
            Spacer(1, 5 * mm),
            table,
        ],
        onFirstPage=draw_page_number,
        onLaterPages=draw_page_number,
    )
    return destination
