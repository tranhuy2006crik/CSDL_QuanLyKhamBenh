"""Shared, parameterized read SQL; align aliases with the final team schema."""

Q_KHOA = """
SELECT MaKhoa AS ma_khoa, TenKhoa AS ten_khoa
FROM Khoa
ORDER BY MaKhoa
"""

Q_BAC_SI = """
SELECT MaBacSi AS ma_bac_si, HoTen AS ten_bac_si, MaKhoa AS ma_khoa
FROM BacSi
WHERE (%(ma_khoa)s IS NULL OR MaKhoa = %(ma_khoa)s)
ORDER BY HoTen, MaBacSi
"""

Q_THUOC = """
SELECT
    MaThuoc AS ma_thuoc,
    TenThuoc AS ten_thuoc,
    DonGia AS don_gia,
    DonViTinh AS don_vi_tinh,
    SoLuongCoSan AS so_luong_co_san
FROM Thuoc
ORDER BY TenThuoc, MaThuoc
"""

Q_PHIEU_TOM_TAT = """
SELECT *
FROM v_tong_hop_lan_kham
WHERE ma_phieu = %(ma_phieu)s
"""

Q_NOI_DUNG_KHAM = """
SELECT ChanDoan AS chan_doan, TrieuChung AS trieu_chung
FROM PhieuKhamBenh
WHERE MaPhieuKhamBenh = %(ma_phieu)s
"""

Q_XET_NGHIEM = """
SELECT
    MaPhieuKhamBenh AS ma_phieu,
    STTXetNghiem AS stt,
    TenXetNghiem AS ten_xet_nghiem,
    KetQuaXetNghiem AS ket_qua,
    NgayGioThucHien AS ngay_gio_thuc_hien,
    DonGiaApDung AS don_gia_ap_dung
FROM XetNghiem
WHERE MaPhieuKhamBenh = %(ma_phieu)s
ORDER BY STTXetNghiem
"""

Q_DON_THUOC = """
SELECT
    d.MaDonThuoc AS ma_don,
    d.MaPhieuKhamBenh AS ma_phieu,
    d.NgayLapDonThuoc AS ngay_lap,
    d.LoiDanChung AS loi_dan,
    v.gia_thuoc AS gia_don
FROM DonThuoc AS d
JOIN v_tong_hop_lan_kham AS v
    ON v.ma_phieu = d.MaPhieuKhamBenh
WHERE d.MaPhieuKhamBenh = %(ma_phieu)s
"""

Q_CHI_TIET_DON = """
SELECT
    c.MaThuoc AS ma_thuoc,
    t.TenThuoc AS ten_thuoc,
    t.DonViTinh AS don_vi_tinh,
    c.SoLuongKe AS so_luong_ke,
    c.CachDung AS cach_dung,
    c.DonGiaApDung AS don_gia_ap_dung,
    c.SoLuongKe * c.DonGiaApDung AS thanh_tien
FROM ChiTietDonThuoc AS c
JOIN Thuoc AS t ON t.MaThuoc = c.MaThuoc
WHERE c.MaDonThuoc = %(ma_don)s
ORDER BY c.MaThuoc
"""
