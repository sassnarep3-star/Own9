#!/usr/bin/env python3
"""
NFL signal research pipeline (Own9).

Inputs  : data/raw/games.csv  (copy of nflverse/nfldata data/games.csv, commit d5c8272)
Outputs : data/site/*.json    (consumed by the static GitHub Pages site at repo root)

Conventions (verified against the data, see flagged.html):
  * result   = home_score - away_score (nflverse data dictionary: "Equals h_score - v_score").
  * spread_line s is HOME-perspective and positive = home favored. Evidence: slope of result on
    spread_line is ~1.04 across 1999-2026 and mean(result - s) ~ 0. Official field definition
    was NOT retrieved in this session -> flagged.
  * Home ATS cover: (result - s) > 0 ; push when == 0 ; away covers when < 0.
  * Totals: over when total > total_line ; under when < ; push when ==.
  * Standard price -110 => risk 1.10 to win 1.00 ; break-even win rate = 110/210 = 52.38%.

Validation design (removes most luck):
  * Discovery window : 1999-2015 (used for stability gate only)
  * Validation window: 2016-2025 (out-of-sample; gates are judged here)
  * Forward window   : 2026 completed games (reported, not gated)
  * Gates: G1 sample >= 150 bets, G2 Wilson 95% lower bound > break-even,
           G3 one-sided binomial p < 0.05 / N_strategies (Bonferroni),
           G4 same direction in discovery AND both validation halves (2016-20, 2021-25),
           G5 ROI > 0 at the offered price in validation.
"""
import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "games.csv"
OUT = ROOT / "data" / "site"
OUT.mkdir(parents=True, exist_ok=True)

RNG = np.random.default_rng(20261104)
BREAKEVEN_110 = 110 / 210  # 0.5238095...
MIN_N = 150
N_BOOT = 1000

# ----------------------------------------------------------------------------
# Load & prepare
# ----------------------------------------------------------------------------
g = pd.read_csv(RAW, low_memory=False)
g["gameday"] = pd.to_datetime(g["gameday"])
g = g.sort_values(["gameday", "game_id"]).reset_index(drop=True)

played = g["result"].notna()
g["margin"] = g["result"]            # home - away
g["spread"] = g["spread_line"]       # home-perspective, positive = home favored
g["total_pts"] = g["total"]


def american_to_prob(odds):
    odds = np.asarray(odds, dtype=float)
    p = np.where(odds < 0, -odds / (-odds + 100.0), 100.0 / (odds + 100.0))
    return p


def american_profit(odds):
    """profit per 1 unit staked when the bet wins."""
    odds = np.asarray(odds, dtype=float)
    return np.where(odds < 0, 100.0 / -odds, odds / 100.0)


# ----------------------------------------------------------------------------
# Own-line model: time-decayed weighted ridge on team ratings + home field.
# Walk-forward: a game is priced using only games played strictly before it.
# ----------------------------------------------------------------------------
TEAMS = sorted(set(g.home_team) | set(g.away_team))
TIDX = {t: i for i, t in enumerate(TEAMS)}
LAMBDA = 25.0          # ridge penalty on team ratings
HALF_LIFE_DAYS = 365.0  # recency weighting


def fit_ratings(hist, asof):
    """hist: completed games with margin; returns (ratings vector, hfa)."""
    n_t = len(TEAMS)
    X = np.zeros((len(hist), n_t + 1))
    h = hist["home_team"].map(TIDX).values
    a = hist["away_team"].map(TIDX).values
    rows = np.arange(len(hist))
    X[rows, h] = 1.0
    X[rows, a] = -1.0
    X[:, n_t] = 1.0  # home-field intercept (unpenalized)
    age = (asof - hist["gameday"]).dt.days.values
    w = 0.5 ** (age / HALF_LIFE_DAYS)
    y = hist["margin"].values
    XtW = X.T * w
    A = XtW @ X
    D = np.eye(n_t + 1) * LAMBDA
    D[n_t, n_t] = 0.0
    beta = np.linalg.solve(A + D, XtW @ y)
    return beta[:n_t], beta[n_t]


def predict_home_margin(ratings, hfa, home, away):
    return hfa + ratings[TIDX[home]] - ratings[TIDX[away]]


