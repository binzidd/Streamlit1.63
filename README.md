# Pulse — a click-to-filter bank earnings dashboard

A demo built on **Streamlit 1.63.0** to exercise its newer interactivity
primitives: chart/table selection events (`on_select`), `st.segmented_control`,
bordered containers (used for both KPI tiles and the `tile()` chart-card
chrome), `st.query_params` for shareable URL state, and `column_config`
formatting.

> **Illustrative data only.** The dataset is randomly generated (seeded, so
> it's reproducible) in the shape of a diversified bank's earnings — Retail
> Banking, Business Banking, Institutional Banking & Markets, and a New
> Zealand arm. It is **not** the real reported financial results of any
> institution; it exists to give the dashboard a believable, drillable shape.

## Why this design

Built for a time-poor executive who wants the headline in 10 seconds, a
drill-down in 60, and an escape hatch to Excel when they want to keep
digging offline:

- **Every tile is a filter.** Click a bar in the period chart, a row in any
  table, or a KPI tile's "View detail" button, and the whole page — KPI
  numbers, every other chart, every table — recomputes around that
  selection. A dropdown filter strip does the same thing for people who'd
  rather type. There is one shared filter state; clicking and choosing from
  a dropdown are equivalent.
  > **Known limitation:** the segment and region bar charts (and the
  > Sankey/waterfall/treemap) are read-only displays, not click-to-filter,
  > in this build. Streamlit 1.63's `st.plotly_chart(on_select="rerun")`
  > bridge never reports a selection for their bar trace — confirmed by
  > exhaustively testing customdata, `tickvals`/`ticktext` label
  > substitution, `tickangle`, `hovertemplate`, single- vs. multi-trace
  > (legend presence), script position (first/middle/last on the page,
  > alone or combined with other charts), and the state-comparison style,
  > none of which changed the outcome. The period chart (`half_trend_bar`)
  > and data-table row selection use the identical `on_select` mechanism and
  > are reliable for a click-then-observe interaction, so the dropdowns
  > remain how you filter by segment/region — the charts still highlight
  > whichever segments/regions are selected via the dropdown, they just
  > don't emit clicks themselves. One further quirk: a table selection can
  > silently clear itself if you switch views right after making it (the
  > `st.dataframe` widget being unmounted appears to fire a stray empty
  > selection event) — reselect after switching views if that happens.
- **Click again to clear.** Selections toggle off, and active filters show
  as removable pills under the filter strip so it's always obvious why the
  numbers moved.
- **KPI tiles lead with the number**, not the chart — big value, a delta in
  a supporting sentence, a sparkline for shape, in that order. A "Compare
  To" dropdown (Prior Period / Budget) next to the filter strip controls
  what that delta is measured against, for every tile at once.
- **The URL is the view.** Every filter — period, segments, regions,
  scenario, compare-to, even a clicked half-year — round-trips through
  `st.query_params`, so a filtered/drilled-down view can be copied and
  shared, and reloading the link restores it exactly.
- **An Excel escape hatch.** The Data & Export view exports exactly what's
  on screen (respecting all active filters) as a formatted `.xlsx`
  workbook — currency number formats, a frozen header, autofilter — not a
  raw CSV dump.

## Structure

```
app.py                 entry point: layout, filter strip, view routing
data/generate.py        seeded synthetic dataset generator (cached)
utils/state.py          single source of truth for cross-tile filter state
utils/formatting.py      currency/%/delta formatting helpers
utils/export.py          formatted Excel workbook builder
components/kpi_tiles.py  KPI tile row (value, delta, sparkline, drill button)
components/charts.py     Plotly figure builders (half_trend_bar wired for on_select; see its module docstring for the rest)
components/tile.py       bordered-card + icon/title chrome wrapping every chart
.streamlit/config.toml   light corporate theme
```

## Running locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Views

- **Overview** — half-on-half Cash NPAT (click a bar to jump the whole page
  to that half), operating income by segment and by region (display-only,
  see the note above — use the dropdown filters to slice by these), and an
  income-statement Sankey tracing segment income through to expenses, tax,
  and Cash NPAT (also display-only — Plotly Sankey nodes don't emit
  box/lasso selection events for `on_select` to pick up).
- **Profitability** — Net Interest Margin and Cost-to-Income trend lines,
  operating income vs. expenses, a P&L waterfall bridging Operating Income
  down to Cash NPAT (Opex, Loan Impairment, Tax as the bridge steps — the
  same reconciling numbers as the Overview Sankey, as a bridge instead of
  a flow diagram), and loan impairment expense by half.
- **Balance Sheet** — deposits vs. gross loans over time, gross loans by
  segment, deposits by region.
- **Segments** — a treemap of Cash NPAT by segment/region, plus a
  selectable summary table.
- **Data & Export** — a quick group-by pivot, the full filtered dataset
  (selectable rows), and the Excel download.
