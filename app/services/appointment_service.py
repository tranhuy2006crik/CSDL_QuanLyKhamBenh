from __future__ import annotations

from datetime import date, datetime, time, timedelta
import logging
import unicodedata
from threading import RLock
from typing import Literal, cast

import mysql.connector
from mysql.connector.connection import MySQLConnection
from mysql.connector.cursor import MySQLCursorDict

from app.appointment_queries import (
    Q_APPOINTMENT_BY_ID,
    Q_APPOINTMENT_BY_ID_FOR_UPDATE,
    Q_APPOINTMENT_IDS,
    Q_APPOINTMENTS_FOR_DOCTOR_DAY,
    Q_APPOINTMENTS_FOR_PATIENT,
    Q_CANCEL_APPOINTMENT,
    Q_INSERT_APPOINTMENT,
    Q_INSERT_DOSSIER,
    Q_INSERT_VISIT_FROM_APPOINTMENT,
    Q_LOCK_APPOINTMENT_FOR_VISIT,
    Q_LOCK_DOCTOR_FEE,
    Q_PATIENT_APPOINTMENT_FOR_DOCTOR_DAY,
    Q_RESCHEDULE_APPOINTMENT,
)
from app.contracts import (
    AppointmentStatus,
    BacSiChiTietDTO,
    Identifier,
    LichHenDTO,
    LichLamViecDTO,
)
from app.demo_data import is_demo_mode
from app.db import get_connection
from app.errors import (
    AppError,
    app_error_from_database,
    require_identifier,
)
from app.services.clinic_service import lay_bac_si, lay_khoa, lay_lich_lam_viec


logger = logging.getLogger(__name__)

APPOINTMENT_MINUTES = 30
BOOKING_HORIZON_DAYS = 30
ACTIVE_STATUSES = {"CHO_KHAM", "DA_KHAM"}
AppointmentActor = Literal["patient", "doctor"]

_lock = RLock()
_demo_appointments: list[LichHenDTO] = []
_demo_next_id = 1

_WEEKDAYS = {
    "thu hai": 0,
    "thu 2": 0,
    "t2": 0,
    "monday": 0,
    "2": 0,
    "thu ba": 1,
    "thu 3": 1,
    "t3": 1,
    "tuesday": 1,
    "3": 1,
    "thu tu": 2,
    "thu 4": 2,
    "t4": 2,
    "wednesday": 2,
    "4": 2,
    "thu nam": 3,
    "thu 5": 3,
    "t5": 3,
    "thursday": 3,
    "5": 3,
    "thu sau": 4,
    "thu 6": 4,
    "t6": 4,
    "friday": 4,
    "6": 4,
    "thu bay": 5,
    "thu 7": 5,
    "t7": 5,
    "saturday": 5,
    "7": 5,
    "chu nhat": 6,
    "cn": 6,
    "sunday": 6,
    "8": 6,
}


def reset_appointment_sessions() -> None:
    global _demo_next_id
    with _lock:
        _demo_appointments.clear()
        _demo_next_id = 1


def _time_from_value(value: time | timedelta) -> time:
    if isinstance(value, time):
        return value.replace(tzinfo=None)
    seconds = int(value.total_seconds())
    if not 0 <= seconds < 24 * 60 * 60:
        raise AppError(
            "DU_LIEU_KHONG_HOP_LE",
            "Giờ làm việc trong lịch bác sĩ không hợp lệ.",
        )
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return time(hours, minutes, seconds)


def _weekday(value: str | int) -> int:
    folded = unicodedata.normalize("NFD", str(value).strip().casefold())
    normalized = "".join(
        character
        for character in folded
        if not unicodedata.combining(character)
    ).replace("đ", "d")
    weekday = _WEEKDAYS.get(normalized)
    if weekday is None:
        raise AppError(
            "DU_LIEU_KHONG_HOP_LE",
            f"Không hiểu thứ trong lịch làm việc của bác sĩ: {value}.",
        )
    return weekday


def _doctor_and_schedule(
    doctor_id: Identifier,
) -> tuple[BacSiChiTietDTO, list[LichLamViecDTO]]:
    doctor = lay_bac_si(doctor_id)
    if doctor is None:
        raise AppError("KHONG_TIM_THAY", "Không tìm thấy bác sĩ.")
    schedule = [
        row
        for row in lay_lich_lam_viec(doctor["ma_khoa"])
        if row["ma_bac_si"] == doctor_id
    ]
    return doctor, schedule


