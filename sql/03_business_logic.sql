-- 03_business_logic.sql: Bộ SQL API cho Python Tkinter (Tham số định dạng %s)
-- 1. Tất cả tham số động dùng định dạng %s chuẩn cho mysql-connector-python / pymysql.
-- 2. Với các thao tác giao dịch nhiều bước, bắt buộc chạy trong cùng một transaction và rollback khi lỗi.

USE quanlykhambenh;

-- ============================================================================
-- 0. NGHIỆP VỤ LỊCH HẸN & TIẾP NHẬN PHIẾU KHÁM
-- ============================================================================

-- 0.1 Đặt lịch hẹn mới
-- Tham số Python tuple: (ma_lich_hen, ma_bac_si, ma_benh_nhan, ngay_hen, gio_bat_dau)
INSERT INTO LichHen (MaLichHen, MaBacSi, MaBenhNhan, NgayHen, GioBatDau, TrangThai)
VALUES (%s, %s, %s, %s, %s, 'CHO_KHAM');

-- 0.2 Hủy lịch hẹn đang chờ khám (Chỉ hủy được trước giờ hẹn và chưa liên kết phiếu khám)
-- Tham số Python tuple: (ma_lich_hen,)
UPDATE LichHen
SET TrangThai = 'DA_HUY'
WHERE MaLichHen = %s
  AND TrangThai = 'CHO_KHAM'
  AND TIMESTAMP(NgayHen, GioBatDau) > NOW()
  AND NOT EXISTS (
      SELECT 1 FROM PhieuKhamBenh pk WHERE pk.MaLichHen = LichHen.MaLichHen
  );

-- 0.3 Tra cứu danh sách lịch hẹn theo ngày
-- Tham số Python tuple: (ngay_hen,)
SELECT 
    lh.MaLichHen,
    lh.NgayHen,
    lh.GioBatDau,
    lh.TrangThai,
    bn.MaBenhNhan,
    bn.HoTen AS TenBenhNhan,
    bn.DiaChi,
    bn.SoDienThoai,
    hs.MaHoSo,
    bs.MaBacSi,
    bs.HoTen AS TenBacSi,
    k.TenKhoa,
    bs.PhongKham,
    pk.MaPhieuKhamBenh,
    pk.TrangThaiPhieuKham
FROM LichHen lh
JOIN BenhNhan bn ON lh.MaBenhNhan = bn.MaBenhNhan
LEFT JOIN HoSoBenhAn hs ON bn.MaBenhNhan = hs.MaBenhNhan
JOIN BacSi bs ON lh.MaBacSi = bs.MaBacSi
JOIN Khoa k ON bs.MaKhoa = k.MaKhoa
LEFT JOIN PhieuKhamBenh pk ON lh.MaLichHen = pk.MaLichHen
WHERE lh.NgayHen = %s
ORDER BY lh.GioBatDau ASC, lh.MaLichHen ASC;

-- 0.4 Tiếp nhận lịch hẹn -> Tạo hồ sơ (nếu chưa có) -> Lập phiếu khám (Transaction)
-- PYTHON: START TRANSACTION; thực hiện 0.4a, kiểm tra có lịch và TrangThai = 'CHO_KHAM'.
-- Chỉ chạy 0.4b khi MaHoSo trả về là NULL; tạo mã hồ sơ CHAR(5) không trùng.
-- Dùng MaHoSo cũ hoặc vừa tạo để chạy 0.4c; yêu cầu 0.4c rowcount = 1.
-- Bất kỳ bước nào lỗi -> ROLLBACK; chỉ COMMIT khi hoàn tất tất cả bước.
-- 0.4a: Khóa lịch hẹn và kiểm tra hồ sơ bệnh án của bệnh nhân (Tham số: (ma_lich_hen,))
SELECT 
    lh.MaLichHen,
    lh.MaBacSi,
    lh.MaBenhNhan,
    lh.TrangThai,
    hs.MaHoSo
FROM LichHen lh
LEFT JOIN HoSoBenhAn hs ON lh.MaBenhNhan = hs.MaBenhNhan
WHERE lh.MaLichHen = %s
FOR UPDATE;

-- 0.4b: Tạo mới hồ sơ bệnh án nếu bệnh nhân chưa có hồ sơ (Tham số: (ma_ho_so_moi, ma_benh_nhan))
INSERT INTO HoSoBenhAn (MaHoSo, MaBenhNhan, NgayLap, TienSuBenh)
VALUES (%s, %s, CURRENT_DATE(), NULL);

