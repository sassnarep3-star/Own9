# Decision register — NFL line research

**Purpose:** a reviewable proposal queue, not a request to implement changes automatically. Each proposal separates what is known, what is missing, the decision it enables, and its acceptance test. No market estimate, injury status, or strategy result is asserted here.

This repository already provides a research dashboard and evidence-gap register. This additive register organizes the next decisions without editing shared navigation, model, dataset, or generated-site files. Link it from the main dashboard during a future integration pass.

## Executive summary

Own9 can specify and test a research process, but cannot currently make an evidence-based claim that any NFL strategy beats a market. A live injury page is not a versioned historical injury archive; a statistics page is not a timestamped odds archive. Without licensed, time-aligned snapshots of information and executable prices, backtests risk look-ahead bias and cannot establish attainable edge. Player availability/depth-chart impacts, fair probability, correlations, market closing comparisons, and leaderboard ranks therefore remain unverified or unevaluated.

Recommended decision: keep the project in **research / paper-only** mode. First resolve data rights and provenance, then define evaluation and eligibility rules, then run a prospective shadow period. Do not announce a funded reward pool until legal, operational, and statistical controls are approved. Luck cannot be removed from individual outcomes; only reduce and quantify uncertainty with pre-registered tests and repeated forward evaluation.

## Questions that must be answered before a reasonable decision

| ID | Decision question | Information available now | Missing information / risk | Evidence needed to decide | Suggested owner |
|---|---|---|---|---|---|
| Q01 | What is the target decision: forecast accuracy, market price discovery, or wagering returns? | The repo proposes original lines and skill-oriented competition. | Primary objective, use case, jurisdiction, and whether any real-money use is intended. | Written scope and approved use policy. | Product / compliance |
| Q02 | Which markets are in scope? | Singles, parlays, and player-prop combinations are named. | League/season coverage, market definitions, void/push rules, books/exchanges, and cutoff times. | Frozen market taxonomy and settlement specs linked to governing rules. | Research |
| Q03 | Are historical inputs genuinely available as they were known at decision time? | Official source links and current pages are catalogued. | Immutable timestamped historical injury, roster, depth chart, weather, stats, and odds snapshots; correction history and licensing. | Sample data audit with source, retrieval timestamp, event-time, version/hash, and usage rights for each field. | Data / legal |
| Q04 | Can original probabilities be calibrated and executed at offered prices? | Modeling and validation methods are described. | Out-of-sample predictions, quote availability, limits, slippage, commission, and line movement. | Frozen model plus timestamped executable quote archive and prospective shadow log. | Modeling / operations |
| Q05 | How will uncertainty and multiple testing be controlled? | The project describes proper scores, holdouts, and multiple-testing concerns. | Number of tried variants, selection history, dependence across weeks/seasons, and pre-registered thresholds. | Trial registry, untouched forward holdout, uncertainty intervals and multiplicity plan. | Statistician |
| Q06 | How are injury and lineup deficiencies represented? | Official injury-report source exists; reports contain status fields. | Historical as-of player status, actual participation, depth chart at each timestamp, replacements and scheme/context. Current report cannot establish historic knowledge. | Versioned snapshots with player/team identifiers and explicit source timestamps; audited sample vs official reports. | Data / football analyst |
| Q07 | What counts as a valid correlation estimate? | Correlation methods are documented. | Paired contemporaneous leg probabilities, shared game/team factors, sample size and regime coverage. | Out-of-sample joint outcomes and forecast probabilities; compare joint model vs independence with intervals. | Modeling |
| Q08 | What makes a leaderboard fair? | A leaderboard concept and validation gates exist. | Eligibility, minimum observations, market-specific tracks, scoring, tie-breaks, entrant selection, appeals and account controls. | Public rules and reproducible scoring script, tested on synthetic fixtures and prospective records. | Product / audit |
| Q09 | Are rewards lawful and operationally safe? | No funded prize pool is established. | Applicable jurisdiction, contest/gambling classification, tax, age, privacy, fraud, conflicts and funding. | Qualified jurisdiction-specific legal review and approved terms before any reward. | Legal / operations |
| Q10 | How should a system abstain? | Fail-closed gates and missing-value policy are present. | Maximum tolerated uncertainty, stale-data rules, market suspension and incident escalation. | Predefined abstention triggers and tests; demonstrable logs for stale/missing inputs. | Product / risk |

