import unittest
from datetime import timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from app.errors import AppError
from app.read_queries import (
    Q_BAO_CAO_BAC_SI,
    Q_INSERT_PHIEU_KHAM,
    Q_INSERT_XET_NGHIEM,
    Q_LICH_SU_BENH_NHAN,
)
from app.services.clinic_service import (
    bao_cao_bac_si,
    lay_lich_lam_viec,
    luu_xet_nghiem,
    tao_phieu_kham,
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
        normalized = " ".join(Q_BAO_CAO_BAC_SI.split())
        self.assertIn("COUNT(p.MaPhieuKhamBenh)", normalized)
        self.assertIn("pk.GiaKhamApDung", normalized)
        self.assertIn("SUM(DonGiaApDung)", normalized)
        self.assertIn("SUM(c.SoLuongKe * c.DonGiaApDung)", normalized)

    def test_report_uses_half_open_month_range_and_filters(self) -> None:
        with patch("app.services.clinic_service._read", return_value=[]) as read:
            bao_cao_bac_si(12, 2026, ma_khoa=3, tu_khoa="An", hien_bac_si_rong=False)

        query, params = read.call_args.args
        self.assertEqual(query, Q_BAO_CAO_BAC_SI)
        self.assertEqual(params["tu_ngay"].isoformat(), "2026-12-01")
        self.assertEqual(params["den_ngay"].isoformat(), "2027-01-01")
        self.assertEqual(params["ma_khoa"], 3)
        self.assertEqual(params["mau_tim"], "%An%")
        self.assertEqual(params["hien_bac_si_rong"], 0)

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
        cursor.fetchone.side_effect = [{"MaPhieuKhamBenh": 1001}, {"stt": 2}]
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


if __name__ == "__main__":
    unittest.main()
