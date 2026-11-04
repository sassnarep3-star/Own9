# COORDINATION.md — Shared Task Board

Last updated: 2026-11-04 (UTC) by session `arena-a1898555`

This file is the single source of truth for who is doing what. Every session must read it
before starting work, claim its task here, and record results when finished.

## Rules in force

1. Read this file before touching any file in the repo.
2. Claim a task by adding your session ID + file scope below, then commit and push the claim
   (`git pull --rebase && git push`) **before** starting work.
3. Never start a task another session has claimed and not released.
4. Keep file scopes non-overlapping. If you need a change in another session's scope, log a
   request in the *Scope requests* section instead of editing the file.
5. Small, frequent commits. `git pull --rebase` before every push.
6. On merge conflict: stop, resolve without discarding other sessions' work, log it here.
7. A task is only `done` when its sources are linked, the verification performed is recorded,
   and any irregularities are listed here.
8. Shared outputs (`outputs/*.json`, `site/index.html`, site navigation) are written **only** by
   the final integration session, after all other tasks are `done` or `needs review`.
9. If a session crashes or its claim is older than 60 minutes with no commits, any session may
   take over and must note the handoff here.
10. `needs review` = published on the site's *Flagged for Review* page; it does not block anything.

### Branch convention

The task brief asks for one branch per session (`session-<id>/<task>`). In this environment the
Arena session is pinned to a single working branch, so **all work is done on
`arena/a1898555-own9`** and no other branch is created, switched to, or pushed. This deviation is
recorded here so other sessions know that `arena/a1898555-own9` == session `arena-a1898555`.
Pull request to `main` is opened from this branch at integration time (see Task T12).

## Sessions

| Session ID | Branch | Role | Started (UTC) | Status |
|---|---|---|---|---|
| `arena-a1898555` | `arena/a1898555-own9` | Owner: all tasks (analysis, site, integration, PR) | 2026-11-04 20:10 | active |

## Task board

Status values: `unclaimed` · `in progress` · `done` · `needs review` · `blocked`

| ID | Task | Status | Owner | File scope |
|---|---|---|---|---|
| T01 | Coordination board + repo scaffold | done | arena-a1898555 | `COORDINATION.md`, `README.md`, `.gitignore`, `requirements.txt` |
| T02 | Data acquisition with pinned commit + SHA256 manifest | in progress | arena-a1898555 | `pipeline/00_fetch_data.py`, `data/manifest.json` |
| T03 | Data audit + internal consistency checks | in progress | arena-a1898555 | `pipeline/01_audit.py`, `outputs/data_audit.json` |
| T04 | Official-source cross-verification (NFL.com) | in progress | arena-a1898555 | `pipeline/02_verify_official.py`, `data/verification/*`, `docs/VERIFICATION_LOG.md` |
| T05 | Line origination engine (own spread/total/ML lines) | in progress | arena-a1898555 | `pipeline/10_line_engine.py`, `outputs/own_lines.csv` |
| T06 | Strategy library: single bets | in progress | arena-a1898555 | `pipeline/20_strategies_single.py`, `outputs/single_bets.json` |
| T07 | Strategy library: parlays (cross-game + same-game) | in progress | arena-a1898555 | `pipeline/21_strategies_parlay.py`, `outputs/parlays.json` |
| T08 | Strategy library: player props + prop combos | in progress | arena-a1898555 | `pipeline/22_strategies_props.py`, `outputs/props.json` |
| T09 | Validation gates, luck removal, multiple-testing control | in progress | arena-a1898555 | `pipeline/30_gates.py`, `outputs/gates.json` |
| T10 | Correlation analysis | in progress | arena-a1898555 | `pipeline/31_correlation.py`, `outputs/correlation.json` |
| T11 | Leaderboard scoring + reward allocation | in progress | arena-a1898555 | `pipeline/40_leaderboard.py`, `outputs/leaderboard.json` |
| T12 | Executive summary + methodology docs | in progress | arena-a1898555 | `docs/EXECUTIVE_SUMMARY.md`, `docs/METHODOLOGY.md` |
| T13 | Static site build (all pages + nav + tables) | in progress | arena-a1898555 | `pipeline/50_build_site.py`, `site/**` |
| T14 | Integration: merge check, link check, Pages deploy, PR + merge | in progress | arena-a1898555 | `.github/workflows/pages.yml`, `site/**`, this file |

## Scope requests

_None yet._

## Session log

### 2026-11-04 20:10 UTC — arena-a1898555 — claim

Claimed T01–T14. No other sessions active at claim time (repo contained only a 6-byte `README.md`,
single commit `4828ac0`, no `COORDINATION.md`). Because there are no competing sessions, scopes are
declared in full-file granularity above; each pipeline stage writes only its own `outputs/*` file so
a future session can take over a single stage without touching the others.

Environment constraint recorded up front (affects every task): the sandbox has outbound network
access only to `github.com`, `codeload.github.com`, `api.github.com`, `registry.npmjs.org`,
`pypi.org`, `files.pythonhosted.org`. Direct `curl` to `nfl.com` or to any sportsbook is blocked;
official-page verification is therefore performed through the browsing tool and transcribed with
its URL (see `docs/VERIFICATION_LOG.md`).
