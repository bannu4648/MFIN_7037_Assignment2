#!/usr/bin/env python3
"""MFIN 7037 Assignment 2 – Extra Credit Analysis"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from pathlib import Path
from datetime import timedelta
import warnings
warnings.filterwarnings('ignore')

DATA = Path(__file__).resolve().parent.parent / 'binance'
FIGS = Path(__file__).resolve().parent / 'figures'
FIGS.mkdir(exist_ok=True)
START = pd.Timestamp('2023-01-01')
RET = 'ret_utc1'

np.random.seed(42)
sns.set_style('whitegrid')
plt.rcParams.update({'font.size': 11, 'figure.dpi': 150})


def metrics(s):
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


def pmf(label, m):
    print(f"  {label:32s} SR={m['sr']:+.2f}  "
          f"Ann={m['ar']*100:+6.1f}%  Vol={m['av']*100:5.1f}%  "
          f"Cum={m['cum']*100:+8.1f}%  MDD={m['mdd']*100:+6.1f}%")


def qsort(df, sig_col, ret_col='fwd', date_col='td', nq=5):
    d = df.dropna(subset=[sig_col, ret_col]).copy()
    d['Q'] = d.groupby(date_col)[sig_col].transform(
        lambda x: (pd.qcut(x, nq, labels=False, duplicates='drop') + 1)
        if len(x) >= nq else pd.Series(np.nan, index=x.index))
    d = d.dropna(subset=['Q'])
    d['Q'] = d['Q'].astype(int)
    pv = (d.groupby([date_col, 'Q'])[ret_col].mean()
          .reset_index()
          .pivot(index=date_col, columns='Q', values=ret_col)
          .sort_index())
    pv.columns.name = None
    ic = sorted(c for c in pv.columns if isinstance(c, (int, np.integer)))
    if len(ic) >= 2:
        pv['LS'] = pv[ic[-1]] - pv[ic[0]]
    return pv, d


def bar_quintile(pv, title, fn):
    ic = sorted(c for c in pv.columns if isinstance(c, (int, np.integer)))
    vals = [pv[c].mean() * 365 * 100 for c in ic]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    colours = ['#c62828' if v < 0 else '#2e7d32' for v in vals]
    ax.bar([f'Q{c}' for c in ic], vals, color=colours, edgecolor='k', lw=.5)
    ax.axhline(0, color='k', lw=.5)
    ax.set_ylabel('Annualised Return (%)')
    ax.set_title(title)
    plt.tight_layout()
    plt.savefig(FIGS / fn, bbox_inches='tight')
    plt.close()
    print(f"    saved {fn}")


def pnl_curve(pv, btc_r, title, fn):
    fig, ax = plt.subplots(figsize=(10, 5.5))
    cum = (1 + pv['LS']).cumprod()
    ax.plot(cum, label='L/S (Q5-Q1)', lw=2)
    if btc_r is not None:
        ix = cum.index.intersection(btc_r.index)
        if len(ix) > 0:
            ax.plot((1 + btc_r.loc[ix]).cumprod(), label='BTC', lw=1.5, alpha=.7)
    ax.set_ylabel('Cumulative Return (x)')
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=.3)
    plt.tight_layout()
    plt.savefig(FIGS / fn, bbox_inches='tight')
    plt.close()
    print(f"    saved {fn}")


def main():
    # ── Load ───────────────────────────────────────────────────────────
    print("Loading data...")
    perp = pd.read_parquet(DATA / 'perp_klines_1h.parquet')
    spot = pd.read_parquet(DATA / 'spot_klines_1h.parquet')
    daily = pd.read_parquet(DATA / 'daily_returns.parquet')
    funding = pd.read_parquet(DATA / 'funding_rates.parquet')
    daily['date'] = pd.to_datetime(daily['date'])
    print(f"  perp={perp.shape}  spot={spot.shape}  daily={daily.shape}")

    # ── Preprocess ─────────────────────────────────────────────────────
    daily = daily.sort_values(['symbol', 'date'])
    daily['fi'] = daily['taker_buy_dollar_volume'] / daily['dollar_volume']
    daily['ret_1d'] = daily.groupby('symbol')[RET].shift(1)
    daily['ret_7d'] = (daily['close_utc1'] /
                       daily.groupby('symbol')['close_utc1'].shift(7) - 1)
    daily['log_dv'] = np.log1p(daily['dollar_volume'])

    # ── Universe (top 100 by trailing 30d avg $ vol) ───────────────────
    udf = daily[['symbol', 'date', 'dollar_volume']].copy()
    udf = udf.sort_values(['symbol', 'date'])
    udf['rdv'] = udf.groupby('symbol')['dollar_volume'].transform(
        lambda x: x.rolling(30, min_periods=30).mean())
    udf = udf.dropna(subset=['rdv'])
    udf['rk'] = udf.groupby('date')['rdv'].rank(ascending=False, method='first')
    univ = udf.loc[udf['rk'] <= 100, ['symbol', 'date']].copy()
    print(f"  Universe: {univ['date'].nunique()} dates")

    # ── Build panel: signal_date -> trade_date = sd+1 ──────────────────
    cols = ['symbol', 'date', 'fi', 'funding_rate_24h', 'ret_1d',
            'ret_7d', 'log_dv', 'close_utc1', 'dollar_volume']
    p = daily[cols].copy().rename(columns={'date': 'sd'})
    p['td'] = p['sd'] + timedelta(days=1)
    p = p.merge(univ, left_on=['symbol', 'sd'],
                right_on=['symbol', 'date']).drop(columns='date')
    rfwd = daily[['symbol', 'date', RET]].rename(
        columns={'date': 'td', RET: 'fwd'})
    p = p.merge(rfwd, on=['symbol', 'td'])
    p = p[p['td'] >= START].dropna(subset=['fi', 'fwd'])
    print(f"  Panel: {len(p):,} rows, {p['td'].nunique()} days")

    btc = (daily.loc[daily['symbol'] == 'BTCUSDT', ['date', RET]]
           .set_index('date')[RET].sort_index())
    btc = btc[btc.index >= START]

    # ══════════════════════════════════════════════════════════════════
    # STEP 0: BASE STRATEGY
    # ══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  STEP 0: BASE STRATEGY - Perp Flow Imbalance Quintile L/S")
    print("=" * 70)
    pv_base, det_base = qsort(p, 'fi')
    pmf('L/S (Q5-Q1)', metrics(pv_base['LS']))
    ic = sorted(c for c in pv_base.columns if isinstance(c, (int, np.integer)))
    for q in ic:
        pmf(f'Q{q}', metrics(pv_base[q]))
    bar_quintile(pv_base, 'Perp Flow Imbalance - Quintile Returns', 'base_bar.png')
    pnl_curve(pv_base, btc, 'L/S P&L vs BTC (from 2023)', 'base_pnl.png')

    melt = pv_base.loc['2026-01':'2026-03']
    if len(melt) > 5:
        print("  2026 meltdown:")
        pmf('L/S (Jan-Feb 2026)', metrics(melt['LS']))

    # ══════════════════════════════════════════════════════════════════
    # EC1: SPOT vs PERP
    # ══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  EC1: SPOT vs PERP SIGNAL COMPARISON")
    print("=" * 70)
    pvol = perp['quote_volume'].sum()
    svol = spot['quote_volume'].sum()
    print(f"  Perp total $ volume: ${pvol:,.0f}")
    print(f"  Spot total $ volume: ${svol:,.0f}")
    print(f"  Perp / Spot ratio:   {pvol / svol:.1f}x")

    sc = spot[['symbol', 'timestamp', 'taker_buy_quote_volume',
               'quote_volume']].copy()
    sc['sd'] = sc['timestamp'].dt.normalize()
    sagg = sc.groupby(['symbol', 'sd']).agg(
        tbqv=('taker_buy_quote_volume', 'sum'),
        qv=('quote_volume', 'sum')).reset_index()
    sagg['fi_spot'] = sagg['tbqv'] / sagg['qv']
    sagg['td'] = sagg['sd'] + timedelta(days=1)

    sp = sagg[['symbol', 'sd', 'td', 'fi_spot']].merge(
        univ, left_on=['symbol', 'sd'],
        right_on=['symbol', 'date']).drop(columns='date')
    sp = sp.merge(rfwd, on=['symbol', 'td'])
    sp = sp[sp['td'] >= START].dropna(subset=['fi_spot', 'fwd'])

    pv_spot, _ = qsort(sp, 'fi_spot')
    pmf('Spot L/S', metrics(pv_spot['LS']))
    pmf('Perp L/S (recap)', metrics(pv_base['LS']))
    bar_quintile(pv_spot, 'Spot Flow Imbalance - Quintile Returns',
                 'ec1_spot_bar.png')
    pnl_curve(pv_spot, btc, 'Spot L/S vs BTC', 'ec1_spot_pnl.png')
    del sc, sagg, sp

    # ══════════════════════════════════════════════════════════════════
    # EC2: TRANSACTION COSTS
    # ══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  EC2: TRANSACTION COSTS")
    print("=" * 70)
    print("  Binance futures: 0.02% maker / 0.04% taker")
    print("  Round-trip per leg ~8 bps; L/S two legs ~16 bps max")

    # Estimate turnover
    long_q = det_base['Q'].max()
    short_q = det_base['Q'].min()
    long_by_day = det_base[det_base['Q'] == long_q].groupby('td')['symbol'].apply(set)
    short_by_day = det_base[det_base['Q'] == short_q].groupby('td')['symbol'].apply(set)
    dates_sorted = sorted(long_by_day.index)
    turn_l, turn_s = [], []
    for i in range(1, len(dates_sorted)):
        pl = long_by_day.iloc[i - 1]
        cl = long_by_day.iloc[i]
        if len(cl) > 0:
            turn_l.append(len(pl.symmetric_difference(cl)) / (2 * max(len(cl), 1)))
        ps = short_by_day.iloc[i - 1]
        cs = short_by_day.iloc[i]
        if len(cs) > 0:
            turn_s.append(len(ps.symmetric_difference(cs)) / (2 * max(len(cs), 1)))
    avg_turn = (np.mean(turn_l) + np.mean(turn_s)) / 2
    print(f"  Avg daily one-way turnover: {avg_turn:.1%}")

    ls_raw = pv_base['LS']
    costs = [0, 2, 5, 8, 10, 15, 20]
    cost_srs = []
    for c in costs:
        adj = ls_raw - c / 10000
        m = metrics(adj)
        cost_srs.append(m['sr'])
        pmf(f'{c:2d} bps/day total friction', m)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(costs, cost_srs, 'o-', lw=2, color='steelblue')
    ax.set_xlabel('Daily Friction (bps)')
    ax.set_ylabel('Sharpe Ratio')
    ax.set_title('L/S Sharpe Sensitivity to Transaction Costs')
    ax.grid(True, alpha=.3)
    plt.tight_layout()
    plt.savefig(FIGS / 'ec2_cost.png', bbox_inches='tight')
    plt.close()
    print("    saved ec2_cost.png")

    # ══════════════════════════════════════════════════════════════════
    # EC3: BINANCE MARKET SHARE
    # ══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  EC3: BINANCE MARKET SHARE & DOLLAR VOLUME")
    print("=" * 70)
    thr = daily.groupby('date').apply(
        lambda g: g.nlargest(100, 'dollar_volume')['dollar_volume'].min()
        if len(g) >= 100 else np.nan)
    thr = thr.dropna()
    avg100 = daily.groupby('date').apply(
        lambda g: g.nlargest(100, 'dollar_volume')['dollar_volume'].mean()
        if len(g) >= 100 else np.nan)
    avg100 = avg100.dropna()
    print(f"  Top-100 threshold (Binance): ${thr.mean():,.0f}/day")
    print(f"  Top-100 average (Binance):   ${avg100.mean():,.0f}/day")
    print(f"  Binance ~ 37-45% global derivatives volume")
    print(f"  => 100th crypto globally:  ~${thr.mean()/0.40:,.0f}/day")
    print(f"  => Average top-100 global: ~${avg100.mean()/0.40:,.0f}/day")
    print(f"  US mid-cap stock: ~$20-200M/day for comparison")

    # ══════════════════════════════════════════════════════════════════
    # EC4: WIN RATE
    # ══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  EC4: WIN RATE ANALYSIS")
    print("=" * 70)
    qmax = det_base['Q'].max()
    qmin = det_base['Q'].min()
    longs = det_base[det_base['Q'] == qmax]
    shorts = det_base[det_base['Q'] == qmin]
    wr_l = (longs['fwd'] > 0).mean()
    wr_s = (shorts['fwd'] < 0).mean()
    wr_comb = ((longs['fwd'] > 0).sum() + (shorts['fwd'] < 0).sum()) / \
              (len(longs) + len(shorts))
    print(f"  Long  (Q{qmax}) win rate (ret>0):  {wr_l:.1%}")
    print(f"  Short (Q{qmin}) win rate (ret<0):  {wr_s:.1%}")
    print(f"  Combined win rate:                {wr_comb:.1%}")

    dwr_l = longs.groupby('td')['fwd'].apply(lambda x: (x > 0).mean())
    dwr_s = shorts.groupby('td')['fwd'].apply(lambda x: (x < 0).mean())
    print(f"  Daily avg win rate (longs):  {dwr_l.mean():.1%} +/- {dwr_l.std():.1%}")
    print(f"  Daily avg win rate (shorts): {dwr_s.mean():.1%} +/- {dwr_s.std():.1%}")

    print("\n  Granularity comparison:")
    for nq, lab in [(3, 'Tercile'), (5, 'Quintile'), (10, 'Decile')]:
        pv_g, _ = qsort(p, 'fi', nq=nq)
        if 'LS' in pv_g.columns:
            pmf(f'{lab} L/S (n={nq})', metrics(pv_g['LS']))

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.5))
    a1.hist(dwr_l, bins=30, alpha=.7, color='#2e7d32')
    a1.axvline(0.5, color='k', ls='--', lw=1)
    a1.set_title(f'Long (Q{qmax}) Daily Win Rate')
    a1.set_xlabel('Win Rate')
    a2.hist(dwr_s, bins=30, alpha=.7, color='#c62828')
    a2.axvline(0.5, color='k', ls='--', lw=1)
    a2.set_title(f'Short (Q{qmin}) Daily Win Rate')
    a2.set_xlabel('Win Rate')
    plt.tight_layout()
    plt.savefig(FIGS / 'ec4_winrate.png', bbox_inches='tight')
    plt.close()
    print("    saved ec4_winrate.png")

    # ══════════════════════════════════════════════════════════════════
    # EC5: DOUBLE SORT
    # ══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  EC5: DOUBLE SORT - Flow Imbalance x Funding Rate")
    print("=" * 70)
    ds = p.dropna(subset=['fi', 'funding_rate_24h', 'fwd']).copy()
    ds['Q_fi'] = ds.groupby('td')['fi'].transform(
        lambda x: pd.qcut(x, 5, labels=False, duplicates='drop') + 1
        if len(x) >= 5 else pd.Series(np.nan, index=x.index))
    ds['Q_fr'] = ds.groupby('td')['funding_rate_24h'].transform(
        lambda x: pd.qcut(x, 5, labels=False, duplicates='drop') + 1
        if len(x) >= 5 else pd.Series(np.nan, index=x.index))
    ds = ds.dropna(subset=['Q_fi', 'Q_fr'])
    ds['Q_fi'] = ds['Q_fi'].astype(int)
    ds['Q_fr'] = ds['Q_fr'].astype(int)

    hm_data = ds.groupby(['Q_fi', 'Q_fr'])['fwd'].mean().unstack() * 365 * 100
    print("  5x5 Ann. Return (%) [rows=FI, cols=FR]:")
    print(hm_data.round(1).to_string())

    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(hm_data, annot=True, fmt='.1f', cmap='RdYlGn', center=0,
                ax=ax,
                xticklabels=[f'FR Q{i}' for i in sorted(hm_data.columns)],
                yticklabels=[f'FI Q{i}' for i in sorted(hm_data.index)])
    ax.set_xlabel('Funding Rate Quintile')
    ax.set_ylabel('Flow Imbalance Quintile')
    ax.set_title('Double Sort: Annualised Returns (%)')
    plt.tight_layout()
    plt.savefig(FIGS / 'ec5_heatmap.png', bbox_inches='tight')
    plt.close()
    print("    saved ec5_heatmap.png")

    hi = ds[(ds['Q_fi'] == 5) & (ds['Q_fr'] == 5)].groupby('td')['fwd'].mean()
    lo = ds[(ds['Q_fi'] == 1) & (ds['Q_fr'] == 1)].groupby('td')['fwd'].mean()
    common = hi.index.intersection(lo.index)
    ls_corner = hi.loc[common] - lo.loc[common]
    pmf('Corner L/S (55 - 11)', metrics(ls_corner))

    # ══════════════════════════════════════════════════════════════════
    # EC6: ML MODEL
    # ══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  EC6: MACHINE LEARNING MODEL")
    print("=" * 70)
    try:
        import lightgbm as lgb
        USE_LGB = True
        print("  Using LightGBM")
    except (ImportError, OSError):
        from sklearn.ensemble import GradientBoostingRegressor
        USE_LGB = False
        print("  LightGBM unavailable, using sklearn GradientBoosting")

    feats = ['fi', 'ret_1d', 'ret_7d', 'funding_rate_24h', 'log_dv']
    mldf = p.dropna(subset=feats + ['fwd']).copy().sort_values('td')
    for f in feats:
        mldf[f'{f}_rk'] = mldf.groupby('td')[f].rank(pct=True)
    frk = [f'{f}_rk' for f in feats]

    months = sorted(mldf['td'].dt.to_period('M').unique())
    start_idx = min(6, len(months) - 1)
    oos_parts = []
    last_model = None
    for i in range(start_idx, len(months)):
        m = months[i]
        tr = mldf[mldf['td'].dt.to_period('M') < m]
        te = mldf[mldf['td'].dt.to_period('M') == m]
        if len(tr) < 500 or len(te) == 0:
            continue
        if USE_LGB:
            model = lgb.LGBMRegressor(
                n_estimators=200, max_depth=4, learning_rate=0.05,
                subsample=0.8, colsample_bytree=0.8, reg_lambda=1.0,
                verbose=-1)
        else:
            model = GradientBoostingRegressor(
                n_estimators=200, max_depth=4, learning_rate=0.05,
                subsample=0.8)
        model.fit(tr[frk], tr['fwd'])
        te = te.copy()
        te['pred'] = model.predict(te[frk])
        oos_parts.append(te)
        last_model = model

    if oos_parts:
        oos = pd.concat(oos_parts)
        print(f"  OOS: {len(oos):,} rows, {oos['td'].nunique()} days")
        pv_ml, _ = qsort(oos, 'pred')
        pmf('ML L/S', metrics(pv_ml['LS']))
        pmf('Base L/S (recap)', metrics(pv_base['LS']))
        bar_quintile(pv_ml, 'ML Model - Quintile Returns', 'ec6_ml_bar.png')
        pnl_curve(pv_ml, btc, 'ML L/S vs BTC', 'ec6_ml_pnl.png')

        imp = pd.Series(last_model.feature_importances_,
                        index=feats).sort_values()
        fig, ax = plt.subplots(figsize=(7, 4))
        imp.plot.barh(ax=ax, color='steelblue')
        ax.set_title('LightGBM Feature Importance (last fold)')
        ax.set_xlabel('Split Count')
        plt.tight_layout()
        plt.savefig(FIGS / 'ec6_importance.png', bbox_inches='tight')
        plt.close()
        print("    saved ec6_importance.png")
    else:
        print("  No OOS predictions generated.")
        pv_ml = None

    # ══════════════════════════════════════════════════════════════════
    # EC7: WASH TRADING
    # ══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  EC7: WASH TRADING DETECTION")
    print("=" * 70)
    wt = perp.groupby('symbol').agg(
        mean_qv=('quote_volume', 'mean'),
        std_qv=('quote_volume', 'std'),
        mean_tc=('trades_count', 'mean'),
        n=('timestamp', 'count')).reset_index()
    wt['cv'] = wt['std_qv'] / wt['mean_qv']
    wt['vol_per_trade'] = wt['mean_qv'] / wt['mean_tc']

    # Vectorised first-digit extraction for Benford's Law
    pv_temp = perp[['symbol', 'quote_volume']].copy()
    pv_temp = pv_temp[pv_temp['quote_volume'] > 0]
    lv = np.log10(pv_temp['quote_volume'].values)
    fd = np.floor(10 ** (lv - np.floor(lv))).astype(int)
    fd = np.clip(fd, 1, 9)
    pv_temp['fd'] = fd

    expected_benford = pd.Series(
        [np.log10(1 + 1 / d) for d in range(1, 10)], index=range(1, 10))

    def chi2_benford(group):
        if len(group) < 50:
            return np.nan
        obs = group.value_counts(normalize=True).reindex(
            range(1, 10), fill_value=0)
        return float((len(group) * ((obs - expected_benford) ** 2 /
                                     expected_benford)).sum())

    print("  Computing Benford chi-squared per symbol...")
    benford_scores = pv_temp.groupby('symbol')['fd'].apply(chi2_benford)
    wt = wt.merge(benford_scores.rename('benford_chi2'),
                  left_on='symbol', right_index=True, how='left')

    print("\n  Top Benford deviations (most suspicious):")
    for _, r in wt.nlargest(10, 'benford_chi2').iterrows():
        print(f"    {r['symbol']:20s}  chi2={r['benford_chi2']:8.1f}  "
              f"CV={r['cv']:.2f}  $/trade={r['vol_per_trade']:,.0f}")

    print("\n  Lowest volume CV (suspiciously stable):")
    for _, r in wt.nsmallest(10, 'cv').iterrows():
        print(f"    {r['symbol']:20s}  CV={r['cv']:.2f}  "
              f"chi2={r['benford_chi2']:.1f}")
    del pv_temp

    # ══════════════════════════════════════════════════════════════════
    # EC8: MAX DRAWDOWN vs LIQUIDITY
    # ══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  EC8: MAX DRAWDOWN vs LIQUIDITY")
    print("=" * 70)
    avg_dv = daily.groupby('symbol')['dollar_volume'].mean()
    top100_syms = avg_dv.nlargest(100).index
    dd_list = []
    for sym in top100_syms:
        ds2 = daily[daily['symbol'] == sym].sort_values('date')
        pr = ds2['close_utc1'].dropna()
        if len(pr) < 30:
            continue
        pk = pr.cummax()
        mdd = ((pr - pk) / pk).min()
        dd_list.append(dict(symbol=sym, mdd=mdd, avg_dv=avg_dv[sym]))
    ddr = pd.DataFrame(dd_list)

    rho, pval = stats.spearmanr(np.log(ddr['avg_dv']), ddr['mdd'])
    print(f"  Spearman(log vol, max DD) = {rho:.3f}  (p={pval:.4f})")
    print(f"  Avg max drawdown:    {ddr['mdd'].mean()*100:.1f}%")
    print(f"  Median max drawdown: {ddr['mdd'].median()*100:.1f}%")
    worst = ddr.loc[ddr['mdd'].idxmin()]
    print(f"  Worst: {worst['symbol']}  {worst['mdd']*100:.1f}%")

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(np.log10(ddr['avg_dv']), ddr['mdd'] * 100, alpha=.6,
               s=40, c='steelblue')
    z = np.polyfit(np.log10(ddr['avg_dv']), ddr['mdd'] * 100, 1)
    xf = np.linspace(np.log10(ddr['avg_dv']).min(),
                     np.log10(ddr['avg_dv']).max(), 50)
    ax.plot(xf, np.poly1d(z)(xf), 'r--', lw=1.5,
            label=f'rho={rho:.2f}')
    ax.set_xlabel('log10 Avg Daily $ Volume')
    ax.set_ylabel('Max Drawdown (%)')
    ax.set_title('Max Drawdown vs Liquidity - Top 100 Cryptos')
    ax.legend()
    ax.grid(True, alpha=.3)
    plt.tight_layout()
    plt.savefig(FIGS / 'ec8_dd.png', bbox_inches='tight')
    plt.close()
    print("    saved ec8_dd.png")

    # ══════════════════════════════════════════════════════════════════
    # EC9: BTC VOLUME SMILE
    # ══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  EC9: BTC INTRADAY VOLUME SMILE")
    print("=" * 70)
    bh = perp[perp['symbol'] == 'BTCUSDT'].copy()
    bh['h_utc'] = bh['timestamp'].dt.hour
    bh['h_et'] = (bh['h_utc'] - 5) % 24

    vol_utc = bh.groupby('h_utc')['quote_volume'].mean()
    vol_et = bh.groupby('h_et')['quote_volume'].mean().sort_index()

    pk_h = vol_utc.idxmax()
    tr_h = vol_utc.idxmin()
    print(f"  Peak hour (UTC):   {pk_h:02d}:00  ${vol_utc.max()/1e6:.0f}M")
    print(f"  Trough hour (UTC): {tr_h:02d}:00  ${vol_utc.min()/1e6:.0f}M")
    print(f"  Peak/Trough:       {vol_utc.max()/vol_utc.min():.2f}x")

    us_h = list(range(14, 22))
    asia_h = list(range(0, 8))
    euro_h = list(range(7, 16))
    total_v = bh['quote_volume'].sum()
    print(f"\n  Volume share by session:")
    print(f"    US    (UTC 14-21): "
          f"{bh[bh['h_utc'].isin(us_h)]['quote_volume'].sum()/total_v:.1%}")
    print(f"    Asia  (UTC 0-7):   "
          f"{bh[bh['h_utc'].isin(asia_h)]['quote_volume'].sum()/total_v:.1%}")
    print(f"    Europe(UTC 7-15):  "
          f"{bh[bh['h_utc'].isin(euro_h)]['quote_volume'].sum()/total_v:.1%}")

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 5))
    a1.bar(vol_utc.index, vol_utc / 1e6, color='steelblue',
           edgecolor='k', lw=.4)
    a1.set_xlabel('Hour (UTC)')
    a1.set_ylabel('Avg Volume ($M)')
    a1.set_title('BTC Hourly Volume - UTC')
    a1.set_xticks(range(0, 24, 2))

    a2.bar(vol_et.index, vol_et / 1e6, color='coral', edgecolor='k', lw=.4)
    a2.axvspan(9.5, 16, alpha=.12, color='green', label='US Equity Hours')
    a2.set_xlabel('Hour (US Eastern)')
    a2.set_ylabel('Avg Volume ($M)')
    a2.set_title('BTC Hourly Volume - Eastern')
    a2.set_xticks(range(0, 24, 2))
    a2.legend()
    plt.tight_layout()
    plt.savefig(FIGS / 'ec9_smile.png', bbox_inches='tight')
    plt.close()
    print("    saved ec9_smile.png")

    print("\n" + "=" * 70)
    print("  ALL DONE - figures saved to figures/")
    print("=" * 70)


if __name__ == '__main__':
    main()
