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
    Identifier,
    KhoaDTO,
    ThuocDanhMuc,
)
from app.demo_data import demo_data, is_demo_mode
from app.db import get_connection
from app.errors import AppError, app_error_from_database, require_identifier
from app.finalized_queries import (
    Q_REPORT_COSTS,
    Q_REPORT_LABS,
    Q_REPORT_MEDICINES,
    Q_REPORT_PRESCRIPTION_NOTE,
    Q_REPORT_VISIT,
)
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


def _read(
    sql: str,
    params: dict[str, Any] | tuple[Any, ...] | None = None,
) -> list[dict[str, Any]]:
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


def lay_bac_si(ma_khoa: Identifier | None = None) -> list[BacSiDTO]:
    if ma_khoa is not None:
        require_identifier(ma_khoa, "ma_khoa", "Mã khoa")
    if is_demo_mode():
        return cast(list[BacSiDTO], demo_data().list_doctors(ma_khoa))
    return cast(list[BacSiDTO], _read(Q_BAC_SI, {"ma_khoa": ma_khoa}))


def lay_thuoc() -> list[ThuocDanhMuc]:
    if is_demo_mode():
        return cast(list[ThuocDanhMuc], demo_data().list_medicines())
    return cast(list[ThuocDanhMuc], _read(Q_THUOC))


def lay_don_thuoc(ma_phieu: Identifier) -> DonThuocDTO | None:
    require_identifier(ma_phieu, "ma_phieu", "Mã phiếu khám")
    if is_demo_mode():
        return demo_data().get_order(ma_phieu)
    rows = _read(Q_DON_THUOC, {"ma_phieu": ma_phieu})
    if not rows:
        return None

    header = rows[0]
    details = _read(Q_CHI_TIET_DON, {"ma_don": header["ma_don"]})
    return cast(DonThuocDTO, {**header, "ds_thuoc": details})


def lay_chi_tiet_lan_kham(
    ma_phieu: Identifier,
    vai_tro: str | None = None,
    ma_nguoi_xem: Identifier | None = None,
) -> ChiTietLanKham:
    require_identifier(ma_phieu, "ma_phieu", "Mã phiếu khám")
    if is_demo_mode():
        detail = demo_data().visit_detail(ma_phieu)
        info = detail["thong_tin"]
        _authorize_visit(info, vai_tro, ma_nguoi_xem)
        return detail
    summary_rows = _read(Q_PHIEU_TOM_TAT, {"ma_phieu": ma_phieu})
    if not summary_rows:
        raise AppError("KHONG_TIM_THAY", "Không tìm thấy phiếu khám.")
    info = summary_rows[0]
    _authorize_visit(info, vai_tro, ma_nguoi_xem)

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


def _authorize_visit(
    info: dict[str, Any], vai_tro: str | None, ma_nguoi_xem: Identifier | None
) -> None:
    if vai_tro is None:
        return
    require_identifier(ma_nguoi_xem, "ma_nguoi_xem", "Mã người xem")
    if info["trang_thai"] == "DANG_KHAM":
        if vai_tro != "doctor" or info["ma_bac_si"] != ma_nguoi_xem:
            raise AppError(
                "KHONG_DU_QUYEN",
                "Phiếu đang khám chỉ bác sĩ phụ trách mới được phép xem.",
            )
        return
    if vai_tro == "patient" and info["ma_benh_nhan"] != ma_nguoi_xem:
        raise AppError("KHONG_DU_QUYEN", "Phiếu khám không thuộc bệnh nhân này.")
    if vai_tro == "doctor" and info["ma_bac_si"] != ma_nguoi_xem:
        raise AppError("KHONG_DU_QUYEN", "Phiếu khám không thuộc bác sĩ này.")
    if vai_tro not in {"patient", "doctor"}:
        raise AppError("DU_LIEU_KHONG_HOP_LE", "Vai trò người xem không hợp lệ.")


