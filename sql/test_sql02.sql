-- test_sql02.sql - KIEM THU TIM KIEM BENH NHAN, THONG KE, LICH BAC SI, LICH HEN.
-- Tuong thich voi bo SQL v5.3: 01_schema / 02_triggers / 03_business_logic / 04_search_statistics.
-- Truy van Python dung %s; cac PREPARE trong file nay dung ? cho MySQL Workbench.
-- STTXetNghiem la CHAR(2), nhap tay bang chuoi; CHECK chi chap nhan '01'..'99'.
-- Yeu cau: database quanlykhambenh moi, da nap DDL, triggers va seed.sql v5.3.
-- CHI CHAY TREN CSDL THU NGHIEM, KHONG CHAY TREN CSDL CO DU LIEU THAT.
-- Script tao 7 phieu kham va 1 lich hen kiem thu; ROLLBACK cac thay doi cuoi file.
-- KHONG GIU LAI du lieu phat sinh hoac thay doi ton kho sau ROLLBACK.

SET NAMES utf8mb4;
USE quanlykhambenh;

-- Kiem tra nen: so phieu ban dau phai = 0 khi chi moi nap seed.sql.
SELECT COUNT(*) AS SoPhieuBanDau,
       CASE WHEN COUNT(*) = 0 THEN 'DAT' ELSE 'CAN_KIEM_TRA_CSDL_KHONG_TRONG' END AS KiemTra
FROM PhieuKhamBenh;

START TRANSACTION;

-- 0. KIEM THU DAT LICH VA DONG BO KHI PHIEU KHAM HOAN THANH
-- Chon ngay hen sau it nhat 31 ngay, vao ngay BS001 co lich lam viec.
-- Thoi diem nay tranh qua khu va khong lam thay doi cac ca thong ke 10-11/2026.
SET @BaseHenTest = DATE_ADD(CURRENT_DATE(), INTERVAL 30 DAY);
SET @ThuBaseHenTest = IF(DAYOFWEEK(@BaseHenTest) = 1, 8, DAYOFWEEK(@BaseHenTest));
SET @NgayHenTest = (
    SELECT DATE_ADD(@BaseHenTest, INTERVAL (MOD(llv.Thu - @ThuBaseHenTest + 6, 7) + 1) DAY)
    FROM LichLamViecBacSi llv
    WHERE llv.MaBacSi = 'BS001'
    ORDER BY MOD(llv.Thu - @ThuBaseHenTest + 6, 7) + 1, llv.GioBatDau
    LIMIT 1
);
SET @GioHenTest = '08:30:00';
SET @NgayGioHenTest = TIMESTAMP(@NgayHenTest, @GioHenTest);

INSERT INTO LichHen (MaLichHen, MaBacSi, MaBenhNhan, NgayHen, GioBatDau, TrangThai)
VALUES ('LH901', 'BS001', 'BN002', @NgayHenTest, @GioHenTest, 'CHO_KHAM');

-- Tiep nhan tao phieu DANG_KHAM; lich hen van phai o CHO_KHAM.
INSERT INTO PhieuKhamBenh
    (MaPhieuKhamBenh, MaBacSi, MaHoSo, MaLichHen, NgayGioKham, ChanDoan,
     TrieuChung, GiaKhamApDung, TrangThaiPhieuKham)
VALUES ('PK907', 'BS001', 'HS002', 'LH901', @NgayGioHenTest,
        'Kiem tra dong bo lich hen', 'Tai kham', 150000, 'DANG_KHAM');
SELECT '0a: phieu DANG_KHAM -> lich van CHO_KHAM' AS CaKiemThu,
       TrangThai AS TrangThaiThucTe,
       CASE WHEN TrangThai = 'CHO_KHAM' THEN 'DAT' ELSE 'SAI' END AS KiemTra
FROM LichHen WHERE MaLichHen = 'LH901';

-- Chot phieu (6.1) va dong bo lich (6.2) trong cung transaction nhu API cua Duc.
UPDATE PhieuKhamBenh
SET TrangThaiPhieuKham = 'HOAN_THANH'
WHERE MaPhieuKhamBenh = 'PK907'
  AND TrangThaiPhieuKham = 'DANG_KHAM'
  AND ChanDoan IS NOT NULL AND TRIM(ChanDoan) <> ''
  AND NOT EXISTS (
      SELECT 1 FROM XetNghiem
      WHERE MaPhieuKhamBenh = 'PK907'
        AND (KetQuaXetNghiem IS NULL OR TRIM(KetQuaXetNghiem) = '')
  );
