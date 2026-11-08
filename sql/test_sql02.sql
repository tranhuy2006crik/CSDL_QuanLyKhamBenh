-- test_sql02.sql - KIEM THU SQL-02 (TIM KIEM + THONG KE)
-- Tuong thich 01_schema(7).sql / 02_triggers(2).sql / 03_business_logic(2).sql.
-- File API 04_search_statistics.sql dung %s cho Python; MySQL PREPARE ben duoi dung ?.
-- Yeu cau: database quanlykhambenh MOI, da nap DDL, triggers va seed.sql.
-- CHI CHAY TREN CSDL THU NGHIEM, KHONG CHAY TREN CSDL CO DU LIEU THAT.
-- Script tu tao 5 phieu kham/du lieu lien quan va ROLLBACK sau khi kiem tra.
-- KHONG GIU LAI bat ky du lieu phat sinh hay thay doi ton kho nao sau ROLLBACK.
-- Cac truy van PREPARE duoi day duoc lay nguyen logic tu 04_search_statistics.sql.

SET NAMES utf8mb4;
USE quanlykhambenh;

-- Kiem tra nen: so phieu ban dau phai = 0 khi chi moi nap seed.sql.
SELECT COUNT(*) AS SoPhieuBanDau,
       CASE WHEN COUNT(*) = 0 THEN 'DAT' ELSE 'CAN_KIEM_TRA_CSDL_KHONG_TRONG' END AS KiemTra
FROM PhieuKhamBenh;

START TRANSACTION;

-- 1. TEST_PK901: BS001 / BN001, 2 xet nghiem, 3 loai thuoc, HOAN_THANH.
INSERT INTO PhieuKhamBenh
    (MaPhieuKhamBenh, MaBacSi, MaHoSo, NgayGioKham, ChanDoan, TrieuChung, GiaKhamApDung, TrangThaiPhieuKham)
VALUES ('TEST_PK901', 'BS001', 'HS001', '2026-10-05 08:00:00',
        'Viem hong', 'Dau hong', 150000, 'DANG_KHAM');
INSERT INTO XetNghiem
    (MaPhieuKhamBenh, STTXetNghiem, TenXetNghiem, KetQuaXetNghiem, NgayGioThucHien, DonGiaApDung)
VALUES
    ('TEST_PK901', 1, 'Cong thuc mau', 'Binh thuong', '2026-10-05 08:30:00', 50000),
    ('TEST_PK901', 2, 'Duong huyet', 'Binh thuong', '2026-10-05 08:40:00', 70000);
INSERT INTO DonThuoc (MaDonThuoc, MaPhieuKhamBenh, NgayLapDonThuoc, LoiDanChung)
VALUES ('TEST_DT901', 'TEST_PK901', '2026-10-05', 'Theo doi tai nha');
-- Gia thuoc lay dung bang Thuoc trong seed.sql, co tru ton kho.
UPDATE Thuoc SET SoLuongCoSan = SoLuongCoSan - 2 WHERE MaThuoc = 'T001' AND SoLuongCoSan >= 2;
UPDATE Thuoc SET SoLuongCoSan = SoLuongCoSan - 3 WHERE MaThuoc = 'T002' AND SoLuongCoSan >= 3;
UPDATE Thuoc SET SoLuongCoSan = SoLuongCoSan - 1 WHERE MaThuoc = 'T003' AND SoLuongCoSan >= 1;
INSERT INTO ChiTietDonThuoc (MaDonThuoc, MaThuoc, SoLuongKe, CachDung, DonGiaApDung)
SELECT 'TEST_DT901', MaThuoc, SoLuong, 'Theo chi dinh', DonGia
FROM (
    SELECT 'T001' AS MaThuoc, 2 AS SoLuong
    UNION ALL SELECT 'T002', 3
    UNION ALL SELECT 'T003', 1
) AS DS JOIN Thuoc t USING(MaThuoc);
UPDATE PhieuKhamBenh SET TrangThaiPhieuKham = 'HOAN_THANH'
WHERE MaPhieuKhamBenh = 'TEST_PK901' AND TrangThaiPhieuKham = 'DANG_KHAM';

-- 2. TEST_PK902: BS001 tai kham CUNG BN001, khong tinh thanh 2 benh nhan.
INSERT INTO PhieuKhamBenh
    (MaPhieuKhamBenh, MaBacSi, MaHoSo, NgayGioKham, ChanDoan, TrieuChung, GiaKhamApDung, TrangThaiPhieuKham)