def _validate_booking_date(booking_date: date) -> None:
    if isinstance(booking_date, datetime) or not isinstance(booking_date, date):
        raise AppError(
            "DU_LIEU_KHONG_HOP_LE", "Ngày hẹn không hợp lệ.", "ngay_hen"
        )
    today = date.today()
    last_day = today + timedelta(days=BOOKING_HORIZON_DAYS)
    if not today <= booking_date <= last_day:
        raise AppError(
            "DU_LIEU_KHONG_HOP_LE",
            f"Chỉ được đặt lịch từ hôm nay đến {last_day:%d/%m/%Y}.",
            "ngay_hen",
        )


def _validate_slot(value: datetime) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is not None
        or value.second != 0
        or value.microsecond != 0
        or value.minute not in (0, 30)
    ):
        raise AppError(
            "DU_LIEU_KHONG_HOP_LE",
            "Giờ hẹn phải là mốc 30 phút, ví dụ 08:00 hoặc 08:30.",
            "gio_hen",
        )


def _active_for_doctor(
    appointments: list[LichHenDTO],
    doctor_id: Identifier,
    exclude_appointment_id: str | None = None,
) -> list[LichHenDTO]:
    return [
        appointment
        for appointment in appointments
        if appointment["ma_bac_si"] == doctor_id
        and appointment["trang_thai"] in ACTIVE_STATUSES
        and appointment["ma_lich"] != exclude_appointment_id
    ]


def _active_for_patient(
    appointments: list[LichHenDTO],
    patient_id: Identifier,
    doctor_id: Identifier,
    on_date: date,
    exclude_appointment_id: str | None = None,
) -> list[LichHenDTO]:
    return [
        appointment
        for appointment in appointments
        if appointment["ma_benh_nhan"] == patient_id
        and appointment["ma_bac_si"] == doctor_id
        and appointment["bat_dau"].date() == on_date
        and appointment["trang_thai"] in ACTIVE_STATUSES
        and appointment["ma_lich"] != exclude_appointment_id
    ]


def _overlaps(start: datetime, end: datetime, other: LichHenDTO) -> bool:
    return start < other["ket_thuc"] and end > other["bat_dau"]


def _slots_for_date(
    booking_date: date,
    schedule: list[LichLamViecDTO],
    appointments: list[LichHenDTO],
) -> list[datetime]:
    now = datetime.now()
    duration = timedelta(minutes=APPOINTMENT_MINUTES)
    slots: set[datetime] = set()
    for row in schedule:
        if _weekday(row["thu"]) != booking_date.weekday():
            continue
        shift_start = datetime.combine(
            booking_date, _time_from_value(row["gio_bat_dau"])
        )
        shift_end = datetime.combine(
            booking_date, _time_from_value(row["gio_ket_thuc"])
        )
        if shift_end <= shift_start:
            raise AppError(
                "DU_LIEU_KHONG_HOP_LE",
                "Ca làm việc phải kết thúc sau giờ bắt đầu.",
            )
        slot = shift_start
        while slot + duration <= shift_end:
            if slot > now and not any(
                appointment["trang_thai"] in ACTIVE_STATUSES
                and _overlaps(slot, slot + duration, appointment)
                for appointment in appointments
            ):
                slots.add(slot)
            slot += duration
    return sorted(slots)


def _appointments_for_doctor_day(
    doctor_id: Identifier, booking_date: date
) -> list[LichHenDTO]:
    if is_demo_mode():
        with _lock:
            return [
                row.copy()
                for row in _active_for_doctor(
                    _demo_appointments, doctor_id
                )
                if row["bat_dau"].date() == booking_date
            ]
    return cast(
        list[LichHenDTO],
        _read(Q_APPOINTMENTS_FOR_DOCTOR_DAY, (doctor_id, booking_date)),
    )


def gio_con_trong(
    ma_bac_si: Identifier,
    ngay_hen: date,
    exclude_ma_lich: str | None = None,
) -> list[datetime]:
    require_identifier(ma_bac_si, "ma_bac_si", "Mã bác sĩ")
    if exclude_ma_lich is not None:
        _validate_sql_code(exclude_ma_lich, "ma_lich", "Mã lịch hẹn")
    _validate_booking_date(ngay_hen)
    _, schedule = _doctor_and_schedule(ma_bac_si)
    appointments = _appointments_for_doctor_day(ma_bac_si, ngay_hen)
    return _slots_for_date(
        ngay_hen,
        schedule,
        [
            row
            for row in appointments
            if row["ma_lich"] != exclude_ma_lich
        ],
    )


