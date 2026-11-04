#!/usr/bin/env python3
"""T06/T07/T08 - Strategy library. Every strategy is a pre-registered rule that emits bets.

Rules of the road
-----------------
* A strategy may only read own_lines.csv (walk-forward own numbers) and the market columns of
  the same game. Nothing else, and never a result column, is used to *choose* a bet.
* Prices are the real American odds in the source data. Where the source has no price for a
  market (opening lines, team totals, parlays) the assumed price is written into the bet row in
  `price_source`, and the assumption is repeated on the site and on the Flagged for Review page.
* Every bet is 1 unit unless the strategy declares a staking rule (S03 uses quarter-Kelly, the
  stake is recorded per bet).
"""
from __future__ import annotations

import json
from itertools import combinations

import numpy as np
import pandas as pd
from scipy.stats import norm

import lib_engine as E

OUT = E.OUT
BETS = OUT / "bets"
SEED = 20261104


# --------------------------------------------------------------------------- helpers


def price_or_none(row, side: str, market: str) -> float:
    if market == "spread":
        return row.home_spread_odds if side == "home" else row.away_spread_odds
    if market == "total":
        return row.over_odds if side == "over" else row.under_odds
    if market == "moneyline":
        return row.home_moneyline if side == "home" else row.away_moneyline
    return np.nan


def settle(row, market: str, side: str, line, price: float) -> tuple[str, float]:
    """Return (outcome, profit) for a 1-unit bet. Outcome in {win, loss, push}."""
    if market == "spread":
        margin = row.home_score - row.away_score
        adj = margin - line if side == "home" else -margin + line
        if adj == 0:
            return "push", 0.0
        win = adj > 0
    elif market == "total":
        if row.total_score == line:
            return "push", 0.0
        win = (row.total_score > line) if side == "over" else (row.total_score < line)
    elif market == "moneyline":
        if row.home_score == row.away_score:
            return "push", 0.0
        win = (row.home_score > row.away_score) if side == "home" else (row.home_score < row.away_score)
    elif market == "team_total":
        pts = row.home_score if side == "home" else row.away_score
        if pts == line:
            return "push", 0.0
        win = pts > line
    else:
        raise ValueError(market)
    return ("win", E.profit_per_unit(price)) if win else ("loss", -1.0)


def build_frame() -> pd.DataFrame:
    l = pd.read_csv(OUT / "own_lines.csv")
    # market price columns first appear in 2006 (audit check A11); keep one window for all
    # strategies so that ROI numbers are comparable across the leaderboard.
    l = l[l.season >= E.EVAL_FIRST_SEASON].copy()
    games = E.load_games()
    extra = games[["game_id", "home_rest", "away_rest", "div_game", "roof", "surface"]]
    l = l.merge(extra, on="game_id", how="left")
    l["total_score"] = l.home_score + l.away_score
    l["home_implied_team_total"] = l.total_line / 2 + l.spread_line / 2
    l["away_implied_team_total"] = l.total_line / 2 - l.spread_line / 2
    l["model_home_pts"] = (l.model_total + l.model_margin) / 2
    l["model_away_pts"] = (l.model_total - l.model_margin) / 2
    l["rest_diff"] = l.home_rest - l.away_rest
    return l


