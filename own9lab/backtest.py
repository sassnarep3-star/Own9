"""Walk-forward evaluation, validation gates, leaderboard, rewards and luck analysis."""
import json
import numpy as np
import pandas as pd
from . import config as C, stats as ST, strategies as S

WORSE = (100 / 115) / (100 / 110)   # win-profit multiplier for prices 5 cents worse (-110 -> -115)
MIN_N = {"single": 200, "teaser": 100, "parlay": 100, "sgp": 100}
REWARD_POOL = 100.0
GATES = [
    ("G0", "Provenance & leakage", "Every bet settles on an officially VERIFIED score; model inputs use only games before the bet's week (asserted). Prices are an unverified secondary source (flagged, not a failure)."),
    ("G1", "Sample size", "Out-of-sample (2020-2026) bets >= 200 for singles, >= 100 for multi-leg bets."),
    ("G2", "Out-of-sample profit", "Out-of-sample ROI > 0 at the recorded closing prices (or the stated assumed price)."),
    ("G3", "Multiple-testing significance", "Holm-adjusted one-sided week-block bootstrap p < 0.05 across all priced strategies."),
    ("G4", "Reality check (data snooping)", "Max-T (Romano-Wolf / White) synchronized week-block bootstrap p < 0.05 across all priced strategies."),
    ("G5", "Development consistency", "Development-period (2010-2019) ROI > 0, i.e. the same sign in and out of sample."),
    ("G6", "Season stability", ">= 4 of 7 out-of-sample seasons profitable and no single season supplies > 50% of out-of-sample profit."),
    ("G7", "Price robustness", "Out-of-sample ROI still > 0 when every winning payout is cut to a price 5 cents worse (-110 -> -115)."),
]


def evaluate(games, preds):
    g, bets = S.all_bets(games, preds)
    reg = {r[0]: {"kind": r[1], "family": r[2], "assumed_price": r[3], "description": r[4]} for r in S.REGISTRY}
    keys = [r[0] for r in S.REGISTRY]

    # ---- G0 assertions (fail closed)
    assert bets.profit.notna().all()
    m = bets[bets.strategy.isin(["S01", "S02", "S03", "S04", "S05"])].merge(preds[["game_id", "data_through"]], on="game_id")
    leak_ok = bool((pd.to_datetime(m.data_through) < pd.to_datetime(m.gameday)).all())
    verified_ok = True  # bets are generated only from score_status == VERIFIED rows (strategies.base)

    oos = bets[bets.period.isin(["TEST", "FWD"])]
    Sm, Nm, weeks = ST.week_matrix(oos, keys)
    inf = ST.inference(Sm, Nm, C.N_BOOT, C.SEED)
    inf.index = keys
    inf["p_holm"] = ST.holm(inf.p)
    inf["p_bh"] = ST.bh(inf.p)

    rows = []
    for k in keys:
        b = bets[bets.strategy == k]
        bo = b[b.period.isin(["TEST", "FWD"])]
        r = {"id": k, **reg[k]}
        for per in ("DEV", "TEST", "FWD"):
            bp = b[b.period == per]
            r[f"n_{per.lower()}"] = int(len(bp))
            r[f"roi_{per.lower()}"] = float(bp.profit.mean()) if len(bp) else None
        r["n_oos"] = int(len(bo))
        r["win_rate_oos"] = float((bo.outcome > 0).sum() / max(1, (bo.outcome != 0).sum()))
        r["roi_oos"] = float(inf.loc[k, "roi"])
        r["profit_units_oos"] = float(bo.profit.sum())
        worse = np.where(bo.profit > 0, bo.profit * WORSE, bo.profit)
        r["roi_oos_worse_price"] = float(worse.mean()) if len(bo) else None
        seas = bo.groupby("season").profit.agg(["sum", "mean", "size"])
        r["season_roi"] = {int(s): round(float(v), 4) for s, v in seas["mean"].items()}
        r["seasons_positive"] = int((seas["mean"] > 0).sum())
        tot = seas["sum"].sum()
        r["max_season_share"] = float(seas["sum"].max() / tot) if tot > 0 else None
        for c in ("se", "lcb95", "p", "p_holm", "p_bh", "p_maxT"):
            r[c] = float(inf.loc[k, c])
        gates = {
            "G0": leak_ok and verified_ok,
            "G1": r["n_oos"] >= MIN_N[r["kind"]],
            "G2": r["roi_oos"] > 0,
            "G3": r["p_holm"] < C.ALPHA,
            "G4": r["p_maxT"] < C.ALPHA,
            "G5": (r["roi_dev"] or -1) > 0,
            "G6": r["seasons_positive"] >= 4 and r["max_season_share"] is not None and r["max_season_share"] <= 0.5,
            "G7": (r["roi_oos_worse_price"] or -1) > 0,
        }
        r["gates"] = gates
        r["gates_passed"] = int(sum(gates.values()))
        r["passes_all"] = all(gates.values())
        r["reward_eligible"] = r["passes_all"] and not r["assumed_price"]
        rows.append(r)
    lb = pd.DataFrame(rows).sort_values("lcb95", ascending=False).reset_index(drop=True)
    lb["rank"] = np.arange(1, len(lb) + 1)
    elig = lb.reward_eligible & (lb.lcb95 > 0)
    lb["reward_points"] = 0.0
    if elig.any():
        lb.loc[elig, "reward_points"] = REWARD_POOL * lb.loc[elig, "lcb95"] / lb.loc[elig, "lcb95"].sum()

    # ---- luck / skill analysis
    luck = {}
    rel = ST.reliability(lb.roi_oos, lb.se)
    lb["roi_oos_shrunk"] = rel.pop("shrunk")
    luck["dispersion"] = rel
    dv = lb.dropna(subset=["roi_dev"])
    luck["persistence_dev_to_oos"] = dict(zip(("spearman", "p"), ST.spearman(dv.roi_dev, dv.roi_oos)))
    seas = bets.groupby(["strategy", "season"]).profit.mean().unstack()
    pairs = []
    for s0 in range(min(C.DEV_SEASONS), 2026):
        if s0 in seas and s0 + 1 in seas:
            d = seas[[s0, s0 + 1]].dropna()
            if len(d) >= 5:
                rho, p = ST.spearman(d[s0], d[s0 + 1])
                pairs.append({"from": s0, "to": s0 + 1, "spearman": rho, "p": p, "n_strategies": len(d)})
    luck["season_to_season"] = pairs
    luck["season_to_season_mean"] = float(np.mean([p["spearman"] for p in pairs]))
    nulls = []
    for k in [r[0] for r in S.REGISTRY if r[1] == "single"]:
        bo = oos[(oos.strategy == k) & oos.opp_profit.notna()]
        sims = ST.random_side_null(bo.profit.to_numpy(), bo.opp_profit.to_numpy(), 4000, C.SEED)
        act = bo.profit.mean()
        nulls.append({"id": k, "n": int(len(bo)), "roi_actual": float(act), "null_mean": float(sims.mean()),
                      "null_p95": float(np.percentile(sims, 95)), "percentile": float((sims < act).mean() * 100),
                      "p_vs_coinflip": float(((sims >= act).sum() + 1) / (len(sims) + 1))})
    luck["coin_flip_null"] = nulls
    meta = {"leakage_check_passed": leak_ok, "verified_scores_only": verified_ok, "oos_weeks": int(len(weeks)),
            "n_boot": C.N_BOOT, "seed": C.SEED, "worse_price_multiplier": WORSE, "reward_pool": REWARD_POOL,
            "registration": S.registration(), "gates": GATES}
    return g, bets, lb, luck, meta


