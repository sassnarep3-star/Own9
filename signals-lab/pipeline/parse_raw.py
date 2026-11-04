"""Parse the archived NFL game-center feed into three flat tables.

Input : <RAW>/nflfastR-raw/raw/<season>/<season>_<week>_<away>_<home>.json.gz   (see pipeline/fetch.py)
Output: data/derived/games_feed.csv.gz        one row per game (final score, quarter scores, kickoff text, weather text)
        data/derived/team_games_feed.csv.gz   one row per team-game (offense: plays, yards, success, turnovers ...)
        data/derived/player_games_feed.csv.gz one row per player-game (passing / rushing / receiving counting stats)

Stat-ID semantics (inferred from the play descriptions stored in the same feed, then reconciled to NFL.com leaders in
pipeline/verify.py -- see data/verified/):
    10 rush att+yds      11 rush TD (att+yds)     14 incomplete pass (att)   15 completion (att,cmp,yds)
    16 passing TD (att,cmp,yds)      19 interception thrown (att)     20 sack taken (yds negative)
    21 reception (rec,yds)   22 receiving TD (rec,yds)   23 lateral reception (yards only)   115 pass target
Scoring plays on 2-point conversions use different IDs (75-78, 104-105) and are intentionally not counted, matching the
official convention that 2-point attempts are excluded from passing/rushing/receiving statistics.
"""
from __future__ import annotations
import gzip, sys
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

import orjson
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import RAW, DERIVED, RAW_SEASONS

FRANCHISE = {"SD": "LAC", "STL": "LA", "OAK": "LV"}      # relocated franchises -> current code
REG_WEEKS = lambda season: 17 if season <= 2020 else 18   # 16-game seasons through 2020, 17-game from 2021 (NFL schedule format)


def norm(code: str) -> str:
    return FRANCHISE.get(code, code)


def first(x, default=None):
    if isinstance(x, list):
        return x[0] if x else default
    return x if x is not None else default