def bao_cao_chi_tiet_phieu(ma_phieu: Identifier) -> dict[str, Any]:
    require_identifier(ma_phieu, "ma_phieu", "Mã phiếu khám")
    if is_demo_mode():
        detail = demo_data().visit_detail(ma_phieu)
        if detail["thong_tin"]["trang_thai"] != "HOAN_THANH":
            raise AppError(
                "CHUA_HOAN_THANH", "Chỉ xuất báo cáo phiếu khám đã hoàn thành."
            )
        info = detail["thong_tin"]
        order = detail["don_thuoc"]
        return {
            "thong_tin": {
                "ma_benh_nhan": info["ma_benh_nhan"],
                "ho_ten": info["ho_ten_benh_nhan"],
                "ngay_sinh": info.get("ngay_sinh"),
                "so_dien_thoai": info["so_dien_thoai"],
                "ma_phieu": info["ma_phieu"],
                "ngay_gio_kham": info["ngay_gio_kham"],
                "bac_si": info["ten_bac_si"],
                "chan_doan": detail["chan_doan"],
                "trieu_chung": detail["trieu_chung"],
            },
            "ds_xet_nghiem": [
                {
                    "stt": row["stt"],
                    "ten_xet_nghiem": row["ten_xet_nghiem"],
                    "ket_qua": row["ket_qua"],
                    "ngay_gio_thuc_hien": row["ngay_gio_thuc_hien"],
                    "don_gia_ap_dung": row["don_gia_ap_dung"],
                }
                for row in detail["ds_xet_nghiem"]
            ],
            "loi_dan": (
                [{"ngay_lap": order["ngay_lap"], "loi_dan": order["loi_dan"]}]
                if order
                else []
            ),
            "ds_thuoc": order["ds_thuoc"] if order else [],
            "tong_chi_phi": {
                "gia_kham": info["gia_kham"],
                "gia_xet_nghiem": info["gia_xet_nghiem"],
                "gia_thuoc": info["gia_thuoc"],
                "tong_chi_phi": info["tong_gia_tri"],
            },
        }
    patient_rows = _read(Q_REPORT_VISIT, (ma_phieu,))
    if not patient_rows:
        raise AppError(
            "KHONG_TIM_THAY",
            "Không tìm thấy phiếu đã hoàn thành để lập báo cáo.",
        )
    patient = patient_rows[0]
    labs = _read(Q_REPORT_LABS, (ma_phieu,))
    notes = _read(Q_REPORT_PRESCRIPTION_NOTE, (ma_phieu,))
    medicines = _read(Q_REPORT_MEDICINES, (ma_phieu,))
    costs = next(iter(_read(Q_REPORT_COSTS, (ma_phieu,))), None)
    if costs is None:
        raise AppError(
            "KHONG_TIM_THAY", "Không đọc được bảng tổng chi phí của phiếu khám."
        )
    return {
        "thong_tin": {
            "ma_benh_nhan": patient["MaBenhNhan"],
            "ho_ten": patient["HoTen"],
            "ngay_sinh": patient["NgaySinh"],
            "so_dien_thoai": patient["SoDienThoai"],
            "ma_phieu": patient["MaPhieuKhamBenh"],
            "ngay_gio_kham": patient["NgayGioKham"],
            "bac_si": patient["BacSiKham"],
            "chan_doan": patient["ChanDoan"],
            "trieu_chung": patient["TrieuChung"],
        },
        "ds_xet_nghiem": [
            {
                "stt": row["STTXetNghiem"],
                "ten_xet_nghiem": row["TenXetNghiem"],
                "ket_qua": row["KetQuaXetNghiem"],
                "ngay_gio_thuc_hien": row["NgayGioThucHien"],
                "don_gia_ap_dung": row["DonGiaApDung"],
            }
            for row in labs
        ],
        "loi_dan": [
            {"ngay_lap": row["NgayLapDonThuoc"], "loi_dan": row["LoiDanChung"]}
            for row in notes
        ],
        "ds_thuoc": [
            {
                "ten_thuoc": row["TenThuoc"],
                "so_luong_ke": row["SoLuongKe"],
                "don_vi_tinh": row["DonViTinh"],
                "cach_dung": row["CachDung"],
                "don_gia_ap_dung": row["DonGiaApDung"],
                "thanh_tien": row["ThanhTien"],
            }
            for row in medicines
        ],
        "tong_chi_phi": {
            "gia_kham": costs["GiaKhamApDung"],
            "gia_xet_nghiem": costs["TongTienXN"],
            "gia_thuoc": costs["TongTienThuoc"],
            "tong_chi_phi": costs["TongChiPhi"],
        },
    }


def tinh_tinh_trang_xet_nghiem(
    so_xet_nghiem: int, so_xet_nghiem_cho: int
) -> str:
    if so_xet_nghiem == 0:
        return CHUA_CHI_DINH
    if so_xet_nghiem_cho > 0:
        return CON_CHO
    return DA_DU_KET_QUA
