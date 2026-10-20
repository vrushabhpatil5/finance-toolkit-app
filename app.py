"""Finance Toolkit - Streamlit app.

Merges two command line projects into one web app:
  - financial-analysis-toolkit (NPV/IRR, ratio analysis, DCF sensitivity)
  - fund-accounting-toolkit (NAV calculation, unitisation)

Run locally with:  streamlit run app.py
"""

import numpy as np
import pandas as pd
import streamlit as st

from core import dcf, nav, npv_irr, ratios, unitisation
from core.io_utils import load_csv, to_csv_bytes

st.set_page_config(
    page_title="Finance Toolkit",
    page_icon="📊",
    layout="wide",
)

TOOLS = {
    "Home": "home",
    "NPV & IRR": "npv_irr",
    "Ratio Analysis": "ratios",
    "DCF Sensitivity": "dcf",
    "NAV Calculation": "nav",
    "Unitisation": "unitisation",
}


def sidebar_source(label: str, sample_name: str, key: str):
    """Upload widget plus the bundled sample fallback."""
    uploaded = st.sidebar.file_uploader(label, type="csv", key=key)
    try:
        df, source = load_csv(uploaded, sample_name)
    except Exception as error:  # noqa: BLE001 - surfaced to the user
        st.error(f"Could not read {label.lower()}: {error}")
        st.stop()
    st.sidebar.caption(f"Using {source}")
    return df


def download(label: str, df: pd.DataFrame, filename: str, index: bool = False):
    st.download_button(
        label,
        data=to_csv_bytes(df, index=index),
        file_name=filename,
        mime="text/csv",
    )


# ----------------------------------------------------------------------------
# Home
# ----------------------------------------------------------------------------
def page_home():
    st.title("Finance Toolkit")
    st.write(
        "Corporate finance analysis and fund accounting calculations in one place. "
        "Pick a tool from the sidebar. Each one runs on bundled sample data by "
        "default, and you can upload your own CSV to replace it."
    )

    left, right = st.columns(2)

    with left:
        st.subheader("Corporate finance")
        st.markdown(
            "- **NPV & IRR** - net present value, internal rate of return, "
            "payback period and an NPV profile curve\n"
            "- **Ratio Analysis** - profitability, liquidity, leverage and "
            "efficiency ratios from a trial balance style input\n"
            "- **DCF Sensitivity** - enterprise value across a WACC and "
            "terminal growth grid"
        )

    with right:
        st.subheader("Fund accounting")
        st.markdown(
            "- **NAV Calculation** - position valuation in base currency, "
            "liabilities, NAV per unit and currency exposure\n"
            "- **Unitisation** - subscription and redemption ledger with unit "
            "creation and cancellation by dealing date"
        )

    st.divider()
    st.caption(
        "Sample data is illustrative only and is not based on any real fund or "
        "company. Calculations are simplified for demonstration."
    )


# ----------------------------------------------------------------------------
# NPV & IRR
# ----------------------------------------------------------------------------
def page_npv_irr():
    st.title("NPV & IRR")
    st.caption("Expected columns: Year, CashFlow. Period 0 is the initial outlay.")

    raw = sidebar_source("Cash flows CSV", "sample_cashflows.csv", "npv_upload")
    discount_rate = (
        st.sidebar.number_input(
            "Discount rate (%)", min_value=0.0, max_value=100.0, value=10.0, step=0.25
        )
        / 100
    )

    try:
        cashflows = npv_irr.prepare_cashflows(raw)
    except ValueError as error:
        st.error(str(error))
        st.stop()

    summary = npv_irr.summarise(cashflows, discount_rate)
    row = summary.iloc[0]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("NPV", f"{row['NPV']:,.2f}")
    col2.metric(
        "IRR",
        f"{row['IRR_Percent']:.2f}%" if pd.notna(row["IRR_Percent"]) else "n/a",
    )
    col3.metric(
        "Payback",
        f"{row['Payback_Periods']:.2f} periods"
        if pd.notna(row["Payback_Periods"])
        else "never",
    )
    col4.metric("Total undiscounted", f"{row['Total_Undiscounted']:,.2f}")

    if pd.isna(row["IRR_Percent"]):
        st.info(
            "IRR needs at least one negative and one positive cash flow to solve."
        )

    st.subheader("Cash flows")
    st.dataframe(cashflows, width="stretch", hide_index=True)

    st.subheader("NPV profile")
    st.caption("NPV across discount rates. It crosses zero at the IRR.")
    profile = npv_irr.npv_profile(cashflows)
    st.line_chart(profile.set_index("Discount_Rate_Percent")["NPV"])

    download("Download summary (CSV)", summary, "npv_irr_summary.csv")


