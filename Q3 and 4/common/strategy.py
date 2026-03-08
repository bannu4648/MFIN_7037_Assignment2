"""Strategy building blocks: flow imbalance, universe, quintile sort, metrics, plots."""
import pandas as pd
import numpy as np
from datetime import timedelta
from pathlib import Path

from .data_loader import RET_COL, START


def flow_imbalance_from_perp(perp):
    """
    Compute daily flow imbalance from perp hourly klines (Q3 requirement).
    flow_imbalance_1d_{i,t} = sum_h taker_buy_quote_volume_{i,t,h} / sum_h quote_volume_{i,t,h}
    """
    perp = perp.copy()
    perp["date"] = perp["timestamp"].dt.normalize()
    # Binance may use taker_buy_quote_volume or similar
    tbqv = "taker_buy_quote_volume" if "taker_buy_quote_volume" in perp.columns else "taker_buy_dollar_volume"
    qv = "quote_volume" if "quote_volume" in perp.columns else "dollar_volume"
    agg = perp.groupby(["symbol", "date"]).agg(
        tbqv=(tbqv, "sum"),
        qv=(qv, "sum"),
    ).reset_index()
    agg["flow_imbalance_1d"] = agg["tbqv"] / agg["qv"]
    return agg[["symbol", "date", "flow_imbalance_1d"]]


def flow_imbalance_from_daily(daily):
    """Flow imbalance from daily_returns (taker_buy_dollar_volume / dollar_volume)."""
    d = daily[["symbol", "date", "taker_buy_dollar_volume", "dollar_volume"]].copy()
    d["flow_imbalance_1d"] = d["taker_buy_dollar_volume"] / d["dollar_volume"]
    return d


def build_universe(daily, top_n=100, window=30):
    """Universe: top `top_n` by trailing `window`-day average dollar volume (quote volume)."""
    udf = daily[["symbol", "date", "dollar_volume"]].copy()
    udf = udf.sort_values(["symbol", "date"])
    udf["roll_dv"] = udf.groupby("symbol")["dollar_volume"].transform(
        lambda x: x.rolling(window, min_periods=window).mean()
    )
    udf = udf.dropna(subset=["roll_dv"])
    udf["rank"] = udf.groupby("date")["roll_dv"].rank(ascending=False, method="first")
    univ = udf.loc[udf["rank"] <= top_n, ["symbol", "date"]].copy()
    return univ


def build_panel(daily, signal_df, univ, ret_col=RET_COL, start=START):
    """
    Panel: signal_date (sd) -> trade_date (td = sd + 1). Forward return = ret from td.
    Uses ret_utc1: return from 1:00 UTC td to 1:00 UTC td+1 (no look-ahead if signal uses day sd's data).
    """
    # Forward returns: one column
    rfwd = daily[["symbol", "date", ret_col]].rename(
        columns={"date": "td", ret_col: "fwd"}
    )
    # Signal on signal_date; require universe on signal_date
    cols_sig = [c for c in ["symbol", "date", "flow_imbalance_1d"] if c in signal_df.columns]
    if not cols_sig:
        cols_sig = [c for c in signal_df.columns if c in ["symbol", "date", "fi"]]
        signal_df = signal_df.rename(columns={"fi": "flow_imbalance_1d"})
    p = signal_df[cols_sig].copy()
    p = p.rename(columns={"date": "sd"})
    p["td"] = p["sd"] + timedelta(days=1)
    p = p.merge(univ, left_on=["symbol", "sd"], right_on=["symbol", "date"]).drop(
        columns=["date"], errors="ignore"
    )
    p = p.merge(rfwd, on=["symbol", "td"])
    p = p[p["td"] >= start].dropna(subset=["flow_imbalance_1d", "fwd"])
    return p


def qsort(df, sig_col, ret_col="fwd", date_col="td", nq=5):
    """Quintile (or nq-tile) sort by signal; return pivot of mean returns and detail df."""
    d = df.dropna(subset=[sig_col, ret_col]).copy()
    d["Q"] = d.groupby(date_col)[sig_col].transform(
        lambda x: (
            pd.qcut(x, nq, labels=False, duplicates="drop") + 1
            if len(x) >= nq
            else pd.Series(np.nan, index=x.index)
        )
    )
    d = d.dropna(subset=["Q"])
    d["Q"] = d["Q"].astype(int)
    pv = (
        d.groupby([date_col, "Q"])[ret_col]
        .mean()
        .reset_index()
        .pivot(index=date_col, columns="Q", values=ret_col)
        .sort_index()
    )
    pv.columns.name = None
    ic = sorted(c for c in pv.columns if isinstance(c, (int, np.integer)))
    if len(ic) >= 2:
        pv["LS"] = pv[ic[-1]] - pv[ic[0]]
    return pv, d


