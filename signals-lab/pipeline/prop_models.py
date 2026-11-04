"""EF-4: player-prop line origination (quantile forecasts) with walk-forward training windows.

Markets (all outcomes are the parsed NFL game-center feed, reconciled to NFL.com leader tables for 2025 top-25 only -> flagged "sample-verified"):
  PASS_YDS   passing yards       (QB: trailing mean attempts >= 18)
  RUSH_YDS   rushing yards       (trailing mean rush attempts >= 8)
  REC_YDS    receiving yards     (trailing mean targets >= 4)
  RECEPTIONS receptions          (same population as REC_YDS)
Population caveat (flagged on the site): the feed has no inactive/DNP list, so a player is evaluated only in games where he recorded
at least the minimum "appearance" volume; zero-usage active games are therefore invisible (conditional-on-appearing definition).

Models (same rows for all, pre-registered):
  PR0  trailing mean of last 6 appearances x empirical ratio-quantiles (naive baseline)
  PR1  empirical-Bayes shrunk EWMA toward a usage-based prior x empirical ratio-quantiles
  PR2  gradient-boosted quantile regression (sklearn HistGradientBoosting) with usage, form, opponent, pace, implied team points
Score: mean pinball loss over tau in {.1,.25,.5,.75,.9}; skill = 1 - loss/loss(PR0); game-clustered bootstrap.
"""
from __future__ import annotations

import itertools
import json
import sys
import time
import warnings

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.ensemble import HistGradientBoostingRegressor

from common import BURN, DEV, TEST, load_games, pinball, verified_seasons
from config import DERIVED, REGISTRY, RESULTS
import game_models as gm

warnings.filterwarnings("ignore")
TAUS = [0.1, 0.25, 0.5, 0.75, 0.9]
GRID = np.round(np.arange(0.01, 1.0, 0.01), 2)
MARKETS = {
    "PASS_YDS": dict(y="pass_yds", usage="pass_att", min_app=10, elig=18.0, allowed="pass_yds"),
    "RUSH_YDS": dict(y="rush_yds", usage="rush_att", min_app=3, elig=8.0, allowed="rush_yds"),
    "REC_YDS": dict(y="rec_yds", usage="targets", min_app=1, elig=4.0, allowed="pass_yds"),
    "RECEPTIONS": dict(y="rec", usage="targets", min_app=1, elig=4.0, allowed="pass_yds"),
}
FEATS = ["n_prev", "mean6", "ewma3", "sd6", "last", "gap", "season_mean", "usage6", "itp", "mp", "opp_allowed", "pace", "home"]
PDEF = dict(ewma_hl=3.0, shrink_k=2.0, gbm=dict(max_depth=3, max_iter=150, learning_rate=0.05, min_samples_leaf=40))


def team_context(max_season: int, P: dict) -> pd.DataFrame:
    """Pre-game implied team points / margin from the (walk-forward) G3 model, one row per game and team."""
    g = load_games(include_2026=False, max_season=max_season)
    r = gm.run_walkforward(g, P, components=("ridge",))
    r = r[["game_id", "home", "away", "G3_margin", "G3_total"]].copy()
    h = pd.DataFrame(dict(game_id=r.game_id, team=r.home, itp=(r.G3_total + r.G3_margin) / 2, mp=r.G3_margin))
    a = pd.DataFrame(dict(game_id=r.game_id, team=r.away, itp=(r.G3_total - r.G3_margin) / 2, mp=-r.G3_margin))
    return pd.concat([h, a], ignore_index=True)


def _team_trailing() -> pd.DataFrame:
    tg = pd.read_csv(DERIVED / "team_games_feed.csv.gz")
    tg = tg[tg.game_type == "REG"].copy()
    d = load_games(include_2026=False)[["game_id", "date"]]
    tg = tg.merge(d, on="game_id")
    opp = tg[["game_id", "team", "pass_yds", "rush_yds"]].rename(columns={"team": "opp", "pass_yds": "allowed_pass_yds", "rush_yds": "allowed_rush_yds"})
    tg = tg.merge(opp, on=["game_id", "opp"], how="left").sort_values(["team", "date"])
    tg["plays"] = tg.pass_att + tg.rush_att
    gb = tg.groupby("team")
    for c in ["allowed_pass_yds", "allowed_rush_yds", "plays"]:
        tg[c + "_tr"] = gb[c].transform(lambda s: s.shift(1).rolling(8, min_periods=3).mean())
    return tg[["game_id", "team", "allowed_pass_yds_tr", "allowed_rush_yds_tr", "plays_tr"]]


