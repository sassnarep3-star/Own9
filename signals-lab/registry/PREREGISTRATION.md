# Pre-registration — NFL signals lab (session `efe45667`)

Written 2026-11-04 (UTC) and committed to git **before** any sealed-test number was computed. The commit time-stamp is the proof of order.
The machine-readable twin is `preregistration.json`; it stores SHA-256 hashes of the code, the frozen hyper-parameters and **this file**.
`pipeline/gates.py` refuses to run the sealed evaluation unless that file is committed and every hash still matches.

## 1. What is being tested

The brief asked for "originating my own lines". No official historical odds source exists that we can reach, so a market benchmark is **not** evaluated (Gate 8 is "N/A", left blank and flagged).
We therefore test **line-pricing quality**: do our own prices (win probability / fair moneyline, expected margin, expected total, player-prop quantiles, joint probabilities) predict official-verified outcomes better than a naive reference, under proper scoring rules?
A pass means "better than the naive reference out of sample". It does **not** mean "beats the market" and is **not** betting advice. Credits on the leaderboard are virtual and have no monetary value.

## 2. Data and verification status (facts already established before this document)

* Game results 2015–2025: parsed from the NFL game-center feed (archived in `nflverse/nflfastR-raw`). Every season's per-team W-L-T / points-for / points-against equals the official NFL.com standings (32/32 teams × 11 seasons). Seasons failing this check would be excluded (fail closed).
* 2026 weeks 1–8: `nflverse/nfldata` results; the team aggregates equal NFL.com's 2026 standings (121 games, 32/32 teams). Week 9 fixtures are taken from the official NFL.com schedule.
* Player-game stats: same feed. Verified only against the NFL.com 2025 top-25 leader tables for passing, rushing and receiving (75/75 rows exact). All other player rows are **sample-verified only** and flagged.
* The feed has no inactive/DNP list and no 2026 files: player evaluation is conditional on the player recording a minimum volume in that game, and no 2026 player-prop lines can be originated (left blank, flagged).

## 3. Splits

| Split | Seasons | Use |
|---|---|---|
| burn-in | 2015–2017 | model fitting only, never scored |
| dev | 2018–2022 | hyper-parameter selection (loader capped at 2022, so later rows are never in memory) |
| **sealed test** | **2023–2025** | **one evaluation, after this commit** |
| forward holdout | 2026 weeks 1–8 | game-level models only, informational (n = 121, wide intervals) |

All models are walk-forward: a prediction for a (season, week) block uses only games from earlier blocks. Player models for 2018–2022 use expanding windows (train on earlier seasons); for 2023–2025 they are fitted **once** on seasons ≤ 2022.

## 4. The family of 31 tested strategies (Holm correction is applied over all of them)

**Game lines (14)** — baseline G0 = home-field-only expanding mean (margin), expanding mean total, normal-CDF win probability.
G1 Elo · G2 time-decayed ridge offense/defense ratings · G3 = G2 + rest/bye (margin) and roof/wind/cold/division (total) context · G4 = mean(G1, G3) · G5 process ratings (yards/play and success rate; turnovers excluded) · G6 = mean(G3, G5).
Markets: ML (win probability) and SPREAD (expected margin) for G1–G6; TOTAL for G2 and G3 only.

**Player props (8)** — baseline PR0 = mean of the player's last 6 appearances × empirical ratio quantiles. PR1 = empirical-Bayes shrunk EWMA × ratio quantiles. PR2 = gradient-boosted quantile regression (τ = .1, .25, .5, .75, .9). Markets: passing yards, rushing yards, receiving yards, receptions (PR1 and PR2 each).

**Parlays and prop combos (9)** — "both legs beat their own median" priced with a Gaussian copula whose ρ and marginal rates come from earlier seasons (≤ 2022 for the sealed test) versus independence. Pairs: QB×top receiver, QB×2nd receiver, QB×lead RB, top×2nd receiver, team spread×QB, game total×QB, team spread×lead RB, QB×opposing QB, home spread×game total.
A placebo pair (two different games in the same week) checks that cross-game parlay legs are independent. It is a diagnostic, not a strategy.

