import calendar
import queue
import tkinter as tk
from collections.abc import Callable
from datetime import date, datetime, timedelta
from threading import Thread
from tkinter import messagebox, ttk
from typing import Any

from app.contracts import (
    AppointmentStatus,
    BacSiDTO,
    BenhNhanDTO,
    Identifier,
    LichHenDTO,
)
from app.errors import AppError
from app.services.appointment_service import (
    cap_nhat_trang_thai,
    an_lich_da_xu_ly,
    cac_khung_gio_trong_ngay,
    dat_lich,
    doi_lich,
    gan_phieu_vao_lich,
    huy_lich,
    hien_lich_da_an,
    lich_theo_bac_si,
    lich_theo_benh_nhan,
)
from app.services.clinic_service import (
    lay_danh_sach_bac_si,
    lay_khoa,
    tim_phieu_dang_kham,
)
from app.services.tra_cuu_service import lay_chi_tiet_lan_kham
from app.ui.views.common import hien_loi
from app.ui.views.visit_dialogs import PhieuKhamDetailDialog, TaoPhieuKhamDialog


STATUS_LABELS = {
    "CONFIRMED": "Chờ khám",
    "ARRIVED": "Đã đến",
    "COMPLETED": "Đã khám",
    "NO_SHOW": "Vắng mặt",
    "CANCELLED": "Đã hủy",
}


def _format_datetime(value: datetime) -> str:
    return value.strftime("%d/%m/%Y %H:%M")


class CalendarDatePicker(ttk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        value: date,
        on_change: Callable[[], None],
        minimum: date | None = None,
        maximum: date | None = None,
    ) -> None:
        super().__init__(parent)
        self.value = value
        self.on_change = on_change
        self.minimum = minimum
        self.maximum = maximum
        self.entry = ttk.Entry(self, width=12, state="readonly")
        self.entry.pack(side="left")
        ttk.Button(
            self,
            text="Lịch",
            command=self._open_calendar,
            style="Secondary.TButton",
        ).pack(side="left", padx=(4, 0))
        self._update_entry()

    def get_date(self) -> date:
        return self.value

    def set_date(self, value: date, notify: bool = True) -> None:
        if isinstance(value, datetime) or not isinstance(value, date):
            raise ValueError("Ngày phải là một giá trị date.")
        self.value = value
        self._update_entry()
        if notify:
            self.on_change()

    def _update_entry(self) -> None:
        self.entry.configure(state="normal")
        self.entry.delete(0, "end")
        self.entry.insert(0, self.value.strftime("%d/%m/%Y"))
        self.entry.configure(state="readonly")

    @staticmethod
    def _month_key(value: date) -> tuple[int, int]:
        return value.year, value.month

    def _open_calendar(self) -> None:
        popup = tk.Toplevel(self)
        popup.title("Chọn ngày hẹn")
        popup.transient(self.winfo_toplevel())
        popup.resizable(False, False)
        popup.columnconfigure(0, weight=1)
        popup.grab_set()

        month = {"year": self.value.year, "month": self.value.month}
        header = ttk.Frame(popup, padding=(10, 10, 10, 4))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)
        calendar_body = ttk.Frame(popup, padding=(10, 4, 10, 10))
        calendar_body.grid(row=1, column=0, sticky="nsew")

        def move_month(offset: int) -> None:
            year, month_number = month["year"], month["month"] + offset
            if month_number < 1:
                year -= 1
                month_number = 12
            elif month_number > 12:
                year += 1
                month_number = 1
            if not 1 <= year <= 9999:
                return
            month.update(year=year, month=month_number)
            render()

        def select_day(day: int) -> None:
            self.set_date(date(month["year"], month["month"], day))
            popup.destroy()

        def render() -> None:
            for child in header.winfo_children():
                child.destroy()
            for child in calendar_body.winfo_children():
                child.destroy()

            current_month = date(month["year"], month["month"], 1)
            previous_month = date(
                month["year"] - (month["month"] == 1),
                12 if month["month"] == 1 else month["month"] - 1,
                1,
            )
            next_month = date(
                month["year"] + (month["month"] == 12),
                1 if month["month"] == 12 else month["month"] + 1,
                1,
            )
            ttk.Button(
                header,
                text="‹",
                width=3,
                state=(
                    "normal"
                    if (
                        self.minimum is None
                        or self._month_key(previous_month)
                        >= self._month_key(self.minimum)
                    )
                    else "disabled"
                ),
                command=lambda: move_month(-1),
            ).grid(row=0, column=0)
            ttk.Label(
                header,
                text=current_month.strftime("%m/%Y"),
                font=("Segoe UI", 10, "bold"),
                anchor="center",
            ).grid(row=0, column=1, sticky="ew", padx=8)
            ttk.Button(
                header,
                text="›",
                width=3,
                state=(
                    "normal"
                    if (
                        self.maximum is None
                        or self._month_key(next_month)
                        <= self._month_key(self.maximum)
                    )
                    else "disabled"
                ),
                command=lambda: move_month(1),
            ).grid(row=0, column=2)

            for column, weekday in enumerate(
                ("T2", "T3", "T4", "T5", "T6", "T7", "CN")
            ):
                ttk.Label(
                    calendar_body, text=weekday, width=4, anchor="center"
                ).grid(row=0, column=column, pady=(0, 4))
            for row_index, week in enumerate(
                calendar.monthcalendar(month["year"], month["month"]), start=1
            ):
                for column, day in enumerate(week):
                    if day == 0:
                        continue
                    selected_date = date(month["year"], month["month"], day)
                    ttk.Button(
                        calendar_body,
                        text=str(day),
                        width=4,
                        state=(
                            "normal"
                            if (
                                (self.minimum is None or selected_date >= self.minimum)
                                and (
                                    self.maximum is None
                                    or selected_date <= self.maximum
                                )
                            )
                            else "disabled"
                        ),
                        command=lambda selected_day=day: select_day(selected_day),
                    ).grid(row=row_index, column=column, padx=1, pady=1)

        render()
        popup.update_idletasks()
        popup.geometry(f"+{self.winfo_rootx()}+{self.winfo_rooty() + self.winfo_height()}")
        popup.protocol("WM_DELETE_WINDOW", popup.destroy)


