# NFL line origination and strategy validation

**Research specification, 2026-11-04. Not a trained model or wagering advice.**

## Executive summary

Own9 started as a repository containing only a README. This session establishes
an auditable research foundation, static dashboard, tested probability utilities,
and a deliberately empty empirical leaderboard. Eight candidate strategies cover
singles, cross-game parlays, and player-prop combinations. Eleven validation gates
separate a plausible idea from a reward-eligible strategy. **No strategy has passed
those gates.** No actual NFL line, correlation, performance estimate or cash award
is asserted.

Primary NFL pages were inspected for the rulebook, team-stat categories, and injury
report schema. They do not constitute a provenance-complete historical as-of
training dataset or an executable odds archive. Numerical team-stat rows were
excluded because extracted column headings were incomplete. Official statistical
software documentation supports the methods, not the profitability of any strategy.
The checked claims and limitations are in [catalog.json](catalog.json), including
direct official source links. These are scoped human/agent reading observations,
not cryptographic snapshots of the full external documents.

**Luck cannot be removed.** We can estimate uncertainty, reduce leakage and
multiple-testing bias, and demand replication. We cannot prove a strategy is
skill-only, guarantee positive returns, or turn short-term profit into evidence of
skill. Reward points are a proposed research incentive, not a funded prize pool.

## Data contract and admission (not yet connected)

Each raw observation would require all of:

- Official source URL and applicable data-use rights; primary NFL/team source for
  football facts, actual operator source for quotes and settlement.
- Source publication/as-of timestamp, UTC retrieval timestamp, immutable snapshot
  location and SHA-256 hash of the snapshot, parser version and entity IDs.
- Game ID, season, week, kickoff UTC and forecast cutoff strictly before kickoff.
- Features known by cutoff; historical revisions must not overwrite earlier facts.
- For a quote: book, jurisdiction, market and player IDs, side, threshold, full
  decimal payout, quote time, ticket rules and bet availability. A theoretical
  product of leg payouts is not an actual parlay quote.
