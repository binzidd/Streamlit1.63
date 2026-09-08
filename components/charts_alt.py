"""Altair chart builders for the single-page dashboard.

Native Altair (rendered by st.altair_chart) rather than Plotly, for two
reasons: Streamlit's `on_select="rerun"` bridge actually reports selections
for Altair's `selection_point` params -- the Plotly bridge never did for a
bar trace in this build -- so EVERY chart here is click-to-filter; and it
keeps the chart layer on Streamlit's own native rendering path.

Each builder returns (chart, param_name). The caller renders it with
st.altair_chart(chart, on_select="rerun", key=...) and passes param_name to
state.handle_altair_select() to turn a click into a page-wide filter.

Palette: the dataviz skill's validated categorical slots (blue/orange/aqua/
yellow) -- validated on this app's white surface: all gates pass, with aqua
and yellow under 3:1 contrast, which is why the categorical bar forms carry
visible direct labels (the skill's "relief rule").
"""
from __future__ import annotations

import altair as alt
import pandas as pd

from utils.formatting import fmt_currency

# Categorical slots 1-4 (dataviz validated order). Fixed per entity, never
# re-assigned by rank -- so a filter that drops series never repaints the
# survivors.
SERIES = {
    "Retail Banking Services": "#2a78d6",
    "Business Banking": "#eb6834",
    "Institutional Banking & Markets": "#1baf7a",
    "New Zealand (ASB)": "#eda100",
}
SEGMENT_ORDER = list(SERIES)

SHORT = {
    "Retail Banking Services": "Retail",
    "Business Banking": "Business",
    "Institutional Banking & Markets": "IB&M",
    "New Zealand (ASB)": "New Zealand",
}

ACCENT = "#2a78d6"
POS = "#1baf7a"
NEG = "#e34948"
MUTED = "#d7dee6"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
AXIS = "#898781"
GRID = "#e1e0d9"

FONT = "system-ui, -apple-system, 'Segoe UI', sans-serif"

# d3's SI prefix renders 1e9 as "G"; finance reads "B". These Vega
# expressions relabel the axis/legend ticks without touching the values.
MONEY_LABEL = "replace(format(datum.value, '$,.2s'), 'G', 'B')"
MONEY_LABEL_SIGNED = "replace(format(datum.value, '+$,.2s'), 'G', 'B')"


def money_axis(**kwargs) -> alt.Axis:
    return alt.Axis(labelExpr=MONEY_LABEL, **kwargs)


def _base(chart: alt.Chart, height: int) -> alt.Chart:
    return chart.properties(height=height).configure_view(stroke=None).configure_axis(
        labelFont=FONT,
        labelColor=AXIS,
        labelFontSize=10,
        titleFont=FONT,
        titleColor=INK_SECONDARY,
        titleFontSize=11,
        gridColor=GRID,
        domainColor=GRID,
        tickColor=GRID,
    ).configure_legend(
        labelFont=FONT, labelColor=INK_SECONDARY, labelFontSize=11,
        titleFont=FONT, titleColor=INK_SECONDARY, titleFontSize=11,
        orient="top", direction="horizontal", offset=4,
    )


def _emphasis(values: list[str], selected: list[str], colors: dict[str, str] | None = None) -> list[str]:
    """Emphasis colouring: when something is selected, everything else goes
    to the de-emphasis gray. With nothing selected every mark keeps its own
    identity colour."""
    if colors:
        return [colors.get(v, ACCENT) if (not selected or v in selected) else MUTED for v in values]
    return [ACCENT if (not selected or v in selected) else MUTED for v in values]


