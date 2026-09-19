"""CBA five-year Profit Announcement data.

Values are sourced from:
  - FY26: CBA Profit Announcement, 12 Aug 2026 (on-disk PDF)
  - FY25: CBA H1/H2 FY25 Profit Announcements (published)
  - FY22-FY24: CBA published annual Profit Announcements

All monetary values in AUD millions unless noted.
"""

YEARS = ["FY22", "FY23", "FY24", "FY25", "FY26"]

# ---- Main annual data keyed by year ----------------------------------------
ANNUAL = {
    "FY22": {
        "npat_m":      9672,   # Cash NPAT
        "oi_m":        22743,  # Operating income (NII + other income)
        "nii_m":       18485,  # Net interest income
        "opex_m":      10651,  # Operating expenses
        "pre_prov_m":  12092,  # Pre-provision profit (PPOP)
        "lie_m":       1095,   # Loan impairment expense
        "nim_pct":     1.90,   # Net interest margin
        "cti_pct":     46.8,   # Cost-to-income ratio
        "roe_pct":     13.4,   # Return on equity
        "cet1_pct":    11.5,   # CET1 capital ratio (APRA)
        "eps_cents":   568,    # Cash EPS (cents)
        "dps_cents":   385,    # Dividends per share (cents)
    },
    "FY23": {
        "npat_m":      10164,
        "oi_m":        26533,
        "nii_m":       22175,
        "opex_m":      11489,
        "pre_prov_m":  15044,
        "lie_m":       1415,
        "nim_pct":     2.10,
        "cti_pct":     43.3,
        "roe_pct":     14.4,
        "cet1_pct":    12.2,
        "eps_cents":   601,
        "dps_cents":   420,
    },
    "FY24": {
        "npat_m":      9836,
        "oi_m":        27185,
        "nii_m":       22889,
        "opex_m":      12070,
        "pre_prov_m":  15115,
        "lie_m":       1306,
        "nim_pct":     2.07,
        "cti_pct":     44.4,
        "roe_pct":     14.0,
        "cet1_pct":    12.3,
        "eps_cents":   589,
        "dps_cents":   465,
    },
    "FY25": {
        "npat_m":      10262,
        "oi_m":        28794,
        "nii_m":       24446,
        "opex_m":      13159,
        "pre_prov_m":  15635,
        "lie_m":       1170,
        "nim_pct":     2.08,
        "cti_pct":     45.7,
        "roe_pct":     13.5,
        "cet1_pct":    12.3,
        "eps_cents":   612,
        "dps_cents":   470,
    },
    "FY26": {
        "npat_m":      10982,
        "oi_m":        30224,
        "nii_m":       25580,
        "opex_m":      13755,
        "pre_prov_m":  16469,
        "lie_m":       788,
        "nim_pct":     2.05,
        "cti_pct":     45.5,
        "roe_pct":     14.0,
        "cet1_pct":    12.0,
        "eps_cents":   657,
        "dps_cents":   505,
    },
}

# ---- Major market events for chart annotations -----------------------------
EVENTS = [
    {
        "type":       "region",
        "date_start": "2020-01-01",
        "date_end":   "2022-05-01",
        "label":      "COVID-19 era",
        "color":      "rgba(59,130,246,0.06)",
    },
    {
        "type":  "vline",
        "date":  "2022-02-24",
        "label": "Russia-Ukraine war",
        "color": "#f59e0b",  # amber
    },
    {
        "type":  "vline",
        "date":  "2022-05-01",
        "label": "RBA hikes begin",
        "color": "#1e3a5f",
    },
    {
        "type":  "vline",
        "date":  "2023-03-10",
        "label": "SVB collapse",
        "color": "#7c3aed",  # purple
    },
    {
        "type":  "vline",
        "date":  "2023-11-01",
        "label": "Peak 4.35%",
        "color": "#ef4444",  # red
    },
    {
        "type":  "vline",
        "date":  "2025-02-01",
        "label": "RBA ↓ easing",
        "color": "#16a34a",  # green
    },
]


def get_sparkline(metric: str) -> list[float]:
    """Return 5-year series for a given metric key, ordered FY22→FY26."""
    return [ANNUAL[y][metric] for y in YEARS]


def get_annual_list() -> list[dict]:
    """Return list of per-year dicts for JSON serialisation (JS consumes this)."""
    return [{"year": y, **ANNUAL[y]} for y in YEARS]
