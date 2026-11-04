"""Player-prop combo research from the archived official NFL.com GameCenter feeds (2009-2019).

No historical prop prices exist in any source available here, so prop combos are evaluated
for CORRELATION and JOINT-HIT LIFT only; ROI is left blank and flagged.

Pre-game player identification (no selection on the outcome):
  QB1  = the team's starting QB recorded in games.csv (GSIS id, same id space as the feed)
  RB1  = most rushing attempts for the team over its previous 3 games (non-QB)
  WR1  = most receiving yards for the team over its previous 3 games
  A player who does not appear in any stat category of the game is treated as inactive
  (prop void, row dropped) -- limitation: a player active with zero touches is also dropped.
Originated prop line = median of the player's previous 6 games (min 3), rounded to x.5.
Games whose archived feed disagreed with the official score are excluded.
Preseason games in the archive are excluded from all histories.
"""
import numpy as np
import pandas as pd
from . import config as C

ROLE_STAT = {"qb": ("passing", "yds"), "rb": ("rushing", "yds"), "wr": ("receiving", "yds")}


def load():
    p = pd.read_csv(C.CACHE / "gc_player_lines.csv.gz", dtype={"eid": str})
    p["date"] = pd.to_datetime(p.eid.str[:8])
    games = pd.read_csv(C.DERIVED / "games.csv", dtype={"old_game_id": str})
    # the archived feed also contains PRESEASON games; keep only regular-season/postseason games
    # listed in the schedule file so preseason snaps never enter role selection or line history
    p = p[p.eid.isin(set(games.old_game_id.dropna()))]
    games = games[(games.game_type == "REG") & (games.score_status == "VERIFIED") & games.season.between(2009, 2019)]
    games = games[games.score_method == "V2 official feed"]
    return p, games


def stat_table(p, cat, col):
    d = p[p.category == cat][["eid", "date", "team", "player_id", "name", col, "att" if cat != "receiving" else "rec"]]
    return d.rename(columns={col: "val"})


def prior_median(hist, pid, date, n=6, min_n=3):
    h = hist.get(pid)
    if h is None:
        return None
    prev = h[h.date < date].tail(n)
    if len(prev) < min_n:
        return None
    return float(np.floor(prev.val.median()) + 0.5)


def build():
    p, games = load()
    eids = set(games.old_game_id)
    pas = stat_table(p, "passing", "yds")
    rus = stat_table(p, "rushing", "yds")
    rec = stat_table(p, "receiving", "yds")
    appeared = p[p.category.str.startswith("appeared:")][["eid", "team", "player_id"]].drop_duplicates()
    app_set = set(zip(appeared.eid, appeared.team, appeared.player_id))
    qb_hist = {k: v.sort_values("date") for k, v in pas[pas.att >= 10].groupby("player_id")}
    rb_hist = {k: v.sort_values("date") for k, v in rus.groupby("player_id")}
    wr_hist = {k: v.sort_values("date") for k, v in rec.groupby("player_id")}
    passers = set(pas[pas.att >= 5].player_id)
    team_games = {}
    for t, grp in p[["eid", "date", "team"]].drop_duplicates().groupby("team"):
        team_games[t] = grp.sort_values("date")
    rows = []
    for g in games.itertuples():
        eid = g.old_game_id
        date = pd.Timestamp(eid[:8])
        for side, opp in (("home", "away"), ("away", "home")):
            team = getattr(g, f"{side}_team")
            fteam = {"JAX": "JAX"}.get(team, team)
            r = {"game_id": g.game_id, "eid": eid, "season": g.season, "week": g.week, "team": team,
                 "opp": getattr(g, f"{opp}_team"), "pts": getattr(g, f"{side}_score"),
                 "opp_pts": getattr(g, f"{opp}_score"), "spread_line": g.spread_line, "total_line": g.total_line,
                 "side": side, "nfl_url": g.nfl_url}
            # QB1: recorded starter
            qid = getattr(g, f"{side}_qb_id")
            q = pas[(pas.eid == eid) & (pas.player_id == qid)]
            r["qb_id"], r["qb_name"] = qid, getattr(g, f"{side}_qb_name")
            r["qb_yds"] = float(q.val.iloc[0]) if len(q) else np.nan
            r["qb_line"] = prior_median(qb_hist, qid, date)
            # RB1 / WR1 from the team's previous 3 games
            tg = team_games.get(fteam)
            prev = tg[tg.date < date].tail(3).eid if tg is not None else []
            for role, table, hist, key in (("rb", rus, rb_hist, "att"), ("wr", rec, wr_hist, "val")):
                pt = table[table.eid.isin(prev) & (table.team == fteam)]
                if role == "rb":
                    pt = pt[~pt.player_id.isin(passers)]
                if len(prev) < 3 or pt.empty:
                    r[f"{role}_id"] = None
                    continue
                pid = pt.groupby("player_id")[key].sum().idxmax()
                r[f"{role}_id"] = pid
                r[f"{role}_name"] = pt[pt.player_id == pid].name.iloc[-1]
                if (eid, fteam, pid) not in app_set:
                    r[f"{role}_yds"] = np.nan  # inactive -> void
                else:
                    cur = table[(table.eid == eid) & (table.player_id == pid)]
                    r[f"{role}_yds"] = float(cur.val.iloc[0]) if len(cur) else 0.0
                r[f"{role}_line"] = prior_median(hist, pid, date)
            rows.append(r)
    d = pd.DataFrame(rows)
    d.to_csv(C.DERIVED / "prop_team_games_2009_2019.csv", index=False, float_format="%.1f")
    return d