def segment_department_drill(df_top: pd.DataFrame, df_drilled: pd.DataFrame, selected_segments: list[str],
                             selected_departments: list[str], metric: str = "operating_income",
                             label: str = "Operating Income") -> tuple[alt.Chart, str, str]:
    """Segment totals; click a bar to drill into that segment's departments.

    Replaces a month x segment heatmap: color intensity is a poor tool for
    comparing four-ish magnitudes precisely, and this data made it worse --
    one segment dominates the scale, which crushed the other three into
    near-identical pale cells. Sorted bar length is what actually lets you
    read four values at a glance, and doubles as a natural drill-down
    target: click "Retail" and the same panel re-renders one level down,
    into Retail's own departments.

    `df_top` should already be filtered by everything EXCEPT the segment
    dimension (state.apply_filters_excluding(df, "segments")); `df_drilled`
    by everything except department. Returns (chart, param_name, dim) --
    dim is "segment" at the top level, "department" once drilled, so the
    caller knows which master filter key this level's click belongs to.
    """
    drilled = len(selected_segments) == 1
    param = "drill_click"

    if not drilled:
        g = df_top.groupby("segment", as_index=False)[metric].sum().sort_values(metric, ascending=False)
        g["seg"] = g["segment"].map(SHORT)
        g["color"] = g["segment"].map(SERIES)
        g["amount_label"] = g[metric].map(fmt_currency) + "   +"
        order = g["seg"].tolist()
        click = alt.selection_point(fields=["segment"], name=param)
        bars = alt.Chart(g).mark_bar(cornerRadiusEnd=3, height=24).encode(
            y=alt.Y("seg:N", sort=order, title=None),
            x=alt.X(f"{metric}:Q", title=None, axis=money_axis()),
            color=alt.Color("color:N", scale=None, legend=None),
            tooltip=[alt.Tooltip("segment:N", title="Segment"),
                     alt.Tooltip(f"{metric}:Q", title=label, format="$,.0f")],
        ).add_params(click)
        labels = alt.Chart(g).mark_text(align="left", dx=6, font=FONT, fontSize=10, color=INK_SECONDARY).encode(
            y=alt.Y("seg:N", sort=order), x=alt.X(f"{metric}:Q"), text="amount_label:N",
        )
        return _base(bars + labels, 220), param, "segment"

    seg = selected_segments[0]
    g = df_drilled.groupby("department", as_index=False)[metric].sum().sort_values(metric, ascending=False)
    seg_color = SERIES.get(seg, ACCENT)
    g["emph"] = [seg_color if (not selected_departments or d in selected_departments) else MUTED
                for d in g["department"]]
    g["amount_label"] = g[metric].map(fmt_currency)
    order = g["department"].tolist()
    click = alt.selection_point(fields=["department"], name=param)
    bars = alt.Chart(g).mark_bar(cornerRadiusEnd=3, height=24).encode(
        y=alt.Y("department:N", sort=order, title=None, axis=alt.Axis(labelLimit=220)),
        x=alt.X(f"{metric}:Q", title=None, axis=money_axis()),
        color=alt.Color("emph:N", scale=None, legend=None),
        tooltip=[alt.Tooltip("department:N", title="Department"),
                 alt.Tooltip(f"{metric}:Q", title=label, format="$,.0f")],
    ).add_params(click)
    labels = alt.Chart(g).mark_text(align="left", dx=6, font=FONT, fontSize=10, color=INK_SECONDARY).encode(
        y=alt.Y("department:N", sort=order), x=alt.X(f"{metric}:Q"), text="amount_label:N",
    )
    return _base(bars + labels, 220), param, "department"


def segment_dumbbell(df: pd.DataFrame, budget_df: pd.DataFrame, selected: list[str],
                     metric: str = "operating_income") -> tuple[alt.Chart, str]:
    """Actual vs Budget per segment -- the dumbbell is the "before -> after
    per item" form: one row per segment, the gap IS the variance, which two
    side-by-side bars make you compute by eye."""
    actual = df.groupby("segment", as_index=False)[metric].sum().rename(columns={metric: "actual"})
    budget = budget_df.groupby("segment", as_index=False)[metric].sum().rename(columns={metric: "budget"})
    g = actual.merge(budget, on="segment", how="outer").fillna(0.0)
    g["seg"] = g["segment"].map(SHORT)
    g["variance"] = g["actual"] - g["budget"]
    g["emph"] = _emphasis(g["segment"].tolist(), selected, SERIES)

    param = "dumb_click"
    click = alt.selection_point(fields=["segment"], name=param)
    order = [SHORT[s] for s in SEGMENT_ORDER]

    # Headroom on the right so the variance labels aren't clipped.
    x_max = float(max(g["actual"].max(), g["budget"].max())) * 1.28
    x_scale = alt.Scale(domain=[0, x_max], nice=False)

    rule = alt.Chart(g).mark_rule(stroke=MUTED, strokeWidth=3).encode(
        y=alt.Y("seg:N", sort=order, title=None),
        x=alt.X("budget:Q", title=None, axis=money_axis(), scale=x_scale),
        x2="actual:Q",
    )
    budget_pt = alt.Chart(g).mark_point(filled=True, size=90, shape="diamond", stroke="white", strokeWidth=1.5).encode(
        y=alt.Y("seg:N", sort=order, title=None),
        x=alt.X("budget:Q", scale=x_scale),
        color=alt.value(AXIS),
        tooltip=[alt.Tooltip("segment:N", title="Segment"), alt.Tooltip("budget:Q", title="Budget", format="$,.0f")],
    )
    actual_pt = alt.Chart(g).mark_point(filled=True, size=150, stroke="white", strokeWidth=1.5).encode(
        y=alt.Y("seg:N", sort=order, title=None),
        x=alt.X("actual:Q", scale=x_scale),
        color=alt.Color("emph:N", scale=None, legend=None),
        tooltip=[alt.Tooltip("segment:N", title="Segment"),
                 alt.Tooltip("actual:Q", title="Actual", format="$,.0f"),
                 alt.Tooltip("variance:Q", title="vs Budget", format="+$,.0f")],
    ).add_params(click)
    g["variance_label"] = [("+" if v >= 0 else "−") + fmt_currency(abs(v)) for v in g["variance"]]
    label = alt.Chart(g).mark_text(align="left", dx=10, font=FONT, fontSize=10, color=INK_SECONDARY).encode(
        y=alt.Y("seg:N", sort=order, title=None),
        x=alt.X("actual:Q", scale=x_scale),
        text=alt.Text("variance_label:N"),
    )
    return _base(rule + budget_pt + actual_pt + label, 220), param


