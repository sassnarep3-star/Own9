"""EF-3: walk-forward game-line origination (win probability, spread/margin, total).

Every prediction for a (season, week) block uses ONLY games from earlier blocks (ratings, regressions, calibration, sigma).
Models
  G0  baseline        home-field-only margin (expanding mean), expanding-mean total
  G1  Elo             538-style Elo with margin-of-victory multiplier; slope to points calibrated on earlier out-of-sample games
  G2  ridge ratings   time-decayed ridge offense/defense ratings on points (margin = difference, total = sum)
  G3  ridge+context   G2 plus rest/bye (margin) and roof/wind/cold (total) corrections fitted on earlier out-of-sample residuals
  G4  ensemble        mean(G1, G3) margin (available for 2026 too)
  G5  process         ridge ratings on yards/play + success rate (turnovers excluded = luck-stripped), mapped to margin by OLS
  G6  blend           mean(G3, G5) margin (needs the play-by-play feed, so not available for 2026)
Hyper-parameters are chosen on DEV seasons only (tune_dev) and then frozen in registry/hyperparameters.json before the sealed run.
"""
from __future__ import annotations

import itertools
import json
import sys
import time

import numpy as np
import pandas as pd
from scipy.stats import norm

from common import BURN, DEV, TEST, FORWARD, load_games, load_team_process
from config import REGISTRY, RESULTS

DEFAULTS = dict(elo=dict(K=20.0, hfa=48.0, regress=0.25), ridge=dict(hl=30.0, lam=30.0), proc=dict(hl=60.0, lam=60.0))
MIN_HIST = 200          # earlier out-of-sample games needed before a calibration/stack is trusted
SIGMA0 = 13.5           # prior margin sd used before MIN_HIST games exist


def _design(hi, ai, neutral, T):
    n = len(hi)
    X = np.zeros((2 * n, 2 + 2 * T))
    X[:, 0] = 1.0
    X[:n, 1] = (~neutral).astype(float)
    r = np.arange(n)
    X[r, 2 + hi] = 1.0; X[r, 2 + T + ai] = 1.0          # home offense, away defense
    X[n + r, 2 + ai] = 1.0; X[n + r, 2 + T + hi] = 1.0  # away offense, home defense
    return X


def _ridge(X, Y, w, lam, T):
    pen = np.r_[0.0, 0.0, np.full(2 * T, lam)]
    Xw = X * w[:, None]
    return np.linalg.solve(X.T @ Xw + np.diag(pen), Xw.T @ Y)


def _ols(F, y, ridge=1e-6):
    F1 = np.c_[np.ones(len(F)), F]
    return np.linalg.solve(F1.T @ F1 + ridge * np.eye(F1.shape[1]), F1.T @ y)


def _apply(beta, F):
    return beta[0] + F @ beta[1:]


