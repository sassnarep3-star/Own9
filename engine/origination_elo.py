"""Line origination from officially sourced results only, plus the demotion gate.

Session `arena/9a409d93-own9`. Everything here computes from the committed
verified results feed (`evidence/results/nfl-2026-results.json`), whose rows were
transcribed verbatim from the official NFL weekly schedule pages. No market
prices are loaded anywhere in this module: the NFL publishes no betting lines,
so every `market_line` field the store emits is `None` and every derived
`diff` is `None`. Model fair numbers are computed outputs from official inputs;
they carry no edge claim and no validation (see flags).

Origination order is fixed and tested: every side (spread) market is emitted
first, then every total, then every moneyline.

All constants below are predeclared conventions recorded before use, not
calibrations tuned on outcomes.
"""
import hashlib
import json
import math
from statistics import NormalDist, mean, stdev

# --- Predeclared model constants (elo-v1) -----------------------------------
ELO_START = 1500.0          # every team starts the season equal
K = 20.0                    # Elo update rate
HFA_ELO = 50.0              # home-field advantage in Elo points
ELO_PER_POINT = 25.0        # Elo -> points conversion for the fair spread
TOTAL_SHRINK = 0.5          # shrinkage of the raw total toward the league mean
TOTAL_WINDOW = 4            # rolling window (played games) for PF/PA
CONFIDENCE = 0.95

MOV_SCALER = 2.2            # margin-of-multiplier scale
MOV_RATING_SCALE = 400.0    # normalises the rating gap inside the MOV term

MARKET_ORDER = ("SPREAD", "TOTAL", "MONEYLINE")


def _finite(x):
    x = float(x)
    if not math.isfinite(x):
        raise ValueError("non-finite value")
    return x


def load_results(path):
    """Load the committed verified results feed; fail closed on surprises."""
    data = json.loads(path.read_text())
    games = []
    for week_label, week in sorted(data["weeks"].items(), key=lambda kv: int(kv[0])):
        for date, away, home, as_, hs, _slug in week["games"]:
            a, h = int(as_), int(hs)
            if a < 0 or h < 0:
                raise ValueError("negative score in results feed")
            games.append({"week": int(week_label), "date": date,
                          "away": away, "home": home,
                          "away_score": a, "home_score": h})
    return data, games


def run_elo(games):
    """Elo through the given games (chronological). Returns final ratings."""
    ratings = {t: ELO_START for g in games for t in (g["home"], g["away"])}
    for g in sorted(games, key=lambda g: (g["week"], g["date"])):
        rh, ra = ratings[g["home"]], ratings[g["away"]]
        dr = (rh + HFA_ELO) - ra
        exp_home = 1.0 / (1.0 + 10.0 ** (-dr / 400.0))
        margin = g["home_score"] - g["away_score"]
        if margin == 0:
            actual = 0.5
            mult = 0.0                      # a tie carries no margin signal
        elif margin > 0:
            actual = 1.0
            mult = _mov(margin, dr)
        else:
            actual = 0.0
            mult = _mov(-margin, -dr)
        ratings[g["home"]] = rh + K * mult * (actual - exp_home)
        ratings[g["away"]] = ra + K * mult * ((1.0 - actual) - (1.0 - exp_home))
    return ratings


def _mov(margin, rating_gap_of_winner):
    """Predeclared margin-of-victory multiplier (elo-v1 convention)."""
    return (math.log(margin + 1.0) * MOV_SCALER
            / (1.0 + 0.43 * max(0.0, rating_gap_of_winner) / MOV_RATING_SCALE))


def rolling_pf_pa(games, window=TOTAL_WINDOW):
    """Last-`window` played games points for/against per team, in feed order."""
    hist = {}
    for g in sorted(games, key=lambda g: (g["week"], g["date"])):
        for t in (g["home"], g["away"]):
            hist.setdefault(t, []).append(g)
    out = {}
    for t, gs in hist.items():
        last = gs[-window:]
        pf = mean([g["home_score"] if g["home"] == t else g["away_score"] for g in last])
        pa = mean([g["away_score"] if g["home"] == t else g["home_score"] for g in last])
        out[t] = (pf, pa, len(last))
    return out


def sample_stats(games):
    """Margins, totals, tie rate, sigma of margins — from official scores only."""
    margins = [g["home_score"] - g["away_score"] for g in games]
    totals = [g["home_score"] + g["away_score"] for g in games]
    return {
        "n_games": len(games),
        "tie_rate": sum(1 for m in margins if m == 0) / len(margins),
        "sigma_margin": stdev(margins),
        "mean_total": mean(totals),
        "mean_margin": mean(margins),
    }


