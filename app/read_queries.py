"""Parameterized SQL for the relations shown in the team's relational schema."""

Q_KHOA = """
SELECT MaKhoa AS ma_khoa, TenKhoa AS ten_khoa
FROM Khoa
ORDER BY TenKhoa, MaKhoa
"""

Q_BAC_SI = """
SELECT MaBacSi AS ma_bac_si, HoTen AS ten_bac_si, MaKhoa AS ma_khoa
FROM BacSi
WHERE (%(ma_khoa)s IS NULL OR MaKhoa = %(ma_khoa)s)
ORDER BY HoTen, MaBacSi
"""

Q_BAC_SI_THEO_MA = """
SELECT MaBacSi AS ma_bac_si, HoTen AS ten_bac_si, MaKhoa AS ma_khoa,
       GiaKham AS gia_kham, PhongKham AS phong_kham
FROM BacSi
WHERE MaBacSi = %(ma_bac_si)s
"""

Q_BENH_NHAN_THEO_MA = """
SELECT MaBenhNhan AS ma_benh_nhan, HoTen AS ho_ten,
       NgaySinh AS ngay_sinh, YEAR(NgaySinh) AS nam_sinh,
       GioiTinh AS gioi_tinh, DiaChi AS dia_chi,
       SoDienThoai AS so_dien_thoai
FROM BenhNhan
WHERE MaBenhNhan = %(ma_benh_nhan)s
"""

Q_THUOC = """
SELECT MaThuoc AS ma_thuoc, TenThuoc AS ten_thuoc, DonGia AS don_gia,
       DonViTinh AS don_vi_tinh, SoLuongCoSan AS so_luong_co_san
FROM Thuoc
ORDER BY TenThuoc, MaThuoc
"""

Q_TIM_BENH_NHAN = """
SELECT b.MaBenhNhan AS ma_benh_nhan, b.HoTen AS ho_ten,
       b.NgaySinh AS ngay_sinh, YEAR(b.NgaySinh) AS nam_sinh,
       b.GioiTinh AS gioi_tinh, b.DiaChi AS dia_chi,
       b.SoDienThoai AS so_dien_thoai
FROM BenhNhan AS b
WHERE (
    %(tu_khoa)s = ''
    OR CAST(b.MaBenhNhan AS CHAR) LIKE %(mau_tim)s
    OR b.HoTen LIKE %(mau_tim)s
    OR b.SoDienThoai LIKE %(mau_tim)s
    OR b.DiaChi LIKE %(mau_tim)s
)
AND (
    %(ma_khoa)s IS NULL
    OR EXISTS (
        SELECT 1
        FROM HoSoBenAn AS h
        JOIN PhieuKhamBenh AS p ON p.MaHoSo = h.MaHoSo
        JOIN BacSi AS bs ON bs.MaBacSi = p.MaBacSi
        WHERE h.MaBenhNhan = b.MaBenhNhan
          AND bs.MaKhoa = %(ma_khoa)s
    )
)
AND (
    %(ma_bac_si)s IS NULL
    OR EXISTS (
        SELECT 1
        FROM HoSoBenAn AS h
        JOIN PhieuKhamBenh AS p ON p.MaHoSo = h.MaHoSo
        WHERE h.MaBenhNhan = b.MaBenhNhan
          AND p.MaBacSi = %(ma_bac_si)s
    )
)
ORDER BY b.HoTen, b.MaBenhNhan
"""

Q_HO_SO_BENH_AN = """
SELECT MaHoSo AS ma_ho_so, MaBenhNhan AS ma_benh_nhan,
       NgayLap AS ngay_lap, TienSuBenh AS tien_su_benh
FROM HoSoBenAn
WHERE MaBenhNhan = %(ma_benh_nhan)s
"""

