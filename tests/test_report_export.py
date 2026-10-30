import tempfile
import unittest
from pathlib import Path

from app.report_export import export_report_pdf


class ReportExportTests(unittest.TestCase):
    def test_exports_report_with_vietnamese_content(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "bao_cao.pdf"
            result = export_report_pdf(
                output_path,
                "Báo cáo lượt khám",
                ["Bác sĩ", "Số lượt khám"],
                [["Nguyễn Văn A", 12]],
            )

            self.assertEqual(result, output_path)
            self.assertTrue(output_path.is_file())
            self.assertTrue(output_path.read_bytes().startswith(b"%PDF-"))

    def test_rejects_rows_with_wrong_column_count(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "bao_cao.pdf"
            with self.assertRaisesRegex(ValueError, "same number of columns"):
                export_report_pdf(output_path, "Báo cáo", ["Tháng", "Tổng"], [[1]])


if __name__ == "__main__":
    unittest.main()
