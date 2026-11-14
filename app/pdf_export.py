from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
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
    Image,
)

FONT_DIRECTORY = Path(__file__).resolve().parents[1] / "assets" / "fonts"
if not FONT_DIRECTORY.exists():
    FONT_DIRECTORY = Path(__file__).resolve().parent / "assets" / "fonts"

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


def _build_pdf_header() -> Table:
    styles = getSampleStyleSheet()
    clinic_info_style = ParagraphStyle(
        "ClinicInfo",
        parent=styles["Normal"],
        leading=16,
    )

    clinic_text = """
    <font name="NotoSans-Bold" size="15" color="#183B56">BỆNH VIỆN TƯ NHÓM 10</font><br/>
    <font name="NotoSans" size="10" color="#333333">
    <b>Địa chỉ:</b> Km10 Đ. Nguyễn Trãi, P. Mỗ Lao, Hà Đông, Hà Nội<br/>
    <b>Điện thoại:</b> (028) 1234 5678 &nbsp;&nbsp;&nbsp;&nbsp; <b>Email:</b> nhom10@gmail.com
    </font>
    """

    logo_dir = Path(__file__).resolve().parents[1] / "assets" / "logo"
    if not logo_dir.exists():
        logo_dir = Path(__file__).resolve().parent / "assets" / "logo"

    logo_path = None
    if logo_dir.exists() and logo_dir.is_dir():
        image_extensions = ("*.png", "*.jpg", "*.jpeg", "*.JPG", "*.PNG")
        for ext in image_extensions:
            files = list(logo_dir.glob(ext))
            if files:
                logo_path = files[0]
                break

    if logo_path and logo_path.is_file():
        logo_element = Image(str(logo_path), width=38 * mm, height=38 * mm)
        logo_element.hAlign = "RIGHT"
    else:
        logo_element = Paragraph(
            "<b>[LOGO BỆNH VIỆN]</b>",
            ParagraphStyle(
                "LogoText",
                alignment=TA_RIGHT,
                fontName="NotoSans-Bold",
                fontSize=12,
                textColor=colors.HexColor("#183B56"),
            ),
        )

    header_table = Table(
        [[Paragraph(clinic_text, clinic_info_style), logo_element]],
        colWidths=["75%", "25%"],
    )
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("LINEBELOW", (0, 0), (-1, -1), 1.5, colors.HexColor("#183B56")),
            ]
        )
    )
    return header_table


def _build_pdf_signature() -> Table:
    styles = getSampleStyleSheet()
    sig_style = ParagraphStyle(
        "Signature", fontName="NotoSans-Bold", fontSize=11, alignment=TA_CENTER
    )
    date_style = ParagraphStyle(
        "SigDate", fontName="NotoSans", fontSize=10, alignment=TA_CENTER, spaceAfter=25
    )

    sig_table = Table(
        [
            [
                "",
                Paragraph(
                    f"Hà Nội, ngày {datetime.now().day} tháng {datetime.now().month} năm {datetime.now().year}",
                    date_style,
                ),
            ],
            [
                "",
                Paragraph(
                    "Bác Sĩ<br/><font size='9'>(Ký, ghi rõ họ tên)</font>",
                    sig_style,
                ),
            ],
        ],
        colWidths=["55%", "45%"],
    )
    return sig_table


def xuat_bang_pdf(
    duong_dan: Path,
    tieu_de: str,
    dieu_kien: str,
    cot: list[dict[str, str]],
    rows: list[dict[str, Any]],
    tong_ket: dict[str, Any],
    bieu_do: list[dict[str, Any]] | None = None,
) -> Path:
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
        [Paragraph(escape(column["label"]), header_style) for column in cot]
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


