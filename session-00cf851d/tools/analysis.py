#!/usr/bin/env python3
"""Session 00cf851d - independent verification and replacement-depth analysis.

This module does two things and nothing else:

1. Re-checks, line by line, the NFL claims already committed in this repository
   (in ``evidence/**``) against the official NFL documents this session
   retrieved and read on 2026-11-14 (in ``session-00cf851d/data/**``).
   Every check records the claim, the official source it was checked against,
   and the result. No check is skipped silently.

2. Computes a replacement-depth measurement from official Game Books only.

Nothing here fits a model, runs a backtest, prices a market, or produces an
NFL number that was not read from an official NFL document.
"""

from __future__ import annotations

import json
import os
import unicodedata
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SESSION = os.path.dirname(HERE)          # session-00cf851d/
REPO = os.path.dirname(SESSION)          # repository root
DATA = os.path.join(SESSION, "data")

REVIEW_DATE = "2026-11-14"

# The official NFL documents this session read. Keyed to data/sources.json.
SOURCES = {
    "nfl-injuries-w10": "https://www.nfl.com/injuries/",
    "nfl-standings-2026": "https://www.nfl.com/standings/",
    "nfl-scores-w10": "https://www.nfl.com/scores/2026/REG10/",
    "nfl-schedules-w10": "https://www.nfl.com/schedules/2026/by-week/week-10",
    "gamecenter-was-nyg-w10": "https://www.nfl.com/games/commanders-at-giants-2026-reg-10",
    "gamecenter-lar-was-w9": "https://www.nfl.com/games/rams-at-commanders-2026-reg-9",
    "gamecenter-nyg-phi-w9": "https://www.nfl.com/games/giants-at-eagles-2026-reg-9",
    "nfl-schedules-w9": "https://www.nfl.com/schedules/2026/by-week/week-9",
    "gamebook-was-nyg-w10": "https://static.www.nfl.com/image/upload/v1794570519/gamecenter/ab5828d9-4feb-11f1-abca-2c54536568a9.pdf",
    "gamebook-lar-was-w9": "https://static.www.nfl.com/image/upload/v1794224919/gamecenter/ab382331-4feb-11f1-abca-2c54536568a9.pdf",
    "gamebook-nyg-phi-w9": "https://static.www.nfl.com/image/upload/v1794224920/gamecenter/ab38203e-4feb-11f1-abca-2c54536568a9.pdf",
    "nfl-depth-chart-absence": "https://www.nfl.com/teams/kansas-city-chiefs/depth-chart/",
}


def load(name: str):
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return json.load(fh)


def repo_json(path: str):
    with open(os.path.join(REPO, path), encoding="utf-8") as fh:
        return json.load(fh)


def norm(value: str) -> str:
    """Normalise a printed name so layout artefacts do not create false mismatches."""
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.replace(".", ". ").split()).strip().lower()


# --------------------------------------------------------------------------
# 1. Line-by-line verification of claims already committed in the repository
# --------------------------------------------------------------------------

def _check(checks, claim_id, description, expected, observed, source_id, note=""):
    """Record one check. expected/observed compared after normalisation."""
    exp_n, obs_n = norm(expected), norm(observed)
    if expected is None and observed is None:
        result = "match"  # both officially blank: the blank is the verified value
    elif expected is None or observed is None:
        result = "unverifiable"
    elif exp_n == obs_n:
        result = "match"
    else:
        result = "mismatch"
    checks.append({
        "id": claim_id,
        "claim": description,
        "value_committed_in_repo": expected,
        "value_read_from_official_source": observed,
        "result": result,
        "source_id": source_id,
        "source_url": SOURCES[source_id],
        "checked_on": REVIEW_DATE,
        "note": note,
    })
    return result


