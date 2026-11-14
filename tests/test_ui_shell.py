import unittest
from datetime import date, datetime, timedelta
from threading import Event
from time import monotonic, sleep
from unittest.mock import patch

from app.ui.app import ClinicApp
from app.demo_data import DEMO_PATIENT_ID
from app.services.appointment_service import (
    gio_trong_30_ngay,
    lich_theo_benh_nhan,
)
from app.services.clinic_service import lay_benh_nhan, lay_lich_su_benh_nhan
from app.ui.views.appointment_views import (
    CancelAppointmentDialog,
    DoctorAppointmentView,
    PatientAppointmentView,
)
from app.ui.views import appointment_views
from app.ui.views.doctor_portal import DoctorPortal
from app.ui.views.patient_portal import PatientPortal
from app.ui.views.patient_portal import DoctorScheduleView
from app.ui.views.patient_portal import _format_work_time


class ClinicShellTests(unittest.TestCase):
    def _wait_until(self, app, condition, timeout: float = 3.0) -> None:
        deadline = monotonic() + timeout
        while not condition() and monotonic() < deadline:
            app.update()
            sleep(0.01)
        self.assertTrue(condition(), "Timed out waiting for background UI work")

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

    def test_doctor_schedule_view_filters_and_shows_degree_and_fee(self) -> None:
        app = ClinicApp(demo_mode=True)
        try:
            view = DoctorScheduleView(app)
            view.grid(sticky="nsew")
            view.department.current(0)
            view._select_department()
            app.update_idletasks()

            self.assertEqual(view.table.heading("chuc_danh", "text"), "Chức danh")
            self.assertEqual(view.table.heading("gia_kham", "text"), "Giá khám")
            self.assertEqual(str(view.title_filter.cget("state")), "readonly")
            self.assertEqual(
                set(view.title_filter.cget("values")),
                {"Tất cả", "Bác sĩ chuyên khoa I (DEMO)"},
            )
            self.assertGreater(len(view.table.get_children()), 0)

            view.doctor_filter.insert(0, "nguyễn minh")
            view.title_filter.set("Bác sĩ chuyên khoa I (DEMO)")
            view.weekday_filter.set("Thứ Hai")
            view._apply_filters()

            filtered_rows = view.table.get_children()
            self.assertEqual(len(filtered_rows), 2)
            row = view.table.item(filtered_rows[0], "values")
            self.assertEqual(row[0], "Nguyễn Minh An (DEMO)")
            self.assertEqual(row[2], "Bác sĩ chuyên khoa I (DEMO)")
            self.assertEqual(row[3], "150.000 VNĐ")
        finally:
            app.destroy()

    def test_doctor_appointments_use_unrestricted_calendar_date_picker(self) -> None:
        app = ClinicApp(demo_mode=True)
        try:
            doctor = {
                "ma_bac_si": 101,
                "ten_bac_si": "Bác sĩ demo",
                "ma_khoa": 1,
            }
            with patch(
                "app.ui.views.appointment_views.lich_theo_bac_si",
                return_value=[],
            ) as load_appointments:
                view = DoctorAppointmentView(app, doctor)
                view.grid(sticky="nsew")
                selected_day = date(2020, 5, 17)
                view.selected_date.set_date(selected_day)

            self.assertIsNone(view.selected_date.minimum)
            self.assertIsNone(view.selected_date.maximum)
            self.assertEqual(view.selected_date.get_date(), selected_day)
            self.assertEqual(
                load_appointments.call_args.args,
                (doctor["ma_bac_si"], selected_day),
            )
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
                patch("app.ui.views.doctor_portal.tim_kiem_benh_nhan", return_value=[]),
                patch("app.ui.views.doctor_portal.bao_cao_bac_si", return_value=[]),
            ):
                portal = DoctorPortal(app, doctor, lambda: None)
                portal.grid()
                app.update_idletasks()
                self.assertEqual(len(portal.notebook.tabs()), 3)
                self.assertEqual(portal.grid_rowconfigure(1)["weight"], 1)
                self.assertEqual(len(portal.appointment_view.card_lists), 3)
                self.assertTrue(hasattr(portal.report_view, "table"))
                self.assertFalse(hasattr(portal.report_view, "chart"))
                portal.destroy()
        finally:
            app.destroy()

    def test_cancel_dialog_requires_reason_and_returns_submitted_reason(self) -> None:
        app = ClinicApp(demo_mode=True)
        try:
            appointment = {
                "ma_lich": 1,
                "ma_benh_nhan": "BN001",
                "ten_benh_nhan": "Bệnh nhân A",
                "ma_bac_si": "BS001",
                "ten_bac_si": "Bác sĩ A",
                "ten_khoa": "Khoa Nội",
                "bat_dau": datetime(2026, 11, 9, 8, 0),
                "ket_thuc": datetime(2026, 11, 9, 8, 30),
                "trang_thai": "CONFIRMED",
                "da_an": False,
                "ly_do_huy": None,
                "ma_phieu_kham": None,
                "tao_luc": datetime(2026, 11, 8, 8, 0),
                "cap_nhat_luc": datetime(2026, 11, 8, 8, 0),
            }
            dialog = CancelAppointmentDialog(app, appointment)
            app.update_idletasks()
            dialog._submit()
            self.assertIsNone(dialog.result)
            self.assertTrue(dialog.winfo_exists())

            dialog.reason.insert("1.0", "Thay đổi kế hoạch")
            dialog._submit()
            self.assertEqual(dialog.result, "Thay đổi kế hoạch")
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

    def test_patient_slot_lookup_does_not_block_tk_event_loop(self) -> None:
        app = ClinicApp(demo_mode=True)
        release_lookup = Event()
        lookup_started = Event()
        lookup_finished = Event()
        event_loop_responsive = Event()
        try:
            patient = lay_benh_nhan(DEMO_PATIENT_ID)
            if patient is None:
                self.fail("Demo patient fixture is missing")
            view = PatientAppointmentView(app, patient)
            view.grid(sticky="nsew")
            self._wait_until(app, lambda: bool(view.doctors))
            original_lookup = appointment_views.cac_khung_gio_trong_ngay

            def slow_lookup(_doctor_id, _selected_date):
                lookup_started.set()
                try:
                    release_lookup.wait(timeout=2)
                    return []
                finally:
                    lookup_finished.set()

            with patch.object(
                appointment_views,
                "cac_khung_gio_trong_ngay",
                side_effect=slow_lookup,
            ):
                view._find_slots()
                self.assertTrue(lookup_started.wait(timeout=1))
                app.after(0, event_loop_responsive.set)
                app.update()
                self.assertTrue(event_loop_responsive.is_set())
        finally:
            release_lookup.set()
            self.assertTrue(lookup_finished.wait(timeout=1))
            app._close()

    def test_demo_patient_can_book_reschedule_and_cancel_without_creating_visit(self) -> None:
        app = ClinicApp(demo_mode=True)
        try:
            patient = lay_benh_nhan(DEMO_PATIENT_ID)
            if patient is None:
                self.fail("Demo patient fixture is missing")
            view = PatientAppointmentView(app, patient)
            view.grid(sticky="nsew")
            self._wait_until(app, lambda: bool(view.doctors))
            starting_visit_count = len(lay_lich_su_benh_nhan(DEMO_PATIENT_ID))
            available_dates = list(
                gio_trong_30_ngay(
                    view.doctors[view.doctor_choice.get()]["ma_bac_si"]
                )
            )
            self.assertTrue(available_dates)
            first_available_day = available_dates[0]
            view.booking_date.set_date(first_available_day)
            self._wait_until(app, lambda: bool(view.slot_statuses))
            self.assertTrue(view.slots)
            with patch("app.ui.views.appointment_views.messagebox.showinfo"):
                view._book()
                self._wait_until(
                    app,
                    lambda: bool(lich_theo_benh_nhan(DEMO_PATIENT_ID))
                    and bool(view.appointments),
                )
            appointment = lich_theo_benh_nhan(DEMO_PATIENT_ID)[0]
            self.assertEqual(appointment["bat_dau"].date(), first_available_day)
            self.assertEqual(
                len(lay_lich_su_benh_nhan(DEMO_PATIENT_ID)), starting_visit_count
            )

            view._select_appointment(str(appointment["ma_lich"]))
            self._wait_until(
                app, lambda: appointment["bat_dau"] in view.slot_statuses
            )
            self.assertEqual(
                view.slot_statuses[appointment["bat_dau"]],
                "booked",
            )
            self.assertNotIn(appointment["bat_dau"], view.slots.values())
            next_available_day = next(
                day for day in available_dates if day > first_available_day
            )
            view.booking_date.set_date(next_available_day)
            self._wait_until(
                app,
                lambda: view.booking_date.get_date() == next_available_day
                and bool(view.slots),
            )
            with patch("app.ui.views.appointment_views.messagebox.showinfo"):
                view._reschedule()
                self._wait_until(
                    app,
                    lambda: lich_theo_benh_nhan(DEMO_PATIENT_ID)[0]["bat_dau"].date()
                    == next_available_day,
                )
            appointment = lich_theo_benh_nhan(DEMO_PATIENT_ID)[0]
            self.assertEqual(appointment["bat_dau"].date(), next_available_day)

            view._select_appointment(str(appointment["ma_lich"]))
            with patch(
                "app.ui.views.appointment_views._ask_cancel_reason",
                return_value="Thay đổi kế hoạch",
            ):
                view._cancel()
                self._wait_until(
                    app,
                    lambda: lich_theo_benh_nhan(DEMO_PATIENT_ID)[0]["trang_thai"]
                    == "CANCELLED",
                )
            self.assertEqual(
                lich_theo_benh_nhan(DEMO_PATIENT_ID)[0]["trang_thai"],
                "CANCELLED",
            )
        finally:
            app._close()


if __name__ == "__main__":
    unittest.main()
