from __future__ import annotations

from copy import deepcopy
import unicodedata
from datetime import date, datetime, time, timedelta
from threading import RLock
from typing import Literal, cast

from app.contracts import (
    AppointmentStatus,
    BacSiChiTietDTO,
    Identifier,
    LichHenDTO,
    LichLamViecDTO,
)
from app.demo_data import is_demo_mode
from app.errors import AppError, require_identifier, require_positive_int
from app.services.clinic_service import (
    lay_bac_si,
    lay_khoa,
    lay_lich_lam_viec,
)
from app.services.tra_cuu_service import lay_chi_tiet_lan_kham


APPOINTMENT_MINUTES = 30
BOOKING_HORIZON_DAYS = 30
ACTIVE_STATUSES = {"CONFIRMED", "ARRIVED"}
AppointmentActor = Literal["patient", "doctor"]

_lock = RLock()
_sessions: dict[bool, list[LichHenDTO]] = {False: [], True: []}
_next_ids: dict[bool, int] = {False: 1, True: 1}

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
    with _lock:
        _sessions[False] = []
        _sessions[True] = []
        _next_ids[False] = 1
        _next_ids[True] = 1


def _session() -> list[LichHenDTO]:
    return _sessions[is_demo_mode()]


def _next_id() -> int:
    key = is_demo_mode()
    value = _next_ids[key]
    _next_ids[key] += 1
    return value


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
    normalized = unicodedata.normalize("NFD", str(value).casefold())
    normalized = "".join(
        character
        for character in normalized
        if unicodedata.category(character) != "Mn"
    ).replace("đ", "d")
    normalized = " ".join(normalized.split())
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


def _active_for_doctor(
    doctor_id: Identifier, exclude_appointment_id: int | None = None
) -> list[LichHenDTO]:
    return [
        appointment
        for appointment in _session()
        if appointment["ma_bac_si"] == doctor_id
        and appointment["trang_thai"] in ACTIVE_STATUSES
        and appointment["ma_lich"] != exclude_appointment_id
    ]


def _active_for_patient(
    patient_id: Identifier, exclude_appointment_id: int | None = None
) -> list[LichHenDTO]:
    return [
        appointment
        for appointment in _session()
        if appointment["ma_benh_nhan"] == patient_id
        and appointment["trang_thai"] in ACTIVE_STATUSES
        and appointment["ma_lich"] != exclude_appointment_id
    ]


def _overlaps(start: datetime, end: datetime, other: LichHenDTO) -> bool:
    return start < other["ket_thuc"] and end > other["bat_dau"]


def _slots_for_date(
    ngay_hen: date,
    schedule: list[LichLamViecDTO],
    appointments: list[LichHenDTO],
) -> list[datetime]:
    now = datetime.now()
    duration = timedelta(minutes=APPOINTMENT_MINUTES)
    slots: set[datetime] = set()
    for row in schedule:
        if _weekday(row["thu"]) != ngay_hen.weekday():
            continue
        shift_start = datetime.combine(
            ngay_hen, _time_from_value(row["gio_bat_dau"])
        )
        shift_end = datetime.combine(ngay_hen, _time_from_value(row["gio_ket_thuc"]))
        if shift_end <= shift_start:
            raise AppError(
                "DU_LIEU_KHONG_HOP_LE",
                "Ca làm việc phải kết thúc sau giờ bắt đầu.",
            )
        slot = shift_start
        while slot + duration <= shift_end:
            slot_end = slot + duration
            if slot > now and not any(
                _overlaps(slot, slot_end, appointment)
                for appointment in appointments
            ):
                slots.add(slot)
            slot += duration
    return sorted(slots)


