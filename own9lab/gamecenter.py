"""Parse archived official NFL.com GameCenter JSON feeds (2009-2019 seasons).

Source: the nflgame-redux 3.0.0 wheel on PyPI (SHA-256 checked in acquire.py)
contains the raw gamecenter-json/<eid>.json.gz files downloaded from NFL.com.
`eid` equals nflverse `old_game_id`.

Outputs (data/derived):
  gc_games.csv          one row per game: teams, final score, status
  gc_player_lines.csv.gz  one row per player-game-category (passing/rushing/receiving)
"""
import gzip, json, re, zipfile
import pandas as pd
from . import config as C

TEAM_FIX = {"JAC": "JAX"}  # GameCenter -> nflverse abbreviations (others are identical)


def parse():
    z = zipfile.ZipFile(C.CACHE / C.GC_WHEEL_NAME)
    games, lines, bad = [], [], []
    for name in sorted(z.namelist()):
        m = re.search(r"gamecenter-json/(\d{10})\.json\.gz$", name)
        if not m:
            continue
        eid = m.group(1)
        raw = gzip.decompress(z.read(name))
        try:
            d = json.loads(raw)
        except ValueError:
            bad.append({"eid": eid, "file": name, "bytes": len(raw), "problem": "not valid JSON"})
            continue
        g = d.get(eid)
        if not g or "home" not in g:
            bad.append({"eid": eid, "file": name, "bytes": len(raw), "problem": "no game object"})
            continue
        rec = {"eid": eid, "qtr": g.get("qtr")}
        for side in ("home", "away"):
            t = g[side]
            abbr = TEAM_FIX.get(t.get("abbr"), t.get("abbr"))
            rec[f"{side}_abbr"] = abbr
            rec[f"{side}_score"] = (t.get("score") or {}).get("T")
            rec[f"{side}_ot_pts"] = (t.get("score") or {}).get("5")
            stats = t.get("stats") or {}
            for cat in ("passing", "rushing", "receiving"):
                for pid, s in (stats.get(cat) or {}).items():
                    row = {"eid": eid, "team": abbr, "side": side, "category": cat, "player_id": pid,
                           "name": s.get("name")}
                    for k in ("att", "cmp", "yds", "tds", "ints", "rec", "lng"):
                        if k in s:
                            row[k] = s[k]
                    lines.append(row)
            # players appearing in any category (used to decide whether a player was active)
            for cat, block in stats.items():
                if cat == "team" or not isinstance(block, dict):
                    continue
                for pid, s in block.items():
                    if isinstance(s, dict):
                        lines.append({"eid": eid, "team": abbr, "side": side, "category": "appeared:" + cat,
                                      "player_id": pid, "name": s.get("name")})
        games.append(rec)
    g = pd.DataFrame(games)
    p = pd.DataFrame(lines)
    C.DERIVED.mkdir(parents=True, exist_ok=True)
    g.to_csv(C.DERIVED / "gc_games.csv", index=False)
    p.to_csv(C.CACHE / "gc_player_lines.csv.gz", index=False)  # regenerable; kept out of git
    pd.DataFrame(bad, columns=["eid", "file", "bytes", "problem"]).to_csv(C.DERIVED / "gc_unparseable_files.csv", index=False)
    return g, p


if __name__ == "__main__":
    g, p = parse()
    print(len(g), "games;", len(p), "player-category rows")
    print(g["qtr"].value_counts().head(10))
