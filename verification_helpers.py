"""Log-file verification helpers, called from renewal_review.robot via Evaluate
(modules=verification_helpers). Written as real functions rather than inline Evaluate
generator expressions - Robot Framework's $var substitution inside a generator
expression's body runs in a nested scope it can't always see into, confirmed live to
fail with "variable '$x' is used in a scope where it cannot be seen"."""
import json
import os


def action_was_logged(log_path, action, contact_id):
    # The log file doesn't exist until the mirror's Flask server writes its first
    # entry - and Selenium's Click Element returns as soon as the click is
    # dispatched, not after the resulting POST/redirect completes server-side, so
    # the caller (Verify Dynamics Action Logged) retries this via Wait Until
    # Keyword Succeeds rather than treating a momentarily-missing file as fatal.
    if not os.path.exists(log_path):
        return False
    with open(log_path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            entry = json.loads(line)
            if entry.get("action") == action and entry.get("contact_id") == contact_id:
                return True
    return False


def body_fragment_was_sent(sent_log_path, body_fragment, fragment_len=30):
    if not os.path.exists(sent_log_path):
        return False
    needle = body_fragment[:fragment_len]
    with open(sent_log_path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            entry = json.loads(line)
            if needle in entry.get("body", ""):
                return True
    return False
