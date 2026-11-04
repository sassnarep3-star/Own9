# COORDINATION.md — shared task board

Status values: `unclaimed` | `in progress` | `done` | `needs review`
(`needs review` items are published on the Flagged for Review page and do not block anything.)

## Session log
- 2026-11-04 · session `arena/75504db2-own9` · only active session on this repo at start. Repo contained only `README.md`; no COORDINATION.md existed, so it was created here.
- 2026-11-04 · T1/T2 claimed and pushed (commit f1a7b76) before any analysis work.
- 2026-11-04 · Analysis pipeline + site pushed (commit 8c5f047). Found and fixed one look-ahead bug in the totals rules before any result was published (recorded as F8).
- 2026-11-04 · No other session claimed or edited any file. No merge conflicts occurred.

## Task board

| ID | Task | Status | Owner (session) | Branch | Files touched |
|----|------|--------|-----------------|--------|---------------|
| T1 | Repo review + irregularity log | done | arena/75504db2-own9 | arena/75504db2-own9 | `COORDINATION.md`, `flagged.html`, `sources.html` |
| T2 | Data pipeline, validation gates, correlations, own-line model | done | arena/75504db2-own9 | arena/75504db2-own9 | `analysis/analyze.py`, `data/raw/`, `data/site/` |
| T3 | Static GitHub Pages site (landing + category subpages) | done | arena/75504db2-own9 | arena/75504db2-own9 | repo root site files (`*.html`, `assets/`, `data/site/`), `analysis/build_site.py`, `README.md` |
| T4 | Integration: rebuild data, link check, publish, PR, merge | in progress (PR #6: https://github.com/sassnarep3-star/Own9/pull/6) | arena/75504db2-own9 | arena/75504db2-own9 → main | all |

## Task records

### T1 — Repo review
- Repo state: `README.md` (title only), no LICENSE, no code, no CI, no existing Pages content. Pages was already enabled on `main` at `/`. The site is therefore published from the repo root (the API returned 403 when trying to change the source folder).
- Sources: https://github.com/sassnarep3-star/Own9 (repo); https://github.com/nflverse/nfldata (upstream clone, commit d5c8272).
- Verification performed: `git status`/`git log` (single commit 4828ac0), `gh api repos/sassnarep3-star/Own9/pages`.
- Irregularities: see the Flagged list below (F7 license/README).

### T2 — Data pipeline
- Source: https://github.com/nflverse/nfldata/blob/master/data/games.csv (secondary). Field definitions: https://nflreadr.nflverse.com/articles/dictionary_schedules.html (partial).
- Verification performed:
  - `result` = home − away and `total` = sum, confirmed against the dictionary text.
  - Spread sign convention determined from data (corr 0.44, mean(margin−spread) ≈ 0.10 for 2016–25). The official `spread_line` field definition was **not** retrieved → F1.
  - Two completed scores matched on nfl.com: https://www.nfl.com/games/chiefs-at-chargers-2025-reg-1 (KC 21, LAC 27) and https://www.nfl.com/games/ravens-at-dolphins-2025-reg-9 (BAL 28, MIA 6).
- Results: 15 strategies, 0 pass all gates. Own model MAE 10.38 vs market 9.78 (2016–25, n=2,761).
- Irregularities: F1, F2, F4, F5, F6, F8.

### T3 — Site
- Built by `analysis/build_site.py` from `data/site/*.json` plus source facts. Pages: index, summary, games, strategies, correlations, own-lines, props, rules, sources, flagged.
- Internal link check: 0 broken local links (checked by script before merge).
- Secondary values are labelled Unverified; the Games page hides them by default.

### T4 — Integration (pending)
- Steps: re-run pipeline, link check, merge to main, confirm Pages build on main `/`, confirm the live site, record PR + merge result below.

## Flagged for review (published on flagged.html)
| ID | Severity | Item | Source links |
|----|----------|------|--------------|
| F1 | High | `spread_line` sign convention not confirmed from the official field definition (behaviour indicates positive = home favored). | https://nflreadr.nflverse.com/articles/dictionary_schedules.html · https://github.com/nflverse/nflreadr/blob/main/vignettes/dictionary_schedules.Rmd |
| F2 | High | All betting lines (spread, total, moneyline) unverified: no official source publishes them. | https://github.com/nflverse/nfldata/blob/master/data/games.csv |
| F3 | High | 2026 Week 9 LV @ SF kickoff: dataset 16:05, nfl.com 4:25 PM. | https://www.nfl.com/schedules/ |
| F4 | Medium | 2026 Week 9 JAX @ BAL spread −10.0 (BAL home): extreme, unverifiable; model disagrees by +10.9 pts. | https://www.nfl.com/schedules/ |
| F5 | Medium | Only 2 completed scores checked against nfl.com out of 7,397. | https://www.nfl.com/games/chiefs-at-chargers-2025-reg-1 · https://www.nfl.com/games/ravens-at-dolphins-2025-reg-9 |
| F6 | Medium | Missing values: moneyline 2,105 rows; temp 2,297; kickoff 259; roof 25; spread/total 124. | https://github.com/nflverse/nfldata/blob/master/data/games.csv |
| F7 | Low | No LICENSE in repo or upstream clone; README is title-only; data reuse rights unconfirmed. | https://github.com/sassnarep3-star/Own9 · https://github.com/nflverse/nfldata |
| F8 | Low | Look-ahead bug in an early draft (totals graded vs final totals) — fixed; reported results use the corrected run. | (internal) analysis/analyze.py |
| F9 | Info | No verified source for historical player-prop prices; props not analyzed. | https://www.nfl.com/schedules/ |
| F10 | Info | 2026 Week 18 rows dated 2027 (season-year convention). | https://nflreadr.nflverse.com/articles/dictionary_schedules.html |

## Handoff notes
- None. All work done by this session; no claims were left stale.

## Integration record (T4)
- PR: https://github.com/sassnarep3-star/Own9/pull/6 (`arena/75504db2-own9` → `main`). Summary, sources, and flagged irregularities are in the PR body.
- Verification before merge: pipeline re-run; 0 broken local links; games page tested against the real JSON; 17 nfl.com game URLs confirmed (2 scores + 15 Week 9 games).
- Merge: see the record below (filled in after merge).