def parse_game(path: str):
    p = Path(path)
    season_s, week_s, away_raw, home_raw = p.name[:-len(".json.gz")].split("_")
    season, week = int(season_s), int(week_s)
    gd = orjson.loads(gzip.open(p).read())["data"]["viewer"]["gameDetail"]
    away, home = norm(away_raw), norm(home_raw)
    game_id = p.name[:-len(".json.gz")]
    plays = [pl for pl in gd.get("plays", []) if not pl.get("playDeleted")]
    max_q = max([pl.get("quarter") or 0 for pl in plays] or [0])
    q = lambda side, i: first(gd.get(f"{side}PointsQ{i}"))
    ot_pts = lambda side: first(gd.get(f"{side}PointsOvertimeTotal"), 0) or 0
    game = dict(
        game_id=game_id, season=season, week=week,
        game_type="REG" if week <= REG_WEEKS(season) else "POST",
        away_team=away, home_team=home, away_raw=away_raw, home_raw=home_raw,
        away_score=first(gd["visitorPointsTotal"]), home_score=first(gd["homePointsTotal"]),
        away_q1=q("visitor", 1), away_q2=q("visitor", 2), away_q3=q("visitor", 3), away_q4=q("visitor", 4), away_ot=ot_pts("visitor"),
        home_q1=q("home", 1), home_q2=q("home", 2), home_q3=q("home", 3), home_q4=q("home", 4), home_ot=ot_pts("home"),
        overtime=int(max_q > 4), phase=first(gd.get("phase")), start_time_local=first(gd.get("startTime")),
        stadium=first(gd.get("stadium")), attendance=first(gd.get("attendance")),
        weather_text=first((gd.get("weather") or {}).get("shortDescription")), n_plays=len(plays),
    )

    # ---- team offense from drives and scrimmage plays
    team = {t: defaultdict(float) for t in (away, home)}
    for dr in gd.get("drives", []):
        t = norm(dr.get("possessionTeam.abbreviation"))
        if t not in team:
            continue
        how = dr.get("howEndedDescription") or ""
        s = team[t]
        s["drives"] += 1
        s["drive_yards"] += dr.get("yards") or 0
        s["drive_first_downs"] += dr.get("firstDowns") or 0
        s["redzone_drives"] += 1 if dr.get("inside20") else 0
        s["scoring_drives"] += 1 if (dr.get("endedWithScore") and how in ("Touchdown", "Field Goal")) else 0
        s["turnover_drives"] += 1 if how in ("Interception", "Fumble") else 0
        s["int_drives"] += 1 if how == "Interception" else 0
        s["fumble_drives"] += 1 if how == "Fumble" else 0

    players = defaultdict(lambda: defaultdict(float))        # (gsis, team) -> stats
    names = {}
    first_passer = {}                                         # team -> gsis id of first passer (starter proxy known at kickoff)
    for pl in plays:
        ptype = pl.get("playType")
        stats = pl.get("playStats") or []
        poss = norm(pl.get("possessionTeam.abbreviation") or "")
        pass_rec = {}                                         # gsis -> dict for this play (dedupe attempts)
        for st in stats:
            sid = st["statId"]; gid = st.get("gsisPlayer.id") or ""
            tm = norm(st.get("team.abbreviation") or "")
            y = st.get("yards") or 0
            if sid in (14, 15, 16, 19, 20, 10, 11, 21, 22, 23, 115) and gid and tm in team:
                names.setdefault(gid, st.get("playerName") or "")
                S = players[(gid, tm)]
                if sid in (14, 15, 16, 19):
                    r = pass_rec.setdefault((gid, tm), dict(cmp=0, yds=0, td=0, int=0))
                    if sid in (15, 16):
                        r["cmp"] = 1; r["yds"] += y
                    if sid == 16:
                        r["td"] = 1
                    if sid == 19:
                        r["int"] = 1
                elif sid == 20:
                    S["sacked"] += 1; S["sack_yds"] += y
                elif sid in (10, 11):
                    S["rush_att"] += 1; S["rush_yds"] += y; S["rush_td"] += 1 if sid == 11 else 0
                elif sid in (21, 22):
                    S["rec"] += 1; S["rec_yds"] += y; S["rec_td"] += 1 if sid == 22 else 0
                elif sid == 23:
                    S["rec_yds"] += y        # lateral reception: NFL.com credits lateral yardage as receiving yards (no reception/target)
                elif sid == 115:
                    S["targets"] += 1
        for (gid, tm), r in pass_rec.items():
            S = players[(gid, tm)]
            S["pass_att"] += 1; S["pass_cmp"] += r["cmp"]; S["pass_yds"] += r["yds"]; S["pass_td"] += r["td"]; S["pass_int"] += r["int"]
            first_passer.setdefault(tm, gid)

        # scrimmage-play efficiency (no accepted-penalty plays): success rate and explosive plays
        if ptype in ("PASS", "RUSH", "SACK", "INTERCEPTION") and poss in team and not pl.get("penaltyOnPlay"):
            down, ytg, yds = pl.get("down"), pl.get("yardsToGo"), pl.get("yards")
            if down in (1, 2, 3, 4) and ytg is not None and yds is not None:
                s = team[poss]
                s["sc_plays"] += 1; s["sc_yards"] += yds
                need = {1: 0.4 * ytg, 2: 0.6 * ytg}.get(down, ytg)
                s["success"] += 1 if yds >= need else 0
                if ptype == "RUSH":
                    s["explosive"] += 1 if yds >= 10 else 0
                elif ptype == "PASS":
                    s["explosive"] += 1 if yds >= 20 else 0
                s["third_att"] += 1 if down == 3 else 0
                s["third_conv"] += 1 if (down == 3 and yds >= ytg) else 0

    # roll player stats into team totals (pass / rush / sack) for the team table
    for (gid, tm), S in players.items():
        T = team[tm]
        for k in ("pass_att", "pass_cmp", "pass_yds", "pass_td", "pass_int", "rush_att", "rush_yds", "rush_td", "sacked", "sack_yds"):
            T[k] += S.get(k, 0)

    team_rows = []
    for t, opp, home_flag in ((away, home, 0), (home, away, 1)):
        row = dict(game_id=game_id, season=season, week=week, game_type=game["game_type"], team=t, opp=opp, home=home_flag,
                   points=game["home_score"] if home_flag else game["away_score"],
                   points_allowed=game["away_score"] if home_flag else game["home_score"])
        row.update({k: v for k, v in team[t].items()})
        row["starter_qb"] = first_passer.get(t)
        team_rows.append(row)

    player_rows = []
    for (gid, tm), S in players.items():
        row = dict(game_id=game_id, season=season, week=week, game_type=game["game_type"], gsis_id=gid, name=names.get(gid, ""),
                   team=tm, opp=home if tm == away else away, home=int(tm == home))
        row.update(S)
        player_rows.append(row)
    return game, team_rows, player_rows


def main():
    files = []
    for s in RAW_SEASONS:
        files += sorted(str(f) for f in (RAW / "nflfastR-raw" / "raw" / str(s)).glob("*.json.gz"))
    print(len(files), "game files")
    with Pool(2) as pool:
        res = pool.map(parse_game, files, chunksize=20)
    games = pd.DataFrame([r[0] for r in res])
    team = pd.DataFrame([row for r in res for row in r[1]]).fillna(0)
    player = pd.DataFrame([row for r in res for row in r[2]]).fillna(0)
    # starter_qb must stay a string / empty
    team["starter_qb"] = team["starter_qb"].replace(0, "")
    DERIVED.mkdir(parents=True, exist_ok=True)
    games.to_csv(DERIVED / "games_feed.csv.gz", index=False)
    team.to_csv(DERIVED / "team_games_feed.csv.gz", index=False)
    player.to_csv(DERIVED / "player_games_feed.csv.gz", index=False)
    print("games", games.shape, "team-games", team.shape, "player-games", player.shape)
    print(games.groupby(["season", "game_type"]).size().unstack(fill_value=0))


if __name__ == "__main__":
    main()
