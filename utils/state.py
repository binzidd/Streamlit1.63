"""Single source of truth for the dashboard's filter state.

Every chart click and every filter-strip widget mutates the same logical
filter values, so clicking a heatmap cell and picking a scenario from a
dropdown are the same kind of event -- anything reading via apply_filters()
reacts to both, and the whole page stays consistent.

Streamlit only allows a widget's session_state value to be set *before* that
widget is instantiated in a given run, and chart clicks are handled further
down the page than the filter strip. So each filter has a "master" value (a
plain session_state key) that anything may write, plus -- for the filters
that still have a bound input -- a pending flag telling the strip to refresh
that widget's own key before it is next created. See sync_before_widgets /
sync_after_widgets, called from app.py around the filter strip.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd
import streamlit as st

DATE_KEY = "f_date_range"
SEGMENTS_KEY = "f_segments"
REGIONS_KEY = "f_regions"
SCENARIO_KEY = "f_scenario"
COMPARE_KEY = "f_compare"

# Only the filters that still have a bound input widget in the filter strip.
# Segment and region are chart-driven now -- clicking a mark is the only way
# to set them -- so they're plain state with no widget to keep in sync.
WIDGET_KEYS = {
    DATE_KEY: "w_date_range",
    SCENARIO_KEY: "w_scenario",
    COMPARE_KEY: "w_compare",
}

COMPARE_OPTIONS = ["Prior Period", "Budget"]

# Charts that emit selections. Clearing a filter from outside a chart has to
# remount them: a chart's selection lives in the browser-side Vega view and is
# reported back on every rerun, so without a remount the chart re-applies the
# filter the user just cleared. Popping the session_state key is NOT enough --
# Streamlit reuses the DOM element for the same key, and the Vega view (and
# its selection) survives. Changing the key is what actually remounts it, so
# chart keys carry a generation counter that clearing bumps.
CHART_KEYS = ("heatmap", "dumbbell", "variance", "scatter", "facets")
CHART_GEN_KEY = "_chart_generation"


def chart_key(name: str) -> str:
    """Widget key for a selection-emitting chart, for the current generation."""
    return f"{name}_{st.session_state.get(CHART_GEN_KEY, 0)}"

ALL_SEGMENTS = [
    "Retail Banking Services",
    "Business Banking",
    "Institutional Banking & Markets",
    "New Zealand (ASB)",
]
ALL_REGIONS = ["NSW/ACT", "VIC/TAS", "QLD", "WA", "SA/NT", "New Zealand"]


def _pending_flag(widget_key: str) -> str:
    return f"_pending_{widget_key}"


def init_state(default_start: dt.date, default_end: dt.date, data_min: dt.date | None = None, data_max: dt.date | None = None) -> None:
    st.session_state.setdefault(DATE_KEY, (default_start, default_end))
    st.session_state.setdefault(SEGMENTS_KEY, [])
    st.session_state.setdefault(REGIONS_KEY, [])
    st.session_state.setdefault(SCENARIO_KEY, "Actual")
    st.session_state.setdefault(COMPARE_KEY, "Prior Period")
    for widget_key in WIDGET_KEYS.values():
        st.session_state.setdefault(_pending_flag(widget_key), False)
    _bootstrap_from_url(data_min or default_start, data_max or default_end)


def _encode_list(values: list[str]) -> str:
    return ",".join(values)


def _decode_list(raw: str) -> list[str]:
    return [v for v in raw.split(",") if v] if raw else []


def _bootstrap_from_url(data_min: dt.date, data_max: dt.date) -> None:
    """Read filter state out of st.query_params exactly once per session, so
    a filtered/selected view is copy-paste shareable like a Tableau URL.

    Must run before the filter-strip widgets are created (it does -- from
    init_state, called at the top of app.py) and before any dropdown reads
    its master key, since it writes those master keys directly. `data_min`/
    `data_max` clamp a URL-supplied date range to what the date_input widget
    actually allows -- an out-of-range value raises StreamlitAPIException
    when that widget is created."""
    if st.session_state.get("_url_bootstrapped"):
        return
    st.session_state["_url_bootstrapped"] = True
    qp = st.query_params
    if "start" in qp and "end" in qp:
        try:
            start = dt.date.fromisoformat(qp["start"])
            end = dt.date.fromisoformat(qp["end"])
            start = max(min(start, data_max), data_min)
            end = max(min(end, data_max), data_min)
            if start <= end:
                st.session_state[DATE_KEY] = (start, end)
        except ValueError:
            pass
    if "segments" in qp:
        st.session_state[SEGMENTS_KEY] = [s for s in _decode_list(qp["segments"]) if s in ALL_SEGMENTS]
    if "regions" in qp:
        st.session_state[REGIONS_KEY] = [r for r in _decode_list(qp["regions"]) if r in ALL_REGIONS]
    if qp.get("scenario") in ("Actual", "Budget"):
        st.session_state[SCENARIO_KEY] = qp["scenario"]
    if qp.get("compare") in COMPARE_OPTIONS:
        st.session_state[COMPARE_KEY] = qp["compare"]


def sync_url() -> None:
    """Call once, at the end of the script, to mirror current filter state
    into st.query_params so the URL always reflects what's on screen."""
    qp = st.query_params
    start, end = _current_date_range()
    qp["start"] = start.isoformat()
    qp["end"] = end.isoformat()
    if st.session_state[SEGMENTS_KEY]:
        qp["segments"] = _encode_list(st.session_state[SEGMENTS_KEY])
    elif "segments" in qp:
        del qp["segments"]
    if st.session_state[REGIONS_KEY]:
        qp["regions"] = _encode_list(st.session_state[REGIONS_KEY])
    elif "regions" in qp:
        del qp["regions"]
    qp["scenario"] = st.session_state[SCENARIO_KEY]
    qp["compare"] = st.session_state[COMPARE_KEY]
    if "half" in qp:
        del qp["half"]


