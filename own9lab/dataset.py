"""Build the analysis game table (2009 season onward) with per-row source links
and the automated official-feed cross-check.

Per-row links
  nfl_url     official NFL.com Game Center page (pattern confirmed on sampled pages,
              see data/verification/nfl_com_url_checks.csv)
  source_url  exact line of nflverse/nfldata games.csv at the pinned commit
  pfr_url / espn_url  secondary references built from the IDs carried in games.csv
"""
import csv
import pandas as pd
from . import config as C

SLUG = {"ARI": "cardinals", "ATL": "falcons", "BAL": "ravens", "BUF": "bills", "CAR": "panthers",
        "CHI": "bears", "CIN": "bengals", "CLE": "browns", "DAL": "cowboys", "DEN": "broncos",
        "DET": "lions", "GB": "packers", "HOU": "texans", "IND": "colts", "JAX": "jaguars",
        "KC": "chiefs", "LA": "rams", "STL": "rams", "LAC": "chargers", "SD": "chargers",
        "LV": "raiders", "OAK": "raiders", "MIA": "dolphins", "MIN": "vikings", "NE": "patriots",
        "NO": "saints", "NYG": "giants", "NYJ": "jets", "PHI": "eagles", "PIT": "steelers",
        "SEA": "seahawks", "SF": "49ers", "TB": "buccaneers", "TEN": "titans"}
POST = {"WC": 1, "DIV": 2, "CON": 3, "SB": 4}


def slug(team, season):
    if team == "WAS":
        return "redskins" if season <= 2019 else ("football-team" if season <= 2021 else "commanders")
    return SLUG[team]


def nfl_url(r):
    wk = f"reg-{int(r.week)}" if r.game_type == "REG" else f"post-{POST[r.game_type]}"
    return f"https://www.nfl.com/games/{slug(r.away_team, r.season)}-at-{slug(r.home_team, r.season)}-{r.season}-{wk}"


def load_raw():
    with open(C.CACHE / "games.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    df = pd.DataFrame(rows)
    df["source_line"] = range(2, len(df) + 2)  # header is line 1; no field contains a newline (checked below)
    raw_lines = (C.CACHE / "games.csv").read_text().splitlines()
    assert len(raw_lines) == len(df) + 1, "embedded newline in games.csv"
    df = df.replace({"": None, "NA": None})
    num = ["season", "week", "away_score", "home_score", "result", "total", "overtime", "away_rest", "home_rest",
           "away_moneyline", "home_moneyline", "spread_line", "away_spread_odds", "home_spread_odds", "total_line",
           "under_odds", "over_odds", "div_game", "temp", "wind"]
    for c in num:
        df[c] = pd.to_numeric(df[c])
    return df


def build():
    df = load_raw()
    df = df[df.season >= C.FIRST_SEASON].copy()
    df["season"] = df.season.astype(int)
    df["nfl_url"] = df.apply(nfl_url, axis=1)
    df["source_url"] = C.NFLDATA_BLOB + "/data/games.csv?plain=1#L" + df.source_line.astype(str)
    df["pfr_url"] = "https://www.pro-football-reference.com/boxscores/" + df.pfr + ".htm"
    df["espn_url"] = "https://www.espn.com/nfl/game/_/gameId/" + df.espn
    df["played"] = df.home_score.notna() & df.away_score.notna()

    # ---- official-feed cross-check (NFL.com GameCenter archive, 2009-2019) ----
    gc = pd.read_csv(C.DERIVED / "gc_games.csv", dtype={"eid": str})
    m = df.merge(gc, left_on="old_game_id", right_on="eid", how="left")
    status = []
    for r in m.itertuples():
        if pd.isna(r.eid):
            status.append("not in feed archive")
        elif str(r.qtr).lower() not in ("final", "final overtime"):
            status.append(f"feed incomplete (qtr={r.qtr})")
        elif (r.home_abbr, r.away_abbr) != (r.home_team, r.away_team):
            status.append(f"team mismatch (feed {r.away_abbr}@{r.home_abbr})")
        else:
            status.append(None)  # teams agree and feed is final -> scores compared below
    m["gc_status"] = status
    # scores compared explicitly (merge suffixes: _x = nflverse, _y = feed)
    feed_ok = m.gc_status.isna()
    same = (m.home_score_x == m.home_score_y) & (m.away_score_x == m.away_score_y)
    m.loc[feed_ok & same, "gc_status"] = "match"
    m.loc[feed_ok & ~same, "gc_status"] = ("score mismatch (feed " + m.away_score_y.astype("Int64").astype(str) + "-" +
                                           m.home_score_y.astype("Int64").astype(str) + ")")
    df["gc_status"] = m.gc_status.values
    df["gc_away_score"] = m.away_score_y.values
    df["gc_home_score"] = m.home_score_y.values
    return df


if __name__ == "__main__":
    d = build()
    print(len(d), "games", d.season.min(), d.season.max())
    print(d.groupby("season").gc_status.value_counts().unstack(fill_value=0))
    print(d[~d.gc_status.isin(["match", "not in feed archive"])][["game_id", "away_score", "home_score", "gc_status"]])


KEEP = ["game_id", "season", "game_type", "week", "gameday", "weekday", "gametime", "away_team", "home_team",
        "away_score", "home_score", "overtime", "location", "div_game", "roof", "surface", "temp", "wind",
        "away_rest", "home_rest", "away_qb_id", "home_qb_id", "away_qb_name", "home_qb_name",
        "spread_line", "total_line", "away_moneyline", "home_moneyline", "away_spread_odds", "home_spread_odds",
        "over_odds", "under_odds", "old_game_id", "nfl_url", "source_url", "pfr_url"]


def write_analysis_table():
    """data/derived/games.csv: scores kept only where officially VERIFIED (else blank);
    market fields kept as model inputs but always flagged line_status=UNVERIFIED."""
    from . import verify
    g = build()
    v, rec = verify.main(g)
    t = g[KEEP].merge(v, on="game_id", how="left")
    bad = t.score_status != "VERIFIED"
    t.loc[bad, ["away_score", "home_score"]] = None
    t["line_status"] = "UNVERIFIED (secondary source; no official source for betting lines)"
    t.loc[t.spread_line.isna(), "line_status"] = "missing"
    t.to_csv(C.DERIVED / "games.csv", index=False)
    return t
