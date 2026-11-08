-- 02_triggers.sql: Trigger bảo vệ toàn vẹn dữ liệu động & Đóng băng phiếu HOAN_THANH
USE quanlykhambenh;
DELIMITER //

-- 1. BẢO VỆ BỆNH NHÂN (Ngày sinh không ở tương lai)
CREATE TRIGGER trg_BenhNhan_BeforeInsert
BEFORE INSERT ON BenhNhan
FOR EACH ROW
BEGIN
    IF NEW.NgaySinh > CURRENT_DATE() THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Ngày sinh không được lớn hơn ngày hiện tại.';
    END IF;
END //

CREATE TRIGGER trg_BenhNhan_BeforeUpdate
BEFORE UPDATE ON BenhNhan
FOR EACH ROW
BEGIN
    IF NEW.NgaySinh > CURRENT_DATE() THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Ngày sinh không được lớn hơn ngày hiện tại.';
    END IF;
END //

-- 2. BẢO VỆ PHIẾU KHÁM BỆNH
-- BẮT ĐẦU KHỐI CẬP NHẬT: chạy riêng khối này trên CSDL đã có trigger cũ.
DROP TRIGGER IF EXISTS trg_PhieuKham_BeforeInsert //
CREATE TRIGGER trg_PhieuKham_BeforeInsert
BEFORE INSERT ON PhieuKhamBenh
FOR EACH ROW
BEGIN
    -- Phiếu mới phải đi qua bước khám trước khi hoàn thành.
    IF NEW.TrangThaiPhieuKham <> 'DANG_KHAM' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Phiếu khám mới phải ở trạng thái ĐANG KHÁM.';
    END IF;
END //

DROP TRIGGER IF EXISTS trg_PhieuKham_BeforeUpdate //
CREATE TRIGGER trg_PhieuKham_BeforeUpdate
BEFORE UPDATE ON PhieuKhamBenh
FOR EACH ROW
BEGIN
    -- Chặn sửa phiếu đã hoàn thành
    IF OLD.TrangThaiPhieuKham = 'HOAN_THANH' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Không thể chỉnh sửa phiếu khám đã HOÀN THÀNH.';
    END IF;

    -- Khóa MaHoSo và MaBacSi không cho phép chuyển nhầm sau khi tạo
    IF OLD.MaHoSo <> NEW.MaHoSo THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Không được phép thay đổi Hồ sơ bệnh án của phiếu khám.';
    END IF;
    IF OLD.MaBacSi <> NEW.MaBacSi THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Không được phép thay đổi Bác sĩ phụ trách của phiếu khám.';
    END IF;

    -- Kiểm tra tại CSDL, kể cả khi UPDATE trực tiếp ngoài SQL mẫu.
    IF NEW.TrangThaiPhieuKham = 'HOAN_THANH' THEN
        IF NEW.ChanDoan IS NULL OR NEW.ChanDoan NOT REGEXP '[^[:space:]]' THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Phải có chẩn đoán trước khi hoàn thành phiếu khám.';
        END IF;

        -- Locking read đọc dữ liệu hiện tại, không dùng snapshot cũ của transaction.
        IF EXISTS (
            SELECT 1 FROM XetNghiem x
            WHERE x.MaPhieuKhamBenh = OLD.MaPhieuKhamBenh
              AND (x.KetQuaXetNghiem IS NULL
                   OR x.KetQuaXetNghiem NOT REGEXP '[^[:space:]]'
                   OR x.NgayGioThucHien IS NULL)
            FOR SHARE
        ) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Tất cả xét nghiệm phải có kết quả trước khi hoàn thành.';
        END IF;

        -- Không kê đơn vẫn hợp lệ; đã có đầu đơn thì phải có ít nhất một thuốc.
        IF EXISTS (
            SELECT 1 FROM DonThuoc d
            WHERE d.MaPhieuKhamBenh = OLD.MaPhieuKhamBenh
              AND NOT EXISTS (
                  SELECT 1 FROM ChiTietDonThuoc ct
                  WHERE ct.MaDonThuoc = d.MaDonThuoc
                  FOR SHARE
              )
            FOR SHARE
        ) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Đơn thuốc phải có ít nhất một thuốc trước khi hoàn thành.';
        END IF;
    END IF;
END //
-- KẾT THÚC KHỐI CẬP NHẬT.

CREATE TRIGGER trg_PhieuKham_BeforeDelete
BEFORE DELETE ON PhieuKhamBenh
FOR EACH ROW
BEGIN
    IF OLD.TrangThaiPhieuKham = 'HOAN_THANH' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Không thể xóa phiếu khám đã HOÀN THÀNH.';
    END IF;
END //

-- 3. BẢO VỆ XÉT NGHIỆM
CREATE TRIGGER trg_XetNghiem_BeforeInsert
BEFORE INSERT ON XetNghiem
FOR EACH ROW
BEGIN
    DECLARE v_TrangThai VARCHAR(20);
    SELECT TrangThaiPhieuKham INTO v_TrangThai FROM PhieuKhamBenh WHERE MaPhieuKhamBenh = NEW.MaPhieuKhamBenh;
    IF v_TrangThai = 'HOAN_THANH' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Không thể thêm xét nghiệm cho phiếu đã HOÀN THÀNH.';
    END IF;
END //

