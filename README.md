# Finance Toolkit

A Streamlit web app merging two command line projects into one interface:

- [financial-analysis-toolkit](https://github.com/vrushabhpatil5/financial-analysis-toolkit) - NPV/IRR, ratio analysis, DCF sensitivity
- [fund-accounting-toolkit](https://github.com/vrushabhpatil5/fund-accounting-toolkit) - NAV calculation, unitisation

Every tool runs on bundled sample data out of the box, and accepts your own CSV upload instead.

## Tools

| Tool | What it does | Input columns |
| --- | --- | --- |
| NPV & IRR | Net present value, IRR, payback period, NPV profile curve | `Year`, `CashFlow` |
| Ratio Analysis | Profitability, liquidity, leverage and efficiency ratios | `Metric`, `Value` |
| DCF Sensitivity | Enterprise value across a WACC x terminal growth grid, with a discount schedule and value curve | `Year`, `FCF` |
| NAV Calculation | Position valuation in base currency, liabilities, NAV per unit, currency exposure and position weights | `Instrument`, `Quantity`, `Price`, `Base_CCY`, `FX_to_Base` plus `Liability`, `Amount`, `Base_CCY` |
| Unitisation | Subscription and redemption ledger, unit creation and cancellation by dealing date, investor holdings | `Date`, `Investor`, `Type`, `Amount_Base` |

## Running locally

```bash
git clone <this repo>
cd finance-toolkit-app
pip install -r requirements.txt
streamlit run app.py
```

The app opens at http://localhost:8501.

## Deploying to Streamlit Community Cloud

1. Push this folder to a GitHub repository.
2. At share.streamlit.io, choose New app and point it at the repo.
3. Set the main file path to `app.py`. Requirements are picked up automatically.

## Project layout

```
app.py                  Streamlit interface and page routing
core/
  io_utils.py           CSV loading, column validation, download helpers
  npv_irr.py            NPV, IRR, payback, NPV profile
  ratios.py             Ratio calculations and formatting
  dcf.py                DCF valuation and sensitivity grid
  nav.py                Position valuation, NAV summary, exposure
  unitisation.py        Subscription and redemption unit ledger
data/                   Sample CSVs, used when nothing is uploaded
requirements.txt
```

## What changed from the original repos

- The CLI menu (`main.py`) and the `if __name__ == "__main__"` runners are replaced by the Streamlit interface.
- Calculations now take dataframes and parameters rather than reading hardcoded file paths, so each function is testable on its own.
- Hardcoded assumptions became inputs: discount rate, WACC and growth ranges, units outstanding, base currency, opening units, and NAV per unit for each dealing date.
- Results are rendered as tables and charts with CSV download buttons, replacing writes to an `outputs/` folder and the saved matplotlib PNG.
- Added input validation with readable errors, plus payback period, ROA, ROE, operating margin, equity ratio, asset turnover, currency exposure, position weights, and a terminal value share figure.

## Notes

- Sample data is illustrative only. It is not based on any real fund or company.
- Calculations are simplified for demonstration: a single flat discount rate, perpetuity growth terminal value, and no accruals, fee tiering, or equalisation in the unitisation logic.
