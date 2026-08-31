"""
Sample Insurer -- Dynamics 365 (Mirror)

A small local web-app mirror of the Microsoft Dynamics 365 CRM "Contact"
record view, built so a Robot Framework + RPA.Browser.Selenium automation
can be developed and tested against it instead of a real production CRM.

ALL data in this app is fictitious. Nothing here represents a real
insurer, real customer, or real production system.

Run with:
    ~/rpa-env/bin/python app.py
Serves on http://127.0.0.1:5057 by default (override with PORT env var).
"""
import json
import os
import uuid
from datetime import datetime, timezone

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONTACTS_PATH = os.path.join(DATA_DIR, "contacts.json")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
ACTION_LOG_PATH = os.path.join(DATA_DIR, "action_log.jsonl")

app = Flask(__name__)
app.secret_key = "dev-only-not-a-real-secret-do-not-reuse"

os.makedirs(UPLOADS_DIR, exist_ok=True)


def load_contacts():
    with open(CONTACTS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_contacts(contacts):
    with open(CONTACTS_PATH, "w", encoding="utf-8") as f:
        json.dump(contacts, f, indent=2)


# In-memory store, seeded from disk at startup. Notes/documents added
# during a run live here (and uploaded files land on disk under
# data/uploads/<contact_id>/) but are NOT written back into
# data/contacts.json -- restarting the app resets to the seed data.
# The one thing that IS durably appended, by design, is action_log.jsonl,
# so an automation's verification step has something reliable to check.
CONTACTS = load_contacts()


def log_action(action, contact_id, details=None):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "contact_id": contact_id,
        "details": details or {},
    }
    with open(ACTION_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def get_contact_or_404(contact_id):
    contact = CONTACTS.get(contact_id)
    if contact is None:
        abort(404)
    return contact


@app.route("/", methods=["GET"])
def home():
    return render_template("search.html", contacts=CONTACTS)


@app.route("/search", methods=["GET", "POST"])
def search():
    policy_number = (request.values.get("policy_number") or "").strip()
    if not policy_number:
        flash("Enter a policy number to search.", "error")
        return redirect(url_for("home"))

    contact = CONTACTS.get(policy_number)
    if contact is None:
        flash(f'No record found for policy number "{policy_number}".', "error")
        return redirect(url_for("home"))

    return redirect(url_for("contact_view", contact_id=contact["id"]))


@app.route("/contact/<contact_id>", methods=["GET"])
def contact_view(contact_id):
    contact = get_contact_or_404(contact_id)

    show_all_docs = request.args.get("docs") == "all"
    documents = contact["documents"] if show_all_docs else contact["documents"][:1]

    show_all_notes = request.args.get("notes") == "all"
    timeline_filter = request.args.get("filter", "no_filter")
    timeline_notes = contact["timeline_notes"]
    if not show_all_notes:
        timeline_notes = timeline_notes[:1]

    show_note_form = request.args.get("enter_note") == "1"

    return render_template(
        "contact.html",
        contact=contact,
        documents=documents,
        total_documents=len(contact["documents"]),
        showing_all_docs=show_all_docs,
        timeline_notes=timeline_notes,
        total_notes=len(contact["timeline_notes"]),
        showing_all_notes=show_all_notes,
        timeline_filter=timeline_filter,
        show_note_form=show_note_form,
    )


@app.route("/contact/<contact_id>/customer-care", methods=["POST"])
def select_customer_care(contact_id):
    contact = get_contact_or_404(contact_id)
    log_action("select_customer_care", contact_id, {"contact_name": contact["contact_name"]})
    flash("Customer Care selected.", "info")
    return redirect(url_for("contact_view", contact_id=contact_id))


@app.route("/contact/<contact_id>/documents/upload", methods=["POST"])
def upload_document(contact_id):
    contact = get_contact_or_404(contact_id)

    uploaded_file = request.files.get("document_file")
    if uploaded_file is None or uploaded_file.filename == "":
        flash("No file selected to upload.", "error")
        return redirect(url_for("contact_view", contact_id=contact_id))

    contact_upload_dir = os.path.join(UPLOADS_DIR, contact_id)
    os.makedirs(contact_upload_dir, exist_ok=True)

    original_name = uploaded_file.filename
    safe_name = f"{uuid.uuid4().hex[:8]}_{original_name}"
    dest_path = os.path.join(contact_upload_dir, safe_name)
    uploaded_file.save(dest_path)

    size_kb = round(os.path.getsize(dest_path) / 1024, 1)
    contact["documents"].append(
        {
            "name": original_name,
            "uploaded": datetime.now(timezone.utc).isoformat(),
            "size_kb": size_kb,
            "stored_as": safe_name,
        }
    )

    log_action(
        "upload_document",
        contact_id,
        {"file_name": original_name, "stored_as": safe_name, "size_kb": size_kb},
    )
    flash(f'Document "{original_name}" uploaded.', "info")
    return redirect(url_for("contact_view", contact_id=contact_id, docs="all"))


@app.route("/contact/<contact_id>/notes", methods=["POST"])
def add_note(contact_id):
    contact = get_contact_or_404(contact_id)

    title = (request.form.get("note_title") or "").strip()
    body = (request.form.get("note_body") or "").strip()
    if not title and not body:
        flash("Enter a note title or body before saving.", "error")
        return redirect(url_for("contact_view", contact_id=contact_id, enter_note="1"))

    attachment = request.files.get("note_attachment")
    attachment_name = None
    if attachment is not None and attachment.filename:
        contact_upload_dir = os.path.join(UPLOADS_DIR, contact_id)
        os.makedirs(contact_upload_dir, exist_ok=True)
        attachment_name = attachment.filename
        safe_name = f"{uuid.uuid4().hex[:8]}_{attachment_name}"
        attachment.save(os.path.join(contact_upload_dir, safe_name))

    note = {
        "title": title or "(no title)",
        "body": body,
        "author": contact["contact_name"],
        "created": datetime.now(timezone.utc).isoformat(),
        "attachment": attachment_name,
    }
    contact["timeline_notes"].insert(0, note)

    log_action(
        "add_note_and_close",
        contact_id,
        {"title": note["title"], "has_attachment": attachment_name is not None},
    )
    flash("Note added and closed.", "info")
    return redirect(url_for("contact_view", contact_id=contact_id, notes="all"))


@app.route("/contact/<contact_id>/save-and-close", methods=["POST"])
def save_and_close(contact_id):
    contact = get_contact_or_404(contact_id)
    entry = log_action("save_and_close", contact_id, {"contact_name": contact["contact_name"]})
    flash(f"Saved and closed at {entry['timestamp']}.", "success")
    return redirect(url_for("contact_view", contact_id=contact_id))


@app.route("/contact/<contact_id>/save-and-continue", methods=["POST"])
def save_and_continue(contact_id):
    contact = get_contact_or_404(contact_id)
    entry = log_action("save_and_continue", contact_id, {"contact_name": contact["contact_name"]})
    flash(f"Saved, continuing at {entry['timestamp']}.", "success")
    return redirect(url_for("contact_view", contact_id=contact_id))


@app.route("/contact/<contact_id>/intermediary", methods=["GET"])
def intermediary_view(contact_id):
    contact = get_contact_or_404(contact_id)
    return render_template("intermediary.html", contact=contact)


@app.route("/uploads/<contact_id>/<path:filename>")
def serve_upload(contact_id, filename):
    contact_upload_dir = os.path.join(UPLOADS_DIR, contact_id)
    return send_from_directory(contact_upload_dir, filename)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5057"))
    app.run(host="127.0.0.1", port=port, debug=False)