UPDATE LichHen lh
JOIN PhieuKhamBenh pk ON lh.MaLichHen = pk.MaLichHen
SET lh.TrangThai = 'DA_KHAM'
WHERE pk.MaPhieuKhamBenh = 'PK907'
  AND pk.TrangThaiPhieuKham = 'HOAN_THANH'
  AND lh.TrangThai = 'CHO_KHAM';
SELECT '0b: phieu HOAN_THANH -> lich DA_KHAM' AS CaKiemThu,
       TrangThai AS TrangThaiThucTe,
       CASE WHEN TrangThai = 'DA_KHAM' THEN 'DAT' ELSE 'SAI' END AS KiemTra
FROM LichHen WHERE MaLichHen = 'LH901';

-- 1. PK901: BS001 / BN001, 2 xet nghiem, 3 loai thuoc, HOAN_THANH.
INSERT INTO PhieuKhamBenh
    (MaPhieuKhamBenh, MaBacSi, MaHoSo, NgayGioKham, ChanDoan, TrieuChung, GiaKhamApDung, TrangThaiPhieuKham)
VALUES ('PK901', 'BS001', 'HS001', '2026-10-05 08:00:00',
        'Viem hong', 'Dau hong', 150000, 'DANG_KHAM');
INSERT INTO XetNghiem
    (MaPhieuKhamBenh, STTXetNghiem, TenXetNghiem, KetQuaXetNghiem, NgayGioThucHien, DonGiaApDung)
VALUES
    ('PK901', '01', 'Cong thuc mau', 'Binh thuong', '2026-10-05 08:30:00', 50000),
    ('PK901', '02', 'Duong huyet', 'Binh thuong', '2026-10-05 08:40:00', 70000);
INSERT INTO DonThuoc (MaDonThuoc, MaPhieuKhamBenh, NgayLapDonThuoc, LoiDanChung)
VALUES ('DT901', 'PK901', '2026-10-05', 'Theo doi tai nha');
-- Gia thuoc lay dung bang Thuoc trong seed.sql, co tru ton kho.
UPDATE Thuoc SET SoLuongCoSan = SoLuongCoSan - 2 WHERE MaThuoc = 'T001' AND SoLuongCoSan >= 2;
UPDATE Thuoc SET SoLuongCoSan = SoLuongCoSan - 3 WHERE MaThuoc = 'T002' AND SoLuongCoSan >= 3;
UPDATE Thuoc SET SoLuongCoSan = SoLuongCoSan - 1 WHERE MaThuoc = 'T003' AND SoLuongCoSan >= 1;
INSERT INTO ChiTietDonThuoc (MaDonThuoc, MaThuoc, SoLuongKe, CachDung, DonGiaApDung)
SELECT 'DT901', MaThuoc, SoLuong, 'Theo chi dinh', DonGia
FROM (
    SELECT 'T001' AS MaThuoc, 2 AS SoLuong
    UNION ALL SELECT 'T002', 3
    UNION ALL SELECT 'T003', 1
) AS DS JOIN Thuoc t USING(MaThuoc);
UPDATE PhieuKhamBenh SET TrangThaiPhieuKham = 'HOAN_THANH'
WHERE MaPhieuKhamBenh = 'PK901' AND TrangThaiPhieuKham = 'DANG_KHAM';

-- 2. PK902: BS001 tai kham CUNG BN001, khong tinh thanh 2 benh nhan.
INSERT INTO PhieuKhamBenh
    (MaPhieuKhamBenh, MaBacSi, MaHoSo, NgayGioKham, ChanDoan, TrieuChung, GiaKhamApDung, TrangThaiPhieuKham)
VALUES ('PK902', 'BS001', 'HS001', '2026-10-12 09:00:00',
        'Tai kham', 'Da giam trieu chung', 150000, 'DANG_KHAM');
INSERT INTO XetNghiem
    (MaPhieuKhamBenh, STTXetNghiem, TenXetNghiem, KetQuaXetNghiem, NgayGioThucHien, DonGiaApDung)
VALUES ('PK902', '01', 'Xet nghiem kiem tra', 'Binh thuong', '2026-10-12 09:30:00', 40000);
UPDATE PhieuKhamBenh SET TrangThaiPhieuKham = 'HOAN_THANH'
WHERE MaPhieuKhamBenh = 'PK902' AND TrangThaiPhieuKham = 'DANG_KHAM';