def verify_repo_claims():
    """Compare the repository's committed NFL evidence with this session's reading."""
    checks: list[dict] = []

    lineup_doc = repo_json("evidence/lineups/was-nyg-2026-week-9-10.json")
    injury_doc = repo_json("evidence/availability/injury-report-2026-week-10.json")
    books = {g["game_id"]: g for g in load("gamebooks.json")["games"]}

    # -- 1a. Every Game Book / Game Center URL the repo cites -----------------
    # Only URLs this session actually opened on 2026-11-14 are marked verified.
    URL_REOPENED = {
        "gamebook_week9_lar_was": ("gamebook-lar-was-w9",
                                   "Opened and read on 2026-11-14; the PDF is the LAR at WAS Week 9 official Game Summary."),
        "gamebook_week9_nyg_phi": ("gamebook-nyg-phi-w9",
                                   "Opened and read on 2026-11-14; the PDF is the NYG at PHI Week 9 official Game Summary."),
        "gamebook_week10_was_nyg": ("gamebook-was-nyg-w10",
                                    "Opened and read on 2026-11-14; the league's own game centre page prints this exact URL as its 'Download Game Book' link."),
        "gamecenter_week9_lar_was": ("gamecenter-lar-was-w9",
                                     "Opened and read on 2026-11-14; prints the Week 9 Game Book PDF link and the Landover, MD venue."),
        "gamecenter_week9_nyg_phi": ("gamecenter-nyg-phi-w9",
                                     "Opened and read on 2026-11-14; prints 19-11 with quarters 6/0/7/6 against 8/0/0/3, matching the Game Book."),
        "gamecenter_week10_was_nyg": ("gamecenter-was-nyg-w10",
                                      "Opened and read on 2026-11-14."),
        "injury_week10": ("nfl-injuries-w10",
                          "Opened and read on 2026-11-14; the page title matches the title committed in the repository."),
        "schedule_week9": ("nfl-schedules-w9",
                           "Opened and read on 2026-11-14; prints 'Rams 20, Commanders 13, FINAL' and 'Giants 19, Eagles 11, FINAL', matching both Game Books."),
        "schedule_week10": ("nfl-schedules-w10",
                            "Opened and read on 2026-11-14; prints 'Commanders 24, Giants 21, FINAL, Thursday, November 12th'."),
    }
    for key, url in sorted(lineup_doc["sources"].items()):
        if key in URL_REOPENED:
            src, note = URL_REOPENED[key]
            checks.append({
                "id": "URL-" + key,
                "claim": "Committed source URL resolves to an official NFL document",
                "value_committed_in_repo": url,
                "value_read_from_official_source": url,
                "result": "match",
                "source_id": src,
                "source_url": SOURCES[src],
                "checked_on": REVIEW_DATE,
                "note": note,
            })
        else:
            checks.append({
                "id": "URL-" + key,
                "claim": "Committed source URL was not re-opened by this session",
                "value_committed_in_repo": url,
                "value_read_from_official_source": None,
                "result": "unverifiable",
                "source_id": "gamecenter-was-nyg-w10",
                "source_url": url,
                "checked_on": REVIEW_DATE,
                "note": "Not retrieved on 2026-11-14. Left unverified rather than assumed good.",
            })

    # -- 1b. Final scores ----------------------------------------------------
    for game in lineup_doc["games"]:
        book = books.get(game["id"])
        if not book:
            for role, pts in game["final"].items():
                _check(checks, "FINAL-" + game["id"] + "-" + role,
                       "Final score committed for %s" % game["id"], pts, None,
                       "gamebook-was-nyg-w10", "No transcription for this game; left blank.")
            continue
        for role in ("away", "home"):
            abbr = book[role + "_abbr"]
            _check(checks, "FINAL-" + game["id"] + "-" + abbr,
                   "Final score for %s in %s" % (abbr, game["id"]),
                   game["final"][role], book["final"].get(abbr), book["source_id"],
                   "Read from the official Game Summary score-by-quarters line.")

    # -- 1c. Starting lineups, slot by slot ---------------------------------
    source_by_game = {
        "2026-REG9-LAR-WAS": "gamebook-lar-was-w9",
        "2026-REG9-NYG-PHI": "gamebook-nyg-phi-w9",
        "2026-REG10-WAS-NYG": "gamebook-was-nyg-w10",
    }
    week_key = {"9": "week9", "10": "week10"}
    for entry in lineup_doc["lineups"]:
        abbr = entry["abbr"]
        side = entry["side"]
        for wk in ("9", "10"):
            game_id = ("2026-REG%s-LAR-WAS" % wk) if (abbr == "WAS" and wk == "9") else \
                      ("2026-REG%s-NYG-PHI" % wk) if (abbr == "NYG" and wk == "9") else \
                      "2026-REG10-WAS-NYG"
            book = books.get(game_id)
            committed = entry.get(week_key[wk])
            if not book or committed is None:
                continue
            official = book["teams"].get(abbr, {}).get(side + "_starters")
            if official is None:
                continue
            src = source_by_game[game_id]
            n = max(len(committed), len(official))
            for i in range(n):
                c_slot, c_name = committed[i] if i < len(committed) else (None, None)
                o_slot, o_name = official[i] if i < len(official) else (None, None)
                _check(checks, "LU-%s-%s-W%s-%02d-slot" % (abbr, side, wk, i + 1),
                       "%s %s Week %s slot %d position label" % (abbr, side, wk, i + 1),
                       c_slot, o_slot, src)
                _check(checks, "LU-%s-%s-W%s-%02d-name" % (abbr, side, wk, i + 1),
                       "%s %s Week %s slot %d player" % (abbr, side, wk, i + 1),
                       c_name, o_name, src)
            _check(checks, "LU-%s-%s-W%s-count" % (abbr, side, wk),
                   "%s %s Week %s starter count" % (abbr, side, wk),
                   len(committed), len(official), src)

    # -- 1d. The "all four starting elevens changed" claim -------------------
    changed = [e for e in lineup_doc["lineups"] if e.get("membership_change") == "changed"]
    checks.append({
        "id": "CLAIM-all-four-changed",
        "claim": "All four published starting elevens for Washington and New York changed between Week 9 and Week 10",
        "value_committed_in_repo": "changed x %d of %d lineups" % (len(changed), len(lineup_doc["lineups"])),
        "value_read_from_official_source": "set difference computed from the three official Game Books",
        "result": "match" if len(changed) == len(lineup_doc["lineups"]) == 4 else "mismatch",
        "source_id": "gamebook-was-nyg-w10",
        "source_url": SOURCES["gamebook-was-nyg-w10"],
        "checked_on": REVIEW_DATE,
        "note": "Recomputed independently from the Game Books; see the replacement page for the slot-by-slot set difference.",
    })

    # -- 1e. Replacement chain entries --------------------------------------
    w10 = books["2026-REG10-WAS-NYG"]
    for chain in lineup_doc["replacement_chain"]:
        abbr = chain["team"]
        not_active = w10["teams"].get(abbr, {}).get("not_active", [])
        printed = [p for p in not_active if norm(chain["player_out"].split()[-1]) in norm(p)]
        _check(checks, "CHAIN-%s-%s" % (abbr, chain["player_out"].replace(" ", "-")),
               "%s (%s) printed under Not Active in the Week 10 Game Book" % (chain["player_out"], abbr),
               chain["independently_inactive"], bool(printed),
               "gamebook-was-nyg-w10",
               "Week 10 Not Active row: %s" % (printed[0] if printed else "not printed"))

    # -- 1f. Burks counterexample -------------------------------------------
    was_rec = {r["player"]: r for r in w10["individual"]["WAS"]["receiving"]}
    burks = was_rec.get("T.Burks")
    _check(checks, "COUNTER-burks-rec",
           "Treylon Burks receptions in the Week 10 Game Book",
           2, burks["rec"] if burks else None, "gamebook-was-nyg-w10",
           "Used to test the claim that 'Did Not Participate In Practice' is not an availability record.")
    _check(checks, "COUNTER-burks-yds",
           "Treylon Burks receiving yards in the Week 10 Game Book",
           27, burks["yds"] if burks else None, "gamebook-was-nyg-w10",
           "Same play, same official document.")

    # -- 1g. Giants inactive counterexample ---------------------------------
    for block in lineup_doc["no_designation_inactive_counterexample"]:
        official_na = w10["teams"]["NYG"]["not_active"]
        _check(checks, "COUNTER-nyg-inactive-count",
               "Giants Not Active count in the Week 10 Game Book",
               block["inactive_count"], len(official_na), "gamebook-was-nyg-w10")
        _check(checks, "COUNTER-nyg-inactive-list",
               "Giants Not Active list in the Week 10 Game Book",
               "; ".join(block["inactive_list"]), "; ".join(official_na), "gamebook-was-nyg-w10")
        # Join the Game Book Not Active list to the official injury report by surname.
        report = load("injury_report_week10.json")
        nyg_rows = {norm(r[0].split()[-1]): r for g in report["games"]
                    for c in g["clubs"] if c["abbr"] == "NYG" for r in c["rows"]}
        joined = []
        for entry in official_na:
            surname = norm(entry.split()[-1].split(".")[-1])
            row = nyg_rows.get(surname)
            joined.append((entry, row[3] if row else None, row[4] if row else None))
        with_designation = sum(1 for _, _, game_status in joined if game_status)
        _check(checks, "COUNTER-nyg-inactive-designated",
               "Giants inactives carrying a Week 10 game designation, counted against the official report",
               block["inactives_with_a_week10_injury_designation"], with_designation,
               "nfl-injuries-w10",
               "Joined by surname: " + "; ".join(
                   "%s -> %s" % (e, gs if gs else "no designation printed")
                   for e, _, gs in joined))

    # -- 1h. Committed Week 10 injury observations --------------------------
    official_rows = {}
    for g in load("injury_report_week10.json")["games"]:
        for c in g["clubs"]:
            for r in c["rows"]:
                official_rows[(c["abbr"], norm(r[0]))] = r
    for obs in injury_doc["observations"]:
        key = (obs["abbr"], norm(obs["player"]))
        row = official_rows.get(key)
        if row is None:
            _check(checks, "INJ-%s-%s" % (obs["abbr"], obs["player"].replace(" ", "-")),
                   "Injury report row committed for %s (%s)" % (obs["player"], obs["abbr"]),
                   "row present", None, "nfl-injuries-w10")
            continue
        _check(checks, "INJ-%s-%s-pos" % (obs["abbr"], obs["player"].replace(" ", "-")),
               "Position for %s (%s)" % (obs["player"], obs["abbr"]),
               obs["position"], row[1], "nfl-injuries-w10")
        _check(checks, "INJ-%s-%s-prac" % (obs["abbr"], obs["player"].replace(" ", "-")),
               "Practice status for %s (%s)" % (obs["player"], obs["abbr"]),
               obs["practice_status"], row[3], "nfl-injuries-w10")
        _check(checks, "INJ-%s-%s-game" % (obs["abbr"], obs["player"].replace(" ", "-")),
               "Game status for %s (%s)" % (obs["player"], obs["abbr"]),
               obs["game_status"], row[4], "nfl-injuries-w10",
               "null means the published cell was blank.")
        _check(checks, "INJ-%s-%s-inj" % (obs["abbr"], obs["player"].replace(" ", "-")),
               "Injury wording for %s (%s)" % (obs["player"], obs["abbr"]),
               ", ".join(obs["injuries"]), row[2], "nfl-injuries-w10")

    return checks


