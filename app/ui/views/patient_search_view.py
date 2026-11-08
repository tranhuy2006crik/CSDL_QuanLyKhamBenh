import tkinter as tk
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from app.pdf_export import xuat_bang_pdf
from app.services.clinic_service import lay_lich_su_benh_nhan, lay_tien_su_benh
from app.services.tim_kiem_service import tim_kiem_benh_nhan
from app.services.tra_cuu_service import lay_chi_tiet_lan_kham
from app.ui.views.common import dinh_dang_tien, hien_loi, tao_bang
from app.ui.views.visit_dialogs import PhieuKhamDetailDialog, TaoPhieuKhamDialog


class PatientSearchView(ttk.Frame):
    def __init__(self, parent: tk.Misc, ma_bac_si: str) -> None:
        super().__init__(parent, padding=10)
        self.ma_bac_si = str(ma_bac_si).strip()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.selected_patient_data = None
        self.patients_data = {}
        self.current_visits = []

        self.paned = ttk.PanedWindow(self, orient="horizontal")
        self.paned.grid(row=0, column=0, sticky="nsew")

        self._build_left_panel()
        self._build_right_panel()

        self.paned.add(self.left_panel, weight=1)
        self.paned.add(self.right_panel, weight=5)

    def _build_left_panel(self):
        self.left_panel = ttk.Frame(
            self.paned, padding=8, relief="solid", borderwidth=1
        )
        self.left_panel.columnconfigure(0, weight=1)
        self.left_panel.rowconfigure(4, weight=1)

        ttk.Label(
            self.left_panel,
            text="Danh sách bệnh nhân",
            font=("Segoe UI", 12, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        search_frame = ttk.Frame(self.left_panel)
        search_frame.grid(row=1, column=0, sticky="ew", pady=(0, 5))
        search_frame.columnconfigure(0, weight=1)

        self.entry_keyword = ttk.Entry(search_frame)
        self.entry_keyword.insert(0, "Mã, tên, SĐT...")
        self.entry_keyword.bind(
            "<FocusIn>",
            lambda e: (
                self.entry_keyword.delete(0, "end")
                if self.entry_keyword.get() == "Mã, tên, SĐT..."
                else None
            ),
        )
        self.entry_keyword.grid(row=0, column=0, sticky="ew")

        ttk.Button(search_frame, text="🔍", width=3, command=self._perform_search).grid(
            row=0, column=1, padx=(4, 2)
        )
        ttk.Button(search_frame, text="Xóa", width=4, command=self._clear_filters).grid(
            row=0, column=2
        )

        self.btn_adv_search = ttk.Button(
            self.left_panel,
            text="Bộ lọc nâng cao (Ẩn/Hiện)",
            command=self._toggle_advanced_search,
        )
        self.btn_adv_search.grid(row=2, column=0, sticky="ew", pady=(0, 5))

        self.adv_frame = ttk.Frame(self.left_panel)
        ttk.Label(self.adv_frame, text="Ngày sinh (dd/mm/yyyy):").pack(anchor="w")
        self.entry_dob = ttk.Entry(self.adv_frame)
        self.entry_dob.pack(fill="x", pady=2)
        ttk.Label(self.adv_frame, text="Giới tính:").pack(anchor="w")
        self.combo_gender = ttk.Combobox(
            self.adv_frame,
            state="readonly",
            values=["Tất cả", "NAM", "NU", "KHAC"],
        )
        self.combo_gender.current(0)
        self.combo_gender.pack(fill="x", pady=4)
        self.is_adv_open = False

        columns = ("ma_bn", "ho_ten")
        self.table = tao_bang(
            self.left_panel,
            columns,
            {"ma_bn": "Mã", "ho_ten": "Họ tên"},
            {"ma_bn": 60, "ho_ten": 150},
        )
        self.table.column("ma_bn", anchor="center")
        self.table.grid(row=4, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(
            self.left_panel, orient="vertical", command=self.table.yview
        )
        scrollbar.grid(row=4, column=1, sticky="ns")
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.bind("<<TreeviewSelect>>", self._on_select_patient)

        self._perform_search()

    def _toggle_advanced_search(self):
        if self.is_adv_open:
            self.adv_frame.grid_forget()
        else:
            self.adv_frame.grid(row=3, column=0, sticky="ew", pady=(0, 5))
        self.is_adv_open = not self.is_adv_open

    def _clear_filters(self):
        self.entry_keyword.delete(0, tk.END)
        self.entry_keyword.insert(0, "Mã, tên, SĐT...")
        self.entry_dob.delete(0, tk.END)
        self.combo_gender.current(0)
        self._perform_search()

    def _build_right_panel(self):
        self.right_panel = ttk.Frame(self.paned, padding=20)
        self.right_panel.columnconfigure(0, weight=1)
        self.right_panel.rowconfigure(1, weight=1)

        self.empty_view = ttk.Frame(self.right_panel)
        self.empty_view.place(relx=0.5, rely=0.5, anchor="center")
        ttk.Label(
            self.empty_view, text="📋", font=("Segoe UI", 40), foreground="gray"
        ).pack()
        ttk.Label(
            self.empty_view,
            text="Chọn một bệnh nhân để xem chi tiết hồ sơ",
            font=("Segoe UI", 12),
            foreground="gray",
        ).pack()

        self.detail_view = ttk.Frame(self.right_panel)
        self.detail_view.columnconfigure(0, weight=1)
        self.detail_view.rowconfigure(3, weight=1)

        self.lbl_name = ttk.Label(
            self.detail_view,
            text="",
            font=("Segoe UI", 20, "bold"),
            foreground="#111827",
        )
        self.lbl_name.grid(row=0, column=0, sticky="w")

        self.lbl_sub_info = ttk.Label(
            self.detail_view,
            text="",
            font=("Segoe UI", 11),
            foreground="#6b7280",
        )
        self.lbl_sub_info.grid(row=1, column=0, sticky="w", pady=(4, 12))

        history_frame = ttk.Frame(self.detail_view)
        history_frame.grid(row=2, column=0, sticky="ew", pady=(0, 16))

        self.lbl_medical_history = ttk.Label(
            history_frame,
            text="Tiền sử bệnh: —",
            wraplength=650,
            justify="left",
            font=("Segoe UI", 10, "italic"),
        )
        self.lbl_medical_history.pack(side="left", fill="x", expand=True)

        table_frame = ttk.Frame(self.detail_view, relief="solid", borderwidth=1)
        table_frame.grid(row=3, column=0, sticky="nsew", pady=(0, 16))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        columns = ("ma_phieu", "ngay_gio", "bac_si", "khoa", "chan_doan", "tong")
        self.table_history = tao_bang(
            table_frame,
            columns,
            {
                "ma_phieu": "Mã phiếu",
                "ngay_gio": "Ngày giờ khám",
                "bac_si": "Bác sĩ",
                "khoa": "Khoa",
                "chan_doan": "Chẩn đoán",
                "tong": "Tổng chi phí",
            },
            {
                "ma_phieu": 80,
                "ngay_gio": 120,
                "bac_si": 130,
                "khoa": 110,
                "chan_doan": 140,
                "tong": 100,
            },
        )

        self.table_history.column("ma_phieu", anchor="center")
        self.table_history.column("ngay_gio", anchor="center")
        self.table_history.column("tong", anchor="e")

        self.table_history.grid(row=0, column=0, sticky="nsew")
        self.table_history.bind("<Double-1>", self._open_selected_visit)

        history_scroll = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.table_history.yview
        )
        history_scroll.grid(row=0, column=1, sticky="ns")
        self.table_history.configure(yscrollcommand=history_scroll.set)

        action_frame = ttk.Frame(self.detail_view)
        action_frame.grid(row=4, column=0, sticky="ew")
        ttk.Button(
            action_frame, text="Xem chi tiết phiếu", command=self._open_selected_visit
        ).pack(side="left")
        ttk.Button(
            action_frame, text="Tạo phiếu khám mới", command=self._create_visit
        ).pack(side="left", padx=8)
        ttk.Button(
            action_frame, text="Tải lại hồ sơ", command=self._refresh_history
        ).pack(side="left")
        ttk.Button(
            action_frame, text="Xuất PDF hồ sơ", command=self._export_history_pdf
        ).pack(side="right")

    def _perform_search(self):
        keyword = self.entry_keyword.get().strip()
        if keyword == "Mã, tên, SĐT...":
            keyword = ""
        dob_str = self.entry_dob.get().strip()
        dob_val = None
        if dob_str:
            try:
                dob_val = datetime.strptime(dob_str, "%d/%m/%Y").date()
            except ValueError:
                messagebox.showerror(
                    "Lỗi",
                    "Ngày sinh phải theo định dạng dd/mm/yyyy",
                    parent=self,
                )
                return
        gender = self.combo_gender.get()
        gender_val = None if gender == "Tất cả" else gender

        try:
            results = tim_kiem_benh_nhan(
                tu_khoa=keyword,
                ngay_sinh=dob_val,
                gioi_tinh=gender_val,
                dia_chi="",
            )
        except Exception as e:
            hien_loi(self, e)
            return

        for item in self.table.get_children():
            self.table.delete(item)
        self.patients_data = {row["MaBenhNhan"]: row for row in results}
        for row in results:
            self.table.insert(
                "",
                "end",
                iid=row["MaBenhNhan"],
                values=(row["MaBenhNhan"], row["HoTen"]),
            )

    def _on_select_patient(self, event):
        selection = self.table.selection()
        if not selection:
            return
        ma_bn = selection[0]
        patient = self.patients_data[ma_bn]
        self.selected_patient_data = patient

        self.empty_view.place_forget()
        self.detail_view.grid(row=0, column=0, sticky="nsew")

        self.lbl_name.configure(text=f"{patient['HoTen']}")
        ngay_sinh = (
            patient["NgaySinh"].strftime("%d/%m/%Y") if patient["NgaySinh"] else "—"
        )
        self.lbl_sub_info.configure(
            text=f"Mã BN: {ma_bn} • Sinh ngày: {ngay_sinh} • SĐT: {patient['SoDienThoai'] or '—'} • Giới tính: {patient['GioiTinh']}"
        )

        self._refresh_history()

    def _refresh_history(self):
        if not self.selected_patient_data:
            return
        ma_bn = self.selected_patient_data["MaBenhNhan"]
        try:
            visits = lay_lich_su_benh_nhan(ma_bn)
            medical_history = lay_tien_su_benh(ma_bn)
        except Exception as e:
            hien_loi(self, e)
            return

        self.current_visits = visits
        self.lbl_medical_history.configure(
            text=f"Tiền sử bệnh: {medical_history or 'Chưa ghi nhận.'}"
        )

        for item in self.table_history.get_children():
            self.table_history.delete(item)
        for visit in visits:
            self.table_history.insert(
                "",
                "end",
                iid=str(visit["ma_phieu"]),
                values=(
                    visit["ma_phieu"],
                    visit["ngay_gio_kham"].strftime("%d/%m/%Y %H:%M"),
                    visit["ten_bac_si"],
                    visit["ten_khoa"],
                    visit["chan_doan"] or "—",
                    dinh_dang_tien(visit["tong_chi_phi"]),
                ),
            )

    def _open_selected_visit(self, event=None):
        selection = self.table_history.selection()
        if not selection:
            if event is None:
                messagebox.showinfo(
                    "Phiếu khám", "Hãy chọn một phiếu khám.", parent=self
                )
            return
        ma_phieu = str(selection[0]).strip()
        try:
            detail = lay_chi_tiet_lan_kham(ma_phieu)
        except Exception as error:
            hien_loi(self, error)
            return

        info = detail["thong_tin"]
        raw_status = (
            info.get("trang_thai_phieu_kham") or info.get("TrangThaiPhieuKham") or ""
        )
        status = (
            "HOAN_THANH"
            if "HOAN_THANH" in ma_phieu.upper()
            or str(raw_status).strip().upper() == "HOAN_THANH"
            else "DANG_KHAM"
        )
        visit_doctor = str(info.get("ma_bac_si", "")).strip()
        if status == "DANG_KHAM" and visit_doctor and visit_doctor != self.ma_bac_si:
            messagebox.showwarning(
                "Không có quyền truy cập",
                f"Phiếu khám {ma_phieu} đang trong trạng thái ĐANG KHÁM của bác sĩ {info.get('ten_bac_si', visit_doctor)}. Bạn không có quyền mở phiếu đang khám của bác sĩ khác.",
                parent=self,
            )
            return

        PhieuKhamDetailDialog(
            self.winfo_toplevel(),
            ma_phieu,
            read_only=(status == "HOAN_THANH" or visit_doctor != self.ma_bac_si),
            on_changed=self._refresh_history,
        )

    def _create_visit(self):
        if not self.selected_patient_data:
            return
        dialog = TaoPhieuKhamDialog(
            self.winfo_toplevel(),
            self.selected_patient_data["MaBenhNhan"],
            self.ma_bac_si,
            self.selected_patient_data["HoTen"],
        )
        self.wait_window(dialog)
        if dialog.result is None:
            return
        self._refresh_history()
        PhieuKhamDetailDialog(
            self.winfo_toplevel(),
            dialog.result,
            read_only=False,
            on_changed=self._refresh_history,
        )

    def _export_history_pdf(self):
        if not self.selected_patient_data:
            return
        ma_bn = self.selected_patient_data["MaBenhNhan"]
        ho_ten = self.selected_patient_data["HoTen"]
        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Lưu PDF Hồ sơ bệnh án",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=f"ho_so_benh_an_{ma_bn}.pdf",
        )
        if not file_path:
            return
        try:
            cot = [
                {"key": "ma_phieu", "label": "Mã phiếu", "kind": "text"},
                {"key": "ngay_gio_kham", "label": "Ngày giờ khám", "kind": "datetime"},
                {"key": "ten_bac_si", "label": "Bác sĩ", "kind": "text"},
                {"key": "ten_khoa", "label": "Khoa", "kind": "text"},
                {"key": "chan_doan", "label": "Chẩn đoán", "kind": "text"},
                {"key": "tong_chi_phi", "label": "Tổng chi phí", "kind": "money"},
            ]
            pdf_rows = [
                {
                    "ma_phieu": str(v["ma_phieu"]),
                    "ngay_gio_kham": v["ngay_gio_kham"],
                    "ten_bac_si": str(v["ten_bac_si"]),
                    "ten_khoa": str(v["ten_khoa"]),
                    "chan_doan": str(v["chan_doan"] or "—"),
                    "tong_chi_phi": Decimal(str(v["tong_chi_phi"] or 0)),
                }
                for v in self.current_visits
            ]
            tong_ket = {
                "tong_so_luot_kham": len(self.current_visits),
                "gia_kham": sum(
                    (Decimal(str(v.get("gia_kham") or 0)) for v in self.current_visits),
                    Decimal("0"),
                ),
                "gia_xet_nghiem": sum(
                    (
                        Decimal(str(v.get("gia_xet_nghiem") or 0))
                        for v in self.current_visits
                    ),
                    Decimal("0"),
                ),
                "gia_thuoc": sum(
                    (
                        Decimal(str(v.get("gia_thuoc") or 0))
                        for v in self.current_visits
                    ),
                    Decimal("0"),
                ),
                "tong_gia_tri": sum(
                    (
                        Decimal(str(v.get("tong_chi_phi") or 0))
                        for v in self.current_visits
                    ),
                    Decimal("0"),
                ),
            }
            xuat_bang_pdf(
                duong_dan=Path(file_path),
                tieu_de=f"HỒ SƠ BỆNH ÁN — {ho_ten} ({ma_bn})",
                dieu_kien=self.lbl_medical_history.cget("text"),
                cot=cot,
                rows=pdf_rows,
                tong_ket=tong_ket,
            )
            messagebox.showinfo(
                "Thành công",
                f"Đã xuất PDF hồ sơ bệnh án tại:\n{file_path}",
                parent=self,
            )
        except Exception as error:
            hien_loi(self, error)
