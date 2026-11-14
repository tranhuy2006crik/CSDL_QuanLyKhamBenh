import tempfile
import unittest
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from app.pdf_export import xuat_bang_pdf, xuat_bao_cao_phieu_kham_pdf
from app.doctor_report_pdf import (
    _build_horizontal_bar_charts,
    xuat_bao_cao_bac_si_pdf,
)
from reportlab.graphics.shapes import Rect, String
from reportlab.lib import colors


class PdfExportTests(unittest.TestCase):
    def test_exports_report_with_vietnamese_filters_totals_and_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "bao_cao.pdf"
            result = xuat_bang_pdf(
                output_path,
                "Báo cáo lượt khám",
                "Tháng 10/2026; khoa Nội",
                [
                    {"key": "ten_bac_si", "label": "Bác sĩ", "kind": "text"},
                    {"key": "ngay", "label": "Ngày", "kind": "date"},
                    {"key": "tong", "label": "Tổng giá trị", "kind": "money"},
                ],
                [
                    {
                        "ten_bac_si": "Nguyễn Văn A",
                        "ngay": date(2026, 10, 30),
                        "tong": Decimal("150000.00"),
                    }
                ],
                {"tong_gia_tri": Decimal("150000.00"), "so_luot_kham": 12},
            )

            self.assertEqual(result, output_path)
            self.assertTrue(output_path.is_file())
            self.assertTrue(output_path.read_bytes().startswith(b"%PDF-"))
            self.assertIn(b"NotoSans", output_path.read_bytes())

    def test_exports_bar_chart_when_report_requests_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "bao_cao_bac_si.pdf"
            xuat_bang_pdf(
                output_path,
                "Báo cáo giá trị khám",
                "Tháng 10/2026",
                [{"key": "ten", "label": "Bác sĩ", "kind": "text"}],
                [{"ten": "Nguyễn Văn A"}],
                {},
                bieu_do=[{"label": "Nguyễn Văn A", "value": Decimal("125000")}],
            )
            self.assertTrue(output_path.read_bytes().startswith(b"%PDF-"))

    def test_exports_combined_doctor_report_for_all_rows(self) -> None:
        rows = [
            {
                "ma_bac_si": doctor_id,
                "ten_bac_si": f"Bác sĩ {doctor_id}",
                "so_luot_kham": doctor_id,
                "so_benh_nhan": doctor_id,
                "gia_kham": Decimal("150000"),
                "gia_xet_nghiem": Decimal("90000"),
                "gia_thuoc": Decimal("20000"),
                "tong_gia_tri": Decimal(doctor_id * 260000),
            }
            for doctor_id in range(1, 13)
        ]
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "bao_cao_bac_si.pdf"
            result = xuat_bao_cao_bac_si_pdf(output_path, 10, 2026, rows)

            self.assertEqual(result, output_path)
            self.assertTrue(output_path.read_bytes().startswith(b"%PDF-"))
            self.assertIn(b"NotoSans", output_path.read_bytes())

    def test_builds_paired_horizontal_bars_and_splits_large_reports(self) -> None:
        rows = [
            {
                "ten_bac_si": f"Bác sĩ {doctor_id}",
                "so_luot_kham": doctor_id,
                "tong_gia_tri": Decimal(doctor_id * 1000),
            }
            for doctor_id in range(9)
        ]

        charts = _build_horizontal_bar_charts(rows, 700)

        self.assertEqual(len(charts), 3)
        self.assertLess(charts[0].height, 150)
        labels = [
            shape.text
            for chart in charts
            for shape in chart.contents
            if isinstance(shape, String)
        ]
        self.assertIn("Bác sĩ 0", labels)
        self.assertIn("Bác sĩ 8", labels)
        self.assertTrue(any("Số lượt khám" in label for label in labels))
        self.assertTrue(any("Tổng giá trị ghi nhận" in label for label in labels))
        colored_bars = [
            shape
            for chart in charts
            for shape in chart.contents
            if isinstance(shape, Rect)
            and (
                shape.fillColor == colors.HexColor("#168AAD")
                or shape.fillColor == colors.HexColor("#E58A2B")
            )
            and shape.width > 8
        ]
        self.assertEqual(len(colored_bars), 16)

    def test_exports_vietnamese_visit_report_with_completed_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "ket_qua_kham.pdf"
            xuat_bao_cao_phieu_kham_pdf(
                output_path,
                {
                    "thong_tin": {
                        "ma_benh_nhan": "BN001",
                        "ho_ten": "Nguyễn Thị Ánh",
                        "ngay_sinh": date(1990, 3, 5),
                        "so_dien_thoai": None,
                        "ma_phieu": "PK001",
                        "ngay_gio_kham": datetime(2026, 10, 30, 9, 0),
                        "bac_si": "Bác sĩ Nguyễn Văn A",
                        "trieu_chung": "Đau đầu",
                        "chan_doan": "Viêm xoang",
                    },
                    "ds_xet_nghiem": [
                        {
                            "stt": 1,
                            "ten_xet_nghiem": "Công thức máu",
                            "ket_qua": "Bình thường",
                            "ngay_gio_thuc_hien": datetime(2026, 10, 30, 9, 30),
                            "don_gia_ap_dung": Decimal("90000"),
                        }
                    ],
                    "loi_dan": [
                        {
                            "ngay_lap": date(2026, 10, 30),
                            "loi_dan": "Tái khám sau một tuần",
                        }
                    ],
                    "ds_thuoc": [
                        {
                            "ten_thuoc": "Thuốc giảm đau",
                            "so_luong_ke": 2,
                            "don_vi_tinh": "viên",
                            "cach_dung": "Uống sau ăn",
                            "don_gia_ap_dung": Decimal("10000"),
                            "thanh_tien": Decimal("20000"),
                        }
                    ],
                    "tong_chi_phi": {
                        "gia_kham": Decimal("150000"),
                        "gia_xet_nghiem": Decimal("90000"),
                        "gia_thuoc": Decimal("20000"),
                        "tong_chi_phi": Decimal("260000"),
                    },
                },
            )

            data = output_path.read_bytes()
            self.assertTrue(data.startswith(b"%PDF-"))
            self.assertIn(b"NotoSans", data)

    def test_rejects_missing_column_value(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            with self.assertRaisesRegex(ValueError, "Thiếu dữ liệu"):
                xuat_bang_pdf(
                    Path(temporary_directory) / "bao_cao.pdf",
                    "Báo cáo",
                    "",
                    [{"key": "thang", "label": "Tháng", "kind": "int"}],
                    [{}],
                    {},
                )

    def test_formats_date_and_datetime_as_vietnamese_local_dates(self) -> None:
        from app.pdf_export import _format_value

        self.assertEqual(_format_value(date(2026, 10, 31), "date"), "31/10/2026")
        self.assertEqual(
            _format_value(datetime(2026, 10, 31, 8, 5, 6), "datetime"),
            "31/10/2026 08:05:06",
        )

    def test_formats_report_summary_without_recalculating_values(self) -> None:
        from app.pdf_export import _format_summary_value, _label_for_summary

        self.assertEqual(_label_for_summary("tong_gia_tri"), "Tổng giá trị")
        self.assertEqual(
            _format_summary_value(Decimal("530000.00")), "530.000 VNĐ"
        )
        self.assertEqual(_format_summary_value(12), "12")


if __name__ == "__main__":
    unittest.main()
