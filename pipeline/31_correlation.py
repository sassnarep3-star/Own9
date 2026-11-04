#!/usr/bin/env python3
"""T10 - Correlation analysis and the closing-line-value bias control.

Three things are measured here, all from the source data:

A. How outcomes move together. This is what a same-game parlay or a prop combo is really
   priced on: the joint probability of two legs is NOT the product unless the legs are
   independent.
B. How the strategies' returns move together, which decides whether the leaderboard is nine
   copies of one bet or genuinely diversified.
C. A control for the best-looking statistic in the whole project: closing-line value (CLV).
   CLV is mechanically positive for ANY model that is closer to the closing line than the
   opening line is, even if that model has no skill at all. So the real model's CLV is
   compared against a placebo model that is allowed to know the closing line (a strict,
   deliberately cheating benchmark). Only beating the placebo is evidence of skill.
"""
from __future__ import annotations

import json
from itertools import combinations

import numpy as np
import pandas as pd

import lib_engine as E

OUT = E.OUT
BETS = OUT / "bets"


def bin_corr(x: np.ndarray, y: np.ndarray) -> dict:
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    n = len(x)
    r = float(np.corrcoef(x, y)[0, 1]) if n > 2 else np.nan
    # Fisher z confidence interval
    if n > 3 and abs(r) < 1:
        z = np.arctanh(r)
        se = 1 / np.sqrt(n - 3)
        lo, hi = np.tanh(z - 1.96 * se), np.tanh(z + 1.96 * se)
    else:
        lo = hi = np.nan
    return {"r": round(r, 4), "n": int(n), "ci95": [round(float(lo), 4), round(float(hi), 4)]}


