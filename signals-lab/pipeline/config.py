"""Shared paths and constants for the signals lab (session efe45667)."""
from __future__ import annotations
import os
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
RAW = Path(os.environ.get("SIGNALS_RAW_DIR", Path.home() / ".cache" / "own9" / "raw"))
DATA = LAB / "data"
VERIFIED = DATA / "verified"
DERIVED = DATA / "derived"
RESULTS = DATA / "results"
REGISTRY = LAB / "registry"

# Seasons whose NFL game-center feed is parsed. A season is only *used* by the models if it passes the
# official NFL.com standings reconciliation (pipeline/verify.py); anything else is excluded (fail closed).
RAW_SEASONS = list(range(2015, 2026))      # nflfastR-raw has the NFL game-center feed through the 2025 postseason
CURRENT_SEASON = 2026                      # in progress on 2026-11-04 (schedule/results from nfldata, verified on NFL.com)

NFLFASTR_RAW_REPO = "https://github.com/nflverse/nflfastR-raw.git"
NFLDATA_REPO = "https://github.com/nflverse/nfldata.git"