def build_opens() -> pd.DataFrame:
    """Opening lines. sc_lines covers 2013-2020, initial_lines covers 2021. Both files are
    underspecified upstream (no timestamp, no book beyond an abbreviation), so the resulting
    table is flagged as third-party and unverified at a primary source."""
    sc = pd.read_csv(E.RAW / "sc_lines.csv", low_memory=False)
    il = pd.read_csv(E.RAW / "initial_lines.csv", low_memory=False)
    games = E.load_games()
    # sc_lines.game_id is the NFL.com game key, which nfldata stores in `old_game_id`
    gsis = games.assign(gsis_int=pd.to_numeric(games.old_game_id, errors="coerce").astype("Int64"))[
        ["game_id", "gsis_int", "home_team", "away_team", "season"]]

    sc = sc.assign(gsis_int=pd.to_numeric(sc.game_id, errors="coerce").astype("Int64")).drop(
        columns=[c for c in ["game_id", "week", "away_team", "home_team"] if c in sc.columns])
    sc = sc.merge(gsis, on="gsis_int", how="inner")
    # The SuperContest file is one row per team: that team's handicap (team perspective).
    sc_home = sc[sc.side == sc.home_team][["game_id", "line"]].rename(columns={"line": "open_home_line"})
    sc_away = sc[sc.side == sc.away_team][["game_id", "line"]].rename(columns={"line": "open_away_line"})
    sc_open = sc_home.merge(sc_away, on="game_id", how="outer")
    sc_open["open_source"] = "sc_lines (SuperContest)"

    il = il.assign(game_id=il.about.astype(str))
    il_home = il[(il.type == "SPREAD")].merge(
        games[["game_id", "home_team"]], on="game_id", how="inner")
    il_home = il_home[il_home.side == il_home.home_team][["game_id", "line"]].rename(
        columns={"line": "open_home_line"})
    il_away = il[(il.type == "SPREAD")].merge(
        games[["game_id", "away_team"]], on="game_id", how="inner")
    il_away = il_away[il_away.side == il_away.away_team][["game_id", "line"]].rename(
        columns={"line": "open_away_line"})
    il_open = il_home.merge(il_away, on="game_id", how="outer")
    il_open["open_source"] = "initial_lines (WSGT)"

    tot = il[il.type == "TOTAL"][["game_id", "side", "line"]]
    tot_open = tot.pivot_table(index="game_id", columns="side", values="line").reset_index()
    tot_open = tot_open.rename(columns={"Over": "open_total_line"})[["game_id", "open_total_line"]]

    opens = pd.concat([sc_open, il_open], ignore_index=True).drop_duplicates("game_id")
    opens = opens.merge(tot_open, on="game_id", how="left")
    return opens