def cac_khung_gio_trong_ngay(
    ma_bac_si: Identifier,
    ngay_hen: date,
    exclude_ma_lich: str | None = None,
) -> list[tuple[datetime, str]]:
    require_identifier(ma_bac_si, "ma_bac_si", "Mã bác sĩ")
    if exclude_ma_lich is not None:
        _validate_sql_code(exclude_ma_lich, "ma_lich", "Mã lịch hẹn")
    _validate_booking_date(ngay_hen)
    _, schedule = _doctor_and_schedule(ma_bac_si)
    appointments = [
        row
        for row in _appointments_for_doctor_day(ma_bac_si, ngay_hen)
        if row["ma_lich"] != exclude_ma_lich
    ]

    now = datetime.now()
    duration = timedelta(minutes=APPOINTMENT_MINUTES)
    slots: dict[datetime, str] = {}
    for row in schedule:
        if _weekday(row["thu"]) != ngay_hen.weekday():
            continue
        start = datetime.combine(ngay_hen, _time_from_value(row["gio_bat_dau"]))
        end = datetime.combine(ngay_hen, _time_from_value(row["gio_ket_thuc"]))
        if end <= start:
            raise AppError(
                "DU_LIEU_KHONG_HOP_LE",
                "Ca làm việc phải kết thúc sau giờ bắt đầu.",
            )
        slot = start
        while slot + duration <= end:
            if any(_overlaps(slot, slot + duration, item) for item in appointments):
                status = "booked"
            elif slot <= now:
                status = "past"
            else:
                status = "available"
            slots[slot] = status
            slot += duration
    return sorted(slots.items())


def gio_trong_30_ngay(
    ma_bac_si: Identifier,
    ngay_bat_dau: date | None = None,
) -> dict[date, list[datetime]]:
    require_identifier(ma_bac_si, "ma_bac_si", "Mã bác sĩ")
    start_date = ngay_bat_dau or date.today()
    _validate_booking_date(start_date)
    _, schedule = _doctor_and_schedule(ma_bac_si)
    appointments: list[LichHenDTO] = []
    for offset in range(BOOKING_HORIZON_DAYS + 1):
        candidate = start_date + timedelta(days=offset)
        if candidate > date.today() + timedelta(days=BOOKING_HORIZON_DAYS):
            break
        appointments.extend(_appointments_for_doctor_day(ma_bac_si, candidate))
    available: dict[date, list[datetime]] = {}
    for offset in range(BOOKING_HORIZON_DAYS + 1):
        candidate = start_date + timedelta(days=offset)
        if candidate > date.today() + timedelta(days=BOOKING_HORIZON_DAYS):
            break
        day_appointments = [
            row for row in appointments if row["bat_dau"].date() == candidate
        ]
        slots = _slots_for_date(candidate, schedule, day_appointments)
        if slots:
            available[candidate] = slots
    return available


def _department_name(department_id: Identifier) -> str:
    department = next(
        (row for row in lay_khoa() if row["ma_khoa"] == department_id),
        None,
    )
    if department is None:
        raise AppError(
            "KHONG_TIM_THAY", "Không tìm thấy khoa của bác sĩ đã chọn."
        )
    return department["ten_khoa"]


