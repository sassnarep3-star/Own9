# Dashboard row-by-row audit

Review scope: the five root dashboard pages at [commit 9f6eb6f3409feefd3005b5f84aa464b7867bf40d](https://github.com/sassnarep3-star/Own9/tree/9f6eb6f3409feefd3005b5f84aa464b7867bf40d). The table below examines each of their 28 data rows. A source may verify a repository state or provide technical context; it does not certify the proposed policy, strategy or profitability. Rows that are proposals or missing evidence remain unverified. Later changes are outside this dated audit and must be rechecked by the integrator.

## Overview

| Row | Baseline entry | Review finding | Official evidence / context |
| --- | --- | --- | --- |
| I1 | Initial repository | Confirmed: the initial tree contains only a README. The statement is limited to that initial commit. | [Initial GitHub tree](https://github.com/sassnarep3-star/Own9/tree/4828ac07f28eb71d0e497836ec363926b5b2be3f) |
| I2 | Line origination | Not implemented at the baseline; timestamped features and matched prices are proposed validation requirements, not NFL-endorsed rules. | [Baseline tree](https://github.com/sassnarep3-star/Own9/tree/9f6eb6f3409feefd3005b5f84aa464b7867bf40d), [leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html) |
| I3 | Skill versus luck | A reasonable research principle, not an empirical performance result. The original heat-flow case study is not NFL-specific. | [ASA p-value statement](https://www.amstat.org/asa/files/pdfs/p-valuestatement.pdf) |
| I4 | Correlation | The baseline page leaves estimates unreported; that absence is not evidence that all possible correlations equal zero. | [Baseline leaderboard](https://github.com/sassnarep3-star/Own9/blob/9f6eb6f3409feefd3005b5f84aa464b7867bf40d/leaderboard.html) |
| I5 | Risk | Safety advice is not evidence of a winning strategy; the original qualitative study is not a betting model. | [UK regulator: spending limits](https://www.gamblingcommission.gov.uk/public-and-players/guide/page/limit-how-much-you-can-spend), [Washington help resources](https://wsgc.wa.gov/responsible-gaming-self-exclusion/resources-people-gambling-disorders) |

## Strategies

| Row | Baseline entry | Review finding | Official evidence / context |
| --- | --- | --- | --- |
| S1 | Game single | Proposed score-distribution model only. NFL statistics are data context; predictive skill and price advantage are unverified. | [NFL player statistics](https://www.nfl.com/stats/player-stats/) |
| S2 | Player prop single | Proposed volume and efficiency model only. Player availability, market terms and prop prices need point-in-time evidence. | [NFL injury report](https://www.nfl.com/injuries/) |
| S3 | Different-game parlay | Proposed joint estimate only. The original NIST heat-flow case study is not a parlay or joint-probability reference. | [Penn State multiplication rule](https://online.stat.psu.edu/stat414/Lesson04) |
| S4 | Same-game prop combo | Proposed joint simulation only. No real paired prop sample, payout quote or validation was established. | [Fanatics Tennessee rules](https://sportsbook.fanatics.com/legal/tn/house-rules/), [Penn State conditional probability](https://online.stat.psu.edu/stat414/Lesson04) |

## Validation gates

| Row | Baseline entry | Review finding | Official evidence / context |
| --- | --- | --- | --- |
| V1 | Provenance | Proposed gate; the NFL stats homepage alone does not demonstrate a retained snapshot, permission, or reconciliation. | [NFL terms](https://www.nfl.com/legal/terms/), [NFL GSIS corrections](https://www.nflgsis.com/Help/About.html) |
| V2 | Point in time | Proposed gate; a current NFL page is not proof of what was known before a historical prediction. | [scikit-learn leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html) |
| V3 | Evaluation | Proposed chronological train, validation and test separation; no such test was run at the baseline. | [scikit-learn time-series splits](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) |
| V4 | Predictive quality | Proposed log loss, Brier score and calibration. The original NIST case study does not define these measures. | [Log-loss documentation](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.log_loss.html), [forecast verification](https://www.spaceweather.gov/sites/default/files/images/u30/Ensemble%20Forecast%20Verification.pdf) |
| V5 | Economics | Proposed gate. The original UK survey does not specify a particular market's settlement, fees, or executable price. | [Fanatics Tennessee house rules](https://sportsbook.fanatics.com/legal/tn/house-rules/) |
| V6 | Selection control | Proposed preregistration, multiplicity control and dependence-aware uncertainty, not a completed analysis. Resampling assumptions and cluster counts matter. | [Penn State multiple testing](https://online.stat.psu.edu/stat555/node/58/), [clustered-data paper hosted by NIH](https://pmc.ncbi.nlm.nih.gov/articles/PMC10893847/) |
| V7 | Stability | Proposed sensitivity and drift checks; no seasonal stability result exists at this baseline. | [NIST case study](https://www.itl.nist.gov/div898/handbook/eda/section4/eda4283.htm) |

## Leaderboard

| Row | Baseline entry | Review finding | Official evidence / context |
| --- | --- | --- | --- |
| L1 | Game single | Not run; score, correlation and reward cells are blank. Do not assign a rank or prize. | [Baseline leaderboard](https://github.com/sassnarep3-star/Own9/blob/9f6eb6f3409feefd3005b5f84aa464b7867bf40d/leaderboard.html) |
| L2 | Player prop single | Not run; score, correlation and reward cells are blank. | [Baseline leaderboard](https://github.com/sassnarep3-star/Own9/blob/9f6eb6f3409feefd3005b5f84aa464b7867bf40d/leaderboard.html) |
| L3 | Cross-game parlay | Not run; score, correlation and reward cells are blank. | [Baseline leaderboard](https://github.com/sassnarep3-star/Own9/blob/9f6eb6f3409feefd3005b5f84aa464b7867bf40d/leaderboard.html) |
| L4 | Same-game prop combo | Not run; score, correlation and reward cells are blank. | [Baseline leaderboard](https://github.com/sassnarep3-star/Own9/blob/9f6eb6f3409feefd3005b5f84aa464b7867bf40d/leaderboard.html) |

## Flagged for Review

| Row | Baseline entry | Review finding | Official evidence / context |
| --- | --- | --- | --- |
| F1 | Historical market prices | The unverified executable-price warning remains valid. An NFL article does report dated historical lines, but it does not prove bet acceptance. | [NFL Week 8 picks](https://www.nfl.com/news/nfl-picks-week-8-2026-nfl-season) |
| F2 | Model and evaluation | Confirmed for the initial tree, which contains only README; not a claim about all later branches. | [Initial GitHub tree](https://github.com/sassnarep3-star/Own9/tree/4828ac07f28eb71d0e497836ec363926b5b2be3f) |
| F3 | Correlation values | Unverified at the baseline; the NIST case study is background rather than evidence about this repository. | [Baseline leaderboard](https://github.com/sassnarep3-star/Own9/blob/9f6eb6f3409feefd3005b5f84aa464b7867bf40d/leaderboard.html) |
| F4 | Strategy rewards | Not verified; the initial tree cannot establish whether a sponsor exists elsewhere. | [Initial GitHub tree](https://github.com/sassnarep3-star/Own9/tree/4828ac07f28eb71d0e497836ec363926b5b2be3f) |
| F5 | Luck | This is a limitation, not a measured skill-versus-luck decomposition. Confidence intervals depend on their method and assumptions. | [ASA p-value statement](https://www.amstat.org/asa/files/pdfs/p-valuestatement.pdf) |
| F6 | Source scope | Correctly warns that a contextual link does not verify every proposal. A semantic review is still needed row by row. | [Baseline generator](https://github.com/sassnarep3-star/Own9/blob/9f6eb6f3409feefd3005b5f84aa464b7867bf40d/tools/build.py) |
| F7 | NFL page scope | Correct for the baseline tree: no historical point-in-time extract was retained there. A publisher-stated line lock is not itself proof of an executable snapshot. | [Baseline tree](https://github.com/sassnarep3-star/Own9/tree/9f6eb6f3409feefd3005b5f84aa464b7867bf40d), [NFL Week 8 picks](https://www.nfl.com/news/nfl-picks-week-8-2026-nfl-season) |
| F8 | Tail risk | NIST supports general caution about skewness and extreme values. No NFL return distribution was measured. | [NIST skewness and kurtosis](https://www.itl.nist.gov/div898/handbook/eda/section3/eda35b.htm) |
