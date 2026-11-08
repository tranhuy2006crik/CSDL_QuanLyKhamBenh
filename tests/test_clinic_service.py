import unittest
from datetime import timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from app.errors import AppError
from app.finalized_queries import Q_MONTHLY_DOCTOR_STATISTICS
from app.read_queries import (
    Q_INSERT_PHIEU_KHAM,
    Q_INSERT_XET_NGHIEM,
    Q_LICH_SU_BENH_NHAN,
)
from app.services.clinic_service import (
    bao_cao_bac_si,
    lay_lich_lam_viec,
    luu_xet_nghiem,
    tao_phieu_kham,
    xoa_phieu_dang_kham,
)


class ClinicServiceTests(unittest.TestCase):
    def test_visit_history_query_uses_confirmed_cost_formula_and_avoids_row_fanout(self) -> None:
        normalized = " ".join(Q_LICH_SU_BENH_NHAN.split())
        self.assertIn("p.GiaKhamApDung", normalized)
        self.assertIn("COALESCE(x.gia_xet_nghiem, 0)", normalized)
        self.assertIn("COALESCE(d.gia_thuoc, 0)", normalized)
        self.assertIn("GROUP BY MaPhieuKhamBenh", normalized)
        self.assertNotIn("v_tong_hop_lan_kham", normalized)

    def test_report_counts_visit_records_and_includes_cost_components(self) -> None:
        normalized = " ".join(Q_MONTHLY_DOCTOR_STATISTICS.split())
        self.assertIn("COUNT(p.MaPhieuKhamBenh)", normalized)
        self.assertIn("p.GiaKhamApDung", normalized)
        self.assertIn("SUM(DonGiaApDung)", normalized)
        self.assertIn("SUM(ct.SoLuongKe * ct.DonGiaApDung)", normalized)
        self.assertIn("p.TrangThaiPhieuKham = 'HOAN_THANH'", normalized)

    def test_report_uses_finalized_month_and_year_parameters(self) -> None:
        connection = Mock()
        cursor = Mock()
        connection.cursor.return_value = cursor
        cursor.fetchall.return_value = []
        with patch(
            "app.services.clinic_service.get_connection", return_value=connection
        ):
            bao_cao_bac_si(12, 2026)

        cursor.execute.assert_called_once_with(Q_MONTHLY_DOCTOR_STATISTICS, (12, 2026))
        connection.close.assert_called_once()

    def test_schedule_is_sorted_by_weekday_and_start_time(self) -> None:
        rows = [
            {
                "ten_bac_si": "Bác sĩ A",
                "thu": "Thứ Tư",
                "gio_bat_dau": timedelta(hours=8),
            },
            {
                "ten_bac_si": "Bác sĩ A",
                "thu": "Thứ Hai",
                "gio_bat_dau": timedelta(hours=13),
            },
            {
                "ten_bac_si": "Bác sĩ A",
                "thu": "Thứ Hai",
                "gio_bat_dau": timedelta(hours=8),
            },
        ]
        with patch("app.services.clinic_service._read", return_value=rows):
            result = lay_lich_lam_viec(1)

        self.assertEqual(
            [
                (row["thu"], str(row["gio_bat_dau"]))
                for row in result
            ],
            [
                ("Thứ Hai", "8:00:00"),
                ("Thứ Hai", "13:00:00"),
                ("Thứ Tư", "8:00:00"),
            ],
        )

    def test_invalid_manual_visit_id_is_rejected_before_connection(self) -> None:
        with patch("app.services.clinic_service.get_connection") as get_connection:
            with self.assertRaises(AppError):
                tao_phieu_kham(0, 1, 1, None, None)
        get_connection.assert_not_called()

    def test_create_visit_links_patient_dossier_and_snapshots_doctor_fee(self) -> None:
        connection = Mock()
        cursor = Mock()
        connection.cursor.return_value = cursor
        cursor.fetchone.side_effect = [
            {"ma_ho_so": 20},
            {"ma_bac_si": 3, "gia_kham": Decimal("150000")},
        ]
        with patch(
            "app.services.clinic_service.get_connection", return_value=connection
        ):
            tao_phieu_kham(1001, 5, 3, "Đau đầu", "Theo dõi")

        insert = next(
            call for call in cursor.execute.call_args_list if call.args[0] == Q_INSERT_PHIEU_KHAM
        )
        self.assertEqual(
            insert.args[1],
            {
                "ma_phieu": 1001,
                "ma_bac_si": 3,
                "ma_ho_so": 20,
                "chan_doan": "Theo dõi",
                "trieu_chung": "Đau đầu",
                "gia_kham": Decimal("150000"),
            },
        )
        connection.commit.assert_called_once()

    def test_lab_sequence_is_scoped_to_consultation_and_saved_to_its_foreign_key(self) -> None:
        connection = Mock()
        cursor = Mock()
        connection.cursor.return_value = cursor
        cursor.fetchone.side_effect = [
            {"trang_thai": "DANG_KHAM"},
            {"stt": 2},
        ]
        with patch(
            "app.services.clinic_service.get_connection", return_value=connection
        ):
            stt = luu_xet_nghiem(
                1001, "Công thức máu", None, None, Decimal("90000")
            )

        insert = next(
            call for call in cursor.execute.call_args_list if call.args[0] == Q_INSERT_XET_NGHIEM
        )
        self.assertEqual(stt, 2)
        self.assertEqual(insert.args[1]["ma_phieu"], 1001)
        self.assertEqual(insert.args[1]["stt"], 2)
        self.assertEqual(insert.args[1]["ket_qua"], None)
        self.assertEqual(insert.args[1]["don_gia_ap_dung"], Decimal("90000"))
        connection.commit.assert_called_once()

    def test_lab_result_requires_performed_datetime(self) -> None:
        with patch("app.services.clinic_service.get_connection") as get_connection:
            with self.assertRaisesRegex(AppError, "ngày giờ thực hiện"):
                luu_xet_nghiem(
                    1,
                    "Công thức máu",
                    "Bình thường",
                    None,
                    Decimal("100000"),
                )
        get_connection.assert_not_called()

    def test_delete_in_progress_visit_checks_each_dependent_row_count(self) -> None:
        connection, cursor = self._delete_visit_connection(stock_rows=1)

        with patch(
            "app.services.clinic_service.get_connection", return_value=connection
        ):
            xoa_phieu_dang_kham("PK001", "BS001")

        self.assertEqual(cursor.execute.call_count, 8)
        connection.commit.assert_called_once()
        connection.rollback.assert_not_called()
        connection.close.assert_called_once()

    def test_delete_in_progress_visit_rolls_back_if_inventory_refund_is_incomplete(
        self,
    ) -> None:
        connection, _cursor = self._delete_visit_connection(stock_rows=0)

        with patch(
            "app.services.clinic_service.get_connection", return_value=connection
        ):
            with self.assertRaises(AppError) as raised:
                xoa_phieu_dang_kham("PK001", "BS001")

        self.assertEqual(raised.exception.code, "XUNG_DOT_DU_LIEU")
        connection.commit.assert_not_called()
        connection.rollback.assert_called_once()
        connection.close.assert_called_once()

    @staticmethod
    def _delete_visit_connection(stock_rows: int) -> tuple[Mock, Mock]:
        connection = Mock()
        cursor = Mock()
        connection.cursor.return_value = cursor
        cursor.fetchone.return_value = {
            "ma_bac_si": "BS001",
            "trang_thai": "DANG_KHAM",
        }
        cursor.fetchall.side_effect = [
            [{"MaDonThuoc": "DT001"}],
            [{"MaThuoc": "T001"}],
        ]

        def execute(sql: str, _params: object) -> None:
            normalized = " ".join(sql.split())
            if normalized.startswith("UPDATE Thuoc"):
                cursor.rowcount = stock_rows
            elif normalized.startswith("DELETE ct"):
                cursor.rowcount = 1
            elif normalized.startswith("DELETE d"):
                cursor.rowcount = 1
            elif normalized.startswith("DELETE x"):
                cursor.rowcount = 0
            elif normalized.startswith("DELETE FROM PhieuKhamBenh"):
                cursor.rowcount = 1

        cursor.execute.side_effect = execute
        return connection, cursor


if __name__ == "__main__":
    unittest.main()