def fair_spread(ratings, home, away):
    """Fair home spread in points; negative means the home team gives points."""
    return ((ratings[home] + HFA_ELO) - ratings[away]) / ELO_PER_POINT


def fair_total(ratings_stats, rollings, home, away):
    pf_h, pa_h, _ = rollings[home]
    pf_a, pa_a, _ = rollings[away]
    raw = 0.5 * (pf_h + pa_a) + 0.5 * (pf_a + pa_h)
    lg = ratings_stats["mean_total"]
    return TOTAL_SHRINK * raw + (1.0 - TOTAL_SHRINK) * lg


def fair_moneylines(spread_points, sigma_margin, tie_rate):
    """Two-way fair prices under the documented normal-margin approximation.

    P(home win) = (1 - tie_rate) * Phi(spread / sigma_margin); the residual
    tie_rate mass is the tie state, which pushes (operator rule, see the
    registered DraftKings market-rule source). Prices are decimal->American
    via the unit-tested core conversions.
    """
    from engine.core import decimal_to_american
    sigma = _finite(sigma_margin)
    if sigma <= 0:
        raise ValueError("sigma must be positive")
    p_home_win = (1.0 - tie_rate) * NormalDist().cdf(_finite(spread_points) / sigma)
    p_away_win = (1.0 - tie_rate) * (1.0 - NormalDist().cdf(_finite(spread_points) / sigma))
    if p_home_win <= 0 or p_away_win <= 0:
        raise ValueError("degenerate win probability")
    return {
        "p_home": p_home_win, "p_away": p_away_win, "p_tie": tie_rate,
        "home_american": round(decimal_to_american(1.0 / p_home_win)),
        "away_american": round(decimal_to_american(1.0 / p_away_win)),
    }


def originate(results_path, week10_path, opened_at):
    """Emit the Week 10 price-snapshot store in origination order.

    Side markets first, then totals, then moneylines. `market_line` is None
    everywhere because no official market price exists; `closed_at` is None
    until the scheduled close-capture workflow records it pre-kickoff.
    """
    data, games = load_results(results_path)
    w10 = json.loads(week10_path.read_text())
    ratings = run_elo(games)
    stats = sample_stats(games)
    rollings = rolling_pf_pa(games)
    inputs_sha = hashlib.sha256(results_path.read_bytes()).hexdigest()

    markets = []
    for g in w10["games"]:
        home, away = g["home"], g["away"]
        game_label = f"{away} @ {home}"
        if g["status"] == "FINAL":
            continue  # kickoff preceded store deployment; nothing to originate
        s = fair_spread(ratings, home, away)
        t = fair_total(stats, rollings, home, away)
        ml = fair_moneylines(s, stats["sigma_margin"], stats["tie_rate"])
        markets.append({
            "market_id": f"2026-w10-{away}-{home}-SPREAD",
            "game": game_label, "season": 2026, "week": 10,
            "market_type": "SPREAD", "selection": f"{away} @ {home} home handicap",
            "model_fair": round(s, 1),
            "model_fair_units": "points (negative = home gives points)",
            "market_line": None, "market_line_source": None, "diff": None,
            "opened_at": opened_at, "closed_at": None,
            "status": "open · close capture pending",
        })
        markets.append({
            "market_id": f"2026-w10-{away}-{home}-TOTAL",
            "game": game_label, "season": 2026, "week": 10,
            "market_type": "TOTAL", "selection": f"{away} @ {home} total points",
            "model_fair": round(t, 1),
            "model_fair_units": "points",
            "market_line": None, "market_line_source": None, "diff": None,
            "opened_at": opened_at, "closed_at": None,
            "status": "open · close capture pending",
        })
        markets.append({
            "market_id": f"2026-w10-{away}-{home}-ML-HOME",
            "game": game_label, "season": 2026, "week": 10,
            "market_type": "MONEYLINE", "selection": f"{home} (home) moneyline",
            "model_fair": ml["home_american"],
            "model_fair_units": "American odds (fair, no margin)",
            "market_line": None, "market_line_source": None, "diff": None,
            "opened_at": opened_at, "closed_at": None,
            "status": "open · close capture pending",
        })
        markets.append({
            "market_id": f"2026-w10-{away}-{home}-ML-AWAY",
            "game": game_label, "season": 2026, "week": 10,
            "market_type": "MONEYLINE", "selection": f"{away} (away) moneyline",
            "model_fair": ml["away_american"],
            "model_fair_units": "American odds (fair, no margin)",
            "market_line": None, "market_line_source": None, "diff": None,
            "opened_at": opened_at, "closed_at": None,
            "status": "open · close capture pending",
        })

    order_index = {m: i for i, m in enumerate(MARKET_ORDER)}
    markets.sort(key=lambda m: order_index[m["market_type"]])
    return {
        "meta": {
            "store": "Own9 price-snapshot store (v1, elo-v1 origination)",
            "origination_order": list(MARKET_ORDER),
            "opened_at": opened_at,
            "inputs": {"results_feed": str(results_path.name), "results_feed_sha256": inputs_sha},
            "method": {
                "id": "elo-v1",
                "inputs": "official final scores only (verified results feed)",
                "constants": {
                    "elo_start": ELO_START, "k": K, "hfa_elo": HFA_ELO,
                    "elo_per_point": ELO_PER_POINT, "total_shrink": TOTAL_SHRINK,
                    "total_window": TOTAL_WINDOW,
                    "mov_scaler": MOV_SCALER, "mov_rating_scale": MOV_RATING_SCALE,
                },
                "sample_stats": {
                    "n_games": stats["n_games"],
                    "tie_rate": round(stats["tie_rate"], 6),
                    "sigma_margin": round(stats["sigma_margin"], 3),
                    "mean_total": round(stats["mean_total"], 3),
                    "mean_margin": round(stats["mean_margin"], 3),
                },
                "market_line_policy": ("always null: the NFL publishes no betting lines; "
                                       "no officially verifiable market price is available, "
                                       "so the difference column stays blank (flagged)"),
            },
        },
        "markets": markets,
    }