# ----------------------------------------------------------------------------
# Ratio analysis
# ----------------------------------------------------------------------------
def page_ratios():
    st.title("Ratio Analysis")
    st.caption("Expected columns: Metric, Value.")

    raw = sidebar_source("Financials CSV", "sample_financials.csv", "ratio_upload")

    try:
        values = ratios.to_metric_dict(raw)
    except ValueError as error:
        st.error(str(error))
        st.stop()

    absent = ratios.missing_metrics(values)
    if absent:
        st.warning(
            "Ratios needing these metrics are skipped: " + ", ".join(absent)
        )

    table = ratios.compute_ratios(values)
    if table.empty:
        st.error("No ratios could be calculated from this file.")
        st.stop()

    headline = {r["Ratio"]: r for _, r in table.iterrows()}
    cols = st.columns(4)
    for col, name in zip(
        cols, ["Gross Margin", "Net Profit Margin", "Current Ratio", "Debt-to-Equity"]
    ):
        if name in headline:
            entry = headline[name]
            col.metric(name, ratios.format_value(entry["Value"], entry["Format"]))

    for category in table["Category"].unique():
        st.subheader(category)
        subset = table[table["Category"] == category]
        st.dataframe(
            ratios.display_table(subset).drop(columns="Category"),
            width="stretch",
            hide_index=True,
        )

    st.subheader("Input metrics")
    st.dataframe(
        pd.DataFrame(
            [{"Metric": k, "Value": v} for k, v in values.items()]
        ),
        width="stretch",
        hide_index=True,
    )

    download(
        "Download ratios (CSV)",
        ratios.display_table(table),
        "ratio_analysis.csv",
    )


