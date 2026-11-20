import argparse

from app.ui.app import ClinicApp


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Hệ thống quản lý khám bệnh ngoại trú")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Chạy dữ liệu minh họa trong bộ nhớ, không kết nối MySQL",
    )
    args = parser.parse_args(argv)
    app = ClinicApp(demo_mode=args.demo)
    app.mainloop()


if __name__ == "__main__":
    main()
