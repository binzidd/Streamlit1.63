"""Build a formatted Excel workbook from the currently filtered view.

The Excel engine is an optional dependency: build_excel_bytes returns None
when neither xlsxwriter nor openpyxl is installed, so a missing package
degrades the one download button to CSV (see app.py) instead of raising
at import-of-data time and blanking the whole dashboard -- which is what
happened on Streamlit Community Cloud when a version pin stopped
XlsxWriter from installing at all.
"""
from __future__ import annotations

import importlib.util
import io

import pandas as pd

DISPLAY_COLUMNS = {
    "date": "Month",
    "fy": "FY",
    "half": "Half",
    "segment": "Segment",
    "department": "Department",
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


def _excel_engine() -> str | None:
    """First installed Excel writer engine, or None if the workbook can't be built."""
    for engine in ("xlsxwriter", "openpyxl"):
        if importlib.util.find_spec(engine) is not None:
            return engine
    return None


def _display_frame(df: pd.DataFrame) -> pd.DataFrame:
    export_df = df[[c for c in DISPLAY_COLUMNS if c in df.columns]].rename(columns=DISPLAY_COLUMNS)
    return export_df.sort_values("Month")


def build_csv_bytes(df: pd.DataFrame) -> bytes:
    """Always-available fallback for the download button."""
    return _display_frame(df).to_csv(index=False).encode("utf-8")


def build_excel_bytes(df: pd.DataFrame, sheet_name: str = "Filtered Data") -> bytes | None:
    engine = _excel_engine()
    if engine is None:
        return None

    export_df = _display_frame(df)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine=engine) as writer:
        export_df.to_excel(writer, index=False, sheet_name=sheet_name)

        # The formatting below is xlsxwriter's API. openpyxl is only a
        # plain-data fallback, so it just gets the sheet written above.
        if engine == "xlsxwriter":
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