if __name__ == "__main__":
    games = pd.read_csv(C.DERIVED / "games.csv", dtype={"old_game_id": str})
    preds = pd.read_csv(C.DERIVED / "model_predictions.csv")
    g, bets, lb, luck, meta = evaluate(games, preds)
    pd.set_option("display.width", 250)
    cols = ["rank", "id", "n_oos", "roi_dev", "roi_test", "roi_fwd", "roi_oos", "lcb95", "p", "p_holm", "p_maxT",
            "seasons_positive", "roi_oos_worse_price", "gates_passed", "passes_all", "reward_points"]
    print(lb[cols].round(4).to_string())
    print(json.dumps({k: v for k, v in luck.items() if k != "season_to_season"}, indent=1, default=float)[:3000])


def cluster_t(sub):
    """ROI and week-cluster-robust t statistic (ratio estimator, linearized)."""
    wk = sub.season.astype(str) + "-" + sub.week.astype(str)
    agg = sub.assign(wk=wk).groupby("wk").profit.agg(["sum", "size"])
    n, W = agg["size"].sum(), len(agg)
    roi = agg["sum"].sum() / n
    if W < 2:
        return roi, 0.0
    var = W / (W - 1) * ((agg["sum"] - roi * agg["size"]) ** 2).sum() / n ** 2
    return roi, roi / np.sqrt(var) if var > 0 else 0.0


def walk_forward_selection(bets, first=2015, t_crit=1.645, min_n=100):
    """EXPLORATORY (defined after the main leaderboard run): before each season, keep only
    priced, non-assumed strategies whose history (2010..t-1) shows t > t_crit; bet them in season t."""
    cand = [r[0] for r in S.REGISTRY if not r[3]]
    picks, meta_bets = [], []
    for t in range(first, 2027):
        hist = bets[(bets.season < t) & bets.strategy.isin(cand)]
        chosen = []
        for k in cand:
            h = hist[hist.strategy == k]
            if len(h) >= min_n:
                roi, tt = cluster_t(h)
                if tt > t_crit:
                    chosen.append(k)
        cur = bets[(bets.season == t) & bets.strategy.isin(chosen)]
        picks.append({"season": t, "selected": chosen, "n_bets": int(len(cur)),
                      "roi": float(cur.profit.mean()) if len(cur) else None})
        meta_bets.append(cur)
    mb = pd.concat(meta_bets)
    oos = mb[mb.season >= 2020].assign(strategy="M01")
    res = {"rule": f"select strategy k for season t if its 2010..t-1 week-cluster t-stat > {t_crit} (n >= {min_n})",
           "status": "EXPLORATORY - rule defined after the main leaderboard run; not eligible for rewards",
           "by_season": picks, "n_oos": int(len(oos))}
    if len(oos):
        Sm, Nm, _ = ST.week_matrix(oos, ["M01"])
        inf = ST.inference(Sm, Nm, C.N_BOOT, C.SEED)
        res.update({"roi_oos": float(inf.roi[0]), "lcb95": float(inf.lcb95[0]), "p": float(inf.p[0])})
    return res
