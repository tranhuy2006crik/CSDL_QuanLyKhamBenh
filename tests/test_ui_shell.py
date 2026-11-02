import unittest
from datetime import date, timedelta
from unittest.mock import patch

from app.ui.app import ClinicApp
from app.ui.views.doctor_portal import DoctorPortal
from app.ui.views.patient_portal import PatientPortal
from app.ui.views.patient_portal import _format_work_time


class ClinicShellTests(unittest.TestCase):
    def test_mysql_time_duration_is_displayed_as_local_clock_time(self) -> None:
        self.assertEqual(_format_work_time(timedelta(hours=8, minutes=30)), "08:30")

    def test_application_starts_with_patient_and_doctor_role_choices(self) -> None:
        app = ClinicApp()
        try:
            self.assertEqual(app.shell.patient_button.cget("text"), "BỆNH NHÂN\nNhập mã bệnh nhân")
            self.assertEqual(app.shell.doctor_button.cget("text"), "BÁC SĨ\nNhập mã bác sĩ")
        finally:
            app.destroy()

    def test_patient_portal_builds_with_empty_history_and_schedule(self) -> None:
        app = ClinicApp()
        try:
            patient = {
                "ma_benh_nhan": 1,
                "ho_ten": "Nguyen Van A",
                "ngay_sinh": date(2000, 1, 1),
                "nam_sinh": 2000,
                "gioi_tinh": "Nam",
                "dia_chi": "Ha Noi",
                "so_dien_thoai": "0123456789",
            }
            with (
                patch("app.ui.views.patient_portal.lay_lich_su_benh_nhan", return_value=[]),
                patch("app.ui.views.patient_portal.lay_tien_su_benh", return_value=None),
                patch("app.ui.views.patient_portal.lay_khoa", return_value=[]),
            ):
                portal = PatientPortal(app, patient, lambda: None)
                portal.grid()
                app.update_idletasks()
                self.assertEqual(len(portal.notebook.tabs()), 2)
                portal.destroy()
        finally:
            app.destroy()

    def test_doctor_portal_builds_patient_and_report_tabs(self) -> None:
        app = ClinicApp()
        try:
            doctor = {
                "ma_bac_si": 2,
                "ten_bac_si": "Bac si B",
                "ma_khoa": 1,
            }
            with (
                patch("app.ui.views.doctor_portal.lay_khoa", return_value=[]),
                patch("app.ui.views.doctor_portal.lay_danh_sach_bac_si", return_value=[]),
                patch("app.ui.views.doctor_portal.tim_kiem_benh_nhan", return_value=[]),
                patch("app.ui.views.doctor_portal.bao_cao_bac_si", return_value=[]),
            ):
                portal = DoctorPortal(app, doctor, lambda: None)
                portal.grid()
                app.update_idletasks()
                self.assertEqual(len(portal.notebook.tabs()), 2)
                self.assertEqual(portal.grid_rowconfigure(1)["weight"], 1)
                portal.destroy()
        finally:
            app.destroy()

    def test_application_window_fits_inside_screen_with_space_for_taskbar(self) -> None:
        app = ClinicApp()
        try:
            app.update_idletasks()
            self.assertLessEqual(
                app.winfo_height() + 120,
                app.winfo_screenheight() + 10,
            )
        finally:
            app.destroy()


if __name__ == "__main__":
    unittest.main()
