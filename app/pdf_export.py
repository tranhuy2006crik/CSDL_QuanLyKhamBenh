from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.platypus import (
    LongTable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


FONT_DIRECTORY = Path(__file__).resolve().parents[1] / "assets" / "fonts"
FONT_REGULAR_PATH = FONT_DIRECTORY / "NotoSans-Regular.ttf"
FONT_BOLD_PATH = FONT_DIRECTORY / "NotoSans-Bold.ttf"
SUPPORTED_COLUMN_KINDS = {"text", "int", "money", "date", "datetime"}
SUMMARY_LABELS = {
    "gia_kham": "Giá khám",
    "gia_xet_nghiem": "Giá xét nghiệm",
    "gia_thuoc": "Giá thuốc kê",
    "tong_gia_tri": "Tổng giá trị",
    "tong_so_luot_kham": "Tổng số lượt khám",
    "so_luot_kham": "Số lượt khám",
    "so_benh_nhan": "Số bệnh nhân",
}


def _register_fonts() -> None:
    registered_fonts = set(pdfmetrics.getRegisteredFontNames())
    if "NotoSans" not in registered_fonts:
        if not FONT_REGULAR_PATH.is_file():
            raise FileNotFoundError(f"Không tìm thấy font: {FONT_REGULAR_PATH}")
        pdfmetrics.registerFont(TTFont("NotoSans", str(FONT_REGULAR_PATH)))
    if "NotoSans-Bold" not in registered_fonts:
        if not FONT_BOLD_PATH.is_file():
            raise FileNotFoundError(f"Không tìm thấy font: {FONT_BOLD_PATH}")
        pdfmetrics.registerFont(TTFont("NotoSans-Bold", str(FONT_BOLD_PATH)))
    pdfmetrics.registerFontFamily(
        "NotoSans",
        normal="NotoSans",
        bold="NotoSans-Bold",
        italic="NotoSans",
        boldItalic="NotoSans-Bold",
    )


def _format_money(value: Any) -> str:
    try:
        amount = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise ValueError(f"Giá trị tiền không hợp lệ: {value!r}") from error
    if not amount.is_finite():
        raise ValueError(f"Giá trị tiền không hữu hạn: {value!r}")
    formatted = f"{amount:,.2f}"
    formatted = formatted.replace(",", "\0").replace(".", ",").replace("\0", ".")
    if amount == amount.to_integral_value():
        formatted = formatted.rsplit(",", 1)[0]
    return f"{formatted} VNĐ"


def _format_value(value: Any, kind: str) -> str:
    if value is None:
        return "—"
    if kind == "money":
        return _format_money(value)
    if kind == "int":
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"Giá trị số nguyên không hợp lệ: {value!r}")
        return f"{int(value):,}".replace(",", ".")
    if kind == "datetime":
        if not isinstance(value, datetime):
            raise ValueError(f"Giá trị datetime không hợp lệ: {value!r}")
        return value.strftime("%d/%m/%Y %H:%M:%S")
    if kind == "date":
        if isinstance(value, datetime) or not isinstance(value, date):
            raise ValueError(f"Giá trị ngày không hợp lệ: {value!r}")
        return value.strftime("%d/%m/%Y")
    return str(value)


def _label_for_summary(key: str) -> str:
    return SUMMARY_LABELS.get(key, key.replace("_", " ").strip().capitalize())


def _format_summary_value(value: Any) -> str:
    if isinstance(value, Decimal):
        return _format_money(value)
    if isinstance(value, int) and not isinstance(value, bool):
        return _format_value(value, "int")
    if isinstance(value, (date, datetime)):
        kind = "datetime" if isinstance(value, datetime) else "date"
        return _format_value(value, kind)
    return _format_value(value, "text")


