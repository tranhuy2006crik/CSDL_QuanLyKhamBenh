import logging
from typing import Any, cast

import mysql.connector

from app.contracts import (
    BacSiDTO,
    CHUA_CHI_DINH,
    ChiTietLanKham,
    CON_CHO,
    DA_DU_KET_QUA,
    DonThuocDTO,
    KhoaDTO,
    ThuocDanhMuc,
)
from app.demo_data import demo_data, is_demo_mode
from app.db import get_connection
from app.errors import AppError, app_error_from_database, require_positive_int
from app.read_queries import (
    Q_BAC_SI,
    Q_CHI_TIET_DON,
    Q_DON_THUOC,
    Q_KHOA,
    Q_NOI_DUNG_KHAM,
    Q_PHIEU_TOM_TAT,
    Q_THUOC,
    Q_XET_NGHIEM,
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
        logger.exception("Read query failed")
        raise app_error_from_database(error) from error
    finally:
        connection.close()


def lay_khoa() -> list[KhoaDTO]:
    if is_demo_mode():
        return cast(list[KhoaDTO], demo_data().list_departments())
    return cast(list[KhoaDTO], _read(Q_KHOA))


def lay_bac_si(ma_khoa: int | None = None) -> list[BacSiDTO]:
    if ma_khoa is not None:
        require_positive_int(ma_khoa, "ma_khoa", "Mã khoa")
    if is_demo_mode():
        return cast(list[BacSiDTO], demo_data().list_doctors(ma_khoa))
    return cast(list[BacSiDTO], _read(Q_BAC_SI, {"ma_khoa": ma_khoa}))


def lay_thuoc() -> list[ThuocDanhMuc]:
    if is_demo_mode():
        return cast(list[ThuocDanhMuc], demo_data().list_medicines())
    return cast(list[ThuocDanhMuc], _read(Q_THUOC))


def lay_don_thuoc(ma_phieu: int) -> DonThuocDTO | None:
    require_positive_int(ma_phieu, "ma_phieu", "Mã phiếu khám")
    if is_demo_mode():
        return demo_data().get_order(ma_phieu)
    rows = _read(Q_DON_THUOC, {"ma_phieu": ma_phieu})
    if not rows:
        return None

    header = rows[0]
    details = _read(Q_CHI_TIET_DON, {"ma_don": header["ma_don"]})
    return cast(DonThuocDTO, {**header, "ds_thuoc": details})


def lay_chi_tiet_lan_kham(ma_phieu: int) -> ChiTietLanKham:
    require_positive_int(ma_phieu, "ma_phieu", "Mã phiếu khám")
    if is_demo_mode():
        return demo_data().visit_detail(ma_phieu)
    summary_rows = _read(Q_PHIEU_TOM_TAT, {"ma_phieu": ma_phieu})
    if not summary_rows:
        raise AppError("KHONG_TIM_THAY", "Không tìm thấy phiếu khám.")

    content_rows = _read(Q_NOI_DUNG_KHAM, {"ma_phieu": ma_phieu})
    if not content_rows:
        raise AppError("KHONG_TIM_THAY", "Không tìm thấy thông tin phiếu khám.")

    return cast(
        ChiTietLanKham,
        {
            "thong_tin": summary_rows[0],
            **content_rows[0],
            "ds_xet_nghiem": _read(Q_XET_NGHIEM, {"ma_phieu": ma_phieu}),
            "don_thuoc": lay_don_thuoc(ma_phieu),
        },
    )


def tinh_tinh_trang_xet_nghiem(
    so_xet_nghiem: int, so_xet_nghiem_cho: int
) -> str:
    if so_xet_nghiem == 0:
        return CHUA_CHI_DINH
    if so_xet_nghiem_cho > 0:
        return CON_CHO
    return DA_DU_KET_QUA
