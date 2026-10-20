"""NAV calculation.

Ported from fund-accounting-toolkit/nav_calculation.py, taking dataframes rather
than file paths and adding a currency exposure breakdown.
"""

import pandas as pd

from .io_utils import require_columns

POSITION_COLS = {"Instrument", "Quantity", "Price", "Base_CCY", "FX_to_Base"}
LIABILITY_COLS = {"Liability", "Amount", "Base_CCY"}


def value_positions(positions: pd.DataFrame) -> pd.DataFrame:
    """Add local and base-currency market values to the positions table."""
    require_columns(positions, POSITION_COLS, "Positions file")
    out = positions.copy()

    for col in ("Quantity", "Price", "FX_to_Base"):
        out[col] = pd.to_numeric(out[col], errors="coerce")
    if out[["Quantity", "Price", "FX_to_Base"]].isna().any().any():
        raise ValueError("Quantity, Price and FX_to_Base must all be numeric.")
    if (out["FX_to_Base"] <= 0).any():
        raise ValueError("FX_to_Base must be greater than 0 for every position.")

    out["Market_Value_Local"] = (out["Quantity"] * out["Price"]).round(2)
    out["Market_Value_Base"] = (out["Market_Value_Local"] * out["FX_to_Base"]).round(2)
    return out


def prepare_liabilities(liabilities: pd.DataFrame) -> pd.DataFrame:
    require_columns(liabilities, LIABILITY_COLS, "Liabilities file")
    out = liabilities.copy()
    out["Amount"] = pd.to_numeric(out["Amount"], errors="coerce")
    if out["Amount"].isna().any():
        raise ValueError("Liability Amount must be numeric.")
    return out


def nav_summary(
    valued_positions: pd.DataFrame,
    liabilities: pd.DataFrame,
    units_outstanding: float,
    base_ccy: str = "USD",
) -> pd.DataFrame:
    if units_outstanding <= 0:
        raise ValueError("Units outstanding must be greater than 0.")

    total_assets = float(valued_positions["Market_Value_Base"].sum())
    total_liabilities = float(liabilities["Amount"].sum())
    net_assets = total_assets - total_liabilities

    return pd.DataFrame(
        [
            {
                "Base_CCY": base_ccy,
                "Total_Assets": round(total_assets, 2),
                "Total_Liabilities": round(total_liabilities, 2),
                "Net_Assets": round(net_assets, 2),
                "Units_Outstanding": round(units_outstanding, 6),
                "NAV_Per_Unit": round(net_assets / units_outstanding, 6),
            }
        ]
    )


def currency_exposure(valued_positions: pd.DataFrame) -> pd.DataFrame:
    """Gross asset exposure grouped by the currency each position is held in."""
    grouped = (
        valued_positions.groupby("Base_CCY", as_index=False)["Market_Value_Base"]
        .sum()
        .rename(columns={"Base_CCY": "Currency", "Market_Value_Base": "Value_Base"})
    )
    total = grouped["Value_Base"].sum()
    grouped["Percent_of_Assets"] = (
        (grouped["Value_Base"] / total * 100).round(2) if total else 0.0
    )
    grouped["Value_Base"] = grouped["Value_Base"].round(2)
    return grouped.sort_values("Value_Base", ascending=False).reset_index(drop=True)


def position_weights(valued_positions: pd.DataFrame) -> pd.DataFrame:
    """Each position's share of gross assets, largest first."""
    out = valued_positions[["Instrument", "Base_CCY", "Market_Value_Base"]].copy()
    total = out["Market_Value_Base"].sum()
    out["Percent_of_Assets"] = (
        (out["Market_Value_Base"] / total * 100).round(2) if total else 0.0
    )
    return out.sort_values("Market_Value_Base", ascending=False).reset_index(drop=True)
