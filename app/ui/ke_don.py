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


class KeDonView(ttk.Frame):
    def __init__(self, parent: tk.Misc, ma_phieu: Identifier | None = None) -> None:
        super().__init__(parent, padding=12)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)
        self.medicines: dict[str, ThuocDanhMuc] = {}
        self.draft: dict[Identifier, DongThuocDraft] = {}
        self.original_quantities: dict[Identifier, int] = {}
        self.current_order_id: Identifier | None = None
        self._saved_snapshot: tuple[object, ...] | None = None
        self._build_widgets()
        if ma_phieu is not None:
            self.ma_phieu.insert(0, str(ma_phieu))
            self.ma_phieu.configure(state="readonly")
            self._reload_medicines(show_errors=False)
            self._load_order(show_missing_message=False)

    def _build_widgets(self) -> None:
        ttk.Label(
            self,
            text="Lập và quản lý đơn thuốc",
            font=("TkDefaultFont", 16, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        header = ttk.LabelFrame(self, text="Thông tin đơn", padding=8)
        header.grid(row=1, column=0, sticky="ew")
        for column in range(6):
            header.columnconfigure(column, weight=1 if column in (1, 3, 5) else 0)

        self.ma_phieu = self._entry(header, "Mã phiếu khám", 0, 0)
        self.ma_don = self._entry(header, "Mã đơn (nhập tay)", 0, 2)
        self.ngay_lap = self._entry(header, "Ngày lập (dd/mm/yyyy)", 0, 4)
        self.ngay_lap.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.ngay_lap.configure(state="readonly")
        ttk.Button(header, text="Tải đơn theo phiếu", command=self._load_order).grid(
            row=0, column=6, padx=(8, 0), sticky="ew"
        )

        ttk.Label(header, text="Lời dặn chung").grid(
            row=1, column=0, sticky="w", pady=(8, 0)
        )
        self.loi_dan = tk.Text(header, height=2, wrap="word")
        self.loi_dan.grid(
            row=1, column=1, columnspan=6, sticky="ew", pady=(8, 0)
        )

        medicine_frame = ttk.LabelFrame(self, text="Thêm thuốc", padding=8)
        medicine_frame.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        medicine_frame.columnconfigure(1, weight=1)
        ttk.Label(medicine_frame, text="Thuốc").grid(row=0, column=0, sticky="w")
        self.medicine_box = ttk.Combobox(medicine_frame, state="readonly")
        self.medicine_box.grid(row=0, column=1, sticky="ew", padx=6)
        self.medicine_box.bind("<<ComboboxSelected>>", self._show_medicine_info)
        self.medicine_info = ttk.Label(medicine_frame, text="Tải danh mục để bắt đầu")
        self.medicine_info.grid(row=0, column=2, sticky="w", padx=6)
        self.quantity = self._entry(medicine_frame, "Số lượng", 0, 3)
        self.dosage = self._entry(medicine_frame, "Cách dùng", 0, 5)
        ttk.Button(
            medicine_frame, text="Tải danh mục", command=self._reload_medicines
        ).grid(row=0, column=7, padx=4)
        ttk.Button(medicine_frame, text="Thêm dòng", command=self._add_medicine).grid(
            row=0, column=8, padx=4
        )

        table_frame = ttk.Frame(self)
        table_frame.grid(row=4, column=0, sticky="nsew", pady=(8, 0))
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        columns = (
            "ma_thuoc",
            "ten_thuoc",
            "so_luong",
            "don_vi",
            "cach_dung",
            "don_gia",
            "thanh_tien",
            "ton",
        )
        self.table = ttk.Treeview(
            table_frame, columns=columns, show="headings", selectmode="browse"
        )
        headings = {
            "ma_thuoc": "Mã",
            "ten_thuoc": "Thuốc",
            "so_luong": "Số lượng",
            "don_vi": "Đơn vị",
            "cach_dung": "Cách dùng",
            "don_gia": "Đơn giá áp dụng",
            "thanh_tien": "Thành tiền",
            "ton": "Tồn hiện tại",
        }
        for key, label in headings.items():
            self.table.heading(key, text=label)
            self.table.column(key, width=115, anchor="w")
        self.table.column("ten_thuoc", width=190)
        self.table.column("cach_dung", width=180)
        self.table.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.table.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.table.configure(yscrollcommand=scrollbar.set)

        controls = ttk.Frame(self)
        controls.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(
            controls,
            text="Xóa thuốc khỏi bản nháp",
            command=self._remove_medicine,
            style="Secondary.TButton",
        ).pack(side="left")
        ttk.Button(
            controls,
            text="Lưu đơn",
            command=self._save_order,
            style="Primary.TButton",
        ).pack(side="right", padx=(6, 0))
        ttk.Button(
            controls,
            text="Hủy đơn đã lưu",
            command=self._delete_order,
            style="Danger.TButton",
        ).pack(side="right")
        self.total_label = ttk.Label(
            self, text="Tổng đơn: 0 VNĐ", font=("TkDefaultFont", 10, "bold")
        )
        self.total_label.grid(row=5, column=0, sticky="e", pady=(8, 0))

    @staticmethod
    def _entry(
        parent: ttk.Frame, label: str, row: int, column: int
    ) -> ttk.Entry:
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w")
        entry = ttk.Entry(parent)
        entry.grid(row=row, column=column + 1, sticky="ew", padx=(4, 8))
        return entry

    def _handle_error(self, error: Exception) -> None:
        if isinstance(error, AppError):
            field_widgets = {
                "ma_phieu": self.ma_phieu,
                "ma_don": self.ma_don,
                "ngay_lap": self.ngay_lap,
                "loi_dan": self.loi_dan,
            }
            if error.field in field_widgets:
                field_widgets[error.field].focus_set()
            if error.code in {"KHONG_DU_TON", "XUNG_DOT_DU_LIEU"}:
                self._reload_medicines(show_errors=False)
            if error.code == "DA_LUU_CAN_TAI_LAI":
                self.current_order_id = self.ma_don.get().strip() or None
                self.original_quantities = {
                    medicine_id: row["so_luong_ke"]
                    for medicine_id, row in self.draft.items()
                }
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
            f'{row["ma_thuoc"]} - {row["ten_thuoc"]}'
            for row in rows
        ]
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
            text=(
                f'{medicine["don_gia"]} VNĐ / {medicine["don_vi_tinh"]}; '
                f'tồn {medicine["so_luong_co_san"]}'
            )
        )

    def _add_medicine(self) -> None:
        medicine = self._selected_medicine()
        if medicine is None:
            self._handle_error(
                AppError(
                    "DU_LIEU_KHONG_HOP_LE",
                    "Hãy tải danh mục và chọn một thuốc.",
                    "ds_thuoc",
                )
            )
            return
        try:
            quantity = int(self.quantity.get().strip())
        except ValueError:
            self._handle_error(
                AppError(
                    "DU_LIEU_KHONG_HOP_LE",
                    "Số lượng kê phải là số nguyên dương.",
                    "ds_thuoc",
                )
            )
            return
        dosage = self.dosage.get().strip()
        if quantity <= 0 or not dosage:
            self._handle_error(
                AppError(
                    "DU_LIEU_KHONG_HOP_LE",
                    "Số lượng phải dương và cách dùng không được để trống.",
                    "ds_thuoc",
                )
            )
            return

        medicine_id = medicine["ma_thuoc"]
        self.draft[medicine_id] = {
            "ma_thuoc": medicine_id,
            "so_luong_ke": quantity,
            "cach_dung": dosage,
            "don_gia_ap_dung": medicine["don_gia"],
            "ten_thuoc": medicine["ten_thuoc"],
            "don_vi_tinh": medicine["don_vi_tinh"],
        }
        self._refresh_table()

    def _remove_medicine(self) -> None:
        selection = self.table.selection()
        if not selection:
            return
        medicine_id = next(
            (key for key in self.draft if str(key) == selection[0]), None
        )
        if medicine_id is not None:
            self.draft.pop(medicine_id, None)
        self._refresh_table()

    def _refresh_table(self) -> None:
        for item in self.table.get_children():
            self.table.delete(item)
        order_total = Decimal("0")
        for medicine_id in sorted(self.draft, key=str):
            row = self.draft[medicine_id]
            medicine = self.medicines.get(str(medicine_id), {})
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
                    f"{price} VNĐ",
                    f"{total} VNĐ",
                    medicine.get("so_luong_co_san", "Không rõ"),
                ),
            )
        self.total_label.configure(text=f"Tổng đơn: {order_total} VNĐ")

    def _snapshot(self) -> tuple[object, ...]:
        return (
            self.ma_phieu.get().strip(),
            self.ma_don.get().strip(),
            self.ngay_lap.get().strip(),
            self.loi_dan.get("1.0", "end").strip(),
            tuple(
                sorted(
                    (
                        str(medicine_id),
                        row["so_luong_ke"],
                        row["cach_dung"],
                    )
                    for medicine_id, row in self.draft.items()
                )
            ),
        )

    def request_close(self, close_window: Callable[[], None]) -> None:
        if (
            self._saved_snapshot is not None
            and self._snapshot() != self._saved_snapshot
            and not xac_nhan_thay_doi_chua_luu(
                self.winfo_toplevel(), self._save_order
            )
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
                self.ma_don.delete(0, "end")
                self._set_order_date(datetime.now().strftime("%d/%m/%Y"))
                self.loi_dan.delete("1.0", "end")
                self._refresh_table()
                self._saved_snapshot = self._snapshot()
                if show_missing_message:
                    messagebox.showinfo(
                        "Đơn thuốc",
                        "Phiếu khám chưa có đơn. Nhập mã đơn mới để tạo.",
                        parent=self,
                    )
                return

            self.current_order_id = order["ma_don"]
            self.ma_don.delete(0, "end")
            self.ma_don.insert(0, str(order["ma_don"]))
            self._set_order_date(order["ngay_lap"].strftime("%d/%m/%Y"))
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
        except (ValueError, TypeError):
            self._handle_error(
                AppError(
                    "DU_LIEU_KHONG_HOP_LE",
                    "Mã phiếu khám không hợp lệ.",
                    "ma_phieu",
                )
            )
        except Exception as error:
            self._handle_error(error)

    def _set_order_date(self, value: str) -> None:
        self.ngay_lap.configure(state="normal")
        self.ngay_lap.delete(0, "end")
        self.ngay_lap.insert(0, value)
        self.ngay_lap.configure(state="readonly")

    def _save_order(self) -> bool:
        try:
            try:
                appointment_id = self.ma_phieu.get().strip()
                if not appointment_id:
                    raise ValueError("empty")
            except ValueError as error:
                raise AppError(
                    "DU_LIEU_KHONG_HOP_LE",
                    "Hãy nhập mã phiếu khám.",
                    "ma_phieu",
                ) from error
            try:
                order_id = self.ma_don.get().strip()
                if not order_id:
                    raise ValueError("empty")
            except ValueError as error:
                raise AppError(
                    "DU_LIEU_KHONG_HOP_LE",
                    "Hãy nhập mã đơn thuốc.",
                    "ma_don",
                ) from error
            try:
                order_date = datetime.strptime(
                    self.ngay_lap.get().strip(), "%d/%m/%Y"
                ).date()
            except ValueError as error:
                raise AppError(
                    "DU_LIEU_KHONG_HOP_LE",
                    "Ngày lập phải theo định dạng dd/mm/yyyy.",
                    "ngay_lap",
                ) from error
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
                (
                    "Giảm hoặc bỏ thuốc sẽ hoàn phần số lượng tương ứng về tồn kho "
                    "theo giả định nghiệp vụ của bài tập. Xác nhận lưu thay đổi?"
                ),
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
            self.original_quantities = {
                line["ma_thuoc"]: line["so_luong_ke"]
                for line in saved["ds_thuoc"]
            }
            self.draft = {
                line["ma_thuoc"]: {
                    "ma_thuoc": line["ma_thuoc"],
                    "ten_thuoc": line["ten_thuoc"],
                    "don_vi_tinh": line["don_vi_tinh"],
                    "so_luong_ke": line["so_luong_ke"],
                    "cach_dung": line["cach_dung"],
                    "don_gia_ap_dung": line["don_gia_ap_dung"],
                }
                for line in saved["ds_thuoc"]
            }
            self._saved_snapshot = self._snapshot()
            if self._reload_medicines(show_errors=False):
                messagebox.showinfo("Đơn thuốc", "Đã lưu đơn thuốc.", parent=self)
            else:
                messagebox.showwarning(
                    "Đơn đã lưu",
                    (
                        "Đơn đã được lưu, nhưng chưa tải lại tồn kho. "
                        "Bấm “Tải danh mục” trước khi thao tác tiếp."
                    ),
                    parent=self,
                )
            return True
        except Exception as error:
            self._handle_error(error)
            return False

    def _delete_order(self) -> None:
        if self.current_order_id is None:
            self._handle_error(
                AppError("KHONG_TIM_THAY", "Hãy tải đơn đã lưu trước khi xóa.")
            )
            return
        confirmed = messagebox.askyesno(
            "Hủy đơn thuốc",
            (
                "Đơn sẽ bị hủy và toàn bộ số lượng thuốc đã lưu sẽ được hoàn tồn. "
                "Việc này dựa trên giả định thuốc chưa giao hoặc đã được hoàn lại "
                "đầy đủ. Bạn có chắc muốn tiếp tục?"
            ),
            parent=self,
        )
        if not confirmed:
            return

        try:
            appointment_id = self.ma_phieu.get().strip()
            xoa_don_thuoc(appointment_id, self.current_order_id)
            self.current_order_id = None
            self.original_quantities.clear()
            self.draft.clear()
            self.ma_don.delete(0, "end")
            self.loi_dan.delete("1.0", "end")
            self._refresh_table()
            self._saved_snapshot = self._snapshot()
            if self._reload_medicines(show_errors=False):
                messagebox.showinfo(
                    "Đơn thuốc", "Đã hủy đơn và hoàn tồn.", parent=self
                )
            else:
                messagebox.showwarning(
                    "Đơn đã hủy",
                    (
                        "Đơn đã được hủy và hoàn tồn. Chưa tải lại được danh mục; "
                        "bấm “Tải danh mục” trước khi thao tác tiếp."
                    ),
                    parent=self,
                )
        except (ValueError, TypeError):
            self._handle_error(
                AppError(
                    "DU_LIEU_KHONG_HOP_LE",
                    "Mã phiếu khám phải là số nguyên dương.",
                    "ma_phieu",
                )
            )
        except Exception as error:
            self._handle_error(error)
