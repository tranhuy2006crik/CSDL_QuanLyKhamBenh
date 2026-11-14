import logging
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, cast

import mysql.connector
from mysql.connector.connection import MySQLConnection
from mysql.connector.cursor import MySQLCursorDict

from app.contracts import (
    BaoCaoBacSiRow,
    BacSiChiTietDTO,
    BacSiDTO,
    BenhNhanDTO,
    Identifier,
    KhoaDTO,
    LichLamViecDTO,
    LichSuKhamRow,
)
from app.demo_data import demo_data, is_demo_mode
from app.db import get_connection
from app.errors import (
    AppError,
    app_error_from_database,
    require_identifier,
    require_positive_int,
)
from app.finalized_queries import (
    Q_COMPLETE_VISIT,
    Q_FIND_IN_PROGRESS_VISIT,
    Q_MONTHLY_DOCTOR_STATISTICS,
    Q_SEARCH_PATIENTS,
)
from app.read_queries import (
    Q_BAC_SI,
    Q_BAC_SI_THEO_MA,
    Q_BENH_NHAN_THEO_MA,
    Q_INSERT_PHIEU_KHAM,
    Q_INSERT_XET_NGHIEM,
    Q_HO_SO_BENH_AN,
    Q_KHOA,
    Q_LICH_LAM_VIEC,
    Q_LICH_SU_BENH_NHAN,
    Q_LOCK_BAC_SI_GIA,
    Q_LOCK_HO_SO_BENH_NHAN,
    Q_LOCK_PHIEU_KHAM,
    Q_LOCK_XET_NGHIEM,
    Q_NEXT_STT_XET_NGHIEM,
    Q_UPDATE_NOI_DUNG_KHAM,
    Q_UPDATE_XET_NGHIEM,
)

logger = logging.getLogger(__name__)