def region_variance(df: pd.DataFrame, budget_df: pd.DataFrame, selected: list[str],
                    metric: str = "operating_income") -> tuple[alt.Chart, str]:
    """Variance to budget by region -- a bullet chart: a pale range bar sized
    to the larger of actual/budget, a bold bar for the actual result, and a
    tick marking the budget target. This is the standard BI form for
    actual-vs-target specifically because it doesn't make you compute a
    height difference by eye -- the tick IS the target, the bar IS the
    result, and color says which side of it you landed on."""
    actual = df.groupby("region", as_index=False)[metric].sum().rename(columns={metric: "actual"})
    budget = budget_df.groupby("region", as_index=False)[metric].sum().rename(columns={metric: "budget"})
    g = actual.merge(budget, on="region", how="outer").fillna(0.0)
    g["variance"] = g["actual"] - g["budget"]
    g["pct"] = (g["variance"] / g["budget"].replace(0, pd.NA)).fillna(0.0)
    g["range_max"] = g[["actual", "budget"]].max(axis=1) * 1.15
    g = g.sort_values("actual", ascending=False)
    g["color"] = [POS if v >= 0 else NEG for v in g["variance"]]
    g["emph"] = [1.0 if (not selected or r in selected) else 0.35 for r in g["region"]]
    order = g["region"].tolist()

    param = "var_click"
    click = alt.selection_point(fields=["region"], name=param)

    range_bg = alt.Chart(g).mark_bar(color=GRID, height=20, cornerRadiusEnd=2).encode(
        y=alt.Y("region:N", sort=order, title=None),
        x=alt.X("range_max:Q", title=None, axis=money_axis()),
    )
    actual_bar = (
        alt.Chart(g)
        .mark_bar(height=8, cornerRadiusEnd=2)
        .encode(
            y=alt.Y("region:N", sort=order, title=None),
            x=alt.X("actual:Q"),
            color=alt.Color("color:N", scale=None, legend=None),
            opacity=alt.Opacity("emph:Q", scale=None, legend=None),
            tooltip=[alt.Tooltip("region:N", title="Region"),
                     alt.Tooltip("actual:Q", title="Actual", format="$,.0f"),
                     alt.Tooltip("budget:Q", title="Budget", format="$,.0f"),
                     alt.Tooltip("pct:Q", title="vs Budget", format="+.1%")],
        )
        .add_params(click)
    )
    target = alt.Chart(g).mark_tick(color=INK, thickness=2, height=22).encode(
        y=alt.Y("region:N", sort=order, title=None),
        x=alt.X("budget:Q"),
        tooltip=[alt.Tooltip("region:N", title="Region"), alt.Tooltip("budget:Q", title="Budget target", format="$,.0f")],
    )
    return _base(range_bg + actual_bar + target, 220), param


