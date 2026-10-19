# SELECTORS.md — how an RPA automation should find things in Outlook Mirror

Tkinter apps don't expose a DOM, so this mirror is built to be located the
way a real desktop-automation tool (pywinauto / RPA.Desktop image+coordinate
locators) finds a real window: **fixed window title, fixed geometry, fixed
click coordinates, exact button text and stable tab/field order.** Widgets
also carry a Tk `name=` (e.g. `.main_frame...reply_button`) for stacks that
read the Tk widget hierarchy directly.

The UI imitates classic Microsoft Outlook (Microsoft 365 desktop, light
theme). Only the controls listed below are functional; every other ribbon
button, tab, folder and icon is decorative and inert.

## Fixed click coordinates (Windows)

All values are **Tk-logical pixels relative to the window's client-area
top-left** (Tk is DPI-unaware, so on the 125%-scaled 1536x864 desktop
multiply by 1.25 and add the physical client origin, e.g. from
`ClientToScreen`). They were measured from the live widgets
(`winfo_rootx/rooty` minus the toplevel's), and verified by real mouse
clicks + typing driving a full reply/send.

| Target | Window | Client x, y |
|---|---|---|
| Inbox row `i` (0-based) | main | `x = 361`, `y = 246 + 68 * i` (row 0 = 246, row 1 = 314, row 2 = 382) |
| **Reply** (ribbon Home > Respond) | main | `320, 101` — disabled until a row is selected |
| Reply (reading-pane header, alternative) | main | `1103, 240` — only shown/enabled once a row is selected |
| New Email (ribbon Home > New) | main | `32, 109` |
| Body text, top line (click, then ctrl+Home, then type) | reply/new | `129, 195` |
| **Send** | reply/new | `43, 115` |

Row formula details: the message list canvas starts at client y=212, rows
are a fixed `ROW_HEIGHT = 68` px, the click point is the row's vertical
centre. Valid while the list is not scrolled (with the 3 seeded emails it
never scrolls).

## Main window

- **Window title (exact):** `Inbox - Example Insurance Broker - Outlook`
- **Geometry:** `1400x760+60+12` (fixed — same size/position every launch)
- Layout: top bar (search) / ribbon tabs / Home ribbon / folder pane (left,
  210 px) / message list (350 px) / reading pane / status bar
  (`Items: n   Unread: n`).

| Element | How to locate | Notes |
|---|---|---|
| Message list | custom Canvas list, widget name `inbox_listbox` (`app.inbox_list`, alias `app.inbox_listbox`) | One 68 px row per email in `data/inbox.json` order. Single click selects and opens it in the reading pane (and marks it read). Listbox-like API: `size()`, `curselection()`, `selection_set(i)`, `get(i)` (returns `"<sender_name> - <subject>"`). |
| New Email | ribbon button `New Email`, widget name `new_email_button` | Always enabled. Opens a blank compose window. |
| Reply | ribbon button `Reply`, widget name `reply_button`; also reading-pane `pane_reply_button` | Disabled until a row has been selected. Opens a compose window pre-filled from the selected email. `Reply All` behaves the same (single sender). |
| Subject (reading pane) | `app.subject_var` / Label `subject_value` | |
| From (reading pane) | `app.from_var` / Label `from_value` | `<sender_name> <<sender_email>>` |
| Received (reading pane) | `app.received_var` / Label `received_value` | e.g. `Tue 25/08/2026 09:14` |
| Body (reading pane) | Text `body_value`, read-only | Full plain-text body. |

Before any row is selected the reading pane shows "Select an item to read".

## Compose window (opened by New Email or Reply)

- **Window title:**
  - New Email → exactly `Untitled - Message (HTML)`
  - Reply → exactly `RE: <original subject> - Message (HTML)` (always
    starts with `RE: `)
- **Geometry:** `960x700+200+40` (fixed)
- Only one compose window can be open at a time — opening a second one
  closes the first.

Field order, top to bottom (also the Tab order):

| Order | Field | Control type | Widget name | Reply pre-fill |
|---|---|---|---|---|
| 1 | To | `Entry` | `to_entry` | original email's `sender_email` |
| 2 | Cc | `Entry` | `cc_entry` | blank (not logged) |
| 3 | Subject | `Entry` | `subject_entry` | `RE: ` + original subject |
| 4 | Body | `Text` | `body_text` | quoted original body (see format below) |
| — | Send | big button at the left of the header, text `Send` | `send_button` | — |
| — | Status label (shows `Sent` after sending) | `Label`, right end of the Subject row | `status_label` | starts blank |

Quoted-reply body format (pre-filled on Reply; the insert cursor starts at
the top, above it):

```
<blank line>
<blank line>
On <received>, <sender_name> <<sender_email>> wrote:
> <original body, line 1>
> <original body, line 2>
> ...
```

### Sending

Clicking **Send**:
1. Appends one JSON line to `data/sent_log.jsonl` with keys `to`, `subject`,
   `body`, `timestamp` (ISO 8601). Nothing goes over the network.
2. Sets the status label text to `Sent` and disables Send.
3. Auto-closes the compose window about 0.7s later.

An automation verifying a send should poll `data/sent_log.jsonl` for the
newly appended line rather than relying on the window closing.

## Data files

- `data/inbox.json` — the 3 seeded inbox emails (see README.md). Reloaded
  each launch; read/unread state is not persisted (all start unread).
- `data/sent_log.jsonl` — append-only log of everything sent. Not cleared
  automatically — delete it (or let `selftest.py` delete it) to reset.
