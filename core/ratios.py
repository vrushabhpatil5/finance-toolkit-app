"""Financial ratio analysis.

Ported from financial-analysis-toolkit/ratio_analysis.py. The original printed a
fixed set of ratios; this version returns a tidy table and skips any ratio whose
inputs are missing rather than raising a KeyError.
"""

import pandas as pd

from .io_utils import require_columns

REQUIRED_COLS = {"Metric", "Value"}

CORE_METRICS = [
    "Revenue",
    "COGS",
    "Net_Income",
    "Current_Assets",
    "Current_Liabilities",
    "Total_Assets",
    "Total_Liabilities",
    "Shareholders_Equity",
]


def to_metric_dict(df: pd.DataFrame) -> dict[str, float]:
    require_columns(df, REQUIRED_COLS, "Financials file")
    values = {}
    for metric, value in zip(df["Metric"], df["Value"]):
        numeric = pd.to_numeric(value, errors="coerce")
        if pd.isna(numeric):
            raise ValueError(f"Value for '{metric}' is not numeric: {value!r}")
        values[str(metric).strip()] = float(numeric)
    return values


def _safe_divide(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def compute_ratios(values: dict[str, float]) -> pd.DataFrame:
    """Return a tidy table: Category, Ratio, Value, Format."""
    get = values.get

    revenue = get("Revenue")
    cogs = get("COGS")
    opex = get("Operating_Expenses")
    net_income = get("Net_Income")
    gross_profit = None if revenue is None or cogs is None else revenue - cogs
    operating_profit = (
        None if gross_profit is None or opex is None else gross_profit - opex
    )

    rows = [
        ("Profitability", "Gross Margin", _safe_divide(gross_profit, revenue), "percent"),
        (
            "Profitability",
            "Operating Margin",
            _safe_divide(operating_profit, revenue),
            "percent",
        ),
        ("Profitability", "Net Profit Margin", _safe_divide(net_income, revenue), "percent"),
        (
            "Profitability",
            "Return on Assets (ROA)",
            _safe_divide(net_income, get("Total_Assets")),
            "percent",
        ),
        (
            "Profitability",
            "Return on Equity (ROE)",
            _safe_divide(net_income, get("Shareholders_Equity")),
            "percent",
        ),
        (
            "Liquidity",
            "Current Ratio",
            _safe_divide(get("Current_Assets"), get("Current_Liabilities")),
            "times",
        ),
        (
            "Liquidity",
            "Working Capital",
            None
            if get("Current_Assets") is None or get("Current_Liabilities") is None
            else get("Current_Assets") - get("Current_Liabilities"),
            "amount",
        ),
        (
            "Leverage",
            "Debt-to-Equity",
            _safe_divide(get("Total_Liabilities"), get("Shareholders_Equity")),
            "times",
        ),
        (
            "Leverage",
            "Debt Ratio",
            _safe_divide(get("Total_Liabilities"), get("Total_Assets")),
            "times",
        ),
        (
            "Leverage",
            "Equity Ratio",
            _safe_divide(get("Shareholders_Equity"), get("Total_Assets")),
            "times",
        ),
        (
            "Efficiency",
            "Asset Turnover",
            _safe_divide(revenue, get("Total_Assets")),
            "times",
        ),
    ]

    table = pd.DataFrame(rows, columns=["Category", "Ratio", "Value", "Format"])
    return table[table["Value"].notna()].reset_index(drop=True)


def format_value(value: float, fmt: str) -> str:
    if fmt == "percent":
        return f"{value:.2%}"
    if fmt == "times":
        return f"{value:.2f}x"
    return f"{value:,.2f}"


def display_table(ratios: pd.DataFrame) -> pd.DataFrame:
    """Human-readable view of the ratio table."""
    out = ratios.copy()
    out["Value"] = [
        format_value(v, f) for v, f in zip(out["Value"], out["Format"])
    ]
    return out[["Category", "Ratio", "Value"]]


def missing_metrics(values: dict[str, float]) -> list[str]:
    return [m for m in CORE_METRICS if m not in values]