-- 0.4c: Lập phiếu khám DANG_KHAM gắn với mã lịch hẹn
-- Tham số Python tuple: (ma_phieu, ma_bac_si, ma_ho_so, ma_lich_hen, trieu_chung, ma_bac_si)
INSERT INTO PhieuKhamBenh (
    MaPhieuKhamBenh, MaBacSi, MaHoSo, MaLichHen, NgayGioKham, TrieuChung, GiaKhamApDung, TrangThaiPhieuKham
)
SELECT %s, %s, %s, %s, NOW(), %s, bs.GiaKham, 'DANG_KHAM'
FROM BacSi bs
WHERE bs.MaBacSi = %s;

-- 0.5 Lập phiếu khám trực tiếp (Nếu bệnh nhân chưa có hồ sơ thì chạy bước 0.4b trước)
-- PYTHON: bước tạo hồ sơ (nếu cần) và 0.5 phải cùng transaction; kiểm tra rowcount = 1.
-- Tham số Python tuple: (ma_phieu, ma_bac_si, ma_ho_so, trieu_chung, ma_bac_si)
INSERT INTO PhieuKhamBenh (
    MaPhieuKhamBenh, MaBacSi, MaHoSo, MaLichHen, NgayGioKham, TrieuChung, GiaKhamApDung, TrangThaiPhieuKham
)
SELECT %s, %s, %s, NULL, NOW(), %s, bs.GiaKham, 'DANG_KHAM'
FROM BacSi bs
WHERE bs.MaBacSi = %s;

-- 0.6 Cập nhật triệu chứng và chẩn đoán khi đang khám
-- Tham số Python tuple: (trieu_chung, chan_doan, ma_phieu)
UPDATE PhieuKhamBenh
SET TrieuChung = %s, ChanDoan = %s
WHERE MaPhieuKhamBenh = %s
  AND TrangThaiPhieuKham = 'DANG_KHAM';


-- ============================================================================
-- 1. NGHIỆP VỤ XÉT NGHIỆM (Chỉ thực thi khi phiếu DANG_KHAM, STT từ '01'..'99')
-- ============================================================================

-- 1.1 Thêm chỉ định xét nghiệm
-- Tham số Python tuple: (ma_phieu, stt, ten_xn, don_gia, ma_phieu)
INSERT INTO XetNghiem (MaPhieuKhamBenh, STTXetNghiem, TenXetNghiem, KetQuaXetNghiem, NgayGioThucHien, DonGiaApDung)
SELECT %s, %s, %s, NULL, NULL, %s
FROM DUAL WHERE (SELECT TrangThaiPhieuKham FROM PhieuKhamBenh WHERE MaPhieuKhamBenh = %s) = 'DANG_KHAM';

-- 1.2 Sửa chỉ định xét nghiệm
-- Tham số Python tuple: (ten_xn_moi, don_gia_moi, ma_phieu, stt, ma_phieu)
UPDATE XetNghiem 
SET TenXetNghiem = %s, DonGiaApDung = %s
WHERE MaPhieuKhamBenh = %s AND STTXetNghiem = %s
  AND (SELECT TrangThaiPhieuKham FROM PhieuKhamBenh WHERE MaPhieuKhamBenh = %s) = 'DANG_KHAM';

-- 1.3 Nhập / Cập nhật kết quả xét nghiệm
-- Tham số Python tuple: (ket_qua, ngay_gio_thuc_hien, ma_phieu, stt, ma_phieu)
UPDATE XetNghiem 
SET KetQuaXetNghiem = %s, NgayGioThucHien = %s
WHERE MaPhieuKhamBenh = %s AND STTXetNghiem = %s
  AND (SELECT TrangThaiPhieuKham FROM PhieuKhamBenh WHERE MaPhieuKhamBenh = %s) = 'DANG_KHAM';

-- 1.4 Xóa chỉ định xét nghiệm
-- Tham số Python tuple: (ma_phieu, stt, ma_phieu)
DELETE FROM XetNghiem 
WHERE MaPhieuKhamBenh = %s AND STTXetNghiem = %s
  AND (SELECT TrangThaiPhieuKham FROM PhieuKhamBenh WHERE MaPhieuKhamBenh = %s) = 'DANG_KHAM';


-- ============================================================================
-- 2. NGHIỆP VỤ KÊ ĐƠN THUỐC MỚI & TRỪ TỒN KHO AN TOÀN (Transaction)
-- ============================================================================

