import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
BINANCE = ROOT / "binance"
START = pd.Timestamp("2023-01-01")
RET_COL = "ret_utc1" 


def load_daily_returns():
    path = BINANCE / "daily_returns.parquet"
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values(["symbol", "date"])


def load_perp_klines():
    path = BINANCE / "perp_klines_1h.parquet"
    return pd.read_parquet(path)


def load_funding_rates():
    path = BINANCE / "funding_rates.parquet"
    return pd.read_parquet(path)