def _read(sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(sql, params or {})
            return cursor.fetchall()
        finally:
            cursor.close()
    except mysql.connector.Error as error:
        logger.exception("Clinic read query failed")
        raise app_error_from_database(error) from error
    finally:
        connection.close()


def _get_one(sql: str, params: dict[str, Any]) -> dict[str, Any] | None:
    rows = _read(sql, params)
    return rows[0] if rows else None


def lay_khoa() -> list[KhoaDTO]:
    if is_demo_mode():
        return cast(list[KhoaDTO], demo_data().list_departments())
    return cast(list[KhoaDTO], _read(Q_KHOA))


def lay_danh_sach_bac_si(ma_khoa: Identifier | None = None) -> list[BacSiDTO]:
    if ma_khoa is not None:
        require_identifier(ma_khoa, "ma_khoa", "Mã khoa")
    if is_demo_mode():
        return cast(list[BacSiDTO], demo_data().list_doctors(ma_khoa))
    return cast(list[BacSiDTO], _read(Q_BAC_SI, {"ma_khoa": ma_khoa}))


def lay_bac_si(ma_bac_si: Identifier) -> BacSiChiTietDTO | None:
    require_identifier(ma_bac_si, "ma_bac_si", "Mã bác sĩ")
    if is_demo_mode():
        return cast(BacSiChiTietDTO | None, demo_data().get_doctor(ma_bac_si))
    row = _get_one(Q_BAC_SI_THEO_MA, {"ma_bac_si": ma_bac_si})
    return cast(BacSiChiTietDTO | None, row)


def lay_benh_nhan(ma_benh_nhan: Identifier) -> BenhNhanDTO | None:
    require_identifier(ma_benh_nhan, "ma_benh_nhan", "Mã bệnh nhân")
    if is_demo_mode():
        return cast(BenhNhanDTO | None, demo_data().get_patient(ma_benh_nhan))
    row = _get_one(Q_BENH_NHAN_THEO_MA, {"ma_benh_nhan": ma_benh_nhan})
    return cast(BenhNhanDTO | None, row)


def tim_kiem_benh_nhan(
    tu_khoa: str = "",
    ngay_sinh: date | None = None,
    gioi_tinh: str | None = None,
    dia_chi: str = "",
) -> list[BenhNhanDTO]:
    keyword = tu_khoa.strip()
    if ngay_sinh is not None and (
        isinstance(ngay_sinh, datetime) or not isinstance(ngay_sinh, date)
    ):
        raise AppError("DU_LIEU_KHONG_HOP_LE", "Ngày sinh không hợp lệ.", "ngay_sinh")
    if gioi_tinh and gioi_tinh.upper() not in {"NAM", "NU", "KHAC"}:
        raise AppError("DU_LIEU_KHONG_HOP_LE", "Giới tính không hợp lệ.", "gioi_tinh")
    address = dia_chi.strip()
    if is_demo_mode():
        rows = demo_data().search_patients(keyword, None, None)
        return cast(
            list[BenhNhanDTO],
            [
                row
                for row in rows
                if (ngay_sinh is None or row["ngay_sinh"] == ngay_sinh)
                and (
                    not gioi_tinh
                    or (row["gioi_tinh"] or "").upper() == gioi_tinh.upper()
                )
                and address.casefold() in (row["dia_chi"] or "").casefold()
            ],
        )
    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                Q_SEARCH_PATIENTS,
                (keyword, keyword, keyword, ngay_sinh, gioi_tinh, address),
            )
            rows = cursor.fetchall()
        finally:
            cursor.close()
    except mysql.connector.Error as error:
        logger.exception("Patient search query failed")
        raise app_error_from_database(error) from error
    finally:
        connection.close()
    return cast(
        list[BenhNhanDTO],
        [
            {
                "ma_benh_nhan": row["MaBenhNhan"],
                "ho_ten": row["HoTen"],
                "ngay_sinh": row["NgaySinh"],
                "nam_sinh": row["NgaySinh"].year if row["NgaySinh"] else None,
                "gioi_tinh": row["GioiTinh"],
                "dia_chi": row["DiaChi"],
                "so_dien_thoai": row["SoDienThoai"],
            }
            for row in rows
        ],
    )


def lay_lich_su_benh_nhan(ma_benh_nhan: Identifier) -> list[LichSuKhamRow]:
    require_identifier(ma_benh_nhan, "ma_benh_nhan", "Mã bệnh nhân")
    if is_demo_mode():
        return cast(list[LichSuKhamRow], demo_data().history(ma_benh_nhan))
    return cast(
        list[LichSuKhamRow],
        _read(Q_LICH_SU_BENH_NHAN, {"ma_benh_nhan": ma_benh_nhan}),
    )


def lay_tien_su_benh(ma_benh_nhan: Identifier) -> str | None:
    require_identifier(ma_benh_nhan, "ma_benh_nhan", "Mã bệnh nhân")
    if is_demo_mode():
        return demo_data().medical_history(ma_benh_nhan)
    row = _get_one(Q_HO_SO_BENH_AN, {"ma_benh_nhan": ma_benh_nhan})
    if row is None:
        return None
    return row["tien_su_benh"]


def _weekday_order(value: str | int) -> tuple[int, str]:
    normalized = str(value).strip().casefold().replace("đ", "d")
    aliases = (
        ("thu hai", "thứ hai", "thu 2", "thứ 2", "t2", "monday", "2"),
        ("thu ba", "thứ ba", "thu 3", "thứ 3", "t3", "tuesday", "3"),
        ("thu tu", "thứ tư", "thu 4", "thứ 4", "t4", "wednesday", "4"),
        ("thu nam", "thứ năm", "thu 5", "thứ 5", "t5", "thursday", "5"),
        ("thu sau", "thứ sáu", "thu 6", "thứ 6", "t6", "friday", "6"),
        ("thu bay", "thứ bảy", "thu 7", "thứ 7", "t7", "saturday", "7"),
        ("chu nhat", "chủ nhật", "cn", "sunday", "8"),
    )
    for index, choices in enumerate(aliases):
        if normalized in choices:
            return index, value
    return len(aliases), value