def bets_from(picks: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(picks)


def evaluate(df: pd.DataFrame, strategy_id: str, name: str, description: str,
             market: str, price_source: str, gate_flags: list[str]) -> dict:
    played = df[df.outcome.isin(["win", "loss", "push"])].copy()
    n = len(played)
    wins = int((played.outcome == "win").sum())
    losses = int((played.outcome == "loss").sum())
    pushes = int((played.outcome == "push").sum())
    staked = float(played.stake.sum())
    profit = float(played.profit.sum())
    roi = profit / staked * 100 if staked > 0 else np.nan
    return {
        "id": strategy_id,
        "name": name,
        "description": description,
        "market": market,
        "price_source": price_source,
        "gate_flags": gate_flags,
        "n_bets": n,
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "staked_units": round(staked, 3),
        "profit_units": round(profit, 3),
        "roi_pct": round(roi, 3) if roi == roi else None,
        "first_season": int(played.season.min()) if n else None,
        "last_season": int(played.season.max()) if n else None,
    }


# --------------------------------------------------------------------------- strategies


def run_singles(f: pd.DataFrame, opens: pd.DataFrame) -> list[tuple[str, dict, pd.DataFrame]]:
    out = []
    rng = np.random.default_rng(SEED)
    d = f[f.result.notna() & f.spread_line.notna()].copy()
    d["edge"] = d.model_margin - d.spread_line

    def spread_bets(sub: pd.DataFrame, min_edge: float, sid: str, sname: str, desc: str,
                    flags: list[str], kelly: bool = False) -> tuple:
        picks = []
        for row in sub.itertuples():
            if abs(row.edge) < min_edge:
                continue
            side = "home" if row.edge > 0 else "away"
            price = price_or_none(row, side, "spread")
            if not np.isfinite(price):
                continue
            stake = 1.0
            if kelly:
                p = norm.cdf(row.edge / row.sigma_margin)  # prob the bet wins (ignoring pushes)
                dec = E.american_to_decimal(price)
                b = dec - 1
                k = max((p * b - (1 - p)) / b, 0.0) if b > 0 else 0.0
                stake = round(min(0.25 * k * 4, 4.0), 3)  # quarter Kelly, capped at 4u
                if stake <= 0:
                    continue
            oc, pr = settle(row, "spread", side, row.spread_line, price)
            picks.append({
                "strategy_id": sid, "game_id": row.game_id, "season": row.season, "week": row.week,
                "gameday": row.gameday, "market": "spread", "side": side, "line": row.spread_line,
                "price": price, "price_source": "games.csv home/away_spread_odds",
                "stake": stake, "outcome": oc, "profit": pr * stake,
                "model_edge": round(float(row.edge), 3),
                "closing_line": row.spread_line, "own_line": round(float(row.model_margin), 3),
            })
        df = bets_from(picks)
        return sid, evaluate(df, sid, sname, desc, "spread",
                             "real price (games.csv)", flags), df

    out.append(spread_bets(d, 2.0, "S01", "Spread edge 2.0+ (flat 1u)",
                           "Bet the side where the own line beats the market line by >= 2.0 points.",
                           ["A06", "A12"]))
    out.append(spread_bets(d, 3.5, "S02", "Spread edge 3.5+ (flat 1u)",
                           "High-conviction subset of S01: >= 3.5 points of disagreement.",
                           ["A06", "A12"]))
    out.append(spread_bets(d, 2.0, "S03", "Spread edge 2.0+ (quarter-Kelly)",
                           "Same entries as S01, staked with quarter-Kelly on the model win "
                           "probability, capped at 4 units.", ["A06", "A12"], kelly=True))
    out.append(spread_bets(d[(d.week <= 4)], 3.0, "S10", "Weeks 1-4 spread edge 3.0+",
                           "Early-season subset: models may hold an information edge before the "
                           "market has a full season of evidence.", ["A06", "A12"]))
    out.append(spread_bets(d[(d.div_game == 1)], 2.5, "S13", "Divisional games, edge 2.5+",
                           "Divisional rematches are the most-scouted games on the schedule; test "
                           "whether the model's edge survives there.", ["A06", "A12"]))
    rest = d[(d.rest_diff.abs() >= 3)]
    out.append(spread_bets(rest, 1.5, "S11", "Rest advantage 3+ days, edge 1.5+",
                           "Teams with a rest edge of at least three days, model edge >= 1.5.",
                           ["A06", "A12"]))

    # ---- totals
    dt = f[f.total.notna() & f.total_line.notna()].copy()
    dt["edge_t"] = dt.model_total - dt.total_line

    def total_bets(sub: pd.DataFrame, min_edge: float, sid, sname, desc, flags):
        picks = []
        for row in sub.itertuples():
            if abs(row.edge_t) < min_edge:
                continue
            side = "over" if row.edge_t > 0 else "under"
            price = price_or_none(row, side, "total")
            if not np.isfinite(price):
                continue
            oc, pr = settle(row, "total", side, row.total_line, price)
            picks.append({
                "strategy_id": sid, "game_id": row.game_id, "season": row.season, "week": row.week,
                "gameday": row.gameday, "market": "total", "side": side, "line": row.total_line,
                "price": price, "price_source": "games.csv over_odds/under_odds",
                "stake": 1.0, "outcome": oc, "profit": pr,
                "model_edge": round(float(row.edge_t), 3),
                "closing_line": row.total_line, "own_line": round(float(row.model_total), 3),
            })
        df = bets_from(picks)
        return sid, evaluate(df, sid, sname, desc, "total", "real price (games.csv)", flags), df

    out.append(total_bets(dt, 2.5, "S04", "Totals edge 2.5+ (flat 1u)",
                          "Over/under where the own total beats the market total by >= 2.5.",
                          ["A08", "A13"]))
    out.append(total_bets(dt, 1.5, "S05", "Totals edge 1.5+ (flat 1u)",
                          "Wider net on totals: >= 1.5 points of disagreement.", ["A08", "A13"]))

    # ---- moneyline value
    picks = []
    for row in f[f.result.notna()].itertuples():
        if not (np.isfinite(row.home_moneyline) and np.isfinite(row.away_moneyline)):
            continue
        ph = norm.cdf(row.model_margin / row.sigma_margin)
        for side, p, price in (("home", ph, row.home_moneyline), ("away", 1 - ph, row.away_moneyline)):
            payout = E.profit_per_unit(price)
            ev = p * payout - (1 - p)
            if ev >= 0.05:
                oc, pr = settle(row, "moneyline", side, np.nan, price)
                picks.append({
                    "strategy_id": "S06", "game_id": row.game_id, "season": row.season,
                    "week": row.week, "gameday": row.gameday, "market": "moneyline", "side": side,
                    "line": np.nan, "price": price, "price_source": "games.csv moneylines",
                    "stake": 1.0, "outcome": oc, "profit": pr,
                    "model_edge": round(float(ev), 4),
                    "closing_line": np.nan, "own_line": round(float(p), 4),
                })
                break
    df = bets_from(picks)
    out.append(("S06", evaluate(df, "S06", "Moneyline EV 5%+",
                                "Bet the moneyline side whose model win probability implies at "
                                "least 5% expected value at the listed price.", "moneyline",
                                "real price (games.csv)", ["A11"]), df))

    # ---- opening-line strategies (open -> close line movement)
    dm = d.merge(opens, on="game_id", how="inner")
    dm = dm.dropna(subset=["open_home_line"])

    def open_strategy(sid, sname, desc, fade: bool, flags):
        """Bet at the CLOSING line after observing the open->close move (actionable ordering:
        the move is known before the close). Real prices from games.csv are used."""
        picks = []
        for row in dm.itertuples():
            open_home = -row.open_home_line    # home-perspective opening spread
            move = row.spread_line - open_home  # close - open, home perspective
            if abs(move) < 1.5:
                continue
            bet_home = (move < 0) if fade else (move > 0)
            # fade: the market moved toward the home side (move>0) -> take the away side
            side = "home" if bet_home else "away"
            price = row.home_spread_odds if side == "home" else row.away_spread_odds
            if not np.isfinite(price):
                continue
            oc, pr = settle(row, "spread", side, row.spread_line, price)
            picks.append({
                "strategy_id": sid, "game_id": row.game_id, "season": row.season, "week": row.week,
                "gameday": row.gameday, "market": "spread", "side": side, "line": row.spread_line,
                "price": price, "price_source": "real closing price (games.csv)",
                "stake": 1.0, "outcome": oc, "profit": pr,
                "model_edge": round(float(move), 3), "line_move": round(float(move), 3),
                "open_line": open_home, "closing_line": row.spread_line,
                "own_line": round(float(row.model_margin), 3),
            })
        df = bets_from(picks)
        return sid, evaluate(df, sid, sname, desc, "spread",
                             "real closing price (games.csv)", flags), df

    out.append(open_strategy("S07", "Fade a 1.5+ point line move",
                            "When the closing line sits >= 1.5 points away from the opener, bet the "
                            "side the market moved away from, at the closing price.",
                            True, ["A14"]))
    out.append(open_strategy("S08", "Follow a 1.5+ point line move",
                             "Same trigger, but bet with the move at the closing price - the "
                             "momentum/steam hypothesis.", False, ["A14"]))

    # model vs the OPENING line, with CLV measurement
    picks = []
    for row in dm.itertuples():
        open_home = -row.open_home_line    # home-perspective opening spread
        edge_open = row.model_margin - open_home
        if abs(edge_open) < 2.0:
            continue
        side = "home" if edge_open > 0 else "away"
        price = -110.0
        oc, pr = settle(row, "spread", side, open_home, price)
        clv = (row.spread_line - open_home) * (1 if side == "home" else -1)
        picks.append({
            "strategy_id": "S09", "game_id": row.game_id, "season": row.season, "week": row.week,
            "gameday": row.gameday, "market": "spread", "side": side, "line": open_home,
            "price": price, "price_source": "ASSUMED -110 (opening price not in source)",
            "stake": 1.0, "outcome": oc, "profit": pr,
            "model_edge": round(float(edge_open), 3), "clv_points": round(float(clv), 3),
            "open_line": row.open_home_line, "closing_line": row.spread_line,
            "own_line": round(float(row.model_margin), 3),
        })
    df = bets_from(picks)
    out.append(("S09", evaluate(df, "S09", "Model vs opening line, edge 2.0+",
                                "Bet at the opening line where the own line beats the opener by "
                                ">= 2.0 points; the closing-line value column measures whether the "
                                "market later moved toward the model.", "spread",
                                "ASSUMED -110 (opening price not in source)", ["A14"]), df))

    # ---- team totals (synthetic market, derived from spread + total)
    picks = []
    for row in f[f.result.notna() & f.total_line.notna() & f.spread_line.notna()].itertuples():
        for side, model_pts, implied in (
                ("home", row.model_home_pts, row.home_implied_team_total),
                ("away", row.model_away_pts, row.away_implied_team_total)):
            edge = model_pts - implied
            if abs(edge) < 2.5:
                continue
            price = -110.0
            oc, pr = settle(row, "team_total", side, implied, price)
            picks.append({
                "strategy_id": "S12", "game_id": row.game_id, "season": row.season, "week": row.week,
                "gameday": row.gameday, "market": "team_total", "side": side, "line": round(implied, 2),
                "price": price, "price_source": "ASSUMED -110 (synthetic market)",
                "stake": 1.0, "outcome": oc, "profit": pr,
                "model_edge": round(float(edge), 3), "closing_line": np.nan,
                "own_line": round(float(model_pts), 2),
            })
    df = bets_from(picks)
    out.append(("S12", evaluate(df, "S12", "Team-total derivative, edge 2.5+",
                                "Own team point projection vs the team total implied by the market "
                                "spread and total. No sportsbook team-total price exists in the "
                                "source, so the line is synthetic and the price is assumed.",
                                "team_total", "ASSUMED -110 (synthetic market)", ["A06", "A08"]), df))

    # ---- placebo control: random side, same games and schedule as S01's universe
    picks = []
    for row in d.itertuples():
        side = "home" if rng.random() < 0.5 else "away"
        price = price_or_none(row, side, "spread")
        if not np.isfinite(price):
            continue
        oc, pr = settle(row, "spread", side, row.spread_line, price)
        picks.append({
            "strategy_id": "S00", "game_id": row.game_id, "season": row.season, "week": row.week,
            "gameday": row.gameday, "market": "spread", "side": side, "line": row.spread_line,
            "price": price, "price_source": "real price (games.csv)", "stake": 1.0,
            "outcome": oc, "profit": pr, "model_edge": np.nan, "closing_line": row.spread_line,
            "own_line": round(float(row.model_margin), 3),
        })
    df = bets_from(picks)
    out.append(("S00", evaluate(df, "S00", "Placebo control: random side every game",
                                "Coin flip on every game with a priced spread. Used to calibrate how "
                                "much ROI variance is pure luck at this sample size.", "spread",
                                "real price (games.csv)", ["A06"]), df))
    return out


def run_parlays(f: pd.DataFrame, singles: dict[str, pd.DataFrame]) -> list[tuple[str, dict, pd.DataFrame]]:
    out = []
    d = f[f.result.notna() & f.spread_line.notna()].copy()
    d["edge"] = d.model_margin - d.spread_line

    def two_leg(sid, sname, desc, legs_per_week: int, flags):
        picks = []
        for (season, week), wk in d.groupby(["season", "week"]):
            cand = wk[wk.edge.abs() >= 2.0].copy()
            if len(cand) < legs_per_week:
                continue
            cand = cand.reindex(cand.edge.abs().sort_values(ascending=False).index).head(legs_per_week)
            dec = 1.0
            ok = True
            leg_info = []
            for row in cand.itertuples():
                side = "home" if row.edge > 0 else "away"
                price = price_or_none(row, side, "spread")
                if not np.isfinite(price):
                    ok = False
                    break
                dec *= E.american_to_decimal(price)
                leg_info.append(f"{row.game_id}:{side}@{row.spread_line}")
            if not ok:
                continue
            profits = []
            wins = 0
            for (row, leg) in zip(cand.itertuples(), leg_info):
                side = "home" if row.edge > 0 else "away"
                oc, pr = settle(row, "spread", side, row.spread_line,
                                row.home_spread_odds if side == "home" else row.away_spread_odds)
                profits.append(pr)
                if oc == "win":
                    wins += 1
                if oc == "push":
                    dec = dec  # push leg is returned at even money by convention; handled below
            if profits.count(0.0):
                continue  # drop weeks with a push leg so the payout stays exact
            outcome = "win" if wins == legs_per_week else "loss"
            profit = (dec - 1) if outcome == "win" else -1.0
            picks.append({
                "strategy_id": sid, "game_id": "+".join(leg_info), "season": season, "week": week,
                "gameday": cand.gameday.min(), "market": "parlay", "side": "n/a",
                "line": np.nan, "price": round((dec - 1) * 100, 2) if dec >= 2 else round(-100 / (dec - 1), 2),
                "price_source": "product of the real leg prices (no parlay price in source)",
                "stake": 1.0, "outcome": outcome, "profit": round(profit, 4),
                "legs": legs_per_week, "decimal_odds": round(dec, 4),
                "model_edge": round(float(cand.edge.abs().mean()), 3),
                "closing_line": np.nan, "own_line": np.nan,
            })
        df = bets_from(picks)
        return sid, evaluate(df, sid, sname, desc, "parlay",
                             "product of real leg prices", flags), df

    out.append(two_leg("P01", "Two-leg cross-game parlay (top 2 edges)",
                       "Each week, parlay the two largest spread disagreements. The parlay price is "
                       "the product of the two real leg prices; sportsbooks do not publish this in "
                       "the source data.", 2, ["A06", "A12"]))
    out.append(two_leg("P02", "Three-leg cross-game parlay (top 3 edges)",
                       "Same rule with three legs; multiplication of three prices quadruples the "
                       "variance of the outcome.", 3, ["A06", "A12"]))

    # ---- same-game parlays: spread + total in the same game
    ds = f[f.result.notna() & f.spread_line.notna() & f.total_line.notna()].copy()
    ds["edge"] = ds.model_margin - ds.spread_line
    ds["edge_t"] = ds.model_total - ds.total_line

    picks = []
    for row in ds.itertuples():
        if abs(row.edge) < 2.0 or abs(row.edge_t) < 2.0:
            continue
        side = "home" if row.edge > 0 else "away"
        tside = "over" if row.edge_t > 0 else "under"
        p1 = price_or_none(row, side, "spread")
        p2 = price_or_none(row, tside, "total")
        if not (np.isfinite(p1) and np.isfinite(p2)):
            continue
        oc1, _ = settle(row, "spread", side, row.spread_line, p1)
        oc2, _ = settle(row, "total", tside, row.total_line, p2)
        if "push" in (oc1, oc2):
            continue
        dec = E.american_to_decimal(p1) * E.american_to_decimal(p2)
        win = oc1 == "win" and oc2 == "win"
        picks.append({
            "strategy_id": "P03", "game_id": row.game_id, "season": row.season, "week": row.week,
            "gameday": row.gameday, "market": "sgp", "side": f"{side}+{tside}", "line": np.nan,
            "price": round((dec - 1) * 100, 2), "price_source": "independent product of leg prices",
            "stake": 1.0, "outcome": "win" if win else "loss",
            "profit": round(dec - 1, 4) if win else -1.0, "legs": 2, "decimal_odds": round(dec, 4),
            "model_edge": round(float(min(abs(row.edge), abs(row.edge_t))), 3),
            "closing_line": np.nan, "own_line": np.nan,
        })
    df = bets_from(picks)
    out.append(("P03", evaluate(df, "P03", "Same-game parlay: spread + total",
                                "Both legs must clear the same 2.0-point threshold. Priced as the "
                                "independent product of the two leg prices - real books apply "
                                "correlation pricing, which is not in the source data.",
                                "sgp", "independent product of leg prices", ["A06", "A08"]), df))

    picks = []
    for row in ds.itertuples():
        if not (np.isfinite(row.home_moneyline) and np.isfinite(row.away_moneyline)):
            continue
        ph = norm.cdf(row.model_margin / row.sigma_margin)
        side = "home" if (ph - E.american_to_prob(row.home_moneyline)) > (E.american_to_prob(row.away_moneyline) - (1 - ph)) else "away"
        ev_ml = (ph * E.profit_per_unit(row.home_moneyline) - (1 - ph)) if side == "home" else \
                ((1 - ph) * E.profit_per_unit(row.away_moneyline) - ph)
        if ev_ml < 0.04 or abs(row.edge_t) < 2.0:
            continue
        tside = "over" if row.edge_t > 0 else "under"
        p1 = price_or_none(row, side, "moneyline")
        p2 = price_or_none(row, tside, "total")
        if not (np.isfinite(p1) and np.isfinite(p2)):
            continue
        oc1, _ = settle(row, "moneyline", side, np.nan, p1)
        oc2, _ = settle(row, "total", tside, row.total_line, p2)
        if "push" in (oc1, oc2):
            continue
        dec = E.american_to_decimal(p1) * E.american_to_decimal(p2)
        win = oc1 == "win" and oc2 == "win"
        picks.append({
            "strategy_id": "P04", "game_id": row.game_id, "season": row.season, "week": row.week,
            "gameday": row.gameday, "market": "sgp", "side": f"{side}+{tside}", "line": np.nan,
            "price": round((dec - 1) * 100, 2), "price_source": "independent product of leg prices",
            "stake": 1.0, "outcome": "win" if win else "loss",
            "profit": round(dec - 1, 4) if win else -1.0, "legs": 2, "decimal_odds": round(dec, 4),
            "model_edge": round(float(ev_ml), 4), "closing_line": np.nan, "own_line": np.nan,
        })
    df = bets_from(picks)
    out.append(("P04", evaluate(df, "P04", "Same-game parlay: moneyline + total",
                                "Moneyline leg needs 4%+ model EV, total leg needs 2.0+ points of "
                                "model edge. Independent-product pricing, as for P03.", "sgp",
                                "independent product of leg prices", ["A11", "A08"]), df))
    return out


def run_props() -> list[dict]:
    """Player-prop strategies. Data check: the pipeline needs player-week outcomes (passing,
    rushing, receiving, receptions, targets...). The only open NFL data release that carries them
    (nflverse-data `player_stats`) is served from GitHub release assets, which this environment
    cannot reach (egress is limited to github.com, codeload, api.github.com, PyPI, npm). Rather
    than invent numbers, every player-prop strategy is BLOCKED and published as such."""
    return [
        {"id": "PR01", "name": "QB passing yards, over/under",
         "status": "blocked",
         "design": ("Project with a shrunk per-attempt rate x projected attempts (opponent pass-rate "
                    "allowed, game script from the own spread). Bet when the projection beats the "
                    "market prop line by >= 8%."),
         "blocker": "player-week passing outcomes and player prop prices are not available from any "
                    "reachable source.",
         "would_need": "nflverse-data player_stats release (player, week, passing_yards) plus a "
                       "sportsbook prop feed.",
         "source_url": "https://github.com/nflverse/nflverse-data/releases/tag/player_stats"},
        {"id": "PR02", "name": "Receptions, over/under",
         "status": "blocked",
         "design": ("Receptions are close to a Poisson process on target share x team pass volume. "
                    "Model with a negative-binomial and bet only when the model tail probability "
                    "differs from the implied prop probability by >= 6%."),
         "blocker": "player-week receiving outcomes are not available from any reachable source.",
         "would_need": "nflverse-data player_stats release (receptions, targets).",
         "source_url": "https://github.com/nflverse/nflverse-data/releases/tag/player_stats"},
        {"id": "PR03", "name": "Prop combo: QB passing + own WR receiving (same game)",
         "status": "blocked",
         "design": ("These legs are positively correlated through shared dropbacks, so the joint "
                    "probability is far above the product of the leg probabilities. A combo should "
                    "only be taken when the book's correlation pricing is worse than the empirical "
                    "joint probability (see the analytic correlation model on the Correlation page)."),
         "blocker": "needs both player-week outcomes and sportsbook same-game-parlay pricing.",
         "would_need": "player-week outcomes + an SGP price feed.",
         "source_url": "https://github.com/nflverse/nflverse-data/releases/tag/player_stats"},
    ]


def main() -> int:
    BETS.mkdir(parents=True, exist_ok=True)
    f = build_frame()
    opens = build_opens()
    print("open-line coverage:", len(opens), "games",
          int(opens.open_home_line.notna().sum()), "with a home opening line")

    results = []
    for sid, meta, df in run_singles(f, opens) + run_parlays(f, {}):
        df.to_csv(BETS / f"{sid}.csv", index=False)
        results.append(meta)
    props = run_props()

    payload = {
        "generated_at_utc": E.MANIFEST["generated_at_utc"],
        "source_commit_sha": E.MANIFEST["commit_sha"],
        "seed": SEED,
        "eval_window": [int(E.EVAL_FIRST_SEASON), 2026],
        "strategies": results,
        "blocked_props": props,
    }
    (OUT / "strategies.json").write_text(json.dumps(payload, indent=2) + "\n")

    tbl = pd.DataFrame(results)[["id", "n_bets", "wins", "losses", "pushes", "roi_pct",
                                 "profit_units", "first_season", "last_season"]]
    print(tbl.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
