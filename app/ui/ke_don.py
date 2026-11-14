import logging
import tkinter as tk
from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from tkinter import messagebox, ttk

from app.contracts import DongThuocDraft, DongThuocInput, Identifier, ThuocDanhMuc
from app.errors import AppError
from app.services.don_thuoc_service import luu_don_thuoc, xoa_don_thuoc
from app.services.tra_cuu_service import lay_don_thuoc, lay_thuoc
from app.ui.views.common import xac_nhan_thay_doi_chua_luu

logger = logging.getLogger(__name__)


def dinh_dang_tien_viet(gia_tri: Decimal | float | int) -> str:
    """Định dạng tiền VNĐ bỏ số thập phân"""
    return f"{int(gia_tri):,} VNĐ".replace(",", ".")


class KeDonView(ttk.Frame):
    def __init__(self, parent: tk.Misc, ma_phieu: Identifier | None = None) -> None:
        super().__init__(parent, padding=12)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        self.medicines: dict[str, ThuocDanhMuc] = {}
        self.draft: dict[Identifier, DongThuocDraft] = {}
        self.original_quantities: dict[Identifier, int] = {}
        self.current_order_id: Identifier | None = None
        self._saved_snapshot: tuple[object, ...] | None = None
        self.editing_medicine_id: Identifier | None = None

        self._build_widgets()

        if ma_phieu is not None:
            self.ma_phieu.insert(0, str(ma_phieu))
            self._lock_entry(self.ma_phieu)
            self._reload_medicines(show_errors=False)
            self._load_order(show_missing_message=False)

    def _lock_entry(self, entry: ttk.Entry) -> None:
        """Khóa Entry nhưng vẫn giữ màu chữ đậm/rõ nét, không bị mờ xám"""
        entry.configure(font=("TkDefaultFont", 10, "bold"), foreground="black")
        entry.bind("<Key>", lambda e: "break")
        entry.bind("<BackSpace>", lambda e: "break")
        entry.bind("<Delete>", lambda e: "break")

    def _unlock_entry(self, entry: ttk.Entry) -> None:
        """Mở khóa Entry"""
        entry.unbind("<Key>")
        entry.unbind("<BackSpace>")
        entry.unbind("<Delete>")
        entry.configure(font=("TkDefaultFont", 10), foreground="black")

    def _build_widgets(self) -> None:
        ttk.Label(
            self,
            text="Lập và quản lý đơn thuốc",
            font=("TkDefaultFont", 16, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        header = ttk.LabelFrame(self, text="Thông tin đơn", padding=12)
        header.grid(row=1, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)

        self.lbl_ngay_lap = ttk.Label(
            header,
            text=f"Ngày lập: {datetime.now().strftime('%d/%m/%Y')}",
            foreground="gray",
        )
        self.lbl_ngay_lap.grid(row=0, column=2, sticky="ne")

        ttk.Label(
            header, text="Mã phiếu khám", font=("TkDefaultFont", 10, "bold")
        ).grid(row=0, column=0, sticky="w", pady=4)
        self.ma_phieu = ttk.Entry(header, width=30)
        self.ma_phieu.grid(row=0, column=1, sticky="w", padx=(20, 0), pady=4)

        ttk.Label(header, text="Mã đơn", font=("TkDefaultFont", 10, "bold")).grid(
            row=1, column=0, sticky="w", pady=4
        )
        self.ma_don = ttk.Entry(header, width=30)
        self.ma_don.grid(row=1, column=1, sticky="w", padx=(20, 0), pady=4)

        ttk.Label(
            header, text="Lời dặn chung", font=("TkDefaultFont", 10, "bold")
        ).grid(row=2, column=0, sticky="nw", pady=4)
        self.loi_dan = tk.Text(
            header, height=3, wrap="word", font=("TkDefaultFont", 10)
        )
        self.loi_dan.grid(
            row=2, column=1, columnspan=2, sticky="ew", padx=(20, 0), pady=4
        )

        medicine_frame = ttk.LabelFrame(self, text="Chỉ định thuốc", padding=12)
        medicine_frame.grid(row=2, column=0, sticky="ew", pady=(12, 0))

        medicine_frame.columnconfigure(1, weight=0)
        medicine_frame.columnconfigure(2, weight=1)
        medicine_frame.columnconfigure(3, weight=0)

        ttk.Label(
            medicine_frame, text="Thuốc", font=("TkDefaultFont", 10, "bold")
        ).grid(row=0, column=0, sticky="w", pady=6)
        self.medicine_box = ttk.Combobox(medicine_frame, state="readonly", width=50)
        self.medicine_box.grid(row=0, column=1, sticky="w", padx=(10, 15), pady=6)
        self.medicine_box.bind("<<ComboboxSelected>>", self._show_medicine_info)

        self.medicine_info = ttk.Label(
            medicine_frame, text="Đang tải danh mục...", foreground="gray"
        )
        self.medicine_info.grid(row=1, column=1, sticky="w", padx=(10, 15), pady=(0, 6))

        qty_frame = ttk.Frame(medicine_frame)
        qty_frame.grid(row=0, column=2, columnspan=2, sticky="e", pady=6)

        ttk.Label(qty_frame, text="Số lượng", font=("TkDefaultFont", 10, "bold")).pack(
            side="left"
        )
        self.quantity = ttk.Entry(qty_frame, width=12)
        self.quantity.pack(side="left", padx=(10, 0))

        ttk.Label(
            medicine_frame, text="Cách dùng", font=("TkDefaultFont", 10, "bold")
        ).grid(row=2, column=0, sticky="nw", pady=6)
        self.dosage = tk.Text(
            medicine_frame, height=3, wrap="word", font=("TkDefaultFont", 10)
        )
        self.dosage.grid(
            row=2, column=1, columnspan=3, sticky="ew", padx=(10, 0), pady=6
        )

        self.med_action_frame = ttk.Frame(medicine_frame)
        self.med_action_frame.grid(
            row=3, column=0, columnspan=4, sticky="e", pady=(10, 0)
        )

        self.btn_delete_med_inline = ttk.Button(
            self.med_action_frame,
            text="Xóa thuốc",
            command=self._prompt_remove_medicine_inline,
            style="Danger.TButton",
        )
        self.btn_cancel_edit = ttk.Button(
            self.med_action_frame,
            text="Hủy sửa",
            command=self._reset_medicine_form,
            style="Secondary.TButton",
        )
        self.btn_submit_med = ttk.Button(
            self.med_action_frame,
            text="Thêm thuốc",
            command=self._submit_medicine,
            style="Primary.TButton",
        )

        self.btn_submit_med.pack(side="right")

        table_container = ttk.Frame(self)
        table_container.grid(row=3, column=0, sticky="nsew", pady=(12, 0))
        table_container.columnconfigure(0, weight=1)
        table_container.rowconfigure(0, weight=1)

        columns = (
            "ma_thuoc",
            "ten_thuoc",
            "so_luong",
            "don_vi",
            "cach_dung",
            "don_gia",
            "thanh_tien",
        )
        self.table = ttk.Treeview(
            table_container, columns=columns, show="headings", selectmode="browse"
        )

        headings = {
            "ma_thuoc": ("Mã", 80, "center"),
            "ten_thuoc": ("Thuốc", 200, "w"),
            "so_luong": ("Số lượng", 80, "center"),
            "don_vi": ("Đơn vị", 80, "center"),
            "cach_dung": ("Cách dùng", 250, "w"),
            "don_gia": ("Đơn giá áp dụng", 120, "e"),
            "thanh_tien": ("Thành tiền", 120, "e"),
        }

        for key, (label, width, anchor) in headings.items():
            self.table.heading(key, text=label)
            self.table.column(key, width=width, anchor=anchor)

        self.table.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(
            table_container, orient="vertical", command=self.table.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.table.configure(yscrollcommand=scrollbar.set)

        self.table.bind("<Double-1>", self._on_table_double_click)

        controls = ttk.Frame(self)
        controls.grid(row=4, column=0, sticky="ew", pady=(12, 12))

        ttk.Button(
            controls, text="Lưu đơn", command=self._save_order, style="Success.TButton"
        ).pack(side="right")
        ttk.Button(
            controls,
            text="Hủy đơn đã lưu",
            command=self._delete_order,
            style="Danger.TButton",
        ).pack(side="right", padx=(0, 8))

        self.total_label = ttk.Label(
            controls,
            text="Tổng đơn: 0 VNĐ",
            font=("TkDefaultFont", 11, "bold"),
            foreground="#C0392B",
        )
        self.total_label.pack(side="left")

    def _handle_error(self, error: Exception) -> None:
        if isinstance(error, AppError):
            field_widgets = {
                "ma_phieu": self.ma_phieu,
                "ma_don": self.ma_don,
                "loi_dan": self.loi_dan,
            }
            if error.field in field_widgets:
                field_widgets[error.field].focus_set()
            if error.code in {"KHONG_DU_TON", "XUNG_DOT_DU_LIEU"}:
                self._reload_medicines(show_errors=False)
            messagebox.showerror("Không thể hoàn thành", error.message, parent=self)
            return
        logger.exception("Unexpected error in prescription form", exc_info=error)
        messagebox.showerror(
            "Lỗi hệ thống",
            "Không thể hoàn thành thao tác. Hãy tải lại dữ liệu hoặc thử lại.",
            parent=self,
        )

    def _reload_medicines(self, show_errors: bool = True) -> bool:
        try:
            rows = lay_thuoc()
        except Exception as error:
            if show_errors:
                self._handle_error(error)
            return False

        self.medicines = {str(row["ma_thuoc"]): row for row in rows}
        self.medicine_box["values"] = [
            f'{row["ma_thuoc"]} - {row["ten_thuoc"]}' for row in rows
        ]
        self.medicine_info.configure(text="Sẵn sàng chỉ định")
        self._refresh_table()
        return True

    def _selected_medicine(self) -> ThuocDanhMuc | None:
        selected = self.medicine_box.get()
        if not selected:
            return None
        try:
            medicine_id = selected.split(" - ", 1)[0]
            return self.medicines.get(medicine_id)
        except (ValueError, IndexError):
            return None

    def _show_medicine_info(self, _event: tk.Event | None = None) -> None:
        medicine = self._selected_medicine()
        if medicine is None:
            self.medicine_info.configure(text="Chưa có thông tin thuốc")
            return
        self.medicine_info.configure(
            text=f'Giá: {dinh_dang_tien_viet(medicine["don_gia"])} / {medicine["don_vi_tinh"]} — Tồn kho: {medicine["so_luong_co_san"]}'
        )

    def _submit_medicine(self) -> None:
        medicine = self._selected_medicine()
        if medicine is None:
            self._handle_error(
                AppError(
                    "DU_LIEU_KHONG_HOP_LE", "Vui lòng chọn một loại thuốc.", "ds_thuoc"
                )
            )
            return

        try:
            quantity = int(self.quantity.get().strip())
            if quantity <= 0:
                raise ValueError
        except ValueError:
            self._handle_error(
                AppError(
                    "DU_LIEU_KHONG_HOP_LE",
                    "Số lượng kê phải là số nguyên dương lớn hơn 0.",
                    "ds_thuoc",
                )
            )
            return

        stock = int(medicine.get("so_luong_co_san", 0))
        if quantity > stock:
            self._handle_error(
                AppError(
                    "KHONG_DU_TON",
                    f"Kho chỉ còn {stock} {medicine['don_vi_tinh']}, không đủ số lượng kê!",
                )
            )
            return

        dosage = self.dosage.get("1.0", "end").strip()
        if not dosage:
            self._handle_error(
                AppError(
                    "DU_LIEU_KHONG_HOP_LE", "Vui lòng nhập cách dùng thuốc.", "ds_thuoc"
                )
            )
            return

        medicine_id = medicine["ma_thuoc"]

        if not self.editing_medicine_id and medicine_id in self.draft:
            messagebox.showwarning(
                "Trùng lặp thuốc",
                "Thuốc này đã có trong đơn.\nVui lòng đúp chuột vào dòng thuốc ở bảng bên dưới để cập nhật số lượng thay vì thêm mới!",
                parent=self,
            )
            return

        self.draft[medicine_id] = {
            "ma_thuoc": medicine_id,
            "so_luong_ke": quantity,
            "cach_dung": dosage,
            "don_gia_ap_dung": medicine["don_gia"],
            "ten_thuoc": medicine["ten_thuoc"],
            "don_vi_tinh": medicine["don_vi_tinh"],
        }

        self._reset_medicine_form()
        self._refresh_table()

    def _reset_medicine_form(self) -> None:
        self.editing_medicine_id = None
        self.medicine_box.configure(state="readonly")
        self.medicine_box.set("")
        self.quantity.delete(0, "end")
        self.dosage.delete("1.0", "end")
        self.medicine_info.configure(text="Sẵn sàng chỉ định")

        self.btn_submit_med.configure(text="Thêm thuốc")
        self.btn_delete_med_inline.pack_forget()
        self.btn_cancel_edit.pack_forget()

    def _on_table_double_click(self, event: tk.Event) -> None:
        """Bắt sự kiện Double Click để sửa"""
        selection = self.table.selection()
        if selection:
            self._edit_medicine(selection[0])

    def _edit_medicine(self, medicine_id: str) -> None:
        row = self.draft.get(medicine_id)
        if not row:
            return

        self.editing_medicine_id = medicine_id

        self.medicine_box.configure(state="normal")
        self.medicine_box.set(f"{medicine_id} - {row['ten_thuoc']}")
        self.medicine_box.configure(state="disabled")

        self.quantity.delete(0, "end")
        self.quantity.insert(0, str(row["so_luong_ke"]))

        self.dosage.delete("1.0", "end")
        self.dosage.insert("1.0", row["cach_dung"])

        self._show_medicine_info()

        self.btn_submit_med.configure(text="Cập nhật thuốc")
        self.btn_cancel_edit.pack(side="right", padx=(0, 8))
        self.btn_delete_med_inline.pack(side="right", padx=(0, 8))

    def _prompt_remove_medicine_inline(self) -> None:
        """Xóa thuốc khỏi bản nháp từ form chỉnh sửa"""
        medicine_id = self.editing_medicine_id
        if not medicine_id:
            return

        row = self.draft.get(medicine_id)
        if not row:
            return

        if messagebox.askyesno(
            "Xóa thuốc", f"Xóa '{row['ten_thuoc']}' khỏi đơn thuốc nháp?", parent=self
        ):
            self.draft.pop(medicine_id, None)
            self._reset_medicine_form()
            self._refresh_table()

    def _refresh_table(self) -> None:
        for item in self.table.get_children():
            self.table.delete(item)

        order_total = Decimal("0")
        for medicine_id in sorted(self.draft, key=str):
            row = self.draft[medicine_id]
            price = Decimal(str(row["don_gia_ap_dung"]))
            total = price * row["so_luong_ke"]
            order_total += total

            self.table.insert(
                "",
                "end",
                iid=str(medicine_id),
                values=(
                    medicine_id,
                    row["ten_thuoc"],
                    row["so_luong_ke"],
                    row["don_vi_tinh"],
                    row["cach_dung"],
                    dinh_dang_tien_viet(price),
                    dinh_dang_tien_viet(total),
                ),
            )
        self.total_label.configure(text=f"Tổng đơn: {dinh_dang_tien_viet(order_total)}")

    def _snapshot(self) -> tuple[object, ...]:
        return (
            self.ma_phieu.get().strip(),
            self.ma_don.get().strip(),
            self.loi_dan.get("1.0", "end").strip(),
            tuple(
                sorted(
                    (str(m_id), r["so_luong_ke"], r["cach_dung"])
                    for m_id, r in self.draft.items()
                )
            ),
        )

    def request_close(self, close_window: Callable[[], None]) -> None:
        if (
            self._saved_snapshot is not None
            and self._snapshot() != self._saved_snapshot
            and not xac_nhan_thay_doi_chua_luu(self.winfo_toplevel(), self._save_order)
        ):
            return
        close_window()

    def _load_order(self, show_missing_message: bool = True) -> None:
        try:
            appointment_id = self.ma_phieu.get().strip()
            if not appointment_id:
                raise AppError(
                    "DU_LIEU_KHONG_HOP_LE", "Hãy nhập mã phiếu khám.", "ma_phieu"
                )

            order = lay_don_thuoc(appointment_id)
            self.draft.clear()
            self.original_quantities.clear()

            if order is None:
                self.current_order_id = None
                self._unlock_entry(self.ma_don)
                self.ma_don.delete(0, "end")
                self.lbl_ngay_lap.configure(
                    text=f"Ngày lập: {datetime.now().strftime('%d/%m/%Y')}"
                )
                self.loi_dan.delete("1.0", "end")
                self._refresh_table()
                self._saved_snapshot = self._snapshot()
                return

            self.current_order_id = order["ma_don"]
            self._unlock_entry(self.ma_don)
            self.ma_don.delete(0, "end")
            self.ma_don.insert(0, str(order["ma_don"]))
            self._lock_entry(self.ma_don)

            self.lbl_ngay_lap.configure(
                text=f"Ngày lập: {order['ngay_lap'].strftime('%d/%m/%Y')}"
            )

            self.loi_dan.delete("1.0", "end")
            self.loi_dan.insert("1.0", order["loi_dan"] or "")

            for line in order["ds_thuoc"]:
                medicine_id = line["ma_thuoc"]
                self.original_quantities[medicine_id] = line["so_luong_ke"]
                self.draft[medicine_id] = {
                    "ma_thuoc": medicine_id,
                    "ten_thuoc": line["ten_thuoc"],
                    "don_vi_tinh": line["don_vi_tinh"],
                    "so_luong_ke": line["so_luong_ke"],
                    "cach_dung": line["cach_dung"],
                    "don_gia_ap_dung": line["don_gia_ap_dung"],
                }
            self._reload_medicines()
            self._saved_snapshot = self._snapshot()
        except Exception as error:
            self._handle_error(error)

    def _save_order(self) -> bool:
        try:
            appointment_id = self.ma_phieu.get().strip()
            if not appointment_id:
                raise AppError(
                    "DU_LIEU_KHONG_HOP_LE", "Hãy nhập mã phiếu khám.", "ma_phieu"
                )

            order_id = self.ma_don.get().strip()
            if not order_id:
                raise AppError(
                    "DU_LIEU_KHONG_HOP_LE", "Hãy nhập mã đơn thuốc.", "ma_don"
                )

            date_str = self.lbl_ngay_lap.cget("text").replace("Ngày lập: ", "").strip()
            order_date = datetime.strptime(date_str, "%d/%m/%Y").date()

            medicines: list[DongThuocInput] = [
                {
                    "ma_thuoc": row["ma_thuoc"],
                    "so_luong_ke": row["so_luong_ke"],
                    "cach_dung": row["cach_dung"],
                }
                for row in self.draft.values()
            ]

            reduced_stock = any(
                row["so_luong_ke"] < self.original_quantities.get(medicine_id, 0)
                for medicine_id, row in self.draft.items()
            ) or any(
                medicine_id not in self.draft
                for medicine_id in self.original_quantities
            )

            if reduced_stock and not messagebox.askyesno(
                "Xác nhận hoàn tồn",
                "Giảm hoặc bỏ thuốc sẽ hoàn phần số lượng tương ứng về tồn kho. Xác nhận lưu?",
                parent=self,
            ):
                return False

            saved = luu_don_thuoc(
                ma_phieu=appointment_id,
                ma_don=order_id,
                ngay_lap=order_date,
                loi_dan=self.loi_dan.get("1.0", "end").strip() or None,
                ds_thuoc=medicines,
                tao_moi=self.current_order_id is None,
            )

            self.current_order_id = saved["ma_don"]
            self._lock_entry(self.ma_don)

            self.original_quantities = {
                line["ma_thuoc"]: line["so_luong_ke"] for line in saved["ds_thuoc"]
            }
            self._saved_snapshot = self._snapshot()

            if self._reload_medicines(show_errors=False):
                messagebox.showinfo(
                    "Thành công", "Đã lưu đơn thuốc và cập nhật tồn kho.", parent=self
                )
            return True

        except Exception as error:
            self._handle_error(error)
            return False

    def _delete_order(self) -> None:
        if self.current_order_id is None:
            self._handle_error(
                AppError("KHONG_TIM_THAY", "Hãy lưu đơn trước khi có thể hủy.")
            )
            return

        if not messagebox.askyesno(
            "Hủy đơn thuốc",
            "Toàn bộ số lượng thuốc đã kê sẽ được hoàn lại kho. Bạn có chắc muốn Hủy đơn này?",
            parent=self,
        ):
            return

        try:
            appointment_id = self.ma_phieu.get().strip()
            xoa_don_thuoc(appointment_id, self.current_order_id)

            self.current_order_id = None
            self.original_quantities.clear()
            self.draft.clear()

            self._unlock_entry(self.ma_don)
            self.ma_don.delete(0, "end")
            self.loi_dan.delete("1.0", "end")

            self._reset_medicine_form()
            self._refresh_table()
            self._saved_snapshot = self._snapshot()

            if self._reload_medicines(show_errors=False):
                messagebox.showinfo(
                    "Thành công", "Đã hủy đơn và hoàn tồn kho.", parent=self
                )

        except Exception as error:
            self._handle_error(error)
