"""Market-board engine for session a77d40e1 (added 2026-11-14).

Pipeline, all deterministic and pure-stdlib:

1. Parse the verbatim official game links in ``data/board/raw/week-NN.txt``
   (transcribed from https://www.nfl.com/schedules/2026/by-week/week-N, retrieved
   2026-11-14 UTC) into a verified results feed.
2. Cross-check every final that the committed secondary nflverse snapshot also
   scores (weeks 1-8); the secondary file is stale for weeks 9-10, so those rest
   on the official transcription alone.
3. Fit the frozen transparent model on officially sourced finals only, originate
   Week 11 markets in the fixed order side -> total -> moneyline, and record open
   and close price snapshots for every originated market.
4. Run the walk-forward diagnostic (originate each past week from strictly earlier
   verified finals only) and score the calls against official results.
5. Split signal from staking, apply the live-to-paper gate fail-closed, and
   compute correlations from official numbers with n published.

No wagering is enabled; market prices do not exist because the league publishes
none, so every market-line / ROI / CLV cell stays blank (never zero).
"""
from __future__ import annotations

import csv
import math
import re
from random import Random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "board" / "raw"
OUT = ROOT / "data" / "board"

# Frozen session instant: every timestamp printed by this engine is this value so
# the build stays byte-for-byte deterministic (CI regenerates and diffs).
BUILD_TS = "2026-11-14T22:30:00Z"

SLUG_TO_CODE = {
    "49ers": "SF", "bears": "CHI", "bengals": "CIN", "bills": "BUF", "broncos": "DEN",
    "browns": "CLE", "buccaneers": "TB", "cardinals": "ARI", "chargers": "LAC",
    "chiefs": "KC", "colts": "IND", "cowboys": "DAL", "dolphins": "MIA", "eagles": "PHI",
    "falcons": "ATL", "giants": "NYG", "jaguars": "JAX", "jets": "NYJ", "lions": "DET",
    "packers": "GB", "panthers": "CAR", "patriots": "NE", "raiders": "LV", "rams": "LA",
    "ravens": "BAL", "saints": "NO", "seahawks": "SEA", "steelers": "PIT", "texans": "HOU",
    "titans": "TEN", "vikings": "MIN", "commanders": "WAS",
}
CODE_TO_NAME = {
    "SF": "49ers", "CHI": "Bears", "CIN": "Bengals", "BUF": "Bills", "DEN": "Broncos",
    "CLE": "Browns", "TB": "Buccaneers", "ARI": "Cardinals", "LAC": "Chargers",
    "KC": "Chiefs", "IND": "Colts", "DAL": "Cowboys", "MIA": "Dolphins", "PHI": "Eagles",
    "ATL": "Falcons", "NYG": "Giants", "JAX": "Jaguars", "NYJ": "Jets", "DET": "Lions",
    "GB": "Packers", "CAR": "Panthers", "NE": "Patriots", "LV": "Raiders", "LA": "Rams",
    "BAL": "Ravens", "NO": "Saints", "SEA": "Seahawks", "PIT": "Steelers", "HOU": "Texans",
    "TEN": "Titans", "MIN": "Vikings", "WAS": "Commanders",
}
MONTHS = {"September": 9, "October": 10, "November": 11}

_FINAL_RE = re.compile(
    r"- \[([A-Za-z0-9]+) (\d+), ([A-Za-z0-9]+) (\d+), FINAL, ([A-Za-z]+), "
    r"([A-Za-z]+) (\d+)(?:st|nd|rd|th)\]\(https://www\.nfl\.com/games/([a-z0-9]+)-at-([a-z0-9]+)-"
    r"(\d{4})-reg-(\d+)\)\s*$"
)
_SCHED_RE = re.compile(
    r"- \[([A-Za-z0-9]+) at ([A-Za-z0-9]+), ([A-Za-z]+), ([A-Za-z]+) (\d+)(?:st|nd|rd|th), "
    r"(\d{1,2}:\d{2} [AP]M), ([A-Z]+)\]\(https://www\.nfl\.com/games/([a-z0-9]+)-at-"
    r"([a-z0-9]+)-(\d{4})-reg-(\d+)\)\s*$"
)
_BYE_RE = re.compile(r"# Teams on bye: ([A-Z, ]+?)(?: \(as published[^)]*\))?$")


