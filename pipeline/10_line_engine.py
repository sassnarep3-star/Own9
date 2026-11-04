#!/usr/bin/env python3
"""T05 - Line origination: build the OWN9 spread / total / moneyline for every game.

Pipeline
  1. tune Elo+ridge hyper-parameters on the 1999-2005 warm-up window (cached in
     outputs/model_params.json; no evaluation season ever informs the parameters).
  2. walk-forward predict every regular-season game 1999-2026 (state only from earlier games).
  3. blend the three margin models and two total models with non-negative least squares,
     weights fitted on the warm-up window only.
  4. score the origination quality out-of-sample against the market line and against the result.
  5. emit the live board for games that have not kicked off yet (2026 weeks 9-10).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy import stats

import lib_engine as E

OUT = E.OUT
PARAM_FILE = OUT / "model_params.json"


def get_params(warm: pd.DataFrame) -> tuple[E.Params, dict]:
    if PARAM_FILE.exists():
        d = json.loads(PARAM_FILE.read_text())
        return E.Params(**d["params"]), d
    params, info = E.tune(warm)
    OUT.mkdir(exist_ok=True)
    PARAM_FILE.write_text(json.dumps(info, indent=2) + "\n")
    return params, info


def _week_buckets(d: pd.DataFrame) -> list[dict]:
    buckets = [(1, 2, "weeks 1-2"), (3, 4, "weeks 3-4"), (5, 8, "weeks 5-8"),
               (9, 13, "weeks 9-13"), (14, 18, "weeks 14-18")]
    out = []
    for lo, hi, label in buckets:
        b = d[(d.week >= lo) & (d.week <= hi)]
        if len(b) == 0:
            continue
        out.append({
            "bucket": label, "n": int(len(b)),
            "mae_model": round(float((b.result - b.model_margin).abs().mean()), 3),
            "mae_market": round(float((b.result - b.market_margin).abs().mean()), 3),
            "mean_abs_edge": round(float(b.edge_margin.abs().mean()), 3),
        })
    return out


def main() -> int:
    games = E.load_games()
    warm = games[(games.season >= E.WARMUP_SEASONS[0]) & (games.season <= E.WARMUP_SEASONS[1])]
    params, tune_info = get_params(warm)

    wf = E.run_walk_forward(params, games)

    # calibration, blend weights and residual scale are all fitted on the warm-up window only
    wf_warm = wf[(wf.season >= E.WARMUP_SEASONS[0]) & (wf.season <= E.WARMUP_SEASONS[1])]
    calib = E.fit_calibration(wf_warm)
    w = E.fit_blend(wf_warm, calib)
    sigma_margin, sigma_total = E.fit_scale(wf_warm, calib, w)
    lines = E.apply_model(wf, calib, w, sigma_margin, sigma_total)
    lines["market_margin"] = lines.spread_line
    lines["edge_margin"] = lines.model_margin - lines.market_margin
    lines["edge_total"] = lines.model_total - lines.total_line
    lines["model_error"] = lines.result - lines.model_margin
    lines["market_error"] = lines.result - lines.market_margin
    lines["is_completed"] = lines.result.notna().astype(int)

    lines.to_csv(OUT / "own_lines.csv", index=False)

    # ------------------------------------------------------------------ accuracy scoring
    ev = lines[(lines.season >= E.EVAL_FIRST_SEASON) & lines.result.notna()]
    rows = []
    for season, d in ev.groupby("season"):
        dm = d.dropna(subset=["market_margin"])
        rows.append({
            "season": int(season),
            "n_games": int(len(d)),
            "mae_model": round(float((d.result - d.model_margin).abs().mean()), 3),
            "mae_market": round(float((dm.result - dm.market_margin).abs().mean()), 3) if len(dm) else None,
            "rmse_model": round(float(np.sqrt(((d.result - d.model_margin) ** 2).mean())), 3),
            "rmse_market": round(float(np.sqrt(((dm.result - dm.market_margin) ** 2).mean())), 3) if len(dm) else None,
            "mae_total_model": round(float((d.total - d.model_total).abs().mean()), 3),
            "mae_total_market": round(float((dm.total - dm.total_line).abs().mean()), 3) if len(dm) else None,
            "corr_model_result": round(float(np.corrcoef(d.model_margin, d.result)[0, 1]), 4),
            "corr_market_result": round(float(np.corrcoef(dm.market_margin, dm.result)[0, 1]), 4) if len(dm) > 2 else None,
        })
    by_season = pd.DataFrame(rows)

    # ------------------------------------------------- market-anchored production line
    from scipy.optimize import nnls as _nnls
    warm_m = wf_warm.dropna(subset=["result", "market_margin", "model_margin"]) if "market_margin" in wf_warm else None
    if warm_m is None or len(warm_m) < 100:
        wf_warm = E.apply_model(wf_warm, calib, w, sigma_margin, sigma_total)
        wf_warm["market_margin"] = wf_warm.spread_line
        warm_m = wf_warm.dropna(subset=["result", "market_margin", "model_margin"])
    Xa = np.column_stack([warm_m.market_margin, warm_m.model_margin])
    wa, _ = _nnls(Xa, warm_m.result.to_numpy(dtype=float))
    alpha = float(wa[0] / wa.sum()) if wa.sum() > 0 else 1.0
    lines["anchored_margin"] = alpha * lines.market_margin + (1 - alpha) * lines.model_margin
    ev = lines[(lines.season >= E.EVAL_FIRST_SEASON) & lines.result.notna()]
    dm = ev.dropna(subset=["market_margin"])
    # does the own line add information on top of the market line?
    X = np.column_stack([np.ones(len(dm)), dm.market_margin, dm.model_margin])
    beta, *_ = np.linalg.lstsq(X, dm.result.to_numpy(), rcond=None)
    resid = dm.result.to_numpy() - X @ beta
    se = np.sqrt(np.diag(np.linalg.inv(X.T @ X) * (resid @ resid) / (len(dm) - X.shape[1])))
    t_model_increment = float(beta[2] / se[2])

    combo = 0.5 * dm.market_margin + 0.5 * dm.model_margin
    acc = {
        "eval_window": [int(E.EVAL_FIRST_SEASON), int(lines.season.max())],
        "n_games_eval": int(len(ev)),
        "n_games_with_market": int(len(dm)),
        "mae_model_spread": round(float((ev.result - ev.model_margin).abs().mean()), 3),
        "mae_market_spread": round(float((dm.result - dm.market_margin).abs().mean()), 3),
        "rmse_model_spread": round(float(np.sqrt(((ev.result - ev.model_margin) ** 2).mean())), 3),
        "rmse_market_spread": round(float(np.sqrt(((dm.result - dm.market_margin) ** 2).mean())), 3),
        "mae_total_model": round(float((ev.total - ev.model_total).abs().mean()), 3),
        "mae_total_market": round(float((dm.total - dm.total_line).abs().mean()), 3),
        "corr_model_result": round(float(np.corrcoef(ev.model_margin, ev.result)[0, 1]), 4),
        "corr_market_result": round(float(np.corrcoef(dm.market_margin, dm.result)[0, 1]), 4),
        "regression_result_on_market_and_model": {
            "intercept": round(float(beta[0]), 4),
            "coef_market": round(float(beta[1]), 4),
            "coef_model_increment": round(float(beta[2]), 4),
            "t_stat_model_increment": round(t_model_increment, 3),
            "note": ("A t-stat below ~2 means the own line does not add statistically detectable "
                     "information beyond the market line; it does NOT mean the line is useless, "
                     "only that the market is hard to beat."),
        },
        "mae_50_50_blend": round(float((dm.result - combo).abs().mean()), 3),
        "anchored": {
            "alpha_market_weight": round(alpha, 4),
            "note": ("alpha fitted on the 1999-2005 warm-up window only: anchored_line = "
                     "alpha*market_line + (1-alpha)*own_line"),
            "mae_anchored": round(float((dm.result - (alpha * dm.market_margin + (1 - alpha) * dm.model_margin)).abs().mean()), 3),
        },
        "mae_by_week_bucket": _week_buckets(dm),
        "edge_margin_sd": round(float(ev.edge_margin.std()), 3),
        "share_games_edge_ge_2": round(float((ev.edge_margin.abs() >= 2).mean()), 4),
        "share_games_edge_ge_3_5": round(float((ev.edge_margin.abs() >= 3.5).mean()), 4),
        "sigma_margin": round(sigma_margin, 3),
        "sigma_total": round(sigma_total, 3),
        "blend_weights": w,
        "calibration": calib,
        "tuning": tune_info,
        "params": params.__dict__,
    }
    (OUT / "line_accuracy.json").write_text(json.dumps(acc, indent=2) + "\n")
    by_season.to_csv(OUT / "line_accuracy_by_season.csv", index=False)

    # ------------------------------------------------------------------- live board
    live = lines[lines.is_completed == 0].copy()
    board = live[[
        "game_id", "season", "week", "gameday", "away_team", "home_team",
        "model_margin", "model_total", "model_home_win_prob",
        "spread_line", "total_line", "home_moneyline", "away_moneyline",
        "edge_margin", "edge_total",
    ]].copy()
    board["status"] = np.where(board.spread_line.notna(), "market_line_present", "market_line_blank")
    board["model_home_line"] = -board.model_margin.round(1)  # home team's handicap, book style
    board = board.sort_values(["week", "gameday", "game_id"])
    board.to_csv(OUT / "live_board.csv", index=False)

    print(json.dumps({k: acc[k] for k in [
        "n_games_eval", "n_games_with_market", "mae_model_spread", "mae_market_spread",
        "mae_total_model", "mae_total_market", "mae_50_50_blend"]}, indent=1))
    print("t-stat model increment:", acc["regression_result_on_market_and_model"]["t_stat_model_increment"])
    print("blend:", w, "sigma:", round(sigma_margin, 2), round(sigma_total, 2))
    print("live board games:", len(board), "with market:", int(board.spread_line.notna().sum()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
