"""Plotly chart builders. Every chart returned here is meant to be rendered
with st.plotly_chart(fig, on_select="rerun", selection_mode="points", key=...)
so a click becomes a cross-filter event upstream in app.py.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

NAVY = "#0F4C81"
GOLD = "#C9A227"
GREEN = "#0F8A5F"
RED = "#C0392B"
GRID = "#E5E8EC"
TEXT = "#1A1D21"
MUTED = "#6B7280"

SEGMENT_COLORS = {
    "Retail Banking Services": "#0F4C81",
    "Business Banking": "#2E86AB",
    "Institutional Banking & Markets": "#6FA8C9",
    "New Zealand (ASB)": "#C9A227",
}
REGION_COLORS = px.colors.qualitative.Prism


def _apply_theme(fig: go.Figure, height: int = 320, title: str | None = None, has_legend: bool = False) -> go.Figure:
    has_multiple_traces = len(fig.data) > 1
    show_legend = has_legend or has_multiple_traces
    top_margin = 8
    if title:
        top_margin += 28
    if show_legend:
        top_margin += 24
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=top_margin, b=8),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, size=13),
        title=dict(text=title, x=0, font=dict(size=14, color=TEXT)) if title else None,
        showlegend=show_legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0),
        hoverlabel=dict(bgcolor="white", font_size=12),
        bargap=0.35,
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID, zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=False)
    return fig


def segment_bar(df: pd.DataFrame, metric: str = "operating_income", label: str = "Operating Income") -> go.Figure:
    # Display-only (no on_select wiring in app.py): a plotly bar chart whose
    # own click handler writes back into a session_state key that also
    # colors/labels its own marks stops forwarding click events to Python
    # after the first rerun in this Streamlit build -- see the note in
    # utils/state.py's handle_click_filter docstring. Segment/region
    # filtering here goes through the dropdowns instead.
    df = df.copy()
    is_stock = metric in ("deposits", "gross_loans", "equity")
    if is_stock:
        latest = df["date"].max()
        g = df[df["date"] == latest].groupby("segment", as_index=False)[metric].sum()
    else:
        g = df.groupby("segment", as_index=False)[metric].sum()
    g = g.sort_values(metric, ascending=False)
    short_labels = {
        "Retail Banking Services": "Retail Banking",
        "Business Banking": "Business Banking",
        "Institutional Banking & Markets": "IB&M",
        "New Zealand (ASB)": "New Zealand",
    }
    colors = [SEGMENT_COLORS.get(s, NAVY) for s in g["segment"]]
    fig = go.Figure(
        go.Bar(
            x=g["segment"].map(lambda s: short_labels.get(s, s)),
            y=g[metric],
            marker_color=colors,
        )
    )
    fig.update_yaxes(title=f"{label} (A$)")
    return _apply_theme(fig, height=300, title=f"{label} by segment")


def region_bar(df: pd.DataFrame, metric: str = "operating_income", label: str = "Operating Income") -> go.Figure:
    df = df.copy()
    is_stock = metric in ("deposits", "gross_loans", "equity")
    if is_stock:
        latest = df["date"].max()
        g = df[df["date"] == latest].groupby("region", as_index=False)[metric].sum()
    else:
        g = df.groupby("region", as_index=False)[metric].sum()
    g = g.sort_values(metric)
    fig = go.Figure(go.Bar(x=g["region"], y=g[metric], marker_color=NAVY))
    fig.update_yaxes(title=f"{label} (A$)")
    return _apply_theme(fig, height=260, title=f"{label} by region")


def half_trend_bar(df: pd.DataFrame, selected_half: str | None, metric: str = "cash_npat", label: str = "Cash NPAT") -> go.Figure:
    # selected_half is safe to read here (unlike segment/region's own
    # filter keys): HALF_KEY has no bound filter-strip widget, so coloring
    # against it doesn't hit the plotly on_select issue described in
    # utils/state.py's handle_click_filter docstring.
    df = df.copy()
    g = df.groupby(["half_key", "half", "scenario"], as_index=False)[metric].sum().sort_values("half_key")
    actual = g[g["scenario"] == "Actual"]
    colors = [NAVY if not selected_half or h == selected_half else "#D7DEE6" for h in actual["half"]]
    fig = go.Figure(go.Bar(x=actual["half"], y=actual[metric], marker_color=colors, name="Actual"))
    budget = g[g["scenario"] == "Budget"]
    if not budget.empty:
        fig.add_trace(
            go.Scatter(x=budget["half"], y=budget[metric], mode="markers", marker=dict(color=GOLD, symbol="diamond", size=9), name="Budget")
        )
    fig.update_yaxes(title=f"{label} (A$)")
    return _apply_theme(fig, height=300, title=f"{label} by half — click a bar to filter the period")


def dual_line(df: pd.DataFrame, cols: list[str], names: list[str], colors: list[str], title: str, y_title: str) -> go.Figure:
    df = df.copy()  # see segment_bar's comment on df.copy()
    g = df.groupby("date", as_index=False)[cols].sum().sort_values("date")
    fig = go.Figure()
    for col, name, color in zip(cols, names, colors):
        fig.add_trace(go.Scatter(x=g["date"], y=g[col], mode="lines", name=name, line=dict(color=color, width=2.5)))
    fig.update_yaxes(title=y_title)
    return _apply_theme(fig, height=300, title=title)


def ratio_line(df: pd.DataFrame, kind: str, title: str, target: float | None = None) -> go.Figure:
    df = df.copy()  # see segment_bar's comment on df.copy()
    if kind == "nim":
        g = df.groupby("date").agg(nii=("net_interest_income", "sum"), assets=("avg_interest_earning_assets", "mean"))
        y = g["nii"] * 12 / g["assets"]
    else:
        g = df.groupby("date").agg(opex=("operating_expenses", "sum"), income=("operating_income", "sum"))
        y = g["opex"] / g["income"]
    y = y.sort_index()
    fig = go.Figure(go.Scatter(x=y.index, y=y.values * 100, mode="lines+markers", line=dict(color=NAVY, width=2.5)))
    if target is not None:
        fig.add_hline(y=target * 100, line_dash="dot", line_color=MUTED, annotation_text="target")
    fig.update_yaxes(title="%")
    return _apply_theme(fig, height=280, title=title)


def stacked_balance_area(df: pd.DataFrame) -> go.Figure:
    df = df.copy()  # see segment_bar's comment on df.copy()
    g = df.groupby("date", as_index=False).agg(deposits=("deposits", "sum"), gross_loans=("gross_loans", "sum")).sort_values("date")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=g["date"], y=g["gross_loans"], name="Gross Loans", mode="lines", line=dict(color=NAVY, width=2.5), fill="tozeroy", fillcolor="rgba(15,76,129,0.08)"))
    fig.add_trace(go.Scatter(x=g["date"], y=g["deposits"], name="Deposits", mode="lines", line=dict(color=GOLD, width=2.5), fill="tozeroy", fillcolor="rgba(201,162,39,0.10)"))
    fig.update_yaxes(title="A$")
    return _apply_theme(fig, height=320, title="Deposits vs. gross loans")


def segment_region_treemap(df: pd.DataFrame) -> go.Figure:
    df = df.copy()  # see segment_bar's comment on df.copy()
    g = df.groupby(["segment", "region"], as_index=False)["cash_npat"].sum()
    g = g[g["cash_npat"] > 0]
    fig = px.treemap(
        g,
        path=["segment", "region"],
        values="cash_npat",
        color="segment",
        color_discrete_map=SEGMENT_COLORS,
    )
    fig.update_traces(hovertemplate="%{label}<br>Cash NPAT: A$%{value:,.0f}<extra></extra>")
    return _apply_theme(fig, height=380, title="Cash NPAT by segment and region")
