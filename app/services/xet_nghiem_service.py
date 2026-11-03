from datetime import datetime
from decimal import Decimal
from app.db import get_connection
from app.errors import AppError, app_error_from_database
from app.read_queries import (
    Q_LOCK_PHIEU_KHAM,
    Q_NEXT_STT_XET_NGHIEM,
    Q_INSERT_XET_NGHIEM,
    Q_LOCK_XET_NGHIEM,
    Q_UPDATE_XET_NGHIEM,
)


def luu_xet_nghiem(
    ma_phieu, ten_xet_nghiem, ket_qua, ngay_gio_thuc_hien, don_gia_ap_dung, stt=None
):
    if not str(ten_xet_nghiem).strip():
        raise AppError(
            "DU_LIEU_SAI", "Ten xet nghiem khong duoc de trong", "ten_xet_nghiem"
        )

    if ket_qua and str(ket_qua).strip() and not ngay_gio_thuc_hien:
        raise AppError(
            "DU_LIEU_SAI", "Can nhap ngay gio khi da co ket qua", "ngay_gio_thuc_hien"
        )

    connection = get_connection()
    cursor = None
    commit_attempted = False

    try:
        price = Decimal(str(don_gia_ap_dung))
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(Q_LOCK_PHIEU_KHAM, {"ma_phieu": ma_phieu})
        if not cursor.fetchone():
            raise AppError("KHONG_THAY", "Khong tim thay phieu kham")

        if stt is None:
            cursor.execute(Q_NEXT_STT_XET_NGHIEM, {"ma_phieu": ma_phieu})
            next_stt_row = cursor.fetchone()
            next_stt = (
                int(next_stt_row["stt"]) if next_stt_row and next_stt_row["stt"] else 1
            )

            cursor.execute(
                Q_INSERT_XET_NGHIEM,
                {
                    "ma_phieu": ma_phieu,
                    "stt": next_stt,
                    "ten_xet_nghiem": str(ten_xet_nghiem).strip(),
                    "ket_qua": str(ket_qua).strip() if ket_qua else None,
                    "ngay_gio_thuc_hien": ngay_gio_thuc_hien,
                    "don_gia_ap_dung": price,
                },
            )
        else:
            cursor.execute(Q_LOCK_XET_NGHIEM, {"ma_phieu": ma_phieu, "stt": stt})
            if not cursor.fetchone():
                raise AppError("KHONG_THAY", "Khong tim thay xet nghiem")

            cursor.execute(
                Q_UPDATE_XET_NGHIEM,
                {
                    "ma_phieu": ma_phieu,
                    "stt": stt,
                    "ten_xet_nghiem": str(ten_xet_nghiem).strip(),
                    "ket_qua": str(ket_qua).strip() if ket_qua else None,
                    "ngay_gio_thuc_hien": ngay_gio_thuc_hien,
                    "don_gia_ap_dung": price,
                },
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
