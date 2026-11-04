# Own9 · NFL own-line research

A static research dashboard (GitHub Pages: https://sassnarep3-star.github.io/Own9/) for originating NFL lines from an own model, testing them against a market baseline, measuring correlations, and applying validation gates before any strategy can enter a leaderboard.

**Status:** Not validated. No strategy passed all seven gates. Market lines come from an unverified third-party file. Player props were not run. Nothing here is betting advice. Sports wagering is restricted in Washington State (see the Flagged for Review page).

## Contents

| Path | Purpose |
|---|---|
| `data/source/games.csv` | Snapshot of nflverse/nfldata games (third-party). sha256 `81a2786f…d222f` |
| `data/source/verified_games.csv` | 5 games checked line by line against official NFL game-center pages |
| `tools/analyze.py` | Walk-forward Elo own line, singles, parlays, correlations, gates → `data/results/` |
| `tools/build.py` | Generates the 12 HTML pages from the results |
| `tools/check.py` | Checks page set, local links, official-source link in every table row, summary consistency |
| `data/results/` | `summary.json`, bet-level CSV, game-level CSV |

## Reproduce

```bash
python3 tools/analyze.py && python3 tools/build.py && python3 tools/check.py
```

Requires Python 3 only (standard library). The analysis is deterministic (seeded bootstrap).

## Method (predeclared)

- Own line: Elo, K = 20, home field 65 Elo, 25 Elo per point, one-third reversion to 1500 each season, using only earlier games.
- Periods: tuning 2006–2015, sealed test 2016–2025, forward check 2026. Thresholds 1, 2, 3 points.
- Pricing: -110 on each side (assumed). Breakeven 52.38%.
- Gates G1–G7 as listed on the Validation page.

## Verification rules

- Every table row links to an official site (nfl.com, wsgc.wa.gov, nist.gov) in its last cell. Third-party sources are labelled.
- Values that cannot be confirmed from an official source are marked unverified. Market-dependent figures are marked as computed from unverified lines.
- Only the 5 games in `verified_games.csv` have scores confirmed against NFL.com.

Earlier research framework and references: see COORDINATION.md log.
