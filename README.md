# Pulse — a single-page, click-to-filter bank earnings dashboard

A demo built on **Streamlit 1.63.0**. Everything is on one page — no tabs, no
hunting across subject areas — and **every chart is a filter**: click a
segment bar, a dumbbell, a variance bar, a bubble or a small-multiple panel
and the whole page recomputes around that selection.

> **Illustrative data only.** The dataset is randomly generated (seeded, so
> it's reproducible) in the shape of a diversified bank's earnings — Retail
> Banking, Business Banking, Institutional Banking & Markets, and a New
> Zealand arm, each split further into 2-3 departments. It is **not** the
> real reported financial results of any institution; it exists to give the
> dashboard a believable, drillable shape.

## Why native Altair

Charts are native Altair rendered by `st.altair_chart(on_select="rerun")`,
not Plotly. That's the whole reason "every chart is a filter" works here:
Streamlit's selection bridge reliably reports Altair `selection_point`
params, where the Plotly bridge never reported a selection for a bar trace in
this build no matter how the figure was constructed. Selections survive the
rerun cycle, so a click becomes a page-wide filter.

Two behaviours that fall out of how those selections work, both handled in
`utils/state.py`:

- **Charts only ever add a filter; clearing goes through the chips or Reset.**
  A chart's reported selection is sticky and momentarily reads empty while it
  re-renders, so treating "empty" as "the user cleared it" makes charts fight
  each other — one chart's blip wipes another's filter.
- **Clearing a filter remounts the charts.** The live selection lives in the
  browser-side Vega view, so without a remount a chart just re-applies the
  filter you cleared. Popping the session_state key isn't enough (Streamlit
  reuses the DOM element for the same key) — the key itself has to change, so
  chart keys carry a generation counter that clearing bumps.

## The charts

Chosen by what the data has to do, not by variety for its own sake — and
deliberately not six more line and bar charts:

| Chart | Form | Why |
|---|---|---|
| Operating income by segment → department | **sorted bar, two-level drill-down** | click a segment bar and the same panel re-renders one level down into that segment's departments — sorted length reads four-ish magnitudes at a glance and doubles as the drill target, where a heatmap's colour intensity could not |
| Actual vs budget by segment | **dumbbell** | before→after per item — the gap *is* the variance, instead of making you compare two bar heights |
| Variance to budget by region | **diverging bar**, centred on zero | above/below budget reads as direction, not as two similar heights |
| Margin vs efficiency | **bubble scatter**, emphasis colouring | shows the NIM/cost-to-income relationship; one accent + gray rather than four hues, since every bubble sits beside every other |
| Cash NPAT trend by segment | **small multiples** | four series faceted rather than four overlapping lines to tell apart at every crossing |
| Profitability bridge | **waterfall** | the one reconciliation from Operating Income down to Cash NPAT |

Colour follows the dataviz method: the validated categorical slots
(blue/orange/aqua/yellow) assigned per segment in fixed order and never
re-assigned by rank, a single-hue sequential ramp for magnitude, and a
diverging blue↔red pair for variance. The palette was run through the
validator against this app's white surface — all gates pass, with aqua and
yellow under 3:1 contrast, which is why the categorical charts carry visible
direct labels.

## Other behaviour

- **KPI strip** — six stat tiles (value, delta, sparkline). A "Compare To"
  control switches every delta between Prior Period and Budget at once.
- **Every chart card is bordered and titled, and the title tells you what's
  active.** Clicking a mark doesn't just filter the data — the affected
  cards' subtitles update live ("Filtered to Retail Banking Services · Home
  Loans"), Tableau's dynamic-title convention, so the page never shows a
  filtered view without saying so.
- **Department is a full drill-down dimension**, not just a chart feature —
  it filters KPIs, every other chart, and the Data & Export pivot exactly
  like segment or region does.
- **The URL is the view.** Every filter round-trips through `st.query_params`,
  so a filtered view can be copied, shared, and reloaded exactly.
- **An Excel escape hatch.** "Data & export" exports exactly what's on screen,
  respecting active filters, as a formatted `.xlsx` — currency formats, frozen
  header, autofilter — not a raw CSV dump.

## Structure

```
app.py                    single page: filter strip, KPI strip, chart grid
data/generate.py           seeded synthetic dataset generator (cached)
utils/state.py             filter state, chart selections, URL sync
utils/formatting.py        currency/%/delta formatting helpers
utils/export.py            formatted Excel workbook builder
components/charts_alt.py   Altair chart builders (each returns chart + param)
components/kpi_tiles.py    KPI stat-tile strip
.streamlit/config.toml     light theme
```

## Running locally

```bash
pip install -r requirements.txt
streamlit run app.py
```
