"""KPI tile row: big number + delta vs prior period + sparkline, click-to-navigate."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.formatting import fmt_currency, fmt_delta_pct, fmt_delta_pp, fmt_pct, fmt_number

POSITIVE = "#0F8A5F"
NEGATIVE = "#C0392B"
NEUTRAL = "#6B7280"
LINE_COLOR = "#0F4C81"


def _monthly_flow(df: pd.DataFrame, col: str) -> pd.Series:
    return df.groupby("date")[col].sum().sort_index()


def _monthly_stock(df: pd.DataFrame, col: str) -> pd.Series:
    return df.groupby("date")[col].sum().sort_index()


def _monthly_nim(df: pd.DataFrame) -> pd.Series:
    g = df.groupby("date").agg(nii=("net_interest_income", "sum"), assets=("avg_interest_earning_assets", "mean"))
    return (g["nii"] * 12 / g["assets"]).sort_index()


def _monthly_cti(df: pd.DataFrame) -> pd.Series:
    g = df.groupby("date").agg(opex=("operating_expenses", "sum"), income=("operating_income", "sum"))
    return (g["opex"] / g["income"]).sort_index()


def _period_value(series: pd.Series, kind: str) -> float | None:
    if series.empty:
        return None
    if kind == "stock":
        return series.iloc[-1]
    if kind in ("ratio_nim", "ratio_cti"):
        return series.mean()
    return series.sum()


def _sparkline(series: pd.Series, color: str) -> go.Figure:
    fig = go.Figure(
        go.Scatter(
            x=series.index,
            y=series.values,
            mode="lines",
            line=dict(color=color, width=2),
            fill="tozeroy",
            fillcolor="rgba(15, 76, 129, 0.10)",
            hoverinfo="skip",
        )
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=48,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return fig


KPI_DEFS = [
    dict(key="operating_income", label="Operating Income", kind="flow", fmt=fmt_currency, delta="pct", series_fn=lambda d: _monthly_flow(d, "operating_income")),
    dict(key="cash_npat", label="Cash NPAT", kind="flow", fmt=fmt_currency, delta="pct", series_fn=lambda d: _monthly_flow(d, "cash_npat")),
    dict(key="nim", label="Net Interest Margin", kind="ratio_nim", fmt=fmt_pct, delta="pp", series_fn=_monthly_nim),
    dict(key="cti", label="Cost-to-Income Ratio", kind="ratio_cti", fmt=fmt_pct, delta="pp", delta_invert=True, series_fn=_monthly_cti),
    dict(key="loan_impairment_expense", label="Loan Impairment Expense", kind="flow", fmt=fmt_currency, delta="pct", delta_invert=True, series_fn=lambda d: _monthly_flow(d, "loan_impairment_expense")),
    dict(key="deposits", label="Customer Deposits", kind="stock", fmt=fmt_currency, delta="pct", series_fn=lambda d: _monthly_stock(d, "deposits")),
]

VIEW_FOR_KPI = {
    "operating_income": "Overview",
    "cash_npat": "Overview",
    "nim": "Profitability",
    "cti": "Profitability",
    "loan_impairment_expense": "Profitability",
    "deposits": "Balance Sheet",
}


def render_kpi_row(period_df: pd.DataFrame, prior_df: pd.DataFrame, trend_df: pd.DataFrame, active_view_key: str) -> None:
    # .copy(): sparkline/KPI charts and the Overview bar charts otherwise read
    # the same columns off the same shared DataFrame, which confuses
    # Streamlit's plotly_chart on_select bridge for unrelated widgets later
    # in the run (see the matching comment in components/charts.py).
    period_df = period_df.copy()
    prior_df = prior_df.copy()
    trend_df = trend_df.copy()
    cols = st.columns(len(KPI_DEFS))
    for col, kpi in zip(cols, KPI_DEFS):
        series = kpi["series_fn"](period_df)
        current = _period_value(series, kpi["kind"])

        prior_series = kpi["series_fn"](prior_df) if not prior_df.empty else pd.Series(dtype=float)
        prior = _period_value(prior_series, kpi["kind"])

        if kpi["delta"] == "pp":
            delta_str, raw = fmt_delta_pp(current, prior) if current is not None else ("n/a vs prior period", None)
        else:
            delta_str, raw = fmt_delta_pct(current, prior) if current is not None else ("n/a vs prior period", None)

        invert = kpi.get("delta_invert", False)
        if raw is None:
            color = NEUTRAL
        elif (raw >= 0) != invert:
            color = POSITIVE
        else:
            color = NEGATIVE

        trend_series = kpi["series_fn"](trend_df).tail(18)

        with col:
            with st.container(border=True):
                st.caption(kpi["label"])
                st.markdown(
                    f"<div style='font-size:1.6rem;font-weight:700;line-height:1.1;color:#1A1D21'>"
                    f"{kpi['fmt'](current) if current is not None else '—'}</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<div style='font-size:0.78rem;color:{color};font-weight:600;margin-top:2px'>{delta_str}</div>",
                    unsafe_allow_html=True,
                )
                if not trend_series.empty and trend_series.notna().any():
                    st.plotly_chart(
                        _sparkline(trend_series, LINE_COLOR),
                        use_container_width=True,
                        config={"displayModeBar": False},
                        key=f"spark_{kpi['key']}",
                    )
                if st.button("View detail →", key=f"nav_{kpi['key']}", use_container_width=True):
                    st.session_state[active_view_key] = VIEW_FOR_KPI[kpi["key"]]
                    st.rerun()
