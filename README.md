# Hệ thống quản lý khám bệnh ngoại trú và kê đơn

Ứng dụng desktop dùng Python Tkinter/ttk, MySQL Community Server và SQL trực
tiếp qua MySQL Connector/Python. Mỗi thành viên chạy MySQL cục bộ với cùng bộ
schema/seed; ứng dụng không tự tạo hoặc reset CSDL khi khởi động.

## Bộ công nghệ đã chốt trong CSDL-01 v1.5

- CPython 3.14.10 Windows x64, có Tcl/Tk và pip.
- MySQL Community Server 8.4.13 LTS, InnoDB; CSDL `btl_csdl`.
- `mysql-connector-python==26.10.0`, `use_pure=True`.
- `reportlab==4.4.10`; font Noto Sans và giấy phép SIL OFL đi kèm trong
  `assets/fonts/`.
- Cấu hình riêng từng máy trong `config.ini`; không dùng `python-dotenv`.

Các phiên bản runtime là đích nhóm chọn. CSDL-01 chưa được đánh dấu hoàn thành
cho đến khi cài và chạy thử trên máy nhóm theo các điều kiện nghiệm thu bên
dưới. Không commit kết quả thử chưa thực hiện.

## Cấu trúc

```text
app/
  config.py                         Đọc config.ini
  contracts.py                      Các kiểu dữ liệu/mã trạng thái dùng chung
  db.py                             get_connection() dùng chung
  errors.py                         AppError và chuyển lỗi MySQL
  pdf_export.py                     Hàm xuat_bang_pdf() dùng chung
  read_queries.py                   SQL SELECT dùng chung; cần Đức review/ghép
  services/
    don_thuoc_service.py            Ghi đơn, trừ/hoàn tồn trong một transaction
    tra_cuu_service.py              Đọc danh mục và chi tiết lần khám
  ui/
    app.py                          Cửa sổ Tk duy nhất
    shell.py                        Notebook 5 tab
    ke_don.py                       Form kê đơn
    views/                           Placeholder các màn hình đang chờ bàn giao
assets/fonts/                       NotoSans regular/bold và giấy phép
scripts/smoke_db_gui.py             Tkinter đọc MySQL thật
sql/                                Schema, view, seed, checks và migrations
tests/                              Kiểm thử tự động
config.example.ini                  Mẫu cấu hình không có mật khẩu thật
requirements.in                     Phụ thuộc trực tiếp
requirements.txt                    Bản khóa phụ thuộc đã cài/thử
main.py                             Điểm khởi chạy
```

Màn hình trong phạm vi là xét nghiệm, kê đơn, tìm kiếm lần khám, báo cáo lượt
khám và báo cáo tổng giá trị. Hiện chỉ form kê đơn có nội dung; các tab còn lại
hiển thị thông báo chờ thành viên phụ trách bàn giao, không hiển thị dữ liệu
giả. `read_queries.py` được thêm để đóng khung alias hợp đồng; Đức cần soát và
ghép với DDL/view cuối trước khi tích hợp chung.

## Cài đặt môi trường trên Windows

1. Cài CPython 3.14.10 x64, giữ Tcl/Tk, pip và Python launcher. Kiểm tra:

   ```powershell
   py -3.14 --version
   py -3.14 -m tkinter
   ```

2. Cài MySQL Community Server 8.4.13 LTS x64. Bootstrap CSDL tạo tài khoản ứng
   dụng `btl_app`; không cấu hình ứng dụng dùng tài khoản `root`.

3. Tạo virtual environment trong thư mục dự án và cài bản khóa:

   ```powershell
   py -3.14 -m venv .venv
   ./.venv/Scripts/python.exe -m pip install -r requirements.txt
   ./.venv/Scripts/python.exe -m pip check
   ```

4. Sao chép mẫu cấu hình và chỉ sửa bản cục bộ:

   ```powershell
   Copy-Item config.example.ini config.ini
   ```

   Điền đúng host, port, database, user và mật khẩu MySQL của máy vào
   `config.ini`. Mật khẩu có thể chứa ký tự `%`. Không commit `config.ini`;
   `.gitignore` đã bỏ qua file này.

## Tạo CSDL demo

Sau khi Đức/Hoàng bàn giao đủ script, mở MySQL CLI với tài khoản quản trị và
chạy một lần theo thứ tự:

