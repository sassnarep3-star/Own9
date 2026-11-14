# Strategy and validation handoff

Everything on this page is a **proposed research protocol**, not an official NFL recommendation, a claim of a measured edge, or a completed validation. No odds are represented as executable and no numerical forecasts, correlation estimates, returns, or rewards have been supplied. Definitions and methodological sources are linked; applicability to a particular market still requires testing.

## Candidate signals

| Candidate | Proposed inputs and output | Unverified prerequisites | Official source / context |
| --- | --- | --- | --- |
| Game single | Fit a pregame distribution of team scores using prior, time-available team performance, location and documented availability; derive win, spread and total probabilities from that same distribution. | Permitted historical data; prediction-time snapshots; price, limits and rules for the exact contract. | [NFL statistics](https://www.nfl.com/stats/player-stats/), [NFL injury report](https://www.nfl.com/injuries/) |
| Player prop single | Model participation separately from opportunities and efficiency, then produce an outcome distribution for the specified player and threshold. | Official player-game observations, historical availability, prop quotes, nonparticipation rules and redistribution rights. | [NFL Game Center example](https://www.nfl.com/games/panthers-at-packers-2026-reg-8), [NFL injury report](https://www.nfl.com/injuries/) |
| Cross-game parlay | Estimate a joint distribution over legs; consider common information and model risk rather than assuming games are independent. Compare with the actual accepted combination price. | Matched simultaneous leg and parlay quotes, joint observations, executable limits and settlement rules. | [Penn State conditional probability](https://online.stat.psu.edu/stat414/Lesson04), [Fanatics Tennessee rules](https://sportsbook.fanatics.com/legal/tn/house-rules/) |
| Same-game prop combo | Jointly model participation, game conditions and player opportunities; calculate each settlement state's probability for the actual bundle. | Paired player-game outcomes, threshold definitions, applicable void/push rules, actual combo prices and independent joint calibration. | [Fanatics Tennessee rules](https://sportsbook.fanatics.com/legal/tn/house-rules/), [Penn State joint probability](https://online.stat.psu.edu/stat414/Lesson04) |
| Weather feature | If permitted and genuinely available before a prediction, evaluate a timestamped forecast for the venue, not the later observed weather. | Historical forecast snapshots, venue mapping, indoor conditions and international coverage were not established. | [NWS API documentation](https://www.weather.gov/documentation/services-web-api) |

## Fail-closed gates

| Gate | Proposed pass condition | Current result | Official source / context |
| --- | --- | --- | --- |
| Rights and provenance | Retain source, license, permission, event identity, retrieval time and revision history; reject sources whose authorized use is unresolved. | Not run | [NFL.com terms](https://www.nfl.com/legal/terms/) |
| Point-in-time integrity | Reject any input, market price or preprocessing fit that was not available at prediction time; freeze forecasts before outcomes. | Not run | [scikit-learn leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html) |
| Evaluation design | Predeclare chronological train, validation and untouched test windows. Keep all selections from an event in the same fold; test prospective forecasts. | Not run | [TimeSeriesSplit documentation](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) |
| Fair comparison | Compare models to a prespecified market or other baseline on the **same eligible events and timestamps**. Report log loss, Brier score, calibration, sample count and missingness. | Not run | [Log loss](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.log_loss.html), [forecast verification](https://www.spaceweather.gov/sites/default/files/images/u30/Ensemble%20Forecast%20Verification.pdf) |
| Economics and settlement | Use the accepted, timestamped price, jurisdiction, limits, fees and versioned market rules. Represent win, loss, push, void and partial settlements as distinct states. | Not run | [Fanatics Tennessee rules](https://sportsbook.fanatics.com/legal/tn/house-rules/) |
| Selection and uncertainty | Register all candidate strategies and selection rules; prespecify multiplicity correction, dependence-aware uncertainty and decision thresholds. Report failures, not only winners. | Not run | [ASA statement](https://www.amstat.org/asa/files/pdfs/p-valuestatement.pdf), [Penn State multiplicity](https://online.stat.psu.edu/stat555/node/58/) |
| Dependence and stability | Predeclare the resampling unit and assess enough independent clusters, joint calibration, season and regime sensitivity, and price drift. Fail closed when uncertainty is too large. | Not run | [Clustered-data article hosted by NIH](https://pmc.ncbi.nlm.nih.gov/articles/PMC10893847/) |
| Rewards and legality | Publish eligibility, ties, exclusion, sponsor, funding, jurisdiction and prize rules before evaluation; do not run a real prize contest until requirements are reviewed. | Not run | [Washington State Gambling Commission](https://wsgc.wa.gov/rules-enforcement/illegal-gambling-activities) |

## Correlation protocol

Predeclare the exact two contracts, line thresholds, player/game identifiers, observation window, and inclusion rules. Align paired win/loss outcomes from the same eligible sample. Track pushes, voids, missing observations and revisions separately; do not silently code them as losses. State whether the reported association is unconditional or conditional on both legs being in action. A threshold-specific correlation should not automatically be applied to another threshold.

For binary win indicators X and Y, with nonzero variances, correlation is covariance divided by the product of standard deviations. With pX = P(X wins), pY = P(Y wins), and p11 = P(both win), this gives the following **identity**, not an observed NFL estimate:

`rho = (p11 - pX * pY) / sqrt(pX * (1-pX) * pY * (1-pY))`

If either indicator has zero variance, the coefficient is undefined; leave it blank. Record the four paired counts, cluster count, estimation window and uncertainty alongside any future result. Intervals do not erase model error or luck. A zero observed estimate is not evidence that every multi-leg combination is mutually independent. The [Penn State correlation definition](https://online.stat.psu.edu/stat414/Lesson18) and [independence discussion](https://online.stat.psu.edu/stat414/Lesson05) provide mathematical context. For three or more legs, pairwise relationships alone generally do not determine the full joint distribution.

## Pricing and leaderboard safeguards

For a single contract where a win pays decimal odds D including returned stake, a loss loses one unit, and push or void returns the full stake, expected net return per unit is `p_win * (D - 1) - p_loss`, before fees. The fair decimal price under those specific assumptions is `1 + p_loss / p_win`, only when `p_win` is positive. These are algebraic identities, not measured prices or recommendations. Partial payments, dead heats, altered prices and multi-leg settlements require their own payoff states and the applicable rules; see the [operator's example rules](https://sportsbook.fanatics.com/legal/tn/house-rules/).

Rank only strategies that pass every gate, within comparable predeclared market divisions, on the same forecast universe and timestamps. Publish paired score improvement, uncertainty and coverage together; using only voluntary selections would permit cherry-picking, and comparing raw Brier scores across different samples can be misleading according to the [forecast-verification material](https://www.spaceweather.gov/sites/default/files/images/u30/Ensemble%20Forecast%20Verification.pdf). Keep actual rewards, prize values and ranks blank until an eligible, legally reviewed competition and sufficient independent evidence exist. These safeguards cannot eliminate luck or guarantee future profits.
