import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: int
    user: str
    password: str
    database: str

    @classmethod
    def from_environment(cls) -> "DatabaseConfig":
        try:
            port = int(os.getenv("DB_PORT", "3306"))
        except ValueError as error:
            raise ValueError("DB_PORT must be an integer.") from error

        if not 1 <= port <= 65535:
            raise ValueError("DB_PORT must be between 1 and 65535.")

        return cls(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            port=port,
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "quanlykhambenh"),
        )
