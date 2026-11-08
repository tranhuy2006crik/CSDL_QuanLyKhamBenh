"""Các thao tác giao dịch cho Huy/Minh (mysql-connector-python, cursor thường).

Lưu đơn mới không rỗng; sửa số lượng, xóa đơn và xóa phiếu trong
MỘT transaction trên cùng connection cho từng thao tác.

Yêu cầu: conn kết nối database quanlykhambenh, engine InnoDB.
Không gọi các hàm này khi conn đã có một transaction đang mở.
"""


def _phai_dang_kham(trang_thai, doi_tuong):
    if trang_thai != "DANG_KHAM":
        raise ValueError(f"{doi_tuong} không tồn tại hoặc không ở trạng thái DANG_KHAM")


def _phai_dung_so_dong(cursor, expected, message):
    if cursor.rowcount != expected:
        raise ValueError(message)


def luu_don_thuoc_moi(conn, ma_don, ma_phieu, danh_sach_thuoc, loi_dan=None):
    """Lưu trọn đơn mới; danh_sach_thuoc là list/tuple (mã thuốc, số lượng, cách dùng).

    Từ chối danh sách rỗng trước khi ghi DB. Chỉ commit khi đầu đơn, toàn bộ
    chi tiết và trừ tồn đều thành công; lỗi ở bất kỳ bước nào sẽ rollback.
    """
    if not isinstance(danh_sach_thuoc, (list, tuple)) or not danh_sach_thuoc:
        raise ValueError("Đơn thuốc phải có ít nhất một thuốc")

    thuoc_ke = []
    ma_da_co = set()
    for dong in danh_sach_thuoc:
        if not isinstance(dong, (list, tuple)) or len(dong) != 3:
            raise ValueError("Mỗi dòng thuốc phải gồm mã thuốc, số lượng và cách dùng")
        ma_thuoc, so_luong, cach_dung = dong
        if not isinstance(ma_thuoc, str) or not ma_thuoc.strip():
            raise ValueError("Mã thuốc không được để trống")
        if ma_thuoc in ma_da_co:
            raise ValueError("Một thuốc không được lặp lại trong cùng đơn")
        if type(so_luong) is not int or so_luong <= 0:
            raise ValueError("Số lượng kê phải là số nguyên dương")
        if not isinstance(cach_dung, str) or not cach_dung.strip():
            raise ValueError("Cách dùng không được để trống")
        ma_da_co.add(ma_thuoc)
        thuoc_ke.append((ma_thuoc, so_luong, cach_dung))

    conn.start_transaction()
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT TrangThaiPhieuKham FROM PhieuKhamBenh
            WHERE MaPhieuKhamBenh = %s FOR UPDATE
        """,
            (ma_phieu,),
        )
        row = cursor.fetchone()
        _phai_dang_kham(row[0] if row else None, "Phiếu khám")

        cursor.execute(
            """
            INSERT INTO DonThuoc (MaDonThuoc, MaPhieuKhamBenh, NgayLapDonThuoc, LoiDanChung)
            SELECT %s, %s, CURRENT_DATE(), %s
            FROM DUAL WHERE (SELECT TrangThaiPhieuKham FROM PhieuKhamBenh
                             WHERE MaPhieuKhamBenh = %s) = 'DANG_KHAM'
        """,
            (ma_don, ma_phieu, loi_dan, ma_phieu),
        )
        _phai_dung_so_dong(cursor, 1, "Không tạo được đầu đơn thuốc")

        for ma_thuoc, so_luong, cach_dung in thuoc_ke:
            cursor.execute(
                """
                UPDATE Thuoc
                SET SoLuongCoSan = SoLuongCoSan - %s
                WHERE MaThuoc = %s AND SoLuongCoSan >= %s
            """,
                (so_luong, ma_thuoc, so_luong),
            )
            _phai_dung_so_dong(cursor, 1, "Thuốc không tồn tại hoặc không đủ tồn kho")

            cursor.execute(
                """
                INSERT INTO ChiTietDonThuoc (MaDonThuoc, MaThuoc, SoLuongKe, CachDung, DonGiaApDung)
                SELECT %s, %s, %s, %s, DonGia FROM Thuoc WHERE MaThuoc = %s
            """,
                (ma_don, ma_thuoc, so_luong, cach_dung, ma_thuoc),
            )
            _phai_dung_so_dong(cursor, 1, "Không lưu được chi tiết đơn thuốc")

        cursor.execute(
            """
            SELECT COUNT(*) FROM ChiTietDonThuoc WHERE MaDonThuoc = %s
        """,
            (ma_don,),
        )
        if cursor.fetchone()[0] != len(thuoc_ke):
            raise ValueError("Đơn thuốc chưa có đầy đủ chi tiết, không thể lưu")

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()


def sua_so_luong_thuoc(conn, ma_don, ma_thuoc, so_luong_moi, cach_dung_moi):
    """Sửa số lượng/cách dùng, trừ hoặc hoàn đúng phần chênh lệch."""
    if type(so_luong_moi) is not int or so_luong_moi <= 0:
        raise ValueError("Số lượng kê mới phải là số nguyên dương")
    if not isinstance(cach_dung_moi, str) or not cach_dung_moi.strip():
        raise ValueError("Cách dùng không được để trống")

    conn.start_transaction()
    cursor = None
    try:
        cursor = conn.cursor()
        # Khóa cả chi tiết, đơn và phiếu để đọc số lượng cũ ổn định.
        cursor.execute(
            """
            SELECT ct.SoLuongKe, ct.CachDung, p.TrangThaiPhieuKham
            FROM ChiTietDonThuoc ct
            JOIN DonThuoc d ON ct.MaDonThuoc = d.MaDonThuoc
            JOIN PhieuKhamBenh p ON d.MaPhieuKhamBenh = p.MaPhieuKhamBenh
            WHERE ct.MaDonThuoc = %s AND ct.MaThuoc = %s
            FOR UPDATE
        """,
            (ma_don, ma_thuoc),
        )
        row = cursor.fetchone()
        if row is None:
            raise ValueError("Không tìm thấy thuốc trong đơn")
        so_luong_cu, cach_dung_cu, trang_thai = row
        _phai_dang_kham(trang_thai, "Phiếu khám của đơn thuốc")

        delta = so_luong_moi - so_luong_cu
        if delta > 0:
            cursor.execute(
                """
                UPDATE Thuoc
                SET SoLuongCoSan = SoLuongCoSan - %s
                WHERE MaThuoc = %s AND SoLuongCoSan >= %s
            """,
                (delta, ma_thuoc, delta),
            )
            _phai_dung_so_dong(cursor, 1, "Thuốc không đủ tồn kho để tăng số lượng")
        elif delta < 0:
            hoan = -delta
            cursor.execute(
                """
                UPDATE Thuoc
                SET SoLuongCoSan = SoLuongCoSan + %s
                WHERE MaThuoc = %s
            """,
                (hoan, ma_thuoc),
            )
            _phai_dung_so_dong(cursor, 1, "Không thể hoàn tồn kho cho thuốc")

        # Không làm UPDATE vô nghĩa vì MySQL có thể báo rowcount=0 khi giá trị không đổi.
        if delta != 0 or cach_dung_moi != cach_dung_cu:
            cursor.execute(
                """
                UPDATE ChiTietDonThuoc ct
                JOIN DonThuoc d ON ct.MaDonThuoc = d.MaDonThuoc
                JOIN PhieuKhamBenh p ON d.MaPhieuKhamBenh = p.MaPhieuKhamBenh
                SET ct.SoLuongKe = %s, ct.CachDung = %s
                WHERE ct.MaDonThuoc = %s AND ct.MaThuoc = %s
                  AND p.TrangThaiPhieuKham = 'DANG_KHAM'
                  AND ct.SoLuongKe = %s
            """,
                (so_luong_moi, cach_dung_moi, ma_don, ma_thuoc, so_luong_cu),
            )
            _phai_dung_so_dong(cursor, 1, "Không thể cập nhật chi tiết đơn thuốc")

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()


def xoa_don_thuoc(conn, ma_don):
    """Hoàn tồn rồi xóa chi tiết + đầu đơn, hoặc rollback toàn bộ."""
    conn.start_transaction()
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT p.TrangThaiPhieuKham
            FROM DonThuoc d
            JOIN PhieuKhamBenh p ON d.MaPhieuKhamBenh = p.MaPhieuKhamBenh
            WHERE d.MaDonThuoc = %s
            FOR UPDATE
        """,
            (ma_don,),
        )
        row = cursor.fetchone()
        _phai_dang_kham(row[0] if row else None, "Đơn thuốc")

        cursor.execute(
            """
            SELECT MaThuoc FROM ChiTietDonThuoc
            WHERE MaDonThuoc = %s FOR UPDATE
        """,
            (ma_don,),
        )
        so_dong_thuoc = len(cursor.fetchall())

        # 4.1 — SQL gốc của Đức.
        cursor.execute(
            """
            UPDATE Thuoc t
            JOIN ChiTietDonThuoc ct ON t.MaThuoc = ct.MaThuoc
            JOIN DonThuoc d ON ct.MaDonThuoc = d.MaDonThuoc
            JOIN PhieuKhamBenh p ON d.MaPhieuKhamBenh = p.MaPhieuKhamBenh
            SET t.SoLuongCoSan = t.SoLuongCoSan + ct.SoLuongKe
            WHERE ct.MaDonThuoc = %s AND p.TrangThaiPhieuKham = 'DANG_KHAM'
        """,
            (ma_don,),
        )
        _phai_dung_so_dong(cursor, so_dong_thuoc, "Hoàn tồn kho chưa đủ số dòng thuốc")

        # 4.2 — SQL gốc của Đức.
        cursor.execute(
            """
            DELETE ct FROM ChiTietDonThuoc ct
            JOIN DonThuoc d ON ct.MaDonThuoc = d.MaDonThuoc
            JOIN PhieuKhamBenh p ON d.MaPhieuKhamBenh = p.MaPhieuKhamBenh
            WHERE ct.MaDonThuoc = %s AND p.TrangThaiPhieuKham = 'DANG_KHAM'
        """,
            (ma_don,),
        )
        _phai_dung_so_dong(cursor, so_dong_thuoc, "Xóa chi tiết đơn chưa đủ số dòng")

        cursor.execute(
            """
            DELETE d FROM DonThuoc d
            JOIN PhieuKhamBenh p ON d.MaPhieuKhamBenh = p.MaPhieuKhamBenh
            WHERE d.MaDonThuoc = %s AND p.TrangThaiPhieuKham = 'DANG_KHAM'
        """,
            (ma_don,),
        )
        _phai_dung_so_dong(cursor, 1, "Không xóa được đầu đơn thuốc")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()


