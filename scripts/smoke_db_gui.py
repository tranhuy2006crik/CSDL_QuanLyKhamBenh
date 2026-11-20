import configparser
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

import mysql.connector


def main() -> None:
    root = tk.Tk()
    root.title("CSDL-01 - Thử Tkinter đọc MySQL")
    root.geometry("700x300")
    status = tk.StringVar(value="Chưa kiểm tra")
    ttk.Label(root, textvariable=status, wraplength=670).pack(padx=12, pady=12)
    tree = ttk.Treeview(root, columns=("ma", "ten"), show="headings")
    tree.heading("ma", text="Mã khoa")
    tree.heading("ten", text="Tên khoa")
    tree.pack(fill="both", expand=True, padx=12, pady=6)

    def kiem_tra() -> None:
        try:
            config = configparser.ConfigParser(interpolation=None)
            config_path = Path(__file__).resolve().parents[1] / "config.ini"
            if not config.read(config_path, encoding="utf-8-sig"):
                raise ValueError("Chưa có config.ini ở thư mục gốc.")
            database = config["mysql"]
            connection = mysql.connector.connect(
                host=database["host"],
                port=database.getint("port", fallback=3306),
                database=database["database"],
                user=database["user"],
                password=database["password"],
                charset="utf8mb4",
                time_zone="+07:00",
                connection_timeout=5,
                use_pure=True,
                autocommit=True,
            )
            try:
                cursor = connection.cursor(dictionary=True)
                try:
                    cursor.execute(
                        "SELECT VERSION() AS phien_ban, DATABASE() AS csdl"
                    )
                    info = cursor.fetchone()
                    cursor.execute(
                        "SELECT MaKhoa, TenKhoa FROM Khoa "
                        "ORDER BY MaKhoa LIMIT 3"
                    )
                    rows = cursor.fetchall()
                finally:
                    cursor.close()
            finally:
                connection.close()

            if not rows:
                raise ValueError("Đọc được Khoa nhưng chưa có dữ liệu mẫu.")
            for item in tree.get_children():
                tree.delete(item)
            for row in rows:
                tree.insert("", "end", values=(row["MaKhoa"], row["TenKhoa"]))
            status.set(
                f"Kết nối thành công: MySQL {info['phien_ban']}; "
                f"CSDL {info['csdl']}; đọc {len(rows)} dòng Khoa"
            )
        except (mysql.connector.Error, OSError, KeyError, ValueError) as error:
            status.set("Kiểm tra thất bại")
            messagebox.showerror("CSDL-01", str(error), parent=root)

    ttk.Button(root, text="Đọc lại MySQL", command=kiem_tra).pack(pady=8)
    root.after(100, kiem_tra)
    root.mainloop()


if __name__ == "__main__":
    main()
