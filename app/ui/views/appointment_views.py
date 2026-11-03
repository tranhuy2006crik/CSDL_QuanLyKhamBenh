import tkinter as tk
from datetime import date, datetime
from tkinter import messagebox, simpledialog, ttk

from app.contracts import AppointmentStatus, BacSiDTO, BenhNhanDTO, LichHenDTO
from app.errors import AppError
from app.services.appointment_service import (
    cap_nhat_trang_thai,
    dat_lich,
    doi_lich,
    gio_con_trong,
    gio_trong_30_ngay,
    huy_lich,
    lich_theo_bac_si,
    lich_theo_benh_nhan,
)
from app.services.clinic_service import lay_danh_sach_bac_si, lay_khoa
from app.ui.views.common import hien_loi, tao_bang
from app.ui.views.visit_dialogs import TaoPhieuKhamDialog


STATUS_LABELS = {
    "CONFIRMED": "Đã xác nhận",
    "ARRIVED": "Đã đến",
    "COMPLETED": "Đã khám",
    "NO_SHOW": "Vắng mặt",
    "CANCELLED": "Đã hủy",
}


def _parse_date(value: str) -> date:
    try:
        return datetime.strptime(value.strip(), "%d/%m/%Y").date()
    except ValueError as error:
        raise AppError(
            "DU_LIEU_KHONG_HOP_LE",
            "Ngày phải theo định dạng dd/mm/yyyy.",
            "ngay_hen",
        ) from error


def _format_date(value: datetime) -> str:
    return value.strftime("%d/%m/%Y")


def _format_datetime(value: datetime) -> str:
    return value.strftime("%d/%m/%Y %H:%M")


