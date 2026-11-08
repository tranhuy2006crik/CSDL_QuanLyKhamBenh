import tkinter as tk
from collections.abc import Callable
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from app.contracts import Identifier
from app.errors import AppError
from app.pdf_export import xuat_bao_cao_phieu_kham_pdf
from app.services.clinic_service import (
    hoan_thanh_phieu_kham,
    luu_noi_dung_kham,
    luu_xet_nghiem,
    tao_phieu_kham,
)
from app.services.tra_cuu_service import (
    bao_cao_chi_tiet_phieu,
    lay_chi_tiet_lan_kham,
)
from app.ui.ke_don import KeDonView
from app.ui.views.common import (
    dinh_dang_tien,
    hien_loi,
    tao_bang,
    xac_nhan_thay_doi_chua_luu,
)


class TaoPhieuKhamDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        ma_benh_nhan: Identifier,
        ma_bac_si: Identifier,
        ten_benh_nhan: str,
    ) -> None:
        super().__init__(parent)
        self.title("Tạo phiếu khám")
        self.geometry("650x520")
        self.minsize(580, 460)
        self.transient(parent)
        self.result: Identifier | None = None
        self.ma_benh_nhan = ma_benh_nhan
        self.ma_bac_si = ma_bac_si
        self.columnconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)

        ttk.Label(
            self,
            text=f"Tạo phiếu khám cho {ten_benh_nhan}",
            font=("TkDefaultFont", 15, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 4))
        ttk.Label(
            self,
            text="Mã phiếu khám nhập thủ công theo quy ước cấp mã của nhóm.",
            wraplength=600,
        ).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 10))

        fields = ttk.Frame(self, padding=(12, 0))
        fields.grid(row=2, column=0, sticky="ew")
        fields.columnconfigure(1, weight=1)
        ttk.Label(fields, text="Mã phiếu khám").grid(row=0, column=0, sticky="w")
        self.ma_phieu = ttk.Entry(fields)
        self.ma_phieu.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        ttk.Label(self, text="Triệu chứng").grid(
            row=3, column=0, sticky="w", padx=12, pady=(10, 4)
        )
        self.trieu_chung = tk.Text(self, height=4, wrap="word")
        self.trieu_chung.grid(row=4, column=0, sticky="nsew", padx=12)

        ttk.Label(self, text="Chẩn đoán").grid(
            row=5, column=0, sticky="w", padx=12, pady=(10, 4)
        )
        self.chan_doan = tk.Text(self, height=4, wrap="word")
        self.chan_doan.grid(row=6, column=0, sticky="ew", padx=12)

        actions = ttk.Frame(self, padding=12)
        actions.grid(row=7, column=0, sticky="ew")
        ttk.Button(actions, text="Hủy", command=self.destroy).pack(side="right")
        ttk.Button(actions, text="Tạo phiếu khám", command=self._save).pack(
            side="right", padx=(0, 8)
        )
        self.grab_set()
        self.ma_phieu.focus_set()

    def _save(self) -> None:
        try:
            ma_phieu = self.ma_phieu.get().strip()
            if not ma_phieu:
                raise ValueError("empty")
            tao_phieu_kham(
                ma_phieu,
                self.ma_benh_nhan,
                self.ma_bac_si,
                self.trieu_chung.get("1.0", "end").strip(),
                self.chan_doan.get("1.0", "end").strip(),
            )
        except ValueError:
            hien_loi(
                self,
                AppError(
                    "DU_LIEU_KHONG_HOP_LE",
                    "Hãy nhập mã phiếu khám.",
                    "ma_phieu",
                ),
            )
            return
        except Exception as error:
            hien_loi(self, error)
            return
        self.result = ma_phieu
        self.destroy()


class XetNghiemDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        ma_phieu: Identifier,
        on_saved: Callable[[], None],
        row: dict[str, object] | None = None,
    ) -> None:
        super().__init__(parent)
        self.title("Xét nghiệm")
        self.geometry("580x480")
        self.minsize(500, 420)
        self.transient(parent)
        self.ma_phieu = ma_phieu
        self.on_saved = on_saved
        self.row = row
        self.columnconfigure(1, weight=1)

        ttk.Label(
            self,
            text="Chỉ định / cập nhật xét nghiệm",
            font=("TkDefaultFont", 14, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=12)
        self.name = self._entry("Tên xét nghiệm", 1)
        self.price = self._entry("Đơn giá áp dụng (VNĐ)", 2)
        self.result_text = tk.Text(self, height=5, wrap="word")
        ttk.Label(self, text="Kết quả (để trống nếu đang chờ)").grid(
            row=3, column=0, columnspan=2, sticky="w", padx=12, pady=(8, 3)
        )
        self.result_text.grid(row=4, column=0, columnspan=2, sticky="ew", padx=12)
        self.time = self._entry("Thời điểm thực hiện (dd/mm/yyyy HH:MM)", 5)
        ttk.Label(
            self,
            text="Xét nghiệm được lưu cùng mã phiếu; STT được cấp tuần tự trong phiếu.",
            wraplength=540,
        ).grid(row=6, column=0, columnspan=2, sticky="w", padx=12, pady=10)
        actions = ttk.Frame(self, padding=12)
        actions.grid(row=7, column=0, columnspan=2, sticky="ew")
        ttk.Button(actions, text="Hủy", command=self.destroy).pack(side="right")
        ttk.Button(actions, text="Lưu xét nghiệm", command=self._save).pack(
            side="right", padx=(0, 8)
        )

        if row is not None:
            self.name.insert(0, str(row["ten_xet_nghiem"]))
            self.price.insert(0, str(row["don_gia_ap_dung"]))
            self.result_text.insert("1.0", str(row["ket_qua"] or ""))
            performed_at = row["ngay_gio_thuc_hien"]
            if isinstance(performed_at, datetime):
                self.time.insert(0, performed_at.strftime("%d/%m/%Y %H:%M"))
        else:
            self.price.insert(0, "0")
        self.grab_set()
        self.name.focus_set()

    def _entry(self, label: str, row: int) -> ttk.Entry:
        ttk.Label(self, text=label).grid(
            row=row, column=0, sticky="w", padx=12, pady=5
        )
        entry = ttk.Entry(self)
        entry.grid(row=row, column=1, sticky="ew", padx=12, pady=5)
        return entry

    def _save(self) -> None:
        try:
            time_value = self.time.get().strip()
            performed_at = (
                datetime.strptime(time_value, "%d/%m/%Y %H:%M")
                if time_value
                else None
            )
        except ValueError:
            hien_loi(
                self,
                AppError(
                    "DU_LIEU_KHONG_HOP_LE",
                    "Thời điểm thực hiện phải theo dd/mm/yyyy HH:MM.",
                    "ngay_gio_thuc_hien",
                ),
            )
            return
        try:
            result = self.result_text.get("1.0", "end").strip() or None
            saved_stt = luu_xet_nghiem(
                self.ma_phieu,
                self.name.get(),
                result,
                performed_at,
                Decimal(self.price.get().strip()),
                int(self.row["stt"]) if self.row is not None else None,
            )
        except (InvalidOperation, ValueError):
            hien_loi(
                self,
                AppError(
                    "DU_LIEU_KHONG_HOP_LE",
                    "Đơn giá phải là số hợp lệ.",
                    "don_gia_ap_dung",
                ),
            )
            return
        except Exception as error:
            hien_loi(self, error)
            return
        messagebox.showinfo(
            "Đã lưu",
            f"Đã lưu xét nghiệm STT {saved_stt} cho phiếu khám {self.ma_phieu}.",
            parent=self,
        )
        self.on_saved()
        self.destroy()


class PhieuKhamDetailDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        ma_phieu: Identifier,
        vai_tro: str,
        ma_nguoi_xem: Identifier,
        on_changed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.title(f"Chi tiết phiếu khám {ma_phieu}")
        self.geometry("1120x720")
        self.minsize(900, 600)
        self.transient(parent)
        self.ma_phieu = ma_phieu
        self.vai_tro = vai_tro
        self.ma_nguoi_xem = ma_nguoi_xem
        self.read_only = vai_tro != "doctor"
        self.dirty = False
        self._saved_symptoms = ""
        self._saved_diagnosis = ""
        self.on_changed = on_changed
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        self.header = ttk.Label(
            self, text="", font=("TkDefaultFont", 12, "bold"), justify="left"
        )
        self.header.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        self.total = ttk.Label(self, text="", font=("TkDefaultFont", 12, "bold"))
        self.total.grid(row=1, column=0, sticky="e", padx=12, pady=(0, 8))

        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.clinical_tab = ttk.Frame(self.notebook, padding=12)
        self.lab_tab = ttk.Frame(self.notebook, padding=8)
        self.medicine_tab = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(self.clinical_tab, text="Khám")
        self.notebook.add(self.lab_tab, text="Xét nghiệm")
        self.notebook.add(self.medicine_tab, text="Đơn thuốc")
        self._build_clinical_tab()
        self._build_lab_tab()
        self._build_medicine_tab()
        actions = ttk.Frame(self, padding=(12, 0, 12, 12))
        actions.grid(row=3, column=0, sticky="ew")
        self.save_content_button = ttk.Button(
            actions,
            text="Lưu thay đổi",
            command=self._save_content,
            style="Primary.TButton",
        )
        self.save_content_button.pack(side="left")
        self.complete_button = ttk.Button(
            actions,
            text="Hoàn thành phiếu",
            command=self._complete_visit,
            style="Success.TButton",
        )
        self.complete_button.pack(side="left", padx=8)
        self.export_button = ttk.Button(
            actions,
            text="Xuất PDF kết quả khám",
            command=self._export_report,
            style="Secondary.TButton",
        )
        self.export_button.pack(side="left")
        ttk.Button(actions, text="Đóng", command=self._request_close).pack(side="right")
        self.protocol("WM_DELETE_WINDOW", self._request_close)
        self._refresh()

    def _build_clinical_tab(self) -> None:
        self.clinical_tab.columnconfigure(0, weight=1)
        for row, label in ((0, "Triệu chứng"), (2, "Chẩn đoán")):
            ttk.Label(
                self.clinical_tab,
                text=label,
                font=("TkDefaultFont", 11, "bold"),
            ).grid(row=row, column=0, sticky="w", pady=(0, 4))
        self.symptoms = tk.Text(self.clinical_tab, height=8, wrap="word")
        self.symptoms.grid(row=1, column=0, sticky="nsew", pady=(0, 12))
        self.diagnosis = tk.Text(self.clinical_tab, height=8, wrap="word")
        self.diagnosis.grid(row=3, column=0, sticky="nsew")
        self.symptoms.bind("<<Modified>>", self._content_changed)
        self.diagnosis.bind("<<Modified>>", self._content_changed)

    def _build_lab_tab(self) -> None:
        self.lab_tab.columnconfigure(0, weight=1)
        self.lab_tab.rowconfigure(0, weight=1)
        columns = (
            "stt",
            "ten",
            "ket_qua",
            "thoi_diem",
            "don_gia",
        )
        self.lab_table = tao_bang(
            self.lab_tab,
            columns,
            {
                "stt": "STT",
                "ten": "Xét nghiệm",
                "ket_qua": "Kết quả",
                "thoi_diem": "Ngày giờ thực hiện",
                "don_gia": "Đơn giá áp dụng",
            },
            {"stt": 55, "ten": 240, "ket_qua": 300, "thoi_diem": 170, "don_gia": 150},
        )
        self.lab_table.grid(row=0, column=0, sticky="nsew")
        if not self.read_only:
            actions = ttk.Frame(self.lab_tab)
            actions.grid(row=1, column=0, sticky="ew", pady=(8, 0))
            self.add_lab_button = ttk.Button(
                actions,
                text="Chỉ định xét nghiệm",
                command=self._add_lab,
            )
            self.add_lab_button.pack(side="left")
            self.edit_lab_button = ttk.Button(
                actions,
                text="Cập nhật kết quả",
                command=self._edit_lab,
            )
            self.edit_lab_button.pack(side="left", padx=8)
        else:
            ttk.Label(
                self.lab_tab,
                text="Xét nghiệm liên kết trực tiếp với phiếu khám; kết quả có thể để trống khi đang chờ.",
            ).grid(row=1, column=0, sticky="w", pady=(8, 0))

    def _build_medicine_tab(self) -> None:
        self.medicine_tab.columnconfigure(0, weight=1)
        self.medicine_tab.rowconfigure(0, weight=1)
        columns = ("ten", "so_luong", "cach_dung", "don_gia", "thanh_tien")
        self.medicine_table = tao_bang(
            self.medicine_tab,
            columns,
            {
                "ten": "Thuốc",
                "so_luong": "Số lượng",
                "cach_dung": "Cách dùng",
                "don_gia": "Đơn giá áp dụng",
                "thanh_tien": "Thành tiền",
            },
            {"ten": 230, "so_luong": 90, "cach_dung": 260, "don_gia": 160, "thanh_tien": 160},
        )
        self.medicine_table.grid(row=0, column=0, sticky="nsew")
        if not self.read_only:
            self.prescription_button = ttk.Button(
                self.medicine_tab,
                text="Kê đơn / quản lý đơn thuốc",
                command=self._open_prescription,
            )
            self.prescription_button.grid(row=1, column=0, sticky="w", pady=(8, 0))
        else:
            self.prescription_note = ttk.Label(self.medicine_tab, text="")
            self.prescription_note.grid(row=1, column=0, sticky="w", pady=(8, 0))

    def _refresh(self) -> None:
        try:
            data = lay_chi_tiet_lan_kham(
                self.ma_phieu, self.vai_tro, self.ma_nguoi_xem
            )
        except Exception as error:
            hien_loi(self, error)
            return
        info = data["thong_tin"]
        self.read_only = (
            self.vai_tro != "doctor" or info["trang_thai"] != "DANG_KHAM"
        )
        self._saved_symptoms = data["trieu_chung"] or ""
        self._saved_diagnosis = data["chan_doan"] or ""
        self.dirty = False
        self.save_content_button.configure(
            state="disabled" if self.read_only else "normal"
        )
        self.complete_button.configure(
            state="disabled" if self.read_only else "normal"
        )
        self.export_button.configure(
            state="normal" if info["trang_thai"] == "HOAN_THANH" else "disabled"
        )
        for name in ("add_lab_button", "edit_lab_button", "prescription_button"):
            button = getattr(self, name, None)
            if button is not None:
                button.configure(state="disabled" if self.read_only else "normal")
        self.header.configure(
            text=(
                f'Phiếu khám: {info["ma_phieu"]}    '
                f'Bệnh nhân: {info["ho_ten_benh_nhan"]} '
                f'(Mã {info["ma_benh_nhan"]})\n'
                f'Bác sĩ: {info["ten_bac_si"]} — {info["ten_khoa"]}    '
                f'Ngày giờ khám: {info["ngay_gio_kham"]:%d/%m/%Y %H:%M}'
            )
        )
        self.total.configure(
            text=(
                f'Giá khám: {dinh_dang_tien(info["gia_kham"])}   |   '
                f'Xét nghiệm: {dinh_dang_tien(info["gia_xet_nghiem"])}   |   '
                f'Thuốc: {dinh_dang_tien(info["gia_thuoc"])}   |   '
                f'Tổng chi phí ghi nhận: {dinh_dang_tien(info["tong_gia_tri"])}'
            )
        )
        self._set_text(self.symptoms, self._saved_symptoms)
        self._set_text(self.diagnosis, self._saved_diagnosis)
        for item in self.lab_table.get_children():
            self.lab_table.delete(item)
        for row in data["ds_xet_nghiem"]:
            performed_at = row["ngay_gio_thuc_hien"]
            self.lab_table.insert(
                "",
                "end",
                iid=str(row["stt"]),
                values=(
                    row["stt"],
                    row["ten_xet_nghiem"],
                    row["ket_qua"] or "Đang chờ kết quả",
                    performed_at.strftime("%d/%m/%Y %H:%M")
                    if performed_at
                    else "—",
                    dinh_dang_tien(row["don_gia_ap_dung"]),
                ),
            )
        for item in self.medicine_table.get_children():
            self.medicine_table.delete(item)
        order = data["don_thuoc"]
        if order:
            for row in order["ds_thuoc"]:
                self.medicine_table.insert(
                    "",
                    "end",
                    values=(
                        row["ten_thuoc"],
                        row["so_luong_ke"],
                        row["cach_dung"],
                        dinh_dang_tien(row["don_gia_ap_dung"]),
                        dinh_dang_tien(row["thanh_tien"]),
                    ),
                )
            if self.read_only:
                self.prescription_note.configure(
                    text=f'Lời dặn: {order["loi_dan"] or "Không có"}'
                )
        elif self.read_only:
            self.prescription_note.configure(text="Phiếu khám không có đơn thuốc.")
        if self.on_changed is not None:
            self.on_changed()

    def _set_text(self, widget: tk.Text, value: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", value or "")
        widget.edit_modified(False)
        widget.configure(state="normal" if not self.read_only else "disabled")

    def _content_changed(self, event: tk.Event) -> None:
        widget = event.widget
        if not widget.edit_modified():
            return
        widget.edit_modified(False)
        self.dirty = (
            self.symptoms.get("1.0", "end").strip() != self._saved_symptoms
            or self.diagnosis.get("1.0", "end").strip() != self._saved_diagnosis
        )

    def _save_content(self) -> bool:
        try:
            luu_noi_dung_kham(
                self.ma_phieu,
                self.symptoms.get("1.0", "end").strip(),
                self.diagnosis.get("1.0", "end").strip(),
            )
        except Exception as error:
            hien_loi(self, error)
            return False
        self._refresh()
        return True

    def _complete_visit(self) -> None:
        if self.dirty and not self._save_content():
            return
        try:
            hoan_thanh_phieu_kham(self.ma_phieu, self.ma_nguoi_xem)
        except Exception as error:
            hien_loi(self, error)
            return
        messagebox.showinfo(
            "Hoàn thành phiếu",
            "Phiếu khám đã chuyển sang HOAN_THANH.",
            parent=self,
        )
        self._refresh()
        if self.on_changed is not None:
            self.on_changed()

    def _request_close(self) -> None:
        if self.dirty and not xac_nhan_thay_doi_chua_luu(
            self, self._save_content
        ):
            return
        self.destroy()

    def _export_report(self) -> None:
        path_text = filedialog.asksaveasfilename(
            parent=self,
            title="Lưu báo cáo kết quả khám",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"ket_qua_kham_{self.ma_phieu}.pdf",
        )
        if not path_text:
            return
        try:
            report = bao_cao_chi_tiet_phieu(self.ma_phieu)
            xuat_bao_cao_phieu_kham_pdf(Path(path_text), report)
        except Exception as error:
            hien_loi(self, error, "Không thể xuất báo cáo")
            return
        messagebox.showinfo(
            "Đã xuất báo cáo", f"Đã lưu báo cáo tại:\n{path_text}", parent=self
        )

    def _selected_lab(self) -> dict[str, object] | None:
        selection = self.lab_table.selection()
        if not selection:
            return None
        stt = int(selection[0])
        try:
            detail = lay_chi_tiet_lan_kham(
                self.ma_phieu, self.vai_tro, self.ma_nguoi_xem
            )
        except Exception as error:
            hien_loi(self, error)
            return None
        for row in detail["ds_xet_nghiem"]:
            if row["stt"] == stt:
                return row
        return None

    def _add_lab(self) -> None:
        XetNghiemDialog(self, self.ma_phieu, self._refresh)

    def _edit_lab(self) -> None:
        row = self._selected_lab()
        if row is None:
            messagebox.showinfo(
                "Xét nghiệm", "Hãy chọn một xét nghiệm cần cập nhật.", parent=self
            )
            return
        XetNghiemDialog(self, self.ma_phieu, self._refresh, row)

    def _open_prescription(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title(f"Kê đơn thuốc — Phiếu khám {self.ma_phieu}")
        dialog.geometry("1180x700")
        dialog.minsize(1000, 580)
        dialog.transient(self)
        form = KeDonView(dialog, ma_phieu=self.ma_phieu)
        form.pack(fill="both", expand=True)
        dialog.protocol("WM_DELETE_WINDOW", lambda: form.request_close(dialog.destroy))
        dialog.grab_set()
        self.wait_window(dialog)
        self._refresh()


__all__ = ["PhieuKhamDetailDialog", "TaoPhieuKhamDialog"]
