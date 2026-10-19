"""
Teams Mirror - a local desktop stand-in for the new Microsoft Teams (dark theme),
deep enough to replay navigating a channel's Shared files to one workbook:
Existing Business -> Renewals -> 2026 Renewals -> APC 2026 RENEWALS.xlsx.

Purpose: give an RPA automation something real to click through for this one
recorded navigation, without needing a real Teams tenant. Opening the actual Excel
file is a separate step in the automation (via the Excel Mirror app) - this app only
mirrors the 3-click Teams navigation itself, ending in a brief "Opening in Excel..."
state.

Automation contract (keep stable - the .robot clicks fixed client coordinates):
  * window title WINDOW_TITLE, fixed geometry GEOMETRY
  * the clickable folder/file name is always in the FIRST row of the file table, at
    ROW1_CLICK (Tk-logical client coordinates) on every level
Everything else (rail, chat list, tabs, toolbar, other rows) is decorative and inert.
Each navigation prints one line to stdout ("teams_mirror: ...") for the run log.

All names and data here are fictitious.

Launch:
    python main.py
"""
import tkinter as tk
from tkinter import font as tkfont

WINDOW_TITLE = "Renewals | Microsoft Teams"
GEOMETRY = "1280x760+40+20"
WIN_W, WIN_H = 1280, 760

# Layout
TOP_H = 46
RAIL_W = 62
PANE_X1 = 352            # right edge of the Chat pane
MAIN_X0 = 362            # main content left edge
MAIN_X1 = 1266
HDR_Y = 70
BREAD_Y = 292
THEAD_Y0, THEAD_Y1 = 312, 348
TBODY_Y0 = 351
ROW_H = 41
NAME_X = 448
ROW1_CY = TBODY_Y0 + 19
# Tk-logical client point the automation clicks: inside the row-1 name link on
# every level ("Renewals", "2026 Renewals", "APC 2026 RENEWALS.xlsx").
ROW1_CLICK = (NAME_X + 22, ROW1_CY)

# Colours (new Teams, dark theme)
BG = "#1F1F1F"
PANEL = "#2E2E2E"
PANEL_HOVER = "#3A3A3A"
TEXT = "#FFFFFF"
TEXT2 = "#D6D6D6"
TEXT3 = "#ADADAD"
TEXT4 = "#8A8A8A"
LINE = "#3D3D3D"
PURPLE = "#7F85F5"
PURPLE_SOFT = "#9586E1"
BANNER_BG = "#2F2A52"
BANNER_LINE = "#4A4589"
FOLDER = "#FFC83D"
FOLDER_BACK = "#E8A80C"
XLSX = "#107C41"

MDL2 = "Segoe MDL2 Assets"

LEVELS = {
    0: {
        "crumbs": ["Existing Business"],
        "rows": [
            ("folder", "Renewals", "March 4, 2024", "Migration Task"),
        ],
    },
    1: {
        "crumbs": ["Existing Business", "Renewals"],
        "rows": [
            ("folder", "2026 Renewals", "October 6", "Underwriting Team"),
            ("folder", "Archive Renewals", "January 15, 2025", "Migration Task"),
            ("folder", "Renewal Review Form", "May 22, 2025", "Constable, Ruth"),
            ("xlsx", "Re-referral rules 300721.xlsx", "July 30, 2021", "Migration Task"),
            ("xlsx", "RS Rating 2024.xlsx", "February 2, 2024", "Hughes, Oliver"),
        ],
    },
    2: {
        "crumbs": ["Existing Business", "Renewals", "2026 Renewals"],
        "rows": [
            ("xlsx", "APC 2026 RENEWALS.xlsx", "October 14", "Underwriting Team"),
            ("xlsx", "Household 2026 RENEWALS.xlsx", "October 9", "Constable, Ruth"),
            ("xlsx", "Pass Back Form.xlsx", "September 30", "Shah, Priya"),
            ("xlsx", "Renewal Tracker 2026.xlsx", "September 18", "Underwriting Team"),
            ("xlsx", "Vulnerable Customers Mapping 2026.xlsx", "August 27", "Ward, Daniel"),
        ],
    },
}


