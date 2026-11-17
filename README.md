# Own9 · NFL decision research

**Public GitHub Pages dashboard:** [sassnarep3-star.github.io/Own9](https://sassnarep3-star.github.io/Own9/)

**Research only:** no wagers are placed or recommended. No strategy is represented as profitable or validated.

Own9 is a source-linked NFL research and decision-readiness project. It combines line-origination experiments, results and availability evidence, strategy-validation gates, open questions, implementation suggestions, and a flagged-review register. The dashboard distinguishes implemented software from evidence that is actually sufficient to support a decision.

## Executive summary

- **The public site and research tooling are exercised by automated checks.** See the current [Pages verification workflow](.github/workflows/pages.yml) and run `npm test` locally. These are repository/build checks, **not** independent verification of every linked fact, model quality, or current NFL data.
- **There is no demonstrated betting edge.** A working pricing function, generated fair line, backtest calculation, synthetic example, or successful software test is not evidence of predictive skill. Use the signal/staking, validation, leaderboard, and flagged-review pages to see what is withheld and why.
- **Do not interpret missing price data as zero or as a market quote.** The site records model outputs separately from market numbers and residuals; where source-backed prices are absent, the empirical fields must remain blank. The opening/closing price requirements are not fully satisfied by the data currently represented.
- **Availability and replacement certainty are incomplete.** Injury designations alone do not prove who played or who replaced a starter. Game Books/inactive evidence, time-bounded official depth information, roster events, and snap evidence have distinct limitations documented on the relevant pages. Do not infer a depth tier from jersey number, experience, or salary.
- **A requested automated NFL-site capture is permission-gated.** NFL.com Terms section 1.3 states that systematic retrieval to compile a collection/database is prohibited absent express prior written consent. The project records this as a blocker; this README does not offer a legal interpretation. [Official terms](https://www.nfl.com/legal/terms/).
- **The registers are not yet reconciled.** The repository flags three overlapping readiness registers (82, 74, and 73 requirement rows) and has not designated one canonical. Their row totals and statuses should not be combined as if they were one consistent ledger. See [DD-14](decision-desk/flagged.html#DD-14).
- **Owner decisions remain open.** The decision pages identify the missing policy choices and default gates. No unresolved input is silently treated as permission, evidence, a market price, or a cleared validation gate.

## Start here

| Need | Page |
| --- | --- |
| Current requirements, gate, and clearing condition | [Decision readiness (82-row register)](readiness/index.html) · [Decision desk (73-row register)](decision-desk/index.html) · [Executive summary](executive-summary.html) |
| Questions, known information, missing information, and discovery probes | [Questions](questions.html) · [Information and answers](information-answers.html) · [Missing-information suggestions](missing-info-suggestions.html) · [Question ledger](question-ledger.html) |
| Review possible improvements before choosing a path | [Suggestions](suggestions.html) · [Costed suggestions](suggestion-costs.html) |
| What needs investigation or correction | [Flagged for Review](flags.html) · [Decision-desk flags](decision-desk/flagged.html) · [Repository review](readiness/repo-review.html) |
| Line origination and price/data readiness | [Origination desk](origination/index.html) · [Own lines](lines.html) · [Price snapshots](price-snapshots.html) |
| Results, validation, and strategy ranking gates | [Results](results.html) · [Validation](validation.html) · [Leaderboard](leaderboard.html) |
| Availability, starters, replacements, and source limits | [Availability](availability.html) · [Injuries and depth](injuries.html) · [Replacement depth](replacement-depth.html) |
| Check source scope | [Source register](sources.html) · [Availability evidence](availability-evidence.html) |

## What the project does and does not establish

| Area | Implemented or published | Still required before using it to make a wagering decision |
| --- | --- | --- |
| Lines | Side → total → moneyline origination order; fair line, market line, and difference represented separately; snapshot storage/schema and guards | An approved price-data policy and sufficiently complete, timestamped, source-backed executable opening and closing quotes for the same market. A model price alone is not a market comparison. |
| Results | A verified-results feed and checks against cited official results sources | Provenance-complete chronological training/validation/holdout data and complete settlement conventions before any backtest or ROI claim. |
| Strategies | Separate signal and staking records, validation gates, and a demotion-to-paper rule | Pre-registration before evaluation; prospective frozen forecasts; proper-score skill versus controls with uncertainty; no leaderboard eligibility from backtest results alone. |
| Parlays and prop combos | Dependence/joint-evidence gates and separate strategy divisions are specified | Directly validated joint probabilities and operator-specific push/void rules. Marginal probabilities must not be multiplied as if independent. |
| Injuries and replacements | Dated evidence, source links, replacement-chain work, and explicit blank/unknown states | Authorized, replayable point-in-time evidence; complete actual inactive/participation data; verified depth route or snap-based proxy; roster-event alignment and coverage across all 32 clubs. |
| Correlations | Correlation calculations and sample-size reporting are implemented in the research code | Adequate independently sourced observations, uncertainty, and a cleared dependence gate. A calculation from a small or incomplete sample is not a dependable relationship. |
| Public dashboard | A landing page, category pages, source/flag pages, and CI checks | Continued source freshness, site-level review of rendered pages after deployment, and resolution of the flagged conflicting registers and data-policy decisions. |

The exact status of each requirement, its gate, and its clearing criterion is on the linked registers. The table above is a navigation summary, not an alternate canonical register.

## Important open decision areas

1. **Price-data policy and acquisition rights.** Decide which price publishers and usage terms are acceptable, how an executable quote is defined, and what to do where a source is unavailable. Do not backtest or rank on synthetic or unsupported market prices.
2. **Availability-source permission and custody.** Resolve the NFL.com Terms blocker before systematic capture; specify what happens to committed raw captures and whether row-level data belongs in a private store. The source/legal flags preserve the relevant URLs and repository evidence.
3. **Canonical requirement register.** Reconcile the 82/74/73-row registers and select one source of truth; preserve conflicting entries until checked rather than merging counts or statuses by assumption.
4. **Strategy preregistration and evaluation.** Freeze strategy definition, sample window, benchmark, and pass/fail rules before a final holdout or prospective evaluation begins. Backtest figures are not leaderboard evidence.
5. **Depth and replacement evidence.** Verify an admissible depth source for every club or a published snap-count route; preserve shared/empty slots, actual starters, inactive evidence, and transactions rather than manufacturing a rank.
6. **Competition and rewards.** Keep rewards disabled until skill eligibility, uncertainty/multiplicity rules, prospective evidence, operational controls, and the division rules have been approved and passed.

For each question, see the [questions page](questions.html), the [readiness decisions](readiness/decisions.html), and the [decision-desk questions and owner decisions](decision-desk/questions.html). These pages publish proposed discovery steps; they do not silently supply answers that the repository does not have.

## Sources and review policy

Official publisher links and the intended scope of each source are listed in the [source register](sources.html). Requirement and evidence pages link to their sources or to the precise local project record; uncertain or unavailable values are left blank and listed for review. A link to an official page verifies only the specific fact stated in its documented scope, not a model proposal or an inference drawn from it.

The site and repository contain multiple independently built sections from earlier work. Their overlaps, stale values, source gaps, and other irregularities are kept visible on [Flagged for Review](flags.html) and the linked section-specific flag pages. In particular, automated tests validate code and page structure; they do not certify the underlying NFL evidence or establish profitability.

## Reproduce locally

Requirements: Python 3.10+ and Node.js (for browser tests).

```sh
npm ci
npm test
npm run test:browser
npm run build
```

`npm test` runs the root Python suite, evidence/register validation, and local link/page checks. `npm run test:browser` runs the browser suite where the installed browser dependencies are available. Builds and tests are not external source verification.

## Site map

- [Landing dashboard](index.html)
- [Origination engine](origination-engine.html) · [Results feed](results-feed.html) · [Correlations](correlations.html) · [Signal vs staking](signal-vs-staking.html) · [Demotion gate](demotion.html)
- [Availability](availability.html) · [Injuries](injuries.html) · [Depth of replacement](depth-of-replacement.html) · [Replacement chains](replacement-chains.html)
- [Requirements](requirements.html) · [Questions](questions.html) · [Suggestions](suggestions.html) · [Flagged for Review](flags.html) · [Sources](sources.html)
