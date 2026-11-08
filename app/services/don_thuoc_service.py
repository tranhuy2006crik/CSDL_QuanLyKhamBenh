import logging
from datetime import date, datetime
from typing import Any

import mysql.connector
from mysql.connector.connection import MySQLConnection
from mysql.connector.cursor import MySQLCursorDict

from app.contracts import DonThuocDTO, DongThuocInput, Identifier
from app.demo_data import demo_data, is_demo_mode
from app.db import get_connection
from app.errors import (
    AppError,
    app_error_from_database,
    require_identifier,
    require_positive_int,
)
from app.services.tra_cuu_service import lay_don_thuoc


logger = logging.getLogger(__name__)
MAX_SQL_INT = 2_147_483_647
MAX_SQL_UNSIGNED_INT = 4_294_967_295

Q_LOCK_PHIEU = """
SELECT NgayGioKham AS ngay_gio_kham,
       TrangThaiPhieuKham AS trang_thai
FROM PhieuKhamBenh
WHERE MaPhieuKhamBenh = %(ma_phieu)s
FOR UPDATE
"""
Q_LOCK_DON_THEO_PHIEU = """
SELECT MaDonThuoc AS ma_don, MaPhieuKhamBenh AS ma_phieu,
       NgayLapDonThuoc AS ngay_lap, LoiDanChung AS loi_dan
FROM DonThuoc
WHERE MaPhieuKhamBenh = %(ma_phieu)s
FOR UPDATE
"""
Q_LOCK_DON_THEO_MA = """
SELECT MaDonThuoc AS ma_don, MaPhieuKhamBenh AS ma_phieu,
       NgayLapDonThuoc AS ngay_lap, LoiDanChung AS loi_dan
FROM DonThuoc
WHERE MaDonThuoc = %(ma_don)s
FOR UPDATE
"""
Q_LOCK_CHI_TIET = """
SELECT MaThuoc AS ma_thuoc, SoLuongKe AS so_luong_ke,
       CachDung AS cach_dung, DonGiaApDung AS don_gia_ap_dung
FROM ChiTietDonThuoc
WHERE MaDonThuoc = %(ma_don)s
ORDER BY MaThuoc
FOR UPDATE
"""
Q_LOCK_THUOC = """
SELECT MaThuoc AS ma_thuoc, TenThuoc AS ten_thuoc,
       DonViTinh AS don_vi_tinh, DonGia AS don_gia,
       SoLuongCoSan AS so_luong_co_san
FROM Thuoc
WHERE MaThuoc = %(ma_thuoc)s
FOR UPDATE
"""
Q_INSERT_DON = """
INSERT INTO DonThuoc
    (MaDonThuoc, MaPhieuKhamBenh, NgayLapDonThuoc, LoiDanChung)
SELECT %(ma_don)s, %(ma_phieu)s, CURRENT_DATE(), %(loi_dan)s
FROM DUAL
WHERE (
    SELECT TrangThaiPhieuKham
    FROM PhieuKhamBenh
    WHERE MaPhieuKhamBenh = %(ma_phieu)s
) = 'DANG_KHAM'
"""
Q_UPDATE_DON = """
UPDATE DonThuoc
SET LoiDanChung = %(loi_dan)s
WHERE MaDonThuoc = %(ma_don)s
  AND MaPhieuKhamBenh = %(ma_phieu)s
"""
Q_DELETE_CHI_TIET = "DELETE FROM ChiTietDonThuoc WHERE MaDonThuoc = %(ma_don)s"
Q_INSERT_CHI_TIET = """
INSERT INTO ChiTietDonThuoc
    (MaDonThuoc, MaThuoc, SoLuongKe, CachDung, DonGiaApDung)
SELECT %(ma_don)s, %(ma_thuoc)s, %(so_luong_ke)s, %(cach_dung)s, DonGia
FROM Thuoc
WHERE MaThuoc = %(ma_thuoc)s
"""
Q_INSERT_CHI_TIET_HISTORICAL_PRICE = """
INSERT INTO ChiTietDonThuoc
    (MaDonThuoc, MaThuoc, SoLuongKe, CachDung, DonGiaApDung)
VALUES
    (%(ma_don)s, %(ma_thuoc)s, %(so_luong_ke)s, %(cach_dung)s, %(don_gia)s)
"""
Q_COUNT_CHI_TIET = """
SELECT COUNT(*) AS so_dong
FROM ChiTietDonThuoc
WHERE MaDonThuoc = %(ma_don)s
"""
Q_TRU_TON = """
UPDATE Thuoc
SET SoLuongCoSan = SoLuongCoSan - %(so_luong)s
WHERE MaThuoc = %(ma_thuoc)s
  AND SoLuongCoSan >= %(so_luong)s
"""
Q_HOAN_TON = """
UPDATE Thuoc
SET SoLuongCoSan = SoLuongCoSan + %(so_luong)s
WHERE MaThuoc = %(ma_thuoc)s
  AND SoLuongCoSan <= %(ton_toi_da)s - %(so_luong)s
"""
Q_DELETE_DON = """
DELETE FROM DonThuoc
WHERE MaDonThuoc = %(ma_don)s
  AND MaPhieuKhamBenh = %(ma_phieu)s
"""