Q_LICH_SU_BENH_NHAN = """
SELECT
    p.MaPhieuKhamBenh AS ma_phieu,
    p.NgayGioKham AS ngay_gio_kham,
    p.MaBacSi AS ma_bac_si,
    bs.HoTen AS ten_bac_si,
    k.TenKhoa AS ten_khoa,
    p.ChanDoan AS chan_doan,
    p.TrieuChung AS trieu_chung,
    p.GiaKhamApDung AS gia_kham,
    COALESCE(x.gia_xet_nghiem, 0) AS gia_xet_nghiem,
    COALESCE(d.gia_thuoc, 0) AS gia_thuoc,
    COALESCE(p.GiaKhamApDung, 0)
        + COALESCE(x.gia_xet_nghiem, 0)
        + COALESCE(d.gia_thuoc, 0) AS tong_chi_phi
FROM HoSoBenAn AS h
JOIN PhieuKhamBenh AS p ON p.MaHoSo = h.MaHoSo
JOIN BacSi AS bs ON bs.MaBacSi = p.MaBacSi
JOIN Khoa AS k ON k.MaKhoa = bs.MaKhoa
LEFT JOIN (
    SELECT MaPhieuKhamBenh, SUM(DonGiaApDung) AS gia_xet_nghiem
    FROM XetNghiem
    GROUP BY MaPhieuKhamBenh
) AS x ON x.MaPhieuKhamBenh = p.MaPhieuKhamBenh
LEFT JOIN (
    SELECT d.MaPhieuKhamBenh,
           SUM(c.SoLuongKe * c.DonGiaApDung) AS gia_thuoc
    FROM DonThuoc AS d
    JOIN ChiTietDonThuoc AS c ON c.MaDonThuoc = d.MaDonThuoc
    GROUP BY d.MaPhieuKhamBenh
) AS d ON d.MaPhieuKhamBenh = p.MaPhieuKhamBenh
WHERE h.MaBenhNhan = %(ma_benh_nhan)s
ORDER BY p.NgayGioKham DESC, p.MaPhieuKhamBenh DESC
"""

Q_PHIEU_TOM_TAT = """
SELECT
    p.MaPhieuKhamBenh AS ma_phieu,
    h.MaBenhNhan AS ma_benh_nhan,
    bn.HoTen AS ho_ten_benh_nhan,
    bn.SoDienThoai AS so_dien_thoai,
    p.MaBacSi AS ma_bac_si,
    bs.HoTen AS ten_bac_si,
    bs.MaKhoa AS ma_khoa,
    k.TenKhoa AS ten_khoa,
    p.NgayGioKham AS ngay_gio_kham,
    COALESCE(x.so_xet_nghiem, 0) AS so_xet_nghiem,
    COALESCE(x.so_xet_nghiem_cho, 0) AS so_xet_nghiem_cho,
    CASE
        WHEN COALESCE(x.so_xet_nghiem, 0) = 0 THEN 'CHUA_CHI_DINH'
        WHEN COALESCE(x.so_xet_nghiem_cho, 0) > 0 THEN 'CON_CHO'
        ELSE 'DA_DU_KET_QUA'
    END AS tinh_trang_xet_nghiem,
    p.GiaKhamApDung AS gia_kham,
    COALESCE(x.gia_xet_nghiem, 0) AS gia_xet_nghiem,
    COALESCE(d.gia_thuoc, 0) AS gia_thuoc,
    COALESCE(p.GiaKhamApDung, 0)
        + COALESCE(x.gia_xet_nghiem, 0)
        + COALESCE(d.gia_thuoc, 0) AS tong_gia_tri
FROM PhieuKhamBenh AS p
JOIN HoSoBenAn AS h ON h.MaHoSo = p.MaHoSo
JOIN BenhNhan AS bn ON bn.MaBenhNhan = h.MaBenhNhan
JOIN BacSi AS bs ON bs.MaBacSi = p.MaBacSi
JOIN Khoa AS k ON k.MaKhoa = bs.MaKhoa
LEFT JOIN (
    SELECT MaPhieuKhamBenh,
           COUNT(*) AS so_xet_nghiem,
           SUM(CASE
                   WHEN KetQuaXetNghiem IS NULL OR TRIM(KetQuaXetNghiem) = ''
                   THEN 1 ELSE 0
               END) AS so_xet_nghiem_cho,
           SUM(DonGiaApDung) AS gia_xet_nghiem
    FROM XetNghiem
    GROUP BY MaPhieuKhamBenh
) AS x ON x.MaPhieuKhamBenh = p.MaPhieuKhamBenh
LEFT JOIN (
    SELECT d.MaPhieuKhamBenh,
           SUM(c.SoLuongKe * c.DonGiaApDung) AS gia_thuoc
    FROM DonThuoc AS d
    JOIN ChiTietDonThuoc AS c ON c.MaDonThuoc = d.MaDonThuoc
    GROUP BY d.MaPhieuKhamBenh
) AS d ON d.MaPhieuKhamBenh = p.MaPhieuKhamBenh
WHERE p.MaPhieuKhamBenh = %(ma_phieu)s
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
SELECT d.MaDonThuoc AS ma_don, d.MaPhieuKhamBenh AS ma_phieu,
       d.NgayLapDonThuoc AS ngay_lap, d.LoiDanChung AS loi_dan,
       COALESCE(SUM(c.SoLuongKe * c.DonGiaApDung), 0) AS gia_don
FROM DonThuoc AS d
LEFT JOIN ChiTietDonThuoc AS c ON c.MaDonThuoc = d.MaDonThuoc
WHERE d.MaPhieuKhamBenh = %(ma_phieu)s
GROUP BY d.MaDonThuoc, d.MaPhieuKhamBenh, d.NgayLapDonThuoc, d.LoiDanChung
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

Q_LICH_LAM_VIEC = """
SELECT
    bs.MaBacSi AS ma_bac_si,
    bs.HoTen AS ten_bac_si,
    bs.PhongKham AS phong_kham,
    lw.Thu AS thu,
    lw.GioBatDau AS gio_bat_dau,
    lw.GioKetThuc AS gio_ket_thuc
