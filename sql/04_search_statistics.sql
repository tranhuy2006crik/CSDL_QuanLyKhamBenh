-- 04_search_statistics.sql
-- Truy van cho tim kiem benh nhan, thong ke kham/doanh thu va lich lam viec bac si.
-- Tham so Python dung %s (mysql-connector-python / pymysql).
USE quanlykhambenh;

-- ============================================================================
-- A. TIM KIEM BENH NHAN
-- Tham so Python theo thu tu (6 gia tri):
-- (tu_khoa, tu_khoa, tu_khoa, ngay_sinh, gioi_tinh, dia_chi)
-- Cot Khoa la cac khoa benh nhan da dat lich (khong tinh lich DA_HUY) hoac da kham.
-- Neu benh nhan co nhieu khoa, tra ve danh sach ten khoa cach nhau bang dau phay.
-- Chuoi rong / NULL o cac bo loc duoc xem la bo qua.
SELECT
    bn.MaBenhNhan,
    bn.HoTen,
    bn.NgaySinh,
    bn.GioiTinh,
    bn.SoDienThoai,
    bn.DiaChi,
    pkhoa.DanhSachKhoa AS Khoa
FROM BenhNhan bn
LEFT JOIN (
    SELECT ds.MaBenhNhan,
           GROUP_CONCAT(DISTINCT ds.TenKhoa ORDER BY ds.TenKhoa SEPARATOR ', ') AS DanhSachKhoa
    FROM (
        SELECT lh.MaBenhNhan, k.TenKhoa
        FROM LichHen lh
        JOIN BacSi bs ON bs.MaBacSi = lh.MaBacSi
        JOIN Khoa k ON k.MaKhoa = bs.MaKhoa
        WHERE lh.TrangThai <> 'DA_HUY'

        UNION

        SELECT hs.MaBenhNhan, k.TenKhoa
        FROM PhieuKhamBenh pk
        JOIN HoSoBenhAn hs ON hs.MaHoSo = pk.MaHoSo
        JOIN BacSi bs ON bs.MaBacSi = pk.MaBacSi
        JOIN Khoa k ON k.MaKhoa = bs.MaKhoa
    ) ds
    GROUP BY ds.MaBenhNhan
) pkhoa ON pkhoa.MaBenhNhan = bn.MaBenhNhan
WHERE (
    LOCATE(TRIM(COALESCE(%s, '')), bn.MaBenhNhan) > 0
    OR LOCATE(TRIM(COALESCE(%s, '')), bn.HoTen) > 0
    OR LOCATE(TRIM(COALESCE(%s, '')), COALESCE(bn.SoDienThoai, '')) > 0
)
AND bn.NgaySinh = COALESCE(%s, bn.NgaySinh)
AND bn.GioiTinh = COALESCE(NULLIF(UPPER(TRIM(%s)), ''), bn.GioiTinh)
AND LOCATE(TRIM(COALESCE(%s, '')), COALESCE(bn.DiaChi, '')) > 0
ORDER BY bn.HoTen, bn.NgaySinh, bn.MaBenhNhan;


-- ============================================================================
-- B. BAO CAO THONG KE LUOT KHAM VA DOANH THU THEO BAC SI
-- Tham so Python: (thang, nam); thang 1..12.
-- Chi tinh phieu HOAN_THANH; van hien bac si chua co luot kham trong thang.
-- Gom tong tien XN/thuoc theo tung phieu truoc khi JOIN de tranh nhan dong.
-- Cac cot tien dung don gia luu tai phieu/XN/chi tiet don thuoc theo schema v5.3.
SELECT
    bs.MaBacSi,
    bs.HoTen AS TenBacSi,
    COUNT(pk.MaPhieuKhamBenh) AS SoLuotKham,
    COUNT(DISTINCT hs.MaBenhNhan) AS SoBenhNhan,
    COALESCE(SUM(pk.GiaKhamApDung), 0) AS TongTienKham,
    COALESCE(SUM(xn.TongTienXN), 0) AS TongTienXetNghiem,
    COALESCE(SUM(dt.TongTienThuoc), 0) AS TongTienThuoc,
    COALESCE(SUM(
        COALESCE(pk.GiaKhamApDung, 0)
        + COALESCE(xn.TongTienXN, 0)
        + COALESCE(dt.TongTienThuoc, 0)
    ), 0) AS TongGiaTriKham
FROM BacSi bs
LEFT JOIN PhieuKhamBenh pk
    ON pk.MaBacSi = bs.MaBacSi
   AND pk.TrangThaiPhieuKham = 'HOAN_THANH'
   AND MONTH(pk.NgayGioKham) = %s
   AND YEAR(pk.NgayGioKham) = %s
LEFT JOIN HoSoBenhAn hs ON hs.MaHoSo = pk.MaHoSo
LEFT JOIN (
    SELECT MaPhieuKhamBenh, SUM(DonGiaApDung) AS TongTienXN
    FROM XetNghiem
    GROUP BY MaPhieuKhamBenh
) xn ON xn.MaPhieuKhamBenh = pk.MaPhieuKhamBenh
LEFT JOIN (
    SELECT d.MaPhieuKhamBenh,
           SUM(ct.SoLuongKe * ct.DonGiaApDung) AS TongTienThuoc
    FROM DonThuoc d
    JOIN ChiTietDonThuoc ct ON ct.MaDonThuoc = d.MaDonThuoc
    GROUP BY d.MaPhieuKhamBenh
) dt ON dt.MaPhieuKhamBenh = pk.MaPhieuKhamBenh
GROUP BY bs.MaBacSi, bs.HoTen
ORDER BY bs.MaBacSi;


-- ============================================================================
-- C. TIM KIEM LICH LAM VIEC BAC SI
-- Bo loc: khoa, ten bac si, trinh do/chuc danh, thu (2..8).
-- Tham so Python theo thu tu (8 gia tri):
-- (ma_khoa, ma_khoa, ten_bs, ten_bs, trinh_do, trinh_do, thu, thu).
-- NULL / chuoi rong bo qua bo loc; Thu dung NULL neu khong loc.
SELECT
    bs.MaBacSi,
    bs.HoTen AS TenBacSi,
    k.TenKhoa AS Khoa,
    bs.PhongKham,
    bs.TrinhDoHocVan AS ChucDanh,
    bs.GiaKham,
    lv.Thu,
    lv.GioBatDau,
    lv.GioKetThuc
FROM LichLamViecBacSi lv
JOIN BacSi bs ON bs.MaBacSi = lv.MaBacSi
JOIN Khoa k ON k.MaKhoa = bs.MaKhoa
WHERE (NULLIF(TRIM(%s), '') IS NULL OR bs.MaKhoa = %s)
  AND (NULLIF(TRIM(%s), '') IS NULL OR LOCATE(TRIM(%s), bs.HoTen) > 0)
  AND (NULLIF(TRIM(%s), '') IS NULL OR bs.TrinhDoHocVan = %s)
  AND (%s IS NULL OR lv.Thu = %s)
ORDER BY k.MaKhoa, bs.HoTen, lv.Thu, lv.GioBatDau;
