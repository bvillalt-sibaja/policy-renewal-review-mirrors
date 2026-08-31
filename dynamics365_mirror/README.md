# Sample Insurer -- Dynamics 365 (Mirror)

A small local Flask app that mirrors the Microsoft Dynamics 365 CRM
"Contact" record view for an insurance renewal case, so a
Robot Framework + `RPA.Browser.Selenium` automation can be built and
tested against it instead of the real production CRM.

**All data in this app is entirely fictitious** — fake insurer ("Sample
Insurer Ltd"), fake contacts ("Mr J Doe", "Ms A Smith"), fake broker
("Sample Broker Services Ltd"), fake policy numbers, fake addresses and
notes. Nothing here is drawn from any real customer or company.

## Running it

```bash
cd /private/tmp/claude-501/-Users-bvillalt/3d7b8968-9828-48af-afc1-41546b272423/scratchpad/mirror_work/dynamics365_mirror
~/rpa-env/bin/python app.py
```

Serves on **http://127.0.0.1:5057** by default. Override the port with
the `PORT` environment variable, e.g. `PORT=5099 ~/rpa-env/bin/python app.py`.

Stop it with Ctrl+C (or `kill` the process) when done — nothing is left
running by default.

## Seeded data

`data/contacts.json` has two contact records, matched by policy number:

| Policy Number | Contact | Scenario |
|---|---|---|
| `0000001` | Mr J Doe | Straightforward renewal — no complaint, standard occupation/building details, 2 seeded timeline notes, 3 seeded documents. |
| `0198766` | Ms A Smith | Complaint-handling scenario — alarm/security-requirement note references a logged complaint, 2 seeded timeline notes, 2 seeded documents. |

Typing either policy number into the global search bar (top of every
page) and pressing Enter, or clicking "Search", opens the matching
`/contact/<id>` record.

State added during a run (notes entered, documents uploaded) lives in
memory plus on disk under `data/uploads/<contact_id>/` for uploaded
files — restarting the app resets the contact data back to the JSON
seed. The one thing that's durably appended across the run, by design,
is `data/action_log.jsonl`, so an automation's verification step has
something reliable to check regardless of page state.

Full id/selector reference for building the Selenium automation is in
[`SELECTORS.md`](./SELECTORS.md).

## What was verified

Ran the app locally on port 5057 and exercised it with `curl`:

- `GET /` → `200`
- `GET /search?policy_number=0000001` → `302` redirect to `/contact/0000001`
- `GET /search?policy_number=<unknown>` → `302` redirect back to `/` with a `flash-error` message (confirmed rendered, using a cookie jar so the Flask session-based flash survives the redirect)
- `GET /search?policy_number=` (empty) → same redirect-with-flash behavior
- `GET /contact/0000001` and `GET /contact/0198766` → `200`
- `GET /contact/<unknown-id>` → `404`
- `POST /contact/0000001/save-and-close` → `302`, appended a `save_and_close` entry to `action_log.jsonl` with a timestamp
- `POST /contact/0000001/save-and-continue` → `302`, appended a `save_and_continue` entry
- `POST /contact/0000001/customer-care` → `302`, appended a `select_customer_care` entry
- `POST /contact/0000001/notes` (title + body, no attachment) → `302`, note prepended to the in-memory timeline, appended an `add_note_and_close` entry (`has_attachment: false`)
- `POST /contact/0000001/documents/upload` (multipart file) → `302`, file saved under `data/uploads/0000001/`, document appended to the list, appended an `upload_document` entry; confirmed the uploaded file is servable at `GET /uploads/0000001/<stored-name>` → `200`
- `POST /contact/0000001/notes` again, this time with a `note_attachment` file → `302`, appended an `add_note_and_close` entry (`has_attachment: true`)
- `GET /contact/0000001` (default) shows only the most recent 1 document / 1 timeline note with `btn-load-more-documents` / `btn-view-more-timeline` present (since totals were now >1 after the uploads/notes above); `?docs=all` / `?notes=all` show the full lists (confirmed 4 documents and 4 timeline notes all render with distinct `doc-item-N` / `timeline-note-N` ids)
- `GET /contact/0198766/intermediary` → `200`, fields render the seeded dummy broker details
- Confirmed no real production data (`ecclesiastical`, `Craven`, `Richardson-Bunbury`, `crm11.dynamics.com`) appears anywhere under this directory

All checks passed with no bugs found. Test artifacts created during
verification (`data/action_log.jsonl`, the uploaded test PDF under
`data/uploads/`) were removed afterward so the directory is back to a
clean seeded state, and the server was stopped.

## Directory layout

```
dynamics365_mirror/
├── app.py                  Flask app (all routes/logic)
├── SELECTORS.md             Full id/selector reference for RPA locators
├── README.md                This file
├── data/
│   ├── contacts.json         Seed data (2 dummy contacts)
│   ├── action_log.jsonl      Created at runtime; one JSON line per state-changing action
│   └── uploads/<contact_id>/ Created at runtime; uploaded files land here
├── templates/
│   ├── base.html              Shared shell: header, global search, side menu, flash messages
│   ├── search.html            Home / global search page
│   ├── contact.html           Contact record view (the main mirrored screen)
│   └── intermediary.html      Related > Intermediary detail page
└── static/
    └── style.css              Minimal plain CSS, no external CDN dependency
```
