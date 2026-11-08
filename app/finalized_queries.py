"""Queries aligned with the team's finalized SQL-03 and SQL-02 files."""

Q_SEARCH_PATIENTS = """
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
ORDER BY bn.HoTen, bn.NgaySinh, bn.MaBenhNhan
"""

Q_MONTHLY_DOCTOR_STATISTICS = """
SELECT
    bs.MaBacSi,
    bs.HoTen AS TenBacSi,
    COUNT(p.MaPhieuKhamBenh) AS SoLuotKham,
    COUNT(DISTINCT hs.MaBenhNhan) AS SoBenhNhan,
    COALESCE(SUM(p.GiaKhamApDung), 0) AS TongTienKham,
    COALESCE(SUM(xn.TongTienXN), 0) AS TongTienXetNghiem,
    COALESCE(SUM(dt.TongTienThuoc), 0) AS TongTienThuoc,
    COALESCE(SUM(
        COALESCE(p.GiaKhamApDung, 0)
        + COALESCE(xn.TongTienXN, 0)
        + COALESCE(dt.TongTienThuoc, 0)
    ), 0) AS TongGiaTriKham
FROM BacSi bs
LEFT JOIN PhieuKhamBenh p
    ON p.MaBacSi = bs.MaBacSi
    AND p.TrangThaiPhieuKham = 'HOAN_THANH'
    AND MONTH(p.NgayGioKham) = %s
    AND YEAR(p.NgayGioKham) = %s
LEFT JOIN HoSoBenhAn hs
    ON hs.MaHoSo = p.MaHoSo
LEFT JOIN (
    SELECT MaPhieuKhamBenh, SUM(DonGiaApDung) AS TongTienXN
    FROM XetNghiem
    GROUP BY MaPhieuKhamBenh
) xn ON xn.MaPhieuKhamBenh = p.MaPhieuKhamBenh
LEFT JOIN (
    SELECT d.MaPhieuKhamBenh,
           SUM(ct.SoLuongKe * ct.DonGiaApDung) AS TongTienThuoc
    FROM DonThuoc d
    JOIN ChiTietDonThuoc ct ON ct.MaDonThuoc = d.MaDonThuoc
    GROUP BY d.MaPhieuKhamBenh
) dt ON dt.MaPhieuKhamBenh = p.MaPhieuKhamBenh
GROUP BY bs.MaBacSi, bs.HoTen
ORDER BY bs.MaBacSi
"""

Q_COMPLETE_VISIT = """
UPDATE PhieuKhamBenh
SET TrangThaiPhieuKham = 'HOAN_THANH'
WHERE MaPhieuKhamBenh = %s
  AND TrangThaiPhieuKham = 'DANG_KHAM'
  AND ChanDoan IS NOT NULL AND TRIM(ChanDoan) <> ''
  AND NOT EXISTS (
      SELECT 1 FROM XetNghiem
      WHERE MaPhieuKhamBenh = %s
        AND (KetQuaXetNghiem IS NULL OR TRIM(KetQuaXetNghiem) = '')
  )
"""

Q_REPORT_VISIT = """
SELECT bn.MaBenhNhan, bn.HoTen, bn.NgaySinh, bn.SoDienThoai,
       pk.MaPhieuKhamBenh, pk.NgayGioKham, bs.HoTen AS BacSiKham,
       pk.ChanDoan, pk.TrieuChung
FROM PhieuKhamBenh pk
JOIN HoSoBenhAn hs ON pk.MaHoSo = hs.MaHoSo
JOIN BenhNhan bn ON hs.MaBenhNhan = bn.MaBenhNhan
JOIN BacSi bs ON pk.MaBacSi = bs.MaBacSi
WHERE pk.MaPhieuKhamBenh = %s AND pk.TrangThaiPhieuKham = 'HOAN_THANH'
"""

Q_REPORT_LABS = """
SELECT x.STTXetNghiem, x.TenXetNghiem, x.KetQuaXetNghiem,
       x.NgayGioThucHien, x.DonGiaApDung
FROM XetNghiem x
JOIN PhieuKhamBenh pk ON x.MaPhieuKhamBenh = pk.MaPhieuKhamBenh
WHERE x.MaPhieuKhamBenh = %s AND pk.TrangThaiPhieuKham = 'HOAN_THANH'
"""

Q_REPORT_PRESCRIPTION_NOTE = """
SELECT d.NgayLapDonThuoc, d.LoiDanChung
FROM DonThuoc d
JOIN PhieuKhamBenh pk ON d.MaPhieuKhamBenh = pk.MaPhieuKhamBenh
WHERE d.MaPhieuKhamBenh = %s AND pk.TrangThaiPhieuKham = 'HOAN_THANH'
"""

Q_REPORT_MEDICINES = """
SELECT t.TenThuoc, ct.SoLuongKe, t.DonViTinh, ct.CachDung,
       ct.DonGiaApDung, (ct.SoLuongKe * ct.DonGiaApDung) AS ThanhTien
FROM ChiTietDonThuoc ct
JOIN DonThuoc dt ON ct.MaDonThuoc = dt.MaDonThuoc
JOIN PhieuKhamBenh pk ON dt.MaPhieuKhamBenh = pk.MaPhieuKhamBenh
JOIN Thuoc t ON ct.MaThuoc = t.MaThuoc
WHERE dt.MaPhieuKhamBenh = %s AND pk.TrangThaiPhieuKham = 'HOAN_THANH'
"""

Q_REPORT_COSTS = """
SELECT p.MaPhieuKhamBenh, p.GiaKhamApDung,
       COALESCE(xn.TongTienXN, 0) AS TongTienXN,
       COALESCE(dt.TongTienThuoc, 0) AS TongTienThuoc,
       (p.GiaKhamApDung + COALESCE(xn.TongTienXN, 0)
        + COALESCE(dt.TongTienThuoc, 0)) AS TongChiPhi
FROM PhieuKhamBenh p
LEFT JOIN (
    SELECT MaPhieuKhamBenh, SUM(DonGiaApDung) AS TongTienXN
    FROM XetNghiem GROUP BY MaPhieuKhamBenh
) xn ON p.MaPhieuKhamBenh = xn.MaPhieuKhamBenh
LEFT JOIN (
    SELECT d.MaPhieuKhamBenh,
           SUM(ct.SoLuongKe * ct.DonGiaApDung) AS TongTienThuoc
    FROM DonThuoc d
    JOIN ChiTietDonThuoc ct ON ct.MaDonThuoc = d.MaDonThuoc
    GROUP BY d.MaPhieuKhamBenh
) dt ON p.MaPhieuKhamBenh = dt.MaPhieuKhamBenh
WHERE p.MaPhieuKhamBenh = %s AND p.TrangThaiPhieuKham = 'HOAN_THANH'
"""

Q_FIND_IN_PROGRESS_VISIT = """
SELECT MaPhieuKhamBenh AS ma_phieu
FROM PhieuKhamBenh
WHERE MaHoSo = (
    SELECT MaHoSo FROM HoSoBenhAn WHERE MaBenhNhan = %(ma_benh_nhan)s
)
AND MaBacSi = %(ma_bac_si)s
AND TrangThaiPhieuKham = 'DANG_KHAM'
"""
