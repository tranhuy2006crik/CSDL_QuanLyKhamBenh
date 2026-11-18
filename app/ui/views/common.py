import os
import logging
import subprocess
import sys
from decimal import Decimal
import shutil
import tempfile
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from typing import Callable

from app.errors import AppError

logger = logging.getLogger(__name__)


def mo_pdf_tren_trinh_duyet(path: Path) -> None:
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=True)
    else:
        subprocess.run(["xdg-open", str(path)], check=True)


def dinh_dang_tien(value: object) -> str:
    amount = Decimal(str(value or 0))
    formatted = f"{amount:,.0f}".replace(",", ".")
    return f"{formatted} VNĐ"


def hien_loi(
    parent: ttk.Widget, error: Exception, title: str = "Không thể hoàn thành"
) -> None:
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


def xac_nhan_thay_doi_chua_luu(parent: tk.Misc, on_save: Callable[[], bool]) -> bool:
    dialog = tk.Toplevel(parent)
    dialog.title("Thay đổi chưa được lưu")
    dialog.geometry("360x120")
    dialog.resizable(False, False)

    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() - dialog.winfo_width()) // 2
    y = (dialog.winfo_screenheight() - dialog.winfo_height()) // 2
    dialog.geometry(f"+{x}+{y}")

    dialog.transient(parent)
    dialog.grab_set()
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
        if on_save():
            finish(True)

    ttk.Button(buttons, text="Lưu thay đổi", command=save).pack(
        side="left", padx=(0, 6)
    )
    ttk.Button(buttons, text="Bỏ thay đổi", command=lambda: finish(True)).pack(
        side="left", padx=6
    )
    ttk.Button(
        buttons,
        text="Tiếp tục chỉnh sửa",
        command=lambda: finish(False),
    ).pack(side="right")
    dialog.protocol("WM_DELETE_WINDOW", lambda: finish(False))
    dialog.grab_set()
    parent.wait_window(dialog)
    return accepted["close"]


class PdfPreviewDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        pdf_path: Path,
        default_filename: str,
        title: str = "Xem trước tài liệu PDF",
    ) -> None:
        super().__init__(parent)
        self.withdraw()
        self.title(title)

        self.pdf_path = pdf_path
        self.default_filename = default_filename

        try:
            import pymupdf  # <-- Đã đổi từ fitz sang pymupdf
        except ImportError:
            messagebox.showerror(
                "Thiếu thư viện",
                "Vui lòng mở Terminal gõ lệnh: pip install PyMuPDF để xem trước PDF.",
                parent=parent,
            )
            self.destroy()
            return

        # Tự động cân chỉnh chiều cao để không bao giờ bị thanh Taskbar che mất nút
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        win_w = min(920, screen_w - 60)
        win_h = min(680, screen_h - 100)

        self.geometry(f"{win_w}x{win_h}")
        self.minsize(720, 520)
        self.configure(background="#F4F7FA")

        self.update_idletasks()
        x = max(0, (screen_w - win_w) // 2)
        y = max(0, (screen_h - win_h) // 2 - 15)
        self.geometry(f"+{x}+{y}")
        self.deiconify()
        self.transient(parent)
        self.grab_set()

        # Hàng 0 (Khung cuộn PDF) co giãn, Hàng 1 (Thanh 3 nút) ghim cố định ở đáy
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)
        self.columnconfigure(0, weight=1)

        viewer_frame = ttk.Frame(self)
        viewer_frame.grid(row=0, column=0, sticky="nsew")
        viewer_frame.rowconfigure(0, weight=1)
        viewer_frame.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(viewer_frame, bg="#525659", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(
            viewer_frame, orient="vertical", command=self.canvas.yview
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        # Thanh chứa 3 nút nằm ngang cố định bên dưới
        btn_frame = ttk.Frame(self, padding=(16, 10))
        btn_frame.grid(row=1, column=0, sticky="ew")

        ttk.Button(
            btn_frame,
            text="Xem trên trình duyệt",
            command=self._open_in_browser,
            style="Info.TButton",
        ).pack(side="left")

        ttk.Button(
            btn_frame,
            text="Đóng",
            command=self._close,
            style="Secondary.TButton",
        ).pack(side="right")

        ttk.Button(
            btn_frame,
            text="Lưu PDF",
            command=self._export_file,
            style="Primary.TButton",
        ).pack(side="right", padx=(0, 8))

        doc = pymupdf.open(str(self.pdf_path))  # <-- Đã đổi từ fitz
        self.tk_images: list[tk.PhotoImage] = []
        self.image_items: list[int] = []
        y_offset = 20
        center_x = win_w // 2

        for page in doc:
            pix = page.get_pixmap(matrix=pymupdf.Matrix(1.4, 1.4))  # <-- Đã đổi từ fitz
            img_data = pix.tobytes("ppm")
            tk_img = tk.PhotoImage(data=img_data)
            self.tk_images.append(tk_img)

            item_id = self.canvas.create_image(
                center_x, y_offset, image=tk_img, anchor="n"
            )
            self.image_items.append(item_id)
            y_offset += tk_img.height() + 20

        doc.close()
        self.total_height = y_offset
        self.canvas.configure(scrollregion=(0, 0, win_w, self.total_height))
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        def _on_mousewheel(event: tk.Event) -> None:
            if self.canvas.winfo_exists():
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.canvas.bind(
            "<Enter>",
            lambda _e: self.canvas.bind_all("<MouseWheel>", _on_mousewheel),
        )
        self.canvas.bind(
            "<Leave>",
            lambda _e: self.canvas.unbind_all("<MouseWheel>"),
        )
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _on_canvas_resize(self, event: tk.Event) -> None:
        center_x = event.width // 2
        for item_id in self.image_items:
            _, y = self.canvas.coords(item_id)
            self.canvas.coords(item_id, center_x, y)
        self.canvas.configure(scrollregion=(0, 0, event.width, self.total_height))

    def _open_in_browser(self) -> None:
        try:
            mo_pdf_tren_trinh_duyet(self.pdf_path)
        except Exception as error:
            hien_loi(self, error, "Không thể mở trên trình duyệt")

    def _export_file(self) -> None:
        path_text = filedialog.asksaveasfilename(
            parent=self,
            title="Lưu file PDF",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=self.default_filename,
        )
        if path_text:
            shutil.copy(str(self.pdf_path), path_text)
            messagebox.showinfo(
                "Đã lưu",
                f"Đã lưu file PDF tại:\n{path_text}",
                parent=self,
            )

    def _close(self) -> None:
        try:
            self.canvas.unbind_all("<MouseWheel>")
        except Exception:
            pass
        self.destroy()
