# MFIN 7037 — Assignment 2: Crypto Long/Short Strategy

## Quick Start (Run Everything)

```bash
# 1. Install dependencies (from repo root)
pip install -r requirements.txt

# 2. Ensure binance/ data folder exists at repo root with these files:
#    binance/perp_klines_1h.parquet
#    binance/spot_klines_1h.parquet
#    binance/daily_returns.parquet
#    binance/funding_rates.parquet

# 3. Run Q3 and Q4 (flow imbalance + momentum backtests + PDF reports)
cd "Q3 and 4"
python run_all.py

# 4. Run Extra Credit (all 9 bonus questions)
cd "../Extra Credit"
python extra_credit.py
```

Total runtime: ~2 minutes. Python 3.10+ required.

On macOS, LightGBM (used in Extra Credit EC6) may need `brew install libomp`. If unavailable, it automatically falls back to scikit-learn's GradientBoosting.

---

## Data

All scripts expect the Binance parquet files in a `binance/` folder at the repo root:

| File | Used By | Description |
|------|---------|-------------|
| `perp_klines_1h.parquet` | Q3, Q4, EC | Hourly OHLCV + taker buy volumes for perpetual futures |
| `daily_returns.parquet` | Q3, Q4, EC | Pre-computed daily returns, dollar volume, funding rates |
| `funding_rates.parquet` | EC | 8-hourly funding rates with mark prices |
| `spot_klines_1h.parquet` | EC only | Hourly OHLCV for spot market (used in EC1) |

The `binance/` folder is git-ignored (files too large). Download from the course folder on Moodle.

---

## Project Structure

```
MFIN_7037_Assignment2/
├── README.md                   # This file
├── requirements.txt            # Python dependencies
├── binance/                    # Data (git-ignored)
├── Q3 and 4/                   # Required questions
│   ├── common/                 # Shared code (data loading, strategy, factor alpha)
│   ├── Q3/                     # Flow imbalance L/S backtest + report
│   ├── Q4/                     # 7-day momentum L/S backtest + report
│   ├── run_all.py              # Runs Q3 + Q4 + builds PDFs
│   └── make_pdfs.py            # Regenerate PDFs only
└── Extra Credit/               # All 9 extra credit questions
    ├── extra_credit.py         # Analysis script (imports from Q3 and 4/common/)
    ├── extra_credit_report.md  # Full writeup with results and citations
    └── figures/                # Generated charts (12 PNGs)
```

---

## Q3 and Q4 (Required Questions)

- **Q3** — Flow-imbalance long/short from perp order flow. Quintile sort on `taker_buy_quote_volume / quote_volume`, top-100 universe by 30-day dollar volume, trade `ret_utc1` at T+1. Includes BTC alpha regression, crypto proxy factor regression (BTC + ETH + market), and 2026 meltdown analysis.
- **Q4** — 7-day momentum long/short (Jegadeesh & Titman 1993). Same universe and timing. Includes same factor regressions.

No external factor data (Fama-French) is used. Factor analysis is crypto-native only.

### Run

```bash
cd "Q3 and 4"
python run_all.py
```

### Outputs

- `Q3 and 4/Q3/figures/`, `Q3 and 4/Q3/results/q3_metrics.txt`, `Q3 and 4/Q3/Q3_FlowImbalance_LongShort.pdf`
- `Q3 and 4/Q4/figures/`, `Q3 and 4/Q4/results/q4_metrics.txt`, `Q3 and 4/Q4/Q4_Momentum_LongShort.pdf`

---

## Extra Credit (9 Questions)

The Extra Credit script imports shared code from `Q3 and 4/common/` (same signal, universe, panel, metrics functions) and builds on top of it.

### Run

```bash
cd "Extra Credit"
python extra_credit.py
```

### Outputs

- `Extra Credit/extra_credit_report.md` — Full writeup
- `Extra Credit/figures/` — 12 generated charts

### Topics Covered

| EC | Topic | Key Result |
|----|-------|------------|
| 1 | Spot vs Perp signal | Perp SR +0.64, Spot SR -1.44 |
| 2 | Transaction costs | Breaks even at ~5 bps/day |
| 3 | Binance market share | Top-100 ~ US mid-cap liquidity |
| 4 | Win rate analysis | 48.7% combined; tercile sort most robust |
| 5 | Double sort (FI x FR) | Corner L/S Sharpe +1.16 |
| 6 | ML model (LightGBM) | Underperforms simple signal |
| 7 | Wash trading detection | Benford's Law + multi-factor scoring |
| 8 | Max drawdown vs liquidity | Median DD -91.5%, rho +0.25 |
| 9 | BTC volume smile | Peak at US open, single hump not U-shape |