def _time_order(value: time | timedelta) -> float:
    if isinstance(value, timedelta):
        return value.total_seconds()
    return value.hour * 3600 + value.minute * 60 + value.second


def lay_lich_lam_viec(ma_khoa: Identifier) -> list[LichLamViecDTO]:
    require_identifier(ma_khoa, "ma_khoa", "Mã khoa")
    if is_demo_mode():
        rows = cast(list[LichLamViecDTO], demo_data().weekly_schedule(ma_khoa))
        rows.sort(
            key=lambda row: (
                row["ten_bac_si"].casefold(),
                *_weekday_order(row["thu"]),
                _time_order(row["gio_bat_dau"]),
            )
        )
        return rows
    rows = cast(
        list[LichLamViecDTO],
        _read(Q_LICH_LAM_VIEC, {"ma_khoa": ma_khoa}),
    )
    rows.sort(
        key=lambda row: (
            row["ten_bac_si"].casefold(),
            *_weekday_order(row["thu"]),
            _time_order(row["gio_bat_dau"]),
        )
    )
    return rows


def bao_cao_bac_si(
    thang: int,
    nam: int,
) -> list[BaoCaoBacSiRow]:
    if isinstance(thang, bool) or not isinstance(thang, int) or not 1 <= thang <= 12:
        raise AppError("DU_LIEU_KHONG_HOP_LE", "Tháng phải từ 1 đến 12.", "thang")
    if isinstance(nam, bool) or not isinstance(nam, int) or not 1 <= nam <= 9998:
        raise AppError("DU_LIEU_KHONG_HOP_LE", "Năm không hợp lệ.", "nam")

    start = date(nam, thang, 1)
    end = date(nam + (thang == 12), 1 if thang == 12 else thang + 1, 1)
    if is_demo_mode():
        return cast(
            list[BaoCaoBacSiRow],
            demo_data().report(start, end, None, "", True),
        )
    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(Q_MONTHLY_DOCTOR_STATISTICS, (thang, nam))
            rows = cursor.fetchall()
        finally:
            cursor.close()
    except mysql.connector.Error as error:
        logger.exception("Monthly doctor statistics query failed")
        raise app_error_from_database(error) from error
    finally:
        connection.close()
    return cast(
        list[BaoCaoBacSiRow],
        [
            {
                "ma_bac_si": row["MaBacSi"],
                "ten_bac_si": row["TenBacSi"],
                "so_luot_kham": row["SoLuotKham"],
                "so_benh_nhan": row["SoBenhNhan"],
                "gia_kham": row["TongTienKham"],
                "gia_xet_nghiem": row["TongTienXetNghiem"],
                "gia_thuoc": row["TongTienThuoc"],
                "tong_gia_tri": row["TongGiaTriKham"],
            }
            for row in rows
        ],
    )


def _validate_id(value: Identifier, field: str, label: str) -> None:
    require_identifier(value, field, label)


def _rollback(connection: MySQLConnection) -> None:
    try:
        connection.rollback()
    except mysql.connector.Error:
        logger.exception("Could not roll back clinic transaction")


def _close_transaction(
    cursor: MySQLCursorDict | None, connection: MySQLConnection
) -> None:
    if cursor is not None:
        try:
            cursor.close()
        except mysql.connector.Error:
            logger.exception("Could not close clinic cursor")
    try:
        connection.close()
    except mysql.connector.Error:
        logger.exception("Could not close clinic connection")


def _clean_optional_text(value: str | None, field: str, label: str) -> str | None:
    if value is not None and not isinstance(value, str):
        raise AppError("DU_LIEU_KHONG_HOP_LE", f"{label} phải là văn bản.", field)
    cleaned = value.strip() if value is not None else ""
    return cleaned or None


