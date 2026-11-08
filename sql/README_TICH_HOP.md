# Bộ SQL của Đức — bản chỉnh tối thiểu

## Phạm vi chỉnh sửa

- `00_drop_tables.sql`: giữ nguyên byte-for-byte bản Đức gửi.
- `01_schema.sql`: giữ nguyên byte-for-byte bản Đức gửi.
- `02_triggers.sql`: giữ phần chặn đổi `MaThuoc` đã có; thêm `trg_PhieuKham_BeforeInsert` buộc phiếu mới là `DANG_KHAM`; bổ sung `trg_PhieuKham_BeforeUpdate` để chặn hoàn thành khi thiếu chẩn đoán, xét nghiệm chưa có kết quả/thời gian hoặc có đầu đơn thuốc rỗng. Các trigger khác giữ nguyên so với bản gửi lần này.
- `03_business_logic.sql`: lần này chỉ bổ sung phần 2: kiểm tra danh sách không rỗng, khóa phiếu, kiểm tra đủ số dòng chi tiết trước `COMMIT`; thêm một dòng ghi chú ở phần 6. Các câu SQL đã có và số lượng tham số của chúng giữ nguyên, gồm câu chốt phiếu và hai báo cáo.
- `transaction_handlers.py`: thêm `luu_don_thuoc_moi` để lưu đầu đơn, chi tiết và trừ tồn trong một transaction; từ chối danh sách rỗng trước khi ghi DB. Ba hàm `sua_so_luong_thuoc`, `xoa_don_thuoc`, `xoa_phieu_dang_kham` giữ nguyên so với bản gửi lần này.
- `README_TICH_HOP.md`: cập nhật cách gọi hàm lưu đơn và cách thay hai trigger trên CSDL đang có dữ liệu.
- `04_search_statistics.sql`, `seed.sql`, `test_sql02.sql` và tài liệu CSDL-01: giữ nguyên so với bản gửi lần này.

## Hướng dẫn cho Huy/Minh

```python
from transaction_handlers import (
    luu_don_thuoc_moi,
    sua_so_luong_thuoc,
    xoa_don_thuoc,
    xoa_phieu_dang_kham,
)

# conn là kết nối mysql.connector tới database quanlykhambenh.
# Các hàm tự bắt đầu/kết thúc giao dịch; KHÔNG gọi khi conn còn giao dịch khác.
luu_don_thuoc_moi(
    conn, "DT001", "PK001",
    [("T001", 2, "Theo chỉ định"), ("T002", 3, "Theo chỉ định")],
    loi_dan="Tái khám theo hẹn",
)
sua_so_luong_thuoc(conn, "DT001", "T001", 5, "Uống sau ăn")
xoa_don_thuoc(conn, "DT001")
xoa_phieu_dang_kham(conn, "PK001")
```

**Lưu ý quan trọng**

1. Không chạy riêng những câu `UPDATE Thuoc` và `DELETE` trong `03_business_logic.sql`: toàn bộ chuỗi phải nằm trong _cùng một transaction_. Chỉ `COMMIT` khi **tất cả** bước thành công; còn lỗi thì `ROLLBACK`.
2. `SELECT ... FOR UPDATE` chỉ có tác dụng giữ khóa trong transaction. Không tính chênh lệch số lượng từ bản ghi cũ tải trước trên giao diện.
3. Chặn đổi `MaThuoc` trực tiếp không đồng nghĩa bác sĩ phải nhập mã thuốc. Giao diện vẫn chọn tên thuốc; nếu muốn đổi loại thuốc, phải hoàn dòng cũ và thêm dòng mới bằng một giao dịch an toàn (chưa có hàm riêng cho thao tác đổi loại thuốc trong bộ chỉnh tối thiểu này).
4. `03_business_logic.sql` là **tập hợp các mẫu câu SQL có `%s`**, không phải file chạy một lần trong MySQL Workbench; mỗi câu phải được Python gọi với tuple tham số tương ứng.
5. Nút **Lưu đơn mới** phải gọi `luu_don_thuoc_moi` với danh sách `(ma_thuoc, so_luong, cach_dung)`. Danh sách phải có ít nhất một dòng. Khi bỏ thuốc cuối cùng, dùng luồng xóa cả đơn `xoa_don_thuoc`; không xóa riêng dòng cuối rồi lưu lại đầu đơn rỗng. Các luồng khác ngoài bốn hàm trên vẫn do phần tích hợp ứng dụng phụ trách.
6. **CSDL đã có dữ liệu/trigger:** trong `02_triggers.sql`, chỉ chạy khối từ `BẮT ĐẦU KHỐI CẬP NHẬT` đến `KẾT THÚC KHỐI CẬP NHẬT`. Khối này có hai cặp `DROP TRIGGER IF EXISTS` / `CREATE TRIGGER` cho `trg_PhieuKham_BeforeInsert` và `trg_PhieuKham_BeforeUpdate`. Chạy `USE quanlykhambenh;`, đặt `DELIMITER //` trước khối và `DELIMITER ;` sau khối. Không chạy lại toàn bộ file trên CSDL đã có các trigger khác; không cần chạy `00_drop_tables.sql` hay xóa dữ liệu để cập nhật.
7. Đầu đơn được phép **rỗng tạm thời trong transaction**, vì phải tạo đầu đơn trước khi thêm chi tiết. Kiểm tra không rỗng nằm ở hàm lưu trước `COMMIT`; trigger còn chặn hoàn thành phiếu nếu phát hiện đơn rỗng. MySQL không có trigger tại `COMMIT`, nên SQL viết tay tạo riêng đầu đơn rồi `COMMIT` bên ngoài hàm này vẫn có thể lưu đơn rỗng; không coi trigger là cơ chế cấm mọi giao dịch SQL tùy ý.
8. Trigger không kiểm tra được thay đổi chưa lưu trên màn hình hay quyền người đang thao tác. Hai nội dung đó vẫn phải kiểm tra tại ứng dụng. Phiếu không kê đơn/không có xét nghiệm vẫn được hoàn thành khi chẩn đoán hợp lệ.

## Kiểm chứng đã thực hiện

- Đã nạp nguyên schema và seed gửi kèm, cùng trigger đã sửa, trên **MySQL Community Server 8.0.46** tách biệt.
- **21 nhóm kiểm thử đều đạt**, gồm: danh sách thuốc rỗng/sai; lưu đủ hai thuốc; thiếu tồn ở thuốc thứ hai; lỗi CSDL khi lưu chi tiết thứ hai; rollback giữ nguyên tồn và không để lại đầu đơn; sửa/xóa đơn bằng ba hàm cũ.
- Trigger đã được kiểm tra với chẩn đoán `NULL`/rỗng/chỉ có khoảng trắng hoặc tab; xét nghiệm thiếu kết quả; đơn rỗng; phiếu hợp lệ không kê đơn; chèn trực tiếp phiếu hoàn thành; giữ khóa dữ liệu sau hoàn thành; câu chốt phiếu cũ và thao tác lặp. Có kiểm tra đọc dữ liệu mới được kết nối khác ghi sau snapshot cũ.
- Chạy nguyên `test_sql02.sql`: 8 ca tìm kiếm và 3 kỳ báo cáo đúng kết quả kỳ vọng; 18 dòng kiểm tra `DAT`, không có `SAI`; dữ liệu phiếu thử được rollback sạch.
- Đây là kiểm thử CSDL và hàm giao dịch; chưa kiểm thử tích hợp giao diện Tkinter/PDF của ứng dụng nhóm.
