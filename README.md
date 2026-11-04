# Own9 · NFL research

A static research dashboard for proposed NFL line-origination strategies, validation gates, a placeholder leaderboard and flagged limitations. Open `index.html` locally or visit the [GitHub Pages site](https://sassnarep3-star.github.io/Own9/).

**Status:** research framework only. No predictions, market data, measured correlations, validated strategies, actual rewards or automated wagering are provided. Luck cannot be removed. References on proposal rows provide context, not endorsement. Blank values are unverified.

## Build and check

Requires Python 3. Run `python3 tools/build.py` to regenerate the five HTML pages and `python3 tools/check.py` to check local link targets and the presence of permitted reference hosts in every table row. This is not an external link checker or a verification of source relevance. Pages deploys from the repository root on `main`.

---

## Research site (`research/`) — NFL signal research (arena/75504db2-own9)

Separate from the root site above. The research pipeline builds its own pages and data.

- Live: https://sassnarep3-star.github.io/Own9/research/
- `analysis/analyze.py` — data pipeline (`research/data/site/*.json`): 15 pre-specified strategies graded with gates G1–G5,
  correlations and parlay joint probabilities, walk-forward own-line model.
- `analysis/build_site.py` — builds `research/*.html` (landing, executive summary, games, strategies, correlations,
  own lines, player props, rules & legal, sources, flagged for review).
- `data/raw/games.csv` — copy of `nflverse/nfldata` `data/games.csv` (commit `d5c8272`, secondary source).

Reproduce:
```bash
python -m venv .venv && . .venv/bin/activate && pip install pandas numpy scipy
python analysis/analyze.py && python analysis/build_site.py
```

Betting lines are not published by the NFL, so all lines are labelled **Unverified** (`research/flagged.html`).
Research only, not betting advice. Sports wagering in Washington is limited to tribal casinos (Washington State Gambling Commission).