class PatientAppointmentView(ttk.Frame):
    def __init__(self, parent: tk.Misc, patient: BenhNhanDTO) -> None:
        super().__init__(parent, padding=12)
        self.patient = patient
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)
        self.departments: dict[str, int] = {}
        self.doctors: dict[str, BacSiDTO] = {}
        self.slots: dict[str, datetime] = {}
        self.appointments: dict[str, LichHenDTO] = {}

        ttk.Label(
            self,
            text="Đặt và quản lý lịch hẹn",
            font=("TkDefaultFont", 16, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            self,
            text=(
                "Lịch hẹn xác nhận ngay khi đặt thành công; mỗi lượt 30 phút, "
                "tối đa một lịch hoạt động mỗi ngày và chỉ đặt trong 30 ngày tới. "
                "Lịch chỉ nằm trong RAM phiên chạy, đóng ứng dụng sẽ mất và "
                "không đồng bộ với máy khác."
            ),
            wraplength=1100,
            justify="left",
        ).grid(row=1, column=0, sticky="ew", pady=(4, 8))

        booking = ttk.LabelFrame(self, text="Chọn khung giờ", padding=8)
        booking.grid(row=2, column=0, sticky="new")
        booking.columnconfigure(1, weight=1)
        ttk.Label(booking, text="Khoa").grid(row=0, column=0, sticky="w")
        self.department = ttk.Combobox(booking, state="readonly", width=25)
        self.department.grid(row=0, column=1, sticky="ew", padx=(5, 12))
        self.department.bind("<<ComboboxSelected>>", self._department_changed)
        ttk.Label(booking, text="Bác sĩ").grid(row=0, column=2, sticky="w")
        self.doctor_choice = ttk.Combobox(booking, state="readonly", width=32)
        self.doctor_choice.grid(row=0, column=3, sticky="ew", padx=(5, 12))
        ttk.Label(booking, text="Ngày (dd/mm/yyyy)").grid(
            row=0, column=4, sticky="w"
        )
        self.booking_date = ttk.Entry(booking, width=14)
        self.booking_date.grid(row=0, column=5, padx=5)
        self.booking_date.insert(0, date.today().strftime("%d/%m/%Y"))
        ttk.Button(booking, text="Tìm giờ trống", command=self._find_slots).grid(
            row=0, column=6, padx=(5, 0)
        )

        ttk.Label(booking, text="Khung giờ").grid(
            row=1, column=0, sticky="w", pady=(8, 0)
        )
        self.slot_choice = ttk.Combobox(booking, state="readonly", width=20)
        self.slot_choice.grid(row=1, column=1, sticky="w", padx=(5, 12), pady=(8, 0))
        self.book_button = ttk.Button(
            booking, text="Đặt lịch", command=self._book
        )
        self.book_button.grid(row=1, column=2, padx=(0, 5), pady=(8, 0))
        self.reschedule_button = ttk.Button(
            booking, text="Đổi lịch đã chọn", command=self._reschedule, state="disabled"
        )
        self.reschedule_button.grid(row=1, column=3, padx=(0, 5), pady=(8, 0))
        self.cancel_button = ttk.Button(
            booking, text="Hủy lịch đã chọn", command=self._cancel, state="disabled"
        )
        self.cancel_button.grid(row=1, column=4, columnspan=2, sticky="w", pady=(8, 0))
        self.slot_status = ttk.Label(booking, text="")
        ttk.Button(
            booking,
            text="Tìm ngày gần nhất có giờ",
            command=self._find_next_available,
        ).grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.slot_status.grid(row=2, column=1, columnspan=6, sticky="w", pady=(8, 0))

        appointments_frame = ttk.LabelFrame(self, text="Lịch hẹn của tôi", padding=6)
        appointments_frame.grid(row=3, column=0, sticky="nsew", pady=(8, 0))
        appointments_frame.rowconfigure(0, weight=1)
        appointments_frame.columnconfigure(0, weight=1)
        self.table = tao_bang(
            appointments_frame,
            ("ma_lich", "thoi_gian", "bac_si", "khoa", "trang_thai", "ly_do"),
            {
                "ma_lich": "Mã lịch",
                "thoi_gian": "Ngày giờ",
                "bac_si": "Bác sĩ",
                "khoa": "Khoa",
                "trang_thai": "Trạng thái",
                "ly_do": "Lý do hủy",
            },
            {
                "ma_lich": 80,
                "thoi_gian": 150,
                "bac_si": 220,
                "khoa": 180,
                "trang_thai": 120,
                "ly_do": 250,
            },
        )
        self.table.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(
            appointments_frame, orient="vertical", command=self.table.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.bind("<<TreeviewSelect>>", self._appointment_selected)
        ttk.Button(
            appointments_frame,
            text="Tải lại lịch",
            command=self._refresh_appointments,
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))

        self._load_departments()
        self._refresh_appointments()

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
        if self.departments:
            self.department.current(0)
            self._department_changed()

    def _department_changed(self, _event: tk.Event | None = None) -> None:
        department_id = self.departments.get(self.department.get())
        try:
            rows = lay_danh_sach_bac_si(department_id)
        except Exception as error:
            hien_loi(self, error)
            return
        self.doctors = {
            f'{row["ten_bac_si"]} (Mã {row["ma_bac_si"]})': row for row in rows
        }
        self.doctor_choice["values"] = list(self.doctors)
        if self.doctors:
            self.doctor_choice.current(0)
        else:
            self.doctor_choice.set("")
        self.slots.clear()
        self.slot_choice.set("")
        self.slot_choice["values"] = []
        if self.doctors:
            self._find_next_available()

    def _selected_appointment(self) -> LichHenDTO | None:
        selection = self.table.selection()
        return self.appointments.get(selection[0]) if selection else None

    def _find_slots(self) -> None:
        doctor = self.doctors.get(self.doctor_choice.get())
        if doctor is None:
            self.slot_status.configure(text="Hãy chọn khoa và bác sĩ.")
            return
        try:
            selected_date = _parse_date(self.booking_date.get())
            appointment = self._selected_appointment()
            is_rescheduling_same_day = (
                appointment is not None
                and appointment["trang_thai"] == "CONFIRMED"
                and appointment["ma_bac_si"] == doctor["ma_bac_si"]
                and appointment["bat_dau"].date() == selected_date
            )
            exclude_id = (
                appointment["ma_lich"]
                if is_rescheduling_same_day
                else None
            )
            slots = gio_con_trong(
                doctor["ma_bac_si"], selected_date, exclude_ma_lich=exclude_id
            )
        except Exception as error:
            self.slots.clear()
            self.slot_choice.set("")
            self.slot_choice["values"] = []
            hien_loi(self, error)
            return
        self.slots = {slot.strftime("%H:%M"): slot for slot in slots}
        self.slot_choice["values"] = list(self.slots)
        if slots:
            if is_rescheduling_same_day:
                self.slot_choice.set("")
                self.slot_status.configure(
                    text=f"Còn {len(slots)} khung giờ; chọn giờ mới để đổi lịch."
                )
            else:
                self.slot_choice.current(0)
                self.slot_status.configure(text=f"Còn {len(slots)} khung giờ.")
        else:
            self.slot_choice.set("")
            self.slot_status.configure(text="Ngày này không còn khung giờ phù hợp.")

    def _find_next_available(self) -> None:
        doctor = self.doctors.get(self.doctor_choice.get())
        if doctor is None:
            self.slot_status.configure(text="Hãy chọn khoa và bác sĩ.")
            return
        try:
            availability = gio_trong_30_ngay(doctor["ma_bac_si"])
        except Exception as error:
            hien_loi(self, error)
            return
        if not availability:
            self.slots.clear()
            self.slot_choice.set("")
            self.slot_choice["values"] = []
            self.slot_status.configure(
                text="Bác sĩ không có khung giờ trống trong 30 ngày tới."
            )
            return
        next_date, next_slots = next(iter(availability.items()))
        self.booking_date.delete(0, "end")
        self.booking_date.insert(0, next_date.strftime("%d/%m/%Y"))
        self.slots = {slot.strftime("%H:%M"): slot for slot in next_slots}
        self.slot_choice["values"] = list(self.slots)
        self.slot_choice.current(0)
        self.slot_status.configure(
            text=(
                f"Ngày gần nhất có giờ trống: {next_date:%d/%m/%Y} "
                f"({len(next_slots)} khung giờ)."
            )
        )

    def _book(self) -> None:
        doctor = self.doctors.get(self.doctor_choice.get())
        slot = self.slots.get(self.slot_choice.get())
        if doctor is None or slot is None:
            hien_loi(
                self,
                AppError(
                    "DU_LIEU_KHONG_HOP_LE",
                    "Hãy chọn bác sĩ và tải/chọn một khung giờ còn trống.",
                ),
            )
            return
        try:
            dat_lich(
                self.patient["ma_benh_nhan"],
                self.patient["ho_ten"],
                doctor["ma_bac_si"],
                slot,
            )
        except Exception as error:
            hien_loi(self, error)
            self._find_slots()
            return
        messagebox.showinfo(
            "Đặt lịch", "Lịch hẹn đã được xác nhận.", parent=self
        )
        self._refresh_appointments()
        self._find_slots()

    def _reschedule(self) -> None:
        appointment = self._selected_appointment()
        doctor = self.doctors.get(self.doctor_choice.get())
        slot = self.slots.get(self.slot_choice.get())
        if appointment is None or doctor is None or slot is None:
            hien_loi(
                self,
                AppError(
                    "DU_LIEU_KHONG_HOP_LE",
                    "Chọn lịch cần đổi, ngày mới, rồi tìm và chọn giờ trống.",
                ),
            )
            return
        if doctor["ma_bac_si"] != appointment["ma_bac_si"]:
            hien_loi(
                self,
                AppError(
                    "DU_LIEU_KHONG_HOP_LE",
                    "Đổi lịch chỉ đổi ngày/giờ, không đổi bác sĩ. "
                    "Hãy hủy lịch cũ rồi đặt lịch mới nếu muốn đổi bác sĩ.",
                ),
            )
            return
        try:
            doi_lich(appointment["ma_lich"], self.patient["ma_benh_nhan"], slot)
        except Exception as error:
            hien_loi(self, error)
            self._find_slots()
            return
        messagebox.showinfo("Đổi lịch", "Đã cập nhật giờ hẹn.", parent=self)
        self._refresh_appointments()
        self._find_slots()

    def _cancel(self) -> None:
        appointment = self._selected_appointment()
        if appointment is None:
            return
        reason = simpledialog.askstring(
            "Hủy lịch",
            "Nhập lý do hủy lịch:",
            parent=self,
        )
        if reason is None:
            return
        try:
            huy_lich(
                appointment["ma_lich"],
                "patient",
                self.patient["ma_benh_nhan"],
                reason,
            )
        except Exception as error:
            hien_loi(self, error)
            return
        self._refresh_appointments()
        self._find_slots()

    def _appointment_selected(self, _event: tk.Event | None = None) -> None:
        appointment = self._selected_appointment()
        active = (
            appointment is not None
            and appointment["trang_thai"] == "CONFIRMED"
            and datetime.now() < appointment["bat_dau"]
        )
        state = "normal" if active else "disabled"
        self.reschedule_button.configure(state=state)
        self.cancel_button.configure(state=state)
        if appointment is None:
            return
        doctor = next(
            (
                item
                for item in self.doctors.values()
                if item["ma_bac_si"] == appointment["ma_bac_si"]
            ),
            None,
        )
        if doctor is not None:
            department_name = next(
                (
                    label
                    for label, department_id in self.departments.items()
                    if department_id == doctor["ma_khoa"]
                ),
                None,
            )
            if department_name:
                self.department.set(department_name)
                self._department_changed()
                doctor_label = next(
                    (
                        label
                        for label, item in self.doctors.items()
                        if item["ma_bac_si"] == appointment["ma_bac_si"]
                    ),
                    "",
                )
                self.doctor_choice.set(doctor_label)
        self.booking_date.delete(0, "end")
        self.booking_date.insert(0, _format_date(appointment["bat_dau"]))
        self._find_slots()

    def _refresh_appointments(self) -> None:
        try:
            rows = lich_theo_benh_nhan(self.patient["ma_benh_nhan"])
        except Exception as error:
            hien_loi(self, error)
            return
        self.appointments.clear()
        for item in self.table.get_children():
            self.table.delete(item)
        for row in rows:
            key = str(row["ma_lich"])
            self.appointments[key] = row
            self.table.insert(
                "",
                "end",
                iid=key,
                values=(
                    row["ma_lich"],
                    _format_datetime(row["bat_dau"]),
                    row["ten_bac_si"],
                    row["ten_khoa"],
                    STATUS_LABELS[row["trang_thai"]],
                    row["ly_do_huy"] or "—",
                ),
            )


class DoctorAppointmentView(ttk.Frame):
    def __init__(self, parent: tk.Misc, doctor: BacSiDTO) -> None:
        super().__init__(parent, padding=12)
        self.doctor = doctor
        self.appointments: dict[str, LichHenDTO] = {}
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        ttk.Label(
            self,
            text="Lịch hẹn trong phiên chạy",
            font=("TkDefaultFont", 16, "bold"),
        ).grid(row=0, column=0, sticky="w")
        controls = ttk.Frame(self)
        controls.grid(row=0, column=1, sticky="e")
        self.columnconfigure(1, weight=1)
        ttk.Label(controls, text="Ngày (dd/mm/yyyy)").pack(side="left")
        self.selected_date = ttk.Entry(controls, width=14)
        self.selected_date.pack(side="left", padx=5)
        self.selected_date.insert(0, date.today().strftime("%d/%m/%Y"))
        ttk.Button(controls, text="Tải lịch", command=self._refresh).pack(side="left")
        ttk.Label(
            self,
            text=(
                "Chỉ hiển thị lịch gắn với bác sĩ đang đăng nhập. Dữ liệu lưu tạm "
                "trong RAM, không đồng bộ giữa các máy."
            ),
            wraplength=1000,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 8))

        table_frame = ttk.Frame(self)
        table_frame.grid(row=2, column=0, columnspan=2, sticky="nsew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        self.table = tao_bang(
            table_frame,
            ("ma_lich", "thoi_gian", "ma_bn", "benh_nhan", "trang_thai", "ly_do"),
            {
                "ma_lich": "Mã lịch",
                "thoi_gian": "Ngày giờ",
                "ma_bn": "Mã bệnh nhân",
                "benh_nhan": "Bệnh nhân",
                "trang_thai": "Trạng thái",
                "ly_do": "Lý do hủy",
            },
            {
                "ma_lich": 80,
                "thoi_gian": 150,
                "ma_bn": 110,
                "benh_nhan": 220,
                "trang_thai": 130,
                "ly_do": 260,
            },
        )
        self.table.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.table.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.bind("<<TreeviewSelect>>", self._appointment_selected)

        actions = ttk.Frame(self)
        actions.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self.arrived_button = ttk.Button(
            actions,
            text="Ghi nhận đã đến",
            command=lambda: self._update_status("ARRIVED"),
            state="disabled",
        )
        self.arrived_button.pack(side="left")
        self.completed_button = ttk.Button(
            actions,
            text="Tạo phiếu khám và hoàn tất",
            command=self._complete_visit,
            state="disabled",
        )
        self.completed_button.pack(side="left", padx=6)
        self.no_show_button = ttk.Button(
            actions,
            text="Đánh dấu vắng mặt",
            command=lambda: self._update_status("NO_SHOW"),
            state="disabled",
        )
        self.no_show_button.pack(side="left")
        self.cancel_button = ttk.Button(
            actions,
            text="Hủy lịch",
            command=self._cancel,
            state="disabled",
        )
        self.cancel_button.pack(side="left", padx=6)
        self._refresh()

    def _selected_appointment(self) -> LichHenDTO | None:
        selection = self.table.selection()
        return self.appointments.get(selection[0]) if selection else None

    def _refresh(self) -> None:
        try:
            selected_date = _parse_date(self.selected_date.get())
            rows = lich_theo_bac_si(
                self.doctor["ma_bac_si"], selected_date
            )
        except Exception as error:
            hien_loi(self, error)
            return
        self.appointments.clear()
        for item in self.table.get_children():
            self.table.delete(item)
        for row in rows:
            key = str(row["ma_lich"])
            self.appointments[key] = row
            self.table.insert(
                "",
                "end",
                iid=key,
                values=(
                    row["ma_lich"],
                    _format_datetime(row["bat_dau"]),
                    row["ma_benh_nhan"],
                    row["ten_benh_nhan"],
                    STATUS_LABELS[row["trang_thai"]],
                    row["ly_do_huy"] or "—",
                ),
            )
        self._appointment_selected()

    def _appointment_selected(self, _event: tk.Event | None = None) -> None:
        appointment = self._selected_appointment()
        status = appointment["trang_thai"] if appointment else ""
        now = datetime.now()
        self.arrived_button.configure(
            state=(
                "normal"
                if appointment
                and status == "CONFIRMED"
                and appointment["bat_dau"].date() == date.today()
                and now < appointment["ket_thuc"]
                else "disabled"
            )
        )
        self.completed_button.configure(
            state="normal" if status == "ARRIVED" else "disabled"
        )
        self.no_show_button.configure(
            state=(
                "normal"
                if appointment and status == "CONFIRMED" and now >= appointment["ket_thuc"]
                else "disabled"
            )
        )
        self.cancel_button.configure(
            state=(
                "normal"
                if appointment and status == "CONFIRMED" and now < appointment["bat_dau"]
                else "disabled"
            )
        )

    def _update_status(self, new_status: AppointmentStatus) -> None:
        appointment = self._selected_appointment()
        if appointment is None:
            return
        try:
            cap_nhat_trang_thai(
                appointment["ma_lich"],
                self.doctor["ma_bac_si"],
                new_status,
            )
        except Exception as error:
            hien_loi(self, error)
            return
        self._refresh()

    def _complete_visit(self) -> None:
        appointment = self._selected_appointment()
        if appointment is None:
            return
        dialog = TaoPhieuKhamDialog(
            self,
            appointment["ma_benh_nhan"],
            appointment["ma_bac_si"],
            appointment["ten_benh_nhan"],
        )
        self.wait_window(dialog)
        if dialog.result is None:
            return
        try:
            cap_nhat_trang_thai(
                appointment["ma_lich"],
                self.doctor["ma_bac_si"],
                "COMPLETED",
                ma_phieu_kham=dialog.result,
            )
        except Exception as error:
            hien_loi(self, error)
            return
        self._refresh()

    def _cancel(self) -> None:
        appointment = self._selected_appointment()
        if appointment is None:
            return
        reason = simpledialog.askstring(
            "Hủy lịch",
            "Nhập lý do hủy lịch:",
            parent=self,
        )
        if reason is None:
            return
        try:
            huy_lich(
                appointment["ma_lich"],
                "doctor",
                self.doctor["ma_bac_si"],
                reason,
            )
        except Exception as error:
            hien_loi(self, error)
            return
        self._refresh()
