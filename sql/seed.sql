-- seed.sql - Du lieu nen cho he thong Quan ly kham benh
-- Tuong thich voi 01_schema(6).sql cua nhom (MySQL 8.0+).
-- Du lieu hoan toan gia lap, chi dung cho BTL / demo.
-- Chi nap vao CSDL moi tao va dang trong. Khong chay lai khi da co du lieu.
-- KHONG tao ban ghi o PhieuKhamBenh, XetNghiem, DonThuoc, ChiTietDonThuoc.
-- Trinh tu INSERT tuan thu khoa ngoai trong DDL.

SET NAMES utf8mb4;
USE quanlykhambenh;

START TRANSACTION;

-- 1. KHOA (4 ban ghi)
INSERT INTO Khoa (MaKhoa, TenKhoa) VALUES
  ('K001', 'Nội tổng hợp'),
  ('K002', 'Ngoại tổng hợp'),
  ('K003', 'Nhi'),
  ('K004', 'Tai Mũi Họng');

-- 2. BAC SI (8 ban ghi)
INSERT INTO BacSi (MaBacSi, MaKhoa, HoTen, GiaKham, TrinhDoHocVan, PhongKham) VALUES
  ('BS001', 'K001', 'Nguyễn Hoàng Minh', 150000, 'Thạc sĩ', 'P101'),
  ('BS002', 'K001', 'Trần Thị Thu Hà', 180000, 'Bác sĩ chuyên khoa I', 'P102'),
  ('BS003', 'K002', 'Lê Đức Thành', 200000, 'Thạc sĩ', 'P201'),
  ('BS004', 'K002', 'Phạm Quốc Huy', 190000, 'Bác sĩ chuyên khoa I', 'P202'),
  ('BS005', 'K003', 'Đỗ Thị Hạnh', 160000, 'Bác sĩ chuyên khoa I', 'P301'),
  ('BS006', 'K003', 'Vũ Văn Nam', 170000, 'Bác sĩ', 'P302'),
  ('BS007', 'K004', 'Nguyễn Thị Lan', 175000, 'Thạc sĩ', 'P401'),
  ('BS008', 'K004', 'Bùi Anh Tuấn', 165000, 'Bác sĩ chuyên khoa I', 'P402');

-- 3. LICH LAM VIEC BAC SI (48 ca, moi ca chia duoc thanh khung 30 phut)
INSERT INTO LichLamViecBacSi (MaBacSi, Thu, GioBatDau, GioKetThuc) VALUES
  ('BS001', 2, '08:00:00', '12:00:00'),
  ('BS001', 2, '13:00:00', '17:00:00'),
  ('BS001', 4, '08:00:00', '12:00:00'),
  ('BS001', 4, '13:00:00', '17:00:00'),
  ('BS001', 6, '08:00:00', '12:00:00'),
  ('BS001', 6, '13:00:00', '17:00:00'),
  ('BS002', 3, '08:00:00', '12:00:00'),
  ('BS002', 3, '13:00:00', '17:00:00'),
  ('BS002', 5, '08:00:00', '12:00:00'),
  ('BS002', 5, '13:00:00', '17:00:00'),
  ('BS002', 7, '08:00:00', '12:00:00'),
  ('BS002', 7, '13:00:00', '17:00:00'),
  ('BS003', 2, '08:00:00', '12:00:00'),
  ('BS003', 2, '13:00:00', '17:00:00'),
  ('BS003', 3, '08:00:00', '12:00:00'),
  ('BS003', 3, '13:00:00', '17:00:00'),
  ('BS003', 5, '08:00:00', '12:00:00'),
  ('BS003', 5, '13:00:00', '17:00:00'),
  ('BS004', 4, '08:00:00', '12:00:00'),
  ('BS004', 4, '13:00:00', '17:00:00'),
  ('BS004', 6, '08:00:00', '12:00:00'),
  ('BS004', 6, '13:00:00', '17:00:00'),
  ('BS004', 7, '08:00:00', '12:00:00'),
  ('BS004', 7, '13:00:00', '17:00:00'),
  ('BS005', 2, '08:00:00', '12:00:00'),
  ('BS005', 2, '13:00:00', '17:00:00'),
  ('BS005', 5, '08:00:00', '12:00:00'),
  ('BS005', 5, '13:00:00', '17:00:00'),
  ('BS005', 7, '08:00:00', '12:00:00'),
  ('BS005', 7, '13:00:00', '17:00:00'),
  ('BS006', 3, '08:00:00', '12:00:00'),
  ('BS006', 3, '13:00:00', '17:00:00'),
  ('BS006', 4, '08:00:00', '12:00:00'),
  ('BS006', 4, '13:00:00', '17:00:00'),
  ('BS006', 6, '08:00:00', '12:00:00'),
  ('BS006', 6, '13:00:00', '17:00:00'),
  ('BS007', 2, '08:00:00', '12:00:00'),
  ('BS007', 2, '13:00:00', '17:00:00'),
  ('BS007', 4, '08:00:00', '12:00:00'),
  ('BS007', 4, '13:00:00', '17:00:00'),
  ('BS007', 7, '08:00:00', '12:00:00'),
  ('BS007', 7, '13:00:00', '17:00:00'),
  ('BS008', 3, '08:00:00', '12:00:00'),
  ('BS008', 3, '13:00:00', '17:00:00'),
  ('BS008', 5, '08:00:00', '12:00:00'),
  ('BS008', 5, '13:00:00', '17:00:00'),
  ('BS008', 6, '08:00:00', '12:00:00'),
  ('BS008', 6, '13:00:00', '17:00:00');