-- 3. PK903: BS002 co phieu DANG_KHAM trong thang 10, PHAI BI LOAI.
INSERT INTO PhieuKhamBenh
    (MaPhieuKhamBenh, MaBacSi, MaHoSo, NgayGioKham, ChanDoan, TrieuChung, GiaKhamApDung, TrangThaiPhieuKham)
VALUES ('PK903', 'BS002', 'HS002', '2026-10-15 10:00:00',
        NULL, 'Met moi', 180000, 'DANG_KHAM');
INSERT INTO XetNghiem
    (MaPhieuKhamBenh, STTXetNghiem, TenXetNghiem, KetQuaXetNghiem, NgayGioThucHien, DonGiaApDung)
VALUES ('PK903', '01', 'Duong huyet', NULL, NULL, 65000);

-- 4. PK904: BS004 / BN003, 2 loai thuoc, HOAN_THANH.
INSERT INTO PhieuKhamBenh
    (MaPhieuKhamBenh, MaBacSi, MaHoSo, NgayGioKham, ChanDoan, TrieuChung, GiaKhamApDung, TrangThaiPhieuKham)
VALUES ('PK904', 'BS004', 'HS003', '2026-10-16 09:00:00',
        'Dau co', 'Dau nhuc', 190000, 'DANG_KHAM');
INSERT INTO DonThuoc (MaDonThuoc, MaPhieuKhamBenh, NgayLapDonThuoc, LoiDanChung)
VALUES ('DT904', 'PK904', '2026-10-16', 'Theo doi trieu chung');
UPDATE Thuoc SET SoLuongCoSan = SoLuongCoSan - 2 WHERE MaThuoc = 'T002' AND SoLuongCoSan >= 2;
UPDATE Thuoc SET SoLuongCoSan = SoLuongCoSan - 1 WHERE MaThuoc = 'T005' AND SoLuongCoSan >= 1;
INSERT INTO ChiTietDonThuoc (MaDonThuoc, MaThuoc, SoLuongKe, CachDung, DonGiaApDung)
SELECT 'DT904', MaThuoc, SoLuong, 'Theo chi dinh', DonGia
FROM (
    SELECT 'T002' AS MaThuoc, 2 AS SoLuong
    UNION ALL SELECT 'T005', 1
) AS DS JOIN Thuoc t USING(MaThuoc);
UPDATE PhieuKhamBenh SET TrangThaiPhieuKham = 'HOAN_THANH'
WHERE MaPhieuKhamBenh = 'PK904' AND TrangThaiPhieuKham = 'DANG_KHAM';

-- 5. PK905: BS002 co phieu HOAN_THANH o thang 11, KHONG TINH cho thang 10.
-- Ngay 03/11 la thu 3, phu hop lich BS002; HS004 da duoc lap tu 01/10.
INSERT INTO PhieuKhamBenh
    (MaPhieuKhamBenh, MaBacSi, MaHoSo, NgayGioKham, ChanDoan, TrieuChung, GiaKhamApDung, TrangThaiPhieuKham)
VALUES ('PK905', 'BS002', 'HS004', '2026-11-03 14:00:00',
        'Viem mui', 'Hat hoi', 180000, 'DANG_KHAM');
INSERT INTO XetNghiem
    (MaPhieuKhamBenh, STTXetNghiem, TenXetNghiem, KetQuaXetNghiem, NgayGioThucHien, DonGiaApDung)
VALUES ('PK905', '01', 'Cong thuc mau', 'Binh thuong', '2026-11-03 14:30:00', 70000);
INSERT INTO DonThuoc (MaDonThuoc, MaPhieuKhamBenh, NgayLapDonThuoc, LoiDanChung)
VALUES ('DT905', 'PK905', '2026-11-03', 'Theo doi trieu chung');
UPDATE Thuoc SET SoLuongCoSan = SoLuongCoSan - 2 WHERE MaThuoc = 'T001' AND SoLuongCoSan >= 2;
INSERT INTO ChiTietDonThuoc (MaDonThuoc, MaThuoc, SoLuongKe, CachDung, DonGiaApDung)
SELECT 'DT905', MaThuoc, 2, 'Theo chi dinh', DonGia FROM Thuoc WHERE MaThuoc = 'T001';
UPDATE PhieuKhamBenh SET TrangThaiPhieuKham = 'HOAN_THANH'
WHERE MaPhieuKhamBenh = 'PK905' AND TrangThaiPhieuKham = 'DANG_KHAM';

