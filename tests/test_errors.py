import unittest

import mysql.connector

from app.errors import app_error_from_database
from app.services.don_thuoc_service import Q_INSERT_DON


class DatabaseErrorMappingTests(unittest.TestCase):
    def test_duplicate_order_id_is_trung_ma(self) -> None:
        error = mysql.connector.Error(
            msg="Duplicate entry '12' for key 'PRIMARY'", errno=1062
        )

        mapped = app_error_from_database(error, Q_INSERT_DON)

        self.assertEqual(mapped.code, "TRUNG_MA")

    def test_duplicate_prescription_per_appointment_is_specific(self) -> None:
        error = mysql.connector.Error(
            msg="Duplicate entry '8' for key 'uq_DonThuoc_MaPhieuKhamBenh'",
            errno=1062,
        )

        mapped = app_error_from_database(error, Q_INSERT_DON)

        self.assertEqual(mapped.code, "DA_CO_DON_THUOC")

    def test_unknown_duplicate_is_not_reported_as_duplicate_order(self) -> None:
        error = mysql.connector.Error(
            msg="Duplicate entry '8' for key 'some_other_unique_key'",
            errno=1062,
        )

        mapped = app_error_from_database(error)

        self.assertEqual(mapped.code, "DU_LIEU_KHONG_HOP_LE")


if __name__ == "__main__":
    unittest.main()
