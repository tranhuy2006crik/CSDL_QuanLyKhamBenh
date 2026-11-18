-- 02_triggers.sql: Trigger bảo vệ toàn vẹn dữ liệu động & Đóng băng phiếu HOAN_THANH
USE quanlykhambenh;
DELIMITER //

-- Don dep trigger AFTER cua cac ban cu khi cap nhat tren CSDL da ton tai.
-- Ban nay dong bo trang thai lich hen bang 03_business_logic.sql (muc 6.1/6.2).
DROP TRIGGER IF EXISTS trg_PhieuKham_AfterInsert //
DROP TRIGGER IF EXISTS trg_PhieuKham_AfterUpdate //
DROP TRIGGER IF EXISTS trg_PhieuKham_AfterDelete //

-- 1. BẢO VỆ BỆNH NHÂN
DROP TRIGGER IF EXISTS trg_BenhNhan_BeforeInsert //
CREATE TRIGGER trg_BenhNhan_BeforeInsert
BEFORE INSERT ON BenhNhan
FOR EACH ROW
BEGIN
    IF NEW.NgaySinh > CURRENT_DATE() THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Ngày sinh không được lớn hơn ngày hiện tại.';
    END IF;
END //

DROP TRIGGER IF EXISTS trg_BenhNhan_BeforeUpdate //
CREATE TRIGGER trg_BenhNhan_BeforeUpdate
BEFORE UPDATE ON BenhNhan
FOR EACH ROW
BEGIN
    IF NEW.NgaySinh > CURRENT_DATE() THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Ngày sinh không được lớn hơn ngày hiện tại.';
    END IF;
END //

-- 2. BẢO VỆ LỊCH HẸN
DROP TRIGGER IF EXISTS trg_LichHen_BeforeInsert //
CREATE TRIGGER trg_LichHen_BeforeInsert
BEFORE INSERT ON LichHen
FOR EACH ROW
BEGIN
    DECLARE v_Thu TINYINT;
    SET v_Thu = IF(DAYOFWEEK(NEW.NgayHen) = 1, 8, DAYOFWEEK(NEW.NgayHen));

    IF NEW.TrangThai <> 'CHO_KHAM' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Lịch hẹn mới tạo phải ở trạng thái CHO_KHAM.';
    END IF;

    IF TIMESTAMP(NEW.NgayHen, NEW.GioBatDau) <= NOW() THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Không được đặt lịch hẹn ở thời điểm trong quá khứ.';
    END IF;

    IF SECOND(NEW.GioBatDau) <> 0 OR MINUTE(NEW.GioBatDau) NOT IN (0, 30) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Giờ bắt đầu lịch hẹn phải nằm trên mốc 30 phút (ví dụ: 08:00, 08:30).';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM LichLamViecBacSi llv
        WHERE llv.MaBacSi = NEW.MaBacSi
          AND llv.Thu = v_Thu
          AND NEW.GioBatDau >= llv.GioBatDau
          AND ADDTIME(NEW.GioBatDau, '00:30:00') <= llv.GioKetThuc
    ) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Khoảng khám 30 phút không nằm trong ca làm việc của bác sĩ.';
    END IF;
END //

