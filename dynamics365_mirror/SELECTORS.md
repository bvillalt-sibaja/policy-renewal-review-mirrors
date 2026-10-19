# SELECTORS.md

Every interactive/verifiable element in the Dynamics 365 mirror, with its
stable `id` (and HTTP endpoint where relevant), for use with
`RPA.Browser.Selenium` locators like `id:global-search-input`.

## Global (present on every page — `templates/base.html`)

| id | Element | Notes |
|---|---|---|
| `btn-toggle-menu` | button (hamburger, top of the left sitemap) | Collapses the persistent left nav (`#side-menu`) to an icon rail and back via inline JS - purely visual, matches the real app's own sitemap-collapse control. |
| `link-app-title` | link | App title / home link. |
| `global-search-form` | form | `GET /search` (hidden until the top bar's magnifier icon is clicked - the real top bar shows a search icon, not an expanded input). Navigating to `/search?policy_number=<n>` directly works regardless. |
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
| `contact-name-heading` | h1 | "Last, First - Saved", matching the real record header. Changing Customer Care flips the status span (`contact-record-status`) to "- Unsaved" client-side until the page reloads (e.g. after Save and continue), as in the recording. |

Command bar (sticky under the top bar): only `Save & Close` is wired up
(see below) - every other command (back arrow, pop-out, `Save`, `New`,
`Open org chart`, `Deactivate`, `Assign`, `Refresh`, `Check Access`,
`Process`, `Follow`, `Flow`, the overflow "more" button, `Share`) is drawn
for visual completeness only and has no `id`; clicking one safely no-ops
(the back arrow goes to `/`). Commands that don't fit the window width
wrap out of view behind the overflow button, like the real app - `Save &
Close` is 4th so stays visible at any normal window width.

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

General info (full-width `General Information` section below the three columns - always rendered/visible, no tab switching needed):

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
| `btn-upload-document` | button ("Upload" in the Document Associated Grid command bar) | Reveals `#upload-panel` (client-side JS toggle, mirrors clicking "Upload" in D365). |
| `upload-panel` | div (hidden until "Upload" clicked) | The "Upload Documents" dialog (modal overlay, still inside `#form-upload-document`): File Upload input, size-limit hint, decorative "Overwrite existing files" toggle, OK + Cancel. |
| `document-upload-input` | file input | `name="document_file"` |
| `btn-upload-ok` | submit button | `POST /contact/<id>/documents/upload` (multipart) — saves file under `data/uploads/<id>/`, appends to the document list, logs `upload_document`, redirects to `?docs=all`. |
| `document-list` | ul | Container for document rows. |
| `doc-item-<n>` | li | 0-indexed within whatever's currently rendered; laid out as a grid row (Name / Created On / Modified / Modified by / Source). |
| `doc-link-<n>` | link inside `doc-item-<n>` | Its only text node is the file name (file-type icon sits outside the `<a>`), so `//a[contains(@id,'doc-link-') and contains(text(),'UW_Pathway_Report')]` matches. Opens `/contact/<id>/documents/<n>` in the same tab and logs `select_document`. |
| `btn-load-more-documents` | link ("Load More Documents") | Only rendered when more than 1 document exists and not already showing all; links to `?docs=all`. |

Timeline / notes (right column):

| id | Element | Notes |
|---|---|---|
| `form-timeline-filter` | form | `GET /contact/<id>?filter=<value>` (not currently rendered as a visible control - kept for the existing `?filter=` query-param behavior). |
| `timeline-note-list` | ul | Container for timeline note rows (styled to match the real Timeline panel: avatar, "Modified on" date, Priority/Closed badges, title, truncated body). |
| `timeline-note-<n>` | li | 0-indexed within whatever's currently rendered; newest note added during the session is inserted first. |
| `btn-view-more-timeline` | link ("Show more") | Only rendered when more than 1 note exists and not already showing all; links to `?notes=all`. Each card's own "View more" row is a decorative client-side expand (no `id`). |
| `btn-enter-note` | div ("Enter a note..." row in the Timeline) | Reveals `#form-add-note` (client-side JS toggle, mirrors clicking "Enter a note..."). |
| `form-add-note` | form (hidden until the note row is clicked) | Rendered inline in the Timeline column ("Create a note"), inside `#section-notes-form`. `POST /contact/<id>/notes` (multipart) |
| `note-title-input` | text input | `name="note_title"` |
| `note-body-textarea` | textarea | `name="note_body"` |
| `note-attachment-input` | file input | `name="note_attachment"` — "Add an Attachment" |
| `btn-add-note-and-close` | submit button ("Add note and close") | Saves the note (prepended to the timeline), logs `add_note_and_close`, redirects to `?notes=all`. |

Related:

| id | Element | Notes |
|---|---|---|
| `link-intermediary` | link ("Intermediary: <name>") | Goes to `/contact/<id>/intermediary` (same tab). |
| `link-related-pseudo` | link | Goes to `/contact/<id>/pseudo` (same tab - deliberately no `target=_blank`). |

## Intermediary page (`templates/intermediary.html`, route `/contact/<id>/intermediary`)

Styled as the real Quote/Policy record "Intermediary [Last, First] - Saved"
(locked-record notice bar, header fields, Messages/General/Activities/
Documents/Related tabs, Basic Information lookups, activities grid).

| id | Element |
|---|---|
| `intermediary-name` | span - the Agency lookup's text (Get Text returns just the broker name) |
| `intermediary-reference` | span - Agency Reference value |
| `intermediary-contact` | span - Broker Contact value |
| `intermediary-phone` | span - Broker Phone value |
| `link-back-to-contact` | the command bar's back arrow (`<a>`, visually-hidden label "Back to Contact") → `/contact/<id>` |

## Document page (`templates/document.html`, route `/contact/<id>/documents/<n>`)

| id | Element |
|---|---|
| `section-document-detail` | document viewer panel |
| `document-name-heading` | h1, file name |
| `field-document-content` | read-only div, the document's text content |
| `link-back-to-contact` | command bar back arrow → `/contact/<id>` |

## Pseudo page (`templates/pseudo.html`, route `/contact/<id>/pseudo`)

| id | Element |
|---|---|
| `section-pseudo-detail` | section |
| `pseudo-summary` | read-only div, summary text |
| `link-back-to-contact` | command bar back arrow → `/contact/<id>` |

## Verification hook (not a page element)

`./data/action_log.jsonl` — one JSON object per line, appended on every
state-changing action (`select_customer_care`, `select_document`, `upload_document`,
`add_note_and_close`, `save_and_continue`). Each line has `timestamp`
(UTC ISO-8601), `action`, `contact_id`, and an action-specific `details`
object. An automation's verification step can tail/parse this file to
confirm what actually happened server-side, independent of what the
DOM/flash message claims.
