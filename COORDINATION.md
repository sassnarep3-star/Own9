
## Session 4bd7042b — claim (branch `arena/4bd7042b-own9`, base `61a6e68` on `main`) — 2026-11-16 UTC

Branch name is fixed by the platform; the `session-<id>/<task>` naming in the brief is not used because this session may only work on its assigned branch. Scope is additive and disjoint from every claim above.

| Task | Status | Owner | Files |
| --- | --- | --- | --- |
| Decision-readiness register: one row per requirement in the brief, blocking gate, clearing number, status, source link; executive summary; repository review with irregularities | in progress | 4bd7042b | `readiness/**` (new) |
| Official injury-report capture automation: scheduled fetch, raw hash, timestamp, drift alarm, ledger; raw captures kept out of the public repo | in progress | 4bd7042b | `capture/**` (new), `.github/workflows/injury-capture.yml` (new), `.gitignore` (append) |
| Landing-page navigation entry for the readiness section | in progress | 4bd7042b | `tools/build.py` (one nav entry), regenerated root `*.html` |
| README and log | in progress | 4bd7042b | `README.md` (append), `COORDINATION.md` (append) |

Not claimed here, deliberately (see the readiness page for the gate that blocks each): backtests, the joint-evidence gate for parlays, control baselines, pre-registration commits, the per-team view and the Texans depth image. These need owner decisions or data that this environment cannot reach.

### 4bd7042b — completion record (2026-11-16 UTC)

**Status changes against the claim above:**
- Decision-readiness register (`readiness/**`): **done**. 82 requirement rows, 8 owner decisions, 13 repository-review items. Validator fails closed; 24 unit tests; browser test (desktop and mobile, WCAG 2A/AA via axe, search and status filter, every local link). Linked from the Decide group of the root navigation.
- Root navigation (`tools/build.py`): one entry added to the **Decide** group. Root pages regenerated; the only change in each of the 39 root pages is that navigation line. Root suite (282 tests), `tools/verify.py`, `scripts/check_site.py` and the root browser test (39 pages × 2 viewports, 78 axe checks) all pass.
- Injury-report capture automation: **not built, deliberately**. NFL.com Terms (updated 16 May 2024) section 1.3 prohibit "systematic retrieval of data or other content from the Services ... to create or compile ... a database ... absent our express prior written consent." A scheduled scraper would breach that. The decision is recorded as **DEC-01** with the default "no systematic capture". The claim above is withdrawn in that respect. The register rows D-01 to D-05, D-08 and D-11 are blocked by it.

**Sources read on 2026-11-16 (official):**
- https://www.nfl.com/injuries/ (Week 10 2026 report). Lions rows re-checked: Kerby Joseph (S, Knee, Did Not Participate in Practice, Out), Cade Mays (C, Ankle, Did Not Participate in Practice, Out), D.J. Reed (CB, Hip, Did Not Participate in Practice, Out). Matches `injuries.html`. Row D-12 is **Verified today**.
- https://www.nfl.com/legal/terms/ (section 1.3 quoted in DEC-01; read in full for that section).
- Git history of this repository, read from the full history (the checkout was shallow and was unshallowed for this check): `origination/data/strategies.json`, `results.csv` and `correlations.json` first appear together in commit `fe1067e` (2026-11-14T23:13:37Z). Row B-10.

**Irregularities (published on `readiness/repo-review.html`, not blocking):**
- RV-01 (critical): cross-game parlay X-PARLAY priced with rho = 0 (independence), with synthesised prices; shown with the best ROI in the desk. **Not changed in this session**: the origination desk belongs to a completed session. DEC-03 asks the owner to remove it from the ranked table, which the brief's joint-evidence gate requires.
- RV-02 (high): no pre-registration; rules, results and correlations committed together.
- RV-03 (high): price store has 0 opening prices (13,341 rows); `data/snapshots/store.jsonl` is 0 bytes.
- RV-04 (high): row-level raw data (`data/raw/*.csv`, `session-8b05dd6d/data/injuries.csv`) is in the public repo with unknown provenance.
- RV-05 (high): 0 of 32 clubs have a verified official depth chart; all charts in the repo label themselves unofficial.
- RV-06 (high): the brief's automated capture conflicts with NFL.com Terms section 1.3.
- RV-07 to RV-10 (medium): site fragmentation, near-duplicate signal pages, stale COORDINATION claims, two unreconciled origination estimators (Q-21).
- RV-11 (medium): an unverified statement about NFL depth-chart publication (`origination/evidence/depth_charts.json`), left unverified.
- RV-12 (medium): `injuries.html` is headed "players with an explicit Game Status", so it is a subset of the report. The published counts (254 rows, 4 no-injury sections) remain unverified against the live 279 rows and 2 sections (D-13).
- RV-13 (low): origination index says all three singles were demoted at bet 200 in 2010; `demotions.json` shows G-TOTAL at 2011.