DROP TRIGGER IF EXISTS trg_LichHen_BeforeUpdate //
CREATE TRIGGER trg_LichHen_BeforeUpdate
BEFORE UPDATE ON LichHen
FOR EACH ROW
BEGIN
    DECLARE v_Thu TINYINT;

    IF OLD.TrangThai IN ('DA_KHAM', 'DA_HUY') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Không thể chỉnh sửa lịch hẹn đã khám hoặc đã hủy.';
    END IF;

    IF OLD.MaLichHen <> NEW.MaLichHen
       OR OLD.MaBenhNhan <> NEW.MaBenhNhan
       OR OLD.MaBacSi <> NEW.MaBacSi THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Không được đổi mã lịch, bệnh nhân hoặc bác sĩ của lịch hẹn.';
    END IF;

    IF NEW.TrangThai = 'DA_KHAM' THEN
        IF OLD.NgayHen <> NEW.NgayHen OR OLD.GioBatDau <> NEW.GioBatDau THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Không được thay đổi ngày giờ hẹn khi xác nhận đã khám.';
        END IF;

        IF NOT EXISTS (
            SELECT 1 FROM PhieuKhamBenh pk
            WHERE pk.MaLichHen = OLD.MaLichHen
              AND pk.TrangThaiPhieuKham = 'HOAN_THANH'
        ) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Chỉ được chuyển sang DA_KHAM khi phiếu khám liên kết đã HOÀN THÀNH.';
        END IF;
    ELSE
        IF EXISTS (
            SELECT 1 FROM PhieuKhamBenh pk
            WHERE pk.MaLichHen = OLD.MaLichHen
        ) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Lịch hẹn đã được tiếp nhận lập phiếu khám, không thể hủy hoặc thay đổi.';
        END IF;

        IF NEW.TrangThai = 'DA_HUY' THEN
            IF OLD.NgayHen <> NEW.NgayHen OR OLD.GioBatDau <> NEW.GioBatDau THEN
                SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Không được thay đổi ngày giờ khi hủy lịch hẹn.';
            END IF;

            IF TIMESTAMP(OLD.NgayHen, OLD.GioBatDau) <= NOW() THEN
                SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Chỉ được hủy lịch hẹn trước giờ hẹn.';
            END IF;
        END IF;

        IF NEW.TrangThai = 'CHO_KHAM' AND (OLD.NgayHen <> NEW.NgayHen OR OLD.GioBatDau <> NEW.GioBatDau) THEN
            IF TIMESTAMP(NEW.NgayHen, NEW.GioBatDau) <= NOW() THEN
                SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Thời gian hẹn mới không được nằm trong quá khứ.';
            END IF;

            IF SECOND(NEW.GioBatDau) <> 0 OR MINUTE(NEW.GioBatDau) NOT IN (0, 30) THEN
                SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Giờ bắt đầu lịch hẹn phải nằm trên mốc 30 phút.';
            END IF;

            SET v_Thu = IF(DAYOFWEEK(NEW.NgayHen) = 1, 8, DAYOFWEEK(NEW.NgayHen));
            IF NOT EXISTS (
                SELECT 1 FROM LichLamViecBacSi llv
                WHERE llv.MaBacSi = NEW.MaBacSi
                  AND llv.Thu = v_Thu
                  AND NEW.GioBatDau >= llv.GioBatDau
                  AND ADDTIME(NEW.GioBatDau, '00:30:00') <= llv.GioKetThuc
            ) THEN
                SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Khoảng khám 30 phút mới không nằm trong ca làm việc của bác sĩ.';
            END IF;
        END IF;
    END IF;
END //

DROP TRIGGER IF EXISTS trg_LichHen_BeforeDelete //
CREATE TRIGGER trg_LichHen_BeforeDelete
BEFORE DELETE ON LichHen
FOR EACH ROW
BEGIN
    IF OLD.TrangThai = 'DA_KHAM' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Không thể xóa lịch hẹn đã khám.';
    END IF;

    IF EXISTS (
        SELECT 1 FROM PhieuKhamBenh pk
        WHERE pk.MaLichHen = OLD.MaLichHen
    ) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Không thể xóa lịch hẹn đang có phiếu khám liên kết.';
    END IF;
END //

