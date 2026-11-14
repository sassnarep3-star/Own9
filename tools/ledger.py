"""Ledger rules for Own9: validation, computed coverage, signal/staking separation,
demotion-gate evaluation and correlation publication.

Standard library only. Every rule fails closed: a missing input yields
'not evaluated' or a blank value, never a pass or an estimate.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data" / "ledger"

# Hosts that may appear as source links for verified values.
OFFICIAL_HOSTS = {"www.nfl.com", "static.www.nfl.com", "operations.nfl.com", "laws.e-gov.go.jp"}
# Market publishers: allowed for price observations only, and always labelled as not official.
MARKET_HOSTS = {"sportsbook.draftkings.com"}
# Method references: allowed for definitions only, never for a value.
METHOD_HOSTS = {"docs.scipy.org", "scikit-learn.org", "www.statsmodels.org", "www.itl.nist.gov", "docs.github.com"}

RESULT_COLS = ["game_id", "season", "week", "date_local", "away", "away_score", "home", "home_score",
               "status", "source_url", "source_page", "check_method", "verification_status"]
PRICE_COLS = ["snapshot_id", "game_id", "origination_order", "market", "side", "line", "american_odds",
              "open_line", "open_odds", "open_time_utc", "close_line", "close_odds", "close_time_utc",
              "observed_date_utc", "observed_time_utc", "book", "market_source_url", "matchup_official_url",
              "verification_status", "notes"]
ORDER = {"spread": 1, "total": 2, "moneyline": 3}

# Proposed thresholds from data/ledger/policy.json. None has been set by the owner.
PROPOSED = {"N_MIN": 200, "N_BIN": 30, "N_CORR_MIN": 30, "N_CORR_PUBLISH": 30}


def load_csv(name: str) -> list[dict]:
    with open(LEDGER / name, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_json(name: str) -> dict:
    return json.loads((LEDGER / name).read_text(encoding="utf-8"))


def host(url: str) -> str:
    return urlparse(url).hostname or ""


def validate_results(rows: list[dict]) -> list[str]:
    errs: list[str] = []
    seen: set[str] = set()
    for i, r in enumerate(rows, 2):
        for c in RESULT_COLS:
            if c not in r:
                errs.append(f"results row {i}: missing column {c}")
        gid = r.get("game_id", "")
        if gid in seen:
            errs.append(f"results row {i}: duplicate game_id {gid}")
        seen.add(gid)
        for c in ("away_score", "home_score", "week", "season"):
            if not str(r.get(c, "")).isdigit():
                errs.append(f"results row {i}: {c} must be an integer read from the source, got {r.get(c)!r}")
        if host(r.get("source_url", "")) not in OFFICIAL_HOSTS:
            errs.append(f"results row {i}: source_url is not an official host")
        if host(r.get("source_page", "")) not in OFFICIAL_HOSTS:
            errs.append(f"results row {i}: source_page is not an official host")
        if r.get("status") != "Final":
            errs.append(f"results row {i}: only final scores are verified results")
    return errs


def validate_prices(rows: list[dict]) -> list[str]:
    errs: list[str] = []
    for i, r in enumerate(rows, 2):
        for c in PRICE_COLS:
            if c not in r:
                errs.append(f"prices row {i}: missing column {c}")
        mkt = r.get("market", "")
        if mkt not in ORDER:
            errs.append(f"prices row {i}: unknown market {mkt!r}")
        elif int(r.get("origination_order") or 0) != ORDER[mkt]:
            errs.append(f"prices row {i}: origination_order must be {ORDER[mkt]} for {mkt} (side, total, moneyline)")
        if host(r.get("market_source_url", "")) not in MARKET_HOSTS:
            errs.append(f"prices row {i}: market_source_url must be a named market page")
        has_open = bool(r.get("open_line") or r.get("open_odds"))
        has_close = bool(r.get("close_line") or r.get("close_odds"))
        if has_open and not r.get("open_time_utc"):
            errs.append(f"prices row {i}: opening value without a timestamp")
        if has_close and not r.get("close_time_utc"):
            errs.append(f"prices row {i}: closing value without a timestamp")
        if not r.get("verification_status"):
            errs.append(f"prices row {i}: verification_status is required")
    return errs


def validate_replacements(rows: list[dict]) -> list[str]:
    errs: list[str] = []
    for i, r in enumerate(rows, 2):
        if host(r.get("source_url", "")) not in OFFICIAL_HOSTS:
            errs.append(f"replacements row {i}: source_url is not an official host")
        # The NFL publishes no depth tier in any source read, so tier cells must stay blank.
        if r.get("depth_tier_out") or r.get("depth_tier_in"):
            errs.append(f"replacements row {i}: depth tier filled without an official published tier")
    return errs


def coverage(results: list[dict], prices: list[dict], replacements: list[dict],
             correlation_n: dict[str, int]) -> dict:
    """Counts computed from the stores, so pages never retype a number."""
    games_priced = {r["game_id"] for r in prices}
    return {
        "verified_results": len(results),
        "verified_weeks": sorted({int(r["week"]) for r in results}),
        "price_rows": len(prices),
        "price_games": len(games_priced),
        "open_values": sum(1 for r in prices if r.get("open_line") or r.get("open_odds")),
        "close_values": sum(1 for r in prices if r.get("close_line") or r.get("close_odds")),
        "fair_lines": 0,  # no fair line exists: no model is fitted on verified inputs
        "difference_values": 0,
        "replacement_records": len(replacements),
        "depth_tiers_published": sum(1 for r in replacements if r.get("depth_tier_out") or r.get("depth_tier_in")),
        "correlation_pairs": len(correlation_n),
        "correlation_official_n_total": sum(correlation_n.values()),
        "correlation_coefficients": 0,
    }


# ---- Leaderboard: signal and staking are separate tracks -----------------------------------

SIGNAL_GATES = [f"G0{i}" for i in range(1, 10)]  # G01 to G09


def signal_eligible(gate_status: dict[str, str]) -> bool:
    """Eligible only when every signal gate G01 to G09 is an explicit pass."""
    return all(gate_status.get(g) == "pass" for g in SIGNAL_GATES)


def rank_signal(strategies: list[dict]) -> list[dict]:
    """Rank on signal metrics only. Staking fields are never read here.

    Each strategy dict: id, gate_status (dict), signal_score (lower is better, or None),
    and optional staking fields that are carried through untouched.
    """
    eligible = [s for s in strategies if signal_eligible(s.get("gate_status", {})) and s.get("signal_score") is not None]
    ranked = sorted(eligible, key=lambda s: (s["signal_score"], s["id"]))
    out = []
    for pos, s in enumerate(ranked, 1):
        out.append({"id": s["id"], "signal_rank": pos})
    return out


def rank_staking_informational(strategies: list[dict]) -> list[dict]:
    """Staking view for display only. It cannot change signal rank or eligibility."""
    return sorted(
        ({"id": s["id"], "roi": s.get("roi")} for s in strategies),
        key=lambda s: (s["roi"] is None, -(s["roi"] or 0), s["id"]),
    )


# ---- Demotion gate -------------------------------------------------------------------------

def evaluate_demotion(m: dict) -> dict[str, str]:
    """Return a state per trigger: 'breach', 'clear' or 'not evaluated'.

    Input keys (None means not available):
      provenance_ok, asof_ok (bool), n_forecasts (int), ll_diff_lower (float: strategy minus market
      log loss, lower 95% bound), n_bin_breaches (int), n_priced (int), clv_upper (float: upper 95%
      bound of mean closing-line value), dep_n (int), dep_outside_band (bool), joint_fail (bool),
      max_drawdown (float), drawdown_cap (float), stake_rule_ok (bool).
    A missing input is 'not evaluated', so a strategy cannot be cleared by absent data.
    """
    def state(ok_when_clear: bool | None) -> str:
        if ok_when_clear is None:
            return "not evaluated"
        return "clear" if ok_when_clear else "breach"

    out: dict[str, str] = {}
    prov = m.get("provenance_ok")
    asof = m.get("asof_ok")
    out["D1"] = "not evaluated" if prov is None or asof is None else ("clear" if prov and asof else "breach")

    n = m.get("n_forecasts")
    ll = m.get("ll_diff_lower")
    if n is None or ll is None or n < PROPOSED["N_MIN"]:
        out["D2"] = "not evaluated"  # too few forecasts to judge: never cleared by default
    else:
        out["D2"] = "breach" if ll > 0 else "clear"
    out["D3"] = state(None if m.get("n_bin_breaches") is None else m["n_bin_breaches"] == 0)
    npr = m.get("n_priced")
    cu = m.get("clv_upper")
    if npr is None or cu is None or npr < PROPOSED["N_MIN"]:
        out["D4"] = "not evaluated"
    else:
        out["D4"] = "breach" if cu < 0 else "clear"
    dn = m.get("dep_n")
    dob = m.get("dep_outside_band")
    jf = m.get("joint_fail")
    if dn is None or dob is None or jf is None:
        out["D5"] = "not evaluated"
    elif jf:
        out["D5"] = "breach"
    elif dn < PROPOSED["N_CORR_MIN"]:
        out["D5"] = "not evaluated"
    else:
        out["D5"] = "breach" if dob else "clear"
    md = m.get("max_drawdown")
    cap = m.get("drawdown_cap")
    sr = m.get("stake_rule_ok")
    if md is None or cap is None or sr is None:
        out["D6"] = "not evaluated"
    else:
        out["D6"] = "breach" if md > cap or not sr else "clear"
    return out


def may_stay_live(states: dict[str, str]) -> bool:
    """A live strategy stays live only if every trigger is explicitly clear."""
    return all(v == "clear" for v in states.values())


# ---- Correlation publication -------------------------------------------------------------

def publish_correlation(r: float | None, n: int, official_only: bool, ci: tuple[float, float] | None) -> dict:
    """n is always published. r and its interval are published only under the rule in policy.json."""
    if n is None or n < 0:
        raise ValueError("n must be a non-negative count")
    if r is None or not official_only or n < PROPOSED["N_CORR_PUBLISH"] or ci is None:
        reason = ("no paired official observations" if n == 0 else
                  "n below minimum" if n < PROPOSED["N_CORR_PUBLISH"] else
                  "unofficial or assumed pairs" if not official_only else
                  "no interval" if ci is None else "no coefficient supplied")
        return {"n": n, "r": None, "ci_low": None, "ci_high": None, "status": f"not published: {reason}"}
    return {"n": n, "r": round(r, 4), "ci_low": round(ci[0], 4), "ci_high": round(ci[1], 4), "status": "published"}


def validate_all() -> dict:
    results = load_csv("results_verified.csv")
    prices = load_csv("price_snapshots.csv")
    reps = load_csv("replacements.csv")
    errs = validate_results(results) + validate_prices(prices) + validate_replacements(reps)
    return {"errors": errs, "coverage": coverage(results, prices, reps, {c["id"]: 0 for c in
                                                                        load_catalog_correlations()})}


def load_catalog_correlations() -> list[dict]:
    cat = json.loads((ROOT / "research" / "catalog.json").read_text(encoding="utf-8"))
    return cat["correlations"]


if __name__ == "__main__":
    res = validate_all()
    if res["errors"]:
        for e in res["errors"]:
            print("ERROR:", e)
        raise SystemExit(1)
    print("PASS: ledger stores valid;", json.dumps(res["coverage"], sort_keys=True))