CREATE TRIGGER trg_XetNghiem_BeforeUpdate
BEFORE UPDATE ON XetNghiem
FOR EACH ROW
BEGIN
    DECLARE v_TrangThaiCu VARCHAR(20);
    IF OLD.MaPhieuKhamBenh <> NEW.MaPhieuKhamBenh THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Không được di chuyển xét nghiệm sang phiếu khám khác.';
    END IF;

    SELECT TrangThaiPhieuKham INTO v_TrangThaiCu FROM PhieuKhamBenh WHERE MaPhieuKhamBenh = OLD.MaPhieuKhamBenh;
    IF v_TrangThaiCu = 'HOAN_THANH' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Không thể sửa xét nghiệm của phiếu đã HOÀN THÀNH.';
    END IF;
END //

CREATE TRIGGER trg_XetNghiem_BeforeDelete
BEFORE DELETE ON XetNghiem
FOR EACH ROW
BEGIN
    DECLARE v_TrangThai VARCHAR(20);
    SELECT TrangThaiPhieuKham INTO v_TrangThai FROM PhieuKhamBenh WHERE MaPhieuKhamBenh = OLD.MaPhieuKhamBenh;
    IF v_TrangThai = 'HOAN_THANH' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Không thể xóa xét nghiệm của phiếu đã HOÀN THÀNH.';
    END IF;
END //

-- 4. BẢO VỆ ĐƠN THUỐC
CREATE TRIGGER trg_DonThuoc_BeforeInsert
BEFORE INSERT ON DonThuoc
FOR EACH ROW
BEGIN
    DECLARE v_TrangThai VARCHAR(20);
    SELECT TrangThaiPhieuKham INTO v_TrangThai FROM PhieuKhamBenh WHERE MaPhieuKhamBenh = NEW.MaPhieuKhamBenh;
    IF v_TrangThai = 'HOAN_THANH' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Không thể tạo đơn thuốc cho phiếu đã HOÀN THÀNH.';
    END IF;
END //

CREATE TRIGGER trg_DonThuoc_BeforeUpdate
BEFORE UPDATE ON DonThuoc
FOR EACH ROW
BEGIN
    DECLARE v_TrangThai VARCHAR(20);
    IF OLD.MaPhieuKhamBenh <> NEW.MaPhieuKhamBenh THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Không được di chuyển đơn thuốc sang phiếu khám khác.';
    END IF;

    SELECT TrangThaiPhieuKham INTO v_TrangThai FROM PhieuKhamBenh WHERE MaPhieuKhamBenh = OLD.MaPhieuKhamBenh;
    IF v_TrangThai = 'HOAN_THANH' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Không thể sửa đơn thuốc của phiếu đã HOÀN THÀNH.';
    END IF;
END //

CREATE TRIGGER trg_DonThuoc_BeforeDelete
BEFORE DELETE ON DonThuoc
FOR EACH ROW
BEGIN
    DECLARE v_TrangThai VARCHAR(20);
    SELECT TrangThaiPhieuKham INTO v_TrangThai FROM PhieuKhamBenh WHERE MaPhieuKhamBenh = OLD.MaPhieuKhamBenh;
    IF v_TrangThai = 'HOAN_THANH' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Không thể xóa đơn thuốc của phiếu đã HOÀN THÀNH.';
    END IF;
END //

-- 5. BẢO VỆ CHI TIẾT ĐƠN THUỐC
CREATE TRIGGER trg_ChiTietDonThuoc_BeforeInsert
BEFORE INSERT ON ChiTietDonThuoc
FOR EACH ROW
BEGIN
    DECLARE v_TrangThai VARCHAR(20);
    SELECT p.TrangThaiPhieuKham INTO v_TrangThai 
    FROM PhieuKhamBenh p 
    JOIN DonThuoc d ON p.MaPhieuKhamBenh = d.MaPhieuKhamBenh 
    WHERE d.MaDonThuoc = NEW.MaDonThuoc;

    IF v_TrangThai = 'HOAN_THANH' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Không thể thêm thuốc vào đơn của phiếu đã HOÀN THÀNH.';
    END IF;
END //

CREATE TRIGGER trg_ChiTietDonThuoc_BeforeUpdate
BEFORE UPDATE ON ChiTietDonThuoc
FOR EACH ROW
BEGIN
    DECLARE v_TrangThai VARCHAR(20);
    IF OLD.MaDonThuoc <> NEW.MaDonThuoc THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Không được di chuyển thuốc sang đơn khác.';
    END IF;
    -- Không đổi MaThuoc trực tiếp: tránh chuyển thuốc mà không hoàn/trừ tồn tương ứng.
    IF OLD.MaThuoc <> NEW.MaThuoc THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Không được đổi trực tiếp mã thuốc trong chi tiết đơn.';
    END IF;

    SELECT p.TrangThaiPhieuKham INTO v_TrangThai 
    FROM PhieuKhamBenh p 
    JOIN DonThuoc d ON p.MaPhieuKhamBenh = d.MaPhieuKhamBenh 
    WHERE d.MaDonThuoc = OLD.MaDonThuoc;
    
    IF v_TrangThai = 'HOAN_THANH' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Không thể sửa chi tiết đơn thuốc của phiếu đã HOÀN THÀNH.';
    END IF;
END //

CREATE TRIGGER trg_ChiTietDonThuoc_BeforeDelete
BEFORE DELETE ON ChiTietDonThuoc
FOR EACH ROW
BEGIN
    DECLARE v_TrangThai VARCHAR(20);
    SELECT p.TrangThaiPhieuKham INTO v_TrangThai 
    FROM PhieuKhamBenh p 
    JOIN DonThuoc d ON p.MaPhieuKhamBenh = d.MaPhieuKhamBenh 
    WHERE d.MaDonThuoc = OLD.MaDonThuoc;
    
    IF v_TrangThai = 'HOAN_THANH' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Không thể xóa thuốc trong đơn của phiếu đã HOÀN THÀNH.';
    END IF;
END //

DELIMITER ;
