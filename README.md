# Own9 — NFL signal research

Research project to build our own NFL lines, test single-bet, parlay, and prop-combo strategies
against validation gates, measure outcome correlations, and publish every number with a source.

**Live site:** https://sassnarep3-star.github.io/Own9/

## Layout
- `analysis/analyze.py` — data pipeline: loads `data/raw/games.csv`, runs the walk-forward own-line model,
  grades 15 pre-specified strategies with gates G1–G5, computes correlations and parlay joint probabilities.
  Writes `docs/data/*.json`.
- `analysis/build_site.py` — builds the static pages in `docs/` (landing, executive summary, games, strategies,
  correlations, own lines, props, rules & legal, sources, flagged for review).
- `data/raw/games.csv` — copy of `nflverse/nfldata` `data/games.csv` (commit `d5c8272`). Secondary source.
- `docs/` — the GitHub Pages site (Pages source: `main` branch, `/docs` folder).
- `COORDINATION.md` — shared task board for parallel agent sessions.

## Reproduce
```bash
python -m venv .venv && . .venv/bin/activate && pip install pandas numpy scipy
python analysis/analyze.py
python analysis/build_site.py
```

## Important
- Betting lines are not published by the NFL; all lines are labelled **Unverified** (see `docs/flagged.html`).
- Research only, not betting advice. Sports wagering in Washington is limited to tribal casinos
  (Washington State Gambling Commission).
