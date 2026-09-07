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
HALF_KEY = "f_selected_half"

WIDGET_KEYS = {
    DATE_KEY: "w_date_range",
    SEGMENTS_KEY: "w_segments",
    REGIONS_KEY: "w_regions",
    SCENARIO_KEY: "w_scenario",
}

ALL_SEGMENTS = [
    "Retail Banking Services",
    "Business Banking",
    "Institutional Banking & Markets",
    "New Zealand (ASB)",
]
ALL_REGIONS = ["NSW/ACT", "VIC/TAS", "QLD", "WA", "SA/NT", "New Zealand"]


def _pending_flag(widget_key: str) -> str:
    return f"_pending_{widget_key}"


def init_state(default_start: dt.date, default_end: dt.date) -> None:
    st.session_state.setdefault(DATE_KEY, (default_start, default_end))
    st.session_state.setdefault(SEGMENTS_KEY, [])
    st.session_state.setdefault(REGIONS_KEY, [])
    st.session_state.setdefault(SCENARIO_KEY, "Actual")
    st.session_state.setdefault(HALF_KEY, None)
    for widget_key in WIDGET_KEYS.values():
        st.session_state.setdefault(_pending_flag(widget_key), False)


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

    for master_key in (SEGMENTS_KEY, REGIONS_KEY, SCENARIO_KEY):
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


def _last_click_key(key: str) -> str:
    return f"_last_click_{key}"


def handle_click_filter(event: dict | None, key: str) -> bool:
    """Toggle a single-value point filter (used for data-table row selection;
    see the module-level note below on why plotly bar charts don't use this).

    Selecting a point sets the filter; selecting it again (an empty
    selection) clears it. Returns True if state changed (caller should
    st.rerun()).

    The "did this change" comparison is against a separate `_last_click_*`
    tracking key, never against `key` itself, mirroring how
    handle_half_click compares against HALF_KEY (no bound widget) while
    writing DATE_KEY (which has one). This is necessary but, empirically,
    not sufficient for st.plotly_chart specifically: even with this
    pattern, a plotly bar chart whose own on_select handler writes back
    into a session_state key that also colors/labels that same chart's
    marks stops forwarding click events to Python after the first rerun --
    reliably reproduced, isolated down to the st.rerun() boundary, but not
    fully root-caused. It does not reproduce for st.dataframe row
    selection, which is why the segment/region bar charts in app.py are
    display-only while the Data & Export / Segments tables' row selection
    still calls this function.
    """
    points = []
    if event is not None:
        event_dict = dict(event)
        points = list((event_dict.get("selection") or {}).get("points", []))
    new_val = None
    if points:
        point = dict(points[0])
        new_val = point.get("customdata")
        if new_val is None:
            new_val = point.get("x")

    last_key = _last_click_key(key)
    st.session_state.setdefault(last_key, None)
    if new_val != st.session_state[last_key]:
        st.session_state[last_key] = new_val
        _set_master(key, [new_val] if new_val else [])
        return True
    return False


def handle_half_click(event: dict | None, halves: pd.DataFrame) -> bool:
    points = []
    if event is not None:
        points = (event.get("selection") or {}).get("points", [])
    new_half = points[0]["x"] if points else None

    if new_half != st.session_state[HALF_KEY]:
        st.session_state[HALF_KEY] = new_half
        if new_half:
            row = halves.loc[halves["half"] == new_half].iloc[0]
            _set_master(DATE_KEY, (row["start"].date(), row["end"].date()))
        return True
    return False


def handle_table_selection(event: dict | None, filtered_df: pd.DataFrame, dim: str, key: str) -> bool:
    """Selecting rows in a data table filters other tiles by the dimension values present.

    See handle_click_filter's docstring for why the comparison is against a
    separate `_last_click_*` key rather than `key` itself.
    """
    rows = []
    if event is not None:
        event_dict = dict(event)
        rows = list((event_dict.get("selection") or {}).get("rows", []))
    values = sorted(filtered_df.iloc[rows][dim].unique().tolist()) if rows else []

    last_key = _last_click_key(key)
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

    return chips
