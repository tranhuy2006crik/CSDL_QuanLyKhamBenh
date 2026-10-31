from datetime import date, datetime
from decimal import Decimal
from typing import Literal, TypedDict


CHUA_CHI_DINH = "CHUA_CHI_DINH"
CON_CHO = "CON_CHO"
DA_DU_KET_QUA = "DA_DU_KET_QUA"


class ThuocDanhMuc(TypedDict):
    ma_thuoc: int
    ten_thuoc: str
    don_gia: Decimal
    don_vi_tinh: str
    so_luong_co_san: int


class KhoaDTO(TypedDict):
    ma_khoa: int
    ten_khoa: str


class BacSiDTO(TypedDict):
    ma_bac_si: int
    ten_bac_si: str
    ma_khoa: int


class XetNghiemDTO(TypedDict):
    ma_phieu: int
    stt: int
    ten_xet_nghiem: str
    ket_qua: str | None
    ngay_gio_thuc_hien: datetime | None
    don_gia_ap_dung: Decimal


class DongThuocInput(TypedDict):
    ma_thuoc: int
    so_luong_ke: int
    cach_dung: str


class DongThuocDraft(TypedDict):
    ma_thuoc: int
    ten_thuoc: str
    don_vi_tinh: str
    so_luong_ke: int
    cach_dung: str
    don_gia_ap_dung: Decimal


class DongThuocDTO(TypedDict):
    ma_thuoc: int
    ten_thuoc: str
    don_vi_tinh: str
    so_luong_ke: int
    cach_dung: str
    don_gia_ap_dung: Decimal
    thanh_tien: Decimal


class DonThuocDTO(TypedDict):
    ma_don: int
    ma_phieu: int
    ngay_lap: date
    loi_dan: str | None
    ds_thuoc: list[DongThuocDTO]
    gia_don: Decimal


class PhieuTomTat(TypedDict):
    ma_phieu: int
    ma_benh_nhan: int
    ho_ten_benh_nhan: str
    so_dien_thoai: str | None
    ma_bac_si: int
    ten_bac_si: str
    ma_khoa: int
    ten_khoa: str
    ngay_gio_kham: datetime
    so_xet_nghiem: int
    so_xet_nghiem_cho: int
    tinh_trang_xet_nghiem: Literal[
        "CHUA_CHI_DINH", "CON_CHO", "DA_DU_KET_QUA"
    ]
    gia_kham: Decimal
    gia_xet_nghiem: Decimal
    gia_thuoc: Decimal
    tong_gia_tri: Decimal


class ChiTietLanKham(TypedDict):
    thong_tin: PhieuTomTat
    chan_doan: str | None
    trieu_chung: str | None
    ds_xet_nghiem: list[XetNghiemDTO]
    don_thuoc: DonThuocDTO | None


class BaoCaoLuotKhamRow(TypedDict):
    ma_bac_si: int
    ten_bac_si: str
    ma_khoa: int
    ten_khoa: str
    so_luot_kham: int
    so_benh_nhan: int


class BaoCaoLuotKham(TypedDict):
    thang: int
    nam: int
    ma_khoa: int | None
    rows: list[BaoCaoLuotKhamRow]
    tong_so_luot_kham: int


class BaoCaoGiaTriRow(TypedDict):
    thang: int
    gia_kham: Decimal
    gia_xet_nghiem: Decimal
    gia_thuoc: Decimal
    tong_gia_tri: Decimal


class BaoCaoGiaTriTotals(TypedDict):
    gia_kham: Decimal
    gia_xet_nghiem: Decimal
    gia_thuoc: Decimal
    tong_gia_tri: Decimal


class BaoCaoGiaTri(TypedDict):
    nam: int
    rows: list[BaoCaoGiaTriRow]
    totals: BaoCaoGiaTriTotals


class PdfColumn(TypedDict):
    key: str
    label: str
    kind: Literal["text", "int", "money", "date", "datetime"]
