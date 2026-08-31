"""
Teams Mirror - a small local desktop-app stand-in for Microsoft Teams, just
deep enough to replay navigating to a specific shared file: Renewals ->
2026 Renewals -> APC 2026 RENEWALS.xlsx.

Purpose: give an RPA automation (Robot Framework + RPA.Desktop) something
real to click through for this one recorded navigation, without needing a
real Teams tenant. Opening the actual Excel file is a separate step in the
automation (via the existing Excel Mirror app) - this app only mirrors the
3-click Teams navigation itself.

All data here is fictitious.

Launch:
    ~/rpa-env/bin/python main.py
"""
import tkinter as tk
from tkinter import font as tkfont

WINDOW_TITLE = "Renewals | Microsoft Teams"
GEOMETRY = "420x420+150+120"

TEAMS_PURPLE = "#464775"
PANEL_BG = "#FFFFFF"
TEXT = "#242424"
TEXT_SECONDARY = "#616161"
BORDER = "#E1DFDD"
HOVER = "#F5F5F5"


def pick_font(root, *candidates, size=12, weight="normal"):
    available = set(tkfont.families(root))
    for name in candidates:
        if name in available:
            return tkfont.Font(family=name, size=size, weight=weight)
    return tkfont.Font(size=size, weight=weight)


class ClickableRow(tk.Label):
    """See outlook_mirror's ColorButton docstring - tk.Button's bg is
    silently ignored by macOS Aqua, a bound Label works on every platform."""

    def __init__(self, master, text, command, font, **kw):
        super().__init__(master, text=text, fg=TEXT, bg=PANEL_BG, font=font,
                          anchor="w", padx=14, pady=10, cursor="hand2", **kw)
        self._command = command
        self.bind("<Button-1>", lambda _e: command())
        self.bind("<Enter>", lambda _e: self.config(bg=HOVER))
        self.bind("<Leave>", lambda _e: self.config(bg=PANEL_BG))


class TeamsApp:
    def __init__(self, root):
        self.root = root
        root.title(WINDOW_TITLE)
        root.geometry(GEOMETRY)
        root.configure(bg=PANEL_BG)

        self.title_font = pick_font(root, "Segoe UI Semibold", "Segoe UI", "SF Pro Text", size=15, weight="bold")
        self.row_font = pick_font(root, "Segoe UI", "SF Pro Text", size=12)

        self.header = tk.Frame(root, bg=TEAMS_PURPLE, height=48)
        self.header.pack(fill="x")
        self.header_label = tk.Label(self.header, text="Teams", fg="#FFFFFF", bg=TEAMS_PURPLE,
                                      font=self.title_font, padx=16)
        self.header_label.pack(side="left", pady=10)

        self.body = tk.Frame(root, bg=PANEL_BG)
        self.body.pack(fill="both", expand=True)

        self.render_root()

    def clear_body(self):
        for w in self.body.winfo_children():
            w.destroy()

    def render_root(self):
        self.clear_body()
        self.header_label.config(text="Teams")
        ClickableRow(self.body, "\U0001F4C1 Renewals", self.render_renewals,
                     self.row_font).pack(fill="x")

    def render_renewals(self):
        self.clear_body()
        self.header_label.config(text="Renewals")
        ClickableRow(self.body, "\U0001F4C1 2026 Renewals", self.render_2026_renewals,
                     self.row_font).pack(fill="x")

    def render_2026_renewals(self):
        self.clear_body()
        self.header_label.config(text="2026 Renewals")
        ClickableRow(self.body, "\U0001F4C4 APC 2026 RENEWALS.xlsx", self.select_apc_file,
                     self.row_font).pack(fill="x")

    def select_apc_file(self):
        self.clear_body()
        self.header_label.config(text="2026 Renewals")
        tk.Label(self.body, text="Opening APC 2026 RENEWALS.xlsx …", fg=TEXT_SECONDARY,
                 bg=PANEL_BG, font=self.row_font, padx=14, pady=14).pack(fill="x")


def main():
    root = tk.Tk()
    TeamsApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