-- 2.0 Khóa phiếu và kiểm tra trạng thái (Tham số: (ma_phieu,))
SELECT TrangThaiPhieuKham FROM PhieuKhamBenh
WHERE MaPhieuKhamBenh = %s FOR UPDATE;

-- 2.1 Tạo vỏ đơn thuốc (Tham số: (ma_don, ma_phieu, loi_dan, ma_phieu))
INSERT INTO DonThuoc (MaDonThuoc, MaPhieuKhamBenh, NgayLapDonThuoc, LoiDanChung)
SELECT %s, %s, CURRENT_DATE(), %s
FROM DUAL WHERE (SELECT TrangThaiPhieuKham FROM PhieuKhamBenh WHERE MaPhieuKhamBenh = %s) = 'DANG_KHAM';

-- 2.2 Trừ tồn kho an toàn (Tham số: (so_luong_ke, ma_thuoc, so_luong_ke))
UPDATE Thuoc 
SET SoLuongCoSan = SoLuongCoSan - %s 
WHERE MaThuoc = %s AND SoLuongCoSan >= %s;

-- 2.3 Thêm chi tiết đơn thuốc (Tham số: (ma_don, ma_thuoc, so_luong_ke, cach_dung, ma_thuoc))
INSERT INTO ChiTietDonThuoc (MaDonThuoc, MaThuoc, SoLuongKe, CachDung, DonGiaApDung)
SELECT %s, %s, %s, %s, DonGia
FROM Thuoc WHERE MaThuoc = %s;

-- 2.4 Kiểm tra đủ chi tiết trước khi COMMIT (Tham số: (ma_don,))
SELECT COUNT(*) AS SoDongThuoc FROM ChiTietDonThuoc WHERE MaDonThuoc = %s;


-- ============================================================================
-- 3. NGHIỆP VỤ SỬA SỐ LƯỢNG THUỐC TRONG ĐƠN (Transaction)
-- ============================================================================

-- 3.0 Khóa bản ghi thuốc trong đơn và đọc số lượng cũ trực tiếp từ DB (Tham số: (ma_don, ma_thuoc))
SELECT ct.SoLuongKe, ct.CachDung, p.TrangThaiPhieuKham
FROM ChiTietDonThuoc ct
JOIN DonThuoc d ON ct.MaDonThuoc = d.MaDonThuoc
JOIN PhieuKhamBenh p ON d.MaPhieuKhamBenh = p.MaPhieuKhamBenh
WHERE ct.MaDonThuoc = %s AND ct.MaThuoc = %s
FOR UPDATE;

-- Kịch bản A: Tăng số lượng thuốc (delta = so_luong_moi - so_luong_cu > 0)
-- 3.A1: Trừ thêm tồn kho (Tham số: (delta, ma_thuoc, delta))
UPDATE Thuoc SET SoLuongCoSan = SoLuongCoSan - %s WHERE MaThuoc = %s AND SoLuongCoSan >= %s;
-- 3.A2: Cập nhật chi tiết đơn (Tham số: (so_luong_moi, cach_dung_moi, ma_don, ma_thuoc, so_luong_cu))
UPDATE ChiTietDonThuoc ct
JOIN DonThuoc d ON ct.MaDonThuoc = d.MaDonThuoc
JOIN PhieuKhamBenh p ON d.MaPhieuKhamBenh = p.MaPhieuKhamBenh
SET ct.SoLuongKe = %s, ct.CachDung = %s
WHERE ct.MaDonThuoc = %s AND ct.MaThuoc = %s AND p.TrangThaiPhieuKham = 'DANG_KHAM'
  AND ct.SoLuongKe = %s;

-- Kịch bản B: Giảm số lượng thuốc (delta = so_luong_cu - so_luong_moi > 0)
-- 3.B1: Hoàn lại phần dư tồn kho (Tham số: (delta, ma_thuoc))
UPDATE Thuoc SET SoLuongCoSan = SoLuongCoSan + %s WHERE MaThuoc = %s;
-- 3.B2: Cập nhật chi tiết đơn (Tham số: (so_luong_moi, cach_dung_moi, ma_don, ma_thuoc, so_luong_cu))
UPDATE ChiTietDonThuoc ct
JOIN DonThuoc d ON ct.MaDonThuoc = d.MaDonThuoc
JOIN PhieuKhamBenh p ON d.MaPhieuKhamBenh = p.MaPhieuKhamBenh
SET ct.SoLuongKe = %s, ct.CachDung = %s
WHERE ct.MaDonThuoc = %s AND ct.MaThuoc = %s AND p.TrangThaiPhieuKham = 'DANG_KHAM'
  AND ct.SoLuongKe = %s;