- For settlement: official result, correction history, exact ticket push/void,
  participation and overtime policy. Never generalize an operator example to all
  jurisdictions. The retrieved DraftKings general rules describe Virginia, not
  Washington. [Operator rules](https://sportsbook.draftkings.com/help/general-betting-rules/general-rules).

No such historical dataset was admitted. Public page accessibility is not a
license for bulk reuse. There is no undocumented fallback to third-party feeds.
Missing values are JSON null and visually blank, with an explicit status field.

## Original probability and line model (proposed, not fitted)

1. Assemble official, as-of game/play and player logs. Version the split calendar.
2. Fit a regularized team offense/defense baseline only on earlier games. Retain
   discrete score support, dispersion, home effects and parameter uncertainty.
3. Estimate possessions, play mix and conditional efficiency using nested
   walk-forward tuning. Injury features require archived reports; do not invent
   status impacts or weights. Compare the simple baseline before adding features.
4. For player props, jointly model team opportunity, participation and constrained
   player allocation, then efficiency. Correlated game paths feed combo legs.
5. Calibrate on prior-only validation folds; publish the final score/prop
   distribution only after all data and validation requirements are met.

`engine/core.py` implements steps **after** a valid distribution exists; it does
not fit the above model. `distribution_lines` returns negative median home margin
as a home-spread reference and median combined score as a total reference. These
are not unique balanced-odds market prices: discreteness, push probability and
asymmetry matter. Price each threshold using the whole PMF. The engine rejects
truncated PMFs that do not sum to one, rather than inventing the missing tail.
NFL rules determine football outcomes; sportsbook ticket rules determine wagers.
[Official rulebook](https://operations.nfl.com/rules-officiating/2026-nfl-rulebook).

## Pricing derivations (project mathematics, not quoted odds)

For decimal payout D (including returned stake) and probabilities W, P, L for
win, push/refund, loss, with W+P+L=1:

- Expected net return per staked unit before costs: W(D-1)-L.
- With per-stake cost c: EV = W(D-1)-L-c.
- Zero-cost fair decimal payout, when W>0: D_fair=1+L/W.
- No finite fair price if W=0. An all-push ticket is not a tradable opportunity.
- No-push special case: D_fair=1/W.

These are algebraic consequences of the stated payoff convention. The operator
market definitions supply **examples**, not universal verification of the
assumptions. [Market rules](https://sportsbook.draftkings.com/help/general-betting-rules/market-rules).
Voids, participation exceptions and combo repricing need separate verified
settlement code; **generic parlay push/void settlement is not implemented**.

Proportional no-vig normalization q_i=(1/D_i)/sum_j(1/D_j) is an explicitly chosen
comparison convention for an exhaustive, mutually exclusive market. It is not a
claim about true probabilities. Markets with different line/cutoff/settlement or
unmatched outcomes must not be combined.

## Correlations and combinations

Publish paired sample IDs, cutoff, season, market threshold, number of independent
games/weeks, r, uncertainty and missingness. Compute both continuous residual
association and actual binary hit-event association. A passing-yards r does not
price two over events. Undefined correlation for constant inputs stays blank.
[SciPy definition and limitations](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.pearsonr.html).

For **two non-push Bernoulli events only**, algebra gives
P(A and B)=p_A p_B + rho sqrt[p_A(1-p_A)p_B(1-p_B)]. Reject values outside the
Fréchet bounds max(0,p_A+p_B-1) <= P(A and B) <= min(p_A,p_B). The utility checks
these constraints. This identity does not estimate rho and cannot be extended
by multiplying pairwise adjustments for three-plus legs. Pairwise correlation
matrices do not identify the full joint distribution. Use calibrated multivariate
samples and count simultaneous hits; model and sampling uncertainty remain.

No correlation coefficient or assumed sign is published for actual NFL markets.
The nested-threshold relationship is a logical identity, not an empirical claim
about a player. Quotes still must be actual operator combo quotes.

## Validation gates, implemented vs proposed

The catalog specifies G01–G11. The engine implements numeric checks, grouped
walk-forward indices, binary Brier/log loss and reliability bins, Pearson r,
Holm-adjusted p-values, week-cluster percentile bootstrap intervals and a
fail-closed gate-evidence structure check. It **does not** independently verify
sources, fit candidate models, generate valid hypothesis-test p-values, enforce
licensing, simulate all settlement cases, perform power analysis, or certify that
an evidence artifact proves a gate. Evidence status requires an independent
review/evaluation pipeline. A status flag/hash alone never certifies truth.

Train/test split units are complete weeks, preserving same-game clustering. For
NFL irregular schedules, our custom splitter is grouped by observed weeks rather
than assuming equally spaced bets. Weeks with no observations are not invented.
The intended full pipeline must also embargo overlapping feature windows when
needed and isolate tuning/calibration from final test outcomes.
[Time-series caveat](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html).

Report scores against fixed constant and synchronized no-vig market baselines on
identical eligible observations. Brier/log loss are proper scores but not pure
calibration measures; include bin counts and reliability diagrams.
[Calibration documentation](https://scikit-learn.org/stable/modules/calibration.html).
Do not discard pushes to improve ROI: use binary proper scores only for the
explicitly conditioned non-push task, and evaluate push predictions separately.
ROI uses every staked ticket including refunds according to its verified rules.

Resample entire observed weeks, preserving each week's joint exposures. Use
paired per-observation score differences rather than two independent intervals.
The implemented percentile cluster bootstrap assumes exchangeable week clusters;
serial dependence or drift requires longer blocks or a different valid method.
Two clusters suffice to run the utility, **not** to claim useful inference. The
bootstrap is not a substitute for pre-registered power analysis. Degenerate
resamples, few weeks, and model selection invalidate naive confidence claims.
[Bootstrap reference](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html).

All registered trials, including abandoned variants, enter the multiplicity
family. Holm adjustment controls family-wise error under valid input tests;
it cannot repair invalid p-values. Proposed promotion requires a positive
cost-adjusted return lower confidence bound, valid corrected significance,
proper-score improvement, stability checks and a final untouched holdout.
Numeric tolerances, confidence level, power and risk limits must be registered
before running real trials; none are represented as empirically established.
[Holm reference](https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html).

## Leaderboard and proposed rewards

Maintain separate tracks for singles, cross-game parlays and prop combinations.
Evaluate the probability target relevant to the ticket, not aggregate leg hit
rate. Prevent the same game or exposure from being counted as independent wins.
Freeze one version per entry per evaluation cycle and archive unsuccessful ones.

Only entries that pass **every** gate can rank. Within comparable tracks, rank
by the lower bound of paired out-of-sample Brier improvement vs the registered
baseline; break ties by lower log loss, then lower peak-to-trough drawdown under
identical capped paper stakes. Net ROI, uncertainty, turnover, max drawdown,
sample size and independent weeks accompany any rank. Profit alone is not the
ranking objective. The site presently has blank ranks and metrics.

Proposed reward: research recognition points awarded by rank in an eligible
cycle, with exact point schedule frozen before a funded competition begins.
No point amounts are invented here, no monetary reward is available, and no
strategy receives an award while blocked. Do not reward greater leverage,
parlay payout size or repeated test-set tuning.

## Autonomous operation and honest stopping condition

The scheduled workflow reruns the deterministic report, test suite, build and
internal-link/source-reference checks. It does not fetch new NFL facts or odds.
The research date is fixed and displayed, not relabeled as fresh by a rebuild.
If evidence is absent, the report emits all strategies blocked, with null ranks,
ROI and correlations. This is an intentional safety result, not a completed
empirical NFL analysis. No manual secrets or inputs are needed for this mode.

To advance beyond this foundation, automated official historical archive access,
rights, parser/snapshot tests, model fitting and an independently audited forward
paper record are still necessary. Until those exist, the honest autonomous action
is to abstain, preserve blanks, and publish the blockers for review.