def xuat_bao_cao_phieu_kham_pdf(duong_dan: Path, report: dict[str, Any]) -> Path:
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

    heading1 = ParagraphStyle(
        "VisitReportHeading1",
        parent=styles["Heading1"],
        fontName="NotoSans-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#24527A"),
        spaceBefore=5 * mm,
        spaceAfter=3 * mm,
    )
    heading2 = ParagraphStyle(
        "VisitReportHeading2",
        parent=styles["Heading2"],
        fontName="NotoSans-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#183B56"),
        spaceBefore=3 * mm,
        spaceAfter=2 * mm,
        leftIndent=5 * mm,
    )
    body = ParagraphStyle(
        "VisitReportBody",
        parent=styles["BodyText"],
        fontName="NotoSans",
        fontSize=11,
        leading=16,
        wordWrap="CJK",
    )
    body_indent = ParagraphStyle(
        "VisitReportBodyIndent",
        parent=body,
        leftIndent=5 * mm,
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
        return Paragraph(
            escape("—" if value is None or value == "" else str(value)), style
        )

    def data_table(rows: list[list[Any]], widths: list[float] | None = None) -> Table:
        table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF4")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#183B56")),
                    ("FONTNAME", (0, 0), (-1, -1), "NotoSans-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "NotoSans"),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B8C5D1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                ]
            )
        )
        return table

    info = report["thong_tin"]
    costs = report["tong_chi_phi"]

    info_table_data = [
        [
            Paragraph(
                f"<b>Mã bệnh nhân:</b> {escape(str(info['ma_benh_nhan']))}", body_indent
            ),
            Paragraph(f"<b>Mã phiếu:</b> {escape(str(info['ma_phieu']))}", body_indent),
        ],
        [
            Paragraph(f"<b>Họ tên:</b> {escape(str(info['ho_ten']))}", body_indent),
            Paragraph(f"<b>Bác sĩ:</b> {escape(str(info['bac_si']))}", body_indent),
        ],
        [
            Paragraph(
                f"<b>Ngày sinh:</b> {escape(_format_value(info['ns_str'] if 'ns_str' in info else info['ngay_sinh'], 'date'))}",
                body_indent,
            ),
            Paragraph(
                f"<b>Ngày giờ khám:</b> {escape(_format_value(info['ngay_gio_kham'], 'datetime'))}",
                body_indent,
            ),
        ],
        [
            Paragraph(
                f"<b>Điện thoại:</b> {escape(str(info['so_dien_thoai'] or '—'))}",
                body_indent,
            ),
            "",
        ],
        [
            Paragraph(
                f"<b>Địa chỉ:</b> {escape(str(info.get('dia_chi') or '—'))}",
                body_indent,
            ),
            "",
        ],
    ]

    info_table = Table(info_table_data, colWidths=["50%", "50%"])
    info_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )

    story: list[Any] = [
        _build_pdf_header(),
        Spacer(1, 5 * mm),
        Paragraph("PHIẾU KHÁM BỆNH", title),
        Paragraph("I - Thông tin hành chính và ca khám", heading1),
        info_table,
        Paragraph("II - Quá trình khám bệnh", heading1),
        Paragraph("1. Triệu chứng", heading2),
        p(info["trieu_chung"], body_indent),
        Paragraph("2. Chẩn đoán", heading2),
        p(info["chan_doan"], body_indent),
        Paragraph("3. Xét nghiệm", heading2),
    ]

    col_hdr_center = ParagraphStyle(
        "ColHdrC", parent=body, fontName="NotoSans-Bold", alignment=TA_CENTER
    )

    cell_center = ParagraphStyle("CellC", parent=body, alignment=TA_CENTER)
    cell_left = ParagraphStyle("CellL", parent=body, alignment=TA_LEFT)
    cell_right = ParagraphStyle("CellR", parent=body, alignment=TA_RIGHT)

    def cp(val: Any, align: str = "left") -> Paragraph:
        s = (
            cell_left
            if align == "left"
            else (cell_center if align == "center" else cell_right)
        )
        return Paragraph(escape("—" if val is None or val == "" else str(val)), s)

    def chdr_c(val: str) -> Paragraph:
        return Paragraph(escape(val), col_hdr_center)

    lab_rows = [
        [
            chdr_c("STT"),
            chdr_c("Xét nghiệm"),
            chdr_c("Kết quả"),
            chdr_c("Thời điểm"),
            chdr_c("Đơn giá"),
        ]
    ]
    for row in report["ds_xet_nghiem"]:
        lab_rows.append(
            [
                cp(row["stt"], "center"),
                cp(row["ten_xet_nghiem"], "left"),
                cp(row["ket_qua"], "left"),
                cp(_format_value(row["ngay_gio_thuc_hien"], "datetime"), "center"),
                cp(_format_money(row["don_gia_ap_dung"]), "center"),
            ]
        )
    if len(lab_rows) > 1:
        story.append(
            data_table(lab_rows, [12 * mm, 45 * mm, 55 * mm, 35 * mm, 31 * mm])
        )
    else:
        story.append(p("Không có chỉ định xét nghiệm.", body_indent))

    story.append(Paragraph("4. Đơn thuốc", heading2))

    for note in report["loi_dan"]:
        story.append(
            Paragraph(
                f'<b>Lời dặn:</b> {escape(note["loi_dan"] or "Không có")}',
                body_indent,
            )
        )
    if not report["loi_dan"]:
        story.append(p("Không có đơn thuốc.", body_indent))

    medicine_rows = [
        [
            chdr_c("Thuốc"),
            chdr_c("SL"),
            chdr_c("ĐVT"),
            chdr_c("Cách dùng"),
            chdr_c("Đơn giá"),
            chdr_c("Thành tiền"),
        ]
    ]
    for row in report["ds_thuoc"]:
        medicine_rows.append(
            [
                cp(row["ten_thuoc"], "left"),
                cp(row["so_luong_ke"], "center"),
                cp(row["don_vi_tinh"], "center"),
                cp(row["cach_dung"], "left"),
                cp(_format_money(row["don_gia_ap_dung"]), "center"),
                cp(_format_money(row["thanh_tien"]), "center"),
            ]
        )
    if len(medicine_rows) > 1:
        story.append(
            data_table(
                medicine_rows, [40 * mm, 12 * mm, 15 * mm, 43 * mm, 29 * mm, 39 * mm]
            )
        )
    else:
        story.append(p("Không có thuốc được kê.", body_indent))

    story.append(Paragraph("III - Chi phí", heading1))

    gia_kham = costs.get("gia_kham", Decimal("0"))
    gia_xet_nghiem = costs.get("gia_xet_nghiem", Decimal("0"))
    gia_thuoc = costs.get("gia_thuoc", Decimal("0"))
    tong_cong = costs["tong_chi_phi"]

    bill_style = ParagraphStyle("BillStyle", parent=body, alignment=TA_RIGHT)

    cost_table_data = [
        [Paragraph("Giá khám:", body), Paragraph(_format_money(gia_kham), bill_style)],
        [
            Paragraph("Giá xét nghiệm:", body),
            Paragraph(_format_money(gia_xet_nghiem), bill_style),
        ],
        [
            Paragraph("Giá thuốc:", body),
            Paragraph(_format_money(gia_thuoc), bill_style),
        ],
        [
            Paragraph("<b>TỔNG CỘNG:</b>", body),
            Paragraph(f"<b>{_format_money(tong_cong)}</b>", bill_style),
        ],
    ]
    cost_table = Table(cost_table_data, colWidths=[130 * mm, 48 * mm], hAlign="RIGHT")
    cost_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
            ]
        )
    )

    story.append(cost_table)

    story.extend([Spacer(1, 15 * mm), _build_pdf_signature()])

    def draw_page_number(canvas: Canvas, _document: SimpleDocTemplate) -> None:
        canvas.saveState()
        canvas.setFont("NotoSans", 8)
        canvas.drawRightString(A4[0] - 16 * mm, 9 * mm, f"Trang {_document.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=draw_page_number, onLaterPages=draw_page_number)
    return duong_dan
