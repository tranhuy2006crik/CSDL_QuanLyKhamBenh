import tkinter as tk
from tkinter import ttk


def configure_styles(root: tk.Misc) -> None:
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")

    background = "#F4F7FA"
    style.configure(".", font=("Segoe UI", 10), background=background)
    style.configure("TFrame", background=background)
    style.configure("TLabel", background=background, foreground="#243746")
    style.configure("TNotebook", background=background)
    style.configure(
        "TNotebook.Tab",
        padding=(8, 4),
        font=("Segoe UI", 9),
        foreground="#243746",
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", "#FFFFFF"), ("active", "#E2EAF1")],
        foreground=[("selected", "#183B56"), ("active", "#183B56")],
    )
    style.configure("Main.TNotebook", background=background)
    style.configure(
        "Main.TNotebook.Tab",
        padding=(14, 7),
        font=("Segoe UI", 10, "bold"),
        foreground="#243746",
    )
    style.map(
        "Main.TNotebook.Tab",
        background=[("selected", "#FFFFFF"), ("active", "#E2EAF1")],
        foreground=[("selected", "#183B56"), ("active", "#183B56")],
    )
    style.configure(
        "SummaryHeading.TLabel",
        background=background,
        foreground="#526574",
        font=("Segoe UI", 9, "bold"),
    )
    style.configure(
        "SummaryValue.TLabel",
        background=background,
        foreground="#1677A5",
        font=("Segoe UI", 17, "bold"),
    )
    style.configure(
        "HistoryValue.TLabel",
        background=background,
        foreground="#243746",
        font=("Segoe UI", 11),
    )
    style.configure(
        "TLabelframe",
        background=background,
        bordercolor="#CCD6E0",
    )
    style.configure(
        "TLabelframe.Label",
        background=background,
        foreground="#183B56",
        font=("Segoe UI", 10, "bold"),
    )
    style.configure(
        "TButton",
        padding=(10, 6),
        background="#E2EAF1",
        foreground="#243746",
        bordercolor="#C5D1DC",
    )
    style.map(
        "TButton",
        background=[
            ("disabled", "#E9EDF1"),
            ("pressed", "#C7D5E1"),
            ("active", "#D2DFE9"),
        ],
        foreground=[("disabled", "#8795A1")],
    )
    style.configure(
        "Primary.TButton",
        background="#1677A5",
        foreground="#FFFFFF",
        bordercolor="#12658D",
        font=("Segoe UI", 10, "bold"),
    )
    style.map(
        "Primary.TButton",
        background=[
            ("disabled", "#9DBAC9"),
            ("pressed", "#0D587C"),
            ("active", "#12688F"),
        ],
        foreground=[("disabled", "#F2F5F7")],
    )
    style.configure(
        "Success.TButton",
        background="#2E8B57",
        foreground="#FFFFFF",
        bordercolor="#267448",
        font=("Segoe UI", 10, "bold"),
    )
    style.map(
        "Success.TButton",
        background=[
            ("disabled", "#A9C6B4"),
            ("pressed", "#226C43"),
            ("active", "#277B4D"),
        ],
        foreground=[("disabled", "#F2F5F7")],
    )
    style.configure(
        "Danger.TButton",
        background="#C0392B",
        foreground="#FFFFFF",
        bordercolor="#A93226",
        font=("Segoe UI", 10, "bold"),
    )
    style.map(
        "Danger.TButton",
        background=[
            ("disabled", "#D7ABA6"),
            ("pressed", "#922B21"),
            ("active", "#A93226"),
        ],
        foreground=[("disabled", "#F2F5F7")],
    )
    style.configure(
        "Info.TButton",
        background="#E7A23B",
        foreground="#243746",
        bordercolor="#C9892C",
    )
    style.map(
        "Info.TButton",
        background=[("pressed", "#C9892C"), ("active", "#D99632")],
    )
    style.configure(
        "Secondary.TButton",
        background="#586B7A",
        foreground="#FFFFFF",
        bordercolor="#465663",
    )
    style.map(
        "Secondary.TButton",
        background=[
            ("disabled", "#B6C0C7"),
            ("pressed", "#3F4E59"),
            ("active", "#4A5B68"),
        ],
        foreground=[("disabled", "#F2F5F7")],
    )
    style.configure(
        "SlotAvailable.TButton",
        padding=(8, 8),
        background="#E7F5EC",
        foreground="#246B43",
        bordercolor="#B7DEC5",
        font=("Segoe UI", 10, "bold"),
    )
    style.map(
        "SlotAvailable.TButton",
        background=[("active", "#D5EEDC"), ("pressed", "#C5E5D0")],
    )
    style.configure(
        "SlotSelected.TButton",
        padding=(8, 8),
        background="#1677A5",
        foreground="#FFFFFF",
        bordercolor="#12658D",
        font=("Segoe UI", 10, "bold"),
    )
    style.map(
        "SlotSelected.TButton",
        background=[("active", "#12688F"), ("pressed", "#0D587C")],
    )
    style.configure(
        "SlotUnavailable.TButton",
        padding=(8, 8),
        background="#F1F3F5",
        foreground="#818C96",
        bordercolor="#D9DEE3",
    )
    style.configure(
        "SlotPast.TButton",
        padding=(8, 8),
        background="#F8F1E6",
        foreground="#8A6D3B",
        bordercolor="#E9D8B8",
    )
    style.configure(
        "Treeview",
        background="#FFFFFF",
        fieldbackground="#FFFFFF",
        foreground="#243746",
        rowheight=27,
    )
    style.configure(
        "Treeview.Heading",
        background="#E2EAF1",
        foreground="#183B56",
        font=("Segoe UI", 10, "bold"),
    )
    root.configure(background=background)
