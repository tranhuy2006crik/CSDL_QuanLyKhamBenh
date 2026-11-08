-- 04_business_logic.sql: Bộ SQL API Tổng quát cho Python Tkinter (Dùng tham số %s)
-- GHI CHÚ CHO HUY VÀ MINH (BACKEND PYTHON TKINTER):
-- 1. Tất cả tham số động đã dùng định dạng %s chuẩn cho `mysql-connector-python` / `pymysql`.
-- 2. Trong Python, với các câu UPDATE trừ tồn kho, if cursor.rowcount == 0 thì BẮT BUỘC conn.rollback() và hiển thị lỗi.

USE quanlykhambenh;

-- ============================================================================
-- 1. NGHIỆP VỤ XÉT NGHIỆM (Chỉ thực thi khi phiếu DANG_KHAM)
-- ============================================================================

-- 1.1 Thêm chỉ định xét nghiệm mới (Đúng 5 tham số %s)
-- Tham số Python tuple: (ma_phieu, stt, ten_xn, don_gia, ma_phieu)
INSERT INTO XetNghiem (MaPhieuKhamBenh, STTXetNghiem, TenXetNghiem, KetQuaXetNghiem, NgayGioThucHien, DonGiaApDung)
SELECT %s, %s, %s, NULL, NULL, %s
FROM DUAL WHERE (SELECT TrangThaiPhieuKham FROM PhieuKhamBenh WHERE MaPhieuKhamBenh = %s) = 'DANG_KHAM';

-- 1.2 Sửa chỉ định xét nghiệm (Sửa tên/giá khi phiếu DANG_KHAM)
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

-- BẮT BUỘC kiểm tra danh sách thuốc có ít nhất một dòng TRƯỚC khi tạo đầu đơn.
-- Python dùng luu_don_thuoc_moi() trong transaction_handlers.py để lưu trọn đơn.
-- start_transaction() -> 2.0 -> 2.1 -> lặp 2.2/2.3 từng thuốc -> 2.4 -> commit().
-- Mỗi INSERT/UPDATE phải có rowcount = 1; lỗi hoặc thiếu dòng -> rollback() tất cả.
-- Không COMMIT chỉ sau 2.1; đầu đơn chỉ được rỗng tạm thời bên trong transaction.

-- Execute 2.0: Khóa phiếu và kiểm tra trạng thái (Tham số: ma_phieu)
SELECT TrangThaiPhieuKham FROM PhieuKhamBenh
WHERE MaPhieuKhamBenh = %s FOR UPDATE;
-- Không có phiếu hoặc trạng thái khác DANG_KHAM -> rollback().

-- Execute 2.1: Tạo vỏ đơn thuốc (Tham số: ma_don, ma_phieu, loi_dan, ma_phieu)
INSERT INTO DonThuoc (MaDonThuoc, MaPhieuKhamBenh, NgayLapDonThuoc, LoiDanChung)
SELECT %s, %s, CURRENT_DATE(), %s
FROM DUAL WHERE (SELECT TrangThaiPhieuKham FROM PhieuKhamBenh WHERE MaPhieuKhamBenh = %s) = 'DANG_KHAM';

-- Execute 2.2: Trừ tồn kho an toàn (Tham số: so_luong_ke, ma_thuoc, so_luong_ke)
-- Python Check: if cursor.rowcount == 0 -> conn.rollback() ngay!
UPDATE Thuoc 
SET SoLuongCoSan = SoLuongCoSan - %s 
WHERE MaThuoc = %s AND SoLuongCoSan >= %s;

-- Execute 2.3: Thêm chi tiết đơn thuốc (Tham số: ma_don, ma_thuoc, so_luong_ke, cach_dung, ma_thuoc)
INSERT INTO ChiTietDonThuoc (MaDonThuoc, MaThuoc, SoLuongKe, CachDung, DonGiaApDung)
SELECT %s, %s, %s, %s, DonGia
FROM Thuoc WHERE MaThuoc = %s;

-- Execute 2.4: Kiểm tra đủ chi tiết trước khi COMMIT (Tham số: ma_don)
SELECT COUNT(*) AS SoDongThuoc FROM ChiTietDonThuoc WHERE MaDonThuoc = %s;
-- Kết quả phải bằng số thuốc yêu cầu và > 0; không đúng -> rollback().


-- ============================================================================
-- 3. NGHIỆP VỤ SỬA SỐ LƯỢNG THUỐC TRONG ĐƠN (Transaction)
-- ============================================================================

