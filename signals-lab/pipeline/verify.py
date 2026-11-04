"""Reconcile the parsed NFL game-center feed against official NFL.com standings pages.

For every season with a transcribed NFL.com standings file (data/verified/nfl_standings/<season>.csv) this compares, per team,
W-L-T, points for and points against computed from the regular-season games in games_feed.csv.gz.
A season is "verified" only if all 32 teams match exactly; otherwise it is excluded from modelling (fail closed).

Writes data/verified/reconciliation_standings.csv (one row per team-season) and data/verified/reconciliation_summary.csv.
"""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DERIVED, VERIFIED

NFL_TO_FRANCHISE = {"AZ": "ARI"}   # NFL.com uses AZ for Arizona; the feed uses ARI


def computed_standings(games: pd.DataFrame) -> pd.DataFrame:
    reg = games[games.game_type == "REG"]
    rows = []
    for _, g in reg.iterrows():
        for side, other in (("home", "away"), ("away", "home")):
            pf, pa = g[f"{side}_score"], g[f"{other}_score"]
            rows.append(dict(season=g.season, team=g[f"{side}_team"], w=int(pf > pa), l=int(pf < pa), t=int(pf == pa), pf=pf, pa=pa))
    return pd.DataFrame(rows).groupby(["season", "team"], as_index=False).sum()


def main():
    games = pd.read_csv(DERIVED / "games_feed.csv.gz")
    comp = computed_standings(games)
    out = []
    for f in sorted((VERIFIED / "nfl_standings").glob("*.csv")):
        off = pd.read_csv(f)
        off["team"] = off.nfl_code.replace(NFL_TO_FRANCHISE)
        m = off.merge(comp, on=["season", "team"], how="outer", suffixes=("_nfl", "_feed"), indicator=True)
        m["match"] = (m._merge == "both") & m.eval("w_nfl == w_feed and l_nfl == l_feed and t_nfl == t_feed and pf_nfl == pf_feed and pa_nfl == pa_feed")
        m = m[m.season == off.season.iloc[0]]
        out.append(m)
    res = pd.concat(out, ignore_index=True)
    cols = ["season", "team", "team_name", "w_nfl", "l_nfl", "t_nfl", "pf_nfl", "pa_nfl", "w_feed", "l_feed", "t_feed", "pf_feed", "pa_feed", "match", "source_url"]
    res[cols].to_csv(VERIFIED / "reconciliation_standings.csv", index=False)
    summ = res.groupby("season").agg(teams_official=("team_name", "count"), teams_matched=("match", "sum")).reset_index()
    summ["verified"] = (summ.teams_official == 32) & (summ.teams_matched == 32)
    summ["source_url"] = summ.season.map(lambda s: f"https://www.nfl.com/standings/league/{s}/REG")
    summ.to_csv(VERIFIED / "reconciliation_summary.csv", index=False)
    print(summ.to_string(index=False))
    bad = res[~res.match]
    if len(bad):
        print("\nMISMATCHES:"); print(bad[cols].to_string(index=False))


import re

SUFFIX = re.compile(r"\b(jr|sr|ii|iii|iv|v)\b\.?", re.I)


def _letters(x: str) -> str:
    return re.sub(r"[^a-z]", "", x.lower())