-- ============================================================================
-- 4. XÓA ĐƠN THUỐC & HOÀN TỒN KHO (Transaction)
-- ============================================================================

-- 4.0 Kiểm tra trạng thái và khóa phiếu/đơn (Tham số: (ma_don,), (ma_don,))
SELECT p.TrangThaiPhieuKham
FROM DonThuoc d
JOIN PhieuKhamBenh p ON d.MaPhieuKhamBenh = p.MaPhieuKhamBenh
WHERE d.MaDonThuoc = %s
FOR UPDATE;

SELECT MaThuoc FROM ChiTietDonThuoc WHERE MaDonThuoc = %s FOR UPDATE;

-- 4.1 Hoàn tồn kho toàn bộ thuốc trong đơn (Tham số: (ma_don,))
UPDATE Thuoc t
JOIN ChiTietDonThuoc ct ON t.MaThuoc = ct.MaThuoc
JOIN DonThuoc d ON ct.MaDonThuoc = d.MaDonThuoc
JOIN PhieuKhamBenh p ON d.MaPhieuKhamBenh = p.MaPhieuKhamBenh
SET t.SoLuongCoSan = t.SoLuongCoSan + ct.SoLuongKe
WHERE ct.MaDonThuoc = %s AND p.TrangThaiPhieuKham = 'DANG_KHAM';

-- 4.2 Xóa chi tiết đơn và vỏ đơn (Tham số: (ma_don,), (ma_don,))
DELETE ct FROM ChiTietDonThuoc ct
JOIN DonThuoc d ON ct.MaDonThuoc = d.MaDonThuoc
JOIN PhieuKhamBenh p ON d.MaPhieuKhamBenh = p.MaPhieuKhamBenh
WHERE ct.MaDonThuoc = %s AND p.TrangThaiPhieuKham = 'DANG_KHAM';

DELETE d FROM DonThuoc d
JOIN PhieuKhamBenh p ON d.MaPhieuKhamBenh = p.MaPhieuKhamBenh
WHERE d.MaDonThuoc = %s AND p.TrangThaiPhieuKham = 'DANG_KHAM';


-- ============================================================================
-- 5. XÓA TRỌN BỘ PHIẾU KHÁM ĐANG KHÁM (Transaction)
-- ============================================================================

-- 5.0 Khóa phiếu khám và kiểm tra trạng thái (Tham số: (ma_phieu,))
SELECT TrangThaiPhieuKham FROM PhieuKhamBenh
WHERE MaPhieuKhamBenh = %s FOR UPDATE;

-- 5.1 Hoàn tồn kho (Tham số: (ma_phieu,))
UPDATE Thuoc t
JOIN ChiTietDonThuoc ct ON t.MaThuoc = ct.MaThuoc
JOIN DonThuoc d ON ct.MaDonThuoc = d.MaDonThuoc
JOIN PhieuKhamBenh p ON d.MaPhieuKhamBenh = p.MaPhieuKhamBenh
SET t.SoLuongCoSan = t.SoLuongCoSan + ct.SoLuongKe
WHERE p.MaPhieuKhamBenh = %s AND p.TrangThaiPhieuKham = 'DANG_KHAM';

-- 5.2 Xóa dữ liệu phụ thuộc (Tham số: (ma_phieu,), (ma_phieu,), (ma_phieu,))
DELETE ct FROM ChiTietDonThuoc ct
JOIN DonThuoc d ON ct.MaDonThuoc = d.MaDonThuoc
JOIN PhieuKhamBenh p ON d.MaPhieuKhamBenh = p.MaPhieuKhamBenh
WHERE p.MaPhieuKhamBenh = %s AND p.TrangThaiPhieuKham = 'DANG_KHAM';

DELETE d FROM DonThuoc d
JOIN PhieuKhamBenh p ON d.MaPhieuKhamBenh = p.MaPhieuKhamBenh
WHERE p.MaPhieuKhamBenh = %s AND p.TrangThaiPhieuKham = 'DANG_KHAM';

DELETE x FROM XetNghiem x
JOIN PhieuKhamBenh p ON x.MaPhieuKhamBenh = p.MaPhieuKhamBenh
WHERE p.MaPhieuKhamBenh = %s AND p.TrangThaiPhieuKham = 'DANG_KHAM';

