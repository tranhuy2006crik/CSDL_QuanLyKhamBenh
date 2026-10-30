from contextlib import contextmanager
from typing import Iterator

import mysql.connector
from mysql.connector.connection import MySQLConnection
from mysql.connector.cursor import MySQLCursorDict

from app.config import DatabaseConfig


def connect(config: DatabaseConfig | None = None) -> MySQLConnection:
    settings = config or DatabaseConfig.from_environment()
    return mysql.connector.connect(
        host=settings.host,
        port=settings.port,
        user=settings.user,
        password=settings.password,
        database=settings.database,
    )


@contextmanager
def transaction(
    config: DatabaseConfig | None = None,
) -> Iterator[MySQLCursorDict]:
    connection = connect(config)
    cursor: MySQLCursorDict | None = None
    try:
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)
        yield cursor
        connection.commit()
    except Exception:
        if connection.is_connected():
            connection.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()