def main() -> int:
    l = pd.read_csv(OUT / "own_lines.csv")
    g = l[(l.season >= E.EVAL_FIRST_SEASON) & l.result.notna() & l.spread_line.notna()].copy()
    g["home_covers"] = (g.result > g.spread_line).astype(float)
    g["under"] = (g.total < g.total_line).astype(float)
    g["over"] = (g.total > g.total_line).astype(float)
    g["home_win"] = (g.result > 0).astype(float)
    g["fav_covers"] = np.where(g.spread_line > 0, g.home_covers, 1 - g.home_covers)
    g["big_fav"] = g.spread_line.abs() >= 3
    g["home_implied_team_total"] = g.total_line / 2 + g.spread_line / 2
    g["away_implied_team_total"] = g.total_line / 2 - g.spread_line / 2
    g["margin_resid"] = g.result - g.spread_line
    g["total_resid"] = g.total - g.total_line

    # ---------------------------------------------------------------- A. outcome correlation
    outcome = {
        "home_cover_vs_over": bin_corr(g.home_covers.to_numpy(), g.over.to_numpy()),
        "home_cover_vs_under": bin_corr(g.home_covers.to_numpy(), g.under.to_numpy()),
        "home_moneyline_vs_over": bin_corr(g.home_win.to_numpy(), g.over.to_numpy()),
        "favorite_covers_vs_over": bin_corr(g.fav_covers.to_numpy(), g.over.to_numpy()),
        "favorite_covers_vs_over_big_fav": bin_corr(
            g.loc[g.big_fav, "fav_covers"].to_numpy(), g.loc[g.big_fav, "over"].to_numpy()),
        "favorite_covers_vs_over_small_line": bin_corr(
            g.loc[~g.big_fav, "fav_covers"].to_numpy(), g.loc[~g.big_fav, "over"].to_numpy()),
        "home_score_vs_away_score": bin_corr(g.home_score.to_numpy(), g.away_score.to_numpy()),
        "margin_resid_vs_total_resid": bin_corr(g.margin_resid.to_numpy(), g.total_resid.to_numpy()),
        "own_margin_error_vs_own_total_error": bin_corr(
            (g.result - g.model_margin).to_numpy(), (g.total - g.model_total).to_numpy()),
        "own_margin_error_vs_market_margin_error": bin_corr(
            (g.result - g.model_margin).to_numpy(), (g.result - g.spread_line).to_numpy()),
    }

    # joint vs independent probability for a same-game spread+total parlay
    joint = float(((g.home_covers == 1) & (g.over == 1)).mean())
    indep = float(g.home_covers.mean() * g.over.mean())
    sgp_pricing_error = {
        "p_home_covers": round(float(g.home_covers.mean()), 4),
        "p_over": round(float(g.over.mean()), 4),
        "p_joint_empirical": round(joint, 4),
        "p_joint_if_independent": round(indep, 4),
        "absolute_error_of_independence_pct": round((joint - indep) * 100, 3),
        "implied_edge_on_a_parlay_pct": round((joint - indep) / indep * 100, 3),
        "n_games": int(len(g)),
    }

    # ------------------------------------------------------------ B. strategy return correlation
    frames = {}
    for p in sorted(BETS.glob("*.csv")):
        d = pd.read_csv(p)
        d = d[d.outcome.isin(["win", "loss", "push"])]
        if len(d) < 100:
            continue
        # per-week ROI series, which is the unit a staking plan actually experiences
        wk = d.groupby(["season", "week"]).apply(
            lambda x: x.profit.sum() / max(x.stake.sum(), 1e-9), include_groups=False)
        frames[p.stem] = wk
    wide = pd.DataFrame(frames).dropna(how="all")
    corr = wide.corr(min_periods=100)
    pairs = []
    ids = list(wide.columns)
    for a, b in combinations(ids, 2):
        r = corr.loc[a, b]
        overlap = int(wide[[a, b]].dropna().shape[0])
        if np.isfinite(r):
            pairs.append({"a": a, "b": b, "r": round(float(r), 4), "n_weeks": overlap})
    pairs.sort(key=lambda d: -abs(d["r"]))

    # ------------------------------------------------------------------ C. CLV bias control
    opens = pd.read_csv(OUT / "bets" / "S09.csv") if (BETS / "S09.csv").exists() else pd.DataFrame()
    clv_block = {}
    if len(opens) > 100:
        real_clv = float(opens.clv_points.mean())
        real_t = float(
            opens.clv_points.mean() / (opens.clv_points.std(ddof=1) / np.sqrt(len(opens))))
        # placebo: a model that is allowed to see the closing line and is exactly as noisy as
        # the real model is. It has an unfair information advantage, so beating it is a strong
        # test.
        gg = g.dropna(subset=["open_line"] if "open_line" in g.columns else [])
        sub = l[(l.season >= 2013) & l.season <= 2021].dropna(subset=["spread_line"]).copy()
        sub = sub.merge(pd.read_csv(BETS / "S09.csv")[["game_id", "open_line"]],
                        on="game_id", how="inner")
        # the placebo must be exactly as close to the closing line as the real model is (that
        # distance is what generates the mechanical CLV), so the noise scale is matched to
        # sd(model - close), not to the forecast error of the result
        sigma = float(np.std(sub.model_margin - sub.spread_line, ddof=1))
        rng = np.random.default_rng(20261106)
        # control that the estimator is unbiased: noise around the OPENING line must give ~0
        open_placebo = []
        for _ in range(200):
            fake_model = (-sub.open_line.to_numpy()) + rng.normal(0, sigma, len(sub))
            edge_o = fake_model - (-sub.open_line.to_numpy())
            sel_o = np.abs(edge_o) >= 2.0
            if sel_o.sum() < 50:
                continue
            move_o = (sub.spread_line.to_numpy()[sel_o] - (-sub.open_line.to_numpy()[sel_o]))
            open_placebo.append(float((move_o * np.sign(edge_o[sel_o])).mean()))
        placebo = []
        for _ in range(400):
            fake_model = sub.spread_line.to_numpy() + rng.normal(0, sigma, len(sub))
            edge = fake_model - (-sub.open_line.to_numpy())
            sel = np.abs(edge) >= 2.0
            if sel.sum() < 50:
                continue
            direction = np.sign(edge[sel])
            move = (sub.spread_line.to_numpy()[sel] - (-sub.open_line.to_numpy()[sel]))
            placebo.append(float((move * direction).mean()))
        placebo = np.array(placebo)
        clv_block = {
            "n_selected_bets": int(len(opens)),
            "real_model_clv_points": round(real_clv, 4),
            "real_model_clv_t": round(real_t, 3),
            "placebo_clv_mean_points": round(float(placebo.mean()), 4),
            "placebo_clv_ci90": [round(float(np.percentile(placebo, 5)), 4),
                                 round(float(np.percentile(placebo, 95)), 4)],
            "placebo_model_sigma": round(sigma, 3),
            "open_noise_control_mean_points": round(float(np.mean(open_placebo)), 4),
            "open_noise_control_note": (
                "Same estimator with noise placed around the OPENING line instead of the closing "
                "line. This must be ~0; it is the check that the placebo comparison is unbiased."),
            "corr_model_minus_close_vs_move": round(float(np.corrcoef(
                sub.model_margin - sub.spread_line, sub.spread_line + sub.open_line)[0, 1]), 4),
            "distance_model_to_close_sd": round(
                float(np.std(sub.model_margin - sub.spread_line, ddof=1)), 3),
            "placebo_definition": (
                "placebo_model = closing_line + Normal(0, sd(model - close)). It therefore sees "
                "the closing line and reproduces the real model's distance from it exactly, "
                "while carrying zero information about the game or about the line move."),
            "verdict": ("real model beats the cheating placebo"
                        if real_clv > float(np.percentile(placebo, 95))
                        else "indistinguishable from the placebo - CLV here is mostly the "
                             "mechanical pull toward the closing line"),
            "interpretation": (
                "The placebo knows the closing line and is only as noisy as the real model, so it "
                "gets the 'model is closer to the close than the opener' effect for free. If the "
                "real model's CLV is inside the placebo range, the CLV number is not evidence of "
                "forecasting skill."),
        }

    # ------------------------------------------- D. prop / team-level leg correlation examples
    g["home_team_total_over"] = (g.home_score > g.home_implied_team_total).astype(float)
    g["away_team_total_over"] = (g.away_score > g.away_implied_team_total).astype(float)
    prop_like = {
        "home_team_over_vs_away_team_over": bin_corr(
            g.home_team_total_over.to_numpy(), g.away_team_total_over.to_numpy()),
        "home_team_over_vs_game_over": bin_corr(
            g.home_team_total_over.to_numpy(), g.over.to_numpy()),
        "home_team_over_vs_home_moneyline": bin_corr(
            g.home_team_total_over.to_numpy(), g.home_win.to_numpy()),
        "home_score_vs_game_total": bin_corr(g.home_score.to_numpy(), g.total.to_numpy()),
    }
    p1 = float(g.home_team_total_over.mean())
    p2 = float(g.over.mean())
    r_hg = float(prop_like["home_team_over_vs_game_over"]["r"])
    example = {
        "p_leg1_home_team_over": round(p1, 4),
        "p_leg2_game_over": round(p2, 4),
        "rho": round(r_hg, 4),
        "p_joint_if_independent": round(p1 * p2, 4),
        "p_joint_correlated": round(
            p1 * p2 + r_hg * np.sqrt(p1 * (1 - p1) * p2 * (1 - p2)), 4),
        "note": ("Binary-leg joint probability: P(A and B) = pA*pB + rho*sqrt(pA(1-pA)pB(1-pB)). "
                 "This is the formula a prop-combo price has to be checked against."),
    }

    payload = {
        "generated_at_utc": E.MANIFEST["generated_at_utc"],
        "source_commit_sha": E.MANIFEST["commit_sha"],
        "outcome_correlations": outcome,
        "sgp_pricing_error": sgp_pricing_error,
        "strategy_return_correlations": {
            "n_strategies": len(ids),
            "n_week_observations": int(len(wide)),
            "strongest_pairs": pairs[:12],
            "weakest_pairs": pairs[-6:],
            "mean_abs_pairwise_r": round(float(np.nanmean([abs(p["r"]) for p in pairs])), 4),
            "matrix": {a: {b: (None if not np.isfinite(corr.loc[a, b]) else round(float(corr.loc[a, b]), 3))
                           for b in ids} for a in ids},
        },
        "clv_bias_control": clv_block,
        "prop_leg_correlations": prop_like,
        "prop_combo_example": example,
    }
    (OUT / "correlation.json").write_text(json.dumps(payload, indent=2) + "\n")

    print("outcome correlations:")
    for k, v in outcome.items():
        print(f"  {k}: r={v['r']} n={v['n']} ci={v['ci95']}")
    print("SGP pricing error:", sgp_pricing_error)
    print("CLV control:", {k: clv_block.get(k) for k in
                           ["real_model_clv_points", "real_model_clv_t",
                            "placebo_clv_mean_points", "placebo_clv_ci90", "verdict"]})
    print("strongest strategy pairs:", pairs[:4])
    print("mean |r| across strategies:", payload["strategy_return_correlations"]["mean_abs_pairwise_r"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
