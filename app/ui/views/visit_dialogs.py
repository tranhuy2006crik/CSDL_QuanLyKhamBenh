import logging
import tkinter as tk
from collections.abc import Callable
from datetime import datetime
from decimal import Decimal, InvalidOperation
from tkinter import messagebox, ttk

from app.errors import AppError
from app.services.clinic_service import (
    chot_phieu_kham,
    luu_noi_dung_kham,
    tao_phieu_kham,
)
from app.services.tra_cuu_service import lay_chi_tiet_lan_kham
from app.services.xet_nghiem_service import luu_xet_nghiem
from app.ui.ke_don import KeDonView
from app.ui.views.common import dinh_dang_tien, hien_loi, tao_bang


class TaoPhieuKhamDialog(tk.Toplevel):
    def __init__(
        self, parent: tk.Misc, ma_benh_nhan: str, ma_bac_si: str, ten_benh_nhan: str
    ) -> None:
        super().__init__(parent)
        self.title("Tạo phiếu khám")
        self.geometry("650x520")
        self.minsize(580, 460)
        self.transient(parent)
        self.result: str | None = None
        self.ma_benh_nhan = str(ma_benh_nhan).strip()
        self.ma_bac_si = str(ma_bac_si).strip()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)

        ttk.Label(
            self,
            text=f"Tạo phiếu khám cho {ten_benh_nhan}",
            font=("Segoe UI", 15, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 4))
        ttk.Label(
            self,
            text="Mã phiếu khám nhập thủ công theo quy ước (VD: PK001).",
            wraplength=600,
        ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))

        fields = ttk.Frame(self, padding=(16, 0))
        fields.grid(row=2, column=0, sticky="ew")
        fields.columnconfigure(1, weight=1)
        ttk.Label(fields, text="Mã phiếu khám").grid(row=0, column=0, sticky="w")
        self.ma_phieu = ttk.Entry(fields)
        self.ma_phieu.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        ttk.Label(self, text="Triệu chứng").grid(
            row=3, column=0, sticky="w", padx=16, pady=(12, 4)
        )
        self.trieu_chung = tk.Text(
            self,
            height=4,
            wrap="word",
            relief="solid",
            bd=1,
            font=("Segoe UI", 10),
            padx=10,
            pady=8,
        )
        self.trieu_chung.grid(row=4, column=0, sticky="nsew", padx=16)

        ttk.Label(self, text="Chẩn đoán").grid(
            row=5, column=0, sticky="w", padx=16, pady=(12, 4)
        )
        self.chan_doan = tk.Text(
            self,
            height=4,
            wrap="word",
            relief="solid",
            bd=1,
            font=("Segoe UI", 10),
            padx=10,
            pady=8,
        )
        self.chan_doan.grid(row=6, column=0, sticky="ew", padx=16)

        actions = ttk.Frame(self, padding=16)
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
            tao_phieu_kham(
                ma_phieu,
                self.ma_benh_nhan,
                self.ma_bac_si,
                self.trieu_chung.get("1.0", "end").strip(),
                self.chan_doan.get("1.0", "end").strip(),
            )
        except Exception as error:
            logging.getLogger(__name__).exception("Lỗi khi tạo phiếu khám: %s", error)
            hien_loi(self, error)
            return
        self.result = ma_phieu
        self.destroy()


class XetNghiemDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        ma_phieu: str,
        on_saved: Callable[[], None],
        row: dict[str, object] | None = None,
    ) -> None:
        super().__init__(parent)
        self.title("Xét nghiệm")
        self.geometry("580x480")
        self.minsize(500, 420)
        self.transient(parent)
        self.ma_phieu = str(ma_phieu).strip()
        self.on_saved = on_saved
        self.row = row
        self.columnconfigure(1, weight=1)

        ttk.Label(
            self,
            text="Chỉ định / cập nhật xét nghiệm",
            font=("Segoe UI", 14, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=16)

        self.name = self._entry("Tên xét nghiệm", 1)
        self.price = self._entry("Đơn giá áp dụng (VNĐ)", 2)

        ttk.Label(self, text="Kết quả (để trống nếu đang chờ)").grid(
            row=3, column=0, columnspan=2, sticky="w", padx=16, pady=(8, 4)
        )
        self.result_text = tk.Text(
            self,
            height=5,
            wrap="word",
            relief="solid",
            bd=1,
            font=("Segoe UI", 10),
            padx=10,
            pady=8,
        )
        self.result_text.grid(row=4, column=0, columnspan=2, sticky="ew", padx=16)

        self.time = self._entry("Thời điểm thực hiện (dd/mm/yyyy HH:MM)", 5)
        ttk.Label(
            self,
            text="Xét nghiệm được lưu cùng mã phiếu; STT được cấp tuần tự trong phiếu.",
            wraplength=540,
            foreground="gray",
        ).grid(row=6, column=0, columnspan=2, sticky="w", padx=16, pady=10)

        actions = ttk.Frame(self, padding=16)
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
        ttk.Label(self, text=label).grid(row=row, column=0, sticky="w", padx=16, pady=6)
        entry = ttk.Entry(self)
        entry.grid(row=row, column=1, sticky="ew", padx=16, pady=6)
        return entry

    def _save(self) -> None:
        try:
            time_value = self.time.get().strip()
            performed_at = (
                datetime.strptime(time_value, "%d/%m/%Y %H:%M") if time_value else None
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
            stt_val = int(self.row["stt"]) if self.row is not None else None
            saved_stt = luu_xet_nghiem(
                self.ma_phieu,
                self.name.get(),
                result,
                performed_at,
                Decimal(self.price.get().strip()),
                stt_val,
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
            logging.getLogger(__name__).exception("Lỗi khi lưu xét nghiệm: %s", error)
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
        ma_phieu: str,
        read_only: bool,
        on_changed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.title(f"Chi tiết phiếu khám {ma_phieu}")
        self.geometry("860x580")
        self.minsize(760, 500)
        self.transient(parent)
        self.ma_phieu = str(ma_phieu).strip()
        self.read_only = read_only
        self.on_changed = on_changed
        self.trang_thai = "DANG_KHAM"

        self.main_frame = ttk.Frame(self, padding=16)
        self.main_frame.pack(fill="both", expand=True)

        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(2, weight=1)

        header_frame = ttk.Frame(self.main_frame)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header_frame.columnconfigure(0, weight=1)

        self.lbl_title = ttk.Label(
            header_frame,
            text=f"Phiếu khám {self.ma_phieu}",
            font=("Segoe UI", 18, "bold"),
        )
        self.lbl_title.grid(row=0, column=0, sticky="w")

        self.lbl_patient_info = ttk.Label(
            header_frame,
            text="Đang tải...",
            font=("Segoe UI", 10),
            foreground="#555555",
        )
        self.lbl_patient_info.grid(row=1, column=0, sticky="w", pady=(2, 0))

        self.lbl_status = ttk.Label(
            header_frame, text="ĐANG KHÁM", font=("Segoe UI", 11, "bold")
        )
        self.lbl_status.grid(row=0, column=1, rowspan=2, sticky="e", padx=4)

        clin_frame = ttk.LabelFrame(self.main_frame, text="Khám lâm sàng", padding=12)
        clin_frame.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        clin_frame.columnconfigure(0, weight=1)

        ttk.Label(clin_frame, text="Triệu chứng", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        self.txt_symptoms = tk.Text(
            clin_frame,
            height=3,
            font=("Segoe UI", 10),
            relief="solid",
            bd=1,
            wrap="word",
            padx=10,
            pady=8,
        )
        self.txt_symptoms.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        ttk.Label(clin_frame, text="Chẩn đoán", font=("Segoe UI", 9, "bold")).grid(
            row=2, column=0, sticky="w", pady=(0, 4)
        )
        self.txt_diagnosis = tk.Text(
            clin_frame,
            height=3,
            font=("Segoe UI", 10),
            relief="solid",
            bd=1,
            wrap="word",
            padx=10,
            pady=8,
        )
        self.txt_diagnosis.grid(row=3, column=0, sticky="ew")

        grid_frame = ttk.Frame(self.main_frame)
        grid_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 12))
        grid_frame.columnconfigure(0, weight=1, uniform="group1")
        grid_frame.columnconfigure(1, weight=1, uniform="group1")
        grid_frame.rowconfigure(0, weight=1)

        self.lab_card = ttk.LabelFrame(
            grid_frame, text="Chỉ định Xét nghiệm", padding=12
        )
        self.lab_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.lab_content = ttk.Frame(self.lab_card)
        self.lab_content.pack(fill="both", expand=True)

        self.btn_add_lab = ttk.Button(
            self.lab_card, text="Thêm xét nghiệm", command=self._add_lab
        )
        self.btn_add_lab.pack(anchor="w", pady=(10, 0))

        self.med_card = ttk.LabelFrame(grid_frame, text="Đơn thuốc", padding=12)
        self.med_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self.med_content = ttk.Frame(self.med_card)
        self.med_content.pack(fill="both", expand=True)

        self.btn_manage_med = ttk.Button(
            self.med_card, text="Thêm thuốc mới", command=self._open_prescription
        )
        self.btn_manage_med.pack(anchor="w", pady=(10, 0))

        self.action_card = ttk.Frame(self.main_frame)
        self.action_card.grid(row=3, column=0, sticky="ew")

        self.btn_complete = ttk.Button(
            self.action_card, text="Hoàn thành phiếu", command=self._complete_visit
        )
        self.btn_complete.pack(side="right")

        self.btn_save = ttk.Button(
            self.action_card, text="Lưu thay đổi", command=self._save_clinical
        )
        self.btn_save.pack(side="right", padx=10)

    def _refresh(self) -> None:
        try:
            data = lay_chi_tiet_lan_kham(self.ma_phieu)
        except Exception as error:
            hien_loi(self, error)
            return

        info = data["thong_tin"]
        self.lbl_patient_info.config(
            text=f"Bác sĩ khám: {info.get('ten_bac_si', '—')}  •  Bệnh nhân: {info.get('ho_ten_benh_nhan', '—')}"
        )

        raw_status = (
            info.get("trang_thai_phieu_kham") or info.get("TrangThaiPhieuKham") or ""
        )
        raw_status = str(raw_status).strip().upper()

        if "HOAN_THANH" in self.ma_phieu.upper() or raw_status == "HOAN_THANH":
            self.trang_thai = "HOAN_THANH"
        else:
            self.trang_thai = "DANG_KHAM"

        is_locked = self.trang_thai == "HOAN_THANH" or self.read_only

        if is_locked:
            self.lbl_status.config(text="HOÀN THÀNH", foreground="green")
            self._lock_ui()
        else:
            self.lbl_status.config(text="ĐANG KHÁM", foreground="black")
            self._unlock_ui()

        self._set_text(self.txt_symptoms, data.get("trieu_chung") or "", lock=is_locked)
        self._set_text(self.txt_diagnosis, data.get("chan_doan") or "", lock=is_locked)

        for widget in self.lab_content.winfo_children():
            widget.destroy()
        ds_xet_nghiem = data.get("ds_xet_nghiem", [])
        if not ds_xet_nghiem:
            ttk.Label(
                self.lab_content,
                text="Chưa có chỉ định xét nghiệm.",
                font=("Segoe UI", 9, "italic"),
                foreground="gray",
            ).pack(anchor="w")
        else:
            for xn in ds_xet_nghiem:
                item = ttk.Frame(self.lab_content)
                item.pack(fill="x", pady=(0, 6))
                item.columnconfigure(0, weight=1)

                ttk.Label(
                    item, text=xn["ten_xet_nghiem"], font=("Segoe UI", 10, "bold")
                ).grid(row=0, column=0, sticky="w")
                ket_qua = xn["ket_qua"] if xn["ket_qua"] else "Đang chờ kết quả..."
                ttk.Label(item, text=f"KQ: {ket_qua}").grid(row=1, column=0, sticky="w")

                if not is_locked:
                    btn = ttk.Label(
                        item,
                        text="Sửa",
                        foreground="#0066cc",
                        cursor="hand2",
                        font=("Segoe UI", 9, "underline"),
                    )
                    btn.grid(row=0, column=1, rowspan=2, sticky="ne")
                    btn.bind("<Button-1>", lambda e, row=xn: self._edit_lab(row))

                ttk.Separator(self.lab_content, orient="horizontal").pack(
                    fill="x", pady=(6, 0)
                )

        for widget in self.med_content.winfo_children():
            widget.destroy()
        don_thuoc = data.get("don_thuoc")
        if not don_thuoc or not don_thuoc.get("ds_thuoc"):
            ttk.Label(
                self.med_content,
                text="Chưa kê đơn thuốc.",
                font=("Segoe UI", 9, "italic"),
                foreground="gray",
            ).pack(anchor="w")
        else:
            for thuoc in don_thuoc["ds_thuoc"]:
                item = ttk.Frame(self.med_content)
                item.pack(fill="x", pady=(0, 6))
                item.columnconfigure(0, weight=1)

                ttk.Label(
                    item, text=thuoc["ten_thuoc"], font=("Segoe UI", 10, "bold")
                ).grid(row=0, column=0, sticky="w")
                ttk.Label(
                    item, text=f"SL: {thuoc['so_luong_ke']} - HD: {thuoc['cach_dung']}"
                ).grid(row=1, column=0, sticky="w")

                if not is_locked:
                    btn = ttk.Label(
                        item,
                        text="Sửa",
                        foreground="#0066cc",
                        cursor="hand2",
                        font=("Segoe UI", 9, "underline"),
                    )
                    btn.grid(row=0, column=1, rowspan=2, sticky="ne")
                    btn.bind("<Button-1>", lambda e: self._open_prescription())

                ttk.Separator(self.med_content, orient="horizontal").pack(
                    fill="x", pady=(6, 0)
                )

    def _lock_ui(self) -> None:
        self.action_card.grid_remove()
        self.btn_add_lab.pack_forget()
        self.btn_manage_med.config(text="Xem chi tiết đơn thuốc")

    def _unlock_ui(self) -> None:
        self.action_card.grid(row=3, column=0, sticky="ew")
        self.btn_add_lab.pack(anchor="w", pady=(10, 0))
        self.btn_manage_med.config(text="Thêm thuốc mới")

    @staticmethod
    def _set_text(widget: tk.Text, value: str, lock: bool) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", value)
        widget.configure(state="disabled" if lock else "normal")
        if lock:
            widget.configure(bg="#f0f0f0")
        else:
            widget.configure(bg="#ffffff")

    def _notify_changed(self) -> None:
        self._refresh()
        if self.on_changed is not None:
            self.on_changed()

    def _save_clinical(self) -> None:
        try:
            luu_noi_dung_kham(
                self.ma_phieu,
                self.txt_symptoms.get("1.0", "end").strip(),
                self.txt_diagnosis.get("1.0", "end").strip(),
            )
            messagebox.showinfo("Thành công", "Đã lưu nội dung lâm sàng.", parent=self)
            self._notify_changed()
        except Exception as e:
            hien_loi(self, e)

    def _complete_visit(self) -> None:
        try:
            luu_noi_dung_kham(
                self.ma_phieu,
                self.txt_symptoms.get("1.0", "end").strip(),
                self.txt_diagnosis.get("1.0", "end").strip(),
            )
        except Exception as e:
            hien_loi(self, e)
            return

        if messagebox.askyesno(
            "Xác nhận",
            "Sau khi hoàn thành, phiếu khám sẽ BỊ KHÓA. Bạn có chắc chắn?",
            parent=self,
        ):
            try:
                chot_phieu_kham(self.ma_phieu)
                messagebox.showinfo(
                    "Thành công", "Đã hoàn thành phiếu khám.", parent=self
                )
                self._notify_changed()
            except Exception as e:
                hien_loi(self, e)

    def _add_lab(self) -> None:
        XetNghiemDialog(self, self.ma_phieu, self._notify_changed)

    def _edit_lab(self, row: dict[str, object]) -> None:
        XetNghiemDialog(self, self.ma_phieu, self._notify_changed, row)

    def _open_prescription(self) -> None:
        is_locked = self.trang_thai == "HOAN_THANH" or self.read_only
        dialog = tk.Toplevel(self)
        dialog.title(f"Đơn thuốc — Phiếu khám {self.ma_phieu}")
        dialog.geometry("1180x700")
        form = KeDonView(dialog, ma_phieu=self.ma_phieu, read_only=is_locked)
        form.pack(fill="both", expand=True)
        dialog.grab_set()
        self.wait_window(dialog)
        self._notify_changed()


__all__ = ["PhieuKhamDetailDialog", "TaoPhieuKhamDialog", "XetNghiemDialog"]