def _validate_draft(
    ma_phieu: Identifier,
    ma_don: Identifier,
    ngay_lap: date,
    loi_dan: str | None,
    ds_thuoc: list[DongThuocInput],
) -> tuple[str | None, list[DongThuocInput]]:
    require_identifier(ma_phieu, "ma_phieu", "Mã phiếu khám")
    require_identifier(ma_don, "ma_don", "Mã đơn thuốc")
    if isinstance(ngay_lap, datetime) or not isinstance(ngay_lap, date):
        raise AppError(
            "DU_LIEU_KHONG_HOP_LE",
            "Ngày lập đơn không hợp lệ.",
            "ngay_lap",
        )
    if loi_dan is not None and not isinstance(loi_dan, str):
        raise AppError(
            "DU_LIEU_KHONG_HOP_LE",
            "Lời dặn phải là văn bản hoặc để trống.",
            "loi_dan",
        )
    cleaned_loi_dan = loi_dan.strip() if loi_dan is not None else None
    if not cleaned_loi_dan:
        cleaned_loi_dan = None

    if not isinstance(ds_thuoc, list) or not ds_thuoc:
        raise AppError(
            "DU_LIEU_KHONG_HOP_LE",
            "Đơn thuốc phải có ít nhất một dòng thuốc.",
            "ds_thuoc",
        )

    cleaned_items: list[DongThuocInput] = []
    seen_medicines: set[Identifier] = set()
    for index, item in enumerate(ds_thuoc):
        field = f"ds_thuoc[{index}]"
        if not isinstance(item, dict):
            raise AppError(
                "DU_LIEU_KHONG_HOP_LE",
                "Dòng thuốc không hợp lệ.",
                field,
            )
        ma_thuoc = item.get("ma_thuoc")
        so_luong = item.get("so_luong_ke")
        cach_dung = item.get("cach_dung")
        require_identifier(ma_thuoc, f"{field}.ma_thuoc", "Mã thuốc")
        require_positive_int(so_luong, f"{field}.so_luong_ke", "Số lượng kê")
        if so_luong > MAX_SQL_INT:
            raise AppError(
                "DU_LIEU_KHONG_HOP_LE",
                "Số lượng kê vượt phạm vi dữ liệu.",
                field,
            )
        if not isinstance(cach_dung, str) or not cach_dung.strip():
            raise AppError(
                "DU_LIEU_KHONG_HOP_LE",
                "Cách dùng không được để trống.",
                f"{field}.cach_dung",
            )
        if ma_thuoc in seen_medicines:
            raise AppError(
                "DU_LIEU_KHONG_HOP_LE",
                f"Thuốc mã {ma_thuoc} chỉ được xuất hiện một lần trong đơn.",
                "ds_thuoc",
            )
        seen_medicines.add(ma_thuoc)
        cleaned_items.append(
            {
                "ma_thuoc": ma_thuoc,
                "so_luong_ke": so_luong,
                "cach_dung": cach_dung.strip(),
            }
        )
    return cleaned_loi_dan, cleaned_items