-- 4. BENH NHAN (15 ban ghi; co trung ten va truong NULL hop le)
INSERT INTO BenhNhan (MaBenhNhan, HoTen, NgaySinh, GioiTinh, DiaChi, SoDienThoai) VALUES
  ('BN001', 'Nguyễn Văn An', '1999-05-12', 'NAM', 'Hà Nội', '0900000101'),
  ('BN002', 'Nguyễn Văn An', '1985-11-20', 'NAM', 'Bắc Ninh', '0900000102'),
  ('BN003', 'Trần Thị Mai', '2001-02-03', 'NU', 'Hà Nội', '0900000103'),
  ('BN004', 'Lê Quốc Bảo', '1993-06-17', 'NAM', 'Hưng Yên', '0900000104'),
  ('BN005', 'Phạm Thu Trang', '1987-09-21', 'NU', 'Hà Nội', '0900000105'),
  ('BN006', 'Hoàng Gia Minh', '2017-03-04', 'NAM', 'Hà Nội', '0900000106'),
  ('BN007', 'Đỗ Thanh Hà', '2012-08-09', 'NU', 'Bắc Giang', '0900000107'),
  ('BN008', 'Trần Thị Mai', '1997-12-15', 'NU', 'Hà Nội', '0900000108'),
  ('BN009', 'Bùi Thanh Tú', '1988-01-01', 'KHAC', 'Hải Phòng', '0900000109'),
  ('BN010', 'Vũ Thị Hồng', '1979-07-28', 'NU', NULL, '0900000110'),
  ('BN011', 'Ngô Đức Long', '1995-04-19', 'NAM', 'Hà Nội', NULL),
  ('BN012', 'Đặng Anh Dũng', '2003-10-08', 'NAM', 'Nam Định', '0900000112'),
  ('BN013', 'Nguyễn Thu Hương', '1962-12-05', 'NU', 'Hà Nội', '0900000113'),
  ('BN014', 'Phan Minh Anh', '2010-06-30', 'NU', 'Hà Nội', '0900000114'),
  ('BN015', 'Tạ Ngọc Lan', '1990-03-13', 'NU', NULL, NULL);

-- 5. HO SO BENH AN (15 ho so; moi benh nhan dung 1 ho so)
INSERT INTO HoSoBenhAn (MaHoSo, MaBenhNhan, NgayLap, TienSuBenh) VALUES
  ('HS001', 'BN001', '2026-10-01', 'Chưa ghi nhận bệnh nền'),
  ('HS002', 'BN002', '2026-10-01', 'Tiền sử dị ứng thời tiết'),
  ('HS003', 'BN003', '2026-10-01', 'Đã từng điều trị viêm họng'),
  ('HS004', 'BN004', '2026-10-01', 'Theo dõi sức khỏe định kỳ'),
  ('HS005', 'BN005', '2026-10-01', NULL),
  ('HS006', 'BN006', '2026-10-01', 'Chưa ghi nhận bệnh nền'),
  ('HS007', 'BN007', '2026-10-01', 'Tiền sử dị ứng thời tiết'),
  ('HS008', 'BN008', '2026-10-01', 'Đã từng điều trị viêm họng'),
  ('HS009', 'BN009', '2026-11-01', 'Theo dõi sức khỏe định kỳ'),
  ('HS010', 'BN010', '2026-11-01', NULL),
  ('HS011', 'BN011', '2026-11-01', 'Chưa ghi nhận bệnh nền'),
  ('HS012', 'BN012', '2026-11-01', 'Tiền sử dị ứng thời tiết'),
  ('HS013', 'BN013', '2026-11-01', 'Đã từng điều trị viêm họng'),
  ('HS014', 'BN014', '2026-11-01', 'Theo dõi sức khỏe định kỳ'),
  ('HS015', 'BN015', '2026-11-01', NULL);

-- 6. THUOC (12 loai; co ton kho du, it va het hang)
INSERT INTO Thuoc (MaThuoc, TenThuoc, DonGia, DonViTinh, SoLuongCoSan) VALUES
  ('T001', 'Paracetamol 500 mg', 2500, 'Viên', 180),
  ('T002', 'Vitamin C 500 mg', 3000, 'Viên', 140),
  ('T003', 'Cetirizine 10 mg', 4000, 'Viên', 80),
  ('T004', 'Natri clorid 0,9%', 15000, 'Chai', 60),
  ('T005', 'Oresol', 5000, 'Gói', 75),
  ('T006', 'Omeprazole 20 mg', 6500, 'Viên', 95),
  ('T007', 'Dung dịch súc miệng', 25000, 'Chai', 35),
  ('T008', 'Men vi sinh', 12000, 'Gói', 50),
  ('T009', 'Kem bôi ngoài da', 30000, 'Tuýp', 18),
  ('T010', 'Thuốc nhỏ mũi', 22000, 'Chai', 25),
  ('T011', 'Ibuprofen 200 mg', 3500, 'Viên', 2),
  ('T012', 'Xịt họng thảo dược', 45000, 'Chai', 0);

COMMIT;