def build_market(name: str, players: pd.DataFrame, ctx: pd.DataFrame, trailing: pd.DataFrame, hl: float) -> pd.DataFrame:
    mk = MARKETS[name]; y = mk["y"]
    d = players[players[mk["usage"]] >= mk["min_app"]].copy().sort_values(["gsis_id", "date"])
    gb = d.groupby("gsis_id")
    d["n_prev"] = gb.cumcount()
    d["last"] = gb[y].shift(1)
    d["gap"] = (d.date - gb.date.shift(1)).dt.days
    d["mean6"] = gb[y].transform(lambda s: s.shift(1).rolling(6, min_periods=1).mean())
    d["sd6"] = gb[y].transform(lambda s: s.shift(1).rolling(6, min_periods=3).std())
    d["ewma3"] = gb[y].transform(lambda s: s.shift(1).ewm(halflife=hl, adjust=True).mean())
    d["usage6"] = gb[mk["usage"]].transform(lambda s: s.shift(1).rolling(6, min_periods=1).mean())
    d["season_mean"] = d.groupby(["gsis_id", "season"])[y].transform(lambda s: s.shift(1).expanding().mean())
    d = d.merge(ctx, on=["game_id", "team"], how="left")
    t = trailing.rename(columns={"team": "opp"})
    d = d.merge(t[["game_id", "opp", f"allowed_{mk['allowed']}_tr"]], on=["game_id", "opp"], how="left").rename(columns={f"allowed_{mk['allowed']}_tr": "opp_allowed"})
    d = d.merge(trailing.rename(columns={"team": "team"})[["game_id", "team", "plays_tr"]], on=["game_id", "team"], how="left").rename(columns={"plays_tr": "pace"})
    d["home"] = d.home.astype(float)
    d["y"] = d[y]; d["market"] = name
    d["eligible"] = (d.n_prev >= 3) & (d.usage6 >= mk["elig"]) & d.mean6.notna()
    return d


def _ratio_q(y, base):
    ok = base > 0.5
    r = np.clip(y[ok] / base[ok], 0, 6)
    return np.sort(r)


def _quantiles(base, rsorted, taus):
    qs = np.quantile(rsorted, taus)
    return np.outer(np.maximum(base, 0.5), qs)


def _pit(y, base, rsorted):
    r = np.clip(y / np.maximum(base, 0.5), 0, 6)
    lo = np.searchsorted(rsorted, r, "left"); hi = np.searchsorted(rsorted, r, "right")
    return (lo + hi) / 2 / len(rsorted)


def fit_predict(train: pd.DataFrame, test: pd.DataFrame, P: dict, run_gbm: bool = True) -> pd.DataFrame:
    """Fit PR0/PR1/PR2 on `train` rows and predict quantiles for `test` rows (no test information is used)."""
    out = test[["market", "game_id", "season", "week", "gsis_id", "name", "team", "opp", "home", "y"]].copy()
    # PR0
    r0 = _ratio_q(train.y.to_numpy(), train.mean6.to_numpy())
    b0 = test.mean6.to_numpy(); q0 = _quantiles(b0, r0, TAUS)
    # PR1
    k = P["shrink_k"]
    A = np.c_[np.ones(len(train)), train.usage6]; coef = np.linalg.lstsq(A, train.y.to_numpy(), rcond=None)[0]
    prior = lambda df: coef[0] + coef[1] * df.usage6.to_numpy()
    def b1_of(df):
        ne = np.minimum(df.n_prev.to_numpy(), 8.0)
        return (ne * df.ewma3.fillna(df.mean6).to_numpy() + k * prior(df)) / (ne + k)
    r1 = _ratio_q(train.y.to_numpy(), b1_of(train)); b1 = b1_of(test); q1 = _quantiles(b1, r1, TAUS)
    out["base0"] = b0; out["base1"] = b1
    out["pit1"] = _pit(test.y.to_numpy(), b1, r1)
    out["pit0"] = _pit(test.y.to_numpy(), b0, r0)
    for j, t in enumerate(TAUS):
        out[f"PR0_q{int(t*100)}"] = q0[:, j]; out[f"PR1_q{int(t*100)}"] = q1[:, j]
    # PR2
    if run_gbm:
        Q = np.zeros((len(test), len(TAUS)))
        for j, t in enumerate(TAUS):
            m = HistGradientBoostingRegressor(loss="quantile", quantile=t, l2_regularization=1.0, random_state=0, **P["gbm"])
            m.fit(train[FEATS], train.y)
            Q[:, j] = m.predict(test[FEATS])
        Q = np.sort(np.maximum(Q, 0), axis=1)
        for j, t in enumerate(TAUS): out[f"PR2_q{int(t*100)}"] = Q[:, j]
    return out


def prepare(max_season: int, P_game: dict, hl: float) -> dict[str, pd.DataFrame]:
    ok = verified_seasons()
    pl = pd.read_csv(DERIVED / "player_games_feed.csv.gz")
    pl = pl[(pl.game_type == "REG") & pl.season.isin(ok) & (pl.season <= max_season)]
    g = load_games(include_2026=False, max_season=max_season)[["game_id", "date"]]
    pl = pl.merge(g, on="game_id")
    pl = pl.groupby(["game_id", "gsis_id"], as_index=False).agg(dict(season="first", week="first", name="first", team="first", opp="first", home="first", date="first",
                                                                       pass_att="sum", pass_yds="sum", rush_att="sum", rush_yds="sum", targets="sum", rec="sum", rec_yds="sum"))
    ctx = team_context(max_season, P_game); trailing = _team_trailing()
    return {m: build_market(m, pl, ctx, trailing, hl) for m in MARKETS}