g["model_line"] = np.nan
asof_dates = sorted(g.loc[g.season >= 2001, "gameday"].unique())
for d in asof_dates:
    d = pd.Timestamp(d)
    mask_target = (g.gameday == d)
    hist = g[played & (g.gameday < d) & (g.season >= 1999)]
    if len(hist) < 100 or not mask_target.any():
        continue
    r, hfa = fit_ratings(hist, d)
    for i in g.index[mask_target]:
        g.at[i, "model_line"] = predict_home_margin(r, hfa, g.at[i, "home_team"], g.at[i, "away_team"])

# Current ratings for upcoming games (all completed games through today's data)
r_now, hfa_now = fit_ratings(g[played], g.loc[played, "gameday"].max() + pd.Timedelta(days=1))

# ----------------------------------------------------------------------------
# Bet definitions. Each returns: pick_mask (bool), side (str), price (American odds)
# ----------------------------------------------------------------------------
s = g["spread"]
tot = g["total_line"]  # PRE-GAME line only (never the final total)
rest_diff = g["home_rest"] - g["away_rest"]
cold = (g["roof"].isin(["outdoors", "open"])) & (g["temp"] < 35)
dome = g["roof"].isin(["dome", "closed"])
model_edge = g["model_line"] - s  # >0 => model likes home more than market

STRATS = []


def add(sid, name, desc, mask, side_fn, price=-110):
    STRATS.append(dict(id=sid, name=name, desc=desc, mask=pd.Series(mask).fillna(False).astype(bool),
                       side=side_fn, price=price))


# side_fn returns per-game 'home' or 'away' series, or 'over'/'under'
def const(v):
    return pd.Series(v, index=g.index)


add("S01", "Home favorite ATS (spread >= 3)", "Bet the home team to cover when home is favored by 3+.",
    s >= 3, const("home"))
add("S02", "Away side vs big home favorite (spread >= 7)", "Bet the road team to cover when home is favored by 7+.",
    s >= 7, const("away"))
add("S03", "Home underdog ATS (-7 to -1)", "Bet the home underdog to cover when it is +1 to +7 underdog.",
    (s <= -1) & (s >= -7), const("home"))
add("S04", "Home big underdog ATS (spread <= -7)", "Bet the home team to cover when it is a 7+ underdog.",
    s <= -7, const("home"))
add("S05", "Over when total >= 50", "Bet the over when total line is 50 or higher.",
    tot >= 50, const("over"))
add("S06", "Under when total <= 40", "Bet the under when total line is 40 or lower.",
    tot <= 40, const("under"))
add("S07", "Under in cold outdoor games (< 35F)", "Bet the under in outdoor/open-roof games with temp < 35F.",
    cold, const("under"))
add("S08", "Over in domes / closed roofs", "Bet the over in dome or closed-roof games.",
    dome, const("over"))
add("S09", "Rest edge: 3+ more rest days", "Bet the team with 3+ more rest days to cover.",
    rest_diff.abs() >= 3, np.where(rest_diff > 0, "home", "away"))
add("S10", "Road team on short rest (<= 6 days)", "Bet the home team to cover when the road team has <= 6 days of rest.",
    g["away_rest"] <= 6, const("home"))
add("S11", "Divisional games: bet the underdog", "In divisional games, bet the underdog to cover.",
    (g["div_game"] == 1) & (s != 0), np.where(s > 0, "away", "home"))
add("S12", "Thursday games: under", "Bet the under in Thursday games.",
    g["weekday"] == "Thursday", const("under"))
assert tot.equals(g["total_line"])
add("M01", "Model edge >= 2 pts (home)", "Own-line model says home is >= 2 pts better than the market.",
    model_edge >= 2, const("home"))
add("M02", "Model edge >= 2 pts (away)", "Own-line model says away is >= 2 pts better than the market.",
    model_edge <= -2, const("away"))
add("M03", "Model edge >= 4 pts (either side)", "Largest-disagreement games: |model - market| >= 4, bet the model side.",
    model_edge.abs() >= 4, np.where(model_edge > 0, "home", "away"))


