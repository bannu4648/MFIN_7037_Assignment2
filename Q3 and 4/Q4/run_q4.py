#!/usr/bin/env python3
"""
Q4: Backtest one other signal — 7-day momentum (Jegadeesh & Titman 1993).
Same universe and timing as Q3; quintile sort on momentum; barplot and P&L vs BTC.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from common.data_loader import load_daily_returns, START, RET_COL
from common.strategy import (
    run_backtest,
    metrics,
    print_backtest_metrics,
    barplot_quintile,
    pnl_curve,
    get_btc_returns,
    get_eth_returns,
)
from common.factor_alpha import btc_alpha, crypto_proxy_alpha, FACTOR_METHODOLOGY_MSG, print_proxy_results


FIGS = Path(__file__).resolve().parent / "figures"
RESULTS = Path(__file__).resolve().parent / "results"
FIGS.mkdir(exist_ok=True)
RESULTS.mkdir(exist_ok=True)


def load_data():
    """Load daily returns and sort by symbol, date."""
    daily = load_daily_returns()
    return daily.sort_values(["symbol", "date"])


def build_momentum_signal(daily):
    """Build signal dataframe with 7-day momentum as flow_imbalance_1d (for build_panel)."""
    daily = daily.copy()
    daily["ret_7d"] = (
        daily["close_utc1"] / daily.groupby("symbol")["close_utc1"].shift(7) - 1
    )
    signal_df = daily[["symbol", "date", "ret_7d"]].copy()
    signal_df = signal_df.rename(columns={"ret_7d": "flow_imbalance_1d"})
    signal_df = signal_df.dropna(subset=["flow_imbalance_1d"])
    return signal_df


def run_factor_regressions(ls_ret, daily, panel):
    """Run BTC alpha and crypto proxy regressions; print results. Returns (btc_res, proxy_res)."""
    btc_ret = get_btc_returns(daily, ret_col=RET_COL, start=START)
    btc_res = btc_alpha(ls_ret, btc_ret)
    print("\nBTC Alpha Regression (L/S regressed on BTC return):")
    print(
        f"  Alpha (daily): {btc_res['alpha']:.6f}  Alpha (ann.): {btc_res['alpha_ann']*100:+.2f}%  "
        f"Beta: {btc_res['beta']:.3f}  t(alpha): {btc_res.get('t_alpha', 'n/a')}  R2: {btc_res.get('r2', 'n/a')}"
    )
    print(FACTOR_METHODOLOGY_MSG)
    eth_ret = get_eth_returns(daily, ret_col=RET_COL, start=START)
    mkt_ret = panel.groupby("td")["fwd"].mean().sort_index()
    proxy_res = crypto_proxy_alpha(ls_ret, btc_ret, eth_ret, mkt_ret)
    print("\nCrypto Proxy regression (BTC + ETH + MktRF):")
    print_proxy_results(
        proxy_res,
        "This checks whether the momentum L/S portfolio is just repackaged BTC, ETH, or broad "
        "market exposure. A non-zero alpha suggests incremental momentum alpha after controlling "
        "for these crypto betas.",
    )
    return btc_res, proxy_res


def save_figures(pv, daily):
    """Save barplot and P&L vs BTC."""
    barplot_quintile(
        pv,
        "Q4: 7-day Momentum Quintile Returns (Jegadeesh & Titman 1993)",
        FIGS / "q4_barplot.png",
    )
    print(f"  Saved {FIGS / 'q4_barplot.png'}")
    btc_ret = get_btc_returns(daily, ret_col=RET_COL, start=START)
    pnl_curve(pv, btc_ret, "Q4: Momentum L/S P&L vs BTC (from 2023-01-01)", FIGS / "q4_pnl.png")
    print(f"  Saved {FIGS / 'q4_pnl.png'}")


def save_results(ls_ret, btc_res, proxy_res):
    """Write metrics to q4_metrics.txt."""
    summary = {
        "L/S": metrics(ls_ret),
        "BTC Alpha Regression": btc_res,
        "Q4 Crypto Proxy FF5 regression (BTC + ETH + MktRF)": proxy_res,
    }
    pd.Series({k: str(v) for k, v in summary.items()}).to_csv(RESULTS / "q4_metrics.txt", header=False)
    print(f"\nMetrics written to {RESULTS / 'q4_metrics.txt'}")


def main():
    print("Q4: Momentum (7-day) long/short")
    print("=" * 60)

    daily = load_data()
    signal_df = build_momentum_signal(daily)

    panel, pv, ls_ret = run_backtest(daily, signal_df, ret_col=RET_COL, start=START)
    print(f"  Panel: {len(panel):,} rows, {panel['td'].nunique()} days")

    print_backtest_metrics(pv)
    save_figures(pv, daily)

    btc_res, proxy_res = run_factor_regressions(ls_ret, daily, panel)
    save_results(ls_ret, btc_res, proxy_res)
    print("Done.")


if __name__ == "__main__":
    main()
