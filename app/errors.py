from __future__ import annotations

from typing import Any

import mysql.connector


class AppError(Exception):
    def __init__(self, code: str, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.field = field


def app_error_from_database(
    error: mysql.connector.Error, statement: str | None = None
) -> AppError:
    errno = getattr(error, "errno", None)
    message = str(getattr(error, "msg", error))

    if errno in (1205, 1213):
        return AppError(
            "XUNG_DOT_DU_LIEU",
            "Dữ liệu đang được thao tác ở nơi khác. Hãy tải lại và thử lại toàn bộ.",
        )
    if errno == 1062:
        normalized_message = message.lower()
        if (
            "maphieukhambenh" in normalized_message
            or "uq_donthuoc_phieu" in normalized_message
        ):
            return AppError(
                "DA_CO_DON_THUOC",
                "Phiếu khám này đã có đơn thuốc. Hãy tải lại dữ liệu.",
            )
        if statement and "INSERT INTO DonThuoc" in statement:
            return AppError("TRUNG_MA", "Mã đơn thuốc đã được sử dụng.")
        if statement and "INSERT INTO ChiTietDonThuoc" in statement:
            return AppError(
                "DU_LIEU_KHONG_HOP_LE",
                "Thuốc bị trùng trong đơn. Hãy tải lại dữ liệu đơn thuốc.",
                "ds_thuoc",
            )
        return AppError(
            "DU_LIEU_KHONG_HOP_LE",
            "Một khóa dữ liệu bị trùng. Hãy tải lại dữ liệu trước khi thử lại.",
        )
    if errno == 1452:
        return AppError(
            "DU_LIEU_KHONG_HOP_LE",
            "Dữ liệu tham chiếu không còn hợp lệ. Hãy tải lại dữ liệu.",
        )
    if errno in (1044, 1045, 1049, 2002, 2003, 2005, 2006, 2013, 2055):
        return AppError(
            "LOI_KET_NOI",
            "Không kết nối được MySQL. Hãy kiểm tra MySQL và config.ini.",
        )
    if errno == 1451:
        return AppError(
            "DU_LIEU_DANG_DUOC_SU_DUNG",
            "Dữ liệu đang được liên kết với bản ghi khác.",
        )
    return AppError("LOI_HE_THONG", "Không thể hoàn thành thao tác với CSDL.")


def require_positive_int(value: Any, field: str, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise AppError(
            "DU_LIEU_KHONG_HOP_LE",
            f"{label} phải là số nguyên dương.",
            field,
        )
    return value


def require_identifier(value: Any, field: str, label: str) -> str | int:
    if isinstance(value, bool) or not (
        isinstance(value, int) and value > 0
        or isinstance(value, str) and value.strip()
    ):
        raise AppError(
            "DU_LIEU_KHONG_HOP_LE",
            f"{label} không hợp lệ.",
            field,
        )
    return value.strip() if isinstance(value, str) else value