def evaluate(mask, side_arr, price=-110):
    """Vectorised grading. Returns dataframe of graded bets with win/push/profit."""
    d = g.loc[mask & played].copy()
    sd = pd.Series(side_arr, index=g.index).loc[d.index]
    m = d["margin"]
    sp = d["spread"]
    tt = d["total_pts"]
    win = pd.Series(np.nan, index=d.index)
    push = pd.Series(False, index=d.index)
    # spread bets
    is_home = sd == "home"
    is_away = sd == "away"
    win[is_home] = ((m - sp) > 0)[is_home].astype(float)
    win[is_away] = ((m - sp) < 0)[is_away].astype(float)
    push[(is_home | is_away) & ((m - sp) == 0)] = True
    # totals
    is_over = sd == "over"
    is_under = sd == "under"
    win[is_over] = (tt > d["total_line"])[is_over].astype(float)
    win[is_under] = (tt < d["total_line"])[is_under].astype(float)
    push[(is_over | is_under) & (tt == d["total_line"])] = True
    d["win"] = win
    d["push"] = push
    graded = d[~d["push"] & d["win"].notna()].copy()
    graded["side"] = sd.loc[graded.index]
    prof = american_profit(price)
    graded["profit"] = np.where(graded["win"] == 1.0, prof, -1.0)
    return graded


def wilson_lower(k, n, z=1.96):
    if n == 0:
        return float("nan")
    p = k / n
    den = 1 + z * z / n
    centre = p + z * z / (2 * n)
    adj = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (centre - adj) / den


def summarize(graded):
    n = len(graded)
    if n == 0:
        return dict(n=0, wins=0, win_rate=None, roi=None, wilson_lo=None, p_value=None)
    k = int(graded["win"].sum())
    wr = k / n
    roi = graded["profit"].mean()
    p = stats.binomtest(k, n, BREAKEVEN_110, alternative="greater").pvalue
    return dict(n=n, wins=k, win_rate=round(wr, 4), roi=round(roi, 4),
                wilson_lo=round(wilson_lower(k, n), 4), p_value=float(p))


season = g["season"]
DISC = (season >= 1999) & (season <= 2015)
VAL = (season >= 2016) & (season <= 2025)
VAL_A = (season >= 2016) & (season <= 2020)
VAL_B = (season >= 2021) & (season <= 2025)
FWD = season == 2026

rows = []
for st in STRATS:
    side_arr = st["side"]
    mask = st["mask"]
    res = {}
    for label, win_mask in [("disc", DISC), ("val", VAL), ("val_a", VAL_A), ("val_b", VAL_B), ("fwd", FWD)]:
        gr = evaluate(mask & win_mask, side_arr, st["price"])
        res[label] = summarize(gr)
    rows.append(dict(id=st["id"], name=st["name"], desc=st["desc"], price=st["price"], **{k: v for k, v in res.items()}))

N_STRAT = len(rows)
ALPHA_ADJ = 0.05 / N_STRAT
for r in rows:
    v = r["val"]
    gates = {}
    gates["G1_sample"] = v["n"] >= MIN_N
    gates["G2_wilson_lo_above_breakeven"] = (v["wilson_lo"] or 0) > BREAKEVEN_110
    gates["G3_bonferroni_p"] = (v["p_value"] is not None) and v["p_value"] < ALPHA_ADJ
    gates["G4_stable_disc_and_halves"] = all([
        (r["disc"]["win_rate"] or 0) > 0.5,
        (r["val_a"]["win_rate"] or 0) > 0.5,
        (r["val_b"]["win_rate"] or 0) > 0.5,
    ])
    gates["G5_roi_positive_val"] = (v["roi"] or -1) > 0
    r["gates"] = gates
    r["passed_all"] = all(gates.values())
    r["bonferroni_alpha"] = round(ALPHA_ADJ, 6)

rows_sorted = sorted(rows, key=lambda r: (not r["passed_all"], -(r["val"]["roi"] or -9)))
for i, r in enumerate(rows_sorted, 1):
    r["rank"] = i