class ScrollableFrame(ttk.Frame):
    def __init__(self, parent: tk.Misc, height: int = 170) -> None:
        super().__init__(parent)
        self.canvas = tk.Canvas(
            self, height=height, highlightthickness=0, background="#F4F7FA"
        )
        self.scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self.canvas.yview
        )
        self.content = ttk.Frame(self.canvas)
        self.window_id = self.canvas.create_window(
            (0, 0), window=self.content, anchor="nw"
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.content.bind("<Configure>", self._content_configured)
        self.canvas.bind("<Configure>", self._canvas_configured)
        self.canvas.bind("<MouseWheel>", self._mousewheel)

    def _content_configured(self, _event: tk.Event) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _canvas_configured(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self.window_id, width=event.width)

    def _mousewheel(self, event: tk.Event) -> None:
        self.canvas.yview_scroll(-int(event.delta / 120), "units")


class AppointmentCard(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        title: str,
        details: tuple[str, ...],
        on_select: Callable[[], None],
        status: str | None = None,
        status_color: str = "#526574",
    ) -> None:
        super().__init__(
            parent,
            background="#FFFFFF",
            highlightthickness=1,
            highlightbackground="#D5DEE6",
            highlightcolor="#1677A5",
            padx=12,
            pady=8,
        )
        self._selected = False
        title_label = tk.Label(
            self,
            text=title,
            background="#FFFFFF",
            foreground="#183B56",
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        )
        title_label.pack(fill="x")
        for detail in details:
            tk.Label(
                self,
                text=detail,
                background="#FFFFFF",
                foreground="#526574",
                anchor="w",
                justify="left",
                wraplength=950,
            ).pack(fill="x", pady=(3, 0))
        if status:
            tk.Label(
                self,
                text=status,
                background="#FFFFFF",
                foreground=status_color,
                font=("Segoe UI", 10, "bold"),
                anchor="w",
            ).pack(fill="x", pady=(5, 0))
        self._bind_click(self, on_select)

    def _bind_click(self, widget: tk.Widget, callback: Callable[[], None]) -> None:
        widget.bind("<Button-1>", lambda _event: callback())
        for child in widget.winfo_children():
            self._bind_click(child, callback)

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self.configure(
            highlightbackground="#1677A5" if selected else "#D5DEE6",
            highlightthickness=2 if selected else 1,
        )


class CancelAppointmentDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, appointment: LichHenDTO) -> None:
        super().__init__(parent)
        self.title("Hủy lịch hẹn")
        self.geometry("520x340")
        self.minsize(460, 300)
        self.transient(parent.winfo_toplevel())
        self.result: str | None = None
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        ttk.Label(
            self,
            text="Hủy lịch hẹn",
            font=("Segoe UI", 15, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 8))
        ttk.Label(
            self,
            text=(
                f'{appointment["ten_benh_nhan"]} ({appointment["ma_benh_nhan"]})\n'
                f'{appointment["ten_bac_si"]} · '
                f'{_format_datetime(appointment["bat_dau"])}–'
                f'{appointment["ket_thuc"]:%H:%M}'
            ),
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))
        ttk.Label(
            self,
            text="Lý do hủy lịch *",
            font=("Segoe UI", 10, "bold"),
        ).grid(row=2, column=0, sticky="w", padx=16)
        self.reason = tk.Text(self, height=5, wrap="word")
        self.reason.grid(row=3, column=0, sticky="nsew", padx=16, pady=6)
        self.error = ttk.Label(self, text="", foreground="#C0392B")
        self.error.grid(row=4, column=0, sticky="w", padx=16)
        actions = ttk.Frame(self, padding=16)
        actions.grid(row=5, column=0, sticky="ew")
        ttk.Button(
            actions,
            text="Quay lại",
            command=self.destroy,
            style="Secondary.TButton",
        ).pack(side="right")
        ttk.Button(
            actions,
            text="Xác nhận hủy lịch",
            command=self._submit,
            style="Danger.TButton",
        ).pack(side="right", padx=(0, 8))
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.grab_set()
        self.reason.focus_set()

    def _submit(self) -> None:
        reason = self.reason.get("1.0", "end").strip()
        if not reason:
            self.error.configure(text="Vui lòng nhập lý do hủy lịch.")
            self.reason.focus_set()
            return
        self.result = reason
        self.destroy()


