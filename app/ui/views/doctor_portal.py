import tkinter as tk
from datetime import date
from decimal import Decimal
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from app.contracts import BaoCaoBacSiRow, BacSiDTO, BenhNhanDTO
from app.errors import AppError
from app.pdf_export import xuat_bang_pdf
from app.services.clinic_service import (
    bao_cao_bac_si,
    lay_danh_sach_bac_si,
    lay_khoa,
    lay_lich_su_benh_nhan,
    lay_tien_su_benh,
    tim_kiem_benh_nhan,
)
from app.ui.views.common import dinh_dang_tien, hien_loi, tao_bang
from app.ui.views.appointment_views import DoctorAppointmentView
from app.ui.views.visit_dialogs import PhieuKhamDetailDialog, TaoPhieuKhamDialog


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
        self.patient_view = DoctorPatientSearchView(
            self.notebook,
            doctor,
        )
        self.report_view = DoctorReportView(self.notebook)
        self.appointment_view = DoctorAppointmentView(self.notebook, doctor)
        self.notebook.add(self.patient_view, text="Bệnh nhân")
        self.notebook.add(self.appointment_view, text="Lịch hẹn")
        self.notebook.add(self.report_view, text="Báo cáo bác sĩ")


class DoctorPatientSearchView(ttk.Frame):
    def __init__(self, parent: tk.Misc, doctor: BacSiDTO) -> None:
        super().__init__(parent, padding=12)
        self.doctor = doctor
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self.departments: dict[str, int | None] = {ALL_DEPARTMENTS: None}
        self.doctors: dict[str, int | None] = {ALL_DOCTORS: None}

        ttk.Label(
            self,
            text="Tra cứu bệnh nhân",
            font=("TkDefaultFont", 16, "bold"),
        ).grid(row=0, column=0, sticky="w")
        filters = ttk.LabelFrame(self, text="Tìm kiếm và lọc", padding=8)
        filters.grid(row=1, column=0, sticky="ew", pady=8)
        filters.columnconfigure(1, weight=1)
        ttk.Label(filters, text="Từ khóa").grid(row=0, column=0, sticky="w")
        self.keyword = ttk.Entry(filters)
        self.keyword.grid(row=0, column=1, sticky="ew", padx=6)
        self.keyword.bind("<Return>", self._search_event)
        ttk.Label(filters, text="Khoa").grid(row=0, column=2, sticky="w", padx=(8, 0))
        self.department = ttk.Combobox(filters, state="readonly", width=24)
        self.department.grid(row=0, column=3, padx=6)
        self.department.bind("<<ComboboxSelected>>", self._department_changed)
        ttk.Label(filters, text="Bác sĩ").grid(row=0, column=4, sticky="w", padx=(8, 0))
        self.doctor_choice = ttk.Combobox(filters, state="readonly", width=28)
        self.doctor_choice.grid(row=0, column=5, padx=6)
        ttk.Button(filters, text="Tìm", command=self._search).grid(
            row=0, column=6, padx=(8, 0)
        )
        ttk.Label(
            filters,
            text="Tìm theo mã, họ tên, số điện thoại hoặc địa chỉ. Lọc khoa/bác sĩ dựa trên lịch sử phiếu khám.",
            wraplength=950,
        ).grid(row=1, column=0, columnspan=7, sticky="w", pady=(6, 0))

        table_frame = ttk.Frame(self)
        table_frame.grid(row=2, column=0, sticky="nsew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        columns = (
            "ma_bn",
            "ho_ten",
            "dien_thoai",
            "nam_sinh",
            "gioi_tinh",
            "dia_chi",
        )
        self.table = tao_bang(
            table_frame,
            columns,
            {
                "ma_bn": "Mã bệnh nhân",
                "ho_ten": "Họ tên",
                "dien_thoai": "Số điện thoại",
                "nam_sinh": "Năm sinh",
                "gioi_tinh": "Giới tính",
                "dia_chi": "Địa chỉ",
            },
            {
                "ma_bn": 110,
                "ho_ten": 200,
                "dien_thoai": 145,
                "nam_sinh": 90,
                "gioi_tinh": 100,
                "dia_chi": 300,
            },
        )
        self.table.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.table.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.bind("<Double-1>", self._open_selected)

        actions = ttk.Frame(self)
        actions.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(
            actions,
            text="Xem hồ sơ bệnh án",
            command=self._open_selected,
        ).pack(side="left")
        ttk.Button(actions, text="Tải lại", command=self._search).pack(
            side="left", padx=8
        )
        ttk.Label(
            actions,
            text="Danh sách chỉ gồm bệnh nhân đã được nhập sẵn vào CSDL.",
        ).pack(side="right")
        self._load_filters()
        self._search()

    def _load_filters(self) -> None:
        try:
            departments = lay_khoa()
            doctors = lay_danh_sach_bac_si()
        except Exception as error:
            hien_loi(self, error)
            return
        self.departments = {ALL_DEPARTMENTS: None}
        self.departments.update(
            {
                f'{row["ten_khoa"]} (Mã {row["ma_khoa"]})': row["ma_khoa"]
                for row in departments
            }
        )
        self.department["values"] = list(self.departments)
        self.department.set(ALL_DEPARTMENTS)
        self._set_doctors(doctors)

    def _set_doctors(self, doctors: list[BacSiDTO]) -> None:
        self.doctors = {ALL_DOCTORS: None}
        self.doctors.update(
            {
                f'{row["ten_bac_si"]} (Mã {row["ma_bac_si"]})': row["ma_bac_si"]
                for row in doctors
            }
        )
        self.doctor_choice["values"] = list(self.doctors)
        if self.doctor_choice.get() not in self.doctors:
            self.doctor_choice.set(ALL_DOCTORS)

    def _department_changed(self, _event: tk.Event | None = None) -> None:
        department_id = self.departments.get(self.department.get())
        try:
            self._set_doctors(lay_danh_sach_bac_si(department_id))
        except Exception as error:
            hien_loi(self, error)

    def _search_event(self, _event: tk.Event) -> None:
        self._search()

    def _search(self) -> None:
        department_id = self.departments.get(self.department.get())
        doctor_id = self.doctors.get(self.doctor_choice.get())
        try:
            patients = tim_kiem_benh_nhan(
                self.keyword.get(),
                ma_khoa=department_id,
                ma_bac_si=doctor_id,
            )
        except Exception as error:
            hien_loi(self, error)
            return
        for item in self.table.get_children():
            self.table.delete(item)
        for patient in patients:
            self.table.insert(
                "",
                "end",
                iid=str(patient["ma_benh_nhan"]),
                values=(
                    patient["ma_benh_nhan"],
                    patient["ho_ten"],
                    patient["so_dien_thoai"] or "—",
                    patient["nam_sinh"] or "—",
                    patient["gioi_tinh"] or "—",
                    patient["dia_chi"] or "—",
                ),
            )

    def _open_selected(self, _event: tk.Event | None = None) -> None:
        selection = self.table.selection()
        if not selection:
            messagebox.showinfo(
                "Hồ sơ bệnh án", "Hãy chọn một bệnh nhân.", parent=self
            )
            return
        patient_id = int(selection[0])
        values = self.table.item(selection[0], "values")
        patient = {
            "ma_benh_nhan": patient_id,
            "ho_ten": values[1],
            "so_dien_thoai": values[2],
            "nam_sinh": values[3],
            "ngay_sinh": None,
            "gioi_tinh": values[4],
            "dia_chi": values[5],
        }
        PatientHistoryDialog(self, patient, self.doctor["ma_bac_si"])


class PatientHistoryDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        patient: BenhNhanDTO,
        ma_bac_si: int,
    ) -> None:
        super().__init__(parent)
        self.title(f'Hồ sơ bệnh án — {patient["ho_ten"]}')
        self.geometry("1000x650")
        self.minsize(820, 520)
        self.transient(parent)
        self.patient = patient
        self.ma_bac_si = ma_bac_si
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        ttk.Label(
            self,
            text=(
                f'Hồ sơ bệnh án: {patient["ho_ten"]} '
                f'(Mã bệnh nhân {patient["ma_benh_nhan"]})'
            ),
            font=("TkDefaultFont", 14, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=12)
        self.medical_history = ttk.Label(
            self, text="Tiền sử bệnh: —", wraplength=950, justify="left"
        )
        self.medical_history.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        table_frame = ttk.Frame(self, padding=(12, 0))
        table_frame.grid(row=2, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        columns = ("ma_phieu", "ngay_gio", "bac_si", "khoa", "chan_doan", "tong")
        self.table = tao_bang(
            table_frame,
            columns,
            {
                "ma_phieu": "Mã phiếu",
                "ngay_gio": "Ngày giờ khám",
                "bac_si": "Bác sĩ",
                "khoa": "Khoa",
                "chan_doan": "Chẩn đoán",
                "tong": "Tổng chi phí",
            },
            {
                "ma_phieu": 90,
                "ngay_gio": 150,
                "bac_si": 170,
                "khoa": 130,
                "chan_doan": 230,
                "tong": 150,
            },
        )
        self.table.grid(row=0, column=0, sticky="nsew")
        self.table.bind("<Double-1>", self._open_selected)
        actions = ttk.Frame(self, padding=12)
        actions.grid(row=3, column=0, sticky="ew")
        ttk.Button(
            actions, text="Xem chi tiết phiếu", command=self._open_selected
        ).pack(side="left")
        ttk.Button(
            actions,
            text="Tạo phiếu khám",
            command=self._create_visit,
        ).pack(side="left", padx=8)
        ttk.Button(actions, text="Đóng", command=self.destroy).pack(side="right")
        self._refresh()

    def _refresh(self) -> None:
        try:
            visits = lay_lich_su_benh_nhan(self.patient["ma_benh_nhan"])
            medical_history = lay_tien_su_benh(self.patient["ma_benh_nhan"])
        except Exception as error:
            hien_loi(self, error)
            return
        self.medical_history.configure(
            text=f"Tiền sử bệnh: {medical_history or 'Chưa ghi nhận.'}"
        )
        for item in self.table.get_children():
            self.table.delete(item)
        for visit in visits:
            self.table.insert(
                "",
                "end",
                iid=str(visit["ma_phieu"]),
                values=(
                    visit["ma_phieu"],
                    visit["ngay_gio_kham"].strftime("%d/%m/%Y %H:%M"),
                    visit["ten_bac_si"],
                    visit["ten_khoa"],
                    visit["chan_doan"] or "—",
                    dinh_dang_tien(visit["tong_chi_phi"]),
                ),
            )

    def _open_selected(self, _event: tk.Event | None = None) -> None:
        selection = self.table.selection()
        if not selection:
            messagebox.showinfo(
                "Phiếu khám", "Hãy chọn một phiếu khám.", parent=self
            )
            return
        PhieuKhamDetailDialog(
            self,
            int(selection[0]),
            read_only=False,
            on_changed=self._refresh,
        )

    def _create_visit(self) -> None:
        dialog = TaoPhieuKhamDialog(
            self,
            self.patient["ma_benh_nhan"],
            self.ma_bac_si,
            self.patient["ho_ten"],
        )
        self.wait_window(dialog)
        if dialog.result is None:
            return
        self._refresh()
        PhieuKhamDetailDialog(
            self,
            dialog.result,
            read_only=False,
            on_changed=self._refresh,
        )


class DoctorReportView(ttk.Frame):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, padding=12)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)
        today = date.today()

        ttk.Label(
            self,
            text="Báo cáo giá trị khám theo bác sĩ",
            font=("TkDefaultFont", 16, "bold"),
        ).grid(row=0, column=0, sticky="w")
        controls = ttk.LabelFrame(self, text="Kỳ báo cáo và bộ lọc", padding=8)
        controls.grid(row=1, column=0, sticky="ew", pady=8)
        ttk.Label(controls, text="Tháng").grid(row=0, column=0, sticky="w")
        self.month = ttk.Combobox(
            controls, state="readonly", width=5, values=[str(month) for month in range(1, 13)]
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
            controls,
            text="Hiện bác sĩ không có lượt khám",
            variable=self.include_empty,
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(8, 0))
        ttk.Button(controls, text="Xem thống kê", command=self._refresh).grid(
            row=1, column=7, sticky="e", pady=(8, 0)
        )
        self.departments: dict[str, int | None] = {ALL_DEPARTMENTS: None}
        self._load_departments()

        summary = ttk.Frame(self, padding=8, relief="groove")
        summary.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        for column in range(3):
            summary.columnconfigure(column, weight=1)
        self.summary_doctors = ttk.Label(summary, text="Bác sĩ: 0")
        self.summary_doctors.grid(row=0, column=0, sticky="w")
        self.summary_visits = ttk.Label(summary, text="Tổng lượt khám: 0")
        self.summary_visits.grid(row=0, column=1, sticky="w")
        self.summary_value = ttk.Label(
            summary, text="Tổng giá trị: 0 VNĐ", font=("TkDefaultFont", 10, "bold")
        )
        self.summary_value.grid(row=0, column=2, sticky="e")

        content = ttk.Panedwindow(self, orient="vertical")
        content.grid(row=3, column=0, sticky="nsew")
        table_frame = ttk.Frame(content)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        columns = ("ma_bac_si", "ten_bac_si", "khoa", "so_luot_kham", "tong_gia_tri")
        self.table = tao_bang(
            table_frame,
            columns,
            {
                "ma_bac_si": "Mã bác sĩ",
                "ten_bac_si": "Bác sĩ",
                "khoa": "Khoa",
                "so_luot_kham": "Số lượt khám",
                "tong_gia_tri": "Tổng giá trị khám",
            },
            {
                "ma_bac_si": 100,
                "ten_bac_si": 220,
                "khoa": 190,
                "so_luot_kham": 130,
                "tong_gia_tri": 210,
            },
        )
        self.table.grid(row=0, column=0, sticky="nsew")
        table_scroll = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.table.yview
        )
        table_scroll.grid(row=0, column=1, sticky="ns")
        self.table.configure(yscrollcommand=table_scroll.set)
        chart_frame = ttk.LabelFrame(
            content, text="Top 8 bác sĩ theo tổng giá trị khám"
        )
        chart_frame.rowconfigure(0, weight=1)
        chart_frame.columnconfigure(0, weight=1)
        self.chart = tk.Canvas(
            chart_frame, height=230, background="white", highlightthickness=0
        )
        self.chart.grid(row=0, column=0, sticky="nsew")
        self.chart.bind("<Configure>", self._draw_chart)
        content.add(table_frame, weight=3)
        content.add(chart_frame, weight=2)

        footer = ttk.Frame(self)
        footer.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        ttk.Label(
            footer,
            text="Chi phí ghi nhận = giá khám áp dụng + xét nghiệm + thuốc; không phản ánh thanh toán.",
        ).pack(side="left")
        ttk.Button(
            footer, text="Xuất báo cáo PDF", command=self._export_pdf
        ).pack(side="right")
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
        except ValueError:
            hien_loi(
                self,
                AppError("DU_LIEU_KHONG_HOP_LE", "Năm phải là số nguyên.", "nam"),
            )
            return
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
                    row["ten_khoa"],
                    row["so_luot_kham"],
                    dinh_dang_tien(row["tong_gia_tri"]),
                ),
            )
        total_amount = sum(
            (Decimal(str(row["tong_gia_tri"] or 0)) for row in rows),
            Decimal("0"),
        )
        total_visits = sum(int(row["so_luot_kham"]) for row in rows)
        self.summary_doctors.configure(text=f"Số bác sĩ: {len(rows)}")
        self.summary_visits.configure(text=f"Tổng lượt khám: {total_visits}")
        self.summary_value.configure(
            text=f"Tổng giá trị khám: {dinh_dang_tien(total_amount)}"
        )
        self._draw_chart()

    def _draw_chart(self, _event: tk.Event | None = None) -> None:
        if not hasattr(self, "chart"):
            return
        canvas = self.chart
        canvas.delete("all")
        width = max(canvas.winfo_width(), 500)
        height = max(canvas.winfo_height(), 180)
        rows = self.rows[:8]
        if not rows:
            canvas.create_text(
                width // 2, height // 2, text="Không có dữ liệu cho bộ lọc hiện tại."
            )
            return
        max_value = max(Decimal(str(row["tong_gia_tri"] or 0)) for row in rows)
        max_value = max_value or Decimal("1")
        label_width = min(220, width // 3)
        value_width = 140
        chart_width = max(30, width - label_width - value_width - 35)
        top = 18
        row_height = max(14, min(34, (height - 24) // len(rows)))
        for index, row in enumerate(rows):
            y = top + index * row_height
            name = str(row["ten_bac_si"])
            if len(name) > 28:
                name = name[:25] + "..."
            canvas.create_text(
                8, y + row_height // 2, text=name, anchor="w", fill="#20354A"
            )
            value = Decimal(str(row["tong_gia_tri"] or 0))
            bar_length = int(chart_width * value / max_value)
            if value > 0:
                canvas.create_rectangle(
                    label_width,
                    y + 5,
                    label_width + max(2, bar_length),
                    y + row_height - 5,
                    fill="#168AAD",
                    outline="",
                )
            canvas.create_text(
                label_width + chart_width + 10,
                y + row_height // 2,
                text=dinh_dang_tien(value),
                anchor="w",
                fill="#20354A",
            )

    def _export_pdf(self) -> None:
        if not self.rows:
            messagebox.showinfo(
                "Xuất báo cáo", "Không có dữ liệu để xuất.", parent=self
            )
            return
        path_text = filedialog.asksaveasfilename(
            parent=self,
            title="Lưu báo cáo bác sĩ",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"bao_cao_bac_si_{self.year.get()}_{self.month.get()}.pdf",
        )
        if not path_text:
            return
        filters = [
            f'Tháng {self.month.get()}/{self.year.get()}',
            f'Khoa: {self.department.get() or ALL_DEPARTMENTS}',
        ]
        if self.keyword.get().strip():
            filters.append(f'Bác sĩ: {self.keyword.get().strip()}')
        try:
            xuat_bang_pdf(
                Path(path_text),
                "BÁO CÁO GIÁ TRỊ KHÁM THEO BÁC SĨ",
                "; ".join(filters),
                [
                    {"key": "ma_bac_si", "label": "Mã BS", "kind": "int"},
                    {"key": "ten_bac_si", "label": "Bác sĩ", "kind": "text"},
                    {"key": "ten_khoa", "label": "Khoa", "kind": "text"},
                    {
                        "key": "so_luot_kham",
                        "label": "Số lượt khám",
                        "kind": "int",
                    },
                    {
                        "key": "tong_gia_tri",
                        "label": "Tổng giá trị khám",
                        "kind": "money",
                    },
                ],
                self.rows,
                {
                    "so_luot_kham": sum(
                        int(row["so_luot_kham"]) for row in self.rows
                    ),
                    "tong_gia_tri": sum(
                        (
                            Decimal(str(row["tong_gia_tri"] or 0))
                            for row in self.rows
                        ),
                        Decimal("0"),
                    ),
                },
                bieu_do=[
                    {
                        "label": str(row["ten_bac_si"]),
                        "value": row["tong_gia_tri"],
                    }
                    for row in self.rows[:10]
                ],
            )
        except Exception as error:
            hien_loi(self, error, "Không thể xuất báo cáo")
            return
        messagebox.showinfo(
            "Đã xuất báo cáo", f"Đã lưu báo cáo tại:\n{path_text}", parent=self
        )
