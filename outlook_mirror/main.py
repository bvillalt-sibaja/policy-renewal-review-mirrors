"""
Outlook Mirror - a local desktop-app stand-in for classic Microsoft Outlook
(Microsoft 365 desktop, light theme).

Purpose: give an RPA automation (Robot Framework + RPA.Desktop fixed-coordinate
clicks) something to open/click/read/compose against, without needing a real
mailbox.

All data in data/inbox.json is entirely fictitious (dummy senders, a dummy
insurer domain, dummy policy numbers). Nothing here sends real email -
"Send" only appends a JSON line to data/sent_log.jsonl.

See SELECTORS.md in this folder for exactly how an automation should locate
every window/widget (titles, fixed geometry, fixed click coordinates).

Only the inbox rows, New Email, Reply (ribbon + reading pane), Reply All /
Forward (both open a reply-style compose), Send and the compose fields are
functional. Every other ribbon button, tab and folder is decorative and inert.

Launch:
    python main.py
"""

import json
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import font as tkfont

try:  # Pillow is only used for anti-aliased ribbon icons; the app works without it.
    from PIL import Image, ImageDraw, ImageFont, ImageTk
    HAVE_PIL = True
except Exception:  # pragma: no cover - fallback path
    HAVE_PIL = False

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
INBOX_PATH = DATA_DIR / "inbox.json"
SENT_LOG_PATH = DATA_DIR / "sent_log.jsonl"

MAIN_WINDOW_TITLE = "Inbox - Example Insurance Broker - Outlook"
NEW_MESSAGE_TITLE = "Untitled - Message (HTML)"
REPLY_TITLE_FMT = "RE: {subject} - Message (HTML)"

# Fixed geometry (Tk-logical pixels; Tk is DPI-unaware on Windows so these are
# the 1536x864 logical screen at 125% scaling). Same size/position every launch.
MAIN_GEOMETRY = "1400x760+60+12"
COMPOSE_GEOMETRY = "960x700+200+40"

ACCOUNT_EMAIL = "renewals@exampleinsurancebroker.test"
ACCOUNT_NAME = "Renewals Team"

# Message-list layout (fixed so row i's click point is a simple formula).
ROW_HEIGHT = 68

# ---- Fluent / Outlook light palette ----
OUTLOOK_BLUE = "#0F6CBD"
OUTLOOK_BLUE_DARK = "#115EA3"
SELECTION_BLUE = "#CCE4F7"
HOVER_GRAY = "#F5F5F5"
APP_BG = "#F0F0F0"          # window chrome / title area
RIBBON_BG = "#FFFFFF"       # ribbon panel
BORDER = "#E0E0E0"
DIVIDER = "#EDEBE9"
TEXT = "#242424"
TEXT_SECONDARY = "#616161"
TEXT_DISABLED = "#BDBDBD"
ICON_GRAY = "#424242"
BUTTON_HOVER = "#EBEBEB"
BUTTON_PRESS = "#E0E0E0"
AVATAR_COLORS = ["#C239B3", "#0F6CBD", "#498205", "#B4009E", "#CA5010", "#038387"]

UI_FONT = "Segoe UI"
QUOTE_HEADER_FMT = "On {received}, {sender_name} <{sender_email}> wrote:"


def pick_font(root, *candidates, size=10, weight="normal"):
    available = set(tkfont.families(root))
    for name in candidates:
        if name in available:
            return tkfont.Font(root=root, family=name, size=size, weight=weight)
    return tkfont.Font(root=root, size=size, weight=weight)


def font_family(root, *candidates):
    available = set(tkfont.families(root))
    for name in candidates:
        if name in available:
            return name
    return "TkDefaultFont"


def avatar_initials(name):
    parts = [p for p in name.replace(",", " ").split() if p]
    letters = [p[0].upper() for p in parts[:2]]
    return "".join(letters) or "?"