-- BẮT BUỘC Python chạy toàn bộ thao tác trong MỘT transaction:
-- start_transaction() -> SELECT ... FOR UPDATE -> tính delta từ số lượng cũ
-- -> UPDATE Thuoc (nếu delta khác 0) -> UPDATE ChiTietDonThuoc -> commit().
-- Bất cứ lỗi nào / rowcount không đúng -> rollback(), KHÔNG commit giữa chừng.
-- Tham khảo hàm sua_so_luong_thuoc() trong transaction_handlers.py.
-- 3.0 Khóa bản ghi thuốc trong đơn, đọc số lượng CŨ trực tiếp từ DB
-- Tham số: (ma_don, ma_thuoc). Không tính delta từ dữ liệu cũ trên giao diện.
SELECT ct.SoLuongKe, ct.CachDung, p.TrangThaiPhieuKham
FROM ChiTietDonThuoc ct
JOIN DonThuoc d ON ct.MaDonThuoc = d.MaDonThuoc
JOIN PhieuKhamBenh p ON d.MaPhieuKhamBenh = p.MaPhieuKhamBenh
WHERE ct.MaDonThuoc = %s AND ct.MaThuoc = %s
FOR UPDATE;
-- Nếu không có dòng hoặc trạng thái khác DANG_KHAM -> rollback().
-- delta = so_luong_moi - so_luong_cu, so_luong_moi phải > 0.

-- Kịch bản A: TĂNG số lượng thuốc (delta = so_luong_moi - so_luong_cu > 0)
-- 3.A1: Trừ thêm kho (Tham số: delta, ma_thuoc, delta) -> Check if cursor.rowcount == 0 -> conn.rollback()
UPDATE Thuoc SET SoLuongCoSan = SoLuongCoSan - %s WHERE MaThuoc = %s AND SoLuongCoSan >= %s;
-- 3.A2: Cập nhật chi tiết đơn (Tham số: so_luong_moi, cach_dung_moi, ma_don, ma_thuoc, so_luong_cu)
-- Phải có rowcount = 1; nếu 0 -> rollback() cả phần trừ tồn ở 3.A1.
UPDATE ChiTietDonThuoc ct
JOIN DonThuoc d ON ct.MaDonThuoc = d.MaDonThuoc
JOIN PhieuKhamBenh p ON d.MaPhieuKhamBenh = p.MaPhieuKhamBenh
SET ct.SoLuongKe = %s, ct.CachDung = %s
WHERE ct.MaDonThuoc = %s AND ct.MaThuoc = %s AND p.TrangThaiPhieuKham = 'DANG_KHAM'
  AND ct.SoLuongKe = %s;

-- Kịch bản B: GIẢM số lượng thuốc (delta = so_luong_cu - so_luong_moi > 0)
-- 3.B1: Hoàn lại phần dư tồn kho (Tham số: delta, ma_thuoc)
UPDATE Thuoc SET SoLuongCoSan = SoLuongCoSan + %s WHERE MaThuoc = %s;
-- 3.B2: Cập nhật chi tiết đơn (Tham số: so_luong_moi, cach_dung_moi, ma_don, ma_thuoc, so_luong_cu)
-- Phải có rowcount = 1; nếu 0 -> rollback() cả phần hoàn tồn ở 3.B1.
UPDATE ChiTietDonThuoc ct
JOIN DonThuoc d ON ct.MaDonThuoc = d.MaDonThuoc
JOIN PhieuKhamBenh p ON d.MaPhieuKhamBenh = p.MaPhieuKhamBenh
SET ct.SoLuongKe = %s, ct.CachDung = %s
WHERE ct.MaDonThuoc = %s AND ct.MaThuoc = %s AND p.TrangThaiPhieuKham = 'DANG_KHAM'
  AND ct.SoLuongKe = %s;


-- ============================================================================
-- 4. XÓA ĐƠN THUỐC & HOÀN TỒN KHO (Transaction)
-- ============================================================================