def margin_scatter(df: pd.DataFrame, selected: list[str]) -> tuple[alt.Chart, str]:
    """Net Interest Margin vs Cost-to-Income, bubble sized by income.

    Emphasis colouring rather than 4 categorical hues: this is an all-pairs
    form (every bubble sits beside every other), where the validated palette
    caps categorical identity at three slots. One accent + gray keeps it
    readable and puts the selected segment forward."""
    # NIM is a monthly rate annualised, so it has to be computed per month
    # and then averaged -- annualising a multi-month SUM of NII would
    # overstate it by the number of months in the window. Both sides of the
    # ratio SUM across whatever rows make up a segment-month (region,
    # department...) -- averaging assets instead silently depends on row
    # count per group, which is what inflated NIM once department rows
    # multiplied the row count without changing the true total.
    monthly = df.groupby(["segment", "date"]).agg(
        nii=("net_interest_income", "sum"),
        assets=("avg_interest_earning_assets", "sum"),
    ).reset_index()
    monthly["nim"] = monthly["nii"] * 12 / monthly["assets"] * 100
    g = df.groupby("segment").agg(
        opex=("operating_expenses", "sum"),
        income=("operating_income", "sum"),
    ).reset_index()
    g = g.merge(monthly.groupby("segment", as_index=False)["nim"].mean(), on="segment")
    g["cti"] = (g["opex"] / g["income"]) * 100
    g["seg"] = g["segment"].map(SHORT)
    g["emph"] = _emphasis(g["segment"].tolist(), selected)

    param = "scatter_click"
    click = alt.selection_point(fields=["segment"], name=param)

    # Median reference lines turn a plain bubble scatter into a four-square
    # analysis: a segment's quadrant (vs the group median on both axes) is
    # the actual read of this chart, not its raw x/y position.
    med_cti = float(g["cti"].median())
    med_nim = float(g["nim"].median())
    x_scale = alt.Scale(zero=False, nice=True)
    y_scale = alt.Scale(zero=False, nice=True)

    vline = alt.Chart(pd.DataFrame({"x": [med_cti]})).mark_rule(stroke=GRID, strokeDash=[4, 3]).encode(
        x=alt.X("x:Q", scale=x_scale),
    )
    hline = alt.Chart(pd.DataFrame({"y": [med_nim]})).mark_rule(stroke=GRID, strokeDash=[4, 3]).encode(
        y=alt.Y("y:Q", scale=y_scale),
    )
    pts = (
        alt.Chart(g)
        .mark_circle(stroke="white", strokeWidth=1.5, opacity=1)
        .encode(
            x=alt.X("cti:Q", title="Cost-to-income %", scale=x_scale),
            y=alt.Y("nim:Q", title="Net interest margin %", scale=y_scale),
            size=alt.Size("income:Q", scale=alt.Scale(range=[200, 1400]), legend=None),
            color=alt.Color("emph:N", scale=None, legend=None),
            tooltip=[alt.Tooltip("segment:N", title="Segment"),
                     alt.Tooltip("nim:Q", title="NIM %", format=".2f"),
                     alt.Tooltip("cti:Q", title="CTI %", format=".1f"),
                     alt.Tooltip("income:Q", title="Operating Income", format="$,.0f")],
        )
        .add_params(click)
    )
    labels = alt.Chart(g).mark_text(dy=-18, font=FONT, fontSize=10, color=INK_SECONDARY).encode(
        x=alt.X("cti:Q", scale=x_scale), y=alt.Y("nim:Q", scale=y_scale), text="seg:N",
    )
    return _base(vline + hline + pts + labels, 220), param