# --- Demotion gate (live -> paper) -------------------------------------------
DEMOTION_THRESHOLDS = {
    "min_trailing_bets": 20,     # below this, no demotion decision is made
    "roi_floor": -0.10,          # trailing-20 flat-stake ROI (per unit) below -10% demotes
    "edge_floor": 0.0,           # trailing mean (model - market) edge <= 0 demotes
    "clv_rate_floor": 0.40,      # closing-line-value positive in <40% of bets demotes
    "brier_ceiling_base": 0.25,  # trailing Brier above base + tolerance demotes
    "brier_tolerance": 0.02,
    "feed_staleness_days": 7,    # inputs older than 7 days demote to paper
}


def demotion_gate(trailing, thresholds=None):
    """Decide whether a live strategy stays live or returns to paper.

    `trailing` carries the trailing-window metrics of a LIVE strategy:
    n_bets, roi_flat, mean_edge, clv_rate, brier, feed_age_days.
    Fails closed: with fewer than min_trailing_bets no demotion is issued and
    the reason is reported; the strategy remains live but is flagged
    unmonitorable. Returns (decision, reasons); decision in
    {"keep_live", "demote_to_paper", "unmonitorable"}.
    """
    th = dict(DEMOTION_THRESHOLDS if thresholds is None else thresholds)
    reasons = []
    n = trailing.get("n_bets", 0)
    if n < th["min_trailing_bets"]:
        return "unmonitorable", [f"trailing bets {n} < {th['min_trailing_bets']}; "
                                 "demotion gate cannot evaluate (fail-closed)"]
    if _finite(trailing["roi_flat"]) < th["roi_floor"]:
        reasons.append(f"trailing ROI {trailing['roi_flat']:.3f} < {th['roi_floor']}")
    if _finite(trailing["mean_edge"]) <= th["edge_floor"]:
        reasons.append(f"trailing mean edge {trailing['mean_edge']:.3f} <= {th['edge_floor']}")
    if _finite(trailing["clv_rate"]) < th["clv_rate_floor"]:
        reasons.append(f"CLV-positive rate {trailing['clv_rate']:.2f} < {th['clv_rate_floor']}")
    if _finite(trailing["brier"]) > th["brier_ceiling_base"] + th["brier_tolerance"]:
        reasons.append(f"trailing Brier {trailing['brier']:.3f} exceeds "
                       f"{th['brier_ceiling_base'] + th['brier_tolerance']:.2f}")
    if _finite(trailing["feed_age_days"]) > th["feed_staleness_days"]:
        reasons.append(f"results feed stale {trailing['feed_age_days']:.0f}d > "
                       f"{th['feed_staleness_days']}d")
    return ("demote_to_paper", reasons) if reasons else ("keep_live", ["all thresholds inside bounds"])
