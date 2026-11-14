import tkinter as tk
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from collections.abc import Callable

try:
    from tkcalendar import DateEntry

    HAS_CALENDAR = True
except ImportError:
    HAS_CALENDAR = False

from app.contracts import BaoCaoBacSiRow, BacSiDTO, BenhNhanDTO, Identifier
from app.errors import AppError
from app.doctor_report_pdf import xuat_bao_cao_bac_si_pdf
from app.services.clinic_service import (
    bao_cao_bac_si,
    lay_lich_su_benh_nhan,
    lay_tien_su_benh,
    lay_ho_so_benh_an,
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
        ).grid(row=0, column=1, sticky="e")

        self.notebook = ttk.Notebook(self, style="Main.TNotebook")
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
        super().__init__(parent)
        self.doctor = doctor
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.search_frame = ttk.Frame(self, padding=12)
        self.search_frame.grid(row=0, column=0, sticky="nsew")
        self.search_frame.columnconfigure(0, weight=1)
        self.search_frame.rowconfigure(2, weight=1)

        ttk.Label(
            self.search_frame,
            text="Tra cứu bệnh nhân",
            font=("TkDefaultFont", 16, "bold"),
        ).grid(row=0, column=0, sticky="w")

        filters = ttk.LabelFrame(self.search_frame, text="Tìm kiếm và lọc", padding=8)
        filters.grid(row=1, column=0, sticky="ew", pady=8)
        filters.columnconfigure(1, weight=1)

        ttk.Label(filters, text="Mã / Họ tên / Số điện thoại").grid(
            row=0, column=0, sticky="w"
        )
        self.keyword = ttk.Entry(filters)
        self.keyword.grid(row=0, column=1, sticky="ew", padx=6)
        self.keyword.bind("<Return>", self._search_event)

        ttk.Label(filters, text="Ngày sinh").grid(
            row=1, column=0, sticky="w", pady=(4, 0)
        )
        if HAS_CALENDAR:
            self.birth_date = DateEntry(
                filters,
                width=12,
                background="darkblue",
                foreground="white",
                borderwidth=2,
                date_pattern="dd/mm/yyyy",
            )
            self.birth_date.delete(
                0, "end"
            )  
        else:
            self.birth_date = ttk.Entry(filters, width=14)
        self.birth_date.grid(row=1, column=1, sticky="w", padx=6, pady=(4, 0))

        ttk.Label(filters, text="Giới tính").grid(
            row=2, column=0, sticky="w", pady=(4, 0)
        )
        self.gender = ttk.Combobox(
            filters, state="readonly", width=12, values=("", "NAM", "NU", "KHAC")
        )
        self.gender.grid(row=2, column=1, sticky="w", padx=6, pady=(4, 0))

        ttk.Label(filters, text="Địa chỉ").grid(
            row=3, column=0, sticky="w", pady=(4, 0)
        )
        self.address = ttk.Entry(filters)
        self.address.grid(row=3, column=1, sticky="ew", padx=6, pady=(4, 0))

        btn_frame = ttk.Frame(filters)
        btn_frame.grid(row=4, column=1, sticky="e", pady=(8, 0))

        ttk.Button(
            btn_frame,
            text="Xóa lọc",
            command=self._clear_filters,
            style="Secondary.TButton",
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            btn_frame, text="Tìm", command=self._search, style="Primary.TButton"
        ).pack(side="left")

        table_frame = ttk.Frame(self.search_frame)
        table_frame.grid(row=2, column=0, sticky="nsew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        columns = ("ma_bn", "ho_ten", "dien_thoai", "nam_sinh", "gioi_tinh", "dia_chi")
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
                "ma_bn": 100,
                "ho_ten": 150,
                "dien_thoai": 110,
                "nam_sinh": 80,
                "gioi_tinh": 80,
                "dia_chi": 150,
            },
        )

        self.table.column("ma_bn", anchor="center")
        self.table.column("ho_ten", anchor="w")
        self.table.column("dien_thoai", anchor="center")
        self.table.column("nam_sinh", anchor="center")
        self.table.column("gioi_tinh", anchor="center")
        self.table.column("dia_chi", anchor="w")

        self.table.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.table.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.bind("<Double-1>", self._open_selected)

        actions = ttk.Frame(self.search_frame)
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

        self._clear_filters()

    def _clear_filters(self) -> None:
        self.keyword.delete(0, "end")
        self.birth_date.delete(0, "end")
        self.gender.set("")
        self.address.delete(0, "end")
        self._search()

    def _search_event(self, _event: tk.Event) -> None:
        self._search()

    def _search(self) -> None:
        try:
            birth_text = self.birth_date.get().strip()
            birth_date = (
                datetime.strptime(birth_text, "%d/%m/%Y").date() if birth_text else None
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

        self.search_frame.grid_remove()

        if hasattr(self, "history_frame") and self.history_frame.winfo_exists():
            self.history_frame.destroy()

        self.history_frame = PatientHistoryViewEmbedded(
            self, patient, self.doctor["ma_bac_si"], self._show_search_view
        )
        self.history_frame.grid(row=0, column=0, sticky="nsew")

    def _show_search_view(self) -> None:
        if hasattr(self, "history_frame") and self.history_frame.winfo_exists():
            self.history_frame.destroy()
        self.search_frame.grid()


class PatientHistoryViewEmbedded(ttk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        patient: BenhNhanDTO,
        ma_bac_si: Identifier,
        on_back: Callable[[], None],
    ) -> None:
        super().__init__(parent, padding=12)
        self.patient = patient
        self.ma_bac_si = ma_bac_si
        self.on_back = on_back
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        top_frame = ttk.Frame(self)
        top_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        top_frame.columnconfigure(1, weight=1)

        ttk.Button(
            top_frame,
            text="← Quay lại danh sách",
            command=self.on_back,
            style="Secondary.TButton",
        ).grid(row=0, column=0, sticky="w")

        ttk.Label(
            top_frame,
            text="HỒ SƠ BỆNH ÁN",
            font=("TkDefaultFont", 18, "bold"),
            anchor="center",
        ).grid(row=0, column=1, sticky="ew")

        ttk.Label(
            top_frame,
            text=f'Ngày lập: {datetime.now().strftime("%d/%m/%Y")}',
            foreground="gray",
        ).grid(row=0, column=2, sticky="e")

        info_frame = ttk.Frame(self)
        info_frame.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        info_frame.columnconfigure(0, weight=1)  
        info_frame.columnconfigure(1, weight=2)  

        patient_info_box = ttk.LabelFrame(
            info_frame, text="Thông tin bệnh nhân", padding=8
        )
        patient_info_box.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        ttk.Label(
            patient_info_box,
            text=f"Họ tên: {patient['ho_ten']}",
            font=("TkDefaultFont", 10, "bold"),
            foreground="#1677A5",
        ).pack(anchor="w", pady=2)
        ttk.Label(patient_info_box, text=f"Mã BN: {patient['ma_benh_nhan']}").pack(
            anchor="w", pady=2
        )
        ttk.Label(
            patient_info_box, text=f"Năm sinh: {patient['nam_sinh'] or '—'}"
        ).pack(anchor="w", pady=2)
        ttk.Label(
            patient_info_box, text=f"Giới tính: {patient['gioi_tinh'] or '—'}"
        ).pack(anchor="w", pady=2)
        ttk.Label(
            patient_info_box, text=f"Điện thoại: {patient['so_dien_thoai'] or '—'}"
        ).pack(anchor="w", pady=2)
        ttk.Label(patient_info_box, text=f"Địa chỉ: {patient['dia_chi'] or '—'}").pack(
            anchor="w", pady=2
        )

        history_box = ttk.LabelFrame(info_frame, text="Tiền sử bệnh", padding=8)
        history_box.grid(row=0, column=1, sticky="nsew")
        self.medical_history = ttk.Label(
            history_box, text="—", wraplength=600, justify="left"
        )
        self.medical_history.pack(anchor="w", fill="both", expand=True)

        table_frame = ttk.Frame(self)
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
                "ma_phieu": 80,
                "ngay_gio": 140,
                "bac_si": 160,
                "khoa": 120,
                "chan_doan": 250,
                "tong": 120,
            },
        )

        self.table.column("ma_phieu", anchor="center")
        self.table.column("ngay_gio", anchor="center")
        self.table.column("bac_si", anchor="center")
        self.table.column("khoa", anchor="center")
        self.table.column("chan_doan", anchor="w")  
        self.table.column("tong", anchor="e")  

        self.table.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.table.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.bind("<Double-1>", self._open_selected)

        actions = ttk.Frame(self, padding=(0, 12, 0, 0))
        actions.grid(row=3, column=0, sticky="ew")
        ttk.Button(
            actions, text="Xem chi tiết phiếu", command=self._open_selected
        ).pack(side="left")
        ttk.Button(
            actions,
            text="Tạo phiếu khám mới",
            command=self._create_visit,
            style="Success.TButton",
        ).pack(side="left", padx=8)

        self._refresh()

    def _refresh(self) -> None:
        try:
            visits = lay_lich_su_benh_nhan(self.patient["ma_benh_nhan"])
            medical_history = lay_tien_su_benh(self.patient["ma_benh_nhan"])
        except Exception as error:
            hien_loi(self, error)
            return
        self.medical_history.configure(text=medical_history or "Chưa ghi nhận.")
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
            messagebox.showinfo("Phiếu khám", "Hãy chọn một phiếu khám.", parent=self)
            return
        PhieuKhamDetailDialog(
            self.winfo_toplevel(),
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
                self.winfo_toplevel(),
                existing_visit,
                vai_tro="doctor",
                ma_nguoi_xem=self.ma_bac_si,
                on_changed=self._refresh,
            )
            return
        dialog = TaoPhieuKhamDialog(
            self.winfo_toplevel(),
            self.patient["ma_benh_nhan"],
            self.ma_bac_si,
            self.patient["ho_ten"],
        )
        self.wait_window(dialog)
        if dialog.result is None:
            return
        self._refresh()
        PhieuKhamDetailDialog(
            self.winfo_toplevel(),
            dialog.result,
            vai_tro="doctor",
            ma_nguoi_xem=self.ma_bac_si,
            on_changed=self._refresh,
        )


