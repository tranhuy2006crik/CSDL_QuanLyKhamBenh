import tkinter as tk

from app.ui.shell import ClinicShell


class ClinicApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Quản lý khám bệnh ngoại trú và kê đơn")
        self.geometry("1250x760")
        self.minsize(1000, 620)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.shell = ClinicShell(self)
        self.shell.grid(row=0, column=0, sticky="nsew")
