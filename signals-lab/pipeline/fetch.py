"""Fetch the machine-readable inputs and write data/manifest.json.

Sources (all on github.com, the only code host reachable from the sandbox):
  * nflverse/nflfastR-raw  -> raw/<season>/<season>_<week>_<away>_<home>.json.gz : the NFL game-center feed
    (final score by quarter, drives, plays and per-play player stat records) archived per game.
  * nflverse/nfldata       -> data/games.csv : schedule/results (used for the in-progress 2026 season and as an
    independent cross-check). Betting-line columns in that file are NOT used anywhere in this project.

Usage:  python pipeline/fetch.py            (idempotent; re-run to refresh)
"""
from __future__ import annotations
import datetime as dt, hashlib, json, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import RAW, DATA, RAW_SEASONS, NFLFASTR_RAW_REPO, NFLDATA_REPO


def run(cmd, cwd=None):
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=cwd, check=True, text=True, capture_output=True).stdout.strip()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sparse_clone_raw() -> Path:
    RAW.mkdir(parents=True, exist_ok=True)
    dest = RAW / "nflfastR-raw"
    if not dest.exists():
        run(["git", "clone", "--depth", "1", "--filter=blob:none", "--no-checkout", NFLFASTR_RAW_REPO, str(dest)])
        run(["git", "sparse-checkout", "init", "--no-cone"], cwd=dest)
    patterns = [f"/raw/{s}/*.json.gz" for s in RAW_SEASONS]
    run(["git", "sparse-checkout", "set", "--no-cone", *patterns], cwd=dest)
    run(["git", "checkout"], cwd=dest)
    return dest


def clone_nfldata() -> Path:
    dest = RAW / "nfldata"
    if not dest.exists():
        run(["git", "clone", "--depth", "1", "--filter=blob:none", "--no-checkout", NFLDATA_REPO, str(dest)])
        run(["git", "sparse-checkout", "init", "--no-cone"], cwd=dest)
    run(["git", "sparse-checkout", "set", "--no-cone", "/data/games.csv", "/data/standings.csv"], cwd=dest)
    run(["git", "checkout"], cwd=dest)
    return dest


def main():
    manifest = {"generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "sources": {}}
    raw = sparse_clone_raw()
    files = sorted((raw / "raw").glob("*/*.json.gz"))
    per_season = {}
    for f in files:
        per_season.setdefault(f.parent.name, []).append(f)
    combined = hashlib.sha256()
    for f in files:
        combined.update(f.name.encode()); combined.update(sha256(f).encode())
    manifest["sources"]["nfl_game_center_feed"] = {
        "repo": "https://github.com/nflverse/nflfastR-raw",
        "commit": run(["git", "rev-parse", "HEAD"], cwd=raw),
        "commit_date": run(["git", "show", "-s", "--format=%cI", "HEAD"], cwd=raw),
        "path_pattern": "raw/<season>/<season>_<week>_<away>_<home>.json.gz",
        "files_per_season": {s: len(v) for s, v in sorted(per_season.items())},
        "files_total": len(files),
        "combined_sha256_of_name_and_file_hashes": combined.hexdigest(),
        "note": "Archived copy of the NFL game-center JSON feed; every value used is reconciled to NFL.com pages in data/verified/.",
    }
    nd = clone_nfldata()
    g = nd / "data" / "games.csv"
    manifest["sources"]["nfldata_games_csv"] = {
        "repo": "https://github.com/nflverse/nfldata",
        "commit": run(["git", "rev-parse", "HEAD"], cwd=nd),
        "commit_date": run(["git", "show", "-s", "--format=%cI", "HEAD"], cwd=nd),
        "path": "data/games.csv", "bytes": g.stat().st_size, "sha256": sha256(g),
        "note": "Third-party schedule/results table. Betting-line columns are never used. Scores are reconciled to NFL.com before use.",
    }
    out = DATA / "manifest.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
