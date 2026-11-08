-- SQL-02 - Tim kiem benh nhan va thong ke (dung chung trong Python Tkinter)
-- Cac SELECT ben duoi dung placeholder %s nhu 03_business_logic.sql cua Duc.
-- Python goi tung SELECT rieng: cursor.execute(sql, tuple_tham_so).
-- Khong noi chuoi du lieu nguoi dung vao SQL.
-- Muon chay thu truc tiep MySQL Workbench: dung test_sql02.sql (PREPARE voi ?).
USE quanlykhambenh;

-- ==========================================
-- A. NGHIỆP VỤ TÌM KIẾM BỆNH NHÂN
-- ==========================================

-- Tham số Python theo thứ tự (6 giá trị):
-- 1, 2, 3: Từ khóa (mã bệnh nhân, họ tên hoặc số điện thoại)
-- 4: Ngày sinh (DATE hoặc NULL)
-- 5: Giới tính (NAM / NU / KHAC hoặc NULL)
-- 6: Địa chỉ (chuỗi hoặc NULL)
-- Điều kiện chuỗi rỗng cũng được xem là bỏ qua bộ lọc.
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


-- ==========================================
-- B. NGHIỆP VỤ BÁO CÁO THỐNG KÊ KHÁM BỆNH
-- ==========================================

-- Tham số Python: (thang, nam); thang 1..12, nam hop le.
-- Chỉ tính phiếu HOAN_THANH, giữ bác sĩ có 0 lượt khám.
-- Tính tiền riêng từng phiếu trước khi JOIN để không nhân đôi.
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
ORDER BY bs.MaBacSi;