def _fetchone(
    cursor: MySQLCursorDict, sql: str, params: dict[str, Any]
) -> dict[str, Any] | None:
    cursor.execute(sql, params)
    return cursor.fetchone()


def _fetchall(
    cursor: MySQLCursorDict, sql: str, params: dict[str, Any]
) -> list[dict[str, Any]]:
    cursor.execute(sql, params)
    return cursor.fetchall()


def _lock_medicines(
    cursor: MySQLCursorDict, medicine_ids: set[Identifier]
) -> dict[Identifier, dict[str, Any]]:
    medicines: dict[Identifier, dict[str, Any]] = {}
    for medicine_id in sorted(medicine_ids, key=str):
        medicine = _fetchone(cursor, Q_LOCK_THUOC, {"ma_thuoc": medicine_id})
        if medicine is None:
            raise AppError(
                "DU_LIEU_KHONG_HOP_LE",
                f"Không tìm thấy thuốc mã {medicine_id}. Hãy tải lại danh mục.",
                "ds_thuoc",
            )
        medicines[medicine_id] = medicine
    return medicines


def _rollback(connection: MySQLConnection) -> None:
    try:
        connection.rollback()
    except mysql.connector.Error:
        logger.exception("Could not roll back prescription transaction")


def _close_resources(
    cursor: MySQLCursorDict | None, connection: MySQLConnection
) -> None:
    if cursor is not None:
        try:
            cursor.close()
        except mysql.connector.Error:
            logger.exception("Could not close prescription cursor")
    try:
        connection.close()
    except mysql.connector.Error:
        logger.exception("Could not close prescription connection")