class DoctorPatientSearchView(ttk.Frame):

    def __init__(self, parent: tk.Misc, doctor: BacSiDTO) -> None:
        super().__init__(parent)
        self.doctor = doctor
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.search_frame = ttk.Frame(self, padding=12)
        self.search_frame.grid(row=0, column=0, sticky="nsew")
        self.search_frame.columnconfigure(0, weight=1)
        self.search_frame.rowconfigure(2, weight=1)

        ttk.Label(
            self.search_frame,
            text="Tra cứu bệnh nhân",
            font=("TkDefaultFont", 16, "bold"),
        ).grid(row=0, column=0, sticky="w")

        filters = ttk.LabelFrame(self.search_frame, text="Tìm kiếm và lọc", padding=8)
        filters.grid(row=1, column=0, sticky="ew", pady=8)
        filters.columnconfigure(1, weight=1)

        row_pad = 6

        ttk.Label(filters, text="Mã / Họ tên / Số điện thoại").grid(
            row=0, column=0, sticky="w", pady=row_pad
        )
        self.keyword = ttk.Entry(filters)
        self.keyword.grid(row=0, column=1, sticky="ew", padx=6, pady=row_pad)
        self.keyword.bind("<Return>", self._search_event)

        ttk.Label(filters, text="Ngày sinh").grid(
            row=1, column=0, sticky="w", pady=row_pad
        )

        birth_frame = ttk.Frame(filters)
        birth_frame.grid(row=1, column=1, sticky="w", padx=6, pady=(4, 0))

        self.birth_date = ttk.Entry(birth_frame, width=12)
        self.birth_date.pack(side="left")

        if HAS_CALENDAR:
            ttk.Button(
                birth_frame, text="📅", width=3, command=self._open_birth_calendar
            ).pack(side="left", padx=(2, 0))

        ttk.Label(filters, text="Giới tính").grid(
            row=2, column=0, sticky="w", pady=row_pad
        )
        self.gender_map = {"": "", "Nam": "NAM", "Nữ": "NU", "Khác": "KHAC"}
        self.gender = ttk.Combobox(
            filters, state="readonly", width=12, values=list(self.gender_map.keys())
        )
        self.gender.set("")
        self.gender.grid(row=2, column=1, sticky="w", padx=6, pady=row_pad)

        ttk.Label(filters, text="Địa chỉ").grid(
            row=3, column=0, sticky="w", pady=row_pad
        )
        self.address = ttk.Entry(filters)
        self.address.grid(row=3, column=1, sticky="ew", padx=6, pady=row_pad)

        bottom_frame = ttk.Frame(filters)
        bottom_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(10, 2))

        ttk.Label(
            bottom_frame,
            text="Ngày sinh dùng định dạng dd/mm/yyyy; để trống tiêu chí không cần lọc.",
            font=("TkDefaultFont", 8),
            foreground="gray",
        ).pack(side="left", pady=4)

        ttk.Button(
            bottom_frame, text="Tìm", command=self._search, style="Primary.TButton"
        ).pack(side="right")

        ttk.Button(
            bottom_frame,
            text="Xóa lọc",
            command=self._clear_filters,
            style="Secondary.TButton",
        ).pack(side="right", padx=(0, 8))

        table_frame = ttk.Frame(self.search_frame)
        table_frame.grid(row=2, column=0, sticky="nsew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        columns = ("ma_bn", "ho_ten", "dien_thoai", "ngay_sinh", "gioi_tinh", "dia_chi")
        self.table = tao_bang(
            table_frame,
            columns,
            {
                "ma_bn": "Mã bệnh nhân",
                "ho_ten": "Họ tên",
                "dien_thoai": "Số điện thoại",
                "ngay_sinh": "Ngày sinh",
                "gioi_tinh": "Giới tính",
                "dia_chi": "Địa chỉ",
            },
            {
                "ma_bn": 100,
                "ho_ten": 150,
                "dien_thoai": 110,
                "ngay_sinh": 90,
                "gioi_tinh": 80,
                "dia_chi": 150,
            },
        )

        self.table.column("ma_bn", anchor="center")
        self.table.column("ho_ten", anchor="w")
        self.table.column("dien_thoai", anchor="center")
        self.table.column("ngay_sinh", anchor="center")
        self.table.column("gioi_tinh", anchor="center")
        self.table.column("dia_chi", anchor="w")

        self.table.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.table.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.bind("<Double-1>", self._open_selected)

        actions = ttk.Frame(self.search_frame)
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

        self._clear_filters()

    def _clear_filters(self) -> None:
        self.keyword.delete(0, "end")
        self.birth_date.delete(0, "end")
        self.gender.set("")
        self.address.delete(0, "end")
        self._search()

    def _search_event(self, _event: tk.Event) -> None:
        self._search()

    def _search(self) -> None:
        try:
            birth_text = self.birth_date.get().strip()
            birth_date = (
                datetime.strptime(birth_text, "%d/%m/%Y").date() if birth_text else None
            )

            selected_label = self.gender.get()
            db_gender = self.gender_map.get(selected_label)

            patients = tim_kiem_benh_nhan(
                self.keyword.get(),
                ngay_sinh=birth_date,
                gioi_tinh=db_gender,
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
            ngay_sinh_str = (
                patient["ngay_sinh"].strftime("%d/%m/%Y")
                if patient.get("ngay_sinh")
                else "—"
            )

            raw_g = (patient.get("gioi_tinh") or "").upper()
            hien_thi_gioi_tinh = {"NAM": "Nam", "NU": "Nữ", "KHAC": "Khác"}.get(
                raw_g, raw_g or "—"
            )

            self.table.insert(
                "",
                "end",
                iid=str(patient["ma_benh_nhan"]),
                values=(
                    patient["ma_benh_nhan"],
                    patient["ho_ten"],
                    patient["so_dien_thoai"] or "—",
                    ngay_sinh_str,
                    hien_thi_gioi_tinh,
                    patient["dia_chi"] or "—",
                ),
            )

    def _open_selected(self, _event: tk.Event | None = None) -> None:
        selection = self.table.selection()
        if not selection:
            messagebox.showinfo("Hồ sơ bệnh án", "Hãy chọn một bệnh nhân.", parent=self)
            return
        patient_id = selection[0]
        values = self.table.item(selection[0], "values")
        patient = {
            "ma_benh_nhan": patient_id,
            "ho_ten": values[1],
            "so_dien_thoai": values[2],
            "ngay_sinh": values[3],
            "gioi_tinh": values[4],
            "dia_chi": values[5],
        }

        self.search_frame.grid_remove()

        if hasattr(self, "history_frame") and self.history_frame.winfo_exists():
            self.history_frame.destroy()

        self.history_frame = PatientHistoryViewEmbedded(
            self, patient, self.doctor["ma_bac_si"], self._show_search_view
        )
        self.history_frame.grid(row=0, column=0, sticky="nsew")

    def _show_search_view(self) -> None:
        if hasattr(self, "history_frame") and self.history_frame.winfo_exists():
            self.history_frame.destroy()
        self.search_frame.grid()

    def _open_birth_calendar(self):
        """Hàm mở popup cuốn lịch siêu cấp ổn định cho ngày sinh"""
        try:
            from tkcalendar import Calendar
        except ImportError:
            return

        top = tk.Toplevel(self)
        top.title("Chọn ngày sinh")
        top.geometry("+%d+%d" % (self.winfo_rootx() + 150, self.winfo_rooty() + 150))
        top.transient(self.winfo_toplevel())
        top.grab_set()

        cal = Calendar(top, selectmode="day", date_pattern="dd/mm/yyyy")
        cal.pack(padx=10, pady=10)

        current_date = self.birth_date.get().strip()
        if current_date:
            try:
                dt = datetime.strptime(current_date, "%d/%m/%Y").date()
                cal.selection_set(dt)
            except ValueError:
                pass

        def on_date_selected(e):
            self.birth_date.delete(0, "end")
            self.birth_date.insert(0, cal.get_date())
            top.destroy()
            self._search()

        cal.bind("<<CalendarSelected>>", on_date_selected)


class PatientHistoryViewEmbedded(ttk.Frame):

    def __init__(
        self,
        parent: tk.Misc,
        patient: BenhNhanDTO,
        ma_bac_si: Identifier,
        on_back: Callable[[], None],
    ) -> None:
        super().__init__(parent, padding=12)
        self.patient = patient
        self.ma_bac_si = ma_bac_si
        self.on_back = on_back
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        top_frame = ttk.Frame(self)
        top_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        top_frame.columnconfigure(1, weight=1)

        ttk.Button(
            top_frame,
            text="← Quay lại danh sách",
            command=self.on_back,
            style="Secondary.TButton",
        ).grid(row=0, column=0, sticky="w")

        ttk.Label(
            top_frame,
            text="HỒ SƠ BỆNH ÁN",
            font=("TkDefaultFont", 18, "bold"),
            anchor="center",
        ).grid(row=0, column=1, sticky="ew")

        self.lbl_ngay_lap = ttk.Label(top_frame, text="Ngày lập: —", foreground="gray")
        self.lbl_ngay_lap.grid(row=0, column=2, sticky="e")

        info_frame = ttk.Frame(self)
        info_frame.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        info_frame.columnconfigure(0, weight=1)
        info_frame.columnconfigure(1, weight=2)

        patient_info_box = ttk.LabelFrame(
            info_frame, text="Thông tin bệnh nhân", padding=8
        )
        patient_info_box.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        ttk.Label(
            patient_info_box,
            text=f"{patient['ho_ten']} (Mã bệnh nhân: {patient['ma_benh_nhan']})",
            font=("TkDefaultFont", 11, "bold"),
            foreground="#1677A5",
        ).pack(anchor="w", pady=2)
        ttk.Label(
            patient_info_box, text=f"Ngày sinh: {patient.get('ngay_sinh') or '—'}"
        ).pack(anchor="w", pady=2)
        ttk.Label(
            patient_info_box, text=f"Giới tính: {patient.get('gioi_tinh') or '—'}"
        ).pack(anchor="w", pady=2)
        ttk.Label(
            patient_info_box, text=f"Điện thoại: {patient.get('so_dien_thoai') or '—'}"
        ).pack(anchor="w", pady=2)
        ttk.Label(
            patient_info_box, text=f"Địa chỉ: {patient.get('dia_chi') or '—'}"
        ).pack(anchor="w", pady=2)

        history_box = ttk.LabelFrame(info_frame, text="Tiền sử bệnh", padding=6)
        history_box.grid(row=0, column=1, sticky="nsew")
        history_box.rowconfigure(0, weight=1)
        history_box.columnconfigure(0, weight=1)

        self.medical_history = tk.Text(
            history_box,
            height=4,
            wrap="word",
            font=("TkDefaultFont", 10),
            relief="flat",
            highlightthickness=0,
            background="#FFFFFF",
        )
        self.medical_history.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        history_scroll = ttk.Scrollbar(
            history_box, orient="vertical", command=self.medical_history.yview
        )
        history_scroll.grid(row=0, column=1, sticky="ns")
        self.medical_history.configure(yscrollcommand=history_scroll.set)
        self.medical_history.configure(state="disabled")  

        table_frame = ttk.Frame(self)
        table_frame.grid(row=2, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        columns = (
            "ma_phieu",
            "ngay_gio",
            "bac_si",
            "khoa",
            "chan_doan",
            "trang_thai",
            "tong",
        )
        self.table = tao_bang(
            table_frame,
            columns,
            {
                "ma_phieu": "Mã phiếu",
                "ngay_gio": "Ngày giờ khám",
                "bac_si": "Bác sĩ",
                "khoa": "Khoa",
                "chan_doan": "Chẩn đoán",
                "trang_thai": "Trạng thái",
                "tong": "Tổng chi phí",
            },
            {
                "ma_phieu": 80,
                "ngay_gio": 140,
                "bac_si": 150,
                "khoa": 110,
                "chan_doan": 180,
                "trang_thai": 110,
                "tong": 120,
            },
        )

        self.table.column("ma_phieu", anchor="center")
        self.table.column("ngay_gio", anchor="center")
        self.table.column("bac_si", anchor="center")
        self.table.column("khoa", anchor="center")
        self.table.column("chan_doan", anchor="w")
        self.table.column("trang_thai", anchor="center")
        self.table.column("tong", anchor="e")

        self.table.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.table.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.bind("<Double-1>", self._open_selected)

        actions = ttk.Frame(self, padding=(0, 12, 0, 0))
        actions.grid(row=3, column=0, sticky="ew")
        ttk.Button(
            actions, text="Xem chi tiết phiếu", command=self._open_selected
        ).pack(side="left")
        ttk.Button(
            actions,
            text="Tạo phiếu khám mới",
            command=self._create_visit,
            style="Success.TButton",
        ).pack(side="left", padx=8)

        self._refresh()

    def _refresh(self) -> None:
        try:
            visits = lay_lich_su_benh_nhan(self.patient["ma_benh_nhan"])
            ho_so = lay_ho_so_benh_an(self.patient["ma_benh_nhan"])
        except Exception as error:
            hien_loi(self, error)
            return

        self.medical_history.configure(state="normal")
        self.medical_history.delete("1.0", "end")

        if ho_so:
            tien_su = ho_so.get("tien_su_benh") or "Chưa ghi nhận."
            ngay_lap = ho_so.get("ngay_lap")
            ngay_lap_str = ngay_lap.strftime("%d/%m/%Y") if ngay_lap else "—"
            self.lbl_ngay_lap.configure(text=f"Ngày lập: {ngay_lap_str}")
        else:
            tien_su = "Chưa ghi nhận."
            self.lbl_ngay_lap.configure(text="Ngày lập: —")

        self.medical_history.insert("1.0", tien_su)
        self.medical_history.configure(state="disabled")

        for item in self.table.get_children():
            self.table.delete(item)

        for visit in visits:
            raw_status = visit.get("trang_thai", "HOAN_THANH")
            text_status = "Đang khám" if raw_status == "DANG_KHAM" else "Hoàn thành"

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
                    text_status,
                    dinh_dang_tien(visit["tong_chi_phi"]),
                ),
            )

    def _open_selected(self, _event: tk.Event | None = None) -> None:
        selection = self.table.selection()
        if not selection:
            messagebox.showinfo("Phiếu khám", "Hãy chọn một phiếu khám.", parent=self)
            return
        PhieuKhamDetailDialog(
            self.winfo_toplevel(),
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
                self.winfo_toplevel(),
                existing_visit,
                vai_tro="doctor",
                ma_nguoi_xem=self.ma_bac_si,
                on_changed=self._refresh,
            )
            return
        dialog = TaoPhieuKhamDialog(
            self.winfo_toplevel(),
            self.patient["ma_benh_nhan"],
            self.ma_bac_si,
            self.patient["ho_ten"],
        )
        self.wait_window(dialog)
        if dialog.result is None:
            return
        self._refresh()
        PhieuKhamDetailDialog(
            self.winfo_toplevel(),
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
        ttk.Button(controls, text="Xem thống kê", command=self._refresh).grid(
            row=0, column=4, padx=8
        )

        summary = ttk.Frame(self, padding=8, relief="groove")
        summary.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        for column in range(3):
            summary.columnconfigure(column, weight=1)
        self.summary_doctors = ttk.Label(summary, text="Số bác sĩ: 0")
        self.summary_doctors.grid(row=0, column=0, sticky="w")
        self.summary_visits = ttk.Label(
            summary,
            text="Tổng lượt khám: 0",
            font=("Segoe UI", 13, "bold"),
            foreground="#111827",
        )
        self.summary_visits.grid(row=0, column=1, sticky="w")
        self.summary_value = ttk.Label(
            summary,
            text="Tổng giá trị khám: 0 VNĐ",
            font=("Segoe UI", 13, "bold"),
            foreground="#111827",
        )
        self.summary_value.grid(row=0, column=2, sticky="e")

        table_frame = ttk.Frame(self)
        table_frame.grid(row=3, column=0, sticky="nsew")
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
            style="Info.TButton",
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

    def _export_pdf(self) -> None:
        if not self.rows:
            messagebox.showinfo(
                "Xuất báo cáo", "Không có dữ liệu để xuất.", parent=self
            )
            return
        try:
            month = int(self.month.get())
            year = int(self.year.get().strip())
        except ValueError:
            hien_loi(
                self,
                AppError("DU_LIEU_KHONG_HOP_LE", "Năm phải là số nguyên.", "nam"),
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
        try:
            xuat_bao_cao_bac_si_pdf(
                Path(path_text),
                month,
                year,
                self.rows,
            )
        except Exception as error:
            hien_loi(self, error, "Không thể xuất báo cáo")
            return
        messagebox.showinfo(
            "Đã xuất báo cáo", f"Đã lưu báo cáo tại:\n{path_text}", parent=self
        )
