"""Unitisation ledger for subscriptions and redemptions.

Ported from fund-accounting-toolkit/unitisation.py. Logic is unchanged; it now
takes a dataframe and returns a per-date NAV table alongside the ledger.
"""

import pandas as pd

from .io_utils import require_columns

TRANSACTION_COLS = {"Date", "Investor", "Type", "Amount_Base"}
VALID_TYPES = {"subscription", "redemption"}


def prepare_transactions(transactions: pd.DataFrame) -> pd.DataFrame:
    require_columns(transactions, TRANSACTION_COLS, "Transactions file")
    out = transactions.copy()

    out["Date"] = pd.to_datetime(out["Date"], errors="coerce")
    if out["Date"].isna().any():
        raise ValueError("Every Date must be a valid date (YYYY-MM-DD).")
    out["Date"] = out["Date"].dt.strftime("%Y-%m-%d")

    out["Amount_Base"] = pd.to_numeric(out["Amount_Base"], errors="coerce")
    if out["Amount_Base"].isna().any():
        raise ValueError("Amount_Base must be numeric.")
    if (out["Amount_Base"] <= 0).any():
        raise ValueError("Amount_Base must be greater than 0. Use Type to set direction.")

    out["Type"] = out["Type"].astype(str).str.strip().str.lower()
    invalid = set(out["Type"]) - VALID_TYPES
    if invalid:
        raise ValueError(
            f"Type must be Subscription or Redemption. Found: {', '.join(sorted(invalid))}"
        )

    out["Investor"] = out["Investor"].astype(str).str.strip()
    return out.sort_values(["Date", "Investor"]).reset_index(drop=True)


def dealing_dates(transactions: pd.DataFrame) -> list[str]:
    return sorted(transactions["Date"].unique().tolist())


def run_unitisation(
    transactions: pd.DataFrame,
    nav_per_unit_by_date: dict[str, float],
    opening_units: float,
    opening_nav_per_unit: float,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return (ledger, investor_summary, totals).

    Subscriptions create units at that date's NAV per unit, redemptions cancel
    them. A redemption larger than the investor's holding is rejected.
    """
    if opening_units < 0:
        raise ValueError("Opening units cannot be negative.")

    investor_units: dict[str, float] = {}
    total_units = float(opening_units)
    rows = []

    for _, record in transactions.iterrows():
        date = record["Date"]
        investor = record["Investor"]
        tx_type = record["Type"]
        amount = float(record["Amount_Base"])

        if date not in nav_per_unit_by_date:
            raise ValueError(f"No NAV per unit supplied for dealing date {date}.")

        navpu = float(nav_per_unit_by_date[date])
        if navpu <= 0:
            raise ValueError(f"NAV per unit must be greater than 0 for {date}.")

        units_delta = amount / navpu
        investor_units.setdefault(investor, 0.0)

        if tx_type == "subscription":
            investor_units[investor] += units_delta
            total_units += units_delta
            signed_units = units_delta
        else:
            if investor_units[investor] + 1e-9 < units_delta:
                raise ValueError(
                    f"Redemption exceeds available units for {investor} on {date}. "
                    f"Holds {investor_units[investor]:.6f}, "
                    f"redeeming {units_delta:.6f}."
                )
            investor_units[investor] -= units_delta
            total_units -= units_delta
            signed_units = -units_delta

        rows.append(
            {
                "Date": date,
                "Investor": investor,
                "Type": tx_type.capitalize(),
                "Amount_Base": round(amount, 2),
                "NAV_Per_Unit": round(navpu, 6),
                "Units_Change": round(signed_units, 6),
                "Investor_Units_After": round(investor_units[investor], 6),
                "Total_Units_After": round(total_units, 6),
            }
        )

    ledger = pd.DataFrame(rows)

    investor_summary = (
        pd.DataFrame(
            [{"Investor": k, "Units": round(v, 6)} for k, v in investor_units.items()]
        )
        .sort_values("Investor")
        .reset_index(drop=True)
    )
    if not investor_summary.empty:
        investor_summary["Percent_of_Units"] = (
            (investor_summary["Units"] / total_units * 100).round(4)
            if total_units
            else 0.0
        )

    totals = pd.DataFrame(
        [
            {
                "Opening_Units": round(opening_units, 6),
                "Opening_NAV_Per_Unit": round(opening_nav_per_unit, 6),
                "Units_Created": round(
                    ledger.loc[ledger["Units_Change"] > 0, "Units_Change"].sum(), 6
                )
                if not ledger.empty
                else 0.0,
                "Units_Cancelled": round(
                    -ledger.loc[ledger["Units_Change"] < 0, "Units_Change"].sum(), 6
                )
                if not ledger.empty
                else 0.0,
                "Closing_Units": round(total_units, 6),
            }
        ]
    )

    return ledger, investor_summary, totals
