import logging
from decimal import Decimal
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
