# Hệ thống quản lý khám bệnh ngoại trú và kê đơn

Ứng dụng desktop Python Tkinter kết nối MySQL. Phạm vi giao diện dự kiến gồm
form xét nghiệm, form kê đơn, tìm kiếm lần khám và hai báo cáo.

## Cấu trúc dự án

```text
app/
  config.py                 Cấu hình kết nối từ biến môi trường
  db.py                     Kết nối MySQL và transaction
  report_export.py          Xuất PDF dùng chung cho hai báo cáo
  services/                 Nghiệp vụ và truy vấn SQL có tham số
  ui/
    app.py                  Cửa sổ chính và điều hướng
    components/             Widget Tkinter dùng chung
    views/                  Các màn hình nghiệp vụ
sql/
  001_schema.sql            Lược đồ và ràng buộc CSDL
  002_views.sql             View/truy vấn dùng chung
  003_seed.sql              Dữ liệu demo
  migrations/               Các thay đổi CSDL về sau
docs/                       ERD, quy ước và tài liệu dự án
tests/                      Kiểm thử cấu hình, SQL và nghiệp vụ
main.py                     Điểm khởi chạy ứng dụng
```

Các màn hình nghiệp vụ và script SQL đang là phần việc sẽ được bổ sung theo
phân công của nhóm.

## Chạy ứng dụng

1. Cài Python và MySQL Server; tạo CSDL theo tên nhóm thống nhất.
2. Tạo môi trường ảo và cài dependencies:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

3. Khai báo cấu hình MySQL trong PowerShell trước khi chạy:

   ```powershell
   $env:DB_HOST = "127.0.0.1"
   $env:DB_PORT = "3306"
   $env:DB_USER = "root"
   $env:DB_PASSWORD = "mat_khau_mysql"
   $env:DB_NAME = "quanlykhambenh"
   ```

4. Khởi chạy giao diện:

   ```powershell
   python main.py
   ```

Biến `DB_PASSWORD` được để ngoài mã nguồn; không commit thông tin đăng nhập.
Các màn hình hiện hiển thị khung điều hướng, chưa thực hiện truy vấn nghiệp vụ.
Xuất PDF dùng chung `app/report_export.py`; cần có font Arial, Segoe UI hoặc
DejaVu Sans trên máy chạy ứng dụng để hiển thị tiếng Việt.

## Kiểm thử

```powershell
python -m unittest discover -s tests -v
```