def score_table(pred: pd.DataFrame, models=("PR0", "PR1", "PR2")) -> pd.DataFrame:
    rows = []
    for mk, d in pred.groupby("market"):
        for m in models:
            if f"{m}_q50" not in d: continue
            pl = np.mean([pinball(d.y, d[f"{m}_q{int(t*100)}"], t) for t in TAUS], axis=0)
            rows.append(dict(market=mk, model=m, n=len(d), pinball=float(pl.mean())))
    t = pd.DataFrame(rows)
    base = t[t.model == "PR0"].set_index("market").pinball
    t["skill_vs_PR0"] = 1 - t.pinball / t.market.map(base)
    return t


def tune_dev(P_game: dict) -> dict:
    """Select PR1 / PR2 settings on DEV seasons only (expanding windows; rows from 2023+ are never loaded)."""
    best = json.loads(json.dumps(PDEF)); log = []
    for hl in [3.0, 5.0, 8.0, 12.0]:
        D = prepare(max(DEV), P_game, hl)
        for kk in [1.0, 2.0, 4.0]:
            P = json.loads(json.dumps(PDEF)); P["ewma_hl"] = hl; P["shrink_k"] = kk
            res = []
            for s in DEV:
                for m, d in D.items():
                    tr = d[(d.season < s) & d.eligible]; te = d[(d.season == s) & d.eligible]
                    res.append(fit_predict(tr, te, P, run_gbm=False))
            sc = score_table(pd.concat(res), models=("PR0", "PR1"))
            pr1 = sc[sc.model == "PR1"].skill_vs_PR0.mean()
            log.append(dict(model="PR1", ewma_hl=hl, shrink_k=kk, dev_mean_skill=float(pr1)))
    t = pd.DataFrame(log).sort_values("dev_mean_skill", ascending=False)
    best["ewma_hl"] = float(t.iloc[0].ewma_hl); best["shrink_k"] = float(t.iloc[0].shrink_k)
    D = prepare(max(DEV), P_game, best["ewma_hl"])
    for depth, iters in [(2, 150), (3, 150), (3, 300)]:
        P = json.loads(json.dumps(best)); P["gbm"] = dict(max_depth=depth, max_iter=iters, learning_rate=0.05, min_samples_leaf=40)
        res = []
        for s in DEV:
            for m, d in D.items():
                tr = d[(d.season < s) & d.eligible]; te = d[(d.season == s) & d.eligible]
                res.append(fit_predict(tr, te, P, run_gbm=True))
        sc = score_table(pd.concat(res), models=("PR0", "PR2"))
        log.append(dict(model="PR2", max_depth=depth, max_iter=iters, dev_mean_skill=float(sc[sc.model == "PR2"].skill_vs_PR0.mean())))
    lg = pd.DataFrame(log); lg.to_csv(RESULTS / "prop_tuning_dev_grid.csv", index=False)
    g2 = lg[lg.model == "PR2"].sort_values("dev_mean_skill", ascending=False).iloc[0]
    best["gbm"] = dict(max_depth=int(g2.max_depth), max_iter=int(g2.max_iter), learning_rate=0.05, min_samples_leaf=40)
    best["_selected_on"] = f"seasons {DEV[0]}-{DEV[-1]} only (expanding windows); 2023+ never loaded"
    return best


def final_run(P_game: dict, P: dict, dev_only: bool = False) -> pd.DataFrame:
    """Dev seasons: expanding windows. Sealed seasons 2023-2025: ONE fit on seasons <= 2022."""
    D = prepare(max(DEV) if dev_only else max(TEST), P_game, P["ewma_hl"])
    res = []
    for m, d in D.items():
        for s in DEV:
            tr = d[(d.season < s) & d.eligible]; te = d[(d.season == s) & d.eligible]
            r = fit_predict(tr, te, P, run_gbm=True); r["split"] = "dev"; res.append(r)
        if dev_only: continue
        tr = d[(d.season <= max(DEV)) & d.eligible]; te = d[d.season.isin(TEST) & d.eligible]
        r = fit_predict(tr, te, P, run_gbm=True); r["split"] = "test"; res.append(r)
    return pd.concat(res, ignore_index=True)


if __name__ == "__main__":
    RESULTS.mkdir(parents=True, exist_ok=True)
    hp = json.loads((REGISTRY / "hyperparameters.json").read_text())
    t0 = time.time()
    if len(sys.argv) > 1 and sys.argv[1] == "tune":
        best = tune_dev(hp)
        hp["props"] = best
        (REGISTRY / "hyperparameters.json").write_text(json.dumps(hp, indent=1))
        print(json.dumps(best, indent=1)); print("tuned in", round(time.time() - t0), "s")
    else:
        dev_only = len(sys.argv) > 1 and sys.argv[1] == "dev"
        pred = final_run(hp, hp["props"], dev_only=dev_only)
        dest = RESULTS / ("_dev_only" if dev_only else ""); dest.mkdir(parents=True, exist_ok=True)
        pred.to_csv(dest / "prop_predictions.csv.gz", index=False)
        print("wrote prop_predictions", pred.shape, "->", dest.name or "results", "in", round(time.time() - t0), "s")
