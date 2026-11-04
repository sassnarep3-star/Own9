"""Auditable mathematical primitives; sources and assumptions in methodology.html.

These functions calculate from supplied inputs. They never certify their inputs as
league-verified, manufacture missing values, or demonstrate a profitable edge.
"""
import math
import random
from datetime import datetime
from statistics import mean


def finite(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('finite numeric value required')
    return float(value)


def probability(value):
    value = finite(value)
    if not 0 <= value <= 1:
        raise ValueError('probability outside [0, 1]')
    return value


def decimal_odds(american):
    american = finite(american)
    if abs(american) < 100:
        raise ValueError('American odds must be <= -100 or >= +100')
    return 1 + (american / 100 if american > 0 else 100 / -american)


def normalized_implied(decimal_prices):
    """Proportional no-vig convention for exhaustive mutually exclusive outcomes.

    Not an estimate of truth; inappropriate for unrelated parlay legs.
    """
    prices = [finite(x) for x in decimal_prices]
    if len(prices) < 2 or any(x <= 1 for x in prices):
        raise ValueError('at least two decimal odds > 1 required')
    implied = [1 / x for x in prices]
    return [x / sum(implied) for x in implied]


def expected_return(p_win, p_push_or_void, decimal_price):
    p_win, refund = probability(p_win), probability(p_push_or_void)
    price = finite(decimal_price)
    if p_win + refund > 1 + 1e-12 or price <= 1:
        raise ValueError('invalid settlement probabilities or price')
    return p_win * price + refund - 1


def fair_decimal(p_win, p_push_or_void=0):
    p_win, refund = probability(p_win), probability(p_push_or_void)
    if p_win + refund > 1 + 1e-12:
        raise ValueError('settlement probabilities exceed one')
    return None if p_win == 0 else (1 - refund) / p_win


def score_lines(score_pmf, home_handicap=0, total_line=0):
    """Integrate a supplied discrete joint score PMF (home, away, probability).

    Handicap is ADDED to home score: -3 means home must win by more than 3.
    Ties are refunds for the specified two-way moneyline convention only.
    No independence/Poisson assumption; no fitted PMF is included in this repo.
    """
    home_handicap, total_line = finite(home_handicap), finite(total_line)
    cells, seen = [], set()
    for home, away, weight in score_pmf:
        if any(isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in (home, away)):
            raise ValueError('scores must be nonnegative integers')
        if (home, away) in seen:
            raise ValueError('duplicate score cell')
        seen.add((home, away))
        cells.append((home, away, probability(weight)))
    if not cells or not math.isclose(sum(p for _, _, p in cells), 1, abs_tol=1e-9, rel_tol=0):
        raise ValueError('PMF mass must equal one; missing tail mass cannot be normalized away')
    result = {}
    for name, value in [('moneyline', lambda h, a: h-a),
                        ('spread', lambda h, a: h-a+home_handicap),
                        ('total_over', lambda h, a: h+a-total_line)]:
        win = sum(p for h, a, p in cells if value(h, a) > 0)
        push = sum(p for h, a, p in cells if value(h, a) == 0)
        result[name] = {'win': win, 'push': push, 'loss': max(0, 1-win-push),
                        'fair_decimal': fair_decimal(win, push)}
    return result


def binary_joint(p_a, p_b, rho):
    """Two binary legs with no pushes/voids; reject infeasible correlations.

    This algebraic identity is not a fitted joint model and does not extend
    pairwise correlations into a unique distribution for three or more legs.
    """
    a, b, rho = probability(p_a), probability(p_b), finite(rho)
    if not -1 <= rho <= 1 or a in (0, 1) or b in (0, 1):
        raise ValueError('nondegenerate marginals and rho in [-1,1] required')
    joint = a*b + rho * math.sqrt(a*(1-a)*b*(1-b))
    lower, upper = max(0, a+b-1), min(a, b)
    if joint < lower-1e-12 or joint > upper+1e-12:
        raise ValueError('joint probability violates Frechet bounds')
    return min(upper, max(lower, joint))


def phi(pairs):
    pairs = list(pairs)
    if not pairs:
        return None
    if any(a not in (0, 1) or b not in (0, 1) for a, b in pairs):
        raise ValueError('binary settled outcomes only; do not encode voids as losses')
    a, b = mean(x for x, _ in pairs), mean(y for _, y in pairs)
    denominator = math.sqrt(a*(1-a)*b*(1-b))
    return None if denominator == 0 else max(-1, min(1, (mean(x*y for x, y in pairs)-a*b)/denominator))


def cluster_correlation(rows, resamples=2000, seed=9, min_clusters=30):
    """Percentile 95% cluster-bootstrap interval (project policy, not a theorem).

    rows: (predeclared independent cluster ID, binary leg A, binary leg B).
    Entire clusters are sampled with replacement. Serial dependence between
    clusters invalidates this interval; use larger time blocks in that case.
    Degenerate replicates fail closed rather than being silently dropped.
    """
    if not isinstance(resamples, int) or resamples < 100 or min_clusters < 2:
        raise ValueError('invalid bootstrap configuration')
    groups = {}
    for group, a, b in rows:
        if not isinstance(group, str) or not group.strip():
            raise ValueError('nonempty cluster ID required')
        groups.setdefault(group, []).append((a, b))
    pairs = [pair for group in groups.values() for pair in group]
    r = phi(pairs)
    result = {'n': len(pairs), 'clusters': len(groups), 'rho': r,
              'ci_low': None, 'ci_high': None, 'status': 'insufficient evidence'}
    if r is None or len(groups) < min_clusters:
        return result
    rng, keys, values = random.Random(seed), list(groups), []
    for _ in range(resamples):
        sample = [pair for key in rng.choices(keys, k=len(keys)) for pair in groups[key]]
        estimate = phi(sample)
        if estimate is None:
            result['status'] = 'degenerate bootstrap; interval withheld'
            return result
        values.append(estimate)
    values.sort()
    result.update(ci_low=values[int(.025*(resamples-1))],
                  ci_high=values[math.ceil(.975*(resamples-1))], status='exploratory estimate')
    return result


def binary_metrics(predictions, outcomes):
    predictions, outcomes = list(predictions), list(outcomes)
    if not predictions or len(predictions) != len(outcomes):
        raise ValueError('aligned nonempty predictions/outcomes required')
    if any(y not in (0, 1) for y in outcomes):
        raise ValueError('binary outcomes required')
    predictions = [probability(p) for p in predictions]
    # Exact impossible predictions receive infinite loss, not a hidden clipping rule.
    losses = [-math.log(p if y else 1-p) if (p if y else 1-p) else math.inf
              for p, y in zip(predictions, outcomes)]
    return {'n': len(outcomes), 'brier': mean((p-y)**2 for p,y in zip(predictions,outcomes)),
            'log_loss': mean(losses)}


def holm_adjust(pvalues):
    values = [probability(p) for p in pvalues]
    order, adjusted, maximum = sorted(range(len(values)), key=values.__getitem__), [0]*len(values), 0
    for rank, index in enumerate(order):
        maximum = max(maximum, min(1, (len(values)-rank)*values[index]))
        adjusted[index] = maximum
    return adjusted


def utc_time(value):
    if not isinstance(value, str):
        raise ValueError('ISO 8601 timestamp required')
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError('timezone required')
    return dt


def audit_record(record):
    """Structural checks only; URL presence and a hash never verify truth."""
    required = ('id', 'game_id', 'strategy_id', 'feature_available_at', 'quote_at',
                'forecast_at', 'kickoff_at', 'outcome_at', 'source_url',
                'quote_source_url', 'snapshot_sha256', 'rules_url', 'outcome')
    errors = [f'missing {key}' for key in required if record.get(key) in (None, '')]
    if errors:
        return errors
    try:
        feature, quote, forecast, kickoff, outcome = [utc_time(record[k]) for k in
            ('feature_available_at', 'quote_at', 'forecast_at', 'kickoff_at', 'outcome_at')]
        if not (feature <= forecast and quote <= forecast < kickoff < outcome):
            errors.append('point-in-time ordering violated')
    except (ValueError, TypeError):
        errors.append('invalid timestamp')
    from urllib.parse import urlparse
    for key in ('source_url', 'quote_source_url', 'rules_url'):
        try:
            url = urlparse(record[key])
            if url.scheme != 'https' or not url.hostname:
                errors.append(f'invalid {key}')
        except (TypeError, ValueError, AttributeError):
            errors.append(f'invalid {key}')
    digest = record['snapshot_sha256']
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        errors.append('invalid snapshot hash')
    if record['outcome'] not in ('win', 'loss', 'push', 'void'):
        errors.append('invalid settlement')
    return errors