def lift_stats(a, b, weeks, n_boot, seed):
    a, b = np.asarray(a, bool), np.asarray(b, bool)
    pa, pb, pab = a.mean(), b.mean(), (a & b).mean()
    lift = pab / (pa * pb)
    phi = np.corrcoef(a.astype(float), b.astype(float))[0, 1]
    rng = np.random.default_rng(seed)
    uw = np.unique(weeks)
    idx = {w: np.where(weeks == w)[0] for w in uw}
    boots = []
    for _ in range(n_boot):
        pick = np.concatenate([idx[w] for w in rng.choice(uw, len(uw))])
        aa, bb = a[pick], b[pick]
        boots.append((aa & bb).mean() / (aa.mean() * bb.mean()))
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return {"n": int(len(a)), "p_a": float(pa), "p_b": float(pb), "p_joint": float(pab), "p_if_independent": float(pa * pb),
            "lift": float(lift), "lift_ci95": [float(lo), float(hi)], "phi": float(phi)}


def american_from_p(p):
    return round(-100 * p / (1 - p)) if p >= 0.5 else round(100 * (1 - p) / p)


def analyze(d):
    d = d.copy()
    d["margin"] = d.pts - d.opp_pts
    d["game_total"] = d.pts + d.opp_pts
    d["wk"] = d.season.astype(str) + "-" + d.week.astype(str)
    side_line = np.where(d.side == "home", d.spread_line, -d.spread_line)  # points the team is favoured by
    d["team_cover"] = d.margin - side_line  # >0 cover
    for role in ("qb", "rb", "wr"):
        d[f"{role}_over"] = d[f"{role}_yds"] - d[f"{role}_line"]
    opp = d[["game_id", "team", "qb_over", "qb_yds"]].rename(columns={"team": "opp", "qb_over": "opp_qb_over", "qb_yds": "opp_qb_yds"})
    d = d.merge(opp, on=["game_id", "opp"], how="left")
    combos = [
        ("PP01", "QB1 passing yards over + WR1 receiving yards over (same team)", "qb_over", "wr_over"),
        ("PP02", "QB1 passing yards over + game total over (closing total)", "qb_over", "game_over"),
        ("PP03", "RB1 rushing yards over + same team covers the closing spread", "rb_over", "team_cover"),
        ("PP04", "QB1 passing yards over + opposing QB1 passing yards over", "qb_over", "opp_qb_over"),
        ("PP05", "QB1 passing yards over + RB1 rushing yards over (same team)", "qb_over", "rb_over"),
        ("PP06", "WR1 receiving yards over + same team covers the closing spread", "wr_over", "team_cover"),
    ]
    d["game_over"] = d.game_total - d.total_line
    out = []
    for i, (cid, desc, x, y) in enumerate(combos):
        sub = d[[x, y, "wk", "season"]].dropna()
        sub = sub[(sub[x] != 0) & (sub[y] != 0)]  # drop pushes
        res = lift_stats(sub[x] > 0, sub[y] > 0, sub.wk.to_numpy(), 2000, C.SEED + i)
        res.update({"id": cid, "description": desc,
                    "fair_price_if_independent": american_from_p(res["p_if_independent"]),
                    "fair_price_with_correlation": american_from_p(res["p_joint"]),
                    "edge_if_book_prices_independently_at_fair_odds": res["lift"] - 1,
                    "roi": None, "roi_status": "BLANK - no historical prop prices (flagged)",
                    "uses_market_line": y in ("game_over", "team_cover")})
        out.append(res)
    corr_pairs = [
        ("QB1 pass yds", "WR1 rec yds", "qb_yds", "wr_yds"),
        ("QB1 pass yds", "team points", "qb_yds", "pts"),
        ("QB1 pass yds", "game total points", "qb_yds", "game_total"),
        ("QB1 pass yds", "team margin", "qb_yds", "margin"),
        ("QB1 pass yds", "opposing QB1 pass yds", "qb_yds", "opp_qb_yds"),
        ("RB1 rush yds", "team margin", "rb_yds", "margin"),
        ("RB1 rush yds", "team points", "rb_yds", "pts"),
        ("RB1 rush yds", "QB1 pass yds", "rb_yds", "qb_yds"),
        ("WR1 rec yds", "team points", "wr_yds", "pts"),
    ]
    corrs = []
    for a, b, x, y in corr_pairs:
        sub = d[[x, y]].dropna()
        r = float(np.corrcoef(sub[x], sub[y])[0, 1])
        z, se = np.arctanh(r), 1 / np.sqrt(len(sub) - 3)
        corrs.append({"x": a, "y": b, "n": int(len(sub)), "pearson_r": r,
                      "ci95": [float(np.tanh(z - 1.96 * se)), float(np.tanh(z + 1.96 * se))]})
    calib = {}
    for role in ("qb", "rb", "wr"):
        s = d[f"{role}_over"].dropna()
        s = s[s != 0]
        calib[role] = {"n": int(len(s)), "over_rate": float((s > 0).mean())}
    return out, corrs, calib


if __name__ == "__main__":
    d = build()
    print(len(d), d[["qb_yds", "qb_line", "rb_yds", "rb_line", "wr_yds", "wr_line"]].notna().mean().round(3).to_dict())
    combos, corrs, calib = analyze(d)
    for c in combos:
        print(c["id"], c["n"], round(c["p_joint"], 3), round(c["p_if_independent"], 3), round(c["lift"], 3), [round(v, 3) for v in c["lift_ci95"]])
    for c in corrs:
        print(c["x"], "~", c["y"], c["n"], round(c["pearson_r"], 3), [round(v, 3) for v in c["ci95"]])
    print(calib)
