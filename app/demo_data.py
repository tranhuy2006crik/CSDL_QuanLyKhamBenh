from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from app.contracts import (
    CHUA_CHI_DINH,
    CON_CHO,
    DA_DU_KET_QUA,
    ChiTietLanKham,
    DonThuocDTO,
    LichSuKhamRow,
)
from app.errors import AppError


DEMO_PATIENT_ID = 900001
DEMO_DOCTOR_ID = 900101
DEMO_SECOND_PATIENT_ID = 900002
DEMO_SECOND_DOCTOR_ID = 900102
DEMO_DEPARTMENT_ID = 90001
DEMO_SECOND_DEPARTMENT_ID = 90002


class DemoClinicData:
    """Isolated in-memory dataset. It never opens a MySQL connection."""

    def __init__(self) -> None:
        today = date.today()
        self.departments = [
            {"ma_khoa": DEMO_DEPARTMENT_ID, "ten_khoa": "Khoa Nội (DEMO)"},
            {"ma_khoa": DEMO_SECOND_DEPARTMENT_ID, "ten_khoa": "Khoa Nhi (DEMO)"},
        ]
        self.doctors = [
            {
                "ma_bac_si": DEMO_DOCTOR_ID,
                "ten_bac_si": "Nguyễn Minh An (DEMO)",
                "ma_khoa": DEMO_DEPARTMENT_ID,
                "gia_kham": Decimal("150000"),
                "phong_kham": "P. DEMO-01",
            },
            {
                "ma_bac_si": DEMO_SECOND_DOCTOR_ID,
                "ten_bac_si": "Trần Thu Hà (DEMO)",
                "ma_khoa": DEMO_SECOND_DEPARTMENT_ID,
                "gia_kham": Decimal("180000"),
                "phong_kham": "P. DEMO-02",
            },
        ]
        self.patients = [
            {
                "ma_benh_nhan": DEMO_PATIENT_ID,
                "ho_ten": "Lê Minh Hùng (DEMO)",
                "ngay_sinh": date(2002, 2, 6),
                "nam_sinh": 2002,
                "gioi_tinh": "Nam",
                "dia_chi": "Hà Nội (dữ liệu demo)",
                "so_dien_thoai": "0900000001",
            },
            {
                "ma_benh_nhan": DEMO_SECOND_PATIENT_ID,
                "ho_ten": "Phạm Ngọc Mai (DEMO)",
                "ngay_sinh": date(2004, 9, 21),
                "nam_sinh": 2004,
                "gioi_tinh": "Nữ",
                "dia_chi": "Hà Nội (dữ liệu demo)",
                "so_dien_thoai": "0900000002",
            },
        ]
        self.dossiers = {
            DEMO_PATIENT_ID: {
                "ma_ho_so": 980001,
                "ma_benh_nhan": DEMO_PATIENT_ID,
                "tien_su_benh": "Dị ứng phấn hoa (dữ liệu minh họa).",
            },
            DEMO_SECOND_PATIENT_ID: {
                "ma_ho_so": 980002,
                "ma_benh_nhan": DEMO_SECOND_PATIENT_ID,
                "tien_su_benh": None,
            },
        }
        self.medicines = {
            990001: {
                "ma_thuoc": 990001,
                "ten_thuoc": "Paracetamol (DEMO)",
                "don_gia": Decimal("2500"),
                "don_vi_tinh": "viên",
                "so_luong_co_san": 100,
            },
            990002: {
                "ma_thuoc": 990002,
                "ten_thuoc": "Vitamin C (DEMO)",
                "don_gia": Decimal("1800"),
                "don_vi_tinh": "viên",
                "so_luong_co_san": 80,
            },
            990003: {
                "ma_thuoc": 990003,
                "ten_thuoc": "Nước muối sinh lý (DEMO)",
                "don_gia": Decimal("12000"),
                "don_vi_tinh": "chai",
                "so_luong_co_san": 30,
            },
        }
        first_visit_date = today.replace(day=1)
        second_visit_date = today
        self.visits: dict[int, dict[str, Any]] = {
            970001: {
                "ma_phieu": 970001,
                "ma_benh_nhan": DEMO_PATIENT_ID,
                "ma_bac_si": DEMO_DOCTOR_ID,
                "ngay_gio_kham": datetime.combine(
                    first_visit_date, time(hour=9, minute=15)
                ),
                "chan_doan": "Viêm mũi dị ứng (minh họa).",
                "trieu_chung": "Hắt hơi, ngạt mũi.",
                "gia_kham": Decimal("150000"),
                "ds_xet_nghiem": [
                    {
                        "ma_phieu": 970001,
                        "stt": 1,
                        "ten_xet_nghiem": "Công thức máu (DEMO)",
                        "ket_qua": "Trong giới hạn tham chiếu (minh họa).",
                        "ngay_gio_thuc_hien": datetime.combine(
                            first_visit_date, time(hour=9, minute=45)
                        ),
                        "don_gia_ap_dung": Decimal("90000"),
                    }
                ],
                "don_thuoc": {
                    "ma_don": 960001,
                    "ngay_lap": first_visit_date,
                    "loi_dan": "Dữ liệu minh họa, không dùng điều trị.",
                    "ds_thuoc": [
                        {
                            "ma_thuoc": 990001,
                            "so_luong_ke": 4,
                            "cach_dung": "Uống khi sốt (minh họa).",
                            "don_gia_ap_dung": Decimal("2500"),
                        },
                        {
                            "ma_thuoc": 990002,
                            "so_luong_ke": 4,
                            "cach_dung": "Sau ăn (minh họa).",
                            "don_gia_ap_dung": Decimal("1800"),
                        },
                    ],
                },
            },
            970002: {
                "ma_phieu": 970002,
                "ma_benh_nhan": DEMO_PATIENT_ID,
                "ma_bac_si": DEMO_SECOND_DOCTOR_ID,
                "ngay_gio_kham": datetime.combine(
                    second_visit_date, time(hour=14, minute=0)
                ),
                "chan_doan": "Theo dõi sức khỏe định kỳ (minh họa).",
                "trieu_chung": "Khám sức khỏe định kỳ.",
                "gia_kham": Decimal("180000"),
                "ds_xet_nghiem": [
                    {
                        "ma_phieu": 970002,
                        "stt": 1,
                        "ten_xet_nghiem": "Đường huyết (DEMO)",
                        "ket_qua": None,
                        "ngay_gio_thuc_hien": None,
                        "don_gia_ap_dung": Decimal("60000"),
                    }
                ],
                "don_thuoc": None,
            },
        }
        weekdays = (
            "Thứ Hai",
            "Thứ Ba",
            "Thứ Tư",
            "Thứ Năm",
            "Thứ Sáu",
            "Thứ Bảy",
            "Chủ Nhật",
        )
        shifts = (
            (timedelta(hours=8), timedelta(hours=12)),
            (timedelta(hours=13), timedelta(hours=17)),
        )
        self.schedule = [
            {
                "ma_bac_si": DEMO_DOCTOR_ID,
                "ten_bac_si": "Nguyễn Minh An (DEMO)",
                "phong_kham": "P. DEMO-01",
                "thu": weekday,
                "gio_bat_dau": start,
                "gio_ket_thuc": end,
                "ma_khoa": DEMO_DEPARTMENT_ID,
            }
            for weekday in weekdays
            for start, end in shifts
        ] + [
            {
                "ma_bac_si": DEMO_SECOND_DOCTOR_ID,
                "ten_bac_si": "Trần Thu Hà (DEMO)",
                "phong_kham": "P. DEMO-02",
                "thu": "Thứ Ba",
                "gio_bat_dau": timedelta(hours=8),
                "gio_ket_thuc": timedelta(hours=12),
                "ma_khoa": DEMO_SECOND_DEPARTMENT_ID,
            },
        ]
        for visit in self.visits.values():
            order = visit["don_thuoc"]
            if order is not None:
                for line in order["ds_thuoc"]:
                    self.medicines[line["ma_thuoc"]]["so_luong_co_san"] -= line[
                        "so_luong_ke"
                    ]
        self._refresh_all_totals()

    @staticmethod
    def _money(value: Decimal | int | str | None) -> Decimal:
        return Decimal(str(value or 0))

    def _refresh_visit_totals(self, visit: dict[str, Any]) -> dict[str, Any]:
        lab_total = sum(
            (self._money(row["don_gia_ap_dung"]) for row in visit["ds_xet_nghiem"]),
            Decimal("0"),
        )
        order = visit["don_thuoc"]
        medicine_total = Decimal("0")
        if order is not None:
            order_lines = []
            for line in order["ds_thuoc"]:
                medicine = self.medicines[line["ma_thuoc"]]
                line_total = self._money(line["don_gia_ap_dung"]) * line["so_luong_ke"]
                medicine_total += line_total
                order_lines.append(
                    {
                        **line,
                        "ten_thuoc": medicine["ten_thuoc"],
                        "don_vi_tinh": medicine["don_vi_tinh"],
                        "thanh_tien": line_total,
                    }
                )
            order["gia_don"] = medicine_total
            order["ds_thuoc_hien_thi"] = order_lines
        visit["gia_xet_nghiem"] = lab_total
        visit["gia_thuoc"] = medicine_total
        visit["tong_gia_tri"] = (
            self._money(visit["gia_kham"]) + lab_total + medicine_total
        )
        return visit

    def _refresh_all_totals(self) -> None:
        for visit in self.visits.values():
            self._refresh_visit_totals(visit)

    def get_patient(self, patient_id: int) -> dict[str, Any] | None:
        row = next(
            (row for row in self.patients if row["ma_benh_nhan"] == patient_id),
            None,
        )
        return deepcopy(row) if row is not None else None

    def get_doctor(self, doctor_id: int) -> dict[str, Any] | None:
        row = next(
            (row for row in self.doctors if row["ma_bac_si"] == doctor_id),
            None,
        )
        return deepcopy(row) if row is not None else None

    def list_departments(self) -> list[dict[str, Any]]:
        return deepcopy(self.departments)

    def list_doctors(self, department_id: int | None = None) -> list[dict[str, Any]]:
        rows = [
            doctor
            for doctor in self.doctors
            if department_id is None or doctor["ma_khoa"] == department_id
        ]
        return deepcopy(
            [
                {
                    "ma_bac_si": row["ma_bac_si"],
                    "ten_bac_si": row["ten_bac_si"],
                    "ma_khoa": row["ma_khoa"],
                }
                for row in rows
            ]
        )

    def list_medicines(self) -> list[dict[str, Any]]:
        return deepcopy(list(self.medicines.values()))

    def search_patients(
        self, keyword: str, department_id: int | None, doctor_id: int | None
    ) -> list[dict[str, Any]]:
        needle = keyword.strip().casefold()
        results = []
        for patient in self.patients:
            if needle and not any(
                needle in str(patient[field] or "").casefold()
                for field in (
                    "ma_benh_nhan",
                    "ho_ten",
                    "so_dien_thoai",
                    "dia_chi",
                )
            ):
                continue
            patient_visits = [
                visit
                for visit in self.visits.values()
                if visit["ma_benh_nhan"] == patient["ma_benh_nhan"]
            ]
            if doctor_id is not None and not any(
                visit["ma_bac_si"] == doctor_id for visit in patient_visits
            ):
                continue
            if department_id is not None:
                doctor_ids = {
                    doctor["ma_bac_si"]
                    for doctor in self.doctors
                    if doctor["ma_khoa"] == department_id
                }
                if not any(
                    visit["ma_bac_si"] in doctor_ids for visit in patient_visits
                ):
                    continue
            results.append(patient)
        return deepcopy(sorted(results, key=lambda row: (row["ho_ten"], row["ma_benh_nhan"])))

    def history(self, patient_id: int) -> list[LichSuKhamRow]:
        rows = []
        for visit in self.visits.values():
            if visit["ma_benh_nhan"] != patient_id:
                continue
            self._refresh_visit_totals(visit)
            doctor = self.get_doctor(visit["ma_bac_si"])
            department = next(
                item for item in self.departments if item["ma_khoa"] == doctor["ma_khoa"]
            )
            rows.append(
                {
                    "ma_phieu": visit["ma_phieu"],
                    "ngay_gio_kham": visit["ngay_gio_kham"],
                    "ma_bac_si": visit["ma_bac_si"],
                    "ten_bac_si": doctor["ten_bac_si"],
                    "ten_khoa": department["ten_khoa"],
                    "chan_doan": visit["chan_doan"],
                    "trieu_chung": visit["trieu_chung"],
                    "gia_kham": visit["gia_kham"],
                    "gia_xet_nghiem": visit["gia_xet_nghiem"],
                    "gia_thuoc": visit["gia_thuoc"],
                    "tong_chi_phi": visit["tong_gia_tri"],
                }
            )
        rows.sort(key=lambda row: (row["ngay_gio_kham"], row["ma_phieu"]), reverse=True)
        return deepcopy(rows)

    def medical_history(self, patient_id: int) -> str | None:
        dossier = self.dossiers.get(patient_id)
        return dossier["tien_su_benh"] if dossier else None

    def weekly_schedule(self, department_id: int) -> list[dict[str, Any]]:
        return deepcopy(
            [
                row
                for row in self.schedule
                if row["ma_khoa"] == department_id
            ]
        )

    def report(
        self,
        start: date,
        end: date,
        department_id: int | None,
        keyword: str,
        include_empty: bool,
    ) -> list[dict[str, Any]]:
        needle = keyword.strip().casefold()
        result = []
        for doctor in self.doctors:
            if department_id is not None and doctor["ma_khoa"] != department_id:
                continue
            if needle and needle not in str(doctor["ma_bac_si"]).casefold() and needle not in doctor[
                "ten_bac_si"
            ].casefold():
                continue
            visits = [
                visit
                for visit in self.visits.values()
                if visit["ma_bac_si"] == doctor["ma_bac_si"]
                and start <= visit["ngay_gio_kham"].date() < end
            ]
            if not visits and not include_empty:
                continue
            total = sum(
                (self._refresh_visit_totals(visit)["tong_gia_tri"] for visit in visits),
                Decimal("0"),
            )
            department = next(
                item for item in self.departments if item["ma_khoa"] == doctor["ma_khoa"]
            )
            result.append(
                {
                    "ma_bac_si": doctor["ma_bac_si"],
                    "ten_bac_si": doctor["ten_bac_si"],
                    "ma_khoa": doctor["ma_khoa"],
                    "ten_khoa": department["ten_khoa"],
                    "so_luot_kham": len(visits),
                    "tong_gia_tri": total,
                }
            )
        result.sort(
            key=lambda row: (
                -row["tong_gia_tri"],
                row["ten_bac_si"],
                row["ma_bac_si"],
            )
        )
        return deepcopy(result)

    def visit_detail(self, visit_id: int) -> ChiTietLanKham:
        visit = self.visits.get(visit_id)
        if visit is None:
            raise AppError("KHONG_TIM_THAY", "Không tìm thấy phiếu khám demo.")
        self._refresh_visit_totals(visit)
        patient = self.get_patient(visit["ma_benh_nhan"])
        doctor = self.get_doctor(visit["ma_bac_si"])
        department = next(
            item for item in self.departments if item["ma_khoa"] == doctor["ma_khoa"]
        )
        pending_labs = sum(
            not row["ket_qua"] for row in visit["ds_xet_nghiem"]
        )
        labs = len(visit["ds_xet_nghiem"])
        order = self._public_order(visit)
        return deepcopy(
            {
                "thong_tin": {
                    "ma_phieu": visit_id,
                    "ma_benh_nhan": visit["ma_benh_nhan"],
                    "ho_ten_benh_nhan": patient["ho_ten"],
                    "so_dien_thoai": patient["so_dien_thoai"],
                    "ma_bac_si": visit["ma_bac_si"],
                    "ten_bac_si": doctor["ten_bac_si"],
                    "ma_khoa": doctor["ma_khoa"],
                    "ten_khoa": department["ten_khoa"],
                    "ngay_gio_kham": visit["ngay_gio_kham"],
                    "so_xet_nghiem": labs,
                    "so_xet_nghiem_cho": pending_labs,
                    "tinh_trang_xet_nghiem": (
                        CHUA_CHI_DINH
                        if labs == 0
                        else CON_CHO
                        if pending_labs
                        else DA_DU_KET_QUA
                    ),
                    "gia_kham": visit["gia_kham"],
                    "gia_xet_nghiem": visit["gia_xet_nghiem"],
                    "gia_thuoc": visit["gia_thuoc"],
                    "tong_gia_tri": visit["tong_gia_tri"],
                },
                "chan_doan": visit["chan_doan"],
                "trieu_chung": visit["trieu_chung"],
                "ds_xet_nghiem": visit["ds_xet_nghiem"],
                "don_thuoc": order,
            }
        )

    def _public_order(self, visit: dict[str, Any]) -> DonThuocDTO | None:
        order = visit["don_thuoc"]
        if order is None:
            return None
        return {
            "ma_don": order["ma_don"],
            "ma_phieu": visit["ma_phieu"],
            "ngay_lap": order["ngay_lap"],
            "loi_dan": order["loi_dan"],
            "ds_thuoc": deepcopy(order.get("ds_thuoc_hien_thi", [])),
            "gia_don": order.get("gia_don", Decimal("0")),
        }

    def get_order(self, visit_id: int) -> DonThuocDTO | None:
        visit = self.visits.get(visit_id)
        if visit is None:
            return None
        self._refresh_visit_totals(visit)
        return deepcopy(self._public_order(visit))

    def create_visit(
        self,
        visit_id: int,
        patient_id: int,
        doctor_id: int,
        symptoms: str | None,
        diagnosis: str | None,
    ) -> None:
        if patient_id not in self.dossiers:
            raise AppError("KHONG_TIM_THAY", "Bệnh nhân demo chưa có hồ sơ bệnh án.")
        doctor = self.get_doctor(doctor_id)
        if doctor is None:
            raise AppError("KHONG_TIM_THAY", "Không tìm thấy bác sĩ demo.")
        if visit_id in self.visits:
            raise AppError("TRUNG_MA", f"Mã phiếu khám {visit_id} đã được dùng.")
        self.visits[visit_id] = {
            "ma_phieu": visit_id,
            "ma_benh_nhan": patient_id,
            "ma_bac_si": doctor_id,
            "ngay_gio_kham": datetime.now().replace(second=0, microsecond=0),
            "chan_doan": diagnosis,
            "trieu_chung": symptoms,
            "gia_kham": doctor["gia_kham"],
            "ds_xet_nghiem": [],
            "don_thuoc": None,
        }
        self._refresh_visit_totals(self.visits[visit_id])

    def update_visit(
        self, visit_id: int, symptoms: str | None, diagnosis: str | None
    ) -> None:
        visit = self.visits.get(visit_id)
        if visit is None:
            raise AppError("KHONG_TIM_THAY", "Không tìm thấy phiếu khám demo.")
        visit["trieu_chung"] = symptoms
        visit["chan_doan"] = diagnosis

    def save_lab(
        self,
        visit_id: int,
        name: str,
        result: str | None,
        performed_at: datetime | None,
        price: Decimal,
        sequence: int | None,
    ) -> int:
        visit = self.visits.get(visit_id)
        if visit is None:
            raise AppError("KHONG_TIM_THAY", "Không tìm thấy phiếu khám demo.")
        if sequence is None:
            sequence = max((row["stt"] for row in visit["ds_xet_nghiem"]), default=0) + 1
            visit["ds_xet_nghiem"].append(
                {
                    "ma_phieu": visit_id,
                    "stt": sequence,
                    "ten_xet_nghiem": name,
                    "ket_qua": result,
                    "ngay_gio_thuc_hien": performed_at,
                    "don_gia_ap_dung": price,
                }
            )
        else:
            row = next(
                (row for row in visit["ds_xet_nghiem"] if row["stt"] == sequence),
                None,
            )
            if row is None:
                raise AppError("KHONG_TIM_THAY", "Không tìm thấy xét nghiệm demo.")
            row.update(
                {
                    "ten_xet_nghiem": name,
                    "ket_qua": result,
                    "ngay_gio_thuc_hien": performed_at,
                    "don_gia_ap_dung": price,
                }
            )
        self._refresh_visit_totals(visit)
        return sequence

    def save_order(
        self,
        visit_id: int,
        order_id: int,
        order_date: date,
        instructions: str | None,
        lines: list[dict[str, Any]],
        create_new: bool,
    ) -> DonThuocDTO:
        visit = self.visits.get(visit_id)
        if visit is None:
            raise AppError("KHONG_TIM_THAY", "Không tìm thấy phiếu khám demo.")
        if order_date < visit["ngay_gio_kham"].date():
            raise AppError(
                "DU_LIEU_KHONG_HOP_LE",
                "Ngày lập đơn không được trước ngày khám.",
                "ngay_lap",
            )
        current = visit["don_thuoc"]
        if create_new and current is not None:
            raise AppError("DA_CO_DON_THUOC", "Phiếu khám demo đã có đơn thuốc.")
        if not create_new and current is None:
            raise AppError("KHONG_TIM_THAY", "Phiếu khám demo chưa có đơn thuốc.")
        if current is not None and current["ma_don"] != order_id:
            raise AppError(
                "KHONG_TIM_THAY", "Mã đơn không thuộc phiếu khám demo."
            )
        if create_new and any(
            other["don_thuoc"] is not None
            and other["don_thuoc"]["ma_don"] == order_id
            for other in self.visits.values()
        ):
            raise AppError("TRUNG_MA", f"Mã đơn thuốc {order_id} đã được dùng.")

        old_lines = {
            line["ma_thuoc"]: line for line in (current["ds_thuoc"] if current else [])
        }
        new_lines = {line["ma_thuoc"]: line for line in lines}
        deltas = {
            medicine_id: new_lines.get(medicine_id, {}).get("so_luong_ke", 0)
            - old_lines.get(medicine_id, {}).get("so_luong_ke", 0)
            for medicine_id in set(old_lines) | set(new_lines)
        }
        for medicine_id, delta in deltas.items():
            medicine = self.medicines.get(medicine_id)
            if medicine is None:
                raise AppError(
                    "DU_LIEU_KHONG_HOP_LE",
                    f"Không tìm thấy thuốc demo mã {medicine_id}.",
                )
            if delta > medicine["so_luong_co_san"]:
                raise AppError(
                    "KHONG_DU_TON",
                    f"Thuốc {medicine['ten_thuoc']} không đủ tồn demo.",
                )
            if (
                delta < 0
                and medicine["so_luong_co_san"] - delta > 2_147_483_647
            ):
                raise AppError(
                    "DU_LIEU_KHONG_HOP_LE",
                    f"Hoàn tồn thuốc demo mã {medicine_id} vượt phạm vi INT.",
                )

        prepared_lines = []
        for medicine_id, line in new_lines.items():
            previous = old_lines.get(medicine_id)
            medicine = self.medicines[medicine_id]
            prepared_lines.append(
                {
                    "ma_thuoc": medicine_id,
                    "so_luong_ke": line["so_luong_ke"],
                    "cach_dung": line["cach_dung"],
                    "don_gia_ap_dung": (
                        previous["don_gia_ap_dung"]
                        if previous is not None
                        else medicine["don_gia"]
                    ),
                }
            )

        for medicine_id, delta in deltas.items():
            self.medicines[medicine_id]["so_luong_co_san"] -= delta
        visit["don_thuoc"] = {
            "ma_don": order_id,
            "ngay_lap": order_date,
            "loi_dan": instructions,
            "ds_thuoc": prepared_lines,
        }
        self._refresh_visit_totals(visit)
        order = self._public_order(visit)
        if order is None:
            raise AppError("LOI_HE_THONG", "Không tạo được đơn demo.")
        return order

    def delete_order(self, visit_id: int, order_id: int) -> None:
        visit = self.visits.get(visit_id)
        if visit is None or visit["don_thuoc"] is None:
            raise AppError("KHONG_TIM_THAY", "Không tìm thấy đơn thuốc demo.")
        order = visit["don_thuoc"]
        if order["ma_don"] != order_id:
            raise AppError("KHONG_TIM_THAY", "Mã đơn không thuộc phiếu khám demo.")
        for line in order["ds_thuoc"]:
            self.medicines[line["ma_thuoc"]]["so_luong_co_san"] += line["so_luong_ke"]
        visit["don_thuoc"] = None
        self._refresh_visit_totals(visit)


_demo_data: DemoClinicData | None = None


def enable_demo_mode() -> None:
    global _demo_data
    _demo_data = DemoClinicData()


def disable_demo_mode() -> None:
    global _demo_data
    _demo_data = None


def is_demo_mode() -> bool:
    return _demo_data is not None


def demo_data() -> DemoClinicData:
    if _demo_data is None:
        raise RuntimeError("Demo mode has not been enabled.")
    return _demo_data
