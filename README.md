# Own9 · Evidence-first NFL research

**Live dashboard:** https://sassnarep3-star.github.io/Own9/

An auditable NFL research workspace covering line origination, singles, parlays,
player-prop combos, seven validation gates, a proposed competition, correlation
requirements, official source scopes and a published review register.

Fifteen pages, `tools/build.py`, `tools/verify.py`, verified snapshots and synthetic data only.

## Start with the decisions, not the archive

| If you want to | Read |
| --- | --- |
| Know what is actually open and what would close it | [Decision brief](decision.html) |
| Know what must be known before deciding | [Questions & answers](questions.html) |
| Review and choose an improvement before it is built | [Suggestions](suggestions.html) |
| See who actually started and who replaced them | [Availability tracker](availability.html) |
| See the full Week 10 2026 injury report snapshot and club depth charts | [Injuries & depth](injuries.html) |
| Check a claim against a publisher | [Sources](sources.html) |
| See what is still wrong or unverified | [Flagged for Review](flags.html) |

## What was verified this session

- Three official NFL Game Books (Weeks 9 and 10, 2026) were read for their
  game-day lineups, inactive lists and final statistics. All four published
  starting elevens for Washington and New York changed between the two weeks.
- One starting slot has a fully documented replacement: Lucas Patrick started at
  center in Week 9, was ruled **Out** with a concussion in Week 10, was printed
  under **Not Active**, and Nick Allegretti started at center.
- Two official counterexamples on WHY a designation feed is not a participation
  record: Treylon Burks did not practise yet started and caught 2 passes for 27
  yards, and six of seven Giants inactives carried no injury designation at all.
- **Depth tiers stay caveated, not invented.** The club depth-chart route on
  nfl.com returns an NFL 404, so the availability tracker keeps tier labels blank
  for Game Book substitution chains. Separately, official club depth charts with
  first/second/third/fourth-string columns were retrieved from the Chiefs,
  Seahawks and Lions team sites on 2026-11-14 (self-labeled "unofficial" by the
  clubs) and are published, with both sources cited, on
  [Injuries & depth](injuries.html). No chart is treated as a certified game-day
  depth record; cross-source conflicts are flagged, not reconciled (F19-F21).
- Correlation handling is implemented, not asserted. A joint price is produced
  only when a Fisher-z interval clears a predeclared deadband; otherwise the joint
  price is left blank instead of assuming independence.

## Executive summary

- **Implemented:** fourteen static dashboard pages; dependency-free pricing, binary scoring,
  Pearson/phi, a Fisher-z correlation interval with a predeclared-deadband dependence gate,
  a joint price that refuses to default to independence, fail-closed eligibility, verified
  two-week lineup evidence with a fail-closed validator, and three validated registers
  (16 suggestions, 22 questions, 16 decisions); 80 Python tests, 2 browser suites and CI.
- **Not established:** an NFL edge, a numerical NFL line, empirical correlation, completed
  model/backtest, historical executable quote archive, verified skill or funded rewards.
- **Do not confuse software tests with strategy validation.** All candidates remain unvalidated;
  empirical values are blank. No bets are placed or recommended. Luck cannot be removed.
- Every table row links to an official publisher or the primary project repository record.
  Scope labels distinguish facts, context, mathematical definitions and project proposals.
  An official contextual source does **not** substantiate an untested strategy.

## Explore

[Decision brief](decision.html) · [Questions & answers](questions.html) ·
[Availability](availability.html) · [Suggestions](suggestions.html) ·
[Strategies](strategies.html) · [Validation](validation.html) ·
[Leaderboard](leaderboard.html) · [Correlations](correlations.html) ·
[Data requirements](data.html) · [Sources](sources.html) ·
[Decision questions (earlier register)](decisions-questions.html) ·
[Repository audit](audit.html) · [Flagged for Review](flags.html)

**Decision support** (canonical dashboard at [`site/`](site/index.html)):
[Suggestions](site/suggestions.html) to review and choose a path before changes ·
[Decision questions](site/questions.html) to answer before deciding ·
[Injury & depth](site/injuries.html) starter/backup deficiency tracking.

Full [research specification](docs/RESEARCH_SPEC.md) and machine-readable
[source review manifest](evidence/sources.json). The audit describes every starting tracked
file scope. Official pages were read only within the manifest's stated scope; unsupported
NFL values were not imported. Acquisition, fitting, uncertainty inference and prospective
paper evaluation remain unimplemented and explicitly flagged.

## Reproduce (Python 3.10+, no third-party packages)

```sh
python3 tools/build.py                 # regenerate the 14 root pages
python3 tools/verify.py                # rows, links, fragments, nav, blanks
python3 engine/availability.py         # lineup + injury evidence rules
python3 engine/registers.py            # suggestions, questions, decisions
python3 -m unittest discover -s tests -v
npm ci && node scripts/browser_test_root.cjs   # published pages, real browser
npm test                               # additive site/ dashboard too
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

## Injury & depth tracking (2026-11-14)

The [injuries & depth page](injuries.html) transcribes the official NFL Week 10 2026
injury report (retrieved 2026-11-14 from [NFL.com](https://www.nfl.com/injuries/)):
160 players carry an explicit Out/Doubtful/Questionable game status across the 14 listed
games, with derived team availability-burden counts. Official club depth charts
([Chiefs](https://www.chiefs.com/team/depth-chart),
[Seahawks](https://www.seahawks.com/team/depth-chart/),
[Lions](https://www.detroitlions.com/team/depth-chart/)) were verified the same day and
cross-referenced against the report to demonstrate starter→next-string derivations with
both sources cited. Where no chart was retrieved, replacement columns stay blank (GB, BAL,
MIA depth slots) — never inferred. No injury-adjusted edge is asserted; the snapshot is a
single point-in-time retrieval (F21).

## Linked subsites (separate owning sessions; not merged into this dashboard)

[site/](site/index.html) (additive dashboard) · [strict-lab/](strict-lab/index.html) ·
[research/](research/index.html) (secondary-source pipeline) ·
[own9-research/](own9-research/index.html) · [release-checks/](release-checks/index.html) ·
[independent-audit/](independent-audit/index.html) (integrated from PR #18, 2026-11-14).
Subsite findings remain governed by their owning sessions' scopes and review registers.
