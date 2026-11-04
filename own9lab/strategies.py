"""Pre-registered strategy catalogue, bet generation and settlement.

All parameters below were fixed before any evaluation was run (registration hash is
written to lab/data/registration.json). Bets are generated only for regular-season
games whose final score is officially VERIFIED and whose required market fields are
present. Prices are the closing American odds recorded in nflverse/nfldata
(UNVERIFIED secondary source) unless a strategy is explicitly marked `assumed_price`.

Sign conventions (nflverse): spread_line > 0 means the home team is favoured by that
many points; result = home_score - away_score.
"""
import hashlib, json
import numpy as np
import pandas as pd
from . import config as C

# ---------------------------------------------------------------- odds helpers
def dec(american):
    a = np.asarray(american, dtype=float)
    return np.where(a > 0, 1 + a / 100.0, 1 + 100.0 / np.abs(a))


def grade(diff):
    """+1 win, 0 push, -1 loss from a cover margin."""
    return np.sign(diff).astype(int)


def profit_single(outcome, d):
    return np.where(outcome > 0, d - 1, np.where(outcome < 0, -1.0, 0.0))


def novig_home(ml_home, ml_away):
    ph, pa = 1 / dec(ml_home), 1 / dec(ml_away)
    return ph / (ph + pa)


# ---------------------------------------------------------------- registry
REGISTRY = [
    # id, kind, family, assumed_price, description
    ("S01", "single", "model", False, "Model spread edge >= 2.0 pts: bet the side the originated spread favours vs the closing spread"),
    ("S02", "single", "model", False, "Model spread edge >= 4.0 pts (same rule, stricter threshold)"),
    ("S03", "single", "model", False, "Model total edge >= 3.0 pts: over if originated total > closing total, else under"),
    ("S04", "single", "model", False, "Model total edge >= 6.0 pts (same rule, stricter threshold)"),
    ("S05", "single", "model", False, "Model moneyline edge: model win prob minus no-vig closing prob >= 0.05 -> bet that side's moneyline"),
    ("S06", "single", "situational", False, "Home underdogs against the spread (non-neutral sites)"),
    ("S07", "single", "situational", False, "Divisional-game underdogs against the spread"),
    ("S08", "single", "situational", False, "Underdogs of 10+ points against the spread"),
    ("S09", "single", "situational", False, "Rest edge: team with 3+ more days of rest than its opponent, against the spread"),
    ("S10", "single", "situational", False, "Wind >= 15 mph in an outdoor/open stadium: under"),
    ("S11", "single", "situational", False, "Divisional games: under"),
    ("S12", "single", "situational", False, "Heavy moneyline favourites (closing ML <= -300)"),
    ("S13", "single", "situational", False, "Long moneyline underdogs (closing ML >= +250)"),
    ("S14", "single", "situational", False, "Prime-time games (kickoff 19:00 ET or later): under"),
    ("P01", "teaser", "parlay", True, "Wong 2-team 6-pt teaser (favs -7.5..-8.5, dogs +1.5..+2.5), ASSUMED price -120"),
    ("P02", "teaser", "parlay", True, "Same Wong teaser legs, ASSUMED price -110"),
    ("P03", "parlay", "parlay", False, "2-team cross-game parlays of S01 picks (same week, chronological pairs), paid at product of closing decimal odds"),
    ("P04", "sgp", "parlay", True, "Same-game parlay: underdog ATS + under when |spread| >= 7, HYPOTHETICAL price = product of legs (as if independent)"),
    ("P05", "sgp", "parlay", True, "Same-game parlay: favourite ATS + over when |spread| >= 7, HYPOTHETICAL price = product of legs (as if independent)"),
]
TEASER_PRICE = {"P01": -120, "P02": -110}


def registration():
    spec = json.dumps(REGISTRY, sort_keys=True) + json.dumps(TEASER_PRICE, sort_keys=True)
    return {"sha256": hashlib.sha256(spec.encode()).hexdigest(), "n_strategies": len(REGISTRY),
            "dev": f"{min(C.DEV_SEASONS)}-{max(C.DEV_SEASONS)}", "test": f"{min(C.TEST_SEASONS)}-{max(C.TEST_SEASONS)}",
            "forward": f"{min(C.FORWARD_SEASONS)}-{max(C.FORWARD_SEASONS)}"}


def period(season):
    return np.where(season <= max(C.DEV_SEASONS), "DEV", np.where(season <= max(C.TEST_SEASONS), "TEST", "FWD"))


