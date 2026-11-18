"""Queries for appointment workflows aligned with the SQL schema."""

Q_APPOINTMENT_IDS = """
SELECT MaLichHen
FROM LichHen
"""

Q_APPOINTMENTS_FOR_DOCTOR_DAY = """
SELECT lh.MaLichHen AS ma_lich,
       lh.MaBenhNhan AS ma_benh_nhan,
       bn.HoTen AS ten_benh_nhan,
       lh.MaBacSi AS ma_bac_si,
       bs.HoTen AS ten_bac_si,
       k.TenKhoa AS ten_khoa,
       TIMESTAMP(lh.NgayHen, lh.GioBatDau) AS bat_dau,
       ADDTIME(TIMESTAMP(lh.NgayHen, lh.GioBatDau), '00:30:00') AS ket_thuc,
       lh.TrangThai AS trang_thai,
       pk.MaPhieuKhamBenh AS ma_phieu_kham
FROM LichHen lh
JOIN BenhNhan bn ON bn.MaBenhNhan = lh.MaBenhNhan
JOIN BacSi bs ON bs.MaBacSi = lh.MaBacSi
JOIN Khoa k ON k.MaKhoa = bs.MaKhoa
LEFT JOIN PhieuKhamBenh pk ON pk.MaLichHen = lh.MaLichHen
WHERE lh.MaBacSi = %s
  AND lh.NgayHen = %s
ORDER BY lh.GioBatDau, lh.MaLichHen
"""

Q_APPOINTMENTS_FOR_PATIENT = """
SELECT lh.MaLichHen AS ma_lich,
       lh.MaBenhNhan AS ma_benh_nhan,
       bn.HoTen AS ten_benh_nhan,
       lh.MaBacSi AS ma_bac_si,
       bs.HoTen AS ten_bac_si,
       k.TenKhoa AS ten_khoa,
       TIMESTAMP(lh.NgayHen, lh.GioBatDau) AS bat_dau,
       ADDTIME(TIMESTAMP(lh.NgayHen, lh.GioBatDau), '00:30:00') AS ket_thuc,
       lh.TrangThai AS trang_thai,
       pk.MaPhieuKhamBenh AS ma_phieu_kham
FROM LichHen lh
JOIN BenhNhan bn ON bn.MaBenhNhan = lh.MaBenhNhan
JOIN BacSi bs ON bs.MaBacSi = lh.MaBacSi
JOIN Khoa k ON k.MaKhoa = bs.MaKhoa
LEFT JOIN PhieuKhamBenh pk ON pk.MaLichHen = lh.MaLichHen
WHERE lh.MaBenhNhan = %s
ORDER BY lh.NgayHen DESC, lh.GioBatDau DESC, lh.MaLichHen
"""

Q_APPOINTMENTS_FOR_DOCTOR = """
SELECT lh.MaLichHen AS ma_lich,
       lh.MaBenhNhan AS ma_benh_nhan,
       bn.HoTen AS ten_benh_nhan,
       lh.MaBacSi AS ma_bac_si,
       bs.HoTen AS ten_bac_si,
       k.TenKhoa AS ten_khoa,
       TIMESTAMP(lh.NgayHen, lh.GioBatDau) AS bat_dau,
       ADDTIME(TIMESTAMP(lh.NgayHen, lh.GioBatDau), '00:30:00') AS ket_thuc,
       lh.TrangThai AS trang_thai,
       pk.MaPhieuKhamBenh AS ma_phieu_kham
FROM LichHen lh
JOIN BenhNhan bn ON bn.MaBenhNhan = lh.MaBenhNhan
JOIN BacSi bs ON bs.MaBacSi = lh.MaBacSi
JOIN Khoa k ON k.MaKhoa = bs.MaKhoa
LEFT JOIN PhieuKhamBenh pk ON pk.MaLichHen = lh.MaLichHen
WHERE lh.MaBacSi = %s
ORDER BY lh.NgayHen DESC, lh.GioBatDau DESC, lh.MaLichHen
"""

Q_APPOINTMENT_BY_ID = """
SELECT lh.MaLichHen AS ma_lich,
       lh.MaBenhNhan AS ma_benh_nhan,
       bn.HoTen AS ten_benh_nhan,
       lh.MaBacSi AS ma_bac_si,
       bs.HoTen AS ten_bac_si,
       k.TenKhoa AS ten_khoa,
       TIMESTAMP(lh.NgayHen, lh.GioBatDau) AS bat_dau,
       ADDTIME(TIMESTAMP(lh.NgayHen, lh.GioBatDau), '00:30:00') AS ket_thuc,
       lh.TrangThai AS trang_thai,
       pk.MaPhieuKhamBenh AS ma_phieu_kham
FROM LichHen lh
JOIN BenhNhan bn ON bn.MaBenhNhan = lh.MaBenhNhan
JOIN BacSi bs ON bs.MaBacSi = lh.MaBacSi
JOIN Khoa k ON k.MaKhoa = bs.MaKhoa
LEFT JOIN PhieuKhamBenh pk ON pk.MaLichHen = lh.MaLichHen
WHERE lh.MaLichHen = %s
"""