VALUES ('TEST_PK902', 'BS001', 'HS001', '2026-10-12 09:00:00',
        'Tai kham', 'Da giam trieu chung', 150000, 'DANG_KHAM');
INSERT INTO XetNghiem
    (MaPhieuKhamBenh, STTXetNghiem, TenXetNghiem, KetQuaXetNghiem, NgayGioThucHien, DonGiaApDung)
VALUES ('TEST_PK902', 1, 'Xet nghiem kiem tra', 'Binh thuong', '2026-10-12 09:30:00', 40000);
UPDATE PhieuKhamBenh SET TrangThaiPhieuKham = 'HOAN_THANH'
WHERE MaPhieuKhamBenh = 'TEST_PK902' AND TrangThaiPhieuKham = 'DANG_KHAM';

-- 3. TEST_PK903: BS002 co phieu DANG_KHAM trong thang 10, PHAI BI LOAI.
INSERT INTO PhieuKhamBenh
    (MaPhieuKhamBenh, MaBacSi, MaHoSo, NgayGioKham, ChanDoan, TrieuChung, GiaKhamApDung, TrangThaiPhieuKham)
VALUES ('TEST_PK903', 'BS002', 'HS002', '2026-10-15 10:00:00',
        NULL, 'Met moi', 180000, 'DANG_KHAM');
INSERT INTO XetNghiem
    (MaPhieuKhamBenh, STTXetNghiem, TenXetNghiem, KetQuaXetNghiem, NgayGioThucHien, DonGiaApDung)
VALUES ('TEST_PK903', 1, 'Duong huyet', NULL, NULL, 65000);

-- 4. TEST_PK904: BS004 / BN003, 2 loai thuoc, HOAN_THANH.
INSERT INTO PhieuKhamBenh
    (MaPhieuKhamBenh, MaBacSi, MaHoSo, NgayGioKham, ChanDoan, TrieuChung, GiaKhamApDung, TrangThaiPhieuKham)
VALUES ('TEST_PK904', 'BS004', 'HS003', '2026-10-16 09:00:00',
        'Dau co', 'Dau nhuc', 190000, 'DANG_KHAM');
INSERT INTO DonThuoc (MaDonThuoc, MaPhieuKhamBenh, NgayLapDonThuoc, LoiDanChung)
VALUES ('TEST_DT904', 'TEST_PK904', '2026-10-16', 'Theo doi trieu chung');
UPDATE Thuoc SET SoLuongCoSan = SoLuongCoSan - 2 WHERE MaThuoc = 'T002' AND SoLuongCoSan >= 2;
UPDATE Thuoc SET SoLuongCoSan = SoLuongCoSan - 1 WHERE MaThuoc = 'T005' AND SoLuongCoSan >= 1;
INSERT INTO ChiTietDonThuoc (MaDonThuoc, MaThuoc, SoLuongKe, CachDung, DonGiaApDung)
SELECT 'TEST_DT904', MaThuoc, SoLuong, 'Theo chi dinh', DonGia
FROM (
    SELECT 'T002' AS MaThuoc, 2 AS SoLuong
    UNION ALL SELECT 'T005', 1
) AS DS JOIN Thuoc t USING(MaThuoc);
UPDATE PhieuKhamBenh SET TrangThaiPhieuKham = 'HOAN_THANH'
WHERE MaPhieuKhamBenh = 'TEST_PK904' AND TrangThaiPhieuKham = 'DANG_KHAM';

-- 5. TEST_PK905: BS002 co phieu HOAN_THANH o thang 11, KHONG TINH cho thang 10.
-- Ngay 03/11 la thu 3, phu hop lich BS002; HS004 da duoc lap tu 01/10.
INSERT INTO PhieuKhamBenh
    (MaPhieuKhamBenh, MaBacSi, MaHoSo, NgayGioKham, ChanDoan, TrieuChung, GiaKhamApDung, TrangThaiPhieuKham)
VALUES ('TEST_PK905', 'BS002', 'HS004', '2026-11-03 14:00:00',
        'Viem mui', 'Hat hoi', 180000, 'DANG_KHAM');