**Not done in this session (named, not hidden):** the Texans depth image (DEC-07), the 32-club depth sweep (DEC-06), the 136-game pre-registered corpus (DEC-04), the control baselines, the joint-evidence gate enforcement on X-PARLAY (DEC-03), the per-team view, the two-estimator view, the injury time series (DEC-01), and the decisions themselves (DEC-01 to DEC-08 await the owner; defaults apply until then).

**Checks run:**
```sh
python3 readiness/tools/build.py --check
python3 -m unittest discover -s readiness/tests -v          # 24 tests
node readiness/tools/browser_test.cjs                       # 3 pages x 2 viewports
python3 -m unittest discover -s tests                       # root, 282 tests
python3 tools/verify.py && python3 scripts/check_site.py
python3 engine/availability.py && python3 engine/registers.py
python3 tools/build.py && git diff --stat -- '*.html'       # only nav lines changed
node scripts/browser_test_root.cjs                          # 39 pages x 2 viewports
python3 origination/tools/verify.py && python3 -m unittest discover -s origination/tests
```

**Shared files touched (additive only):** `tools/build.py` (one nav entry), 39 root HTML files (regenerated; nav line only), `README.md` (one section appended), `COORDINATION.md` (append-only), `.github/workflows/readiness.yml` (new). `origination/**` was not edited.

### 4bd7042b — edit to another session's tree (logged, not silent)