-- 5.3 Xóa phiếu khám (Tham số: (ma_phieu,))
DELETE FROM PhieuKhamBenh 
WHERE MaPhieuKhamBenh = %s AND TrangThaiPhieuKham = 'DANG_KHAM';


-- ============================================================================
-- 6. HOÀN THÀNH PHIẾU KHÁM VÀ ĐỒNG BỘ LỊCH HẸN (Transaction)
-- ============================================================================
-- PYTHON: bắt đầu một transaction, chạy 6.1 và yêu cầu rowcount = 1.
-- Nếu phiếu có MaLichHen, chạy 6.2 và yêu cầu rowcount = 1; nếu không có thì bỏ 6.2.
-- Nếu bất kỳ bước nào thất bại/rowcount sai -> ROLLBACK; chỉ COMMIT khi mọi bước đúng.
-- Không COMMIT ngay sau 6.1 vì có thể gây lệch TrangThaiPhieuKham / LichHen.

-- 6.1 Chốt phiếu khám sang HOAN_THANH (Tham số: (ma_phieu, ma_phieu))
UPDATE PhieuKhamBenh 
SET TrangThaiPhieuKham = 'HOAN_THANH' 
WHERE MaPhieuKhamBenh = %s 
  AND TrangThaiPhieuKham = 'DANG_KHAM'
  AND ChanDoan IS NOT NULL AND TRIM(ChanDoan) <> ''
  AND NOT EXISTS (
      SELECT 1 FROM XetNghiem 
      WHERE MaPhieuKhamBenh = %s 
        AND (KetQuaXetNghiem IS NULL OR TRIM(KetQuaXetNghiem) = '')
  );

-- 6.2 Cập nhật trạng thái lịch hẹn liên kết (nếu có) sang DA_KHAM (Tham số: (ma_phieu,))
UPDATE LichHen lh
JOIN PhieuKhamBenh pk ON lh.MaLichHen = pk.MaLichHen
SET lh.TrangThai = 'DA_KHAM'
WHERE pk.MaPhieuKhamBenh = %s
  AND pk.TrangThaiPhieuKham = 'HOAN_THANH'
  AND lh.TrangThai = 'CHO_KHAM';


-- ============================================================================
-- 7A. TRUY VẤN CHI TIẾT PHIẾU KHÁM TRONG HỒ SƠ BỆNH ÁN
-- ============================================================================

-- BA_1: Thông tin hành chính và nội dung chuyên môn ca khám (Tham số: (ma_phieu,))
SELECT 
    bn.MaBenhNhan, 
    bn.HoTen AS TenBenhNhan, 
    bn.NgaySinh, 
    bn.GioiTinh,
    bn.DiaChi,
    bn.SoDienThoai,
    hs.MaHoSo,
    hs.TienSuBenh,
    pk.MaPhieuKhamBenh, 
    pk.MaLichHen,
    pk.NgayGioKham, 
    bs.HoTen AS BacSiKham, 
    k.TenKhoa,
    pk.TrieuChung,
    pk.ChanDoan,
    pk.TrangThaiPhieuKham
FROM PhieuKhamBenh pk
JOIN HoSoBenhAn hs ON pk.MaHoSo = hs.MaHoSo
JOIN BenhNhan bn ON hs.MaBenhNhan = bn.MaBenhNhan
JOIN BacSi bs ON pk.MaBacSi = bs.MaBacSi
JOIN Khoa k ON bs.MaKhoa = k.MaKhoa
WHERE pk.MaPhieuKhamBenh = %s;

-- BA_2: Danh sách xét nghiệm và kết quả (Tham số: (ma_phieu,))
SELECT 
    x.STTXetNghiem, 
    x.TenXetNghiem, 
    x.KetQuaXetNghiem, 
    x.NgayGioThucHien
FROM XetNghiem x
WHERE x.MaPhieuKhamBenh = %s
ORDER BY x.STTXetNghiem ASC;

-- BA_3a: Thông tin chung đơn thuốc và lời dặn (Tham số: (ma_phieu,))
SELECT 
    d.MaDonThuoc,
    d.NgayLapDonThuoc, 
    d.LoiDanChung 
FROM DonThuoc d
WHERE d.MaPhieuKhamBenh = %s;

-- BA_3b: Chi tiết thuốc và hướng dẫn sử dụng (Tham số: (ma_phieu,))
SELECT 
    t.MaThuoc,
    t.TenThuoc, 
    ct.SoLuongKe, 
    t.DonViTinh, 
    ct.CachDung