## 5. Metrics and skill

| Market | Loss | Reference |
|---|---|---|
| ML | log loss of home-win probability (ties count ½) | G0 |
| SPREAD | absolute error of expected margin | G0 |
| TOTAL | absolute error of expected total | G0 total |
| Props | mean pinball loss over τ ∈ {.1,.25,.5,.75,.9} | PR0 |
| Combos | log loss of the joint-event probability | independence |

Skill = 1 − mean(loss of strategy) / mean(loss of reference). Intervals and p-values: cluster bootstrap (resample whole games), 2,000 resamples, one-sided H0: skill ≤ 0.
Informational extra: skill of each game strategy versus Elo (G1), and a shuffled-prediction "luck envelope" (300 within-week permutations of the strategy's own predictions).

## 6. Gates — a strategy is **Validated** only if it passes G1–G7

1. **Provenance** — outcomes come from seasons that reconcile exactly to official NFL.com standings. Props and combos that use props pass only as "sample-verified" (75/75 exact on the NFL.com sample) and carry a visible flag.
2. **Point-in-time** — (a) truncation test: for 10 randomly drawn sealed-test weeks, re-running the game models with every later game removed and that week's outcomes hidden reproduces the week's predictions to 1e-9; (b) 300 random prop rows: the trailing features (count, mean of last 6, usage, last value) equal a brute-force recomputation from earlier rows only.
3. **Out-of-sample skill** — lower 95 % bound of skill on the sealed test > 0.
4. **Calibration** — not demonstrably miscalibrated. ML: 95 % CI of the logistic recalibration slope contains 1 and of the intercept contains 0. SPREAD/TOTAL: CI of the OLS slope of outcome on prediction contains 1 and CI of the mean error contains 0. Props: mean |coverage − τ| ≤ 0.03 and max ≤ 0.06 across the five quantiles. Combos: CI of (observed − predicted joint frequency) contains 0.
5. **Stability** — skill > 0 in at least 2 of the 3 sealed seasons **and** in at least 3 of the 5 dev seasons.
6. **Multiple testing** — Holm-adjusted p < 0.05 over all 31 strategies.
7. **Precision** — half-width of the 95 % interval ≤ 3 percentage points (otherwise the result is inconclusive, not a pass).
8. **Market benchmark** — N/A. No official historical odds source is reachable, so this is left blank and flagged. It is not counted as pass or fail.

## 7. Ranking and virtual credits

Rank by the lower 95 % bound of sealed-test skill within two tiers: **Validated** (all of G1–G7) and **Ranked (not validated)**. Credits = round(1000 × lower bound) for Validated strategies only; zero otherwise.
If nothing validates, the site says so. Passing here means "better than a naive reference", not "profitable".

## 8. Frozen hyper-parameters (chosen on dev only; see `hyperparameters.json` and the dev grids in `data/results/`)

Elo K = 20, home advantage 35, regression to mean 0.33 · ridge half-life 15 weeks, λ = 5 · process ratings half-life 20 weeks, λ = 10 · props EWMA half-life 5 appearances, shrinkage k = 2, boosting depth 2 / 150 iterations / learning rate 0.05 / min leaf 40.
Each grid was widened once when its optimum sat on the edge. Both selections are interior. No hyper-parameter is changed after this commit.

## 9. Declared limitations

* The reference models are naive (home-field only, trailing mean). Beating them does not show an edge over a betting market. Elo comparisons are reported alongside.
* The same sealed seasons feed 31 hypotheses; Holm controls the family-wise error only for tests listed here.
* Roofed venues are identified from missing weather readings or explicit indoor labels in the feed (heuristic). Off-site games are identified from the stadium differing from the home team's usual stadium that season (heuristic). The division map was checked against nfldata's own 2026 `div_game` (272/272).
* Player evaluation is conditional on appearing with minimum volume. Pass attempts and yards for laterals follow NFL.com's convention (verified on the sample).
* Process (G5/G6) models need play-by-play, which does not exist for 2026, so they cannot price Week 9.