def tao_phieu_kham(
    ma_phieu: Identifier,
    ma_benh_nhan: Identifier,
    ma_bac_si: Identifier,
    trieu_chung: str | None,
    chan_doan: str | None,
) -> None:
    _validate_id(ma_phieu, "ma_phieu", "Mã phiếu khám")
    _validate_id(ma_benh_nhan, "ma_benh_nhan", "Mã bệnh nhân")
    _validate_id(ma_bac_si, "ma_bac_si", "Mã bác sĩ")
    cleaned_symptoms = _clean_optional_text(trieu_chung, "trieu_chung", "Triệu chứng")
    cleaned_diagnosis = _clean_optional_text(chan_doan, "chan_doan", "Chẩn đoán")

    if is_demo_mode():
        demo_data().create_visit(
            ma_phieu,
            ma_benh_nhan,
            ma_bac_si,
            cleaned_symptoms,
            cleaned_diagnosis,
        )
        return

    connection = get_connection()
    cursor: MySQLCursorDict | None = None
    commit_attempted = False
    try:
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(Q_LOCK_HO_SO_BENH_NHAN, {"ma_benh_nhan": ma_benh_nhan})
        dossier = cursor.fetchone()
        if dossier is None:
            raise AppError(
                "KHONG_TIM_THAY",
                "Bệnh nhân chưa có hồ sơ bệnh án trong CSDL.",
            )
        cursor.execute(Q_LOCK_BAC_SI_GIA, {"ma_bac_si": ma_bac_si})
        doctor = cursor.fetchone()
        if doctor is None:
            raise AppError("KHONG_TIM_THAY", "Không tìm thấy bác sĩ.")
        cursor.execute(
            Q_INSERT_PHIEU_KHAM,
            {
                "ma_phieu": ma_phieu,
                "ma_bac_si": ma_bac_si,
                "ma_ho_so": dossier["ma_ho_so"],
                "chan_doan": cleaned_diagnosis,
                "trieu_chung": cleaned_symptoms,
                "gia_kham": doctor["gia_kham"],
            },
        )
        commit_attempted = True
        connection.commit()
    except AppError:
        if not commit_attempted:
            _rollback(connection)
        raise
    except mysql.connector.Error as error:
        if commit_attempted:
            raise AppError(
                "COMMIT_CHUA_XAC_DINH",
                (
                    f"Chưa xác định được phiếu khám {ma_phieu} đã lưu hay chưa. "
                    "Hãy tải lại hồ sơ bệnh án và kiểm tra mã phiếu trước khi thử lại."
                ),
            ) from error
        _rollback(connection)
        logger.exception("Could not create consultation %s", ma_phieu)
        raise app_error_from_database(error, Q_INSERT_PHIEU_KHAM) from error
    except Exception as error:
        if commit_attempted:
            raise AppError(
                "COMMIT_CHUA_XAC_DINH",
                (
                    f"Chưa xác định được phiếu khám {ma_phieu} đã lưu hay chưa. "
                    "Hãy tải lại hồ sơ bệnh án và kiểm tra mã phiếu trước khi thử lại."
                ),
            ) from error
        _rollback(connection)
        raise
    finally:
        _close_transaction(cursor, connection)