def _validate_sql_code(value: Identifier, field: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 5:
        raise AppError(
            "DU_LIEU_KHONG_HOP_LE",
            f"{label} phải là chuỗi từ 1 đến 5 ký tự.",
            field,
        )
    return value.strip()


def _new_appointment_id(used_ids: set[str]) -> str:
    for sequence in range(1, 1000):
        candidate = f"LH{sequence:03d}"
        if candidate not in used_ids:
            return candidate
    raise AppError(
        "KHONG_THE_TAO_MA",
        "Đã sử dụng hết dải mã lịch LH001–LH999.",
        "ma_lich",
    )


def _new_demo_appointment_id() -> str:
    global _demo_next_id
    while _demo_next_id <= 999:
        candidate = f"LH{_demo_next_id:03d}"
        _demo_next_id += 1
        if all(row["ma_lich"] != candidate for row in _demo_appointments):
            return candidate
    raise AppError(
        "KHONG_THE_TAO_MA",
        "Đã sử dụng hết dải mã lịch demo LH001–LH999.",
        "ma_lich",
    )


def _build_appointment(
    *,
    ma_lich: str,
    ma_benh_nhan: Identifier,
    ten_benh_nhan: str,
    ma_bac_si: Identifier,
    ten_bac_si: str,
    ten_khoa: str,
    bat_dau: datetime,
    trang_thai: AppointmentStatus = "CHO_KHAM",
    ma_phieu_kham: Identifier | None = None,
) -> LichHenDTO:
    return {
        "ma_lich": ma_lich,
        "ma_benh_nhan": ma_benh_nhan,
        "ten_benh_nhan": ten_benh_nhan,
        "ma_bac_si": ma_bac_si,
        "ten_bac_si": ten_bac_si,
        "ten_khoa": ten_khoa,
        "bat_dau": bat_dau,
        "ket_thuc": bat_dau + timedelta(minutes=APPOINTMENT_MINUTES),
        "trang_thai": trang_thai,
        "ma_phieu_kham": ma_phieu_kham,
    }


def dat_lich(
    ma_benh_nhan: Identifier,
    ten_benh_nhan: str,
    ma_bac_si: Identifier,
    ngay_gio_bat_dau: datetime,
) -> LichHenDTO:
    require_identifier(ma_benh_nhan, "ma_benh_nhan", "Mã bệnh nhân")
    require_identifier(ma_bac_si, "ma_bac_si", "Mã bác sĩ")
    if not isinstance(ten_benh_nhan, str) or not ten_benh_nhan.strip():
        raise AppError(
            "DU_LIEU_KHONG_HOP_LE", "Tên bệnh nhân không hợp lệ."
        )
    _validate_slot(ngay_gio_bat_dau)
    booking_date = ngay_gio_bat_dau.date()
    _validate_booking_date(booking_date)
    doctor, schedule = _doctor_and_schedule(ma_bac_si)
    department = _department_name(doctor["ma_khoa"])
    duration = timedelta(minutes=APPOINTMENT_MINUTES)

    if ngay_gio_bat_dau not in _slots_for_date(
        booking_date, schedule, _appointments_for_doctor_day(ma_bac_si, booking_date)
    ):
        raise AppError(
            "KHUNG_GIO_KHONG_CON",
            "Khung giờ không còn trống hoặc nằm ngoài lịch làm việc. Hãy tải lại giờ trống.",
        )

    if is_demo_mode():
        with _lock:
            if ngay_gio_bat_dau <= datetime.now():
                raise AppError("KHUNG_GIO_KHONG_CON", "Khung giờ đã qua.")
            if _active_for_patient(
                _demo_appointments,
                ma_benh_nhan,
                ma_bac_si,
                booking_date,
            ):
                raise AppError(
                    "DA_CO_LICH_TRONG_NGAY",
                    "Bệnh nhân đã có lịch hoạt động với bác sĩ này trong ngày.",
                )
            if any(
                _overlaps(ngay_gio_bat_dau, ngay_gio_bat_dau + duration, row)
                for row in _active_for_doctor(
                    _demo_appointments, ma_bac_si
                )
            ):
                raise AppError(
                    "KHUNG_GIO_KHONG_CON",
                    "Bác sĩ vừa có lịch khác trong khung giờ này. Hãy chọn giờ khác.",
                )
            appointment = _build_appointment(
                ma_lich=_new_demo_appointment_id(),
                ma_benh_nhan=ma_benh_nhan,
                ten_benh_nhan=ten_benh_nhan.strip(),
                ma_bac_si=ma_bac_si,
                ten_bac_si=doctor["ten_bac_si"],
                ten_khoa=department,
                bat_dau=ngay_gio_bat_dau,
            )
            _demo_appointments.append(appointment)
            return appointment.copy()

    def insert(cursor: MySQLCursorDict) -> LichHenDTO:
        if ngay_gio_bat_dau <= datetime.now():
            raise AppError("KHUNG_GIO_KHONG_CON", "Khung giờ đã qua.")
        cursor.execute(Q_APPOINTMENTS_FOR_DOCTOR_DAY, (ma_bac_si, booking_date))
        existing_doctor_appointments = cast(
            list[LichHenDTO], cursor.fetchall()
        )
        if _slots_for_date(
            booking_date, schedule, existing_doctor_appointments
        ).count(ngay_gio_bat_dau) == 0:
            raise AppError(
                "KHUNG_GIO_KHONG_CON",
                "Khung giờ vừa được đặt. Hãy tải lại giờ trống.",
            )
        cursor.execute(
            Q_PATIENT_APPOINTMENT_FOR_DOCTOR_DAY,
            (ma_benh_nhan, ma_bac_si, booking_date),
        )
        if cursor.fetchone() is not None:
            raise AppError(
                "DA_CO_LICH_TRONG_NGAY",
                "Bệnh nhân đã có lịch hoạt động với bác sĩ này trong ngày.",
            )

        for _attempt in range(3):
            cursor.execute(Q_APPOINTMENT_IDS)
            used_ids = {row["MaLichHen"].strip() for row in cursor.fetchall()}
            appointment_id = _new_appointment_id(used_ids)
            try:
                cursor.execute(
                    Q_INSERT_APPOINTMENT,
                    (
                        appointment_id,
                        ma_bac_si,
                        ma_benh_nhan,
                        booking_date,
                        ngay_gio_bat_dau.time(),
                    ),
                )
            except mysql.connector.Error as error:
                if getattr(error, "errno", None) != 1062:
                    raise
                cursor.execute(
                    "SELECT MaLichHen FROM LichHen WHERE MaLichHen = %s",
                    (appointment_id,),
                )
                if cursor.fetchone() is not None:
                    continue
                raise _appointment_database_error(error) from error
            return _build_appointment(
                ma_lich=appointment_id,
                ma_benh_nhan=ma_benh_nhan,
                ten_benh_nhan=ten_benh_nhan.strip(),
                ma_bac_si=ma_bac_si,
                ten_bac_si=doctor["ten_bac_si"],
                ten_khoa=department,
                bat_dau=ngay_gio_bat_dau,
            )
        raise AppError(
            "KHONG_THE_TAO_MA",
            "Không thể cấp mã lịch hẹn duy nhất. Hãy thử lại.",
        )

    return cast(LichHenDTO, _transaction(insert, Q_INSERT_APPOINTMENT))


def lich_theo_benh_nhan(ma_benh_nhan: Identifier) -> list[LichHenDTO]:
    require_identifier(ma_benh_nhan, "ma_benh_nhan", "Mã bệnh nhân")
    if is_demo_mode():
        with _lock:
            return sorted(
                [
                    row.copy()
                    for row in _demo_appointments
                    if row["ma_benh_nhan"] == ma_benh_nhan
                ],
                key=lambda row: row["bat_dau"],
                reverse=True,
            )
    return cast(
        list[LichHenDTO],
        _read(Q_APPOINTMENTS_FOR_PATIENT, (ma_benh_nhan,)),
    )


def lich_theo_bac_si(
    ma_bac_si: Identifier, ngay_hen: date
) -> list[LichHenDTO]:
    require_identifier(ma_bac_si, "ma_bac_si", "Mã bác sĩ")
    if isinstance(ngay_hen, datetime) or not isinstance(ngay_hen, date):
        raise AppError(
            "DU_LIEU_KHONG_HOP_LE", "Ngày xem lịch không hợp lệ.", "ngay_hen"
        )
    if is_demo_mode():
        with _lock:
            return sorted(
                [
                    row.copy()
                    for row in _demo_appointments
                    if row["ma_bac_si"] == ma_bac_si
                    and row["bat_dau"].date() == ngay_hen
                ],
                key=lambda row: row["bat_dau"],
            )
    return cast(
        list[LichHenDTO],
        _read(Q_APPOINTMENTS_FOR_DOCTOR_DAY, (ma_bac_si, ngay_hen)),
    )





def doi_lich(
    ma_lich: str,
    ma_benh_nhan: Identifier,
    ngay_gio_bat_dau_moi: datetime,
) -> LichHenDTO:
    appointment_id = _validate_sql_code(ma_lich, "ma_lich", "Mã lịch hẹn")
    require_identifier(ma_benh_nhan, "ma_benh_nhan", "Mã bệnh nhân")
    _validate_slot(ngay_gio_bat_dau_moi)
    new_date = ngay_gio_bat_dau_moi.date()
    _validate_booking_date(new_date)

    if is_demo_mode():
        with _lock:
            current = _get_demo_owned_appointment(
                appointment_id, "patient", ma_benh_nhan
            )
            if (
                current["trang_thai"] != "CHO_KHAM"
                or datetime.now() >= current["bat_dau"]
            ):
                raise AppError(
                    "KHONG_THE_DOI_LICH",
                    "Chỉ có thể đổi lịch đang chờ khám trước giờ hẹn.",
                )
            if current["bat_dau"] == ngay_gio_bat_dau_moi:
                raise AppError(
                    "KHUNG_GIO_KHONG_CON",
                    "Khung giờ mới phải khác khung giờ hiện tại.",
                )
            snapshot = current.copy()
            doctor_id = current["ma_bac_si"]

        _, schedule = _doctor_and_schedule(doctor_id)

        with _lock:
            current = _get_demo_owned_appointment(
                appointment_id, "patient", ma_benh_nhan
            )
            if (
                current["trang_thai"] != "CHO_KHAM"
                or datetime.now() >= current["bat_dau"]
                or current["bat_dau"] != snapshot["bat_dau"]
            ):
                raise AppError(
                    "KHONG_THE_DOI_LICH",
                    "Lịch vừa được cập nhật hoặc không còn đủ điều kiện đổi.",
                )
            if any(
                row["ma_lich"] != appointment_id
                for row in _active_for_patient(
                    _demo_appointments,
                    ma_benh_nhan,
                    current["ma_bac_si"],
                    new_date,
                    appointment_id,
                )
            ):
                raise AppError(
                    "DA_CO_LICH_TRONG_NGAY",
                    "Bệnh nhân đã có lịch hoạt động với bác sĩ này trong ngày.",
                )
            candidates = _slots_for_date(
                new_date,
                schedule,
                [
                    row
                    for row in _active_for_doctor(
                        _demo_appointments, current["ma_bac_si"], appointment_id
                    )
                    if row["bat_dau"].date() == new_date
                ],
            )
            if ngay_gio_bat_dau_moi not in candidates:
                raise AppError(
                    "KHUNG_GIO_KHONG_CON",
                    "Khung giờ mới không còn trống hoặc ngoài lịch làm việc.",
                )
            current["bat_dau"] = ngay_gio_bat_dau_moi
            current["ket_thuc"] = ngay_gio_bat_dau_moi + timedelta(minutes=30)
            return current.copy()

    def update(cursor: MySQLCursorDict) -> LichHenDTO:
        current = _get_owned_appointment(
            cursor, appointment_id, "patient", ma_benh_nhan, for_update=True
        )
        if current["trang_thai"] != "CHO_KHAM" or datetime.now() >= current["bat_dau"]:
            raise AppError(
                "KHONG_THE_DOI_LICH",
                "Chỉ có thể đổi lịch đang chờ khám trước giờ hẹn.",
            )
        if current["bat_dau"] == ngay_gio_bat_dau_moi:
            raise AppError(
                "KHUNG_GIO_KHONG_CON",
                "Khung giờ mới phải khác khung giờ hiện tại.",
            )
        doctor, schedule = _doctor_and_schedule(current["ma_bac_si"])
        cursor.execute(
            Q_APPOINTMENTS_FOR_DOCTOR_DAY,
            (current["ma_bac_si"], new_date),
        )
        rows = [
            row
            for row in cast(list[LichHenDTO], cursor.fetchall())
            if row["ma_lich"] != appointment_id
        ]
        if ngay_gio_bat_dau_moi not in _slots_for_date(new_date, schedule, rows):
            raise AppError(
                "KHUNG_GIO_KHONG_CON",
                "Khung giờ mới không còn trống hoặc ngoài lịch làm việc.",
            )
        cursor.execute(
            Q_PATIENT_APPOINTMENT_FOR_DOCTOR_DAY,
            (ma_benh_nhan, current["ma_bac_si"], new_date),
        )
        other = next(
            (
                row
                for row in cursor.fetchall()
                if row["MaLichHen"].strip() != appointment_id
            ),
            None,
        )
        if other is not None:
            raise AppError(
                "DA_CO_LICH_TRONG_NGAY",
                "Bệnh nhân đã có lịch hoạt động với bác sĩ này trong ngày.",
            )
        cursor.execute(
            Q_RESCHEDULE_APPOINTMENT,
            (
                new_date,
                ngay_gio_bat_dau_moi.time(),
                appointment_id,
                ma_benh_nhan,
            ),
        )
        if cursor.rowcount != 1:
            raise AppError(
                "KHONG_THE_DOI_LICH",
                "Lịch vừa được cập nhật hoặc đã được liên kết với phiếu khám.",
            )
        return _build_appointment(
            ma_lich=appointment_id,
            ma_benh_nhan=current["ma_benh_nhan"],
            ten_benh_nhan=current["ten_benh_nhan"],
            ma_bac_si=current["ma_bac_si"],
            ten_bac_si=doctor["ten_bac_si"],
            ten_khoa=_department_name(doctor["ma_khoa"]),
            bat_dau=ngay_gio_bat_dau_moi,
            trang_thai="CHO_KHAM",
        )

    return cast(LichHenDTO, _transaction(update, Q_RESCHEDULE_APPOINTMENT))


def huy_lich(
    ma_lich: str,
    actor: AppointmentActor,
    actor_id: Identifier,
) -> None:
    appointment_id = _validate_sql_code(ma_lich, "ma_lich", "Mã lịch hẹn")
    if actor not in ("patient", "doctor"):
        raise AppError("DU_LIEU_KHONG_HOP_LE", "Vai trò hủy lịch không hợp lệ.")
    require_identifier(actor_id, "actor_id", "Mã người thao tác")
    if is_demo_mode():
        with _lock:
            appointment = _get_demo_owned_appointment(
                appointment_id, actor, actor_id
            )
            if (
                appointment["trang_thai"] != "CHO_KHAM"
                or datetime.now() >= appointment["bat_dau"]
                or appointment["ma_phieu_kham"] is not None
            ):
                raise AppError(
                    "KHONG_THE_HUY_LICH",
                    "Chỉ hủy được lịch đang chờ khám, chưa đến giờ và chưa có phiếu khám.",
                )
            appointment["trang_thai"] = "DA_HUY"
        return

    def cancel(cursor: MySQLCursorDict) -> None:
        current = _get_owned_appointment(
            cursor,
            appointment_id,
            actor,
            actor_id,
            for_update=True,
        )
        if current["trang_thai"] != "CHO_KHAM":
            raise AppError(
                "KHONG_THE_HUY_LICH", "Chỉ hủy được lịch đang ở trạng thái CHO_KHAM."
            )
        if datetime.now() >= current["bat_dau"]:
            raise AppError(
                "KHONG_THE_HUY_LICH", "Không thể hủy lịch sau khi đã đến giờ hẹn."
            )
        cursor.execute(Q_CANCEL_APPOINTMENT, (appointment_id,))
        if cursor.rowcount != 1:
            raise AppError(
                "KHONG_THE_HUY_LICH",
                "Lịch đã được liên kết với phiếu khám hoặc vừa được cập nhật.",
            )

    _transaction(cancel, Q_CANCEL_APPOINTMENT)


def tao_phieu_kham_tu_lich(
    ma_phieu: Identifier,
    ma_lich: str,
    ma_bac_si: Identifier,
    trieu_chung: str | None,
    ma_ho_so_moi: Identifier | None = None,
    chan_doan: str | None = None,
) -> None:
    visit_id = _validate_sql_code(ma_phieu, "ma_phieu", "Mã phiếu khám")
    appointment_id = _validate_sql_code(ma_lich, "ma_lich", "Mã lịch hẹn")
    require_identifier(ma_bac_si, "ma_bac_si", "Mã bác sĩ")
    symptoms = trieu_chung.strip() if isinstance(trieu_chung, str) else ""
    if trieu_chung is not None and not isinstance(trieu_chung, str):
        raise AppError("DU_LIEU_KHONG_HOP_LE", "Triệu chứng phải là văn bản.")
    if chan_doan is not None and not isinstance(chan_doan, str):
        raise AppError("DU_LIEU_KHONG_HOP_LE", "Chẩn đoán phải là văn bản.")
    diagnosis = chan_doan.strip() if chan_doan is not None else ""
    if ma_ho_so_moi is not None:
        _validate_sql_code(ma_ho_so_moi, "ma_ho_so", "Mã hồ sơ")

    if is_demo_mode():
        with _lock:
            appointment = _get_demo_owned_appointment(
                appointment_id, "doctor", ma_bac_si
            )
            if appointment["trang_thai"] != "CHO_KHAM":
                raise AppError(
                    "KHONG_THE_CAP_NHAT",
                    "Chỉ tiếp nhận lịch đang ở trạng thái CHO_KHAM.",
                )
            if appointment["ma_phieu_kham"] is not None:
                raise AppError(
                    "DA_CO_PHIEU_KHAM", "Lịch hẹn đã có phiếu khám liên kết."
                )
            from app.services.clinic_service import tao_phieu_kham

            tao_phieu_kham(
                visit_id,
                appointment["ma_benh_nhan"],
                ma_bac_si,
                symptoms,
                diagnosis or None,
            )
            appointment["ma_phieu_kham"] = visit_id
        return

    def create_visit(cursor: MySQLCursorDict) -> None:
        cursor.execute(Q_LOCK_APPOINTMENT_FOR_VISIT, (appointment_id,))
        appointment = cursor.fetchone()
        if appointment is None:
            raise AppError("KHONG_TIM_THAY", "Không tìm thấy lịch hẹn.")
        if appointment["ma_bac_si"] != ma_bac_si:
            raise AppError("KHONG_DU_QUYEN", "Lịch hẹn không thuộc bác sĩ hiện tại.")
        if appointment["trang_thai"] != "CHO_KHAM":
            raise AppError(
                "KHONG_THE_CAP_NHAT",
                "Chỉ tiếp nhận lịch đang ở trạng thái CHO_KHAM.",
            )
        if appointment["ma_ho_so"] is None:
            if ma_ho_so_moi is None:
                raise AppError(
                    "CAN_MA_HO_SO",
                    "Bệnh nhân chưa có hồ sơ bệnh án. Hãy nhập mã hồ sơ mới.",
                    "ma_ho_so",
                )
            cursor.execute(
                Q_INSERT_DOSSIER,
                (ma_ho_so_moi, appointment["ma_benh_nhan"]),
            )
            dossier_id = ma_ho_so_moi
        else:
            if ma_ho_so_moi is not None:
                raise AppError(
                    "DU_LIEU_KHONG_HOP_LE",
                    "Bệnh nhân đã có hồ sơ bệnh án; không nhập mã hồ sơ mới.",
                    "ma_ho_so",
                )
            dossier_id = appointment["ma_ho_so"]
        cursor.execute(Q_LOCK_DOCTOR_FEE, (ma_bac_si,))
        doctor = cursor.fetchone()
        if doctor is None:
            raise AppError("KHONG_TIM_THAY", "Không tìm thấy bác sĩ.")
        cursor.execute(
            Q_INSERT_VISIT_FROM_APPOINTMENT,
            (
                visit_id,
                ma_bac_si,
                dossier_id,
                appointment_id,
                diagnosis or None,
                symptoms or None,
                doctor["gia_kham"],
            ),
        )

    _transaction(create_visit, Q_INSERT_VISIT_FROM_APPOINTMENT)


def hoan_tat_lich_demo(
    ma_phieu: Identifier, ma_bac_si: Identifier
) -> None:
    if not is_demo_mode():
        return
    with _lock:
        for appointment in _demo_appointments:
            if (
                appointment["ma_phieu_kham"] == ma_phieu
                and appointment["ma_bac_si"] == ma_bac_si
            ):
                if appointment["trang_thai"] != "CHO_KHAM":
                    raise AppError(
                        "KHONG_THE_CAP_NHAT",
                        "Lịch hẹn không còn ở trạng thái CHO_KHAM.",
                    )
                appointment["trang_thai"] = "DA_KHAM"
                return


def _get_demo_owned_appointment(
    ma_lich: str,
    actor: AppointmentActor,
    actor_id: Identifier,
) -> LichHenDTO:
    for appointment in _demo_appointments:
        if appointment["ma_lich"] != ma_lich:
            continue
        owner_id = (
            appointment["ma_benh_nhan"]
            if actor == "patient"
            else appointment["ma_bac_si"]
        )
        if owner_id != actor_id:
            raise AppError(
                "KHONG_DU_QUYEN", "Lịch hẹn không thuộc tài khoản hiện tại."
            )
        return appointment
    raise AppError("KHONG_TIM_THAY", "Không tìm thấy lịch hẹn.")


def _get_owned_appointment(
    cursor: MySQLCursorDict,
    ma_lich: str,
    actor: AppointmentActor,
    actor_id: Identifier,
    *,
    for_update: bool = False,
) -> LichHenDTO:
    query = Q_APPOINTMENT_BY_ID_FOR_UPDATE if for_update else Q_APPOINTMENT_BY_ID
    cursor.execute(query, (ma_lich,))
    row = cursor.fetchone()
    if row is None:
        raise AppError("KHONG_TIM_THAY", "Không tìm thấy lịch hẹn.")
    owner_id = row["ma_benh_nhan"] if actor == "patient" else row["ma_bac_si"]
    if owner_id != actor_id:
        raise AppError("KHONG_DU_QUYEN", "Lịch hẹn không thuộc tài khoản hiện tại.")
    return cast(LichHenDTO, row)


def _read(sql: str, params: tuple[object, ...]) -> list[dict[str, object]]:
    connection = get_connection()
    cursor: MySQLCursorDict | None = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sql, params)
        return cursor.fetchall()
    except mysql.connector.Error as error:
        logger.exception("Appointment query failed")
        raise _appointment_database_error(error) from error
    finally:
        _close(cursor, connection)