def _set_master(master_key: str, value) -> None:
    """Update a master filter value, marking its widget (if any) for sync
    before it's next instantiated."""
    st.session_state[master_key] = value
    widget_key = WIDGET_KEYS.get(master_key)
    if widget_key:
        st.session_state[_pending_flag(widget_key)] = True


def sync_before_widgets() -> None:
    """Call once, immediately before creating the filter-strip widgets.

    Deletes each widget's own session_state entry when its master value was
    changed programmatically (a chart click, a chip's clear button) since
    the widget last rendered. With the key absent, Streamlit re-initializes
    the widget from its `default=`/`value=` argument on this run, which
    then reads the up-to-date master value -- the standard, documented way
    to update a widget's displayed value from outside a user interaction.
    """
    for master_key, widget_key in WIDGET_KEYS.items():
        flag = _pending_flag(widget_key)
        if st.session_state.get(flag):
            st.session_state.pop(widget_key, None)
            st.session_state[flag] = False


def sync_after_widgets() -> None:
    """Call once, immediately after creating the filter-strip widgets, to
    pull any direct user edits back into the master filter values."""
    date_val = st.session_state[WIDGET_KEYS[DATE_KEY]]
    if isinstance(date_val, tuple) and len(date_val) == 2:
        if date_val != st.session_state[DATE_KEY]:
            st.session_state[DATE_KEY] = date_val

    for master_key in (SCENARIO_KEY, COMPARE_KEY):
        widget_val = st.session_state[WIDGET_KEYS[master_key]]
        if widget_val != st.session_state[master_key]:
            st.session_state[master_key] = widget_val


def _current_date_range() -> tuple[dt.date, dt.date]:
    val = st.session_state[DATE_KEY]
    if isinstance(val, tuple) and len(val) == 2:
        return val
    if isinstance(val, tuple) and len(val) == 1:
        return val[0], val[0]
    return val, val