def luu_noi_dung_kham(
    ma_phieu: Identifier,
    trieu_chung: str | None,
    chan_doan: str | None,
) -> None:
    _validate_id(ma_phieu, "ma_phieu", "Mã phiếu khám")
    params = {
        "ma_phieu": ma_phieu,
        "trieu_chung": _clean_optional_text(trieu_chung, "trieu_chung", "Triệu chứng"),
        "chan_doan": _clean_optional_text(chan_doan, "chan_doan", "Chẩn đoán"),
    }
    if is_demo_mode():
        demo_data().update_visit(ma_phieu, params["trieu_chung"], params["chan_doan"])
        return
    connection = get_connection()
    cursor: MySQLCursorDict | None = None
    commit_attempted = False
    try:
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(Q_LOCK_PHIEU_KHAM, {"ma_phieu": ma_phieu})
        locked_visit = cursor.fetchone()
        if locked_visit is None:
            raise AppError("KHONG_TIM_THAY", "Không tìm thấy phiếu khám.")
        if locked_visit["trang_thai"] != "DANG_KHAM":
            raise AppError(
                "PHIEU_DA_HOAN_THANH", "Phiếu khám đã hoàn thành và chỉ được xem."
            )
        cursor.execute(Q_UPDATE_NOI_DUNG_KHAM, params)
        commit_attempted = True
        connection.commit()
    except AppError:
        if not commit_attempted:
            _rollback(connection)
        raise
    except mysql.connector.Error as error:
        if commit_attempted:
            raise AppError(
                "COMMIT_CHUA_XAC_DINH",
                "Chưa xác định được kết quả cập nhật. Hãy tải lại phiếu khám trước khi thao tác tiếp.",
            ) from error
        _rollback(connection)
        logger.exception("Could not update consultation %s", ma_phieu)
        raise app_error_from_database(error, Q_UPDATE_NOI_DUNG_KHAM) from error
    except Exception as error:
        if commit_attempted:
            raise AppError(
                "COMMIT_CHUA_XAC_DINH",
                "Chưa xác định được kết quả cập nhật. Hãy tải lại phiếu khám trước khi thao tác tiếp.",
            ) from error
        _rollback(connection)
        raise
    finally:
        _close_transaction(cursor, connection)


