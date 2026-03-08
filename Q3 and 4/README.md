# Q3 and Q4 — Assignment 2 Required Questions

## Structure

- **`common/`** — Shared code: data loading, flow imbalance, universe building, quintile sort, metrics, plots, and factor regressions (BTC alpha, crypto proxy: BTC + ETH + equal-weighted market). PDF report generation from markdown.
- **`Q3/`** — Question 3: Flow imbalance L/S from perp klines. Timeline (signal T, trade T+1), backtest, barplot, P&L vs BTC, BTC alpha regression, crypto proxy regression, 2026 meltdown window. Report in REPORT.md and PDF.
- **`Q4/`** — Question 4: 7-day momentum L/S (Jegadeesh & Titman 1993). Same universe and timing as Q3; backtest, barplot, P&L vs BTC, BTC alpha regression, crypto proxy regression. Report in REPORT.md and PDF.

Root scripts:

- **`run_all.py`** — Runs Q3 backtest, Q4 backtest, then builds both PDFs in one go.
- **`make_pdfs.py`** — Builds both Q3 and Q4 PDF reports from existing REPORT.md and figures (no backtest).

## Data

Place Binance parquet files in the assignment root's `binance/` folder (same as Extra Credit):

- `binance/perp_klines_1h.parquet`
- `binance/daily_returns.parquet`
- `binance/funding_rates.parquet` (optional; used in Extra Credit)

No external factor data (e.g. Fama–French CSV) is required. Factor analysis uses only crypto-native regressors: BTC return, ETH return, and an equal-weighted market return across the top-100 universe.

## Run

From the **assignment root** (MFIN_7037_Assignment2), install dependencies then run from the "Q3 and 4" folder:

```bash
pip install -r requirements.txt
cd "Q3 and 4"
python run_all.py
```

This runs the Q3 backtest, Q4 backtest, and generates both PDF reports. To run or build parts separately:

```bash
cd "Q3 and 4/Q3"
python run_q3.py
```

```bash
cd "Q3 and 4/Q4"
python run_q4.py
```

To regenerate only the PDFs (after editing REPORT.md or figures):

```bash
cd "Q3 and 4"
python make_pdfs.py
```

Outputs:

- **Q3:** `Q3/figures/` (barplot, P&L), `Q3/results/q3_metrics.txt` (L/S metrics, BTC alpha, crypto proxy regression, meltdown); `Q3/REPORT.md` and `Q3/Q3_FlowImbalance_LongShort.pdf`.
- **Q4:** `Q4/figures/` (barplot, P&L), `Q4/results/q4_metrics.txt` (L/S metrics, BTC Alpha Regression, crypto proxy regression); `Q4/REPORT.md` and `Q4/Q4_Momentum_LongShort.pdf`.

## Factor methodology

The assignment does not provide Fama–French factor data, and standard FF5 + MOM factors (SMB, HML, RMW, CMA, MOM) are built for equity markets and do not carry a direct meaning in crypto. We therefore do not run a traditional FF5 regression. Instead, both Q3 and Q4 use a **crypto-native proxy factor regression**: L/S returns are regressed on BTC return, ETH return, and an equal-weighted market return over the top-100 universe. Results (alpha, betas, t-stats, R²) are written to the respective metrics files and discussed in the reports. A standalone **BTC alpha** regression (single factor) is also run for both questions and reported in the same metrics files.
