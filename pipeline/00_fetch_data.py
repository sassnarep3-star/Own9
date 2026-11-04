#!/usr/bin/env python3
"""T02 - Fetch the third-party source data at a pinned commit and record provenance.

Source: nflverse/nfldata (Lee Sharpe's "Analyzing NFL Data" repository).
Pinned commit + SHA256 checksums are stored in data/manifest.json. Nothing downstream may
read a file whose checksum does not match the manifest; pipeline/01_audit.py enforces that.

No API keys, no scraping, no manual input.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_REPO = ROOT / "data" / "raw" / "nfldata"
MANIFEST = ROOT / "data" / "manifest.json"

REPO_URL = "https://github.com/nflverse/nfldata.git"
# Files the pipeline consumes. Names are taken verbatim from the upstream data/ directory.
FILES = [
    "games.csv",
    "closing_lines.csv",
    "initial_lines.csv",
    "sc_lines.csv",
    "win_totals.csv",
    "standings.csv",
    "teams.csv",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=RAW_REPO, check=True, capture_output=True, text=True
    ).stdout.strip()


def clone() -> str:
    if not (RAW_REPO / ".git").exists():
        RAW_REPO.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "--depth", "1", REPO_URL, str(RAW_REPO)],
            check=True,
            capture_output=True,
            text=True,
        )
    return git("rev-parse", "HEAD")


def checkout(sha: str) -> bool:
    """Try to move the shallow clone to the pinned commit. Returns True on success."""
    head = git("rev-parse", "HEAD")
    if head == sha:
        return True
    try:
        subprocess.run(
            ["git", "fetch", "--depth", "1", "origin", sha],
            cwd=RAW_REPO,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "checkout", "--force", sha],
            cwd=RAW_REPO,
            check=True,
            capture_output=True,
            text=True,
        )
        return git("rev-parse", "HEAD") == sha
    except subprocess.CalledProcessError:
        return False


def main() -> int:
    head = clone()
    pinned = None
    if MANIFEST.exists():
        pinned = json.loads(MANIFEST.read_text()).get("commit_sha")

    drift = False
    if pinned and pinned != head:
        if checkout(pinned):
            head = pinned
        else:
            drift = True
            print(
                f"[warn] could not check out pinned commit {pinned}; using {head}. "
                "Manifest will be rewritten and the drift flagged.",
                file=sys.stderr,
            )

    files = {}
    for name in FILES:
        path = RAW_REPO / "data" / name
        if not path.exists():
            raise SystemExit(f"missing upstream file: {name}")
        files[name] = {
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
            "lines": sum(1 for _ in path.open("rb")),
            "source_url": f"https://github.com/nflverse/nfldata/blob/{head}/data/{name}",
            "raw_url": f"https://raw.githubusercontent.com/nflverse/nfldata/{head}/data/{name}",
        }

    commit_date = git("log", "-1", "--format=%cI")
    manifest = {
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dataset": "nflverse/nfldata (Lee Sharpe, 'Analyzing NFL Data')",
        "repo_url": "https://github.com/nflverse/nfldata",
        "commit_sha": head,
        "commit_date_utc": commit_date,
        "pin_drift": drift,
        "documentation_urls": {
            "DATASETS.md": f"https://github.com/nflverse/nfldata/blob/{head}/DATASETS.md",
            "README.md": f"https://github.com/nflverse/nfldata/blob/{head}/README.md",
        },
        "license_note": (
            "The upstream repository contains no LICENSE file, so redistribution terms are "
            "undefined. These CSVs are therefore NOT vendored into this repository; they are "
            "fetched at the pinned commit above and only derived, aggregated outputs are "
            "committed. Flagged on the site's 'Flagged for Review' page."
        ),
        "files": files,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"pinned commit {head} ({commit_date}) - {len(files)} files hashed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