def gio_con_trong(
    ma_bac_si: Identifier,
    ngay_hen: date,
    exclude_ma_lich: int | None = None,
) -> list[datetime]:
    require_identifier(ma_bac_si, "ma_bac_si", "Mã bác sĩ")
    if exclude_ma_lich is not None:
        require_positive_int(exclude_ma_lich, "exclude_ma_lich", "Mã lịch")
    _validate_booking_date(ngay_hen)
    _, schedule = _doctor_and_schedule(ma_bac_si)
    with _lock:
        appointments = deepcopy(_active_for_doctor(ma_bac_si, exclude_ma_lich))
    return _slots_for_date(ngay_hen, schedule, appointments)


def cac_khung_gio_trong_ngay(
    ma_bac_si: Identifier,
    ngay_hen: date,
    exclude_ma_lich: int | None = None,
) -> list[tuple[datetime, str]]:
    require_identifier(ma_bac_si, "ma_bac_si", "Mã bác sĩ")
    if exclude_ma_lich is not None:
        require_positive_int(exclude_ma_lich, "exclude_ma_lich", "Mã lịch")
    _validate_booking_date(ngay_hen)
    _, schedule = _doctor_and_schedule(ma_bac_si)
    with _lock:
        appointments = deepcopy(_active_for_doctor(ma_bac_si, exclude_ma_lich))

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
    with _lock:
        appointments = deepcopy(_active_for_doctor(ma_bac_si))
    available: dict[date, list[datetime]] = {}
    for offset in range(BOOKING_HORIZON_DAYS + 1):
        candidate = start_date + timedelta(days=offset)
        if candidate > date.today() + timedelta(days=BOOKING_HORIZON_DAYS):
            break
        slots = _slots_for_date(candidate, schedule, appointments)
        if slots:
            available[candidate] = slots
    return available


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
    if not isinstance(ngay_gio_bat_dau, datetime) or ngay_gio_bat_dau.tzinfo:
        raise AppError(
            "DU_LIEU_KHONG_HOP_LE", "Ngày giờ hẹn không hợp lệ.", "gio_hen"
        )

    booking_date = ngay_gio_bat_dau.date()
    _validate_booking_date(booking_date)
    doctor, _ = _doctor_and_schedule(ma_bac_si)
    department_name = _department_name(doctor["ma_khoa"])
    slots = gio_con_trong(ma_bac_si, booking_date)
    if ngay_gio_bat_dau not in slots:
        raise AppError(
            "KHUNG_GIO_KHONG_CON",
            "Khung giờ không còn trống hoặc nằm ngoài lịch làm việc. Hãy tải lại giờ trống.",
        )

    with _lock:
        _validate_booking_date(booking_date)
        if ngay_gio_bat_dau <= datetime.now():
            raise AppError(
                "KHUNG_GIO_KHONG_CON",
                "Khung giờ đã qua. Hãy tải lại giờ trống.",
            )
        if any(
            appointment["bat_dau"].date() == booking_date
            for appointment in _active_for_patient(ma_benh_nhan)
        ):
            raise AppError(
                "DA_CO_LICH_TRONG_NGAY",
                "Bệnh nhân đã có một lịch hẹn đang hoạt động trong ngày này.",
            )
        if any(
            _overlaps(
                ngay_gio_bat_dau,
                ngay_gio_bat_dau + timedelta(minutes=APPOINTMENT_MINUTES),
                appointment,
            )
            for appointment in _active_for_doctor(ma_bac_si)
        ):
            raise AppError(
                "KHUNG_GIO_KHONG_CON",
                "Bác sĩ vừa có lịch khác trong khung giờ này. Hãy chọn giờ khác.",
            )
        now = datetime.now()
        appointment: LichHenDTO = {
            "ma_lich": _next_id(),
            "ma_benh_nhan": ma_benh_nhan,
            "ten_benh_nhan": ten_benh_nhan.strip(),
            "ma_bac_si": ma_bac_si,
            "ten_bac_si": doctor["ten_bac_si"],
            "ten_khoa": department_name,
            "bat_dau": ngay_gio_bat_dau,
            "ket_thuc": ngay_gio_bat_dau
            + timedelta(minutes=APPOINTMENT_MINUTES),
            "trang_thai": "CONFIRMED",
            "da_an": False,
            "ly_do_huy": None,
            "ma_phieu_kham": None,
            "tao_luc": now,
            "cap_nhat_luc": now,
        }
        _session().append(appointment)
        return cast(LichHenDTO, appointment.copy())


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


