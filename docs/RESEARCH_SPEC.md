# NFL line origination — proposed research specification

As of 2026-11-04. **Not a fitted model, proof of skill, or wagering service.**
Official references and their checked scopes are in [the evidence register](../evidence/sources.json).

## Executive decision

Build an auditable forecasting competition before risking capital. No verified historical executable price archive or point-in-time, paired NFL dataset was obtained. There is consequently no defensible numerical NFL line, correlation, return, ranking, or cash reward to report. Missing values remain null/blank. Mathematical unit tests are not strategy validation.

## Data contract (proposed; acquisition not implemented)

Every observation needs stable game/player/team IDs, season, season type, kickoff UTC,
market/selection/threshold, source URL, raw capture SHA-256, retrieval UTC, source publication UTC,
revision ID and availability UTC. Preserve raw payloads subject to source permissions.
Separate feature captures, forecasts, quotes, settlements and eligibility attestations.

Forecasts: model/code/config hash, training cutoff, issued UTC, probabilities for each settlement
state, uncertainty method, selection rule and withheld/abstained reason. Quotes: operator, jurisdiction,
market ID, decimal price, capture time, limit/availability evidence, overround and rules snapshot.
Settlements: official outcome, exact push/void/dead-heat/reduced-leg treatment, settlement timestamp.
The NFL statistics and injury pages prove publication of those categories, not access to an official
historical odds feed or a license to redistribute. Do not substitute community datasets under an
“official verified” label. Current injury pages cannot reconstruct pre-kickoff availability.

## Strategy registry (hypotheses, not discovered edges)

- G1 game singles: fit regularized opponent-adjusted scoring distributions from past-only game/drive
  efficiency, pace and availability. Home margin = home score minus away score; price home cover as
  P(margin + home handicap > 0), push at equality. Moneyline must model ties and exact market rules;
  total over uses P(home + away > total). Fair spread is not generally the mean margin.
- P1 player single: forecast participation, opportunities and conditional efficiency separately;
  compare a negative-binomial count candidate with a simpler exposure-only baseline. Receiving,
  rushing and passing yard distributions require their own models; do not recycle count likelihoods.
- X1 cross-game parlay: estimate joint probability using common-week latent effects; compare with an
  independence baseline but never assume independence as fact. Use actual quoted combo price.
- S1 same-game prop combo: joint team-play-volume, pass/rush allocation, target allocation and
  conditional efficiency simulation, with shared game script. Enforce team/player accounting
  constraints and model each rule-defined settlement state. Pairwise rho cannot price 3+ legs.
- A1 abstention candidate: issue no pick if required input/quote stale, missing or outside training
  support. Any edge cutoff must be frozen on validation data; publish coverage including abstentions.

Ablations: opponent adjustment, pace, availability and joint effects independently removed. Register
all trials, including failed variants. No inferred sign or size is assigned to any signal.

## Proposed validation policy — not yet run

1. Provenance: 100% of evaluated records have required IDs, official outcome references, capture
   hashes, correct units and rules. Missing required record quarantined; do not impute a price.
2. Point in time: every feature and executable quote available strictly before forecast issue and
   kickoff; no same-game records split across folds; reject revised future data. Freeze predictions.
3. Holdout: oldest seasons for training, later season(s) for tuning, latest completed eligible
   season untouched for final test; expanding season/week folds within development only. Exact
   seasons and minimum effective sample set by pre-study power simulation, not chosen after results.
   Without a frozen power/design report this gate cannot pass.
4. Prediction: predeclared paired improvement (market baseline log loss minus model log loss) must
   have a strictly positive simultaneous lower confidence bound on the sealed test. Report Brier,
   calibration bins, calibration uncertainty, all folds, sample sizes and selection coverage. Treat
   game, prop and joint-event contests separately; unlike targets cannot be ranked together.
5. Economics: evaluate flat hypothetical one-unit stakes using captured executable prices and all
   settlement states, fees and capacity limits. Require strictly positive simultaneous lower bound
   on mean net return after costs, plus a predeclared tolerable drawdown limit. No cash stakes now.
6. Selection: freeze the complete candidate family before final test. Proposed familywise alpha
   0.05, allocated across all primary prediction and return claims (not just surviving strategies).
   Week-block resampling proposed to retain within-week/game dependence; study block size,
   nonstationarity and sparse-event power first. No valid interval or power study means no pass.
7. Stability: require predeclared subgroup and degradation checks by season, quote freshness and
   availability changes, prospective paper-trading replication and a kill switch for missing data
   or drift. Numerical tolerances and sample sizes must be frozen before evaluation; currently unset.

## Correlation and joint pricing

Predeclare leg definitions, thresholds, direction, market rules and observation window. Join on
stable event and settlement IDs; missing, void and push records are not losses. Separate descriptive
statistic correlations from binary leg-win correlations and from return correlations. For binary
nonconstant paired legs, phi equals Pearson correlation on 0/1 indicators. Report eligible n,
excluded n and reasons, joint win frequency, covariance and a week-block interval. Undefined rho
stays blank. Marginal probabilities p and q plus rho determine two-leg joint success via
p*q + rho*sqrt(p*(1-p)*q*(1-q)), subject to feasible Bernoulli bounds. This is algebra, not an
estimator for NFL probabilities and not sufficient for 3+ legs. Resampling/interval implementation
is not supplied. No correlation estimate or independence assertion is published.

## Competition and reward design

Research-only four separate tracks (G1, P1, X1, S1); only gate-eligible candidates are ranked.
Rank by simultaneous lower bound on improvement in matched-target log loss; display Brier,
calibration, net-return interval, drawdown, coverage and effective sample next to rank. Frozen tie
rule: lower Brier, then smaller model complexity; unresolved tie shares rank. All submissions and
hashes published before scoring, including rejected candidates. Proposed non-cash recognition only:
“research leader” badge per eligible track, no badge when none qualify. No funded competition,
sponsor, monetary pool, prize schedule or actual award exists. No inter-track global winner.

## What is actually automated

`research/metrics.py` performs exact settlement math, descriptive Pearson/phi, binary scoring,
proportional no-vig baseline and fail-closed gate eligibility. It does not infer trust in inputs.
`tools/build.py` renders the evidence-backed static site; `tools/verify.py` checks row structure,
known references, local assets/fragments, generated-file freshness and the absence of invented NFL
metrics. Unit tests exercise synthetic arithmetic, not NFL backtests. Ingestion, source permission
checks, model fitting, interval inference, independent attestation and scheduled market collection
remain unimplemented, explicitly flagged. No credentials or manual entries requested from the user.

## Safety

Probabilistic sports outcomes retain chance. Validation may provide evidence of predictive skill,
never remove luck or guarantee future profits. No automated wagering or personal financial advice.
