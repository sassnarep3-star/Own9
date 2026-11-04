"""Resampling statistics used by the validation gates and luck analysis.

All bootstraps resample whole (season, week) blocks, because bets in the same week share
information (same slate, same market moves) and multi-leg bets span games of one week.
A single synchronized set of week resamples is used for every strategy, so the max-T
reality check (Romano-Wolf single step / White's reality check) respects the dependence
between strategies.
"""
import numpy as np
import pandas as pd
from scipy.stats import spearmanr


def week_matrix(bets, keys, profit_col="profit"):
    """Per-strategy per-week profit sums S and bet counts N (K x W)."""
    wk = bets.season.astype(str) + "-" + bets.week.astype(int).astype(str).str.zfill(2)
    weeks = np.sort(wk.unique())
    wi = {w: i for i, w in enumerate(weeks)}
    S = np.zeros((len(keys), len(weeks)))
    N = np.zeros((len(keys), len(weeks)))
    ki = {k: i for i, k in enumerate(keys)}
    for (k, w), grp in bets.assign(_wk=wk).groupby(["strategy", "_wk"]):
        if k in ki:
            S[ki[k], wi[w]] = grp[profit_col].sum()
            N[ki[k], wi[w]] = len(grp)
    return S, N, weeks


def sync_bootstrap(S, N, n_boot, seed):
    rng = np.random.default_rng(seed)
    W = S.shape[1]
    Cm = rng.multinomial(W, np.full(W, 1.0 / W), size=n_boot).astype(float)  # B x W
    num = Cm @ S.T
    den = Cm @ N.T
    with np.errstate(invalid="ignore", divide="ignore"):
        roi = num / den
    return roi  # B x K (nan if a replicate drew no bets for a strategy)


def inference(S, N, n_boot, seed):
    roi_obs = S.sum(1) / N.sum(1)
    boot = sync_bootstrap(S, N, n_boot, seed)
    se = np.nanstd(boot, axis=0, ddof=1)
    lcb = np.nanpercentile(boot, 5, axis=0)
    cen = boot - roi_obs  # centered: null of zero expected profit
    p = (np.sum(cen >= roi_obs, axis=0) + 1) / (np.sum(~np.isnan(cen), axis=0) + 1)
    t_obs = roi_obs / se
    tmax = np.nanmax(cen / se, axis=1)
    p_maxt = np.array([(np.sum(tmax >= t) + 1) / (len(tmax) + 1) for t in t_obs])
    return pd.DataFrame({"roi": roi_obs, "se": se, "lcb95": lcb, "p": p, "t": t_obs, "p_maxT": p_maxt})


def holm(p):
    p = np.asarray(p, float)
    order = np.argsort(p)
    m = len(p)
    adj = np.empty(m)
    run = 0.0
    for rank, i in enumerate(order):
        run = max(run, (m - rank) * p[i])
        adj[i] = min(1.0, run)
    return adj


def bh(p):
    p = np.asarray(p, float)
    m = len(p)
    order = np.argsort(p)
    adj = np.empty(m)
    prev = 1.0
    for rank in range(m - 1, -1, -1):
        i = order[rank]
        prev = min(prev, p[i] * m / (rank + 1))
        adj[i] = prev
    return adj


def random_side_null(own_profit, opp_profit, n_sim, seed):
    """ROI distribution when each bet's side is chosen by a fair coin (same games, real prices)."""
    rng = np.random.default_rng(seed)
    pick = rng.random((n_sim, len(own_profit))) < 0.5
    sims = np.where(pick, own_profit[None, :], opp_profit[None, :]).mean(1)
    return sims


def reliability(rois, ses):
    """Share of cross-strategy ROI dispersion explained by sampling noise (luck)."""
    rois, ses = np.asarray(rois), np.asarray(ses)
    var_obs = np.var(rois, ddof=1)
    var_noise = np.mean(ses ** 2)
    luck_share = float(min(1.0, var_noise / var_obs)) if var_obs > 0 else 1.0
    rel = max(0.0, 1 - var_noise / var_obs) if var_obs > 0 else 0.0
    return {"var_observed": float(var_obs), "var_noise": float(var_noise), "luck_share": luck_share,
            "reliability": float(rel), "shrunk": (np.mean(rois) + rel * (rois - np.mean(rois))).tolist()}


def spearman(a, b):
    r = spearmanr(a, b)
    return float(r.statistic), float(r.pvalue)
