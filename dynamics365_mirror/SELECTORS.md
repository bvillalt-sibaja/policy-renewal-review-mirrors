# SELECTORS.md

Every interactive/verifiable element in the Dynamics 365 mirror, with its
stable `id` (and HTTP endpoint where relevant), for use with
`RPA.Browser.Selenium` locators like `id:global-search-input`.

## Global (present on every page — `templates/base.html`)

| id | Element | Notes |
|---|---|---|
| `btn-toggle-menu` | button (hamburger, top-left) | Toggles `#side-menu` visibility via inline JS. |
| `link-app-title` | link | App title / home link. |
| `global-search-form` | form | `GET /search` |
| `global-search-input` | text input | `name="policy_number"` |
| `global-search-button` | submit button | Submits the search form (Enter key also works). |
| `side-menu` | nav (hidden by default) | Revealed by `btn-toggle-menu`. |
| `menu-link-home` | link | Goes to `/`. |
| `menu-link-contacts` | link | Decorative, no-op. |
| `menu-link-cases` | link | Decorative, no-op ("not implemented in mirror"). |
| `menu-link-settings` | link | Decorative, no-op ("not implemented in mirror"). |
| `flash-messages` | div | Wrapper for flash banners, only present when a flash exists. |
| `flash-success` / `flash-info` / `flash-error` | div | One per category, text is the message. |

## Search / home page (`templates/search.html`, route `/`)

| id | Element | Notes |
|---|---|---|
| `table-seed-contacts` | table | Lists all seeded contacts. |
| `row-contact-<id>` | tr | e.g. `row-contact-0000001` |
| `link-open-contact-<id>` | link | Direct link to `/contact/<id>`, bypassing search. |

`GET/POST /search?policy_number=<value>` — looks up the contact whose
policy number matches exactly, then `302` redirects to `/contact/<id>`.
Unknown policy number → `302` redirect back to `/` with a
`flash-error` message; empty value → same, with a different message.

## Contact record page (`templates/contact.html`, route `/contact/<id>`)

Header / actions:

| id | Element | Notes |
|---|---|---|
| `contact-name-heading` | h1 | "Contact: <name>" |
| `contact-policy-number` | strong | Policy number text |
| `contact-scenario-label` | strong | "Straightforward Renewal" or "Complaint Handling" |
| `btn-customer-care` | button | `POST /contact/<id>/customer-care` — logs `select_customer_care`, flashes confirmation, redirects back. |
| `btn-save-and-close` | button | `POST /contact/<id>/save-and-close` — logs `save_and_close` with timestamp, flashes confirmation. |
| `btn-save-and-continue` | button | `POST /contact/<id>/save-and-continue` — logs `save_and_continue` with timestamp, flashes confirmation. |

General info:

| id | Element |
|---|---|
| `field-occupation-details` | read-only div, dummy occupation text |
| `field-building-contents` | read-only div, dummy building & contents summary |
| `field-alarm-requirement-note` | read-only div, dummy CRM alarm/security-requirement free text |

Documents:

| id | Element | Notes |
|---|---|---|
| `btn-upload-document` | button | Reveals `#upload-panel` (client-side JS toggle, mirrors clicking "Upload" in D365). |
| `upload-panel` | div (hidden until "Upload" clicked) | Contains the file input + OK button. |
| `document-upload-input` | file input | `name="document_file"` |
| `btn-upload-ok` | submit button | `POST /contact/<id>/documents/upload` (multipart) — saves file under `data/uploads/<id>/`, appends to the document list, logs `upload_document`, redirects to `?docs=all`. |
| `document-list` | ul | Container for document rows. |
| `doc-item-<n>` | li | 0-indexed within whatever's currently rendered. |
| `btn-load-more-documents` | link | Only rendered when more than 1 document exists and not already showing all; links to `?docs=all`. |

Timeline / notes:

| id | Element | Notes |
|---|---|---|
| `form-timeline-filter` | form | `GET /contact/<id>?filter=<value>` |
| `select-timeline-filter` | select | Options: `no_filter` ("No Filter Applied"), `notes` ("Notes"). Auto-submits on change. |
| `timeline-note-list` | ul | Container for timeline note rows. |
| `timeline-note-<n>` | li | 0-indexed within whatever's currently rendered; newest note added during the session is inserted first. |
| `btn-view-more-timeline` | link | Only rendered when more than 1 note exists and not already showing all; links to `?notes=all`. |
| `btn-enter-note` | button | Reveals `#form-add-note` (client-side JS toggle, mirrors clicking "Enter a Note"). |
| `form-add-note` | form (hidden until "Enter a Note" clicked) | `POST /contact/<id>/notes` (multipart) |
| `note-title-input` | text input | `name="note_title"` |
| `note-body-textarea` | textarea | `name="note_body"` |
| `note-attachment-input` | file input | `name="note_attachment"` — "Add an Attachment" |
| `btn-add-note-and-close` | submit button | Saves the note (prepended to the timeline), logs `add_note_and_close`, redirects to `?notes=all`. |

Related:

| id | Element | Notes |
|---|---|---|
| `link-intermediary` | link | Goes to `/contact/<id>/intermediary`. |

## Intermediary page (`templates/intermediary.html`, route `/contact/<id>/intermediary`)

| id | Element |
|---|---|
| `intermediary-name` | read-only div |
| `intermediary-reference` | read-only div |
| `intermediary-contact` | read-only div |
| `intermediary-phone` | read-only div |
| `link-back-to-contact` | link back to `/contact/<id>` |

## Verification hook (not a page element)

`./data/action_log.jsonl` — one JSON object per line, appended on every
state-changing action (`select_customer_care`, `upload_document`,
`add_note_and_close`, `save_and_close`, `save_and_continue`). Each line
has `timestamp` (UTC ISO-8601), `action`, `contact_id`, and an
action-specific `details` object. An automation's verification step can
tail/parse this file to confirm what actually happened server-side,
independent of what the DOM/flash message claims.
