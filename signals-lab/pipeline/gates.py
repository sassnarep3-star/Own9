"""EF-6: validation gates, leaderboard, calibration, point-in-time audit and skill-vs-luck diagnostics.

Run:  python gates.py             -> SEALED evaluation (2023-2025 + 2026 W1-8 forward holdout); run once after registry/PREREGISTRATION.md is committed
      python gates.py --dev-only  -> code smoke test on DEV seasons only, writes to data/results/_dev_only/ (never touches 2023+)
Gate definitions are fixed in registry/PREREGISTRATION.md (thresholds below mirror it exactly).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.linear_model import LogisticRegression

import game_models as gm
import joint
import prop_models as pm
from common import DEV, TEST, FORWARD, american, cluster_boot_skill, holm, load_games, load_team_process, logloss, pinball, verified_seasons
from config import DATA, DERIVED, REGISTRY, RESULTS, VERIFIED

DEV_ONLY = "--dev-only" in sys.argv
SRC = RESULTS / ("_dev_only" if DEV_ONLY else "")
OUT = SRC
EVAL = "dev" if DEV_ONLY else "test"
EVAL_SEASONS = DEV if DEV_ONLY else TEST
# ---- pre-registered thresholds
ALPHA = 0.05; PREC_MAX_HALFWIDTH = 0.03; COV_MEAN_TOL = 0.03; COV_MAX_TOL = 0.06; BOOT_B = 2000; CAL_B = 500
GAME_MODELS = {"G1": "Elo (margin-of-victory, regressed to mean)", "G2": "Time-decayed ridge offense/defense ratings (points)",
               "G3": "Ridge ratings + rest/bye/roof/wind/cold context", "G4": "Ensemble: mean of Elo and G3", "G5": "Process ratings (yards/play + success rate; turnovers excluded)",
               "G6": "Blend: mean of G3 and process G5"}
MKT_NAME = {"ML": "Win probability (fair moneyline)", "SPREAD": "Spread (expected home margin)", "TOTAL": "Total points"}
PROP_NAME = {"PR1": "Shrunk-EWMA x empirical ratio quantiles", "PR2": "Gradient-boosted quantile regression"}
PAIR_NAME = {"QB_x_REC1": "QB passing yds + top receiver yds", "QB_x_REC2": "QB passing yds + 2nd receiver yds", "QB_x_RB1": "QB passing yds + lead RB rushing yds",
             "REC1_x_REC2": "Top receiver + 2nd receiver yds", "MARGIN_x_QB": "Team spread + own QB passing yds", "TOTAL_x_QB": "Game total + QB passing yds",
             "MARGIN_x_RB1": "Team spread + lead RB rushing yds", "QB_x_QB_opp": "Both starting QBs' passing yds", "MARGIN_x_TOTAL": "Home spread + game total (ML-and-over style)"}


def bootstrap_ci(x, B=CAL_B, seed=1):
    rng = np.random.default_rng(seed); n = len(x)
    idx = rng.integers(0, n, size=(B, n)); m = np.asarray(x)[idx].mean(1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def calib_ml(p, y):
    ok = y != 0.5; p = np.asarray(p)[ok]; y = np.asarray(y)[ok]
    x = np.log(np.clip(p, 1e-4, 1 - 1e-4) / (1 - np.clip(p, 1e-4, 1 - 1e-4))).reshape(-1, 1)
    def fit(ix):
        m = LogisticRegression(C=1e6, max_iter=200).fit(x[ix], y[ix]); return m.coef_[0, 0], m.intercept_[0]
    s, i = fit(np.arange(len(y))); rng = np.random.default_rng(2); bs = np.array([fit(rng.integers(0, len(y), len(y))) for _ in range(CAL_B)])
    lo_s, hi_s = np.percentile(bs[:, 0], [2.5, 97.5]); lo_i, hi_i = np.percentile(bs[:, 1], [2.5, 97.5])
    return dict(slope=float(s), slope_lo=float(lo_s), slope_hi=float(hi_s), icpt=float(i), icpt_lo=float(lo_i), icpt_hi=float(hi_i),
                ok=bool(lo_s <= 1 <= hi_s and lo_i <= 0 <= hi_i))


def calib_reg(pred, act):
    pred = np.asarray(pred); act = np.asarray(act); n = len(pred); rng = np.random.default_rng(3)
    def sl(ix): return np.polyfit(pred[ix], act[ix], 1)[0]
    s = sl(np.arange(n)); bs = np.array([sl(rng.integers(0, n, n)) for _ in range(CAL_B)])
    bias = float(np.mean(act - pred)); blo, bhi = bootstrap_ci(act - pred)
    lo_s, hi_s = np.percentile(bs, [2.5, 97.5])
    return dict(slope=float(s), slope_lo=float(lo_s), slope_hi=float(hi_s), bias=bias, bias_lo=blo, bias_hi=bhi, ok=bool(lo_s <= 1 <= hi_s and blo <= 0 <= bhi))


# ----------------------------------------------------------------------------- point-in-time audits (truncation tests)
def audit_games(P: dict, n_blocks: int = 10) -> dict:
    g = load_games(include_2026=not DEV_ONLY, max_season=2022 if DEV_ONLY else None); proc = load_team_process()
    full = gm.run_walkforward(g, P, components=("elo", "ridge", "proc"), proc=proc)
    key = g.groupby(["season", "week"]).date.min().sort_values().reset_index()
    key = key[key.season.isin(EVAL_SEASONS)]
    rng = np.random.default_rng(11); pick = rng.choice(len(key), size=min(n_blocks, len(key)), replace=False)
    cols = [c for c in full.columns if c.endswith(("_margin", "_total", "_p"))]
    bad = 0
    for i in pick:
        s, w, d0 = key.season.iat[i], key.week.iat[i], key.date.iat[i]
        blk = g[(g.season == s) & (g.week == w)]
        # truncation: remove every game strictly after the block's last game date AND hide the block's own outcomes
        g2 = g[(g.date <= blk.date.max())].copy()
        hide = g2.index.isin(blk.index); g2.loc[hide, ["home_score", "away_score", "margin", "total", "home_win"]] = np.nan
        part = gm.run_walkforward(g2, P, components=("elo", "ridge", "proc"), proc=proc)
        a = part[(part.season == s) & (part.week == w)].set_index("game_id")[cols]; b = full[(full.season == s) & (full.week == w)].set_index("game_id")[cols].loc[a.index]
        if not np.allclose(a.to_numpy(float), b.to_numpy(float), equal_nan=True, atol=1e-9): bad += 1
    return dict(blocks_tested=int(len(pick)), mismatches=int(bad), ok=bool(bad == 0))


def audit_props(P: dict, n: int = 300) -> dict:
    D = pm.prepare(2022 if DEV_ONLY else max(TEST), P, P["props"]["ewma_hl"])
    pl = pd.read_csv(DERIVED / "player_games_feed.csv.gz"); pl = pl[pl.game_type == "REG"]
    g = load_games(include_2026=False)[["game_id", "date"]]; pl = pl.merge(g, on="game_id")
    rng = np.random.default_rng(5); bad = 0; tested = 0
    for name, d in D.items():
        mk = pm.MARKETS[name]; e = d[d.eligible & d.season.isin(EVAL_SEASONS)]
        e = e.iloc[rng.choice(len(e), size=min(n // 4, len(e)), replace=False)]
        raw = pl[pl[mk["usage"]] >= mk["min_app"]]
        for _, r in e.iterrows():
            h = raw[(raw.gsis_id == r.gsis_id) & (raw.date < r.date)].sort_values("date")
            h = h.groupby("game_id", as_index=False).agg(date=("date", "first"), v=(mk["y"], "sum"), u=(mk["usage"], "sum")).sort_values("date")
            tested += 1
            if len(h) != r.n_prev or not np.isclose(h.v.tail(6).mean(), r.mean6) or not np.isclose(h.u.tail(6).mean(), r.usage6) or not np.isclose(h.v.iloc[-1], r["last"]): bad += 1
    return dict(rows_tested=int(tested), mismatches=int(bad), ok=bool(bad == 0))


# ----------------------------------------------------------------------------- luck / skill diagnostics
def luck_tables() -> pd.DataFrame:
    g = load_games(include_2026=False); g = g[g.season <= 2025]
    tg = pd.read_csv(DERIVED / "team_games_feed.csv.gz"); tg = tg[tg.game_type == "REG"]
    rows = []
    for _, r in g.iterrows():
        for t, o, pf, pa, wk in [(r.home, r.away, r.home_score, r.away_score, r.week), (r.away, r.home, r.away_score, r.home_score, r.week)]:
            rows.append((r.season, t, wk, pf, pa))
    L = pd.DataFrame(rows, columns=["season", "team", "week", "pf", "pa"])
    L["win"] = np.where(L.pf > L.pa, 1.0, np.where(L.pf < L.pa, 0.0, 0.5)); L["one"] = (L.pf - L.pa).abs() <= 8
    T = L.groupby(["season", "team"]).agg(g=("win", "size"), wins=("win", "sum"), pf=("pf", "sum"), pa=("pa", "sum"))
    T["wp"] = T.wins / T.g; T["pd"] = (T.pf - T.pa) / T.g
    one = L[L.one].groupby(["season", "team"]).win.agg(["mean", "size"]).rename(columns={"mean": "wp_one", "size": "n_one"})
    T = T.join(one); T["pyth"] = T.pf ** 2.37 / (T.pf ** 2.37 + T.pa ** 2.37); T["pyth_res"] = T.wp - T.pyth
    tov = tg.merge(tg[["game_id", "team", "turnover_drives"]].rename(columns={"team": "opp", "turnover_drives": "opp_to"}), on=["game_id", "opp"])
    tm = tov.groupby(["season", "team"]).apply(lambda d: (d.opp_to - d.turnover_drives).sum() / len(d)).rename("to_margin")
    T = T.join(tm).reset_index()
    out = []
    obs_var = T.groupby("season").wp.var(ddof=0).mean(); bin_var = float((0.25 / T.g).mean())
    out.append(dict(metric="Variance of team win% (observed, mean of 11 seasons)", value=obs_var, note="32 teams per season; ties counted 0.5"))
    out.append(dict(metric="Variance expected if every game were a coin flip (binomial, p=0.5)", value=bin_var, note="0.25 / games played"))
    out.append(dict(metric="Share of win% variance explained by pure luck (binomial / observed)", value=bin_var / obs_var, note="remainder = persistent skill + schedule"))
    half = L.assign(h=L.week % 2).groupby(["season", "team", "h"]).win.mean().unstack()
    r = np.mean([np.corrcoef(d[0], d[1])[0, 1] for _, d in half.groupby("season")])
    out.append(dict(metric="Split-half reliability of win% (odd vs even weeks, Spearman-Brown corrected)", value=2 * r / (1 + r), note=f"raw half-vs-half r = {r:.3f}"))
    T2 = T.copy(); T2["season"] += 1; M = T.merge(T2, on=["season", "team"], suffixes=("", "_prev"))
    for lab, c in [("Win% (year-over-year correlation)", "wp"), ("Point differential per game", "pd"), ("Turnover margin per game", "to_margin"), ("Record in one-score games (<= 8 pts) win%", "wp_one"), ("Pythagorean residual (win% minus points-implied win%)", "pyth_res")]:
        mm = M.dropna(subset=[c, c + "_prev"]); out.append(dict(metric=f"Persistence: {lab}", value=float(np.corrcoef(mm[c], mm[c + "_prev"])[0, 1]), note=f"{len(mm)} team-season pairs"))
    return pd.DataFrame(out)


# ----------------------------------------------------------------------------- strategy evaluation
def losses_game(pred, model, market):
    d = pred[pred[f"{model}_margin"].notna() & pred.margin.notna()].copy()
    if market == "ML":
        d["lm"] = logloss(d[f"{model}_p"], d.home_win); d["lb"] = logloss(d["G0_p"], d.home_win)
    elif market == "SPREAD":
        d["lm"] = (d.margin - d[f"{model}_margin"]).abs(); d["lb"] = (d.margin - d["G0_margin"]).abs()
    else:
        d["lm"] = (d.total - d[f"{model}_total"]).abs(); d["lb"] = (d.total - d["G0_total"]).abs()
    return d


def losses_prop(pred, model, market):
    d = pred[(pred.market == market) & pred[f"{model}_q50"].notna()].copy()
    d["lm"] = np.mean([pinball(d.y, d[f"{model}_q{int(t*100)}"], t) for t in pm.TAUS], axis=0)
    d["lb"] = np.mean([pinball(d.y, d[f"PR0_q{int(t*100)}"], t) for t in pm.TAUS], axis=0)
    return d


def season_skills(d, seasons):
    return {int(s): float(1 - d[d.season == s].lm.sum() / d[d.season == s].lb.sum()) for s in seasons if (d.season == s).any()}


PREREG_FILES = ["pipeline/common.py", "pipeline/game_models.py", "pipeline/prop_models.py", "pipeline/joint.py", "pipeline/gates.py", "registry/hyperparameters.json", "registry/PREREGISTRATION.md"]


def sha(path) -> str:
    return hashlib.sha256((REGISTRY.parent / path).read_bytes()).hexdigest()


def preregistration_check() -> dict:
    """The sealed run refuses to execute unless the pre-registration is committed and the code/parameters are byte-identical to it."""
    pj = REGISTRY / "preregistration.json"
    if not pj.exists(): sys.exit("REFUSING sealed run: registry/preregistration.json does not exist")
    reg = json.loads(pj.read_text()); lab = REGISTRY.parent
    commit = subprocess.run(["git", "log", "-1", "--format=%H %cI", "--", "registry/preregistration.json"], cwd=lab, capture_output=True, text=True).stdout.strip()
    if not commit: sys.exit("REFUSING sealed run: preregistration.json is not committed to git")
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "registry", "pipeline"], cwd=lab, capture_output=True, text=True).stdout.strip()
    bad = [f for f in PREREG_FILES if sha(f) != reg["sha256"].get(f)]
    if bad: sys.exit(f"REFUSING sealed run: files changed since pre-registration: {bad}")
    return dict(prereg_commit=commit.split()[0], prereg_commit_time=commit.split()[1], files_match=True, working_tree_dirty=bool(dirty))


def main():
    t0 = time.time(); OUT.mkdir(parents=True, exist_ok=True)
    prereg = None if DEV_ONLY else preregistration_check()
    P = json.loads((REGISTRY / "hyperparameters.json").read_text())
    gp = pd.read_csv(SRC / "game_predictions.csv.gz"); pp = pd.read_csv(SRC / "prop_predictions.csv.gz")
    ev = lambda d: d[d.split == EVAL]; dv = lambda d: d[d.split == "dev"]
    audit_g = audit_games(P); audit_p = audit_props(P)
    print("audits", audit_g, audit_p, round(time.time() - t0))
    rec = pd.read_csv(VERIFIED / "reconciliation_summary.csv"); prov_games = bool(rec.verified.astype(bool).all()) and len(rec) == 11
    ytd = pd.read_csv(VERIFIED / "reconciliation_standings_2026_ytd.csv"); prov_2026 = bool(ytd.iloc[:, :].astype(str).apply(lambda c: c.str.contains("False", case=False)).sum().sum() == 0)
    leaders = pd.read_csv(VERIFIED / "reconciliation_player_leaders.csv"); lead_ok = int(leaders.shape[0])
    entries = []; cal_rows = []; sk_rows = []
    # ---- game strategies
    for model in GAME_MODELS:
        for market in ["ML", "SPREAD"] + (["TOTAL"] if model in ("G2", "G3") else []):
            d_ev = losses_game(ev(gp), model, market); d_dv = losses_game(dv(gp), model, market)
            sk, lo, hi, p, se = cluster_boot_skill(d_ev.lm, d_ev.lb, d_ev.game_id, B=BOOT_B)
            if market == "ML": cal = calib_ml(d_ev[f"{model}_p"], d_ev.home_win)
            elif market == "SPREAD": cal = calib_reg(d_ev[f"{model}_margin"], d_ev.margin)
            else: cal = calib_reg(d_ev[f"{model}_total"], d_ev.total)
            # luck placebo: shuffle this model's predictions across games within each season-week
            rng = np.random.default_rng(21); perm = []
            col = f"{model}_p" if market == "ML" else (f"{model}_margin" if market == "SPREAD" else f"{model}_total")
            for _ in range(300):
                sh = d_ev.copy(); sh[col] = sh.groupby(["season", "week"])[col].transform(lambda s: rng.permutation(s.to_numpy()))
                if market == "ML": lm = logloss(sh[col], sh.home_win)
                elif market == "SPREAD": lm = (sh.margin - sh[col]).abs()
                else: lm = (sh.total - sh[col]).abs()
                perm.append(1 - lm.sum() / d_ev.lb.sum())
            luck_p = float((np.sum(np.array(perm) >= sk) + 1) / 301); luck_hi = float(np.percentile(perm, 97.5))
            ss_ev = season_skills(d_ev, EVAL_SEASONS); ss_dv = season_skills(d_dv, DEV)
            vs = (np.nan, np.nan, np.nan)
            if model != "G1" and market != "TOTAL":
                d1 = losses_game(ev(gp), "G1", market).set_index("game_id").lm; dd = d_ev.set_index("game_id"); cm = dd.index.intersection(d1.index)
                s2, l2, h2, _, _ = cluster_boot_skill(dd.loc[cm].lm, d1.loc[cm], cm, B=1000); vs = (s2, l2, h2)
            entries.append(dict(id=f"{model}|{market}", family="Game lines", model=model, market=market, description=f"{GAME_MODELS[model]} - {MKT_NAME[market]}", n=len(d_ev), skill=sk, lo=lo, hi=hi, p=p, se=se,
                                luck_p=luck_p, luck_envelope_hi=luck_hi, vs=vs, ss_ev=ss_ev, ss_dv=ss_dv, cal=cal, pit=audit_g["ok"], prov=prov_games, prov_note="game results reconciled to NFL.com standings (32/32 teams, every season)"))
    # ---- prop strategies
    for model in ["PR1", "PR2"]:
        for market in pm.MARKETS:
            d_ev = losses_prop(ev(pp), model, market); d_dv = losses_prop(dv(pp), model, market)
            sk, lo, hi, p, se = cluster_boot_skill(d_ev.lm, d_ev.lb, d_ev.game_id, B=BOOT_B)
            cov = {t: float((d_ev.y <= d_ev[f"{model}_q{int(t*100)}"]).mean()) for t in pm.TAUS}
            err = [abs(cov[t] - t) for t in pm.TAUS]
            cal = dict(cov=cov, mean_abs_err=float(np.mean(err)), max_abs_err=float(np.max(err)), ok=bool(np.mean(err) <= COV_MEAN_TOL and np.max(err) <= COV_MAX_TOL))
            entries.append(dict(id=f"{model}|{market}", family="Player props", model=model, market=market, description=f"{PROP_NAME[model]} - {market.replace('_', ' ').lower()}", n=len(d_ev), skill=sk, lo=lo, hi=hi, p=p, se=se,
                                luck_p=np.nan, luck_envelope_hi=np.nan, ss_ev=season_skills(d_ev, EVAL_SEASONS), ss_dv=season_skills(d_dv, DEV), cal=cal, pit=bool(audit_p["ok"] and audit_g["ok"]), prov=bool(prov_games and lead_ok == 75),
                                prov_note=f"player outcomes: NFL game-center feed; sample-verified only ({lead_ok}/75 NFL.com 2025 leader rows exact); all other rows unverified"))
    # ---- combos (copula vs independence)
    gp_all = gp[gp.margin.notna()]
    pairs = joint.build_pairs(gp_all, pp[pp.split.isin(["dev", "test"])] if not DEV_ONLY else pp)
    corr = joint.table_correlations(pairs)
    for name in joint.PAIRS:
        fit_ev = (lambda sc, s: sc <= max(DEV)) if not DEV_ONLY else (lambda sc, s: sc < s)
        L_ev = joint.pricing_losses(pairs, name, EVAL_SEASONS, fit_ev); L_dv = joint.pricing_losses(pairs, name, DEV, lambda sc, s: sc < s)
        if L_ev.empty: continue
        sk, lo, hi, p, se = cluster_boot_skill(L_ev.l_cop, L_ev.l_ind, L_ev.game_id, B=BOOT_B)
        diff = L_ev.I - L_ev.p_cop; blo, bhi = bootstrap_ci(diff.to_numpy())
        cal = dict(obs=float(L_ev.I.mean()), pred_cop=float(L_ev.p_cop.mean()), pred_ind=float(L_ev.p_ind.mean()), diff=float(diff.mean()), lo=blo, hi=bhi, ok=bool(blo <= 0 <= bhi))
        pair_prov = prov_games and (lead_ok == 75 or name == "MARGIN_x_TOTAL")
        d2 = L_dv.rename(columns={"l_cop": "lm", "l_ind": "lb"}) if not L_dv.empty else L_dv
        entries.append(dict(id=f"COP|{name}", family="Parlays & prop combos", model="COP", market=name, description=f"Gaussian-copula pricing of 'both legs over own line': {PAIR_NAME[name]}", n=len(L_ev), skill=sk, lo=lo, hi=hi, p=p, se=se,
                            luck_p=np.nan, luck_envelope_hi=np.nan, ss_ev=season_skills(L_ev.rename(columns={"l_cop": "lm", "l_ind": "lb"}), EVAL_SEASONS), ss_dv=season_skills(d2, DEV) if not L_dv.empty else {}, cal=cal,
                            pit=bool(audit_p["ok"] and audit_g["ok"]), prov=bool(pair_prov), prov_note="game legs reconciled to NFL.com; prop legs sample-verified only" if name != "MARGIN_x_TOTAL" else "game results reconciled to NFL.com standings"))
    # ---- gates
    hp = holm({e["id"]: e["p"] for e in entries})
    gate_rows = []; board = []
    for e in entries:
        npos_ev = sum(v > 0 for v in e["ss_ev"].values()); npos_dv = sum(v > 0 for v in e["ss_dv"].values())
        need_ev = 2 if len(EVAL_SEASONS) == 3 else 3
        g1 = bool(e["prov"]); g2 = bool(e["pit"]); g3 = bool(e["lo"] > 0); g4 = bool(e["cal"]["ok"])
        g5 = bool(npos_ev >= need_ev and (DEV_ONLY or npos_dv >= 3)); g6 = bool(hp[e["id"]] < ALPHA); g7 = bool((e["hi"] - e["lo"]) / 2 <= PREC_MAX_HALFWIDTH)
        allp = all([g1, g2, g3, g4, g5, g6, g7]); credits = int(round(1000 * max(e["lo"], 0))) if allp else 0
        flags = []
        if e["family"] != "Game lines": flags.append("player outcomes sample-verified only")
        if not g3: flags.append("lower 95% CI of skill is not above 0")
        if not g4: flags.append("calibration gate failed")
        if not g5: flags.append("not positive in enough seasons")
        if not g6: flags.append("fails Holm correction over all tested strategies")
        if np.isfinite(e["luck_p"]) and e["luck_p"] > 0.05: flags.append("not distinguishable from shuffled-prediction luck")
        gate_rows.append(dict(id=e["id"], family=e["family"], G1_provenance=g1, G2_point_in_time=g2, G3_oos_skill=g3, G4_calibration=g4, G5_stability=g5, G6_holm=g6, G7_precision=g7,
                              G8_market_benchmark="N/A - no official historical odds source; left blank", holm_p=hp[e["id"]], raw_p=e["p"], seasons_positive_eval=f"{npos_ev}/{len(e['ss_ev'])}", seasons_positive_dev=f"{npos_dv}/{len(e['ss_dv'])}",
                              ci_halfwidth=(e["hi"] - e["lo"]) / 2, provenance=e["prov_note"], validated=allp))
        board.append(dict(id=e["id"], family=e["family"], model=e["model"], market=e["market"], description=e["description"], n_eval=e["n"], skill=e["skill"], ci_lo=e["lo"], ci_hi=e["hi"], holm_p=hp[e["id"]], luck_p=e["luck_p"],
                          luck_envelope_hi=e["luck_envelope_hi"], vs_elo=e.get("vs", (np.nan,) * 3)[0], vs_elo_lo=e.get("vs", (np.nan,) * 3)[1], vs_elo_hi=e.get("vs", (np.nan,) * 3)[2], tier="Validated" if allp else "Ranked (not validated)", credits=credits, gates_passed=int(sum([g1, g2, g3, g4, g5, g6, g7])), flags="; ".join(flags)))
        for s, v in {**{f"dev {k}": x for k, x in e["ss_dv"].items()}, **{f"{'sealed' if not DEV_ONLY else 'dev'} {k}": x for k, x in e["ss_ev"].items()}}.items():
            sk_rows.append(dict(id=e["id"], season=s, skill=v))
        cal_rows.append(dict(id=e["id"], **{k: (json.dumps(v) if isinstance(v, dict) else v) for k, v in e["cal"].items()}))
    lb = pd.DataFrame(board).sort_values(["tier", "ci_lo"], ascending=[False, False]).reset_index(drop=True)
    lb.insert(0, "rank", range(1, len(lb) + 1))
    lb.to_csv(OUT / "leaderboard.csv", index=False); pd.DataFrame(gate_rows).to_csv(OUT / "gates.csv", index=False)
    pd.DataFrame(sk_rows).to_csv(OUT / "skill_by_season.csv", index=False); pd.DataFrame(cal_rows).to_csv(OUT / "calibration.csv", index=False)
    corr.to_csv(OUT / "correlations.csv", index=False)
    pr = []
    for name in joint.PAIRS:
        L = joint.pricing_losses(pairs, name, EVAL_SEASONS, (lambda sc, s: sc <= max(DEV)) if not DEV_ONLY else (lambda sc, s: sc < s))
        if not L.empty: pr.append(dict(pair=name, n=len(L), rho_fit=float(L.rho.iloc[0]), p_ind=float(L.p_ind.iloc[0]), p_copula=float(L.p_cop.iloc[0]), observed=float(L.I.mean()), logloss_ind=float(L.l_ind.mean()), logloss_copula=float(L.l_cop.mean())))
    pd.DataFrame(pr).to_csv(OUT / "pricing_tests.csv", index=False)
    luck_tables().to_csv(OUT / "luck_tables.csv", index=False)
    if not DEV_ONLY:
        fw = []
        f = gp[(gp.season == FORWARD) & gp.margin.notna()]
        for model in GAME_MODELS:
            for market in ["ML", "SPREAD"] + (["TOTAL"] if model in ("G2", "G3") else []):
                d = losses_game(f, model, market)
                if len(d) < 20: continue
                sk, lo, hi, _, _ = cluster_boot_skill(d.lm, d.lb, d.game_id, B=1000)
                fw.append(dict(id=f"{model}|{market}", n_games=len(d), skill_vs_G0=sk, ci_lo=lo, ci_hi=hi, note="2026 W1-8 forward holdout (team level; 121 games; wide CIs; informational, not a gate)"))
        pd.DataFrame(fw).to_csv(OUT / "forward_holdout.csv", index=False)
        sched = pd.read_csv(VERIFIED / "nfl_schedule_2026_week9.csv"); w9 = gp[(gp.season == FORWARD) & (gp.week == 9)].copy()
        avail = lb[(lb.family == "Game lines") & (lb.market == "ML") & lb.model.isin(["G1", "G2", "G3", "G4"])]
        head = (avail[avail.tier == "Validated"] if (avail.tier == "Validated").any() else avail).sort_values("ci_lo", ascending=False).iloc[0].model
        tots = lb[(lb.family == "Game lines") & (lb.market == "TOTAL")].sort_values(["tier", "ci_lo"], ascending=[False, False]); tot_model = tots.iloc[0].model
        rows = []
        for _, r in w9.iterrows():
            sc = sched[(sched.away_nfl_code == r.away) & (sched.home_nfl_code == r.home)]
            if len(sc) != 1: continue
            sc = sc.iloc[0]; ph = float(r[f"{head}_p"])
            rows.append(dict(game=f"{r.away} @ {r.home}", away=r.away, home=r.home, kickoff=f"{sc.kickoff_day} {sc.kickoff_local_time_official}", network=sc.network, neutral_site=bool(r.neutral),
                             headline_model=head, home_win_prob=ph, fair_ml_home=american(ph), fair_ml_away=american(1 - ph), exp_margin_home=float(r[f"{head}_margin"]), total_model=tot_model, exp_total=float(r[f"{tot_model}_total"]),
                             G1_home_win_prob=float(r["G1_p"]), G2_home_win_prob=float(r["G2_p"]), G3_home_win_prob=float(r["G3_p"]), G4_home_win_prob=float(r["G4_p"]), model_tier=str(lb[lb.id == f"{head}|ML"].tier.iloc[0]), official_game_url=sc.official_game_url))
        pd.DataFrame(rows).to_csv(OUT / "week9_lines.csv", index=False)
    json.dump(dict(preregistration=prereg, audit_games=audit_g, audit_props=audit_p, eval_split=EVAL, prov_games=prov_games, prov_2026=prov_2026, leader_rows=lead_ok, n_strategies=len(entries), alpha=ALPHA,
                   sigmas=pairs.attrs.get("sigmas"), seconds=round(time.time() - t0)), open(OUT / "run_manifest.json", "w"), indent=1)
    print(lb[["rank", "id", "tier", "skill", "ci_lo", "ci_hi", "holm_p", "credits", "gates_passed"]].round(4).to_string(index=False))
    print("done in", round(time.time() - t0), "s")


if __name__ == "__main__":
    main()
