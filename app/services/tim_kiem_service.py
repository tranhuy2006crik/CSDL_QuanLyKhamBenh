from datetime import date
from app.db import get_connection
from app.errors import app_error_from_database


def tim_kiem_benh_nhan(
    tu_khoa: str = "",
    ngay_sinh: date | None = None,
    gioi_tinh: str | None = None,
    dia_chi: str = "",
):
    connection = get_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        sql = """
            SELECT
                bn.MaBenhNhan,
                bn.HoTen,
                bn.NgaySinh,
                bn.GioiTinh,
                bn.SoDienThoai,
                bn.DiaChi
            FROM BenhNhan bn
            WHERE (
                LOCATE(TRIM(COALESCE(%s, '')), bn.MaBenhNhan) > 0
                OR LOCATE(TRIM(COALESCE(%s, '')), bn.HoTen) > 0
                OR LOCATE(TRIM(COALESCE(%s, '')), COALESCE(bn.SoDienThoai, '')) > 0
            )
            AND bn.NgaySinh = COALESCE(%s, bn.NgaySinh)
            AND bn.GioiTinh = COALESCE(NULLIF(UPPER(TRIM(%s)), ''), bn.GioiTinh)
            AND LOCATE(TRIM(COALESCE(%s, '')), COALESCE(bn.DiaChi, '')) > 0
            ORDER BY bn.HoTen, bn.NgaySinh, bn.MaBenhNhan;
        """
        val_tu_khoa = tu_khoa.strip() if tu_khoa.strip() else None
        val_dia_chi = dia_chi.strip() if dia_chi.strip() else None

        params = (
            val_tu_khoa,
            val_tu_khoa,
            val_tu_khoa,
            ngay_sinh,
            gioi_tinh,
            val_dia_chi,
        )

        cursor.execute(sql, params)
        return cursor.fetchall()
    except Exception as e:
        raise app_error_from_database(e) from e
    finally:
        if cursor:
            cursor.close()
        connection.close()
