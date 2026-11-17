# Availability/personnel ablation protocol

**Purpose:** estimate whether verified, pre-kickoff availability information improves forecasts, rather than subtracting a fixed number of points for an absent starter. This is a preregistered comparison of two otherwise identical models—not an injury adjustment rule.

**Current result:** not computed. No committed corpus of paired, pre-kickoff, source-hashed availability forecasts passes the contract below. The empty result is intentional; the utility does not fill missing rows or infer a depth tier. This protocol does not retroactively pre-register the other candidates listed elsewhere in the repository; each strategy still needs its own commit-frozen definition before its evaluation window. The project must not run repeated NFL-page capture without a permitted/licensed route: the existing decision record quotes [NFL.com Terms, section 1.3](https://www.nfl.com/legal/terms/) and records recurring capture as blocked pending permission. No capture was added here.

## Comparison

For one frozen target and model family, generate two forecasts for every same held-out fixture:

1. **Without verified availability:** use the frozen baseline features.
2. **With verified availability:** use the same model family, training window, target, market/settlement rule and chronological holdout, adding only the preregistered availability/personnel feature set.

Both variants are recorded as a complete three-state probability vector: `win`, `push`, and `loss`. A push is an outcome, not a win/loss silently dropped. The row also records the fixture/target, held-out season week, training cutoff, availability snapshot time, forecast time, kickoff, source URLs, snapshot hashes, model-spec hashes, registration commit, and an input-artifact locator. Raw row-level artifacts belong in an access-controlled store; the public site should contain only derived analysis. The evaluator hashes the frozen policy and paired forecast corpus so the reported aggregate can be traced to its exact inputs. A hash or locator does not prove that an artifact exists, is immutable, or has correct contents; independent review is still required.

The availability route must be established from official, dated evidence. The [NFL injury report](https://www.nfl.com/injuries/) documents the designation source; official [NFL Game Books](https://static.www.nfl.com/image/upload/v1794570519/gamecenter/ab5828d9-4feb-11f1-abca-2c54536568a9.pdf) document game-day lineups, inactives and statistics for that fixture. A designation alone is not proof of playing time. Replacement depth must not be inferred from jersey order or an unofficial chart. A playing-time feature requires an official participation/snap source, and every feature snapshot must be available before the forecast was recorded and before kickoff.

## Score and uncertainty

For outcome class \(y\) and three-class probabilities \(p_k\), the utility uses the categorical Brier score

\[
B = \sum_{k \in \{win,push,loss\}} (p_k - 1[k=y])^2.
\]

For each paired fixture it computes `Brier_without_availability − Brier_with_availability`. Positive values favor the availability-feature model. The published point difference is the mean paired difference; its interval resamples whole held-out weeks, preserving within-week clustering. The confidence level is Bonferroni-adjusted from the preregistered familywise alpha and number of registered comparisons.

The week-cluster percentile interval assumes exchangeable held-out weeks. It is not a causal estimate and does not establish that injury information caused a forecast improvement. Temporal drift or dependence across weeks needs a preregistered sensitivity analysis. This ablation interval does not replace the separately required game-cluster lower bound for leaderboard ranking. The utility always returns `eligible_for_leaderboard: false`; benchmark-relative skill, independent source verification, prospective replication, staking/ROI, and the rest of the leaderboard gates are outside this calculation.

## Fail-closed admission contract

`engine/ablation.py::evaluate_availability_ablation(rows, policy)` refuses an estimate unless all of these are supplied and consistent:

- a frozen registration ID, full commit hash and registration time that predates each forecast;
- the target, shared model-spec hash, distinct without/with feature-set hashes, family size, familywise alpha, minimum held-out-week gate, bootstrap count and seed;
- a chronological `train_through_week < heldout_week` for every row, with nondecreasing training weeks and cutoff timestamps, matching kickoff-time order across holdout weeks, and one shared training cutoff and training-data digest for every fixture in each held-out week;
- pre-kickoff availability and forecast timestamps; the result observation must be after kickoff;
- paired probabilities with explicit mass summing to one for `win`, `push` and `loss`;
- a registered first-party NFL/club source URL plus SHA-256-shaped digests for the input, availability, result, forecast record and training artifacts, together with a nonempty input-artifact locator (artifact existence and immutable storage still require independent review); and
- no duplicate fixture/target row.

The code checks URL membership and digest **format**, not the bytes behind the digest, whether a source actually entails a value, whether a commit exists/is ancestral, or whether every tried strategy is included in `family_size`. An independent reviewer must verify those facts before any reported difference could enter a strategy review. A positive interval from this utility is not, by itself, proof of skill.

## Current decision status

| Item | State | What clears it | Official source scope |
| --- | --- | --- | --- |
| Official time-stamped availability history | Missing as an eligible multi-day corpus; the public site has a point-in-time report record, not a replayable season history | A rights-cleared source, immutable pre-kickoff snapshots, hashes and conflict handling | [NFL injury report](https://www.nfl.com/injuries/) · [NFL.com Terms §1.3](https://www.nfl.com/legal/terms/) |
| Actual starters, inactive status and participation | Partial across a few official Game Books; not a season-wide feature table | Official Game Book or official snap/participation records for the same held-out fixtures | [NFL Game Book](https://static.www.nfl.com/image/upload/v1794570519/gamecenter/ab5828d9-4feb-11f1-abca-2c54536568a9.pdf) · [NFL player statistics](https://www.nfl.com/stats/player-stats/) |
| Preregistered matched forecast pairs | None committed for this protocol | Commit the frozen target, feature definitions, fit windows, family size, thresholds and scoring rule before the test window | [NFL schedule](https://www.nfl.com/schedules/2026/by-week/week-10) — fixture context only; registration remains a project artifact |
| Ablation difference and uncertainty | **Blank / not computed** | Same-fixture out-of-sample forecasts with enough preregistered held-out weeks and verified source artifacts | [NFL official results schedule](https://www.nfl.com/schedules/2026/by-week/week-10) · [Brier score reference](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.brier_score_loss.html) |
| Leaderboard eligibility | **Not eligible** | Independent source audit, multiplicity-complete results, prospective paper replication and every other admission gate | [Official NFL result source](https://www.nfl.com/schedules/2026/by-week/week-10) — no leaderboard or skill endorsement |

These rows are project-status statements, not NFL statistics. Official source scope is linked above; the source register and open permission issue are available in the [decision desk](../decision-desk/index.html) and the [flagged review page](../decision-desk/flagged.html).

## Reproduce the utility

```sh
python3 -m unittest tests.test_ablation -v
```

All test forecasts are synthetic, clearly named as such, and never written to the public results or leaderboard. The method currently computes no NFL estimate.
