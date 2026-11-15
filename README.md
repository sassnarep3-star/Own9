# Own9 · Evidence-first NFL research

**Live dashboard:** https://sassnarep3-star.github.io/Own9/

An auditable NFL research workspace covering line origination, singles, parlays,
player-prop combos, seven validation gates, a proposed competition, correlation
requirements, official source scopes and a published review register.

Nineteen pages, `tools/build.py`, `tools/verify.py`, verified snapshots and synthetic data only,
plus one market-data audit computed at build time from the files committed in `data/raw/`.

## Start with the decisions, not the archive

| If you want to | Read |
| --- | --- |
| Know what is actually open and what would close it | [Line origination desk](origination/index.html) · [Decision brief](decision.html) |
| Know what must be known before deciding | [Questions & answers](questions.html) |
| Review and choose an improvement before it is built | [Suggestions](suggestions.html) |
| See who actually started and who replaced them | [Availability tracker](availability.html) |
| See the full Week 10 2026 injury report snapshot and club depth charts | [Injuries & depth](injuries.html) |
| Check a claim against a publisher | [Sources](sources.html) |
| See what is still wrong or unverified | [Flagged for Review](flags.html) |
| Know what the committed price file actually contains | [Own lines](lines.html) |
| Know which official source answers an availability question | [Availability sources](availability-evidence.html) |
| See which questions are answered, open, or blocked on a decision | [Question ledger](question-ledger.html) |

## Session f5961230 (15 Nov 2026): repair, Week 10 re-check, decision readiness

- **Repaired two failing checks on main.** The scheduled close job had set all 52 Week 10 markets to
  "closed · pre-kickoff capture" with no market price. The store is back to its open state, and
  `tools/snapshot_close.py` now refuses to write until a real closing-price source exists (F58).
- **[Week 10 re-check](week10-recheck.html).** The official NFL injury page, read on 15 Nov 2026, shows
  347 player rows in 28 club tables, 171 of them with a designation (hand count; the repo capture has 162 by script count). The repo capture agrees on rows but
  has Chargers rows with every injury and designation cell blank, and an Arden Key entry the official page
  does not show (F59, F60). Several figures in the brief (254/279 rows, the "injury-free" Seahawks and
  Bengals, the blank Lions designations) are not reproduced; each claim has a verdict and a link.
- **[Decision readiness](readiness.html).** One row per requirement in the brief, with status, blocking gate
  and the number that would clear it. Counts are summarised on the [overview](index.html).
- **New findings** are on [Flagged for Review](flags.html) as F58–F70. The "VR-xx / VQ-xx" references, the
  136-game log and the price-data policy could not be traced in the repository (F62–F64).
- **Not done:** most of the brief's data-collection items (archives, snap counts, Game Books for 14 games,
  venue transcription, NWS overlays, depth charts for 32 clubs) need sources this session could not
  obtain, and are listed as blocked rather than filled in.

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

- **Implemented:** nineteen static dashboard pages; dependency-free pricing, binary scoring,
  Pearson/phi, a Fisher-z correlation interval with a predeclared-deadband dependence gate,
  a joint price that refuses to default to independence, fail-closed eligibility, verified
  two-week lineup evidence with a fail-closed validator, and three validated registers
  (16 suggestions, 22 questions, 16 decisions); and, from the 14 Nov 2026 integration, a costed
  suggestion sheet (18 items, 4 candidate paths), a question ledger (32 questions, 7 discovery
  probes), an official availability-source register with two checked absences, and a measured
  audit of the committed market-lines file: 105 Python tests, 2 browser suites and CI.
- **Not established:** an NFL edge, a numerical NFL line, empirical correlation, completed
  model/backtest, historical executable quote archive, verified skill or funded rewards.
  Note the nuance on the second clause: an undocumented local file with 20,490 historical quote
  rows *does* exist in `data/raw/` — it is measured on [Own lines](lines.html), is mostly unpriced,
  stops in 2018 and is quarantined, so it establishes no archive that can be cited or backtested.
- **Do not confuse software tests with strategy validation.** All candidates remain unvalidated;
  empirical values are blank. No bets are placed or recommended. Luck cannot be removed.
- Every table row links to an official publisher or the primary project repository record.
  Scope labels distinguish facts, context, mathematical definitions and project proposals.
  An official contextual source does **not** substantiate an untested strategy.