def xuat_bang_pdf(
    duong_dan: Path,
    tieu_de: str,
    dieu_kien: str,
    cot: list[dict[str, str]],
    rows: list[dict[str, Any]],
    tong_ket: dict[str, Any],
    bieu_do: list[dict[str, Any]] | None = None,
) -> Path:
    """Export the exact report rows supplied by a screen/service to a PDF."""
    if not isinstance(duong_dan, Path):
        raise TypeError("duong_dan phải là pathlib.Path.")
    if not tieu_de.strip():
        raise ValueError("Tiêu đề báo cáo không được để trống.")
    if not cot:
        raise ValueError("Báo cáo phải có ít nhất một cột.")

    for column in cot:
        if set(column) != {"key", "label", "kind"}:
            raise ValueError("Mỗi cột phải có đúng các khóa key, label, kind.")
        if column["kind"] not in SUPPORTED_COLUMN_KINDS:
            raise ValueError(f"Kiểu cột không hỗ trợ: {column['kind']}")
    for row in rows:
        missing_keys = {column["key"] for column in cot} - row.keys()
        if missing_keys:
            raise ValueError(
                "Thiếu dữ liệu cho cột: " + ", ".join(sorted(missing_keys))
            )
    if bieu_do is not None:
        for item in bieu_do:
            if set(item) != {"label", "value"}:
                raise ValueError("Mỗi mục biểu đồ phải có đúng label và value.")
            if not isinstance(item["label"], str):
                raise ValueError("Nhãn biểu đồ phải là văn bản.")
            _format_money(item["value"])

    _register_fonts()
    duong_dan.parent.mkdir(parents=True, exist_ok=True)
    page_size = landscape(A4) if len(cot) >= 5 else A4
    document = SimpleDocTemplate(
        str(duong_dan),
        pagesize=page_size,
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title=tieu_de,
        author="Hệ thống quản lý khám bệnh ngoại trú",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ClinicReportTitle",
        parent=styles["Title"],
        fontName="NotoSans-Bold",
        alignment=TA_CENTER,
        fontSize=15,
        leading=19,
        spaceAfter=5 * mm,
    )
    condition_style = ParagraphStyle(
        "ClinicReportCondition",
        parent=styles["BodyText"],
        fontName="NotoSans",
        fontSize=8,
        leading=11,
        spaceAfter=2 * mm,
    )
    header_style = ParagraphStyle(
        "ClinicReportHeader",
        parent=condition_style,
        fontName="NotoSans-Bold",
        textColor=colors.white,
        alignment=TA_CENTER,
    )
    cell_style = ParagraphStyle(
        "ClinicReportCell",
        parent=condition_style,
        fontSize=8,
        leading=10,
        wordWrap="CJK",
    )
    money_style = ParagraphStyle(
        "ClinicReportMoney",
        parent=cell_style,
        alignment=TA_RIGHT,
    )

    table_data: list[list[Paragraph]] = [
        [
            Paragraph(escape(column["label"]), header_style)
            for column in cot
        ]
    ]
    for row in rows:
        cells: list[Paragraph] = []
        for column in cot:
            kind = column["kind"]
            value = _format_value(row[column["key"]], kind)
            style = money_style if kind == "money" else cell_style
            cells.append(Paragraph(escape(value), style))
        table_data.append(cells)

    table = LongTable(
        table_data,
        colWidths=[document.width / len(cot)] * len(cot),
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

    story: list[Any] = [
        Paragraph(escape(tieu_de), title_style),
        Paragraph(
            f"<b>Kỳ báo cáo / bộ lọc:</b> {escape(dieu_kien.strip() or 'Không có')}",
            condition_style,
        ),
        Paragraph("<b>Đơn vị tiền:</b> VNĐ", condition_style),
        Spacer(1, 3 * mm),
    ]
    if bieu_do:
        chart_height = max(28 * mm, min(65 * mm, 8 * mm * len(bieu_do) + 10 * mm))
        chart_width = document.width
        chart = Drawing(chart_width, chart_height)
        values = [Decimal(str(item["value"])) for item in bieu_do]
        maximum = max(values, default=Decimal("0")) or Decimal("1")
        label_width = chart_width * 0.30
        value_width = chart_width * 0.20
        bars_width = chart_width - label_width - value_width - 8 * mm
        row_height = (chart_height - 6 * mm) / max(1, len(bieu_do))
        for index, item in enumerate(bieu_do):
            y = chart_height - (index + 1) * row_height
            value = values[index]
            label = str(item["label"])
            if len(label) > 32:
                label = label[:29] + "..."
            chart.add(
                String(0, y + row_height * 0.28, label, fontName="NotoSans", fontSize=7)
            )
            bar_length = float(value / maximum) * bars_width if value > 0 else 0
            if bar_length:
                chart.add(
                    Rect(
                        label_width,
                        y + row_height * 0.16,
                        bar_length,
                        row_height * 0.68,
                        fillColor=colors.HexColor("#168AAD"),
                        strokeColor=None,
                    )
                )
            chart.add(
                String(
                    label_width + bars_width + 3 * mm,
                    y + row_height * 0.28,
                    _format_money(value),
                    fontName="NotoSans",
                    fontSize=7,
                )
            )
        story.extend(
            [
                Paragraph("So sánh tổng giá trị theo bác sĩ", condition_style),
                chart,
                Spacer(1, 3 * mm),
            ]
        )
    if rows:
        story.append(table)
    else:
        story.append(Paragraph("Không có dữ liệu.", cell_style))

    if tong_ket:
        summary_data = [
            [
                Paragraph(
                    escape(_label_for_summary(key)),
                    ParagraphStyle(
                        f"ClinicSummaryLabel{index}",
                        parent=cell_style,
                        fontName="NotoSans-Bold",
                    ),
                ),
                Paragraph(
                    escape(_format_summary_value(value)),
                    cell_style,
                ),
            ]
            for index, (key, value) in enumerate(tong_ket.items())
        ]
        summary_table = LongTable(
            summary_data,
            colWidths=[document.width * 0.35, document.width * 0.65],
            hAlign="LEFT",
        )
        summary_table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B8C5D1")),
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E8EEF4")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.extend([Spacer(1, 5 * mm), summary_table])

    def draw_page_number(canvas: Canvas, _document: SimpleDocTemplate) -> None:
        canvas.saveState()
        canvas.setFont("NotoSans", 8)
        canvas.drawRightString(
            page_size[0] - 12 * mm,
            9 * mm,
            f"Trang {_document.page}",
        )
        canvas.restoreState()

    document.build(story, onFirstPage=draw_page_number, onLaterPages=draw_page_number)
    return duong_dan


def xuat_bao_cao_phieu_kham_pdf(
    duong_dan: Path, report: dict[str, Any]
) -> Path:
    if not isinstance(duong_dan, Path):
        raise TypeError("duong_dan phải là pathlib.Path.")
    for key in ("thong_tin", "ds_xet_nghiem", "loi_dan", "ds_thuoc", "tong_chi_phi"):
        if key not in report:
            raise ValueError(f"Thiếu dữ liệu báo cáo: {key}")

    _register_fonts()
    duong_dan.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(duong_dan),
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title="Báo cáo kết quả khám bệnh",
        author="Hệ thống quản lý khám bệnh ngoại trú",
    )
    styles = getSampleStyleSheet()
    heading = ParagraphStyle(
        "VisitReportHeading",
        parent=styles["Heading2"],
        fontName="NotoSans-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#24527A"),
        spaceBefore=3 * mm,
        spaceAfter=2 * mm,
    )
    body = ParagraphStyle(
        "VisitReportBody",
        parent=styles["BodyText"],
        fontName="NotoSans",
        fontSize=9,
        leading=13,
        wordWrap="CJK",
    )
    label = ParagraphStyle(
        "VisitReportLabel",
        parent=body,
        fontName="NotoSans-Bold",
    )
    title = ParagraphStyle(
        "VisitReportTitle",
        parent=styles["Title"],
        fontName="NotoSans-Bold",
        fontSize=16,
        leading=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#183B56"),
        spaceAfter=5 * mm,
    )

    def p(value: Any, style: ParagraphStyle = body) -> Paragraph:
        return Paragraph(escape("—" if value is None or value == "" else str(value)), style)

    def data_table(rows: list[list[Any]], widths: list[float] | None = None) -> Table:
        table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF4")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#183B56")),
                    ("FONTNAME", (0, 0), (-1, -1), "NotoSans"),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B8C5D1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        return table

    info = report["thong_tin"]
    costs = report["tong_chi_phi"]
    story: list[Any] = [
        Paragraph("BÁO CÁO KẾT QUẢ KHÁM BỆNH", title),
        Paragraph("Thông tin hành chính và ca khám", heading),
        data_table(
            [
                [p("Mã bệnh nhân", label), p(info["ma_benh_nhan"]),
                 p("Họ tên", label), p(info["ho_ten"])],
                [p("Ngày sinh", label), p(_format_value(info["ngay_sinh"], "date")),
                 p("Điện thoại", label), p(info["so_dien_thoai"])],
                [p("Mã phiếu", label), p(info["ma_phieu"]),
                 p("Ngày giờ khám", label), p(_format_value(info["ngay_gio_kham"], "datetime"))],
                [p("Bác sĩ", label), p(info["bac_si"]), p("Trạng thái", label), p("HOÀN THÀNH")],
            ],
            [29 * mm, 52 * mm, 30 * mm, 67 * mm],
        ),
        Paragraph("Triệu chứng", heading),
        p(info["trieu_chung"]),
        Paragraph("Chẩn đoán", heading),
        p(info["chan_doan"]),
        Paragraph("Xét nghiệm và kết quả", heading),
    ]
    lab_rows = [[p("STT", label), p("Xét nghiệm", label), p("Kết quả", label),
                 p("Thời điểm", label), p("Đơn giá", label)]]
    for row in report["ds_xet_nghiem"]:
        lab_rows.append(
            [
                p(row["stt"]),
                p(row["ten_xet_nghiem"]),
                p(row["ket_qua"]),
                p(_format_value(row["ngay_gio_thuc_hien"], "datetime")),
                p(_format_money(row["don_gia_ap_dung"])),
            ]
        )
    story.append(
        data_table(lab_rows, [12 * mm, 43 * mm, 57 * mm, 35 * mm, 31 * mm])
        if len(lab_rows) > 1
        else p("Không có chỉ định xét nghiệm.")
    )
    story.append(Paragraph("Đơn thuốc", heading))
    for note in report["loi_dan"]:
        story.append(
            p(
                f'Lời dặn ({_format_value(note["ngay_lap"], "date")}): '
                f'{note["loi_dan"] or "Không có"}'
            )
        )
    if not report["loi_dan"]:
        story.append(p("Không có đơn thuốc."))
    medicine_rows = [[p("Thuốc", label), p("SL", label), p("ĐVT", label),
                      p("Cách dùng", label), p("Đơn giá", label), p("Thành tiền", label)]]
    for row in report["ds_thuoc"]:
        medicine_rows.append(
            [
                p(row["ten_thuoc"]),
                p(row["so_luong_ke"]),
                p(row["don_vi_tinh"]),
                p(row["cach_dung"]),
                p(_format_money(row["don_gia_ap_dung"])),
                p(_format_money(row["thanh_tien"])),
            ]
        )
    story.append(
        data_table(
            medicine_rows,
            [37 * mm, 10 * mm, 15 * mm, 44 * mm, 34 * mm, 38 * mm],
        )
        if len(medicine_rows) > 1
        else p("Không có thuốc được kê.")
    )
    story.extend(
        [
            Paragraph("Tổng chi phí ghi nhận", heading),
            data_table(
                [
                    [p("Giá khám", label), p(_format_money(costs["gia_kham"])),
                     p("Xét nghiệm", label), p(_format_money(costs["gia_xet_nghiem"]))],
                    [p("Thuốc", label), p(_format_money(costs["gia_thuoc"])),
                     p("Tổng chi phí", label), p(_format_money(costs["tong_chi_phi"]))],
                ],
                [35 * mm, 50 * mm, 35 * mm, 58 * mm],
            ),
        ]
    )

    def draw_page_number(canvas: Canvas, _document: SimpleDocTemplate) -> None:
        canvas.saveState()
        canvas.setFont("NotoSans", 8)
        canvas.drawRightString(
            A4[0] - 16 * mm, 9 * mm, f"Trang {_document.page}"
        )
        canvas.restoreState()

    document.build(story, onFirstPage=draw_page_number, onLaterPages=draw_page_number)
    return duong_dan
