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
    KhoaDTO,
    LichLamViecDTO,
    LichSuKhamRow,
)
from app.demo_data import demo_data, is_demo_mode
from app.db import get_connection
from app.errors import AppError, app_error_from_database, require_positive_int
from app.read_queries import (
    Q_BAC_SI,
    Q_BAC_SI_THEO_MA,
    Q_BAO_CAO_BAC_SI,
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
    Q_TIM_BENH_NHAN,
    Q_UPDATE_NOI_DUNG_KHAM,
    Q_UPDATE_XET_NGHIEM,
)


logger = logging.getLogger(__name__)
MAX_SQL_UNSIGNED_INT = 4_294_967_295


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


def lay_danh_sach_bac_si(ma_khoa: int | None = None) -> list[BacSiDTO]:
    if ma_khoa is not None:
        require_positive_int(ma_khoa, "ma_khoa", "Mã khoa")
    if is_demo_mode():
        return cast(list[BacSiDTO], demo_data().list_doctors(ma_khoa))
    return cast(list[BacSiDTO], _read(Q_BAC_SI, {"ma_khoa": ma_khoa}))


def lay_bac_si(ma_bac_si: int) -> BacSiChiTietDTO | None:
    require_positive_int(ma_bac_si, "ma_bac_si", "Mã bác sĩ")
    if is_demo_mode():
        return cast(BacSiChiTietDTO | None, demo_data().get_doctor(ma_bac_si))
    row = _get_one(Q_BAC_SI_THEO_MA, {"ma_bac_si": ma_bac_si})
    return cast(BacSiChiTietDTO | None, row)


def lay_benh_nhan(ma_benh_nhan: int) -> BenhNhanDTO | None:
    require_positive_int(ma_benh_nhan, "ma_benh_nhan", "Mã bệnh nhân")
    if is_demo_mode():
        return cast(BenhNhanDTO | None, demo_data().get_patient(ma_benh_nhan))
    row = _get_one(Q_BENH_NHAN_THEO_MA, {"ma_benh_nhan": ma_benh_nhan})
    return cast(BenhNhanDTO | None, row)


def tim_kiem_benh_nhan(
    tu_khoa: str = "",
    ma_khoa: int | None = None,
    ma_bac_si: int | None = None,
) -> list[BenhNhanDTO]:
    if ma_khoa is not None:
        require_positive_int(ma_khoa, "ma_khoa", "Mã khoa")
    if ma_bac_si is not None:
        require_positive_int(ma_bac_si, "ma_bac_si", "Mã bác sĩ")
    keyword = tu_khoa.strip()
    params = {
        "tu_khoa": keyword,
        "mau_tim": f"%{keyword}%",
        "ma_khoa": ma_khoa,
        "ma_bac_si": ma_bac_si,
    }
    if is_demo_mode():
        return cast(
            list[BenhNhanDTO],
            demo_data().search_patients(keyword, ma_khoa, ma_bac_si),
        )
    return cast(list[BenhNhanDTO], _read(Q_TIM_BENH_NHAN, params))


def lay_lich_su_benh_nhan(ma_benh_nhan: int) -> list[LichSuKhamRow]:
    require_positive_int(ma_benh_nhan, "ma_benh_nhan", "Mã bệnh nhân")
    if is_demo_mode():
        return cast(list[LichSuKhamRow], demo_data().history(ma_benh_nhan))
    return cast(
        list[LichSuKhamRow],
        _read(Q_LICH_SU_BENH_NHAN, {"ma_benh_nhan": ma_benh_nhan}),
    )


def lay_tien_su_benh(ma_benh_nhan: int) -> str | None:
    require_positive_int(ma_benh_nhan, "ma_benh_nhan", "Mã bệnh nhân")
    if is_demo_mode():
        return demo_data().medical_history(ma_benh_nhan)
    row = _get_one(Q_HO_SO_BENH_AN, {"ma_benh_nhan": ma_benh_nhan})
    if row is None:
        return None
    return row["tien_su_benh"]


def _weekday_order(value: str) -> tuple[int, str]:
    normalized = value.strip().casefold().replace("đ", "d")
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


