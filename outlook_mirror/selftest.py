"""
Headless self-test for the Outlook Mirror app.

Pattern: tk.Tk() + root.withdraw(), then drive the app's methods/button
commands directly (no mainloop, no real display interaction needed).

Run with:
    ~/rpa-env/bin/python selftest.py
"""

import json
import sys
import tkinter as tk
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import main as outlook_mirror  # noqa: E402

SENT_LOG_PATH = outlook_mirror.SENT_LOG_PATH

failures = []


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        failures.append(label)


def main():
    # Start each run from a clean sent-log so the assertions below are
    # unambiguous about what THIS run produced.
    if SENT_LOG_PATH.exists():
        SENT_LOG_PATH.unlink()

    root = tk.Tk()
    root.withdraw()

    app = outlook_mirror.OutlookMirrorApp(root)

    emails = app.emails
    check("inbox seeded with at least 3 emails", len(emails) >= 3)

    # --- Click into each inbox email and verify the reading pane ---
    for i, email in enumerate(emails):
        app.select_email(i)
        check(
            f"row {i}: reading pane subject matches",
            app.subject_var.get() == email["subject"],
        )
        check(
            f"row {i}: reading pane body matches",
            app.body_value.get("1.0", "end-1c") == email["body"],
        )
        check(
            f"row {i}: reading pane sender shown",
            email["sender_email"] in app.from_var.get(),
        )

    # --- Locate the complaint-scenario email ---
    complaint_index = next(
        (i for i, e in enumerate(emails) if "COMPLAINT" in e["subject"]), None
    )
    check("complaint email found in seeded inbox", complaint_index is not None)

    complaint_email = emails[complaint_index]
    app.select_email(complaint_index)

    # --- Open Reply on the complaint email and check compose pre-fill ---
    compose = app.open_reply()
    check("reply compose window opened", compose is not None)
    check(
        "reply window title is 'RE: <original subject>'",
        compose.title() == "RE: " + complaint_email["subject"],
    )
    check(
        "reply To field pre-filled with original sender",
        compose.to_var.get() == complaint_email["sender_email"],
    )
    check(
        "reply Subject field pre-filled with RE: prefix",
        compose.subject_var.get() == "RE: " + complaint_email["subject"],
    )
    body_text = compose.body_text.get("1.0", "end-1c")
    check(
        "reply Body quotes the original message",
        complaint_email["sender_name"] in body_text
        and all(
            ("> " + line) in body_text
            for line in complaint_email["body"].splitlines()
            if line.strip()
        ),
    )

    # --- Click Send and verify the sent log ---
    compose.send()

    check("sent_log.jsonl was created", SENT_LOG_PATH.exists())
    lines = SENT_LOG_PATH.read_text(encoding="utf-8").strip().splitlines()
    check("exactly one entry logged", len(lines) == 1)

    logged = json.loads(lines[0]) if lines else {}
    check("logged 'to' matches complaint sender", logged.get("to") == complaint_email["sender_email"])
    check(
        "logged 'subject' matches RE: subject",
        logged.get("subject") == "RE: " + complaint_email["subject"],
    )
    check(
        "logged 'body' contains quoted original body",
        all(
            ("> " + line) in logged.get("body", "")
            for line in complaint_email["body"].splitlines()
            if line.strip()
        ),
    )
    check("logged entry has a timestamp", bool(logged.get("timestamp")))
    check("compose status shows 'Sent'", compose.status_var.get() == "Sent")
    check("app.last_sent recorded the sent entry", app.last_sent == logged)

    # --- New Email compose should start blank ---
    app.selected_index = None
    new_compose = app.open_new_email()
    check("new-email window title is 'New Message'", new_compose.title() == "New Message")
    check("new-email To field starts blank", new_compose.to_var.get() == "")
    check("new-email Subject field starts blank", new_compose.subject_var.get() == "")
    check(
        "new-email Body field starts blank",
        new_compose.body_text.get("1.0", "end-1c") == "",
    )

    root.destroy()

    print()
    if failures:
        print(f"{len(failures)} check(s) FAILED:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("All checks passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
