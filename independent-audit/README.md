# Independent NFL source audit

Reviewed on 2026-11-04 UTC by session `arena/489d1d3e-own9`. This directory is an independent, narrowly scoped handoff; it does not change the dashboard or files claimed by other sessions. The audit of the existing dashboard is anchored to main at commit `9f6eb6f`.

## Executive summary

- The [initial repository tree](https://github.com/sassnarep3-star/Own9/tree/4828ac07f28eb71d0e497836ec363926b5b2be3f) contained only a README. It did not contain a model, backtest, strategy leaderboard, or historic dataset.
- We found **a limited official-publisher historical snapshot**, not a validated betting feed. The [NFL Week 8 picks article](https://www.nfl.com/news/nfl-picks-week-8-2026-nfl-season) says its FanDuel-provided lines were locked at 1:30 p.m. ET on Thursday, October 29, 2026. The article displays moneylines, one stated spread side and game totals. Matchups and final scores can be reviewed against the [NFL Week 8 schedule](https://www.nfl.com/schedules/2026/by-week/week-8). These are NFL.com-reported values, not proof that a user could actually have placed a wager at those odds.
- The article is a mutable editorial page with later updates. A stated lock time is not proof of a contemporaneous, executable sportsbook quote, and the current page cannot establish exactly when all of its other content became available. Do not use later text as point-in-time features.
- The [NFL.com terms](https://www.nfl.com/legal/terms/) restrict systematic retrieval to compile a database without express written consent; rights to collect, republish or commercialize these data have not been established. A preliminary local transcription was withdrawn rather than published as a dataset. This is a rights concern, not a legal determination about any particular use.
- Spread and total prices and evidence of execution are **unverified and blank**. There are no player-prop or parlay quotes in this snapshot. It is only one week, not a sample sufficient to validate an edge, strategy, or correlation. No simulated profit, picks, probabilities, or correlation values are claimed.
- Luck cannot be eliminated from future outcomes. Proper out-of-sample tests, uncertainty estimates, multiple-comparison controls, and a matched benchmark can help distinguish evidence of forecasting skill from noise; they cannot guarantee profit. The [American Statistical Association](https://www.amstat.org/asa/files/pdfs/p-valuestatement.pdf) cautions against treating a p-value alone as the probability that a hypothesis is true or as a substitute for transparent reporting.
- Actual reward eligibility and legal compliance are **unverified**. This is research, not a sponsored competition or wagering service. As one jurisdictional example, the [Washington State Gambling Commission](https://wsgc.wa.gov/rules-enforcement/illegal-gambling-activities) describes restrictions on sports wagering and defines gambling using prize, chance, and consideration. This example does not assert the user's location or determine the law for any particular contest.

## Artifacts

- `source-ledger.md`: links, the specific claim each source supports, access status, and what it cannot verify.
- `dashboard-row-audit.md`: a line-by-line review of the existing dashboard's data rows, tied to a fixed commit. These findings concern that baseline; other sessions may subsequently change it.
- `integration-handoff.md`: suggested validation and product changes, clearly marked as proposed rather than externally endorsed.

## Integration request

The final integrator should link the official article and schedule for review, present the article only as an **NFL-reported historical example**, and flag collection/republishing rights, executable prices, missing spread/total prices, historic player-prop and parlay quotes, and all model results as unverified. Do not publish the withdrawn transcription or automate systematic collection without appropriate rights review and authorization. The row-level audit is not a substitute for re-verifying the eventual combined site. If the final site includes this directory, link its pages from the shared navigation without changing or deleting other sessions' work.
