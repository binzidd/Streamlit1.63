"""Pulse -- a click-to-filter bank earnings dashboard.

Built to exercise Streamlit 1.63 features (st.plotly_chart selection events,
st.dataframe row selection, st.segmented_control, bordered containers,
column_config) around a synthetic bank-earnings dataset in the shape of a
retail/business/institutional bank with a New Zealand arm.

All figures are randomly generated and illustrative only -- this is a demo
of Streamlit interactivity, not a real financial report.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from components import charts
from components.kpi_tiles import render_kpi_row
from components.tile import tile
from data.generate import generate_dataset, get_halves
from utils import state
from utils.export import build_excel_bytes

st.set_page_config(page_title="Pulse — Bank Earnings Dashboard", page_icon="🏦", layout="wide")

# ---------------------------------------------------------------- styling --
st.markdown(
    """
    <style>
    .block-container { padding-top: 1.6rem; max-width: 1300px; }
    div[data-testid="stMetric"] { background: white; }
    .chip-row button {
        border-radius: 999px !important;
        padding: 0.15rem 0.8rem !important;
        font-size: 0.78rem !important;
        border: 1px solid #D7DEE6 !important;
        background: #F4F6F8 !important;
        color: #1A1D21 !important;
    }
    div[data-testid="stContainer"]:has(> div > div > div[data-testid="stCaptionContainer"]) {
        transition: box-shadow 0.15s ease;
    }
    .pulse-header-title { font-size: 1.9rem; font-weight: 800; color: #0F4C81; margin-bottom: -0.3rem; }
    .pulse-disclaimer { color: #6B7280; font-size: 0.8rem; }
    .pulse-tile-title { font-size: 0.95rem; font-weight: 700; color: #1A1D21; margin-bottom: 0.1rem; }
    .pulse-tile-icon { margin-right: 0.45rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------------------------- data --
df = generate_dataset()
halves = get_halves(df)

max_date = df["date"].max()
DEFAULT_END = max_date.date()
DEFAULT_START = (max_date - pd.DateOffset(months=11)).date()
DATA_MIN = df["date"].min().date()
DATA_MAX = df["date"].max().date()

state.init_state(DEFAULT_START, DEFAULT_END, DATA_MIN, DATA_MAX)
st.session_state.setdefault("active_view", "Overview")

# ------------------------------------------------------------------ header --
left, right = st.columns([3, 1])
with left:
    st.markdown('<div class="pulse-header-title">Pulse — Group Earnings Dashboard</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="pulse-disclaimer">Illustrative synthetic data generated for a Streamlit 1.63 feature demo. '
        "Not the real reported results of any institution. Click any chart, a table row, or a dropdown to filter "
        "the whole page — the URL updates so a filtered view is shareable.</div>",
        unsafe_allow_html=True,
    )
with right:
    st.write("")
    if st.button("↺ Reset all filters", use_container_width=True):
        state.reset_filters(DEFAULT_START, DEFAULT_END)
        st.rerun()

st.divider()

# ------------------------------------------------------------- filter strip --
state.sync_before_widgets()

f1, f2, f3, f4, f5 = st.columns([1.4, 1.3, 1.3, 1, 1.3])
with f1:
    st.date_input(
        "Period",
        value=st.session_state[state.DATE_KEY],
        min_value=DATA_MIN,
        max_value=DATA_MAX,
        key=state.WIDGET_KEYS[state.DATE_KEY],
    )
with f2:
    st.multiselect(
        "Segment",
        options=state.ALL_SEGMENTS,
        default=st.session_state[state.SEGMENTS_KEY],
        key=state.WIDGET_KEYS[state.SEGMENTS_KEY],
    )
with f3:
    st.multiselect(
        "Region",
        options=state.ALL_REGIONS,
        default=st.session_state[state.REGIONS_KEY],
        key=state.WIDGET_KEYS[state.REGIONS_KEY],
    )
with f4:
    _scenario_options = ["Actual", "Budget"]
    st.selectbox(
        "Scenario",
        options=_scenario_options,
        index=_scenario_options.index(st.session_state[state.SCENARIO_KEY]),
        key=state.WIDGET_KEYS[state.SCENARIO_KEY],
    )
with f5:
    st.selectbox(
        "Compare To",
        options=state.COMPARE_OPTIONS,
        index=state.COMPARE_OPTIONS.index(st.session_state[state.COMPARE_KEY]),
        key=state.WIDGET_KEYS[state.COMPARE_KEY],
        help="What the KPI tiles' deltas are measured against.",
    )

state.sync_after_widgets()

chips = state.active_filter_chips(DEFAULT_START, DEFAULT_END)
if chips:
    st.markdown('<div class="chip-row">', unsafe_allow_html=True)
    chip_cols = st.columns(len(chips) + 2)
    for c, (label, clear_fn) in zip(chip_cols, chips):
        if c.button(f"{label}  ✕", key=f"chip_{label}"):
            clear_fn()
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ------------------------------------------------------------- apply filters --
filtered_df = state.apply_filters(df)
trend_df = state.dim_filtered(df)

if st.session_state[state.COMPARE_KEY] == "Budget":
    compare_df = state.budget_period_df(df)
    compare_label = "budget"
else:
    compare_df = state.prior_period_df(df)
    compare_label = "prior period"

if filtered_df.empty:
    st.warning("No data matches the current filter combination. Try clearing a filter above.")
    state.sync_url()
    st.stop()

# ---------------------------------------------------------------- kpi row --
render_kpi_row(filtered_df, compare_df, trend_df, active_view_key="active_view", compare_label=compare_label)

st.write("")
active_view = st.segmented_control(
    "View",
    options=["Overview", "Profitability", "Balance Sheet", "Segments", "Data & Export"],
    key="active_view",
    label_visibility="collapsed",
)
st.write("")

# ------------------------------------------------------------------- views --
if active_view == "Overview":
    c1, c2 = st.columns([1.3, 1])
    with c1:
        with tile("Cash NPAT by Half", "📈", "Click a bar to filter the period"):
            fig = charts.half_trend_bar(trend_df, st.session_state[state.HALF_KEY])
            event = st.plotly_chart(fig, on_select="rerun", selection_mode="points", key="half_chart_overview", use_container_width=True, config={"displayModeBar": False})
            if state.handle_half_click(event, halves):
                st.rerun()
    with c2:
        with tile("Operating Income by Segment", "🏦"):
            seg_df = state.apply_filters_excluding(df, "segments")
            fig = charts.segment_bar(seg_df, selected=st.session_state[state.SEGMENTS_KEY])
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with tile("Operating Income by Region", "🌏"):
        reg_df = state.apply_filters_excluding(df, "regions")
        fig = charts.region_bar(reg_df, selected=st.session_state[state.REGIONS_KEY])
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with tile("Income Statement Flow", "🌊"):
        st.plotly_chart(charts.income_statement_sankey(filtered_df), use_container_width=True, config={"displayModeBar": False})

elif active_view == "Profitability":
    c1, c2 = st.columns(2)
    with c1:
        with tile("Net Interest Margin", "📐"):
            st.plotly_chart(charts.ratio_line(filtered_df, "nim", target=0.020), use_container_width=True, config={"displayModeBar": False})
    with c2:
        with tile("Cost-to-Income Ratio", "📐"):
            st.plotly_chart(charts.ratio_line(filtered_df, "cti", target=0.42), use_container_width=True, config={"displayModeBar": False})

    with tile("Operating Income vs. Expenses", "💰"):
        st.plotly_chart(
            charts.dual_line(
                filtered_df,
                cols=["operating_income", "operating_expenses"],
                names=["Operating Income", "Operating Expenses"],
                colors=[charts.NAVY, charts.RED],
                y_title="A$",
            ),
            use_container_width=True,
            config={"displayModeBar": False},
        )

    with tile("Profitability Bridge", "💧", "Operating Income to Cash NPAT"):
        st.plotly_chart(charts.income_statement_waterfall(filtered_df), use_container_width=True, config={"displayModeBar": False})

    with tile("Loan Impairment Expense by Half", "📉", "Click a bar to filter the period"):
        fig = charts.half_trend_bar(trend_df, st.session_state[state.HALF_KEY], metric="loan_impairment_expense", label="Loan Impairment Expense")
        event = st.plotly_chart(fig, on_select="rerun", selection_mode="points", key="half_chart_profit", use_container_width=True, config={"displayModeBar": False})
        if state.handle_half_click(event, halves):
            st.rerun()

elif active_view == "Balance Sheet":
    with tile("Deposits vs. Gross Loans", "🏛️"):
        st.plotly_chart(charts.stacked_balance_area(filtered_df), use_container_width=True, config={"displayModeBar": False})

    c1, c2 = st.columns(2)
    with c1:
        with tile("Gross Loans by Segment", "🏦"):
            seg_df = state.apply_filters_excluding(df, "segments")
            fig = charts.segment_bar(seg_df, metric="gross_loans", label="Gross Loans", selected=st.session_state[state.SEGMENTS_KEY])
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with c2:
        with tile("Deposits by Region", "🌏"):
            reg_df = state.apply_filters_excluding(df, "regions")
            fig = charts.region_bar(reg_df, metric="deposits", label="Deposits", selected=st.session_state[state.REGIONS_KEY])
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

elif active_view == "Segments":
    with tile("Cash NPAT by Segment and Region", "🌳"):
        st.plotly_chart(charts.segment_region_treemap(filtered_df), use_container_width=True, config={"displayModeBar": False})

    summary = (
        filtered_df.groupby("segment", as_index=False)
        .agg(
            operating_income=("operating_income", "sum"),
            cash_npat=("cash_npat", "sum"),
            loan_impairment_expense=("loan_impairment_expense", "sum"),
            net_new_customers=("net_new_customers", "sum"),
        )
        .sort_values("cash_npat", ascending=False)
    )
    with tile("Segment Summary", "📋", "Select rows to filter the rest of the page"):
        event = st.dataframe(
            summary,
            hide_index=True,
            use_container_width=True,
            on_select="rerun",
            selection_mode="multi-row",
            key="segment_table",
            column_config={
                "segment": "Segment",
                "operating_income": st.column_config.NumberColumn("Operating Income", format="A$%.0f"),
                "cash_npat": st.column_config.NumberColumn("Cash NPAT", format="A$%.0f"),
                "loan_impairment_expense": st.column_config.NumberColumn("Loan Impairment Exp.", format="A$%.0f"),
                "net_new_customers": st.column_config.NumberColumn("Net New Customers", format="%d"),
            },
        )
        if state.handle_table_selection(event, summary, "segment", state.SEGMENTS_KEY, track_key="segment_table"):
            st.rerun()

else:  # Data & Export
    st.caption("Group by a dimension for a quick pivot, or scroll the full filtered dataset below. Select rows to filter the rest of the page.")
    pivot_dim = st.selectbox("Group by", options=["segment", "region", "half"], format_func=str.title)
    pivot = (
        filtered_df.groupby(pivot_dim, as_index=False)
        .agg(
            operating_income=("operating_income", "sum"),
            cash_npat=("cash_npat", "sum"),
            deposits=("deposits", "sum"),
            gross_loans=("gross_loans", "sum"),
        )
        .sort_values("cash_npat", ascending=False)
    )
    st.dataframe(
        pivot,
        hide_index=True,
        use_container_width=True,
        column_config={
            pivot_dim: pivot_dim.title(),
            "operating_income": st.column_config.NumberColumn("Operating Income", format="A$%.0f"),
            "cash_npat": st.column_config.NumberColumn("Cash NPAT", format="A$%.0f"),
            "deposits": st.column_config.NumberColumn("Deposits", format="A$%.0f"),
            "gross_loans": st.column_config.NumberColumn("Gross Loans", format="A$%.0f"),
        },
    )

    st.write("")
    display_cols = [
        "date", "fy", "half", "segment", "region", "scenario",
        "operating_income", "operating_expenses", "loan_impairment_expense",
        "net_interest_income", "cash_npat", "statutory_npat",
        "gross_loans", "deposits", "net_new_customers",
    ]
    detail_df = filtered_df[display_cols].sort_values("date")
    event = st.dataframe(
        detail_df,
        hide_index=True,
        use_container_width=True,
        height=380,
        on_select="rerun",
        selection_mode="multi-row",
        key="data_table_full",
        column_config={
            "date": st.column_config.DateColumn("Month", format="MMM YYYY"),
            "operating_income": st.column_config.NumberColumn("Operating Income", format="A$%.0f"),
            "operating_expenses": st.column_config.NumberColumn("Operating Expenses", format="A$%.0f"),
            "loan_impairment_expense": st.column_config.NumberColumn("Loan Impairment Exp.", format="A$%.0f"),
            "net_interest_income": st.column_config.NumberColumn("Net Interest Income", format="A$%.0f"),
            "cash_npat": st.column_config.NumberColumn("Cash NPAT", format="A$%.0f"),
            "statutory_npat": st.column_config.NumberColumn("Statutory NPAT", format="A$%.0f"),
            "gross_loans": st.column_config.NumberColumn("Gross Loans", format="A$%.0f"),
            "deposits": st.column_config.NumberColumn("Deposits", format="A$%.0f"),
            "net_new_customers": st.column_config.NumberColumn("Net New Customers", format="%d"),
        },
    )
    if state.handle_table_selection(event, detail_df, "segment", state.SEGMENTS_KEY, track_key="data_table_full"):
        st.rerun()

    st.write("")
    excel_bytes = build_excel_bytes(filtered_df)
    st.download_button(
        "⬇ Download filtered view as Excel",
        data=excel_bytes,
        file_name="pulse_filtered_export.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

st.divider()
st.markdown(
    '<div class="pulse-disclaimer">Pulse is a demo dashboard built to exercise Streamlit 1.63 interactivity '
    "(chart/table selection events, segmented control, bordered containers). All financial figures are "
    "synthetically generated and do not represent any real company's actual results.</div>",
    unsafe_allow_html=True,
)

state.sync_url()