## Line origination desk

A separate desk that originates its own NFL side, total and moneyline numbers and
scores them against the recorded market: [Line origination](origination/index.html).

- Price-snapshot store with separate opening and closing field groups. The opening
  columns are empty on every row because no source obtained records an opening price.
- A results feed verified against the official publisher: the 2010, 2018 and 2025
  seasons match the NFL standings exactly for all 32 clubs on points for and against,
  and all 121 completed 2026 games match the official by-week schedule pages.
- Fair line, market number and difference published as three separate columns.
- Signal and staking in two tables that are never combined.
- Replacement depth read from club-published charts, tier by tier.
- Correlations published with n, behind a dependence gate that refuses a price when
  the interval straddles the declared deadband.
- A demotion gate, defined and replayed: it would have demoted every live candidate
  at the first evaluable window.

No strategy on that desk has earned a stake, and every signal lower bound is negative.

## Explore

[Origination engine](origination-engine.html) · [Verified results](results.html) ·
[Depth of replacement](depth-of-replacement.html) · [Dependence](dependence.html) ·
[Signal / staking split](signal-vs-staking.html) · [Requirements coverage](requirements.html) ·
[Decision brief](decision.html) · [Questions & answers](questions.html) ·
[Question ledger](question-ledger.html) · [Suggestion costs](suggestion-costs.html) ·
[Own lines](lines.html) · [Availability sources](availability-evidence.html) ·
[Availability](availability.html) · [Suggestions](suggestions.html) ·
[Strategies](strategies.html) · [Validation](validation.html) ·
[Leaderboard](leaderboard.html) · [Correlations](correlations.html) ·
[Data requirements](data.html) · [Sources](sources.html) ·
[Decision questions (earlier register)](decisions-questions.html) ·
[Repository audit](audit.html) · [Flagged for Review](flags.html)

## Origination engine (`0167a04c`, 14 Nov 2026)

The eight numbered origination requirements, implemented against committed data rather than
described. Everything below is computed at build time by `engine/origination.py` from files in
`data/`, so no figure can be retyped into prose and drift.

| Page | What it holds |
| --- | --- |
| [Origination engine](origination-engine.html) | The price-snapshot store (committed header-only, 0 records, measured at 0% of games priced), the capture rules, and the side → total → moneyline order with its reconciliation. |
| [Verified results](results.html) | Sixteen official NFL results with a source link per row; three cross-checked against official Game Books; settlement coverage per market family and the ROI readiness gate. |
| [Depth of replacement](depth-of-replacement.html) | Ten ruled-out players matched to the column of an official club depth chart, so depth is a measured number of strings travelled, split by offence and defence. |
| [Dependence](dependence.html) | Four correlations computed from the official results, each published with its n, the interval the gate grants and the verdict. All four fail the predeclared floor. |
| [Signal / staking split](signal-vs-staking.html) | Two record types, two independent rankings, a masking report, and the demotion gate that sends a live strategy back to paper. |
| [Requirements coverage](requirements.html) | The eight requirements line by line, the files inspected, the irregularities found and an executive summary. |

Reproduce: `python3 tools/build.py` · `python3 tools/verify.py` ·
`python3 -m unittest discover -s tests -v`. Findings are published as **F50–F57** on
[Flagged for Review](flags.html), continuing the existing numbering.

Data added: `data/results/verified-results.csv` (16 rows),
`data/snapshots/price-snapshots.csv` (header-only by design) and
`data/depth/club-depth-charts-2026-11-14.json` (KC, SEA, DET charts transcribed column by
column). Two checked absences are recorded, not worked around: the NFL game-centre and scores
routes do not publish the final score as retrievable text, and the schedule route publishes no
kickoff time or overtime flag for completed games.

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
python3 tools/build.py
python3 origination/tools/run.py       # regenerate the origination desk's data
python3 origination/tools/build.py     # regenerate the origination desk's pages                 # regenerate the 19 root pages
python3 tools/verify.py                # rows, links, fragments, nav, blanks
python3 engine/availability.py         # lineup + injury evidence rules
python3 engine/registers.py            # suggestions, questions, decisions
python3 tools/lines_audit.py           # measure the committed market-lines file
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

## Added by session `4f2e0291` on 14 Nov 2026

