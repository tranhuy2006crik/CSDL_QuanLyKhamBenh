import copy
import unittest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch

from app.errors import AppError
from app.services import don_thuoc_service as service


class FakeCursor:
    def __init__(self, connection: "FakeConnection") -> None:
        self.connection = connection
        self.result_one = None
        self.result_all = []
        self.rowcount = 0
        self.closed = False

    def execute(self, sql, params) -> None:
        state = self.connection.state
        self.result_one = None
        self.result_all = []
        self.rowcount = 0

        if sql == service.Q_LOCK_PHIEU:
            self.result_one = state["appointments"].get(params["ma_phieu"])
        elif sql == service.Q_LOCK_DON_THEO_PHIEU:
            self.result_all = [
                order
                for order in state["orders"].values()
                if order["ma_phieu"] == params["ma_phieu"]
            ]
            self.result_one = self.result_all[0] if self.result_all else None
        elif sql == service.Q_LOCK_DON_THEO_MA:
            self.result_one = state["orders"].get(params["ma_don"])
        elif sql == service.Q_LOCK_CHI_TIET:
            self.result_all = list(
                state["details"].get(params["ma_don"], {}).values()
            )
        elif sql == service.Q_LOCK_THUOC:
            self.result_one = state["medicines"].get(params["ma_thuoc"])
        elif sql == service.Q_INSERT_DON:
            order_id = params["ma_don"]
            if order_id in state["orders"]:
                raise RuntimeError("duplicate order id")
            state["orders"][order_id] = {
                "ma_don": order_id,
                "ma_phieu": params["ma_phieu"],
                "ngay_lap": params["ngay_lap"],
                "loi_dan": params["loi_dan"],
            }
            state["details"][order_id] = {}
            self.rowcount = 1
        elif sql == service.Q_UPDATE_DON:
            order = state["orders"][params["ma_don"]]
            order["ngay_lap"] = params["ngay_lap"]
            order["loi_dan"] = params["loi_dan"]
            self.rowcount = 1
        elif sql == service.Q_DELETE_CHI_TIET:
            state["details"][params["ma_don"]] = {}
            self.rowcount = 1
        elif sql == service.Q_INSERT_CHI_TIET:
            order_lines = state["details"][params["ma_don"]]
            medicine_id = params["ma_thuoc"]
            if medicine_id in order_lines:
                raise RuntimeError("duplicate medicine in order")
            order_lines[medicine_id] = {
                "ma_thuoc": medicine_id,
                "so_luong_ke": params["so_luong_ke"],
                "cach_dung": params["cach_dung"],
                "don_gia_ap_dung": params["don_gia"],
            }
            self.rowcount = 1
        elif sql == service.Q_TRU_TON:
            medicine = state["medicines"][params["ma_thuoc"]]
            quantity = params["so_luong"]
            if medicine["so_luong_co_san"] >= quantity:
                medicine["so_luong_co_san"] -= quantity
                self.rowcount = 1
                self.connection.stock_updates += 1
                if self.connection.fail_after_stock_update == self.connection.stock_updates:
                    raise RuntimeError("injected SQL failure after stock update")
        elif sql == service.Q_HOAN_TON:
            medicine = state["medicines"][params["ma_thuoc"]]
            quantity = params["so_luong"]
            if medicine["so_luong_co_san"] <= params["ton_toi_da"] - quantity:
                medicine["so_luong_co_san"] += quantity
                self.rowcount = 1
        elif sql == service.Q_DELETE_DON:
            order_id = params["ma_don"]
            order = state["orders"].get(order_id)
            if order and order["ma_phieu"] == params["ma_phieu"]:
                del state["orders"][order_id]
                state["details"].pop(order_id, None)
                self.rowcount = 1
        else:
            raise AssertionError(f"Unexpected SQL: {sql}")

    def fetchone(self):
        return copy.deepcopy(self.result_one)

    def fetchall(self):
        return copy.deepcopy(self.result_all)

    def close(self) -> None:
        self.closed = True


class FakeConnection:
    def __init__(
        self,
        state: dict,
        fail_after_stock_update: int | None = None,
        fail_commit: bool = False,
    ) -> None:
        self.state = state
        self.snapshot = None
        self.fail_after_stock_update = fail_after_stock_update
        self.fail_commit = fail_commit
        self.stock_updates = 0
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def start_transaction(self) -> None:
        self.snapshot = copy.deepcopy(self.state)

    def cursor(self, dictionary: bool = False) -> FakeCursor:
        if not dictionary:
            raise AssertionError("Expected dictionary cursor")
        return FakeCursor(self)

    def commit(self) -> None:
        if self.fail_commit:
            raise RuntimeError("injected commit outcome error")
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1
        self.state.clear()
        self.state.update(copy.deepcopy(self.snapshot))

    def close(self) -> None:
        self.closed = True