def lich_theo_benh_nhan(
    ma_benh_nhan: Identifier, bao_gom_da_an: bool = False
) -> list[LichHenDTO]:
    require_identifier(ma_benh_nhan, "ma_benh_nhan", "Mã bệnh nhân")
    with _lock:
        rows = [
            row
            for row in _session()
            if row["ma_benh_nhan"] == ma_benh_nhan
            and (bao_gom_da_an or not row["da_an"])
        ]
        return cast(
            list[LichHenDTO],
            [row.copy() for row in sorted(rows, key=lambda item: item["bat_dau"])],
        )


def lich_theo_bac_si(
    ma_bac_si: Identifier, ngay_hen: date, bao_gom_da_an: bool = False
) -> list[LichHenDTO]:
    require_identifier(ma_bac_si, "ma_bac_si", "Mã bác sĩ")
    if isinstance(ngay_hen, datetime) or not isinstance(ngay_hen, date):
        raise AppError(
            "DU_LIEU_KHONG_HOP_LE", "Ngày xem lịch không hợp lệ.", "ngay_hen"
        )
    with _lock:
        rows = [
            row
            for row in _session()
            if row["ma_bac_si"] == ma_bac_si
            and row["bat_dau"].date() == ngay_hen
            and (bao_gom_da_an or not row["da_an"])
        ]
        return cast(
            list[LichHenDTO],
            [row.copy() for row in sorted(rows, key=lambda item: item["bat_dau"])],
        )


def _get_owned_appointment(
    ma_lich: int, actor: AppointmentActor, actor_id: Identifier
) -> LichHenDTO:
    require_positive_int(ma_lich, "ma_lich", "Mã lịch hẹn")
    require_identifier(actor_id, "actor_id", "Mã người thao tác")
    for appointment in _session():
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
    raise AppError("KHONG_TIM_THAY", "Không tìm thấy lịch hẹn trong phiên này.")


def doi_lich(
    ma_lich: int,
    ma_benh_nhan: Identifier,
    ngay_gio_bat_dau_moi: datetime,
) -> LichHenDTO:
    require_identifier(ma_benh_nhan, "ma_benh_nhan", "Mã bệnh nhân")
    if not isinstance(ngay_gio_bat_dau_moi, datetime) or ngay_gio_bat_dau_moi.tzinfo:
        raise AppError(
            "DU_LIEU_KHONG_HOP_LE", "Ngày giờ hẹn mới không hợp lệ."
        )
    with _lock:
        appointment = _get_owned_appointment(ma_lich, "patient", ma_benh_nhan)
        now = datetime.now()
        if appointment["trang_thai"] != "CONFIRMED" or now >= appointment["bat_dau"]:
            raise AppError(
                "KHONG_THE_DOI_LICH",
                "Chỉ có thể đổi lịch đã xác nhận và trước giờ hẹn.",
            )
        new_date = ngay_gio_bat_dau_moi.date()
        _validate_booking_date(new_date)
        if any(
            row["bat_dau"].date() == new_date
            for row in _active_for_patient(ma_benh_nhan, ma_lich)
        ):
            raise AppError(
                "DA_CO_LICH_TRONG_NGAY",
                "Bệnh nhân đã có một lịch hẹn đang hoạt động trong ngày này.",
            )
        slots = gio_con_trong(
            appointment["ma_bac_si"],
            new_date,
            exclude_ma_lich=ma_lich,
        )
        if ngay_gio_bat_dau_moi not in slots:
            raise AppError(
                "KHUNG_GIO_KHONG_CON",
                "Khung giờ mới không còn trống hoặc ngoài lịch làm việc.",
            )
        if datetime.now() >= ngay_gio_bat_dau_moi:
            raise AppError(
                "KHUNG_GIO_KHONG_CON",
                "Khung giờ mới đã qua. Hãy tải lại giờ trống.",
            )
        appointment["bat_dau"] = ngay_gio_bat_dau_moi
        appointment["ket_thuc"] = ngay_gio_bat_dau_moi + timedelta(
            minutes=APPOINTMENT_MINUTES
        )
        appointment["cap_nhat_luc"] = now
        return cast(LichHenDTO, appointment.copy())


