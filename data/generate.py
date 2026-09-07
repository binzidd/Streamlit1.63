"""Synthetic bank-earnings dataset for the Pulse finance dashboard.

All figures here are illustrative and randomly generated for the purpose of
demonstrating Streamlit 1.63 features. They are NOT the real reported
financial results of any institution.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

START = pd.Timestamp("2022-01-01")
END = pd.Timestamp("2026-06-01")  # latest closed month = end of FY26 (Jun-2026)

SEGMENTS = {
    "Retail Banking Services": {
        "regions": ["NSW/ACT", "VIC/TAS", "QLD", "WA", "SA/NT"],
        "income_share": 0.45,
        "nim": 0.021,
        "cti": 0.44,
        "impair_rate": 0.0012,
    },
    "Business Banking": {
        "regions": ["NSW/ACT", "VIC/TAS", "QLD", "WA", "SA/NT"],
        "income_share": 0.24,
        "nim": 0.023,
        "cti": 0.38,
        "impair_rate": 0.0018,
    },
    "Institutional Banking & Markets": {
        "regions": ["NSW/ACT", "VIC/TAS", "QLD", "WA", "SA/NT"],
        "income_share": 0.18,
        "nim": 0.016,
        "cti": 0.42,
        "impair_rate": 0.0008,
    },
    "New Zealand (ASB)": {
        "regions": ["New Zealand"],
        "income_share": 0.13,
        "nim": 0.022,
        "cti": 0.40,
        "impair_rate": 0.0014,
    },
}

SCENARIOS = ["Actual", "Budget"]

ANNUAL_GROUP_OPERATING_INCOME = 27_000_000_000  # A$ illustrative
TAX_RATE = 0.30


def _seasonal(month: int) -> float:
    # mild seasonality: stronger in Mar/Jun (quarter-end), softer in Jan
    return 1.0 + 0.06 * np.sin((month - 3) / 12 * 2 * np.pi)


def _fy_half(date: pd.Timestamp) -> tuple[str, str, str]:
    """CBA-style fiscal year (Jul-Jun). Returns (fy_label, half_label, half_key)."""
    if date.month >= 7:
        fy = date.year + 1
        half = "1H"
    else:
        fy = date.year
        half = "2H"
    fy_label = f"FY{str(fy)[-2:]}"
    half_label = f"{half}{str(fy)[-2:]}"
    half_key = f"{fy}-{half}"
    return fy_label, half_label, half_key


@st.cache_data(show_spinner=False)
def generate_dataset(seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range(START, END, freq="MS")
    n_months = len(dates)
    year_index = np.array([(d.year - START.year) + (d.month - 1) / 12 for d in dates])
    growth = 1 + 0.045 * year_index  # ~4.5%/yr trend growth

    # a deliberate "story" moment: EMEA-style regional wobble ->
    # here, a soft patch in Business Banking impairments during 2023
    shock_mask = (dates >= "2023-04-01") & (dates <= "2023-09-01")

    rows = []
    for seg_name, cfg in SEGMENTS.items():
        seg_annual_income = ANNUAL_GROUP_OPERATING_INCOME * cfg["income_share"]
        base_monthly_income = seg_annual_income / 12
        n_regions = len(cfg["regions"])

        for region in cfg["regions"]:
            region_weight = 1 / n_regions
            for scenario in SCENARIOS:
                is_budget = scenario == "Budget"
                for i, date in enumerate(dates):
                    seasonal = _seasonal(date.month)
                    noise = rng.normal(1.0, 0.015 if is_budget else 0.045)
                    if is_budget:
                        # budget set flat off trend growth, no seasonality surprises
                        income = base_monthly_income * (1 + 0.04 * year_index[i]) * region_weight * noise
                    else:
                        income = base_monthly_income * growth[i] * seasonal * region_weight * noise

                    cti = cfg["cti"] * rng.normal(1.0, 0.03)
                    opex = income * cti

                    impair_rate = cfg["impair_rate"]
                    if shock_mask[i] and seg_name == "Business Banking":
                        impair_rate *= 2.4
                    gross_loans = (income / cfg["nim"]) * rng.normal(1.0, 0.02)
                    loan_impairment = gross_loans * impair_rate / 12

                    pre_tax = income - opex - loan_impairment
                    cash_npat = pre_tax * (1 - TAX_RATE)
                    notable_items = cash_npat * rng.normal(0, 0.02)
                    statutory_npat = cash_npat + notable_items

                    avg_interest_earning_assets = gross_loans * rng.normal(1.05, 0.01)
                    net_interest_income = avg_interest_earning_assets * cfg["nim"] / 12 * rng.normal(1.0, 0.02)
                    other_income = max(income - net_interest_income, 0)

                    deposits = gross_loans * rng.normal(0.78, 0.03)
                    equity = gross_loans * 0.09 * rng.normal(1.0, 0.02)

                    new_customers = int(max(rng.normal(4200 * region_weight * (1 + 0.02 * year_index[i]), 300), 0))
                    churned_customers = int(max(rng.normal(3100 * region_weight, 250), 0))

                    fy_label, half_label, half_key = _fy_half(date)

                    rows.append(
                        {
                            "date": date,
                            "fy": fy_label,
                            "half": half_label,
                            "half_key": half_key,
                            "segment": seg_name,
                            "region": region,
                            "scenario": scenario,
                            "operating_income": income,
                            "operating_expenses": opex,
                            "loan_impairment_expense": loan_impairment,
                            "net_interest_income": net_interest_income,
                            "other_operating_income": other_income,
                            "cash_npat": cash_npat,
                            "statutory_npat": statutory_npat,
                            "avg_interest_earning_assets": avg_interest_earning_assets,
                            "gross_loans": gross_loans,
                            "deposits": deposits,
                            "equity": equity,
                            "new_customers": new_customers,
                            "churned_customers": churned_customers,
                        }
                    )

    df = pd.DataFrame(rows)
    df["net_new_customers"] = df["new_customers"] - df["churned_customers"]
    return df


@st.cache_data(show_spinner=False)
def get_halves(df: pd.DataFrame) -> pd.DataFrame:
    """Ordered, deduplicated half-year reference table with start/end dates."""
    halves = (
        df.groupby("half_key")
        .agg(half=("half", "first"), start=("date", "min"), end=("date", "max"))
        .reset_index()
        .sort_values("half_key")
        .reset_index(drop=True)
    )
    return halves