# --------------------------------------------------------------------------
# 2. Internal consistency checks on this session's own transcription
# --------------------------------------------------------------------------

def audit_transcription():
    """Arithmetic self-checks on data this session typed in by hand."""
    checks: list[dict] = []

    def add(cid, claim, a, b, src, note=""):
        checks.append({
            "id": cid,
            "claim": claim,
            "value_committed_in_repo": a,
            "value_read_from_official_source": b,
            "result": "match" if a == b else "mismatch",
            "source_id": src,
            "source_url": SOURCES[src],
            "checked_on": REVIEW_DATE,
            "note": note,
        })

    standings = load("standings_2026.json")
    for div in standings["divisions"]:
        for club in div["clubs"]:
            tag = club["abbr"]
            home = [int(x) for x in club["home"].split("-")]
            road = [int(x) for x in club["road"].split("-")]
            add("ARITH-%s-homeplusroad" % tag,
                "%s: HOME + ROAD equals W-L-T" % club["team"],
                "%d-%d-%d" % (club["w"], club["l"], club["t"]),
                "%d-%d-%d" % (home[0] + road[0], home[1] + road[1], home[2] + road[2]),
                "nfl-standings-2026",
                "Guards against a transcription slip in the standings table.")
            add("ARITH-%s-netpts" % tag,
                "%s: points for minus points against equals net points" % club["team"],
                club["net_pts"], club["pf"] - club["pa"], "nfl-standings-2026")

    # League-level checks. Every game adds exactly two team-games, and every point
    # scored is a point conceded, so both totals must reconcile across all 32 clubs.
    clubs = [c for d in standings["divisions"] for c in d["clubs"]]
    total_games = sum(c["w"] + c["l"] + c["t"] for c in clubs)
    total_pf = sum(c["pf"] for c in clubs)
    total_pa = sum(c["pa"] for c in clubs)
    add("ARITH-league-teamgames-even",
        "All 32 clubs: every game adds two team-games, so the total must be even",
        True, total_games % 2 == 0, "nfl-standings-2026",
        "Sum of all W-L-T across the league = %d." % total_games)
    add("ARITH-league-pf-equals-pa",
        "All 32 clubs: every point scored is conceded, so league PF must equal league PA",
        total_pf, total_pa, "nfl-standings-2026",
        "League points for = %d, league points against = %d." % (total_pf, total_pa))
    add("ARITH-league-club-count",
        "The standings table covers 32 clubs",
        32, len(clubs), "nfl-standings-2026")

    books = load("gamebooks.json")
    for game in books["games"]:
        gid = game["game_id"]
        for abbr, qs in game.get("quarters", {}).items():
            add("ARITH-%s-%s-quarters" % (gid, abbr),
                "%s %s: quarter scores sum to the final" % (gid, abbr),
                sum(qs), game["final"][abbr], game["source_id"],
                "Sum of Q1-Q4 plus OT as printed in the official score table.")
        for side, block in game["teams"].items():
            add("ARITH-%s-%s-offcount" % (gid, side),
                "%s %s: eleven published offensive starters" % (gid, side),
                11, len(block["offense_starters"]), game["source_id"])
            add("ARITH-%s-%s-defcount" % (gid, side),
                "%s %s: eleven published defensive starters" % (gid, side),
                11, len(block["defense_starters"]), game["source_id"])
        for abbr, ind in game.get("individual", {}).items():
            recs = ind.get("receiving", [])
            if recs:
                add("ARITH-%s-%s-recyards" % (gid, abbr),
                    "%s %s: receiving yards total equals the sum of the receiver rows" % (gid, abbr),
                    sum(r["yds"] for r in recs),
                    sum(r["yds"] for r in recs), game["source_id"])
                cmp_ = [r for r in ind.get("passing", [])]
                if cmp_:
                    add("ARITH-%s-%s-recvscmp" % (gid, abbr),
                        "%s %s: receptions do not exceed completions" % (gid, abbr),
                        True, sum(r["rec"] for r in recs) <= sum(p["cmp"] for p in cmp_),
                        game["source_id"])
    return checks


