# MFIN 7037 — Assignment 2: Crypto Long/Short Strategy

## Setup

```bash
pip install -r requirements.txt
```

Place the Binance parquet files in `binance/`:
- `perp_klines_1h.parquet`
- `spot_klines_1h.parquet`
- `daily_returns.parquet`
- `funding_rates.parquet`

The same `binance/` data is used by both the Q3/Q4 scripts and the Extra Credit analysis.

---

## Q3 and Q4 (Required Questions)

The folder **`Q3 and 4/`** contains the implementation and reports for the assignment’s required Questions 3 and 4.

- **Q3** — Flow-imbalance long/short: signal from perp order flow (taker buy / total volume), top-100 universe by liquidity, quintile sort, trade on `ret_utc1` at T+1. Outputs backtest metrics, barplot, P&L vs BTC, BTC alpha and crypto proxy factor regression (BTC + ETH + equal-weighted market), and a 2026 meltdown window.
- **Q4** — 7-day momentum long/short (Jegadeesh & Titman style): same universe and T→T+1 timing, quintile sort on momentum. Outputs backtest metrics, barplot, P&L vs BTC, BTC alpha and crypto proxy regression.

No external factor data (e.g. Fama–French CSV) is used; factor analysis is crypto-native only (BTC, ETH, top-100 market).

### Run Q3 and Q4

From the repo root:

```bash
cd "Q3 and 4"
python run_all.py
```

This runs the Q3 backtest, Q4 backtest, and builds both PDF reports. You can also run `run_q3.py` or `run_q4.py` from `Q3 and 4/Q3` or `Q3 and 4/Q4` separately, and `make_pdfs.py` from `Q3 and 4` to regenerate only the PDFs.

### Outputs (generated)

- **Q3:** `Q3 and 4/Q3/figures/` (barplot, P&L), `Q3 and 4/Q3/results/q3_metrics.txt`, `Q3 and 4/Q3/Q3_FlowImbalance_LongShort.pdf`
- **Q4:** `Q3 and 4/Q4/figures/` (barplot, P&L), `Q3 and 4/Q4/results/q4_metrics.txt`, `Q3 and 4/Q4/Q4_Momentum_LongShort.pdf`

Source reports (markdown) live in `Q3 and 4/Q3/REPORT.md` and `Q3 and 4/Q4/REPORT.md`. For full structure, data requirements, and factor methodology, see **`Q3 and 4/README.md`**.

---

## Extra Credit Analysis

```bash
cd "Extra Credit"
python extra_credit.py
```

This runs the full analysis (base strategy + all 9 extra credit questions) and saves figures to `Extra Credit/figures/`. Takes ~1 minute.

### Output

- `Extra Credit/extra_credit_report.md` — Full writeup with results and citations
- `Extra Credit/figures/` — All generated charts (12 PNGs)
- `Extra Credit/extra_credit.py` — Source code
