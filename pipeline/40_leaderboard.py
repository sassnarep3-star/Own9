#!/usr/bin/env python3
"""T11 - Leaderboard scoring and reward allocation.

Scoring philosophy: rank on the luck-adjusted effect size, not on raw ROI. Raw ROI over a few
hundred bets is mostly noise, so the ranking uses

    score = shrunk_ROI * (gates passed / gates applicable)

where shrunk_ROI = ROI * t^2 / (1 + t^2) is the posterior mean of the edge under a
unit-information prior centred on zero. A strategy with a big ROI and a tiny t-stat shrinks to
almost nothing, which is exactly the point.

Rewards: a 1,000-point allocation pool. Points are only paid to strategies that clear every
applicable gate. If nothing clears, the pool is recorded as unallocated (escrowed) and the rules
for the next cycle are published instead of paying a lucky strategy.
"""
from __future__ import annotations

import json

import pandas as pd

import lib_engine as E

OUT = E.OUT
POOL = 1000.0
MAX_SHARE = 0.40


def main() -> int:
    gates = json.loads((OUT / "gates.json").read_text())
    corr = json.loads((OUT / "correlation.json").read_text())
    strategies = json.loads((OUT / "strategies.json").read_text())

    rows = [r for r in gates["strategies"] if r.get("gates_passed") is not None]
    for r in rows:
        r["luck_share_pct"] = (
            round(100 * (1 - (r["shrunk_roi_pct"] / r["roi_pct"])), 2)
            if r.get("roi_pct") not in (None, 0) and r.get("shrunk_roi_pct") is not None
            else None
        )
    rows.sort(key=lambda r: (-(r.get("score") or 0), -(r.get("gates_passed") or 0), -(r["n_bets"])))

    for i, r in enumerate(rows, start=1):
        r["rank"] = i

    passers = [r for r in rows if r["status"] == "pass"]
    watch = [r for r in rows if r["status"] == "partial"]

    # reward allocation among passers, score-proportional with a per-strategy cap
    rewards = []
    if passers:
        total = sum(max(r["score"], 0.0) for r in passers)
        for r in passers:
            share = max(r["score"], 0.0) / total if total > 0 else 1 / len(passers)
            share = min(share, MAX_SHARE)
            rewards.append({"id": r["id"], "points": round(POOL * share, 2)})
        paid = sum(x["points"] for x in rewards)
        unallocated = round(POOL - paid, 2)
    else:
        unallocated = POOL

    for r in rows:
        r["reward_points"] = next((x["points"] for x in rewards if x["id"] == r["id"]), 0.0)

    tiers = []
    for r in rows:
        if r["status"] == "pass":
            r["tier"] = "Gold - cleared every gate"
        elif r["status"] == "partial":
            r["tier"] = "Silver - watchlist (gates cleared, significance not reached)"
        elif r["roi_pct"] is not None and r["roi_pct"] > 0:
            r["tier"] = "Bronze - positive ROI, not significant"
        else:
            r["tier"] = "Unranked - no demonstrated edge"
        tiers.append({"id": r["id"], "tier": r["tier"]})

    portfolio = {
        "n_strategies": len(rows),
        "n_passed_all_gates": len(passers),
        "n_watchlist": len(watch),
        "n_fdr_rejections": gates["method"]["rejections"],
        "aggregate_profit_units_all_strategies": round(sum(r["profit_units"] for r in rows), 2),
        "aggregate_staked_units": round(sum(r["staked_units"] for r in rows), 2),
        "mean_abs_strategy_correlation": corr["strategy_return_correlations"]["mean_abs_pairwise_r"],
    }

    payload = {
        "generated_at_utc": E.MANIFEST["generated_at_utc"],
        "source_commit_sha": E.MANIFEST["commit_sha"],
        "pool_points": POOL,
        "max_share_per_strategy": MAX_SHARE,
        "reward_rules": [
            "Only strategies that clear every applicable validation gate are paid.",
            "The 1,000-point pool is split in proportion to the luck-adjusted score.",
            "No single strategy may take more than 40% of the pool (concentration cap).",
            "If no strategy clears the gates, the pool is escrowed and rolls into the next cycle.",
            "Points are an internal research budget, not money and not a stake recommendation.",
        ],
        "rewards": rewards,
        "unallocated_points": unallocated,
        "tiers": tiers,
        "portfolio": portfolio,
        "leaderboard": rows,
    }
    (OUT / "leaderboard.json").write_text(json.dumps(payload, indent=2) + "\n")

    tbl = pd.DataFrame(rows)[["rank", "id", "n_bets", "roi_pct", "shrunk_roi_pct", "t_stat",
                              "gates_passed", "status", "score", "reward_points"]]
    print(tbl.to_string(index=False))
    print(f"\npassed all gates: {len(passers)} | watchlist: {len(watch)} | "
          f"pool unallocated: {unallocated}")
    print("portfolio:", portfolio)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
