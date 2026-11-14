"""Scoring, uncertainty and settlement arithmetic.

Every function here takes supplied numbers and returns either a number or None.
None propagates: a missing input never becomes a zero.
"""

import math

Z95 = 1.959963984540054


def mean(xs):
    if not xs:
        return None
    return sum(xs) / len(xs)


def sd(xs):
    if len(xs) < 2:
        return None
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def log_loss(probabilities, outcomes):
    """Mean log-loss. Probabilities are clipped away from 0 and 1 to stay finite."""
    if not probabilities:
        return None
    total = 0.0
    for p, y in zip(probabilities, outcomes):
        p = min(max(p, 1e-12), 1 - 1e-12)
        total += -(y * math.log(p) + (1 - y) * math.log(1 - p))
    return total / len(probabilities)


def brier(probabilities, outcomes):
    if not probabilities:
        return None
    return sum((p - y) ** 2 for p, y in zip(probabilities, outcomes)) / len(probabilities)


def cluster_robust_lcb(diffs, clusters, z=Z95):
    """Lower confidence bound on the mean of `diffs`, clustered by `clusters`.

    Cluster-robust because bets inside the same week share opponents, weather and
    injury news; treating them as independent would understate the uncertainty.
    Returns (mean, standard error, lower bound, number of clusters).
    """
    if len(diffs) < 2:
        return None
    m = mean(diffs)
    sums = {}
    for value, cluster in zip(diffs, clusters):
        sums[cluster] = sums.get(cluster, 0.0) + (value - m)
    g = len(sums)
    if g < 2:
        return None
    n = len(diffs)
    scale = g / (g - 1) * (n - 1) / (n - 1) if n > 1 else 1.0
    variance = scale * sum(v * v for v in sums.values()) / (n * n)
    se = math.sqrt(variance)
    return {'mean': m, 'se': se, 'lcb': m - z * se, 'clusters': g, 'n': n}


def paired_log_loss_gain(model_probs, market_probs, outcomes, clusters):
    """Per-bet log-loss improvement of the model over the market baseline.

    Positive means the model scored the outcome better. Returns the clustered
    lower confidence bound, which is the number the leaderboard ranks on.
    """
    diffs = []
    for pm, pk, y in zip(model_probs, market_probs, outcomes):
        pkm = min(max(pm, 1e-12), 1 - 1e-12)
        pkk = min(max(pk, 1e-12), 1 - 1e-12)
        diffs.append(-(y * math.log(pkk) + (1 - y) * math.log(1 - pkk))
                     + (y * math.log(pkm) + (1 - y) * math.log(1 - pkm)))
    return cluster_robust_lcb(diffs, clusters)


def roi(returns, stakes):
    """Net return per unit staked. Returns None when nothing was staked."""
    total_stake = sum(stakes)
    if total_stake <= 0:
        return None
    return sum(returns) / total_stake


def max_drawdown(returns_sequence):
    """Largest peak-to-trough decline of the cumulative net-return series."""
    peak = 0.0
    cumulative = 0.0
    worst = 0.0
    for value in returns_sequence:
        cumulative += value
        peak = max(peak, cumulative)
        worst = min(worst, cumulative - peak)
    return worst


def pearson(xs, ys):
    """Pearson r with n. Returns None when undefined (constant or n < 3)."""
    n = len(xs)
    if n < 3 or n != len(ys):
        return None
    mx, my = mean(xs), mean(ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None
    return {'r': sxy / math.sqrt(sxx * syy), 'n': n}


def fisher_z_interval(r, n, z=Z95):
    """Fisher z-transform interval for a Pearson correlation."""
    if r is None or n is None or n < 4 or abs(r) >= 1:
        return None
    zr = 0.5 * math.log((1 + r) / (1 - r))
    se = 1.0 / math.sqrt(n - 3)
    lo = zr - z * se
    hi = zr + z * se
    return {'r': r, 'n': n, 'lo': math.tanh(lo), 'hi': math.tanh(hi)}


def phi_coefficient(xs, ys):
    """Pearson r computed on 0/1 legs, i.e. the phi coefficient."""
    return pearson([1.0 if x else 0.0 for x in xs], [1.0 if y else 0.0 for y in ys])


def frechet_bounds(p, q):
    """Sharp bounds on a joint probability given its two marginals."""
    return max(0.0, p + q - 1.0), min(p, q)


def joint_from_correlation(p, q, rho):
    """Two-leg joint probability under a Gaussian-copula dependence."""
    if rho is None:
        return None
    value = p * q + rho * math.sqrt(p * (1 - p) * q * (1 - q))
    lo, hi = frechet_bounds(p, q)
    return min(hi, max(lo, value))


def kelly_fraction(p, decimal_odds, cap=0.25):
    """Fractional Kelly stake with a hard cap. Zero when there is no edge."""
    if p is None or decimal_odds is None or decimal_odds <= 1:
        return 0.0
    b = decimal_odds - 1.0
    q = 1.0 - p
    raw = (b * p - q) / b
    if raw <= 0:
        return 0.0
    return min(cap, raw)


def settlement(market, home_score, away_score, quote_line):
    """Recompute a settlement state from the two final scores.

    Returns 1 (win), 0 (loss) or 0.5 (push) for the side named in the call.
    """
    home, away = int(home_score), int(away_score)
    margin = home - away
    total = home + away
    if market == 'SIDE':
        if quote_line is None:
            return None
        if margin == quote_line:
            return 0.5
        return 1.0 if margin > quote_line else 0.0
    if market == 'TOTAL':
        if quote_line is None:
            return None
        if total == quote_line:
            return 0.5
        return 1.0 if total > quote_line else 0.0
    if margin == 0:
        return 0.5
    return 1.0 if margin > 0 else 0.0
