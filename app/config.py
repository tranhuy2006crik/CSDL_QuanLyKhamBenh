import configparser
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config.ini"


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: int
    database: str
    user: str
    password: str

    @classmethod
    def from_file(cls, path: Path = CONFIG_PATH) -> "DatabaseConfig":
        parser = configparser.ConfigParser(interpolation=None)
        try:
            loaded_files = parser.read(path, encoding="utf-8-sig")
        except OSError as error:
            raise ValueError(f"Không đọc được cấu hình MySQL: {path}") from error

        if not loaded_files:
            raise ValueError(
                f"Chưa có config.ini. Sao chép config.example.ini thành {path.name}."
            )
        if "mysql" not in parser:
            raise ValueError("config.ini phải có mục [mysql].")

        section = parser["mysql"]
        required = ("host", "database", "user", "password")
        missing = [key for key in required if key not in section]
        if missing:
            raise ValueError(
                "Thiếu cấu hình MySQL bắt buộc: " + ", ".join(missing)
            )

        try:
            port = section.getint("port", fallback=3306)
        except ValueError as error:
            raise ValueError("mysql.port phải là số nguyên.") from error
        if not 1 <= port <= 65535:
            raise ValueError("mysql.port phải nằm trong khoảng 1 đến 65535.")

        values = {key: section.get(key, "").strip() for key in required}
        if any(not values[key] for key in ("host", "database", "user")):
            raise ValueError("mysql.host, mysql.database và mysql.user không được rỗng.")

        return cls(
            host=values["host"],
            port=port,
            database=values["database"],
            user=values["user"],
            password=section.get("password", raw=True),
        )
