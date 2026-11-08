from datetime import datetime
from decimal import Decimal
from app.db import get_connection
from app.errors import AppError, app_error_from_database


def luu_xet_nghiem(
    ma_phieu: str,
    ten_xet_nghiem: str,
    ket_qua: str | None,
    ngay_gio_thuc_hien: datetime | None,
    don_gia_ap_dung: Decimal,
    stt: int | None = None,
) -> int:
    ma_phieu = str(ma_phieu).strip()

    if not str(ten_xet_nghiem).strip():
        raise AppError(
            "DU_LIEU_SAI", "Tên xét nghiệm không được để trống", "ten_xet_nghiem"
        )

    if ket_qua and str(ket_qua).strip() and not ngay_gio_thuc_hien:
        raise AppError(
            "DU_LIEU_SAI", "Cần nhập ngày giờ khi đã có kết quả", "ngay_gio_thuc_hien"
        )

    connection = get_connection()
    cursor = None
    commit_attempted = False

    try:
        price = Decimal(str(don_gia_ap_dung))
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)

        # Khóa phiếu khám để chống xung đột (Concurrency Control)
        cursor.execute(
            "SELECT 1 FROM PhieuKhamBenh WHERE MaPhieuKhamBenh = %s FOR UPDATE",
            (ma_phieu,),
        )
        if not cursor.fetchone():
            raise AppError("KHONG_THAY", "Không tìm thấy phiếu khám")

        if stt is None:
            # Lấy STT tiếp theo cho xét nghiệm mới
            cursor.execute(
                "SELECT COALESCE(MAX(STTXetNghiem), 0) + 1 AS stt FROM XetNghiem WHERE MaPhieuKhamBenh = %s",
                (ma_phieu,),
            )
            next_stt_row = cursor.fetchone()
            next_stt = (
                int(next_stt_row["stt"]) if next_stt_row and next_stt_row["stt"] else 1
            )

            sql_insert = """
                INSERT INTO XetNghiem (MaPhieuKhamBenh, STTXetNghiem, TenXetNghiem, KetQuaXetNghiem, NgayGioThucHien, DonGiaApDung)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(
                sql_insert,
                (
                    ma_phieu,
                    next_stt,
                    str(ten_xet_nghiem).strip(),
                    str(ket_qua).strip() if ket_qua else None,
                    ngay_gio_thuc_hien,
                    price,
                ),
            )
        else:
            # Cập nhật xét nghiệm đã có
            cursor.execute(
                "SELECT 1 FROM XetNghiem WHERE MaPhieuKhamBenh = %s AND STTXetNghiem = %s FOR UPDATE",
                (ma_phieu, stt),
            )
            if not cursor.fetchone():
                raise AppError("KHONG_THAY", "Không tìm thấy xét nghiệm")

            sql_update = """
                UPDATE XetNghiem 
                SET TenXetNghiem = %s, KetQuaXetNghiem = %s, NgayGioThucHien = %s, DonGiaApDung = %s
                WHERE MaPhieuKhamBenh = %s AND STTXetNghiem = %s
            """
            cursor.execute(
                sql_update,
                (
                    str(ten_xet_nghiem).strip(),
                    str(ket_qua).strip() if ket_qua else None,
                    ngay_gio_thuc_hien,
                    price,
                    ma_phieu,
                    stt,
                ),
            )
            next_stt = stt

        commit_attempted = True
        connection.commit()
        return next_stt

    except Exception as error:
        if not commit_attempted:
            connection.rollback()
        if isinstance(error, AppError):
            raise error
        raise app_error_from_database(error) from error
    finally:
        if cursor:
            cursor.close()
        connection.close()
