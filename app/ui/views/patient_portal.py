import tkinter as tk
from datetime import time, timedelta
from decimal import Decimal
from tkinter import ttk

from app.contracts import BenhNhanDTO
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
        ttk.Button(header, text="Đổi vai trò / đăng xuất", command=on_logout).grid(
            row=0, column=1, sticky="e"
        )

        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=1, column=0, sticky="nsew")
        self.history_view = PatientHistoryView(self.notebook, patient, self._open_visit)
        self.appointment_view = PatientAppointmentView(self.notebook, patient)
        self.schedule_view = DoctorScheduleView(self.notebook)
        self.notebook.add(self.history_view, text="Hồ sơ bệnh án")
        self.notebook.add(self.appointment_view, text="Đặt lịch hẹn")
        self.notebook.add(self.schedule_view, text="Lịch làm việc bác sĩ")

    def _open_visit(self, ma_phieu: str) -> None:
        PhieuKhamDetailDialog(self, ma_phieu, read_only=True)


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
        self.rowconfigure(3, weight=1)

        ttk.Label(
            self,
            text="Hồ sơ bệnh án của tôi",
            font=("TkDefaultFont", 16, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.medical_history = ttk.Label(self, text="Tiền sử bệnh: —", wraplength=1100)
        self.medical_history.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        self.summary = ttk.Label(self, text="")
        self.summary.grid(row=2, column=0, sticky="ew", pady=(0, 8))

        table_frame = ttk.Frame(self)
        table_frame.grid(row=3, column=0, sticky="nsew")
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
        # Sửa lại đúng tên các cột trong `columns` khớp với khai báo phía trên
        self.table.column("stt", anchor="center", width=50)
        self.table.column("ma_phieu", anchor="center", width=100)
        self.table.column("ngay_gio", anchor="center", width=130)
        self.table.column("bac_si", anchor="w", width=190)
        self.table.column("khoa", anchor="w", width=155)
        self.table.column("tong_chi_phi", anchor="e", width=190)

        self.table.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.table.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.bind("<Double-1>", self._open_selected)

        actions = ttk.Frame(self)
        actions.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(
            actions,
            text="Xem chi tiết",
            command=self._open_selected,
        ).pack(side="left")
        ttk.Button(actions, text="Tải lại", command=self._refresh).pack(
            side="left", padx=8
        )
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
        self.summary.configure(
            text=(
                f"Tổng số lần khám: {len(rows)}     "
                f"Tổng chi phí ghi nhận: {dinh_dang_tien(total)}"
            )
        )
        self.medical_history.configure(
            text=f"Tiền sử bệnh: {medical_history or 'Chưa ghi nhận.'}"
        )

    def _open_selected(self, _event: tk.Event | None = None) -> None:
        selection = self.table.selection()
        if selection:
            self.open_visit(str(selection[0]))


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
        self.departments = {}
        self.status = ttk.Label(self, text="Chọn khoa để xem lịch làm việc theo tuần.")
        self.status.grid(row=2, column=0, sticky="nw", pady=8)
        table_frame = ttk.Frame(self)
        table_frame.grid(row=3, column=0, sticky="nsew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        columns = ("bac_si", "phong", "thu", "bat_dau", "ket_thuc")
        self.table = tao_bang(
            table_frame,
            columns,
            {
                "bac_si": "Bác sĩ",
                "phong": "Phòng khám",
                "thu": "Thứ",
                "bat_dau": "Giờ bắt đầu",
                "ket_thuc": "Giờ kết thúc",
            },
            {"bac_si": 240, "phong": 140, "thu": 130, "bat_dau": 150, "ket_thuc": 150},
        )
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
            f'{row["ten_khoa"]} (Mã {row["ma_khoa"]})': row["ma_khoa"] for row in rows
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
                    row["thu"],
                    _format_work_time(start),
                    _format_work_time(end),
                ),
            )
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