def run_backtest(daily, signal_df, ret_col=RET_COL, start=START, top_n=100, window=30):
    """Build universe, panel, quintile sort; return panel, pivot of quintile returns, and L/S series."""
    univ = build_universe(daily, top_n=top_n, window=window)
    panel = build_panel(daily, signal_df, univ, ret_col=ret_col, start=start)
    pv, _ = qsort(panel, "flow_imbalance_1d", ret_col="fwd", date_col="td", nq=5)
    ls_ret = pv["LS"]
    return panel, pv, ls_ret


def print_backtest_metrics(pv):
    """Print quintile and L/S annualised metrics to console."""
    def _pmf(label, m):
        print(f"  {label:28s} SR={m['sr']:+.2f}  Ann={m['ar']*100:+6.1f}%  Vol={m['av']*100:5.1f}%  Cum={m['cum']*100:+8.1f}%  MDD={m['mdd']*100:+6.1f}%")
    print("\nQuintile & L/S (annualised):")
    ic = sorted(c for c in pv.columns if isinstance(c, (int, np.integer)))
    if "LS" in pv.columns:
        _pmf("L/S (Q5−Q1)", metrics(pv["LS"]))
    for q in ic:
        _pmf(f"Q{q}", metrics(pv[q]))


def metrics(s):
    """Annualised Sharpe, return, vol; cumulative return; max drawdown."""
    s = s.dropna()
    if len(s) < 2:
        return dict(sr=np.nan, ar=np.nan, av=np.nan, cum=np.nan, mdd=np.nan)
    mu = s.mean() * 365
    vol = s.std() * np.sqrt(365)
    sr = mu / vol if vol > 0 else np.nan
    cum = (1 + s).prod() - 1
    eq = (1 + s).cumprod()
    mdd = (eq / eq.cummax() - 1).min()
    return dict(sr=sr, ar=mu, av=vol, cum=cum, mdd=mdd)


def barplot_quintile(pv, title, savepath):
    """Bar plot of quintile annualised returns."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ic = sorted(c for c in pv.columns if isinstance(c, (int, np.integer)))
    vals = [pv[c].mean() * 365 * 100 for c in ic]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    colors = ["#c62828" if v < 0 else "#2e7d32" for v in vals]
    ax.bar([f"Q{c}" for c in ic], vals, color=colors, edgecolor="k", lw=0.5)
    ax.axhline(0, color="k", lw=0.5)
    ax.set_ylabel("Annualised Return (%)")
    ax.set_title(title)
    plt.tight_layout()
    savepath = Path(savepath)
    savepath.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(savepath, bbox_inches="tight")
    plt.close()


def pnl_curve(pv, btc_ret, title, savepath):
    """Cumulative P&L of L/S vs BTC."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 5.5))
    cum = (1 + pv["LS"]).cumprod()
    ax.plot(cum, label="L/S (Q5−Q1)", lw=2)
    if btc_ret is not None:
        ix = cum.index.intersection(btc_ret.index)
        if len(ix) > 0:
            ax.plot(
                (1 + btc_ret.loc[ix]).cumprod(), label="BTC", lw=1.5, alpha=0.7
            )
    ax.set_ylabel("Cumulative Return (x)")
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    savepath = Path(savepath)
    savepath.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(savepath, bbox_inches="tight")
    plt.close()


def get_btc_returns(daily, ret_col=RET_COL, start=START):
    """BTC daily return series for comparison."""
    btc = (
        daily.loc[daily["symbol"] == "BTCUSDT", ["date", ret_col]]
        .set_index("date")[ret_col]
        .sort_index()
    )
    return btc[btc.index >= start]


def get_eth_returns(daily, ret_col=RET_COL, start=START):
    """ETH daily return series (for crypto proxy regression)."""
    eth = (
        daily.loc[daily["symbol"] == "ETHUSDT", ["date", ret_col]]
        .set_index("date")[ret_col]
        .sort_index()
    )
    return eth[eth.index >= start]