# ----------------------------------------------------------------------------
# Own-line model backtest vs market
# ----------------------------------------------------------------------------
mod = g[played & g.model_line.notna() & g.spread.notna()].copy()
mod_val = mod[(mod.season >= 2016) & (mod.season <= 2025)]
mae_model = float((mod_val.model_line - mod_val.margin).abs().mean())
mae_market = float((mod_val.spread - mod_val.margin).abs().mean())
model_summary = dict(
    evaluated_games_2016_2025=int(len(mod_val)),
    mae_model_vs_margin=round(mae_model, 3),
    mae_market_vs_margin=round(mae_market, 3),
    note="Lower mean absolute error is better. Model is walk-forward (no look-ahead).",
)

# Upcoming (unplayed) games from the nflverse schedule, priced by our own model
up = g[(~played) & g.spread.notna()].copy()
up_rows = []
for _, r in up.iterrows():
    if r.season != 2026 or r.week != 9:
        continue
    ml = predict_home_margin(r_now, hfa_now, r.home_team, r.away_team)
    up_rows.append(dict(
        game_id=r.game_id, week=int(r.week), gameday=str(r.gameday.date()), gametime=r.gametime if isinstance(r.gametime, str) else None,
        away=r.away_team, home=r.home_team,
        market_spread_home=float(r.spread), total_market=float(r.total_line),
        own_line_home=round(float(ml), 2),
        edge_home_pts=round(float(ml - r.spread), 2),
    ))

# ----------------------------------------------------------------------------
# Correlations between outcomes (phi / Pearson on 0/1 indicators) with bootstrap CI
# ----------------------------------------------------------------------------
c = g[played & g.spread.notna() & g.total_line.notna() & (season >= 1999)].copy()
c = c[(c.margin != c.spread) & (c.total_pts != c.total_line)]  # drop spread/total pushes
c["home_cover"] = (c.margin - c.spread > 0).astype(int)
c["over"] = (c.total_pts > c.total_line).astype(int)
c["home_win"] = (c.margin > 0).astype(int)
fav_home = c.spread > 0
c["fav_win_su"] = np.where(fav_home, c.home_win, 1 - c.home_win)
c["fav_cover"] = np.where(fav_home, c.home_cover, 1 - c.home_cover)
c["under"] = 1 - c.over
c["high_total"] = (c.total_line >= 47).astype(int)
c["big_fav"] = (c.spread.abs() >= 7).astype(int)
c["home_fav"] = (c.spread > 0).astype(int)

VARS = {
    "home_cover": "Home covers spread",
    "fav_cover": "Favorite covers spread",
    "home_win": "Home wins straight up",
    "fav_win_su": "Favorite wins straight up",
    "over": "Game goes over total",
    "under": "Game goes under total",
    "home_fav": "Home is favored",
}
corr_rows = []
keys = list(VARS.keys())
M = {}
for a in keys:
    for b in keys:
        if a >= b:
            continue
        x = c[a].values.astype(float)
        y = c[b].values.astype(float)
        r0 = float(np.corrcoef(x, y)[0, 1])
        boots = []
        n = len(x)
        for _ in range(N_BOOT):
            idx = RNG.integers(0, n, n)
            boots.append(np.corrcoef(x[idx], y[idx])[0, 1])
        lo, hi = np.nanpercentile(boots, [2.5, 97.5])
        pval = stats.pearsonr(x, y).pvalue
        corr_rows.append(dict(a=a, b=b, label_a=VARS[a], label_b=VARS[b], r=round(r0, 4),
                              ci_lo=round(float(lo), 4), ci_hi=round(float(hi), 4),
                              p_value=float(pval), n=int(n)))
        M[(a, b)] = r0
        M[(b, a)] = r0

# Parlay: empirical joint frequency vs independence (2-leg, -110 each, both must win)
PARLAY_PAIRS = [
    ("home_cover", "home_win", "Home covers AND home wins"),
    ("home_cover", "over", "Home covers AND game goes over"),
    ("fav_cover", "under", "Favorite covers AND game goes under"),
    ("fav_win_su", "fav_cover", "Favorite wins straight up AND covers"),
    ("home_fav", "over", "Home favored AND over"),
    ("home_cover", "under", "Home covers AND game goes under"),
]
parlay_rows = []
for a, b, label in PARLAY_PAIRS:
    pa = c[a].mean()
    pb = c[b].mean()
    pab = (c[a] * c[b]).mean()
    indep = pa * pb
    dec_leg = 1 + 100 / 110
    par_dec = dec_leg * dec_leg
    ev_emp = pab * par_dec - 1
    ev_ind = indep * par_dec - 1
    parlay_rows.append(dict(
        label=label, a=a, b=b, n=int(len(c)),
        p_a=round(float(pa), 4), p_b=round(float(pb), 4),
        p_joint=round(float(pab), 4), p_indep=round(float(indep), 4),
        excess_joint=round(float(pab - indep), 4),
        decimal_odds_2leg=round(par_dec, 4),
        ev_per_unit_empirical=round(float(ev_emp), 4),
        ev_per_unit_if_independent=round(float(ev_ind), 4),
        r=round(float(M[(a, b)]), 4) if (a, b) in M else None,
    ))