## Suggestions for review (not implementation commitments)

| ID | Proposal | Why it improves decisions | Required discovery / prerequisite | Acceptance test | Priority |
|---|---|---|---|---|---|
| S01 | Add a data-admission gate and provenance manifest before any model input. | Prevents silent look-ahead, undocumented data, and unlicensed use. | Establish official/authorized archives, rights, timestamps, entity IDs, correction policy. | Every admitted field has source, event-time, observed-time, version/hash, rights status, and missingness report; reject incomplete rows. | P0 |
| S02 | Create a versioned injury and lineup timeline, separate from the live injury display. | Distinguishes report status from actual replacement/availability and when the information became known. | Historical reports, roster/depth snapshots, participation and reliable player IDs. | Reconstruct a dated sample with no future data leakage; unresolved player/team matches stay flagged, never guessed. | P0 |
| S03 | Make an explicit decision brief for each strategy: forecast, quote, edge, uncertainty, and abstain reason. | Lets a reviewer understand what would change a decision, not just see a point estimate. | Calibrated forecast and executable quote data. | Reproducible report includes time, market rules, inputs, probability interval, price, costs, data freshness and gate statuses; otherwise no recommendation. | P1 |
| S04 | Evaluate parlays with joint probabilities, not products of independent leg estimates by default. | Shared teams, game scripts, weather, and player usage can make legs dependent. | Paired, timestamped leg/outcome history and enough support for each combination. | Compare joint forecast to independence baseline on untouched data, with uncertainty and grouped-by-game evaluation; insufficient support => not evaluated. | P1 |
| S05 | Split competition into tracks and score probabilistic skill before return. | Separates forecast quality from variance in stakes and market selection. | Rules, eligible observations, frozen predictions, proper-score baseline and anti-selection policy. | Publish reproducible scoring on prospective locked submissions; report uncertainty and show no winner if minimum evidence/gates fail. | P1 |
| S06 | Introduce a shadow-mode period before any real-money integration or rewards. | Measures operational data failures and prospective stability without implying historical backtest is sufficient. | Data rights, monitoring, locked predictions and incident process. | Time-stamped predictions and prices are immutable; independent audit reproduces metrics and all incidents are disclosed. | P2 |
| S07 | Add a structured suggestion-review workflow to the dashboard. | Makes proposals, missing information, owners, choices, and rationale visible before implementation. | Shared integration owner to add navigation and decide a storage/review convention. | Reviewer can mark accept / reject / defer with rationale and evidence; accepted items become scoped tasks only after approval. | P1 |
| S08 | Publish an explicit non-goals and safety policy. | Avoids implying guaranteed profit or that luck can be removed. | Legal/product review if the use expands beyond research. | Every public strategy display says paper/research status, uncertainty, and current gate state; no unverified performance claims. | P0 |

## Proposed review outcomes

For each S-item, a reviewer should select **accept**, **reject**, or **defer**, record a rationale and identify the evidence or decision owner. Acceptance authorizes planning only, not deployment. Any factual value added later must have an official/authorized source link at the row level; unconfirmed values remain blank and visibly flagged.

## Verification boundary

This file is a proposal and requirements checklist. It does not claim that the referenced repository evidence has been independently re-audited here, nor that any NFL data, price, correlation, injury, strategy, or reward has been verified. See the dashboard's sources and Flagged for Review pages for the current project evidence and its stated limits.
