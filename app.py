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

from contextlib import contextmanager

import pandas as pd
import streamlit as st

from components import charts_alt as C
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
    .pulse-card-hint.is-filtered { color: #2a78d6; font-weight: 600; }
    /* Every bordered container (KPI tiles, chart cards) gets breathing room
       below it -- Streamlit lays consecutive containers flush against each
       other otherwise, which is what made the chart grid read as one solid
       block instead of a set of distinct cards. */
    div[data-testid="stVerticalBlockBorderWrapper"] { margin-bottom: 1.1rem; }
    /* The small-multiples facet chart has a fixed per-panel width (it can't
       reflow like a single-view chart can). Streamlit measured it against
       the card's content width and rendered it wider than that -- the
       constraining box turned out to be stFullScreenFrame (Streamlit's
       expand-to-fullscreen wrapper), not the chart element itself, so the
       last panel was bleeding past the card and getting cropped by
       something further up the tree. Scroll rather than crop. */
    div[data-testid="stFullScreenFrame"] { overflow-x: auto; }
    </style>
    """,
    unsafe_allow_html=True,
)


@contextmanager
def card(title: str, hint: str = "", owns: str | None = None):
    """Bordered chart card with a heading that updates live with the active
    cross-filters (Tableau's dynamic-title convention: a click doesn't just
    change what a chart shows, it changes what the chart is now titled).

    `owns` is the filter dimension this specific chart's own marks already
    ARE ("segments"/"regions"/"department") -- left out of its own dynamic
    subtitle, since a chart showing segment bars doesn't need to also tell
    you it's filtered to a segment. Charts that don't own a dimension
    (the waterfall) pass owns=None and show the full active-filter context.
    """
    with st.container(border=True):
        st.markdown(f'<div class="pulse-card-title">{title}</div>', unsafe_allow_html=True)
        ctx = state.filter_summary(exclude=owns)
        if ctx:
            st.markdown(f'<div class="pulse-card-hint is-filtered">Filtered to {ctx}</div>', unsafe_allow_html=True)
        if hint:
            st.markdown(f'<div class="pulse-card-hint">{hint}</div>', unsafe_allow_html=True)
        yield


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

row2_a, row2_b = st.columns(2, gap="medium")
with row2_a:
    with card("Variance to budget by region", "Click a bar to filter that region", owns="regions"):
        chart, param = C.region_variance(state.apply_filters_excluding(df, "regions"), budget_df, regions_sel)
        ev = st.altair_chart(chart, on_select="rerun", key=state.chart_key("variance"), use_container_width=True)
        if state.handle_altair_select(ev, param, "region", state.REGIONS_KEY, state.chart_key("variance")):
            st.rerun()
with row2_b:
    with card("Margin vs efficiency", "Bubble = operating income · click to filter segment", owns="segments"):
        chart, param = C.margin_scatter(state.apply_filters_excluding(df, "segments"), segments_sel)
        ev = st.altair_chart(chart, on_select="rerun", key=state.chart_key("scatter"), use_container_width=True)
        if state.handle_altair_select(ev, param, "segment", state.SEGMENTS_KEY, state.chart_key("scatter")):
            st.rerun()

row3_a, row3_b = st.columns(2, gap="medium")
with row3_a:
    with card("Cash NPAT trend by segment", "Click a panel to filter that segment", owns="segments"):
        chart, param = C.trend_facets(state.dim_filtered_excluding(df, "segments"), segments_sel)
        ev = st.altair_chart(chart, on_select="rerun", key=state.chart_key("facets"), use_container_width=True)
        if state.handle_altair_select(ev, param, "segment", state.SEGMENTS_KEY, state.chart_key("facets")):
            st.rerun()
with row3_b:
    with card("Profitability bridge", "Operating income to Cash NPAT"):
        st.altair_chart(C.pnl_waterfall(filtered_df), use_container_width=True)

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
