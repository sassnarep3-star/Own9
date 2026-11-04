#!/usr/bin/env python3
"""T03 - Audit the source data and prove (or refute) that its fields mean what we assume.

Every check is recorded with a machine-readable result in outputs/data_audit.json and is
quoted on the site's "Data & Sources" page. Nothing is assumed: each convention used by the
model (spread sign, odds units, moneyline units) is tested against an independent field in
the same or another source file.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "nfldata" / "data"
MANIFEST = json.loads((ROOT / "data" / "manifest.json").read_text())
OUT = ROOT / "outputs"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(name: str) -> pd.DataFrame:
    path = RAW / name
    expected = MANIFEST["files"][name]["sha256"]
    got = sha256(path)
    if got != expected:
        raise SystemExit(f"CHECKSUM MISMATCH for {name}: {got} != {expected}")
    return pd.read_csv(path, low_memory=False)


def american_to_prob(o: float) -> float:
    if o is None or np.isnan(o) or o == 0:
        return np.nan
    return 100.0 / (o + 100.0) if o > 0 else -o / (-o + 100.0)


def american_payout(o: float) -> float:
    """Profit per 1 unit staked at American odds o."""
    return o / 100.0 if o > 0 else 100.0 / -o


def main() -> int:
    checks: list[dict] = []

    def check(cid, name, ok, detail, source):
        checks.append(
            {"id": cid, "check": name, "result": "pass" if ok else "fail",
             "detail": detail, "source": source}
        )

    games = load("games.csv")
    closing = load("closing_lines.csv")
    initial = load("initial_lines.csv")
    sc = load("sc_lines.csv")
    win_totals = load("win_totals.csv")
    standings = load("standings.csv")
    teams = load("teams.csv")

    # ---------------------------------------------------------------- structural integrity
    dup = int(games.game_id.duplicated().sum())
    check("A01", "game_id is unique in games.csv", dup == 0, f"{dup} duplicates",
          MANIFEST["files"]["games.csv"]["source_url"])

    scored = games.dropna(subset=["home_score", "away_score"])
    r_ok = bool(np.allclose(scored.result, scored.home_score - scored.away_score))
    t_ok = bool(np.allclose(scored.total, scored.home_score + scored.away_score))
    check("A02", "result == home_score - away_score", r_ok,
          f"checked {len(scored)} completed games", MANIFEST["files"]["games.csv"]["source_url"])
    check("A03", "total == home_score + away_score", t_ok,
          f"checked {len(scored)} completed games", MANIFEST["files"]["games.csv"]["source_url"])

    # 32 clubs per season, all present in teams.csv
    n_teams = games.groupby("season").apply(
        lambda d: len(set(d.home_team) | set(d.away_team)), include_groups=False)
    bad_teams = int((n_teams < 30).sum())
    unknown = sorted((set(games.home_team) | set(games.away_team)) - set(teams.team.dropna()))
    check("A04", "every club code appears in teams.csv", not unknown,
          f"unknown: {unknown}", MANIFEST["files"]["teams.csv"]["source_url"])
    check("A05", "each season has >= 30 distinct clubs", bad_teams == 0,
          "seasons with <30 club codes: " + str(int(bad_teams)),
          MANIFEST["files"]["games.csv"]["source_url"])

    # ------------------------------------------------- spread sign convention (home-perspective)
    mkt = games.dropna(subset=["spread_line", "result"])
    corr = float(np.corrcoef(mkt.spread_line, mkt.result)[0, 1])
    check("A06", "spread_line is home-perspective and positive when the HOME team is favoured",
          corr > 0.3,
          f"corr(spread_line, result) = {corr:.4f} on n={len(mkt)}; "
          "positive spread_line must coincide with positive result (home wins by that many)",
          MANIFEST["files"]["games.csv"]["source_url"])

    # cross-file: games.spread_line must equal -1 * closing_lines SPREAD line for the away side
    closing = closing.assign(game_key=closing.alt_game_id.astype(str))
    cl_sp = closing[closing.type == "SPREAD"].merge(
        games[["game_id", "away_team", "home_team", "spread_line"]],
        left_on="game_key", right_on="game_id", how="inner")
    away_rows = cl_sp[cl_sp.side == cl_sp.away_team]
    diff = (away_rows.line + away_rows.spread_line).abs()
    agree = float((diff < 0.01).mean())
    check("A07", "games.spread_line agrees with closing_lines.csv SPREAD sign convention",
          agree > 0.98,
          f"{agree*100:.2f}% of {len(away_rows)} games agree on the away-side line "
          f"(max |diff| = {diff.max():.2f})",
          MANIFEST["files"]["closing_lines.csv"]["source_url"])

    cl_tot = closing[closing.type == "TOTAL"].merge(
        games[["game_id", "total_line"]], left_on="game_key", right_on="game_id", how="inner")
    tdiff = (cl_tot.line - cl_tot.total_line).abs()
    t_agree = float((tdiff < 0.01).mean())
    check("A08", "games.total_line agrees with closing_lines.csv TOTAL line", t_agree > 0.98,
          f"{t_agree*100:.2f}% of {len(cl_tot)} rows agree (max |diff| = {tdiff.max():.2f})",
          MANIFEST["files"]["closing_lines.csv"]["source_url"])

    # closing_lines outcome flag re-derived from the scoreboard
    sp = closing[closing.type == "SPREAD"].merge(
        games[["game_id", "home_team", "away_team", "result"]],
        left_on="game_key", right_on="game_id", how="inner")
    sp = sp.dropna(subset=["result"])
    signed = np.where(sp.side == sp.home_team, sp.line + sp.result, sp.line - sp.result)
    derived = (signed > 0).astype(float)
    push = (signed == 0)
    ok_rows = ~push
    outcome_agree = float((derived[ok_rows] == sp.outcome[ok_rows]).mean())
    check("A09", "closing_lines SPREAD outcome flag reproduces from scores + line",
          outcome_agree > 0.99,
          f"{outcome_agree*100:.2f}% of {int(ok_rows.sum())} non-push spread rows agree "
          f"({int(push.sum())} pushes excluded)",
          MANIFEST["files"]["closing_lines.csv"]["source_url"])

    to = closing[closing.type == "TOTAL"].merge(
        games[["game_id", "total", "home_score", "away_score"]],
        left_on="game_key", right_on="game_id", how="inner").dropna(subset=["total"])
    over_won = (to.total > to.line) * (to.side == "Over") + (to.total < to.line) * (to.side == "Under")
    to_push = to.total == to.line
    t_out_agree = float((over_won[~to_push].astype(float) == to.outcome[~to_push]).mean())
    check("A10", "closing_lines TOTAL outcome flag reproduces from score + line", t_out_agree > 0.99,
          f"{t_out_agree*100:.2f}% of {int((~to_push).sum())} non-push total rows agree",
          MANIFEST["files"]["closing_lines.csv"]["source_url"])

    # -------------------------------------------------------------------- odds units
    ml = games.dropna(subset=["away_moneyline", "home_moneyline"])
    implied = ml.away_moneyline.map(american_to_prob) + ml.home_moneyline.map(american_to_prob)
    ml_ok = bool(implied.between(1.0, 1.20).mean() > 0.97)
    check("A11", "moneyline columns are American odds (two-sided implied prob 1.00-1.20)",
          ml_ok,
          f"n={len(ml)}, share in [1.00,1.20] = {implied.between(1.0,1.20).mean():.4f}, "
          f"median overround = {implied.median():.4f}",
          MANIFEST["files"]["games.csv"]["source_url"])

    # spread/total prices: is home_spread_odds the price on the home side?
    spg = games.dropna(subset=["spread_line", "home_spread_odds", "away_spread_odds"])
    fav_is_home = spg.spread_line > 0
    # favourites are usually priced below +100 (negative American odds)
    fav_neg = float((spg.loc[fav_is_home, "home_spread_odds"] < 0).mean())
    dog_pos = float((spg.loc[~fav_is_home, "home_spread_odds"] > 0).mean())
    check("A12", "home_spread_odds is the price of the HOME side at spread_line",
          fav_neg > 0.8 and dog_pos > 0.8,
          f"when the home team is favoured, home_spread_odds < 0 in {fav_neg*100:.1f}% of games; "
          f"when the home team is the underdog, home_spread_odds > 0 in {dog_pos*100:.1f}% of games "
          f"(n={len(spg)}) - both consistent with a home-side price",
          MANIFEST["files"]["games.csv"]["source_url"])

    ov = games.dropna(subset=["total_line", "over_odds", "under_odds"])
    ov_impl = ov.over_odds.map(american_to_prob) + ov.under_odds.map(american_to_prob)
    check("A13", "over_odds/under_odds are American odds", bool(ov_impl.between(1.0, 1.20).mean() > 0.95),
          f"n={len(ov)}, median overround = {ov_impl.median():.4f}",
          MANIFEST["files"]["games.csv"]["source_url"])

    # sc_lines / initial_lines semantics: sc_lines.line for the away team should be ~ -home spread
    games = games.assign(gsis_int=pd.to_numeric(games.gsis, errors="coerce"))
    scm = sc.drop(columns=["away_team", "home_team", "week", "season"]).merge(
        games[["game_id", "gsis_int", "away_team", "home_team", "spread_line"]],
        left_on=sc.game_id.astype("int64"), right_on="gsis_int", how="inner")
    sc_away = scm[scm.side == scm.away_team]
    sc_agree = float(((sc_away.line + sc_away.spread_line).abs() < 5.0).mean())
    check("A14", "sc_lines lines are team-perspective spreads on the same scale (within 5 pts of close)",
          sc_agree > 0.95,
          f"{sc_agree*100:.2f}% of {len(sc_away)} away-side rows within 5 pts of the closing line; "
          "sc_lines is an OPENING line set, so it is expected to differ from the close",
          MANIFEST["files"]["sc_lines.csv"]["source_url"])

    # ---------------------------------------------------------------- coverage
    reg = games[games.game_type == "REG"]
    cov = {}
    for label, df in [("games", games), ("closing_lines", closing), ("sc_lines", sc),
                      ("initial_lines", initial), ("win_totals", win_totals)]:
        if label == "closing_lines":
            seasons = sorted(df.alt_game_id.astype(str).str[:4].astype(int).unique())
        elif "season" in df.columns:
            seasons = sorted(df.season.dropna().astype(int).unique())
        cov[label] = {"first": int(min(seasons)), "last": int(max(seasons)),
                      "n_seasons": len(seasons)}

    price_cov = {}
    for col in ["spread_line", "home_spread_odds", "total_line", "over_odds",
                "away_moneyline", "home_moneyline"]:
        s = reg.dropna(subset=[col])
        price_cov[col] = {"n": int(len(s)), "first_season": int(s.season.min()),
                          "last_season": int(s.season.max())}

    # ---------------------------------------------------- season structure + doc lag
    seasons_struct = (
        reg.groupby("season")
        .agg(games=("game_id", "size"), weeks=("week", "max"),
             completed=("home_score", "count"))
        .reset_index()
    )
    # DATASETS.md is the upstream documentation for games.csv; detect columns it does not describe
    doc = (RAW.parent / "DATASETS.md").read_text()
    documented = {m.group(1) for m in re.finditer(r"`([a-z_0-9]+)`", doc)}
    undocumented = [c for c in games.columns if c not in documented]
    wk_doc_says = "This will be 1-17 for the regular season" in doc
    wk_actual = int(reg[reg.season >= 2021].week.max())
    check("A15", "upstream documentation (DATASETS.md) covers every games.csv column", not undocumented,
          f"columns not described in DATASETS.md: {undocumented}",
          MANIFEST["documentation_urls"]["DATASETS.md"])
    check("A16", "upstream documentation matches the current regular-season length", 
          not (wk_doc_says and wk_actual > 17),
          f"DATASETS.md states regular season weeks are 1-17 (and week 18 = wildcard), but the data "
          f"contains regular-season week {wk_actual} (season 2026 has "
          f"{int(seasons_struct[seasons_struct.season==2026].games.iloc[0])} scheduled REG games). "
          "Documentation lag - flagged.",
          MANIFEST["documentation_urls"]["DATASETS.md"])

    # ------------------------------------------------------------ implied facts to be
    # cross-checked against NFL.com by pipeline/02_verify_official.py
    official_targets = {
        "season_2026_weeks": int(reg[reg.season == 2026].week.max()),
        "season_2026_reg_games": int(len(reg[reg.season == 2026])),
        "season_2025_reg_games": int(len(reg[reg.season == 2025])),
        "completed_games_2026": int(reg[(reg.season == 2026)].home_score.notna().sum()),
        "last_completed_gameday_2026": str(reg[(reg.season == 2026)].dropna(subset=["home_score"]).gameday.max()),
    }

    audit = {
        "generated_at_utc": MANIFEST["generated_at_utc"],
        "source_commit_sha": MANIFEST["commit_sha"],
        "checks": checks,
        "n_pass": sum(c["result"] == "pass" for c in checks),
        "n_fail": sum(c["result"] == "fail" for c in checks),
        "coverage": cov,
        "market_price_coverage": price_cov,
        "season_structure": seasons_struct.to_dict(orient="records"),
        "undocumented_columns": undocumented,
        "official_crosscheck_targets": official_targets,
        "row_counts": {
            "games": len(games), "closing_lines": len(closing), "initial_lines": len(initial),
            "sc_lines": len(sc), "win_totals": len(win_totals), "standings": len(standings),
            "teams": len(teams),
        },
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "data_audit.json").write_text(json.dumps(audit, indent=2) + "\n")

    print(f"checks: {audit['n_pass']} pass / {audit['n_fail']} fail")
    for c in checks:
        flag = "PASS" if c["result"] == "pass" else "FAIL"
        print(f"  [{flag}] {c['id']} {c['check']}: {c['detail'][:110]}")
    print("coverage:", cov)
    print("undocumented columns:", undocumented)
    print("2026 targets:", official_targets)
    return 0 if audit["n_fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
