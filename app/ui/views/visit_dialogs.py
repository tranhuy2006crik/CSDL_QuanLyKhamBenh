import tkinter as tk
from collections.abc import Callable
from datetime import datetime, time, date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

try:
    from tkcalendar import DateEntry

    HAS_CALENDAR = True
except ImportError:
    HAS_CALENDAR = False

from app.contracts import Identifier
from app.errors import AppError
from app.pdf_export import xuat_bao_cao_phieu_kham_pdf
from app.services.clinic_service import (
    hoan_thanh_phieu_kham,
    luu_noi_dung_kham,
    luu_xet_nghiem,
    tao_phieu_kham,
    lay_benh_nhan,
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
        self.update_idletasks()
        x = (self.winfo_screenwidth() - self.winfo_width()) // 2
        y = (self.winfo_screenheight() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
        self.minsize(580, 460)
        self.configure(background="#F4F7FA")
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
        self.trieu_chung = tk.Text(
            self,
            height=4,
            wrap="word",
            background="#FFFFFF",
            relief="flat",
            highlightbackground="#CCD6E0",
            highlightthickness=1,
        )
        self.trieu_chung.grid(row=4, column=0, sticky="nsew", padx=12)

        ttk.Label(self, text="Chẩn đoán").grid(
            row=5, column=0, sticky="w", padx=12, pady=(10, 4)
        )
        self.chan_doan = tk.Text(
            self,
            height=4,
            wrap="word",
            background="#FFFFFF",
            relief="flat",
            highlightbackground="#CCD6E0",
            highlightthickness=1,
        )
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
                AppError("DU_LIEU_KHONG_HOP_LE", "Hãy nhập mã phiếu khám.", "ma_phieu"),
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
        self.geometry("620x480")
        self.update_idletasks()
        x = (self.winfo_screenwidth() - self.winfo_width()) // 2
        y = (self.winfo_screenheight() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
        self.minsize(520, 420)
        self.configure(background="#F4F7FA")
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

        ttk.Label(self, text="Kết quả (để trống nếu đang chờ)").grid(
            row=3, column=0, columnspan=2, sticky="w", padx=12, pady=(8, 3)
        )
        self.result_text = tk.Text(
            self,
            height=4,
            wrap="word",
            background="#FFFFFF",
            relief="flat",
            highlightbackground="#CCD6E0",
            highlightthickness=1,
        )
        self.result_text.grid(row=4, column=0, columnspan=2, sticky="ew", padx=12)

        ttk.Label(self, text="Thời điểm thực hiện").grid(
            row=5, column=0, sticky="w", padx=12, pady=10
        )

        time_frame = ttk.Frame(self)
        time_frame.grid(row=5, column=1, sticky="ew", padx=12, pady=10)

        self.date_picker = ttk.Entry(time_frame, width=12)
        self.date_picker.pack(side="left")

        if HAS_CALENDAR:
            ttk.Button(
                time_frame, text="📅", width=3, command=self._open_calendar
            ).pack(side="left", padx=(2, 6))

        ttk.Label(time_frame, text=" Giờ: ").pack(side="left")
        time_options = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 15, 30, 45)]
        self.time_picker = ttk.Combobox(
            time_frame,
            width=6,
            state="readonly",
            values=time_options,
        )
        self.time_picker.pack(side="left")

        ttk.Label(
            self,
            text="Xét nghiệm được lưu cùng mã phiếu; STT được cấp tuần tự trong phiếu.",
            wraplength=560,
            foreground="gray",
        ).grid(row=6, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 10))

        actions = ttk.Frame(self, padding=12)
        actions.grid(row=7, column=0, columnspan=2, sticky="ew")
        ttk.Button(
            actions, text="Hủy", command=self.destroy, style="Secondary.TButton"
        ).pack(side="right")
        ttk.Button(
            actions, text="Lưu xét nghiệm", command=self._save, style="Primary.TButton"
        ).pack(side="right", padx=(0, 8))

        if row is not None:
            self.name.insert(0, str(row["ten_xet_nghiem"]))
            self.price.insert(0, str(row["don_gia_ap_dung"]))
            self.result_text.insert("1.0", str(row["ket_qua"] or ""))
            performed_at = row["ngay_gio_thuc_hien"]
            if isinstance(performed_at, datetime):
                self.date_picker.delete(0, "end")
                self.date_picker.insert(0, performed_at.strftime("%d/%m/%Y"))
                self.time_picker.set(performed_at.strftime("%H:%M"))
            else:
                self._set_default_time()
        else:
            self.price.insert(0, "")
            self._set_default_time()

        self.grab_set()
        self.name.focus_set()

    def _open_calendar(self):
        """Hàm mở popup cuốn lịch siêu cấp ổn định"""
        try:
            from tkcalendar import Calendar
        except ImportError:
            return

        top = tk.Toplevel(self)
        top.title("Chọn ngày")
        top.geometry("+%d+%d" % (self.winfo_rootx() + 80, self.winfo_rooty() + 80))
        top.transient(self)
        top.grab_set()

        cal = Calendar(top, selectmode="day", date_pattern="dd/mm/yyyy")
        cal.pack(padx=10, pady=10)

        current_date = self.date_picker.get().strip()
        if current_date:
            try:
                dt = datetime.strptime(current_date, "%d/%m/%Y").date()
                cal.selection_set(dt)
            except ValueError:
                pass

        def on_date_selected(e):
            self.date_picker.delete(0, "end")
            dt_obj = cal.selection_get()
            self.date_picker.insert(0, dt_obj.strftime("%d/%m/%Y"))
            top.destroy()

        cal.bind("<<CalendarSelected>>", on_date_selected)

    def _set_default_time(self):
        now = datetime.now()
        self.date_picker.delete(0, "end")
        self.date_picker.insert(0, now.strftime("%d/%m/%Y"))
        m = (now.minute // 15) * 15
        self.time_picker.set(f"{now.hour:02d}:{m:02d}")

    def _entry(self, label: str, row: int) -> ttk.Entry:
        ttk.Label(self, text=label).grid(row=row, column=0, sticky="w", padx=12, pady=5)
        entry = ttk.Entry(self)
        entry.grid(row=row, column=1, sticky="ew", padx=12, pady=5)
        return entry

    def _save(self) -> None:
        try:
            result = self.result_text.get("1.0", "end").strip() or None

            if result is None:
                performed_at = None
            else:
                d = datetime.strptime(self.date_picker.get().strip(), "%d/%m/%Y").date()

                time_str = self.time_picker.get().strip()
                h, m = map(int, time_str.split(":"))
                performed_at = datetime.combine(d, time(h, m))

            ten_xet_nghiem = self.name.get().strip()
            if not ten_xet_nghiem:
                hien_loi(
                    self,
                    AppError(
                        "DU_LIEU_KHONG_HOP_LE",
                        "Vui lòng nhập Tên xét nghiệm.",
                        "ten_xet_nghiem",
                    ),
                )
                return

            price_str = self.price.get().strip()
            price_val = Decimal(price_str) if price_str else Decimal("0")

            saved_stt = luu_xet_nghiem(
                self.ma_phieu,
                ten_xet_nghiem,
                result,
                performed_at,
                price_val,
                int(self.row["stt"]) if self.row is not None else None,
            )
        except (InvalidOperation, ValueError):
            hien_loi(
                self,
                AppError(
                    "DU_LIEU_KHONG_HOP_LE",
                    "Thời điểm thực hiện hoặc Đơn giá không hợp lệ.",
                    "ngay_gio_thuc_hien",
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

        self.geometry("1024x720")
        self.update_idletasks()
        x = (self.winfo_screenwidth() - self.winfo_width()) // 2
        y = (self.winfo_screenheight() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
        self.minsize(950, 650)
        self.configure(background="#F4F7FA")
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

        top_frame = ttk.Frame(self)
        top_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 10))
        top_frame.columnconfigure(0, weight=1)
        top_frame.columnconfigure(1, weight=2)
        top_frame.columnconfigure(2, weight=1)

        self.lbl_title = ttk.Label(
            top_frame, text="", font=("TkDefaultFont", 18, "bold"), anchor="center"
        )
        self.lbl_title.grid(row=0, column=1, sticky="ew")

        self.lbl_status = ttk.Label(
            top_frame, text="", font=("TkDefaultFont", 11, "bold")
        )
        self.lbl_status.grid(row=0, column=2, sticky="e", pady=(0, 2))

        self.lbl_datetime = ttk.Label(top_frame, text="", foreground="gray")
        self.lbl_datetime.grid(row=1, column=2, sticky="e")

        info_frame = ttk.Frame(self)
        info_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 15))
        info_frame.columnconfigure(0, weight=1)
        info_frame.columnconfigure(1, weight=1)

        left_info = ttk.Frame(info_frame)
        left_info.grid(row=0, column=0, sticky="nsew")

        self.lbl_patient = ttk.Label(
            left_info, text="", font=("TkDefaultFont", 12, "bold"), foreground="#1677A5"
        )
        self.lbl_patient.pack(anchor="w", pady=2)
        self.lbl_dob = ttk.Label(left_info, text="")
        self.lbl_dob.pack(anchor="w", pady=2)
        self.lbl_gender = ttk.Label(left_info, text="")
        self.lbl_gender.pack(anchor="w", pady=2)
        self.lbl_phone = ttk.Label(left_info, text="")
        self.lbl_phone.pack(anchor="w", pady=2)
        self.lbl_address = ttk.Label(left_info, text="")
        self.lbl_address.pack(anchor="w", pady=2)
        self.lbl_doctor = ttk.Label(
            left_info, text="", font=("TkDefaultFont", 10, "bold")
        )
        self.lbl_doctor.pack(anchor="w", pady=(6, 2))

        right_info = ttk.Frame(info_frame)
        right_info.grid(row=0, column=1, sticky="ne", pady=(50, 0))

        self.total = ttk.Label(
            right_info,
            text="",
            font=("TkDefaultFont", 10, "bold"),
            foreground="#C0392B",
            justify="right",
        )
        self.total.pack(anchor="e", pady=2)

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
            style="Info.TButton",
        )
        self.export_button.pack(side="left")
        ttk.Button(actions, text="Đóng", command=self._request_close).pack(side="right")

        self.protocol("WM_DELETE_WINDOW", self._request_close)
        self._refresh()

    def _build_clinical_tab(self) -> None:
        self.clinical_tab.columnconfigure(0, weight=1)
        self.clinical_tab.rowconfigure(1, weight=1)
        self.clinical_tab.rowconfigure(3, weight=1)

        ttk.Label(
            self.clinical_tab, text="Triệu chứng", font=("TkDefaultFont", 13, "bold")
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        self.symptoms = tk.Text(
            self.clinical_tab,
            font=("TkDefaultFont", 11),
            padx=10,
            pady=10,
            background="#FFFFFF",
            relief="flat",
            highlightbackground="#CCD6E0",
            highlightthickness=1,
        )
        self.symptoms.grid(row=1, column=0, sticky="nsew", pady=(0, 15))

        ttk.Label(
            self.clinical_tab, text="Chẩn đoán", font=("TkDefaultFont", 13, "bold")
        ).grid(row=2, column=0, sticky="w", pady=(0, 6))

        self.diagnosis = tk.Text(
            self.clinical_tab,
            font=("TkDefaultFont", 11),
            padx=10,
            pady=10,
            background="#FFFFFF",
            relief="flat",
            highlightbackground="#CCD6E0",
            highlightthickness=1,
        )
        self.diagnosis.grid(row=3, column=0, sticky="nsew")

        self.symptoms.bind("<<Modified>>", self._content_changed)
        self.diagnosis.bind("<<Modified>>", self._content_changed)

    def _build_lab_tab(self) -> None:
        self.lab_tab.columnconfigure(0, weight=1)
        self.lab_tab.rowconfigure(0, weight=1)
        columns = ("stt", "ten", "ket_qua", "thoi_diem", "don_gia")
        self.lab_table = tao_bang(
            self.lab_tab,
            columns,
            {
                "stt": "STT",
                "ten": "Xét nghiệm",
                "ket_qua": "Kết quả",
                "thoi_diem": "Ngày giờ thực hiện",
                "don_gia": "Đơn giá",
            },
            {"stt": 55, "ten": 240, "ket_qua": 250, "thoi_diem": 160, "don_gia": 140},
        )
        self.lab_table.column("stt", anchor="center")
        self.lab_table.column("ten", anchor="w")
        self.lab_table.column("ket_qua", anchor="w")
        self.lab_table.column("thoi_diem", anchor="center")
        self.lab_table.column("don_gia", anchor="e")

        self.lab_table.grid(row=0, column=0, sticky="nsew")

        self.lab_actions = ttk.Frame(self.lab_tab)
        self.lab_actions.grid(row=1, column=0, sticky="ew", pady=(8, 0))

        self.add_lab_button = ttk.Button(
            self.lab_actions, text="Chỉ định xét nghiệm", command=self._add_lab
        )
        self.add_lab_button.pack(side="left")
        self.edit_lab_button = ttk.Button(
            self.lab_actions, text="Cập nhật kết quả", command=self._edit_lab
        )
        self.edit_lab_button.pack(side="left", padx=8)

        self.lab_note = ttk.Label(
            self.lab_actions,
            text="Xét nghiệm liên kết trực tiếp với phiếu khám; kết quả có thể để trống khi đang chờ.",
        )

    def _build_medicine_tab(self) -> None:
        self.medicine_tab.columnconfigure(0, weight=1)
        self.medicine_tab.rowconfigure(0, weight=1)
        columns = ("stt", "ten", "so_luong", "cach_dung", "don_gia", "thanh_tien")
        self.medicine_table = tao_bang(
            self.medicine_tab,
            columns,
            {
                "stt": "STT",
                "ten": "Thuốc",
                "so_luong": "Số lượng",
                "cach_dung": "Cách dùng",
                "don_gia": "Đơn giá áp dụng",
                "thanh_tien": "Thành tiền",
            },
            {
                "stt": 55,
                "ten": 220,
                "so_luong": 80,
                "cach_dung": 230,
                "don_gia": 140,
                "thanh_tien": 140,
            },
        )
        self.medicine_table.column("stt", anchor="center")
        self.medicine_table.column("ten", anchor="w")
        self.medicine_table.column("so_luong", anchor="center")
        self.medicine_table.column("cach_dung", anchor="w")
        self.medicine_table.column("don_gia", anchor="e")
        self.medicine_table.column("thanh_tien", anchor="e")

        self.medicine_table.grid(row=0, column=0, sticky="nsew")

        self.med_actions = ttk.Frame(self.medicine_tab)
        self.med_actions.grid(row=1, column=0, sticky="ew", pady=(8, 0))

        self.prescription_button = ttk.Button(
            self.med_actions,
            text="Kê đơn / quản lý đơn thuốc",
            command=self._open_prescription,
        )
        self.prescription_button.pack(side="left")

        self.prescription_note = ttk.Label(self.med_actions, text="")
        self.prescription_note.pack(side="left", padx=8)

    def _refresh(self) -> None:
        try:
            data = lay_chi_tiet_lan_kham(self.ma_phieu, self.vai_tro, self.ma_nguoi_xem)
        except Exception as error:
            hien_loi(self, error)
            return

        info = data["thong_tin"]
        patient = lay_benh_nhan(info["ma_benh_nhan"])

        self.read_only = self.vai_tro != "doctor" or info["trang_thai"] != "DANG_KHAM"
        self._saved_symptoms = data["trieu_chung"] or ""
        self._saved_diagnosis = data["chan_doan"] or ""
        self.dirty = False

        self.lbl_title.configure(text=f'PHIẾU KHÁM: {info["ma_phieu"]}')
        self.lbl_datetime.configure(
            text=f'Ngày giờ khám: {info["ngay_gio_kham"]:%d/%m/%Y %H:%M}'
        )

        trang_thai = info["trang_thai"]
        if trang_thai == "HOAN_THANH":
            self.lbl_status.configure(text="HOÀN THÀNH", foreground="#2E8B57")
        else:
            self.lbl_status.configure(text="ĐANG KHÁM", foreground="#E7A23B")

        self.lbl_patient.configure(
            text=f"{info['ho_ten_benh_nhan']} (Mã bệnh nhân: {info['ma_benh_nhan']})"
        )

        if patient:
            ngay_sinh_str = (
                patient["ngay_sinh"].strftime("%d/%m/%Y")
                if patient.get("ngay_sinh")
                else "—"
            )
            self.lbl_dob.configure(text=f"Ngày sinh: {ngay_sinh_str}")

            raw_g = (patient.get("gioi_tinh") or "").upper()
            hien_thi_gt = {"NAM": "Nam", "NU": "Nữ", "KHAC": "Khác"}.get(
                raw_g, raw_g or "—"
            )

            self.lbl_gender.configure(text=f"Giới tính: {hien_thi_gt}")
            self.lbl_address.configure(text=f"Địa chỉ: {patient.get('dia_chi') or '—'}")
        else:
            self.lbl_dob.configure(text="Ngày sinh: —")
            self.lbl_gender.configure(text="Giới tính: —")
            self.lbl_address.configure(text="Địa chỉ: —")

        self.lbl_phone.configure(text=f"Điện thoại: {info['so_dien_thoai'] or '—'}")
        self.lbl_doctor.configure(
            text=f"Bác sĩ: {info['ten_bac_si']} — {info['ten_khoa']}"
        )

        self.total.configure(
            text=(
                f'Giá khám: {dinh_dang_tien(info["gia_kham"])}\n\n'
                f'Xét nghiệm: {dinh_dang_tien(info["gia_xet_nghiem"])}\n\n'
                f'Thuốc: {dinh_dang_tien(info["gia_thuoc"])}'
            )
        )

        if self.read_only:
            self.save_content_button.pack_forget()
            self.complete_button.pack_forget()
            self.export_button.pack(side="left")
        else:
            self.save_content_button.pack(side="left")
            self.complete_button.pack(side="left", padx=8)
            self.export_button.pack_forget()

        if self.read_only:
            self.add_lab_button.pack_forget()
            self.edit_lab_button.pack_forget()
            self.lab_note.pack(side="left")

            self.prescription_button.pack_forget()
            self.prescription_note.pack(side="left")
        else:
            self.add_lab_button.pack(side="left")
            self.edit_lab_button.pack(side="left", padx=8)
            self.lab_note.pack_forget()

            self.prescription_button.pack(side="left")
            self.prescription_note.pack_forget()

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
                    performed_at.strftime("%d/%m/%Y %H:%M") if performed_at else "—",
                    dinh_dang_tien(row["don_gia_ap_dung"]),
                ),
            )

        for item in self.medicine_table.get_children():
            self.medicine_table.delete(item)
        order = data["don_thuoc"]
        if order:
            for index, row in enumerate(order["ds_thuoc"], start=1):
                self.medicine_table.insert(
                    "",
                    "end",
                    values=(
                        index,
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
        messagebox.showinfo("Đã lưu", "Đã lưu nội dung khám thành công.", parent=self)
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
            "Hoàn thành phiếu", "Phiếu khám đã chuyển sang HOAN_THANH.", parent=self
        )
        self._refresh()
        if self.on_changed is not None:
            self.on_changed()

    def _request_close(self) -> None:
        if self.dirty and not xac_nhan_thay_doi_chua_luu(self, self._save_content):
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
        dialog.update_idletasks()
        x = (self.winfo_screenwidth() - self.winfo_width()) // 2
        y = (self.winfo_screenheight() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
        self.minsize(1000, 580)
        self.configure(background="#F4F7FA")
        self.transient(self)
        form = KeDonView(dialog, ma_phieu=self.ma_phieu)
        form.pack(fill="both", expand=True)
        dialog.protocol("WM_DELETE_WINDOW", lambda: form.request_close(dialog.destroy))
        dialog.grab_set()
        self.wait_window(dialog)
        self._refresh()


__all__ = ["PhieuKhamDetailDialog", "TaoPhieuKhamDialog"]