def huy_lich(
    ma_lich: int,
    actor: AppointmentActor,
    actor_id: int,
    ly_do: str,
) -> None:
    if actor not in ("patient", "doctor"):
        raise AppError("DU_LIEU_KHONG_HOP_LE", "Vai trò hủy lịch không hợp lệ.")
    if not isinstance(ly_do, str) or not ly_do.strip():
        raise AppError(
            "DU_LIEU_KHONG_HOP_LE", "Cần nhập lý do hủy lịch.", "ly_do"
        )
    with _lock:
        appointment = _get_owned_appointment(ma_lich, actor, actor_id)
        if appointment["trang_thai"] != "CONFIRMED":
            raise AppError(
                "KHONG_THE_HUY_LICH",
                "Chỉ có thể hủy lịch đang ở trạng thái đã xác nhận.",
            )
        if datetime.now() >= appointment["bat_dau"]:
            raise AppError(
                "KHONG_THE_HUY_LICH", "Không thể hủy lịch sau khi đã đến giờ hẹn."
            )
        appointment["trang_thai"] = "CANCELLED"
        appointment["ly_do_huy"] = ly_do.strip()
        appointment["cap_nhat_luc"] = datetime.now()


def cap_nhat_trang_thai(
    ma_lich: int,
    ma_bac_si: Identifier,
    trang_thai_moi: AppointmentStatus,
    ma_phieu_kham: Identifier | None = None,
) -> LichHenDTO:
    require_identifier(ma_bac_si, "ma_bac_si", "Mã bác sĩ")
    if trang_thai_moi not in {"ARRIVED", "COMPLETED", "NO_SHOW"}:
        raise AppError(
            "DU_LIEU_KHONG_HOP_LE", "Trạng thái cập nhật không hợp lệ."
        )
    with _lock:
        appointment = _get_owned_appointment(ma_lich, "doctor", ma_bac_si)
        today = date.today()
        now = datetime.now()
        current = appointment["trang_thai"]
        if trang_thai_moi == "ARRIVED":
            if (
                current != "CONFIRMED"
                or appointment["bat_dau"].date() != today
                or now >= appointment["ket_thuc"]
            ):
                raise AppError(
                    "KHONG_THE_CAP_NHAT",
                    "Chỉ ghi nhận đã đến trong khoảng thời gian của lịch hôm nay.",
                )
        elif trang_thai_moi == "COMPLETED":
            if current != "ARRIVED":
                raise AppError(
                    "KHONG_THE_CAP_NHAT",
                    "Chỉ chuyển sang đã khám sau khi ghi nhận bệnh nhân đã đến.",
                )
            if appointment["ma_phieu_kham"] is None:
                raise AppError(
                    "DU_LIEU_KHONG_HOP_LE",
                    "Cần liên kết phiếu khám thực tế trước khi hoàn tất lịch hẹn.",
                    "ma_phieu_kham",
                )
            require_identifier(ma_phieu_kham, "ma_phieu_kham", "Mã phiếu khám")
            if appointment["ma_phieu_kham"] != ma_phieu_kham:
                raise AppError(
                    "DU_LIEU_KHONG_HOP_LE",
                    "Phiếu khám không khớp với phiếu đã liên kết.",
                    "ma_phieu_kham",
                )
            visit = lay_chi_tiet_lan_kham(
                ma_phieu_kham, "doctor", ma_bac_si
            )
            visit_info = visit["thong_tin"]
            if (
                visit_info["ma_benh_nhan"] != appointment["ma_benh_nhan"]
                or visit_info["ma_bac_si"] != ma_bac_si
                or visit_info["ngay_gio_kham"].date() != appointment["bat_dau"].date()
                or visit_info["trang_thai"] != "HOAN_THANH"
            ):
                raise AppError(
                    "CHUA_HOAN_THANH",
                    "Lịch chỉ chuyển sang đã khám sau khi phiếu khám liên kết hoàn thành.",
                    "ma_phieu_kham",
                )
        elif (
            current != "CONFIRMED"
            or now < appointment["ket_thuc"]
        ):
            raise AppError(
                "KHONG_THE_CAP_NHAT",
                "Chỉ đánh dấu vắng mặt cho lịch đã xác nhận sau khi hết giờ hẹn.",
            )
        appointment["trang_thai"] = trang_thai_moi
        appointment["cap_nhat_luc"] = now
        return cast(LichHenDTO, appointment.copy())


