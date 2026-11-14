import tkinter as tk
from datetime import time, timedelta
from decimal import Decimal
from tkinter import ttk

from app.contracts import BenhNhanDTO, Identifier
from app.services.clinic_service import (
    lay_khoa,
    lay_lich_su_benh_nhan,
    lay_lich_lam_viec,
    lay_tien_su_benh,
)
from app.ui.views.common import dinh_dang_tien, hien_loi, tao_bang
from app.ui.views.appointment_views import PatientAppointmentView
from app.ui.views.visit_dialogs import PhieuKhamDetailDialog


def _format_work_time(value: time | timedelta) -> str:
    if isinstance(value, time):
        return value.strftime("%H:%M")
    total_minutes = int(value.total_seconds() // 60)
    sign = "-" if total_minutes < 0 else ""
    hours, minutes = divmod(abs(total_minutes), 60)
    return f"{sign}{hours:02}:{minutes:02}"


def _format_weekday(value: str | int) -> str:
    if isinstance(value, int) or str(value).isdigit():
        number = int(value)
        if 2 <= number <= 7:
            return f"Thứ {('Hai', 'Ba', 'Tư', 'Năm', 'Sáu', 'Bảy')[number - 2]}"
        if number == 8:
            return "Chủ Nhật"
    return str(value)


class PatientPortal(ttk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        patient: BenhNhanDTO,
        on_logout,
    ) -> None:
        super().__init__(parent, padding=10)
        self.patient = patient
        self.on_logout = on_logout
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header.columnconfigure(0, weight=1)
        ttk.Label(
            header,
            text=f'Hồ sơ bệnh nhân — {patient["ho_ten"]} (Mã {patient["ma_benh_nhan"]})',
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

        self.notebook = ttk.Notebook(self, style="Main.TNotebook")
        self.notebook.grid(row=1, column=0, sticky="nsew")
        self.history_view = PatientHistoryView(
            self.notebook, patient, self._open_visit
        )
        self.appointment_view = PatientAppointmentView(self.notebook, patient)
        self.schedule_view = DoctorScheduleView(self.notebook)
        self.notebook.add(self.history_view, text="Hồ sơ bệnh án")
        self.notebook.add(self.appointment_view, text="Đặt lịch hẹn")
        self.notebook.add(self.schedule_view, text="Lịch làm việc bác sĩ")

    def _open_visit(self, ma_phieu: Identifier) -> None:
        PhieuKhamDetailDialog(
            self,
            ma_phieu,
            vai_tro="patient",
            ma_nguoi_xem=self.patient["ma_benh_nhan"],
        )


class PatientHistoryView(ttk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        patient: BenhNhanDTO,
        open_visit,
    ) -> None:
        super().__init__(parent, padding=12)
        self.patient = patient
        self.open_visit = open_visit
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        ttk.Label(
            self,
            text="Hồ sơ bệnh án của tôi",
            font=("TkDefaultFont", 16, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))
        summary = ttk.Frame(self, padding=(4, 8, 4, 12))
        summary.grid(row=1, column=0, sticky="ew")
        for column, weight in enumerate((5, 2, 3)):
            summary.columnconfigure(column, weight=weight)

        history_group = ttk.Frame(summary)
        history_group.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        ttk.Label(
            history_group,
            text="TIỀN SỬ BỆNH",
            style="SummaryHeading.TLabel",
        ).pack(anchor="w", pady=(0, 4))
        self.medical_history = ttk.Label(
            history_group,
            text="Chưa ghi nhận.",
            style="HistoryValue.TLabel",
            wraplength=600,
            justify="left",
        )
        self.medical_history.pack(anchor="w", fill="x")

        visits_group = ttk.Frame(summary)
        visits_group.grid(row=0, column=1, sticky="nsew", padx=(12, 18))
        ttk.Label(
            visits_group,
            text="TỔNG SỐ LẦN KHÁM",
            style="SummaryHeading.TLabel",
            wraplength=150,
        ).pack(anchor="w", pady=(0, 4))
        self.visit_count = ttk.Label(
            visits_group, text="0", style="SummaryValue.TLabel"
        )
        self.visit_count.pack(anchor="w")

        cost_group = ttk.Frame(summary)
        cost_group.grid(row=0, column=2, sticky="nsew", padx=(12, 0))
        ttk.Label(
            cost_group,
            text="TỔNG CHI PHÍ GHI NHẬN",
            style="SummaryHeading.TLabel",
            wraplength=210,
        ).pack(anchor="w", pady=(0, 4))
        self.total_cost = ttk.Label(
            cost_group,
            text=dinh_dang_tien(0),
            style="SummaryValue.TLabel",
        )
        self.total_cost.pack(anchor="w")

        table_frame = ttk.Frame(self)
        table_frame.grid(row=2, column=0, sticky="nsew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        columns = (
            "stt",
            "ma_phieu",
            "ngay_gio",
            "bac_si",
            "khoa",
            "tong_chi_phi",
        )
        self.table = tao_bang(
            table_frame,
            columns,
            {
                "stt": "STT",
                "ma_phieu": "Mã phiếu",
                "ngay_gio": "Ngày giờ khám",
                "bac_si": "Bác sĩ",
                "khoa": "Khoa",
                "tong_chi_phi": "Tổng chi phí ghi nhận",
            },
            {
                "stt": 55,
                "ma_phieu": 100,
                "ngay_gio": 165,
                "bac_si": 190,
                "khoa": 155,
                "tong_chi_phi": 190,
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
            text="Xem chi tiết",
            command=self._open_selected,
        ).pack(side="left")
        ttk.Button(actions, text="Tải lại", command=self._refresh).pack(side="left", padx=8)
        ttk.Label(
            actions,
            text="Chỉ xem; chi phí là giá trị ghi nhận, không thể hiện trạng thái thanh toán.",
        ).pack(side="right")
        self._refresh()

    def _refresh(self) -> None:
        try:
            rows = lay_lich_su_benh_nhan(self.patient["ma_benh_nhan"])
            medical_history = lay_tien_su_benh(self.patient["ma_benh_nhan"])
        except Exception as error:
            hien_loi(self, error)
            return
        for item in self.table.get_children():
            self.table.delete(item)
        total = Decimal("0")
        for index, row in enumerate(rows, start=1):
            total += Decimal(str(row["tong_chi_phi"] or 0))
            self.table.insert(
                "",
                "end",
                iid=str(row["ma_phieu"]),
                values=(
                    index,
                    row["ma_phieu"],
                    row["ngay_gio_kham"].strftime("%d/%m/%Y %H:%M"),
                    row["ten_bac_si"],
                    row["ten_khoa"],
                    dinh_dang_tien(row["tong_chi_phi"]),
                ),
            )
        self.visit_count.configure(text=str(len(rows)))
        self.total_cost.configure(text=dinh_dang_tien(total))
        self.medical_history.configure(text=medical_history or "Chưa ghi nhận.")

    def _open_selected(self, _event: tk.Event | None = None) -> None:
        selection = self.table.selection()
        if selection:
            self.open_visit(selection[0])


class DoctorScheduleView(ttk.Frame):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, padding=12)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)
        ttk.Label(
            self,
            text="Lịch làm việc định kỳ của bác sĩ",
            font=("TkDefaultFont", 16, "bold"),
        ).grid(row=0, column=0, sticky="w")
        controls = ttk.Frame(self)
        controls.grid(row=1, column=0, sticky="ew", pady=10)
        ttk.Label(controls, text="Khoa").pack(side="left")
        self.department = ttk.Combobox(controls, state="readonly", width=38)
        self.department.pack(side="left", padx=8)
        self.department.bind("<<ComboboxSelected>>", self._select_department)
        ttk.Label(controls, text="Tên bác sĩ").pack(side="left", padx=(12, 4))
        self.doctor_filter = ttk.Entry(controls, width=20)
        self.doctor_filter.pack(side="left")
        self.doctor_filter.bind("<KeyRelease>", self._apply_filters)
        ttk.Label(controls, text="Chức danh").pack(side="left", padx=(12, 4))
        self.title_filter = ttk.Combobox(
            controls,
            state="readonly",
            width=24,
            values=("Tất cả",),
        )
        self.title_filter.current(0)
        self.title_filter.pack(side="left")
        self.title_filter.bind("<<ComboboxSelected>>", self._apply_filters)
        ttk.Label(controls, text="Thứ").pack(side="left", padx=(12, 4))
        self.weekday_filter = ttk.Combobox(
            controls,
            state="readonly",
            width=12,
            values=(
                "Tất cả",
                "Thứ Hai",
                "Thứ Ba",
                "Thứ Tư",
                "Thứ Năm",
                "Thứ Sáu",
                "Thứ Bảy",
                "Chủ Nhật",
            ),
        )
        self.weekday_filter.current(0)
        self.weekday_filter.pack(side="left")
        self.weekday_filter.bind("<<ComboboxSelected>>", self._apply_filters)
        self.schedule_rows = []
        self.departments = {}
        self.status = ttk.Label(
            self, text="Chọn khoa để xem lịch làm việc theo tuần."
        )
        self.status.grid(row=2, column=0, sticky="nw", pady=8)
        table_frame = ttk.Frame(self)
        table_frame.grid(row=3, column=0, sticky="nsew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        columns = (
            "bac_si",
            "phong",
            "chuc_danh",
            "gia_kham",
            "thu",
            "bat_dau",
            "ket_thuc",
        )
        self.table = tao_bang(
            table_frame,
            columns,
            {
                "bac_si": "Bác sĩ",
                "phong": "Phòng khám",
                "chuc_danh": "Chức danh",
                "gia_kham": "Giá khám",
                "thu": "Thứ",
                "bat_dau": "Giờ bắt đầu",
                "ket_thuc": "Giờ kết thúc",
            },
            {
                "bac_si": 190,
                "phong": 120,
                "chuc_danh": 180,
                "gia_kham": 130,
                "thu": 110,
                "bat_dau": 120,
                "ket_thuc": 120,
            },
        )
        self.table.column("gia_kham", anchor="e")
        self.table.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.table.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.table.configure(yscrollcommand=scrollbar.set)
        self._load_departments()

    def _load_departments(self) -> None:
        try:
            rows = lay_khoa()
        except Exception as error:
            hien_loi(self, error)
            return
        self.departments = {
            f'{row["ten_khoa"]} (Mã {row["ma_khoa"]})': row["ma_khoa"]
            for row in rows
        }
        self.department["values"] = list(self.departments)

    def _select_department(self, _event: tk.Event | None = None) -> None:
        department_id = self.departments.get(self.department.get())
        if department_id is None:
            return
        try:
            rows = lay_lich_lam_viec(department_id)
        except Exception as error:
            hien_loi(self, error)
            return
        self.schedule_rows = rows
        selected_title = self.title_filter.get()
        titles = sorted(
            {
                row["trinh_do_hoc_van"].strip()
                for row in rows
                if row.get("trinh_do_hoc_van")
                and row["trinh_do_hoc_van"].strip()
            },
            key=str.casefold,
        )
        self.title_filter["values"] = ("Tất cả", *titles)
        if selected_title not in titles and selected_title != "Tất cả":
            selected_title = "Tất cả"
        self.title_filter.set(selected_title or "Tất cả")
        self._apply_filters()
        if rows:
            status = (
                "Lịch định kỳ tham khảo; lịch này không cho biết ngày nghỉ đột xuất "
                "hoặc chỗ còn trống. Muốn đặt khung giờ cụ thể, mở tab “Đặt lịch hẹn”."
            )
        else:
            status = (
                "Khoa chưa có lịch làm việc được ghi nhận nên hiện không có cơ sở "
                "tạo khung giờ đặt hẹn."
            )
        self.status.configure(text=status)

    def _apply_filters(self, _event: tk.Event | None = None) -> None:
        name_filter = self.doctor_filter.get().strip().casefold()
        title_filter = self.title_filter.get()
        selected_weekday = self.weekday_filter.get()
        rows = [
            row
            for row in self.schedule_rows
            if name_filter in row["ten_bac_si"].casefold()
            and (
                title_filter == "Tất cả"
                or (row.get("trinh_do_hoc_van") or "").strip() == title_filter
            )
            and (
                selected_weekday in ("", "Tất cả")
                or _format_weekday(row["thu"]) == selected_weekday
            )
        ]
        for item in self.table.get_children():
            self.table.delete(item)
        for index, row in enumerate(rows):
            start = row["gio_bat_dau"]
            end = row["gio_ket_thuc"]
            self.table.insert(
                "",
                "end",
                iid=f"{row['ma_bac_si']}-{index}",
                values=(
                    row["ten_bac_si"],
                    row["phong_kham"] or "—",
                    row.get("trinh_do_hoc_van") or "—",
                    dinh_dang_tien(row["gia_kham"]),
                    _format_weekday(row["thu"]),
                    _format_work_time(start),
                    _format_work_time(end),
                ),
            )
