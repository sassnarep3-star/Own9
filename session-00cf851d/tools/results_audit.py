#!/usr/bin/env python3
"""Session 00cf851d - audit of the repository's committed results and price file.

Read-only. Opens ``data/raw/games.csv`` as it is committed and measures it:
it never edits it. Every published number is either copied from that file or
computed from it here, and every comparison is against an official NFL page
this session read on 2026-11-14.
"""

from __future__ import annotations

import csv
import json
import os
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
SESSION = os.path.dirname(HERE)
REPO = os.path.dirname(SESSION)
DATA = os.path.join(SESSION, "data")
REVIEW_DATE = "2026-11-14"

GAMES_CSV = os.path.join(REPO, "data", "raw", "games.csv")
OFFICIAL_RESULTS = os.path.join(DATA, "official_results.json")
STANDINGS = os.path.join(DATA, "standings_2026.json")

SCHEDULE_W9 = "https://www.nfl.com/schedules/2026/by-week/week-9"
SCHEDULE_W10 = "https://www.nfl.com/schedules/2026/REG10/"
STANDINGS_URL = "https://www.nfl.com/standings/"


def num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def load_games():
    with open(GAMES_CSV, newline="", encoding="utf-8", errors="replace") as fh:
        return list(csv.DictReader(fh))


