# Own9 · NFL Research Lab

**[Open the dashboard](https://sassnarep3-star.github.io/Own9/site/)** ·
[Flagged for Review](https://sassnarep3-star.github.io/Own9/site/review.html) ·
[Methodology](METHODOLOGY.md) ·
[Verification scope](VERIFICATION.md) ·
[Coordination and publication log](../COORDINATION.md)

## Executive summary

Own9 is an evidence-first foundation for originating NFL probabilities and
comparing single bets, parlays and player-prop combinations. The session base commit
contained only a README. Concurrent work was later inherited and preserved; its
empirical claims are not recertified by this additive dashboard.

- **8 candidate strategies**, explicitly unvalidated, covering all requested bet classes.
- **11 promotion gates** addressing provenance, as-of leakage, holdouts, calibration,
  correlation, execution, statistical uncertainty, multiplicity and forward paper results.
- **13 checked primary-source pages**, each with a limited observed claim and direct
  link; every dashboard data row has an official source/method reference.
- **12 static pages** with category navigation, searchable tables, CSV exports,
  machine-readable manifests and a clearly labeled review register.
- **Tested pricing/evaluation primitives**, not a trained NFL model: push-aware fair
  payouts/EV, discrete PMFs, probability scores, two-event dependence constraints,
  complete-week splits, week-cluster bootstrap and Holm adjustment.

**No proven winning strategies, actual NFL lines, ROI, ranks or correlations are
published.** No provenance-complete historical as-of NFL dataset or executable
odds archive was admitted. Unknown values remain blank and flagged. Luck cannot
be eliminated, finite samples do not certify skill, and past results cannot
guarantee future returns. The leaderboard is a paper-research design, not a
funded competition, automated sportsbook, or wagering recommendation.

### Important findings

The official NFL injury page distinguishes practice status from game status;
blank fields are not inferred. Extracted NFL numerical team-stat rows lacked
reliable column headings and were excluded. A legacy NFL injury-policy link and
an attempted NIST URL returned 404 content. Retrieved operator general rules are
Virginia-specific and cannot establish Washington applicability. See the
[verification register](VERIFICATION.md) and [source manifest](catalog.json).

## Run without secrets or manual inputs

Python 3.11+ is sufficient for the report, engine tests, build and link checks.
The deployed site has no runtime dependencies, analytics, external fonts, API
keys or user-data collection.

```sh
python research/make_catalog.py
python scripts/build_site.py
python -m unittest discover -s tests -v
python scripts/check_site.py
python -m engine.report
python -m http.server 3000 --bind 0.0.0.0 --directory site
```

Optional browser verification uses Node 22.12+ on Linux x64 (or another environment
supported by the bundled Chromium package). Browser tools are dev-only and locked:

```sh
npm ci --ignore-scripts
npm run test:browser
```

This checks all pages at desktop/mobile widths, WCAG A/AA rules using axe, search,
status filtering, CSV source URLs, blank empirical cells, no-JavaScript navigation
and browser errors. Automated accessibility scans are not a full accessibility audit.
Screenshots are temporary ignored files under `build/`, not source artifacts.

## Repository map

| Scope | Purpose |
|---|---|
| `research/make_catalog.py` | Curated source/strategy/requirement registry definition; edit here before regenerating |
| `research/catalog.json` | Generated canonical row manifest; missing empirical data are JSON null |
| `research/METHODOLOGY.md` | Executive brief, data contract, derivations, assumptions, validation and reward design |
| `research/VERIFICATION.md` | Checked scope, source limitations and verification levels |
| `engine/` | Dependency-free probability/evaluation utilities and abstaining status report |
| `tests/` | Synthetic arithmetic fixtures and manifest invariants, never NFL backtests |
| `scripts/` | Deterministic site build, HTML/link/source checks and browser verification |
| `site/` | Deployable static output and local assets; readable without JavaScript |
| `.github/workflows/pages.yml` | Tests on branch/PR; verifies generated output; existing main/root Pages publishing deploys after merge |
| `COORDINATION.md` | Shared claims, file scopes, irregularities and publication evidence |

The workflow reruns daily and on changes. It checks existing evidence; it **does
not fetch fresh NFL data**, automatically fit models or place wagers. The research
snapshot date remains 2026-11-04 until research is actually refreshed. A rebuild
never turns old evidence into new evidence. The isolated `site/` dashboard publishes beneath existing main/root Pages.
The shared root dashboard remains unchanged. Settings writes were not permitted;
no configuration change or extra publishing branch is required.

## What remains necessary before empirical claims

Rights-cleared official historical game/player/play snapshots, publication/as-of
metadata, synchronized actual singles/prop/combo quotes, ticket-specific settlement
rules, fitted and independently evaluated models, registered statistical thresholds,
and forward paper evidence. Until then, automatic abstention is the correct output.
Local source references and passing code tests do not substitute for these inputs.

## Coordination

Read `COORDINATION.md` before editing. Our session changes only additive files listed in its corrected claim.
The existing root integration owner retains shared root navigation outputs. Arena fixes this session's branch to
`arena/a54b6387-own9`; all work and pushes remain on that branch. Open a PR from it
to main and use a successful verification run before merging and publishing.
