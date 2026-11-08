import tkinter as tk

from app.demo_data import disable_demo_mode, enable_demo_mode
from app.services.appointment_service import reset_appointment_sessions
from app.ui.shell import ClinicShell
from app.ui.styles import configure_styles


class ClinicApp(tk.Tk):
    def __init__(self, demo_mode: bool = False) -> None:
        if demo_mode:
            enable_demo_mode()
        else:
            disable_demo_mode()
        reset_appointment_sessions()
        super().__init__()
        configure_styles(self)
        self.title(
            "Quản lý khám bệnh ngoại trú và kê đơn"
            + (" — DEMO OFFLINE, không kết nối MySQL" if demo_mode else "")
        )
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        width = min(1250, screen_width - 40)
        height = min(760, screen_height - 120)
        self.geometry(
            f"{width}x{height}"
            f"+{max(0, (screen_width - width) // 2)}"
            f"+{max(0, (screen_height - height) // 2 - 20)}"
        )
        self.minsize(min(1000, width), min(620, height))
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.shell = ClinicShell(self, demo_mode=demo_mode)
        self.shell.grid(row=0, column=0, sticky="nsew")
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _close(self) -> None:
        reset_appointment_sessions()
        disable_demo_mode()
        self.destroy()