def pick_font(root, *candidates, size=10, weight="normal", underline=False):
    available = set(tkfont.families(root))
    for name in candidates:
        if name in available:
            return tkfont.Font(root=root, family=name, size=size, weight=weight,
                               underline=underline)
    return tkfont.Font(root=root, size=size, weight=weight, underline=underline)


def rr_points(x1, y1, x2, y2, r):
    return [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
            x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]


def teams_icon(root, size=32):
    img = tk.PhotoImage(master=root, width=size, height=size)
    img.put("#5B5FC7", to=(2, 4, size - 2, size - 4))
    img.put("#7B83EB", to=(size // 2, 2, size - 2, size // 2))
    img.put("#FFFFFF", to=(8, 10, 22, 13))
    img.put("#FFFFFF", to=(13, 13, 17, 25))
    return img


class TeamsApp:
    def __init__(self, root):
        self.root = root
        root.title(WINDOW_TITLE)
        root.geometry(GEOMETRY)
        root.resizable(False, False)
        root.configure(bg=BG)
        try:
            self._icon = teams_icon(root)
            root.iconphoto(True, self._icon)
        except tk.TclError:
            pass

        fam = ("Segoe UI", "SF Pro Text", "Helvetica")
        semi = ("Segoe UI Semibold", "Segoe UI", "SF Pro Text", "Helvetica")
        self.f = pick_font(root, *fam, size=10)
        self.f_s = pick_font(root, *fam, size=9)
        self.f_xs = pick_font(root, *fam, size=7)
        self.f_pill = pick_font(root, *fam, size=8)
        self.f_b = pick_font(root, *semi, size=10)
        self.f_bs = pick_font(root, *semi, size=9)
        self.f_title = pick_font(root, "Segoe UI", *fam, size=14, weight="bold")
        self.f_hdr = pick_font(root, "Segoe UI", *fam, size=13, weight="bold")
        self.f_crumb = pick_font(root, *fam, size=13)
        self.f_crumb_b = pick_font(root, "Segoe UI", *fam, size=13, weight="bold")
        self.f_tab = pick_font(root, *fam, size=11)
        self.f_tab_b = pick_font(root, "Segoe UI", *fam, size=11, weight="bold")
        self.f_name = pick_font(root, *fam, size=10)
        self.f_name_u = pick_font(root, *fam, size=10, underline=True)
        self.f_i = pick_font(root, MDL2, "Segoe UI Symbol", size=11)
        self.f_is = pick_font(root, MDL2, "Segoe UI Symbol", size=8)
        self.f_il = pick_font(root, MDL2, "Segoe UI Symbol", size=14)

        self.cv = tk.Canvas(root, width=WIN_W, height=WIN_H, bg=BG,
                            highlightthickness=0, bd=0)
        self.cv.place(x=0, y=0)
        self.level = 0
        self._opening_job = None
        self._anim_job = None

        self._draw_top_bar()
        self._draw_rail()
        self._draw_chat_pane()
        self._draw_channel_header()
        self.render_level(0)

    # ---------------------------------------------------------------- helpers
    def rr(self, x1, y1, x2, y2, r, **kw):
        return self.cv.create_polygon(rr_points(x1, y1, x2, y2, r), smooth=True, **kw)

    def text(self, x, y, s, font=None, fill=TEXT2, anchor="w", **kw):
        return self.cv.create_text(x, y, text=s, font=font or self.f, fill=fill,
                                   anchor=anchor, **kw)

    def icon(self, x, y, glyph, fill=TEXT2, font=None, **kw):
        return self.cv.create_text(x, y, text=glyph, font=font or self.f_i, fill=fill, **kw)

    def avatar(self, x, y, initials, color, r=11, status=None):
        cv = self.cv
        cv.create_oval(x - r, y - r, x + r, y + r, fill=color, outline="")
        cv.create_text(x, y, text=initials, fill="#1F1F1F" if color in ("#E6E6E6", "#F1C6A8", "#C4B5FD") else TEXT,
                       font=self.f_xs)
        if status:
            cv.create_oval(x + r - 7, y + r - 7, x + r + 1, y + r + 1, fill=status, outline=BG, width=2)

    def folder_icon(self, x, y, tags=()):
        cv = self.cv
        cv.create_polygon(x - 9, y - 6, x - 3, y - 6, x - 1, y - 4, x + 9, y - 4, x + 9, y + 7,
                          x - 9, y + 7, fill=FOLDER_BACK, outline="", tags=tags)
        cv.create_polygon(x - 9, y - 2, x + 9, y - 2, x + 9, y + 7, x - 9, y + 7,
                          fill=FOLDER, outline="", tags=tags)

    def xlsx_icon(self, x, y, tags=()):
        cv = self.cv
        cv.create_rectangle(x - 4, y - 8, x + 9, y + 8, fill="#FFFFFF", outline="#C8C8C8", tags=tags)
        for yy in (y - 4, y, y + 4):
            cv.create_line(x + 1, yy, x + 8, yy, fill="#21A366", tags=tags)
        cv.create_rectangle(x - 9, y - 5, x + 3, y + 6, fill=XLSX, outline="", tags=tags)
        cv.create_text(x - 3, y + 1, text="X", fill="#FFFFFF",
                       font=(self.f_b.actual("family"), 7, "bold"), tags=tags)

    # ------------------------------------------------------------ static chrome
    def _draw_top_bar(self):
        cv = self.cv
        # Teams logo
        self.rr(18, 12, 38, 32, 4, fill="#5B5FC7", outline="")
        cv.create_oval(30, 8, 40, 18, fill="#7B83EB", outline="")
        self.text(28, 22, "T", font=self.f_bs, fill=TEXT, anchor="center")
        self.icon(300, 22, "", fill=TEXT3, font=self.f_is)
        self.icon(330, 22, "", fill=TEXT4, font=self.f_is)
        self.rr(350, 7, 930, 37, 5, fill="#292929", outline="#3B3B3B")
        self.icon(372, 22, "", fill=TEXT3, font=self.f_is)
        self.text(390, 22, "Search (Ctrl+E)", font=self.f, fill=TEXT3)
        self.icon(1032, 22, "", fill=TEXT2, font=self.f_is)
        self.text(1162, 22, "Example Insurance Group", font=self.f_s, fill=TEXT2, anchor="e")
        self.avatar(1184, 22, "UT", "#C4B5FD", r=12, status="#6BB700")

    def _draw_rail(self):
        items = [
            ("Activity", "", 66),
            ("Chat", "", 116),
            ("Calendar", "", 166),
            ("Calls", "", 216),
            ("OneDrive", "", 266),
            ("Copilot", None, 316),
        ]
        for label, glyph, y in items:
            active = label == "Chat"
            color = PURPLE_SOFT if active else TEXT2
            if glyph:
                self.icon(31, y, glyph, fill=color, font=self.f_i)
            else:  # Copilot: two interlocking rounded shapes
                self.rr(23, y - 8, 35, y + 4, 4, fill="", outline=color, width=1.5)
                self.rr(28, y - 4, 40, y + 8, 4, fill="", outline=color, width=1.5)
            self.text(31, y + 17, label, font=self.f_xs, fill=TEXT2 if not active else TEXT,
                      anchor="center")
            if active:
                self.cv.create_rectangle(2, y - 14, 5, y + 20, fill=PURPLE_SOFT, outline="")
        # Activity badge
        self.cv.create_oval(36, 52, 48, 64, fill="#C4314B", outline="")
        self.text(42, 58, "2", font=self.f_xs, fill=TEXT, anchor="center")
        self.icon(31, 362, "", fill=TEXT2, font=self.f_is)
        self.rr(22, 394, 40, 412, 4, fill="", outline=TEXT2, width=1.3)
        self.icon(31, 403, "", fill=TEXT2, font=self.f_is)
        self.text(31, 422, "Apps", font=self.f_xs, fill=TEXT2, anchor="center")
        self.icon(31, 732, "", fill=TEXT2, font=self.f_i)

    def _draw_chat_pane(self):
        cv = self.cv
        self.text(86, 70, "Chat", font=self.f_title, fill=TEXT)
        self.icon(246, 70, "", fill=TEXT2, font=self.f_is)
        self.icon(274, 70, "", fill=TEXT2, font=self.f_is)
        self.icon(304, 70, "", fill=TEXT2, font=self.f_i)
        x = 84
        for pill in ("Unread", "Channels", "Chats", "Meeting chats"):
            w = self.f_pill.measure(pill) + 16
            self.rr(x, 103, x + w, 123, 9, fill=BG, outline="#4A4A4A")
            self.text(x + w // 2, 113, pill, font=self.f_pill, fill=TEXT2, anchor="center")
            x += w + 4
        chats = [
            ("meeting", "Renewals Kick off", None),
            ("SC", "Collins, Sarah", "#F1C6A8"),
            ("PS", "Shah, Priya", "#E6E6E6"),
            ("ME", "Ellis, Mark, Jake", "#E6E6E6"),
            ("HP", "Price, Hannah", "#F1C6A8"),
            ("meeting", "Weekly Team Catch Up", None),
            ("OH", "Hughes, Oliver", "#D7A07A"),
            ("RC", "Constable, Ruth", "#F1C6A8"),
            ("DW", "Ward, Daniel", "#E6E6E6"),
        ]
        y = 146
        for initials, name, color in chats:
            if initials == "meeting":
                cv.create_oval(85, y - 10, 105, y + 10, fill="#4F52B2", outline="")
                self.icon(95, y, "", fill=TEXT, font=self.f_is)
            else:
                self.avatar(95, y, initials, color, r=10,
                            status="#6BB700" if initials in ("PS", "ME", "DW") else "#C4314B"
                            if initials in ("SC", "RC") else None)
            self.text(114, y, name, font=self.f, fill=TEXT2)
            y += 28
        self.text(76, y + 2, "See more", font=self.f, fill=PURPLE)
        y += 32
        self.icon(80, y, "", fill=TEXT3, font=self.f_is)
        self.text(90, y, "Teams and channels", font=self.f, fill=TEXT3)
        y += 30
        teams = [
            ("Underwriting Audit", "#8378DE", ["General"]),
            ("Example Insurance", "#3AAFB7",
             ["General", "Broker", "Existing Business", "Operations", "Team", "Underwriting"]),
        ]
        for team, color, channels in teams:
            self.icon(80, y, "", fill=TEXT3, font=self.f_is)
            self.rr(88, y - 9, 106, y + 9, 4, fill=color, outline="")
            self.text(114, y, team, font=self.f, fill=TEXT2)
            y += 27
            for ch in channels:
                if ch == "Existing Business":
                    self.rr(70, y - 12, 342, y + 12, 4, fill="#2D2D2D", outline="")
                    self.text(114, y, ch, font=self.f_b, fill=TEXT)
                else:
                    self.text(114, y, ch, font=self.f, fill=TEXT2)
                y += 26
        self.text(114, y, "See all channels", font=self.f, fill=PURPLE)
        self.text(86, y + 28, "See all your teams", font=self.f, fill=PURPLE)

    def _draw_channel_header(self):
        cv = self.cv
        self.rr(MAIN_X0, HDR_Y - 14, MAIN_X0 + 28, HDR_Y + 14, 4, fill="#3AAFB7", outline="")
        cv.create_rectangle(MAIN_X0 + 8, HDR_Y - 5, MAIN_X0 + 20, HDR_Y + 4, fill="#7FD3DA", outline="")
        self.text(MAIN_X0 + 38, HDR_Y, "Existing Business", font=self.f_hdr, fill=TEXT)
        x = MAIN_X0 + 58 + self.f_hdr.measure("Existing Business")
        for tab in ("Posts", "Shared", "Notes"):
            active = tab == "Shared"
            fnt = self.f_tab_b if active else self.f_tab
            self.text(x, HDR_Y, tab, font=fnt, fill=TEXT if active else TEXT2)
            w = fnt.measure(tab)
            if active:
                self.rr(x, HDR_Y + 22, x + w + 14, HDR_Y + 25, 1, fill=PURPLE, outline="")
                self.icon(x + w + 8, HDR_Y + 1, "", fill=TEXT3, font=self.f_is)
                w += 14
            x += w + 20
        self.rr(x, HDR_Y - 8, x + 16, HDR_Y + 8, 3, fill="", outline=TEXT2)
        self.icon(x + 8, HDR_Y, "", fill=TEXT2, font=self.f_is)
        self.icon(1110, HDR_Y, "", fill=TEXT2, font=self.f_i)
        self.text(1124, HDR_Y, "Meet now", font=self.f_b, fill=TEXT2)
        self.icon(1196, HDR_Y + 1, "", fill=TEXT2, font=self.f_is)
        self.icon(1228, HDR_Y, "", fill=TEXT2, font=self.f_i)
        self.icon(1254, HDR_Y, "", fill=TEXT2, font=self.f_is)

        # banner
        self.rr(MAIN_X0 - 6, 104, MAIN_X1, 142, 5, fill=BANNER_BG, outline=BANNER_LINE)
        self.icon(MAIN_X0 + 12, 123, "", fill="#B4A7F5", font=self.f_i)
        self.text(MAIN_X0 + 30, 123, "Find all content shared in this channel, along with items "
                  "from the document library, under the Shared tab.", font=self.f, fill=TEXT)
        self.icon(MAIN_X1 - 20, 123, "", fill=TEXT, font=self.f_is)

        # pills
        w1 = self.f_b.measure("All documents") + 44
        self.rr(MAIN_X0 - 6, 158, MAIN_X0 - 6 + w1, 186, 13, fill="#25253A", outline="#8B8FE0", width=1.4)
        self.icon(MAIN_X0 + 12, 172, "", fill=TEXT, font=self.f_is)
        self.text(MAIN_X0 + 28, 172, "All documents", font=self.f_b, fill=TEXT)
        x = MAIN_X0 + w1 + 2
        w2 = self.f.measure("In messages") + 44
        self.rr(x, 158, x + w2, 186, 13, fill=BG, outline="#4D4D4D")
        self.icon(x + 18, 172, "", fill=TEXT2, font=self.f_is)
        self.text(x + 34, 172, "In messages", font=self.f, fill=TEXT2)

        # command bar
        ty = 219
        self.rr(MAIN_X0 - 6, ty - 14, MAIN_X0 + 76, ty + 14, 4, fill=PURPLE, outline="")
        self.icon(MAIN_X0 + 10, ty, "", fill="#1B1B3A", font=self.f_is)
        self.text(MAIN_X0 + 22, ty, "New", font=self.f_b, fill="#1B1B3A")
        self.icon(MAIN_X0 + 60, ty + 1, "", fill="#1B1B3A", font=self.f_is)
        x = MAIN_X0 + 92
        for glyph, label, chevron in (("", "Upload", True), ("", "Edit in grid view", False),
                                      ("", "Share", False), ("", "Copy link", False),
                                      ("", "Forms", False)):
            self.icon(x + 7, ty, glyph, fill=TEXT2, font=self.f_i)
            self.text(x + 22, ty, label, font=self.f, fill=TEXT2)
            x += 22 + self.f.measure(label) + 6
            if chevron:
                self.icon(x + 2, ty + 1, "", fill=TEXT2, font=self.f_is)
                x += 12
            x += 14
        # "New" badge after Forms
        bx = x - 14
        self.rr(bx, ty - 9, bx + 34, ty + 9, 9, fill="#4F52B2", outline="")
        self.text(bx + 17, ty, "New", font=self.f_xs, fill=TEXT, anchor="center")
        self.icon(bx + 56, ty, "", fill=TEXT2, font=self.f_is)
        self.icon(1040, ty, "", fill=TEXT2, font=self.f_i)
        self.text(1054, ty, "All Documents", font=self.f, fill=TEXT2)
        self.icon(1160, ty, "", fill=TEXT2, font=self.f_i)
        self.text(1174, ty, "Details", font=self.f, fill=TEXT2)
        self.icon(1252, ty, "", fill=TEXT2, font=self.f_i)

        # table header (static across levels)
        self.rr(MAIN_X0 - 6, THEAD_Y0, MAIN_X1, THEAD_Y1, 4, fill=PANEL, outline="")
        hy = (THEAD_Y0 + THEAD_Y1) // 2
        self.icon(422, hy, "", fill=TEXT2, font=self.f_i)
        self.text(NAME_X, hy, "Name", font=self.f_bs, fill=TEXT2)
        self.icon(NAME_X + 44, hy + 1, "", fill=TEXT4, font=self.f_is)
        self.text(822, hy, "Modified", font=self.f_bs, fill=TEXT2)
        self.icon(882, hy + 1, "", fill=TEXT4, font=self.f_is)
        self.text(936, hy, "Modified By", font=self.f_bs, fill=TEXT2)
        self.icon(1012, hy + 1, "", fill=TEXT4, font=self.f_is)
        self.icon(1066, hy, "", fill=TEXT2, font=self.f_is)
        self.text(1080, hy, "Add column", font=self.f_bs, fill=TEXT2)

        # table body panel
        self.rr(MAIN_X0 - 6, TBODY_Y0, MAIN_X1, WIN_H + 10, 4, fill=PANEL, outline="")

    # -------------------------------------------------------------- dynamic
    def render_level(self, level):
        cv = self.cv
        self.level = level
        cv.delete("dyn")
        if self._opening_job:
            self.root.after_cancel(self._opening_job)
            self._opening_job = None
        spec = LEVELS[level]

        # breadcrumb
        x = MAIN_X0 + 4
        crumbs = spec["crumbs"]
        for i, c in enumerate(crumbs):
            last = i == len(crumbs) - 1
            fnt = self.f_crumb_b if last else self.f_crumb
            self.text(x, BREAD_Y, c, font=fnt, fill=TEXT if last else TEXT2, tags="dyn")
            x += fnt.measure(c)
            if not last:
                self.icon(x + 14, BREAD_Y + 1, "", fill=TEXT2, font=self.f_is, tags="dyn")
                x += 30

        for i, (kind, name, modified, by) in enumerate(spec["rows"]):
            cy = ROW1_CY + i * ROW_H
            tag = f"row{i}"
            tags = ("dyn", tag)
            bgid = cv.create_rectangle(MAIN_X0 - 4, cy - ROW_H // 2 + 1, MAIN_X1 - 2,
                                       cy + ROW_H // 2 - 1, fill=PANEL, outline="", tags=tags)
            radio = cv.create_oval(381, cy - 8, 397, cy + 8, outline="", tags=tags)
            if kind == "folder":
                self.folder_icon(422, cy, tags=tags)
            else:
                self.xlsx_icon(422, cy, tags=tags)
            nid = self.text(NAME_X, cy, name, font=self.f_name, fill=TEXT, tags=tags + (f"name{i}",))
            self.text(822, cy, modified, font=self.f_s, fill=TEXT2, tags=tags)
            pw = self.f_s.measure(by) + 20
            cv.create_polygon(rr_points(932, cy - 11, 932 + pw, cy + 11, 10), smooth=True,
                              fill="#3D3D3D", outline="", tags=tags)
            self.text(942, cy, by, font=self.f_s, fill=TEXT2, tags=tags)
            # hover row actions (shown on hover)
            acts = []
            for j, g in enumerate(("", "", "")):
                acts.append(self.icon(712 + j * 28, cy, g, fill=TEXT2, font=self.f_is,
                                      tags=tags, state="hidden"))
            cv.tag_bind(tag, "<Enter>", lambda _e, b=bgid, r=radio, a=acts, n=nid:
                        self._hover(b, r, a, n, True))
            cv.tag_bind(tag, "<Leave>", lambda _e, b=bgid, r=radio, a=acts, n=nid:
                        self._hover(b, r, a, n, False))
            if i == 0:
                # The only live link per level: the row-1 name (plus its icon/row,
                # so a slightly-off click still navigates like a row double-click).
                cv.tag_bind(tag, "<Button-1>", lambda _e: self._open_row1())
                cv.tag_bind(tag, "<Enter>", lambda _e: cv.config(cursor="hand2"), add="+")
                cv.tag_bind(tag, "<Leave>", lambda _e: cv.config(cursor=""), add="+")

    def _hover(self, bgid, radio, acts, nid, on):
        cv = self.cv
        if not cv.find_withtag(bgid):
            return
        cv.itemconfig(bgid, fill=PANEL_HOVER if on else PANEL)
        cv.itemconfig(radio, outline=TEXT2 if on else "")
        cv.itemconfig(nid, font=self.f_name_u if on else self.f_name)
        for a in acts:
            cv.itemconfig(a, state="normal" if on else "hidden")

    def _open_row1(self):
        if self.level == 0:
            print("teams_mirror: opened folder Renewals", flush=True)
            self.render_level(1)
        elif self.level == 1:
            print("teams_mirror: opened folder 2026 Renewals", flush=True)
            self.render_level(2)
        else:
            print("teams_mirror: opening APC 2026 RENEWALS.xlsx in Excel", flush=True)
            self._show_opening()

    def _show_opening(self):
        cv = self.cv
        cv.delete("opening")
        # mark row 1 selected
        cv.create_oval(381, ROW1_CY - 8, 397, ROW1_CY + 8, fill=PURPLE, outline="",
                       tags=("dyn", "opening"))
        self.icon(389, ROW1_CY, "", fill="#1F1F1F", font=self.f_is, tags=("dyn", "opening"))
        cx, cy = (MAIN_X0 + MAIN_X1) // 2, 560
        t = ("dyn", "opening")
        cv.create_polygon(rr_points(cx - 190, cy - 52, cx + 190, cy + 52, 8), smooth=True,
                          fill="#292929", outline="#4A4A4A", tags=t)
        self.xlsx_icon(cx - 150, cy - 14, tags=t)
        self.text(cx - 128, cy - 22, "Opening in Excel…", font=self.f_b, fill=TEXT, tags=t)
        self.text(cx - 128, cy - 2, "APC 2026 RENEWALS.xlsx", font=self.f_s, fill=TEXT2, tags=t)
        cv.create_rectangle(cx - 160, cy + 26, cx + 160, cy + 29, fill="#3D3D3D", outline="", tags=t)
        self._bar = cv.create_rectangle(cx - 160, cy + 26, cx - 90, cy + 29, fill=PURPLE,
                                        outline="", tags=t)
        self._bar_x = 0
        self._animate(cx)
        self._opening_job = self.root.after(6000, self._hide_opening)

    def _animate(self, cx):
        if not self.cv.find_withtag("opening"):
            return
        self._bar_x = (self._bar_x + 8) % 320
        x0 = cx - 160 + self._bar_x
        self.cv.coords(self._bar, x0, 560 + 26, min(cx + 160, x0 + 70), 560 + 29)
        self._anim_job = self.root.after(30, lambda: self._animate(cx))

    def _hide_opening(self):
        self._opening_job = None
        self.cv.delete("opening")


def main():
    root = tk.Tk()
    TeamsApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
