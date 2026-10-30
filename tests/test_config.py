import os
import unittest
from unittest.mock import patch

from app.config import DatabaseConfig


class DatabaseConfigTests(unittest.TestCase):
    def test_reads_database_settings_from_environment(self) -> None:
        environment = {
            "DB_HOST": "db.example",
            "DB_PORT": "3307",
            "DB_USER": "clinic",
            "DB_PASSWORD": "local-secret",
            "DB_NAME": "clinic_test",
        }
        with patch.dict(os.environ, environment, clear=True):
            config = DatabaseConfig.from_environment()

        self.assertEqual(config.host, "db.example")
        self.assertEqual(config.port, 3307)
        self.assertEqual(config.user, "clinic")
        self.assertEqual(config.password, "local-secret")
        self.assertEqual(config.database, "clinic_test")

    def test_rejects_non_integer_port(self) -> None:
        with patch.dict(os.environ, {"DB_PORT": "invalid"}, clear=True):
            with self.assertRaisesRegex(ValueError, "DB_PORT must be an integer"):
                DatabaseConfig.from_environment()

    def test_rejects_port_outside_tcp_range(self) -> None:
        with patch.dict(os.environ, {"DB_PORT": "70000"}, clear=True):
            with self.assertRaisesRegex(ValueError, "between 1 and 65535"):
                DatabaseConfig.from_environment()


if __name__ == "__main__":
    unittest.main()