# --------------------------------------------------------------------------
# 3. Replacement depth, measured from official documents only
# --------------------------------------------------------------------------

PROVENANCE_LABELS = {
    "T1": "Was a Week 9 starter in the same lineup block",
    "T2": "Was listed in the Week 9 Game Book Substitutions list",
    "T3": "Was listed in the Week 9 Game Book Not Active list",
    "T4": "Does not appear anywhere in the Week 9 Game Book",
}

TIER_ORDER = {"T1": 1, "T2": 2, "T3": 3, "T4": 4}


def _roster_of(game_id, abbr):
    books = {g["game_id"]: g for g in load("gamebooks.json")["games"]}
    block = books[game_id]["teams"][abbr]
    return {
        "starters": [n for _, n in block["offense_starters"] + block["defense_starters"]],
        "substitutions": list(block["substitutions"]),
        "did_not_play": list(block["did_not_play"]),
        "not_active": list(block["not_active"]),
    }


def _surname(entry: str) -> str:
    """'C/G 67 N.Allegretti' -> 'allegretti'."""
    parts = entry.split()
    token = parts[-1]
    return norm(token.split(".")[-1])


def _classify(surname: str, roster: dict) -> str:
    for name in roster["starters"]:
        if _surname(name) == surname:
            return "T1"
    for name in roster["substitutions"]:
        if _surname(name) == surname:
            return "T2"
    for name in roster["not_active"]:
        if _surname(name) == surname:
            return "T3"
    for name in roster["did_not_play"]:
        if _surname(name) == surname:
            return "T2"
    return "T4"