def run_walkforward(g: pd.DataFrame, P: dict, components=("elo", "ridge", "proc"), proc: pd.DataFrame | None = None) -> pd.DataFrame:
    """Return one row per game with every model's margin / total / home-win probability (NaN where unavailable)."""
    g = g.reset_index(drop=True)
    teams = sorted(set(g.home) | set(g.away)); T = len(teams); ix = {t: i for i, t in enumerate(teams)}
    hi = g.home.map(ix).to_numpy(); ai = g.away.map(ix).to_numpy(); neu = g.neutral.to_numpy(bool)
    tt = ((g.season - 2015) * 40 + g.week).to_numpy(float)
    pts_h = g.home_score.to_numpy(float); pts_a = g.away_score.to_numpy(float)
    margin = g.margin.to_numpy(float); total = g.total.to_numpy(float)
    played = ~np.isnan(margin)
    if proc is not None and "proc" in components:
        pm = g[["game_id", "home", "away"]].merge(proc.rename(columns={"team": "home", "ypp": "ypp_h", "sr": "sr_h"})[["game_id", "home", "ypp_h", "sr_h"]], on=["game_id", "home"], how="left")
        pm = pm.merge(proc.rename(columns={"team": "away", "ypp": "ypp_a", "sr": "sr_a"})[["game_id", "away", "ypp_a", "sr_a"]], on=["game_id", "away"], how="left")
        PY = pm[["ypp_h", "sr_h"]].to_numpy(float); PYa = pm[["ypp_a", "sr_a"]].to_numpy(float)
        has_proc = ~np.isnan(PY).any(1) & ~np.isnan(PYa).any(1)
    else:
        has_proc = np.zeros(len(g), bool)

    # context features (all known before kickoff)
    rest_diff = np.clip(g.rest_home.to_numpy(float) - g.rest_away.to_numpy(float), -4, 4)
    ctx_m = np.c_[rest_diff, g.bye_home.to_numpy(float), g.bye_away.to_numpy(float)]
    wind = np.nan_to_num(g.wind.to_numpy(float)); temp = g.temp.to_numpy(float)
    dome = g.dome.to_numpy(bool)
    cold = np.where(dome | np.isnan(temp), 0.0, np.clip(40 - temp, 0, 40))
    ctx_t = np.c_[dome.astype(float), np.where(dome, 0.0, wind), cold, g["div"].to_numpy(float)]

    names = ["G0", "G1", "G2", "G3", "G4", "G5", "G6"]
    out = {f"{m}_margin": np.full(len(g), np.nan) for m in names}
    out.update({f"{m}_total": np.full(len(g), np.nan) for m in ["G0", "G2", "G3"]})
    out.update({f"{m}_p": np.full(len(g), np.nan) for m in names})

    key = g.groupby(["season", "week"]).date.min().sort_values()
    blocks = [np.where((g.season == s) & (g.week == w))[0] for (s, w) in key.index]

    elo = {t: 1500.0 for t in teams}; last_season = None
    K, hfa, reg = P["elo"]["K"], P["elo"]["hfa"], P["elo"]["regress"]
    hist = dict(idx=[])          # indices of finished games already usable as history
    raw = {k: np.full(len(g), np.nan) for k in ["elo_diff", "r_margin", "r_total", "dypp", "dsr"]}
    final_m = {m: np.full(len(g), np.nan) for m in names}

    def sigma(m):
        h = np.array(hist["idx"], int)
        if len(h) < MIN_HIST: return SIGMA0
        r = margin[h] - final_m[m][h]; r = r[~np.isnan(r)]
        return float(np.sqrt(np.mean(r ** 2))) if len(r) >= MIN_HIST else SIGMA0

    for bi, b in enumerate(blocks):
        s = g.season.iat[b[0]]
        if s != last_season:
            if last_season is not None:
                for t in teams: elo[t] = (1 - reg) * elo[t] + reg * 1505.0
            last_season = s
        past = np.array(hist["idx"], int)
        t_now = tt[b[0]]
        # ---------- Elo (ratings before this block) ----------
        if "elo" in components:
            raw["elo_diff"][b] = [elo[g.home.iat[i]] - elo[g.away.iat[i]] + (0.0 if neu[i] else hfa) for i in b]
        # ---------- ridge ratings on points ----------
        if "ridge" in components and len(past) >= 400:
            w = 0.5 ** ((t_now - tt[past]) / P["ridge"]["hl"])
            X = _design(hi[past], ai[past], neu[past], T)
            Y = np.r_[pts_h[past], pts_a[past]][:, None]
            th = _ridge(X, Y, np.r_[w, w], P["ridge"]["lam"], T)
            m = len(b); pr = _design(hi[b], ai[b], neu[b], T) @ th
            ph, pa = pr[:m, 0], pr[m:, 0]
            raw["r_margin"][b] = ph - pa; raw["r_total"][b] = ph + pa
        # ---------- process ratings ----------
        if "proc" in components:
            pp = past[has_proc[past]] if len(past) else past
            if len(pp) >= 400:
                w = 0.5 ** ((t_now - tt[pp]) / P["proc"]["hl"])
                X = _design(hi[pp], ai[pp], neu[pp], T)
                Y = np.r_[PY[pp], PYa[pp]]
                th = _ridge(X, Y, np.r_[w, w], P["proc"]["lam"], T)
                m = len(b); pr = _design(hi[b], ai[b], neu[b], T) @ th
                raw["dypp"][b] = pr[:m, 0] - pr[m:, 0]; raw["dsr"][b] = pr[:m, 1] - pr[m:, 1]
        # ---------- turn raw outputs into model predictions (calibrations use ONLY earlier out-of-sample games) ----------
        hh = past[~np.isnan(raw["elo_diff"][past])] if len(past) else past
        # G0
        mu0 = np.nanmean(margin[past]) if len(past) else 3.0
        tot0 = np.nanmean(total[past]) if len(past) else 44.0
        out["G0_margin"][b] = np.where(neu[b], 0.0, mu0); out["G0_total"][b] = tot0
        # G1
        if "elo" in components:
            slope = (np.sum(raw["elo_diff"][hh] * margin[hh]) / np.sum(raw["elo_diff"][hh] ** 2)) if len(hh) >= MIN_HIST else 1 / 25.0
            out["G1_margin"][b] = slope * raw["elo_diff"][b]
        # G2 / G3
        hr = past[~np.isnan(raw["r_margin"][past])] if len(past) else past
        if "ridge" in components and not np.isnan(raw["r_margin"][b]).all():
            out["G2_margin"][b] = raw["r_margin"][b]; out["G2_total"][b] = raw["r_total"][b]
            if len(hr) >= MIN_HIST:
                bm = _ols(ctx_m[hr], margin[hr] - raw["r_margin"][hr], ridge=50.0)
                bt = _ols(ctx_t[hr], total[hr] - raw["r_total"][hr], ridge=50.0)
                out["G3_margin"][b] = raw["r_margin"][b] + _apply(bm, ctx_m[b]); out["G3_total"][b] = raw["r_total"][b] + _apply(bt, ctx_t[b])
            else:
                out["G3_margin"][b] = raw["r_margin"][b]; out["G3_total"][b] = raw["r_total"][b]
        # G5
        hp = past[~np.isnan(raw["dypp"][past])] if len(past) else past
        if "proc" in components and not np.isnan(raw["dypp"][b]).all() and len(hp) >= MIN_HIST:
            bb = _ols(np.c_[raw["dypp"][hp], raw["dsr"][hp]], margin[hp], ridge=1e-3)
            out["G5_margin"][b] = _apply(bb, np.c_[raw["dypp"][b], raw["dsr"][b]])
        # G4 / G6 blends
        out["G4_margin"][b] = np.where(np.isnan(out["G1_margin"][b]) | np.isnan(out["G3_margin"][b]), np.nan, (out["G1_margin"][b] + out["G3_margin"][b]) / 2)
        out["G6_margin"][b] = (out["G3_margin"][b] + out["G5_margin"][b]) / 2
        for m in names:
            final_m[m][b] = out[f"{m}_margin"][b]
            sg = sigma(m)
            out[f"{m}_p"][b] = norm.cdf(out[f"{m}_margin"][b] / sg)
        # ---------- after the block: reveal outcomes, update Elo and history ----------
        for i in sorted(b, key=lambda k: (g.date.iat[k], k)):
            if not played[i]: continue
            d = elo[g.home.iat[i]] - elo[g.away.iat[i]] + (0.0 if neu[i] else hfa)
            ph = 1 / (1 + 10 ** (-d / 400)); res = 1.0 if margin[i] > 0 else 0.0 if margin[i] < 0 else 0.5
            dw = d if margin[i] > 0 else -d
            mult = np.log(abs(margin[i]) + 1) * 2.2 / (dw * 0.001 + 2.2) if margin[i] != 0 else 1.0
            sh = K * mult * (res - ph)
            elo[g.home.iat[i]] += sh; elo[g.away.iat[i]] -= sh
        hist["idx"].extend([i for i in b if played[i]])

    res = pd.DataFrame(out)
    res.insert(0, "game_id", g.game_id); res.insert(1, "season", g.season); res.insert(2, "week", g.week); res.insert(3, "split", g.split)
    res["home"] = g.home; res["away"] = g.away; res["neutral"] = g.neutral
    res["margin"] = g.margin; res["total"] = g.total; res["home_win"] = g.home_win
    return res


