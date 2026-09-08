"""Pulse -- a single-page, click-to-filter bank earnings dashboard.

Everything lives on one page: no tab navigation, no hunting across subject
areas. A KPI strip up top, then a grid of charts, every one of which is a
filter -- click a heatmap cell, a dumbbell, a variance bar, a bubble or a
small-multiple and the whole page recomputes around it.

Charts are native Altair via st.altair_chart(on_select="rerun") rather than
Plotly: Streamlit's selection bridge actually reports Altair selection
params, which is what makes "every chart is a filter" possible here.

All figures are randomly generated and illustrative only -- this is a demo
of Streamlit interactivity, not a real financial report.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from components import charts_alt as C
from components.kpi_tiles import render_kpi_row
from data.generate import generate_dataset
from utils import state
from utils.export import build_csv_bytes, build_excel_bytes

st.set_page_config(page_title="Pulse — Bank Earnings", page_icon="🏦", layout="wide")

st.markdown(
    """
    <style>
    .block-container { padding-top: 2.6rem; padding-bottom: 1rem; max-width: 1500px; }
    .chip-row button {
        border-radius: 999px !important;
        padding: 0.05rem 0.7rem !important;
        font-size: 0.75rem !important;
        border: 1px solid #d7dee6 !important;
        background: #f4f6f8 !important;
        color: #0b0b0b !important;
    }
    .pulse-title { font-size: 1.45rem; font-weight: 800; color: #0b0b0b; margin-bottom: -0.1rem; }
    .pulse-sub { color: #898781; font-size: 0.74rem; }
    .pulse-card-title { font-size: 0.82rem; font-weight: 700; color: #0b0b0b;
                        letter-spacing: 0.01em; line-height: 1.35; }
    .pulse-card-hint { font-size: 0.68rem; color: #898781; line-height: 1.35;
                       margin-bottom: 0.2rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def card(title: str, hint: str = "") -> None:
    st.markdown(f'<div class="pulse-card-title">{title}</div>', unsafe_allow_html=True)
    if hint:
        st.markdown(f'<div class="pulse-card-hint">{hint}</div>', unsafe_allow_html=True)


# -------------------------------------------------------------------- data --
df = generate_dataset()

max_date = df["date"].max()
DEFAULT_END = max_date.date()
DEFAULT_START = (max_date - pd.DateOffset(months=11)).date()
DATA_MIN, DATA_MAX = df["date"].min().date(), df["date"].max().date()

state.init_state(DEFAULT_START, DEFAULT_END, DATA_MIN, DATA_MAX)

# ------------------------------------------------------- header + filters --
head, f1, f2, f3, reset = st.columns([2.6, 1.5, 0.9, 1.1, 0.8], vertical_alignment="bottom")
with head:
    st.markdown('<div class="pulse-title">Pulse — Group Earnings</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="pulse-sub">Illustrative synthetic data. Every chart is a filter — click any mark.</div>',
        unsafe_allow_html=True,
    )

state.sync_before_widgets()
with f1:
    st.date_input("Period", value=st.session_state[state.DATE_KEY], min_value=DATA_MIN, max_value=DATA_MAX,
                  key=state.WIDGET_KEYS[state.DATE_KEY], label_visibility="collapsed")
with f2:
    _scenarios = ["Actual", "Budget"]
    st.selectbox("Scenario", _scenarios, index=_scenarios.index(st.session_state[state.SCENARIO_KEY]),
                 key=state.WIDGET_KEYS[state.SCENARIO_KEY], label_visibility="collapsed")
with f3:
    st.selectbox("Compare To", state.COMPARE_OPTIONS,
                 index=state.COMPARE_OPTIONS.index(st.session_state[state.COMPARE_KEY]),
                 key=state.WIDGET_KEYS[state.COMPARE_KEY], label_visibility="collapsed",
                 help="What the KPI deltas are measured against.")
with reset:
    if st.button("↺ Reset", use_container_width=True):
        state.reset_filters(DEFAULT_START, DEFAULT_END)
        st.rerun()
state.sync_after_widgets()

chips = state.active_filter_chips(DEFAULT_START, DEFAULT_END)
if chips:
    st.markdown('<div class="chip-row">', unsafe_allow_html=True)
    chip_cols = st.columns(min(len(chips), 6) + 3)
    for c, (label, clear_fn) in zip(chip_cols, chips):
        if c.button(f"{label}  ✕", key=f"chip_{label}"):
            clear_fn()
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------------------------------------------------ filtered data --
filtered_df = state.apply_filters(df)
trend_df = state.dim_filtered(df)
budget_df = state.budget_period_df(df)

if st.session_state[state.COMPARE_KEY] == "Budget":
    compare_df, compare_label = budget_df, "budget"
else:
    compare_df, compare_label = state.prior_period_df(df), "prior period"

if filtered_df.empty:
    st.warning("No data matches the current filters. Clear a chip above to get back.")
    state.sync_url()
    st.stop()

segments_sel = st.session_state[state.SEGMENTS_KEY]
regions_sel = st.session_state[state.REGIONS_KEY]

# ----------------------------------------------------------------- KPI row --
render_kpi_row(filtered_df, compare_df, trend_df, compare_label=compare_label)

# ------------------------------------------------------------- chart grid --
row1_a, row1_b = st.columns([1.35, 1])
with row1_a:
    card("Operating income by segment & month", "Click a cell to filter that segment")
    chart, param = C.segment_heatmap(state.apply_filters_excluding(df, "segments"), segments_sel)
    ev = st.altair_chart(chart, on_select="rerun", key=state.chart_key("heatmap"), use_container_width=True)
    if state.handle_altair_select(ev, param, "segment", state.SEGMENTS_KEY, state.chart_key("heatmap")):
        st.rerun()
with row1_b:
    card("Actual vs budget by segment", "Gap = variance · click a dot to filter")
    chart, param = C.segment_dumbbell(state.apply_filters_excluding(df, "segments"), budget_df, segments_sel)
    ev = st.altair_chart(chart, on_select="rerun", key=state.chart_key("dumbbell"), use_container_width=True)
    if state.handle_altair_select(ev, param, "segment", state.SEGMENTS_KEY, state.chart_key("dumbbell")):
        st.rerun()

row2_a, row2_b = st.columns([1, 1.35])
with row2_a:
    card("Variance to budget by region", "Click a bar to filter that region")
    chart, param = C.region_variance(state.apply_filters_excluding(df, "regions"), budget_df, regions_sel)
    ev = st.altair_chart(chart, on_select="rerun", key=state.chart_key("variance"), use_container_width=True)
    if state.handle_altair_select(ev, param, "region", state.REGIONS_KEY, state.chart_key("variance")):
        st.rerun()
with row2_b:
    card("Margin vs efficiency", "Bubble = operating income · click to filter segment")
    chart, param = C.margin_scatter(state.apply_filters_excluding(df, "segments"), segments_sel)
    ev = st.altair_chart(chart, on_select="rerun", key=state.chart_key("scatter"), use_container_width=True)
    if state.handle_altair_select(ev, param, "segment", state.SEGMENTS_KEY, state.chart_key("scatter")):
        st.rerun()

row3_a, row3_b = st.columns([1.15, 1])
with row3_a:
    card("Cash NPAT trend by segment", "Click a panel to filter that segment")
    chart, param = C.trend_facets(state.dim_filtered_excluding(df, "segments"), segments_sel)
    ev = st.altair_chart(chart, on_select="rerun", key=state.chart_key("facets"), use_container_width=True)
    if state.handle_altair_select(ev, param, "segment", state.SEGMENTS_KEY, state.chart_key("facets")):
        st.rerun()
with row3_b:
    card("Profitability bridge", "Operating income to Cash NPAT")
    st.altair_chart(C.pnl_waterfall(filtered_df), use_container_width=True)

# ------------------------------------------------------- detail + export --
with st.expander("Data & export", expanded=False):
    pivot_dim = st.selectbox("Group by", ["segment", "region", "half"], format_func=str.title)
    pivot = (
        filtered_df.groupby(pivot_dim, as_index=False)
        .agg(operating_income=("operating_income", "sum"), cash_npat=("cash_npat", "sum"),
             deposits=("deposits", "sum"), gross_loans=("gross_loans", "sum"))
        .sort_values("cash_npat", ascending=False)
    )
    st.dataframe(
        pivot, hide_index=True, use_container_width=True,
        column_config={
            pivot_dim: pivot_dim.title(),
            "operating_income": st.column_config.NumberColumn("Operating Income", format="A$%.0f"),
            "cash_npat": st.column_config.NumberColumn("Cash NPAT", format="A$%.0f"),
            "deposits": st.column_config.NumberColumn("Deposits", format="A$%.0f"),
            "gross_loans": st.column_config.NumberColumn("Gross Loans", format="A$%.0f"),
        },
    )
    excel_bytes = build_excel_bytes(filtered_df)
    if excel_bytes is not None:
        st.download_button(
            "⬇ Download filtered view as Excel",
            data=excel_bytes,
            file_name="pulse_filtered_export.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.download_button(
            "⬇ Download filtered view as CSV",
            data=build_csv_bytes(filtered_df),
            file_name="pulse_filtered_export.csv",
            mime="text/csv",
        )
        st.caption("Install `XlsxWriter` for the formatted Excel workbook — falling back to CSV.")

st.markdown(
    '<div class="pulse-sub">Synthetic data generated for a Streamlit 1.63 feature demo '
    "(native Altair selection events, st.query_params URL state, column_config). Not the reported "
    "results of any institution.</div>",
    unsafe_allow_html=True,
)

state.sync_url()
