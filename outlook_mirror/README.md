# Outlook Mirror

A small local desktop-app mirror of Microsoft Outlook (inbox + reading pane
+ compose/reply), built so an RPA automation (Robot Framework + a
Python/Tkinter or pywinauto-style desktop-automation approach) can be built
and tested against it instead of a real mailbox.

All content is invented/dummy data — no real names, domains, or email
addresses from any real system are used anywhere in this app.

## Launch

```
python main.py
```

(Requires Tkinter, which ships with the `~/rpa-env` Python 3.11 install —
confirmed working via `~/rpa-env/bin/python -c "import tkinter"`.)

This opens the "Inbox" window (`Inbox - Example Insurance Broker - Outlook`,
fixed at `1400x760+60+12`), styled after classic Microsoft 365 Outlook
(light theme): Home ribbon (New Email, Reply, ... - only New Email / Reply /
Reply All are functional, the rest is decorative), folder pane, an
Outlook-style message list (fixed 68 px rows: sender, subject, preview,
date; unread items bold/blue) and a reading pane with its own Reply / Reply
All / Forward buttons. Icons are drawn with Pillow when available (blank
otherwise - the app still works). See
[`SELECTORS.md`](./SELECTORS.md) for exactly how to locate every window and
control for automation purposes.

## Seeded inbox (`data/inbox.json`)

Three dummy emails, in this order:

1. **Renewal Request - Policy 02/HHR/0000001** — from `Alex Renewals`
   (`alex.renewals@sampleclientbroker.test`). A plain, routine renewal
   request for dummy policyholder "Mr J Doe", no complications — the
   "everything's fine, just process it" case.
2. **COMPLAINT - Mr J Doe & Mrs A Doe - 02/HHR/0198766** — from
   `Jamie Client Care` (`jamie.clientcare@sampleclientbroker.test`). States
   the client has raised a formal complaint and legal proceedings are
   ongoing — the case meant to drive a downstream "route this to the
   complaint-handling path, not standard renewal" decision.
3. **FYI - Scheduled system maintenance this weekend** — from
   `Sample Insurer IT` (`it.notices@sampleinsurer.test`). A generic internal
   notice with no action required, included just to make the inbox look
   like a real inbox (more than one email, not all of it renewal-related).

Edit `data/inbox.json` to change what's seeded — it's a plain JSON array of
objects with `id`, `sender_name`, `sender_email`, `subject`, `received`, and
`body`. It's reloaded fresh on every launch; there's no read/unread state
persisted across restarts.

## Compose / Reply / Send

- **New Email** opens a blank compose window (title
  `Untitled - Message (HTML)`, fixed at `960x700+200+40`).
- **Reply** (enabled once an inbox row is selected) opens a compose window
  titled after the original subject (`RE: <subject> - Message (HTML)`), pre-filled with the
  original sender's address in To, `RE: ` + the original subject, and a
  quoted copy of the original body.
- **Send** never touches a network. It appends one JSON line
  (`to`, `subject`, `body`, `timestamp`) to `data/sent_log.jsonl`, shows a
  brief "Sent" confirmation in the compose window, and auto-closes the
  window about 0.7 seconds later. `data/sent_log.jsonl` is append-only and
  not cleared automatically — that's the file an automation's verification
  step should read to check what was actually composed/sent.

## What was verified

`selftest.py` drives the app headlessly (`tk.Tk()` + `root.withdraw()`,
calling the app's methods/button commands directly — no real display or
`mainloop()` needed) and checks:

- The inbox is seeded with the 3 emails above.
- Clicking into each of the 3 inbox rows (`app.select_email(i)`) shows the
  correct subject, body, and sender in the reading pane.
- Opening **Reply** on the complaint email produces a compose window with
  the correct title (`RE: COMPLAINT - Mr J Doe & Mrs A Doe - 02/HHR/0198766 - Message (HTML)`),
  the correct pre-filled To/Subject, and a body that quotes every line of
  the original message.
- Clicking **Send** on that reply appends exactly one correctly-shaped
  entry to `data/sent_log.jsonl` (right `to`/`subject`/quoted `body`, plus a
  timestamp), and the compose window's status label shows `Sent`.
- Opening **New Email** afterwards produces a compose window with the
  correct title (`Untitled - Message (HTML)`) and all three fields blank.

Run it with:

```
python selftest.py
```

Latest run (Windows, Maker runtime venv): **all 28 checks passed**, no exceptions. (The script deletes any
existing `data/sent_log.jsonl` at the start of each run so its log
assertions are unambiguous — delete it yourself too if you want a clean
slate before your own automation run.)

A live (non-headless) instantiation of the app was also smoke-tested
separately (`tk.Tk()` without `withdraw()`, building the real window and
reading back its title/geometry/listbox contents) to confirm it behaves the
same way outside the self-test harness.

## Notes for the automation this mirror supports

- The fixed click coordinates in `SELECTORS.md` were measured and verified
  live on Windows (125% scaling, DPI-unaware Tk): real mouse clicks on
  row/Reply/body/Send plus typed text produced the expected
  `sent_log.jsonl` entry. Other OSes render different chrome/fonts, so
  re-measure there.
- Only the inbox rows, New Email, Reply/Reply All, the compose fields and
  Send are functional; all other ribbon/folder/tab controls are inert
  decoration.
