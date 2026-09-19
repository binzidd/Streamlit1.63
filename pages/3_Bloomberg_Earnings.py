"""Bloomberg Red Meat editorial page — CBA FY26 Earnings.

Two-column scrollytelling: left 45% text sections (8 × 100vh), right 55%
chart panel repositioned via window.scroll.

All figures grounded in CBA FY26 Profit Announcement (12 August 2026).
Chart data is synthetic/illustrative.
"""
from __future__ import annotations

import json
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import pandas as pd
import streamlit as st

from components.bloomberg_editorial import st_bloomberg_editorial
from data.generate import (
    PAYOUT_RATIO,
    SHARES_OUTSTANDING,
    generate_dataset,
    generate_stock_data,
)

st.set_page_config(
    page_title="Bloomberg Earnings — CBA FY26",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---- Hide all Streamlit chrome (same pattern as 2_Earnings_Story.py)
st.markdown(
    """<style>
    [data-testid="stSidebar"],
    [data-testid="collapsedControl"],
    [data-testid="stSidebarNav"],
    button[aria-label="Close sidebar"],
    .stSidebarCollapsedControl { display:none !important; }
    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    #MainMenu, header { display:none !important; }
    .stApp { background:#1e3a5f; }
    .block-container {
        padding:0 !important;
        margin:0 !important;
        max-width:100% !important;
    }
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
    "div_npat": {
        "Retail Banking Services": 5587,
        "Business Banking": 4544,
        "Institutional Banking and Markets": 1258,
        "New Zealand (ASB)": 1112,
    },
    "div_nim": {
        "Retail Banking Services": 2.50,
        "Business Banking": 3.39,
        "Institutional Banking and Markets": 0.87,
        "New Zealand (ASB)": 2.30,
    },
    "div_cti": {
        "Retail Banking Services": 39.3,
        "Business Banking": 32.2,
        "Institutional Banking and Markets": 40.6,
        "New Zealand (ASB)": 46.4,
    },
    "div_lie": {
        "Retail Banking Services": 378,
        "Business Banking": 310,
        "Institutional Banking and Markets": 33,
        "New Zealand (ASB)": 66,
    },
}

SEGMENTS = [
    "Retail Banking Services",
    "Business Banking",
    "Institutional Banking and Markets",
    "New Zealand (ASB)",
]

_SEGMENT_SHORT_KEYS: dict[str, str] = {
    "Retail Banking Services":           "retail",
    "Business Banking":                  "business",
    "Institutional Banking and Markets": "ibm",
    "New Zealand (ASB)":                 "nz",
}


# ---------------------------------------------------------------- data prep --
@st.cache_data(show_spinner=False)
def _build_monthly_records(seed: int = 42) -> list[dict]:
    """Aggregate dataset to monthly wide format with per-segment columns.

    Returns a JSON-serialisable list of dicts with keys:
        date, operating_income, cash_npat, <one key per segment>,
        nii_<short>, other_<short>, opex_<short>, lie_<short> for each segment.
    """
    df = generate_dataset(seed=seed)
    actual_df = df[df["scenario"] == "Actual"]

    monthly_seg: pd.DataFrame = (
        actual_df
        .groupby(["date", "segment"], observed=True)[["operating_income", "cash_npat"]]
        .sum()
        .reset_index()
    )

    monthly_total: pd.DataFrame = (
        monthly_seg
        .groupby("date", observed=True)[["operating_income", "cash_npat"]]
        .sum()
        .reset_index()
    )

    seg_pivot: pd.DataFrame = (
        monthly_seg
        .pivot(index="date", columns="segment", values="operating_income")
        .reset_index()
    )
    seg_pivot.columns.name = None

    monthly_wide: pd.DataFrame = (
        monthly_total
        .merge(seg_pivot, on="date", how="left")
        .sort_values("date")
        .reset_index(drop=True)
    )

    monthly_seg_detail: pd.DataFrame = (
        actual_df
        .groupby(["date", "segment"], observed=True)[
            ["net_interest_income", "other_operating_income",
             "operating_expenses", "loan_impairment_expense"]
        ]
        .sum()
        .reset_index()
    )
    monthly_seg_detail["nii"]   = monthly_seg_detail["net_interest_income"]
    monthly_seg_detail["other"] = monthly_seg_detail["other_operating_income"]
    monthly_seg_detail["opex"]  = monthly_seg_detail["operating_expenses"]
    monthly_seg_detail["lie"]   = monthly_seg_detail["loan_impairment_expense"]

    for metric in ("nii", "other", "opex", "lie"):
        metric_pivot = (
            monthly_seg_detail
            .pivot(index="date", columns="segment", values=metric)
            .reset_index()
        )
        metric_pivot.columns.name = None
        rename_map = {
            seg: f"{metric}_{short}"
            for seg, short in _SEGMENT_SHORT_KEYS.items()
            if seg in metric_pivot.columns
        }
        metric_pivot = metric_pivot.rename(columns=rename_map)
        keep_cols = ["date"] + list(rename_map.values())
        metric_pivot = metric_pivot[[c for c in keep_cols if c in metric_pivot.columns]]
        monthly_wide = monthly_wide.merge(metric_pivot, on="date", how="left")

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
    """Weekly (Friday close) share price records."""
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
    return [
        {"date": row["date"].strftime("%Y-%m-%d"), "value": float(row["value"])}
        for _, row in weekly.iterrows()
    ]


@st.cache_data(show_spinner=False)
def _build_kpis(seed: int = 42) -> dict:
    """Computed KPI metrics from dataset and stock series."""
    df = generate_dataset(seed=seed)
    stock_df = generate_stock_data(seed=seed)

    actual_df = df[df["scenario"] == "Actual"]

    latest_close = float(stock_df["close"].iloc[-1])
    first_close  = float(stock_df["close"].iloc[0])
    price_growth_pct = (latest_close - first_close) / first_close * 100

    max_date = actual_df["date"].max()
    trailing_12m = actual_df[actual_df["date"] >= max_date - pd.DateOffset(months=11)]
    annual_income = float(trailing_12m["operating_income"].sum())
    annual_npat   = float(trailing_12m["cash_npat"].sum())

    min_date = actual_df["date"].min()
    first_12m = actual_df[actual_df["date"] <= min_date + pd.DateOffset(months=11)]
    first_income = float(first_12m["operating_income"].sum())
    income_growth_pct = (
        (annual_income - first_income) / first_income * 100
        if first_income > 0 else 0.0
    )

    eps = annual_npat / SHARES_OUTSTANDING
    pe_ratio  = round(latest_close / eps, 1) if eps > 0 else 0.0
    div_yield = round((eps * PAYOUT_RATIO / latest_close) * 100, 2) if latest_close > 0 else 0.0

    return {
        "share_price":       round(latest_close, 2),
        "pe_ratio":          pe_ratio,
        "div_yield":         div_yield,
        "eps":               round(eps, 6),
        "annual_income_b":   round(annual_income / 1e9, 2),
        "annual_npat_b":     round(annual_npat / 1e9, 2),
        "income_growth_pct": round(income_growth_pct, 1),
        "price_growth_pct":  round(price_growth_pct, 1),
    }


# ---- Load commentary from JSON
@st.cache_data(show_spinner=False)
def _load_commentary() -> dict:
    commentary_path = pathlib.Path(__file__).parent.parent / "data" / "commentary.json"
    try:
        with open(commentary_path, "r") as f:
            return json.load(f)
    except Exception:
        return {}


# -------------------------------------------------------------------- page --
chart_data = {
    "monthly":    _build_monthly_records(),
    "stock":      _build_stock_records(),
    "kpis":       _build_kpis(),
    "real_kpis":  REAL_KPIS,
    "segments":   SEGMENTS,
    "commentary": _load_commentary(),
}

# 8 chapters × ~100vh each + buffer
st_bloomberg_editorial(chart_data, key="bloomberg", height=9000)

st.caption(
    "Illustrative scenario data grounded in CBA FY26 Profit Announcement (12 August 2026). "
    "All chart data is synthetic."
)