# ----------------------------------------------------------------------------
# DCF sensitivity
# ----------------------------------------------------------------------------
def page_dcf():
    st.title("DCF Sensitivity")
    st.caption("Expected columns: Year, FCF. Forecast free cash flows, one row per year.")

    raw = sidebar_source(
        "Forecast cash flows CSV", "forecast_cashflows.csv", "dcf_upload"
    )

    st.sidebar.subheader("WACC range (%)")
    wacc_start = st.sidebar.number_input("WACC from", 0.1, 50.0, 7.5, 0.25)
    wacc_stop = st.sidebar.number_input("WACC to", 0.1, 50.0, 10.0, 0.25)
    wacc_step = st.sidebar.number_input("WACC step", 0.05, 10.0, 0.5, 0.05)

    st.sidebar.subheader("Terminal growth range (%)")
    g_start = st.sidebar.number_input("Growth from", 0.0, 20.0, 0.0, 0.25)
    g_stop = st.sidebar.number_input("Growth to", 0.0, 20.0, 1.25, 0.25)
    g_step = st.sidebar.number_input("Growth step", 0.05, 5.0, 0.25, 0.05)

    try:
        forecast = dcf.prepare_fcf(raw)
        wacc_values = dcf.build_range(wacc_start / 100, wacc_stop / 100, wacc_step / 100)
        growth_values = dcf.build_range(g_start / 100, g_stop / 100, g_step / 100)
    except ValueError as error:
        st.error(str(error))
        st.stop()

    if len(wacc_values) * len(growth_values) > 2500:
        st.error("That grid is too large. Widen the step size or narrow the range.")
        st.stop()

    fcfs = forecast["FCF"].to_numpy(dtype=float)

    st.subheader("Base case")
    base_col1, base_col2 = st.columns(2)
    base_wacc = base_col1.select_slider(
        "WACC for the base case (%)",
        options=[round(w * 100, 2) for w in wacc_values],
        value=round(float(wacc_values[len(wacc_values) // 2]) * 100, 2),
    )
    base_growth = base_col2.select_slider(
        "Terminal growth for the base case (%)",
        options=[round(g * 100, 2) for g in growth_values],
        value=round(float(growth_values[len(growth_values) // 2]) * 100, 2),
    )

    breakdown = dcf.valuation_breakdown(fcfs, base_wacc / 100, base_growth / 100)
    row = breakdown.iloc[0]

    if row["Enterprise_Value"] is None or pd.isna(row["Enterprise_Value"]):
        st.error("WACC must be above terminal growth for the perpetuity to hold.")
    else:
        m1, m2, m3 = st.columns(3)
        m1.metric("Enterprise value", f"{row['Enterprise_Value']:,.2f}")
        m2.metric("PV of forecast FCF", f"{row['PV_Explicit_FCF']:,.2f}")
        m3.metric(
            "Terminal value share",
            f"{row['Terminal_Share_Percent']:.1f}%"
            if pd.notna(row["Terminal_Share_Percent"])
            else "n/a",
        )

    st.subheader("Discount schedule")
    schedule = dcf.discounted_schedule(fcfs, base_wacc / 100)
    st.dataframe(schedule, width="stretch", hide_index=True)

    st.subheader("Sensitivity grid")
    st.caption("Enterprise value by WACC (rows) and terminal growth (columns).")
    grid = dcf.sensitivity_grid(fcfs, wacc_values, growth_values)
    st.dataframe(
        grid.style.format("{:,.2f}", na_rep="n/a").background_gradient(
            cmap="RdYlGn", axis=None
        ),
        width="stretch",
    )

    st.subheader("Value vs WACC")
    st.caption(f"Holding terminal growth at {base_growth:.2f}%.")
    curve = dcf.value_vs_wacc(fcfs, wacc_values, base_growth / 100)
    st.line_chart(curve.set_index("WACC_Percent")["Enterprise_Value"])

    left, right = st.columns(2)
    with left:
        download("Download grid (CSV)", grid, "dcf_sensitivity.csv", index=True)
    with right:
        download("Download base case (CSV)", breakdown, "dcf_base_case.csv")


# ----------------------------------------------------------------------------
# NAV calculation
# ----------------------------------------------------------------------------
def page_nav():
    st.title("NAV Calculation")
    st.caption(
        "Positions need: Instrument, Quantity, Price, Base_CCY, FX_to_Base. "
        "Liabilities need: Liability, Amount, Base_CCY."
    )

    positions_raw = sidebar_source(
        "Positions CSV", "sample_fund_positions.csv", "nav_pos_upload"
    )
    liabilities_raw = sidebar_source(
        "Liabilities CSV", "sample_liabilities.csv", "nav_liab_upload"
    )

    base_ccy = st.sidebar.text_input("Base currency", value="USD", max_chars=5)
    units_outstanding = st.sidebar.number_input(
        "Units outstanding", min_value=0.000001, value=100000.0, step=1000.0, format="%.6f"
    )

    try:
        valued = nav.value_positions(positions_raw)
        liabilities = nav.prepare_liabilities(liabilities_raw)
        summary = nav.nav_summary(valued, liabilities, units_outstanding, base_ccy.upper())
    except ValueError as error:
        st.error(str(error))
        st.stop()

    row = summary.iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total assets", f"{row['Total_Assets']:,.2f}")
    c2.metric("Total liabilities", f"{row['Total_Liabilities']:,.2f}")
    c3.metric("Net assets", f"{row['Net_Assets']:,.2f}")
    c4.metric("NAV per unit", f"{row['NAV_Per_Unit']:,.6f}")

    st.subheader("Valued positions")
    st.dataframe(valued, width="stretch", hide_index=True)

    left, right = st.columns(2)

    with left:
        st.subheader("Currency exposure")
        exposure = nav.currency_exposure(valued)
        st.dataframe(exposure, width="stretch", hide_index=True)
        st.bar_chart(exposure.set_index("Currency")["Value_Base"])

    with right:
        st.subheader("Position weights")
        weights = nav.position_weights(valued)
        st.dataframe(weights, width="stretch", hide_index=True)
        st.bar_chart(weights.set_index("Instrument")["Percent_of_Assets"])

    st.subheader("Liabilities")
    st.dataframe(liabilities, width="stretch", hide_index=True)

    d1, d2, d3 = st.columns(3)
    with d1:
        download("Download NAV summary", summary, "nav_summary.csv")
    with d2:
        download("Download valued positions", valued, "nav_positions_valued.csv")
    with d3:
        download("Download currency exposure", exposure, "nav_currency_exposure.csv")


# ----------------------------------------------------------------------------
# Unitisation
# ----------------------------------------------------------------------------
def page_unitisation():
    st.title("Unitisation")
    st.caption(
        "Transactions need: Date, Investor, Type (Subscription or Redemption), "
        "Amount_Base."
    )

    raw = sidebar_source(
        "Transactions CSV", "sample_investor_transactions.csv", "unit_upload"
    )

    opening_units = st.sidebar.number_input(
        "Opening units", min_value=0.0, value=100000.0, step=1000.0, format="%.6f"
    )
    opening_navpu = st.sidebar.number_input(
        "Opening NAV per unit", min_value=0.000001, value=1.0, step=0.01, format="%.6f"
    )

    try:
        transactions = unitisation.prepare_transactions(raw)
    except ValueError as error:
        st.error(str(error))
        st.stop()

    dates = unitisation.dealing_dates(transactions)

    st.subheader("NAV per unit by dealing date")
    st.caption(
        "In practice these come from the NAV pack for each date. Edit the values "
        "below to reprice the ledger."
    )
    nav_input = st.data_editor(
        pd.DataFrame({"Date": dates, "NAV_Per_Unit": [round(opening_navpu, 6)] * len(dates)}),
        width="stretch",
        hide_index=True,
        disabled=["Date"],
        column_config={
            "NAV_Per_Unit": st.column_config.NumberColumn(
                "NAV per unit", min_value=0.000001, format="%.6f"
            )
        },
        key="navpu_editor",
    )

    nav_by_date = dict(zip(nav_input["Date"], nav_input["NAV_Per_Unit"]))

    try:
        ledger, investors, totals = unitisation.run_unitisation(
            transactions, nav_by_date, opening_units, opening_navpu
        )
    except ValueError as error:
        st.error(str(error))
        st.stop()

    totals_row = totals.iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Opening units", f"{totals_row['Opening_Units']:,.2f}")
    c2.metric("Units created", f"{totals_row['Units_Created']:,.2f}")
    c3.metric("Units cancelled", f"{totals_row['Units_Cancelled']:,.2f}")
    c4.metric("Closing units", f"{totals_row['Closing_Units']:,.2f}")

    st.subheader("Unitisation ledger")
    st.dataframe(ledger, width="stretch", hide_index=True)

    left, right = st.columns(2)

    with left:
        st.subheader("Investor holdings")
        st.dataframe(investors, width="stretch", hide_index=True)

    with right:
        st.subheader("Total units over time")
        if not ledger.empty:
            series = ledger.groupby("Date")["Total_Units_After"].last()
            st.line_chart(series)

    d1, d2 = st.columns(2)
    with d1:
        download("Download ledger (CSV)", ledger, "unitisation_ledger.csv")
    with d2:
        download("Download investor units (CSV)", investors, "investor_units.csv")


# ----------------------------------------------------------------------------
# Router
# ----------------------------------------------------------------------------
PAGES = {
    "home": page_home,
    "npv_irr": page_npv_irr,
    "ratios": page_ratios,
    "dcf": page_dcf,
    "nav": page_nav,
    "unitisation": page_unitisation,
}


def main():
    st.sidebar.title("Finance Toolkit")
    choice = st.sidebar.radio("Tool", list(TOOLS.keys()), label_visibility="collapsed")
    st.sidebar.divider()
    PAGES[TOOLS[choice]]()
    st.sidebar.divider()
    st.sidebar.caption("Built with Streamlit. Sample data is illustrative only.")


if __name__ == "__main__":
    main()