INSERT INTO XetNghiem
    (MaPhieuKhamBenh, STTXetNghiem, TenXetNghiem, KetQuaXetNghiem, NgayGioThucHien, DonGiaApDung)
VALUES ('TEST_PK905', 1, 'Cong thuc mau', 'Binh thuong', '2026-11-03 14:30:00', 70000);
INSERT INTO DonThuoc (MaDonThuoc, MaPhieuKhamBenh, NgayLapDonThuoc, LoiDanChung)
VALUES ('TEST_DT905', 'TEST_PK905', '2026-11-03', 'Theo doi trieu chung');
UPDATE Thuoc SET SoLuongCoSan = SoLuongCoSan - 2 WHERE MaThuoc = 'T001' AND SoLuongCoSan >= 2;
INSERT INTO ChiTietDonThuoc (MaDonThuoc, MaThuoc, SoLuongKe, CachDung, DonGiaApDung)
SELECT 'TEST_DT905', MaThuoc, 2, 'Theo chi dinh', DonGia FROM Thuoc WHERE MaThuoc = 'T001';
UPDATE PhieuKhamBenh SET TrangThaiPhieuKham = 'HOAN_THANH'
WHERE MaPhieuKhamBenh = 'TEST_PK905' AND TrangThaiPhieuKham = 'DANG_KHAM';

-- 6. Truy van SQL-02 dung ? trong PREPARE de chay tren MySQL Workbench.
-- Noi dung truy van tuong duong 04_search_statistics.sql (o Python thay ? bang %s).
PREPARE test_tim_benh_nhan FROM '
SELECT
    bn.MaBenhNhan,
    bn.HoTen,
    bn.NgaySinh,
    bn.GioiTinh,
    bn.SoDienThoai,
    bn.DiaChi
