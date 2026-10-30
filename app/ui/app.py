import tkinter as tk
from tkinter import ttk

from app.ui.views.placeholder import PlaceholderView


class ClinicApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Quản lý khám bệnh ngoại trú và kê đơn")
        self.geometry("1100x700")
        self.minsize(850, 560)

        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        navigation = ttk.Frame(self, padding=12)
        navigation.grid(row=0, column=0, sticky="ns")
        navigation.columnconfigure(0, weight=1)

        ttk.Label(
            navigation,
            text="QUẢN LÝ KHÁM BỆNH",
            font=("TkDefaultFont", 11, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 16))

        self.content = ttk.Frame(self, padding=24)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.columnconfigure(0, weight=1)

        screens = (
            ("Trang chủ", "Trang chủ"),
            ("Xét nghiệm", "Chỉ định và kết quả xét nghiệm"),
            ("Kê đơn thuốc", "Lập và quản lý đơn thuốc"),
            ("Tìm kiếm lần khám", "Tìm kiếm và xem chi tiết lần khám"),
            ("Báo cáo lượt khám", "Báo cáo số lượt khám theo bác sĩ"),
            ("Báo cáo giá trị", "Báo cáo giá trị khám, xét nghiệm và thuốc"),
        )
        for row, (label, title) in enumerate(screens, start=1):
            ttk.Button(
                navigation,
                text=label,
                command=lambda screen_title=title: self.show_screen(screen_title),
            ).grid(row=row, column=0, sticky="ew", pady=3)

        self.show_screen("Trang chủ")

    def show_screen(self, title: str) -> None:
        for child in self.content.winfo_children():
            child.destroy()

        PlaceholderView(self.content, title=title).grid(
            row=0, column=0, sticky="nsew"
        )