def trend_facets(df: pd.DataFrame, selected: list[str], metric: str = "cash_npat") -> tuple[alt.Chart, str]:
    """Small multiples: one mini trend per segment. Faceting is the honest
    answer to four series on one all-pairs plot -- four overlaid lines would
    need four categorical hues telling apart at every crossing point."""
    g = df.groupby(["date", "segment"], as_index=False)[metric].sum()
    g["seg"] = g["segment"].map(SHORT)
    g["emph"] = _emphasis(g["segment"].tolist(), selected, SERIES)

    param = "facet_click"
    click = alt.selection_point(fields=["segment"], name=param)

    chart = (
        alt.Chart(g)
        .mark_area(
            line={"strokeWidth": 2},
            point=alt.OverlayMarkDef(size=45, filled=True, opacity=1, stroke="white", strokeWidth=1),
            opacity=0.18, interpolate="monotone", clip=True,
        )
        .encode(
            x=alt.X("date:T", title=None, axis=alt.Axis(format="%b %y", labelOverlap=True, tickCount=3)),
            y=alt.Y(f"{metric}:Q", title=None, axis=alt.Axis(labelExpr=MONEY_LABEL, tickCount=3)),
            color=alt.Color("emph:N", scale=None, legend=None),
            tooltip=[alt.Tooltip("segment:N", title="Segment"),
                     alt.Tooltip("date:T", title="Month", format="%b %Y"),
                     alt.Tooltip(f"{metric}:Q", title="Cash NPAT", format="$,.0f")],
        )
        .add_params(click)
        .properties(width=150, height=140)
        .facet(facet=alt.Facet("seg:N", title=None, sort=[SHORT[s] for s in SEGMENT_ORDER],
                               header=alt.Header(labelFont=FONT, labelFontSize=11, labelColor=INK_SECONDARY)),
               columns=4)
    )
    # .facet() returns a FacetChart; configure_* must be applied at this level.
    return chart.configure_view(stroke=None).configure_axis(
        labelFont=FONT, labelColor=AXIS, labelFontSize=9,
        gridColor=GRID, domainColor=GRID, tickColor=GRID,
    ), param


def pnl_waterfall(df: pd.DataFrame) -> alt.Chart:
    """P&L bridge, Operating Income down to Cash NPAT. Display-only: the
    bars are stages of one reconciliation, not a dimension to filter by."""
    income = df["operating_income"].sum()
    opex = df["operating_expenses"].sum()
    impair = df["loan_impairment_expense"].sum()
    cash_npat = df["cash_npat"].sum()
    pretax = income - opex - impair
    tax = max(pretax - cash_npat, 0)

    steps = [
        ("Operating Income", 0.0, income, "total"),
        ("Opex", income - opex, income, "down"),
        ("Loan Impairment", pretax, income - opex, "down"),
        ("Pre-Tax Profit", 0.0, pretax, "total"),
        ("Tax", cash_npat, pretax, "down"),
        ("Cash NPAT", 0.0, cash_npat, "total"),
    ]
    g = pd.DataFrame(steps, columns=["stage", "low", "high", "kind"])
    g["amount"] = [income, -opex, -impair, pretax, -tax, cash_npat]
    g["color"] = g["kind"].map({"total": ACCENT, "down": "#e34948"})
    g["amount_label"] = [
        fmt_currency(a) if k == "total" else ("+" if a >= 0 else "−") + fmt_currency(abs(a))
        for a, k in zip(g["amount"], g["kind"])
    ]

    # Headroom so the value label above the tallest bar isn't clipped.
    y_max = float(max(income, pretax, cash_npat)) * 1.12

    bars = alt.Chart(g).mark_bar(cornerRadius=3, size=34).encode(
        x=alt.X("stage:N", sort=g["stage"].tolist(), title=None, axis=alt.Axis(labelAngle=0, labelLimit=90)),
        y=alt.Y("low:Q", title=None, axis=money_axis(), scale=alt.Scale(domain=[0, y_max], nice=False)),
        y2="high:Q",
        color=alt.Color("color:N", scale=None, legend=None),
        tooltip=[alt.Tooltip("stage:N", title="Stage"), alt.Tooltip("amount:Q", title="Amount", format="+$,.0f")],
    )
    labels = alt.Chart(g).mark_text(dy=-8, font=FONT, fontSize=10, color=INK_SECONDARY, baseline="bottom").encode(
        x=alt.X("stage:N", sort=g["stage"].tolist()),
        y=alt.Y("high:Q"),
        text=alt.Text("amount_label:N"),
    )
    return _base(bars + labels, 220)


def sparkline(series: pd.Series, positive: bool = True) -> alt.Chart:
    """Tiny trend for a KPI stat tile -- no axes, no legend, shape only."""
    g = pd.DataFrame({"date": series.index, "value": series.values})
    return (
        alt.Chart(g)
        .mark_area(line={"strokeWidth": 1.5, "color": ACCENT}, color=ACCENT, opacity=0.15, interpolate="monotone", clip=True)
        .encode(
            x=alt.X("date:T", axis=None),
            y=alt.Y("value:Q", axis=None, scale=alt.Scale(zero=False)),
        )
        .properties(height=38)
        .configure_view(stroke=None)
    )