Q_APPOINTMENT_BY_ID_FOR_UPDATE = """
SELECT lh.MaLichHen AS ma_lich,
       lh.MaBenhNhan AS ma_benh_nhan,
       bn.HoTen AS ten_benh_nhan,
       lh.MaBacSi AS ma_bac_si,
       bs.HoTen AS ten_bac_si,
       k.TenKhoa AS ten_khoa,
       TIMESTAMP(lh.NgayHen, lh.GioBatDau) AS bat_dau,
       ADDTIME(TIMESTAMP(lh.NgayHen, lh.GioBatDau), '00:30:00') AS ket_thuc,
       lh.TrangThai AS trang_thai,
       pk.MaPhieuKhamBenh AS ma_phieu_kham
FROM LichHen lh
JOIN BenhNhan bn ON bn.MaBenhNhan = lh.MaBenhNhan
JOIN BacSi bs ON bs.MaBacSi = lh.MaBacSi
JOIN Khoa k ON k.MaKhoa = bs.MaKhoa
LEFT JOIN PhieuKhamBenh pk ON pk.MaLichHen = lh.MaLichHen
WHERE lh.MaLichHen = %s
FOR UPDATE
"""

Q_PATIENT_APPOINTMENT_FOR_DOCTOR_DAY = """
SELECT MaLichHen
FROM LichHen
WHERE MaBenhNhan = %s
  AND MaBacSi = %s
  AND NgayHen = %s
  AND TrangThai IN ('CHO_KHAM', 'DA_KHAM')
"""

Q_INSERT_APPOINTMENT = """
INSERT INTO LichHen
    (MaLichHen, MaBacSi, MaBenhNhan, NgayHen, GioBatDau, TrangThai)
VALUES (%s, %s, %s, %s, %s, 'CHO_KHAM')
"""

Q_RESCHEDULE_APPOINTMENT = """
UPDATE LichHen
SET NgayHen = %s, GioBatDau = %s
WHERE MaLichHen = %s
  AND MaBenhNhan = %s
  AND TrangThai = 'CHO_KHAM'
  AND TIMESTAMP(NgayHen, GioBatDau) > NOW()
  AND NOT EXISTS (
      SELECT 1
      FROM PhieuKhamBenh pk
      WHERE pk.MaLichHen = LichHen.MaLichHen
  )
"""

Q_CANCEL_APPOINTMENT = """
UPDATE LichHen
SET TrangThai = 'DA_HUY'
WHERE MaLichHen = %s
  AND TrangThai = 'CHO_KHAM'
  AND TIMESTAMP(NgayHen, GioBatDau) > NOW()
  AND NOT EXISTS (
      SELECT 1
      FROM PhieuKhamBenh pk
      WHERE pk.MaLichHen = LichHen.MaLichHen
  )
"""

Q_MARK_APPOINTMENT_DONE = """
UPDATE LichHen lh
JOIN PhieuKhamBenh pk ON pk.MaLichHen = lh.MaLichHen
SET lh.TrangThai = 'DA_KHAM'
WHERE lh.MaLichHen = %s
  AND lh.TrangThai = 'CHO_KHAM'
  AND pk.TrangThaiPhieuKham = 'HOAN_THANH'
"""

Q_LOCK_APPOINTMENT_FOR_VISIT = """
SELECT lh.MaLichHen AS ma_lich,
       lh.MaBacSi AS ma_bac_si,
       lh.MaBenhNhan AS ma_benh_nhan,
       lh.TrangThai AS trang_thai,
       hs.MaHoSo AS ma_ho_so
FROM LichHen lh
LEFT JOIN HoSoBenhAn hs ON hs.MaBenhNhan = lh.MaBenhNhan
WHERE lh.MaLichHen = %s
FOR UPDATE
"""

Q_INSERT_DOSSIER = """
INSERT INTO HoSoBenhAn (MaHoSo, MaBenhNhan, NgayLap, TienSuBenh)
VALUES (%s, %s, CURRENT_DATE(), NULL)
"""

Q_LOCK_DOCTOR_FEE = """
SELECT GiaKham AS gia_kham
FROM BacSi
WHERE MaBacSi = %s
FOR UPDATE
"""

Q_INSERT_VISIT_FROM_APPOINTMENT = """
INSERT INTO PhieuKhamBenh (
    MaPhieuKhamBenh, MaBacSi, MaHoSo, MaLichHen, NgayGioKham,
    ChanDoan, TrieuChung, GiaKhamApDung, TrangThaiPhieuKham
)
VALUES (%s, %s, %s, %s, NOW(), %s, %s, %s, 'DANG_KHAM')
"""