class FeedError(RuntimeError):
    """Raised when the transcription fails a structural integrity check."""


class OrderViolation(RuntimeError):
    """Raised when origination order side -> total -> moneyline is broken."""


def _date(year: int, month_name: str, day: str) -> str:
    month = MONTHS[month_name]
    return f"{year}-{month:02d}-{int(day):02d}"


def parse_week_file(path: Path) -> dict:
    """Parse one verbatim schedule transcription; fail loudly on any anomaly."""
    games, byes = [], []
    for lineno, raw in enumerate(path.read_text().splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            m = _BYE_RE.match(line)
            if m:
                byes = [t.strip() for t in m.group(1).split(",") if t.strip()]
            continue
        fm = _FINAL_RE.match(line)
        sm = _SCHED_RE.match(line)
        if fm:
            name_a, score_a, name_b, score_b, weekday, mon, day, away, home, season, week = fm.groups()
            a_slug, b_slug = name_a.lower(), name_b.lower()
            if a_slug != away or b_slug != home:
                raise FeedError(f"{path.name}:{lineno}: link text teams disagree with URL slug")
            games.append({
                "game_id": f"{away}-at-{home}-{season}-reg-{week}",
                "season": int(season), "week": int(week),
                "kickoff_date": _date(int(season), mon, day), "weekday": weekday,
                "away": SLUG_TO_CODE[away], "home": SLUG_TO_CODE[home],
                "away_score": int(score_a), "home_score": int(score_b),
                "status": "final", "nfl_url": f"https://www.nfl.com/games/{away}-at-{home}-{season}-reg-{week}",
            })
        elif sm:
            name_a, name_b, weekday, mon, day, kickoff, network, away, home, season, week = sm.groups()
            a_slug, b_slug = name_a.lower(), name_b.lower()
            if a_slug != away or b_slug != home:
                raise FeedError(f"{path.name}:{lineno}: link text teams disagree with URL slug")
            games.append({
                "game_id": f"{away}-at-{home}-{season}-reg-{week}",
                "season": int(season), "week": int(week),
                "kickoff_date": _date(int(season), mon, day), "weekday": weekday,
                "away": SLUG_TO_CODE[away], "home": SLUG_TO_CODE[home],
                "away_score": None, "home_score": None,
                "status": "scheduled", "kickoff_time": kickoff, "network": network,
                "nfl_url": f"https://www.nfl.com/games/{away}-at-{home}-{season}-reg-{week}",
            })
        else:
            raise FeedError(f"{path.name}:{lineno}: unrecognised schedule line: {line[:80]}")
    codes = [g["away"] for g in games] + [g["home"] for g in games]
    if len(set(codes)) != len(codes):
        dupes = sorted({c for c in codes if codes.count(c) > 1})
        raise FeedError(f"{path.name}: a club appears in two games in one week: {dupes}")
    if 2 * len(games) + len(byes) != 32:
        raise FeedError(f"{path.name}: 2x{len(games)} games + {len(byes)} byes != 32 clubs")
    for g in games:
        if g["away"] in byes or g["home"] in byes:
            raise FeedError(f"{path.name}: a bye club appears in a game: {g['game_id']}")
    return {"week": games[0]["week"] if games else None, "games": games, "byes": byes}


def load_feed() -> tuple[list[dict], list[dict], list[str], dict]:
    """Return (finals, upcoming, irregularities, feed_stats) from all transcriptions."""
    finals, upcoming, irregularities = [], [], []
    weeks = []
    for path in sorted(RAW.glob("week-*.txt")):
        data = parse_week_file(path)
        weeks.append(data["week"])
        finals.extend(g for g in data["games"] if g["status"] == "final")
        upcoming.extend(g for g in data["games"] if g["status"] == "scheduled")
    if weeks != list(range(1, 12)):
        raise FeedError(f"week files 1..11 expected, found {weeks}")
    # Integrity: a final must have non-negative scores, and game ids must be unique.
    ids = [g["game_id"] for g in finals + upcoming]
    if len(set(ids)) != len(ids):
        raise FeedError("duplicate game_id in feed")
    # Cross-check against the committed secondary snapshot where it has scores.
    secondary_path = ROOT / "data" / "raw" / "games.csv"
    secondary = {}
    if secondary_path.exists():
        with secondary_path.open() as fh:
            for row in csv.DictReader(fh):
                if row["season"] == "2026" and row["game_type"] == "REG":
                    secondary[(int(row["week"]), row["away_team"], row["home_team"])] = row
    checked_both = 0
    mismatches = 0
    for g in finals:
        row = secondary.get((g["week"], g["away"], g["home"]))
        if row and row["away_score"] and row["home_score"]:
            checked_both += 1
            if (int(row["away_score"]), int(row["home_score"])) != (g["away_score"], g["home_score"]):
                mismatches += 1
                irregularities.append(
                    f"{g['game_id']}: official {g['away_score']}-{g['home_score']} vs "
                    f"secondary {row['away_score']}-{row['home_score']}"
                )
    stale = sorted({g["week"] for g in finals
                    if not (secondary.get((g["week"], g["away"], g["home"])) or {}).get("away_score")})
    if stale:
        irregularities.append(
            "data/raw/games.csv (secondary, quarantined) has no scores for weeks "
            + ",".join(str(w) for w in stale)
            + "; those finals rest on the official transcription only"
        )
    feed_stats = {
        "finals": len(finals),
        "pending": len(upcoming),
        "cross_checked_vs_secondary": checked_both,
        "score_mismatches_vs_secondary": mismatches,
        "official_only_weeks": stale,
    }
    return finals, upcoming, irregularities, feed_stats


# ---------------------------------------------------------------- model (frozen)

def _mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs)