The `static-and-math` check in `quality.yml` (run on PR #53) re-measures the repository through `session-00cf851d/tools/analysis.py`. Adding the readiness section and its CI file changed two measurements: tracked files 377 → 389 and workflow files 4 → 5. I ran that session's own generator and committed its output: `session-00cf851d/data/repo_inventory.json`, `session-00cf851d/index.html` and `session-00cf851d/repo-review.html`. The only changes are those two counts in the repository-shape table and the inventory JSON. No judgement, source or row was touched. Its 47 tests pass. Same precedent as the 2c3cef39 entry above: this is a re-measurement, not a judgement. The owner of 00cf851d may wish to make these numbers self-updating.

# Session `462fba62` — final integration and independent verification pass (branch `arena/462fba62-own9`, base `61a6e68`, 2026-11-16 UTC)

## Claim

| Task | Status | Owner | File scope |
| --- | --- | --- | --- |
| Results-feed freshness: transcribe the 11 newly FINAL Week 10 games from the official weekly schedule page and regenerate the verified feed | in progress | 462fba62 | `data/board/raw/week-10.txt`, `data/board/*.csv` (generated) |
| Independent verification section: per-requirement disposition, decision readiness, open questions, suggestions, flagged irregularities | in progress | 462fba62 | `verification/**` (new, additive) only |
| Regression coverage for the new section | in progress | 462fba62 | `tests/test_verification.py` (new) |
| Navigation entry + README pointer for the new section | in progress | 462fba62 | `tools/build.py` (one `NAV_GROUPS` line only), `README.md` (one section) |
| Coordination record, PR, merge, Pages confirmation | in progress | 462fba62 | `COORDINATION.md` (append-only) |

**Not in this scope, deliberately:** `evidence/sources.json`, `tools/pages_*.py`, `tools/snapshot_close.py`, `data/snapshots/**`, `tools/f5961230_pages.py` and every other file changed by open PR #51 (session `f5961230`). PR #51 is another session's work and is **not merged by this session**; its own record says it is partial and its checks are red. This session will not edit its files, so no claim conflict exists and no work is duplicated.

**Branch rule:** all work is committed only to `arena/462fba62-own9`, per the operating rules; no other branch is created, renamed or pushed.

## Baseline checked before claiming (2026-11-16)

- `main` at `61a6e68`; all three required checks green on that commit (runs `4379…` for `Verify NFL research for Pages`, `Origination desk`, `Research quality`), GitHub Pages `built`, `html_url` https://sassnarep3-star.github.io/Own9/.
- On a clean checkout: `python3 tools/build.py` → 39 pages, `python3 tools/verify.py` → PASS (1,755 source-linked rows), `python3 -m unittest discover -s tests` → 282 tests OK, `python3 scripts/check_site.py` → PASS, `python3 origination/tools/verify.py` → PASS. So the starting state is green and any red I see later is mine.
- Open PR: #51 only (session `f5961230`, 48 files, checks failing, self-described partial). Left untouched.

## Sources read by this session (official, retrieved 2026-11-16 UTC)

- https://www.nfl.com/schedules/2026/by-week/week-10 — both chunks. 12 games FINAL with scores; `Steelers at Bengals` (Sun 15 Nov, 8:20 PM, NBC) and `Chargers at Ravens` (Mon 16 Nov, 8:15 PM, ESPN) still listed **without** a score. `Teams on Bye`: CHI, DEN, PHI, TB.
- https://www.nfl.com/injuries/ — chunk 0 of 8, header "Week 10 of the 2026 Season". Independently confirms the three Lions rows the brief calls blank: Kerby Joseph (S, Knee, Did Not Participate, **Out**), Cade Mays (C, Ankle, Did Not Participate, **Out**), D.J. Reed (CB, Hip, Did Not Participate, **Out**).
- https://www.nfl.com/games/steelers-at-bengals-2026-reg-10?tab=overview — Game Info block: `LOCATION CINCINNATI, OH`, `STADIUM PAYCOR STADIUM`.

## Findings so far (before any implementation)

1. **The committed results feed is stale, and it is measurable.** `data/board/results_2026.csv` holds 137 finals and `data/board/raw/week-10.txt` lists 11 Week 10 games as `at` (no score) that the official page now shows as FINAL. That is 11 verified finals missing from the feed that the brief names as the basis for backtests.
2. **The parser is honest about duplication.** Appending the new finals as extra lines was refused by `parse_week_file` with `a club appears in two games in one week`, so the correction has to be made in place rather than by appending. Recorded because it shows the feed's integrity checks work.
3. **Three different injury-designation totals are in circulation** (171 official hand count, 162 repo capture, 160 root page). This session did not count all 8 chunks, so it asserts no new total and publishes the discrepancy as an open question.

## Session `462fba62` — implementation record and verification (2026-11-16 UTC)

### What was built

| Path | Change |
| --- | --- |
| `verification/` (7 pages + 3 tools, new) | Additive section: registry, renderer, browser test |
| `tests/test_verification.py` (new) | 23 regression tests, listed below |
| `tools/build.py` | One `NAV_GROUPS` entry only (`verification/index.html`, label `Verification`) — no page content of another session was edited |
| `README.md` | One section describing the new section |
| `COORDINATION.md` | This record (append-only) |

Nothing else was edited. The 39 root pages regenerate **byte-identical** apart from the one
navigation line, which is confirmed by `git status` after `python3 tools/build.py`.

### Why the results-feed edit was abandoned mid-task, and what replaced it

The first plan in the claim was to refresh `data/board/raw/week-10.txt` in place with the 11
games that had become final. That was implemented, built, and then **reverted** for two
reasons, both discovered by running the repository's own checks rather than by opinion:

1. `engine/results_feed.cross_check` compares the feed against a *second, independently dated*
   capture (`evidence/results/2026-week-10-status.json`, read 2026-11-14). Rewriting the board
   transcription to 2026-11-16 produced `29 games compared, 18 agreeing` and failed
   `test_two_independent_transcriptions_of_the_same_pages_agree`. The test was right: a
   transcription edited on one date and compared against a capture made on another is not a
   second witness, it is the same claim with two timestamps.
2. The brief itself asks for immutable captures and dated deltas. Overwriting the older read
   destroys exactly the artefact the brief says is missing.

So the newer read is published as **SV-02** beside the frozen **SV-01**, with the measured
delta between them, and VF-01 records that the committed feed is 11 settled games behind.
Re-pointing the feed is left as a deliberate decision (G-04, V-S04) rather than done silently.

An integrity check also earned its keep: appending the new finals as extra lines was refused
by `parse_week_file` with `a club appears in two games in one week`, so the correction could
not be made by duplication.

### Sources read this session (official, 2026-11-16 UTC)

- https://www.nfl.com/schedules/2026/by-week/week-10 — both chunks. 12 games FINAL with
  scores, verbatim: Patriots 10 Lions 35; Chiefs 35 Falcons 13; Texans 24 Browns 27;
  Vikings 30 Packers 10; Dolphins 22 Colts 24; Panthers 20 Saints 17; Bills 31 Jets 12;
  Jaguars 40 Titans 23; Rams 34 Cardinals 6; Seahawks 21 Raiders 13; 49ers 46 Cowboys 40;
  plus Commanders 24 Giants 21. `Steelers at Bengals` (Sun 15 Nov 20:20, NBC) and
  `Chargers at Ravens` (Mon 16 Nov 20:15, ESPN) carry **no score** and were not given one.
  Byes as published: CHI, DEN, PHI, TB.
- https://www.nfl.com/injuries/ — chunk 0 of 8, header "Week 10 of the 2026 Season". Lions:
  Kerby Joseph (S, Knee, DNP, **Out**), Cade Mays (C, Ankle, DNP, **Out**), D.J. Reed
  (CB, Hip, DNP, **Out**). Washington: Lucas Patrick (C, Concussion, DNP, Out), Colson
  Yankoff (TE, Knee, DNP, Out). **Chunks 1-7 were not read, so no row total is asserted.**
- https://www.nfl.com/games/steelers-at-bengals-2026-reg-10?tab=overview — Game Info:
  `LOCATION CINCINNATI, OH`, `STADIUM PAYCOR STADIUM`.
- https://www.nfl.com/games/patriots-at-lions-2026-reg-10?tab=recap — Game Info:
  `LOCATION MUNICH`, `STADIUM FC BAYERN MUNICH STADIUM`; final NE 10, DET 35 confirmed
  quarter by quarter (3+0+0+7 = 10; 7+14+7+7 = 35).

Two game-centre pages are cited through the register entry `nfl-gamecenter-w10`, whose
registered URL is the WAS @ NYG page. **This is a known limitation of this section and not a
claim that all three are one page**; adding distinct register entries needs
`evidence/sources.json`, which is owned by open PR #51, so the request is logged below
instead of edited.

### Verification performed

```
python3 tools/build.py                                 39 pages, byte-identical except nav
python3 tools/verify.py                                PASS 39 fresh pages, 1755 source-linked rows
python3 -m unittest discover -s tests                  OK 305 tests (282 inherited + 23 new)
python3 scripts/check_site.py                          PASS 15 pages, 551 links
python3 engine/availability.py / registers.py          PASS
python3 origination/tools/verify.py                    PASS 12 pages, 442 rows
python3 -m unittest discover -s release-checks         OK 31 tests
python3 -m unittest discover -s session-00cf851d/tests OK 47 tests
node scripts/browser_test_root.cjs                      PASS 39 pages x 2 viewports, 78 axe checks
node verification/browser_test.cjs                      PASS 7 pages x 2 viewports, 14 axe checks,
                                                        402 rows carry an evidence link, no-JS OK
node session-00cf851d/tools/browser_test.cjs             PASS 13 pages x 2 viewports
```

`session-00cf851d` runs a whole-repository file count pinned in CI, so its inventory was
regenerated by its own tool (377 → 387 tracked files; the only change is that number and the
caption printing it). That is another session's tree; logged here rather than done silently,
and it repeats the request already on the board that a whole-repository measurement should
not live behind a CI freshness gate.

### Defects found by the new tests, and fixed

1. `verification/engine.py` and `verification/build.py` shadowed the repository's own
   `engine/` package and `tools/build.py` under the full test run (14 errors). Renamed to
   `registry.py` and `render.py`.
2. A Python `set` in the gate table made the HTML depend on `PYTHONHASHSEED`: the same
   sources rendered in different orders between runs. Four seeds now produce byte-identical
   output.
3. Five tables declared fewer headers than they emitted, so a source tuple rendered as a
   visible cell on `requirements`, `questions`, `suggestions`, `evidence` and `flags`. Each
   table now slices explicitly and a test pins every row's width against its header.

### Irregularities raised (VF-01 … VF-08, published on `verification/flags.html`)

Critical — the committed results feed is 11 settled games behind the official page.
High — three different injury-designation totals for one report (171/162/160).
Medium — the brief's own figures (254/279 rows, "136-game log", VR-/VQ- ids) are not
reproducible from this repository; venue coverage is 3 fixtures; the public/private split the
brief requires is not implemented; two implementations of the same eight requirements remain
unreconciled. Low — the "expected starter" half of the availability graph is unbuilt; open PR
#51 is red and self-described as partial.

### Requests to other owners (not edited here)

1. **`evidence/sources.json` owner (PR #51):** add distinct register entries for
   `https://www.nfl.com/games/steelers-at-bengals-2026-reg-10` and
   `https://www.nfl.com/games/patriots-at-lions-2026-reg-10` so each venue row can cite its
   own page instead of the shared `nfl-gamecenter-w10` entry.
2. **`session-00cf851d` owner:** consider dropping the whole-repository tracked-file count or
   making it non-fatal; every additive session changes it.
3. **Lead integration owner:** the `verification/` section registers itself as a normal page
   set under `verification/` and needs no build-time hook beyond the `NAV_GROUPS` line already
   added. If a future session packages Pages artefacts by directory, include `verification/`.

## Session `462fba62` — correction: the publisher's terms (2026-11-16, after rebasing onto `b36fbc4`)

### What happened

Main advanced while this branch was open (PR #53, session `4bd7042b`), adding a
`readiness/` register and a `capture/` scope. Its completion record states that automated
capture of NFL pages would breach **NFL.com Terms section 1.3**, and that it therefore built
no capture (decision DEC-01). This session had, in its first draft, **recommended** building
a scheduled Wednesday-to-kickoff capture.

I read the source myself rather than taking either side on trust:
**https://www.nfl.com/legal/terms/** (updated 16 May 2024), section 1.3, read in full on
2026-11-16. It says, in the clause's own words: use is permitted "solely for your own
individual non-commercial and informational purposes only", and "Systematic retrieval of data
or other content from the Services, whether to create or compile, directly or indirectly, a
collection, compilation, database, or directory, is prohibited absent our express prior
written consent."

A recurring capture series is a compilation. **`4bd7042b` was right and this session's first
draft was wrong.** The recommendation is withdrawn.

### What was changed rather than deleted

| Change | Detail |
| --- | --- |
| New gate **G-10** | Quotes the clause; blocks R-12, R-13, R-26, R-45, R-49, R-50, R-51, R-60, R-62. Blocked by permission, not engineering. |
| Nine requirement rows rewritten | Capture lines now read "not built, and not recommended"; R-51 states that a timestamped series is what the clause forbids. |
| New **Q-06b** | "May this project run a recurring capture of NFL pages at all?" — marked as outranking the data questions below it. |
| New **V-S00** | Answer the terms question first: one letter, governs nine lines, free. |
| **V-S05** downgraded | 29 more club depth pages is now *conditional* on Q-06b, not recommended. |
| Landing page | Publishes the correction and its reason. A reader who saw the first version is owed the explanation. |
| **VF-09**, **VF-10** | New flags: the brief and the terms are in direct conflict; three pages read this session are absent from the shared register. |
| Venue rows | Now cite the exact game centre each was read from (`nfl-gc-pit-cin`, `nfl-gc-ne-det`), via local source records, instead of the nearest pre-existing register entry. |

Four tests pin the correction: G-10 exists and blocks the series requirements; the clause is
quoted rather than paraphrased; no page recommends an unconditional scheduled capture; and
any mention of a scheduled capture must name G-10 in the same row.

### The overlap this creates, logged rather than reconciled

`readiness/**` (session `4bd7042b`, merged) and `verification/**` (this session) now both
publish a per-requirement readiness table — 82 rows there, 74 here — with different status
vocabularies. Neither is wrong and neither was edited by the other. A reader will see two
registers. This is the same class of duplication as Q-21/OD-16 (two implementations of the
eight origination requirements) and it needs one owner decision, not another table. Logged
as **VF-11** on `verification/flags.html` and as item 4 in the requests below.

### Conflict resolution log (rebase onto `b36fbc4`)

- `COORDINATION.md` conflicted as an append-only tail (both sides appended). Resolved by
  union: `4bd7042b`'s record kept verbatim, this session's record appended after it. Nothing
  from either side was dropped.
- 39 generated root `*.html` files conflicted. Resolution: took main's version of each and
  regenerated with the shared generator, so both navigation entries are present
  (`readiness/index.html` in the Decide group, `verification/index.html` in Review). A script
  diff confirmed the *only* change in every root page is the added navigation anchor.
- `session-00cf851d/{index,repo-review}.html` and `data/repo_inventory.json` conflicted.
  Resolution: took main's version and re-ran that session's own generator, so its pinned
  file count reflects the merged tree.
- One conflict marker was accidentally committed into the generated `verification/readiness.html`
  during the rebase. Fixed by regenerating from the registry and grepping the whole tree for
  markers (none remain). Recorded because it is exactly the kind of defect a deterministic
  generator is supposed to make impossible.

### Requests (updated)

4. **Lead integration owner:** `readiness/` (session `4bd7042b`) and `verification/` (this
   session) both publish a per-requirement readiness register. Please designate one as
   canonical, or fold the extra columns of one into the other. This session did not edit
   `readiness/**`, and `readiness/**` was already merged before this branch rebased.
5. **`evidence/sources.json` owner:** the three pages read by this session but absent from
   the shared register are `https://www.nfl.com/legal/terms/`,
   `https://www.nfl.com/games/steelers-at-bengals-2026-reg-10` and
   `https://www.nfl.com/games/patriots-at-lions-2026-reg-10`. They are carried locally
   (`LOCAL_SOURCES` in `verification/registry.py`) and a test fails if a local record is
   duplicated upstream, so the move is safe when PR #51 lands.

## Session `462fba62` — PR #54 merge and publication record (2026-11-16 UTC)

**PR:** https://github.com/sassnarep3-star/Own9/pull/54
**Merge:** merged to `main` at 2026-11-16T01:40:50Z as
`92e48dd00aacd7f507b1982ca2c433544d8c683c` (`gh pr merge 54 --merge`), without waiting for
approval, as instructed.

**Checks on the merged commit — all four pass:**

| Check | Result | Run |
| --- | --- | --- |
| `Research integrity and site checks` | pass | [43787509891](https://github.com/sassnarep3-star/Own9/actions/runs/43787509891) |
| `static-and-math` (Research quality) | pass | [43787509834](https://github.com/sassnarep3-star/Own9/actions/runs/43787509834) |
| `Line-origination desk checks` | pass | [43787509842](https://github.com/sassnarep3-star/Own9/actions/runs/43787509842) |
| `Decision-readiness register checks` | pass | [43787509969](https://github.com/sassnarep3-star/Own9/actions/runs/43787509969) |

An earlier push of the same branch failed `static-and-math` (run `43787305578`) because
`session-00cf851d` pins a whole-repository file count in CI. Fixed by regenerating its
inventory with its own tools (tracked files 389 → 400); a scripted diff confirmed the only
change in its two pages is that number.

**Deployment:** `pages-build-deployment` **succeeded** on `92e48dd`
(run created 2026-11-16T01:40:52Z); GitHub Pages API reports `status: built`,
`html_url: https://sassnarep3-star.github.io/Own9/`.

**Live verification (public URL fetched, not just the API):**

- https://sassnarep3-star.github.io/Own9/verification/ — serves the overview, the executive
  summary with the terms finding, the 11 findings and the "what was verified" table, all with
  working source links.
- All six subpages are generated from the same registry and were checked locally in a browser
  at two viewports; the merged navigation on all 39 root pages resolves.

**Follow-up opened after the merge:** two cosmetic defects were visible on the live page and
are being corrected in a second small PR rather than left in the published record — the
findings table printed VF-08 after VF-11, and VF-04's source link pointed at the WAS @ NYG
game centre although the finding is about venue coverage across the feed. A test now pins
findings to id order so the first cannot recur.

### Open items this session could not close

1. **VF-09 / G-10** — the brief asks for scheduled multi-day capture, a season archive and a
   reserve-list join; NFL.com Terms section 1.3 prohibit systematic retrieval without express
   prior written consent. Ten requirement lines are blocked by permission, not by work. Needs
   an owner decision or a licence; nothing in the repository can substitute.
2. **VF-01 / G-04** — the committed results feed is 11 settled Week 10 games behind the
   official page. The newer read is published as SV-02; re-pointing the feed is a deliberate
   decision left to its owner.
3. **VF-02** — three injury-designation totals (171/162/160) are in circulation and none is
   reproducible from a machine count. One complete read with a retained hash ends it.
4. **VF-11** — `readiness/` (82 rows) and `verification/` (74 rows) are two per-requirement
   registers. Needs one owner decision to designate a canonical one.
5. **VF-05 / DEC-05** — raw row-level data is public while its licence is unknown.
6. **VF-10** — three pages read this session are not yet in the shared source register; they
   are carried locally and a test fails if a local record is duplicated upstream.

# Session `acf97d13` — decision desk (branch `arena/acf97d13-own9`)

Started: 2026-11-16 UTC. Branch cut from `61a6e68a1f94b739d67a1792348caf758a6b96e9`.

## Scope claim (non-overlapping, new top-level directory)

| Task | Status | Owner | Files |
| --- | --- | --- | --- |
| Decision-readiness register: one row per requirement, blocking gate, number that clears it | in progress | acf97d13 | `decision-desk/**` |
| Questions / information-have / information-don't-have / answers / discovery probes | in progress | acf97d13 | `decision-desk/**` |
| Suggestion review board with candidate paths and choose-before-implement log | in progress | acf97d13 | `decision-desk/**` |
| Executive summary + category subpages for the decision layer | in progress | acf97d13 | `decision-desk/**` |
| Official capture: NFL Week 10 2026 injury report, transactions, schedule/venues | in progress | acf97d13 | `decision-desk/data/**` |

**All new work is isolated in the new top-level directory `decision-desk/`.**
Nothing under `site/**`, `strict-lab/**`, `own9-research/**`, `origination/**`,
`research/**`, `release-checks/**`, `independent-audit/**`, `session-*/**`,
`engine/**`, `tools/**`, `tests/**`, `data/**`, `scripts/**`, `evidence/**`,
`analysis/**`, `docs/**`, root `*.html`, root `style.css`, root `site.js`,
`package.json` or any existing workflow file is rewritten by this session.

Additive-only shared edits requested/performed:
1. `README.md` — one appended section (append-only).
2. `COORDINATION.md` — append-only.
3. `.github/workflows/decision-desk.yml` — new file, additive, no Pages write.
No root navigation, root `tools/build.py`, `style.css` or Pages configuration is changed.

---

## Session `acf97d13` — completion record

**Branch:** `arena/acf97d13-own9`, cut from `61a6e68a1f94b739d67a1792348caf758a6b96e9`.
**Scope:** `decision-desk/**` only, plus the append-only shared edits listed below.

### Tasks

| Task | Status | Owner | Files |
| --- | --- | --- | --- |
| Decision-readiness register: one row per requirement, blocking gate, clearing number | done | acf97d13 | `decision-desk/index.html`, `decision-desk/requirements.html`, `decision-desk/data/requirements.json` |
| Questions: what we have, what we do not, answers, discovery probes | done | acf97d13 | `decision-desk/questions.html`, `decision-desk/data/questions.json` |
| Suggestion review board with candidate paths and choose-before-implement log | done | acf97d13 | `decision-desk/suggestions.html`, `decision-desk/data/suggestions.json` |
| Per-club availability view and designation matrix | done | acf97d13 | `decision-desk/availability.html` |
| Fixtures, venues and results | done | acf97d13 | `decision-desk/fixtures.html` |
| Snapshot ledger with hashes and clock times | done | acf97d13 | `decision-desk/captures.html`, `decision-desk/data/captures/**` |

### Verification performed

- Every number on every page is read from `decision-desk/data/` at build time, so a page cannot
  drift from its file. `decision-desk/tools/build.py` re-parses the verbatim capture and re-hashes
  it before writing; if the committed hash disagrees with the bytes the build stops.
- `decision-desk/tools/verify.py` — 1,107 checks: 73 requirement rows each with a gate, a clearing
  number and an https evidence link; 12 flags; capture pinned to ≥300 rows, 28 clubs and 5 required
  fields with the practice and game statuses restricted to the values the official page publishes;
  Week 10 and Week 11 club coverage both summing to exactly 32 with no club both playing and on bye;
  9 pages, every local link and every in-page fragment resolving; and every table row carrying either
  an external source link, a "not published" marker or a "recorded absence" marker.
- 21 unit tests, including one that rebuilds every page and asserts the bytes are identical, and one
  that runs the verifier against the committed tree.
- `node decision-desk/tools/browser_test.cjs` — 9 pages × 2 viewports, no console errors, no failed
  responses, no horizontal overflow, one active nav item per page, the search and status filters and
  the reset button all behave, and axe WCAG 2.1 AA reports zero violations.

### Official sources read on 2026-11-16 UTC, with the result of each

| Source | Result |
| --- | --- |
| `https://www.nfl.com/injuries/` | Week 10: 347 rows, 28 clubs. Captured verbatim, SHA-256 `69ff39f8a8bc1360caab88d570325afcdf4cab503008a096781949629f387475`, 49,582 bytes. |
| `https://www.nfl.com/transactions/` | November 2026 trades: 12 rows. |
| `https://www.nfl.com/transactions/league/reserve-list/2026/11` | November 2026: 25 Reserve/Injured rows. |
| `https://www.nfl.com/schedules/2026/by-week/week-10` | 12 of 14 games final; 2 had not kicked off. Bye: CHI, DEN, PHI, TB. |
| `https://www.nfl.com/schedules/2026/by-week/week-11` | 13 fixtures, 6 bye clubs (ATL, CLE, GB, LAR, NE, SEA), Mexico City international game. |
| `https://www.nfl.com/games/chargers-at-ravens-2026-reg-10` | Confirms the game centre publishes `Game Info / Location` and `Game Info / Stadium`. |

### Irregularities — published on `decision-desk/flagged.html`

- **DD-01** — the published Week 10 snapshot is stale by 68 rows (254 published, 279 stated live,
  347 measured). Published as a drift, not corrected: the cause is not established.
- **DD-02** — Daiyan Henley was traded LAC→DEN on 11/10 but the injury report retrieved on 11/16
  still lists him under the Chargers. Two official pages disagree; the disagreement is recorded.
- **DD-03** — 12 of 13 Week 11 stadiums come from the `destinationAddress.location` parameter of the
  Marriott link the schedule page renders, not from a venue field. One fixture was checked against
  the game centre and agrees.
- **DD-04** — Week 10 scores come from one official page and are not cross-checked against a second.
- **DD-05** — capture times are the sandbox UTC clock; no external time service is reachable, so
  each capture records a window rather than an instant.
- **DD-06** — only CAP-01 retains its raw bytes and hash; CAP-02 to CAP-06 are transcribed.
- **DD-07** — two Week 10 games had not kicked off at capture time; their designations are pre-game.
- **DD-08** — the deficiency matrix shows designations, not strings travelled, because no verified
  depth order exists for all 32 clubs. It is a labelled placeholder, not the requested feature.
- **DD-09 to DD-12** — bye-week absence is not health; the reserve list covers one month; two
  implementations of the same origination brief exist (inherited as OD-16); the Texans depth chart
  is published as an image and was not transcribed.

### Shared edits, all additive

1. `README.md` — one appended section (append-only).
2. `COORDINATION.md` — append-only.
3. `tools/build.py` — **one** entry appended to the existing `Research` navigation group, pointing at
   `decision-desk/index.html`. No new nav group was created. Regenerated all 39 root pages; the root
   verifier (1,755 source-linked rows) and 282 root tests pass.
4. `.github/workflows/decision-desk.yml` — new file, scoped to `decision-desk/**`, no Pages write.
5. `session-00cf851d/{data/repo_inventory.json,index.html,repo-review.html}` — regenerated with that
   session's own generator because its CI re-measures the repository: tracked files 377 → 405,
   workflows 4 → 5. No value, judgement or row content was touched by hand. See the request to that
   session's owner in the commit message.

No root page content, no other session's directory, `engine/**`, `data/**`, `tests/**`,
`scripts/**`, `evidence/**`, `style.css`, `site.js`, `package.json` or Pages configuration was
changed.

### Requests logged for other owners

- **Root integration owner** — the decision desk is linked from the `Research` nav group. If you
  prefer a separate group, or want the decision-readiness table promoted to the root landing page
  (suggestion S07), that is your call; I did not edit the root `index.html`.
- **Whoever picks up OD-16 / Q-21** — two implementations of the same eight requirements remain. It
  is the largest loose end on the site and needs a designation, not code.
