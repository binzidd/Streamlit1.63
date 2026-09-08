"""Single source of truth for cross-tile filtering.

Every filter widget AND every chart/table click end up mutating the same
logical filter state, so a dropdown change and a chart click are
equivalent -- any tile that reads via apply_filters() reacts to both.

Streamlit only allows a widget's session_state value to be set *before*
that widget is instantiated in a given script run. Chart-click handling
happens further down the page than the filter dropdowns, so it can't
write directly into a dropdown's own widget key. Instead we keep a
"master" filter value (a plain, non-widget session_state key) that chart
clicks and table selections mutate freely, and a small pending-sync flag
that tells the filter strip to push the master value into the widget key
*before* that widget is created on the next rerun. See sync_before_widgets
/ sync_after_widgets, called from app.py around the filter strip.
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
HALF_KEY = "f_selected_half"

WIDGET_KEYS = {
    DATE_KEY: "w_date_range",
    SEGMENTS_KEY: "w_segments",
    REGIONS_KEY: "w_regions",
    SCENARIO_KEY: "w_scenario",
    COMPARE_KEY: "w_compare",
}

COMPARE_OPTIONS = ["Prior Period", "Budget"]

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
    st.session_state.setdefault(HALF_KEY, None)
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
    if "half" in qp:
        st.session_state[HALF_KEY] = qp["half"] or None


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
    if st.session_state[HALF_KEY]:
        qp["half"] = st.session_state[HALF_KEY]
    elif "half" in qp:
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
            st.session_state[HALF_KEY] = None

    for master_key in (SEGMENTS_KEY, REGIONS_KEY, SCENARIO_KEY, COMPARE_KEY):
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
    the other half of the Compare To toggle (see active_filter_chips and
    render_kpi_row's compare_df/compare_label)."""
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


def handle_half_click(event: dict | None, halves: pd.DataFrame) -> bool:
    """Comparison is against a separate `_last_click_*` tracker (seeded to
    the CURRENT HALF_KEY, not None) rather than HALF_KEY directly. A URL can
    bootstrap HALF_KEY to e.g. "1H26" before this chart has ever actually
    been clicked in this session; on that first render the chart's on_select
    value is naturally empty (nothing clicked yet), and comparing straight
    against HALF_KEY would read that as "the user cleared it" and wipe the
    URL-provided selection immediately."""
    points = []
    if event is not None:
        points = (event.get("selection") or {}).get("points", [])
    new_half = points[0]["x"] if points else None

    last_key = _last_click_key(HALF_KEY)
    st.session_state.setdefault(last_key, st.session_state[HALF_KEY])
    if new_half != st.session_state[last_key]:
        st.session_state[last_key] = new_half
        st.session_state[HALF_KEY] = new_half
        if new_half:
            row = halves.loc[halves["half"] == new_half].iloc[0]
            _set_master(DATE_KEY, (row["start"].date(), row["end"].date()))
        return True
    return False


def handle_table_selection(event: dict | None, filtered_df: pd.DataFrame, dim: str, key: str, track_key: str | None = None) -> bool:
    """Selecting rows in a data table filters other tiles by the dimension values present.

    See handle_click_filter's docstring for why the comparison is against a
    separate `_last_click_*` key rather than `key` itself. `track_key`
    defaults to `key` for a single caller, but must be passed explicitly
    (the table's own st.dataframe `key=`) whenever more than one table
    writes to the same master `key` -- e.g. both the Segments-view summary
    table and the Data & Export detail table filter by "segment" into
    SEGMENTS_KEY. Sharing one `_last_click_*` tracker between them means
    switching from one table's selection to the other (or just switching
    views) looks like "selection went away" and silently clears the filter
    you just set.
    """
    rows = []
    if event is not None:
        event_dict = dict(event)
        rows = list((event_dict.get("selection") or {}).get("rows", []))
    values = sorted(filtered_df.iloc[rows][dim].unique().tolist()) if rows else []

    last_key = _last_click_key(track_key or key)
    st.session_state.setdefault(last_key, [])
    if values != st.session_state[last_key]:
        st.session_state[last_key] = values
        _set_master(key, values)
        return True
    return False


def reset_filters(default_start: dt.date, default_end: dt.date) -> None:
    _set_master(DATE_KEY, (default_start, default_end))
    _set_master(SEGMENTS_KEY, [])
    _set_master(REGIONS_KEY, [])
    _set_master(SCENARIO_KEY, "Actual")
    _set_master(COMPARE_KEY, "Prior Period")
    st.session_state[HALF_KEY] = None


def active_filter_chips(default_start: dt.date, default_end: dt.date) -> list[tuple[str, callable]]:
    chips: list[tuple[str, callable]] = []

    start, end = _current_date_range()
    if (start, end) != (default_start, default_end):
        def _clear_date():
            _set_master(DATE_KEY, (default_start, default_end))
            st.session_state[HALF_KEY] = None

        label = st.session_state[HALF_KEY] or f"{start:%b %Y} – {end:%b %Y}"
        chips.append((f"Period: {label}", _clear_date))

    for seg in st.session_state[SEGMENTS_KEY]:
        def _clear_seg(s=seg):
            _set_master(SEGMENTS_KEY, [v for v in st.session_state[SEGMENTS_KEY] if v != s])

        chips.append((f"Segment: {seg}", _clear_seg))

    for reg in st.session_state[REGIONS_KEY]:
        def _clear_reg(r=reg):
            _set_master(REGIONS_KEY, [v for v in st.session_state[REGIONS_KEY] if v != r])

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