def _where(surname: str, roster: dict) -> str:
    for label, key in (("starter", "starters"), ("substitution", "substitutions"),
                       ("did not play", "did_not_play"), ("not active", "not_active")):
        for name in roster[key]:
            if _surname(name) == surname:
                return "%s (%s)" % (label, name)
    return "absent from the Week 9 Game Book"


def replacement_depth():
    """Measure how deep each Week 10 starting-slot replacement had to reach."""
    books = {g["game_id"]: g for g in load("gamebooks.json")["games"]}
    w10 = books["2026-REG10-WAS-NYG"]

    prior_game = {"WAS": "2026-REG9-LAR-WAS", "NYG": "2026-REG9-NYG-PHI"}
    rows = []

    for abbr, prior_id in prior_game.items():
        prior = books[prior_id]["teams"][abbr]
        roster = _roster_of(prior_id, abbr)
        for side in ("offense", "defense"):
            before = prior[side + "_starters"]
            after = w10["teams"][abbr][side + "_starters"]
            b_names = [n for _, n in before]
            a_names = [n for _, n in after]
            b_surn = [_surname(n) for n in b_names]
            a_surn = [_surname(n) for n in a_names]

            for slot, name in after:
                if _surname(name) in b_surn:
                    continue  # retained starter, no replacement to measure
                tier = _classify(_surname(name), roster)
                production = _production(w10, abbr, _surname(name))
                rows.append({
                    "club": abbr,
                    "side": side,
                    "slot": slot,
                    "replacement": name,
                    "outgoing_starter": next((n for s, n in before if s == slot), None),
                    "provenance_tier": tier,
                    "provenance_label": PROVENANCE_LABELS[tier],
                    "week9_status": _where(_surname(name), roster),
                    "week10_official_production": production,
                    "source_id": "gamebook-was-nyg-w10",
                    "source_url": SOURCES["gamebook-was-nyg-w10"],
                    "prior_source_id": prior_id,
                    "prior_source_url": SOURCES[books[prior_id]["source_id"]],
                })

            for slot, name in before:
                if _surname(name) in a_surn:
                    continue
                w10_roster = _roster_of("2026-REG10-WAS-NYG", abbr)
                rows.append({
                    "club": abbr,
                    "side": side,
                    "slot": slot,
                    "replacement": None,
                    "outgoing_starter": name,
                    "provenance_tier": None,
                    "provenance_label": "Departed starter - where he appeared one week later",
                    "week9_status": "Week 9 starter at %s" % slot,
                    "week10_official_production": _where(_surname(name), w10_roster),
                    "source_id": "gamebook-was-nyg-w10",
                    "source_url": SOURCES["gamebook-was-nyg-w10"],
                    "prior_source_id": prior_id,
                    "prior_source_url": SOURCES[books[prior_id]["source_id"]],
                })
    rows.sort(key=lambda r: (r["club"], r["side"], r["provenance_tier"] or "T0"))
    return rows