-- BẮT BUỘC Python: start_transaction() -> khóa đơn + phiếu (4.0)
-- -> hoàn tồn (4.1) -> xóa chi tiết rồi đầu đơn (4.2) -> commit().
-- Lỗi, thiếu dòng hoặc số dòng cập nhật/xóa không đúng -> rollback() TẤT CẢ.
-- KHÔNG thực hiện 4.1 / 4.2 riêng lẻ ngoài transaction.
-- Tham khảo xoa_don_thuoc() trong transaction_handlers.py.
-- 4.0 Kiểm tra trạng thái và khóa phiếu/đơn trước khi thay đổi dữ liệu
-- Tham số: (ma_don,)
SELECT p.TrangThaiPhieuKham
FROM DonThuoc d
JOIN PhieuKhamBenh p ON d.MaPhieuKhamBenh = p.MaPhieuKhamBenh
WHERE d.MaDonThuoc = %s
FOR UPDATE;
-- Nếu không tìm thấy đơn hoặc trạng thái khác DANG_KHAM -> rollback().
-- Đếm/khóa các chi tiết trong cùng transaction để đối chiếu số dòng:
SELECT MaThuoc FROM ChiTietDonThuoc WHERE MaDonThuoc = %s FOR UPDATE;

-- 4.1 Hoàn tồn kho toàn bộ thuốc trong đơn (Tham số: ma_don)
UPDATE Thuoc t
JOIN ChiTietDonThuoc ct ON t.MaThuoc = ct.MaThuoc
JOIN DonThuoc d ON ct.MaDonThuoc = d.MaDonThuoc
JOIN PhieuKhamBenh p ON d.MaPhieuKhamBenh = p.MaPhieuKhamBenh
SET t.SoLuongCoSan = t.SoLuongCoSan + ct.SoLuongKe
WHERE ct.MaDonThuoc = %s AND p.TrangThaiPhieuKham = 'DANG_KHAM';

-- 4.2 Xóa chi tiết đơn và vỏ đơn (Tham số: ma_don)
DELETE ct FROM ChiTietDonThuoc ct
JOIN DonThuoc d ON ct.MaDonThuoc = d.MaDonThuoc
JOIN PhieuKhamBenh p ON d.MaPhieuKhamBenh = p.MaPhieuKhamBenh
WHERE ct.MaDonThuoc = %s AND p.TrangThaiPhieuKham = 'DANG_KHAM';

DELETE d FROM DonThuoc d
JOIN PhieuKhamBenh p ON d.MaPhieuKhamBenh = p.MaPhieuKhamBenh
WHERE d.MaDonThuoc = %s AND p.TrangThaiPhieuKham = 'DANG_KHAM';
-- rowcount của lệnh DELETE đầu đơn phải = 1, nếu không -> rollback().
-- Chỉ commit khi hoàn tồn + xóa chi tiết + xóa đầu đơn đều thành công.


-- ============================================================================
-- 5. XÓA TRỌN BỘ PHIẾU KHÁM ĐANG KHÁM (Transaction)
-- ============================================================================

-- BẮT BUỘC Python: start_transaction() -> khóa phiếu (5.0)
-- -> hoàn tồn (5.1) -> xóa các bảng con (5.2) -> xóa phiếu (5.3) -> commit().
-- Lỗi ở BẤT KỲ bước nào -> rollback() TẤT CẢ, không commit giữa chừng.
-- Tham khảo xoa_phieu_dang_kham() trong transaction_handlers.py.
-- 5.0 Khóa phiếu khám và kiểm tra trạng thái trước khi thay đổi dữ liệu
-- Tham số: (ma_phieu,)
SELECT TrangThaiPhieuKham FROM PhieuKhamBenh
WHERE MaPhieuKhamBenh = %s FOR UPDATE;
-- Không tìm thấy phiếu / trạng thái khác DANG_KHAM -> rollback().

-- 5.1 Hoàn tồn kho (Tham số: ma_phieu)
UPDATE Thuoc t
JOIN ChiTietDonThuoc ct ON t.MaThuoc = ct.MaThuoc
JOIN DonThuoc d ON ct.MaDonThuoc = d.MaDonThuoc
JOIN PhieuKhamBenh p ON d.MaPhieuKhamBenh = p.MaPhieuKhamBenh
SET t.SoLuongCoSan = t.SoLuongCoSan + ct.SoLuongKe
WHERE p.MaPhieuKhamBenh = %s AND p.TrangThaiPhieuKham = 'DANG_KHAM';

-- 5.2 Xóa dữ liệu phụ thuộc (Tham số: ma_phieu)
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

-- 5.3 Xóa phiếu khám (Tham số: ma_phieu)
DELETE FROM PhieuKhamBenh 
WHERE MaPhieuKhamBenh = %s AND TrangThaiPhieuKham = 'DANG_KHAM';
-- rowcount phải = 1. Chỉ commit sau khi tất cả dữ liệu con đã xóa thành công;
-- nếu không, rollback() để hoàn tác cả việc hoàn tồn kho ở 5.1.


