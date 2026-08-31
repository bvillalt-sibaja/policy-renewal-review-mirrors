# policy-renewal-review-mirrors

Companion mirror-app assets for the `renewal_review.robot` policy renewal
review automation (see `bvillalt/policy-renewal-review-automation` for the
automation itself, and `Mimica-Automation/eigalpha-mirror` for the EIGALPHA
mirror). Dummy/fictitious test data throughout - no real systems.

- `outlook_mirror/` - Tkinter mirror of the Outlook mailbox.
- `dynamics365_mirror/` - Flask mirror of the Dynamics 365 CRM contact view.
- `excel_mirror/` - Tkinter mirror of Excel navigation over the fixtures below.
- `fixtures/` - dummy Excel workbooks read/written by the automation.
- `excel_helpers.py`, `verification_helpers.py` - Python helpers called from
  the `.robot` file via `Evaluate`.

Downloaded and extracted at runtime by `renewal_review.robot`'s Suite Setup
(Maker Player only uploads the single `.robot` file, so these assets can't
travel as sibling directories - see that repo's README for details).
