-- 01_schema.sql: Cấu trúc CSDL và Ràng buộc toàn vẹn
CREATE DATABASE IF NOT EXISTS quanlykhambenh
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

USE quanlykhambenh;

-- 1. Bảng Khoa
CREATE TABLE Khoa (
    MaKhoa VARCHAR(20) NOT NULL,
    TenKhoa VARCHAR(100) NOT NULL,
    PRIMARY KEY (MaKhoa),
    CONSTRAINT CHK_Khoa_MaKhoa CHECK (TRIM(MaKhoa) <> ''),
    CONSTRAINT CHK_Khoa_TenKhoa CHECK (TRIM(TenKhoa) <> '')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 2. Bảng BenhNhan
CREATE TABLE BenhNhan (
    MaBenhNhan VARCHAR(20) NOT NULL,
    HoTen VARCHAR(100) NOT NULL,
    NgaySinh DATE NOT NULL,
    GioiTinh VARCHAR(10) NOT NULL,
    DiaChi VARCHAR(255) NULL,
    SoDienThoai VARCHAR(20) NULL,
    PRIMARY KEY (MaBenhNhan),
    CONSTRAINT CHK_BenhNhan_MaBenhNhan CHECK (TRIM(MaBenhNhan) <> ''),
    CONSTRAINT CHK_BenhNhan_HoTen CHECK (TRIM(HoTen) <> ''),
    CONSTRAINT CHK_BenhNhan_GioiTinh CHECK (GioiTinh IN ('NAM', 'NU', 'KHAC')),
    CONSTRAINT CHK_BenhNhan_SoDienThoai CHECK (SoDienThoai IS NULL OR SoDienThoai REGEXP '^[0-9]{9,15}$')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 3. Bảng Thuoc
CREATE TABLE Thuoc (
    MaThuoc VARCHAR(20) NOT NULL,
    TenThuoc VARCHAR(255) NOT NULL,
    DonGia DECIMAL(15,2) NOT NULL,
    DonViTinh VARCHAR(30) NOT NULL,
    SoLuongCoSan INT NOT NULL,
    PRIMARY KEY (MaThuoc),
    CONSTRAINT CHK_Thuoc_MaThuoc CHECK (TRIM(MaThuoc) <> ''),
    CONSTRAINT CHK_Thuoc_TenThuoc CHECK (TRIM(TenThuoc) <> ''),
    CONSTRAINT CHK_Thuoc_DonGia CHECK (DonGia >= 0),
    CONSTRAINT CHK_Thuoc_DonViTinh CHECK (TRIM(DonViTinh) <> ''),
    CONSTRAINT CHK_Thuoc_SoLuongCoSan CHECK (SoLuongCoSan >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 4. Bảng BacSi
CREATE TABLE BacSi (
    MaBacSi VARCHAR(20) NOT NULL,
    MaKhoa VARCHAR(20) NOT NULL,
    HoTen VARCHAR(100) NOT NULL,
    GiaKham DECIMAL(15,2) NOT NULL,
    TrinhDoHocVan VARCHAR(100) NULL,
    PhongKham VARCHAR(100) NULL,
    PRIMARY KEY (MaBacSi),
    CONSTRAINT FK_BacSi_Khoa FOREIGN KEY (MaKhoa) 
        REFERENCES Khoa(MaKhoa) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT CHK_BacSi_MaBacSi CHECK (TRIM(MaBacSi) <> ''),
    CONSTRAINT CHK_BacSi_HoTen CHECK (TRIM(HoTen) <> ''),
    CONSTRAINT CHK_BacSi_GiaKham CHECK (GiaKham >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 5. Bảng LichLamViecBacSi
CREATE TABLE LichLamViecBacSi (
    MaBacSi VARCHAR(20) NOT NULL,
    Thu TINYINT NOT NULL,
    GioBatDau TIME NOT NULL,
    GioKetThuc TIME NOT NULL,
    PRIMARY KEY (MaBacSi, Thu, GioBatDau),
    CONSTRAINT FK_LichLamViec_BacSi FOREIGN KEY (MaBacSi) 
        REFERENCES BacSi(MaBacSi) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT CHK_LichLamViec_Thu CHECK (Thu BETWEEN 2 AND 8),
    CONSTRAINT CHK_LichLamViec_Gio CHECK (GioKetThuc > GioBatDau)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 6. Bảng HoSoBenhAn
CREATE TABLE HoSoBenhAn (
    MaHoSo VARCHAR(20) NOT NULL,
    MaBenhNhan VARCHAR(20) NOT NULL,
    NgayLap DATE NOT NULL,
    TienSuBenh TEXT NULL,
    PRIMARY KEY (MaHoSo),
    CONSTRAINT UQ_HoSoBenhAn_MaBenhNhan UNIQUE (MaBenhNhan),
    CONSTRAINT FK_HoSoBenhAn_BenhNhan FOREIGN KEY (MaBenhNhan) 
        REFERENCES BenhNhan(MaBenhNhan) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT CHK_HoSoBenhAn_MaHoSo CHECK (TRIM(MaHoSo) <> '')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 7. Bảng PhieuKhamBenh
CREATE TABLE PhieuKhamBenh (
    MaPhieuKhamBenh VARCHAR(20) NOT NULL,
    MaBacSi VARCHAR(20) NOT NULL,
    MaHoSo VARCHAR(20) NOT NULL,
    NgayGioKham DATETIME NOT NULL,
    ChanDoan TEXT NULL,
    TrieuChung TEXT NULL,
    GiaKhamApDung DECIMAL(15,2) NOT NULL,
    TrangThaiPhieuKham VARCHAR(20) NOT NULL DEFAULT 'DANG_KHAM',
    PRIMARY KEY (MaPhieuKhamBenh),
    CONSTRAINT FK_PhieuKham_BacSi FOREIGN KEY (MaBacSi) 
        REFERENCES BacSi(MaBacSi) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT FK_PhieuKham_HoSo FOREIGN KEY (MaHoSo) 
        REFERENCES HoSoBenhAn(MaHoSo) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT CHK_PhieuKham_MaPhieu CHECK (TRIM(MaPhieuKhamBenh) <> ''),
    CONSTRAINT CHK_PhieuKham_GiaKham CHECK (GiaKhamApDung >= 0),
    CONSTRAINT CHK_PhieuKham_TrangThai CHECK (TrangThaiPhieuKham IN ('DANG_KHAM', 'HOAN_THANH'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- UNIQUE INDEX: Chỉ cho phép 1 bác sĩ có tối đa 1 phiếu DANG_KHAM cho 1 hồ sơ cùng lúc
CREATE UNIQUE INDEX UQ_PhieuKham_DangKham 
ON PhieuKhamBenh (MaHoSo, MaBacSi, (CASE WHEN TrangThaiPhieuKham = 'DANG_KHAM' THEN 1 ELSE NULL END));

-- 8. Bảng XetNghiem
CREATE TABLE XetNghiem (
    MaPhieuKhamBenh VARCHAR(20) NOT NULL,
    STTXetNghiem INT UNSIGNED NOT NULL,
    TenXetNghiem VARCHAR(255) NOT NULL,
    KetQuaXetNghiem TEXT NULL,
    NgayGioThucHien DATETIME NULL,
    DonGiaApDung DECIMAL(15,2) NOT NULL,
    PRIMARY KEY (MaPhieuKhamBenh, STTXetNghiem),
    CONSTRAINT FK_XetNghiem_PhieuKham FOREIGN KEY (MaPhieuKhamBenh) 
        REFERENCES PhieuKhamBenh(MaPhieuKhamBenh) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT CHK_XetNghiem_STT CHECK (STTXetNghiem > 0),
    CONSTRAINT CHK_XetNghiem_Ten CHECK (TRIM(TenXetNghiem) <> ''),
    CONSTRAINT CHK_XetNghiem_DonGia CHECK (DonGiaApDung >= 0),
    CONSTRAINT CHK_XetNghiem_KetQua CHECK (
        (KetQuaXetNghiem IS NULL AND NgayGioThucHien IS NULL) OR
        (KetQuaXetNghiem IS NOT NULL AND NgayGioThucHien IS NOT NULL AND TRIM(KetQuaXetNghiem) <> '')
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 9. Bảng DonThuoc
CREATE TABLE DonThuoc (
    MaDonThuoc VARCHAR(20) NOT NULL,
    MaPhieuKhamBenh VARCHAR(20) NOT NULL,
    NgayLapDonThuoc DATE NOT NULL,
    LoiDanChung TEXT NULL,
    PRIMARY KEY (MaDonThuoc),
    CONSTRAINT UQ_DonThuoc_MaPhieuKhamBenh UNIQUE (MaPhieuKhamBenh),
    CONSTRAINT FK_DonThuoc_PhieuKham FOREIGN KEY (MaPhieuKhamBenh) 
        REFERENCES PhieuKhamBenh(MaPhieuKhamBenh) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT CHK_DonThuoc_MaDon CHECK (TRIM(MaDonThuoc) <> '')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 10. Bảng ChiTietDonThuoc
CREATE TABLE ChiTietDonThuoc (
    MaDonThuoc VARCHAR(20) NOT NULL,
    MaThuoc VARCHAR(20) NOT NULL,
    SoLuongKe INT NOT NULL,
    CachDung VARCHAR(500) NOT NULL,
    DonGiaApDung DECIMAL(15,2) NOT NULL,
    PRIMARY KEY (MaDonThuoc, MaThuoc),
    CONSTRAINT FK_ChiTietDon_DonThuoc FOREIGN KEY (MaDonThuoc) 
        REFERENCES DonThuoc(MaDonThuoc) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT FK_ChiTietDon_Thuoc FOREIGN KEY (MaThuoc) 
        REFERENCES Thuoc(MaThuoc) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT CHK_ChiTietDon_SoLuong CHECK (SoLuongKe > 0),
    CONSTRAINT CHK_ChiTietDon_CachDung CHECK (TRIM(CachDung) <> ''),
    CONSTRAINT CHK_ChiTietDon_DonGia CHECK (DonGiaApDung >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- INDEX tối ưu truy vấn
CREATE INDEX IDX_BenhNhan_SoDienThoai ON BenhNhan(SoDienThoai);
CREATE INDEX IDX_PhieuKham_NgayGioKham ON PhieuKhamBenh(NgayGioKham);