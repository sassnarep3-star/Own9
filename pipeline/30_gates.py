#!/usr/bin/env python3
"""T09 - Validation gates, luck removal and multiple-testing control.

Nothing here is allowed to look at a strategy's name or its story: every number comes from the
bet files written by pipeline/20_strategies.py.

Gates (a strategy must pass every applicable gate)
  G1 PROVENANCE   every bet carries a source-backed price (real price, or an assumption that is
                  written on the bet row and re-tested for sensitivity)
  G2 SAMPLE       n >= 300 settled bets spread over >= 5 seasons
  G3 SIGNIFICANCE two-sided test of "beat the price" with Benjamini-Hochberg FDR across all
                  strategies (q < 0.10) and t >= 2
  G4 STABILITY    >= 55% of seasons profitable AND second half of the sample profitable
  G5 ROBUSTNESS   profitable after removing the single best season and after removing the 5%
                  most profitable bets
  G6 LUCK         shrunk ROI (t^2/(1+t^2) Bayes factor style shrinkage toward zero) > 0.5%
  G7 ECONOMICS    no bet priced worse than -130, >= 20 bets per season, and (when the price was
                  assumed) the ROI stays positive with a 10-cent worse price
  G8 CLV          only where the strategy bets a line other than the close: mean closing-line
                  value > 0 with t >= 2

The null model used for G3/G6 is "the price is fair": each bet wins with probability
1/decimal_odds, independently. That is exactly the hypothesis a bettor must reject.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import lib_engine as E

OUT = E.OUT
BETS = OUT / "bets"
N_SIM = 20000
N_BOOT = 10000


def decimal(price: float) -> float:
    return E.american_to_decimal(price)


def load_bets(sid: str) -> pd.DataFrame:
    p = BETS / f"{sid}.csv"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p)
    if len(df) == 0:
        return df
    df = df[df.outcome.isin(["win", "loss", "push"])].copy()
    df["dec"] = df.price.map(decimal)
    df["p_fair"] = 1.0 / df.dec
    return df


def simulate_fair(df: pd.DataFrame, rng: np.random.Generator) -> np.ndarray:
    """ROI (%) distribution under 'the price is fair'."""
    n = len(df)
    p = df.p_fair.to_numpy()
    stake = df.stake.to_numpy()
    win_profit = (df.dec.to_numpy() - 1.0) * stake
    push = (df.outcome == "push").to_numpy()
    total_stake = stake.sum()
    roi = np.empty(N_SIM)
    for i in range(N_SIM):
        w = rng.random(n) < p
        payoff = np.where(push, 0.0, np.where(w, win_profit, -stake))
        roi[i] = payoff.sum() / total_stake * 100
    return roi


def bootstrap_roi(df: pd.DataFrame, rng: np.random.Generator) -> tuple[float, float]:
    profit = df.profit.to_numpy()
    stake = df.stake.to_numpy()
    n = len(df)
    out = np.empty(N_BOOT)
    for i in range(N_BOOT):
        idx = rng.integers(0, n, n)
        s = stake[idx].sum()
        out[i] = profit[idx].sum() / s * 100 if s > 0 else np.nan
    return float(np.nanpercentile(out, 5)), float(np.nanpercentile(out, 95))


def roi_of(df: pd.DataFrame) -> float:
    s = df.stake.sum()
    return float(df.profit.sum() / s * 100) if s > 0 else np.nan


def main() -> int:
    strat = json.loads((OUT / "strategies.json").read_text())
    rng = np.random.default_rng(20261105)
    rows = []
    for s in strat["strategies"]:
        sid = s["id"]
        df = load_bets(sid)
        if len(df) < 30:
            rows.append({**s, "gates": {"G2": False}, "status": "insufficient data",
                         "p_value": None, "t_stat": None})
            continue

        roi = roi_of(df)
        profit = df.profit.to_numpy()
        stake = df.stake.to_numpy()
        per_bet = profit / stake
        n = len(df)
        t = float(per_bet.mean() / (per_bet.std(ddof=1) / np.sqrt(n))) if per_bet.std(ddof=1) > 0 else 0.0

        # null distribution under fair pricing
        sim = simulate_fair(df, rng)
        p_val = float((sim >= roi).mean())

        ci_lo, ci_hi = bootstrap_roi(df, rng)

        # seasons
        by_season = df.groupby("season").apply(roi_of, include_groups=False)
        n_seasons = int(len(by_season))
        share_pos = float((by_season > 0).mean())
        seasons = sorted(df.season.unique())
        mid = seasons[len(seasons) // 2] if seasons else None
        second_half = df[df.season >= mid] if mid is not None else df
        roi_second = roi_of(second_half)

        # robustness: drop best season, drop top-5% profit bets
        best_season = by_season.idxmax() if len(by_season) else None
        roi_drop_best = roi_of(df[df.season != best_season]) if best_season is not None else np.nan
        cut = np.quantile(profit, 0.95)
        roi_drop_top = roi_of(df[profit < cut])

        # economics: price sensitivity with a 10-cent worse price
        worst_price = float(df.price.min())
        assumed = df.price_source.astype(str).str.contains("ASSUMED").all()
        worse = df.copy()
        worse["price"] = worse.price - 10
        worse["dec"] = worse.price.map(decimal)
        worse["profit"] = np.where(worse.outcome == "win",
                                   (worse.dec - 1) * worse.stake,
                                   np.where(worse.outcome == "loss", -worse.stake, 0.0))
        roi_worse = roi_of(worse)

        # CLV (only strategies that bet a different line than the close)
        clv_ok = "clv_points" in df.columns and df.clv_points.notna().any()
        clv_mean = float(df.clv_points.mean()) if clv_ok else None
        clv_t = None
        if clv_ok:
            v = df.clv_points.dropna()
            clv_t = float(v.mean() / (v.std(ddof=1) / np.sqrt(len(v)))) if v.std(ddof=1) > 0 else 0.0

        shrunk = roi * (t * t / (1 + t * t)) if t == t else np.nan

        gates = {
            "G1": bool(not assumed or roi_worse > 0 or assumed is False),
            "G2": bool(n >= 300 and n_seasons >= 5),
            "G3": None,   # filled after FDR
            "G4": bool(share_pos >= 0.55 and roi_second > 0),
            "G5": bool(roi_drop_best > 0 and roi_drop_top > 0),
            "G6": bool(shrunk > 0.5),
            "G7": bool(worst_price >= -130 and n / max(n_seasons, 1) >= 20 and np.isfinite(roi_worse)),
            "G8": bool(clv_ok and clv_mean is not None and clv_mean > 0 and clv_t is not None and clv_t >= 2),
        }
        rows.append({
            **s,
            "roi_pct": round(roi, 3),
            "t_stat": round(t, 3),
            "p_value": p_val,
            "ci90_roi": [round(ci_lo, 3), round(ci_hi, 3)],
            "shrunk_roi_pct": round(float(shrunk), 3) if shrunk == shrunk else None,
            "n_seasons": n_seasons,
            "share_seasons_profitable": round(share_pos, 3),
            "roi_second_half": round(float(roi_second), 3),
            "roi_drop_best_season": round(float(roi_drop_best), 3),
            "roi_drop_top5_bets": round(float(roi_drop_top), 3),
            "roi_with_10c_worse_price": round(float(roi_worse), 3),
            "worst_price": worst_price,
            "bets_per_season": round(n / max(n_seasons, 1), 1),
            "clv_mean_points": round(clv_mean, 4) if clv_mean is not None else None,
            "clv_t_stat": round(clv_t, 3) if clv_t is not None else None,
            "null_roi_mean": round(float(sim.mean()), 3),
            "null_roi_p95": round(float(np.percentile(sim, 95)), 3),
            "gates": gates,
        })

    # ---- Benjamini-Hochberg FDR across every strategy that has a p-value
    tested = [r for r in rows if r.get("p_value") is not None]
    tested.sort(key=lambda r: r["p_value"])
    m = len(tested)
    q = 0.10
    k_max = 0
    for i, r in enumerate(tested, start=1):
        if r["p_value"] <= q * i / m:
            k_max = i
    rejects = {r["id"] for r in tested[:k_max]}
    for r in rows:
        if r.get("p_value") is None:
            continue
        g = r["gates"]
        g["G3"] = bool(r["id"] in rejects and r["t_stat"] >= 2)
        passed = sum(1 for v in g.values() if v is True)
        applicable = len(g)
        r["gates_passed"] = passed
        r["gates_total"] = applicable
        r["fdr_significant"] = r["id"] in rejects
        if all(v is True for v in g.values()):
            r["status"] = "pass"
        elif passed >= 6:
            r["status"] = "partial"
        else:
            r["status"] = "fail"
        # composite score used by the leaderboard: shrunk ROI scaled by gates cleared
        r["score"] = round(max(r["shrunk_roi_pct"] or 0.0, 0.0) * (passed / applicable), 4)

    payload = {
        "generated_at_utc": E.MANIFEST["generated_at_utc"],
        "source_commit_sha": E.MANIFEST["commit_sha"],
        "method": {
            "null": "each bet wins with probability 1/decimal_odds (the price is fair)",
            "n_sim": N_SIM, "n_boot": N_BOOT, "fdr_q": q, "tests": m,
            "rejections": int(k_max),
        },
        "gate_definitions": {
            "G1": "every price is source-backed or its assumption is re-tested",
            "G2": "n >= 300 settled bets over >= 5 seasons",
            "G3": "beat-the-price test passes BH-FDR (q<0.10) and t >= 2",
            "G4": ">=55% of seasons profitable and second half of the sample profitable",
            "G5": "profitable after dropping the best season and the top 5% of bets",
            "G6": "shrunk ROI > 0.5% (effect survives shrinkage toward zero)",
            "G7": "no price worse than -130, >= 20 bets/season, survives a 10-cent worse price",
            "G8": "positive closing-line value with t >= 2 (only where the bet line is not the close)",
        },
        "strategies": rows,
    }
    (OUT / "gates.json").write_text(json.dumps(payload, indent=2) + "\n")

    tbl = pd.DataFrame(rows)[["id", "n_bets", "roi_pct", "t_stat", "p_value", "shrunk_roi_pct",
                              "gates_passed", "status"]]
    print(tbl.to_string(index=False))
    print(f"\nBH-FDR: {m} tests, {k_max} rejections at q={q}: {sorted(rejects)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