FROM BenhNhan bn
WHERE (
    LOCATE(TRIM(COALESCE(?, '''')), bn.MaBenhNhan) > 0
    OR LOCATE(TRIM(COALESCE(?, '''')), bn.HoTen) > 0
    OR LOCATE(TRIM(COALESCE(?, '''')), COALESCE(bn.SoDienThoai, '''')) > 0
)
AND bn.NgaySinh = COALESCE(?, bn.NgaySinh)
AND bn.GioiTinh = COALESCE(NULLIF(UPPER(TRIM(?)), ''''), bn.GioiTinh)
AND LOCATE(TRIM(COALESCE(?, '''')), COALESCE(bn.DiaChi, '''')) > 0
ORDER BY bn.HoTen, bn.NgaySinh, bn.MaBenhNhan
';

-- A1: 2 benh nhan trung ten Nguyen Van An -> BN001, BN002.
SELECT 'A1: tim trung ten: mong doi BN001, BN002' AS CaKiemThu;
SET @TuKhoa = 'Nguyễn Văn An', @NgaySinh = NULL, @GioiTinh = NULL, @DiaChi = NULL;
EXECUTE test_tim_benh_nhan USING @TuKhoa, @TuKhoa, @TuKhoa, @NgaySinh, @GioiTinh, @DiaChi;

-- A2: Tim qua so dien thoai -> BN002.
SELECT 'A2: tim SĐT: mong doi BN002' AS CaKiemThu;
SET @TuKhoa = '0900000102', @NgaySinh = NULL, @GioiTinh = NULL, @DiaChi = NULL;
EXECUTE test_tim_benh_nhan USING @TuKhoa, @TuKhoa, @TuKhoa, @NgaySinh, @GioiTinh, @DiaChi;

-- A3: Tim qua ma benh nhan -> BN001.
SELECT 'A3: tim ma: mong doi BN001' AS CaKiemThu;
SET @TuKhoa = 'BN001', @NgaySinh = NULL, @GioiTinh = NULL, @DiaChi = NULL;
EXECUTE test_tim_benh_nhan USING @TuKhoa, @TuKhoa, @TuKhoa, @NgaySinh, @GioiTinh, @DiaChi;

-- A4: Tu khoa AND ngay sinh AND gioi tinh AND dia chi -> BN001.
SELECT 'A4: 4 bo loc ket hop: mong doi BN001' AS CaKiemThu;
SET @TuKhoa = 'Nguyễn Văn An', @NgaySinh = '1999-05-12', @GioiTinh = 'NAM', @DiaChi = 'Hà Nội';
EXECUTE test_tim_benh_nhan USING @TuKhoa, @TuKhoa, @TuKhoa, @NgaySinh, @GioiTinh, @DiaChi;

-- A5: Tat ca tham so NULL -> 15 benh nhan (neu CSDL chi co seed.sql).
SELECT 'A5: bo qua bo loc: mong doi 15 benh nhan' AS CaKiemThu;
SET @TuKhoa = NULL, @NgaySinh = NULL, @GioiTinh = NULL, @DiaChi = NULL;
EXECUTE test_tim_benh_nhan USING @TuKhoa, @TuKhoa, @TuKhoa, @NgaySinh, @GioiTinh, @DiaChi;

-- A6: Tu khoa khong ton tai -> 0 dong.
SELECT 'A6: tu khoa khong khop: mong doi 0 dong' AS CaKiemThu;
SET @TuKhoa = 'KHONG_TIM_THAY_999', @NgaySinh = NULL, @GioiTinh = NULL, @DiaChi = NULL;
EXECUTE test_tim_benh_nhan USING @TuKhoa, @TuKhoa, @TuKhoa, @NgaySinh, @GioiTinh, @DiaChi;

-- A7: Ky tu % duoc tim nhu chuoi binh thuong, khong phai wildcard -> 0 dong.
SELECT 'A7: tim ky tu %: mong doi 0 dong' AS CaKiemThu;
SET @TuKhoa = '%', @NgaySinh = NULL, @GioiTinh = NULL, @DiaChi = NULL;
EXECUTE test_tim_benh_nhan USING @TuKhoa, @TuKhoa, @TuKhoa, @NgaySinh, @GioiTinh, @DiaChi;

-- A8: Ky tu _ duoc tim nhu chuoi binh thuong, khong phai wildcard -> 0 dong.
SELECT 'A8: tim ky tu _: mong doi 0 dong' AS CaKiemThu;
SET @TuKhoa = '_', @NgaySinh = NULL, @GioiTinh = NULL, @DiaChi = NULL;
EXECUTE test_tim_benh_nhan USING @TuKhoa, @TuKhoa, @TuKhoa, @NgaySinh, @GioiTinh, @DiaChi;
DEALLOCATE PREPARE test_tim_benh_nhan;

PREPARE test_thong_ke FROM '
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
    AND p.TrangThaiPhieuKham = ''HOAN_THANH''
    AND MONTH(p.NgayGioKham) = ?
    AND YEAR(p.NgayGioKham) = ?
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
';

-- B1: Thang 10/2026 -> 8 bac si; BS001 2 luot / 1 BN / 478000;
-- BS004 1 luot / 1 BN / 201000; con lai 0.
SELECT 'B1: thang 10/2026: BS001 2/478000; BS004 1/201000; 6 bac si 0' AS CaKiemThu;
SET @Thang = 10, @Nam = 2026;
EXECUTE test_thong_ke USING @Thang, @Nam;

-- B2: Thang 11/2026 -> BS002 1 luot, 255000; con lai 0.
SELECT 'B2: thang 11/2026: BS002 1/255000; 7 bac si 0' AS CaKiemThu;
SET @Thang = 11, @Nam = 2026;
EXECUTE test_thong_ke USING @Thang, @Nam;

-- B3: Thang 09/2026 -> tat ca 8 bac si co 0 luot, 0 gia tri.
SELECT 'B3: thang 09/2026: ca 8 bac si deu 0' AS CaKiemThu;
SET @Thang = 9, @Nam = 2026;
EXECUTE test_thong_ke USING @Thang, @Nam;
DEALLOCATE PREPARE test_thong_ke;

-- C1: Doi chieu doc lap 1 phieu co 2 XN + 3 loai thuoc.
-- 150000 + 50000 + 70000 + 2*2500 + 3*3000 + 1*4000 = 288000.
SELECT k.MaPhieuKhamBenh, k.TienKham, k.TienXN, k.TienThuoc,
       k.TongGiaTriThucTe, 288000 AS TongGiaTriMongDoi,
       CASE WHEN k.TongGiaTriThucTe = 288000 THEN 'DAT' ELSE 'SAI' END AS KiemTra
FROM (
    SELECT p.MaPhieuKhamBenh, p.GiaKhamApDung AS TienKham,
           (SELECT COALESCE(SUM(x.DonGiaApDung), 0)
            FROM XetNghiem x WHERE x.MaPhieuKhamBenh = p.MaPhieuKhamBenh) AS TienXN,
           (SELECT COALESCE(SUM(ct.SoLuongKe * ct.DonGiaApDung), 0)
            FROM DonThuoc d JOIN ChiTietDonThuoc ct ON ct.MaDonThuoc = d.MaDonThuoc
            WHERE d.MaPhieuKhamBenh = p.MaPhieuKhamBenh) AS TienThuoc,
           p.GiaKhamApDung
           + (SELECT COALESCE(SUM(x.DonGiaApDung), 0)
              FROM XetNghiem x WHERE x.MaPhieuKhamBenh = p.MaPhieuKhamBenh)
           + (SELECT COALESCE(SUM(ct.SoLuongKe * ct.DonGiaApDung), 0)
              FROM DonThuoc d JOIN ChiTietDonThuoc ct ON ct.MaDonThuoc = d.MaDonThuoc
              WHERE d.MaPhieuKhamBenh = p.MaPhieuKhamBenh) AS TongGiaTriThucTe
    FROM PhieuKhamBenh p WHERE p.MaPhieuKhamBenh = 'TEST_PK901'
) k;

-- C2: Dem phieu HOAN_THANH dung thang 10 theo tung bac si, doc lap voi bao cao.
SELECT b.MaBacSi,
       COUNT(p.MaPhieuKhamBenh) AS SoLuot,
       CASE WHEN b.MaBacSi = 'BS001' THEN 2
            WHEN b.MaBacSi = 'BS004' THEN 1 ELSE 0 END AS SoLuotMongDoi,
       CASE WHEN COUNT(p.MaPhieuKhamBenh) =
                 CASE WHEN b.MaBacSi = 'BS001' THEN 2
                      WHEN b.MaBacSi = 'BS004' THEN 1 ELSE 0 END
            THEN 'DAT' ELSE 'SAI' END AS KiemTra
FROM BacSi b
LEFT JOIN PhieuKhamBenh p
    ON p.MaBacSi = b.MaBacSi
   AND p.TrangThaiPhieuKham = 'HOAN_THANH'
   AND p.NgayGioKham >= '2026-10-01'
   AND p.NgayGioKham < '2026-11-01'
GROUP BY b.MaBacSi ORDER BY b.MaBacSi;

-- C3: Kiem tra so luong thuoc sau ke don (trong giao dich tam).
SELECT MaThuoc, SoLuongCoSan AS TonKhoSauKeTrongTest
FROM Thuoc WHERE MaThuoc IN ('T001','T002','T003','T005') ORDER BY MaThuoc;
-- Mong doi: T001=176, T002=135, T003=79, T005=74.

-- D1-D3: Test them/sua/xoa BENH NHAN hop le, tim kiem thay doi theo.
-- Trigger ngay sinh chap nhan 1999; khong de lai du lieu sau ROLLBACK.
INSERT INTO BenhNhan (MaBenhNhan, HoTen, NgaySinh, GioiTinh, DiaChi, SoDienThoai)
VALUES ('BN_TEST99', 'Nguyễn Văn An', '1999-05-12', 'NAM', 'Hà Nội', '0900000199');
SELECT 'D1: them benh nhan trung ten => 3 ket qua' AS CaKiemThu,
       COUNT(*) AS ThucTe, 3 AS KyVong,
       CASE WHEN COUNT(*) = 3 THEN 'DAT' ELSE 'SAI' END AS KiemTra
FROM BenhNhan WHERE HoTen = 'Nguyễn Văn An';
UPDATE BenhNhan SET HoTen = 'Bệnh nhân vừa sửa' WHERE MaBenhNhan = 'BN_TEST99';
SELECT 'D2: sua ten => ten moi tim thay' AS CaKiemThu,
       COUNT(*) AS ThucTe, 1 AS KyVong,
       CASE WHEN COUNT(*) = 1 THEN 'DAT' ELSE 'SAI' END AS KiemTra
FROM BenhNhan WHERE HoTen = 'Bệnh nhân vừa sửa';
DELETE FROM BenhNhan WHERE MaBenhNhan = 'BN_TEST99';
SELECT 'D3: xoa => ten moi khong con' AS CaKiemThu,
       COUNT(*) AS ThucTe, 0 AS KyVong,
       CASE WHEN COUNT(*) = 0 THEN 'DAT' ELSE 'SAI' END AS KiemTra
FROM BenhNhan WHERE HoTen = 'Bệnh nhân vừa sửa';

-- D4-D5: Them/xoa bac si KHONG co luot kham; bao cao phai van co dong 0.
INSERT INTO BacSi (MaBacSi, MaKhoa, HoTen, GiaKham, TrinhDoHocVan, PhongKham)
VALUES ('BS_TEST', 'K001', 'Bác sĩ kiểm thử', 130000, 'Bác sĩ', 'PTEST');
SELECT 'D4: them bac si 0 luot => 9 bac si' AS CaKiemThu,
       COUNT(*) AS ThucTe, 9 AS KyVong,
       CASE WHEN COUNT(*) = 9 THEN 'DAT' ELSE 'SAI' END AS KiemTra
FROM BacSi;
DELETE FROM BacSi WHERE MaBacSi = 'BS_TEST';
SELECT 'D5: xoa bac si 0 luot => 8 bac si' AS CaKiemThu,
       COUNT(*) AS ThucTe, 8 AS KyVong,
       CASE WHEN COUNT(*) = 8 THEN 'DAT' ELSE 'SAI' END AS KiemTra
FROM BacSi;

-- D6: Gia kham duoc sua KHI DANG_KHAM, sau do chot HOAN_THANH.
-- BS003 / HS005, ngay 20/10 la thu 3 - trung lich da co trong seed.sql.
INSERT INTO PhieuKhamBenh
    (MaPhieuKhamBenh, MaBacSi, MaHoSo, NgayGioKham, ChanDoan, TrieuChung,
     GiaKhamApDung, TrangThaiPhieuKham)
VALUES ('TEST_PK906', 'BS003', 'HS005', '2026-10-20 09:00:00',
        'Kham tong quat', 'Met moi', 200000, 'DANG_KHAM');
UPDATE PhieuKhamBenh SET GiaKhamApDung = 210000
WHERE MaPhieuKhamBenh = 'TEST_PK906' AND TrangThaiPhieuKham = 'DANG_KHAM';
SELECT 'D6a: chua hoan thanh => BS003 0 luot' AS CaKiemThu,
       COUNT(*) AS ThucTe, 0 AS KyVong,
       CASE WHEN COUNT(*) = 0 THEN 'DAT' ELSE 'SAI' END AS KiemTra
FROM PhieuKhamBenh
WHERE MaBacSi = 'BS003' AND TrangThaiPhieuKham = 'HOAN_THANH'
  AND NgayGioKham >= '2026-10-01' AND NgayGioKham < '2026-11-01';
UPDATE PhieuKhamBenh SET TrangThaiPhieuKham = 'HOAN_THANH'
WHERE MaPhieuKhamBenh = 'TEST_PK906' AND TrangThaiPhieuKham = 'DANG_KHAM';
SELECT 'D6b: chot xong => BS003 1 luot / 210000' AS CaKiemThu,
       COUNT(*) AS SoLuot, COALESCE(SUM(GiaKhamApDung), 0) AS TongTien,
       CASE WHEN COUNT(*) = 1 AND COALESCE(SUM(GiaKhamApDung), 0) = 210000
            THEN 'DAT' ELSE 'SAI' END AS KiemTra
FROM PhieuKhamBenh
WHERE MaBacSi = 'BS003' AND TrangThaiPhieuKham = 'HOAN_THANH'
  AND NgayGioKham >= '2026-10-01' AND NgayGioKham < '2026-11-01';

-- KHONG DUOC COMMIT; hoan tac toan bo 6 phieu va thay doi ton kho.
ROLLBACK;

-- C4: Sau ROLLBACK, so phieu TEST_PK9* phai bang 0.
SELECT COUNT(*) AS SoPhieuConLai,
       CASE WHEN COUNT(*) = 0 THEN 'DAT' ELSE 'SAI' END AS KiemTra
FROM PhieuKhamBenh WHERE MaPhieuKhamBenh LIKE 'TEST_PK9%';

-- C5: Ton kho ve dung gia tri ban dau trong seed.sql.
SELECT MaThuoc, SoLuongCoSan AS TonKhoSauRollback
FROM Thuoc WHERE MaThuoc IN ('T001','T002','T003','T005') ORDER BY MaThuoc;
-- Mong doi: T001=180, T002=140, T003=80, T005=75.
