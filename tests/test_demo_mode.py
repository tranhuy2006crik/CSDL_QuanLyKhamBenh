import unittest
from datetime import date
from unittest.mock import patch

import main as application_entry
from app.demo_data import (
    DEMO_DOCTOR_ID,
    DEMO_PATIENT_ID,
    DEMO_SECOND_DEPARTMENT_ID,
    disable_demo_mode,
    enable_demo_mode,
    is_demo_mode,
)
from app.errors import AppError
from app.services.clinic_service import (
    bao_cao_bac_si,
    lay_bac_si,
    lay_benh_nhan,
    lay_danh_sach_bac_si,
    lay_khoa,
    lay_lich_lam_viec,
    lay_lich_su_benh_nhan,
    lay_tien_su_benh,
    luu_noi_dung_kham,
    luu_xet_nghiem,
    tao_phieu_kham,
    tim_kiem_benh_nhan,
)
from app.services.don_thuoc_service import luu_don_thuoc, xoa_don_thuoc
from app.services.tra_cuu_service import (
    lay_chi_tiet_lan_kham,
    lay_don_thuoc,
    lay_thuoc,
)
from app.ui.app import ClinicApp


class DemoModeTests(unittest.TestCase):
    def setUp(self) -> None:
        enable_demo_mode()

    def tearDown(self) -> None:
        disable_demo_mode()

    def test_interactive_service_reads_and_writes_never_connect_to_mysql(self) -> None:
        with (
            patch("app.services.clinic_service.get_connection") as clinic_connection,
            patch("app.services.tra_cuu_service.get_connection") as lookup_connection,
            patch("app.services.don_thuoc_service.get_connection") as prescription_connection,
        ):
            self.assertEqual(lay_benh_nhan(DEMO_PATIENT_ID)["ma_benh_nhan"], DEMO_PATIENT_ID)
            self.assertEqual(lay_bac_si(DEMO_DOCTOR_ID)["ma_bac_si"], DEMO_DOCTOR_ID)
            self.assertEqual(len(lay_khoa()), 2)
            self.assertEqual(len(lay_danh_sach_bac_si()), 2)
            self.assertEqual(len(lay_thuoc()), 3)
            self.assertTrue(lay_tien_su_benh(DEMO_PATIENT_ID))
            self.assertTrue(lay_lich_su_benh_nhan(DEMO_PATIENT_ID))
            self.assertTrue(lay_lich_lam_viec(DEMO_SECOND_DEPARTMENT_ID))
            self.assertTrue(tim_kiem_benh_nhan("Huy"))
            self.assertTrue(
                bao_cao_bac_si(date.today().month, date.today().year)
            )
            self.assertTrue(lay_chi_tiet_lan_kham(970001)["ds_xet_nghiem"])
            self.assertIsNotNone(lay_don_thuoc(970001))

            tao_phieu_kham(970003, DEMO_PATIENT_ID, DEMO_DOCTOR_ID, "Đau đầu", None)
            luu_noi_dung_kham(970003, "Đau đầu", "Theo dõi")
            self.assertEqual(
                luu_xet_nghiem(
                    970003,
                    "Xét nghiệm demo",
                    None,
                    None,
                    "12500",
                ),
                1,
            )
            saved = luu_don_thuoc(
                970003,
                960003,
                date.today(),
                "Lời dặn demo",
                [
                    {
                        "ma_thuoc": 990003,
                        "so_luong_ke": 2,
                        "cach_dung": "Dùng thử",
                    }
                ],
                tao_moi=True,
            )
            self.assertEqual(saved["ma_don"], 960003)
            self.assertEqual(saved["ds_thuoc"][0]["don_gia_ap_dung"], 12000)
            edited = luu_don_thuoc(
                970003,
                960003,
                date.today(),
                "Đã chỉnh sửa trong bộ nhớ",
                [
                    {
                        "ma_thuoc": 990003,
                        "so_luong_ke": 3,
                        "cach_dung": "Dùng thử",
                    }
                ],
                tao_moi=False,
            )
            self.assertEqual(edited["ds_thuoc"][0]["don_gia_ap_dung"], 12000)
            self.assertEqual(
                next(item for item in lay_thuoc() if item["ma_thuoc"] == 990003)[
                    "so_luong_co_san"
                ],
                27,
            )
            xoa_don_thuoc(970003, 960003)
            self.assertEqual(
                next(item for item in lay_thuoc() if item["ma_thuoc"] == 990003)[
                    "so_luong_co_san"
                ],
                30,
            )

        clinic_connection.assert_not_called()
        lookup_connection.assert_not_called()
        prescription_connection.assert_not_called()

    def test_demo_session_is_opt_in_and_reset_when_enabled_again(self) -> None:
        self.assertTrue(is_demo_mode())
        tao_phieu_kham(970099, DEMO_PATIENT_ID, DEMO_DOCTOR_ID, None, None)

        enable_demo_mode()

        with self.assertRaises(AppError):
            lay_chi_tiet_lan_kham(970099)
        disable_demo_mode()
        self.assertFalse(is_demo_mode())

    def test_command_line_flag_explicitly_selects_demo_mode(self) -> None:
        with patch.object(application_entry, "ClinicApp") as app_class:
            application_entry.main(["--demo"])
            application_entry.main([])

        self.assertEqual(
            [call.kwargs for call in app_class.call_args_list],
            [{"demo_mode": True}, {"demo_mode": False}],
        )
        self.assertEqual(app_class.return_value.mainloop.call_count, 2)

    def test_demo_window_identifies_offline_mode_and_cleans_up_on_close(self) -> None:
        app = ClinicApp(demo_mode=True)
        try:
            self.assertIn("DEMO OFFLINE", app.title())
            home = app.shell.winfo_children()[0]
            labels = [
                child.cget("text")
                for child in home.winfo_children()
                if child.winfo_class() == "TLabel"
            ]
            self.assertTrue(any("900001" in text and "900101" in text for text in labels))
        finally:
            app._close()
        self.assertFalse(is_demo_mode())


if __name__ == "__main__":
    unittest.main()