def create_state() -> dict:
    return {
        "appointments": {
            1: {"ngay_gio_kham": datetime(2026, 10, 30, 9, 0)}
        },
        "orders": {},
        "details": {},
        "medicines": {
            1: {
                "ma_thuoc": 1,
                "ten_thuoc": "Thuốc A",
                "don_vi_tinh": "viên",
                "don_gia": Decimal("10000.00"),
                "so_luong_co_san": 10,
            },
            2: {
                "ma_thuoc": 2,
                "ten_thuoc": "Thuốc B",
                "don_vi_tinh": "viên",
                "don_gia": Decimal("20000.00"),
                "so_luong_co_san": 8,
            },
        },
    }


def read_order(state: dict, appointment_id: int):
    order = next(
        (
            row
            for row in state["orders"].values()
            if row["ma_phieu"] == appointment_id
        ),
        None,
    )
    if order is None:
        return None
    details = []
    total = Decimal("0")
    for line in state["details"][order["ma_don"]].values():
        medicine = state["medicines"][line["ma_thuoc"]]
        line_total = line["don_gia_ap_dung"] * line["so_luong_ke"]
        total += line_total
        details.append(
            {
                **line,
                "ten_thuoc": medicine["ten_thuoc"],
                "don_vi_tinh": medicine["don_vi_tinh"],
                "thanh_tien": line_total,
            }
        )
    return {
        **order,
        "ds_thuoc": details,
        "gia_don": total,
    }