# ----------------------------------------------------------------------------
# Game-level table for the site (all seasons; unverified flags)
# ----------------------------------------------------------------------------
# nfl.com game-page URLs confirmed on nfl.com in this session (exact slugs, team nicknames).
# No URL is generated from abbreviations: nfl.com uses nicknames, so a pattern would guess.
NFLCOM_VERIFIED = {
    "2025_01_KC_LAC": "https://www.nfl.com/games/chiefs-at-chargers-2025-reg-1",
    "2025_09_BAL_MIA": "https://www.nfl.com/games/ravens-at-dolphins-2025-reg-9",
    "2026_09_JAX_BAL": "https://www.nfl.com/games/jaguars-at-ravens-2026-reg-9",
    "2026_09_CIN_ATL": "https://www.nfl.com/games/bengals-at-falcons-2026-reg-9",
    "2026_09_DEN_CAR": "https://www.nfl.com/games/broncos-at-panthers-2026-reg-9",
    "2026_09_DAL_IND": "https://www.nfl.com/games/cowboys-at-colts-2026-reg-9",
    "2026_09_NYJ_KC": "https://www.nfl.com/games/jets-at-chiefs-2026-reg-9",
    "2026_09_DET_MIA": "https://www.nfl.com/games/lions-at-dolphins-2026-reg-9",
    "2026_09_CLE_NO": "https://www.nfl.com/games/browns-at-saints-2026-reg-9",
    "2026_09_NYG_PHI": "https://www.nfl.com/games/giants-at-eagles-2026-reg-9",
    "2026_09_LA_WAS": "https://www.nfl.com/games/rams-at-commanders-2026-reg-9",
    "2026_09_HOU_LAC": "https://www.nfl.com/games/texans-at-chargers-2026-reg-9",
    "2026_09_LV_SF": "https://www.nfl.com/games/raiders-at-49ers-2026-reg-9",
    "2026_09_GB_NE": "https://www.nfl.com/games/packers-at-patriots-2026-reg-9",
    "2026_09_ARI_SEA": "https://www.nfl.com/games/cardinals-at-seahawks-2026-reg-9",
    "2026_09_TB_CHI": "https://www.nfl.com/games/buccaneers-at-bears-2026-reg-9",
    "2026_09_BUF_MIN": "https://www.nfl.com/games/bills-at-vikings-2026-reg-9",
}


games_out = []
for _, r in g.iterrows():
    gi = dict(
        game_id=r.game_id, season=int(r.season), game_type=r.game_type, week=int(r.week),
        date=str(r.gameday.date()), away=r.away_team, home=r.home_team,
        away_score=None if pd.isna(r.away_score) else int(r.away_score),
        home_score=None if pd.isna(r.home_score) else int(r.home_score),
        spread_home=None if pd.isna(r.spread_line) else float(r.spread_line),
        total_line=None if pd.isna(r.total_line) else float(r.total_line),
        home_ml=None if pd.isna(r.home_moneyline) else int(r.home_moneyline),
        away_ml=None if pd.isna(r.away_moneyline) else int(r.away_moneyline),
        roof=None if pd.isna(r.roof) else r.roof,
        temp=None if pd.isna(r.temp) else float(r.temp),
        status="played" if played.loc[_] else "scheduled",
        model_line_home=None if pd.isna(r.model_line) else round(float(r.model_line), 2),
        nflverse_row=f"https://github.com/nflverse/nfldata/blob/master/data/games.csv",
        nfl_com=NFLCOM_VERIFIED.get(r.game_id),
    )
    games_out.append(gi)

