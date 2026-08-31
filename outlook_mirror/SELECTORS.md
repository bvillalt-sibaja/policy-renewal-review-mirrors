# SELECTORS.md — how an RPA automation should find things in Outlook Mirror

Tkinter apps don't expose a DOM, so this mirror is built to be located the
way a real desktop-automation tool (pywinauto / RPA.Desktop image+coordinate
locators) finds a real Tk window: **fixed window title, fixed geometry,
exact button/label text, and stable tab/field order.** Every widget below
also carries a Tk widget `name=` (visible in the Tk widget path, e.g.
`.main_frame.toolbar.new_email_button`), for automation stacks that can read
the Tk widget hierarchy directly.

## Main window ("Inbox")

- **Window title (exact):** `Inbox - Example Insurance Broker - Outlook`
- **Geometry:** `900x520+100+100` (fixed — same size/position every launch)
- Layout: toolbar across the top, then a 2-pane body (inbox list on the
  left, reading pane on the right).

| Element | How to locate | Notes |
|---|---|---|
| Inbox list | `Listbox`, widget name `inbox_listbox` | One row per email, top-to-bottom in the same order as `data/inbox.json`. Row text is exactly `"<sender_name> - <subject>"`. Click/select a row (or send it a `<<ListboxSelect>>`) to open that email in the reading pane. |
| "New Email" button | `Button`, exact text `New Email`, widget name `new_email_button` | Always enabled. Opens a blank compose window. |
| "Reply" button | `Button`, exact text `Reply`, widget name `reply_button` | Disabled until an inbox row has been selected at least once. Opens a compose window pre-filled from the currently selected email. |
| Subject (reading pane) | `Label`, widget name `subject_value` | Row 1 of the reading-pane header, right of a `Subject:` label. |
| From (reading pane) | `Label`, widget name `from_value` | Row 2, right of a `From:` label. Format: `<sender_name> <<sender_email>>`. |
| Received (reading pane) | `Label`, widget name `received_value` | Row 3, right of a `Received:` label. |
| Body (reading pane) | `Text`, widget name `body_value`, read-only (`state=disabled`) | Full plain-text body of the selected email. |

## Compose window (opened by "New Email" or "Reply")

- **Window title:**
  - New Email → exactly `New Message`
  - Reply → exactly `RE: <original subject>` (mirrors real Outlook, which
    titles a reply window after the subject line)
- **Geometry:** `560x480+250+150` (fixed)
- Only one compose window can be open at a time — opening a second one
  closes the first.

Field order, top to bottom (also the Tab order — use this if targeting by
tab-index rather than by name):

| Order | Field | Control type | Widget name | Reply pre-fill |
|---|---|---|---|---|
| 1 | To | `Entry` | `to_entry` | original email's `sender_email` |
| 2 | Subject | `Entry` | `subject_entry` | `RE: ` + original subject |
| 3 | Body | `Text` | `body_text` | quoted original body (see format below) |
| 4 | Send button | `Button`, exact text `Send` | `send_button` | — |
| — | Status label (shows `Sent` after sending) | `Label` | `status_label` | starts blank |

Quoted-reply body format (what appears pre-filled in field 3 on Reply):

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
   `body`, `timestamp` (ISO 8601). This is the only durable record of a
   "sent" message — nothing goes over the network.
2. Sets the status label text to `Sent`.
3. Auto-closes the compose window about 0.7s later.

An automation verifying a send should poll/read `data/sent_log.jsonl` for
the newly appended line rather than relying on the window closing, since the
close is a cosmetic delay only.

## Data files

- `data/inbox.json` — the 3 seeded inbox emails (see README.md for details).
  Edit this to change what the mirror shows; the app reloads it each launch
  (no persistence of read/unread state).
- `data/sent_log.jsonl` — append-only log of everything sent through the
  compose window. One JSON object per line. Not cleared automatically —
  delete it (or let `selftest.py` delete it) to reset between test runs.
