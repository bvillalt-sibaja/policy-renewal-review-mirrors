"""Excel mirror: a Tkinter app that looks like desktop Excel (Microsoft 365, Windows 11)
and mimics genuine Excel navigation (a Name Box + formula bar) over a real .xlsx
workbook, so an RPA automation drives it the same way a human would - type a cell
reference into the Name Box and press Enter to select it, then type a value into the
formula bar and press Enter to commit - rather than manipulating the file invisibly.

Usage: main.py <path-to-xlsx> [sheet-name]
Every commit is saved to the workbook on disk immediately (openpyxl save per edit -
fine for the small dummy workbooks this mirrors).

Automation contract (keep stable - the .robot clicks fixed client coordinates):
  * window title "<file name> - Excel", geometry GEOMETRY (fixed size + position)
  * Name Box click point: NAME_BOX_CLICK (Tk-logical client coordinates)
  * Name Box <Return> -> select + scroll to the cell, focus moves to the formula bar
  * formula bar <Return> -> write the cell, save the workbook, focus back to Name Box
  * Ctrl+A selects all text in both boxes
The ribbon, title strip, sheet tabs and status bar are decorative (inert).
"""
import os
import re
import sys

import tkinter as tk
from tkinter import font as tkfont

try:
    from openpyxl import load_workbook
    from openpyxl.utils import get_column_letter, column_index_from_string
except ImportError:
    print("excel_mirror: openpyxl is required (pip install openpyxl)", file=sys.stderr)
    sys.exit(1)

GEOMETRY = "1280x760+40+20"
WIN_W, WIN_H = 1280, 760
# Tk-logical client coordinates of the Name Box centre (verified from live widgets).
NAME_BOX_CLICK = (52, 182)

# Layout (client y coordinates)
TITLE_H = 34          # in-window title strip (AutoSave, file name, search)
TABS_H = 30           # ribbon tab names
RIBBON_H = 100        # ribbon body (white rounded panel)
FBAR_H = 36           # Name Box + formula bar row
SHEETBAR_H = 28
STATUS_H = 24

COL_HDR_H = 20
ROW_HDR_W = 36
ROW_H = 20
DEFAULT_COL_W = 64
MAX_AUTO_COL_W = 200
MAX_COLS = 16384

# Colours (Microsoft 365 light theme)
CHROME_BG = "#F3F3F3"
RIBBON_BG = "#FFFFFF"
RIBBON_BORDER = "#E0E0E0"
TEXT = "#242424"
TEXT_SOFT = "#616161"
TEXT_FAINT = "#8A8A8A"
GREEN = "#107C41"
GREEN_DARK = "#0E5C2F"
GRIDLINE = "#E1E1E1"
HDR_BG = "#F5F5F5"
HDR_LINE = "#D4D4D4"
HDR_SEL_BG = "#D3F0E0"
BOX_BORDER = "#C7C7C7"

MDL2 = "Segoe MDL2 Assets"
CELL_REF_RE = re.compile(r"^\$?([A-Za-z]{1,3})\$?([0-9]+)$")


def cell_ref_to_rc(ref):
    m = CELL_REF_RE.match(ref.strip())
    if not m:
        return None
    col_letters, row_str = m.groups()
    return int(row_str), column_index_from_string(col_letters.upper())


def pick_font(root, *candidates, size=11, weight="normal", slant="roman"):
    available = set(tkfont.families(root))
    for name in candidates:
        if name in available:
            return tkfont.Font(root=root, family=name, size=size, weight=weight, slant=slant)
    return tkfont.Font(root=root, size=size, weight=weight, slant=slant)