FROM BacSi AS bs
JOIN LichLamViecBacSi AS lw ON lw.MaBacSi = bs.MaBacSi
WHERE bs.MaKhoa = %(ma_khoa)s
ORDER BY bs.HoTen, lw.Thu, lw.GioBatDau
"""

Q_BAO_CAO_BAC_SI = """
SELECT
    bs.MaBacSi AS ma_bac_si,
    bs.HoTen AS ten_bac_si,
    k.MaKhoa AS ma_khoa,
    k.TenKhoa AS ten_khoa,
    COUNT(p.MaPhieuKhamBenh) AS so_luot_kham,
    COALESCE(SUM(p.tong_gia_tri), 0) AS tong_gia_tri
FROM BacSi AS bs
JOIN Khoa AS k ON k.MaKhoa = bs.MaKhoa
LEFT JOIN (
    SELECT
        pk.MaBacSi,
        h.MaBenhNhan,
        pk.MaPhieuKhamBenh,
        COALESCE(pk.GiaKhamApDung, 0)
            + COALESCE(x.gia_xet_nghiem, 0)
            + COALESCE(d.gia_thuoc, 0) AS tong_gia_tri
    FROM PhieuKhamBenh AS pk
    JOIN HoSoBenAn AS h ON h.MaHoSo = pk.MaHoSo
    LEFT JOIN (
        SELECT MaPhieuKhamBenh, SUM(DonGiaApDung) AS gia_xet_nghiem
        FROM XetNghiem
        GROUP BY MaPhieuKhamBenh
    ) AS x ON x.MaPhieuKhamBenh = pk.MaPhieuKhamBenh
    LEFT JOIN (
        SELECT d.MaPhieuKhamBenh,
               SUM(c.SoLuongKe * c.DonGiaApDung) AS gia_thuoc
        FROM DonThuoc AS d
        JOIN ChiTietDonThuoc AS c ON c.MaDonThuoc = d.MaDonThuoc
        GROUP BY d.MaPhieuKhamBenh
    ) AS d ON d.MaPhieuKhamBenh = pk.MaPhieuKhamBenh
    WHERE pk.NgayGioKham >= %(tu_ngay)s
      AND pk.NgayGioKham < %(den_ngay)s
) AS p ON p.MaBacSi = bs.MaBacSi
WHERE (%(ma_khoa)s IS NULL OR bs.MaKhoa = %(ma_khoa)s)
  AND (
      %(tu_khoa)s = ''
      OR CAST(bs.MaBacSi AS CHAR) LIKE %(mau_tim)s
      OR bs.HoTen LIKE %(mau_tim)s
  )
  AND (%(hien_bac_si_rong)s = 1 OR p.MaPhieuKhamBenh IS NOT NULL)
