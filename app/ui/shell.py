import tkinter as tk
from tkinter import ttk

from app.errors import AppError
from app.services.clinic_service import lay_bac_si, lay_benh_nhan
from app.ui.views.common import hien_loi
from app.ui.views.doctor_portal import DoctorPortal
from app.ui.views.patient_portal import PatientPortal


class ClinicShell(ttk.Frame):
    def __init__(self, parent: tk.Misc, demo_mode: bool = False) -> None:
        super().__init__(parent, padding=16)
        self.parent = parent
        self.demo_mode = demo_mode
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self._show_home()

    def _clear(self) -> None:
        for child in self.winfo_children():
            child.destroy()

    def _show_home(self) -> None:
        self._clear()
        home = ttk.Frame(self, padding=24)
        home.grid(row=0, column=0, sticky="nsew")
        home.columnconfigure(0, weight=1)
        home.columnconfigure(1, weight=1)
        ttk.Label(
            home,
            text="Hệ thống quản lý khám bệnh ngoại trú",
            font=("TkDefaultFont", 20, "bold"),
        ).grid(row=0, column=0, columnspan=2, pady=(20, 12))
        ttk.Label(
            home,
            text=(
                "CHẾ ĐỘ DEMO OFFLINE — không đọc/ghi MySQL; dữ liệu được làm mới "
                "khi khởi động lại.\nMã bệnh nhân: 900001 hoặc 900002  |  "
                "Mã bác sĩ: 900101 hoặc 900102"
                if self.demo_mode
                else "Chọn vai trò để tiếp tục"
            ),
            font=("TkDefaultFont", 12),
            justify="center",
        ).grid(row=1, column=0, columnspan=2, pady=(0, 28))
        self.patient_button = ttk.Button(
            home,
            text="BỆNH NHÂN\nNhập mã bệnh nhân",
            command=lambda: self._show_code_entry("patient"),
            width=32,
        )
        self.patient_button.grid(row=2, column=0, padx=16, ipady=28, sticky="nsew")
        self.doctor_button = ttk.Button(
            home,
            text="BÁC SĨ\nNhập mã bác sĩ",
            command=lambda: self._show_code_entry("doctor"),
            width=32,
        )
        self.doctor_button.grid(row=2, column=1, padx=16, ipady=28, sticky="nsew")
        ttk.Label(
            home,
            text=(
                # "Lưu ý: đăng nhập bằng mã chỉ là cơ chế phân luồng cho bản đồ án, "
                # "không phải xác thực bảo mật."
            ),
            wraplength=800,
            justify="center",
        ).grid(row=3, column=0, columnspan=2, pady=24)

    def _show_code_entry(self, role: str) -> None:
        self._clear()
        screen = ttk.Frame(self, padding=24)
        screen.grid(row=0, column=0, sticky="nsew")
        screen.columnconfigure(0, weight=1)
        role_title = "Bệnh nhân" if role == "patient" else "Bác sĩ"
        ttk.Button(screen, text="← Quay lại", command=self._show_home).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            screen,
            text=f"{role_title} — nhập mã",
            font=("TkDefaultFont", 18, "bold"),
        ).grid(row=1, column=0, pady=(40, 16))
        code = ttk.Entry(screen, width=30)
        code.grid(row=2, column=0, ipady=5)
        ttk.Label(
            screen,
            text="Mã định danh không thay thế mật khẩu hoặc bước xác minh danh tính.",
        ).grid(row=3, column=0, pady=10)
        ttk.Button(
            screen,
            text="Tiếp tục",
            command=lambda: self._enter_portal(role, code.get()),
        ).grid(row=4, column=0, pady=12)
        code.bind(
            "<Return>",
            lambda _event: self._enter_portal(role, code.get()),
        )
        code.focus_set()

    def _enter_portal(self, role: str, raw_code: str) -> None:
        try:
            code = int(raw_code.strip())
        except ValueError:
            hien_loi(
                self,
                AppError(
                    "DU_LIEU_KHONG_HOP_LE",
                    "Mã định danh phải là số nguyên dương.",
                ),
            )
            return
        try:
            if role == "patient":
                record = lay_benh_nhan(code)
                if record is None:
                    hien_loi(
                        self,
                        AppError(
                            "KHONG_TIM_THAY",
                            "Không tìm thấy mã bệnh nhân demo."
                            if self.demo_mode
                            else "Không tìm thấy mã bệnh nhân trong CSDL.",
                        ),
                    )
                    return
                self._clear()
                portal = PatientPortal(self, record, self._show_home)
            else:
                record = lay_bac_si(code)
                if record is None:
                    hien_loi(
                        self,
                        AppError(
                            "KHONG_TIM_THAY",
                            "Không tìm thấy mã bác sĩ demo."
                            if self.demo_mode
                            else "Không tìm thấy mã bác sĩ trong CSDL.",
                        ),
                    )
                    return
                self._clear()
                portal = DoctorPortal(self, record, self._show_home)
        except Exception as error:
            hien_loi(self, error)
            return
        portal.grid(row=0, column=0, sticky="nsew")