class PrescriptionServiceTests(unittest.TestCase):
    def run_save(
        self,
        state: dict,
        connection: FakeConnection,
        *,
        ma_don: int,
        quantity: int,
        tao_moi: bool,
    ):
        with (
            patch.object(service, "get_connection", return_value=connection),
            patch.object(
                service,
                "lay_don_thuoc",
                side_effect=lambda appointment_id: read_order(state, appointment_id),
            ),
        ):
            return service.luu_don_thuoc(
                ma_phieu=1,
                ma_don=ma_don,
                ngay_lap=date(2026, 10, 30),
                loi_dan=None,
                ds_thuoc=[
                    {
                        "ma_thuoc": 1,
                        "so_luong_ke": quantity,
                        "cach_dung": "Ngày 2 lần",
                    }
                ],
                tao_moi=tao_moi,
            )

    def test_create_saves_order_and_decreases_inventory_once(self) -> None:
        state = create_state()
        connection = FakeConnection(state)

        order = self.run_save(
            state, connection, ma_don=10, quantity=3, tao_moi=True
        )

        self.assertEqual(state["medicines"][1]["so_luong_co_san"], 7)
        self.assertEqual(
            state["details"][10][1]["don_gia_ap_dung"], Decimal("10000.00")
        )
        self.assertEqual(order["gia_don"], Decimal("30000.00"))
        self.assertEqual(connection.commits, 1)
        self.assertEqual(connection.rollbacks, 0)
        self.assertTrue(connection.closed)

    def test_insufficient_inventory_rolls_back_without_partial_order(self) -> None:
        state = create_state()
        state["medicines"][1]["so_luong_co_san"] = 2
        connection = FakeConnection(state)

        with self.assertRaises(AppError) as raised:
            self.run_save(state, connection, ma_don=10, quantity=3, tao_moi=True)

        self.assertEqual(raised.exception.code, "KHONG_DU_TON")
        self.assertIn("cần trừ thêm 3", raised.exception.message)
        self.assertEqual(state["medicines"][1]["so_luong_co_san"], 2)
        self.assertNotIn(10, state["orders"])
        self.assertEqual(connection.commits, 0)
        self.assertEqual(connection.rollbacks, 1)

    def test_edit_decreases_only_delta_and_keeps_historical_price(self) -> None:
        state = create_state()
        state["medicines"][1]["so_luong_co_san"] = 2
        state["medicines"][1]["don_gia"] = Decimal("15000.00")
        state["orders"][10] = {
            "ma_don": 10,
            "ma_phieu": 1,
            "ngay_lap": date(2026, 10, 30),
            "loi_dan": None,
        }
        state["details"][10] = {
            1: {
                "ma_thuoc": 1,
                "so_luong_ke": 3,
                "cach_dung": "Cách cũ",
                "don_gia_ap_dung": Decimal("10000.00"),
            }
        }
        connection = FakeConnection(state)

        order = self.run_save(
            state, connection, ma_don=10, quantity=5, tao_moi=False
        )

        self.assertEqual(state["medicines"][1]["so_luong_co_san"], 0)
        self.assertEqual(state["details"][10][1]["so_luong_ke"], 5)
        self.assertEqual(
            state["details"][10][1]["don_gia_ap_dung"], Decimal("10000.00")
        )
        self.assertEqual(order["gia_don"], Decimal("50000.00"))

    def test_edit_refunds_only_reduced_quantity(self) -> None:
        state = create_state()
        state["medicines"][1]["so_luong_co_san"] = 7
        state["orders"][10] = {
            "ma_don": 10,
            "ma_phieu": 1,
            "ngay_lap": date(2026, 10, 30),
            "loi_dan": None,
        }
        state["details"][10] = {
            1: {
                "ma_thuoc": 1,
                "so_luong_ke": 3,
                "cach_dung": "Cách cũ",
                "don_gia_ap_dung": Decimal("10000.00"),
            }
        }
        connection = FakeConnection(state)

        self.run_save(state, connection, ma_don=10, quantity=1, tao_moi=False)

        self.assertEqual(state["medicines"][1]["so_luong_co_san"], 9)
        self.assertEqual(state["details"][10][1]["so_luong_ke"], 1)

    def test_delete_refunds_once_and_second_delete_does_not_change_stock(self) -> None:
        state = create_state()
        state["medicines"][1]["so_luong_co_san"] = 7
        state["orders"][10] = {
            "ma_don": 10,
            "ma_phieu": 1,
            "ngay_lap": date(2026, 10, 30),
            "loi_dan": None,
        }
        state["details"][10] = {
            1: {
                "ma_thuoc": 1,
                "so_luong_ke": 3,
                "cach_dung": "Ngày 2 lần",
                "don_gia_ap_dung": Decimal("10000.00"),
            }
        }
        first_connection = FakeConnection(state)

        with patch.object(
            service, "get_connection", return_value=first_connection
        ):
            result = service.xoa_don_thuoc(ma_phieu=1, ma_don=10)

        self.assertIsNone(result)
        self.assertEqual(state["medicines"][1]["so_luong_co_san"], 10)
        self.assertNotIn(10, state["orders"])
        self.assertEqual(first_connection.commits, 1)

        second_connection = FakeConnection(state)
        with patch.object(
            service, "get_connection", return_value=second_connection
        ):
            with self.assertRaises(AppError) as raised:
                service.xoa_don_thuoc(ma_phieu=1, ma_don=10)

        self.assertEqual(raised.exception.code, "KHONG_TIM_THAY")
        self.assertEqual(state["medicines"][1]["so_luong_co_san"], 10)
        self.assertEqual(second_connection.rollbacks, 1)

    def test_unexpected_error_after_stock_update_rolls_back_everything(self) -> None:
        state = create_state()
        connection = FakeConnection(state, fail_after_stock_update=1)

        with self.assertLogs("app.services.don_thuoc_service", level="ERROR"):
            with self.assertRaises(AppError) as raised:
                self.run_save(
                    state, connection, ma_don=10, quantity=3, tao_moi=True
                )

        self.assertEqual(raised.exception.code, "LOI_HE_THONG")
        self.assertEqual(state["medicines"][1]["so_luong_co_san"], 10)
        self.assertNotIn(10, state["orders"])
        self.assertEqual(connection.commits, 0)
        self.assertEqual(connection.rollbacks, 1)

    def test_commit_error_is_reported_as_uncertain_without_rollback_claim(self) -> None:
        state = create_state()
        connection = FakeConnection(state, fail_commit=True)

        with self.assertLogs("app.services.don_thuoc_service", level="ERROR"):
            with self.assertRaises(AppError) as raised:
                self.run_save(
                    state, connection, ma_don=10, quantity=3, tao_moi=True
                )

        self.assertEqual(raised.exception.code, "COMMIT_CHUA_XAC_DINH")
        self.assertEqual(connection.rollbacks, 0)
        self.assertEqual(state["medicines"][1]["so_luong_co_san"], 7)
        self.assertIn(10, state["orders"])

    def test_post_commit_refresh_error_does_not_repeat_write(self) -> None:
        state = create_state()
        connection = FakeConnection(state)
        with (
            patch.object(service, "get_connection", return_value=connection),
            patch.object(
                service,
                "lay_don_thuoc",
                side_effect=AppError("LOI_KET_NOI", "database disconnected"),
            ),
            self.assertRaises(AppError) as raised,
        ):
            service.luu_don_thuoc(
                ma_phieu=1,
                ma_don=10,
                ngay_lap=date(2026, 10, 30),
                loi_dan=None,
                ds_thuoc=[
                    {
                        "ma_thuoc": 1,
                        "so_luong_ke": 3,
                        "cach_dung": "Ngày 2 lần",
                    }
                ],
                tao_moi=True,
            )

        self.assertEqual(raised.exception.code, "DA_LUU_CAN_TAI_LAI")
        self.assertEqual(connection.commits, 1)
        self.assertEqual(connection.rollbacks, 0)
        self.assertEqual(state["medicines"][1]["so_luong_co_san"], 7)

    def test_rejects_empty_order_before_opening_connection(self) -> None:
        with patch.object(service, "get_connection") as get_connection:
            with self.assertRaises(AppError) as raised:
                service.luu_don_thuoc(
                    ma_phieu=1,
                    ma_don=10,
                    ngay_lap=date(2026, 10, 30),
                    loi_dan=None,
                    ds_thuoc=[],
                    tao_moi=True,
                )

        self.assertEqual(raised.exception.code, "DU_LIEU_KHONG_HOP_LE")
        get_connection.assert_not_called()


if __name__ == "__main__":
    unittest.main()
