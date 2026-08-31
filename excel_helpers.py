"""Small helpers for the Excel fixtures, called from renewal_review.robot via Evaluate
(modules=excel_helpers) - kept as plain functions instead of one-line Evaluate
expressions for readability."""
import openpyxl


def read_vulnerable_customer_description(path, policy_display):
    wb = openpyxl.load_workbook(path)
    ws = wb.active
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] == policy_display:
            return row[2]
    raise ValueError(f"No row found for policy {policy_display!r} in {path}")