def lay_lich_lam_viec(ma_khoa: int) -> list[LichLamViecDTO]:
    require_positive_int(ma_khoa, "ma_khoa", "Mã khoa")
    if is_demo_mode():
        rows = cast(
            list[LichLamViecDTO], demo_data().weekly_schedule(ma_khoa)
        )
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
    ma_khoa: int | None = None,
    tu_khoa: str = "",
    hien_bac_si_rong: bool = True,
) -> list[BaoCaoBacSiRow]:
    if isinstance(thang, bool) or not isinstance(thang, int) or not 1 <= thang <= 12:
        raise AppError("DU_LIEU_KHONG_HOP_LE", "Tháng phải từ 1 đến 12.", "thang")
    if isinstance(nam, bool) or not isinstance(nam, int) or not 1 <= nam <= 9999:
        raise AppError("DU_LIEU_KHONG_HOP_LE", "Năm không hợp lệ.", "nam")
    if ma_khoa is not None:
        require_positive_int(ma_khoa, "ma_khoa", "Mã khoa")
    if not isinstance(hien_bac_si_rong, bool):
        raise AppError(
            "DU_LIEU_KHONG_HOP_LE",
            "Tùy chọn hiển thị bác sĩ không có lượt khám không hợp lệ.",
        )

    start = date(nam, thang, 1)
    end = date(nam + (thang == 12), 1 if thang == 12 else thang + 1, 1)
    keyword = tu_khoa.strip()
    if is_demo_mode():
        return cast(
            list[BaoCaoBacSiRow],
            demo_data().report(start, end, ma_khoa, keyword, hien_bac_si_rong),
        )
    return cast(
        list[BaoCaoBacSiRow],
        _read(
            Q_BAO_CAO_BAC_SI,
            {
                "tu_ngay": start,
                "den_ngay": end,
                "ma_khoa": ma_khoa,
                "tu_khoa": keyword,
                "mau_tim": f"%{keyword}%",
                "hien_bac_si_rong": int(hien_bac_si_rong),
            },
        ),
    )


def _validate_id(value: int, field: str, label: str) -> None:
    require_positive_int(value, field, label)
    if value > MAX_SQL_UNSIGNED_INT:
        raise AppError(
            "DU_LIEU_KHONG_HOP_LE",
            f"{label} vượt phạm vi INT UNSIGNED.",
            field,
        )


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
    ma_phieu: int,
    ma_benh_nhan: int,
    ma_bac_si: int,
    trieu_chung: str | None,
    chan_doan: str | None,
) -> None:
    _validate_id(ma_phieu, "ma_phieu", "Mã phiếu khám")
    _validate_id(ma_benh_nhan, "ma_benh_nhan", "Mã bệnh nhân")
    _validate_id(ma_bac_si, "ma_bac_si", "Mã bác sĩ")
    cleaned_symptoms = _clean_optional_text(
        trieu_chung, "trieu_chung", "Triệu chứng"
    )
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
    ma_phieu: int,
    trieu_chung: str | None,
    chan_doan: str | None,
) -> None:
    _validate_id(ma_phieu, "ma_phieu", "Mã phiếu khám")
    params = {
        "ma_phieu": ma_phieu,
        "trieu_chung": _clean_optional_text(
            trieu_chung, "trieu_chung", "Triệu chứng"
        ),
        "chan_doan": _clean_optional_text(chan_doan, "chan_doan", "Chẩn đoán"),
    }
    if is_demo_mode():
        demo_data().update_visit(
            ma_phieu, params["trieu_chung"], params["chan_doan"]
        )
        return
    connection = get_connection()
    cursor: MySQLCursorDict | None = None
    commit_attempted = False
    try:
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(Q_LOCK_PHIEU_KHAM, {"ma_phieu": ma_phieu})
        if cursor.fetchone() is None:
            raise AppError("KHONG_TIM_THAY", "Không tìm thấy phiếu khám.")
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
    ma_phieu: int,
    ten_xet_nghiem: str,
    ket_qua: str | None,
    ngay_gio_thuc_hien: datetime | None,
    don_gia_ap_dung: Decimal | str | int,
    stt: int | None = None,
) -> int:
    _validate_id(ma_phieu, "ma_phieu", "Mã phiếu khám")
    if stt is not None:
        _validate_id(stt, "stt", "STT xét nghiệm")
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
    if ngay_gio_thuc_hien is not None and not isinstance(
        ngay_gio_thuc_hien, datetime
    ):
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
        if cursor.fetchone() is None:
            raise AppError("KHONG_TIM_THAY", "Không tìm thấy phiếu khám.")
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
