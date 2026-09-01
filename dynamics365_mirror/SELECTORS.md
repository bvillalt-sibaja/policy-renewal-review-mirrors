# SELECTORS.md

Every interactive/verifiable element in the Dynamics 365 mirror, with its
stable `id` (and HTTP endpoint where relevant), for use with
`RPA.Browser.Selenium` locators like `id:global-search-input`.

## Global (present on every page — `templates/base.html`)

| id | Element | Notes |
|---|---|---|
| `btn-toggle-menu` | button (hamburger, top-left) | Collapses/expands the persistent left nav (`#side-menu`) via inline JS - purely visual, matches the real app's own sidebar-collapse control. |
| `link-app-title` | link | App title / home link. |
| `global-search-form` | form | `GET /search` (present but visually hidden - the real top bar shows a search icon, not an expanded input, until clicked). |
| `global-search-input` | text input | `name="policy_number"` |
| `global-search-button` | submit button | Submits the search form (Enter key also works). |
| `side-menu` | nav (visible by default) | Persistent left navigation; `menu-link-contacts` is the only real link, the rest are decorative labels matching the real app's nav groups (My Work, Customers, Opportunities, Market Information, Apc). |
| `menu-link-contacts` | link | Goes to `/`. |
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

Header:

| id | Element | Notes |
|---|---|---|
| `contact-name-heading` | h1 | "Last, First - Saved" (or "- Unsaved"), matching the real record header. |

Ribbon: only `Save & Close` is wired up (see below) - every other ribbon
button (`Save`, `New`, `Open org chart`, `Deactivate`, `Assign`, `Refresh`,
`Check Access`, `Process`, `Follow`, `Flow`, `Share`) is drawn for visual
completeness only and has no `id`/handler; clicking one safely no-ops.

Customer Care / save flow - matches the real recorded sequence (Write:
Select Toggle Menu → Write: Select Customer Care → Action: Select Save &
Close → Action: Select Save and Continue) exactly, including the real
"Unsaved changes" confirmation prompt:

| id | Element | Notes |
|---|---|---|
| `field-customer-care` | native `<select>` | Options: `--Select--`, `Customer Care`, `Customer Care - F`, `Not Applicable`, `Previous Customer Care`, `Previous Customer Care - F`. Clicking it opens the dropdown ("Select Toggle Menu" in the recording); choosing an option fires a background `POST /contact/<id>/customer-care` (no page reload) that logs `select_customer_care` and persists the value - this is the recording's own separate "Write: Select Customer Care" step. |
| `field-customer-care-4-drivers` | div (lookup placeholder) | Visual only ("Select or search options") - not wired to any action; nothing in the recording shows a distinct click target for it. |
| `btn-save-and-close` | button, `type="button"` | Never posts directly - opens `#modal-unsaved-changes` (matches the real app: Save & Close with a pending field change always prompts before actually saving). |
| `modal-unsaved-changes` | div (hidden until Save & Close is clicked) | "Unsaved changes" dialog: "Do you want to save your changes before leaving this page?" |
| `btn-modal-save-and-continue` | submit button, inside `#form-save-and-continue` | `POST /contact/<id>/save-and-continue` — logs `save_and_continue` with a timestamp and redirects. This is the real action the recording's "Select Save and Continue" step performs - there is no separate ribbon button for it. |
| `btn-modal-discard-changes` | button, `type="button"` | Closes the modal without saving (not used by the current automation, present for completeness). |

General info (left column, `Contact Information`):

| id | Element |
|---|---|
| `field-occupation-details` | read-only div, dummy occupation text |
| `field-building-contents` | read-only div, dummy building & contents summary |
| `field-alarm-requirement-note` | read-only div, dummy CRM alarm/security-requirement free text |

The rest of the left column (Salutation, Title, First/Last/Middle
Name, Suffix, Gender, Date of Birth, Email fields, Occupation,
EdenTree Key Client, Customer Due Diligence, EPS, Owner) is drawn from
each contact's `profile` object in `data/contacts.json` for visual
completeness only - none of it has its own `id`, since nothing in the
recording or this automation reads/writes those fields individually.

Middle column (`Quotes/Policies (Insured)`) is a static empty-state grid
("No data available", "0 - 0 of 0") - decorative only, no `id`s.

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

Timeline / notes (right column):

| id | Element | Notes |
|---|---|---|
| `form-timeline-filter` | form | `GET /contact/<id>?filter=<value>` (not currently rendered as a visible control - kept for the existing `?filter=` query-param behavior). |
| `timeline-note-list` | ul | Container for timeline note rows (styled to match the real Timeline panel: avatar, "Modified on" date, Priority/Closed badges, title, truncated body). |
| `timeline-note-<n>` | li | 0-indexed within whatever's currently rendered; newest note added during the session is inserted first. |
| `btn-view-more-timeline` | link | Only rendered when more than 1 note exists and not already showing all; links to `?notes=all`. |
| `btn-enter-note` | div | Reveals `#form-add-note` (client-side JS toggle, mirrors clicking "Enter a note..."). |
| `form-add-note` | form (hidden until the note row is clicked) | `POST /contact/<id>/notes` (multipart) |
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
`add_note_and_close`, `save_and_continue`). Each line has `timestamp`
(UTC ISO-8601), `action`, `contact_id`, and an action-specific `details`
object. An automation's verification step can tail/parse this file to
confirm what actually happened server-side, independent of what the
DOM/flash message claims.
