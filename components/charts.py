"""Plotly chart builders.

Only half_trend_bar and the data-table selections in app.py drive
click-to-filter via st.plotly_chart(on_select="rerun")/st.dataframe
(on_select="rerun") -- segment_bar/region_bar are display-only. Streamlit
1.63's on_select bridge never reports a selection for those two charts'
bar trace no matter how the figure is built (customdata, tickvals/ticktext,
trace count, legend, script position, and comparison style were all ruled
out); see the git history around this comment for the investigation. They
still read the SEGMENTS_KEY/REGIONS_KEY dropdown filters to highlight the
active selection, via apply_filters_excluding() in utils/state.py.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils.formatting import fmt_currency

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
    # Titles now live in the tile() header (components/tile.py), not here --
    # tile-wrapped charts pass no title. Passing title=None (rather than
    # omitting the key) to update_layout still creates an empty Plotly title
    # object, which renders a bold "undefined" tspan client-side, so the key
    # is only included at all when there's an actual string.
    has_multiple_traces = len(fig.data) > 1
    show_legend = has_legend or has_multiple_traces
    top_margin = 8
    if title:
        top_margin += 28
    if show_legend:
        top_margin += 24
    layout = dict(
        height=height,
        margin=dict(l=8, r=8, t=top_margin, b=8),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, size=13),
        showlegend=show_legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0),
        hoverlabel=dict(bgcolor="white", font_size=12),
        bargap=0.35,
    )
    if title:
        layout["title"] = dict(text=title, x=0, font=dict(size=14, color=TEXT))
    fig.update_layout(**layout)
    fig.update_xaxes(showgrid=False, linecolor=GRID, zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=False)
    return fig


MUTED_BAR = "#D7DEE6"


def segment_bar(df: pd.DataFrame, metric: str = "operating_income", label: str = "Operating Income", selected: list[str] | None = None) -> go.Figure:
    # Display-only -- see this module's docstring. df must come from
    # state.apply_filters_excluding(df, "segments") so every segment stays
    # present as a bar regardless of the dropdown filter for this same
    # dimension -- only marker colors change to highlight the selection.
    df = df.copy()
    is_stock = metric in ("deposits", "gross_loans", "equity")
    if is_stock:
        latest = df["date"].max()
        g = df[df["date"] == latest].groupby("segment", as_index=False)[metric].sum()
    else:
        g = df.groupby("segment", as_index=False)[metric].sum()
    g = g.sort_values(metric, ascending=False)
    selected = selected or []
    colors = [SEGMENT_COLORS.get(s, NAVY) if (not selected or s in selected) else MUTED_BAR for s in g["segment"]]
    fig = go.Figure(
        go.Bar(
            x=g["segment"],
            y=g[metric],
            marker_color=colors,
            hovertemplate="%{x}<br>%{y:$,.0f}<extra></extra>",
        )
    )
    fig.update_yaxes(title=f"{label} (A$)")
    return _apply_theme(fig, height=300)


def region_bar(df: pd.DataFrame, metric: str = "operating_income", label: str = "Operating Income", selected: list[str] | None = None) -> go.Figure:
    # Display-only -- see segment_bar's comment above.
    df = df.copy()
    is_stock = metric in ("deposits", "gross_loans", "equity")
    if is_stock:
        latest = df["date"].max()
        g = df[df["date"] == latest].groupby("region", as_index=False)[metric].sum()
    else:
        g = df.groupby("region", as_index=False)[metric].sum()
    g = g.sort_values(metric)
    selected = selected or []
    colors = [NAVY if (not selected or r in selected) else MUTED_BAR for r in g["region"]]
    fig = go.Figure(
        go.Bar(
            x=g["region"],
            y=g[metric],
            marker_color=colors,
            hovertemplate="%{x}<br>%{y:$,.0f}<extra></extra>",
        )
    )
    fig.update_yaxes(title=f"{label} (A$)")
    return _apply_theme(fig, height=260)


def half_trend_bar(df: pd.DataFrame, selected_half: str | None, metric: str = "cash_npat", label: str = "Cash NPAT") -> go.Figure:
    # Click-to-filter -- the one bar chart in this file where on_select
    # actually works; see this module's docstring.
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
    return _apply_theme(fig, height=300)


def dual_line(df: pd.DataFrame, cols: list[str], names: list[str], colors: list[str], y_title: str) -> go.Figure:
    df = df.copy()  # see segment_bar's comment on df.copy()
    g = df.groupby("date", as_index=False)[cols].sum().sort_values("date")
    fig = go.Figure()
    for col, name, color in zip(cols, names, colors):
        fig.add_trace(go.Scatter(x=g["date"], y=g[col], mode="lines", name=name, line=dict(color=color, width=2.5)))
    fig.update_yaxes(title=y_title)
    return _apply_theme(fig, height=300)


def ratio_line(df: pd.DataFrame, kind: str, target: float | None = None) -> go.Figure:
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
    return _apply_theme(fig, height=280)


def stacked_balance_area(df: pd.DataFrame) -> go.Figure:
    df = df.copy()  # see segment_bar's comment on df.copy()
    g = df.groupby("date", as_index=False).agg(deposits=("deposits", "sum"), gross_loans=("gross_loans", "sum")).sort_values("date")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=g["date"], y=g["gross_loans"], name="Gross Loans", mode="lines", line=dict(color=NAVY, width=2.5), fill="tozeroy", fillcolor="rgba(15,76,129,0.08)"))
    fig.add_trace(go.Scatter(x=g["date"], y=g["deposits"], name="Deposits", mode="lines", line=dict(color=GOLD, width=2.5), fill="tozeroy", fillcolor="rgba(201,162,39,0.10)"))
    fig.update_yaxes(title="A$")
    return _apply_theme(fig, height=320)


def income_statement_waterfall(df: pd.DataFrame) -> go.Figure:
    """P&L bridge from Operating Income down to Cash NPAT -- the same
    reconciling figures as income_statement_sankey (opex + impairment + tax
    + cash_npat == operating_income) read as a step-by-step bridge instead
    of a flow diagram."""
    df = df.copy()
    income = df["operating_income"].sum()
    opex = df["operating_expenses"].sum()
    impair = df["loan_impairment_expense"].sum()
    pretax = income - opex - impair
    cash_npat = df["cash_npat"].sum()
    tax = max(pretax - cash_npat, 0)

    # Explicit text labels rather than texttemplate="%{y}": for measure=
    # "total" bars (Pre-Tax Profit, Cash NPAT) Plotly computes the bar's
    # HEIGHT from the running sum and ignores the y value we pass (0,
    # a placeholder) -- but %{y} in a texttemplate still resolves to that
    # raw 0, not the running total, so the total bars would label as $0.
    text = [fmt_currency(v) for v in (income, -opex, -impair, pretax, -tax, cash_npat)]

    fig = go.Figure(
        go.Waterfall(
            x=["Operating Income", "Opex", "Loan Impairment", "Pre-Tax Profit", "Tax", "Cash NPAT"],
            measure=["absolute", "relative", "relative", "total", "relative", "total"],
            y=[income, -opex, -impair, 0, -tax, 0],
            text=text,
            decreasing=dict(marker=dict(color=RED)),
            increasing=dict(marker=dict(color=GREEN)),
            totals=dict(marker=dict(color=NAVY)),
            connector=dict(line=dict(color=GRID, width=1)),
            textposition="outside",
        )
    )
    fig.update_yaxes(title="A$")
    return _apply_theme(fig, height=360)


def income_statement_sankey(df: pd.DataFrame) -> go.Figure:
    # Display-only, like segment_bar/region_bar: Sankey nodes don't emit
    # box/lasso selection events through st.plotly_chart(on_select="rerun"),
    # so there's nothing to wire up here.
    df = df.copy()
    short_labels = {
        "Retail Banking Services": "Retail Banking",
        "Business Banking": "Business Banking",
        "Institutional Banking & Markets": "IB&M",
        "New Zealand (ASB)": "New Zealand",
    }
    seg_totals = (
        df.groupby("segment", as_index=False)["operating_income"]
        .sum()
        .sort_values("operating_income", ascending=False)
    )
    seg_totals = seg_totals[seg_totals["operating_income"] > 0]

    total_opex = df["operating_expenses"].sum()
    total_impair = df["loan_impairment_expense"].sum()
    total_cash_npat = df["cash_npat"].sum()
    total_income = seg_totals["operating_income"].sum()
    total_tax = max(total_income - total_opex - total_impair - total_cash_npat, 0)

    seg_labels = [short_labels.get(s, s) for s in seg_totals["segment"]]
    hub_idx = len(seg_labels)
    outflow_labels = ["Operating Expenses", "Loan Impairment", "Tax", "Cash NPAT"]
    labels = seg_labels + ["Operating Income"] + outflow_labels

    seg_colors = [SEGMENT_COLORS.get(s, NAVY) for s in seg_totals["segment"]]
    outflow_colors = [RED, "#B5651D", MUTED, GREEN]
    node_colors = seg_colors + [NAVY] + outflow_colors

    sources = list(range(len(seg_labels))) + [hub_idx] * 4
    targets = [hub_idx] * len(seg_labels) + [hub_idx + 1, hub_idx + 2, hub_idx + 3, hub_idx + 4]
    values = seg_totals["operating_income"].tolist() + [total_opex, total_impair, total_tax, total_cash_npat]

    def _to_rgba(hex_color: str, alpha: float = 0.35) -> str:
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"

    link_colors = [_to_rgba(c) for c in seg_colors] + [_to_rgba(c) for c in outflow_colors]

    fig = go.Figure(
        go.Sankey(
            arrangement="snap",
            node=dict(label=labels, color=node_colors, pad=18, thickness=16, line=dict(color="white", width=0.5)),
            link=dict(source=sources, target=targets, value=values, color=link_colors),
        )
    )
    fig.update_traces(valueformat=",.0f", valuesuffix=" A$")
    return _apply_theme(fig, height=380)


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
    return _apply_theme(fig, height=380)