Nothing above was rewritten to make room for this: `tools/pages_4f2e0291.py` registers four pages
through the same `page()` API, and their own rows, statuses and scoring are untouched.

- **`lines.html`** — the committed `data/raw/closing_lines.csv` is measured, not described: 20,490
  rows, seasons 2006–2018, joins to scores only through an alternate identifier, 85.2% of spread and
  total rows unpriced, and 18 rows (0.088%) disagreeing with outcomes recomputed from the sibling
  score snapshot across 5 games (2 fully inverted). Push coding was checked and is consistent. No
  edge, ROI or backtest claim is drawn from it, and the file stays quarantined.
- **`availability-evidence.html`** — the ten official and club sources read on 14 Nov 2026, each with
  what the page publishes and its limits; 26 transcribed Week 10 report rows and 13 Nov-2026
  reserve-list moves; two checked absences (the league depth-chart path tried 404s, and there is no
  snap or participation category among the eleven statistics categories); the deficiency-model
  specification and six candidate availability signals with every measured column left blank.
  `injuries.html` and `availability.html` carry the wider slate and the lineup evidence; this page
  records the sources behind all of it.
- **`question-ledger.html`** — 32 questions (19 answered from official sources or this repository,
  6 closable with data work, 7 needing an owner decision) plus 7 probes for discovering missing input.
- **`suggestion-costs.html`** — 18 costed suggestions with status, four unranked candidate paths and a
  decision log that records "none yet" rather than implying approval. Nothing marked *Awaiting
  decision* was implemented.

Findings are appended to `flags.html` as **F22–F27** (continuing the existing numbering; three
findings this session had raised are not repeated because F13, F17–F19 and F21 already record them),
and `index.html` gained a directory of all seven published sections with per-section certification
status. `tools/verify.py` gained `www.patriots.com`, the club depth-chart source read here.

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

---

## Added by session `a77d40e1` on 14 Nov 2026 — market-board delta

Six pages registered through the shared `page()` API (`tools/pages_a77d40e1.py`), computed at
build time by `engine/board.py` from the verified feed in `data/board/`. Nothing owned by another
session was rewritten; `flags.html` and `index.html` gained appended sections via the same
`PAGES[...]` mechanism session `4f2e0291` used.

- **`results-feed.html`** — every 2026 final (137 games: Weeks 1–9 complete slates plus the settled
  Week 10 Thursday game) transcribed verbatim from the official league schedule pages
  (`data/board/raw/week-NN.txt` is the transcription record, one file per week). 121 of the finals
  also matched the committed secondary snapshot row-for-row (zero disagreements); the secondary file
  is stale for Weeks 9–10, so those rest on the official transcription alone (F29). This is the feed
  that makes walk-forward scoring, backtests and ROI computable at all; it carries results only.
- **`origination.html`** — Week 11 board: 39 markets originated side first, then the total, then the
  moneyline, enforced mechanically by `engine/board.py` (a total cannot exist without its game's side;
  a moneyline cannot exist without the total; regression-tested). The model's fair line, the market
  line and the difference are separate columns; market and difference are blank by policy because no
  official source publishes wagering prices and no book of record is approved (Q28 lineage).
- **`price-snapshots.html`** — the open/close store: 39 open snapshots captured at origination
  (frozen timestamp `2026-11-14T22:30:00Z`), 39 close snapshots pending by design (blank, never
  fabricated — F30), market-price cells blank throughout.