def luu_xet_nghiem(
    ma_phieu: Identifier,
    ten_xet_nghiem: str,
    ket_qua: str | None,
    ngay_gio_thuc_hien: datetime | None,
    don_gia_ap_dung: Decimal | str | int,
    stt: int | None = None,
) -> int:
    _validate_id(ma_phieu, "ma_phieu", "Mã phiếu khám")
    if stt is not None:
        require_positive_int(stt, "stt", "STT xét nghiệm")
    name = ten_xet_nghiem.strip() if isinstance(ten_xet_nghiem, str) else ""
    if not name:
        raise AppError(
            "DU_LIEU_KHONG_HOP_LE",
            "Tên xét nghiệm không được để trống.",
            "ten_xet_nghiem",
        )
    result = _clean_optional_text(ket_qua, "ket_qua", "Kết quả xét nghiệm")
    if result is not None and ngay_gio_thuc_hien is None:
        raise AppError(
            "DU_LIEU_KHONG_HOP_LE",
            "Cần nhập ngày giờ thực hiện khi đã có kết quả.",
            "ngay_gio_thuc_hien",
        )
    if ngay_gio_thuc_hien is not None and not isinstance(ngay_gio_thuc_hien, datetime):
        raise AppError(
            "DU_LIEU_KHONG_HOP_LE",
            "Ngày giờ thực hiện không hợp lệ.",
            "ngay_gio_thuc_hien",
        )
    try:
        price = Decimal(str(don_gia_ap_dung))
    except (InvalidOperation, ValueError) as error:
        raise AppError(
            "DU_LIEU_KHONG_HOP_LE",
            "Đơn giá xét nghiệm phải là số hợp lệ.",
            "don_gia_ap_dung",
        ) from error
    if not price.is_finite() or price < 0:
        raise AppError(
            "DU_LIEU_KHONG_HOP_LE",
            "Đơn giá xét nghiệm phải là số không âm.",
            "don_gia_ap_dung",
        )

    if is_demo_mode():
        return demo_data().save_lab(
            ma_phieu, name, result, ngay_gio_thuc_hien, price, stt
        )

    connection = get_connection()
    cursor: MySQLCursorDict | None = None
    commit_attempted = False
    try:
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(Q_LOCK_PHIEU_KHAM, {"ma_phieu": ma_phieu})
        locked_visit = cursor.fetchone()
        if locked_visit is None:
            raise AppError("KHONG_TIM_THAY", "Không tìm thấy phiếu khám.")
        if locked_visit["trang_thai"] != "DANG_KHAM":
            raise AppError(
                "PHIEU_DA_HOAN_THANH",
                "Không thể thay đổi xét nghiệm của phiếu đã hoàn thành.",
            )
        if stt is None:
            cursor.execute(Q_NEXT_STT_XET_NGHIEM, {"ma_phieu": ma_phieu})
            row = cursor.fetchone()
            next_stt = int(row["stt"])
            cursor.execute(
                Q_INSERT_XET_NGHIEM,
                {
                    "ma_phieu": ma_phieu,
                    "stt": next_stt,
                    "ten_xet_nghiem": name,
                    "ket_qua": result,
                    "ngay_gio_thuc_hien": ngay_gio_thuc_hien,
                    "don_gia_ap_dung": price,
                },
            )
        else:
            cursor.execute(
                Q_LOCK_XET_NGHIEM,
                {"ma_phieu": ma_phieu, "stt": stt},
            )
            if cursor.fetchone() is None:
                raise AppError(
                    "KHONG_TIM_THAY",
                    "Không tìm thấy xét nghiệm cần cập nhật trong phiếu khám.",
                )
            cursor.execute(
                Q_UPDATE_XET_NGHIEM,
                {
                    "ma_phieu": ma_phieu,
                    "stt": stt,
                    "ten_xet_nghiem": name,
                    "ket_qua": result,
                    "ngay_gio_thuc_hien": ngay_gio_thuc_hien,
                    "don_gia_ap_dung": price,
                },
            )
            next_stt = stt
        commit_attempted = True
        connection.commit()
        return next_stt
    except AppError:
        if not commit_attempted:
            _rollback(connection)
        raise
    except mysql.connector.Error as error:
        if commit_attempted:
            raise AppError(
                "COMMIT_CHUA_XAC_DINH",
                (
                    f"Chưa xác định được xét nghiệm STT {stt or 'mới'} đã lưu hay chưa. "
                    "Hãy tải lại chi tiết phiếu khám trước khi thao tác tiếp."
                ),
            ) from error
        _rollback(connection)
        logger.exception("Could not save lab result for consultation %s", ma_phieu)
        raise app_error_from_database(error, Q_INSERT_XET_NGHIEM) from error
    except Exception as error:
        if commit_attempted:
            raise AppError(
                "COMMIT_CHUA_XAC_DINH",
                (
                    f"Chưa xác định được xét nghiệm STT {stt or 'mới'} đã lưu hay chưa. "
                    "Hãy tải lại chi tiết phiếu khám trước khi thao tác tiếp."
                ),
            ) from error
        _rollback(connection)
        raise
    finally:
        _close_transaction(cursor, connection)


def tim_phieu_dang_kham(
    ma_benh_nhan: Identifier, ma_bac_si: Identifier
) -> Identifier | None:
    _validate_id(ma_benh_nhan, "ma_benh_nhan", "Mã bệnh nhân")
    _validate_id(ma_bac_si, "ma_bac_si", "Mã bác sĩ")
    if is_demo_mode():
        return demo_data().find_in_progress_visit(ma_benh_nhan, ma_bac_si)
    row = _get_one(
        Q_FIND_IN_PROGRESS_VISIT,
        {"ma_benh_nhan": ma_benh_nhan, "ma_bac_si": ma_bac_si},
    )
    return row["ma_phieu"] if row else None