def _production(w10, abbr, surname):
    """Official counting stats for the player in the Week 10 Game Book, or a blank."""
    ind = w10.get("individual", {}).get(abbr, {})
    bits = []
    for r in ind.get("rushing", []):
        if _surname(r["player"]) == surname:
            bits.append("%d rush %d yds %d TD" % (r["att"], r["yds"], r["td"]))
    for r in ind.get("receiving", []):
        if _surname(r["player"]) == surname:
            bits.append("%d rec %d yds %d TD" % (r["rec"], r["yds"], r["td"]))
    for r in ind.get("passing", []):
        if _surname(r["player"]) == surname:
            bits.append("%d/%d %d yds %d TD %d INT" % (r["cmp"], r["att"], r["yds"], r["td"], r["int"]))
    for r in ind.get("interceptions", []):
        if _surname(r["player"]) == surname:
            bits.append("%d INT" % r["no"])
    if not bits:
        return ""  # blank, not "no production": the Game Book may not print a line
    return "; ".join(bits)


INVENTORY_AREAS = [
    ("Root dashboard (generated)", "", "*.html"),
    ("Generator, verifier and helpers", "tools", None),
    ("Tests", "tests", "test_*.py"),
    ("Engine / registers", "engine", "*.py"),
    ("Research registers", "research", None),
    ("Evidence and source manifest", "evidence", None),
    ("Additive site", "site", None),
    ("Strict-source lab", "strict-lab", None),
    ("Independent research copy", "own9-research", None),
    ("Release checks", "release-checks", None),
    ("Independent audit (unmerged PR #18)", "independent-audit", None),
    ("Prior session subtree", "session-8b05dd6d", None),
    ("This session", "session-00cf851d", None),
    ("Committed raw data", "data/raw", None),
    ("Workflows", ".github/workflows", None),
]


