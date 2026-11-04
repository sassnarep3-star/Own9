"""Official verification of every game result used by own9lab.

Methods (first applicable wins, see lab/verification.html):
  V1  NFL.com page check     score observed on an NFL.com page fetched by this session
                             (data/verification/nfl_com_game_checks.csv)
  V2  Official feed match    teams and final score equal the archived NFL.com GameCenter
                             JSON feed (2009-2019; data/derived/gc_games.csv)
  V3  Standings reconciled   regular-season game whose two teams' official season totals
                             (W-L-T, PF, PA from NFL.com standings, transcribed in
                             data/verification/nfl_com_standings.csv) are reproduced exactly
                             by the games table (2020-2026)
Anything else is UNVERIFIED (blank in published tables, listed on lab/flags.html).
Betting lines/prices have no official source: always UNVERIFIED.
"""
import pandas as pd
from . import config as C


def standings_reconciliation(games):
    off = pd.read_csv(C.VERIFY / "nfl_com_standings.csv")
    reg = games[(games.game_type == "REG") & games.played & games.season.isin(off.season.unique())]
    rows = []
    for side, opp in (("home", "away"), ("away", "home")):
        t = reg[["season", f"{side}_team", f"{side}_score", f"{opp}_score"]].copy()
        t.columns = ["season", "team", "pf", "pa"]
        rows.append(t)
    t = pd.concat(rows)
    t["w"] = (t.pf > t.pa).astype(int)
    t["l"] = (t.pf < t.pa).astype(int)
    t["t"] = (t.pf == t.pa).astype(int)
    calc = t.groupby(["season", "team"])[["w", "l", "t", "pf", "pa"]].sum().reset_index()
    m = off.merge(calc, on=["season", "team"], how="outer", suffixes=("_official", "_games"), indicator=True)
    cols = ["w", "l", "t", "pf", "pa"]
    m["match"] = (m["_merge"] == "both") & all_equal(m, cols)
    m["diff"] = m.apply(lambda r: "; ".join(f"{c}: official {r[c + '_official']} vs games {r[c + '_games']}"
                                            for c in cols if r[c + "_official"] != r[c + "_games"]), axis=1)
    return m.drop(columns="_merge")


def all_equal(m, cols):
    ok = pd.Series(True, index=m.index)
    for c in cols:
        ok &= m[c + "_official"] == m[c + "_games"]
    return ok


def verify(games):
    checks = pd.read_csv(C.VERIFY / "nfl_com_game_checks.csv")
    unknown = set(checks.game_id) - set(games.game_id)
    if unknown:
        raise SystemExit(f"nfl_com_game_checks.csv references unknown game_id(s): {sorted(unknown)}")
    rec = standings_reconciliation(games)
    ok_team = {(r.season, r.team) for r in rec.itertuples() if r.match}
    chk = checks.set_index("game_id")
    out = []
    for r in games.itertuples():
        method, status, evidence, url = None, "UNVERIFIED", "", r.nfl_url
        if r.game_id in chk.index:
            c = chk.loc[r.game_id]
            url = c.official_url
            if (c.official_away_score, c.official_home_score) == (r.away_score, r.home_score):
                method, status = "V1 NFL.com page", "VERIFIED"
                evidence = f"{c.observed_on}: {r.away_team} {c.official_away_score} - {r.home_team} {c.official_home_score}"
            else:
                status = "MISMATCH"
                evidence = (f"NFL.com shows {c.official_away_score}-{c.official_home_score}; "
                            f"games table {r.away_score}-{r.home_score}")
        elif r.gc_status == "match":
            method, status = "V2 official feed", "VERIFIED"
            evidence = f"GameCenter feed eid {r.old_game_id}: {r.away_team} {int(r.gc_away_score)} - {r.home_team} {int(r.gc_home_score)}"
        elif not r.played:
            status = "SCHEDULED"
        elif (r.game_type == "REG" and (r.season, r.home_team) in ok_team and (r.season, r.away_team) in ok_team):
            method, status = "V3 standings reconciled", "VERIFIED"
            url = r.nfl_url
            evidence = (f"{r.season} NFL.com standings totals for {r.away_team} and {r.home_team} reproduced exactly "
                        f"(https://www.nfl.com/standings/league/{r.season}/REG)")
        else:
            if isinstance(r.gc_status, str) and r.gc_status.startswith("score mismatch"):
                status, evidence = "MISMATCH", f"archived feed: {r.gc_status}"
            elif r.game_type != "REG" and r.season >= 2020:
                evidence = "postseason game 2020+: not covered by REG standings; no NFL.com page check yet"
            else:
                evidence = f"official feed: {r.gc_status}"
        out.append({"game_id": r.game_id, "score_status": status, "score_method": method,
                    "official_url": url, "evidence": evidence})
    v = pd.DataFrame(out)
    return v, rec


def main(games):
    v, rec = verify(games)
    rec.to_csv(C.VERIFY / "standings_reconciliation.csv", index=False)
    v.to_csv(C.VERIFY / "game_verification.csv", index=False)
    return v, rec


if __name__ == "__main__":
    from . import dataset
    g = dataset.build()
    v, rec = main(g)
    print(rec.groupby("season").match.agg(["sum", "count"]))
    print(rec[~rec.match][["season", "team", "diff"]].to_string())
    vv = v.merge(g[["game_id", "season", "game_type"]], on="game_id")
    print(pd.crosstab(vv.season, vv.score_status.fillna("") + " " + vv.score_method.fillna("")))