-- ============================================================================
-- 6. CHỐT PHIẾU KHÁM SANG HOAN_THANH
-- ============================================================================

-- Trigger trong 02_triggers.sql kiểm tra lại chẩn đoán, kết quả XN và đơn rỗng.
-- Tham số Python tuple: (ma_phieu, ma_phieu)
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


-- ============================================================================
-- 7. API BÁO CÁO KẾT QUẢ KHÁM (CHỈ DÀNH CHO PHIẾU HOAN_THANH)
-- 5 câu SELECT độc lập (Tham số Python tuple: (ma_phieu,))
-- ============================================================================

-- Q1: Thông tin Hành chính & Ca khám
SELECT bn.MaBenhNhan, bn.HoTen, bn.NgaySinh, bn.SoDienThoai,
       pk.MaPhieuKhamBenh, pk.NgayGioKham, bs.HoTen AS BacSiKham, pk.ChanDoan, pk.TrieuChung
FROM PhieuKhamBenh pk
JOIN HoSoBenhAn hs ON pk.MaHoSo = hs.MaHoSo
JOIN BenhNhan bn ON hs.MaBenhNhan = bn.MaBenhNhan
JOIN BacSi bs ON pk.MaBacSi = bs.MaBacSi
WHERE pk.MaPhieuKhamBenh = %s AND pk.TrangThaiPhieuKham = 'HOAN_THANH';

-- Q2: Danh sách Xét nghiệm & Kết quả
SELECT x.STTXetNghiem, x.TenXetNghiem, x.KetQuaXetNghiem, x.NgayGioThucHien, x.DonGiaApDung
FROM XetNghiem x
JOIN PhieuKhamBenh pk ON x.MaPhieuKhamBenh = pk.MaPhieuKhamBenh
WHERE x.MaPhieuKhamBenh = %s AND pk.TrangThaiPhieuKham = 'HOAN_THANH';

-- Q3a: Lời dặn đơn thuốc
SELECT d.NgayLapDonThuoc, d.LoiDanChung 
FROM DonThuoc d
JOIN PhieuKhamBenh pk ON d.MaPhieuKhamBenh = pk.MaPhieuKhamBenh
WHERE d.MaPhieuKhamBenh = %s AND pk.TrangThaiPhieuKham = 'HOAN_THANH';

-- Q3b: Chi tiết danh sách Thuốc kê
SELECT t.TenThuoc, ct.SoLuongKe, t.DonViTinh, ct.CachDung, ct.DonGiaApDung, (ct.SoLuongKe * ct.DonGiaApDung) AS ThanhTien
FROM ChiTietDonThuoc ct
JOIN DonThuoc dt ON ct.MaDonThuoc = dt.MaDonThuoc
JOIN PhieuKhamBenh pk ON dt.MaPhieuKhamBenh = pk.MaPhieuKhamBenh
JOIN Thuoc t ON ct.MaThuoc = t.MaThuoc
WHERE dt.MaPhieuKhamBenh = %s AND pk.TrangThaiPhieuKham = 'HOAN_THANH';

-- Q4: Báo cáo Tổng chi phí
SELECT 
    p.MaPhieuKhamBenh,
    p.GiaKhamApDung,
    COALESCE(xn.TongTienXN, 0) AS TongTienXN,
    COALESCE(dt.TongTienThuoc, 0) AS TongTienThuoc,
    (p.GiaKhamApDung + COALESCE(xn.TongTienXN, 0) + COALESCE(dt.TongTienThuoc, 0)) AS TongChiPhi
FROM PhieuKhamBenh p
LEFT JOIN (
    SELECT MaPhieuKhamBenh, SUM(DonGiaApDung) AS TongTienXN 
    FROM XetNghiem GROUP BY MaPhieuKhamBenh
) xn ON p.MaPhieuKhamBenh = xn.MaPhieuKhamBenh
LEFT JOIN (
    SELECT d.MaPhieuKhamBenh, SUM(ct.SoLuongKe * ct.DonGiaApDung) AS TongTienThuoc
    FROM DonThuoc d
    JOIN ChiTietDonThuoc ct ON d.MaDonThuoc = ct.MaDonThuoc
    GROUP BY d.MaPhieuKhamBenh
) dt ON p.MaPhieuKhamBenh = dt.MaPhieuKhamBenh
WHERE p.MaPhieuKhamBenh = %s AND p.TrangThaiPhieuKham = 'HOAN_THANH';