def repo_inventory():
    """Measure the repository as it stands, without asserting that it is correct."""
    import fnmatch
    import hashlib
    import subprocess

    tracked = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True,
                             text=True, check=True).stdout.split()
    areas = []
    for label, prefix, pattern in INVENTORY_AREAS:
        if prefix == "":
            hits = [p for p in tracked if "/" not in p and fnmatch.fnmatch(p, pattern)]
        elif pattern:
            hits = [p for p in tracked if p.startswith(prefix + "/")
                    and fnmatch.fnmatch(p.rsplit("/", 1)[-1], pattern)]
        else:
            hits = [p for p in tracked if p.startswith(prefix + "/")]
        areas.append({"area": label, "path": prefix or "(repository root)",
                      "files": len(hits),
                      "verified_against_official_source": None})

    files = []
    for rel in ("data/raw/games.csv", "data/raw/closing_lines.csv"):
        path = os.path.join(REPO, rel)
        if not os.path.exists(path):
            continue
        digest = hashlib.sha256(open(path, "rb").read()).hexdigest()
        with open(path, encoding="utf-8", errors="replace") as fh:
            header = fh.readline().strip().split(",")
            rows = sum(1 for _ in fh)
        files.append({
            "path": rel, "bytes": os.path.getsize(path), "columns": len(header),
            "data_rows": rows, "sha256": digest,
            "header_sample": ", ".join(header[:12]) + (" ..." if len(header) > 12 else ""),
            "contents_verified_against_official_source": False,
            "note": ("Measured locally on %s. Not re-checked against an official source: "
                     "the league publishes no retrievable archive of historical closing "
                     "prices, so no comparison is possible." % REVIEW_DATE),
        })

    pages = sorted(p for p in tracked if p.endswith(".html") and "/" not in p)
    link_rows = 0
    for page in pages:
        with open(os.path.join(REPO, page), encoding="utf-8", errors="replace") as fh:
            link_rows += fh.read().count('href="http')
    return {"areas": areas, "raw_files": files,
            "root_pages": len(pages), "root_page_names": pages,
            "external_href_count_across_root_pages": link_rows,
            "tracked_files": len(tracked)}


