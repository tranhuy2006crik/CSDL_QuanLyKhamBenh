import unittest

from app.ui.app import ClinicApp


class ClinicShellTests(unittest.TestCase):
    def test_application_creates_one_window_with_five_workflow_tabs(self) -> None:
        app = ClinicApp()
        try:
            self.assertEqual(len(app.shell.notebook.tabs()), 5)
            self.assertEqual(
                app.shell.notebook.tab(app.shell.notebook.tabs()[0], "text"),
                "Xét nghiệm",
            )
            self.assertEqual(
                app.shell.notebook.tab(app.shell.notebook.tabs()[1], "text"),
                "Kê đơn thuốc",
            )
        finally:
            app.destroy()


if __name__ == "__main__":
    unittest.main()