# ----------------------------------------------------------------------------- development-only hyper-parameter selection
def tune_dev(verbose: bool = True) -> dict:
    """Pick hyper-parameters using ONLY seasons <= 2022 (the loader is capped, so 2023+ rows are never in memory)."""
    g = load_games(include_2026=False, max_season=max(DEV)); assert g.season.max() <= max(DEV)
    proc = load_team_process()
    dev = lambda r: r[r.split == "dev"]
    best = dict(DEFAULTS); log = []
    # Elo: dev log loss of the win probability
    scores = []
    for K, hfa, reg in itertools.product([12, 20, 30], [35, 48, 60], [0.2, 0.33]):
        P = json.loads(json.dumps(DEFAULTS)); P["elo"] = dict(K=float(K), hfa=float(hfa), regress=float(reg))
        r = dev(run_walkforward(g, P, components=("elo",)))
        ll = float(-np.mean(r.home_win * np.log(r.G1_p.clip(1e-4, 1 - 1e-4)) + (1 - r.home_win) * np.log((1 - r.G1_p).clip(1e-4, 1 - 1e-4))))
        scores.append((ll, K, hfa, reg)); log.append(dict(model="G1", K=K, hfa=hfa, regress=reg, dev_logloss=ll))
    ll, K, hfa, reg = min(scores); best["elo"] = dict(K=float(K), hfa=float(hfa), regress=float(reg))
    # Ridge points ratings: dev RMSE(margin)/RMSE(G0) + MAE(total)/MAE(G0)
    scores = []
    for hl, lam in itertools.product([6, 10, 15, 30, 60], [2, 5, 10, 30]):
        P = json.loads(json.dumps(DEFAULTS)); P["ridge"] = dict(hl=float(hl), lam=float(lam))
        r = dev(run_walkforward(g, P, components=("ridge",)))
        s1 = np.sqrt(np.mean((r.margin - r.G2_margin) ** 2)) / np.sqrt(np.mean((r.margin - r.G0_margin) ** 2))
        s2 = np.mean(np.abs(r.total - r.G2_total)) / np.mean(np.abs(r.total - r.G0_total))
        scores.append((float(s1 + s2), hl, lam)); log.append(dict(model="G2", hl=hl, lam=lam, dev_rel_rmse_margin=float(s1), dev_rel_mae_total=float(s2)))
    sc, hl, lam = min(scores); best["ridge"] = dict(hl=float(hl), lam=float(lam))
    # Process ratings: dev RMSE of the OLS-mapped margin
    scores = []
    for hl, lam in itertools.product([10, 20, 30, 60], [10, 30, 100]):
        P = json.loads(json.dumps(DEFAULTS)); P["proc"] = dict(hl=float(hl), lam=float(lam))
        r = dev(run_walkforward(g, P, components=("proc",), proc=proc))
        r = r.dropna(subset=["G5_margin"])
        s = float(np.sqrt(np.mean((r.margin - r.G5_margin) ** 2)) / np.sqrt(np.mean((r.margin - r.G0_margin) ** 2)))
        scores.append((s, hl, lam)); log.append(dict(model="G5", hl=hl, lam=lam, dev_rel_rmse_margin=s))
    sc, hl, lam = min(scores); best["proc"] = dict(hl=float(hl), lam=float(lam))
    best["_selected_on"] = f"seasons {DEV[0]}-{DEV[-1]} only (walk-forward); 2023+ never loaded"
    pd.DataFrame(log).to_csv(RESULTS / "game_tuning_dev_grid.csv", index=False)
    if verbose:
        print(json.dumps(best, indent=1))
    return best


def run_all(P: dict, dev_only: bool = False) -> pd.DataFrame:
    g = load_games(include_2026=not dev_only, max_season=max(DEV) if dev_only else None)
    proc = load_team_process()
    return run_walkforward(g, P, components=("elo", "ridge", "proc"), proc=proc)


if __name__ == "__main__":
    RESULTS.mkdir(parents=True, exist_ok=True); REGISTRY.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    if len(sys.argv) > 1 and sys.argv[1] == "tune":
        best = tune_dev()
        (REGISTRY / "hyperparameters.json").write_text(json.dumps(best, indent=1))
        print("tuned in", round(time.time() - t0), "s")
    else:
        P = json.loads((REGISTRY / "hyperparameters.json").read_text())
        dev_only = len(sys.argv) > 1 and sys.argv[1] == "dev"
        pred = run_all(P, dev_only=dev_only)
        dest = RESULTS / ("_dev_only" if dev_only else ""); dest.mkdir(parents=True, exist_ok=True)
        pred.to_csv(dest / "game_predictions.csv.gz", index=False)
        print("wrote game_predictions", pred.shape, "->", dest.name or "results", "in", round(time.time() - t0), "s")
