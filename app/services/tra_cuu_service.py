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
from app.errors import AppError, app_error_from_database
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
            rows = cursor.fetchall()

            # Tự động map lại các Tên Cột từ SQL sang đúng chuẩn biến cho UI
            for row in rows:
                keys = list(row.keys())
                for k in keys:
                    k_low = k.lower()
                    if k_low in ("trangthaiphieukham", "trang_thai_phieu_kham"):
                        row["trang_thai_phieu_kham"] = row[k]
                    elif k_low in ("maphieukhambenh", "ma_phieu"):
                        row["ma_phieu"] = row[k]
                    elif k_low in ("madonthuoc", "ma_don"):
                        row["ma_don"] = row[k]
                    elif k_low in ("hotenbenhnhan", "ho_ten_benh_nhan"):
                        row["ho_ten_benh_nhan"] = row[k]
                    elif k_low in ("tenbacsi", "ten_bac_si"):
                        row["ten_bac_si"] = row[k]
                    elif k_low in ("trieuchung", "trieu_chung"):
                        row["trieu_chung"] = row[k]
                    elif k_low in ("chandoan", "chan_doan"):
                        row["chan_doan"] = row[k]

            return rows
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
        val_khoa = str(ma_khoa).strip()
        if not val_khoa:
            raise AppError(
                "DU_LIEU_KHONG_HOP_LE", "Mã khoa không được để trống.", "ma_khoa"
            )
    if is_demo_mode():
        return cast(list[BacSiDTO], demo_data().list_doctors(ma_khoa))
    return cast(list[BacSiDTO], _read(Q_BAC_SI, {"ma_khoa": ma_khoa}))


def lay_thuoc() -> list[ThuocDanhMuc]:
    if is_demo_mode():
        return cast(list[ThuocDanhMuc], demo_data().list_medicines())
    return cast(list[ThuocDanhMuc], _read(Q_THUOC))


def lay_don_thuoc(ma_phieu: str) -> DonThuocDTO | None:
    val_phieu = str(ma_phieu).strip()
    if not val_phieu:
        raise AppError(
            "DU_LIEU_KHONG_HOP_LE", "Mã phiếu khám không được để trống.", "ma_phieu"
        )

    if is_demo_mode():
        return demo_data().get_order(val_phieu)
    rows = _read(Q_DON_THUOC, {"ma_phieu": val_phieu})
    if not rows:
        return None

    header = rows[0]
    ma_don = header.get("ma_don") or header.get("MaDonThuoc")
    details = _read(Q_CHI_TIET_DON, {"ma_don": ma_don})

    for dt in details:
        for k in list(dt.keys()):
            k_low = k.lower()
            if k_low == "tenthuoc":
                dt["ten_thuoc"] = dt[k]
            elif k_low == "soluongke":
                dt["so_luong_ke"] = dt[k]
            elif k_low == "cachdung":
                dt["cach_dung"] = dt[k]

    return cast(DonThuocDTO, {**header, "ds_thuoc": details})


def lay_chi_tiet_lan_kham(ma_phieu: str) -> ChiTietLanKham:
    val_phieu = str(ma_phieu).strip()
    if not val_phieu:
        raise AppError(
            "DU_LIEU_KHONG_HOP_LE", "Mã phiếu khám không được để trống.", "ma_phieu"
        )

    if is_demo_mode():
        return demo_data().visit_detail(val_phieu)

    summary_rows = _read(Q_PHIEU_TOM_TAT, {"ma_phieu": val_phieu})
    if not summary_rows:
        raise AppError("KHONG_TIM_THAY", "Không tìm thấy phiếu khám.")

    # Bổ sung ép lấy trạng thái trực tiếp từ bảng PhieuKhamBenh nếu query tóm tắt thiếu
    status_query = "SELECT TrangThaiPhieuKham FROM PhieuKhamBenh WHERE MaPhieuKhamBenh = %(ma_phieu)s"
    real_status_rows = _read(status_query, {"ma_phieu": val_phieu})
    if real_status_rows:
        real_status = real_status_rows[0].get("trang_thai_phieu_kham") or "DANG_KHAM"
        summary_rows[0]["trang_thai_phieu_kham"] = str(real_status).strip().upper()

    content_rows = _read(Q_NOI_DUNG_KHAM, {"ma_phieu": val_phieu})
    if not content_rows:
        raise AppError("KHONG_TIM_THAY", "Không tìm thấy thông tin phiếu khám.")

    ds_xet_nghiem = _read(Q_XET_NGHIEM, {"ma_phieu": val_phieu})

    for xn in ds_xet_nghiem:
        for k in list(xn.keys()):
            k_low = k.lower()
            if k_low == "tenxetnghiem":
                xn["ten_xet_nghiem"] = xn[k]
            elif k_low == "ketquaxetnghiem":
                xn["ket_qua"] = xn[k]
            elif k_low == "dongiaapdung":
                xn["don_gia_ap_dung"] = xn[k]
            elif k_low == "ngaygiothuchien":
                xn["ngay_gio_thuc_hien"] = xn[k]
            elif k_low == "sttxetnghiem":
                xn["stt"] = xn[k]

    return cast(
        ChiTietLanKham,
        {
            "thong_tin": summary_rows[0],
            **content_rows[0],
            "ds_xet_nghiem": ds_xet_nghiem,
            "don_thuoc": lay_don_thuoc(val_phieu),
        },
    )


def tinh_tinh_trang_xet_nghiem(so_xet_nghiem: int, so_xet_nghiem_cho: int) -> str:
    if so_xet_nghiem == 0:
        return CHUA_CHI_DINH
    if so_xet_nghiem_cho > 0:
        return CON_CHO
    return DA_DU_KET_QUA
