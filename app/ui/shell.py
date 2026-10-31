import tkinter as tk
from tkinter import ttk

from app.ui.ke_don import KeDonView
from app.ui.views.placeholder import PlaceholderView


class ClinicShell(ttk.Frame):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, padding=8)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=0, column=0, sticky="nsew")
        self.frames: dict[str, ttk.Frame] = {}

        self._add_screen("Xét nghiệm", "Form xét nghiệm đang chờ bàn giao.")
        self.frames["Kê đơn thuốc"] = KeDonView(self.notebook)
        self.notebook.add(self.frames["Kê đơn thuốc"], text="Kê đơn thuốc")
        self._add_screen("Tìm kiếm lần khám", "Màn hình tìm kiếm đang chờ bàn giao.")
        self._add_screen(
            "Báo cáo lượt khám", "Báo cáo lượt khám đang chờ bàn giao."
        )
        self._add_screen(
            "Báo cáo tổng giá trị", "Báo cáo tổng giá trị đang chờ bàn giao."
        )

    def _add_screen(self, title: str, message: str) -> None:
        frame = PlaceholderView(self.notebook, title=title, message=message)
        self.frames[title] = frame
        self.notebook.add(frame, text=title)