def hoan_thanh_phieu_kham(ma_phieu: Identifier, ma_bac_si: Identifier) -> None:
    _validate_id(ma_phieu, "ma_phieu", "Mã phiếu khám")
    _validate_id(ma_bac_si, "ma_bac_si", "Mã bác sĩ")
    if is_demo_mode():
        demo_data().complete_visit(ma_phieu, ma_bac_si)
        return
    connection = get_connection()
    cursor: MySQLCursorDict | None = None
    commit_attempted = False
    try:
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(Q_LOCK_PHIEU_KHAM, {"ma_phieu": ma_phieu})
        visit = cursor.fetchone()
        if visit is None:
            raise AppError("KHONG_TIM_THAY", "Không tìm thấy phiếu khám.")
        if visit["ma_bac_si"] != ma_bac_si:
            raise AppError(
                "KHONG_DU_QUYEN", "Chỉ bác sĩ phụ trách mới được chốt phiếu."
            )
        if visit["trang_thai"] != "DANG_KHAM":
            raise AppError("PHIEU_DA_HOAN_THANH", "Phiếu khám đã hoàn thành.")
        cursor.execute(Q_COMPLETE_VISIT, (ma_phieu, ma_phieu))
        if cursor.rowcount != 1:
            raise AppError(
                "CHUA_DU_DIEU_KIEN_HOAN_THANH",
                "Cần có chẩn đoán và hoàn tất toàn bộ kết quả xét nghiệm trước khi chốt phiếu.",
            )
        commit_attempted = True
        connection.commit()
    except AppError:
        if not commit_attempted:
            _rollback(connection)
        raise
    except mysql.connector.Error as error:
        if commit_attempted:
            raise AppError(
                "COMMIT_CHUA_XAC_DINH",
                "Chưa xác định được kết quả chốt phiếu. Hãy tải lại phiếu khám.",
            ) from error
        _rollback(connection)
        logger.exception("Could not complete consultation %s", ma_phieu)
        raise app_error_from_database(error, Q_COMPLETE_VISIT) from error
    except Exception:
        if not commit_attempted:
            _rollback(connection)
        raise
    finally:
        _close_transaction(cursor, connection)