- **`signal-staking.html`** — two disjoint sheets. The signal sheet scores walk-forward calls on
  official results (weeks 3–9 complete slates: n=104, directional accuracy 63.5%, Brier 0.2356,
  per-week rows published including the partial Week 10). The staking sheet describes the plan only;
  ROI, CLV and exposure caps are blank because no executable prices exist. The live-to-paper gate
  (session `feaa600b`, PR #34) is applied fail-closed: every entry stays Paper. Also carries the new
  BQ1–BQ6 question register and BS1–BS6 suggestion register for review before any decision.
- **`correlations-official.html`** — Pearson correlations computed exclusively from the verified
  official results, with n published beside every value, Fisher-z 95% intervals, and a predeclared
  0.10 deadband that refuses dependence claims inside it: margin↔total r=-0.161 (n=137, declared
  outside deadband), home↔away points r=0.076 (n=137, no claim), club margin week-over-week r=0.086
  (n=242, no claim). Dependency-free implementation, unit-tested against textbook values.
- **`replacement-depth.html`** — the depth of each Week 10 starter replacement as a first-class
  field (`depth_travelled`: 8 chart-derived second-string drops, 5 withheld where no club chart was
  retrieved or sources conflict), with both sources cited per row and the WAS centre chain evidenced
  by two official Game Books.

Verification: `tools/verify.py` PASS (25 pages, 1033 source-linked rows); 126 Python tests,
31 release-checks, availability/decision registers, both browser suites (25 root pages × 2
viewports, 50 axe checks) and `scripts/check_site.py` all pass; regeneration byte-identical.
Sources used this session (registered in `evidence/sources.json`, all retrieved 2026-11-14):
the nine official weekly schedule pages not already on the register. Findings F28–F31 published on
`flags.html`. Shared-file edits, all logged on the board: `tools/build.py` (exec block, NAV_GROUPS,
KEEP_DATE_14, and `tabindex="0"` on generated table wrappers — the axe
`scrollable-region-focusable` violation session `201adb50`'s lines.html tables trigger at mobile
width), `tests/test_own9_delta.py` (two count assertions made dynamic floors), `evidence/sources.json`
(append-only), `README.md` (this section), `flags.html`/`index.html` (appended via `PAGES[...]`).
## Week 10 snapshot store, replacement chains and the demotion gate (2026-11-14, session arena/9a409d93-own9)

Complements to the a77d40e1 market-board delta (results feed, market board, Week 11 store, official
correlations, signal/staking sheets) — this session adds only what that delta did not publish:

- **[Week 10 snapshot store](markets.html)** (`data/snapshots/2026-w10-price-snapshot.json`) — 52 originated
  Week 10 markets (13 pre-kickoff games × spread, total, two moneylines; the Thursday game kicked off before
  the store existed and is explicitly not originated). Every row records `model_fair`, `market_line`, `diff`,
  `opened_at`/`closed_at` as separate fields; `market_line` is null everywhere because no official or licensed
  price source exists (F34) — blanks are policy, never inference. Fair numbers come from the predeclared
  `elo-v1` method (`engine/origination_elo.py`) computed only from official scores; unvalidated outputs (F35).
- **Origination order** — side → total → moneyline, fixed in `engine/origination_elo.py` and enforced by tests.
- **[Replacement chains](replacement-chains.html)** — for the Week 10 report's 76 Out/Doubtful players, the
  replacement **and its depth** (published chart order), derived only where a club depth chart places both
  players: 33 chains across 17 clubs from 19 newly retrieved club charts; 43 withheld chains published with
  reasons (co-listed ties, last-listed, absent from chart, [Houston's checked absence](https://www.houstontexans.com/team/depth-chart/)).
  Chart-relative tiers are weaker than certified game-day depth (F36). a77d40e1's depth-travelled register
  ([replacement-depth.html](replacement-depth.html)) covers the three-chart evidence it retrieved.
- **[Demotion gate](demotion.html)** — quantitative live → paper triggers (trailing ROI, mean edge, CLV rate,
  Brier drift, feed staleness, fail-closed below 20 graded bets) in `engine/origination_elo.py::demotion_gate`,
  boundary-tested in `tests/test_origination.py`; complements the leaderboard's policy gate (feaa600b/a77d40e1).
  Nothing is live, so the gate is armed but never triggered.
- **Leaderboard signal/staking table** — appended to [leaderboard.html](leaderboard.html), cross-linked to
  a77d40e1's [signal-staking.html](signal-staking.html) sheets.
- **Close capture** — `tools/snapshot_close.py` + scheduled [snapshot.yml](.github/workflows/snapshot.yml)
  record `closed_at` (and, if the feed grew, `model_fair_close`) before kickoff, refusing to run if the
  declared method constants changed, and committing only under `data/snapshots/` — the scheduled close run
  a77d40e1's F30 asked for, adopted here for the Week 10 store.

New suggestions S-17–S-21 (price archive, close-capture adoption, sealed backtest, signal/staking adoption,
game-centre row verification) and open questions Q-23/Q-24 (grading operator; re-promotion thresholds) are in
the registers awaiting review. Findings F34–F39 are on [flags.html](flags.html).
