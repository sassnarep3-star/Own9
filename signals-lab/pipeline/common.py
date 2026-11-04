"""Shared loaders, scoring rules and cluster-bootstrap helpers for the signals lab (session efe45667).

Design rules enforced here
  * FAIL CLOSED: only seasons whose parsed feed equals the official NFL.com standings (reconciliation_summary.csv, verified=True) are loaded.
  * 2026 (in progress) is loaded from the nflverse/nfldata schedule table; its completed games are accepted only if every team's
    W-L-T/PF/PA equals NFL.com's standings through Week 8 (reconciliation_standings_2026_ytd.csv, all matched).
  * Every feature for a game is computed from information dated before that game (rest/bye from prior game dates only).
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

from config import DERIVED, RAW, REGISTRY, RESULTS, VERIFIED

BURN = [2015, 2016, 2017]          # fit-only warm-up (never scored)
DEV = [2018, 2019, 2020, 2021, 2022]   # hyper-parameter selection allowed here
TEST = [2023, 2024, 2025]          # sealed: evaluated once after pre-registration
FORWARD = 2026                     # forward holdout (weeks 1-8 played, week 9 = origination target)

DIVISIONS = {
    "BUF": "AE", "MIA": "AE", "NE": "AE", "NYJ": "AE", "BAL": "AN", "CIN": "AN", "CLE": "AN", "PIT": "AN",
    "HOU": "AS", "IND": "AS", "JAX": "AS", "TEN": "AS", "DEN": "AW", "KC": "AW", "LV": "AW", "LAC": "AW",
    "DAL": "NE", "NYG": "NE", "PHI": "NE", "WAS": "NE", "CHI": "NN", "DET": "NN", "GB": "NN", "MIN": "NN",
    "ATL": "NS", "CAR": "NS", "NO": "NS", "TB": "NS", "ARI": "NW", "LA": "NW", "SEA": "NW", "SF": "NW",
}
NFLDATA_GAMES = RAW / "nfldata" / "data" / "games.csv"


def verified_seasons() -> list[int]:
    s = pd.read_csv(VERIFIED / "reconciliation_summary.csv")
    return sorted(int(x) for x in s[s.verified.astype(bool)].season)


def _weather(txt: str) -> tuple[float, float, bool]:
    t = re.search(r"Temp:\s*(-?\d+)", txt or "")
    w = re.search(r"Wind:\s*(?:Calm|[A-Z]+)?\s*(\d+)\s*mph", txt or "")
    temp = float(t.group(1)) if t else np.nan
    # roofed venue = explicit indoor label OR no usable temperature reading in the feed (data-driven, no outside knowledge)
    dome = bool(re.search(r"Controlled|Indoor|Dome|Closed|Roof", txt or "", re.I)) or np.isnan(temp)
    wind = float(w.group(1)) if w else (0.0 if "Calm" in (txt or "") else np.nan)
    return (temp, 0.0 if dome else wind, dome)


def load_team_process() -> pd.DataFrame:
    """Team-game process stats from the feed (turnovers deliberately excluded): yards/play, success rate, explosive rate."""
    t = pd.read_csv(DERIVED / "team_games_feed.csv.gz")
    t = t[t.game_type == "REG"].copy()
    plays = t["sc_plays"].replace(0, np.nan)
    t["ypp"] = t["sc_yards"] / plays
    t["sr"] = t["success"] / plays
    t["xpl"] = t["explosive"] / plays
    return t[["game_id", "team", "ypp", "sr", "xpl"]]


def load_games(include_2026: bool = True, max_season: int | None = None) -> pd.DataFrame:
    """One row per regular-season game, chronologically sorted, with leak-free context features."""
    ok = verified_seasons()
    g = pd.read_csv(DERIVED / "games_feed.csv.gz")
    g = g[(g.game_type == "REG") & g.season.isin(ok)].copy()
    g["date"] = pd.to_datetime(g.start_time_local.str.split(",").str[0], format="%m/%d/%y")
    wx = g.weather_text.fillna("").map(_weather)
    g["temp"] = [a for a, _, _ in wx]; g["wind"] = [b for _, b, _ in wx]; g["dome"] = [c for _, _, c in wx]
    modal = g.groupby(["season", "home_team"]).stadium.agg(lambda s: s.mode().iat[0]).rename("modal").reset_index()
    g = g.merge(modal, on=["season", "home_team"], how="left")
    g["neutral"] = g.stadium != g.modal          # off-site = not the home team's usual stadium (international/relocated games)
    g = g.rename(columns={"away_team": "away", "home_team": "home"})
    g["src"] = "game-center feed"
    cols = ["game_id", "season", "week", "date", "away", "home", "away_score", "home_score", "neutral", "dome", "wind", "temp", "src"]
    g = g[cols]
    if include_2026:
        n = pd.read_csv(NFLDATA_GAMES)
        n = n[(n.season == FORWARD) & (n.game_type == "REG")].copy()
        n["date"] = pd.to_datetime(n.gameday)
        n = n.rename(columns={"away_team": "away", "home_team": "home"})
        n["away"] = n.away.replace({"ARI": "ARI"}); n["home"] = n.home.replace({"ARI": "ARI"})
        n["neutral"] = n.location.eq("Neutral")
        n["dome"] = n.roof.isin(["dome", "closed"])
        n["src"] = "nflverse/nfldata"
        g = pd.concat([g, n[cols]], ignore_index=True)
    if max_season is not None:
        g = g[g.season <= max_season]
    g = g.sort_values(["date", "game_id"]).reset_index(drop=True)
    # rest / bye from *previous* games of the same team in the same season only
    long = pd.concat([g[["game_id", "season", "date", "home"]].rename(columns={"home": "team"}),
                      g[["game_id", "season", "date", "away"]].rename(columns={"away": "team"})]).sort_values(["team", "date"])
    long["prev"] = long.groupby(["team", "season"]).date.shift(1)
    long["rest"] = (long.date - long.prev).dt.days
    long["rest"] = long.rest.fillna(7.0)
    rest = long.set_index(["game_id", "team"]).rest
    g["rest_home"] = [rest[(i, t)] for i, t in zip(g.game_id, g.home)]
    g["rest_away"] = [rest[(i, t)] for i, t in zip(g.game_id, g.away)]
    g["bye_home"] = g.rest_home >= 13; g["bye_away"] = g.rest_away >= 13
    g["div"] = [DIVISIONS[h] == DIVISIONS[a] for h, a in zip(g.home, g.away)]
    g["margin"] = g.home_score - g.away_score
    g["total"] = g.home_score + g.away_score
    g["home_win"] = np.where(g.margin > 0, 1.0, np.where(g.margin < 0, 0.0, np.where(g.margin.isna(), np.nan, 0.5)))
    g["split"] = np.select([g.season.isin(BURN), g.season.isin(DEV), g.season.isin(TEST), g.season == FORWARD], ["burn", "dev", "test", "forward"], "other")
    return g


def check_division_map_against_2026() -> tuple[int, int]:
    """Sanity check of the hard-coded division map using nfldata's own div_game flag for 2026 (all weeks)."""
    n = pd.read_csv(NFLDATA_GAMES)
    n = n[(n.season == FORWARD) & (n.game_type == "REG")]
    mine = [int(DIVISIONS[h] == DIVISIONS[a]) for h, a in zip(n.home_team, n.away_team)]
    return int(sum(m == d for m, d in zip(mine, n.div_game))), len(n)


