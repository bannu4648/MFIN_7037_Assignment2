import pandas as pd
import numpy as np

try:
    from statsmodels.api import OLS, add_constant
    HAS_STATS = True
except ImportError:
    HAS_STATS = False


def btc_alpha(ls_returns, btc_returns):
    common = ls_returns.index.intersection(btc_returns.index)
    if len(common) < 10:
        return dict(alpha=np.nan, beta=np.nan, alpha_ann=np.nan, t_alpha=np.nan, r2=np.nan)
    y = ls_returns.loc[common].values
    x = btc_returns.loc[common].values
    if not HAS_STATS:
        # Fallback: numpy OLS
        x_const = np.column_stack([np.ones(len(x)), x])
        b = np.linalg.lstsq(x_const, y, rcond=None)[0]
        alpha, beta = b[0], b[1]
        pred = x_const @ b
        res = y - pred
        r2 = 1 - (res.var() / y.var()) if y.var() > 0 else np.nan
        se = np.sqrt(np.diag(np.linalg.pinv(x_const.T @ x_const)) * (res @ res) / (len(y) - 2))
        t_alpha = alpha / se[0] if se[0] > 0 else np.nan
        return dict(
            alpha=alpha,
            beta=beta,
            alpha_ann=alpha * 365,
            t_alpha=t_alpha,
            r2=r2,
        )
    x_const = add_constant(pd.Series(x, index=common))
    model = OLS(y, x_const).fit()
    return dict(
        alpha=model.params.iloc[0],
        beta=model.params.iloc[1],
        alpha_ann=model.params.iloc[0] * 365,
        t_alpha=model.tvalues.iloc[0],
        r2=model.rsquared,
    )


# One-line message printed by Q3/Q4 to explain why we use crypto proxy instead of FF5.
FACTOR_METHODOLOGY_MSG = (
    "\nFactor methodology:\n"
    "  The assignment does not provide Fama-French factor data, and standard FF5 + MOM factors "
    "(SMB, HML, RMW, CMA, MOM) are constructed from equity markets and carry no direct meaning "
    "in crypto asset markets. We therefore do not run a traditional FF5 regression. Instead, we "
    "use a crypto-native proxy factor regression — regressing L/S returns on BTC, ETH, and an "
    "equal-weighted market return across the top-100 universe — as the appropriate analogue for "
    "factor exposure analysis."
)


def crypto_proxy_alpha(ls_returns, btc_returns, eth_returns, mkt_returns):
    if not HAS_STATS:
        # statsmodels should be available via requirements, but fall back gracefully.
        return dict(
            alpha=np.nan,
            alpha_ann=np.nan,
            betas={},
            t_alpha=np.nan,
            r2=np.nan,
        )

    common = (
        ls_returns.index
        .intersection(btc_returns.index)
        .intersection(eth_returns.index)
        .intersection(mkt_returns.index)
    )
    if len(common) < 30:
        return dict(
            alpha=np.nan,
            alpha_ann=np.nan,
            betas={},
            t_alpha=np.nan,
            r2=np.nan,
        )

    y = ls_returns.loc[common]
    x = pd.DataFrame(
        {
            "BTC": btc_returns.loc[common],
            "ETH": eth_returns.loc[common],
            "MktRF": mkt_returns.loc[common],
        }
    )
    x_const = add_constant(x)
    model = OLS(y, x_const).fit()
    betas = model.params.iloc[1:].to_dict()
    return dict(
        alpha=model.params.iloc[0],
        alpha_ann=model.params.iloc[0] * 365,
        betas=betas,
        t_alpha=model.tvalues.iloc[0],
        r2=model.rsquared,
    )


def print_proxy_results(proxy_res, interpretation):
    """Print crypto proxy regression stats and a one-line interpretation (used by Q3 and Q4)."""
    print(
        f"  Alpha (daily): {proxy_res['alpha']:.6f}  Alpha (ann.): {proxy_res['alpha_ann']*100:+.2f}%  "
        f"R2: {proxy_res.get('r2', 'n/a')}"
    )
    betas = proxy_res.get("betas", {})
    print(
        "  Betas: "
        f"BTC={betas.get('BTC', float('nan')):.3f}, "
        f"ETH={betas.get('ETH', float('nan')):.3f}, "
        f"MktRF={betas.get('MktRF', float('nan')):.3f}"
    )
    print(f"  Interpretation: {interpretation}")