def _base_mask(df: pd.DataFrame) -> pd.Series:
    mask = df["scenario"] == st.session_state[SCENARIO_KEY]
    if st.session_state[SEGMENTS_KEY]:
        mask &= df["segment"].isin(st.session_state[SEGMENTS_KEY])
    if st.session_state[REGIONS_KEY]:
        mask &= df["region"].isin(st.session_state[REGIONS_KEY])
    return mask


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    start, end = _current_date_range()
    mask = (df["date"] >= pd.Timestamp(start)) & (df["date"] <= pd.Timestamp(end))
    mask &= _base_mask(df)
    return df.loc[mask]


def apply_filters_excluding(df: pd.DataFrame, exclude: str) -> pd.DataFrame:
    """Like apply_filters, but skips one dimension's OWN filter -- "segments"
    or "regions". Used to build segment_bar/region_bar's figure so every
    segment/region stays present as a bar regardless of the dropdown filter
    for that same dimension -- only marker colors change, to highlight the
    active selection (see charts.py's `selected` param) instead of the chart
    shrinking to a single bar. (segment_bar/region_bar are display-only --
    Streamlit's on_select bridge doesn't report clicks on their trace in
    this build, see charts.py's module docstring -- but this still matters:
    without it, choosing a segment from the dropdown would leave its own
    "by segment" chart showing just one bar, which reads as broken.)
    """
    start, end = _current_date_range()
    mask = (df["date"] >= pd.Timestamp(start)) & (df["date"] <= pd.Timestamp(end))
    mask &= df["scenario"] == st.session_state[SCENARIO_KEY]
    if exclude != "segments" and st.session_state[SEGMENTS_KEY]:
        mask &= df["segment"].isin(st.session_state[SEGMENTS_KEY])
    if exclude != "regions" and st.session_state[REGIONS_KEY]:
        mask &= df["region"].isin(st.session_state[REGIONS_KEY])
    return df.loc[mask]


def dim_filtered(df: pd.DataFrame) -> pd.DataFrame:
    """Segment/region/scenario filters only, ignoring the date range -- used to
    draw full-history sparklines/trend charts that still respect dimension
    cross-filters."""
    return df.loc[_base_mask(df)]


def dim_filtered_excluding(df: pd.DataFrame, exclude: str) -> pd.DataFrame:
    """dim_filtered, minus one dimension's own filter -- the full-history
    equivalent of apply_filters_excluding, for the small-multiples trend
    (every segment keeps its panel; the selected one is highlighted)."""
    mask = df["scenario"] == st.session_state[SCENARIO_KEY]
    if exclude != "segments" and st.session_state[SEGMENTS_KEY]:
        mask &= df["segment"].isin(st.session_state[SEGMENTS_KEY])
    if exclude != "regions" and st.session_state[REGIONS_KEY]:
        mask &= df["region"].isin(st.session_state[REGIONS_KEY])
    return df.loc[mask]


def prior_period_df(df: pd.DataFrame) -> pd.DataFrame:
    """Same dimension filters, but the immediately preceding window of equal length."""
    start, end = _current_date_range()
    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    length = end_ts - start_ts
    prior_end = start_ts - pd.DateOffset(months=1)
    prior_start = prior_end - length

    mask = (df["date"] >= prior_start) & (df["date"] <= prior_end)
    mask &= _base_mask(df)
    return df.loc[mask]


def budget_period_df(df: pd.DataFrame) -> pd.DataFrame:
    """Same period and segment/region filters, but the Budget scenario --
    the other half of the Compare To toggle (see render_kpi_row's
    compare_df/compare_label)."""
    start, end = _current_date_range()
    mask = (df["date"] >= pd.Timestamp(start)) & (df["date"] <= pd.Timestamp(end))
    mask &= df["scenario"] == "Budget"
    if st.session_state[SEGMENTS_KEY]:
        mask &= df["segment"].isin(st.session_state[SEGMENTS_KEY])
    if st.session_state[REGIONS_KEY]:
        mask &= df["region"].isin(st.session_state[REGIONS_KEY])
    return df.loc[mask]


def _last_click_key(key: str) -> str:
    return f"_last_click_{key}"


