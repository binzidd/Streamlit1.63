"""Build a formatted Excel workbook from the currently filtered view."""
from __future__ import annotations

import io

import pandas as pd

DISPLAY_COLUMNS = {
    "date": "Month",
    "fy": "FY",
    "half": "Half",
    "segment": "Segment",
    "region": "Region",
    "scenario": "Scenario",
    "operating_income": "Operating Income",
    "operating_expenses": "Operating Expenses",
    "loan_impairment_expense": "Loan Impairment Expense",
    "net_interest_income": "Net Interest Income",
    "cash_npat": "Cash NPAT",
    "statutory_npat": "Statutory NPAT",
    "gross_loans": "Gross Loans",
    "deposits": "Deposits",
    "net_new_customers": "Net New Customers",
}
CURRENCY_COLS = {
    "Operating Income",
    "Operating Expenses",
    "Loan Impairment Expense",
    "Net Interest Income",
    "Cash NPAT",
    "Statutory NPAT",
    "Gross Loans",
    "Deposits",
}


def build_excel_bytes(df: pd.DataFrame, sheet_name: str = "Filtered Data") -> bytes:
    export_df = df[[c for c in DISPLAY_COLUMNS if c in df.columns]].rename(columns=DISPLAY_COLUMNS)
    export_df = export_df.sort_values("Month")

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        export_df.to_excel(writer, index=False, sheet_name=sheet_name)
        workbook = writer.book
        worksheet = writer.sheets[sheet_name]

        header_fmt = workbook.add_format(
            {"bold": True, "bg_color": "#0F4C81", "font_color": "white", "border": 1}
        )
        currency_fmt = workbook.add_format({"num_format": "A$#,##0"})
        date_fmt = workbook.add_format({"num_format": "mmm yyyy"})

        for col_idx, col_name in enumerate(export_df.columns):
            worksheet.write(0, col_idx, col_name, header_fmt)
            width = max(14, len(col_name) + 2)
            if col_name in CURRENCY_COLS:
                worksheet.set_column(col_idx, col_idx, width, currency_fmt)
            elif col_name == "Month":
                worksheet.set_column(col_idx, col_idx, width, date_fmt)
            else:
                worksheet.set_column(col_idx, col_idx, width)

        worksheet.freeze_panes(1, 0)
        worksheet.autofilter(0, 0, len(export_df), len(export_df.columns) - 1)

    return buffer.getvalue()