FROM ChiTietDonThuoc ct
JOIN DonThuoc dt ON ct.MaDonThuoc = dt.MaDonThuoc
JOIN Thuoc t ON ct.MaThuoc = t.MaThuoc
WHERE dt.MaPhieuKhamBenh = %s;


-- ============================================================================
-- 7B. TRUY VẤN HÓA ĐƠN VÀ BẢNG KÊ ĐƠN GIÁ THEO PHIẾU KHÁM
-- ============================================================================

-- HD_1: Thông tin đầu mục hóa đơn và đơn giá khám lâm sàng (Tham số: (ma_phieu,))
SELECT 
    pk.MaPhieuKhamBenh,
    hs.MaHoSo,
    bn.MaBenhNhan,
    bn.HoTen AS TenBenhNhan,
    bn.DiaChi,
    bn.SoDienThoai,
    pk.NgayGioKham,
    bs.HoTen AS BacSiThucHien,
    k.TenKhoa,
    pk.GiaKhamApDung AS DonGiaKham
FROM PhieuKhamBenh pk
JOIN HoSoBenhAn hs ON pk.MaHoSo = hs.MaHoSo
JOIN BenhNhan bn ON hs.MaBenhNhan = bn.MaBenhNhan
JOIN BacSi bs ON pk.MaBacSi = bs.MaBacSi
JOIN Khoa k ON bs.MaKhoa = k.MaKhoa
WHERE pk.MaPhieuKhamBenh = %s AND pk.TrangThaiPhieuKham = 'HOAN_THANH';

-- HD_2: Bảng kê đơn giá dịch vụ xét nghiệm (Tham số: (ma_phieu,))
SELECT 
    x.STTXetNghiem,
    x.TenXetNghiem,
    1 AS SoLuong,
    x.DonGiaApDung,
    x.DonGiaApDung AS ThanhTien
FROM XetNghiem x
JOIN PhieuKhamBenh pk ON x.MaPhieuKhamBenh = pk.MaPhieuKhamBenh
WHERE x.MaPhieuKhamBenh = %s AND pk.TrangThaiPhieuKham = 'HOAN_THANH'
ORDER BY x.STTXetNghiem ASC;

-- HD_3: Bảng kê đơn giá thuốc xuất bán (Tham số: (ma_phieu,))
SELECT 
    t.MaThuoc,
    t.TenThuoc,
    t.DonViTinh,
    ct.SoLuongKe,
    ct.DonGiaApDung,
    (ct.SoLuongKe * ct.DonGiaApDung) AS ThanhTien
FROM ChiTietDonThuoc ct
JOIN DonThuoc dt ON ct.MaDonThuoc = dt.MaDonThuoc
JOIN PhieuKhamBenh pk ON dt.MaPhieuKhamBenh = pk.MaPhieuKhamBenh
JOIN Thuoc t ON ct.MaThuoc = t.MaThuoc
WHERE dt.MaPhieuKhamBenh = %s AND pk.TrangThaiPhieuKham = 'HOAN_THANH';

-- HD_4: Tổng hợp thanh toán hóa đơn (Tham số: (ma_phieu,))
SELECT 
    p.MaPhieuKhamBenh,
    p.MaHoSo,
    p.GiaKhamApDung AS TienKham,
    COALESCE(xn.TongTienXN, 0) AS TongTienXetNghiem,
    COALESCE(dt.TongTienThuoc, 0) AS TongTienThuoc,
    (p.GiaKhamApDung + COALESCE(xn.TongTienXN, 0) + COALESCE(dt.TongTienThuoc, 0)) AS TongThanhToan
FROM PhieuKhamBenh p
LEFT JOIN (
    SELECT MaPhieuKhamBenh, SUM(DonGiaApDung) AS TongTienXN 
    FROM XetNghiem 
    GROUP BY MaPhieuKhamBenh
) xn ON p.MaPhieuKhamBenh = xn.MaPhieuKhamBenh
LEFT JOIN (
    SELECT d.MaPhieuKhamBenh, SUM(ct.SoLuongKe * ct.DonGiaApDung) AS TongTienThuoc
    FROM DonThuoc d
    JOIN ChiTietDonThuoc ct ON d.MaDonThuoc = ct.MaDonThuoc
    GROUP BY d.MaPhieuKhamBenh
) dt ON p.MaPhieuKhamBenh = dt.MaPhieuKhamBenh
WHERE p.MaPhieuKhamBenh = %s AND p.TrangThaiPhieuKham = 'HOAN_THANH';