def _transaction(operation, statement: str | None = None):
    connection = get_connection()
    cursor: MySQLCursorDict | None = None
    commit_attempted = False
    try:
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)
        result = operation(cursor)
        commit_attempted = True
        connection.commit()
        return result
    except AppError:
        if not commit_attempted:
            _rollback(connection)
        raise
    except mysql.connector.Error as error:
        if commit_attempted:
            raise AppError(
                "COMMIT_CHUA_XAC_DINH",
                "Chưa xác định được kết quả cập nhật lịch hẹn. Hãy tải lại lịch.",
            ) from error
        _rollback(connection)
        logger.exception("Appointment transaction failed")
        raise _appointment_database_error(error, statement) from error
    except Exception:
        if not commit_attempted:
            _rollback(connection)
        raise
    finally:
        _close(cursor, connection)


def _appointment_database_error(
    error: mysql.connector.Error, statement: str | None = None
) -> AppError:
    errno = getattr(error, "errno", None)
    message = str(getattr(error, "msg", error)).casefold()
    if errno == 1062:
        if "uq_lichhen_benhnhan_bacsi_ngay" in message:
            return AppError(
                "DA_CO_LICH_TRONG_NGAY",
                "Bệnh nhân đã có lịch hoạt động với bác sĩ này trong ngày.",
            )
        return AppError(
            "KHUNG_GIO_KHONG_CON",
            "Khung giờ vừa được đặt. Hãy tải lại giờ trống.",
        )
    if errno == 1644 or getattr(error, "sqlstate", None) == "45000":
        if "lich hẹn" in message or "lịch hẹn" in message:
            return AppError("DU_LIEU_KHONG_HOP_LE", str(getattr(error, "msg", error)))
    return app_error_from_database(error, statement)


def _rollback(connection: MySQLConnection) -> None:
    try:
        connection.rollback()
    except mysql.connector.Error:
        logger.exception("Could not roll back appointment transaction")


def _close(
    cursor: MySQLCursorDict | None, connection: MySQLConnection
) -> None:
    if cursor is not None:
        try:
            cursor.close()
        except mysql.connector.Error:
            logger.exception("Could not close appointment cursor")
    try:
        connection.close()
    except mysql.connector.Error:
        logger.exception("Could not close appointment connection")
