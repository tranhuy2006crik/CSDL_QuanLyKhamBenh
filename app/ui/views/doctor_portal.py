import tkinter as tk
from datetime import date
from decimal import Decimal
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from app.contracts import BaoCaoBacSiRow, BacSiDTO, BenhNhanDTO
from app.errors import AppError
from app.pdf_export import xuat_bang_pdf
from app.services.clinic_service import bao_cao_bac_si, lay_khoa
from app.ui.views.common import dinh_dang_tien, hien_loi, tao_bang
from app.ui.views.appointment_views import DoctorAppointmentView
from app.ui.views.patient_search_view import PatientSearchView

ALL_DEPARTMENTS = "Tất cả khoa"
ALL_DOCTORS = "Tất cả bác sĩ"


class DoctorPortal(ttk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        doctor: BacSiDTO,
        on_logout,
    ) -> None:
        super().__init__(parent, padding=10)
        self.doctor = doctor
        self.on_logout = on_logout
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header.columnconfigure(0, weight=1)
        ttk.Label(
            header,
            text=f'Khu vực bác sĩ — {doctor["ten_bac_si"]} (Mã {doctor["ma_bac_si"]})',
            font=("TkDefaultFont", 15, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ttk.Button(header, text="Đổi vai trò / đăng xuất", command=on_logout).grid(
            row=0, column=1, sticky="e"
        )

        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=1, column=0, sticky="nsew")

        # Truyền trực tiếp mã bác sĩ vào PatientSearchView thay vì callback
        self.patient_view = PatientSearchView(
            self.notebook, ma_bac_si=self.doctor["ma_bac_si"]
        )

        self.report_view = DoctorReportView(self.notebook)
        self.appointment_view = DoctorAppointmentView(self.notebook, doctor)

        self.notebook.add(self.patient_view, text="Tra cứu bệnh nhân & Hồ sơ")
        self.notebook.add(self.appointment_view, text="Lịch hẹn")
        self.notebook.add(self.report_view, text="Báo cáo bác sĩ")


class DoctorReportView(ttk.Frame):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, padding=12)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)
        today = date.today()

        ttk.Label(
            self,
            text="THỐNG KÊ KHÁM BỆNH THEO BÁC SĨ",
            font=("TkDefaultFont", 16, "bold"),
        ).grid(row=0, column=0, sticky="w")

        controls = ttk.LabelFrame(self, text="Kỳ báo cáo và bộ lọc", padding=8)
        controls.grid(row=1, column=0, sticky="ew", pady=8)

        ttk.Label(controls, text="Tháng").grid(row=0, column=0, sticky="w")
        self.month = ttk.Combobox(
            controls,
            state="readonly",
            width=5,
            values=[str(month) for month in range(1, 13)],
        )
        self.month.set(str(today.month))
        self.month.grid(row=0, column=1, padx=5)

        ttk.Label(controls, text="Năm").grid(row=0, column=2, sticky="w")
        self.year = ttk.Entry(controls, width=8)
        self.year.insert(0, str(today.year))
        self.year.grid(row=0, column=3, padx=5)

        ttk.Label(controls, text="Khoa").grid(row=0, column=4, sticky="w")
        self.department = ttk.Combobox(controls, state="readonly", width=24)
        self.department.grid(row=0, column=5, padx=5)

        ttk.Label(controls, text="Mã/tên bác sĩ").grid(
            row=0, column=6, sticky="w", padx=(8, 0)
        )
        self.keyword = ttk.Entry(controls, width=22)
        self.keyword.grid(row=0, column=7, padx=5)

        self.include_empty = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            controls, text="Hiện bác sĩ không có lượt khám", variable=self.include_empty
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(8, 0))
        ttk.Button(controls, text="Xem thống kê", command=self._refresh).grid(
            row=1, column=7, sticky="e", pady=(8, 0)
        )

        self.departments: dict[str, int | None] = {ALL_DEPARTMENTS: None}
        self._load_departments()

        content_frame = ttk.Frame(self)
        content_frame.grid(row=3, column=0, sticky="nsew")
        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=1)
        content_frame.rowconfigure(0, weight=1)

        # -- BẢNG DỮ LIỆU BÊN TRÁI --
        table_frame = ttk.Frame(content_frame)
        table_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        columns = ("ma_bac_si", "ten_bac_si", "so_luot_kham", "tong_gia_tri")
        self.table = tao_bang(
            table_frame,
            columns,
            {
                "ma_bac_si": "Mã BS",
                "ten_bac_si": "Bác sĩ",
                "so_luot_kham": "Số lượt",
                "tong_gia_tri": "Tổng giá trị (VNĐ)",
            },
            {
                "ma_bac_si": 70,
                "ten_bac_si": 180,
                "so_luot_kham": 90,
                "tong_gia_tri": 140,
            },
        )

        # --- CĂN LỀ CHUẨN BÁO CÁO THỐNG KÊ ---
        self.table.column("ma_bac_si", anchor="center")  # Mã -> Căn giữa
        self.table.column("ten_bac_si", anchor="w")  # Tên -> Căn trái (mặc định)
        self.table.column(
            "so_luot_kham", anchor="center"
        )  # Số lượng -> Căn giữa (hoặc phải)
        self.table.column("tong_gia_tri", anchor="e")  # Tiền tệ -> Căn phải

        self.table.grid(row=0, column=0, sticky="nsew")
        table_scroll = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.table.yview
        )
        table_scroll.grid(row=0, column=1, sticky="ns")
        self.table.configure(yscrollcommand=table_scroll.set)

        chart_frame = ttk.LabelFrame(
            content_frame, text="Top 5 Bác sĩ theo Tháng", padding=8
        )
        chart_frame.grid(row=0, column=1, sticky="nsew")
        chart_frame.rowconfigure(0, weight=1)
        chart_frame.columnconfigure(0, weight=1)

        self.chart = tk.Canvas(chart_frame, background="white", highlightthickness=0)
        self.chart.grid(row=0, column=0, sticky="nsew")
        self.chart.bind("<Configure>", self._draw_chart)

        legend_frame = ttk.Frame(chart_frame)
        legend_frame.grid(row=1, column=0, sticky="w", pady=(8, 0))
        tk.Label(legend_frame, text="■", fg="#3498db", font=("Arial", 12)).pack(
            side="left"
        )
        ttk.Label(legend_frame, text="Số lượt khám").pack(side="left", padx=(0, 16))
        tk.Label(legend_frame, text="■", fg="#e74c3c", font=("Arial", 12)).pack(
            side="left"
        )
        ttk.Label(legend_frame, text="Tổng giá trị khám").pack(side="left")

        footer = ttk.Frame(self)
        footer.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(footer, text="Xuất báo cáo PDF", command=self._export_pdf).pack(
            side="right"
        )

        self.rows: list[BaoCaoBacSiRow] = []
        self._refresh()

    def _load_departments(self) -> None:
        try:
            departments = lay_khoa()
        except Exception as error:
            hien_loi(self, error)
            return
        self.departments.update(
            {
                f'{row["ten_khoa"]} (Mã {row["ma_khoa"]})': row["ma_khoa"]
                for row in departments
            }
        )
        self.department["values"] = list(self.departments)
        self.department.set(ALL_DEPARTMENTS)

    def _refresh(self) -> None:
        try:
            month = int(self.month.get())
            year = int(self.year.get().strip())
            rows = bao_cao_bac_si(
                month,
                year,
                ma_khoa=self.departments.get(self.department.get()),
                tu_khoa=self.keyword.get(),
                hien_bac_si_rong=self.include_empty.get(),
            )
        except Exception as error:
            hien_loi(self, error)
            return

        self.rows = rows
        for item in self.table.get_children():
            self.table.delete(item)

        for row in rows:
            self.table.insert(
                "",
                "end",
                iid=str(row["ma_bac_si"]),
                values=(
                    row["ma_bac_si"],
                    row["ten_bac_si"],
                    row["so_luot_kham"],
                    dinh_dang_tien(row["tong_gia_tri"]),
                ),
            )
        self._draw_chart()

    def _draw_chart(self, _event: tk.Event | None = None) -> None:
        if not hasattr(self, "chart"):
            return
        canvas = self.chart
        canvas.delete("all")
        width = max(canvas.winfo_width(), 400)
        height = max(canvas.winfo_height(), 250)

        valid_rows = [r for r in self.rows if Decimal(str(r["tong_gia_tri"] or 0)) > 0]
        rows = sorted(
            valid_rows, key=lambda x: Decimal(str(x["tong_gia_tri"])), reverse=True
        )[:5]

        if not rows:
            canvas.create_text(
                width // 2,
                height // 2,
                text="Không có dữ liệu lượt khám để vẽ biểu đồ.",
            )
            return

        max_visits = max(int(row["so_luot_kham"]) for row in rows) or 1
        max_value = max(
            Decimal(str(row["tong_gia_tri"] or 0)) for row in rows
        ) or Decimal("1")
        y_offset = 20
        group_height = (height - 40) // max(len(rows), 1)
        bar_height = 14

        for row in rows:
            name = f"{row['ma_bac_si']} - {row['ten_bac_si']}"
            canvas.create_text(
                10, y_offset, text=name, anchor="w", font=("Arial", 9, "bold")
            )
            visit_val = int(row["so_luot_kham"])
            value_val = Decimal(str(row["tong_gia_tri"] or 0))
            w_visit = int((width - 120) * (visit_val / max_visits))
            w_value = int((width - 120) * float(value_val / max_value))

            canvas.create_rectangle(
                10,
                y_offset + 15,
                10 + max(2, w_visit),
                y_offset + 15 + bar_height,
                fill="#3498db",
                outline="",
            )
            canvas.create_text(
                10 + w_visit + 5,
                y_offset + 15 + bar_height // 2,
                text=f"{visit_val} lượt",
                anchor="w",
                fill="#7f8c8d",
            )

            canvas.create_rectangle(
                10,
                y_offset + 32,
                10 + max(2, w_value),
                y_offset + 32 + bar_height,
                fill="#e74c3c",
                outline="",
            )
            canvas.create_text(
                10 + w_value + 5,
                y_offset + 32 + bar_height // 2,
                text=dinh_dang_tien(value_val),
                anchor="w",
                fill="#7f8c8d",
            )
            y_offset += group_height

    def _export_pdf(self) -> None:
        messagebox.showinfo(
            "Thông báo",
            "Tính năng xuất PDF đang chờ team APP-01 hoàn thiện API dùng chung.",
            parent=self,
        )
