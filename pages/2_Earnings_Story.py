"""Pulse — Earnings Story page.

A scrollytelling narrative that walks through five years of synthetic bank
earnings data using a D3 v7 sticky-chart + step-card layout.

All figures are randomly generated and illustrative only.
"""
from __future__ import annotations

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

st.set_page_config(
    page_title="Earnings Story — Pulse",
    page_icon="📜",
    layout="wide",
)

st.markdown(
    '<style>.block-container{padding-top:0.5rem;max-width:1500px;}</style>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- constants --
SEGMENTS = [
    "Retail Banking Services",
    "Business Banking",
    "Institutional Banking & Markets",
    "New Zealand (ASB)",
]


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

    # Serialise: ISO date strings, native Python floats.
    export = monthly_wide.copy()
    export["date"] = export["date"].dt.strftime("%Y-%m-%d")
    for col in ["operating_income", "cash_npat"] + SEGMENTS:
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


# -------------------------------------------------------------------- page --
st.markdown("## The Five-Year Earnings Story")
st.markdown(
    # Fix 19: replace 'demo purposes' with editorial copy that matches the
    # immersive tone; move the synthetic-data caveat to a smaller caption below.
    "Scroll through the sections below to follow a five-year narrative of "
    "synthetic bank earnings — income, credit stress, and the market's verdict."
)

chart_data = {
    "monthly":  _build_monthly_records(),
    "stock":    _build_stock_records(),
    "kpis":     _build_kpis(),
    "segments": SEGMENTS,
}

# Fix 12: pass an explicit height so Streamlit reserves space before JS runs.
st_scrollytelling(chart_data, key="story", height=900)

st.caption("All figures are synthetically generated for illustrative purposes only.")
