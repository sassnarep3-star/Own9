# Own9 · NFL Research Lab

**Live site:** https://sassnarep3-star.github.io/Own9/

A source-linked, static research dashboard for originating NFL fair lines,
registering signal hypotheses and evaluating reproducible forecasting skill.
The original dashboard from PR #1 is preserved and expanded by this integration.

## Executive decision

**Research only; do not deploy capital.** Eight candidate strategies are proposed,
none has passed validation. No independently verified point-in-time outcomes-and-
quotes dataset, trained NFL model, real-data backtest, measured correlation or
funded reward exists. Luck cannot be removed. Missing measured values stay
`null` in JSON and blank (explicitly labeled unverified) in tables.

The [executive summary](downloads/executive-summary.md),
[Evidence library](https://sassnarep3-star.github.io/Own9/sources.html), and
[Flagged for Review](https://sassnarep3-star.github.io/Own9/flags.html) describe
verified source scope, proposals and remaining evidence gaps separately.

## Contents

- Eight pages: overview, strategies, pricing/correlation, validation,
  leaderboard, evidence library, requirements/audit and flagged review.
- Eight candidates covering game/player singles, cross-game parlays and
  same-game prop combinations. Input requirements and falsification tests included.
- Eight fail-closed evidence gates; competition rules and noncash recognition
  proposals, not an operating or funded prize program.
- Fourteen official contextual references checked on 2026-11-04, with excerpts,
  scope and limitations. Every one of 97 table rows has official reference links.
- Twelve source-linked CSV exports; progressive table search; responsive navigation;
  downloadable executive summary, policy, catalog and readiness report.
- Dependency-free mathematical utilities: score-PMF price integration, refund-aware
  EV, two-binary-leg joint feasibility, phi, cluster bootstrap, Brier/log loss,
  Holm correction and structural point-in-time checks.
- Synthetic unit tests, schema/link/asset checks and deterministic generation.

## Run locally (Python 3.11+; no dependencies or secrets)

```sh
python3 tools/run_analysis.py
python3 tools/build.py
python3 -m unittest discover -s tests -v
python3 tools/check.py
python3 -m http.server 8000 --bind 0.0.0.0
```

Open `http://localhost:8000/Own9/` only when the server serves a parent directory
containing `Own9`; with the commands above, open `http://localhost:8000/` instead.
The deployed site uses relative paths and works under GitHub Pages `/Own9/`.

`tools/check.py` checks local links, fragments, assets, table citation registration,
source scopes, exports, explicit empty-value labels and deterministic generation.
**It does not verify external source truth, prove a scientific claim or backtest
an NFL model.** Passing code tests must not be described as passing strategy gates.

## Automated readiness and publication

`research/observations.json` deliberately contains no unverified observations.
The runner has no random-data fallback. It emits a blocked readiness report
without user input. Even structurally valid records cannot promote a strategy:
independent provenance, model and experiment review have not been implemented.
Licensed data cannot be obtained by a static site or reconstructed retroactively.

GitHub Actions builds/tests on PRs and main, with a weekly readiness rebuild.
Only checked static site assets and research artifacts are uploaded for Pages.
Deployment runs only from main after the build checks. This does not place bets,
request credentials, obtain paid data or re-certify dynamic source facts.

## File map

| Scope | Purpose |
| --- | --- |
| `research/catalog.json` | Section-checked source ledger, hypotheses, requirements and review flags |
| `research/policy.json` | Proposed validation and competition policy; numeric settings are not verified adequacy guarantees |
| `research/observations.json`, `research/run.json` | Empty evidence input and generated blocked readiness output |
| `analysis/core.py` | Mathematical/structural primitives; assumptions documented in docstrings |
| `tests/` | Synthetic tests only, not empirical findings |
| `tools/` | Readiness, deterministic site generation, structural checks, deployment packaging |
| Root HTML/CSS/JS, `downloads/` | Published dashboard and exports |
| `COORDINATION.md` | Shared claims, preserved session history, sources, conflicts, PR and deployment log |

## Important flags

- Inherited broad NIST heat-flow-meter citation was not NFL validation authority.
- A candidate NFL injury-policy URL returned a soft 404 and was excluded.
- DraftKings general rules inspected were Virginia-scoped; do not infer
  Washington legal eligibility or universal sportsbook settlement rules.
- UK regulator qualitative staking research is not US law or a staking prescription.
- Official method maintainers document definitions, not the validity of Own9
  signals, numerical policy thresholds or profit claims.

See the full review register on the site. Coordination records preserve earlier
work; this session uses only its platform-assigned branch.
