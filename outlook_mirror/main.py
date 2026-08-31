"""
Outlook Mirror - a small local desktop-app stand-in for Microsoft Outlook.

Purpose: give an RPA automation (Robot Framework + a Python/Tkinter or
pywinauto-style desktop-automation approach) something to open/click/read/
compose against, without needing a real mailbox.

All data in data/inbox.json is entirely fictitious (dummy senders, a dummy
insurer domain, dummy policy numbers). Nothing here sends real email -
"Send" only appends a JSON line to data/sent_log.jsonl.

See SELECTORS.md in this folder for exactly how an automation should locate
every window/widget (titles, button text, field order).

Launch:
    ~/rpa-env/bin/python main.py
"""

import json
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import font as tkfont

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
INBOX_PATH = DATA_DIR / "inbox.json"
SENT_LOG_PATH = DATA_DIR / "sent_log.jsonl"

MAIN_WINDOW_TITLE = "Inbox - Example Insurance Broker - Outlook"
MAIN_GEOMETRY = "900x520+100+100"
COMPOSE_GEOMETRY = "560x480+250+150"

# Real Outlook brand colors.
OUTLOOK_BLUE = "#0F6CBD"
OUTLOOK_BLUE_DARK = "#0A4A82"
SELECTION_BLUE = "#C7E0F4"
BORDER = "#E1DFDD"
TEXT_SECONDARY = "#605E5C"
AVATAR_COLORS = ["#C239B3", "#0F6CBD", "#498205", "#B4009E", "#CA5010"]


def pick_font(root, *candidates, size=10, weight="normal"):
    available = set(tkfont.families(root))
    for name in candidates:
        if name in available:
            return tkfont.Font(family=name, size=size, weight=weight)
    return tkfont.Font(size=size, weight=weight)


def avatar_initials(name):
    parts = [p for p in name.replace(",", " ").split() if p]
    letters = [p[0].upper() for p in parts[:2]]
    return "".join(letters) or "?"


class ColorButton(tk.Label):
    """A tk.Label styled and bound as a button.

    A real tk.Button's bg color is silently ignored by macOS's native Aqua theme
    (confirmed live: it renders as a generic light-gray system button with barely-
    visible text no matter what bg/fg is set) - a Label respects its bg/fg on every
    platform, so this is used everywhere a colored button is needed in this app.
    Supports the same enabled/disabled pattern real code here already relies on
    (`.config(state="disabled")` / `.config(state="normal")`) via an override.
    """

    def __init__(self, master, text, command, fg, bg, active_bg, disabled_fg="#A19F9D",
                 disabled_bg=None, enabled=True, **kw):
        self._command = command
        self._fg = fg
        self._bg = bg
        self._active_bg = active_bg
        self._disabled_fg = disabled_fg
        self._disabled_bg = disabled_bg or bg
        self._enabled = enabled
        super().__init__(master, text=text, fg=fg, bg=bg, cursor="hand2", **kw)
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self._apply_state()

    def _on_click(self, _event=None):
        if self._enabled and self._command:
            self._command()

    def _on_enter(self, _event=None):
        if self._enabled:
            self.config(bg=self._active_bg, cursor="hand2")

    def _on_leave(self, _event=None):
        if self._enabled:
            self.config(bg=self._bg, cursor="arrow")

    def _apply_state(self):
        if self._enabled:
            self.config(fg=self._fg, bg=self._bg, cursor="hand2")
        else:
            self.config(fg=self._disabled_fg, bg=self._disabled_bg, cursor="arrow")

    def config(self, **kw):
        # Accept the same state="disabled"/"normal" calls the app's own code
        # already uses against real tk widgets, on top of normal tk options.
        state = kw.pop("state", None)
        super().config(**kw)
        if state == "disabled":
            self._enabled = False
            self._apply_state()
        elif state == "normal":
            self._enabled = True
            self._apply_state()

    configure = config

QUOTE_HEADER_FMT = "On {received}, {sender_name} <{sender_email}> wrote:"


