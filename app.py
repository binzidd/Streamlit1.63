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
from components.tv_chart import st_tv_chart
from data.generate import (
    SHARES_OUTSTANDING,
    PAYOUT_RATIO,
    generate_dataset,
    generate_peer_data,
    generate_stock_data,
    get_halves,
)
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

state.init_state(DEFAULT_START, DEFAULT_END)
st.session_state.setdefault("active_view", "Overview")

# ------------------------------------------------------------------ header --
left, right = st.columns([3, 1])
with left:
    st.markdown('<div class="pulse-header-title">Pulse — Group Earnings Dashboard</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="pulse-disclaimer">Illustrative synthetic data generated for a Streamlit 1.63 feature demo. '
        "Not the real reported results of any institution. Click the period chart, a table row, or a dropdown to filter the whole page.</div>",
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

f1, f2, f3, f4 = st.columns([1.6, 1.4, 1.4, 1])
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
prior_df = state.prior_period_df(df)
trend_df = state.dim_filtered(df)

if filtered_df.empty:
    st.warning("No data matches the current filter combination. Try clearing a filter above.")
    st.stop()

# ---------------------------------------------------------------- kpi row --
render_kpi_row(filtered_df, prior_df, trend_df, active_view_key="active_view")

st.write("")
active_view = st.segmented_control(
    "View",
    options=["Overview", "Profitability", "Balance Sheet", "Segments", "Market View", "Data & Export"],
    key="active_view",
    label_visibility="collapsed",
)
st.write("")

# ------------------------------------------------------------------- views --
if active_view == "Overview":
    c1, c2 = st.columns([1.3, 1])
    with c1:
        fig = charts.half_trend_bar(trend_df, st.session_state[state.HALF_KEY])
        event = st.plotly_chart(fig, on_select="rerun", selection_mode="points", key="half_chart_overview", use_container_width=True)
        if state.handle_half_click(event, halves):
            st.rerun()
    with c2:
        st.plotly_chart(charts.segment_bar(filtered_df), use_container_width=True, config={"displayModeBar": False})

    st.plotly_chart(charts.region_bar(filtered_df), use_container_width=True, config={"displayModeBar": False})

    st.plotly_chart(charts.income_statement_sankey(filtered_df), use_container_width=True, config={"displayModeBar": False})

elif active_view == "Profitability":
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(charts.ratio_line(filtered_df, "nim", "Net Interest Margin", target=0.020), use_container_width=True, config={"displayModeBar": False})
    with c2:
        st.plotly_chart(charts.ratio_line(filtered_df, "cti", "Cost-to-Income Ratio", target=0.42), use_container_width=True, config={"displayModeBar": False})

    st.plotly_chart(
        charts.dual_line(
            filtered_df,
            cols=["operating_income", "operating_expenses"],
            names=["Operating Income", "Operating Expenses"],
            colors=[charts.NAVY, charts.RED],
            title="Operating income vs. expenses",
            y_title="A$",
        ),
        use_container_width=True,
        config={"displayModeBar": False},
    )

    fig = charts.half_trend_bar(trend_df, st.session_state[state.HALF_KEY], metric="loan_impairment_expense", label="Loan Impairment Expense")
    event = st.plotly_chart(fig, on_select="rerun", selection_mode="points", key="half_chart_profit", use_container_width=True)
    if state.handle_half_click(event, halves):
        st.rerun()

elif active_view == "Balance Sheet":
    st.plotly_chart(charts.stacked_balance_area(filtered_df), use_container_width=True, config={"displayModeBar": False})

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(charts.segment_bar(filtered_df, metric="gross_loans", label="Gross Loans"), use_container_width=True, config={"displayModeBar": False})
    with c2:
        st.plotly_chart(charts.region_bar(filtered_df, metric="deposits", label="Deposits"), use_container_width=True, config={"displayModeBar": False})

elif active_view == "Segments":
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
    if state.handle_table_selection(event, summary, "segment", state.SEGMENTS_KEY):
        st.rerun()

elif active_view == "Market View":
    # ---------------------------------------------------------------- stock data --
    stock_df = generate_stock_data()
    peer_map = generate_peer_data()

    date_start, date_end = st.session_state[state.DATE_KEY]
    ts_start = pd.Timestamp(date_start)
    ts_end   = pd.Timestamp(date_end)

    filtered_stock = stock_df[
        (stock_df["date"] >= ts_start) & (stock_df["date"] <= ts_end)
    ].copy()

    # ----------------------------------------------------------- market KPIs --
    latest_close = filtered_stock["close"].iloc[-1] if not filtered_stock.empty else 0.0
    prev_close   = filtered_stock["close"].iloc[-2] if len(filtered_stock) > 1 else latest_close
    day_chg_pct  = (latest_close - prev_close) / prev_close * 100 if prev_close else 0.0

    # YTD: compare to close on the first trading day of the current calendar year
    ytd_start_year = ts_end.year
    ytd_base_df = stock_df[stock_df["date"].dt.year == ytd_start_year]
    ytd_base = ytd_base_df["close"].iloc[0] if not ytd_base_df.empty else latest_close
    ytd_pct = (latest_close - ytd_base) / ytd_base * 100 if ytd_base else 0.0

    # Earnings-derived: use filtered_df (the earnings data for the period)
    actual_earnings = filtered_df[filtered_df["scenario"] == "Actual"]
    annual_npat = actual_earnings["cash_npat"].sum()
    eps = annual_npat / SHARES_OUTSTANDING
    pe_ratio = latest_close / eps if eps > 0 else 0.0
    dps = eps * PAYOUT_RATIO
    div_yield = dps / latest_close * 100 if latest_close > 0 else 0.0

    mk1, mk2, mk3, mk4, mk5 = st.columns(5)
    with mk1:
        st.metric("Share Price", f"A${latest_close:.2f}", f"{day_chg_pct:+.2f}% today")
    with mk2:
        st.metric("YTD Return", f"{ytd_pct:+.1f}%")
    with mk3:
        st.metric("P/E Ratio", f"{pe_ratio:.1f}×")
    with mk4:
        st.metric("Dividend Yield", f"{div_yield:.2f}%")
    with mk5:
        st.metric("EPS (period)", f"A${eps:.4f}")

    st.write("")

    # ------------------------------------------------ candlestick + volume --
    if filtered_stock.empty:
        st.info("No stock data for the selected date range.")
    else:
        ohlcv = filtered_stock.copy()
        ohlcv["time"] = ohlcv["date"].dt.strftime("%Y-%m-%d")
        series_data = ohlcv[["time", "open", "high", "low", "close"]].to_dict("records")
        vol_data    = ohlcv[["time", "volume"]].rename(columns={"volume": "value"}).to_dict("records")

        st.markdown("**Share price — daily OHLCV**")
        st_tv_chart(
            series_data,
            volume_data=vol_data,
            chart_type="candlestick",
            height=430,
            key="tv_candle",
        )

        st.write("")

        # ----------------------------------------- peer comparison --
        # Normalise bank + peers to 100 at the start of the visible range
        peer_cols, info_col = st.columns([2.2, 1])

        with peer_cols:
            weekly_stock = (
                filtered_stock.set_index("date")["close"]
                .resample("W-FRI")
                .last()
                .dropna()
                .reset_index()
            )
            if not weekly_stock.empty:
                base_price = weekly_stock["close"].iloc[0]
                bank_norm = weekly_stock.copy()
                bank_norm["time"]  = bank_norm["date"].dt.strftime("%Y-%m-%d")
                bank_norm["value"] = (bank_norm["close"] / base_price * 100).round(2)
                bank_series = bank_norm[["time", "value"]].to_dict("records")

                # Slice peer data to the same date range
                overlay_list: list[dict] = []
                peer_colors = {"Peer A": "#C9A227", "Peer B": "#C0392B", "Peer C": "#6FA8C9"}
                for peer_name, peer_df in peer_map.items():
                    sliced = peer_df[
                        (peer_df["time"] >= ts_start.strftime("%Y-%m-%d"))
                        & (peer_df["time"] <= ts_end.strftime("%Y-%m-%d"))
                    ].copy()
                    if sliced.empty:
                        continue
                    base_val = sliced["value"].iloc[0]
                    sliced["value"] = (sliced["value"] / base_val * 100).round(2)
                    overlay_list.append({
                        "name":  peer_name,
                        "color": peer_colors.get(peer_name, "#888"),
                        "data":  sliced[["time", "value"]].to_dict("records"),
                    })

                st.markdown("**Relative performance vs peers (indexed to 100)**")
                st_tv_chart(
                    bank_series,
                    overlays=overlay_list,
                    chart_type="area",
                    height=280,
                    colors={"line": "#0F4C81"},
                    key="tv_peers",
                )

        with info_col:
            st.markdown("**Market snapshot**")
            snap = {
                "Metric": [
                    "Share price",
                    "Day change",
                    "YTD return",
                    "52-wk high",
                    "52-wk low",
                    "P/E ratio",
                    "Div yield",
                    "EPS (period)",
                ],
                "Value": [
                    f"A${latest_close:.2f}",
                    f"{day_chg_pct:+.2f}%",
                    f"{ytd_pct:+.1f}%",
                    f"A${filtered_stock['high'].max():.2f}",
                    f"A${filtered_stock['low'].min():.2f}",
                    f"{pe_ratio:.1f}×",
                    f"{div_yield:.2f}%",
                    f"A${eps:.4f}",
                ],
            }
            st.dataframe(
                snap,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Metric": st.column_config.TextColumn("Metric", width="medium"),
                    "Value":  st.column_config.TextColumn("Value",  width="small"),
                },
            )

        st.caption(
            "All share price data is synthetically generated for this demo and does not represent "
            "the actual trading history of any listed security. Peer returns are also illustrative."
        )

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
    if state.handle_table_selection(event, detail_df, "segment", state.SEGMENTS_KEY):
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