# ---------------------------------------------------------------- leg builders
def base(games, preds):
    g = games.merge(preds[["game_id", "spread_hat", "total_hat", "p_home"]], on="game_id", how="left")
    g = g[(g.game_type == "REG") & (g.score_status == "VERIFIED") & (g.season >= min(C.DEV_SEASONS))].copy()
    g["result"] = g.home_score - g.away_score
    g["total"] = g.home_score + g.away_score
    g["period"] = period(g.season)
    return g


def ats_legs(g, home_mask, away_mask, tease=0.0):
    """Legs on a side; cover margin = side margin - (side line - tease)."""
    out = []
    for side, mask in (("home", home_mask), ("away", away_mask)):
        d = g[mask & g.spread_line.notna() & g[f"{side}_spread_odds"].notna()].copy()
        if side == "home":
            d["diff"] = d.result - (d.spread_line - tease)
            d["sel"] = d.home_team + " " + fmt_line(-(d.spread_line - tease))
        else:
            d["diff"] = -d.result - (-d.spread_line - tease)
            d["sel"] = d.away_team + " " + fmt_line(d.spread_line + tease)
        d["odds"] = d[f"{side}_spread_odds"]
        d["opp_odds"] = d["away_spread_odds" if side == "home" else "home_spread_odds"]
        d["market"] = "ATS"
        out.append(d)
    return pd.concat(out)


def tot_legs(g, over_mask, under_mask):
    out = []
    for side, mask in (("over", over_mask), ("under", under_mask)):
        d = g[mask & g.total_line.notna() & g[f"{side}_odds"].notna()].copy()
        d["diff"] = (d.total - d.total_line) * (1 if side == "over" else -1)
        d["sel"] = pd.Series([f"{side.capitalize()} {v:g}" for v in d.total_line], index=d.index, dtype=object)
        d["odds"] = d[f"{side}_odds"]
        d["opp_odds"] = d["under_odds" if side == "over" else "over_odds"]
        d["market"] = "TOTAL"
        out.append(d)
    return pd.concat(out)


def ml_legs(g, home_mask, away_mask):
    out = []
    for side, mask in (("home", home_mask), ("away", away_mask)):
        d = g[mask & g.home_moneyline.notna() & g.away_moneyline.notna()].copy()
        d["diff"] = d.result * (1 if side == "home" else -1)
        d["sel"] = d[f"{side}_team"] + " ML"
        d["odds"] = d[f"{side}_moneyline"]
        d["opp_odds"] = d["away_moneyline" if side == "home" else "home_moneyline"]
        d["market"] = "ML"
        out.append(d)
    return pd.concat(out)


def fmt_line(x):
    return pd.Series([f"{v:+g}" for v in x], index=x.index, dtype=object)


COLS = ["game_id", "season", "week", "gameday", "gametime", "period", "market", "sel", "odds", "opp_odds", "diff"]


def finish_single(sid, legs):
    b = legs[COLS].copy()
    b["outcome"] = grade(b["diff"])
    b["dec"] = dec(b.odds)
    b["profit"] = profit_single(b.outcome, b.dec)
    b["opp_profit"] = profit_single(-b.outcome, dec(b.opp_odds.fillna(-110)))
    b.loc[b.opp_odds.isna(), "opp_profit"] = np.nan
    b["strategy"] = sid
    b["n_legs"] = 1
    return b.drop(columns="diff")


def singles(g):
    out = {}
    edge = g.spread_hat - g.spread_line
    out["S01"] = ats_legs(g, edge >= 2.0, edge <= -2.0)
    out["S02"] = ats_legs(g, edge >= 4.0, edge <= -4.0)
    tedge = g.total_hat - g.total_line
    out["S03"] = tot_legs(g, tedge >= 3.0, tedge <= -3.0)
    out["S04"] = tot_legs(g, tedge >= 6.0, tedge <= -6.0)
    nv = novig_home(g.home_moneyline, g.away_moneyline)
    medge = g.p_home - nv
    out["S05"] = ml_legs(g, medge >= 0.05, medge <= -0.05)
    neutral = g.location == "Neutral"
    out["S06"] = ats_legs(g, (g.spread_line < 0) & ~neutral, pd.Series(False, index=g.index))
    div = g.div_game == 1
    out["S07"] = ats_legs(g, div & (g.spread_line < 0), div & (g.spread_line > 0))
    out["S08"] = ats_legs(g, g.spread_line <= -10, g.spread_line >= 10)
    rd = g.home_rest - g.away_rest
    out["S09"] = ats_legs(g, rd >= 3, rd <= -3)
    windy = (g.wind >= 15) & g.roof.isin(["outdoors", "open"])
    none = pd.Series(False, index=g.index)
    out["S10"] = tot_legs(g, none, windy)
    out["S11"] = tot_legs(g, none, div)
    out["S12"] = ml_legs(g, g.home_moneyline <= -300, g.away_moneyline <= -300)
    out["S13"] = ml_legs(g, g.home_moneyline >= 250, g.away_moneyline >= 250)
    prime = g.gametime.fillna("00:00") >= "19:00"
    out["S14"] = tot_legs(g, none, prime)
    return {k: finish_single(k, v) for k, v in out.items()}


