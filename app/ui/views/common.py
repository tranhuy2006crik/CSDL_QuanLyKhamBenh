import logging
from decimal import Decimal
import tkinter as tk
from tkinter import messagebox, ttk

from app.errors import AppError


logger = logging.getLogger(__name__)


def dinh_dang_tien(value: object) -> str:
    amount = Decimal(str(value or 0))
    formatted = f"{amount:,.0f}".replace(",", ".")
    return f"{formatted} VNĐ"


def hien_loi(parent: ttk.Widget, error: Exception, title: str = "Không thể hoàn thành") -> None:
    if isinstance(error, AppError):
        messagebox.showerror(title, error.message, parent=parent)
        return
    logger.exception("Unexpected clinic UI error", exc_info=error)
    messagebox.showerror(
        "Lỗi hệ thống",
        "Không thể hoàn thành thao tác. Hãy kiểm tra kết nối hoặc thử lại.",
        parent=parent,
    )


def tao_bang(
    parent: ttk.Widget,
    columns: tuple[str, ...],
    headings: dict[str, str],
    widths: dict[str, int],
) -> ttk.Treeview:
    table = ttk.Treeview(parent, columns=columns, show="headings", selectmode="browse")
    for column in columns:
        table.heading(column, text=headings[column])
        table.column(column, width=widths.get(column, 120), anchor="w")
    return table


def xac_nhan_thay_doi_chua_luu(
    parent: tk.Misc, luu_thay_doi
) -> bool:
    dialog = tk.Toplevel(parent)
    dialog.title("Thay đổi chưa được lưu")
    dialog.transient(parent)
    dialog.resizable(False, False)
    accepted = {"close": False}
    ttk.Label(
        dialog,
        text="Bạn có thay đổi chưa lưu. Bạn muốn làm gì?",
        padding=(18, 18, 18, 10),
    ).pack()
    buttons = ttk.Frame(dialog, padding=(12, 0, 12, 12))
    buttons.pack(fill="x")

    def finish(close: bool) -> None:
        accepted["close"] = close
        dialog.destroy()

    def save() -> None:
        if luu_thay_doi():
            finish(True)

    ttk.Button(
        buttons, text="Lưu thay đổi", command=save
    ).pack(side="left", padx=(0, 6))
    ttk.Button(
        buttons, text="Bỏ thay đổi", command=lambda: finish(True)
    ).pack(side="left", padx=6)
    ttk.Button(
        buttons,
        text="Tiếp tục chỉnh sửa",
        command=lambda: finish(False),
    ).pack(side="right")
    dialog.protocol("WM_DELETE_WINDOW", lambda: finish(False))
    dialog.grab_set()
    parent.wait_window(dialog)
    return accepted["close"]