def main():
    rows = load_games()
    official = json.load(open(OFFICIAL_RESULTS, encoding="utf-8"))
    standings = json.load(open(STANDINGS, encoding="utf-8"))

    # ---------- 1. Internal arithmetic across every row that has a result -----
    bad_margin = bad_total = 0
    for r in rows:
        a, h, res, tot = num(r["away_score"]), num(r["home_score"]), num(r["result"]), num(r["total"])
        if None in (a, h, res, tot):
            continue
        if abs((h - a) - res) > 1e-9:
            bad_margin += 1
        if abs((h + a) - tot) > 1e-9:
            bad_total += 1
    with_result = sum(1 for r in rows if r["result"].strip())

    # ---------- 2. Sign convention, established from the data ---------------
    pairs = [(num(r["result"]), num(r["spread_line"])) for r in rows
             if r["result"].strip() and r["spread_line"].strip()]
    pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
    xs = [b for _, b in pairs]
    ys = [a for a, _ in pairs]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / len(xs)
    corr = cov / (statistics.pstdev(xs) * statistics.pstdev(ys))

    # ---------- 3. Completeness of the current season ------------------------
    s2026 = [r for r in rows if r["season"] == "2026"]
    played_by_date = [r for r in s2026 if r["gameday"] <= REVIEW_DATE]
    missing = [r for r in played_by_date if not r["result"].strip()]
    missing_ids = {r["game_id"] for r in missing}

    # ---------- 4. Per-club recomputation against the official standings -----
    official_by_abbr = {c["abbr"]: c for d in standings["divisions"] for c in d["clubs"]}
    # The committed file uses older club codes for two clubs the league now
    # abbreviates differently. Without this map those two clubs silently fail
    # every join against an official source.
    ALIAS = {"ARI": "AZ", "LA": "LAR"}
    for old, new in ALIAS.items():
        if new in official_by_abbr:
            official_by_abbr[old] = official_by_abbr[new]
    club_rows = []
    for abbr, off in sorted(official_by_abbr.items()):
        if abbr in ALIAS.values():
            continue  # the same club is reported under its committed-file code
        played = [r for r in s2026 if abbr in (r["home_team"], r["away_team"]) and r["result"].strip()]
        gaps = [r for r in missing if abbr in (r["home_team"], r["away_team"])]
        w = l = t = pf = pa = 0
        for r in played:
            if r["home_team"] == abbr:
                hs, as_ = num(r["home_score"]), num(r["away_score"])
            else:
                hs, as_ = num(r["away_score"]), num(r["home_score"])
            if hs is None or as_ is None:
                continue
            pf += hs
            pa += as_
            if hs > as_:
                w += 1
            elif hs < as_:
                l += 1
            else:
                t += 1
        checkable = not gaps
        club_rows.append({
            "abbr": abbr, "team": off["team"],
            "games_in_file_with_result": len(played),
            "games_missing_result": len(gaps),
            "recomputed_w": w, "recomputed_l": l, "recomputed_t": t,
            "recomputed_pf": pf, "recomputed_pa": pa,
            "official_w": off["w"], "official_l": off["l"], "official_t": off["t"],
            "official_pf": off["pf"], "official_pa": off["pa"],
            "reconciles": (w == off["w"] and l == off["l"] and t == off["t"]
                           and pf == off["pf"] and pa == off["pa"]) if checkable else None,
            "status": ("reconciles with the official standings" if checkable and
                       (w == off["w"] and l == off["l"] and t == off["t"]
                        and pf == off["pf"] and pa == off["pa"])
                       else "cannot be reconciled: %d game(s) this club played are missing a result" % len(gaps)
                       if gaps else "DOES NOT RECONCILE"),
            "source_url": STANDINGS_URL,
        })

    # ---------- 5. Market versus outcome for the completed 2026 games --------
    market = []
    for r in sorted(s2026, key=lambda x: (x["gameday"], x["game_id"])):
        res, tot = num(r["result"]), num(r["total"])
        if res is None or tot is None:
            continue
        spread, total_line = num(r["spread_line"]), num(r["total_line"])
        hml, aml = num(r["home_moneyline"]), num(r["away_moneyline"])
        market.append({
            "game_id": r["game_id"], "week": r["week"], "gameday": r["gameday"],
            "away": r["away_team"], "home": r["home_team"],
            "closing_spread_home": spread, "closing_total": total_line,
            "home_moneyline": hml, "away_moneyline": aml,
            "model_fair_line": None,
            "model_fair_total": None,
            "actual_home_margin": res, "actual_total": tot,
            "spread_miss_home": (res - spread) if spread is not None else None,
            "total_miss": (tot - total_line) if total_line is not None else None,
            "result_source": "data/raw/games.csv (not re-verified against an official page by this session)",
        })

    # ---------- 6. Officially verified outcomes, including the missing ones ---
    verified = []
    for o in official["results"]:
        row = next((r for r in s2026 if r["game_id"] == o["game_id_in_repo"]), None)
        in_file_result = row["result"].strip() if row else ""
        verified.append({
            "game_id": o["game_id_in_repo"], "week": o["week"], "gameday": o["gameday"],
            "away": o["away_abbr"], "away_points": o["away_points"],
            "home": o["home_abbr"], "home_points": o["home_points"],
            "official_home_margin": o["home_points"] - o["away_points"],
            "official_total": o["home_points"] + o["away_points"],
            "result_present_in_committed_file": bool(in_file_result),
            "committed_file_result": in_file_result or None,
            "closing_spread_home": num(row["spread_line"]) if row else None,
            "closing_total": num(row["total_line"]) if row else None,
            "source_url": o["source_url"],
        })

    spread_misses = [m["spread_miss_home"] for m in market if m["spread_miss_home"] is not None]
    total_misses = [m["total_miss"] for m in market if m["total_miss"] is not None]

    # ---------- 7. The same reconciliation, with the official outcomes applied --
    # This is the test that decides whether the sixteen outcomes this session read
    # are right. If they are, every club's recomputed record, points for and points
    # against must land exactly on the official standings. If any club is off, a
    # transcription is wrong or the sign convention is wrong, and the claim that
    # the missing results were the only cause of the 2-of-32 result would not hold.
    official = json.load(open(OFFICIAL_RESULTS, encoding="utf-8"))
    fill = {r["game_id_in_repo"]: (int(r["home_points"]), int(r["away_points"]))
            for r in official["results"]}
    after_rows, after_ok = [], 0
    for abbr, off in sorted(official_by_abbr.items()):
        if abbr in ALIAS.values():
            continue
        w = l = t = pf = pa = 0
        for r in s2026:
            if abbr not in (r["home_team"], r["away_team"]):
                continue
            if r["game_id"] in fill:
                hs, as_ = fill[r["game_id"]]
            elif r["result"].strip():
                # result = home - away, total = home + away (sign convention
                # established from the data in section 2).
                tot, res = int(r["total"]), int(r["result"])
                hs, as_ = (tot + res) // 2, (tot - res) // 2
            else:
                continue
            if r["home_team"] != abbr:
                hs, as_ = as_, hs
            pf += hs
            pa += as_
            if hs > as_:
                w += 1
            elif hs < as_:
                l += 1
            else:
                t += 1
        got = (w, l, t, pf, pa)
        exp = (off["w"], off["l"], off["t"], off["pf"], off["pa"])
        if got == exp:
            after_ok += 1
        after_rows.append({"abbr": abbr, "team": off["team"], "recomputed": got,
                           "official": exp, "matches": got == exp})
    after = {
        "description": ("The per-club reconciliation of section 4 repeated with the sixteen officially "
                        "read outcomes applied to the games the committed file leaves blank. Every club "
                        "is now checkable, so this is a direct test of the transcription: a single wrong "
                        "score would break two clubs at once."),
        "standings_source_url": STANDINGS_URL,
        "outcomes_applied": len(fill),
        "clubs": after_rows,
        "clubs_matching": after_ok,
        "clubs_checked": len(after_rows),
        "statement": ("%d of %d clubs reconcile exactly on W-L-T, points for and points against once the "
                      "official outcomes are applied, against %d of %d before."
                      % (after_ok, len(after_rows),
                         sum(1 for c in club_rows if c["reconciles"]), len(club_rows))),
    }

    doc = {
        "register_name": "Audit of the committed results and price file (data/raw/games.csv)",
        "file_sha256": None,
        "reviewed_on": REVIEW_DATE,
        "session": "00cf851d",
        "source_file": "data/raw/games.csv",
        "method": "Read-only. Nothing in the source file was changed. Values are copied or computed here; comparisons are against official NFL pages read on 2026-11-14.",
        "coverage": {
            "rows": len(rows),
            "seasons": "%s to %s" % (min(r["season"] for r in rows), max(r["season"] for r in rows)),
            "columns": len(rows[0]),
            "rows_with_a_result": with_result,
            "rows_with_closing_spread": sum(1 for r in rows if r["spread_line"].strip()),
            "rows_with_closing_total": sum(1 for r in rows if r["total_line"].strip()),
            "rows_with_moneylines": sum(1 for r in rows if r["home_moneyline"].strip()),
            "rows_with_opening_prices": 0,
            "opening_price_note": "The file has no opening-price column. Every price column is a single closing value, so a store that records both the opening and the closing number cannot be built from this file alone.",
        },
        "internal_consistency": {
            "rows_where_result_equals_home_minus_away": with_result - bad_margin,
            "rows_where_that_fails": bad_margin,
            "rows_where_total_equals_home_plus_away": with_result - bad_total,
            "rows_where_that_fails": bad_total,
        },
        "convention": {
            "how_it_was_established": ("Correlated the result column against the spread column over every row where both are present. "
                                       "A positive correlation means the two share a sign, so the spread column is stated from the home club's perspective."),
            "n_pairs": len(pairs),
            "correlation": round(corr, 4),
            "statement": ("result = home_score - away_score, total = home_score + away_score, and spread_line is the "
                          "closing line from the home club's perspective (positive means the home club was favoured by that many points)."),
        },
        "current_season_completeness": {
            "season": 2026,
            "scheduled_rows": len(s2026),
            "rows_with_gameday_on_or_before_review_date": len(played_by_date),
            "of_those_missing_a_result": len(missing),
            "missing_game_ids": sorted(missing_ids),
            "statement": ("Every one of the %d most recent games the file carries a price for is missing its result, "
                          "including the 2026-11-12 Thursday-night game the league published two days before this review."
                          % len(missing)),
        },
        "club_reconciliation": {
            "description": ("For each club, the season record and points are recomputed from the committed file and compared "
                            "with the official standings read on 2026-11-14. A club can only be reconciled if none of its games "
                            "is missing a result."),
            "standings_source_url": STANDINGS_URL,
            "clubs": club_rows,
            "reconciled": sum(1 for c in club_rows if c["reconciles"]),
            "blocked_by_missing_results": sum(1 for c in club_rows if c["games_missing_result"]),
        },
        "officially_verified_outcomes": {
            "description": ("Outcomes the league publishes for games this session read. Each is compared with what the committed "
                            "file holds for the same game id."),
            "rows": verified,
            "n": len(verified),
        },
        "reconciliation_after_official_ingest": after,
        "market_vs_outcome_2026": {
            "description": ("Closing price against actual outcome for every 2026 game the file has a result for. "
                            "'model_fair_line' is deliberately left blank: no model in this repository has been fitted and "
                            "validated, so printing a fair line would be fabrication, and the difference column that depends "
                            "on it is left blank with it."),
            "n_games": len(market),
            "mean_absolute_spread_miss": round(statistics.mean(abs(v) for v in spread_misses), 3) if spread_misses else None,
            "mean_absolute_total_miss": round(statistics.mean(abs(v) for v in total_misses), 3) if total_misses else None,
            "mean_signed_spread_miss": round(statistics.mean(spread_misses), 3) if spread_misses else None,
            "mean_signed_total_miss": round(statistics.mean(total_misses), 3) if total_misses else None,
            "interpretation_note": ("These are descriptive measurements of how far the closing price finished from the result. "
                                    "They are not a strategy, not an edge, and not a claim that anyone could have beaten the "
                                    "number, because the closing price is not a price anyone could have taken."),
            "rows": market,
        },
    }
    out = os.path.join(DATA, "results_audit.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    print("games.csv: %d rows, %s, %d with a result" % (
        len(rows), doc["coverage"]["seasons"], with_result))
    print("internal: %d margin failures, %d total failures" % (bad_margin, bad_total))
    print("convention: n=%d corr=%.4f" % (len(pairs), corr))
    print("2026: %d scheduled, %d played by %s, %d missing a result" % (
        len(s2026), len(played_by_date), REVIEW_DATE, len(missing)))
    print("clubs reconciled against official standings: %d; blocked by missing results: %d" % (
        doc["club_reconciliation"]["reconciled"], doc["club_reconciliation"]["blocked_by_missing_results"]))
    for c in club_rows:
        print("  %-3s %s" % (c["abbr"], c["status"]))
    print("after applying the official outcomes: %s" % after["statement"])
    print("official outcomes recorded: %d (present in file: %d)" % (
        len(verified), sum(1 for v in verified if v["result_present_in_committed_file"])))
    print("market-vs-outcome 2026 rows: %d  MAE spread=%.3f total=%.3f" % (
        len(market), doc["market_vs_outcome_2026"]["mean_absolute_spread_miss"] or 0,
        doc["market_vs_outcome_2026"]["mean_absolute_total_miss"] or 0))


if __name__ == "__main__":
    main()