# ----------------------------------------------------------------------------
# Dataset summary (for Sources / Flagged pages)
# ----------------------------------------------------------------------------
summary = dict(
    generated_for_date="2026-11-04",
    rows=int(len(g)),
    seasons=[int(g.season.min()), int(g.season.max())],
    played_rows=int(played.sum()),
    scheduled_rows=int((~played).sum()),
    duplicate_game_ids=int(g.game_id.duplicated().sum()),
    missing=dict(
        spread_line=int(g.spread_line.isna().sum()),
        total_line=int(g.total_line.isna().sum()),
        home_moneyline=int(g.home_moneyline.isna().sum()),
        temp=int(g.temp.isna().sum()),
        gametime=int(g.gametime.isna().sum()),
        roof=int(g.roof.isna().sum()),
    ),
    sign_check=dict(
        corr_result_spread_1999_2015=round(float(g.loc[played & DISC & g.spread.notna(), "margin"].corr(g.loc[played & DISC & g.spread.notna(), "spread"])), 4),
        corr_result_spread_2016_2025=round(float(g.loc[played & VAL & g.spread.notna(), "margin"].corr(g.loc[played & VAL & g.spread.notna(), "spread"])), 4),
        mean_margin_minus_spread_2016_2025=round(float((g.loc[played & VAL & g.spread.notna(), "margin"] - g.loc[played & VAL & g.spread.notna(), "spread"]).mean()), 4),
        note="Positive correlation & mean(margin - spread) ~ 0 => spread_line is home-perspective (positive = home favored).",
    ),
    spot_checks_nflcom=[
        dict(game_id="2025_01_KC_LAC", nfl_com="https://www.nfl.com/games/chiefs-at-chargers-2025-reg-1",
             nflverse=dict(away="KC", away_score=21, home="LAC", home_score=27), nfl_com_score=dict(KC=21, LAC=27), match=True),
        dict(game_id="2025_09_BAL_MIA", nfl_com="https://www.nfl.com/games/ravens-at-dolphins-2025-reg-9",
             nflverse=dict(away="BAL", away_score=28, home="MIA", home_score=6), nfl_com_score=dict(BAL=28, MIA=6), match=True),
    ],
    model=model_summary,
    strategies_tested=N_STRAT,
    bonferroni_alpha=round(ALPHA_ADJ, 6),
    breakeven_110=round(BREAKEVEN_110, 4),
    strategies_passing_all_gates=int(sum(r["passed_all"] for r in rows)),
)

# Write JSON
def dump(name, obj):
    with open(OUT / name, "w") as f:
        json.dump(obj, f, indent=1, default=lambda o: float(o) if isinstance(o, (np.floating,)) else (int(o) if isinstance(o, np.integer) else str(o)))


dump("strategies.json", rows_sorted)
dump("correlations.json", dict(variables=VARS, n=int(len(c)), pairs=corr_rows, parlays=parlay_rows,
                               bootstrap_resamples=N_BOOT, seed=20261104))
dump("own_lines.json", dict(model=dict(
        type="Walk-forward time-decayed ridge rating model",
        lambda_ridge=LAMBDA, half_life_days=HALF_LIFE_DAYS,
        note="Ratings use only games played strictly before the game being priced."),
    backtest=model_summary, upcoming_week9_2026=up_rows,
    ratings_now=sorted([dict(team=t, rating=round(float(r_now[TIDX[t]]), 2)) for t in TEAMS], key=lambda d: -d["rating"]),
    home_field_advantage=round(float(hfa_now), 2)))
dump("games.json", games_out)
dump("summary.json", summary)

print("strategies:", N_STRAT, "passing all gates:", summary["strategies_passing_all_gates"])
for r in rows_sorted:
    v = r["val"]
    print(f'{r["rank"]:>2} {r["id"]} {r["name"][:44]:44s} val n={v["n"]:>4} wr={v["win_rate"]} roi={v["roi"]} lo={v["wilson_lo"]} p={v["p_value"]:.4f} pass={r["passed_all"]}')
print("model:", model_summary)
print("upcoming:", len(up_rows))
print("parlays:", [(p["label"], p["p_joint"], p["p_indep"]) for p in parlay_rows])
