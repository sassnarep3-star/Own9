"""Game-level and strategy-level correlation estimates (regular season, verified scores)."""
import itertools
import numpy as np
import pandas as pd
from . import config as C


def fisher_ci(r, n):
    if n <= 3 or not np.isfinite(r):
        return [None, None]
    z, se = np.arctanh(np.clip(r, -0.999999, 0.999999)), 1 / np.sqrt(n - 3)
    return [float(np.tanh(z - 1.96 * se)), float(np.tanh(z + 1.96 * se))]


def corr_row(name, x, y, period, note=""):
    m = pd.notna(x) & pd.notna(y)
    x, y = np.asarray(x[m], float), np.asarray(y[m], float)
    r = float(np.corrcoef(x, y)[0, 1]) if len(x) > 2 else np.nan
    return {"measure": name, "period": period, "n": int(len(x)), "r": r, "ci95": fisher_ci(r, len(x)), "note": note}


def game_level(base, preds):
    g = base.merge(preds[["game_id"]], on="game_id")
    g = g[g.spread_line.notna() & g.total_line.notna()].copy()
    g["fav_margin"] = np.where(g.spread_line >= 0, g.result, -g.result)
    g["fav_line"] = g.spread_line.abs()
    g["fav_cover"] = np.sign(g.fav_margin - g.fav_line)
    g["over"] = np.sign(g.total - g.total_line)
    rows = []
    for per, sel in (("DEV 2010-2019", g.period == "DEV"), ("OOS 2020-2026", g.period != "DEV"), ("ALL 2010-2026", g.period.notna())):
        d = g[sel]
        rows.append(corr_row("Originated spread vs closing spread", d.spread_hat, d.spread_line, per, "model vs market (market unverified)"))
        rows.append(corr_row("Originated total vs closing total", d.total_hat, d.total_line, per, "model vs market (market unverified)"))
        rows.append(corr_row("Closing spread vs actual home margin", d.spread_line, d.result, per))
        rows.append(corr_row("Originated spread vs actual home margin", d.spread_hat, d.result, per))
        rows.append(corr_row("Closing total vs actual total", d.total_line, d.total, per))
        rows.append(corr_row("Originated total vs actual total", d.total_hat, d.total, per))
        rows.append(corr_row("Model edge (spread_hat - close) vs ATS residual (margin - close)",
                             d.spread_hat - d.spread_line, d.result - d.spread_line, per,
                             "positive would mean the model adds information beyond the close"))
        rows.append(corr_row("Model edge (total_hat - close) vs totals residual (total - close)",
                             d.total_hat - d.total_line, d.total - d.total_line, per))
    # side-total correlation (phi) by favourite size, pushes excluded
    phis = []
    buckets = [("All", 0, 99), ("Fav 0-2.5", 0, 2.5), ("Fav 3-6.5", 3, 6.5), ("Fav 7-9.5", 7, 9.5), ("Fav 10+", 10, 99)]
    for per, sel in (("ALL 2010-2026", g.period.notna()), ("OOS 2020-2026", g.period != "DEV")):
        for name, lo, hi in buckets:
            d = g[sel & g.fav_line.between(lo, hi) & (g.fav_cover != 0) & (g.over != 0)]
            a, b = (d.fav_cover > 0).astype(float), (d.over > 0).astype(float)
            r = float(np.corrcoef(a, b)[0, 1]) if len(d) > 2 else np.nan
            pj = float(((a == 1) & (b == 1)).mean())
            phis.append({"bucket": name, "period": per, "n": int(len(d)), "phi_fav_cover_vs_over": r,
                         "ci95": fisher_ci(r, len(d)), "p_fav_cover": float(a.mean()), "p_over": float(b.mean()),
                         "p_fav_cover_and_over": pj, "p_dog_cover_and_under": float(((a == 0) & (b == 0)).mean())})
    # same-week cross-game correlation of home-cover outcomes
    pairs_x, pairs_y = [], []
    cov = np.sign(g.result - g.spread_line)
    g2 = g.assign(hc=cov)[cov != 0]
    for _, grp in g2.groupby(["season", "week"]):
        v = (grp.hc > 0).astype(float).to_numpy()
        for i, j in itertools.permutations(range(len(v)), 2):
            pairs_x.append(v[i]); pairs_y.append(v[j])
    r_cross = float(np.corrcoef(pairs_x, pairs_y)[0, 1])
    n_games = int(len(g2))
    cross = {"measure": "Same-week cross-game correlation of home-cover outcomes (all ordered pairs)",
             "r": r_cross, "n_ordered_pairs": len(pairs_x), "n_games": n_games,
             "note": "near zero supports pricing cross-game parlays as independent legs"}
    return rows, phis, cross


def strategy_matrix(bets):
    oos = bets[bets.period != "DEV"]
    wk = oos.season.astype(str) + "-" + oos.week.astype(str).str.zfill(2)
    m = oos.assign(wk=wk).groupby(["wk", "strategy"]).profit.sum().unstack().fillna(0.0)
    c = m.corr()
    pairs = []
    for a, b in itertools.combinations(c.columns, 2):
        pairs.append({"a": a, "b": b, "r_weekly_pnl": float(c.loc[a, b])})
    pairs.sort(key=lambda x: -abs(x["r_weekly_pnl"]))
    return {"columns": list(c.columns), "matrix": c.round(3).values.tolist(), "top_pairs": pairs[:15],
            "n_weeks": int(len(m))}
