"""DCF valuation and WACC x terminal growth sensitivity.

Ported from financial-analysis-toolkit/dcf_sensitivity_wacc_growth.py. The fixed
ranges and the matplotlib chart are replaced by parameters and tidy dataframes.
"""

import numpy as np
import pandas as pd

from .io_utils import require_columns

REQUIRED_COLS = {"Year", "FCF"}


def prepare_fcf(df: pd.DataFrame) -> pd.DataFrame:
    require_columns(df, REQUIRED_COLS, "Forecast cash flow file")
    out = df.copy()
    out["Year"] = pd.to_numeric(out["Year"], errors="coerce")
    out["FCF"] = pd.to_numeric(out["FCF"], errors="coerce")
    if out[["Year", "FCF"]].isna().any().any():
        raise ValueError("Year and FCF must both be numeric.")
    return out.sort_values("Year").reset_index(drop=True)


def enterprise_value(fcfs: np.ndarray, wacc: float, growth: float) -> float:
    """PV of forecast FCFs plus PV of a perpetuity-growth terminal value.

    Returns NaN when WACC <= growth, where the perpetuity formula breaks down.
    """
    values = np.asarray(fcfs, dtype=float)
    n = len(values)
    if n == 0:
        return float("nan")
    if wacc <= growth:
        return float("nan")

    periods = np.arange(1, n + 1)
    pv_explicit = float(np.sum(values / (1 + wacc) ** periods))

    terminal_value = values[-1] * (1 + growth) / (wacc - growth)
    pv_terminal = terminal_value / (1 + wacc) ** n

    return pv_explicit + pv_terminal


def valuation_breakdown(
    fcfs: np.ndarray, wacc: float, growth: float
) -> pd.DataFrame:
    """Split the headline value into explicit-period PV and terminal PV."""
    values = np.asarray(fcfs, dtype=float)
    n = len(values)
    periods = np.arange(1, n + 1)
    pv_explicit = float(np.sum(values / (1 + wacc) ** periods))

    if wacc <= growth:
        pv_terminal = float("nan")
    else:
        terminal_value = values[-1] * (1 + growth) / (wacc - growth)
        pv_terminal = terminal_value / (1 + wacc) ** n

    total = pv_explicit + pv_terminal

    return pd.DataFrame(
        [
            {
                "WACC_Percent": round(wacc * 100, 4),
                "Terminal_Growth_Percent": round(growth * 100, 4),
                "PV_Explicit_FCF": round(pv_explicit, 2),
                "PV_Terminal_Value": round(pv_terminal, 2)
                if not np.isnan(pv_terminal)
                else None,
                "Enterprise_Value": round(total, 2) if not np.isnan(total) else None,
                "Terminal_Share_Percent": round(pv_terminal / total * 100, 2)
                if not np.isnan(total) and total != 0
                else None,
            }
        ]
    )


def discounted_schedule(fcfs: np.ndarray, wacc: float) -> pd.DataFrame:
    """Year-by-year discount factors and present values."""
    values = np.asarray(fcfs, dtype=float)
    periods = np.arange(1, len(values) + 1)
    factors = 1 / (1 + wacc) ** periods
    return pd.DataFrame(
        {
            "Year": periods,
            "FCF": np.round(values, 2),
            "Discount_Factor": np.round(factors, 6),
            "PV_of_FCF": np.round(values * factors, 2),
        }
    )


def sensitivity_grid(
    fcfs: np.ndarray,
    wacc_values: np.ndarray,
    growth_values: np.ndarray,
) -> pd.DataFrame:
    """Enterprise value for each WACC (rows) x terminal growth (columns) pair."""
    grid = pd.DataFrame(
        index=[f"{w * 100:.2f}%" for w in wacc_values],
        columns=[f"{g * 100:.2f}%" for g in growth_values],
        dtype=float,
    )
    for wacc in wacc_values:
        for growth in growth_values:
            grid.loc[f"{wacc * 100:.2f}%", f"{growth * 100:.2f}%"] = enterprise_value(
                fcfs, wacc, growth
            )
    grid.index.name = "WACC"
    grid.columns.name = "Terminal growth"
    return grid.round(2)


def value_vs_wacc(
    fcfs: np.ndarray, wacc_values: np.ndarray, growth: float
) -> pd.DataFrame:
    """Valuation curve across WACC at a fixed terminal growth rate."""
    return pd.DataFrame(
        {
            "WACC_Percent": [round(w * 100, 4) for w in wacc_values],
            "Enterprise_Value": [enterprise_value(fcfs, w, growth) for w in wacc_values],
        }
    )


def build_range(start: float, stop: float, step: float) -> np.ndarray:
    """Inclusive range in decimal terms, guarded against a zero or negative step."""
    if step <= 0:
        raise ValueError("Step must be greater than 0.")
    if stop < start:
        start, stop = stop, start
    count = int(round((stop - start) / step)) + 1
    return np.round(start + step * np.arange(count), 10)