def handle_altair_select(event: dict | None, param: str, dim: str, master_key: str, track_key: str) -> bool:
    """Turn a click on an Altair chart into a page-wide filter.

    st.altair_chart(on_select="rerun") reports a `selection_point` param as
    `event.selection[<param name>]`: a list of the selected rows, each a dict
    of that row's encoded fields. So `dim` is just a column name to read off
    those rows.

    `track_key` is the chart's own st.altair_chart key, NOT `master_key`:
    several charts filter the same dimension (the heatmap, the dumbbell and
    the small multiples all write SEGMENTS_KEY), and a tracker shared between
    them would read one chart's empty selection as "the user cleared it" and
    wipe what another chart just set. Returns True if state changed, so the
    caller can st.rerun().
    """
    rows = []
    if event is not None:
        rows = ((event.get("selection") or {}).get(param) or [])
    values = sorted({r[dim] for r in rows if isinstance(r, dict) and r.get(dim) is not None})

    # An EMPTY selection is never treated as "the user cleared this filter" --
    # clearing is the chips' and Reset's job. A chart's reported selection is
    # sticky in Streamlit's widget state but momentarily reads empty while the
    # chart re-renders, so acting on empty makes charts fight each other: the
    # blip zeroes this tracker, and the chart's sticky value then re-applies
    # itself on the next unrelated interaction, swallowing that click.
    if not values:
        return False

    tracker = _last_click_key(track_key)
    st.session_state.setdefault(tracker, [])
    if values != st.session_state[tracker]:
        st.session_state[tracker] = values
        _set_master(master_key, values)
        return True
    return False




def clear_chart_selections() -> None:
    """Remount every selection-emitting chart, dropping its live selection.

    Called whenever a filter is cleared from outside a chart (Reset, or a
    chip's X). Bumping the generation changes every chart's widget key, which
    is what actually gives us a fresh Vega view with nothing selected; the old
    keys' state and trackers are then dead and swept up here."""
    for name in CHART_KEYS:
        old = chart_key(name)
        st.session_state.pop(old, None)
        st.session_state.pop(_last_click_key(old), None)
    st.session_state[CHART_GEN_KEY] = st.session_state.get(CHART_GEN_KEY, 0) + 1


def reset_filters(default_start: dt.date, default_end: dt.date) -> None:
    _set_master(DATE_KEY, (default_start, default_end))
    _set_master(SEGMENTS_KEY, [])
    _set_master(REGIONS_KEY, [])
    _set_master(SCENARIO_KEY, "Actual")
    _set_master(COMPARE_KEY, "Prior Period")
    clear_chart_selections()


def active_filter_chips(default_start: dt.date, default_end: dt.date) -> list[tuple[str, callable]]:
    chips: list[tuple[str, callable]] = []

    start, end = _current_date_range()
    if (start, end) != (default_start, default_end):
        def _clear_date():
            _set_master(DATE_KEY, (default_start, default_end))

        chips.append((f"Period: {start:%b %Y} – {end:%b %Y}", _clear_date))

    for seg in st.session_state[SEGMENTS_KEY]:
        def _clear_seg(s=seg):
            _set_master(SEGMENTS_KEY, [v for v in st.session_state[SEGMENTS_KEY] if v != s])
            clear_chart_selections()

        chips.append((f"Segment: {seg}", _clear_seg))

    for reg in st.session_state[REGIONS_KEY]:
        def _clear_reg(r=reg):
            _set_master(REGIONS_KEY, [v for v in st.session_state[REGIONS_KEY] if v != r])
            clear_chart_selections()

        chips.append((f"Region: {reg}", _clear_reg))

    if st.session_state[SCENARIO_KEY] != "Actual":
        def _clear_scenario():
            _set_master(SCENARIO_KEY, "Actual")

        chips.append((f"Scenario: {st.session_state[SCENARIO_KEY]}", _clear_scenario))

    if st.session_state[COMPARE_KEY] != "Prior Period":
        def _clear_compare():
            _set_master(COMPARE_KEY, "Prior Period")

        chips.append((f"Compare to: {st.session_state[COMPARE_KEY]}", _clear_compare))

    return chips
