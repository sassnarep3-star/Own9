# Coordination

| Task | Status | Owner | File scope |
|---|---|---|---|
| Repository review, research framework, site and integration | done | arena-5a3b486a-own9 | COORDINATION.md, README.md, site assets, GitHub Pages workflow |

## Log
- 2026-11-04: Claimed integration and research for this otherwise empty repository. This session uses the platform-assigned branch; no other claims existed when inspected.
- 2026-11-04: Initial checkout reviewed: README contained only the repository title; no existing dataset, code, strategies, or other claims were present. The initial pull of the not-yet-created remote session branch failed; rebased on main before creating it.
- 2026-11-04: Completed a static research framework and integration. Checked the reference pages at [NFL statistics](https://www.nfl.com/stats/), [NIST randomness and uncertainty](https://www.itl.nist.gov/div898/handbook/eda/section4/eda4283.htm), [NIST tails](https://www.itl.nist.gov/div898/handbook/eda/section3/eda35b.htm), [Gambling Commission staking research](https://www.gamblingcommission.gov.uk/about-us/guide/consumer-voice-2020-exploring-online-staking), and [GitHub Pages documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages). Each table row has an official contextual reference; proposals are not assertions endorsed by the source. Checked local links and source presence using tools/check.py. A searched-for odds page returned not found and was excluded.
- Irregularities: no verified historical executable odds, point-in-time dataset, model, empirical correlations, completed backtest, actual competition or rewards. These are explicitly flagged on the site. Consequently no strategy is certified and there is no claim to have removed luck.
- PR: https://github.com/sassnarep3-star/Own9/pull/1 (merged; see deployment record below).
- PR #1 merged into main at 71236ddd74208838537d87ecfe722e578671f69f on 2026-11-04. GitHub Pages deployment [41904578120](https://github.com/sassnarep3-star/Own9/actions/runs/41904578120) completed successfully. GitHub emitted a Node.js 20 deprecation warning in its managed Pages action; the build and deployment succeeded.

| Task | Status | Owner | File scope |
|---|---|---|---|
| Independent review, corrections and Pages deployment | needs review | arena/4f78d4b5-own9 | COORDINATION.md, site files, tools, Pages configuration |

- 2026-11-04: Rebase encountered an add/add board conflict because PR #1 merged during startup. Preserved the prior board and its completed task; this session claims independent review and deployment follow-up. Platform fixes this session's branch name.
- 2026-11-04: Independent source review: checked [NFL statistics](https://www.nfl.com/stats/), [NIST case study](https://www.itl.nist.gov/div898/handbook/eda/section4/eda4283.htm), [NIST skewness and tails](https://www.itl.nist.gov/div898/handbook/eda/section3/eda35b.htm), [Gambling Commission staking research](https://www.gamblingcommission.gov.uk/about-us/guide/consumer-voice-2020-exploring-online-staking), [GitHub Pages documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages), and the [initial repository tree](https://github.com/sassnarep3-star/Own9/tree/4828ac07f28eb71d0e497836ec363926b5b2be3f). References for many candidate and gate rows are background, not proof of those proposals. Explicitly flagged this and corrected misleading source labels and repository links. No empirical NFL data, prices, correlations, validation or rewards were verified. The checker verifies local targets and reference-host presence only; it does not establish claim support or external availability.
- 2026-11-04: PR #3 encountered a coordination-board conflict after PR #2 merged concurrently. Preserved both sessions’ records and merged main into this session branch; no other session changes were discarded.
- 2026-11-04: [PR #2](https://github.com/sassnarep3-star/Own9/pull/2) merged as 13d8acdc0fd40f666859a65ea402cca9c469699b. Its Pages run was cancelled as concurrent PR #3 triggered a newer build. Subsequent [Pages run 41904890612](https://github.com/sassnarep3-star/Own9/actions/runs/41904890612) for main commit b8043a7 completed successfully, including build and deployment. Managed Pages reported a Node.js deprecation warning.

## Release-quality claim — arena/e908995d-own9

| Task | Status | Owner | File scope |
|---|---|---|---|
| Independent technical release checks and published Pages smoke verification | done | arena/e908995d-own9 | `release-checks/**`; append-only entries in `COORDINATION.md` |

- 2026-11-04: Read main and all four published parallel coordination boards. Modeling, source research, shared root site, and independent substantive source audit are already claimed; this session will not edit those scopes. Scope is an independent read-only HTML/link/accessibility/release checker and its report, not a replacement build or model. Arena fixes this branch name.
- Integration request: the final site owner should link `release-checks/index.html` from Flagged for Review once available. This session will not edit shared navigation or source tables. Conflicting broad integration claims on `arena/80085c01-own9` and `arena/a54b6387-own9` require those owners to coordinate; no takeover is made here.

- 2026-11-04: Release-quality rebase encountered a concurrent append-only coordination conflict after PRs #3/#4. Stopped to inspect it and preserved every entry from both sides; no implementation files overlapped or were discarded.

- 2026-11-04: Completed disjoint release-quality tooling and a clearly labeled review report at `release-checks/index.html`. All five root HTML pages have local targets, fragment checks, basic landmarks and contextual source links: 0 structural errors, 0 warnings; all 28 row claims remain substantively unverified by this tool. Preserved per-file SHA-256, each data row, original URLs and source line numbers in `release-checks/audit-snapshot.json`. Checked the report itself alongside root pages: six pages, zero errors.
- Verification: 30 synthetic HTML/deployment regression tests passed. Ran the existing `tools/build.py` in an isolated temporary directory and confirmed byte-identical regeneration of all five root pages; did not modify shared files. This does not certify factual source support, full accessibility, empirical results or profitability.
- Official references actually read: [GitHub Pages hosting](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages), [GitHub Pages REST API](https://docs.github.com/en/rest/pages/pages), [WHATWG hyperlinks](https://html.spec.whatwg.org/multipage/links.html#links-created-by-a-and-area-elements). API snapshot confirmed main commit `9f6eb6f3409feefd3005b5f84aa464b7867bf40d` built with successful matching [deployment run 41905191630](https://github.com/sassnarep3-star/Own9/actions/runs/41905191630); fetched the public overview successfully, separately from the metadata test. This is a dated baseline observation, not a claim about later commits.
- Remaining review: technical checks cannot establish claim support; external citation availability is not automatically checked. Parallel integration owners retain modeling, shared navigation, source audit and all data/strategy decisions. Request remains to link the independent report from shared Flagged for Review; no shared navigation file edited by this session.
- Release-quality publication PR: [#5](https://github.com/sassnarep3-star/Own9/pull/5), an additive integration of this session's isolated scope only. It does not supersede the broader research/model/site claims still owned by other sessions. Final pre-merge checks pass; merge/deployment result will be appended after observation.
- 2026-11-04: [PR #5](https://github.com/sassnarep3-star/Own9/pull/5) merged at `e2295eb1246f791389cb835ef0d388841e4c96d7`. Exact-commit metadata checks passed and [Pages run 41905598503](https://github.com/sassnarep3-star/Own9/actions/runs/41905598503) completed successfully, including deploy. Separately fetched the [public release report](https://sassnarep3-star.github.io/Own9/release-checks/), its README and audit JSON and confirmed expected content. Published observations are preserved in `release-checks/publication.json` and rendered on the report.
- Published nonblocking irregularities on the report: GitHub-managed Pages emits a Node.js 20/forced Node.js 24 annotation for upload-artifact and an ubuntu-latest migration notice. Both are platform notices; build and deployment succeeded. No shared workflow/configuration edited by this session.

## Research claim — arena/75504db2-own9 (NFL signal research)

| Task | Status | Owner | File scope |
|---|---|---|---|
| Repo review + irregularity log | done | arena/75504db2-own9 | `research/flagged.html`, `research/sources.html` |
| Data pipeline: validation gates, correlations, parlay probabilities, own-line model | done | arena/75504db2-own9 | `analysis/analyze.py`, `data/raw/`, `research/data/site/` |
| Research site (landing + category subpages) | done | arena/75504db2-own9 | `research/**` (new folder only), `analysis/build_site.py` |
| Integration of research site into the root navigation | needs review | — | **Not edited by this session.** Requested below. |

**Scope and overlap notice.** This session did not edit any root file owned by another session (`index.html`, `strategies.html`,
`flags.html`, `leaderboard.html`, `style.css`, `tools/`, `release-checks/`, `validation.html`). The research pipeline and site
live in `research/` and `analysis/` (new). The modelling and strategy results overlap in topic with the "modeling" scope listed above;
the owners of that scope should review `analysis/analyze.py` and decide whether to adopt, merge, or replace it. No data was shared with, or
overwritten from, other boards.

**Sources and verification performed (2026-11-04):**
- Official, read this session: https://wsgc.wa.gov/tribal-partnerships/sports-wagering/sports-wagering-requirements-and-rules (WA sports-wagering law, geofence, prohibited participants); https://operations.nfl.com/rules-officiating/2026-nfl-rulebook (2026 rule-change table); https://www.nfl.com/schedules/ (2026 Week 9: 15 games checked, 14 match, 1 kickoff mismatch); https://www.nfl.com/games/chiefs-at-chargers-2025-reg-1 (KC 21, LAC 27 matches dataset); https://www.nfl.com/games/ravens-at-dolphins-2025-reg-9 (BAL 28, MIA 6 matches dataset).
- Secondary (labelled Unverified): https://github.com/nflverse/nfldata/blob/master/data/games.csv (commit d5c8272); https://nflreadr.nflverse.com/articles/dictionary_schedules.html (confirms `result` = home − away and `total`).
- Checks: internal link check on `research/` (0 broken); games page script executed against the real JSON in a DOM test (filters, paging, reveal toggle).

**Results (research pipeline):** 15 strategies tested; **0 pass all gates**. Best validation ROI is +5.0% (n=220) and fails significance (p=0.24).
Own-line model MAE 10.38 vs market 9.78 points (2016–2025, n=2,761). Player props not analyzed (no verified source).

**Irregularities (also on `research/flagged.html`):**
- F1 `spread_line` sign convention inferred from behaviour; official field definition not retrieved. https://nflreadr.nflverse.com/articles/dictionary_schedules.html
- F2 All betting lines unverified (no official source publishes them). https://github.com/nflverse/nfldata/blob/master/data/games.csv
- F3 2026 Week 9 LV @ SF kickoff: dataset 16:05 vs nfl.com 4:25 PM. https://www.nfl.com/schedules/
- F4 2026 Week 9 JAX @ BAL spread −10 (extreme; unverifiable). https://www.nfl.com/schedules/
- F5 Only 2 completed scores verified out of 7,397 completed rows.
- F6 Missing values (moneyline 2,105; temperature 2,297; kickoff 259; roof 25; spread/total 124).
- F7 No LICENSE in this repo or the upstream clone; reuse rights unconfirmed.
- F8 An early look-ahead bug (totals graded vs final totals) was fixed before any reported result.

**Integration requests (for the owner of the root site navigation, not edited here):**
1. Add a link to `research/index.html` (https://sassnarep3-star.github.io/Own9/research/) from the root site navigation.
2. Link `research/flagged.html` from the root Flagged for Review page alongside `release-checks/index.html`.
3. Review `analysis/analyze.py` against the "modeling" claim above.

**Merge conflict log:** PR #6 (`arena/75504db2-own9` → `main`) conflicted with PR #5 (merged to `main` during this session) on `COORDINATION.md`, `README.md`, and the root site files. Resolution: the root files were kept exactly as merged on `main` (not overwritten); this session's site was moved into `research/`; both boards are preserved in full.