def xoa_phieu_dang_kham(conn, ma_phieu):
    """Hoàn tồn, xóa các bảng phụ thuộc rồi xóa phiếu trong một transaction."""
    conn.start_transaction()
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT TrangThaiPhieuKham FROM PhieuKhamBenh
            WHERE MaPhieuKhamBenh = %s FOR UPDATE
        """,
            (ma_phieu,),
        )
        row = cursor.fetchone()
        _phai_dang_kham(row[0] if row else None, "Phiếu khám")

        cursor.execute(
            """
            SELECT MaDonThuoc FROM DonThuoc
            WHERE MaPhieuKhamBenh = %s FOR UPDATE
        """,
            (ma_phieu,),
        )
        so_don = len(cursor.fetchall())

        cursor.execute(
            """
            SELECT ct.MaThuoc
            FROM ChiTietDonThuoc ct
            JOIN DonThuoc d ON ct.MaDonThuoc = d.MaDonThuoc
            WHERE d.MaPhieuKhamBenh = %s FOR UPDATE
        """,
            (ma_phieu,),
        )
        so_dong_thuoc = len(cursor.fetchall())

        # 5.1 — SQL gốc của Đức.
        cursor.execute(
            """
            UPDATE Thuoc t
            JOIN ChiTietDonThuoc ct ON t.MaThuoc = ct.MaThuoc
            JOIN DonThuoc d ON ct.MaDonThuoc = d.MaDonThuoc
            JOIN PhieuKhamBenh p ON d.MaPhieuKhamBenh = p.MaPhieuKhamBenh
            SET t.SoLuongCoSan = t.SoLuongCoSan + ct.SoLuongKe
            WHERE p.MaPhieuKhamBenh = %s AND p.TrangThaiPhieuKham = 'DANG_KHAM'
        """,
            (ma_phieu,),
        )
        _phai_dung_so_dong(cursor, so_dong_thuoc, "Hoàn tồn kho khi xóa phiếu chưa đủ")

        # 5.2 — SQL gốc của Đức.
        cursor.execute(
            """
            DELETE ct FROM ChiTietDonThuoc ct
            JOIN DonThuoc d ON ct.MaDonThuoc = d.MaDonThuoc
            JOIN PhieuKhamBenh p ON d.MaPhieuKhamBenh = p.MaPhieuKhamBenh
            WHERE p.MaPhieuKhamBenh = %s AND p.TrangThaiPhieuKham = 'DANG_KHAM'
        """,
            (ma_phieu,),
        )
        _phai_dung_so_dong(
            cursor, so_dong_thuoc, "Xóa chi tiết thuốc khi xóa phiếu chưa đủ"
        )

        cursor.execute(
            """
            DELETE d FROM DonThuoc d
            JOIN PhieuKhamBenh p ON d.MaPhieuKhamBenh = p.MaPhieuKhamBenh
            WHERE p.MaPhieuKhamBenh = %s AND p.TrangThaiPhieuKham = 'DANG_KHAM'
        """,
            (ma_phieu,),
        )
        _phai_dung_so_dong(cursor, so_don, "Xóa đầu đơn khi xóa phiếu chưa đủ")

        cursor.execute(
            """
            DELETE x FROM XetNghiem x
            JOIN PhieuKhamBenh p ON x.MaPhieuKhamBenh = p.MaPhieuKhamBenh
            WHERE p.MaPhieuKhamBenh = %s AND p.TrangThaiPhieuKham = 'DANG_KHAM'
        """,
            (ma_phieu,),
        )

        # 5.3 — SQL gốc của Đức.
        cursor.execute(
            """
            DELETE FROM PhieuKhamBenh
            WHERE MaPhieuKhamBenh = %s AND TrangThaiPhieuKham = 'DANG_KHAM'
        """,
            (ma_phieu,),
        )
        _phai_dung_so_dong(cursor, 1, "Không xóa được phiếu khám")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
