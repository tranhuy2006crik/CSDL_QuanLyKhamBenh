from tkinter import ttk


class PlaceholderView(ttk.Frame):
    def __init__(self, master: ttk.Frame, title: str) -> None:
        super().__init__(master)
        self.columnconfigure(0, weight=1)

        ttk.Label(self, text=title, font=("TkDefaultFont", 18, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 12)
        )
        ttk.Label(
            self,
            text="Khung giao diện đã sẵn sàng. Màn hình nghiệp vụ sẽ được bổ sung.",
            wraplength=700,
        ).grid(row=1, column=0, sticky="w")