def xoa_phieu_dang_kham(ma_phieu: Identifier, ma_bac_si: Identifier) -> None:
    _validate_id(ma_phieu, "ma_phieu", "Mã phiếu khám")
    _validate_id(ma_bac_si, "ma_bac_si", "Mã bác sĩ")
    if is_demo_mode():
        demo_data().delete_in_progress_visit(ma_phieu, ma_bac_si)
        return

    connection = get_connection()
    cursor: MySQLCursorDict | None = None
    commit_attempted = False
    try:
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(Q_LOCK_PHIEU_KHAM, {"ma_phieu": ma_phieu})
        visit = cursor.fetchone()
        if visit is None:
            raise AppError("KHONG_TIM_THAY", "Không tìm thấy phiếu khám.")
        if visit["ma_bac_si"] != ma_bac_si:
            raise AppError("KHONG_DU_QUYEN", "Chỉ bác sĩ phụ trách mới được xóa phiếu.")
        if visit["trang_thai"] != "DANG_KHAM":
            raise AppError("PHIEU_DA_HOAN_THANH", "Không thể xóa phiếu đã hoàn thành.")

        cursor.execute(
            """
            SELECT MaDonThuoc
            FROM DonThuoc
            WHERE MaPhieuKhamBenh = %s
            FOR UPDATE
            """,
            (ma_phieu,),
        )
        order_count = len(cursor.fetchall())
        cursor.execute(
            """
            SELECT ct.MaThuoc
            FROM ChiTietDonThuoc ct
            JOIN DonThuoc d ON ct.MaDonThuoc = d.MaDonThuoc
            WHERE d.MaPhieuKhamBenh = %s
            FOR UPDATE
            """,
            (ma_phieu,),
        )
        detail_count = len(cursor.fetchall())

        cursor.execute(
            """
            UPDATE Thuoc t
            JOIN ChiTietDonThuoc ct ON t.MaThuoc = ct.MaThuoc
            JOIN DonThuoc d ON ct.MaDonThuoc = d.MaDonThuoc
            JOIN PhieuKhamBenh p ON d.MaPhieuKhamBenh = p.MaPhieuKhamBenh
            SET t.SoLuongCoSan = t.SoLuongCoSan + ct.SoLuongKe
            WHERE p.MaPhieuKhamBenh = %s
              AND p.TrangThaiPhieuKham = 'DANG_KHAM'
            """,
            (ma_phieu,),
        )
        if cursor.rowcount != detail_count:
            raise AppError(
                "XUNG_DOT_DU_LIEU",
                "Không thể hoàn đủ tồn kho của phiếu. Hãy tải lại trước khi xóa.",
            )

        cursor.execute(
            """
            DELETE ct FROM ChiTietDonThuoc ct
            JOIN DonThuoc d ON ct.MaDonThuoc = d.MaDonThuoc
            JOIN PhieuKhamBenh p ON d.MaPhieuKhamBenh = p.MaPhieuKhamBenh
            WHERE p.MaPhieuKhamBenh = %s
              AND p.TrangThaiPhieuKham = 'DANG_KHAM'
            """,
            (ma_phieu,),
        )
        if cursor.rowcount != detail_count:
            raise AppError(
                "XUNG_DOT_DU_LIEU",
                "Không xóa đủ chi tiết đơn thuốc. Hãy tải lại trước khi xóa.",
            )

        cursor.execute(
            """
            DELETE d FROM DonThuoc d
            JOIN PhieuKhamBenh p ON d.MaPhieuKhamBenh = p.MaPhieuKhamBenh
            WHERE p.MaPhieuKhamBenh = %s
              AND p.TrangThaiPhieuKham = 'DANG_KHAM'
            """,
            (ma_phieu,),
        )
        if cursor.rowcount != order_count:
            raise AppError(
                "XUNG_DOT_DU_LIEU",
                "Không xóa đủ đơn thuốc. Hãy tải lại trước khi xóa.",
            )

        cursor.execute(
            """
            DELETE x FROM XetNghiem x
            JOIN PhieuKhamBenh p ON x.MaPhieuKhamBenh = p.MaPhieuKhamBenh
            WHERE p.MaPhieuKhamBenh = %s
              AND p.TrangThaiPhieuKham = 'DANG_KHAM'
            """,
            (ma_phieu,),
        )
        cursor.execute(
            """
            DELETE FROM PhieuKhamBenh
            WHERE MaPhieuKhamBenh = %s
              AND TrangThaiPhieuKham = 'DANG_KHAM'
            """,
            (ma_phieu,),
        )
        if cursor.rowcount != 1:
            raise AppError(
                "XUNG_DOT_DU_LIEU",
                "Phiếu khám vừa thay đổi. Hãy tải lại trước khi xóa.",
            )
        commit_attempted = True
        connection.commit()
    except AppError:
        if not commit_attempted:
            _rollback(connection)
        raise
    except mysql.connector.Error as error:
        if commit_attempted:
            raise AppError(
                "COMMIT_CHUA_XAC_DINH",
                "Chưa xác định được kết quả xóa phiếu. Hãy tải lại hồ sơ bệnh án.",
            ) from error
        _rollback(connection)
        logger.exception("Could not delete in-progress consultation %s", ma_phieu)
        raise app_error_from_database(error) from error
    except Exception:
        if not commit_attempted:
            _rollback(connection)
        raise
    finally:
        _close_transaction(cursor, connection)


def lay_ho_so_benh_an(ma_benh_nhan: Identifier) -> dict[str, Any] | None:
    require_identifier(ma_benh_nhan, "ma_benh_nhan", "Mã bệnh nhân")
    if is_demo_mode():
        tien_su = demo_data().medical_history(ma_benh_nhan)
        return (
            {"ngay_lap": date.today(), "tien_su_benh": tien_su}
            if tien_su is not None
            else None
        )

    return _get_one(Q_HO_SO_BENH_AN, {"ma_benh_nhan": ma_benh_nhan})
