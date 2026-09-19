"""Pulse — Earnings Story page.

A scrollytelling narrative that walks through five years of synthetic bank
earnings data using a D3 v7 sticky-chart + step-card layout.

All figures are randomly generated and illustrative only.
"""
from __future__ import annotations

import json
import sys
import pathlib

# Streamlit pages/ subdirectory does not automatically have the project root on
# sys.path, so add it explicitly before any project-relative imports.
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import pandas as pd
import streamlit as st

from components.scrollytelling import st_scrollytelling
from data.generate import (
    PAYOUT_RATIO,
    SHARES_OUTSTANDING,
    generate_dataset,
    generate_stock_data,
)
from data.cba_real import EVENTS, get_annual_list

st.set_page_config(
    page_title="Earnings Story — Pulse",
    page_icon="📜",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """<style>
    /* hide sidebar and toggle */
    [data-testid="stSidebar"],
    [data-testid="collapsedControl"],
    [data-testid="stSidebarNav"],
    button[aria-label="Close sidebar"],
    .stSidebarCollapsedControl { display:none !important; }
    /* hide Streamlit top header bar */
    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    #MainMenu, header { display:none !important; }
    /* full-bleed page */
    .stApp { background:#f8fafc; }
    .block-container {
        padding:0 !important;
        margin:0 !important;
        max-width:100% !important;
    }
    /* hide title and description — component has its own */
    </style>""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- constants --
REAL_KPIS = {
    "cash_npat_m": 10982,
    "npat_growth_pct": 7,
    "nim_pct": 2.05,
    "nim_change_bps": -3,
    "cti_pct": 45.5,
    "cti_change_bps": -20,
    "roe_pct": 14.0,
    "roe_change_bps": 50,
    "cet1_pct": 12.0,
    "cet1_change_bps": -30,
    "eps_cents": 656.9,
    "dps_cents": 505,
    "lie_m": 788,
    "lie_rate_bps": 8,
    "pre_provision_m": 16469,
    "operating_income_m": 30224,
    "div_npat": {"Retail Banking Services": 5587, "Business Banking": 4544,
                 "Institutional Banking and Markets": 1258, "New Zealand (ASB)": 1112},
    "div_nim": {"Retail Banking Services": 2.50, "Business Banking": 3.39,
                "Institutional Banking and Markets": 0.87, "New Zealand (ASB)": 2.30},
    "div_cti": {"Retail Banking Services": 39.3, "Business Banking": 32.2,
                "Institutional Banking and Markets": 40.6, "New Zealand (ASB)": 46.4},
    "div_lie": {"Retail Banking Services": 378, "Business Banking": 310,
                "Institutional Banking and Markets": 33, "New Zealand (ASB)": 66},
}

SEGMENTS = [
    "Retail Banking Services",
    "Business Banking",
    "Institutional Banking and Markets",
    "New Zealand (ASB)",
]

# Mapping from segment name to short key used in nii_*/other_*/opex_*/lie_* columns.
_SEGMENT_SHORT_KEYS: dict[str, str] = {
    "Retail Banking Services":          "retail",
    "Business Banking":                 "business",
    "Institutional Banking and Markets": "ibm",
    "New Zealand (ASB)":                "nz",
}


# ---------------------------------------------------------------- data prep --
@st.cache_data(show_spinner=False)
def _build_monthly_records(seed: int = 42) -> list[dict]:
    """Aggregate the full dataset to monthly (date, segment) grain, then pivot
    to wide format so each segment is a column alongside group totals.

    Returns a JSON-serialisable list of dicts with keys:
        date, operating_income, cash_npat, <one key per segment>
    """
    df = generate_dataset(seed=seed)

    # Filter to Actual scenario first — halves the data before groupby.
    actual_df = df[df["scenario"] == "Actual"]

    # Aggregate departments + regions back to (date, segment) grain.
    monthly_seg: pd.DataFrame = (
        actual_df
        .groupby(["date", "segment"], observed=True)[["operating_income", "cash_npat"]]
        .sum()
        .reset_index()
    )

    # Group-level total per month.
    monthly_total: pd.DataFrame = (
        monthly_seg
        .groupby("date", observed=True)[["operating_income", "cash_npat"]]
        .sum()
        .reset_index()
    )

    # Wide pivot: one column per segment.
    seg_pivot: pd.DataFrame = (
        monthly_seg
        .pivot(index="date", columns="segment", values="operating_income")
        .reset_index()
    )
    seg_pivot.columns.name = None  # drop the "segment" name from column MultiIndex

    # Merge totals with segment columns.
    monthly_wide: pd.DataFrame = (
        monthly_total
        .merge(seg_pivot, on="date", how="left")
        .sort_values("date")
        .reset_index(drop=True)
    )

    # ------ per-segment revenue / costs / LIE --------------------------------
    # Second groupby at (date, segment) grain to pick up the three extra cols.
    monthly_seg_detail: pd.DataFrame = (
        actual_df
        .groupby(["date", "segment"], observed=True)[
            ["net_interest_income", "other_operating_income",
             "operating_expenses", "loan_impairment_expense"]
        ]
        .sum()
        .reset_index()
    )
    # Emit three separate columns so JS can build the two-layer NII / other-income
    # stacked anatomy and the opex band independently.
    # nii   -> net interest income (bottom layer)
    # other -> other operating income (stacked on top of NII)
    # opex  -> operating expenses (cost band; JS reads opex_<key>)
    # lie   -> loan impairment expense (retained for future chart use)
    monthly_seg_detail["nii"]   = monthly_seg_detail["net_interest_income"]
    monthly_seg_detail["other"] = monthly_seg_detail["other_operating_income"]
    monthly_seg_detail["opex"]  = monthly_seg_detail["operating_expenses"]
    monthly_seg_detail["lie"]   = monthly_seg_detail["loan_impairment_expense"]

    # Pivot nii, other, opex, lie to wide format keyed by shortKey.
    for metric in ("nii", "other", "opex", "lie"):
        metric_pivot = (
            monthly_seg_detail
            .pivot(index="date", columns="segment", values=metric)
            .reset_index()
        )
        metric_pivot.columns.name = None
        # Rename segment columns to shortKey-prefixed names.
        rename_map = {
            seg: f"{metric}_{short}"
            for seg, short in _SEGMENT_SHORT_KEYS.items()
            if seg in metric_pivot.columns
        }
        metric_pivot = metric_pivot.rename(columns=rename_map)
        # Drop any columns that were not in the shortKey map (safety).
        keep_cols = ["date"] + list(rename_map.values())
        metric_pivot = metric_pivot[[c for c in keep_cols if c in metric_pivot.columns]]
        monthly_wide = monthly_wide.merge(metric_pivot, on="date", how="left")
    # -------------------------------------------------------------------------

    # Serialise: ISO date strings, native Python floats.
    export = monthly_wide.copy()
    export["date"] = export["date"].dt.strftime("%Y-%m-%d")
    detail_cols = [
        f"{metric}_{short}"
        for metric in ("nii", "other", "opex", "lie")
        for short in _SEGMENT_SHORT_KEYS.values()
    ]
    for col in ["operating_income", "cash_npat"] + SEGMENTS + detail_cols:
        if col in export.columns:
            export[col] = export[col].fillna(0.0).astype(float)

    return export.to_dict("records")


@st.cache_data(show_spinner=False)
def _build_stock_records(seed: int = 42) -> list[dict]:
    """Resample daily stock prices to weekly (Friday close), return raw A$ closes.

    The JS will show raw share price values on the Y axis.
    """
    stock_df = generate_stock_data(seed=seed)
    weekly: pd.DataFrame = (
        stock_df
        .set_index("date")["close"]
        .resample("W-FRI")
        .last()
        .dropna()
        .reset_index()
        .rename(columns={"close": "value"})
    )
    records = [
        {"date": row["date"].strftime("%Y-%m-%d"), "value": float(row["value"])}
        for _, row in weekly.iterrows()
    ]
    return records


@st.cache_data(show_spinner=False)
def _build_kpis(seed: int = 42) -> dict:
    """Compute KPI metrics from the full dataset and stock series.

    Returns a dict with keys:
        share_price, pe_ratio, div_yield, eps,
        annual_income_b, annual_npat_b,
        income_growth_pct, price_growth_pct
    """
    df = generate_dataset(seed=seed)
    stock_df = generate_stock_data(seed=seed)

    actual_df = df[df["scenario"] == "Actual"]

    # Share price metrics
    latest_close = float(stock_df["close"].iloc[-1])
    first_close  = float(stock_df["close"].iloc[0])
    price_growth_pct = (latest_close - first_close) / first_close * 100

    # Trailing 12 months of actual earnings
    max_date = actual_df["date"].max()
    trailing_12m = actual_df[actual_df["date"] >= max_date - pd.DateOffset(months=11)]
    annual_income = float(trailing_12m["operating_income"].sum())
    annual_npat   = float(trailing_12m["cash_npat"].sum())

    # First 12 months for income growth comparison
    min_date = actual_df["date"].min()
    first_12m = actual_df[actual_df["date"] <= min_date + pd.DateOffset(months=11)]
    first_income = float(first_12m["operating_income"].sum())
    income_growth_pct = (
        (annual_income - first_income) / first_income * 100
        if first_income > 0 else 0.0
    )

    # Valuation ratios
    eps = annual_npat / SHARES_OUTSTANDING
    pe_ratio  = round(latest_close / eps, 1) if eps > 0 else 0.0
    div_yield = round((eps * PAYOUT_RATIO / latest_close) * 100, 2) if latest_close > 0 else 0.0

    return {
        "share_price":       round(latest_close, 2),
        "pe_ratio":          pe_ratio,
        "div_yield":         div_yield,
        "eps":               round(eps, 6),
        "annual_income_b":   round(annual_income / 1e9, 2),
        "annual_npat_b":     round(annual_npat   / 1e9, 2),
        "income_growth_pct": round(income_growth_pct, 1),
        "price_growth_pct":  round(price_growth_pct, 1),
    }


@st.cache_data(show_spinner=False)
def _load_commentary() -> dict:
    """Load AI commentary from data/commentary.json if it exists, else return {}."""
    commentary_path = pathlib.Path(__file__).parent.parent / "data" / "commentary.json"
    if commentary_path.exists():
        try:
            return json.loads(commentary_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


# -------------------------------------------------------------------- page --
chart_data = {
    "monthly":    _build_monthly_records(),
    "stock":      _build_stock_records(),
    "kpis":       _build_kpis(),
    "real_kpis":  REAL_KPIS,
    "segments":   SEGMENTS,
    "commentary": _load_commentary(),
    "annual":     get_annual_list(),
    "events":     EVENTS,
}

# JS uses window.innerHeight for actual sizing; this large value avoids clipping.
st_scrollytelling(chart_data, key="story", height=5000)

st.caption("Illustrative scenario data grounded in CBA FY26 Profit Announcement (12 August 2026). All chart data is synthetic.")
