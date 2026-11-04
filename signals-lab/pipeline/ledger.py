"""Write a transcribed NFL.com standings page to data/verified/nfl_standings/<season>.csv.

Usage (from a Python shell or script):
    from ledger import write_standings
    write_standings(2024, "DET,15,2,0,564,342; KC,15,2,0,385,326; ...", retrieved="2026-11-04")

Rows are transcribed by hand from https://www.nfl.com/standings/league/<season>/REG in the order shown on the page. The only
automation is attaching the team name for the NFL.com logo code and the source URL; pipeline/verify.py then reconciles every row
against the game-center feed, so any transcription slip shows up as a mismatch instead of silently passing.
"""
from __future__ import annotations
import csv
from pathlib import Path
from config import VERIFIED

NAMES = {
    "ARI": "Arizona Cardinals", "AZ": "Arizona Cardinals", "ATL": "Atlanta Falcons", "BAL": "Baltimore Ravens", "BUF": "Buffalo Bills",
    "CAR": "Carolina Panthers", "CHI": "Chicago Bears", "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns", "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos", "DET": "Detroit Lions", "GB": "Green Bay Packers", "HOU": "Houston Texans", "IND": "Indianapolis Colts",
    "JAX": "Jacksonville Jaguars", "KC": "Kansas City Chiefs", "LA": "Los Angeles Rams", "LAC": "Los Angeles Chargers",
    "LV": "Las Vegas Raiders", "MIA": "Miami Dolphins", "MIN": "Minnesota Vikings", "NE": "New England Patriots",
    "NO": "New Orleans Saints", "NYG": "New York Giants", "NYJ": "New York Jets", "PHI": "Philadelphia Eagles",
    "PIT": "Pittsburgh Steelers", "SEA": "Seattle Seahawks", "SF": "San Francisco 49ers", "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans", "WAS": "Washington Commanders",
    # historical names as displayed on NFL.com for earlier seasons (franchise mapping handled in verify.py)
    "OAK": "Oakland Raiders", "SD": "San Diego Chargers", "STL": "St. Louis Rams",
}


def write_standings(season: int, compact: str, retrieved: str, phase: str = "REG") -> Path:
    url = f"https://www.nfl.com/standings/league/{season}/{phase}"
    out = VERIFIED / "nfl_standings" / f"{season}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = [r.strip() for r in compact.replace("\n", ";").split(";") if r.strip()]
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["season", "nfl_code", "team_name", "w", "l", "t", "pf", "pa", "source_url", "retrieved_utc"])
        for r in rows:
            code, W, L, T, PF, PA = [x.strip() for x in r.split(",")]
            w.writerow([season, code, NAMES[code], int(W), int(L), int(T), int(PF), int(PA), url, retrieved])
    print(f"wrote {out} ({len(rows)} rows)")
    return out