def pair_within_week(legs):
    """Chronological pairing of legs within each (season, week); leftover leg dropped."""
    legs = legs.sort_values(["season", "week", "gameday", "gametime", "game_id"]).copy()
    legs["k"] = legs.groupby(["season", "week"]).cumcount() // 2
    sizes = legs.groupby(["season", "week", "k"]).game_id.transform("size")
    return legs[sizes == 2]


def combine(legs, sid, price_rule):
    rows = []
    for (season, week, k), grp in legs.groupby(["season", "week", "k"], sort=False):
        o = grp.outcome.to_numpy()
        d = grp.dec.to_numpy()
        if (o < 0).any():
            outcome, prof = -1, -1.0
        elif (o == 0).all():
            outcome, prof = 0, 0.0
        else:
            outcome, prof = price_rule(o, d)
        r = grp.iloc[0]
        rows.append({"game_id": " + ".join(grp.game_id), "season": season, "week": week, "gameday": r.gameday,
                     "gametime": r.gametime, "period": r.period, "market": sid, "sel": " | ".join(grp.sel),
                     "odds": np.nan, "outcome": outcome, "dec": np.nan, "profit": prof, "strategy": sid,
                     "n_legs": len(grp)})
    return pd.DataFrame(rows)


def multis(g, singles_out):
    out = {}
    # --- Wong teaser legs (side line L_S in [7.5, 8.5] favourites or [-2.5, -1.5] dogs), teased 6 pts
    Lh = g.spread_line          # home side line (home favoured by L)
    Lh_ok = Lh.between(7.5, 8.5) | Lh.between(-2.5, -1.5)
    La_ok = (-Lh).between(7.5, 8.5) | (-Lh).between(-2.5, -1.5)
    legs = ats_legs(g, Lh_ok, La_ok, tease=6.0)
    legs["outcome"] = grade(legs["diff"])
    legs["dec"] = np.nan
    legs = pair_within_week(legs)
    for sid, price in TEASER_PRICE.items():
        payout = float(dec(price)) - 1
        # one leg pushes, other wins -> push (assumed house rule, documented)
        rule = (lambda o, d, payout=payout: (1, payout) if (o > 0).all() else (0, 0.0))
        out[sid] = combine(legs, sid, rule)
    # --- P03: 2-team parlays of S01 picks at product of closing decimal odds (pushed legs drop out)
    s1 = singles_out["S01"].copy()
    s1 = s1.drop_duplicates("game_id")
    p = pair_within_week(s1)

    def true_odds(o, d):
        dd = np.where(o == 0, 1.0, d)
        return 1, float(np.prod(dd) - 1)
    out["P03"] = combine(p, "P03", true_odds)
    # --- same-game parlays (hypothetical independent pricing)
    big = g.spread_line.abs() >= 7
    fav_home = g.spread_line > 0
    dog_ats = ats_legs(g, big & ~fav_home, big & fav_home)
    fav_ats = ats_legs(g, big & fav_home, big & ~fav_home)
    none = pd.Series(False, index=g.index)
    under = tot_legs(g, none, big)
    over = tot_legs(g, big, none)
    for sid, a, b in (("P04", dog_ats, under), ("P05", fav_ats, over)):
        both = pd.concat([a, b])
        both = both[both.game_id.isin(set(a.game_id) & set(b.game_id))].copy()
        both["outcome"] = grade(both["diff"])
        both["dec"] = dec(both.odds)
        res = []
        for gid, grp in both.groupby("game_id", sort=False):
            o, d = grp.outcome.to_numpy(), grp.dec.to_numpy()
            if (o < 0).any():
                outcome, prof = -1, -1.0
            elif (o == 0).all():
                outcome, prof = 0, 0.0
            else:
                outcome, prof = true_odds(o, d)
            r = grp.iloc[0]
            res.append({"game_id": gid, "season": r.season, "week": r.week, "gameday": r.gameday,
                        "gametime": r.gametime, "period": r.period, "market": sid, "sel": " | ".join(grp.sel),
                        "odds": np.nan, "outcome": outcome, "dec": float(np.prod(d)), "profit": prof,
                        "strategy": sid, "n_legs": 2})
        out[sid] = pd.DataFrame(res)
    return out


def all_bets(games, preds):
    g = base(games, preds)
    s = singles(g)
    m = multis(g, s)
    bets = pd.concat(list(s.values()) + list(m.values()), ignore_index=True)
    return g, bets