def load_inbox():
    with open(INBOX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def quote_body(email):
    """Build the quoted-reply block used to pre-fill a Reply compose window."""
    header = QUOTE_HEADER_FMT.format(**email)
    quoted_lines = "\n".join("> " + line for line in email["body"].splitlines())
    return "\n\n\n" + header + "\n" + quoted_lines


class ComposeWindow(tk.Toplevel):
    """
    Compose / Reply window.

    Field order (top to bottom, and Tab order), for automation that locates
    controls by tab-order rather than a name/id:
        1. To         -> Entry   (name="to_entry")
        2. Subject    -> Entry   (name="subject_entry")
        3. Body       -> Text    (name="body_text")
        4. Send       -> Button, text="Send" (name="send_button")

    Window title:
      - New message:   "New Message"
      - Reply message: "RE: <original subject>"   (mirrors real Outlook,
        which titles a reply window after the subject line)
    """

    def __init__(self, master, app, mode="new", source_email=None):
        super().__init__(master, name="compose_window")
        self.app = app
        self.mode = mode
        self.source_email = source_email
        self.result = None  # set to the sent dict once Send is clicked

        prefill_to = ""
        prefill_subject = ""
        prefill_body = ""

        if mode == "reply" and source_email is not None:
            self.title("RE: " + source_email["subject"])
            prefill_to = source_email["sender_email"]
            prefill_subject = "RE: " + source_email["subject"]
            prefill_body = quote_body(source_email)
        else:
            self.title("New Message")

        self.geometry(COMPOSE_GEOMETRY)
        self.resizable(True, True)
        self.configure(bg="#FFFFFF")

        bold = pick_font(self, "Segoe UI Semibold", "Segoe UI", "Helvetica", size=10, weight="bold")
        normal = pick_font(self, "Segoe UI", "Helvetica", size=10)

        # -- brand title strip, matching the main inbox window --
        titlebar = tk.Frame(self, bg=OUTLOOK_BLUE, height=30)
        titlebar.grid(row=0, column=0, columnspan=2, sticky="we")
        titlebar.grid_propagate(False)
        tk.Label(
            titlebar, text=self.title(), font=bold, fg="#FFFFFF", bg=OUTLOOK_BLUE, anchor="w",
        ).pack(side="left", padx=10, fill="y")

        # --- To ---
        tk.Label(self, text="To:", anchor="w", width=10, name="to_label",
                 font=normal, bg="#FFFFFF").grid(
            row=1, column=0, sticky="w", padx=8, pady=(10, 2)
        )
        self.to_var = tk.StringVar(value=prefill_to)
        self.to_entry = tk.Entry(self, textvariable=self.to_var, width=55, name="to_entry",
                                  font=normal, relief="solid", bd=1)
        self.to_entry.grid(row=1, column=1, sticky="we", padx=(0, 8), pady=(10, 2))

        # --- Subject ---
        tk.Label(self, text="Subject:", anchor="w", width=10, name="subject_label",
                 font=normal, bg="#FFFFFF").grid(
            row=2, column=0, sticky="w", padx=8, pady=2
        )
        self.subject_var = tk.StringVar(value=prefill_subject)
        self.subject_entry = tk.Entry(
            self, textvariable=self.subject_var, width=55, name="subject_entry",
            font=normal, relief="solid", bd=1,
        )
        self.subject_entry.grid(row=2, column=1, sticky="we", padx=(0, 8), pady=2)

        # --- Body ---
        tk.Label(self, text="Body:", anchor="nw", width=10, name="body_label",
                 font=normal, bg="#FFFFFF").grid(
            row=3, column=0, sticky="nw", padx=8, pady=2
        )
        self.body_text = tk.Text(self, width=55, height=16, wrap="word", name="body_text",
                                  font=normal, relief="solid", bd=1)
        self.body_text.grid(row=3, column=1, sticky="nsew", padx=(0, 8), pady=2)
        if prefill_body:
            self.body_text.insert("1.0", prefill_body)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # --- Status + Send ---
        self.status_var = tk.StringVar(value="")
        self.status_label = tk.Label(
            self, textvariable=self.status_var, fg="#1a7f37", name="status_label",
            font=bold, bg="#FFFFFF",
        )
        self.status_label.grid(row=4, column=0, sticky="w", padx=8, pady=(4, 8))

        self.send_button = ColorButton(
            self, text="Send", command=self.send, name="send_button",
            font=normal, fg="#FFFFFF", bg=OUTLOOK_BLUE, active_bg=OUTLOOK_BLUE_DARK,
            width=12, pady=6, anchor="center",
        )
        self.send_button.grid(row=4, column=1, sticky="e", padx=8, pady=(4, 8))

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


class OutlookMirrorApp(tk.Frame):
    """
    Main inbox window.

    Widgets an automation cares about:
      - Inbox list:    Listbox, name="inbox_listbox". Each row's text is
                        "<sender_name> - <subject>" in the order emails
                        appear in data/inbox.json (top = first/newest).
      - Reading pane:   Label name="subject_value" (subject text),
                        Label name="from_value" (sender text),
                        Text  name="body_value" (read-only body).
      - "New Email" button: text="New Email", name="new_email_button".
      - "Reply" button:     text="Reply", name="reply_button"
                             (enabled only once an inbox row is selected).
    """

    def __init__(self, master):
        super().__init__(master, name="main_frame")
        self.master = master
        self.emails = load_inbox()
        self.selected_index = None
        self.active_compose = None
        self.last_sent = None  # most recent entry sent, for verification

        master.title(MAIN_WINDOW_TITLE)
        master.geometry(MAIN_GEOMETRY)

        self.pack(fill="both", expand=True)
        self._build_widgets()
        self._populate_inbox()

    # ---------- UI construction ----------

    def _build_widgets(self):
        bold = pick_font(self, "Segoe UI Semibold", "Segoe UI", "Helvetica", size=11, weight="bold")
        normal = pick_font(self, "Segoe UI", "Helvetica", size=10)
        brand_font = pick_font(self, "Segoe UI Semibold", "Segoe UI", "Helvetica", size=12, weight="bold")

        # -- brand title strip (Outlook blue), like the Excel/Dynamics mirrors' own --
        titlebar = tk.Frame(self, bg=OUTLOOK_BLUE, height=32)
        titlebar.pack(side="top", fill="x")
        titlebar.pack_propagate(False)
        tk.Label(
            titlebar, text="✉  Outlook", font=brand_font, fg="#FFFFFF",
            bg=OUTLOOK_BLUE, anchor="w",
        ).pack(side="left", padx=10)

        toolbar = tk.Frame(self, name="toolbar", bg="#FAF9F8", height=44,
                            highlightthickness=1, highlightbackground=BORDER)
        toolbar.pack(side="top", fill="x")
        toolbar.pack_propagate(False)

        self.new_email_button = ColorButton(
            toolbar,
            text="➕  New Email",
            name="new_email_button",
            command=self.open_new_email,
            font=normal, fg="#FFFFFF", bg=OUTLOOK_BLUE, active_bg=OUTLOOK_BLUE_DARK,
            padx=12, pady=8,
        )
        self.new_email_button.pack(side="left", padx=(10, 6), pady=8)

        self.reply_button = ColorButton(
            toolbar,
            text="↩  Reply",
            name="reply_button",
            command=self.open_reply,
            enabled=False,
            font=normal, fg=OUTLOOK_BLUE_DARK, bg="#FFFFFF", active_bg=SELECTION_BLUE,
            disabled_fg=TEXT_SECONDARY, disabled_bg="#FFFFFF",
            relief="solid", bd=1, padx=12, pady=8,
        )
        self.reply_button.pack(side="left", pady=8)

        body_frame = tk.Frame(self, name="body_frame", bg="#FFFFFF")
        body_frame.pack(side="top", fill="both", expand=True)

        # --- Left: inbox list ---
        list_frame = tk.Frame(body_frame, name="list_frame", bg="#FFFFFF")
        list_frame.pack(side="left", fill="y")

        tk.Label(list_frame, text="Inbox", font=bold, bg="#FFFFFF", anchor="w").pack(
            anchor="w", padx=10, pady=(8, 4)
        )

        list_scroll = tk.Scrollbar(list_frame, orient="vertical")
        self.inbox_listbox = tk.Listbox(
            list_frame,
            name="inbox_listbox",
            width=42,
            height=24,
            exportselection=False,
            yscrollcommand=list_scroll.set,
            font=normal, relief="flat", bd=0, highlightthickness=0,
            selectbackground=SELECTION_BLUE, selectforeground="#000000",
            activestyle="none",
        )
        list_scroll.config(command=self.inbox_listbox.yview)
        self.inbox_listbox.pack(side="left", fill="y", padx=(10, 0))
        list_scroll.pack(side="left", fill="y")
        self.inbox_listbox.bind("<<ListboxSelect>>", self._on_listbox_select)

        tk.Frame(body_frame, bg=BORDER, width=1).pack(side="left", fill="y")

        # --- Right: reading pane ---
        reading_frame = tk.Frame(body_frame, name="reading_frame", bg="#FFFFFF")
        reading_frame.pack(side="left", fill="both", expand=True)

        header = tk.Frame(reading_frame, name="reading_header", bg="#FFFFFF")
        header.pack(side="top", fill="x", padx=14, pady=(12, 8))

        self.subject_var = tk.StringVar(value="")
        tk.Label(
            header, textvariable=self.subject_var, name="subject_value",
            anchor="w", font=(bold.actual("family"), 15, "bold"), bg="#FFFFFF",
            wraplength=460, justify="left",
        ).pack(anchor="w", pady=(0, 8))

        sender_row = tk.Frame(header, bg="#FFFFFF")
        sender_row.pack(anchor="w", fill="x")

        self.avatar_canvas = tk.Canvas(sender_row, width=32, height=32, bg="#FFFFFF",
                                        highlightthickness=0)
        self.avatar_canvas.pack(side="left", padx=(0, 8))

        sender_text_col = tk.Frame(sender_row, bg="#FFFFFF")
        sender_text_col.pack(side="left", fill="x", expand=True)

        self.from_var = tk.StringVar(value="")
        tk.Label(sender_text_col, textvariable=self.from_var, name="from_value",
                 anchor="w", font=bold, bg="#FFFFFF").pack(anchor="w")

        self.received_var = tk.StringVar(value="")
        tk.Label(sender_text_col, textvariable=self.received_var, name="received_value",
                 anchor="w", font=normal, fg=TEXT_SECONDARY, bg="#FFFFFF").pack(anchor="w")

        tk.Frame(reading_frame, bg=BORDER, height=1).pack(fill="x", padx=14)

        self.body_value = tk.Text(
            reading_frame, name="body_value", wrap="word", state="disabled",
            font=normal, relief="flat", bd=0, highlightthickness=0, padx=14, pady=12,
        )
        self.body_value.pack(side="top", fill="both", expand=True, pady=(4, 0))

    def _populate_inbox(self):
        for email in self.emails:
            self.inbox_listbox.insert(
                "end", f"{email['sender_name']} - {email['subject']}"
            )

    # ---------- behaviour ----------

    def _on_listbox_select(self, _event=None):
        selection = self.inbox_listbox.curselection()
        if not selection:
            return
        self.select_email(selection[0])

    def select_email(self, index):
        """Programmatically select inbox row `index` and render it in the
        reading pane. Used both by the UI click handler and by automation/
        self-tests driving the app directly."""
        email = self.emails[index]
        self.selected_index = index

        self.inbox_listbox.selection_clear(0, "end")
        self.inbox_listbox.selection_set(index)

        self.subject_var.set(email["subject"])
        self.from_var.set(f"{email['sender_name']} <{email['sender_email']}>")
        self.received_var.set(email["received"])

        self.avatar_canvas.delete("all")
        color = AVATAR_COLORS[index % len(AVATAR_COLORS)]
        self.avatar_canvas.create_oval(1, 1, 31, 31, fill=color, outline="")
        self.avatar_canvas.create_text(
            16, 16, text=avatar_initials(email["sender_name"]),
            fill="#FFFFFF", font=("Segoe UI", 11, "bold"),
        )

        self.body_value.config(state="normal")
        self.body_value.delete("1.0", "end")
        self.body_value.insert("1.0", email["body"])
        self.body_value.config(state="disabled")

        self.reply_button.config(state="normal")

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
    app = OutlookMirrorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