def parse_received(received):
    try:
        return datetime.strptime(received, "%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return None


def list_time_text(received):
    """Outlook's message-list date column (dd/mm/yyyy for older items)."""
    dt = parse_received(received)
    return dt.strftime("%d/%m/%Y") if dt else str(received)


def header_time_text(received):
    """Reading-pane header date, e.g. 'Tue 25/08/2026 09:14'."""
    dt = parse_received(received)
    return dt.strftime("%a %d/%m/%Y %H:%M") if dt else str(received)


def preview_text(body):
    return " ".join(body.split())


def elide(font, text, max_px):
    if font.measure(text) <= max_px:
        return text
    ell = "..."
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if font.measure(text[:mid] + ell) <= max_px:
            lo = mid
        else:
            hi = mid - 1
    return text[:lo].rstrip() + ell


def load_inbox():
    with open(INBOX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def quote_body(email):
    """Build the quoted-reply block used to pre-fill a Reply compose window."""
    header = QUOTE_HEADER_FMT.format(**email)
    quoted_lines = "\n".join("> " + line for line in email["body"].splitlines())
    return "\n\n\n" + header + "\n" + quoted_lines


# ----------------------------------------------------------------------
# Icons (drawn with Pillow at 4x and downsampled, so they are anti-aliased)
# ----------------------------------------------------------------------
G = ICON_GRAY
B = OUTLOOK_BLUE
RED = "#C50F1F"
WHITE = "#FFFFFF"


class _Pen:
    """Draws in a 32x32 design box, scaled to the real (supersampled) size."""

    def __init__(self, draw, k):
        self.d = draw
        self.k = k

    def _p(self, pts):
        return [(x * self.k, y * self.k) for x, y in pts]

    def _b(self, box):
        x0, y0, x1, y1 = box
        return (x0 * self.k, y0 * self.k, x1 * self.k, y1 * self.k)

    def _w(self, w):
        return max(4, int(round(w * self.k)))

    def line(self, pts, color=G, w=2.0):
        self.d.line(self._p(pts), fill=color, width=self._w(w), joint="curve")

    def rect(self, box, outline=G, fill=None, w=2.0, r=0):
        if r:
            self.d.rounded_rectangle(self._b(box), radius=r * self.k, outline=outline,
                                     fill=fill, width=self._w(w) if outline else 0)
        else:
            self.d.rectangle(self._b(box), outline=outline, fill=fill,
                             width=self._w(w) if outline else 0)

    def oval(self, box, outline=G, fill=None, w=2.0):
        self.d.ellipse(self._b(box), outline=outline, fill=fill,
                       width=self._w(w) if outline else 0)

    def poly(self, pts, outline=G, fill=None, w=2.0):
        if fill:
            self.d.polygon(self._p(pts), fill=fill)
        if outline:
            self.line(list(pts) + [pts[0]], outline, w)

    def arc(self, box, start, end, color=G, w=2.0):
        self.d.arc(self._b(box), start, end, fill=color, width=self._w(w))

    def text(self, xy, s, size, fill=WHITE, bold=True):
        path = "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"
        try:
            fnt = ImageFont.truetype(path, int(size * self.k))
        except Exception:
            fnt = ImageFont.load_default()
        self.d.text((xy[0] * self.k, xy[1] * self.k), s, font=fnt, fill=fill, anchor="mm")


def _envelope(p, x0, y0, x1, y1, color=G, fill=WHITE, w=2.0):
    p.rect((x0, y0, x1, y1), outline=color, fill=fill, w=w, r=2)
    p.line([(x0 + 1.5, y0 + 1.5), ((x0 + x1) / 2, (y0 + y1) / 2 + 0.5), (x1 - 1.5, y0 + 1.5)], color, w)


def _reply_arrow(p, x, y, s=1.0, color=B, w=2.2, mirror=False):
    """Curved reply arrow, arrowhead pointing left at (x, y)."""
    def m(px, py):
        return (x + (-px if mirror else px) * s, y + py * s)
    p.line([m(6, -6), m(0, 0), m(6, 6)], color, w)
    p.line([m(0, 0), m(10, 0), m(15, 2), m(18, 6), m(19, 11)], color, w)


def _ico_mail(p):
    _envelope(p, 4, 8, 28, 24)


def _ico_new_email(p):
    _envelope(p, 3, 6, 25, 21)
    p.oval((17, 16, 31, 30), outline=None, fill=B)
    p.line([(24, 19.5), (24, 26.5)], WHITE, 2)
    p.line([(20.5, 23), (27.5, 23)], WHITE, 2)


def _ico_new_items(p):
    _envelope(p, 9, 4, 29, 18)
    _envelope(p, 3, 11, 23, 27)


def _ico_delete(p):
    p.line([(5, 8), (27, 8)], G, 2)
    p.rect((12, 4, 20, 8), outline=G, w=2, r=1)
    p.poly([(8, 8), (10, 28), (22, 28), (24, 8)], outline=G)
    p.line([(13.5, 13), (13.5, 23)], G, 1.6)
    p.line([(18.5, 13), (18.5, 23)], G, 1.6)


def _ico_archive(p):
    p.rect((4, 5, 28, 11), outline=G, w=2, r=1.5)
    p.rect((6, 11, 26, 27), outline=G, w=2, r=1.5)
    p.line([(13, 16), (19, 16)], G, 2)


def _ico_reply(p):
    _envelope(p, 8, 12, 29, 27)
    _reply_arrow(p, 3, 9, 0.8)


def _ico_reply_all(p):
    _envelope(p, 9, 12, 30, 27)
    _reply_arrow(p, 8, 9, 0.75)
    p.line([(7, 4), (2, 9), (7, 14)], B, 2.2)


def _ico_forward(p):
    _envelope(p, 3, 12, 24, 27)
    _reply_arrow(p, 29, 9, 0.8, mirror=True)


def _ico_teams(p):
    p.oval((19, 4, 28, 13), outline=None, fill="#7B83EB")
    p.rect((16, 12, 30, 25), outline=None, fill="#7B83EB", r=4)
    p.rect((3, 8, 21, 26), outline=None, fill="#4B53BC", r=2)
    p.text((12, 17), "T", 13)


def _ico_move(p):
    p.poly([(3, 8), (12, 8), (14.5, 11), (29, 11), (29, 26), (3, 26)], outline=G)
    p.line([(10, 18.5), (22, 18.5)], B, 2.2)
    p.line([(18, 14.5), (22, 18.5), (18, 22.5)], B, 2.2)


def _ico_rules(p):
    p.rect((6, 3, 24, 28), outline=G, w=2, r=1.5)
    for y in (9, 14, 19):
        p.line([(10, y), (20, y)], G, 1.6)
    p.line([(17, 24), (21, 28), (29, 19)], B, 2.4)


def _ico_onenote(p):
    p.rect((14, 6, 29, 26), outline="#7719AA", w=2, r=1.5)
    p.rect((3, 5, 21, 27), outline=None, fill="#7719AA", r=2)
    p.text((12, 16), "N", 13)


def _ico_policy(p):
    p.rect((5, 3, 23, 28), outline=G, w=2, r=1.5)
    for y in (9, 14, 19):
        p.line([(9, y), (19, y)], G, 1.6)
    p.poly([(19, 16), (25, 14), (31, 16), (30.5, 23), (25, 29), (19.5, 23)], outline=None, fill=B)


def _ico_unread_read(p):
    p.poly([(4, 13), (16, 5), (28, 13), (28, 27), (4, 27)], outline=G, fill=WHITE)
    p.line([(4.5, 13.5), (16, 21), (27.5, 13.5)], G, 2)


def _ico_categorize(p):
    p.rect((4, 4, 14.5, 14.5), outline=None, fill="#D13438", r=1.5)
    p.rect((17.5, 4, 28, 14.5), outline=None, fill="#0F6CBD", r=1.5)
    p.rect((4, 17.5, 14.5, 28), outline=None, fill="#FFB900", r=1.5)
    p.rect((17.5, 17.5, 28, 28), outline=None, fill="#107C10", r=1.5)


def _ico_follow_up(p):
    p.poly([(9, 5), (27, 5), (22.5, 11.5), (27, 18), (9, 18)], outline=None, fill="#D13438")
    p.line([(8, 4), (8, 29)], G, 2.2)


def _ico_read_aloud(p):
    p.line([(3, 26), (10, 6), (17, 26)], G, 2.2)
    p.line([(5.5, 19), (14.5, 19)], G, 2)
    p.arc((14, 9, 24, 23), -60, 60, B, 2)
    p.arc((16, 5, 30, 27), -60, 60, B, 2)


def _ico_translate(p):
    p.rect((3, 4, 19, 20), outline=G, w=2, r=2)
    p.text((11, 12), "A", 11, fill=G)
    p.rect((13, 12, 29, 28), outline=None, fill=B, r=2)
    p.text((21, 20), "a", 11)


def _ico_addins(p):
    p.rect((4, 4, 14, 14), outline=G, w=2, r=1)
    p.rect((4, 18, 14, 28), outline=G, w=2, r=1)
    p.rect((18, 18, 28, 28), outline=G, w=2, r=1)
    p.line([(23, 3), (23, 15)], B, 2.4)
    p.line([(17, 9), (29, 9)], B, 2.4)


def _ico_poll(p):
    p.rect((4, 6, 28, 28), outline=G, w=2, r=2)
    p.line([(4.5, 12), (27.5, 12)], G, 2)
    p.line([(10, 3), (10, 8)], G, 2)
    p.line([(22, 3), (22, 8)], G, 2)
    p.line([(10, 20), (14, 24), (22, 16)], B, 2.4)


def _ico_search(p):
    p.oval((5, 5, 20, 20), outline=G, w=2.4)
    p.line([(18, 18), (27, 27)], G, 2.6)


def _ico_send(p):
    p.poly([(4, 5), (29, 16), (4, 27), (8.5, 16)], outline=B, fill=WHITE, w=2.2)
    p.line([(8.5, 16), (17, 16)], B, 2.2)


def _ico_attach(p):
    p.line([(21, 9), (21, 24), (19.5, 27.5), (16, 29), (12.5, 27.5), (11, 24),
            (11, 7), (12.5, 4), (15.5, 3), (18.5, 4), (19.5, 7), (19.5, 23),
            (18, 25), (16, 25.5), (14, 25), (13, 23), (13, 10)], G, 1.8)


def _ico_signature(p):
    p.line([(4, 24), (8, 18), (11, 24), (14, 19), (16, 23)], G, 1.8)
    p.line([(17, 21), (27, 7)], G, 2.2)
    p.line([(24, 5), (29, 9)], G, 2.2)
    p.line([(3, 28), (29, 28)], G, 1.6)


def _ico_link(p):
    p.rect((3, 11, 18, 21), outline=G, w=2, r=5)
    p.rect((14, 11, 29, 21), outline=G, w=2, r=5)


def _ico_paste(p):
    p.rect((5, 6, 23, 28), outline=G, w=2, r=2)
    p.rect((10, 3, 18, 8), outline=G, fill=WHITE, w=2, r=1)
    p.rect((14, 14, 28, 29), outline=B, fill=WHITE, w=2, r=1)


def _ico_painter(p):
    p.rect((5, 4, 25, 12), outline=G, w=2, r=1.5)
    p.line([(25, 8), (28, 8), (28, 16), (15, 16), (15, 20)], G, 2)
    p.rect((13, 20, 17, 29), outline=None, fill=G)


def _ico_highlight(p):
    p.line([(9, 20), (20, 5), (25, 9), (14, 24)], G, 2)
    p.line([(9, 20), (8, 24), (14, 24)], G, 2)
    p.rect((3, 26, 29, 30), outline=None, fill="#FFE200")


def _ico_font_color(p):
    p.line([(7, 22), (16, 3), (25, 22)], G, 2.4)
    p.line([(10, 15), (22, 15)], G, 2)
    p.rect((3, 25, 29, 30), outline=None, fill="#D13438")


def _ico_dictate(p):
    p.rect((11, 3, 21, 19), outline=G, w=2, r=5)
    p.arc((6, 8, 26, 24), 0, 180, G, 2)
    p.line([(16, 24), (16, 29)], G, 2)


def _ico_sensitivity(p):
    p.poly([(16, 3), (28, 8), (27, 18), (16, 29), (5, 18), (4, 8)], outline=G)
    p.line([(11, 16), (15, 20), (22, 12)], B, 2.2)


def _ico_more(p):
    for x in (7, 16, 25):
        p.oval((x - 2, 14, x + 2, 18), outline=None, fill=G)


def _ico_calendar(p):
    p.rect((4, 6, 28, 28), outline=G, w=2, r=2.5)
    p.line([(4.5, 12), (27.5, 12)], G, 2)
    for x in (10, 16, 22):
        for y in (17, 23):
            p.oval((x - 1.5, y - 1.5, x + 1.5, y + 1.5), outline=None, fill=G)


def _ico_people(p):
    p.oval((10, 4, 22, 16), outline=G, w=2)
    p.arc((5, 18, 27, 40), 180, 360, G, 2)


def _ico_tasks(p):
    p.rect((4, 4, 28, 28), outline=G, w=2, r=3)
    p.line([(9, 16), (14, 21), (23, 11)], G, 2.2)


def _ico_ignore(p):
    _envelope(p, 3, 6, 23, 20)
    p.oval((16, 15, 30, 29), outline=RED, fill=WHITE, w=2)
    p.line([(18.5, 26.5), (27.5, 17.5)], RED, 2)


def _ico_cleanup(p):
    _envelope(p, 3, 5, 23, 19)
    p.line([(28, 12), (20, 25)], B, 2.2)
    p.poly([(16, 23), (23, 27), (21, 30), (14, 28)], outline=None, fill=B)


def _ico_junk(p):
    _envelope(p, 3, 6, 23, 20)
    p.oval((16, 15, 30, 29), outline=None, fill=RED)
    p.line([(20, 22), (26, 22)], WHITE, 2.2)


def _ico_meeting(p):
    p.rect((3, 6, 23, 26), outline=G, w=2, r=2)
    p.line([(3.5, 11), (22.5, 11)], G, 2)
    p.oval((19, 17, 29, 27), outline=None, fill=B)


def _ico_team_email(p):
    _envelope(p, 3, 9, 23, 24)
    p.oval((21, 3, 29, 11), outline=None, fill="#7B83EB")
    p.rect((19, 11, 31, 19), outline=None, fill="#4B53BC", r=3)


def _ico_to_manager(p):
    p.line([(4, 16), (26, 16)], B, 2.4)
    p.line([(19, 9), (26, 16), (19, 23)], B, 2.4)


def _ico_done(p):
    p.line([(5, 17), (12, 24), (27, 8)], "#107C10", 2.6)


def _ico_create_new(p):
    p.line([(16, 5), (16, 27)], B, 2.6)
    p.line([(5, 16), (27, 16)], B, 2.6)


def _ico_reply_delete(p):
    _reply_arrow(p, 3, 12, 0.9)
    p.line([(20, 20), (28, 28)], RED, 2.2)
    p.line([(28, 20), (20, 28)], RED, 2.2)


def _ico_address_book(p):
    p.rect((6, 3, 26, 29), outline=G, w=2, r=2)
    p.oval((12, 8, 20, 16), outline=G, w=1.8)
    p.arc((10, 17, 22, 29), 180, 360, G, 1.8)
    p.line([(3, 9), (7, 9)], G, 2)
    p.line([(3, 16), (7, 16)], G, 2)
    p.line([(3, 23), (7, 23)], G, 2)


def _ico_filter(p):
    p.poly([(4, 5), (28, 5), (19, 16), (19, 27), (13, 23), (13, 16)], outline=G)


def _ico_outlook(p):
    p.rect((11, 4, 30, 28), outline=None, fill="#28A8EA", r=2)
    p.line([(12, 6), (21, 14), (29, 6)], "#0F6CBD", 2)
    p.rect((2, 8, 20, 26), outline=None, fill="#0F6CBD", r=2)
    p.oval((6, 11.5, 16, 22.5), outline=WHITE, w=2.4)


def _ico_sync(p):
    p.arc((5, 5, 27, 27), 200, 340, G, 2.2)
    p.arc((5, 5, 27, 27), 20, 160, G, 2.2)
    p.line([(24, 5), (25.5, 11), (19.5, 11)], G, 2.2)
    p.line([(8, 27), (6.5, 21), (12.5, 21)], G, 2.2)


def _ico_undo(p):
    p.line([(5, 6), (5, 14), (13, 14)], G, 2.2)
    p.arc((5, 7, 27, 29), 200, 350, G, 2.2)


def _ico_save(p):
    p.poly([(4, 4), (24, 4), (28, 8), (28, 28), (4, 28)], outline=G)
    p.rect((10, 4.5, 21, 11), outline=G, w=1.8)
    p.rect((9, 17, 23, 27.5), outline=G, w=1.8)


def _ico_bell(p):
    p.arc((7, 4, 25, 22), 180, 360, G, 2)
    p.line([(7, 13), (7, 21), (4, 24), (28, 24), (25, 21), (25, 13)], G, 2)
    p.arc((12, 22, 20, 30), 0, 180, G, 2)


def _ico_lightbulb(p):
    p.oval((7, 3, 25, 21), outline=G, w=2)
    p.line([(12, 25), (20, 25)], G, 2)
    p.line([(13, 29), (19, 29)], G, 2)


def _ico_chevron_down(p):
    p.line([(6, 12), (16, 22), (26, 12)], G, 2.6)


def _ico_chevron_right(p):
    p.line([(12, 6), (22, 16), (12, 26)], G, 2.6)


def _ico_arrow_reply(p):
    _reply_arrow(p, 4, 12, 1.0, G, 2.2)


def _ico_arrow_reply_all(p):
    _reply_arrow(p, 9, 12, 0.95, G, 2.2)
    p.line([(9, 6), (3, 12), (9, 18)], G, 2.2)


def _ico_arrow_forward(p):
    _reply_arrow(p, 28, 12, 1.0, G, 2.2, mirror=True)


def _ico_sort_up(p):
    p.line([(16, 27), (16, 5)], G, 2.2)
    p.line([(9, 12), (16, 5), (23, 12)], G, 2.2)


def _ico_flag_outline(p):
    p.poly([(9, 5), (27, 5), (22.5, 11.5), (27, 18), (9, 18)], outline=G)
    p.line([(8, 4), (8, 29)], G, 2.2)


ICON_DRAWERS = {k[5:]: v for k, v in globals().items() if k.startswith("_ico_")}


class IconFactory:
    def __init__(self, master):
        self.master = master
        self.cache = {}

    def get(self, name, size=32, disabled=False):
        key = (name, size, disabled)
        if key in self.cache:
            return self.cache[key]
        img = None
        if HAVE_PIL and name in ICON_DRAWERS:
            try:
                ss = 4
                big = Image.new("RGBA", (size * ss, size * ss), (255, 255, 255, 0))
                ICON_DRAWERS[name](_Pen(ImageDraw.Draw(big), size * ss / 32.0))
                im = big.resize((size, size), Image.LANCZOS)
                if disabled:
                    r, g, b_, a = im.split()
                    gray = Image.merge("RGB", (r, g, b_)).convert("L").convert("RGB")
                    a = a.point(lambda v: int(v * 0.35))
                    im = Image.merge("RGBA", (*gray.split(), a))
                img = ImageTk.PhotoImage(im, master=self.master)
            except Exception:
                img = None
        if img is None:
            img = tk.PhotoImage(master=self.master, width=size, height=size)
        self.cache[key] = img
        return img


# ----------------------------------------------------------------------
# Generic widgets
# ----------------------------------------------------------------------
def _bind_tree(widget, sequence, func):
    widget.bind(sequence, func, add="+")
    for child in widget.winfo_children():
        _bind_tree(child, sequence, func)


class FlatButton(tk.Frame):
    """Ribbon-style button: optional icon + text, flat with hover highlight.

    layout="large": icon on top, (multi-line) caption below (big ribbon button)
    layout="small": icon left, caption right (small ribbon row / toolbar)
    Supports .config(state="disabled"/"normal") like a real tk.Button.
    `command=None` makes it purely decorative (hover only, click does nothing).
    """

    def __init__(self, master, text="", icon=None, icons=None, command=None,
                 layout="small", bg=RIBBON_BG, fg=TEXT, font=None, icon_size=None,
                 dropdown=False, enabled=True, padx=6, pady=3, border=None,
                 hover_bg=BUTTON_HOVER, name=None, width=None):
        kw = {"name": name} if name else {}
        super().__init__(master, bg=bg, **kw)
        self._command = command
        self._bg = bg
        self._hover_bg = hover_bg
        self._fg = fg
        self._enabled = enabled
        self._icons = icons
        self._icon_name = icon
        self._icon_size = icon_size or (32 if layout == "large" else 16)
        self._text = text
        if border:
            self.config(highlightthickness=1, highlightbackground=border, highlightcolor=border)
        font = font or (UI_FONT, 9)

        self.icon_label = None
        if icon and icons is not None:
            self.icon_label = tk.Label(self, image=icons.get(icon, self._icon_size), bg=bg, bd=0)
        caption = text + (" \u02c5" if dropdown and text else "")
        self.text_label = tk.Label(self, text=caption, bg=bg, fg=fg, font=font, bd=0,
                                   justify="center")
        if width:
            self.text_label.config(width=width)
        if layout == "large":
            if self.icon_label:
                self.icon_label.pack(side="top", padx=padx, pady=(pady + 2, 2))
            self.text_label.pack(side="top", padx=padx, pady=(0, pady))
        else:
            if self.icon_label:
                self.icon_label.pack(side="left", padx=(padx, 4 if text else padx), pady=pady)
            if text:
                self.text_label.pack(side="left", padx=(0 if self.icon_label else padx, padx), pady=pady)
        for w in (self, self.icon_label, self.text_label):
            if w is None:
                continue
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)
            w.bind("<ButtonRelease-1>", self._on_click)
            w.bind("<Button-1>", self._on_press)
        self._apply_state()

    def _set_bg(self, color):
        tk.Frame.configure(self, bg=color)
        for w in (self.icon_label, self.text_label):
            if w is not None:
                w.configure(bg=color)

    def _on_enter(self, _e=None):
        if self._enabled:
            self._set_bg(self._hover_bg)

    def _on_leave(self, _e=None):
        self._set_bg(self._bg)

    def _on_press(self, _e=None):
        if self._enabled:
            self._set_bg(BUTTON_PRESS)

    def _on_click(self, event=None):
        if not self._enabled:
            return
        # Only fire if released over the button (normal button semantics).
        if event is not None:
            x, y = event.x_root, event.y_root
            x0, y0 = self.winfo_rootx(), self.winfo_rooty()
            inside = x0 <= x < x0 + self.winfo_width() and y0 <= y < y0 + self.winfo_height()
            self._set_bg(self._hover_bg if inside else self._bg)
            if not inside:
                return
        if self._command:
            try:
                self._command()
            except tk.TclError:
                pass

    def invoke(self):
        if self._enabled and self._command:
            return self._command()

    def _apply_state(self):
        self.text_label.configure(fg=self._fg if self._enabled else TEXT_DISABLED)
        if self.icon_label is not None and self._icons is not None:
            self.icon_label.configure(
                image=self._icons.get(self._icon_name, self._icon_size, disabled=not self._enabled))
        if not self._enabled:
            self._set_bg(self._bg)

    def config(self, **kw):
        state = kw.pop("state", None)
        if kw:
            tk.Frame.configure(self, **kw)
        if state == "disabled":
            self._enabled = False
            self._apply_state()
        elif state == "normal":
            self._enabled = True
            self._apply_state()

    configure = config

    def cget(self, key):
        if key == "state":
            return "normal" if self._enabled else "disabled"
        if key == "text":
            return self._text
        return tk.Frame.cget(self, key)


# Backwards-compatible name used by earlier versions of this mirror.
ColorButton = FlatButton


class RibbonGroup(tk.Frame):
    """A ribbon group: content area + caption at the bottom + right separator."""

    def __init__(self, master, caption, separator=True):
        super().__init__(master, bg=RIBBON_BG)
        self.body = tk.Frame(self, bg=RIBBON_BG)
        self.body.pack(side="top", fill="both", expand=True, padx=2)
        tk.Label(self, text=caption, bg=RIBBON_BG, fg=TEXT_SECONDARY,
                 font=(UI_FONT, 8)).pack(side="bottom", pady=(0, 2))
        self.separator = separator

    def column(self):
        col = tk.Frame(self.body, bg=RIBBON_BG)
        col.pack(side="left", fill="y", anchor="n", pady=(2, 0))
        return col


def ribbon_separator(parent):
    sep = tk.Frame(parent, bg=RIBBON_BG, width=9)
    tk.Frame(sep, bg=BORDER, width=1).pack(fill="y", expand=True, pady=6)
    return sep


# ----------------------------------------------------------------------
# Message list (custom-drawn, fixed-height two/three-line items)
# ----------------------------------------------------------------------
class MessageList(tk.Frame):
    """Outlook-style message list drawn on a Canvas.

    Row i occupies canvas y = [i*ROW_HEIGHT, (i+1)*ROW_HEIGHT). A single click
    selects the row and calls on_select(index). Exposes a small Listbox-like
    API (size/curselection/selection_set/selection_clear/get) so code written
    against the old `inbox_listbox` keeps working.
    """

    def __init__(self, master, emails, on_select, name="inbox_listbox"):
        super().__init__(master, bg="#FFFFFF", name=name)
        self.emails = emails
        self.on_select = on_select
        self.selected = None
        self.hover = None
        self.unread = [True] * len(emails)
        self.canvas = tk.Canvas(self, bg="#FFFFFF", highlightthickness=0, bd=0,
                                name="message_canvas")
        self.vbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self._on_yscroll)
        self.canvas.pack(side="left", fill="both", expand=True)
        self._vbar_shown = False
        self.f_sender = tkfont.Font(root=self, family=UI_FONT, size=10)
        self.f_sender_b = tkfont.Font(root=self, family=UI_FONT, size=10, weight="bold")
        self.f_subject = tkfont.Font(root=self, family=UI_FONT, size=9)
        self.f_subject_b = tkfont.Font(root=self, family="Segoe UI Semibold", size=9)
        self.f_small = tkfont.Font(root=self, family=UI_FONT, size=9)
        self.canvas.bind("<Configure>", lambda e: self.redraw())
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Leave>", self._on_leave)
        self.canvas.bind("<MouseWheel>", self._on_wheel)

    # -- Listbox-compatible API --
    def size(self):
        return len(self.emails)

    def curselection(self):
        return () if self.selected is None else (self.selected,)

    def selection_clear(self, *_args):
        self.selected = None
        self.redraw()

    def selection_set(self, index, *_args):
        self.selected = int(index)
        self.redraw()

    def get(self, index):
        e = self.emails[int(index)]
        return f"{e['sender_name']} - {e['subject']}"

    def mark_read(self, index):
        self.unread[index] = False
        self.redraw()

    def unread_count(self):
        return sum(1 for u in self.unread if u)

    # -- events --
    def _row_at(self, y):
        idx = int(self.canvas.canvasy(y) // ROW_HEIGHT)
        return idx if 0 <= idx < len(self.emails) else None

    def _on_click(self, event):
        idx = self._row_at(event.y)
        if idx is not None:
            self.on_select(idx)

    def _on_motion(self, event):
        idx = self._row_at(event.y)
        if idx != self.hover:
            self.hover = idx
            self.redraw()

    def _on_leave(self, _e):
        if self.hover is not None:
            self.hover = None
            self.redraw()

    def _on_wheel(self, event):
        if self._vbar_shown:
            self.canvas.yview_scroll(int(-event.delta / 120) * 3, "units")

    def _on_yscroll(self, first, last):
        need = not (float(first) <= 0.0 and float(last) >= 1.0)
        if need and not self._vbar_shown:
            self.vbar.pack(side="right", fill="y", before=self.canvas)
            self._vbar_shown = True
        elif not need and self._vbar_shown:
            self.vbar.pack_forget()
            self._vbar_shown = False
        self.vbar.set(first, last)

    # -- drawing --
    def redraw(self):
        c = self.canvas
        c.delete("all")
        w = max(c.winfo_width(), 200)
        for i, e in enumerate(self.emails):
            y0 = i * ROW_HEIGHT
            unread = self.unread[i]
            selected = i == self.selected
            bg = SELECTION_BLUE if selected else (HOVER_GRAY if i == self.hover else "#FFFFFF")
            c.create_rectangle(0, y0, w, y0 + ROW_HEIGHT, fill=bg, outline="")
            if selected or unread:
                c.create_rectangle(0, y0, 3, y0 + ROW_HEIGHT - 1,
                                   fill=OUTLOOK_BLUE, outline="")
            left, right = 22, w - 12
            time_txt = list_time_text(e["received"])
            tfont = self.f_subject_b if unread else self.f_small
            time_w = tfont.measure(time_txt)
            sfont = self.f_sender_b if unread else self.f_sender
            c.create_text(left, y0 + 7, anchor="nw", fill=TEXT, font=sfont,
                          text=elide(sfont, e["sender_name"], right - left - 26))
            # decorative flag hover icon slot (right of sender)
            subj_font = self.f_subject_b if unread else self.f_subject
            c.create_text(left, y0 + 27, anchor="nw",
                          fill=OUTLOOK_BLUE if unread else TEXT, font=subj_font,
                          text=elide(subj_font, e["subject"], right - left - time_w - 10))
            c.create_text(right, y0 + 27, anchor="ne", font=tfont,
                          fill=OUTLOOK_BLUE if unread else TEXT_SECONDARY, text=time_txt)
            c.create_text(left, y0 + 45, anchor="nw", fill=TEXT_SECONDARY, font=self.f_small,
                          text=elide(self.f_small, preview_text(e["body"]), right - left))
            if not selected:
                c.create_line(left, y0 + ROW_HEIGHT - 1, w, y0 + ROW_HEIGHT - 1, fill=DIVIDER)
        c.configure(scrollregion=(0, 0, w, max(len(self.emails) * ROW_HEIGHT, 1)))


# ----------------------------------------------------------------------
# Compose / Reply window
# ----------------------------------------------------------------------
class ComposeWindow(tk.Toplevel):
    """
    Compose / Reply window (classic Outlook "Message (HTML)" inspector).

    Field order (top to bottom, and Tab order):
        1. To         -> Entry   (name="to_entry")
        2. Cc         -> Entry   (name="cc_entry", decorative - not logged)
        3. Subject    -> Entry   (name="subject_entry")
        4. Body       -> Text    (name="body_text")
    Send is the big "Send" button at the left of the header (name="send_button").

    Window title:
      - New message:   "Untitled - Message (HTML)"
      - Reply message: "RE: <original subject> - Message (HTML)"
    """

    def __init__(self, master, app, mode="new", source_email=None):
        super().__init__(master, name="compose_window")
        self.app = app
        self.mode = mode
        self.source_email = source_email
        self.result = None  # set to the sent dict once Send is clicked
        icons = app.icons if app is not None and hasattr(app, "icons") else IconFactory(self)
        self.icons = icons

        prefill_to = ""
        prefill_subject = ""
        prefill_body = ""
        if mode == "reply" and source_email is not None:
            self.title(REPLY_TITLE_FMT.format(subject=source_email["subject"]))
            prefill_to = source_email["sender_email"]
            prefill_subject = "RE: " + source_email["subject"]
            prefill_body = quote_body(source_email)
        else:
            self.title(NEW_MESSAGE_TITLE)

        self.geometry(COMPOSE_GEOMETRY)
        self.resizable(True, True)
        self.minsize(700, 500)
        self.configure(bg=APP_BG)

        body_family = font_family(self, "Aptos", "Calibri", UI_FONT)
        normal = (UI_FONT, 9)

        # ---- tab row ----
        tabs = tk.Frame(self, bg=APP_BG, height=30, name="tab_row")
        tabs.pack(side="top", fill="x")
        tabs.pack_propagate(False)
        for t in ("File", "Message", "Insert", "Draw", "Options", "Format Text", "Review", "Help"):
            selected = t == "Message"
            cell = tk.Frame(tabs, bg=APP_BG)
            cell.pack(side="left", padx=(8 if t == "File" else 0, 0))
            tk.Label(cell, text=t, bg=APP_BG, fg=TEXT,
                     font=("Segoe UI Semibold", 9) if selected else normal,
                     padx=8).pack(side="top", pady=(5, 1))
            tk.Frame(cell, bg=OUTLOOK_BLUE if selected else APP_BG, height=2).pack(
                side="top", fill="x", padx=10)
        tell = FlatButton(tabs, text="Tell me what you want to do", icon="lightbulb",
                          icons=icons, bg=APP_BG, hover_bg=BUTTON_HOVER, fg=TEXT_SECONDARY)
        tell.pack(side="left", padx=(18, 0), pady=3)

        # ---- simplified (single-line) ribbon ----
        ribbon_wrap = tk.Frame(self, bg=APP_BG)
        ribbon_wrap.pack(side="top", fill="x", padx=8, pady=(2, 6))
        ribbon = tk.Frame(ribbon_wrap, bg=RIBBON_BG, height=40, highlightthickness=1,
                          highlightbackground=BORDER, name="ribbon")
        ribbon.pack(fill="x")
        ribbon.pack_propagate(False)

        def tool(icon, text="", dropdown=False):
            b = FlatButton(ribbon, text=text, icon=icon, icons=icons, dropdown=dropdown,
                           padx=5, pady=5)
            b.pack(side="left", padx=1, pady=4)
            return b

        def sep():
            tk.Frame(ribbon, bg=BORDER, width=1).pack(side="left", fill="y", pady=9, padx=5)

        tool("paste", dropdown=True)
        tool("painter")
        sep()
        font_box = tk.Frame(ribbon, bg=RIBBON_BG, highlightthickness=1, highlightbackground="#C7C7C7")
        font_box.pack(side="left", padx=(2, 4), pady=8)
        tk.Label(font_box, text=f"{body_family} (Body)", width=15, anchor="w", bg=RIBBON_BG,
                 fg=TEXT, font=normal).pack(side="left", padx=(5, 0))
        tk.Label(font_box, text="\u02c5", bg=RIBBON_BG, fg=TEXT_SECONDARY, font=normal).pack(side="left", padx=3)
        size_box = tk.Frame(ribbon, bg=RIBBON_BG, highlightthickness=1, highlightbackground="#C7C7C7")
        size_box.pack(side="left", padx=(0, 6), pady=8)
        tk.Label(size_box, text="11", width=3, anchor="w", bg=RIBBON_BG, fg=TEXT,
                 font=normal).pack(side="left", padx=(5, 0))
        tk.Label(size_box, text="\u02c5", bg=RIBBON_BG, fg=TEXT_SECONDARY, font=normal).pack(side="left", padx=3)
        for txt, fnt in (("B", (UI_FONT, 10, "bold")), ("I", (UI_FONT, 10, "italic")),
                         ("U", (UI_FONT, 10, "underline"))):
            FlatButton(ribbon, text=txt, font=fnt, padx=8, pady=4).pack(side="left", padx=1, pady=4)
        tool("highlight", dropdown=True)
        tool("font_color", dropdown=True)
        tool("more")
        sep()
        tool("attach", "Attach File", dropdown=True)
        tool("link", "Link", dropdown=True)
        tool("signature", "Signature", dropdown=True)
        sep()
        tool("follow_up", dropdown=True)
        tool("dictate", dropdown=True)
        tool("sensitivity", dropdown=True)
        tool("more")

        # ---- header: Send / To / Cc / Subject ----
        header = tk.Frame(self, bg=APP_BG, name="header")
        header.pack(side="top", fill="x", padx=8)

        send_col = tk.Frame(header, bg=APP_BG)
        send_col.pack(side="left", anchor="n", padx=(4, 10), pady=(2, 0))
        self.send_button = FlatButton(
            send_col, text="Send", icon="send", icons=icons, command=self.send,
            name="send_button", layout="large", icon_size=32, bg="#FFFFFF",
            border="#D1D1D1", padx=14, pady=8, font=(UI_FONT, 9),
        )
        self.send_button.pack(side="top")

        fields = tk.Frame(header, bg=APP_BG)
        fields.pack(side="left", fill="x", expand=True)
        fields.grid_columnconfigure(1, weight=1)

        def field_button(row, text, name):
            b = FlatButton(fields, text=text, bg="#FFFFFF", border="#D1D1D1",
                           hover_bg=BUTTON_HOVER, padx=0, pady=3, width=8, name=name,
                           command=lambda: self._focus_field(row))
            b.grid(row=row, column=0, sticky="w", pady=(2, 4), padx=(0, 10))
            return b

        def field_entry(row, var, name):
            wrap = tk.Frame(fields, bg=APP_BG)
            wrap.grid(row=row, column=1, sticky="we", pady=(2, 4), padx=(0, 6))
            e = tk.Entry(wrap, textvariable=var, name=name, font=(UI_FONT, 10), relief="flat",
                         bd=0, bg=APP_BG, fg=TEXT, insertbackground=TEXT,
                         highlightthickness=0)
            e.pack(side="top", fill="x", ipady=3)
            tk.Frame(wrap, bg="#C7C7C7", height=1).pack(side="top", fill="x")
            return e

        self.to_var = tk.StringVar(master=self, value=prefill_to)
        self.cc_var = tk.StringVar(master=self, value="")
        self.subject_var = tk.StringVar(master=self, value=prefill_subject)

        field_button(0, "To", "to_label")
        self.to_entry = field_entry(0, self.to_var, "to_entry")
        field_button(1, "Cc", "cc_label")
        self.cc_entry = field_entry(1, self.cc_var, "cc_entry")
        tk.Label(fields, text="Subject", bg=APP_BG, fg=TEXT, font=normal, width=8,
                 anchor="e", name="subject_label").grid(row=2, column=0, sticky="w",
                                                        pady=(2, 6), padx=(0, 10))
        subj_wrap = tk.Frame(fields, bg=APP_BG)
        subj_wrap.grid(row=2, column=1, sticky="we", pady=(2, 6), padx=(0, 6))
        self.status_var = tk.StringVar(master=self, value="")
        self.status_label = tk.Label(subj_wrap, textvariable=self.status_var, fg="#107C10",
                                     bg=APP_BG, font=("Segoe UI Semibold", 9), name="status_label")
        self.status_label.pack(side="right", padx=(6, 0))
        tk.Label(subj_wrap, image=icons.get("sensitivity", 16), bg=APP_BG).pack(side="right", padx=4)
        self.subject_entry = tk.Entry(subj_wrap, textvariable=self.subject_var, name="subject_entry",
                                      font=(UI_FONT, 10), relief="flat", bd=0, bg=APP_BG, fg=TEXT,
                                      insertbackground=TEXT, highlightthickness=0)
        self.subject_entry.pack(side="top", fill="x", ipady=3)
        tk.Frame(subj_wrap, bg="#C7C7C7", height=1).pack(side="top", fill="x")

        # ---- body ----
        body_wrap = tk.Frame(self, bg="#FFFFFF", highlightthickness=1,
                             highlightbackground=BORDER, name="body_frame")
        body_wrap.pack(side="top", fill="both", expand=True, padx=8, pady=(4, 8))
        body_scroll = tk.Scrollbar(body_wrap, orient="vertical")
        self.body_text = tk.Text(body_wrap, wrap="word", name="body_text",
                                 font=(body_family, 11), relief="flat", bd=0,
                                 highlightthickness=0, padx=14, pady=12, fg="#000000",
                                 insertbackground="#000000", undo=True,
                                 yscrollcommand=body_scroll.set)
        body_scroll.config(command=self.body_text.yview)
        body_scroll.pack(side="right", fill="y")
        self.body_text.pack(side="left", fill="both", expand=True)
        if prefill_body:
            self.body_text.insert("1.0", prefill_body)
        self.body_text.mark_set("insert", "1.0")

    def _focus_field(self, row):
        try:
            (self.to_entry, self.cc_entry)[row].focus_set()
        except (tk.TclError, IndexError):
            pass

    def get_fields(self):
        return {
            "to": self.to_var.get(),
            "subject": self.subject_var.get(),
            "body": self.body_text.get("1.0", "end-1c"),
        }

    def send(self):
        """
        Send does NOT touch the network. It appends the composed message as
        one JSON line to data/sent_log.jsonl, shows a brief "Sent"
        confirmation, and closes the window shortly after.
        """
        fields = self.get_fields()
        entry = {
            "to": fields["to"],
            "subject": fields["subject"],
            "body": fields["body"],
            "timestamp": datetime.now().isoformat(),
        }
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(SENT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        self.result = entry
        self.status_var.set("Sent")
        self.send_button.config(state="disabled")
        self.app.on_compose_sent(entry)
        # Give a human user a moment to see "Sent" before the window closes.
        # (In headless self-tests, this callback is simply never pumped -
        # the log write above already happened synchronously.)
        try:
            self.after(700, self.destroy)
        except tk.TclError:
            pass


# ----------------------------------------------------------------------
# Main window
# ----------------------------------------------------------------------
class OutlookMirrorApp(tk.Frame):
    """
    Main inbox window (classic Outlook explorer).

    Widgets an automation cares about:
      - Message list:   MessageList (canvas), name="inbox_listbox"; also
                        available as `app.inbox_list` / `app.inbox_listbox`.
                        Rows in data/inbox.json order, ROW_HEIGHT px each.
      - Reading pane:   subject_var / from_var / received_var, Text
                        name="body_value" (read-only body).
      - "New Email":    ribbon Home > New, name="new_email_button".
      - "Reply":        ribbon Home > Respond, name="reply_button"
                        (enabled only once an inbox row is selected). The
                        reading-pane header has its own Reply button too
                        (`pane_reply_button`).
    """

    def __init__(self, master):
        super().__init__(master, name="main_frame", bg=APP_BG)
        self.master = master
        self.emails = load_inbox()
        self.selected_index = None
        self.active_compose = None
        self.last_sent = None  # most recent entry sent, for verification
        self.icons = IconFactory(master)

        master.title(MAIN_WINDOW_TITLE)
        master.geometry(MAIN_GEOMETRY)
        master.minsize(1000, 600)
        master.configure(bg=APP_BG)
        try:
            master.iconphoto(True, self.icons.get("outlook", 32))
        except tk.TclError:
            pass

        self.pack(fill="both", expand=True)
        self._build_widgets()
        self._update_status()

    # ---------- UI construction ----------

    def _build_widgets(self):
        self._build_top_bar()
        self._build_tabs()
        self._build_ribbon()
        self._build_status_bar()
        body = tk.Frame(self, bg=APP_BG, name="body_frame")
        body.pack(side="top", fill="both", expand=True)
        self._build_folder_pane(body)
        self._build_message_list(body)
        self._build_reading_pane(body)

    def _build_top_bar(self):
        ic = self.icons
        bar = tk.Frame(self, bg=APP_BG, height=38, name="top_bar")
        bar.pack(side="top", fill="x")
        bar.pack_propagate(False)
        tk.Label(bar, image=ic.get("outlook", 20), bg=APP_BG).pack(side="left", padx=(12, 8))
        for name in ("sync", "undo"):
            FlatButton(bar, icon=name, icons=ic, bg=APP_BG, padx=5, pady=5).pack(side="left", padx=1)
        # Search box (decorative)
        search = tk.Frame(bar, bg="#FFFFFF", highlightthickness=1, highlightbackground="#D1D1D1",
                          name="search_box")
        search.place(relx=0.5, rely=0.5, anchor="center", width=520, height=28)
        tk.Label(search, image=ic.get("search", 16), bg="#FFFFFF").pack(side="left", padx=(10, 6))
        tk.Label(search, text="Search", bg="#FFFFFF", fg=TEXT_SECONDARY,
                 font=(UI_FONT, 10)).pack(side="left")
        right = tk.Frame(bar, bg=APP_BG)
        right.pack(side="right", padx=10)
        FlatButton(right, icon="bell", icons=ic, bg=APP_BG, padx=5, pady=5).pack(side="left", padx=4)
        av = tk.Canvas(right, width=28, height=28, bg=APP_BG, highlightthickness=0)
        av.pack(side="left", padx=4)
        av.create_oval(2, 2, 26, 26, fill="#5C2E91", outline="")
        av.create_text(14, 14, text=avatar_initials(ACCOUNT_NAME), fill="#FFFFFF",
                       font=(UI_FONT, 8, "bold"))

    def _build_tabs(self):
        tabs = tk.Frame(self, bg=APP_BG, height=30, name="tab_row")
        tabs.pack(side="top", fill="x")
        tabs.pack_propagate(False)
        for t in ("File", "Home", "Send / Receive", "Folder", "View", "Help"):
            selected = t == "Home"
            cell = tk.Frame(tabs, bg=APP_BG)
            cell.pack(side="left", padx=(10 if t == "File" else 0, 0))
            lbl = tk.Label(cell, text=t, bg=APP_BG, fg=TEXT,
                           font=("Segoe UI Semibold", 9) if selected else (UI_FONT, 9), padx=9)
            lbl.pack(side="top", pady=(5, 1))
            tk.Frame(cell, bg=OUTLOOK_BLUE if selected else APP_BG, height=2).pack(
                side="top", fill="x", padx=10)

    def _build_ribbon(self):
        ic = self.icons
        wrap = tk.Frame(self, bg=APP_BG, name="ribbon_wrap")
        wrap.pack(side="top", fill="x", padx=8, pady=(1, 6))
        ribbon = tk.Frame(wrap, bg=RIBBON_BG, height=96, highlightthickness=1,
                          highlightbackground=BORDER, name="ribbon")
        ribbon.pack(fill="x")
        ribbon.pack_propagate(False)
        tk.Label(ribbon, image=ic.get("chevron_down", 12), bg=RIBBON_BG).place(
            relx=1.0, rely=1.0, x=-6, y=-4, anchor="se")

        def large(parent, text, icon, command=None, dropdown=False, enabled=True, name=None):
            b = FlatButton(parent, text=text, icon=icon, icons=ic, command=command,
                           layout="large", dropdown=dropdown, enabled=enabled, padx=4, pady=2,
                           name=name)
            b.pack(side="left", anchor="n", padx=1, pady=(3, 0))
            return b

        def small(parent, text, icon, dropdown=False):
            b = FlatButton(parent, text=text, icon=icon, icons=ic, dropdown=dropdown,
                           padx=4, pady=2)
            b.pack(side="top", anchor="w", pady=0)
            return b

        def group(caption, last=False):
            g = RibbonGroup(ribbon, caption)
            g.pack(side="left", fill="y")
            if not last:
                ribbon_separator(ribbon).pack(side="left", fill="y")
            return g

        g = group("New")
        self.new_email_button = large(g.body, "New\nEmail", "new_email", self.open_new_email,
                                      name="new_email_button")
        large(g.body, "New\nItems", "new_items", dropdown=True)

        g = group("Delete")
        col = g.column()
        small(col, "Ignore", "ignore")
        small(col, "Clean Up", "cleanup", dropdown=True)
        small(col, "Junk", "junk", dropdown=True)
        large(g.body, "Delete", "delete")
        large(g.body, "Archive", "archive")

        g = group("Respond")
        self.reply_button = large(g.body, "Reply", "reply", self.open_reply, enabled=False,
                                  name="reply_button")
        self.reply_all_button = large(g.body, "Reply\nAll", "reply_all", self.open_reply,
                                      enabled=False)
        self.forward_button = large(g.body, "Forward", "forward", None, enabled=False)
        col = g.column()
        small(col, "Meeting", "meeting")
        small(col, "Teams", "team_email")
        small(col, "More", "more", dropdown=True)

        g = group("Teams")
        large(g.body, "Share to\nTeams", "teams")

        g = group("Quick Steps")
        qs = tk.Frame(g.body, bg=RIBBON_BG, highlightthickness=1, highlightbackground=BORDER)
        qs.pack(side="left", fill="y", pady=(4, 2), padx=2)
        c1 = tk.Frame(qs, bg=RIBBON_BG)
        c1.pack(side="left", anchor="n")
        c2 = tk.Frame(qs, bg=RIBBON_BG)
        c2.pack(side="left", anchor="n")
        small(c1, "Move to: ?", "move")
        small(c1, "Team Email", "team_email")
        small(c1, "Reply & Delete", "reply_delete")
        small(c2, "To Manager", "to_manager")
        small(c2, "Done", "done")
        small(c2, "Create New", "create_new")

        g = group("Move")
        large(g.body, "Move", "move", dropdown=True)
        large(g.body, "Rules", "rules", dropdown=True)
        large(g.body, "Send to\nOneNote", "onenote")

        g = group("Tags")
        large(g.body, "Unread/\nRead", "unread_read")
        large(g.body, "Categorize", "categorize", dropdown=True)
        large(g.body, "Follow\nUp", "follow_up", dropdown=True)

        g = group("Find")
        col = g.column()
        sp = tk.Frame(col, bg=RIBBON_BG, highlightthickness=1, highlightbackground="#C7C7C7")
        sp.pack(side="top", anchor="w", padx=4, pady=(3, 2))
        tk.Label(sp, text="Search People", width=16, anchor="w", bg=RIBBON_BG,
                 fg=TEXT_SECONDARY, font=(UI_FONT, 8)).pack(side="left", padx=4, pady=1)
        small(col, "Address Book", "address_book")
        small(col, "Filter Email", "filter", dropdown=True)

        g = group("Speech")
        large(g.body, "Read\nAloud", "read_aloud")
        g = group("Add-ins", last=True)
        large(g.body, "Get\nAdd-ins", "addins")

    def _build_status_bar(self):
        bar = tk.Frame(self, bg=APP_BG, height=26, name="status_bar")
        bar.pack(side="bottom", fill="x")
        bar.pack_propagate(False)
        tk.Frame(bar, bg=BORDER, height=1).pack(side="top", fill="x")
        self.status_items_var = tk.StringVar(master=self, value="")
        self.status_unread_var = tk.StringVar(master=self, value="")
        tk.Label(bar, textvariable=self.status_items_var, bg=APP_BG, fg=TEXT,
                 font=(UI_FONT, 8)).pack(side="left", padx=(12, 14))
        tk.Label(bar, textvariable=self.status_unread_var, bg=APP_BG, fg=TEXT,
                 font=(UI_FONT, 8)).pack(side="left", padx=(0, 14))
        tk.Label(bar, text="\u23f0 Reminders: 0", bg=APP_BG, fg=TEXT,
                 font=(UI_FONT, 8)).pack(side="left")
        zoom = tk.Canvas(bar, width=150, height=20, bg=APP_BG, highlightthickness=0)
        zoom.pack(side="right", padx=(0, 6))
        zoom.create_text(8, 10, text="\u2212", fill=TEXT_SECONDARY, font=(UI_FONT, 9))
        zoom.create_line(18, 10, 108, 10, fill="#8A8A8A")
        zoom.create_rectangle(61, 5, 65, 15, fill="#5C5C5C", outline="")
        zoom.create_text(116, 10, text="+", fill=TEXT_SECONDARY, font=(UI_FONT, 9))
        zoom.create_text(134, 10, text="100%", fill=TEXT, font=(UI_FONT, 8))
        views = tk.Canvas(bar, width=46, height=20, bg=APP_BG, highlightthickness=0)
        views.pack(side="right", padx=4)
        views.create_rectangle(3, 4, 19, 16, outline="#5C5C5C", fill="#D6D6D6")
        views.create_line(9, 4, 9, 16, fill="#5C5C5C")
        views.create_rectangle(27, 4, 43, 16, outline="#5C5C5C")
        views.create_line(27, 10, 43, 10, fill="#5C5C5C")
        tk.Label(bar, text="Connected to: Microsoft Exchange", bg=APP_BG, fg=TEXT,
                 font=(UI_FONT, 8)).pack(side="right", padx=12)
        tk.Label(bar, text="All folders are up to date.", bg=APP_BG, fg=TEXT,
                 font=(UI_FONT, 8)).pack(side="right", padx=4)

    def _build_folder_pane(self, body):
        ic = self.icons
        pane = tk.Frame(body, bg=APP_BG, width=210, name="folder_pane")
        pane.pack(side="left", fill="y")
        pane.pack_propagate(False)

        nav = tk.Frame(pane, bg=APP_BG, height=40)
        nav.pack(side="bottom", fill="x")
        for i, name in enumerate(("mail", "calendar", "people", "tasks", "more")):
            b = FlatButton(nav, icon=name, icons=ic, bg=APP_BG, padx=7, pady=6, icon_size=20)
            b.pack(side="left", padx=(10 if i == 0 else 2, 0), pady=4)
            if name == "mail":
                b.icon_label.configure(image=ic.get("mail", 20))
                tk.Frame(b, bg=OUTLOOK_BLUE, height=2).place(relx=0.2, rely=1.0, relwidth=0.6,
                                                              anchor="sw")

        tree = tk.Frame(pane, bg=APP_BG)
        tree.pack(side="top", fill="both", expand=True, pady=(6, 0))
        self._folder_rows = []

        def heading(text, expanded=True):
            row = tk.Frame(tree, bg=APP_BG)
            row.pack(side="top", fill="x", pady=(6, 2))
            tk.Label(row, image=ic.get("chevron_down" if expanded else "chevron_right", 10),
                     bg=APP_BG).pack(side="left", padx=(10, 6))
            tk.Label(row, text=text, bg=APP_BG, fg=TEXT, font=("Segoe UI Semibold", 10),
                     anchor="w").pack(side="left")

        def folder(text, count=None, selected=False, expandable=False):
            bg = "#D6D6D6" if selected else APP_BG
            row = tk.Frame(tree, bg=bg, height=24)
            row.pack(side="top", fill="x", padx=(6, 6))
            row.pack_propagate(False)
            if expandable:
                tk.Label(row, image=ic.get("chevron_right", 9), bg=bg).pack(side="left", padx=(12, 0))
                pad = 6
            else:
                pad = 33
            name = tk.Label(row, text=text, bg=bg, fg=TEXT, anchor="w",
                            font=("Segoe UI Semibold", 9) if (selected or count) else (UI_FONT, 9))
            name.pack(side="left", padx=(pad, 0))
            cnt = None
            if count is not None:
                cnt = tk.Label(row, text=str(count), bg=bg, fg=OUTLOOK_BLUE,
                               font=("Segoe UI Semibold", 9))
                cnt.pack(side="right", padx=8)
            widgets = [row, name] + ([cnt] if cnt else [])

            def enter(_e, ws=widgets, sel=selected):
                if not sel:
                    for w in ws:
                        w.configure(bg=BUTTON_HOVER)
                for w in row.winfo_children():
                    w.configure(bg=BUTTON_HOVER if not sel else bg)

            def leave(_e, ws=widgets):
                for w in ws:
                    w.configure(bg=bg)
                for w in row.winfo_children():
                    w.configure(bg=bg)
            _bind_tree(row, "<Enter>", enter)
            _bind_tree(row, "<Leave>", leave)
            return cnt

        heading("Favourites")
        self.fav_inbox_count = folder("Inbox", 0, selected=True)
        folder("Sent Items")
        folder("Deleted Items")
        heading(ACCOUNT_EMAIL if len(ACCOUNT_EMAIL) < 26 else "Renewals Team")
        self.inbox_count = folder("Inbox", 0, expandable=True)
        folder("Drafts")
        folder("Sent Items")
        folder("Deleted Items", expandable=True)
        folder("Archive")
        folder("Conversation History", expandable=True)
        folder("Junk Email")
        folder("Outbox")
        folder("RSS Feeds")
        folder("Search Folders", expandable=True)
        heading("Groups", expanded=False)

    def _build_message_list(self, body):
        ic = self.icons
        outer = tk.Frame(body, bg="#FFFFFF", width=350, name="list_frame",
                         highlightthickness=1, highlightbackground=BORDER)
        outer.pack(side="left", fill="y", pady=(0, 0))
        outer.pack_propagate(False)
        header = tk.Frame(outer, bg="#FFFFFF", height=40, name="list_header")
        header.pack(side="top", fill="x")
        header.pack_propagate(False)
        for t, sel in (("All", True), ("Unread", False)):
            cell = tk.Frame(header, bg="#FFFFFF")
            cell.pack(side="left", padx=(14 if t == "All" else 6, 0))
            tk.Label(cell, text=t, bg="#FFFFFF", fg=OUTLOOK_BLUE if sel else TEXT,
                     font=("Segoe UI Semibold", 10) if sel else (UI_FONT, 10)).pack(side="top", pady=(8, 0))
            tk.Frame(cell, bg=OUTLOOK_BLUE if sel else "#FFFFFF", height=2).pack(side="top", fill="x")
        FlatButton(header, icon="sort_up", icons=ic, bg="#FFFFFF", padx=4, pady=4,
                   icon_size=14).pack(side="right", padx=(0, 8))
        FlatButton(header, text="By Date", bg="#FFFFFF", dropdown=True, padx=4, pady=3,
                   font=(UI_FONT, 9)).pack(side="right", padx=2)

        self.inbox_list = MessageList(outer, self.emails, self.select_email, name="inbox_listbox")
        self.inbox_list.pack(side="top", fill="both", expand=True)
        # Backwards-compatible alias (the old plain Listbox's attribute name).
        self.inbox_listbox = self.inbox_list

    def _build_reading_pane(self, body):
        ic = self.icons
        pane = tk.Frame(body, bg="#FFFFFF", name="reading_frame",
                        highlightthickness=1, highlightbackground=BORDER)
        pane.pack(side="left", fill="both", expand=True, padx=(4, 8))
        self.reading_frame = pane

        header = tk.Frame(pane, bg="#FFFFFF", name="reading_header")
        header.pack(side="top", fill="x", padx=(20, 14), pady=(14, 6))

        self.subject_var = tk.StringVar(master=self, value="")
        self.subject_label = tk.Label(header, textvariable=self.subject_var, name="subject_value",
                                      anchor="w", font=(UI_FONT, 14), bg="#FFFFFF", fg=TEXT,
                                      justify="left", wraplength=760)
        self.subject_label.pack(side="top", anchor="w", fill="x", pady=(0, 10))

        sender_row = tk.Frame(header, bg="#FFFFFF")
        sender_row.pack(side="top", fill="x")

        self.avatar_canvas = tk.Canvas(sender_row, width=44, height=44, bg="#FFFFFF",
                                       highlightthickness=0)
        self.avatar_canvas.pack(side="left", anchor="n", padx=(0, 12))

        actions = tk.Frame(sender_row, bg="#FFFFFF")
        actions.pack(side="right", anchor="n")
        btns = tk.Frame(actions, bg="#FFFFFF")
        btns.pack(side="top", anchor="e")
        grp = tk.Frame(btns, bg="#D1D1D1")
        grp.pack(side="left")
        self.pane_reply_button = FlatButton(grp, text="Reply", icon="arrow_reply", icons=ic,
                                            command=self.open_reply, padx=8, pady=4,
                                            name="pane_reply_button")
        self.pane_reply_button.pack(side="left", padx=(1, 0), pady=1)
        self.pane_reply_all_button = FlatButton(grp, text="Reply All", icon="arrow_reply_all",
                                                icons=ic, command=self.open_reply, padx=8, pady=4)
        self.pane_reply_all_button.pack(side="left", padx=(1, 0), pady=1)
        self.pane_forward_button = FlatButton(grp, text="Forward", icon="arrow_forward", icons=ic,
                                              padx=8, pady=4)
        self.pane_forward_button.pack(side="left", padx=1, pady=1)
        tm = tk.Frame(btns, bg="#D1D1D1")
        tm.pack(side="left", padx=(6, 0))
        FlatButton(tm, icon="teams", icons=ic, padx=6, pady=4).pack(padx=1, pady=1)
        mo = tk.Frame(btns, bg="#D1D1D1")
        mo.pack(side="left", padx=(6, 0))
        FlatButton(mo, icon="more", icons=ic, padx=6, pady=4).pack(padx=1, pady=1)
        self.received_var = tk.StringVar(master=self, value="")
        tk.Label(actions, textvariable=self.received_var, name="received_value", anchor="e",
                 font=(UI_FONT, 9), fg=TEXT_SECONDARY, bg="#FFFFFF").pack(side="top", anchor="e",
                                                                          pady=(6, 0))

        sender_text_col = tk.Frame(sender_row, bg="#FFFFFF")
        sender_text_col.pack(side="left", fill="x", expand=True, anchor="n")
        self.from_var = tk.StringVar(master=self, value="")
        tk.Label(sender_text_col, textvariable=self.from_var, name="from_value", anchor="w",
                 font=(UI_FONT, 10), fg=TEXT, bg="#FFFFFF").pack(side="top", anchor="w", pady=(2, 0))
        self.to_line_var = tk.StringVar(master=self, value="")
        tk.Label(sender_text_col, textvariable=self.to_line_var, anchor="w",
                 font=(UI_FONT, 9), fg=TEXT_SECONDARY, bg="#FFFFFF").pack(side="top", anchor="w",
                                                                          pady=(2, 0))

        body_wrap = tk.Frame(pane, bg="#FFFFFF")
        body_wrap.pack(side="top", fill="both", expand=True, padx=(8, 0), pady=(8, 0))
        scroll = tk.Scrollbar(body_wrap, orient="vertical")
        body_family = font_family(self, "Aptos", "Calibri", UI_FONT)
        self.body_value = tk.Text(
            body_wrap, name="body_value", wrap="word", state="disabled",
            font=(body_family, 11), fg="#000000", relief="flat", bd=0, highlightthickness=0,
            padx=60, pady=6, yscrollcommand=scroll.set, cursor="arrow",
        )
        scroll.config(command=self.body_value.yview)
        scroll.pack(side="right", fill="y")
        self.body_value.pack(side="left", fill="both", expand=True)

        # "Select an item to read" empty state, covering the pane until a row is chosen.
        self.empty_state = tk.Frame(pane, bg="#FFFFFF", name="empty_state")
        inner = tk.Frame(self.empty_state, bg="#FFFFFF")
        inner.place(relx=0.5, rely=0.42, anchor="center")
        tk.Label(inner, image=ic.get("mail", 64), bg="#FFFFFF").pack(side="top")
        tk.Label(inner, text="Select an item to read", font=("Segoe UI Semibold", 12),
                 fg=TEXT, bg="#FFFFFF").pack(side="top", pady=(10, 2))
        tk.Label(inner, text="Nothing is selected", font=(UI_FONT, 9),
                 fg=TEXT_SECONDARY, bg="#FFFFFF").pack(side="top")
        self.empty_state.place(x=0, y=0, relwidth=1, relheight=1)

        for b in (self.pane_reply_button, self.pane_reply_all_button):
            b.config(state="disabled")

    # ---------- behaviour ----------

    def _update_status(self):
        n = len(self.emails)
        unread = self.inbox_list.unread_count()
        self.status_items_var.set(f"Items: {n}")
        self.status_unread_var.set(f"Unread: {unread}")
        for lbl in (getattr(self, "fav_inbox_count", None), getattr(self, "inbox_count", None)):
            if lbl is not None:
                lbl.configure(text=str(unread) if unread else "")

    def _on_listbox_select(self, _event=None):
        selection = self.inbox_list.curselection()
        if selection:
            self.select_email(selection[0])

    def select_email(self, index):
        """Programmatically select inbox row `index` and render it in the
        reading pane. Used both by the UI click handler and by automation/
        self-tests driving the app directly."""
        email = self.emails[index]
        self.selected_index = index

        self.inbox_list.selection_set(index)
        self.inbox_list.mark_read(index)

        self.subject_var.set(email["subject"])
        self.from_var.set(f"{email['sender_name']} <{email['sender_email']}>")
        self.to_line_var.set(f"To:  {ACCOUNT_NAME} <{ACCOUNT_EMAIL}>")
        self.received_var.set(header_time_text(email["received"]))

        self.avatar_canvas.delete("all")
        color = AVATAR_COLORS[index % len(AVATAR_COLORS)]
        self.avatar_canvas.create_oval(1, 1, 43, 43, fill=color, outline="")
        self.avatar_canvas.create_text(
            22, 22, text=avatar_initials(email["sender_name"]),
            fill="#FFFFFF", font=(UI_FONT, 12),
        )

        self.body_value.config(state="normal")
        self.body_value.delete("1.0", "end")
        self.body_value.insert("1.0", email["body"])
        self.body_value.config(state="disabled")

        self.empty_state.place_forget()
        for b in (self.reply_button, self.reply_all_button, self.forward_button,
                  self.pane_reply_button, self.pane_reply_all_button):
            b.config(state="normal")
        self._update_status()

    def _close_active_compose(self):
        if self.active_compose is not None:
            try:
                if self.active_compose.winfo_exists():
                    self.active_compose.destroy()
            except tk.TclError:
                pass
            self.active_compose = None

    def open_new_email(self):
        self._close_active_compose()
        self.active_compose = ComposeWindow(self.master, self, mode="new")
        return self.active_compose

    def open_reply(self):
        if self.selected_index is None:
            return None
        self._close_active_compose()
        source_email = self.emails[self.selected_index]
        self.active_compose = ComposeWindow(
            self.master, self, mode="reply", source_email=source_email
        )
        return self.active_compose

    def on_compose_sent(self, entry):
        self.last_sent = entry


def main():
    root = tk.Tk()
    OutlookMirrorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