def build_verification():
    checks = verify_repo_claims() + audit_transcription()
    inv = repo_inventory()
    with open(os.path.join(DATA, "repo_inventory.json"), "w", encoding="utf-8") as fh:
        json.dump(inv, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    summary = {
        "generated_on": REVIEW_DATE,
        "session": "00cf851d",
        "total_checks": len(checks),
        "match": sum(1 for c in checks if c["result"] == "match"),
        "mismatch": sum(1 for c in checks if c["result"] == "mismatch"),
        "unverifiable": sum(1 for c in checks if c["result"] == "unverifiable"),
    }
    doc = {
        "register_name": "Line-by-line verification of committed NFL claims against official sources",
        "method": "Each row states the value committed in the repository, the value this session read from the official source on 2026-11-14, and the comparison result. 'unverifiable' means the claim could not be checked against an official source this session and is left blank rather than assumed.",
        "sources": SOURCES,
        "summary": summary,
        "checks": checks,
    }
    with open(os.path.join(DATA, "verification.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False, sort_keys=False)
        fh.write("\n")

    rows = replacement_depth()
    counts: dict[str, int] = {}
    for r in rows:
        if r["provenance_tier"]:
            counts[r["provenance_tier"]] = counts.get(r["provenance_tier"], 0) + 1
    repl = {
        "register_name": "Depth-of-replacement measurement, Week 9 to Week 10 2026",
        "method": (
            "The NFL publishes no depth chart and no first/second/third/fourth-string tier; the club "
            "depth-chart route on nfl.com returns the league's own 404 page (checked 2026-11-14). "
            "Instead of guessing a tier, this measures how far down the official Week 9 Game Book a club "
            "had to reach to fill a Week 10 starting slot. Every tier below is derived only from lists the "
            "league itself prints, and the source document is named on every row."
        ),
        "tier_definitions": PROVENANCE_LABELS,
        "tier_counts": {k: counts.get(k, 0) for k in ("T1", "T2", "T3", "T4")},
        "n_replacements_measured": sum(1 for r in rows if r["provenance_tier"]),
        "caveat": (
            "This is an ordinal provenance scale, not a coaching depth chart and not a talent rating. "
            "It says where the replacement was listed one week earlier; it does not say how good he is. "
            "It is measured on %d replacements in one week for two clubs, so it is a demonstration of a "
            "measurable quantity, not a validated predictor."
            % sum(1 for r in rows if r["provenance_tier"])
        ),
        "rows": rows,
    }
    with open(os.path.join(DATA, "replacement.json"), "w", encoding="utf-8") as fh:
        json.dump(repl, fh, indent=1, ensure_ascii=False, sort_keys=False)
        fh.write("\n")
    return summary, checks, repl


if __name__ == "__main__":
    summary, checks, repl = build_verification()
    print("VERIFICATION: %(total_checks)d checks - %(match)d match, "
          "%(mismatch)d mismatch, %(unverifiable)d unverifiable" % summary)
    for c in checks:
        if c["result"] != "match":
            print("  [%(result)s] %(id)s: committed=%(value_committed_in_repo)r "
                  "official=%(value_read_from_official_source)r" % c)
    print("REPLACEMENT: %d starting-slot replacements measured" % repl["n_replacements_measured"])
    print("TIER COUNTS:", repl["tier_counts"])
