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

## Running the Extra Credit Analysis

```bash
cd "Extra Credit"
python extra_credit.py
```

This runs the full analysis (base strategy + all 9 extra credit questions) and saves figures to `Extra Credit/figures/`. Takes ~1 minute.

## Output

- `Extra Credit/extra_credit_report.md` — Full writeup with results and citations
- `Extra Credit/figures/` — All generated charts (12 PNGs)
- `Extra Credit/extra_credit.py` — Source code
