import tkinter as tk
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from app.contracts import BaoCaoBacSiRow, BacSiDTO, BenhNhanDTO, Identifier
from app.errors import AppError
from app.pdf_export import xuat_bang_pdf
from app.services.clinic_service import (
    bao_cao_bac_si,
    lay_lich_su_benh_nhan,
    lay_tien_su_benh,
    tim_phieu_dang_kham,
    tim_kiem_benh_nhan,
)
from app.ui.views.common import dinh_dang_tien, hien_loi, tao_bang
from app.ui.views.appointment_views import DoctorAppointmentView
from app.ui.views.visit_dialogs import PhieuKhamDetailDialog, TaoPhieuKhamDialog


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
        ttk.Button(
            header,
            text="Đổi vai trò / đăng xuất",
            command=on_logout,
            style="Secondary.TButton",
        ).grid(
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

        ttk.Label(
            self,
            text="Tra cứu bệnh nhân",
            font=("TkDefaultFont", 16, "bold"),
        ).grid(row=0, column=0, sticky="w")
        filters = ttk.LabelFrame(self, text="Tìm kiếm và lọc", padding=8)
        filters.grid(row=1, column=0, sticky="ew", pady=8)
        filters.columnconfigure(1, weight=1)
        ttk.Label(filters, text="Mã / họ tên / điện thoại").grid(
            row=0, column=0, sticky="w"
        )
        self.keyword = ttk.Entry(filters)
        self.keyword.grid(row=0, column=1, sticky="ew", padx=6)
        self.keyword.bind("<Return>", self._search_event)
        ttk.Label(filters, text="Ngày sinh").grid(row=0, column=2, sticky="w")
        self.birth_date = ttk.Entry(filters, width=13)
        self.birth_date.grid(row=0, column=3, padx=6)
        ttk.Label(filters, text="Giới tính").grid(row=0, column=4, sticky="w")
        self.gender = ttk.Combobox(
            filters, state="readonly", width=12, values=("", "NAM", "NU", "KHAC")
        )
        self.gender.grid(row=0, column=5, padx=6)
        ttk.Label(filters, text="Địa chỉ").grid(row=1, column=0, sticky="w", pady=6)
        self.address = ttk.Entry(filters)
        self.address.grid(row=1, column=1, sticky="ew", padx=6, pady=6)
        ttk.Button(
            filters,
            text="Tìm",
            command=self._search,
            style="Primary.TButton",
        ).grid(
            row=1, column=5, padx=6, sticky="e"
        )
        ttk.Label(
            filters,
            text="Ngày sinh dùng định dạng dd/mm/yyyy; để trống tiêu chí không cần lọc.",
            wraplength=950,
        ).grid(row=2, column=0, columnspan=6, sticky="w")

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
            style="Primary.TButton",
        ).pack(side="left")
        ttk.Button(actions, text="Tải lại", command=self._search).pack(
            side="left", padx=8
        )
        ttk.Label(
            actions,
            text="Danh sách chỉ gồm bệnh nhân đã được nhập sẵn vào CSDL.",
        ).pack(side="right")
        self.gender.set("")
        self._search()

    def _search_event(self, _event: tk.Event) -> None:
        self._search()

    def _search(self) -> None:
        try:
            birth_text = self.birth_date.get().strip()
            birth_date = (
                datetime.strptime(birth_text, "%d/%m/%Y").date()
                if birth_text
                else None
            )
            patients = tim_kiem_benh_nhan(
                self.keyword.get(),
                ngay_sinh=birth_date,
                gioi_tinh=self.gender.get() or None,
                dia_chi=self.address.get(),
            )
        except ValueError:
            hien_loi(
                self,
                AppError(
                    "DU_LIEU_KHONG_HOP_LE",
                    "Ngày sinh phải theo định dạng dd/mm/yyyy.",
                    "ngay_sinh",
                ),
            )
            return
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
        patient_id = selection[0]
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
        ma_bac_si: Identifier,
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
            selection[0],
            vai_tro="doctor",
            ma_nguoi_xem=self.ma_bac_si,
            on_changed=self._refresh,
        )

    def _create_visit(self) -> None:
        try:
            existing_visit = tim_phieu_dang_kham(
                self.patient["ma_benh_nhan"], self.ma_bac_si
            )
        except Exception as error:
            hien_loi(self, error)
            return
        if existing_visit is not None:
            PhieuKhamDetailDialog(
                self,
                existing_visit,
                vai_tro="doctor",
                ma_nguoi_xem=self.ma_bac_si,
                on_changed=self._refresh,
            )
            return
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
            vai_tro="doctor",
            ma_nguoi_xem=self.ma_bac_si,
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
        controls = ttk.LabelFrame(self, text="Kỳ báo cáo", padding=8)
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
        ttk.Button(controls, text="Xem thống kê", command=self._refresh).grid(
            row=0, column=4, padx=8
        )

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
        columns = (
            "ma_bac_si",
            "ten_bac_si",
            "so_luot_kham",
            "so_benh_nhan",
            "gia_kham",
            "gia_xet_nghiem",
            "gia_thuoc",
            "tong_gia_tri",
        )
        self.table = tao_bang(
            table_frame,
            columns,
            {
                "ma_bac_si": "Mã bác sĩ",
                "ten_bac_si": "Bác sĩ",
                "so_luot_kham": "Số lượt khám",
                "so_benh_nhan": "Số bệnh nhân",
                "gia_kham": "Tiền khám",
                "gia_xet_nghiem": "Tiền xét nghiệm",
                "gia_thuoc": "Tiền thuốc",
                "tong_gia_tri": "Tổng giá trị khám",
            },
            {
                "ma_bac_si": 100,
                "ten_bac_si": 220,
                "so_luot_kham": 105,
                "so_benh_nhan": 110,
                "gia_kham": 145,
                "gia_xet_nghiem": 145,
                "gia_thuoc": 145,
                "tong_gia_tri": 160,
            },
        )
        self.table.grid(row=0, column=0, sticky="nsew")
        table_scroll = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.table.yview
        )
        table_scroll.grid(row=0, column=1, sticky="ns")
        self.table.configure(yscrollcommand=table_scroll.set)
        chart_frame = ttk.Frame(content)
        chart_frame.columnconfigure(0, weight=1)
        chart_frame.columnconfigure(1, weight=1)
        for column, title in enumerate(
            ("Số lượt khám (thang riêng)", "Tổng giá trị ghi nhận (thang riêng)")
        ):
            chart = ttk.LabelFrame(chart_frame, text=title)
            chart.grid(row=0, column=column, sticky="nsew", padx=(0, 5) if column == 0 else (5, 0))
            chart.rowconfigure(0, weight=1)
            chart.columnconfigure(0, weight=1)
            canvas = tk.Canvas(chart, height=200, background="white", highlightthickness=0)
            canvas.grid(row=0, column=0, sticky="nsew")
            canvas.bind(
                "<Configure>",
                lambda event, target=canvas, metric=(
                    "so_luot_kham" if column == 0 else "tong_gia_tri"
                ): self._draw_chart(event, target, metric),
            )
            if column == 0:
                self.visit_chart = canvas
            else:
                self.value_chart = canvas
        content.add(table_frame, weight=3)
        content.add(chart_frame, weight=2)

        footer = ttk.Frame(self)
        footer.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        ttk.Label(
            footer,
            text="Chi phí ghi nhận = giá khám áp dụng + xét nghiệm + thuốc; không phản ánh thanh toán.",
        ).pack(side="left")
        ttk.Button(
            footer,
            text="Xuất báo cáo PDF",
            command=self._export_pdf,
            style="Primary.TButton",
        ).pack(side="right")
        self.rows: list[BaoCaoBacSiRow] = []
        self._refresh()

    def _refresh(self) -> None:
        try:
            month = int(self.month.get())
            year = int(self.year.get().strip())
            rows = bao_cao_bac_si(month, year)
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
                    row["so_luot_kham"],
                    row["so_benh_nhan"],
                    dinh_dang_tien(row["gia_kham"]),
                    dinh_dang_tien(row["gia_xet_nghiem"]),
                    dinh_dang_tien(row["gia_thuoc"]),
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
        self._draw_chart(None, self.visit_chart, "so_luot_kham")
        self._draw_chart(None, self.value_chart, "tong_gia_tri")

    def _draw_chart(
        self,
        _event: tk.Event | None,
        canvas: tk.Canvas,
        metric: str,
    ) -> None:
        if not hasattr(self, "rows"):
            return
        canvas.delete("all")
        width = max(canvas.winfo_width(), 500)
        height = max(canvas.winfo_height(), 180)
        rows = sorted(
            self.rows,
            key=lambda row: Decimal(str(row[metric] or 0)),
            reverse=True,
        )[:8]
        if not rows:
            canvas.create_text(
                width // 2, height // 2, text="Không có dữ liệu cho bộ lọc hiện tại."
            )
            return
        max_value = max(Decimal(str(row[metric] or 0)) for row in rows) or Decimal("1")
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
            value = Decimal(str(row[metric] or 0))
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
                text=(
                    str(int(value))
                    if metric == "so_luot_kham"
                    else dinh_dang_tien(value)
                ),
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
        filters = [f'Tháng {self.month.get()}/{self.year.get()}']
        try:
            xuat_bang_pdf(
                Path(path_text),
                "BÁO CÁO GIÁ TRỊ KHÁM THEO BÁC SĨ",
                "; ".join(filters),
                [
                    {"key": "ma_bac_si", "label": "Mã BS", "kind": "text"},
                    {"key": "ten_bac_si", "label": "Bác sĩ", "kind": "text"},
                    {
                        "key": "so_luot_kham",
                        "label": "Số lượt khám",
                        "kind": "int",
                    },
                    {
                        "key": "so_benh_nhan",
                        "label": "Số bệnh nhân",
                        "kind": "int",
                    },
                    {"key": "gia_kham", "label": "Tiền khám", "kind": "money"},
                    {
                        "key": "gia_xet_nghiem",
                        "label": "Tiền xét nghiệm",
                        "kind": "money",
                    },
                    {"key": "gia_thuoc", "label": "Tiền thuốc", "kind": "money"},
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
                    "so_benh_nhan": sum(
                        int(row["so_benh_nhan"]) for row in self.rows
                    ),
                    "gia_kham": sum(
                        (Decimal(str(row["gia_kham"] or 0)) for row in self.rows),
                        Decimal("0"),
                    ),
                    "gia_xet_nghiem": sum(
                        (
                            Decimal(str(row["gia_xet_nghiem"] or 0))
                            for row in self.rows
                        ),
                        Decimal("0"),
                    ),
                    "gia_thuoc": sum(
                        (Decimal(str(row["gia_thuoc"] or 0)) for row in self.rows),
                        Decimal("0"),
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
