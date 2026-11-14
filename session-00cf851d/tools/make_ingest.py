"""Emit this session's official outcomes in the repository's published feed schema.

`data/raw/verified_results.csv` defines the schema and carries no data rows.
This script produces rows that match it exactly, but writes them inside this
session's own directory. It does not edit `data/raw/verified_results.csv`;
that file belongs to another session, and the decision to ingest is theirs.
"""

import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SESSION = os.path.dirname(HERE)
DATA = os.path.join(SESSION, "data")

# Exact header order published in data/raw/verified_results.csv.
COLUMNS = ["game_id", "season", "week", "home_team", "away_team", "home_score",
           "away_score", "status", "source_url", "retrieved_utc", "overtime",
           "total_line", "spread_line"]

RETRIEVED = "2026-11-14"


def main():
    reg = json.load(open(os.path.join(DATA, "official_results.json"), encoding="utf-8"))
    out = os.path.join(DATA, "verified_results_ingest.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        n = 0
        for r in reg["results"]:
            w.writerow({
                "game_id": r["game_id_in_repo"],
                "season": r["season"],
                "week": r["week"],
                "home_team": r["home_abbr"],
                "away_team": r["away_abbr"],
                "home_score": r["home_points"],
                "away_score": r["away_points"],
                "status": "FINAL",
                "source_url": r["source_url"],
                "retrieved_utc": RETRIEVED,
                # The league schedule page does not print overtime, and the
                # committed prices are not an official source. Both stay blank.
                "overtime": "", "total_line": "", "spread_line": "",
            })
            n += 1
    print("Wrote %d ingest rows to %s (schema: data/raw/verified_results.csv)" % (n, out))
    return n


if __name__ == "__main__":
    main()
