"""KPI stat-tile strip: value, delta vs the chosen baseline, sparkline.

A handful of headline numbers is a KPI row of stat tiles, not a chart -- the
value leads, the delta gives it direction, the sparkline gives it shape.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from components import charts_alt as C
from utils.formatting import fmt_currency, fmt_delta_pct, fmt_delta_pp, fmt_pct

POSITIVE = "#006300"
NEGATIVE = "#d03b3b"
NEUTRAL = "#898781"


def _flow(df: pd.DataFrame, col: str) -> pd.Series:
    return df.groupby("date")[col].sum().sort_index()


def _nim(df: pd.DataFrame) -> pd.Series:
    g = df.groupby("date").agg(nii=("net_interest_income", "sum"), assets=("avg_interest_earning_assets", "mean"))
    return (g["nii"] * 12 / g["assets"]).sort_index()


def _cti(df: pd.DataFrame) -> pd.Series:
    g = df.groupby("date").agg(opex=("operating_expenses", "sum"), income=("operating_income", "sum"))
    return (g["opex"] / g["income"]).sort_index()


def _value(series: pd.Series, kind: str) -> float | None:
    if series.empty:
        return None
    if kind == "stock":
        return series.iloc[-1]
    if kind == "ratio":
        return series.mean()
    return series.sum()


KPI_DEFS = [
    dict(key="operating_income", label="Operating Income", kind="flow", fmt=fmt_currency, delta="pct",
         series_fn=lambda d: _flow(d, "operating_income")),
    dict(key="cash_npat", label="Cash NPAT", kind="flow", fmt=fmt_currency, delta="pct",
         series_fn=lambda d: _flow(d, "cash_npat")),
    dict(key="nim", label="Net Interest Margin", kind="ratio", fmt=fmt_pct, delta="pp", series_fn=_nim),
    dict(key="cti", label="Cost-to-Income", kind="ratio", fmt=fmt_pct, delta="pp", invert=True, series_fn=_cti),
    dict(key="loan_impairment_expense", label="Loan Impairment", kind="flow", fmt=fmt_currency, delta="pct",
         invert=True, series_fn=lambda d: _flow(d, "loan_impairment_expense")),
    dict(key="deposits", label="Customer Deposits", kind="stock", fmt=fmt_currency, delta="pct",
         series_fn=lambda d: _flow(d, "deposits")),
]


def render_kpi_row(period_df: pd.DataFrame, compare_df: pd.DataFrame, trend_df: pd.DataFrame,
                   compare_label: str = "prior period") -> None:
    cols = st.columns(len(KPI_DEFS))
    for col, kpi in zip(cols, KPI_DEFS):
        current = _value(kpi["series_fn"](period_df), kpi["kind"])
        baseline = _value(kpi["series_fn"](compare_df), kpi["kind"]) if not compare_df.empty else None

        fmt_delta = fmt_delta_pp if kpi["delta"] == "pp" else fmt_delta_pct
        delta_str, raw = fmt_delta(current, baseline, compare_label) if current is not None else (f"n/a vs {compare_label}", None)

        if raw is None:
            color = NEUTRAL
        elif (raw >= 0) != kpi.get("invert", False):
            color = POSITIVE
        else:
            color = NEGATIVE

        with col, st.container(border=True):
            st.markdown(
                f"<div style='font-size:0.7rem;color:#52514e;line-height:1.2'>{kpi['label']}</div>"
                f"<div style='font-size:1.35rem;font-weight:750;line-height:1.25;color:#0b0b0b'>"
                f"{kpi['fmt'](current) if current is not None else '—'}</div>"
                f"<div style='font-size:0.68rem;color:{color};font-weight:600'>{delta_str}</div>",
                unsafe_allow_html=True,
            )
            spark = kpi["series_fn"](trend_df).tail(18)
            if not spark.empty and spark.notna().any():
                st.altair_chart(C.sparkline(spark), use_container_width=True)
