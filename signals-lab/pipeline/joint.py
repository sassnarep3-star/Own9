"""EF-5: correlation values and joint (parlay / prop-combo) pricing.

Everything is defined on *own-model* z-scores so that the correlation is between surprises, not between levels:
  prop z  = Phi^-1(PIT of the outcome under the PR1 predictive distribution)           (mid-rank PIT, clipped to [.001,.999])
  game z  = (actual - G3 prediction) / sigma_dev      (margin from the team's perspective; total from the game's)
Pairs (one observation per team-game or game):
  QB_x_REC1 / QB_x_REC2 / QB_x_RB1 / REC1_x_REC2 / MARGIN_x_QB / TOTAL_x_QB / MARGIN_x_RB1 / QB_x_QB_opp / MARGIN_x_TOTAL
  CROSSGAME: margin z of two *different* games in the same week (placebo: parlay legs from different games should be independent)
REC1/REC2/RB1 are chosen pre-game: highest-projected (PR1 base) receiver / non-QB rusher of that team among players who appeared.
Pricing test ("both legs beat their own median"): independence p = pA*pB (marginal rates from earlier seasons) vs Gaussian copula with
rho estimated on earlier seasons only; scored by joint log loss on the evaluation seasons.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import multivariate_normal, norm

from common import DEV, TEST, cluster_boot_skill, logloss
from config import RESULTS

PAIRS = ["QB_x_REC1", "QB_x_REC2", "QB_x_RB1", "REC1_x_REC2", "MARGIN_x_QB", "TOTAL_x_QB", "MARGIN_x_RB1", "QB_x_QB_opp", "MARGIN_x_TOTAL"]
ZC = 0.001


def _z(p):
    return norm.ppf(np.clip(p, ZC, 1 - ZC))


def build_pairs(game_pred: pd.DataFrame, prop_pred: pd.DataFrame) -> pd.DataFrame:
    """Long table: pair, season, split, game_id, z1, z2 (one row per observation)."""
    gp = game_pred[game_pred.G3_margin.notna() & game_pred.margin.notna() & game_pred.season.between(2018, 2025)].copy()
    sig_m = (gp[gp.split == "dev"].margin - gp[gp.split == "dev"].G3_margin).std()
    sig_t = (gp[gp.split == "dev"].total - gp[gp.split == "dev"].G3_total).std()
    gp["zm_home"] = (gp.margin - gp.G3_margin) / sig_m
    gp["zt"] = (gp.total - gp.G3_total) / sig_t
    P = prop_pred.copy(); P["z"] = _z(P.pit1)
    qb = P[P.market == "PASS_YDS"].sort_values("base1", ascending=False).drop_duplicates(["game_id", "team"])[["game_id", "team", "z"]].rename(columns={"z": "z_qb"})
    qb_ids = set(zip(P[P.market == "PASS_YDS"].game_id, P[P.market == "PASS_YDS"].gsis_id))
    rec = P[P.market == "REC_YDS"].sort_values(["game_id", "team", "base1"], ascending=[True, True, False]).copy()
    rec["rk"] = rec.groupby(["game_id", "team"]).cumcount() + 1
    rb = P[P.market == "RUSH_YDS"].copy()
    rb = rb[[(g, i) not in qb_ids for g, i in zip(rb.game_id, rb.gsis_id)]].sort_values("base1", ascending=False).drop_duplicates(["game_id", "team"])[["game_id", "team", "z"]].rename(columns={"z": "z_rb"})
    side = pd.concat([gp[["game_id", "season", "split", "home"]].rename(columns={"home": "team"}).assign(zm=gp.zm_home, zt=gp.zt),
                      gp[["game_id", "season", "split", "away"]].rename(columns={"away": "team"}).assign(zm=-gp.zm_home, zt=gp.zt)])
    side = side.merge(qb, on=["game_id", "team"], how="left").merge(rb, on=["game_id", "team"], how="left")
    for k in (1, 2):
        side = side.merge(rec[rec.rk == k][["game_id", "team", "z"]].rename(columns={"z": f"z_rec{k}"}), on=["game_id", "team"], how="left")
    out = []
    def add(name, a, b, df):
        d = df[[a, b, "game_id", "season", "split"]].dropna().rename(columns={a: "z1", b: "z2"}); d["pair"] = name; out.append(d)
    add("QB_x_REC1", "z_qb", "z_rec1", side); add("QB_x_REC2", "z_qb", "z_rec2", side); add("QB_x_RB1", "z_qb", "z_rb", side)
    add("REC1_x_REC2", "z_rec1", "z_rec2", side); add("MARGIN_x_QB", "zm", "z_qb", side); add("TOTAL_x_QB", "zt", "z_qb", side); add("MARGIN_x_RB1", "zm", "z_rb", side)
    # opposing QBs: one row per game (home QB vs away QB)
    q = side[["game_id", "season", "split", "team", "z_qb"]].dropna()
    h = gp[["game_id", "home"]].rename(columns={"home": "team"}).merge(q, on=["game_id", "team"]).rename(columns={"z_qb": "z1"})
    a = gp[["game_id", "away"]].rename(columns={"away": "team"}).merge(q[["game_id", "team", "z_qb"]], on=["game_id", "team"]).rename(columns={"z_qb": "z2"})
    d = h.merge(a[["game_id", "z2"]], on="game_id")[["z1", "z2", "game_id", "season", "split"]]; d["pair"] = "QB_x_QB_opp"; out.append(d)
    d = gp[["zm_home", "zt", "game_id", "season", "split"]].rename(columns={"zm_home": "z1", "zt": "z2"}); d["pair"] = "MARGIN_x_TOTAL"; out.append(d)
    pairs = pd.concat(out, ignore_index=True)
    # placebo: two different games in the same season-week
    rng = np.random.default_rng(7); rows = []
    for (s, w), d in gp.groupby(["season", "week"]):
        if len(d) < 2: continue
        perm = rng.permutation(len(d))
        for i, j in enumerate(perm):
            if i != j: rows.append((d.zm_home.iat[i], d.zm_home.iat[j], d.game_id.iat[i], s, d.split.iat[i], "CROSSGAME"))
    pairs = pd.concat([pairs, pd.DataFrame(rows, columns=["z1", "z2", "game_id", "season", "split", "pair"])], ignore_index=True)
    pairs.attrs["sigmas"] = dict(margin=float(sig_m), total=float(sig_t))
    return pairs


def corr_ci(d: pd.DataFrame, B: int = 1000, seed: int = 3):
    """Pearson correlation with a game-clustered bootstrap CI."""
    if len(d) < 30: return np.nan, np.nan, np.nan
    codes, uniq = pd.factorize(d.game_id)
    C = len(uniq); x = d.z1.to_numpy(); y = d.z2.to_numpy()
    sx = np.bincount(codes, x, C); sy = np.bincount(codes, y, C); sxx = np.bincount(codes, x * x, C); syy = np.bincount(codes, y * y, C); sxy = np.bincount(codes, x * y, C); n = np.bincount(codes, minlength=C).astype(float)
    rng = np.random.default_rng(seed); r = np.empty(B)
    for b0 in range(0, B, 250):
        idx = rng.integers(0, C, size=(min(250, B - b0), C))
        N = n[idx].sum(1); SX = sx[idx].sum(1); SY = sy[idx].sum(1)
        cov = sxy[idx].sum(1) / N - SX / N * SY / N
        r[b0:b0 + 250] = cov / np.sqrt((sxx[idx].sum(1) / N - (SX / N) ** 2) * (syy[idx].sum(1) / N - (SY / N) ** 2))
    pt = float(np.corrcoef(x, y)[0, 1])
    return pt, float(np.percentile(r, 2.5)), float(np.percentile(r, 97.5))


def table_correlations(pairs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name in PAIRS + ["CROSSGAME"]:
        for lab, sel in [("dev 2018-22", pairs.split == "dev"), ("sealed 2023-25", pairs.split == "test")]:
            d = pairs[(pairs.pair == name) & sel]
            r, lo, hi = corr_ci(d)
            rows.append(dict(pair=name, period=lab, n=len(d), rho=r, ci_lo=lo, ci_hi=hi))
    return pd.DataFrame(rows)


def _p_both_over(pa, pb, rho):
    a = norm.ppf(1 - pa); b = norm.ppf(1 - pb)
    if abs(rho) < 1e-9: return pa * pb
    return 1 - norm.cdf(a) - norm.cdf(b) + multivariate_normal(mean=[0, 0], cov=[[1, rho], [rho, 1]]).cdf([a, b])


def pricing_losses(pairs: pd.DataFrame, name: str, eval_seasons: list[int], fit_filter) -> dict:
    """Walk-forward: for each evaluation season, rho and the marginal rates come from earlier seasons only (fit_filter(season) -> bool mask)."""
    d = pairs[pairs.pair == name]
    parts = []
    for s in eval_seasons:
        tr = d[fit_filter(d.season, s)]
        te = d[d.season == s]
        if len(tr) < 100 or len(te) == 0: continue
        pa = float((tr.z1 > 0).mean()); pb = float((tr.z2 > 0).mean()); rho = float(np.corrcoef(tr.z1, tr.z2)[0, 1])
        p_ind = pa * pb; p_cop = float(_p_both_over(pa, pb, rho))
        I = ((te.z1 > 0) & (te.z2 > 0)).astype(float).to_numpy()
        parts.append(pd.DataFrame(dict(season=s, game_id=te.game_id.to_numpy(), I=I, l_ind=logloss(np.full(len(I), p_ind), I), l_cop=logloss(np.full(len(I), p_cop), I), p_cop=p_cop, p_ind=p_ind, rho=rho)))
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
