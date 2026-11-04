#!/usr/bin/env python3
"""Shared engine: data loading, betting math, walk-forward line origination.

Design rules enforced here
--------------------------
1. Walk-forward only. A game's own line is produced from state built exclusively from games
   that kicked off earlier (strictly earlier `gameday` + `gametime`). No future information.
2. Hyper-parameters are tuned on the warm-up window 1999-2005 only. Every season from 2006 on is
   out-of-sample for tuning, blending and evaluation.
3. Sign conventions (verified in pipeline/01_audit.py, checks A06/A07):
      spread_line  > 0  -> HOME team is favoured by that many points (== expected home margin)
      home covers  <=>  (home_score - away_score) > spread_line
      team handicap (home) = -spread_line
4. All market prices are American odds taken verbatim from the source files. No price is invented.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "nfldata" / "data"
OUT = ROOT / "outputs"
MANIFEST = json.loads((ROOT / "data" / "manifest.json").read_text())

MARKET_COLS = [
    "spread_line", "total_line", "home_spread_odds", "away_spread_odds",
    "over_odds", "under_odds", "home_moneyline", "away_moneyline",
]

# ---------------------------------------------------------------------------- odds helpers


def american_to_decimal(o: float) -> float:
    if o is None or np.isnan(o) or o == 0:
        return np.nan
    return 1.0 + (o / 100.0 if o > 0 else 100.0 / -o)


def american_to_prob(o: float) -> float:
    if o is None or np.isnan(o) or o == 0:
        return np.nan
    return 100.0 / (o + 100.0) if o > 0 else -o / (-o + 100.0)


def profit_per_unit(o: float) -> float:
    """Profit on a 1-unit winning bet at American odds `o`."""
    if o is None or np.isnan(o) or o == 0:
        return np.nan
    return o / 100.0 if o > 0 else 100.0 / -o


def implied_from_prob(p: float, margin: float = 0.0) -> float:
    """Fair American odds for probability p, with an optional book margin added."""
    p = min(max(p * (1 + margin), 1e-6), 1 - 1e-6)
    dec = 1.0 / p
    return (dec - 1.0) * 100.0 if dec >= 2.0 else -100.0 / (dec - 1.0)


# ------------------------------------------------------------------------- data loading


def load_games() -> pd.DataFrame:
    games = pd.read_csv(RAW / "games.csv", low_memory=False)
    teams = pd.read_csv(RAW / "teams.csv", low_memory=False)

    # stable franchise key across renames (STL->LA, SD->LAC, OAK->LV)
    tmap = teams.dropna(subset=["team", "nfl_team_id"]).copy()
    tmap["nfl_team_id"] = tmap.nfl_team_id.astype(int)
    key = tmap.set_index(["season", "team"]).nfl_team_id
    # fallback for seasons the teams table does not cover (it starts in 2002)
    fallback = (tmap.sort_values("season").groupby("team").nfl_team_id.first().to_dict())

    def fid(season: int, team: str) -> int:
        for s in (season, season - 1, season + 1):
            if (s, team) in key.index:
                return int(key.loc[(s, team)])
        if team in fallback:
            return int(fallback[team])
        raise KeyError(f"no franchise id for {team} in {season}")

    games = games[games.game_type == "REG"].copy()
    games["fid_home"] = [fid(s, t) for s, t in zip(games.season, games.home_team)]
    games["fid_away"] = [fid(s, t) for s, t in zip(games.season, games.away_team)]
    games["kickoff"] = pd.to_datetime(
        games.gameday.fillna("2100-01-01") + " " + games.gametime.fillna("12:00"), errors="coerce"
    )
    # gameday is the reliable field; gametime is Eastern local. Use gameday for ordering so that
    # every game in a week is predicted from the same state (no intra-week leakage).
    games["order_date"] = pd.to_datetime(games.gameday, errors="coerce")
    games["is_home"] = (games.location == "Home").astype(int)
    games = games.sort_values(["order_date", "game_id"]).reset_index(drop=True)
    for c in MARKET_COLS:
        games[c] = pd.to_numeric(games[c], errors="coerce")
    games["home_handicap"] = -games.spread_line  # team-perspective handicap for the home side
    return games


def completed(games: pd.DataFrame) -> pd.DataFrame:
    return games.dropna(subset=["home_score", "away_score"])


# ------------------------------------------------------------------------ rating models


@dataclass
class Params:
    elo_k: float = 20.0
    elo_hfa: float = 2.2          # points of home-field advantage in rating space
    elo_season_decay: float = 0.65  # rating multiplier applied at each season boundary
    ridge_lambda: float = 60.0
    ridge_tau_days: float = 120.0
    ewma_halflife: float = 6.0     # games


class LineEngine:
    """Walk-forward state. Call `week_start` once per (season, week), then `predict`/`update`."""

    def __init__(self, params: Params, league_mean: float = 21.5):
        self.p = params
        self.league_mean = league_mean
        self.elo: dict[int, float] = {}
        self.last_season: int | None = None
        self.off: dict[int, float] = {}
        self.defn: dict[int, float] = {}
        self.games_seen: dict[int, int] = {}
        self.hist: list[dict] = []
        self.ridge = None
        self.mridge = None
        self.franchises: list[int] = []
        self._fix: dict[int, int] = {}

    # ---- utilities
    def _r(self, f: int) -> float:
        return self.elo.get(f, 0.0)

    def _off(self, f: int) -> float:
        return self.off.get(f, self.league_mean)

    def _def(self, f: int) -> float:
        return self.defn.get(f, self.league_mean)

    def season_rollover(self, season: int) -> None:
        if self.last_season is not None and season != self.last_season:
            d = self.p.elo_season_decay
            self.elo = {k: v * d for k, v in self.elo.items()}
        self.last_season = season

    # ---- ridge opponent-adjusted scoring model
    def fit_ridge(self, asof: pd.Timestamp) -> None:
        h = pd.DataFrame(self.hist)
        if len(h) < 200:
            self.ridge = None
            return
        self.franchises = sorted(set(h.fid_home) | set(h.fid_away))
        idx = {f: i for i, f in enumerate(self.franchises)}
        self._fix = idx
        n = len(self.franchises)
        age = (asof - h.order_date).dt.days.clip(lower=0).to_numpy()
        w = np.exp(-np.log(2) * age / self.p.ridge_tau_days)
        # normalise to a mean of 1 so that the ridge penalty is interpretable in "games of prior"
        w = w / max(w.mean(), 1e-9)

        # two rows per game: home team's score, away team's score
        team = np.concatenate([h.fid_home.to_numpy(), h.fid_away.to_numpy()])
        opp = np.concatenate([h.fid_away.to_numpy(), h.fid_home.to_numpy()])
        home_flag = np.concatenate([np.ones(len(h)), np.zeros(len(h))])
        y = np.concatenate([h.home_score.to_numpy(), h.away_score.to_numpy()]).astype(float)
        ww = np.concatenate([w, w])
        ti = np.array([idx[t] for t in team])
        oi = np.array([idx[t] for t in opp])

        # design: [1, is_home, off_team (n), def_opp (n)]
        dim = 2 + 2 * n
        A = np.zeros((dim, dim))
        b = np.zeros(dim)

        def add(i, j, v):
            A[i, j] += v
            if i != j:
                A[j, i] += v

        add(0, 0, ww.sum())
        add(0, 1, (ww * home_flag).sum())
        w_team = np.bincount(ti, weights=ww, minlength=n)
        w_opp = np.bincount(oi, weights=ww, minlength=n)
        wy_team = np.bincount(ti, weights=ww * y, minlength=n)
        wy_opp = np.bincount(oi, weights=ww * y, minlength=n)
        w_home_team = np.bincount(ti, weights=ww * home_flag, minlength=n)
        w_home_opp = np.bincount(oi, weights=ww * home_flag, minlength=n)
        for k in range(n):
            add(0, 2 + k, w_team[k])
            add(0, 2 + n + k, w_opp[k])
            add(1, 2 + k, w_home_team[k])
            add(1, 2 + n + k, w_home_opp[k])
            add(2 + k, 2 + k, w_team[k])            # off-off is diagonal
            add(2 + n + k, 2 + n + k, w_opp[k])     # def-def is diagonal
        # off/def cross term: sum of weights for each (team, opp) pair
        pair = np.zeros((n, n))
        np.add.at(pair, (ti, oi), ww)
        A[2:2 + n, 2 + n:2 + 2 * n] += pair
        A[2 + n:2 + 2 * n, 2:2 + n] += pair.T
        b[0] = (ww * y).sum()
        b[1] = (ww * home_flag * y).sum()
        b[2:2 + n] = wy_team
        b[2 + n:2 + 2 * n] = wy_opp

        reg = np.eye(dim) * self.p.ridge_lambda
        reg[0, 0] = 0.0
        reg[1, 1] = 0.0
        # shrink off/def toward 0 (i.e. toward the intercept) harder than the intercept itself
        self.ridge = np.linalg.solve(A + reg, b)

    def fit_margin_ridge(self, asof: pd.Timestamp) -> None:
        """Model D: margin-space ridge with an explicit home-field term.

        For each completed game:  result = b0 + b1*is_home + rating_home - rating_away
        solved with exponentially decayed weights and a ridge penalty on the ratings.
        """
        h = pd.DataFrame(self.hist)
        if len(h) < 200:
            self.mridge = None
            return
        fr = sorted(set(h.fid_home) | set(h.fid_away))
        idx = {f: i for i, f in enumerate(fr)}
        n = len(fr)
        age = (asof - h.order_date).dt.days.clip(lower=0).to_numpy()
        w = np.exp(-np.log(2) * age / self.p.ridge_tau_days)
        w = w / max(w.mean(), 1e-9)
        hi = np.array([idx[f] for f in h.fid_home])
        ai = np.array([idx[f] for f in h.fid_away])
        y = (h.home_score - h.away_score).to_numpy(dtype=float)
        is_home = h.is_home.to_numpy(dtype=float) if "is_home" in h.columns else np.ones(len(h))

        dim = 2 + n
        A = np.zeros((dim, dim))
        b = np.zeros(dim)
        # accumulate cross products for sparse rows [1, is_home, e_home, -e_away]
        A[0, 0] = w.sum()
        A[0, 1] = A[1, 0] = (w * is_home).sum()
        A[0, 2:] = w.sum() * 0
        np.add.at(A[0, 2:], hi, w)
        np.add.at(A[0, 2:], ai, -w)
        A[2:, 0] = A[0, 2:]
        A[1, 2:] = 0.0
        np.add.at(A[1, 2:], hi, w * is_home)
        np.add.at(A[1, 2:], ai, -w * is_home)
        A[2:, 1] = A[1, 2:]
        np.add.at(A, (hi, hi), w)
        np.add.at(A, (ai, ai), w)
        np.add.at(A, (hi, ai), -w)
        np.add.at(A, (ai, hi), -w)
        b[0] = (w * y).sum()
        b[1] = (w * is_home * y).sum()
        np.add.at(b[2:], hi, w * y)
        np.add.at(b[2:], ai, -w * y)
        reg = np.eye(dim) * self.p.ridge_lambda
        reg[0, 0] = 0.0
        reg[1, 1] = 0.0
        # a fixed prior of 20 pseudo-games of rating 0 for every club keeps clubs with very few
        # games in the decay window from exploding
        reg[2:, 2:] += np.eye(n) * 20.0
        self.mridge = np.linalg.solve(A + reg, b)
        self.mridge[2:] = np.clip(self.mridge[2:], -35.0, 35.0)
        self.mridge_idx = idx

    def _ridge_scores(self, fid_home: int, fid_away: int) -> tuple[float, float] | None:
        if self.ridge is None or fid_home not in self._fix or fid_away not in self._fix:
            return None
        b = self.ridge
        n = len(self.franchises)
        ih, ia = self._fix[fid_home], self._fix[fid_away]
        home_score = b[0] + b[1] + b[2 + ih] - b[2 + n + ia]
        away_score = b[0] + b[2 + ia] - b[2 + n + ih]
        clip = lambda v: float(np.clip(v, 0.0, 70.0))
        return clip(home_score), clip(away_score)

    # ---- prediction
    def predict(self, row) -> dict:
        fh, fa = int(row.fid_home), int(row.fid_away)
        hfa_home = self.p.elo_hfa if row.is_home == 1 else 0.0
        hfa_away = 0.0 if row.is_home == 1 else self.p.elo_hfa

        # Model A - Elo (margin space)
        elo_margin = (self._r(fh) + hfa_home) - (self._r(fa) + hfa_away)

        # Model B - ridge opponent-adjusted scoring
        rs = self._ridge_scores(fh, fa)
        if rs is None:
            ridge_margin = np.nan
            ridge_total = np.nan
        else:
            hs, as_ = rs
            ridge_margin = hs - as_
            ridge_total = hs + as_

        # Model D - margin-space ridge
        md = getattr(self, "mridge", None)
        if md is None or fh not in getattr(self, "mridge_idx", {}) or fa not in self.mridge_idx:
            massey_margin = np.nan
        else:
            mi = self.mridge_idx
            massey_margin = float(np.clip(
                md[0] + md[1] * float(row.is_home) + md[2 + mi[fh]] - md[2 + mi[fa]], -45.0, 45.0))

        # Model C - naive EWMA scoring, shrunk
        off_h, def_h = self._off(fh), self._def(fh)
        off_a, def_a = self._off(fa), self._def(fa)
        c_home = (off_h + def_a) / 2.0
        c_away = (off_a + def_h) / 2.0
        naive_margin = c_home - c_away
        naive_total = c_home + c_away

        return {
            "elo_margin": elo_margin, "elo_total": np.nan,
            "ridge_margin": ridge_margin, "ridge_total": ridge_total,
            "massey_margin": massey_margin,
            "naive_margin": naive_margin, "naive_total": naive_total,
        }

    # ---- state update after a completed game
    def update(self, row) -> None:
        fh, fa = int(row.fid_home), int(row.fid_away)
        res = float(row.home_score) - float(row.away_score)

        # Elo in points-of-margin space. The update is a bounded (tanh) function of the
        # surprise, measured in units of the margin standard deviation (14 points). Bounding
        # the update stops blowouts from dominating the ratings.
        hfa = self.p.elo_hfa if row.is_home == 1 else 0.0
        exp_margin = (self._r(fh) + hfa) - self._r(fa)
        delta = self.p.elo_k * float(np.tanh((res - exp_margin) / 14.0))
        self.elo[fh] = self._r(fh) + delta
        self.elo[fa] = self._r(fa) - delta

        # EWMA scoring
        hl = self.p.ewma_halflife
        a = 1.0 - 0.5 ** (1.0 / hl)
        self.off[fh] = (1 - a) * self._off(fh) + a * float(row.home_score)
        self.defn[fh] = (1 - a) * self._def(fh) + a * float(row.away_score)
        self.off[fa] = (1 - a) * self._off(fa) + a * float(row.away_score)
        self.defn[fa] = (1 - a) * self._def(fa) + a * float(row.home_score)

        self.hist.append({
            "order_date": row.order_date, "fid_home": fh, "fid_away": fa,
            "home_score": float(row.home_score), "away_score": float(row.away_score),
            "is_home": float(getattr(row, "is_home", 1)),
        })


# ------------------------------------------------------------------ walk-forward generation

WARMUP_SEASONS = (1999, 2005)
EVAL_FIRST_SEASON = 2006


MARGIN_COMPONENTS = ["elo_margin", "ridge_margin", "massey_margin", "naive_margin"]
TOTAL_COMPONENTS = ["ridge_total", "naive_total"]


def fit_calibration(wf: pd.DataFrame) -> dict:
    """Per-component linear calibration (a + b*x) fitted on the warm-up window only.

    Without this step each component carries its own scale and home-field bias; an
    uncalibrated bias of ~2 points would manufacture fake betting edges later.
    """
    calib = {}
    for c in MARGIN_COMPONENTS:
        d = wf.dropna(subset=[c, "result"])
        if len(d) < 100:
            calib[c] = {"a": 0.0, "b": 1.0, "n": int(len(d))}
            continue
        b, a = np.polyfit(d[c].to_numpy(dtype=float), d.result.to_numpy(dtype=float), 1)
        calib[c] = {"a": float(a), "b": float(b), "n": int(len(d))}
    for c in TOTAL_COMPONENTS:
        d = wf.dropna(subset=[c, "total"])
        if len(d) < 100:
            calib[c] = {"a": 0.0, "b": 1.0, "n": int(len(d))}
            continue
        b, a = np.polyfit(d[c].to_numpy(dtype=float), d.total.to_numpy(dtype=float), 1)
        calib[c] = {"a": float(a), "b": float(b), "n": int(len(d))}
    return calib


def _calibrated(wf: pd.DataFrame, calib: dict, comps: list[str]) -> np.ndarray:
    x = wf[comps].to_numpy(dtype=float).copy()
    for j, c in enumerate(comps):
        x[:, j] = calib[c]["a"] + calib[c]["b"] * x[:, j]
    return x


def fit_blend(wf_warm: pd.DataFrame, calib: dict) -> dict:
    from scipy.optimize import nnls

    Xm = _calibrated(wf_warm, calib, MARGIN_COMPONENTS)
    ym = wf_warm.result.to_numpy(dtype=float)
    okm = np.isfinite(Xm).all(axis=1) & np.isfinite(ym)
    wm, _ = nnls(Xm[okm], ym[okm])
    if wm.sum() <= 0:  # degenerate guard
        wm = np.array([0.25, 0.0, 0.0, 0.75])

    Xt = _calibrated(wf_warm, calib, TOTAL_COMPONENTS)
    yt = wf_warm.total.to_numpy(dtype=float)
    okt = np.isfinite(Xt).all(axis=1) & np.isfinite(yt)
    wt, _ = nnls(Xt[okt], yt[okt])
    if wt.sum() <= 0:
        wt = np.array([0.0, 1.0])
    return {"margin": dict(zip(MARGIN_COMPONENTS, np.round(wm, 6).tolist())),
            "total": dict(zip(TOTAL_COMPONENTS, np.round(wt, 6).tolist()))}


def apply_model(wf: pd.DataFrame, calib: dict, blend: dict, sigma_margin: float,
                sigma_total: float) -> pd.DataFrame:
    wf = wf.copy()
    Xm = _calibrated(wf, calib, MARGIN_COMPONENTS)
    Xt = _calibrated(wf, calib, TOTAL_COMPONENTS)
    wm = np.array([blend["margin"][c] for c in MARGIN_COMPONENTS])
    wt = np.array([blend["total"][c] for c in TOTAL_COMPONENTS])
    wf["model_margin"] = np.where(np.isfinite(Xm).all(axis=1), Xm @ wm, np.nan)
    wf["model_total"] = np.where(np.isfinite(Xt).all(axis=1), Xt @ wt, np.nan)
    wf["sigma_margin"] = sigma_margin
    wf["sigma_total"] = sigma_total
    wf["model_home_win_prob"] = norm.cdf(wf.model_margin / sigma_margin)
    return wf


def fit_scale(wf_warm: pd.DataFrame, calib: dict, blend: dict) -> tuple[float, float]:
    tmp = apply_model(wf_warm, calib, blend, 1.0, 1.0)
    m = tmp.dropna(subset=["result", "model_margin"])
    t = tmp.dropna(subset=["total", "model_total"])
    return (float(np.std(m.result - m.model_margin, ddof=1)),
            float(np.std(t.total - t.model_total, ddof=1)))


def tune(warm: pd.DataFrame) -> tuple[Params, dict]:
    """Grid search on the warm-up window only, scored by the calibrated blend MAE."""
    best = None
    wf_cache: dict[tuple, pd.DataFrame] = {}
    grid = [
        dict(elo_k=k, elo_hfa=h, elo_season_decay=d, ridge_lambda=lam,
             ridge_tau_days=tau, ewma_halflife=hl)
        for k in (10.0, 16.0, 24.0)
        for h in (1.8, 2.6)
        for d in (0.5, 0.7)
        for lam in (0.5, 2.0, 8.0)
        for tau in (90.0, 240.0)
        for hl in (5.0, 10.0)
    ]
    for cfg in grid:
        params = Params(**cfg)
        wf = run_walk_forward(params, warm)
        calib = fit_calibration(wf)
        blend = fit_blend(wf, calib)
        tmp = apply_model(wf, calib, blend, 1.0, 1.0)
        m = tmp.dropna(subset=["result", "model_margin"])
        t = tmp.dropna(subset=["total", "model_total"])
        score = float((m.result - m.model_margin).abs().mean() + (t.total - t.model_total).abs().mean()) / 2
        if best is None or score < best[0]:
            best = (score, params, cfg)
    score, params, cfg = best
    return params, {"warmup_blend_mae": round(score, 4), "params": params.__dict__,
                    "grid_size": len(grid)}


def run_walk_forward(params: Params, games: pd.DataFrame | None = None) -> pd.DataFrame:
    games = load_games() if games is None else games
    eng = LineEngine(params)
    rows: list[dict] = []

    grouped = games.groupby(["season", "week"], sort=True)
    for (season, week), wk in grouped:
        eng.season_rollover(int(season))
        # fit the ridge model with everything completed before this week's first kickoff
        asof = wk.order_date.min()
        if pd.notna(asof):
            eng.fit_ridge(asof)
            eng.fit_margin_ridge(asof)
        for row in wk.itertuples():
            pred = eng.predict(row)
            rec = {
                "game_id": row.game_id, "season": int(season), "week": int(week),
                "gameday": row.gameday, "home_team": row.home_team, "away_team": row.away_team,
                "home_score": row.home_score, "away_score": row.away_score,
                "result": row.result, "total": row.total, "is_home": int(row.is_home),
                **pred,
            }
            for c in MARKET_COLS:
                rec[c] = getattr(row, c)
            rows.append(rec)
            if pd.notna(row.home_score) and pd.notna(row.away_score):
                eng.update(row)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    games = load_games()
    warm = games[(games.season >= WARMUP_SEASONS[0]) & (games.season <= WARMUP_SEASONS[1])]
    params, tune_info = tune(warm)
    print("tuned:", tune_info)