def luu_don_thuoc(
    ma_phieu: Identifier,
    ma_don: Identifier,
    ngay_lap: date,
    loi_dan: str | None,
    ds_thuoc: list[DongThuocInput],
    tao_moi: bool,
) -> DonThuocDTO:
    if not isinstance(tao_moi, bool):
        raise AppError(
            "DU_LIEU_KHONG_HOP_LE", "Chế độ lưu đơn không hợp lệ.", "tao_moi"
        )
    cleaned_loi_dan, cleaned_items = _validate_draft(
        ma_phieu, ma_don, ngay_lap, loi_dan, ds_thuoc
    )

    if is_demo_mode():
        return demo_data().save_order(
            ma_phieu,
            ma_don,
            ngay_lap,
            cleaned_loi_dan,
            cleaned_items,
            tao_moi,
        )

    connection = get_connection()
    cursor: MySQLCursorDict | None = None
    commit_attempted = False
    last_statement: str | None = None
    try:
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)

        appointment = _fetchone(cursor, Q_LOCK_PHIEU, {"ma_phieu": ma_phieu})
        if appointment is None:
            raise AppError("KHONG_TIM_THAY", "Không tìm thấy phiếu khám.")
        if appointment["trang_thai"] != "DANG_KHAM":
            raise AppError(
                "PHIEU_DA_HOAN_THANH",
                "Không thể thay đổi đơn thuốc của phiếu đã hoàn thành.",
            )
        ngay_gio_kham = appointment["ngay_gio_kham"]
        if ngay_lap < ngay_gio_kham.date():
            raise AppError(
                "DU_LIEU_KHONG_HOP_LE",
                "Ngày lập đơn không được trước ngày khám.",
                "ngay_lap",
            )

        existing_rows = _fetchall(
            cursor, Q_LOCK_DON_THEO_PHIEU, {"ma_phieu": ma_phieu}
        )
        if tao_moi and existing_rows:
            raise AppError(
                "DA_CO_DON_THUOC",
                "Phiếu khám này đã có đơn thuốc.",
                "ma_phieu",
            )
        if not tao_moi and not existing_rows:
            raise AppError("KHONG_TIM_THAY", "Không tìm thấy đơn thuốc của phiếu.")

        existing = existing_rows[0] if existing_rows else None
        if existing is not None and existing["ma_don"] != ma_don:
            raise AppError(
                "KHONG_TIM_THAY",
                "Mã đơn thuốc không thuộc phiếu khám đang chọn.",
                "ma_don",
            )
        if tao_moi:
            duplicate = _fetchone(
                cursor, Q_LOCK_DON_THEO_MA, {"ma_don": ma_don}
            )
            if duplicate is not None:
                raise AppError(
                    "TRUNG_MA", f"Mã đơn thuốc {ma_don} đã được sử dụng.", "ma_don"
                )

        old_lines = (
            _fetchall(cursor, Q_LOCK_CHI_TIET, {"ma_don": ma_don})
            if existing is not None
            else []
        )
        old_by_medicine = {row["ma_thuoc"]: row for row in old_lines}
        new_by_medicine = {row["ma_thuoc"]: row for row in cleaned_items}
        medicine_ids = set(old_by_medicine) | set(new_by_medicine)
        medicines = _lock_medicines(cursor, medicine_ids)

        deltas: dict[Identifier, int] = {}
        for medicine_id in sorted(medicine_ids, key=str):
            old_quantity = (
                int(old_by_medicine[medicine_id]["so_luong_ke"])
                if medicine_id in old_by_medicine
                else 0
            )
            new_quantity = (
                int(new_by_medicine[medicine_id]["so_luong_ke"])
                if medicine_id in new_by_medicine
                else 0
            )
            delta = new_quantity - old_quantity
            medicine = medicines[medicine_id]
            stock = int(medicine["so_luong_co_san"])
            if delta > stock:
                raise AppError(
                    "KHONG_DU_TON",
                    (
                        f"Thuốc {medicine['ten_thuoc']} (mã {medicine_id}): "
                        f"cần trừ thêm {delta}, tồn hiện tại {stock}."
                    ),
                    "ds_thuoc",
                )
            if delta < 0 and stock - delta > MAX_SQL_INT:
                raise AppError(
                    "DU_LIEU_KHONG_HOP_LE",
                    f"Hoàn tồn thuốc mã {medicine_id} vượt phạm vi INT.",
                    "ds_thuoc",
                )
            deltas[medicine_id] = delta

        header_params = {
            "ma_don": ma_don,
            "ma_phieu": ma_phieu,
            "loi_dan": cleaned_loi_dan,
        }
        if existing is None:
            last_statement = Q_INSERT_DON
            cursor.execute(Q_INSERT_DON, header_params)
            if cursor.rowcount != 1:
                raise AppError(
                    "XUNG_DOT_DU_LIEU",
                    "Không thể tạo đầu đơn thuốc cho phiếu đang khám.",
                )
        else:
            cursor.execute(Q_UPDATE_DON, header_params)
            cursor.execute(Q_DELETE_CHI_TIET, {"ma_don": ma_don})
            if cursor.rowcount != len(old_lines):
                raise AppError(
                    "XUNG_DOT_DU_LIEU",
                    "Chi tiết đơn thuốc vừa thay đổi. Hãy tải lại trước khi lưu.",
                )

        ordered_medicine_ids = [item["ma_thuoc"] for item in cleaned_items]
        ordered_medicine_ids.extend(
            sorted(medicine_ids - set(new_by_medicine), key=str)
        )
        for medicine_id in ordered_medicine_ids:
            delta = deltas[medicine_id]
            if delta > 0:
                last_statement = Q_TRU_TON
                cursor.execute(
                    Q_TRU_TON,
                    {"ma_thuoc": medicine_id, "so_luong": delta},
                )
                if cursor.rowcount != 1:
                    raise AppError(
                        "KHONG_DU_TON",
                        f"Tồn thuốc mã {medicine_id} vừa thay đổi. Hãy tải lại.",
                        "ds_thuoc",
                    )
            elif delta < 0:
                last_statement = Q_HOAN_TON
                cursor.execute(
                    Q_HOAN_TON,
                    {
                        "ma_thuoc": medicine_id,
                        "so_luong": -delta,
                        "ton_toi_da": MAX_SQL_INT,
                    },
                )
                if cursor.rowcount != 1:
                    raise AppError(
                        "DU_LIEU_KHONG_HOP_LE",
                        f"Không thể hoàn tồn thuốc mã {medicine_id}.",
                        "ds_thuoc",
                    )

            item = new_by_medicine.get(medicine_id)
            if item is None:
                continue
            old_line = old_by_medicine.get(medicine_id)
            statement = (
                Q_INSERT_CHI_TIET_HISTORICAL_PRICE
                if old_line is not None
                else Q_INSERT_CHI_TIET
            )
            params: dict[str, Any] = {
                "ma_don": ma_don,
                "ma_thuoc": medicine_id,
                "so_luong_ke": item["so_luong_ke"],
                "cach_dung": item["cach_dung"],
            }
            if old_line is not None:
                params["don_gia"] = old_line["don_gia_ap_dung"]
            last_statement = statement
            cursor.execute(
                statement,
                params,
            )
            if cursor.rowcount != 1:
                raise AppError(
                    "XUNG_DOT_DU_LIEU",
                    f"Không lưu được thuốc mã {medicine_id}. Hãy tải lại đơn.",
                )

        cursor.execute(Q_COUNT_CHI_TIET, {"ma_don": ma_don})
        count_row = cursor.fetchone()
        if count_row is None or int(count_row["so_dong"]) != len(cleaned_items):
            raise AppError(
                "XUNG_DOT_DU_LIEU",
                "Đơn thuốc chưa có đầy đủ chi tiết. Hãy tải lại trước khi thao tác.",
            )

        commit_attempted = True
        connection.commit()
    except AppError:
        if not commit_attempted:
            _rollback(connection)
        raise
    except mysql.connector.Error as error:
        if commit_attempted:
            logger.exception("Commit outcome is unknown for prescription %s", ma_don)
            raise AppError(
                "COMMIT_CHUA_XAC_DINH",
                (
                    f"Chưa xác định được kết quả lưu đơn {ma_don}. "
                    "Hãy tải đơn theo mã này trước khi thao tác tiếp."
                ),
            ) from error
        _rollback(connection)
        logger.exception("MySQL error while saving prescription %s", ma_don)
        raise app_error_from_database(error, last_statement) from error
    except Exception as error:
        if commit_attempted:
            logger.exception("Commit outcome is unknown for prescription %s", ma_don)
            raise AppError(
                "COMMIT_CHUA_XAC_DINH",
                (
                    f"Chưa xác định được kết quả lưu đơn {ma_don}. "
                    "Hãy tải đơn theo mã này trước khi thao tác tiếp."
                ),
            ) from error
        _rollback(connection)
        logger.exception("Unexpected error while saving prescription %s", ma_don)
        raise AppError(
            "LOI_HE_THONG", "Không thể lưu đơn thuốc. Hãy thử tải lại dữ liệu."
        ) from error
    finally:
        _close_resources(cursor, connection)

    try:
        saved = lay_don_thuoc(ma_phieu)
    except AppError as error:
        raise AppError(
            "DA_LUU_CAN_TAI_LAI",
            (
                f"Đơn thuốc {ma_don} đã lưu, nhưng chưa tải lại được dữ liệu. "
                "Không lưu lại lần nữa; hãy tải đơn theo mã phiếu."
            ),
        ) from error
    if saved is None:
        raise AppError(
            "DA_LUU_CAN_TAI_LAI",
            f"Đơn thuốc {ma_don} đã lưu nhưng không đọc lại được.",
        )
    return saved