def gan_phieu_vao_lich(
    ma_lich: int, ma_bac_si: Identifier, ma_phieu_kham: Identifier
) -> LichHenDTO:
    require_identifier(ma_bac_si, "ma_bac_si", "Mã bác sĩ")
    require_identifier(ma_phieu_kham, "ma_phieu_kham", "Mã phiếu khám")
    with _lock:
        appointment = _get_owned_appointment(ma_lich, "doctor", ma_bac_si)
        if appointment["trang_thai"] != "ARRIVED":
            raise AppError(
                "KHONG_THE_CAP_NHAT",
                "Chỉ liên kết phiếu khi bệnh nhân đã được ghi nhận đến khám.",
            )
        visit = lay_chi_tiet_lan_kham(ma_phieu_kham, "doctor", ma_bac_si)
        info = visit["thong_tin"]
        if (
            info["ma_benh_nhan"] != appointment["ma_benh_nhan"]
            or info["ma_bac_si"] != ma_bac_si
            or info["ngay_gio_kham"].date() != appointment["bat_dau"].date()
        ):
            raise AppError(
                "DU_LIEU_KHONG_HOP_LE",
                "Phiếu khám phải thuộc đúng bệnh nhân, bác sĩ và ngày hẹn.",
                "ma_phieu_kham",
            )
        if appointment["ma_phieu_kham"] not in (None, ma_phieu_kham):
            raise AppError(
                "PHIEU_DA_LIEN_KET", "Lịch hẹn đã liên kết với một phiếu khám khác."
            )
        appointment["ma_phieu_kham"] = ma_phieu_kham
        appointment["cap_nhat_luc"] = datetime.now()
        return cast(LichHenDTO, appointment.copy())


def an_lich_da_xu_ly(
    ma_lich: int, actor: AppointmentActor, actor_id: Identifier
) -> None:
    with _lock:
        appointment = _get_owned_appointment(ma_lich, actor, actor_id)
        if appointment["trang_thai"] not in {"COMPLETED", "NO_SHOW", "CANCELLED"}:
            raise AppError(
                "KHONG_THE_CAP_NHAT",
                "Chỉ có thể ẩn lịch đã khám, đã hủy hoặc vắng mặt.",
            )
        appointment["da_an"] = True
        appointment["cap_nhat_luc"] = datetime.now()


def hien_lich_da_an(
    ma_lich: int, actor: AppointmentActor, actor_id: Identifier
) -> None:
    with _lock:
        appointment = _get_owned_appointment(ma_lich, actor, actor_id)
        appointment["da_an"] = False
        appointment["cap_nhat_luc"] = datetime.now()
