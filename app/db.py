import logging

import mysql.connector
from mysql.connector.connection import MySQLConnection

from app.config import DatabaseConfig
from app.errors import AppError, app_error_from_database


logger = logging.getLogger(__name__)


def get_connection() -> MySQLConnection:
    try:
        settings = DatabaseConfig.from_file()
    except ValueError as error:
        raise AppError("LOI_KET_NOI", str(error)) from error

    try:
        return mysql.connector.connect(
            host=settings.host,
            port=settings.port,
            database=settings.database,
            user=settings.user,
            password=settings.password,
            charset="utf8mb4",
            time_zone="+07:00",
            connection_timeout=5,
            use_pure=True,
            autocommit=True,
        )
    except mysql.connector.Error as error:
        logger.exception("Could not connect to MySQL")
        raise app_error_from_database(error) from error