def xoa_don_thuoc(ma_phieu: Identifier, ma_don: Identifier) -> None:
    require_identifier(ma_phieu, "ma_phieu", "Mã phiếu khám")
    require_identifier(ma_don, "ma_don", "Mã đơn thuốc")
    if is_demo_mode():
        demo_data().delete_order(ma_phieu, ma_don)
        return
    connection = get_connection()
    cursor: MySQLCursorDict | None = None
    commit_attempted = False
    try:
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)

        appointment = _fetchone(cursor, Q_LOCK_PHIEU, {"ma_phieu": ma_phieu})
        if appointment is None:
            raise AppError("KHONG_TIM_THAY", "Không tìm thấy phiếu khám.")
        if appointment["trang_thai"] != "DANG_KHAM":
            raise AppError(
                "PHIEU_DA_HOAN_THANH",
                "Không thể xóa đơn thuốc của phiếu đã hoàn thành.",
            )

        header = _fetchone(
            cursor, Q_LOCK_DON_THEO_PHIEU, {"ma_phieu": ma_phieu}
        )
        if header is None or header["ma_don"] != ma_don:
            raise AppError("KHONG_TIM_THAY", "Không tìm thấy đơn thuốc của phiếu.")

        old_lines = _fetchall(cursor, Q_LOCK_CHI_TIET, {"ma_don": ma_don})
        medicine_ids = {row["ma_thuoc"] for row in old_lines}
        medicines = _lock_medicines(cursor, medicine_ids)
        for line in old_lines:
            medicine_id = line["ma_thuoc"]
            quantity = int(line["so_luong_ke"])
            stock = int(medicines[medicine_id]["so_luong_co_san"])
            if stock + quantity > MAX_SQL_INT:
                raise AppError(
                    "DU_LIEU_KHONG_HOP_LE",
                    f"Hoàn tồn thuốc mã {medicine_id} vượt phạm vi INT.",
                )

        for medicine_id in sorted(medicine_ids, key=str):
            quantity = sum(
                int(line["so_luong_ke"])
                for line in old_lines
                if line["ma_thuoc"] == medicine_id
            )
            cursor.execute(
                Q_HOAN_TON,
                {
                    "ma_thuoc": medicine_id,
                    "so_luong": quantity,
                    "ton_toi_da": MAX_SQL_INT,
                },
            )
            if cursor.rowcount != 1:
                raise AppError(
                    "DU_LIEU_KHONG_HOP_LE",
                    f"Không thể hoàn tồn thuốc mã {medicine_id}.",
                )

        cursor.execute(Q_DELETE_CHI_TIET, {"ma_don": ma_don})
        if cursor.rowcount != len(old_lines):
            raise AppError(
                "XUNG_DOT_DU_LIEU",
                "Chi tiết đơn thuốc vừa thay đổi. Hãy tải lại trước khi xóa.",
            )
        cursor.execute(Q_DELETE_DON, {"ma_don": ma_don, "ma_phieu": ma_phieu})
        if cursor.rowcount != 1:
            raise AppError(
                "XUNG_DOT_DU_LIEU",
                "Đơn thuốc vừa thay đổi. Hãy tải lại trước khi xóa.",
            )

        commit_attempted = True
        connection.commit()
    except AppError:
        if not commit_attempted:
            _rollback(connection)
        raise
    except mysql.connector.Error as error:
        if commit_attempted:
            logger.exception("Commit outcome is unknown while deleting %s", ma_don)
            raise AppError(
                "COMMIT_CHUA_XAC_DINH",
                (
                    f"Chưa xác định được kết quả xóa đơn {ma_don}. "
                    "Hãy tải lại đơn và tồn kho trước khi thao tác tiếp."
                ),
            ) from error
        _rollback(connection)
        logger.exception("MySQL error while deleting prescription %s", ma_don)
        raise app_error_from_database(error) from error
    except Exception as error:
        if commit_attempted:
            logger.exception("Commit outcome is unknown while deleting %s", ma_don)
            raise AppError(
                "COMMIT_CHUA_XAC_DINH",
                (
                    f"Chưa xác định được kết quả xóa đơn {ma_don}. "
                    "Hãy tải lại đơn và tồn kho trước khi thao tác tiếp."
                ),
            ) from error
        _rollback(connection)
        logger.exception("Unexpected error while deleting prescription %s", ma_don)
        raise AppError(
            "LOI_HE_THONG", "Không thể xóa đơn thuốc. Hãy tải lại dữ liệu."
        ) from error
    finally:
        _close_resources(cursor, connection)