-- 3. BẢO VỆ PHIẾU KHÁM BỆNH
DROP TRIGGER IF EXISTS trg_PhieuKham_BeforeInsert //
CREATE TRIGGER trg_PhieuKham_BeforeInsert
BEFORE INSERT ON PhieuKhamBenh
FOR EACH ROW
BEGIN
    DECLARE v_LH_TrangThai VARCHAR(20);
    DECLARE v_LH_MaBacSi CHAR(5);
    DECLARE v_LH_MaBenhNhan CHAR(5);
    DECLARE v_HS_MaBenhNhan CHAR(5);

    IF NEW.TrangThaiPhieuKham <> 'DANG_KHAM' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Phiếu khám mới phải ở trạng thái ĐANG KHÁM.';
    END IF;

    IF NEW.MaLichHen IS NOT NULL THEN
        SELECT TrangThai, MaBacSi, MaBenhNhan
        INTO v_LH_TrangThai, v_LH_MaBacSi, v_LH_MaBenhNhan
        FROM LichHen
        WHERE MaLichHen = NEW.MaLichHen;

        IF v_LH_TrangThai IS NULL THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Mã lịch hẹn không tồn tại.';
        END IF;

        IF v_LH_TrangThai <> 'CHO_KHAM' THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Chỉ được tiếp nhận lịch hẹn đang ở trạng thái CHO_KHAM.';
        END IF;

        IF v_LH_MaBacSi <> NEW.MaBacSi THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Bác sĩ trên phiếu khám không khớp với lịch hẹn.';
        END IF;

        SELECT MaBenhNhan INTO v_HS_MaBenhNhan FROM HoSoBenhAn WHERE MaHoSo = NEW.MaHoSo;
        IF v_LH_MaBenhNhan <> v_HS_MaBenhNhan THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Bệnh nhân của hồ sơ bệnh án không khớp với lịch hẹn.';
        END IF;
    END IF;
END //

DROP TRIGGER IF EXISTS trg_PhieuKham_BeforeUpdate //
CREATE TRIGGER trg_PhieuKham_BeforeUpdate
BEFORE UPDATE ON PhieuKhamBenh
FOR EACH ROW
BEGIN
    IF OLD.TrangThaiPhieuKham = 'HOAN_THANH' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Không thể chỉnh sửa phiếu khám đã HOÀN THÀNH.';
    END IF;

    IF OLD.MaHoSo <> NEW.MaHoSo THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Không được phép thay đổi Hồ sơ bệnh án của phiếu khám.';
    END IF;
    IF OLD.MaBacSi <> NEW.MaBacSi THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Không được phép thay đổi Bác sĩ phụ trách của phiếu khám.';
    END IF;
    IF NOT (OLD.MaLichHen <=> NEW.MaLichHen) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Không được phép thay đổi Mã lịch hẹn gắn với phiếu khám.';
    END IF;

    IF NEW.TrangThaiPhieuKham = 'HOAN_THANH' THEN
        IF NEW.ChanDoan IS NULL OR NEW.ChanDoan NOT REGEXP '[^[:space:]]' THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Phải có chẩn đoán trước khi hoàn thành phiếu khám.';
        END IF;

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

DROP TRIGGER IF EXISTS trg_PhieuKham_BeforeDelete //
CREATE TRIGGER trg_PhieuKham_BeforeDelete
BEFORE DELETE ON PhieuKhamBenh
FOR EACH ROW
BEGIN
    IF OLD.TrangThaiPhieuKham = 'HOAN_THANH' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Không thể xóa phiếu khám đã HOÀN THÀNH.';
    END IF;
END //

-- 4. BẢO VỆ XÉT NGHIỆM
DROP TRIGGER IF EXISTS trg_XetNghiem_BeforeInsert //
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

DROP TRIGGER IF EXISTS trg_XetNghiem_BeforeUpdate //
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

DROP TRIGGER IF EXISTS trg_XetNghiem_BeforeDelete //
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

-- 5. BẢO VỆ ĐƠN THUỐC
DROP TRIGGER IF EXISTS trg_DonThuoc_BeforeInsert //
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

DROP TRIGGER IF EXISTS trg_DonThuoc_BeforeUpdate //
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

DROP TRIGGER IF EXISTS trg_DonThuoc_BeforeDelete //
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

-- 6. BẢO VỆ CHI TIẾT ĐƠN THUỐC
DROP TRIGGER IF EXISTS trg_ChiTietDonThuoc_BeforeInsert //
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

DROP TRIGGER IF EXISTS trg_ChiTietDonThuoc_BeforeUpdate //
CREATE TRIGGER trg_ChiTietDonThuoc_BeforeUpdate
BEFORE UPDATE ON ChiTietDonThuoc
FOR EACH ROW
BEGIN
    DECLARE v_TrangThai VARCHAR(20);
    IF OLD.MaDonThuoc <> NEW.MaDonThuoc THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Lỗi: Không được di chuyển thuốc sang đơn khác.';
    END IF;
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

DROP TRIGGER IF EXISTS trg_ChiTietDonThuoc_BeforeDelete //
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