# Own9 · Evidence-first NFL research

**Live dashboard:** https://sassnarep3-star.github.io/Own9/

An auditable NFL research workspace covering line origination, singles, parlays,
player-prop combos, seven validation gates, a proposed competition, correlation
requirements, official source scopes and a published review register.

## Executive summary

- **Implemented:** nine static dashboard pages; dependency-free pricing, binary scoring,
  Pearson/phi and two-leg joint-probability primitives; fail-closed eligibility; tests and CI.
- **Not established:** an NFL edge, a numerical NFL line, empirical correlation, completed
  model/backtest, historical executable quote archive, verified skill or funded rewards.
- **Do not confuse software tests with strategy validation.** All candidates remain unvalidated;
  empirical values are blank. No bets are placed or recommended. Luck cannot be removed.
- Every table row links to an official publisher or the primary project repository record.
  Scope labels distinguish facts, context, mathematical definitions and project proposals.
  An official contextual source does **not** substantiate an untested strategy.

## Explore

[Strategies](strategies.html) · [Validation](validation.html) ·
[Leaderboard](leaderboard.html) · [Correlations](correlations.html) ·
[Injuries & depth](injuries.html) · [Decision questions](questions.html) ·
[Data requirements](data.html) · [Sources](sources.html) ·
[Repository audit](audit.html) · [Flagged for Review](flags.html)

### Injury & depth tracking (added 14 Nov 2026)

The [injuries & depth page](injuries.html) transcribes the official NFL Week 10 2026
injury report (retrieved 2026-11-14 from [NFL.com](https://www.nfl.com/injuries/)):
160 players carry an explicit Out/Doubtful/Questionable game status across the 14 listed
games. Official club depth charts ([Chiefs](https://www.chiefs.com/team/depth-chart),
[Seahawks](https://www.seahawks.com/team/depth-chart/),
[Lions](https://www.detroitlions.com/team/depth-chart/)) were verified the same day and
cross-referenced against the report to demonstrate starter→2nd/3rd-string replacement
derivations. All charts are self-labeled "unofficial" by the clubs; conflicts with the
league report (e.g., DET safety) are published on [Flagged for Review](flags.html) F13-F15,
never silently reconciled. No injury-adjusted edge is asserted; no historical point-in-time
injury archive exists in verified evidence.

### Linked subsites (separate owning sessions; not merged into this dashboard)

[site/](site/index.html) (additive dashboard) · [strict-lab/](strict-lab/index.html) ·
[research/](research/index.html) (secondary-source pipeline) ·
[own9-research/](own9-research/index.html) · [release-checks/](release-checks/index.html) ·
[independent-audit/](independent-audit/index.html) (integrated from PR #18, 2026-11-14).
Subsite findings remain governed by their owning sessions' scopes and review registers.

Full [research specification](docs/RESEARCH_SPEC.md) and machine-readable
[source review manifest](evidence/sources.json). The audit describes every starting tracked
file scope. Official pages were read only within the manifest's stated scope; unsupported
NFL values were not imported. Acquisition, fitting, uncertainty inference and prospective
paper evaluation remain unimplemented and explicitly flagged.

## Reproduce (Python 3.10+, no third-party packages)

```sh
python3 tools/build.py
python3 tools/verify.py
python3 -m unittest discover -s tests -v
python3 -m http.server 8000 --bind 0.0.0.0
```

The last command is optional for local viewing. GitHub Pages publishes repository root from
`main`, with relative assets compatible with `/Own9/`. `tools/check.py` remains a compatibility
alias. Generation is deterministic, and CI checks committed outputs before regeneration.
The verifier checks all source-linked rows, local assets/fragments, navigation, and missing
empirical fields; **it does not prove external link availability or factual entailment**.

`research/metrics.py` accepts supplied numbers, not verified market inputs. Test fixtures are
synthetic except a clearly identified arithmetic example from official sklearn documentation.
No secret, API key, paid feed, user data entry, cash prize or automatic wagering is required.

See [COORDINATION.md](COORDINATION.md) for claims, preserved concurrent-session records,
verification performed, irregularities, PRs and deployment results.

---

## Separate inherited research (not certified by this dashboard)

PR #6 later added a secondary-source analysis subtree. Its empirical numbers have not passed this integration’s official row-level verification requirement and are not adopted as verified results. Its original description is retained below as an attributed session record.

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