def verify_player_leaders():
    """Compare official NFL.com season leader tables with sums of the parsed game-center feed.

    A row is verified only when ALL transcribed counting stats equal the feed sums for exactly one player whose
    (abbreviated) feed name is consistent with the official full name. Players are summed across teams (season totals).
    """
    players = pd.read_csv(DERIVED / "player_games_feed.csv.gz")
    out = []
    for f in sorted((VERIFIED / "nfl_player_leaders").glob("*.csv")):
        off = pd.read_csv(f)
        season = int(off.season.iloc[0]); cat = off.category.iloc[0]
        stat_cols = [c for c in off.columns if c not in ("season", "category", "rank", "player", "source_url", "retrieved_utc")]
        feed_cols = {c: ("sack_yds_lost" if c == "sack_yds" else c) for c in stat_cols}
        players["sack_yds_lost"] = -players["sack_yds"]            # NFL.com lists sack yards lost as a positive number
        reg = players[(players.season == season) & (players.game_type == "REG")]
        agg = reg.groupby("gsis_id", as_index=False).agg({**{feed_cols[c]: "sum" for c in stat_cols}, "name": "first"})
        agg = agg.rename(columns={"sack_yds_lost": "sack_yds"})
        for _, row in off.iterrows():
            want = _letters(SUFFIX.sub("", row.player))
            cand = agg[agg.name.map(lambda n: want.endswith(_letters(n.split(".", 1)[-1])) and len(_letters(n.split(".", 1)[-1])) > 1)]
            exact = cand[(cand[stat_cols] == row[stat_cols].astype(float)).all(axis=1)]
            rec = dict(season=season, category=cat, rank=row["rank"], player_nfl=row.player, matched_feed_name=exact.name.iloc[0] if len(exact) == 1 else "",
                       gsis_id=exact.gsis_id.iloc[0] if len(exact) == 1 else "", match=len(exact) == 1, source_url=row.source_url)
            for c in stat_cols:
                rec[f"{c}_nfl"] = row[c]
            if len(exact) != 1 and len(cand):          # closest candidate for diagnosis
                near = cand.iloc[(cand[stat_cols[0]] - row[stat_cols[0]]).abs().argsort().iloc[0]]
                for c in stat_cols:
                    rec[f"{c}_feed"] = near[c]
                rec["matched_feed_name"] = "NEAREST: " + near["name"]
            out.append(rec)
    res = pd.DataFrame(out)
    res.to_csv(VERIFIED / "reconciliation_player_leaders.csv", index=False)
    summ = res.groupby(["season", "category"]).agg(rows_official=("match", "size"), rows_matched=("match", "sum")).reset_index()
    print(summ.to_string(index=False))
    bad = res[~res.match]
    if len(bad):
        print("\nUNMATCHED:"); print(bad.to_string(index=False))
    return res


def verify_2026_ytd():
    """Reconcile the in-progress 2026 regular season (nfldata schedule/results) against NFL.com standings through Week 8.

    The NFL game-center archive used for 2015-2025 has no 2026 files, so 2026 results come from the nfldata games table and are
    accepted only if every team's W-L-T / PF / PA equals the official standings page (data/verified/nfl_standings_ytd/).
    """
    import glob
    g = pd.read_csv(Path.home() / ".cache" / "own9" / "raw" / "nfldata" / "data" / "games.csv")
    g = g[(g.season == 2026) & (g.game_type == "REG") & g.result.notna()]
    rec = []
    for _, r in g.iterrows():
        for side, oth in (("home", "away"), ("away", "home")):
            pf, pa = r[f"{side}_score"], r[f"{oth}_score"]
            rec.append(dict(team=r[f"{side}_team"], w=int(pf > pa), l=int(pf < pa), t=int(pf == pa), pf=pf, pa=pa))
    comp = pd.DataFrame(rec).groupby("team", as_index=False).sum()
    out = []
    for f in sorted(glob.glob(str(VERIFIED / "nfl_standings_ytd" / "*.csv"))):
        off = pd.read_csv(f)
        off["team"] = off.nfl_code.replace(NFL_TO_FRANCHISE)
        m = off.merge(comp, on="team", how="outer", suffixes=("_nfl", "_data"), indicator=True)
        m["match"] = (m._merge == "both") & m.eval("w_nfl == w_data and l_nfl == l_data and t_nfl == t_data and pf_nfl == pf_data and pa_nfl == pa_data")
        m["season"] = 2026
        out.append(m)
    res = pd.concat(out, ignore_index=True)
    keep = ["season", "through_week", "team", "team_name", "w_nfl", "l_nfl", "t_nfl", "pf_nfl", "pa_nfl", "w_data", "l_data", "t_data", "pf_data", "pa_data", "match", "source_url"]
    res[keep].to_csv(VERIFIED / "reconciliation_standings_2026_ytd.csv", index=False)
    print(f"2026 YTD: {len(g)} completed games; teams matched {int(res.match.sum())} of {len(res)}")
    bad = res[~res.match]
    if len(bad):
        print(bad[keep].to_string(index=False))
    return res


if __name__ == "__main__":
    main()
    print()
    verify_player_leaders()
    print()
    verify_2026_ytd()