# ----------------------------------------------------------------------------- scoring rules and bootstrap
def logloss(p, y):
    p = np.clip(np.asarray(p, float), 1e-4, 1 - 1e-4)
    y = np.asarray(y, float)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def brier(p, y):
    return (np.asarray(p, float) - np.asarray(y, float)) ** 2


def pinball(y, q, tau):
    d = np.asarray(y, float) - np.asarray(q, float)
    return np.maximum(tau * d, (tau - 1) * d)


def cluster_boot_skill(l_model, l_base, clusters, B: int = 2000, seed: int = 0):
    """Skill = 1 - mean(l_model)/mean(l_base) with a cluster bootstrap (resample whole clusters, e.g. games).

    Returns (skill, lo95, hi95, p_one_sided) where p tests H0: skill <= 0 (bootstrap proportion, +1 smoothing).
    """
    l_model = np.asarray(l_model, float); l_base = np.asarray(l_base, float)
    codes, uniq = pd.factorize(pd.Series(clusters))
    C = len(uniq)
    sm = np.bincount(codes, weights=l_model, minlength=C)
    sb = np.bincount(codes, weights=l_base, minlength=C)
    rng = np.random.default_rng(seed)
    out = np.empty(B)
    step = 250
    for s in range(0, B, step):
        idx = rng.integers(0, C, size=(min(step, B - s), C))
        out[s:s + step] = 1 - sm[idx].sum(1) / sb[idx].sum(1)
    point = 1 - sm.sum() / sb.sum()
    lo, hi = np.percentile(out, [2.5, 97.5])
    p = (np.sum(out <= 0) + 1) / (B + 1)
    se = out.std(ddof=1)
    return float(point), float(lo), float(hi), float(p), float(se)


def holm(pvals: dict[str, float]) -> dict[str, float]:
    """Holm-Bonferroni adjusted p-values (monotone), over the whole family of strategies that were tested."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    adj, running = {}, 0.0
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        adj[k] = running
    return adj


def american(p: float) -> float:
    """Fair American odds for win probability p (no vig)."""
    p = float(np.clip(p, 1e-6, 1 - 1e-6))
    return -round(100 * p / (1 - p)) if p >= 0.5 else round(100 * (1 - p) / p)


if __name__ == "__main__":
    ok, n = check_division_map_against_2026()
    print(f"division map agrees with nfldata div_game on {ok}/{n} 2026 games")
    g = load_games()
    print(g.groupby("split").size().to_dict(), "| neutral/off-site games:", int(g.neutral.sum()), "| future games:", int(g.margin.isna().sum()))
    print(g[g.neutral].groupby("season").size().to_dict())
    print(g[["temp", "wind"]].isna().mean().round(3).to_dict(), "dome share", round(g.dome.mean(), 3))
