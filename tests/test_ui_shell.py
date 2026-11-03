import unittest
from datetime import date, datetime, timedelta
from unittest.mock import patch

from app.ui.app import ClinicApp
from app.demo_data import DEMO_PATIENT_ID
from app.services.appointment_service import (
    lich_theo_benh_nhan,
)
from app.services.clinic_service import lay_benh_nhan, lay_lich_su_benh_nhan
from app.ui.views.appointment_views import PatientAppointmentView
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
                patch("app.ui.views.appointment_views.lay_khoa", return_value=[]),
            ):
                portal = PatientPortal(app, patient, lambda: None)
                portal.grid()
                app.update_idletasks()
                self.assertEqual(len(portal.notebook.tabs()), 3)
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
                self.assertEqual(len(portal.notebook.tabs()), 3)
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

    def test_demo_patient_can_book_reschedule_and_cancel_without_creating_visit(self) -> None:
        app = ClinicApp(demo_mode=True)
        try:
            patient = lay_benh_nhan(DEMO_PATIENT_ID)
            if patient is None:
                self.fail("Demo patient fixture is missing")
            view = PatientAppointmentView(app, patient)
            view.grid(sticky="nsew")
            app.update_idletasks()
            self.assertTrue(view.slots)
            nearest_day = datetime.strptime(
                view.booking_date.get(), "%d/%m/%Y"
            ).date()
            self.assertGreaterEqual(nearest_day, date.today())
            starting_visit_count = len(lay_lich_su_benh_nhan(DEMO_PATIENT_ID))

            first_available_day = next(
                date.today() + timedelta(days=offset)
                for offset in range(1, 31)
            )
            view.booking_date.delete(0, "end")
            view.booking_date.insert(0, first_available_day.strftime("%d/%m/%Y"))
            view._find_slots()
            self.assertTrue(view.slots)
            with patch("app.ui.views.appointment_views.messagebox.showinfo"):
                view._book()
            appointment = lich_theo_benh_nhan(DEMO_PATIENT_ID)[0]
            self.assertEqual(appointment["bat_dau"].date(), first_available_day)
            self.assertEqual(
                len(lay_lich_su_benh_nhan(DEMO_PATIENT_ID)), starting_visit_count
            )

            view.table.selection_set(str(appointment["ma_lich"]))
            view._appointment_selected()
            next_available_day = next(
                date.today() + timedelta(days=offset)
                for offset in range(1, 31)
                if date.today() + timedelta(days=offset) > first_available_day
            )
            view.booking_date.delete(0, "end")
            view.booking_date.insert(0, next_available_day.strftime("%d/%m/%Y"))
            view._find_slots()
            with patch("app.ui.views.appointment_views.messagebox.showinfo"):
                view._reschedule()
            appointment = lich_theo_benh_nhan(DEMO_PATIENT_ID)[0]
            self.assertEqual(appointment["bat_dau"].date(), next_available_day)

            view.table.selection_set(str(appointment["ma_lich"]))
            view._appointment_selected()
            with patch(
                "app.ui.views.appointment_views.simpledialog.askstring",
                return_value="Thay đổi kế hoạch",
            ):
                view._cancel()
            self.assertEqual(
                lich_theo_benh_nhan(DEMO_PATIENT_ID)[0]["trang_thai"],
                "CANCELLED",
            )
        finally:
            app._close()


if __name__ == "__main__":
    unittest.main()
