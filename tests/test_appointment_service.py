from copy import deepcopy
from datetime import date, datetime, time, timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import unittest
from unittest.mock import patch

from app.demo_data import (
    DEMO_DOCTOR_ID,
    DEMO_PATIENT_ID,
    DEMO_SECOND_PATIENT_ID,
    disable_demo_mode,
    enable_demo_mode,
    is_demo_mode,
)
from app.errors import AppError
from app.services import appointment_service
from app.services.clinic_service import hoan_thanh_phieu_kham, tao_phieu_kham
from app.services.appointment_service import (
    cap_nhat_trang_thai,
    cac_khung_gio_trong_ngay,
    dat_lich,
    doi_lich,
    gan_phieu_vao_lich,
    gio_con_trong,
    gio_trong_30_ngay,
    huy_lich,
    lich_theo_bac_si,
    lich_theo_benh_nhan,
    reset_appointment_sessions,
)


class AppointmentServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        enable_demo_mode()
        reset_appointment_sessions()

    def tearDown(self) -> None:
        reset_appointment_sessions()
        disable_demo_mode()

    def _next_workday(self, after: date | None = None) -> date:
        start = after or date.today()
        for offset in range(1, 31):
            candidate = start + timedelta(days=offset)
            if candidate.weekday() in (0, 2):
                return candidate
        self.fail("No doctor workday found within booking horizon")

    def _next_slot(self, on_date: date) -> datetime:
        slots = gio_con_trong(DEMO_DOCTOR_ID, on_date)
        self.assertTrue(slots)
        return slots[0]

    def test_booking_blocks_doctor_overlap_and_patient_second_booking_same_day(self) -> None:
        booking_date = self._next_workday()
        slot = self._next_slot(booking_date)
        booked = dat_lich(DEMO_PATIENT_ID, "Bệnh nhân A", DEMO_DOCTOR_ID, slot)

        with self.assertRaises(AppError) as overlap:
            dat_lich(
                DEMO_SECOND_PATIENT_ID,
                "Bệnh nhân B",
                DEMO_DOCTOR_ID,
                slot,
            )
        self.assertEqual(overlap.exception.code, "KHUNG_GIO_KHONG_CON")

        other_slot = slot + timedelta(minutes=30)
        with self.assertRaises(AppError) as same_day:
            dat_lich(
                DEMO_PATIENT_ID,
                "Bệnh nhân A",
                DEMO_DOCTOR_ID,
                other_slot,
            )
        self.assertEqual(same_day.exception.code, "DA_CO_LICH_TRONG_NGAY")
        self.assertEqual(
            [row["ma_lich"] for row in lich_theo_benh_nhan(DEMO_PATIENT_ID)],
            [booked["ma_lich"]],
        )

    def test_cancel_releases_slot_and_requires_a_reason(self) -> None:
        booking_date = self._next_workday()
        slot = self._next_slot(booking_date)
        appointment = dat_lich(
            DEMO_PATIENT_ID, "Bệnh nhân A", DEMO_DOCTOR_ID, slot
        )

        with self.assertRaises(AppError) as missing_reason:
            huy_lich(appointment["ma_lich"], "patient", DEMO_PATIENT_ID, " ")
        self.assertEqual(missing_reason.exception.code, "DU_LIEU_KHONG_HOP_LE")

        huy_lich(
            appointment["ma_lich"],
            "patient",
            DEMO_PATIENT_ID,
            "Không thể đến khám",
        )
        self.assertIn(slot, gio_con_trong(DEMO_DOCTOR_ID, booking_date))
        self.assertEqual(
            lich_theo_benh_nhan(DEMO_PATIENT_ID)[0]["trang_thai"], "CANCELLED"
        )

    def test_calendar_slots_include_available_and_booked_statuses(self) -> None:
        booking_date = self._next_workday()
        first_slot = self._next_slot(booking_date)
        dat_lich(
            DEMO_PATIENT_ID,
            "Bệnh nhân A",
            DEMO_DOCTOR_ID,
            first_slot,
        )

        slots = dict(cac_khung_gio_trong_ngay(DEMO_DOCTOR_ID, booking_date))

        self.assertEqual(slots[first_slot], "booked")
        self.assertIn("available", slots.values())
        self.assertEqual(
            slots[first_slot + timedelta(minutes=30)], "available"
        )

    def test_reschedule_keeps_old_booking_when_new_slot_is_unavailable(self) -> None:
        first_date = self._next_workday()
        second_date = self._next_workday(first_date)
        original_slot = self._next_slot(first_date)
        occupied_slot = self._next_slot(second_date)
        first = dat_lich(
            DEMO_PATIENT_ID, "Bệnh nhân A", DEMO_DOCTOR_ID, original_slot
        )
        dat_lich(
            DEMO_SECOND_PATIENT_ID,
            "Bệnh nhân B",
            DEMO_DOCTOR_ID,
            occupied_slot,
        )

        with self.assertRaises(AppError) as unavailable:
            doi_lich(first["ma_lich"], DEMO_PATIENT_ID, occupied_slot)
        self.assertEqual(unavailable.exception.code, "KHUNG_GIO_KHONG_CON")
        self.assertEqual(
            lich_theo_benh_nhan(DEMO_PATIENT_ID)[0]["bat_dau"], original_slot
        )

        new_slot = occupied_slot + timedelta(minutes=30)
        changed = doi_lich(first["ma_lich"], DEMO_PATIENT_ID, new_slot)
        self.assertEqual(changed["bat_dau"], new_slot)

    def test_doctor_status_transitions_and_ownership(self) -> None:
        booking_date = date.today()
        appointment_start = datetime.combine(booking_date, time(10))
        appointment = {
            "ma_lich": 1,
            "ma_benh_nhan": DEMO_PATIENT_ID,
            "ten_benh_nhan": "Bệnh nhân A",
            "ma_bac_si": DEMO_DOCTOR_ID,
            "ten_bac_si": "Bác sĩ demo",
            "ten_khoa": "Khoa demo",
            "bat_dau": appointment_start,
            "ket_thuc": appointment_start + timedelta(minutes=30),
            "trang_thai": "CONFIRMED",
            "ly_do_huy": None,
            "ma_phieu_kham": None,
            "tao_luc": appointment_start - timedelta(days=1),
            "cap_nhat_luc": appointment_start - timedelta(days=1),
        }
        appointment_service._session().append(appointment)

        class FrozenDateTime(datetime):
            current = appointment_start - timedelta(minutes=5)

            @classmethod
            def now(cls, tz=None):
                return cls.current

        with patch.object(appointment_service, "datetime", FrozenDateTime):
            with self.assertRaises(AppError) as wrong_doctor:
                cap_nhat_trang_thai(1, DEMO_DOCTOR_ID + 1, "ARRIVED")
            self.assertEqual(wrong_doctor.exception.code, "KHONG_DU_QUYEN")

            arrived = cap_nhat_trang_thai(1, DEMO_DOCTOR_ID, "ARRIVED")
            self.assertEqual(arrived["trang_thai"], "ARRIVED")
            with self.assertRaises(AppError):
                cap_nhat_trang_thai(1, DEMO_DOCTOR_ID, "NO_SHOW")
            with self.assertRaises(AppError):
                cap_nhat_trang_thai(1, DEMO_DOCTOR_ID, "COMPLETED")

            tao_phieu_kham(
                970123, DEMO_PATIENT_ID, DEMO_DOCTOR_ID, "Triệu chứng", "Chẩn đoán"
            )
            gan_phieu_vao_lich(1, DEMO_DOCTOR_ID, 970123)
            hoan_thanh_phieu_kham(970123, DEMO_DOCTOR_ID)
            completed = cap_nhat_trang_thai(
                1, DEMO_DOCTOR_ID, "COMPLETED", ma_phieu_kham=970123
            )
            self.assertEqual(completed["trang_thai"], "COMPLETED")
            self.assertEqual(completed["ma_phieu_kham"], 970123)
            with self.assertRaises(AppError):
                cap_nhat_trang_thai(1, DEMO_DOCTOR_ID, "ARRIVED")

            no_show_appointment = deepcopy(appointment)
            no_show_appointment["ma_lich"] = 2
            no_show_appointment["trang_thai"] = "CONFIRMED"
            appointment_service._session().append(no_show_appointment)
            FrozenDateTime.current = appointment_start + timedelta(minutes=31)
            absent = cap_nhat_trang_thai(2, DEMO_DOCTOR_ID, "NO_SHOW")
            self.assertEqual(absent["trang_thai"], "NO_SHOW")

    def test_booking_rejects_dates_beyond_horizon(self) -> None:
        invalid_date = date.today() + timedelta(days=31)
        with self.assertRaises(AppError) as error:
            gio_con_trong(DEMO_DOCTOR_ID, invalid_date)
        self.assertEqual(error.exception.code, "DU_LIEU_KHONG_HOP_LE")

    def test_find_available_slots_across_horizon_skips_non_workdays(self) -> None:
        available = gio_trong_30_ngay(DEMO_DOCTOR_ID)

        self.assertTrue(available)
        self.assertTrue(
            all(day.weekday() in range(7) for day in available)
        )
        self.assertEqual(
            {day.weekday() for day in available}, set(range(7))
        )
        self.assertTrue(
            all(slots for slots in available.values())
        )
        self.assertTrue(
            all(
                date.today() <= day <= date.today() + timedelta(days=30)
                for day in available
            )
        )

    def test_concurrent_bookings_cannot_claim_the_same_slot(self) -> None:
        booking_date = self._next_workday()
        slot = self._next_slot(booking_date)
        barrier = Barrier(2)
        original_slot_lookup = appointment_service.gio_con_trong

        def wait_until_both_have_checked_slots(
            doctor_id: int,
            requested_date: date,
            exclude_ma_lich: int | None = None,
        ) -> list[datetime]:
            available = original_slot_lookup(
                doctor_id, requested_date, exclude_ma_lich
            )
            barrier.wait(timeout=5)
            return available

        def try_booking(patient_id: int) -> str:
            try:
                dat_lich(
                    patient_id,
                    f"Bệnh nhân {patient_id}",
                    DEMO_DOCTOR_ID,
                    slot,
                )
            except AppError as error:
                return error.code
            return "BOOKED"

        with (
            patch.object(
                appointment_service,
                "gio_con_trong",
                side_effect=wait_until_both_have_checked_slots,
            ),
            ThreadPoolExecutor(max_workers=2) as executor,
        ):
            results = list(
                executor.map(
                    try_booking,
                    (DEMO_PATIENT_ID, DEMO_SECOND_PATIENT_ID),
                )
            )

        self.assertCountEqual(results, ["BOOKED", "KHUNG_GIO_KHONG_CON"])
        self.assertEqual(
            len(lich_theo_bac_si(DEMO_DOCTOR_ID, booking_date)), 1
        )

    def test_list_by_doctor_is_scoped_to_doctor_and_date(self) -> None:
        booking_date = self._next_workday()
        slot = self._next_slot(booking_date)
        appointment = dat_lich(
            DEMO_PATIENT_ID, "Bệnh nhân A", DEMO_DOCTOR_ID, slot
        )

        rows = lich_theo_bac_si(DEMO_DOCTOR_ID, booking_date)
        self.assertEqual([row["ma_lich"] for row in rows], [appointment["ma_lich"]])
        self.assertEqual(lich_theo_bac_si(DEMO_DOCTOR_ID, date.today()), [])

    def test_demo_and_mysql_mode_use_isolated_ram_sessions(self) -> None:
        demo_date = self._next_workday()
        demo_slot = self._next_slot(demo_date)
        dat_lich(DEMO_PATIENT_ID, "Bệnh nhân demo", DEMO_DOCTOR_ID, demo_slot)

        disable_demo_mode()
        real_date = self._next_workday()
        weekday_names = (
            "Thứ Hai",
            "Thứ Ba",
            "Thứ Tư",
            "Thứ Năm",
            "Thứ Sáu",
            "Thứ Bảy",
            "Chủ Nhật",
        )
        doctor = {
            "ma_bac_si": 7,
            "ten_bac_si": "Bác sĩ thật",
            "ma_khoa": 8,
            "gia_kham": 100,
            "phong_kham": "P.1",
        }
        schedule = {
            "ma_bac_si": 7,
            "ten_bac_si": "Bác sĩ thật",
            "phong_kham": "P.1",
            "thu": weekday_names[real_date.weekday()],
            "gio_bat_dau": timedelta(hours=8),
            "gio_ket_thuc": timedelta(hours=10),
        }
        with (
            patch.object(
                appointment_service,
                "_doctor_and_schedule",
                return_value=(doctor, [schedule]),
            ),
            patch.object(
                appointment_service, "_department_name", return_value="Khoa thật"
            ),
        ):
            real_slot = gio_con_trong(7, real_date)[0]
            dat_lich(70, "Bệnh nhân thật", 7, real_slot)
            self.assertEqual(len(lich_theo_benh_nhan(70)), 1)
            self.assertFalse(is_demo_mode())

        enable_demo_mode()
        self.assertEqual(len(lich_theo_benh_nhan(DEMO_PATIENT_ID)), 1)
        self.assertEqual(lich_theo_benh_nhan(70), [])


if __name__ == "__main__":
    unittest.main()
