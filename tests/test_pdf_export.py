import tempfile
import unittest
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from app.pdf_export import xuat_bang_pdf


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