GROUP BY bs.MaBacSi, bs.HoTen, k.MaKhoa, k.TenKhoa
ORDER BY tong_gia_tri DESC, bs.HoTen, bs.MaBacSi
"""

Q_LOCK_HO_SO_BENH_NHAN = """
SELECT h.MaHoSo AS ma_ho_so
FROM HoSoBenAn AS h
WHERE h.MaBenhNhan = %(ma_benh_nhan)s
FOR UPDATE
"""

Q_LOCK_BAC_SI_GIA = """
SELECT MaBacSi AS ma_bac_si, GiaKham AS gia_kham
FROM BacSi
WHERE MaBacSi = %(ma_bac_si)s
FOR UPDATE
"""

Q_INSERT_PHIEU_KHAM = """
INSERT INTO PhieuKhamBenh
    (MaPhieuKhamBenh, MaBacSi, MaHoSo, NgayGioKham,
     ChanDoan, TrieuChung, GiaKhamApDung)
VALUES
    (%(ma_phieu)s, %(ma_bac_si)s, %(ma_ho_so)s, NOW(),
     %(chan_doan)s, %(trieu_chung)s, %(gia_kham)s)
"""

Q_UPDATE_NOI_DUNG_KHAM = """
UPDATE PhieuKhamBenh
SET ChanDoan = %(chan_doan)s, TrieuChung = %(trieu_chung)s
WHERE MaPhieuKhamBenh = %(ma_phieu)s
"""

Q_LOCK_PHIEU_KHAM = """
SELECT MaPhieuKhamBenh
FROM PhieuKhamBenh
WHERE MaPhieuKhamBenh = %(ma_phieu)s
FOR UPDATE
"""

Q_NEXT_STT_XET_NGHIEM = """
SELECT COALESCE(MAX(STTXetNghiem), 0) + 1 AS stt
FROM XetNghiem
WHERE MaPhieuKhamBenh = %(ma_phieu)s
"""

Q_LOCK_XET_NGHIEM = """
SELECT STTXetNghiem
FROM XetNghiem
WHERE MaPhieuKhamBenh = %(ma_phieu)s
  AND STTXetNghiem = %(stt)s
FOR UPDATE
"""

Q_INSERT_XET_NGHIEM = """
INSERT INTO XetNghiem
    (MaPhieuKhamBenh, STTXetNghiem, TenXetNghiem,
     KetQuaXetNghiem, NgayGioThucHien, DonGiaApDung)
VALUES
    (%(ma_phieu)s, %(stt)s, %(ten_xet_nghiem)s,
     %(ket_qua)s, %(ngay_gio_thuc_hien)s, %(don_gia_ap_dung)s)
"""

Q_UPDATE_XET_NGHIEM = """
UPDATE XetNghiem
SET TenXetNghiem = %(ten_xet_nghiem)s,
    KetQuaXetNghiem = %(ket_qua)s,
    NgayGioThucHien = %(ngay_gio_thuc_hien)s,
    DonGiaApDung = %(don_gia_ap_dung)s
WHERE MaPhieuKhamBenh = %(ma_phieu)s
  AND STTXetNghiem = %(stt)s
"""
