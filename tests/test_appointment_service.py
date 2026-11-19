from datetime import date, datetime, time, timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event, Thread
import unittest
from unittest.mock import Mock, patch

from app.demo_data import (
    DEMO_DOCTOR_ID,
    DEMO_PATIENT_ID,
    DEMO_SECOND_PATIENT_ID,
    disable_demo_mode,
    enable_demo_mode,
    is_demo_mode,
)
from app.errors import AppError
from app.appointment_queries import Q_INSERT_VISIT_FROM_APPOINTMENT
from app.services import appointment_service
from app.services.clinic_service import (
    hoan_thanh_phieu_kham,
    luu_noi_dung_kham,
)
from app.services.appointment_service import (
    cac_khung_gio_trong_ngay,
    dat_lich,
    doi_lich,
    gio_con_trong,
    gio_trong_30_ngay,
    huy_lich,
    lich_theo_bac_si,
    lich_theo_benh_nhan,
    reset_appointment_sessions,
    tao_phieu_kham_tu_lich,
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

    def test_cancel_releases_slot_without_reason_column(self) -> None:
        booking_date = self._next_workday()
        slot = self._next_slot(booking_date)
        appointment = dat_lich(
            DEMO_PATIENT_ID, "Bệnh nhân A", DEMO_DOCTOR_ID, slot
        )

        huy_lich(
            appointment["ma_lich"],
            "patient",
            DEMO_PATIENT_ID,
        )
        self.assertIn(slot, gio_con_trong(DEMO_DOCTOR_ID, booking_date))
        self.assertEqual(
            lich_theo_benh_nhan(DEMO_PATIENT_ID)[0]["trang_thai"], "DA_HUY"
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

    def test_reschedule_does_not_make_original_slot_available(self) -> None:
        booking_date = self._next_workday()
        original_slot = self._next_slot(booking_date)
        appointment = dat_lich(
            DEMO_PATIENT_ID, "Bệnh nhân A", DEMO_DOCTOR_ID, original_slot
        )

        self.assertEqual(
            dict(cac_khung_gio_trong_ngay(DEMO_DOCTOR_ID, booking_date))[
                original_slot
            ],
            "booked",
        )
        with self.assertRaises(AppError) as same_slot:
            doi_lich(appointment["ma_lich"], DEMO_PATIENT_ID, original_slot)
        self.assertEqual(same_slot.exception.code, "KHUNG_GIO_KHONG_CON")

    def test_booking_reuses_loaded_doctor_schedule(self) -> None:
        booking_date = self._next_workday()
        doctor_and_schedule = appointment_service._doctor_and_schedule(
            DEMO_DOCTOR_ID
        )
        slot = datetime.combine(booking_date, time(8))
        with (
            patch.object(
                appointment_service,
                "_doctor_and_schedule",
                return_value=doctor_and_schedule,
            ) as load_doctor_schedule,
            patch.object(
                appointment_service, "_department_name", return_value="Khoa demo"
            ),
            patch.object(
                appointment_service, "_slots_for_date", return_value=[slot]
            ),
            patch.object(appointment_service, "gio_con_trong") as reload_slots,
        ):
            dat_lich(DEMO_PATIENT_ID, "Bệnh nhân A", DEMO_DOCTOR_ID, slot)

        load_doctor_schedule.assert_called_once_with(DEMO_DOCTOR_ID)
        reload_slots.assert_not_called()

    def test_reschedule_does_not_hold_session_lock_during_schedule_read(self) -> None:
        first_date = self._next_workday()
        second_date = self._next_workday(first_date)
        original_slot = self._next_slot(first_date)
        new_slot = self._next_slot(second_date)
        appointment = dat_lich(
            DEMO_PATIENT_ID, "Bệnh nhân A", DEMO_DOCTOR_ID, original_slot
        )
        lock_was_available = Event()
        original_schedule_lookup = appointment_service._doctor_and_schedule

        def verify_lock_available(*_args, **_kwargs):
            def acquire_from_another_thread() -> None:
                acquired = appointment_service._lock.acquire(timeout=1)
                if acquired:
                    lock_was_available.set()
                    appointment_service._lock.release()

            thread = Thread(target=acquire_from_another_thread)
            thread.start()
            thread.join(timeout=1.5)
            return original_schedule_lookup(*_args, **_kwargs)

        with patch.object(
            appointment_service,
            "_doctor_and_schedule",
            side_effect=verify_lock_available,
        ):
            updated = doi_lich(
                appointment["ma_lich"], DEMO_PATIENT_ID, new_slot
            )

        self.assertTrue(lock_was_available.is_set())
        self.assertEqual(updated["bat_dau"], new_slot)

    def test_appointment_is_marked_done_only_after_linked_visit_completes(self) -> None:
        booking_date = self._next_workday()
        appointment = dat_lich(
            DEMO_PATIENT_ID,
            "Bệnh nhân A",
            DEMO_DOCTOR_ID,
            self._next_slot(booking_date),
        )
        tao_phieu_kham_tu_lich(
            "PK123",
            appointment["ma_lich"],
            DEMO_DOCTOR_ID,
            "Triệu chứng",
        )
        self.assertEqual(
            lich_theo_benh_nhan(DEMO_PATIENT_ID)[0]["trang_thai"], "CHO_KHAM"
        )

        luu_noi_dung_kham("PK123", "Triệu chứng", "Chẩn đoán")
        hoan_thanh_phieu_kham("PK123", DEMO_DOCTOR_ID)

        updated = lich_theo_benh_nhan(DEMO_PATIENT_ID)[0]
        self.assertEqual(updated["trang_thai"], "DA_KHAM")
        self.assertEqual(updated["ma_phieu_kham"], "PK123")

    def test_mysql_visit_creation_links_appointment_and_saves_diagnosis(self) -> None:
        cursor = Mock()
        cursor.fetchone.side_effect = [
            {
                "ma_bac_si": 3,
                "ma_benh_nhan": 5,
                "ma_ho_so": 20,
                "trang_thai": "CHO_KHAM",
            },
            {"gia_kham": 150000},
        ]

        with (
            patch(
                "app.services.appointment_service.is_demo_mode",
                return_value=False,
            ),
            patch(
                "app.services.appointment_service._transaction",
                side_effect=lambda operation, _statement: operation(cursor),
            ),
        ):
            tao_phieu_kham_tu_lich(
                "PK001",
                "LH001",
                3,
                "Triệu chứng",
                chan_doan="Chẩn đoán",
            )

        insert = next(
            item
            for item in cursor.execute.call_args_list
            if item.args[0] == Q_INSERT_VISIT_FROM_APPOINTMENT
        )
        self.assertEqual(
            insert.args[1],
            (
                "PK001",
                3,
                20,
                "LH001",
                "Chẩn đoán",
                "Triệu chứng",
                150000,
            ),
        )

    def test_mysql_visit_creation_requires_existing_dossier(self) -> None:
        cursor = Mock()
        cursor.fetchone.return_value = {
            "ma_bac_si": 3,
            "ma_benh_nhan": 5,
            "ma_ho_so": None,
            "trang_thai": "CHO_KHAM",
        }

        with (
            patch(
                "app.services.appointment_service.is_demo_mode",
                return_value=False,
            ),
            patch(
                "app.services.appointment_service._transaction",
                side_effect=lambda operation, _statement: operation(cursor),
            ),
            self.assertRaises(AppError) as error,
        ):
            tao_phieu_kham_tu_lich(
                "PK001",
                "LH001",
                3,
                "Triệu chứng",
                chan_doan="Chẩn đoán",
            )

        self.assertEqual(error.exception.code, "CAN_HO_SO_BENH_AN")

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
            "ten_khoa": "Khoa thật",
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
            patch.object(appointment_service, "_read", return_value=[]),
            patch.object(
                appointment_service,
                "_transaction",
                side_effect=lambda operation, _statement: operation(cursor),
            ),
        ):
            cursor = Mock()
            cursor.fetchall.return_value = []
            cursor.fetchone.return_value = None
            cursor.rowcount = 1
            real_slot = gio_con_trong(7, real_date)[0]
            real_appointment = dat_lich(70, "Bệnh nhân thật", 7, real_slot)
            self.assertEqual(real_appointment["ma_benh_nhan"], 70)
            self.assertFalse(is_demo_mode())

        enable_demo_mode()
        self.assertEqual(len(lich_theo_benh_nhan(DEMO_PATIENT_ID)), 1)
        self.assertEqual(lich_theo_benh_nhan(70), [])


if __name__ == "__main__":
    unittest.main()
