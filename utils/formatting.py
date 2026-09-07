"""Consistent number formatting for the dashboard."""
from __future__ import annotations


def fmt_currency(value: float, decimals: int = 1) -> str:
    """Abbreviate A$ values to B/M, e.g. 12345678900 -> 'A$12.3B'."""
    if value is None:
        return "—"
    sign = "-" if value < 0 else ""
    value = abs(value)
    if value >= 1_000_000_000:
        return f"{sign}A${value / 1_000_000_000:.{decimals}f}B"
    if value >= 1_000_000:
        return f"{sign}A${value / 1_000_000:.{decimals}f}M"
    if value >= 1_000:
        return f"{sign}A${value / 1_000:.{decimals}f}K"
    return f"{sign}A${value:.0f}"


def fmt_pct(value: float, decimals: int = 1) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.{decimals}f}%"


def fmt_number(value: float) -> str:
    if value is None:
        return "—"
    return f"{value:,.0f}"


def fmt_delta_pct(current: float, prior: float) -> tuple[str, float | None]:
    """Return (display string, raw pct-change) comparing current vs prior."""
    if prior in (None, 0) or current is None:
        return "n/a vs prior period", None
    change = (current - prior) / abs(prior)
    arrow = "▲" if change >= 0 else "▼"
    return f"{arrow} {abs(change) * 100:.1f}% vs prior period", change


def fmt_delta_pp(current: float, prior: float) -> tuple[str, float | None]:
    """Delta in percentage points, for ratio-type KPIs (NIM, CTI)."""
    if prior is None or current is None:
        return "n/a vs prior period", None
    change_pp = (current - prior) * 100
    arrow = "▲" if change_pp >= 0 else "▼"
    return f"{arrow} {abs(change_pp):.1f}pp vs prior period", change_pp