-- 6. Truy van SQL-02 dung ? trong PREPARE de chay tren MySQL Workbench.
-- Noi dung truy van tuong duong 04_search_statistics.sql (o Python thay ? bang %s).
PREPARE test_tim_benh_nhan FROM '
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
           GROUP_CONCAT(DISTINCT ds.TenKhoa ORDER BY ds.TenKhoa SEPARATOR '', '') AS DanhSachKhoa
    FROM (
        SELECT lh.MaBenhNhan, k.TenKhoa
        FROM LichHen lh
        JOIN BacSi bs ON bs.MaBacSi = lh.MaBacSi
        JOIN Khoa k ON k.MaKhoa = bs.MaKhoa
        WHERE lh.TrangThai <> ''DA_HUY''

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
-- Cot Khoa duoc hien kem; BN001 va BN002 deu thuoc K001 tu lich hen mau.
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
    FROM PhieuKhamBenh p WHERE p.MaPhieuKhamBenh = 'PK901'
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
VALUES ('BN999', 'Nguyễn Văn An', '1999-05-12', 'NAM', 'Hà Nội', '0900000199');
SELECT 'D1: them benh nhan trung ten => 3 ket qua' AS CaKiemThu,
       COUNT(*) AS ThucTe, 3 AS KyVong,
       CASE WHEN COUNT(*) = 3 THEN 'DAT' ELSE 'SAI' END AS KiemTra
FROM BenhNhan WHERE HoTen = 'Nguyễn Văn An';
UPDATE BenhNhan SET HoTen = 'Bệnh nhân vừa sửa' WHERE MaBenhNhan = 'BN999';
SELECT 'D2: sua ten => ten moi tim thay' AS CaKiemThu,
       COUNT(*) AS ThucTe, 1 AS KyVong,
       CASE WHEN COUNT(*) = 1 THEN 'DAT' ELSE 'SAI' END AS KiemTra
FROM BenhNhan WHERE HoTen = 'Bệnh nhân vừa sửa';
DELETE FROM BenhNhan WHERE MaBenhNhan = 'BN999';
SELECT 'D3: xoa => ten moi khong con' AS CaKiemThu,
       COUNT(*) AS ThucTe, 0 AS KyVong,
       CASE WHEN COUNT(*) = 0 THEN 'DAT' ELSE 'SAI' END AS KiemTra
FROM BenhNhan WHERE HoTen = 'Bệnh nhân vừa sửa';

-- D4-D5: Them/xoa bac si KHONG co luot kham; bao cao phai van co dong 0.
INSERT INTO BacSi (MaBacSi, MaKhoa, HoTen, GiaKham, TrinhDoHocVan, PhongKham)
VALUES ('BS999', 'K001', 'Bác sĩ kiểm thử', 130000, 'Bác sĩ', 'PTEST');
SELECT 'D4: them bac si 0 luot => 9 bac si' AS CaKiemThu,
       COUNT(*) AS ThucTe, 9 AS KyVong,
       CASE WHEN COUNT(*) = 9 THEN 'DAT' ELSE 'SAI' END AS KiemTra
FROM BacSi;
DELETE FROM BacSi WHERE MaBacSi = 'BS999';
SELECT 'D5: xoa bac si 0 luot => 8 bac si' AS CaKiemThu,
       COUNT(*) AS ThucTe, 8 AS KyVong,
       CASE WHEN COUNT(*) = 8 THEN 'DAT' ELSE 'SAI' END AS KiemTra
FROM BacSi;

-- D6: Gia kham duoc sua KHI DANG_KHAM, sau do chot HOAN_THANH.
-- BS003 / HS005, ngay 20/10 la thu 3 - trung lich da co trong seed.sql.
INSERT INTO PhieuKhamBenh
    (MaPhieuKhamBenh, MaBacSi, MaHoSo, NgayGioKham, ChanDoan, TrieuChung,
     GiaKhamApDung, TrangThaiPhieuKham)
VALUES ('PK906', 'BS003', 'HS005', '2026-10-20 09:00:00',
        'Kham tong quat', 'Met moi', 200000, 'DANG_KHAM');
UPDATE PhieuKhamBenh SET GiaKhamApDung = 210000
WHERE MaPhieuKhamBenh = 'PK906' AND TrangThaiPhieuKham = 'DANG_KHAM';
SELECT 'D6a: chua hoan thanh => BS003 0 luot' AS CaKiemThu,
       COUNT(*) AS ThucTe, 0 AS KyVong,
       CASE WHEN COUNT(*) = 0 THEN 'DAT' ELSE 'SAI' END AS KiemTra
FROM PhieuKhamBenh
WHERE MaBacSi = 'BS003' AND TrangThaiPhieuKham = 'HOAN_THANH'
  AND NgayGioKham >= '2026-10-01' AND NgayGioKham < '2026-11-01';
UPDATE PhieuKhamBenh SET TrangThaiPhieuKham = 'HOAN_THANH'
WHERE MaPhieuKhamBenh = 'PK906' AND TrangThaiPhieuKham = 'DANG_KHAM';
SELECT 'D6b: chot xong => BS003 1 luot / 210000' AS CaKiemThu,
       COUNT(*) AS SoLuot, COALESCE(SUM(GiaKhamApDung), 0) AS TongTien,
       CASE WHEN COUNT(*) = 1 AND COALESCE(SUM(GiaKhamApDung), 0) = 210000
            THEN 'DAT' ELSE 'SAI' END AS KiemTra
FROM PhieuKhamBenh
WHERE MaBacSi = 'BS003' AND TrangThaiPhieuKham = 'HOAN_THANH'
  AND NgayGioKham >= '2026-10-01' AND NgayGioKham < '2026-11-01';


-- E. KIỂM THỬ TÌM KIẾM LỊCH LÀM VIỆC BÁC SĨ
-- Số ca kỳ vọng dựa trên seed.sql (8 bác sĩ, mỗi bác sĩ 6 ca).
PREPARE test_lich_bac_si FROM '
SELECT COUNT(*) AS SoCaThucTe, ? AS SoCaKyVong,
       CASE WHEN COUNT(*) = ? THEN ''DAT'' ELSE ''SAI'' END AS KiemTra
FROM LichLamViecBacSi lv
JOIN BacSi bs ON bs.MaBacSi = lv.MaBacSi
JOIN Khoa k ON k.MaKhoa = bs.MaKhoa
WHERE (NULLIF(TRIM(?), '''') IS NULL OR bs.MaKhoa = ?)
  AND (NULLIF(TRIM(?), '''') IS NULL OR LOCATE(TRIM(?), bs.HoTen) > 0)
  AND (NULLIF(TRIM(?), '''') IS NULL OR bs.TrinhDoHocVan = ?)
  AND (? IS NULL OR lv.Thu = ?)
';

-- E1: Không lọc -> 48 ca.
SET @KyVong = 48, @Khoa = NULL, @Ten = NULL, @ChucDanh = NULL, @Thu = NULL;
EXECUTE test_lich_bac_si USING @KyVong, @KyVong, @Khoa, @Khoa, @Ten, @Ten, @ChucDanh, @ChucDanh, @Thu, @Thu;

-- E2: Khoa K001 -> 12 ca.
SET @KyVong = 12, @Khoa = 'K001', @Ten = NULL, @ChucDanh = NULL, @Thu = NULL;
EXECUTE test_lich_bac_si USING @KyVong, @KyVong, @Khoa, @Khoa, @Ten, @Ten, @ChucDanh, @ChucDanh, @Thu, @Thu;

-- E3: Tên Nguyễn Hoàng Minh -> 6 ca.
SET @KyVong = 6, @Khoa = NULL, @Ten = 'Nguyễn Hoàng Minh', @ChucDanh = NULL, @Thu = NULL;
EXECUTE test_lich_bac_si USING @KyVong, @KyVong, @Khoa, @Khoa, @Ten, @Ten, @ChucDanh, @ChucDanh, @Thu, @Thu;

-- E4: Chức danh Thạc sĩ -> 18 ca.
SET @KyVong = 18, @Khoa = NULL, @Ten = NULL, @ChucDanh = 'Thạc sĩ', @Thu = NULL;
EXECUTE test_lich_bac_si USING @KyVong, @KyVong, @Khoa, @Khoa, @Ten, @Ten, @ChucDanh, @ChucDanh, @Thu, @Thu;

-- E5: Thứ 2 -> 8 ca.
SET @KyVong = 8, @Khoa = NULL, @Ten = NULL, @ChucDanh = NULL, @Thu = 2;
EXECUTE test_lich_bac_si USING @KyVong, @KyVong, @Khoa, @Khoa, @Ten, @Ten, @ChucDanh, @ChucDanh, @Thu, @Thu;

-- E6: K001 + Nguyễn Hoàng Minh + Thạc sĩ + Thứ 2 -> 2 ca.
SET @KyVong = 2, @Khoa = 'K001', @Ten = 'Nguyễn Hoàng Minh', @ChucDanh = 'Thạc sĩ', @Thu = 2;
EXECUTE test_lich_bac_si USING @KyVong, @KyVong, @Khoa, @Khoa, @Ten, @Ten, @ChucDanh, @ChucDanh, @Thu, @Thu;

-- E7: Tên không tồn tại -> 0 ca.
SET @KyVong = 0, @Khoa = NULL, @Ten = 'Khong co bac si', @ChucDanh = NULL, @Thu = NULL;
EXECUTE test_lich_bac_si USING @KyVong, @KyVong, @Khoa, @Khoa, @Ten, @Ten, @ChucDanh, @ChucDanh, @Thu, @Thu;

-- E8: Bộ lọc chuỗi rỗng -> 48 ca.
SET @KyVong = 48, @Khoa = '', @Ten = '  ', @ChucDanh = '', @Thu = NULL;
EXECUTE test_lich_bac_si USING @KyVong, @KyVong, @Khoa, @Khoa, @Ten, @Ten, @ChucDanh, @ChucDanh, @Thu, @Thu;

-- E9: Tìm tên chứa % hoặc _ (ký tự theo nghĩa đen) -> mỗi trường hợp 0 ca trên seed.
SET @KyVong = 0, @Khoa = NULL, @Ten = '%', @ChucDanh = NULL, @Thu = NULL;
EXECUTE test_lich_bac_si USING @KyVong, @KyVong, @Khoa, @Khoa, @Ten, @Ten, @ChucDanh, @ChucDanh, @Thu, @Thu;
SET @Ten = '_';
EXECUTE test_lich_bac_si USING @KyVong, @KyVong, @Khoa, @Khoa, @Ten, @Ten, @ChucDanh, @ChucDanh, @Thu, @Thu;

-- E10: Thêm dữ liệu chứa ký tự % và _ thật để kiểm tra tìm chính xác.
INSERT INTO BacSi (MaBacSi, MaKhoa, HoTen, GiaKham, TrinhDoHocVan, PhongKham)
VALUES ('BS998', 'K001', 'Bác sĩ %_ thử', 150000, 'Thạc sĩ', 'P998');
INSERT INTO LichLamViecBacSi (MaBacSi, Thu, GioBatDau, GioKetThuc)
VALUES ('BS998', 2, '08:00:00', '12:00:00');
SET @KyVong = 1, @Ten = '%';
EXECUTE test_lich_bac_si USING @KyVong, @KyVong, @Khoa, @Khoa, @Ten, @Ten, @ChucDanh, @ChucDanh, @Thu, @Thu;
SET @Ten = '_';
EXECUTE test_lich_bac_si USING @KyVong, @KyVong, @Khoa, @Khoa, @Ten, @Ten, @ChucDanh, @ChucDanh, @Thu, @Thu;
DEALLOCATE PREPARE test_lich_bac_si;

-- KHONG DUOC COMMIT; rollback 7 phieu, LH901 va cac thay doi ton kho/trang thai hen.
ROLLBACK;

-- C4: Sau ROLLBACK, so phieu PK9* phai bang 0.
SELECT COUNT(*) AS SoPhieuConLai,
       CASE WHEN COUNT(*) = 0 THEN 'DAT' ELSE 'SAI' END AS KiemTra
FROM PhieuKhamBenh WHERE MaPhieuKhamBenh LIKE 'PK9%';

-- 0c: Hai lich hen seed van CHO_KHAM; lich LH901 trong test bi hoan tac.
SELECT '0c-a: lich seed van CHO_KHAM' AS CaKiemThu,
       COUNT(*) AS SoLichChoThucTe,
       CASE WHEN COUNT(*) = 2 THEN 'DAT' ELSE 'SAI' END AS KiemTra
FROM LichHen
WHERE MaLichHen IN ('LH001', 'LH002') AND TrangThai = 'CHO_KHAM';
SELECT '0c-b: LH901 duoc hoan tac' AS CaKiemThu,
       COUNT(*) AS SoBanGhiThucTe,
       CASE WHEN COUNT(*) = 0 THEN 'DAT' ELSE 'SAI' END AS KiemTra
FROM LichHen WHERE MaLichHen = 'LH901';

-- C5: Ton kho ve dung gia tri ban dau trong seed.sql.
SELECT MaThuoc, SoLuongCoSan AS TonKhoSauRollback
FROM Thuoc WHERE MaThuoc IN ('T001','T002','T003','T005') ORDER BY MaThuoc;
-- Mong doi: T001=180, T002=140, T003=80, T005=75.
