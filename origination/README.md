# Line-origination desk

A self-contained section of the Own9 research site. It originates its own NFL
side, total and moneyline numbers, records them in a price-snapshot store,
settles them against a verified results feed, and scores strategies with signal
and money in two separate tables.

**Live:** https://sassnarep3-star.github.io/Own9/origination/

## Read the result first

No strategy on this desk has earned a stake. Every clustered lower bound on
log-loss gain versus the de-vigged closing price is negative, and the desk's own
demotion gate would have demoted all three single-market strategies at the first
evaluable window — bet 200, at the end of the 2010 season. The cross-game parlay
has the best staking number in the desk (12.92% flat over 285 bets) and the
worst signal bound (−0.313), which is precisely why the two are scored apart.

Nothing here is a recommendation to wager.

## What is in here

| Path | What it is |
| --- | --- |
| `index.html` | Executive summary and the state of each of the eight requirements |
| `method.html` | The model, the origination order, and every frozen constant |
| `prices.html` | Price-snapshot store schema, coverage, and the official results-feed checks |
| `originated.html` | Model fair line, market number and difference as three columns |
| `leaderboard.html` | Signal table and staking table, never combined |
| `demotion.html` | Demotion rules, thresholds and the replay |
| `correlations.html` | Every dependence value with its n, and the gate that refuses prices |
| `depth.html` | Replacement depth, read from club-published charts |
| `questions.html` | What we have, what we do not, and what would close each gap |
| `suggestions.html` | Costed, falsifiable proposals awaiting a choice |
| `flagged.html` | Everything wrong, missing or unverified (OD-01 … OD-15) |
| `sources.html` | Source register; a row may cite nothing outside it |
| `ownline/` | The engine: model, metrics, pipeline, scoring, depth register |
| `tools/run.py` | Regenerates every derived file from the committed inputs |
| `tools/build.py` | Renders the pages deterministically |
| `tools/verify.py` | Row sources, local links, origination order, data integrity |
| `data/` | Derived CSV and JSON outputs |
| `evidence/` | Values transcribed from official pages on 2026-11-14 |

## Reproduce

```sh
python3 origination/tools/run.py      # derived data from the committed inputs
python3 origination/tools/build.py    # render the pages
python3 origination/tools/verify.py   # sources, links, ordering, integrity
python3 -m unittest discover -s origination/tests -v
```

Standard library only, Python 3.10+. Deterministic: the same committed inputs
produce byte-identical outputs, and CI fails if regeneration changes anything.

## Rules this section keeps

- Every published table row links to a source in `data/sources.json`. The
  verifier fails the build if a row appears without one.
- A value that cannot be confirmed is rendered blank and flagged. It is never
  inferred, never zeroed, never rounded into existence.
- The opening-price columns are empty on every row, because no source obtained
  for this project records an opening price (flag OD-02).
- No opening number, therefore no closing line value, is claimed anywhere.
- The moneyline is derived from the same margin distribution as the side. The
  code asserts it; the two cannot disagree about one game.
- Correlation is measured, never assumed, and never published without an n.
- Signal ranks. Money is published beside it and cannot move it.

## Inputs and their defects

Both input files are read-only and come from `data/raw/` in the repository root:
`games.csv` (scores and recorded market numbers, 1999–2026) and
`closing_lines.csv` (per-side snapshot, 2006–2018, not used as an input here).

Their provenance, licence and capture times are unknown. Three whole seasons and
one week were checked against the official NFL publisher and matched exactly,
which confirms the score content for those seasons but says nothing about the
rights to use the file. See flags OD-01, OD-03 and OD-13.
