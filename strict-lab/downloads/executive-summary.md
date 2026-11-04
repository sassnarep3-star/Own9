# Own9 NFL Lab — Executive summary

Evidence review: 2026-11-04 UTC.

## Decision
Do not deploy capital. This is a research framework with tested mathematical
utilities, not a verified NFL pricing model or profitable betting system. Luck
cannot be removed. No independently verified point-in-time market dataset,
trained model, measured correlation, sealed backtest or funded reward exists in
this strict-source lab. Other sessions’ exploratory work is outside its scope.

## Research design
Eight candidate designs cover opponent-adjusted game lines, availability,
schedule/rest, player volume × efficiency, role changes, cross-game parlays,
QB/receiver combinations and game-script/player combinations. Each has official
input requirements and falsification tests. These are hypotheses, not facts.

## Validation and competition
All eight evidence gates must pass: provenance, information timing, chronological
holdout, power/calibration, predictive improvement, economic robustness,
multiple-testing/dependence controls and prospective replication. Within matched
market tracks, proposed ranking uses a lower confidence bound on improvement in
proper forecast loss against contemporaneous market prices. Rewards are proposed
noncash recognition only, with no funded program or winners.

## What works today
Static dashboard; source-linked tables and CSV exports; score-PMF price
integration; refund-aware EV; two-leg joint feasibility; phi and cluster bootstrap;
Brier/log loss; Holm adjustment; timestamp checks; fail-closed readiness report;
synthetic unit tests; deterministic build and local-link checks. Root integration
owners control automated publication; no lab-specific workflow is installed.

## Evidence boundary
Official NFL pages establish potential input fields, not sportsbook prices or
historical quote availability. Official maintainer docs establish statistical
method definitions, not NFL edges. DraftKings rules inspected include a Virginia
scope and must not be generalized to Washington or any other jurisdiction.
The inherited NIST heat-flow citation was overly broad; a candidate NFL injury
policy URL soft-404ed. Both are recorded on Flagged for Review. Actual unknown
values are null/blank, never estimated and presented as observations.

## Manual-review source links
- NFL-STATS: https://www.nfl.com/stats/player-stats/
  Scope: Passing, rushing and receiving categories are visible. No statistics imported or used to fit a model; season totals are not a point-in-time game-level dataset.
- NFL-SCORES: https://www.nfl.com/scores/
  Scope: Game links and schedule context checked. No complete historical scores archive was obtained.
- NFL-INJ: https://www.nfl.com/injuries/
  Scope: Practice and game-status fields are visible; blank fields and No Injuries Reported must not be interpreted as verified availability. Historical revision timestamps not established.
- SCI-RHO: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.pearsonr.html
  Scope: Formula, [-1,1] range, constant-input warning and degenerate bootstrap warning checked in chunks 0–1. Default normal-theory p-value is not suitable as automatic evidence for dependent binary NFL legs.
- SCI-BOOT: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html
  Scope: Signature checked. Cluster-percentile bootstrap in Own9 is a project implementation, not a claim that SciPy automatically handles NFL clustering.
- SK-TIME: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html
  Scope: Time-order warning checked. Equal spacing assumption noted. Project uses week/group-aware design rather than blindly splitting irregular player rows.
- SK-SCORE: https://scikit-learn.org/stable/modules/model_evaluation.html
  Scope: Proper scoring discussion and classification table identifying Brier score and log loss checked. No NFL edge or numerical project thresholds are endorsed by this source.
- SK-CAL: https://scikit-learn.org/stable/modules/calibration.html
  Scope: Calibration curves and warning that Brier/log loss also reflect resolution and uncertainty checked. Must inspect calibration separately.
- SM-HOLM: https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html
  Scope: Holm method, corrected p-values and family-wise error-rate parameter checked. Source does not validate project-generated p-values.
- DK-GENERAL: https://sportsbook.draftkings.com/help/general-betting-rules/general-rules
  Scope: Jurisdiction, terms precedence and rules-revision caveats checked in introduction only. Not applicable-law verification for Washington or any other jurisdiction; no odds obtained.
- DK-MARKET: https://sportsbook.draftkings.com/help/general-betting-rules/market-rules
  Scope: Two-way moneyline ties, whole-number spread and total push definitions checked. Do not extrapolate to all operators or prop/SGP void rules.
- NIST-TAIL: https://www.itl.nist.gov/div898/handbook/eda/section3/eda35b.htm
  Scope: Definitions and outlier sensitivity checked. Tail risk is a methodological consideration, not a measured property of absent NFL returns.
- UKGC: https://www.gamblingcommission.gov.uk/about-us/guide/consumer-voice-2020-exploring-online-staking
  Scope: Qualitative research and sample limitation checked. Context for risk controls, not a US legality or staking recommendation.
- GH-PAGES: https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
  Scope: Workflow artifact and deployment permissions checked. Repository deployment is independently confirmed through GitHub API, not inferred from this document.

See sources.html, flags.html and research/catalog.json for the full ledger.
