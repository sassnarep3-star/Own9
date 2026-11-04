#!/usr/bin/env python3
"""T04 - Cross-verify the third-party data against the official league source (NFL.com).

The transcriptions live in data/verification/official_crosscheck.json (one object per page,
each with the URL it was read from). This script re-derives the same values from games.csv and
reports a per-row match/mismatch, so the verification is mechanical rather than asserted.

Anything that could not be read from an official page stays `null` in the transcription file and
is reported as "unverified" - never filled in.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import lib_engine as E

OUT = E.OUT
VER = Path(__file__).resolve().parent.parent / "data" / "verification" / "official_crosscheck.json"


def main() -> int:
    src = json.loads(VER.read_text())
    games = pd.read_csv(E.RAW / "games.csv", low_memory=False)
    games = games[games.game_type == "REG"]

    results: list[dict] = []

    # ---- score cross-checks
    for block in src["score_crosschecks"]:
        season = None
        for g in block["games"]:
            cand = games[(games.away_team == g["away"]) & (games.home_team == g["home"])]
            # restrict to the season implied by the label
            season_label = int(block["label"][:4])
            cand = cand[cand.season == season_label]
            if cand.empty:
                results.append({**g, "check": block["id"], "status": "no matching row",
                                "data_values": None, "source_url": block["source_url"]})
                continue
            row = cand.iloc[0]
            ok = (float(row.away_score) == g["away_score"]) and (float(row.home_score) == g["home_score"])
            results.append({
                "check": block["id"], "label": block["label"], "game_id": row.game_id,
                "season": int(row.season), "week": int(row.week),
                "away": g["away"], "home": g["home"],
                "official": f"{g['away']} {g['away_score']} - {g['home']} {g['home_score']}",
                "data": f"{row.away_team} {int(row.away_score)} - {row.home_team} {int(row.home_score)}",
                "status": "match" if ok else "MISMATCH",
                "source_url": block["source_url"],
                "data_source_url": E.MANIFEST["files"]["games.csv"]["source_url"],
            })

    # ---- record cross-checks (recomputed from games.csv)
    rec_rows = []
    for block in src["record_crosschecks"]:
        season = 2026
        d = games[(games.season == season) & games.home_score.notna()]
        recs = {}
        for row in d.itertuples():
            for team, pf, pa in ((row.home_team, row.home_score, row.away_score),
                                 (row.away_team, row.away_score, row.home_score)):
                w, l, t = recs.get(team, (0, 0, 0))
                if pf > pa:
                    w += 1
                elif pf < pa:
                    l += 1
                else:
                    t += 1
                recs[team] = (w, l, t)
        for team, official in block["records"].items():
            mine = recs.get(team)
            mine_s = f"{mine[0]}-{mine[1]}-{mine[2]}" if mine else None
            status = "unverified (not shown on retrieved page)" if official is None else (
                "match" if mine_s == official else "MISMATCH")
            rec_rows.append({
                "check": block["id"], "team": team, "official": official,
                "data": mine_s, "status": status, "source_url": block["source_url"],
                "data_source_url": E.MANIFEST["files"]["games.csv"]["source_url"],
            })

    # ---- schedule cross-checks
    sched_rows = []
    for block in src["schedule_crosschecks"]:
        for m in block["matchups"]:
            cand = games[(games.season == 2026) & (games.away_team == m["away"])
                         & (games.home_team == m["home"])]
            if cand.empty:
                sched_rows.append({**m, "status": "no matching row in data", "source_url": block["source_url"]})
                continue
            row = cand.iloc[0]
            date_ok = str(row.gameday) == m["gameday"]
            sched_rows.append({
                "check": block["id"], "game_id": row.game_id, "week": int(row.week),
                "matchup": f"{m['away']} at {m['home']}",
                "official_gameday": m["gameday"], "data_gameday": str(row.gameday),
                "status": "match" if date_ok else "MISMATCH",
                "source_url": block["source_url"],
                "data_source_url": E.MANIFEST["files"]["games.csv"]["source_url"],
            })

    score_ok = sum(r["status"] == "match" for r in results)
    rec_ok = sum(r["status"] == "match" for r in rec_rows)
    rec_unver = sum(r["status"].startswith("unverified") for r in rec_rows)
    sched_ok = sum(r["status"] == "match" for r in sched_rows)

    payload = {
        "generated_at_utc": E.MANIFEST["generated_at_utc"],
        "source_commit_sha": E.MANIFEST["commit_sha"],
        "transcriptions_retrieved_at_utc": src["retrieved_at_utc"],
        "summary": {
            "score_rows_checked": len(results), "score_rows_matched": score_ok,
            "record_rows_checked": len(rec_rows), "record_rows_matched": rec_ok,
            "record_rows_unverified": rec_unver,
            "schedule_rows_checked": len(sched_rows), "schedule_rows_matched": sched_ok,
        },
        "score_checks": results,
        "record_checks": rec_rows,
        "schedule_checks": sched_rows,
    }
    (OUT / "verification.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload["summary"], indent=1))
    bad = [r for r in results if r["status"] != "match"] + \
          [r for r in rec_rows if r["status"] == "MISMATCH"] + \
          [r for r in sched_rows if r["status"] != "match"]
    if bad:
        print("MISMATCHES:")
        for b in bad:
            print(" ", b)
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
