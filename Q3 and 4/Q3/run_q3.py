#!/usr/bin/env python3
"""
Q3: Flow imbalance L/S from perp klines.
- Timeline: signal from day T (hours 0–23 UTC); trade using ret_utc1 on T+1 (1am T+1 → 1am T+2).
- Quintile sort, top 100 by 30d dollar volume, backtest from 2023-01-01.
- Outputs: metrics, barplot, P&L vs BTC, BTC alpha, crypto proxy regression, 2026 meltdown.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from common.data_loader import load_daily_returns, load_perp_klines, START, RET_COL
from common.strategy import (
    flow_imbalance_from_perp,
    flow_imbalance_from_daily,
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
    """Load daily returns and perp klines."""
    print("Loading data...")
    daily = load_daily_returns()
    perp = load_perp_klines()
    print(f"  daily: {daily.shape}, perp: {perp.shape}")
    return daily, perp


def build_flow_imbalance_signal(daily, perp):
    """Build signal dataframe with flow_imbalance_1d (from perp or daily fallback)."""
    if "taker_buy_quote_volume" in perp.columns and "quote_volume" in perp.columns:
        fi_df = flow_imbalance_from_perp(perp)
        print("  Flow imbalance computed from perp hourly klines.")
    else:
        fi_df = flow_imbalance_from_daily(daily)
        fi_df = fi_df[["symbol", "date", "flow_imbalance_1d"]]
        print("  Flow imbalance from daily_returns (taker_buy_dollar_volume / dollar_volume).")
    return fi_df


def run_factor_regressions(ls_ret, daily, panel):
    """Run BTC alpha and crypto proxy regressions; print results. Returns (btc_res, proxy_res)."""
    btc_ret = get_btc_returns(daily, ret_col=RET_COL, start=START)
    btc_res = btc_alpha(ls_ret, btc_ret)
    print("\nBTC alpha (L/S regressed on BTC return):")
    print(f"  Alpha (daily): {btc_res['alpha']:.6f}  Alpha (ann.): {btc_res['alpha_ann']*100:+.2f}%")
    print(f"  Beta: {btc_res['beta']:.3f}  t(alpha): {btc_res.get('t_alpha', 'n/a')}  R2: {btc_res.get('r2', 'n/a')}")

    print(FACTOR_METHODOLOGY_MSG)
    eth_ret = get_eth_returns(daily, ret_col=RET_COL, start=START)
    mkt_ret = panel.groupby("td")["fwd"].mean().sort_index()
    proxy_res = crypto_proxy_alpha(ls_ret, btc_ret, eth_ret, mkt_ret)
    print("\nCrypto Proxy regression (BTC + ETH + MktRF):")
    print_proxy_results(
        proxy_res,
        "This regression asks whether the L/S returns can be explained by broad BTC, ETH, and "
        "market moves. A materially positive alpha indicates residual stock-selection alpha "
        "beyond simple crypto beta exposure.",
    )
    return btc_res, proxy_res


def save_figures(pv, daily):
    """Save barplot and P&L vs BTC."""
    barplot_quintile(
        pv,
        "Q3: Flow Imbalance Quintile Returns (from perp klines)",
        FIGS / "q3_barplot.png",
    )
    print(f"  Saved {FIGS / 'q3_barplot.png'}")
    btc_ret = get_btc_returns(daily, ret_col=RET_COL, start=START)
    pnl_curve(pv, btc_ret, "Q3: L/S P&L vs BTC (from 2023-01-01)", FIGS / "q3_pnl.png")
    print(f"  Saved {FIGS / 'q3_pnl.png'}")


def print_meltdown(pv):
    """Print L/S metrics over 2026 Jan–Mar if available."""
    melt = pv.loc["2026-01":"2026-03"]
    if len(melt) >= 5:
        print("\nEarly 2026 meltdown (Jan–Mar 2026):")
        m = metrics(melt["LS"])
        print(f"  {'L/S':28s} SR={m['sr']:+.2f}  Ann={m['ar']*100:+6.1f}%  Vol={m['av']*100:5.1f}%  Cum={m['cum']*100:+8.1f}%  MDD={m['mdd']*100:+6.1f}%")
    else:
        print("\n2026 meltdown: insufficient data in sample.")


def save_results(ls_ret, btc_res, proxy_res, pv):
    """Write metrics and optional meltdown stats to q3_metrics.txt."""
    melt = pv.loc["2026-01":"2026-03"]
    summary = {
        "L/S": metrics(ls_ret),
        "BTC_alpha": btc_res,
        "Crypto Proxy FF5 regression (BTC + ETH + MktRF)": proxy_res,
        "meltdown_2026": metrics(melt["LS"]) if len(melt) >= 5 else None,
    }
    pd.Series({k: str(v) for k, v in summary.items()}).to_csv(RESULTS / "q3_metrics.txt", header=False)
    print(f"\nMetrics written to {RESULTS / 'q3_metrics.txt'}")


def main():
    print("Q3: Flow imbalance long/short (from perp klines)")
    print("=" * 60)

    daily, perp = load_data()
    signal_df = build_flow_imbalance_signal(daily, perp)

    panel, pv, ls_ret = run_backtest(daily, signal_df, ret_col=RET_COL, start=START)
    print(f"  Panel: {len(panel):,} rows, {panel['td'].nunique()} days")

    print_backtest_metrics(pv)
    save_figures(pv, daily)

    btc_res, proxy_res = run_factor_regressions(ls_ret, daily, panel)
    print_meltdown(pv)
    save_results(ls_ret, btc_res, proxy_res, pv)
    print("Done.")


if __name__ == "__main__":
    main()