def _ask_cancel_reason(
    parent: tk.Misc, appointment: LichHenDTO
) -> str | None:
    dialog = CancelAppointmentDialog(parent, appointment)
    parent.wait_window(dialog)
    return dialog.result


class PatientAppointmentView(ttk.Frame):
    def __init__(self, parent: tk.Misc, patient: BenhNhanDTO) -> None:
        super().__init__(parent, padding=12)
        self.patient = patient
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)
        self.rowconfigure(4, weight=1)
        self.departments: dict[str, int] = {}
        self.doctors: dict[str, BacSiDTO] = {}
        self.slots: dict[str, datetime] = {}
        self.slot_statuses: dict[datetime, str] = {}
        self.slot_buttons: dict[datetime, ttk.Button] = {}
        self.selected_slot: datetime | None = None
        self.appointments: dict[str, LichHenDTO] = {}
        self.appointment_cards: dict[str, AppointmentCard] = {}
        self.selected_appointment_id: str | None = None
        self.show_hidden = tk.BooleanVar(value=False)
        self._background_results: queue.Queue[
            tuple[str, int, Any, Exception | None]
        ] = queue.Queue()
        self._background_callbacks: dict[
            str,
            tuple[
                int,
                Callable[[Any], None],
                Callable[[Exception], None] | None,
            ],
        ] = {}
        self._background_sequences: dict[str, int] = {}
        self._background_poll_id: str | None = None
        self._slots_request = 0
        self._mutation_in_progress = False
        self.bind("<Destroy>", self._cancel_background_poll, add="+")

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

        booking = ttk.LabelFrame(self, text="Đặt lịch hẹn", padding=8)
        booking.grid(row=2, column=0, sticky="new")
        booking.columnconfigure(1, weight=1)
        booking.columnconfigure(3, weight=1)
        ttk.Label(booking, text="Khoa").grid(row=0, column=0, sticky="w")
        self.department = ttk.Combobox(booking, state="readonly", width=25)
        self.department.grid(row=0, column=1, sticky="ew", padx=(5, 12))
        self.department.bind("<<ComboboxSelected>>", self._department_changed)
        ttk.Label(booking, text="Bác sĩ").grid(row=0, column=2, sticky="w")
        self.doctor_choice = ttk.Combobox(booking, state="readonly", width=32)
        self.doctor_choice.grid(row=0, column=3, sticky="ew", padx=(5, 12))
        ttk.Label(booking, text="Ngày hẹn").grid(row=0, column=4, sticky="w")
        self.booking_date = CalendarDatePicker(
            booking,
            date.today(),
            self._find_slots,
            minimum=date.today(),
            maximum=date.today() + timedelta(days=30),
        )
        self.booking_date.grid(row=0, column=5, sticky="w", padx=5)
        self.doctor_choice.bind("<<ComboboxSelected>>", self._find_slots)

        self.book_button = ttk.Button(
            booking,
            text="Đặt lịch",
            command=self._book,
            style="Primary.TButton",
        )
        self.book_button.grid(row=1, column=0, sticky="w", padx=(5, 0), pady=(8, 0))
        self.reschedule_button = ttk.Button(
            booking,
            text="Đổi lịch đã chọn",
            command=self._reschedule,
            state="disabled",
            style="Info.TButton",
        )
        self.reschedule_button.grid(row=1, column=1, sticky="w", padx=(5, 0), pady=(8, 0))
        self.cancel_button = ttk.Button(
            booking,
            text="Hủy lịch đã chọn",
            command=self._cancel,
            state="disabled",
            style="Danger.TButton",
        )
        self.cancel_button.grid(row=1, column=2, sticky="w", padx=(5, 0), pady=(8, 0))
        self.slot_status = ttk.Label(booking, text="Chọn bác sĩ và ngày để xem giờ.")
        self.slot_status.grid(row=2, column=0, columnspan=6, sticky="w", pady=(8, 0))

        slot_frame = ttk.LabelFrame(self, text="Khung giờ 30 phút", padding=6)
        slot_frame.grid(row=3, column=0, sticky="nsew", pady=(8, 0))
        self.slot_grid = ScrollableFrame(slot_frame, height=150)
        self.slot_grid.grid(row=0, column=0, sticky="nsew")
        slot_frame.rowconfigure(0, weight=1)
        slot_frame.columnconfigure(0, weight=1)

        appointments_frame = ttk.LabelFrame(self, text="Lịch hẹn của tôi", padding=6)
        appointments_frame.grid(row=4, column=0, sticky="nsew", pady=(8, 0))
        appointments_frame.rowconfigure(1, weight=1)
        appointments_frame.columnconfigure(0, weight=1)
        appointment_actions = ttk.Frame(appointments_frame)
        appointment_actions.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ttk.Button(
            appointment_actions,
            text="Tải lại lịch",
            command=self._refresh_appointments,
        ).pack(side="left")
        self.hide_button = ttk.Button(
            appointment_actions,
            text="Ẩn lịch đã xử lý",
            command=self._toggle_hidden,
            state="disabled",
            style="Secondary.TButton",
        )
        self.hide_button.pack(side="left", padx=8)
        ttk.Checkbutton(
            appointment_actions,
            text="Hiện lịch đã ẩn",
            variable=self.show_hidden,
            command=self._refresh_appointments,
        ).pack(side="right")
        self.appointment_list = ScrollableFrame(appointments_frame, height=135)
        self.appointment_list.grid(row=1, column=0, sticky="nsew")

        self._load_departments()
        self._refresh_appointments()

    def _run_in_background(
        self,
        task_name: str,
        task: Callable[[], Any],
        on_success: Callable[[Any], None],
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        sequence = self._background_sequences.get(task_name, 0) + 1
        self._background_sequences[task_name] = sequence
        self._background_callbacks[task_name] = (
            sequence,
            on_success,
            on_error,
        )

        def run() -> None:
            try:
                result = task()
            except Exception as error:
                self._background_results.put(
                    (task_name, sequence, None, error)
                )
            else:
                self._background_results.put(
                    (task_name, sequence, result, None)
                )

        Thread(target=run, daemon=True).start()
        if self._background_poll_id is None:
            self._background_poll_id = self.after(30, self._poll_background_tasks)

    def _poll_background_tasks(self) -> None:
        self._background_poll_id = None
        while True:
            try:
                task_name, sequence, result, error = (
                    self._background_results.get_nowait()
                )
            except queue.Empty:
                break
            callback = self._background_callbacks.get(task_name)
            if callback is None or callback[0] != sequence:
                continue
            del self._background_callbacks[task_name]
            _sequence, on_success, on_error = callback
            if error is not None:
                if on_error is not None:
                    on_error(error)
                else:
                    hien_loi(self, error)
            else:
                on_success(result)
        if self._background_callbacks and self.winfo_exists():
            self._background_poll_id = self.after(
                30, self._poll_background_tasks
            )

    def _cancel_background_poll(self, event: tk.Event) -> None:
        if event.widget is self and self._background_poll_id is not None:
            self.after_cancel(self._background_poll_id)
            self._background_poll_id = None

    def _set_mutation_busy(self, busy: bool) -> None:
        self._mutation_in_progress = busy
        self.book_button.configure(state="disabled" if busy else "normal")
        appointment = self._selected_appointment()
        active = (
            not busy
            and appointment is not None
            and appointment["trang_thai"] == "CONFIRMED"
            and datetime.now() < appointment["bat_dau"]
        )
        state = "normal" if active else "disabled"
        self.reschedule_button.configure(state=state)
        self.cancel_button.configure(state=state)

    def _load_departments(self) -> None:
        self.slot_status.configure(text="Đang tải danh sách khoa...")

        def loaded(rows: list[dict[str, Any]]) -> None:
            self.departments = {
                f'{row["ten_khoa"]} (Mã {row["ma_khoa"]})': row["ma_khoa"]
                for row in rows
            }
            self.department["values"] = list(self.departments)
            if self.departments:
                self.department.current(0)
                self._department_changed()
            else:
                self.slot_status.configure(text="Chưa có khoa để đặt lịch.")

        def failed(error: Exception) -> None:
            self.slot_status.configure(text="Không tải được danh sách khoa.")
            hien_loi(self, error)

        self._run_in_background("departments", lay_khoa, loaded, failed)

    def _department_changed(
        self,
        _event: tk.Event | None = None,
        selected_doctor_id: Identifier | None = None,
    ) -> None:
        department_id = self.departments.get(self.department.get())
        self.doctors.clear()
        self.doctor_choice.set("")
        self.doctor_choice["values"] = ()
        self.slots.clear()
        self.slot_statuses.clear()
        self.selected_slot = None
        self._render_slots()
        if department_id is None:
            self.slot_status.configure(text="Hãy chọn khoa.")
            return
        self.slot_status.configure(text="Đang tải danh sách bác sĩ...")

        def loaded(rows: list[BacSiDTO]) -> None:
            self.doctors = {
                f'{row["ten_bac_si"]} (Mã {row["ma_bac_si"]})': row for row in rows
            }
            self.doctor_choice["values"] = list(self.doctors)
            selected_label = next(
                (
                    label
                    for label, doctor in self.doctors.items()
                    if doctor["ma_bac_si"] == selected_doctor_id
                ),
                None,
            )
            if selected_label is not None:
                self.doctor_choice.set(selected_label)
            elif self.doctors:
                self.doctor_choice.current(0)
            if self.doctors:
                self._find_slots()
            else:
                self.slot_status.configure(
                    text="Khoa này chưa có bác sĩ để đặt lịch."
                )

        def failed(error: Exception) -> None:
            self.slot_status.configure(text="Không tải được danh sách bác sĩ.")
            hien_loi(self, error)

        self._run_in_background(
            "doctors",
            lambda: lay_danh_sach_bac_si(department_id),
            loaded,
            failed,
        )

    def _selected_appointment(self) -> LichHenDTO | None:
        if self.selected_appointment_id is None:
            return None
        return self.appointments.get(self.selected_appointment_id)

    def _find_slots(self, _event: tk.Event | None = None) -> None:
        self._slots_request += 1
        request = self._slots_request
        doctor = self.doctors.get(self.doctor_choice.get())
        if doctor is None:
            self.slots.clear()
            self.slot_statuses.clear()
            self.selected_slot = None
            self._render_slots()
            self.slot_status.configure(text="Hãy chọn khoa và bác sĩ.")
            return
        try:
            selected_date = self.booking_date.get_date()
            appointment = self._selected_appointment()
            if (
                appointment is not None
                and appointment["trang_thai"] == "CONFIRMED"
                and datetime.now() < appointment["bat_dau"]
                and appointment["ma_bac_si"] != doctor["ma_bac_si"]
            ):
                self.slots.clear()
                self.slot_statuses.clear()
                self.selected_slot = None
                self._render_slots()
                self.slot_status.configure(
                    text="Đổi lịch chỉ áp dụng với bác sĩ hiện tại của lịch hẹn."
                )
                return
            doctor_id = doctor["ma_bac_si"]
        except Exception as error:
            hien_loi(self, error)
            return
        self.slots.clear()
        self.slot_statuses.clear()
        self.selected_slot = None
        self._render_slots()
        self.slot_status.configure(
            text=f"Đang tải khung giờ ngày {selected_date:%d/%m/%Y}..."
        )

        def loaded(rows: list[tuple[datetime, str]]) -> None:
            current_doctor = self.doctors.get(self.doctor_choice.get())
            if (
                request != self._slots_request
                or self.booking_date.get_date() != selected_date
                or current_doctor is None
                or current_doctor["ma_bac_si"] != doctor_id
            ):
                return
            self.slot_statuses = dict(rows)
            available = [slot for slot, status in rows if status == "available"]
            self.slots = {slot.strftime("%H:%M"): slot for slot in available}
            self.selected_slot = available[0] if available else None
            self.slot_status.configure(
                text=(
                    f"Còn {len(available)} khung giờ ngày {selected_date:%d/%m/%Y}. "
                    "Chọn ô màu xanh để tiếp tục."
                    if available
                    else f"Ngày {selected_date:%d/%m/%Y} không còn khung giờ phù hợp."
                )
            )
            self._render_slots()

        def failed(error: Exception) -> None:
            if request != self._slots_request:
                return
            self.slot_status.configure(text="Không tải được khung giờ.")
            hien_loi(self, error)

        self._run_in_background(
            "slots",
            lambda: cac_khung_gio_trong_ngay(doctor_id, selected_date),
            loaded,
            failed,
        )

    def _render_slots(self) -> None:
        for child in self.slot_grid.content.winfo_children():
            child.destroy()
        self.slot_buttons.clear()
        for column in range(3):
            self.slot_grid.content.columnconfigure(column, weight=1)
        if not self.slot_statuses:
            ttk.Label(
                self.slot_grid.content,
                text="Chọn bác sĩ và ngày để hiển thị các khung giờ.",
            ).grid(row=0, column=0, sticky="w", padx=8, pady=10)
            return

        for index, (slot, status) in enumerate(sorted(self.slot_statuses.items())):
            if status == "available":
                selected = slot == self.selected_slot
                label = "Đã chọn" if selected else "Còn trống"
                style = "SlotSelected.TButton" if selected else "SlotAvailable.TButton"
                button_state = "normal"
                callback = lambda current=slot: self._select_slot(current)
            else:
                label = "Đã đặt" if status == "booked" else "Đã qua"
                style = "SlotUnavailable.TButton" if status == "booked" else "SlotPast.TButton"
                button_state = "disabled"
                callback = None
            button = ttk.Button(
                self.slot_grid.content,
                text=f"{slot:%H:%M}\n{label}",
                style=style,
                state=button_state,
                command=callback,
            )
            button.grid(
                row=index // 3,
                column=index % 3,
                sticky="ew",
                padx=4,
                pady=4,
                ipadx=4,
                ipady=3,
            )
            self.slot_buttons[slot] = button

    def _select_slot(self, slot: datetime) -> None:
        if self.slot_statuses.get(slot) != "available":
            return
        self.selected_slot = slot
        self._render_slots()

    def _book(self) -> None:
        doctor = self.doctors.get(self.doctor_choice.get())
        slot = self.selected_slot
        if doctor is None or slot is None or self.slot_statuses.get(slot) != "available":
            hien_loi(
                self,
                AppError(
                    "DU_LIEU_KHONG_HOP_LE",
                    "Hãy chọn bác sĩ, ngày và một khung giờ còn trống.",
                ),
            )
            return
        self._set_mutation_busy(True)
        self.slot_status.configure(text="Đang xác nhận lịch hẹn...")

        def booked(_appointment: LichHenDTO) -> None:
            self._set_mutation_busy(False)
            messagebox.showinfo(
                "Đặt lịch", "Lịch hẹn đã được xác nhận.", parent=self
            )
            self._refresh_appointments()
            self._find_slots()

        def failed(error: Exception) -> None:
            self._set_mutation_busy(False)
            hien_loi(self, error)
            self._find_slots()

        self._run_in_background(
            "booking",
            lambda: dat_lich(
                self.patient["ma_benh_nhan"],
                self.patient["ho_ten"],
                doctor["ma_bac_si"],
                slot,
            ),
            booked,
            failed,
        )

    def _reschedule(self) -> None:
        appointment = self._selected_appointment()
        doctor = self.doctors.get(self.doctor_choice.get())
        slot = self.selected_slot
        if appointment is None or doctor is None or slot is None:
            hien_loi(
                self,
                AppError(
                    "DU_LIEU_KHONG_HOP_LE",
                    "Chọn lịch cần đổi, ngày mới và một khung giờ còn trống.",
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
        self._set_mutation_busy(True)
        self.slot_status.configure(text="Đang cập nhật lịch hẹn...")

        def rescheduled(_updated: LichHenDTO) -> None:
            self._set_mutation_busy(False)
            messagebox.showinfo("Đổi lịch", "Đã cập nhật giờ hẹn.", parent=self)
            self._refresh_appointments()

        def failed(error: Exception) -> None:
            self._set_mutation_busy(False)
            hien_loi(self, error)
            self._find_slots()
            self._appointment_selected()

        self._run_in_background(
            "rescheduling",
            lambda: doi_lich(
                appointment["ma_lich"],
                self.patient["ma_benh_nhan"],
                slot,
            ),
            rescheduled,
            failed,
        )

    def _cancel(self) -> None:
        appointment = self._selected_appointment()
        if appointment is None:
            return
        reason = _ask_cancel_reason(self, appointment)
        if reason is None:
            return
        self._set_mutation_busy(True)

        def cancelled(_result: None) -> None:
            self._set_mutation_busy(False)
            self.selected_appointment_id = None
            self._refresh_appointments()
            self._find_slots()

        def failed(error: Exception) -> None:
            self._set_mutation_busy(False)
            hien_loi(self, error)
            self._appointment_selected()

        self._run_in_background(
            "cancelling",
            lambda: huy_lich(
                appointment["ma_lich"],
                "patient",
                self.patient["ma_benh_nhan"],
                reason,
            ),
            cancelled,
            failed,
        )

    def _appointment_selected(self, _event: tk.Event | None = None) -> None:
        appointment = self._selected_appointment()
        for key, card in self.appointment_cards.items():
            card.set_selected(key == self.selected_appointment_id)
        active = (
            appointment is not None
            and appointment["trang_thai"] == "CONFIRMED"
            and datetime.now() < appointment["bat_dau"]
            and not self._mutation_in_progress
        )
        state = "normal" if active else "disabled"
        self.reschedule_button.configure(state=state)
        self.cancel_button.configure(state=state)
        self.hide_button.configure(
            text="Khôi phục lịch" if appointment and appointment["da_an"] else "Ẩn lịch đã xử lý",
            state=(
                "normal"
                if appointment
                and (
                    appointment["da_an"]
                    or appointment["trang_thai"]
                    in {"COMPLETED", "NO_SHOW", "CANCELLED"}
                )
                else "disabled"
            ),
        )
        if appointment is None:
            return
        self.booking_date.set_date(appointment["bat_dau"].date(), notify=False)
        if not date.today() <= appointment["bat_dau"].date() <= date.today() + timedelta(days=30):
            self.slots.clear()
            self.slot_statuses.clear()
            self.selected_slot = None
            self.slot_status.configure(
                text="Ngày lịch này ngoài thời hạn đặt lịch; không có giờ để đổi."
            )
            self._render_slots()
            return

        department_label = next(
            (
                label
                for label in self.departments
                if label.split(" (Mã ", 1)[0] == appointment["ten_khoa"]
            ),
            None,
        )
        current_doctor = self.doctors.get(self.doctor_choice.get())
        if department_label is not None and (
            self.department.get() != department_label
            or current_doctor is None
            or current_doctor["ma_bac_si"] != appointment["ma_bac_si"]
        ):
            self.department.set(department_label)
            self._department_changed(
                selected_doctor_id=appointment["ma_bac_si"]
            )
            return
        doctor_label = next(
            (
                label
                for label, doctor in self.doctors.items()
                if doctor["ma_bac_si"] == appointment["ma_bac_si"]
            ),
            None,
        )
        if doctor_label is not None:
            self.doctor_choice.set(doctor_label)
        self._find_slots()

    def _select_appointment(self, appointment_id: str) -> None:
        self.selected_appointment_id = appointment_id
        self._appointment_selected()

    def _refresh_appointments(self) -> None:
        try:
            rows = lich_theo_benh_nhan(
                self.patient["ma_benh_nhan"],
                bao_gom_da_an=self.show_hidden.get(),
            )
        except Exception as error:
            hien_loi(self, error)
            return
        self.appointments.clear()
        self.appointment_cards.clear()
        for child in self.appointment_list.content.winfo_children():
            child.destroy()
        if self.selected_appointment_id not in {
            str(row["ma_lich"]) for row in rows
        }:
            self.selected_appointment_id = None
        for row in rows:
            key = str(row["ma_lich"])
            self.appointments[key] = row
            details = [
                f'Bác sĩ: {row["ten_bac_si"]} · Khoa: {row["ten_khoa"]}',
                f'{_format_datetime(row["bat_dau"])}–{row["ket_thuc"]:%H:%M}',
            ]
            if row["ly_do_huy"]:
                details.append(f'Lý do hủy: {row["ly_do_huy"]}')
            if row["da_an"]:
                details.append("Lịch đang được ẩn")
            card = AppointmentCard(
                self.appointment_list.content,
                f'Mã lịch {row["ma_lich"]}',
                tuple(details),
                lambda current=key: self._select_appointment(current),
                status=STATUS_LABELS[row["trang_thai"]],
                status_color={
                    "CONFIRMED": "#8A5A00",
                    "ARRIVED": "#1677A5",
                    "COMPLETED": "#1F7A3D",
                    "NO_SHOW": "#B42318",
                    "CANCELLED": "#B42318",
                }[row["trang_thai"]],
            )
            card.pack(fill="x", padx=5, pady=4)
            card.set_selected(key == self.selected_appointment_id)
            self.appointment_cards[key] = card
        if not rows:
            ttk.Label(
                self.appointment_list.content,
                text="Chưa có lịch hẹn để hiển thị.",
            ).pack(anchor="w", padx=8, pady=10)
        self._appointment_selected()

    def _toggle_hidden(self) -> None:
        appointment = self._selected_appointment()
        if appointment is None:
            return
        try:
            if appointment["da_an"]:
                hien_lich_da_an(
                    appointment["ma_lich"],
                    "patient",
                    self.patient["ma_benh_nhan"],
                )
            else:
                an_lich_da_xu_ly(
                    appointment["ma_lich"],
                    "patient",
                    self.patient["ma_benh_nhan"],
                )
        except Exception as error:
            hien_loi(self, error)
            return
        self._refresh_appointments()


class DoctorAppointmentView(ttk.Frame):
    def __init__(self, parent: tk.Misc, doctor: BacSiDTO) -> None:
        super().__init__(parent, padding=12)
        self.doctor = doctor
        self.appointments: dict[str, LichHenDTO] = {}
        self.show_hidden = tk.BooleanVar(value=False)
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
        ttk.Label(controls, text="Ngày").pack(side="left")
        self.selected_date = CalendarDatePicker(
            controls,
            date.today(),
            self._refresh,
        )
        self.selected_date.pack(side="left", padx=5)
        ttk.Label(
            self,
            text=(
                "Chỉ hiển thị lịch gắn với bác sĩ đang đăng nhập. Dữ liệu lưu tạm "
                "trong RAM, không đồng bộ giữa các máy."
            ),
            wraplength=1000,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 8))

        self.status_tabs = ttk.Notebook(self)
        self.status_tabs.grid(row=2, column=0, columnspan=2, sticky="nsew")
        self.selected_appointment_id: str | None = None
        self.cards: dict[str, AppointmentCard] = {}
        self.card_lists: dict[str, ScrollableFrame] = {}
        self.status_groups = {
            "waiting": ("Chờ khám", {"CONFIRMED", "ARRIVED"}),
            "done": ("Đã khám", {"COMPLETED"}),
            "processed": ("Đã hủy / Vắng mặt", {"CANCELLED", "NO_SHOW"}),
        }
        for key, (title, _statuses) in self.status_groups.items():
            cards = ScrollableFrame(self.status_tabs, height=360)
            cards.content.columnconfigure(0, weight=1)
            self.card_lists[key] = cards
            self.status_tabs.add(cards, text=title)
        self.status_tabs.bind("<<NotebookTabChanged>>", self._tab_changed)

        actions = ttk.Frame(self)
        actions.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self.arrived_button = ttk.Button(
            actions,
            text="Ghi nhận đã đến",
            command=lambda: self._update_status("ARRIVED"),
            state="disabled",
            style="Info.TButton",
        )
        self.arrived_button.pack(side="left")
        self.completed_button = ttk.Button(
            actions,
            text="Tạo phiếu khám và hoàn tất",
            command=self._complete_visit,
            state="disabled",
            style="Success.TButton",
        )
        self.completed_button.pack(side="left", padx=6)
        self.no_show_button = ttk.Button(
            actions,
            text="Đánh dấu vắng mặt",
            command=lambda: self._update_status("NO_SHOW"),
            state="disabled",
            style="Danger.TButton",
        )
        self.no_show_button.pack(side="left")
        self.cancel_button = ttk.Button(
            actions,
            text="Hủy lịch",
            command=self._cancel,
            state="disabled",
            style="Danger.TButton",
        )
        self.cancel_button.pack(side="left", padx=6)
        self.hide_button = ttk.Button(
            actions,
            text="Ẩn lịch đã xử lý",
            command=self._toggle_hidden,
            state="disabled",
            style="Secondary.TButton",
        )
        self.hide_button.pack(side="left", padx=6)
        ttk.Checkbutton(
            actions,
            text="Hiện lịch đã ẩn",
            variable=self.show_hidden,
            command=self._refresh,
        ).pack(side="right")
        self._refresh()

    def _selected_appointment(self) -> LichHenDTO | None:
        if self.selected_appointment_id is None:
            return None
        return self.appointments.get(self.selected_appointment_id)

    def _tab_changed(self, _event: tk.Event | None = None) -> None:
        self.selected_appointment_id = None
        self._appointment_selected()

    def _refresh(self) -> None:
        try:
            selected_date = self.selected_date.get_date()
            rows = lich_theo_bac_si(
                self.doctor["ma_bac_si"],
                selected_date,
                bao_gom_da_an=self.show_hidden.get(),
            )
            for row in rows:
                if row["trang_thai"] == "ARRIVED" and row["ma_phieu_kham"]:
                    detail = lay_chi_tiet_lan_kham(
                        row["ma_phieu_kham"], "doctor", self.doctor["ma_bac_si"]
                    )
                    if detail["thong_tin"]["trang_thai"] == "HOAN_THANH":
                        row.update(
                            cap_nhat_trang_thai(
                                row["ma_lich"],
                                self.doctor["ma_bac_si"],
                                "COMPLETED",
                                ma_phieu_kham=row["ma_phieu_kham"],
                            )
                        )
        except Exception as error:
            hien_loi(self, error)
            return
        self.appointments.clear()
        self.cards.clear()
        for card_list in self.card_lists.values():
            for child in card_list.content.winfo_children():
                child.destroy()
        if self.selected_appointment_id not in {
            str(row["ma_lich"]) for row in rows
        }:
            self.selected_appointment_id = None
        for row in rows:
            key = str(row["ma_lich"])
            self.appointments[key] = row
            group = next(
                name
                for name, (_title, statuses) in self.status_groups.items()
                if row["trang_thai"] in statuses
            )
            details = [
                f'{_format_datetime(row["bat_dau"])} – {_format_datetime(row["ket_thuc"])}',
                f'Mã lịch: {row["ma_lich"]} · Mã bệnh nhân: {row["ma_benh_nhan"]}',
                f'Trạng thái: {STATUS_LABELS[row["trang_thai"]]}',
            ]
            if row["ma_phieu_kham"]:
                details.append(f'Phiếu khám liên kết: {row["ma_phieu_kham"]}')
            if row["ly_do_huy"]:
                details.append(f'Lý do hủy: {row["ly_do_huy"]}')
            if row["da_an"]:
                details.append("Lịch đang được ẩn")
            card = AppointmentCard(
                self.card_lists[group].content,
                f'{row["ten_benh_nhan"]} ({row["ma_benh_nhan"]})',
                tuple(details),
                lambda current=key: self._select_appointment(current),
            )
            card.pack(fill="x", padx=8, pady=5)
            card.set_selected(key == self.selected_appointment_id)
            self.cards[key] = card
        for key, card_list in self.card_lists.items():
            if not any(
                row["trang_thai"] in self.status_groups[key][1] for row in rows
            ):
                ttk.Label(
                    card_list.content,
                    text="Không có lịch hẹn trong trạng thái này.",
                ).grid(row=0, column=0, sticky="w", padx=10, pady=12)
        self._appointment_selected()

    def _select_appointment(self, appointment_id: str) -> None:
        self.selected_appointment_id = appointment_id
        self._appointment_selected()

    def _appointment_selected(
        self,
        _event: tk.Event | None = None,
    ) -> None:
        appointment = self._selected_appointment()
        for key, card in self.cards.items():
            card.set_selected(key == self.selected_appointment_id)
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
        self.completed_button.configure(
            text=(
                "Mở phiếu khám"
                if appointment and appointment["ma_phieu_kham"]
                else "Tạo / tiếp tục phiếu khám"
            )
        )
        self.hide_button.configure(
            text="Khôi phục lịch" if appointment and appointment["da_an"] else "Ẩn lịch đã xử lý",
            state=(
                "normal"
                if appointment
                and (
                    appointment["da_an"]
                    or status in {"COMPLETED", "NO_SHOW", "CANCELLED"}
                )
                else "disabled"
            ),
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
        try:
            visit_id = appointment["ma_phieu_kham"] or tim_phieu_dang_kham(
                appointment["ma_benh_nhan"], appointment["ma_bac_si"]
            )
        except Exception as error:
            hien_loi(self, error)
            return
        if visit_id is None:
            dialog = TaoPhieuKhamDialog(
                self,
                appointment["ma_benh_nhan"],
                appointment["ma_bac_si"],
                appointment["ten_benh_nhan"],
            )
            self.wait_window(dialog)
            visit_id = dialog.result
            if visit_id is None:
                return
        try:
            gan_phieu_vao_lich(
                appointment["ma_lich"], self.doctor["ma_bac_si"], visit_id
            )
        except Exception as error:
            hien_loi(self, error)
            return
        PhieuKhamDetailDialog(
            self,
            visit_id,
            vai_tro="doctor",
            ma_nguoi_xem=self.doctor["ma_bac_si"],
            on_changed=self._refresh,
        )
        self._refresh()

    def _toggle_hidden(self) -> None:
        appointment = self._selected_appointment()
        if appointment is None:
            return
        try:
            if appointment["da_an"]:
                hien_lich_da_an(
                    appointment["ma_lich"], "doctor", self.doctor["ma_bac_si"]
                )
            else:
                an_lich_da_xu_ly(
                    appointment["ma_lich"], "doctor", self.doctor["ma_bac_si"]
                )
        except Exception as error:
            hien_loi(self, error)
            return
        self._refresh()

    def _cancel(self) -> None:
        appointment = self._selected_appointment()
        if appointment is None:
            return
        reason = _ask_cancel_reason(self, appointment)
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
