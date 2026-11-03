from app.db import get_connection
from app.errors import app_error_from_database
from app.read_queries import Q_TIM_BENH_NHAN


def tim_kiem_benh_nhan(tu_khoa="", ma_khoa=None, ma_bac_si=None):
    connection = get_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        mau_tim = f"%{tu_khoa.strip()}%" if tu_khoa else ""

        params = {
            "tu_khoa": tu_khoa.strip(),
            "mau_tim": mau_tim,
            "ma_khoa": ma_khoa,
            "ma_bac_si": ma_bac_si,
        }

        cursor.execute(Q_TIM_BENH_NHAN, params)
        return cursor.fetchall()
    except Exception as e:
        raise app_error_from_database(e) from e
    finally:
        if cursor:
            cursor.close()
        connection.close()