def rounded_rect(cv, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return cv.create_polygon(pts, smooth=True, **kw)


def excel_icon(root, size=32):
    """Window/taskbar icon: green tile with a white X, drawn pixel by pixel."""
    img = tk.PhotoImage(master=root, width=size, height=size)
    img.put("#185C37", to=(0, 0, size, size))
    img.put("#21A366", to=(size // 2, 0, size, size // 2))
    img.put("#107C41", to=(size // 2, size // 2, size, size))
    m = size // 6
    img.put("#107C41", to=(m - 2, m + 2, size // 2 + 4, size - m - 2))
    lo, hi = m + 5, size - m - 5
    for i in range(lo, hi):
        t = (i - lo) / max(1, (hi - lo - 1))
        x1 = int(m + 2 + t * (size // 2 - m - 2))
        x2 = int(size // 2 + 1 - t * (size // 2 - m - 2))
        for dx in (0, 1, 2):
            img.put("#FFFFFF", to=(x1 + dx, i, x1 + dx + 1, i + 1))
            img.put("#FFFFFF", to=(x2 + dx - 2, i, x2 + dx - 1, i + 1))
    return img


class ExcelMirror:
    def __init__(self, root, path, sheet_name=None):
        self.root = root
        self.path = path
        self.sheet_name = sheet_name
        self.selected = (1, 1)
        self.view_row = 1
        self.view_col = 1
        self.file_name = os.path.basename(path.replace("\\", "/"))

        root.title(f"{self.file_name} - Excel")
        # Fixed size AND position every launch: the automation clicks fixed client
        # coordinates (NAME_BOX_CLICK). Changing the layout above the formula bar
        # moves the Name Box - re-measure and update the .robot if you do.
        root.geometry(GEOMETRY)
        root.resizable(False, False)
        root.configure(bg=CHROME_BG)
        try:
            self._icon = excel_icon(root)
            root.iconphoto(True, self._icon)
        except tk.TclError:
            pass

        self.f_ui = pick_font(root, "Segoe UI", "Helvetica", size=9)
        self.f_ui_s = pick_font(root, "Segoe UI", "Helvetica", size=8)
        self.f_ui_b = pick_font(root, "Segoe UI Semibold", "Segoe UI", "Helvetica", size=9)
        self.f_tab = pick_font(root, "Segoe UI", "Helvetica", size=9)
        self.f_tab_b = pick_font(root, "Segoe UI Semibold", "Segoe UI", "Helvetica", size=9)
        self.f_cell = pick_font(root, "Calibri", "Segoe UI", "Helvetica", size=11)
        self.f_cell_b = pick_font(root, "Calibri", "Segoe UI", "Helvetica", size=11, weight="bold")
        self.f_hdr = pick_font(root, "Calibri", "Segoe UI", "Helvetica", size=11)
        self.f_hdr_b = pick_font(root, "Calibri", "Segoe UI", "Helvetica", size=11, weight="bold")
        self.f_box = pick_font(root, "Calibri", "Segoe UI", "Helvetica", size=11)
        self.f_fx = pick_font(root, "Cambria", "Times New Roman", size=11, slant="italic")
        self.f_ico = pick_font(root, MDL2, "Segoe UI Symbol", size=10)
        self.f_ico_s = pick_font(root, MDL2, "Segoe UI Symbol", size=8)
        self.f_ico_l = pick_font(root, MDL2, "Segoe UI Symbol", size=18)

        self._load_workbook()

        y = 0
        self.top = tk.Canvas(root, width=WIN_W, height=TITLE_H + TABS_H + RIBBON_H,
                             bg=CHROME_BG, highlightthickness=0, bd=0)
        self.top.place(x=0, y=0)
        self._draw_title_strip(self.top)
        self._draw_ribbon_tabs(self.top, TITLE_H)
        self._draw_ribbon(self.top, TITLE_H + TABS_H)
        y = TITLE_H + TABS_H + RIBBON_H

        self._build_formula_bar(y)
        y += FBAR_H

        grid_h = WIN_H - y - SHEETBAR_H - STATUS_H
        self.grid = tk.Canvas(root, width=WIN_W, height=grid_h, bg="#FFFFFF",
                              highlightthickness=0, bd=0, cursor="plus")
        self.grid.place(x=0, y=y)
        self.grid_w, self.grid_h = WIN_W, grid_h
        self.grid.bind("<Button-1>", self._on_grid_click)
        self.grid.bind("<MouseWheel>", self._on_wheel)
        y += grid_h

        self.sheetbar = tk.Canvas(root, width=WIN_W, height=SHEETBAR_H, bg=CHROME_BG,
                                  highlightthickness=0, bd=0)
        self.sheetbar.place(x=0, y=y)
        self._draw_sheet_bar(self.sheetbar)
        y += SHEETBAR_H

        self.status = tk.Canvas(root, width=WIN_W, height=STATUS_H, bg=CHROME_BG,
                                highlightthickness=0, bd=0)
        self.status.place(x=0, y=y)
        self._draw_status_bar(self.status)

        self._select_cell(1, 1)
        self.name_box.focus_set()

    # ------------------------------------------------------------------ data
    def _load_workbook(self):
        self.wb = load_workbook(self.path)
        self.ws = self.wb[self.sheet_name] if self.sheet_name else self.wb.active
        self.col_widths = {}
        for c in range(1, max(self.ws.max_column, 1) + 1):
            letter = get_column_letter(c)
            dim = self.ws.column_dimensions.get(letter)
            if dim is not None and dim.width:
                self.col_widths[c] = int(dim.width * 7 + 5)
                continue
            # No explicit widths in the dummy fixtures: auto-fit the way a user
            # would have (double-clicked the column border), capped for long text.
            widest = 0
            for r in range(1, min(self.ws.max_row, 400) + 1):
                v = self.ws.cell(row=r, column=c).value
                if v is None:
                    continue
                s = str(v)
                if len(s) > 60:
                    continue  # long notes overflow into neighbours instead
                widest = max(widest, self.f_cell.measure(s) + 12)
            self.col_widths[c] = max(DEFAULT_COL_W, min(MAX_AUTO_COL_W, widest))

    def col_w(self, c):
        return self.col_widths.get(c, DEFAULT_COL_W)

    # --------------------------------------------------------- chrome drawing
    def _draw_title_strip(self, cv):
        f = self.f_ui
        # Excel app tile
        cv.create_rectangle(12, 9, 28, 25, fill="#107C41", outline="")
        cv.create_rectangle(20, 9, 28, 17, fill="#21A366", outline="")
        cv.create_rectangle(9, 12, 21, 22, fill="#185C37", outline="")
        cv.create_text(15, 17, text="X", fill="#FFFFFF",
                       font=(self.f_ui_b.actual("family"), 8, "bold"))
        cv.create_text(44, 17, text="AutoSave", anchor="w", fill=TEXT, font=f)
        # toggle (Off)
        rounded_rect(cv, 98, 9, 136, 25, 8, fill="#FFFFFF", outline="#8A8A8A")
        cv.create_oval(103, 13, 111, 21, fill="#616161", outline="")
        cv.create_text(127, 17, text="Off", fill=TEXT, font=self.f_ui_s)
        x = 152
        for glyph in ("", "", "", "", ""):
            small = glyph == ""
            cv.create_text(x, 17, text=glyph, fill=TEXT_SOFT if small else TEXT,
                           font=self.f_ico_s if small else self.f_ico)
            x += 12 if small else 20
        stem = os.path.splitext(self.file_name)[0]
        cv.create_text(276, 17, text=f"{stem}  •  Saved to this PC", anchor="w",
                       fill=TEXT, font=f)
        cv.create_text(276 + f.measure(f"{stem}  •  Saved to this PC") + 10, 18,
                       text="", fill=TEXT_SOFT, font=self.f_ico_s)
        # search box
        rounded_rect(cv, 560, 5, 880, 29, 5, fill="#FFFFFF", outline="#D1D1D1")
        cv.create_text(576, 17, text="", fill=TEXT_SOFT, font=self.f_ico)
        cv.create_text(592, 17, text="Search (Alt+Q)", anchor="w", fill=TEXT_SOFT, font=f)
        # right side: user + copilot-ish icons
        cv.create_text(1140, 17, text="Underwriting Team", anchor="e", fill=TEXT, font=f)
        cv.create_oval(1150, 6, 1172, 28, fill="#8764B8", outline="")
        cv.create_text(1161, 17, text="UT", fill="#FFFFFF", font=self.f_ui_s)
        cv.create_text(1200, 17, text="", fill=TEXT_SOFT, font=self.f_ico)
        cv.create_text(1236, 17, text="", fill=TEXT_SOFT, font=self.f_ico)

    def _draw_ribbon_tabs(self, cv, y0):
        tabs = ["File", "Home", "Insert", "Draw", "Page Layout", "Formulas", "Data",
                "Review", "View", "Automate", "Help"]
        x = 14
        cy = y0 + TABS_H // 2
        for t in tabs:
            active = t == "Home"
            fnt = self.f_tab_b if active else self.f_tab
            w = fnt.measure(t)
            cv.create_text(x, cy, text=t, anchor="w", fill=GREEN if active else TEXT, font=fnt)
            if active:
                rounded_rect(cv, x, y0 + TABS_H - 5, x + w, y0 + TABS_H - 2, 1,
                             fill=GREEN, outline=GREEN)
            x += w + 22
        # Comments / Share
        rounded_rect(cv, 1078, y0 + 4, 1172, y0 + 26, 4, fill="#FFFFFF", outline="#D1D1D1")
        cv.create_text(1092, cy, text="", fill=TEXT, font=self.f_ico)
        cv.create_text(1104, cy, text="Comments", anchor="w", fill=TEXT, font=self.f_ui)
        rounded_rect(cv, 1180, y0 + 4, 1268, y0 + 26, 4, fill=GREEN, outline=GREEN)
        cv.create_text(1196, cy, text="", fill="#FFFFFF", font=self.f_ico)
        cv.create_text(1210, cy, text="Share", anchor="w", fill="#FFFFFF", font=self.f_ui_b)
        cv.create_text(1254, cy + 1, text="", fill="#FFFFFF", font=self.f_ico_s)

    def _draw_ribbon(self, cv, y0):
        rounded_rect(cv, 6, y0 + 2, WIN_W - 6, y0 + RIBBON_H - 6, 8,
                     fill=RIBBON_BG, outline=RIBBON_BORDER)
        top = y0 + 8
        lbl_y = y0 + RIBBON_H - 17
        f, fi, fs = self.f_ui, self.f_ico, self.f_ico_s

        def sep(x):
            cv.create_line(x, top + 2, x, y0 + RIBBON_H - 14, fill="#E0E0E0")

        def group_label(x1, x2, text, launcher=True):
            cv.create_text((x1 + x2) // 2, lbl_y, text=text, fill=TEXT_SOFT, font=self.f_ui_s)
            if launcher:
                cv.create_text(x2 - 8, lbl_y, text="↘", fill=TEXT_FAINT, font=self.f_ui_s)

        def big(x, glyph, label, color=TEXT, chevron=False, w=48):
            cv.create_text(x + w // 2, top + 18, text=glyph, fill=color, font=self.f_ico_l)
            cv.create_text(x + w // 2, top + 46, text=label, fill=TEXT, font=f)
            if chevron:
                cv.create_text(x + w // 2, top + 60, text="", fill=TEXT_SOFT, font=fs)

        def small(x, y, glyph, label=None, color=TEXT, chevron=False):
            cv.create_text(x + 8, y, text=glyph, fill=color, font=fi)
            nx = x + 20
            if label:
                cv.create_text(nx, y, text=label, anchor="w", fill=TEXT, font=f)
                nx += f.measure(label) + 4
            if chevron:
                cv.create_text(nx + 4, y + 1, text="", fill=TEXT_SOFT, font=fs)
                nx += 10
            return nx

        def combo(x, y, w, text):
            cv.create_rectangle(x, y - 10, x + w, y + 10, fill="#FFFFFF", outline=BOX_BORDER)
            cv.create_text(x + 5, y, text=text, anchor="w", fill=TEXT, font=f)
            cv.create_text(x + w - 9, y + 1, text="", fill=TEXT_SOFT, font=fs)

        r1, r2, r3 = top + 8, top + 32, top + 56

        # Clipboard
        x = 14
        cv.create_text(x + 22, top + 16, text="", fill=TEXT, font=self.f_ico_l)
        cv.create_text(x + 22, top + 44, text="Paste", fill=TEXT, font=f)
        cv.create_text(x + 22, top + 58, text="", fill=TEXT_SOFT, font=fs)
        small(x + 48, r1, "")
        small(x + 48, r2, "", chevron=True)
        small(x + 48, r3, "", color="#C19C00")
        group_label(10, 100, "Clipboard")
        sep(104)

        # Font
        x = 112
        combo(x, r1, 112, "Calibri")
        combo(x + 118, r1, 40, "11")
        cv.create_text(x + 176, r1, text="A˄", fill=TEXT, font=self.f_ui)
        cv.create_text(x + 198, r1, text="A˅", fill=TEXT, font=self.f_ui_s)
        bx = x
        for txt, style in (("B", "bold"), ("I", "italic"), ("U", "underline")):
            cv.create_text(bx + 9, r2, text=txt, fill=TEXT,
                           font=(self.f_cell.actual("family"), 11, style))
            bx += 22
        cv.create_text(bx, r2 + 1, text="", fill=TEXT_SOFT, font=fs)
        bx += 14
        cv.create_line(bx, r2 - 9, bx, r2 + 9, fill="#E0E0E0")
        bx += 8
        cv.create_rectangle(bx, r2 - 7, bx + 14, r2 + 7, outline=TEXT, dash=(1, 1))
        cv.create_line(bx, r2 + 7, bx + 14, r2 + 7, fill=TEXT)
        cv.create_text(bx + 22, r2 + 1, text="", fill=TEXT_SOFT, font=fs)
        bx += 36
        cv.create_text(bx + 7, r2 - 2, text="", fill=TEXT, font=fi)
        cv.create_rectangle(bx, r2 + 6, bx + 15, r2 + 9, fill="#FFFF00", outline="")
        cv.create_text(bx + 22, r2 + 1, text="", fill=TEXT_SOFT, font=fs)
        bx += 36
        cv.create_text(bx + 7, r2 - 2, text="A", fill=TEXT,
                       font=(self.f_cell.actual("family"), 11, "underline"))
        cv.create_rectangle(bx, r2 + 6, bx + 15, r2 + 9, fill="#FF0000", outline="")
        cv.create_text(bx + 22, r2 + 1, text="", fill=TEXT_SOFT, font=fs)
        group_label(108, 340, "Font")
        sep(344)

        # Alignment
        x = 352
        ax = x
        for g in ("", "", ""):
            cv.create_text(ax + 9, r1, text="≡", fill=TEXT, font=self.f_cell)
            ax += 22
        ax += 6
        cv.create_text(ax + 6, r1, text="ab", fill=TEXT, font=self.f_ui_s)
        cv.create_text(ax + 22, r1, text="Wrap Text", anchor="w", fill=TEXT, font=f)
        ax = x
        for g in ("", "", ""):
            cv.create_text(ax + 9, r2, text=g, fill=TEXT, font=fi)
            ax += 22
        ax += 6
        cv.create_text(ax + 6, r2, text="", fill=TEXT, font=fi)
        cv.create_text(ax + 22, r2, text="Merge & Center", anchor="w", fill=TEXT, font=f)
        cv.create_text(ax + 26 + f.measure("Merge & Center"), r2 + 1, text="",
                       fill=TEXT_SOFT, font=fs)
        cv.create_text(x + 9, r3, text="⇤", fill=TEXT, font=f)
        cv.create_text(x + 31, r3, text="⇥", fill=TEXT, font=f)
        cv.create_text(x + 56, r3, text="ab↗", fill=TEXT, font=self.f_ui_s)
        group_label(348, 548, "Alignment")
        sep(552)

        # Number
        x = 560
        combo(x, r1, 120, "General")
        nx = x
        for t in ("$", "%", "9"):
            cv.create_text(nx + 8, r2, text=t if t != "9" else ",", fill=TEXT,
                           font=(self.f_ui.actual("family"), 10))
            nx += 22 if t != "$" else 14
            if t == "$":
                cv.create_text(nx + 2, r2 + 1, text="", fill=TEXT_SOFT, font=fs)
                nx += 12
        cv.create_text(nx + 14, r2, text=".0←", fill=TEXT, font=self.f_ui_s)
        cv.create_text(nx + 42, r2, text=".00→", fill=TEXT, font=self.f_ui_s)
        group_label(556, 690, "Number")
        sep(694)

        # Styles
        x = 702
        cv.create_rectangle(x + 2, r1 - 7, x + 14, r1 + 7, fill="#FFFFFF", outline=TEXT_SOFT)
        cv.create_rectangle(x + 4, r1 - 5, x + 12, r1 - 1, fill="#F4B183", outline="")
        cv.create_rectangle(x + 4, r1 + 1, x + 12, r1 + 5, fill="#9DC3E6", outline="")
        cv.create_text(x + 20, r1, text="Conditional Formatting", anchor="w", fill=TEXT, font=f)
        cv.create_text(x + 26 + f.measure("Conditional Formatting"), r1 + 1, text="",
                       fill=TEXT_SOFT, font=fs)
        cv.create_text(x + 8, r2, text="", fill="#2E75B6", font=fi)
        cv.create_text(x + 20, r2, text="Format as Table", anchor="w", fill=TEXT, font=f)
        cv.create_text(x + 26 + f.measure("Format as Table"), r2 + 1, text="",
                       fill=TEXT_SOFT, font=fs)
        cv.create_rectangle(x + 2, r3 - 6, x + 14, r3 + 6, fill="#C6EFCE", outline="#7FB78E")
        cv.create_text(x + 20, r3, text="Cell Styles", anchor="w", fill=TEXT, font=f)
        cv.create_text(x + 26 + f.measure("Cell Styles"), r3 + 1, text="",
                       fill=TEXT_SOFT, font=fs)
        group_label(698, 868, "Styles", launcher=False)
        sep(872)

        # Cells
        x = 880
        for i, (g, label) in enumerate((("", "Insert"), ("", "Delete"),
                                        ("", "Format"))):
            big(x + i * 50, g, label, chevron=True)
        group_label(876, 1032, "Cells", launcher=False)
        sep(1036)

        # Editing
        x = 1044
        cv.create_text(x + 8, r1, text="Σ", fill=TEXT, font=(self.f_ui.actual("family"), 11))
        cv.create_text(x + 20, r1, text="AutoSum", anchor="w", fill=TEXT, font=f)
        cv.create_text(x + 8, r2, text="", fill="#2E75B6", font=fi)
        cv.create_text(x + 20, r2, text="Fill", anchor="w", fill=TEXT, font=f)
        cv.create_text(x + 8, r3, text="", fill="#C239B3", font=fi)
        cv.create_text(x + 20, r3, text="Clear", anchor="w", fill=TEXT, font=f)
        for yy, w in ((r1, "AutoSum"), (r2, "Fill"), (r3, "Clear")):
            cv.create_text(x + 26 + f.measure(w), yy + 1, text="", fill=TEXT_SOFT, font=fs)
        big(x + 88, "", "Sort &", w=52)
        cv.create_text(x + 110, top + 60, text="Filter", fill=TEXT, font=f)
        cv.create_text(x + 110 + f.measure("Filter") // 2 + 7, top + 61, text="",
                       fill=TEXT_SOFT, font=fs)
        big(x + 142, "", "Find &", w=52)
        cv.create_text(x + 168, top + 60, text="Select", fill=TEXT, font=f)
        group_label(1040, 1250, "Editing", launcher=False)
        cv.create_text(WIN_W - 18, y0 + RIBBON_H - 16, text="", fill=TEXT_SOFT, font=fs)

    def _build_formula_bar(self, y):
        bar = tk.Canvas(self.root, width=WIN_W, height=FBAR_H, bg=CHROME_BG,
                        highlightthickness=0, bd=0)
        bar.place(x=0, y=y)
        self.fbar_canvas = bar
        box_y, box_h = 6, 24

        # Name Box: white box with a dropdown chevron, like real Excel.
        nb = tk.Frame(self.root, bg="#FFFFFF", highlightthickness=1,
                      highlightbackground=BOX_BORDER, highlightcolor=BOX_BORDER)
        nb.place(x=8, y=y + box_y, width=100, height=box_h)
        self.name_box = tk.Entry(nb, font=self.f_box, relief="flat", bd=0, bg="#FFFFFF",
                                 fg=TEXT, highlightthickness=0, insertwidth=1,
                                 selectbackground="#B4D7F0", selectforeground=TEXT)
        self.name_box.place(x=4, y=1, width=78, height=box_h - 4)
        tk.Label(nb, text="", font=self.f_ico_s, fg=TEXT_SOFT, bg="#FFFFFF"
                 ).place(x=84, y=4)
        self.name_box.bind("<Return>", self._on_name_box_enter)
        self.name_box.bind("<KP_Enter>", self._on_name_box_enter)
        self.name_box.bind("<Control-a>", self._select_all)
        self.name_box.bind("<Control-A>", self._select_all)

        cy = box_y + box_h // 2
        bar.create_text(118, cy, text="⋮", fill=TEXT_FAINT, font=self.f_ui)
        bar.create_text(136, cy, text="", fill=TEXT_FAINT, font=self.f_ico)
        bar.create_text(160, cy, text="", fill=TEXT_FAINT, font=self.f_ico)
        bar.create_text(185, cy, text="fx", fill=TEXT, font=self.f_fx)

        fb = tk.Frame(self.root, bg="#FFFFFF", highlightthickness=1,
                      highlightbackground=BOX_BORDER, highlightcolor=BOX_BORDER)
        fb.place(x=202, y=y + box_y, width=WIN_W - 202 - 8, height=box_h)
        self.formula_bar = tk.Entry(fb, font=self.f_box, relief="flat", bd=0, bg="#FFFFFF",
                                    fg=TEXT, highlightthickness=0, insertwidth=1,
                                    selectbackground="#B4D7F0", selectforeground=TEXT)
        self.formula_bar.place(x=6, y=1, width=WIN_W - 202 - 8 - 34, height=box_h - 4)
        tk.Label(fb, text="", font=self.f_ico_s, fg=TEXT_SOFT, bg="#FFFFFF"
                 ).place(x=WIN_W - 202 - 8 - 22, y=4)
        self.formula_bar.bind("<Return>", self._on_formula_bar_enter)
        self.formula_bar.bind("<KP_Enter>", self._on_formula_bar_enter)
        self.formula_bar.bind("<Control-a>", self._select_all)
        self.formula_bar.bind("<Control-A>", self._select_all)

    def _draw_sheet_bar(self, cv):
        cy = SHEETBAR_H // 2
        cv.create_text(16, cy, text="", fill=TEXT_FAINT, font=self.f_ico_s)
        cv.create_text(36, cy, text="", fill=TEXT_FAINT, font=self.f_ico_s)
        x = 56
        for name in self.wb.sheetnames:
            active = name == self.ws.title
            fnt = self.f_tab_b if active else self.f_tab
            w = fnt.measure(name) + 28
            if active:
                cv.create_rectangle(x, 0, x + w, SHEETBAR_H - 3, fill="#FFFFFF", outline="")
                cv.create_line(x, 0, x, SHEETBAR_H - 3, fill="#E0E0E0")
                cv.create_line(x + w, 0, x + w, SHEETBAR_H - 3, fill="#E0E0E0")
                cv.create_rectangle(x + 8, SHEETBAR_H - 6, x + w - 8, SHEETBAR_H - 4,
                                    fill=GREEN, outline="")
            cv.create_text(x + w // 2, cy - 1, text=name, fill=GREEN if active else TEXT,
                           font=fnt)
            x += w
            if not active:
                cv.create_line(x, 6, x, SHEETBAR_H - 6, fill="#D0D0D0")
        cv.create_oval(x + 10, cy - 9, x + 28, cy + 9, outline="#BDBDBD")
        cv.create_text(x + 19, cy, text="", fill=TEXT_SOFT, font=self.f_ico_s)
        # horizontal scrollbar (right half)
        hx = 760
        cv.create_text(hx - 16, cy, text="⋮", fill=TEXT_FAINT, font=self.f_ui)
        cv.create_text(hx, cy, text="", fill=TEXT_FAINT, font=self.f_ico_s)
        cv.create_text(WIN_W - 30, cy, text="", fill=TEXT_FAINT, font=self.f_ico_s)
        self.hthumb = rounded_rect(cv, hx + 14, cy - 3, hx + 220, cy + 3, 3,
                                   fill="#A6A6A6", outline="")
        self.hx0, self.hx1 = hx + 14, WIN_W - 44

    def _draw_status_bar(self, cv):
        cy = STATUS_H // 2
        cv.create_line(0, 0, WIN_W, 0, fill="#E6E6E6")
        cv.create_text(12, cy, text="Ready", anchor="w", fill=TEXT, font=self.f_ui)
        cv.create_text(70, cy, text="", fill=TEXT_SOFT, font=self.f_ico_s)
        cv.create_text(82, cy, text="Accessibility: Good to go", anchor="w", fill=TEXT,
                       font=self.f_ui)
        cv.create_text(904, cy, text="", fill=TEXT_SOFT, font=self.f_ico_s)
        cv.create_text(916, cy, text="Display Settings", anchor="w", fill=TEXT, font=self.f_ui)
        x = 1028
        for i, g in enumerate(("", "", "")):
            if i == 0:
                cv.create_rectangle(x - 9, 3, x + 9, STATUS_H - 3, fill="#E0E0E0", outline="")
            cv.create_text(x, cy, text=g, fill=TEXT, font=self.f_ico_s)
            x += 26
        cv.create_text(1112, cy, text="–", fill=TEXT, font=self.f_ui)
        cv.create_line(1122, cy, 1222, cy, fill="#8A8A8A")
        cv.create_line(1172, cy - 4, 1172, cy + 4, fill="#8A8A8A")
        cv.create_rectangle(1169, cy - 6, 1175, cy + 6, fill="#5C5C5C", outline="")
        cv.create_text(1232, cy, text="+", fill=TEXT, font=self.f_ui)
        cv.create_text(1268, cy, text="100%", anchor="e", fill=TEXT, font=self.f_ui)

    # ----------------------------------------------------------- grid drawing
    def _visible_rows(self):
        return max(1, (self.grid_h - COL_HDR_H) // ROW_H)

    def _visible_cols(self):
        """[(col, x0, x1)] for columns at least partly on screen."""
        cols, x, c = [], ROW_HDR_W, self.view_col
        limit = self.grid_w - 14  # leave the vertical scrollbar gutter
        while x < limit and c <= MAX_COLS:
            w = self.col_w(c)
            cols.append((c, x, x + w))
            x += w
            c += 1
        return cols

    def _clip(self, text, width, fnt):
        if fnt.measure(text) <= width:
            return text
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if fnt.measure(text[:mid]) <= width:
                lo = mid
            else:
                hi = mid - 1
        return text[:lo]

    def _cell_style(self, cell):
        fill = None
        try:
            if cell.fill is not None and cell.fill.patternType == "solid":
                rgb = cell.fill.fgColor.rgb
                if isinstance(rgb, str) and len(rgb) == 8 and rgb[:2] != "00":
                    fill = "#" + rgb[2:]
        except Exception:
            pass
        bold = bool(cell.font is not None and cell.font.b)
        halign = cell.alignment.horizontal if cell.alignment is not None else None
        return fill, bold, halign

    def _render_grid(self):
        cv = self.grid
        cv.delete("all")
        sel_r, sel_c = self.selected
        nrows = self._visible_rows()
        cols = self._visible_cols()
        right = cols[-1][2] if cols else self.grid_w
        bottom = COL_HDR_H + nrows * ROW_H
        gw = self.grid_w - 14

        # cell fills + text
        for i in range(nrows + 1):
            r = self.view_row + i
            y0 = COL_HDR_H + i * ROW_H
            row_vals = {}
            for c, x0, x1 in cols:
                v = self.ws.cell(row=r, column=c).value
                if v is not None and str(v) != "":
                    row_vals[c] = v
            for c, x0, x1 in cols:
                cell = self.ws.cell(row=r, column=c)
                fill, bold, halign = self._cell_style(cell)
                if fill:
                    cv.create_rectangle(x0, y0, x1, y0 + ROW_H, fill=fill, outline="")
            for c, x0, x1 in cols:
                if c not in row_vals:
                    continue
                v = row_vals[c]
                cell = self.ws.cell(row=r, column=c)
                _fill, bold, halign = self._cell_style(cell)
                fnt = self.f_cell_b if bold else self.f_cell
                is_num = isinstance(v, (int, float)) and not isinstance(v, bool)
                text = (f"{v:g}" if isinstance(v, float) else str(v)).replace("\n", " ")
                if halign is None:
                    halign = "right" if is_num else "left"
                if halign == "right":
                    cv.create_text(x1 - 3, y0 + ROW_H // 2 + 1, text=self._clip(text, x1 - x0 - 5, fnt),
                                   anchor="e", fill="#000000", font=fnt)
                elif halign == "center":
                    cv.create_text((x0 + x1) // 2, y0 + ROW_H // 2 + 1,
                                   text=self._clip(text, x1 - x0 - 4, fnt), fill="#000000", font=fnt)
                else:
                    # left-aligned text overflows into empty neighbours, like Excel
                    end = x1
                    for c2, _a, b in cols:
                        if c2 <= c:
                            continue
                        if c2 in row_vals:
                            break
                        end = b
                    end = min(end, gw)
                    shown = self._clip(text, end - x0 - 5, fnt)
                    if x0 + 3 + fnt.measure(shown) > x1:
                        # hide the gridlines the overflowing text runs across
                        cv.create_rectangle(x1 - 1, y0 + 1, min(end, x0 + 6 + fnt.measure(shown)),
                                            y0 + ROW_H - 1, fill="#FFFFFF", outline="")
                    cv.create_text(x0 + 3, y0 + ROW_H // 2 + 1,
                                   text=self._clip(text, end - x0 - 5, fnt),
                                   anchor="w", fill="#000000", font=fnt)

        # gridlines go underneath fills/overflow masks (tag_lower below)
        for c, x0, x1 in cols:
            cv.create_line(x1, COL_HDR_H, x1, bottom + ROW_H, fill=GRIDLINE, tags="gl")
        for i in range(nrows + 2):
            y = COL_HDR_H + i * ROW_H
            cv.create_line(ROW_HDR_W, y, right, y, fill=GRIDLINE, tags="gl")
        cv.tag_lower("gl")

        # column headers
        cv.create_rectangle(0, 0, self.grid_w, COL_HDR_H, fill=HDR_BG, outline="")
        for c, x0, x1 in cols:
            selected = c == sel_c
            if selected:
                cv.create_rectangle(x0, 0, x1, COL_HDR_H, fill=HDR_SEL_BG, outline="")
                cv.create_line(x0, COL_HDR_H - 1, x1 + 1, COL_HDR_H - 1, fill=GREEN, width=2)
            cv.create_line(x1, 0, x1, COL_HDR_H, fill=HDR_LINE)
            cv.create_text((x0 + x1) // 2, COL_HDR_H // 2 + 1, text=get_column_letter(c),
                           fill=GREEN_DARK if selected else "#444444",
                           font=self.f_hdr_b if selected else self.f_hdr)
        cv.create_line(0, COL_HDR_H - 1, self.grid_w, COL_HDR_H - 1, fill=HDR_LINE)

        # row headers
        cv.create_rectangle(0, COL_HDR_H, ROW_HDR_W, self.grid_h, fill=HDR_BG, outline="")
        for i in range(nrows + 1):
            r = self.view_row + i
            y0 = COL_HDR_H + i * ROW_H
            selected = r == sel_r
            if selected:
                cv.create_rectangle(0, y0, ROW_HDR_W, y0 + ROW_H, fill=HDR_SEL_BG, outline="")
                cv.create_line(ROW_HDR_W - 1, y0, ROW_HDR_W - 1, y0 + ROW_H + 1, fill=GREEN, width=2)
            cv.create_line(0, y0 + ROW_H, ROW_HDR_W, y0 + ROW_H, fill=HDR_LINE)
            cv.create_text(ROW_HDR_W // 2, y0 + ROW_H // 2 + 1, text=str(r),
                           fill=GREEN_DARK if selected else "#444444",
                           font=self.f_hdr_b if selected else self.f_hdr)
        cv.create_line(ROW_HDR_W - 1, COL_HDR_H, ROW_HDR_W - 1, self.grid_h, fill=HDR_LINE)

        # select-all corner
        cv.create_rectangle(0, 0, ROW_HDR_W, COL_HDR_H, fill=HDR_BG, outline="")
        cv.create_polygon(ROW_HDR_W - 4, 4, ROW_HDR_W - 4, COL_HDR_H - 4,
                          ROW_HDR_W - 4 - (COL_HDR_H - 8), COL_HDR_H - 4,
                          fill="#C2C2C2", outline="")
        cv.create_line(ROW_HDR_W - 1, 0, ROW_HDR_W - 1, COL_HDR_H, fill=HDR_LINE)
        cv.create_line(0, COL_HDR_H - 1, ROW_HDR_W, COL_HDR_H - 1, fill=HDR_LINE)

        # active cell: thick green border + fill handle
        for c, x0, x1 in cols:
            if c == sel_c and self.view_row <= sel_r < self.view_row + nrows + 1:
                y0 = COL_HDR_H + (sel_r - self.view_row) * ROW_H
                cv.create_rectangle(x0, y0, x1, y0 + ROW_H, outline=GREEN, width=2)
                cv.create_rectangle(x1 - 3, y0 + ROW_H - 3, x1 + 3, y0 + ROW_H + 3,
                                    fill=GREEN, outline="#FFFFFF")
                break

        # vertical scrollbar gutter
        sx = self.grid_w - 14
        cv.create_rectangle(sx, 0, self.grid_w, self.grid_h, fill="#FAFAFA", outline="")
        cv.create_text(sx + 7, 8, text="▴", fill=TEXT_FAINT, font=self.f_ui_s)
        cv.create_text(sx + 7, self.grid_h - 8, text="▾", fill=TEXT_FAINT, font=self.f_ui_s)
        span = max(self.ws.max_row, self.view_row + nrows) + nrows
        track0, track1 = 18, self.grid_h - 18
        t0 = track0 + (track1 - track0) * (self.view_row - 1) / span
        t1 = max(t0 + 24, track0 + (track1 - track0) * (self.view_row - 1 + nrows) / span)
        rounded_rect(cv, sx + 4, t0, sx + 10, min(t1, track1), 3, fill="#A6A6A6", outline="")

        # horizontal thumb in the sheet bar
        hspan = max(self.ws.max_column, 20) + 10
        hx0, hx1 = self.hx0, self.hx1
        a = hx0 + (hx1 - hx0) * (self.view_col - 1) / hspan
        self.sheetbar.coords(self.hthumb, *self._rr_points(a, SHEETBAR_H // 2 - 3,
                                                           a + 206, SHEETBAR_H // 2 + 3, 3))

    @staticmethod
    def _rr_points(x1, y1, x2, y2, r):
        return [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
                x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]

    # -------------------------------------------------------------- behaviour
    def _ensure_visible(self, row, col):
        nrows = self._visible_rows()
        if row < self.view_row or row >= self.view_row + nrows:
            # Scroll the viewport to bring the target row into view, like real
            # Excel's Name Box navigation (Pass Back Form.xlsx uses rows > 200).
            self.view_row = max(1, row - nrows // 2)
        if col < self.view_col:
            self.view_col = col
        else:
            limit = self.grid_w - 14
            while True:
                x = ROW_HDR_W + sum(self.col_w(c) for c in range(self.view_col, col + 1))
                if x <= limit or self.view_col >= col:
                    break
                self.view_col += 1

    def _select_cell(self, row, col):
        self.selected = (row, col)
        self._ensure_visible(row, col)
        ref = f"{get_column_letter(col)}{row}"
        self.name_box.delete(0, "end")
        self.name_box.insert(0, ref)
        value = self.ws.cell(row=row, column=col).value
        self.formula_bar.delete(0, "end")
        self.formula_bar.insert(0, "" if value is None else str(value))
        self._render_grid()

    def _select_all(self, event):
        event.widget.select_range(0, "end")
        event.widget.icursor("end")
        return "break"

    def _on_grid_click(self, event):
        if event.x < ROW_HDR_W or event.y < COL_HDR_H or event.x > self.grid_w - 14:
            return
        row = self.view_row + (event.y - COL_HDR_H) // ROW_H
        for c, x0, x1 in self._visible_cols():
            if x0 <= event.x < x1:
                self._select_cell(row, c)
                self.grid.focus_set()
                return

    def _on_wheel(self, event):
        step = -3 if event.delta > 0 else 3
        self.view_row = max(1, self.view_row + step)
        self._render_grid()

    def _on_name_box_enter(self, _event):
        rc = cell_ref_to_rc(self.name_box.get())
        if rc is None:
            return "break"
        row, col = rc
        if row < 1 or col < 1 or row > 1048576 or col > MAX_COLS:
            return "break"
        self._select_cell(row, col)
        self.formula_bar.focus_set()
        self.formula_bar.icursor("end")
        return "break"

    def _on_formula_bar_enter(self, _event):
        row, col = self.selected
        value = self.formula_bar.get()
        self.ws.cell(row=row, column=col, value=value)
        self.wb.save(self.path)
        self._select_cell(row, col)
        self.name_box.focus_set()
        return "break"


def main(path, sheet_name=None):
    root = tk.Tk()
    ExcelMirror(root, path, sheet_name)
    root.mainloop()


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        print("usage: main.py <path-to-xlsx> [sheet-name]", file=sys.stderr)
        sys.exit(2)
    main(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else None)