def _std(xs):
    xs = list(xs)
    if len(xs) < 2:
        return None
    m = _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def phi(x: float) -> float:
    """Standard normal CDF via math.erf (no third-party dependency)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def fit(finals: list[dict]) -> dict:
    """Frozen model fit on officially sourced finals only.

    off/def are points scored/allowed per game; hfa is mean home margin;
    sigma_margin/sigma_total are residual standard deviations of this same fit.
    Every parameter is published with its n on the origination page.
    """
    if len(finals) < 8:
        raise FeedError("model fit refuses to run on fewer than 8 verified finals")
    off, dfn = {}, {}
    for side in ("away", "home"):
        scored = [g[f"{side}_score"] for g in finals]
        allowed = [g["home_score" if side == "away" else "away_score"] for g in finals]
        for i, g in enumerate(finals):
            off.setdefault(g[side], []).append(scored[i])
            dfn.setdefault(g[side], []).append(allowed[i])
    off = {k: _mean(v) for k, v in off.items()}
    dfn = {k: _mean(v) for k, v in dfn.items()}
    hfa = _mean(g["home_score"] - g["away_score"] for g in finals)
    residuals_m, residuals_t = [], []
    for g in finals:
        ep_h = (off[g["home"]] + dfn[g["away"]]) / 2
        ep_a = (off[g["away"]] + dfn[g["home"]]) / 2
        residuals_m.append((g["home_score"] - g["away_score"]) - (ep_h - ep_a + hfa))
        residuals_t.append((g["home_score"] + g["away_score"]) - (ep_h + ep_a))
    return {
        "off": off, "def": dfn, "hfa": hfa,
        "sigma_margin": _std(residuals_m), "sigma_total": _std(residuals_t),
        "n": len(finals),
    }


def price(model: dict, game: dict) -> dict:
    """Price one game: side, total and moneyline from the same joint expectation."""
    ep_h = (model["off"][game["home"]] + model["def"][game["away"]]) / 2
    ep_a = (model["off"][game["away"]] + model["def"][game["home"]]) / 2
    margin = ep_h - ep_a + model["hfa"]
    total = ep_h + ep_a
    p_home = phi(margin / model["sigma_margin"])
    fair_home_line = -margin
    if p_home >= 0.5:
        ml_home_american = -int(round(100 * p_home / (1 - p_home)))
    else:
        ml_home_american = +int(round(100 * (1 - p_home) / p_home))
    return {
        "ep_home": ep_h, "ep_away": ep_a, "margin": margin, "total": total,
        "fair_home_line": fair_home_line,
        "fair_home_line_half": round(fair_home_line * 2) / 2,
        "p_home_win": p_home, "p_home_american": ml_home_american,
    }


# --------------------------------------------------------- origination and store

def originate(games: list[dict], model: dict, phase_open_ts: str,
              close_prices: dict[str, float] | None = None) -> tuple[list[dict], list[dict]]:
    """Originate side, then total, then moneyline for each game, in that order.

    Returns (markets, snapshots). The order rule is enforced mechanically: the
    total market cannot be created before the side market of the same game, and
    the moneyline cannot be created before the total. ``close_prices`` maps
    market_id -> close price; missing entries yield a pending close snapshot
    with a blank price (never a fabricated number).
    """
    close_prices = close_prices or {}
    markets, snapshots = [], []
    for game in games:
        p = price(model, game)
        seq = 0
        for mtype in ("side", "total", "ml"):
            seq += 1
            mid = f"{game['game_id']}#{mtype}"
            if mtype == "side":
                val = p["fair_home_line_half"]
            elif mtype == "total":
                val = round(p["total"] * 2) / 2
            else:
                val = p["p_home_american"]
            markets.append({
                "market_id": mid, "game_id": game["game_id"], "week": game["week"],
                "market_type": mtype, "origination_seq": seq, "side": f"{game['away']}@{game['home']}",
                "model_price": val,
                "model_price_unrounded": {"side": p["fair_home_line"], "total": p["total"],
                                          "ml": p["p_home_win"]}[mtype],
                "market_price": None, "difference": None,
                "n_fit": model["n"], "originated_at": phase_open_ts,
            })
            snapshots.append({
                "market_id": mid, "market_type": mtype, "game_id": game["game_id"],
                "phase": "open", "model_price": val, "market_price": None,
                "captured_at": phase_open_ts,
            })
            close_val = close_prices.get(mid)
            snapshots.append({
                "market_id": mid, "market_type": mtype, "game_id": game["game_id"],
                "phase": "close",
                "model_price": close_val,  # None stays blank: never fabricated
                "market_price": None,
                "captured_at": BUILD_TS if close_val is not None else None,
            })
    # Mechanical order check over the assembled board.
    seen: dict[str, set] = {}
    for m in markets:
        types = seen.setdefault(m["game_id"], set())
        if m["market_type"] == "total" and "side" not in types:
            raise OrderViolation(f"total originated before side for {m['game_id']}")
        if m["market_type"] == "ml" and "total" not in types:
            raise OrderViolation(f"moneyline originated before total for {m['game_id']}")
        types.add(m["market_type"])
    return markets, snapshots


def walk_forward(finals: list[dict], upcoming: list[dict], start_week: int = 3) -> list[dict]:
    """Originate each past week from strictly earlier verified finals, then score.

    Week w's markets are priced on a model fit that has never seen week w or
    later; the calls are scored against the official results of week w. This is
    a walk-forward diagnostic on official numbers, not a backtest of profit:
    with no executable market prices, ROI and CLV stay blank.
    """
    weeks = sorted({g["week"] for g in finals})
    rows = []
    for w in weeks:
        if w < start_week:
            continue
        train = [g for g in finals if g["week"] < w]
        evals = [g for g in finals if g["week"] == w]
        if not train or not evals:
            continue
        expected = len(evals) + len([g for g in upcoming if g["week"] == w])
        model = fit(train)
        picks, correct, ties, brier, mae_m, mae_t, bias = 0, 0, 0, 0.0, 0.0, 0.0, 0.0
        for g in evals:
            p = price(model, g)
            actual_m = g["home_score"] - g["away_score"]
            actual_t = g["home_score"] + g["away_score"]
            if abs(p["p_home_win"] - 0.5) < 1e-12:
                ties += 1
            else:
                picks += 1
                home_pick = p["p_home_win"] > 0.5
                home_won = actual_m > 0
                correct += 1 if home_pick == home_won else 0
            brier += (p["p_home_win"] - (1.0 if actual_m > 0 else 0.0 if actual_m < 0 else 0.5)) ** 2
            mae_m += abs(p["margin"] - actual_m)
            mae_t += abs(p["total"] - actual_t)
            bias += p["fair_home_line"] - (-actual_m)  # fair home line vs the line that ties actual
        n = len(evals)
        rows.append({
            "week": w, "n_fit": len(train), "n": n, "expected_games": expected,
            "complete": n == expected,
            "picks": picks, "ties": ties,
            "dir_acc": (correct / picks) if picks else None,
            "brier_home_win": brier / n,
            "mae_margin": mae_m / n, "mae_total": mae_t / n,
            "mean_fair_line_bias_vs_result": bias / n,
        })
    return rows


def brier_skill_panel(finals: list[dict], upcoming: list[dict], *,
                      start_week: int = 3, end_week: int = 9,
                      resamples: int = 2000, confidence: float = 0.95,
                      seed: int = 9) -> dict:
    """Pooled Brier skill vs a fixed 50/50 home-win forecast, with week clusters.

    Only complete, chronological holdout weeks are included. Every forecast for
    week ``w`` is fit on finals from weeks strictly before ``w``. Ties use a
    half-win target, matching ``walk_forward``. The percentile interval resamples
    whole weeks (not individual games); it is a descriptive uncertainty interval,
    assumes exchangeable week clusters, and is not adjusted for multiple model
    trials. This statistic does not remove luck or validate a strategy.
    """
    if type(start_week) is not int or start_week < 2:
        raise FeedError("start_week must be an integer >= 2")
    if end_week is not None and (type(end_week) is not int or end_week < start_week):
        raise FeedError("end_week must be an integer >= start_week")
    if type(resamples) is not int or resamples < 100:
        raise FeedError("at least 100 cluster bootstrap resamples are required")
    if not isinstance(confidence, (int, float)) or not 0 < confidence < 1:
        raise FeedError("confidence must be between zero and one")
    if type(seed) is not int:
        raise FeedError("seed must be an integer")

    weeks = sorted({g["week"] for g in finals})
    by_week = {}
    for week in weeks:
        if week < start_week or (end_week is not None and week > end_week):
            continue
        train = [g for g in finals if g["week"] < week]
        evals = [g for g in finals if g["week"] == week]
        expected = len(evals) + sum(g["week"] == week for g in upcoming)
        if not train or not evals or len(evals) != expected:
            continue
        model = fit(train)
        losses = []
        for game in evals:
            p_home = price(model, game)["p_home_win"]
            margin = game["home_score"] - game["away_score"]
            observed = 1.0 if margin > 0 else 0.0 if margin < 0 else 0.5
            model_loss = (p_home - observed) ** 2
            baseline_loss = (0.5 - observed) ** 2
            losses.append((model_loss, baseline_loss))
        by_week[week] = losses

    if len(by_week) < 2:
        raise FeedError("at least two complete week clusters are required")
    total_model = sum(m for rows in by_week.values() for m, _ in rows)
    total_base = sum(b for rows in by_week.values() for _, b in rows)
    if total_base <= 0:
        raise FeedError("Brier skill is undefined for an all-tie benchmark sample")
    n_games = sum(len(rows) for rows in by_week.values())
    brier_model = total_model / n_games
    brier_baseline = total_base / n_games
    skill = 1.0 - total_model / total_base

    # Resample complete weeks with replacement. Recompute the skill ratio in each
    # draw so the benchmark denominator remains paired with its sampled outcomes.
    rng = Random(seed)
    blocks = list(by_week.values())
    draws = []
    for _ in range(resamples):
        sampled = rng.choices(blocks, k=len(blocks))
        model_sum = sum(m for block in sampled for m, _ in block)
        base_sum = sum(b for block in sampled for _, b in block)
        if base_sum > 0:
            draws.append(1.0 - model_sum / base_sum)
    if len(draws) < max(100, resamples // 2):
        raise FeedError("too few valid cluster-bootstrap draws")
    draws.sort()

    def quantile(q):
        position = q * (len(draws) - 1)
        lower = int(position)
        upper = min(lower + 1, len(draws) - 1)
        fraction = position - lower
        return draws[lower] + fraction * (draws[upper] - draws[lower])

    alpha = (1.0 - float(confidence)) / 2.0
    return {
        "n_games": n_games,
        "n_weeks": len(by_week),
        "weeks": sorted(by_week),
        "model_brier": brier_model,
        "baseline_brier": brier_baseline,
        "brier_skill": skill,
        "ci_low": quantile(alpha),
        "ci_high": quantile(1.0 - alpha),
        "confidence": float(confidence),
        "resamples": resamples,
        "seed": seed,
        "benchmark": "constant 0.5 home-win probability; not market favorites",
        "interval_method": "percentile bootstrap of complete weeks; two-sided; exchangeability assumed",
        "multiplicity_adjusted": False,
    }


# ------------------------------------------------------------------ correlations

def pearson(xs, ys) -> tuple[float, int]:
    xs, ys = list(xs), list(ys)
    n = len(xs)
    if n != len(ys) or n < 3:
        raise FeedError("pearson needs two aligned lists of length >= 3")
    mx, my = _mean(xs), _mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return 0.0, n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return sxy / math.sqrt(sxx * syy), n


def fisher_ci(r: float, n: int, z: float = 1.959963985) -> tuple[float, float]:
    """95% CI for a Pearson r via Fisher z (matches the published scipy method)."""
    if n < 4:
        return (None, None)
    zr = math.atanh(r)
    se = 1 / math.sqrt(n - 3)
    return (math.tanh(zr - z * se), math.tanh(zr + z * se))


def correlations(finals: list[dict], deadband: float = 0.10) -> list[dict]:
    """Correlations computed ONLY from officially sourced numbers; n always published."""
    margins = [g["home_score"] - g["away_score"] for g in finals]
    totals = [g["home_score"] + g["away_score"] for g in finals]
    home_pts = [g["home_score"] for g in finals]
    away_pts = [g["away_score"] for g in finals]
    pairs = [
        ("game margin (home - away) vs game total (home + away)", margins, totals),
        ("home points vs away points (same game)", home_pts, away_pts),
    ]
    # Team margin persistence: same club, consecutive verified weeks.
    team_seq: dict[str, list[tuple[int, int]]] = {}
    for g in sorted(finals, key=lambda g: g["week"]):
        m = g["home_score"] - g["away_score"]
        team_seq.setdefault(g["home"], []).append((g["week"], m))
        team_seq.setdefault(g["away"], []).append((g["week"], -m))
    prevs, currs = [], []
    for club, seq in team_seq.items():
        seq.sort()
        for (_, m0), (_, m1) in zip(seq, seq[1:]):
            prevs.append(m0)
            currs.append(m1)
    pairs.append(("club margin in week t-1 vs club margin in week t", prevs, currs))
    out = []
    for label, xs, ys in pairs:
        r, n = pearson(xs, ys)
        lo, hi = fisher_ci(r, n)
        out.append({
            "pair": label, "n": n, "pearson_r": round(r, 4),
            "ci_low": None if lo is None else round(lo, 4),
            "ci_high": None if hi is None else round(hi, 4),
            "deadband": deadband,
            "dependence_claimed": "no (inside deadband)" if abs(r) < deadband else "declared (outside deadband)",
        })
    return out


# ------------------------------------------------------------- leaderboard split

def leaderboard(walk_rows: list[dict]) -> list[dict]:
    """Signal sheet and staking sheet kept disjoint.

    Signal columns are aggregated over COMPLETE walk-forward weeks only
    (officially settled full slates); a partial week is displayed on the
    diagnostics table but never folded into an aggregate. Signal columns are
    computed from official results only. Staking columns describe the plan;
    every price-dependent staking metric (ROI, CLV, closing comparison) is
    blank because no official source publishes wagering prices. The
    live-to-paper gate (session feaa600b, merged PR #34) is applied fail-closed:
    its operating parameters are unset, so every entry stays Paper.
    """
    complete = [r for r in walk_rows if r["complete"]]
    n_total = sum(r["n"] for r in complete)
    picks_total = sum(r["picks"] for r in complete)
    correct_total = sum(round((r["dir_acc"] or 0) * r["picks"]) for r in complete)
    # The aggregate is over the game-level predictions represented by n_total,
    # so weight weekly means by their evaluated game counts (not equally by week).
    brier_w = (sum(r["n"] * r["brier_home_win"] for r in complete) / n_total
               if n_total else None)
    mae_m_w = (sum(r["n"] * r["mae_margin"] for r in complete) / n_total
               if n_total else None)
    mae_t_w = (sum(r["n"] * r["mae_total"] for r in complete) / n_total
               if n_total else None)
    dir_acc = (correct_total / picks_total) if picks_total else None
    entries = []
    for key, label, sig in (
        ("side", "OWN-SIDE · walk-forward side model",
         {"dir_acc": dir_acc, "n_dir": picks_total, "mae": mae_m_w}),
        ("total", "OWN-TOTAL · walk-forward total model",
         {"dir_acc": None, "n_dir": 0, "mae": mae_t_w}),
        ("ml", "OWN-ML · walk-forward moneyline model",
         {"dir_acc": dir_acc, "n_dir": picks_total, "mae": None}),
    ):
        entries.append({
            "strategy": label,
            "status": "Paper",
            # The total model has no calibrated over/under probability here;
            # never copy a home-win Brier into that track.
            "signal": {"n_walk_games": n_total, **sig,
                       "brier_home_win": None if key == "total" else brier_w},
            "staking": {"plan": "flat 1 unit, singles only (parlay exposure not implemented)",
                        "roi": None, "clv": None, "exposure_cap": None},
            "gate": "Live-to-paper gate operating parameters unset -> live issuance blocked",
        })
    return entries


# ----------------------------------------------------------- replacement depth

def replacement_depth() -> list[dict]:
    """Structured replacement register: the depth travelled, not just the fact.

    Rows come from evidence already committed and source-verified on the shared
    pages: the official Game Books for WAS/NYG weeks 9-10 (actual lineup change),
    the official Week 10 injury report, and the club depth charts (KC, SEA, DET)
    that publish first/second/third/fourth-string columns. depth_travelled is 1
    for a second-string replacement, 2 for third-string, 3 for fourth-string;
    blank where no club chart was retrieved. Never inferred.
    """
    rows = [
        # team, slot, outgoing starter, status source, replacement, replacement status, depth, chart?
        ("WAS", "C (1st)", "Lucas Patrick", "Out W10 (concussion); started W9 per Game Book",
         "Nick Allegretti", "Started W10 per Game Book", None, "No WAS chart retrieved"),
        ("SEA", "QB (1st)", "Sam Darnold", "Out (report)", "Drew Lock", "No game status on report; league news: will start", 1, "SEA chart"),
        ("SEA", "LT (1st)", "Charles Cross", "Out (report)", "Josh Jones", "Not listed on report", 1, "SEA chart"),
        ("SEA", "LG (1st)", "Quenton Nelson", "Out (report)", "Anthony Bradford", "Not listed on report", 1, "SEA chart"),
        ("SEA", "DT slot 1 (1st)", "Leonard Williams", "Out (report)", "Rylie Mills", "Not listed on report", 1, "SEA chart"),
        ("KC", "RT (1st)", "Jaylon Moore", "Out (report)", "Joshua Ezeudu", "Not listed on report", 1, "KC chart"),
        ("KC", "RB (1st)", "Kenneth Walker III", "Questionable (report)", "Emmett Johnson",
         "Conditional: order applies only if starter cannot play", 1, "KC chart"),
        ("DET", "C (1st)", "Cade Mays", "Out (report)", "Juice Scruggs", "Not listed on report", 1, "DET chart"),
        ("DET", "CB slot 1 (1st)", "D.J. Reed", "Out (report)", "Rock Ya-Sin", "Not listed on report", 1, "DET chart"),
        ("DET", "S", "Kerby Joseph", "Out (report)", None,
         "Withheld: report and club chart conflict; no replacement may be inferred", None, "DET chart (conflict, F14)"),
        ("MIA", "QB (1st)", "Malik Willis", "IR (league news)", "Kyle McCord",
         "League news: in line for first start", None, "No MIA chart retrieved"),
        ("BAL", "QB (1st)", "Lamar Jackson", "IR (league news)", None,
         "Withheld: no verified chart or start announcement", None, "No BAL chart retrieved"),
        ("GB", "RB (1st)", "Josh Jacobs", "Out (report); league news: finger surgery", None,
         "Withheld: no GB chart retrieved; no replacement inferred", None, "No GB chart retrieved"),
    ]
    return [
        {"team": t, "slot": slot, "outgoing": out, "outgoing_status": ostat,
         "replacement": repl, "replacement_status": rstat,
         "depth_travelled": depth, "chart": chart}
        for t, slot, out, ostat, repl, rstat, depth, chart in rows
    ]


# ------------------------------------------------------------------------ export

def write_exports(finals: list[dict], upcoming: list[dict], markets: list[dict],
                  snapshots: list[dict], walk_rows: list[dict], corr_rows: list[dict],
                  lb_rows: list[dict], repl_rows: list[dict]) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    counts = {}

    def dump(name: str, header: list[str], rows: list[dict]) -> None:
        path = OUT / name
        with path.open("w", newline="") as fh:
            # LF line endings keep deterministic generated artifacts clean under
            # Git's whitespace checks on every platform.
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(header)
            for r in rows:
                w.writerow([("" if r.get(k) is None else r.get(k)) for k in header])
        counts[name] = len(rows)

    dump("results_2026.csv",
         ["game_id", "week", "kickoff_date", "weekday", "away", "away_score", "home", "home_score", "nfl_url"],
         sorted(finals, key=lambda g: (g["week"], g["game_id"])))
    dump("schedule_pending_2026.csv",
         ["game_id", "week", "kickoff_date", "weekday", "kickoff_time", "network", "away", "home", "nfl_url"],
         sorted(upcoming, key=lambda g: (g["week"], g["kickoff_date"], g["game_id"])))
    dump("markets_week11.csv",
         ["origination_seq", "week", "game_id", "market_id", "market_type", "side",
          "model_price", "model_price_unrounded", "market_price", "difference", "n_fit", "originated_at"],
         markets)
    dump("price_snapshots.csv",
         ["market_id", "market_type", "game_id", "phase", "model_price", "market_price", "captured_at"],
         snapshots)
    dump("walk_forward.csv",
         ["week", "n_fit", "n", "expected_games", "complete", "picks", "ties", "dir_acc",
          "brier_home_win", "mae_margin", "mae_total", "mean_fair_line_bias_vs_result"], walk_rows)
    dump("correlations.csv",
         ["pair", "n", "pearson_r", "ci_low", "ci_high", "deadband", "dependence_claimed"], corr_rows)
    dump("leaderboard.csv",
         ["strategy", "status", "n_walk_games", "dir_acc", "n_dir", "mae", "brier_home_win",
          "staking_plan", "roi", "clv", "exposure_cap", "gate"],
         [{"strategy": e["strategy"], "status": e["status"],
           "n_walk_games": e["signal"]["n_walk_games"], "dir_acc": e["signal"]["dir_acc"],
           "n_dir": e["signal"]["n_dir"], "mae": e["signal"]["mae"],
           "brier_home_win": e["signal"]["brier_home_win"],
           "staking_plan": e["staking"]["plan"], "roi": e["staking"]["roi"],
           "clv": e["staking"]["clv"], "exposure_cap": e["staking"]["exposure_cap"],
           "gate": e["gate"]} for e in lb_rows])
    dump("replacement_depth.csv",
         ["team", "slot", "outgoing", "outgoing_status", "replacement", "replacement_status",
          "depth_travelled", "chart"], repl_rows)
    return counts


def run() -> dict:
    """Execute the whole board pipeline and return every artefact for the pages."""
    finals, upcoming, irregularities, feed_stats = load_feed()
    live_model = fit(finals)
    w11 = [g for g in upcoming if g["week"] == 11]
    markets, snapshots = originate(w11, live_model, BUILD_TS)
    walk_rows = walk_forward(finals, upcoming)
    corr_rows = correlations(finals)
    lb_rows = leaderboard(walk_rows)
    skill_panel = brier_skill_panel(finals, upcoming)
    repl_rows = replacement_depth()
    counts = write_exports(finals, upcoming, markets, snapshots, walk_rows, corr_rows, lb_rows, repl_rows)
    return {
        "finals": finals, "upcoming": upcoming, "irregularities": irregularities,
        "feed_stats": feed_stats,
        "model": live_model, "markets": markets, "snapshots": snapshots,
        "walk_rows": walk_rows, "corr_rows": corr_rows, "lb_rows": lb_rows,
        "skill_panel": skill_panel,
        "repl_rows": repl_rows, "counts": counts, "week11_games": w11,
    }


if __name__ == "__main__":
    artefacts = run()
    print(f"finals verified: {len(artefacts['finals'])}; pending: {len(artefacts['upcoming'])}; "
          f"week-11 markets: {len(artefacts['markets'])}; snapshots: {len(artefacts['snapshots'])}")
    print("irregularities:", *artefacts["irregularities"], sep="\n  - " if artefacts["irregularities"] else " none")
    for row in artefacts["walk_rows"]:
        print("walk-forward", row)
    for row in artefacts["corr_rows"]:
        print("correlation", row)