```sql
SOURCE <duong-dan-du-an>/sql/00_bootstrap.sql;
SOURCE <duong-dan-du-an>/sql/01_schema.sql;
SOURCE <duong-dan-du-an>/sql/02_views.sql;
SOURCE <duong-dan-du-an>/sql/03_seed.sql;
SOURCE <duong-dan-du-an>/sql/04_checks.sql;
USE btl_csdl;
SELECT VERSION(), DATABASE();
SELECT MaKhoa, TenKhoa FROM Khoa ORDER BY MaKhoa LIMIT 3;
```

Các script SQL trên hiện chưa được nhóm bàn giao trong repository; do đó chưa
thể dựng/khôi phục CSDL demo hoặc xác nhận truy vấn thật. Không chạy lại seed
trên CSDL đã có dữ liệu. Với thay đổi schema về sau, áp dụng migration cho
CSDL cũ; không chạy migration cũ lên CSDL mới đã dựng từ schema hiện tại.

## Chạy ứng dụng và kiểm tra kết nối

```powershell
./.venv/Scripts/python.exe main.py
```

`main.py` tạo một Tk và một Notebook 5 tab. Ứng dụng không tự nạp seed hoặc tự
reset CSDL.

Khi đã có `config.ini`, schema và ít nhất một dòng Khoa, kiểm tra Tkinter đọc
dữ liệu MySQL thật:

```powershell
./.venv/Scripts/python.exe scripts/smoke_db_gui.py
```

Đạt yêu cầu khi cửa sổ hiển thị phiên bản MySQL, tên CSDL và các dòng Khoa đọc
từ bảng; đổi tên Khoa trong MySQL rồi bấm “Đọc lại MySQL” phải thấy giá trị mới.
Hiện chưa có `config.ini`/schema dùng chung và chưa ghi nhận bằng chứng chạy,
nên smoke test thật **chưa chạy**.

## Quy tắc kê đơn và tồn kho

- Tạo đơn cần mã đơn nhập tay; không dùng `AUTO_INCREMENT`, `lastrowid` hoặc
  sinh mã từ `MAX()+1`.
- UI gửi toàn bộ danh sách thuốc nháp. Service đọc lại đơn và tồn dưới khóa
  transaction; chỉ trừ phần chênh lệch khi sửa.
- Giá thuốc đã lưu được giữ nguyên; thuốc mới dùng giá danh mục lúc lưu.
- Đầu đơn, dòng chi tiết và tồn cùng một transaction; lỗi trước commit rollback
  toàn bộ. Thuốc được khóa theo mã tăng dần; không retry ngầm.
- Giảm/bỏ thuốc đã lưu hoặc xóa đơn yêu cầu xác nhận giả định hoàn tồn; danh
  mục thuốc được tải lại sau khi ghi.
- Dữ liệu demo phải seed tồn cuối đã phản ánh các đơn mẫu, không gọi lại service
  để trừ tồn lần nữa.

## Khôi phục bộ dữ liệu demo

Quy trình này chỉ dành cho CSDL demo mới/rỗng. Trước khi dựng lại, dừng ứng dụng
và phiên ghi, xác nhận đúng CSDL cần khôi phục, sao lưu dữ liệu cần giữ; sau đó
chạy bootstrap, schema, view, seed đúng một lần và checks. Đối chiếu kết quả
seed đã được nhóm chốt: tồn thuốc 1 là 7, thuốc 2 là 6; tháng 10/2026 tổng
390.000 VNĐ, tháng 11/2026 là 140.000 VNĐ, tổng năm 530.000 VNĐ. Những số liệu
này là kỳ vọng tài liệu, chưa phải kết quả chạy hiện tại. Không sửa tay tồn để
làm khớp con số; sửa bộ seed/SQL rồi khôi phục lại từ đầu.

## Kiểm thử

```powershell
./.venv/Scripts/python.exe -m unittest discover -s tests -v
```

Kiểm thử tự động không thay thế các ca nghiệm thu MySQL TON-01..TON-14. Các ca
transaction/rollback/đồng thời chỉ được ghi PASS sau khi chạy trên CSDL MySQL
được dựng từ đúng script dùng chung và lưu bằng chứng trước/sau.

## Quy trình Git của nhóm

- Dùng một repository; `main` chỉ nhận thay đổi đã review.
- Mỗi nhiệm vụ làm trên nhánh `feature/<ma-cong-viec>-<ten-ngan>`, liên kết Issue
  và mở PR có ít nhất một reviewer khác tác giả.
- Thay đổi schema qua migration; đồng thời cập nhật script dựng CSDL mới.
- Không commit `.venv`, `config.ini`, log hoặc PDF đầu ra.
