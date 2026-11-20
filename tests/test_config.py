import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.config import DatabaseConfig
from app.db import get_connection


class DatabaseConfigTests(unittest.TestCase):
    def test_reads_config_ini_and_preserves_percent_in_password(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "config.ini"
            path.write_text(
                "[mysql]\n"
                "host = localhost\n"
                "port = 3307\n"
                "database = clinic\n"
                "user = clinic_app\n"
                "password = 50%secure\n",
                encoding="utf-8",
            )
            config = DatabaseConfig.from_file(path)

        self.assertEqual(config.host, "localhost")
        self.assertEqual(config.port, 3307)
        self.assertEqual(config.database, "clinic")
        self.assertEqual(config.user, "clinic_app")
        self.assertEqual(config.password, "50%secure")

    def test_rejects_missing_config_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "missing.ini"
            with self.assertRaisesRegex(ValueError, "Chưa có config.ini"):
                DatabaseConfig.from_file(path)

    def test_rejects_invalid_port(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "config.ini"
            path.write_text(
                "[mysql]\nhost=x\ndatabase=x\nuser=x\npassword=x\nport=70000\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "1 đến 65535"):
                DatabaseConfig.from_file(path)

    def test_connection_uses_shared_mysql_options(self) -> None:
        config = DatabaseConfig(
            host="localhost",
            port=3307,
            database="clinic",
            user="clinic_app",
            password="secret",
        )
        with (
            patch("app.db.DatabaseConfig.from_file", return_value=config),
            patch("app.db.mysql.connector.connect") as connector,
        ):
            get_connection()

        connector.assert_called_once_with(
            host="localhost",
            port=3307,
            database="clinic",
            user="clinic_app",
            password="secret",
            charset="utf8mb4",
            time_zone="+07:00",
            connection_timeout=5,
            use_pure=True,
            autocommit=True,
        )


if __name__ == "__main__":
    unittest.main()
