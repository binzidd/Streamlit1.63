"""Tile chrome: a consistent bordered card + icon/title header for every
chart, replacing per-chart Plotly titles (which fight the tile's own visual
rhythm once every chart lives in its own bordered container)."""
from __future__ import annotations

from contextlib import contextmanager

import streamlit as st


@contextmanager
def tile(title: str, icon: str = "", caption: str | None = None):
    with st.container(border=True):
        st.markdown(
            f'<div class="pulse-tile-title"><span class="pulse-tile-icon">{icon}</span>{title}</div>',
            unsafe_allow_html=True,
        )
        if caption:
            st.caption(caption)
        yield
