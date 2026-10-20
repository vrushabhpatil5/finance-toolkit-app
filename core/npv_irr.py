"""NPV and IRR calculations.

Ported from financial-analysis-toolkit/npv_irr_calculator.py, refactored so the
maths is separated from input/output.
"""

import numpy as np
import numpy_financial as npf
import pandas as pd

from .io_utils import require_columns

REQUIRED_COLS = {"Year", "CashFlow"}


def prepare_cashflows(df: pd.DataFrame) -> pd.DataFrame:
    require_columns(df, REQUIRED_COLS, "Cash flow file")
    out = df.copy()
    out["Year"] = pd.to_numeric(out["Year"], errors="coerce")
    out["CashFlow"] = pd.to_numeric(out["CashFlow"], errors="coerce")
    if out[["Year", "CashFlow"]].isna().any().any():
        raise ValueError("Year and CashFlow must both be numeric.")
    return out.sort_values("Year").reset_index(drop=True)


def npv(cashflows: np.ndarray, discount_rate: float) -> float:
    """Period 0 is undiscounted, matching numpy-financial convention."""
    return float(npf.npv(discount_rate, cashflows))


def irr(cashflows: np.ndarray) -> float | None:
    """Return IRR as a decimal, or None when no sign change makes it solvable."""
    values = np.asarray(cashflows, dtype=float)
    if not (values.min() < 0 < values.max()):
        return None
    result = npf.irr(values)
    if result is None or np.isnan(result):
        return None
    return float(result)


def payback_period(cashflows: np.ndarray) -> float | None:
    """Undiscounted payback in periods, interpolated within the crossing period."""
    cumulative = np.cumsum(np.asarray(cashflows, dtype=float))
    if cumulative[-1] < 0:
        return None
    for i, total in enumerate(cumulative):
        if total >= 0:
            if i == 0:
                return 0.0
            previous = cumulative[i - 1]
            step = total - previous
            if step == 0:
                return float(i)
            return float(i - 1 + (-previous / step))
    return None


def summarise(df: pd.DataFrame, discount_rate: float) -> pd.DataFrame:
    """One-row summary table of the headline metrics."""
    values = df["CashFlow"].to_numpy(dtype=float)
    computed_irr = irr(values)
    payback = payback_period(values)

    return pd.DataFrame(
        [
            {
                "Discount_Rate_Percent": round(discount_rate * 100, 4),
                "NPV": round(npv(values, discount_rate), 2),
                "IRR_Percent": round(computed_irr * 100, 4)
                if computed_irr is not None
                else None,
                "Payback_Periods": round(payback, 2) if payback is not None else None,
                "Total_Undiscounted": round(float(values.sum()), 2),
            }
        ]
    )


def npv_profile(
    df: pd.DataFrame, low: float = 0.0, high: float = 0.30, steps: int = 61
) -> pd.DataFrame:
    """NPV across a range of discount rates, for the NPV profile chart."""
    values = df["CashFlow"].to_numpy(dtype=float)
    rates = np.linspace(low, high, steps)
    return pd.DataFrame(
        {
            "Discount_Rate_Percent": [round(r * 100, 4) for r in rates],
            "NPV": [npv(values, r) for r in rates],
        }
    )
