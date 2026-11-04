"""Dependency-free, deterministic pricing and research primitives.

Inputs are supplied distributions/observations, NOT verified NFL predictions.
See research/METHODOLOGY.md for assumptions and evidence requirements.
"""
from collections import defaultdict
from dataclasses import dataclass
from math import isfinite, log, sqrt
from random import Random
from statistics import mean


def finite(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError('expected a finite number')
    return float(value)


def probability(value):
    value = finite(value)
    if not 0 <= value <= 1:
        raise ValueError('probability outside [0, 1]')
    return value


def american_to_decimal(odds):
    odds = finite(odds)
    if abs(odds) < 100:
        raise ValueError('standard American odds require |odds| >= 100')
    return 1 + (odds / 100 if odds > 0 else 100 / -odds)


def decimal_to_american(odds):
    odds = finite(odds)
    if odds <= 1:
        raise ValueError('decimal odds must exceed 1')
    return (odds - 1) * 100 if odds >= 2 else -100 / (odds - 1)


def no_vig(decimal_prices):
    """Proportional normalization, a modeling convention, not true probability.

Use only an exhaustive, mutually exclusive market with matching settlement.
"""
    if len(decimal_prices) < 2:
        raise ValueError('need an exhaustive market with >=2 outcomes')
    if any(finite(d) <= 1 for d in decimal_prices):
        raise ValueError('decimal odds must exceed 1')
    inv = [1 / d for d in decimal_prices]
    return [x / sum(inv) for x in inv]


@dataclass(frozen=True)
class Outcome:
    win: float
    push: float
    loss: float

    def __post_init__(self):
        for p in (self.win, self.push, self.loss):
            probability(p)
        if abs(self.win + self.push + self.loss - 1) > 1e-9:
            raise ValueError('outcome mass must sum to one')

    def fair_decimal(self):
        # Push refunds stake. If no possible win, no finite fair price.
        return None if self.win == 0 else 1 + self.loss / self.win

    def ev(self, decimal_price, cost=0):
        d, c = finite(decimal_price), finite(cost)
        if d <= 1 or c < 0:
            raise ValueError('invalid quote or cost')
        return self.win * (d - 1) - self.loss - c


def score_market(distribution, market, line=0):
    """Discrete joint score PMF -> home moneyline/spread or total-over outcome.

    Scores include any overtime required by the verified ticket. A home spread
    adds `line` to home score (negative = home favorite). Two-way tie = push
    is an explicit assumption, not universal sportsbook settlement.
    """
    if market not in ('moneyline', 'spread', 'total_over'):
        raise ValueError('unsupported market')
    line = finite(line)
    if not distribution:
        raise ValueError('missing joint score distribution')
    w = p = l = total = 0.0
    for scores, mass in distribution.items():
        if len(scores) != 2 or any(type(s) is not int or s < 0 for s in scores):
            raise ValueError('scores must be two nonnegative integers')
        mass = probability(mass)
        home, away = scores
        margin = home - away if market == 'moneyline' else home - away + line if market == 'spread' else home + away - line
        total += mass
        if margin > 0:
            w += mass
        elif margin == 0:
            p += mass
        else:
            l += mass
    if abs(total - 1) > 1e-9:
        raise ValueError('PMF must sum to one; do not silently renormalize tails')
    return Outcome(w, p, l)


def distribution_lines(distribution):
    """Return median-based reference lines, not executable sportsbook quotes."""
    score_market(distribution, 'moneyline')  # validates joint PMF
    margins, totals = defaultdict(float), defaultdict(float)
    for (h, a), p in distribution.items():
        margins[h - a] += p
        totals[h + a] += p
    def median(pmf):
        cumulative = 0
        for x, p in sorted(pmf.items()):
            cumulative += p
            if cumulative >= .5 - 1e-12:
                return x
    return {'home_spread_reference': -median(margins), 'total_reference': median(totals),
            'home_moneyline_fair_decimal': score_market(distribution, 'moneyline').fair_decimal()}


def bernoulli_joint(p_a, p_b, rho):
    """For TWO binary non-push events only; reject infeasible correlations."""
    a, b, r = probability(p_a), probability(p_b), finite(rho)
    if not -1 <= r <= 1:
        raise ValueError('correlation outside [-1, 1]')
    scale = sqrt(a * (1 - a) * b * (1 - b))
    if scale == 0:
        raise ValueError('correlation undefined for deterministic event')
    joint = a * b + r * scale
    if joint < max(0, a + b - 1) - 1e-12 or joint > min(a, b) + 1e-12:
        raise ValueError('correlation violates Frechet bounds')
    return min(min(a, b), max(max(0, a + b - 1), joint))


def sample_joint_hit(rows):
    """Empirical all-leg hit frequency. Sampling error is not model uncertainty."""
    if not rows or not rows[0] or any(len(r) != len(rows[0]) for r in rows):
        raise ValueError('nonempty rectangular joint sample required')
    if any(type(v) is not bool for r in rows for v in r):
        raise ValueError('binary booleans only; handle push/void states separately')
    return sum(all(r) for r in rows) / len(rows)


def pearson(x, y):
    if len(x) != len(y) or len(x) < 2:
        raise ValueError('need >=2 paired values')
    x, y = [finite(v) for v in x], [finite(v) for v in y]
    mx, my = mean(x), mean(y)
    xx, yy = sum((v - mx)**2 for v in x), sum((v - my)**2 for v in y)
    if xx == 0 or yy == 0:
        return None  # Undefined, not zero correlation.
    return max(-1, min(1, sum((a-mx)*(b-my) for a,b in zip(x,y)) / sqrt(xx*yy)))


def probability_scores(predictions, outcomes):
    """Binary non-push observations only. No clipping of impossible forecasts."""
    if not predictions or len(predictions) != len(outcomes):
        raise ValueError('nonempty paired predictions and labels required')
    ps = [probability(p) for p in predictions]
    if any(type(y) is not int or y not in (0, 1) for y in outcomes):
        raise ValueError('labels must be integers 0 or 1')
    losses = [float('inf') if (p == 0 and y == 1) or (p == 1 and y == 0)
              else -log(p if y else 1-p) for p,y in zip(ps,outcomes)]
    return {'brier': mean((p-y)**2 for p,y in zip(ps,outcomes)), 'log_loss': mean(losses)}


def reliability_bins(predictions, outcomes, n_bins=10):
    probability_scores(predictions, outcomes)
    if type(n_bins) is not int or n_bins < 1:
        raise ValueError('positive integer bin count required')
    buckets = [[] for _ in range(n_bins)]
    for p, y in zip(predictions, outcomes):
        buckets[min(int(p * n_bins), n_bins - 1)].append((p,y))
    return [{'n': len(b), 'mean_p': mean(p for p,y in b) if b else None,
             'hit_rate': mean(y for p,y in b) if b else None} for b in buckets]


def holm_adjust(pvalues):
    """Holm step-down adjusted p-values, in original registration order."""
    ps = [probability(p) for p in pvalues]
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adjusted, previous = [0.0] * len(ps), 0.0
    for k, i in enumerate(order):
        previous = max(previous, min(1.0, (len(ps) - k) * ps[i]))
        adjusted[i] = previous
    return adjusted


def week_bootstrap_ci(values, weeks, resamples=2000, confidence=.95, seed=9):
    """Cluster-percentile interval on per-observation mean; resample whole weeks.

    Equal probability for each observed week; unequal-sized weeks contribute
    their original number of observations when drawn. Assumes exchangeable
    week clusters; not valid under arbitrary cross-week dependence/drift.
    """
    if not values or len(values) != len(weeks):
        raise ValueError('paired values and week IDs required')
    if not 0 < finite(confidence) < 1 or type(resamples) is not int or resamples < 100:
        raise ValueError('invalid confidence or too few resamples')
    groups = defaultdict(list)
    for v,w in zip(values,weeks):
        if w is None or w == '':
            raise ValueError('missing week ID')
        groups[w].append(finite(v))
    blocks = list(groups.values())
    if len(blocks) < 2:
        raise ValueError('at least two independent week blocks required')
    rng = Random(seed)
    sims = sorted(mean(v for b in rng.choices(blocks,k=len(blocks)) for v in b) for _ in range(resamples))
    def quantile(q):
        at = q * (len(sims)-1)
        lo = int(at)
        hi = min(lo+1,len(sims)-1)
        return sims[lo] + (at-lo)*(sims[hi]-sims[lo])
    alpha = (1-confidence)/2
    return (quantile(alpha),quantile(1-alpha))


def walk_forward(week_ids, min_train_weeks, gap_weeks=0):
    """Ordered (season, week) or sortable IDs; entire week held out per fold."""
    if type(min_train_weeks) is not int or min_train_weeks < 1 or type(gap_weeks) is not int or gap_weeks < 0:
        raise ValueError('invalid train/gap week counts')
    weeks = sorted(set(week_ids))
    for pos in range(min_train_weeks+gap_weeks,len(weeks)):
        train = set(weeks[:pos-gap_weeks])
        test = weeks[pos]
        yield ([i for i,w in enumerate(week_ids) if w in train], [i for i,w in enumerate(week_ids) if w == test])


GATE_IDS = tuple(f'G{i:02}' for i in range(1,12))


def eligibility(gates):
    """Fail closed. Evidence paths/hashes are attestations, NOT source verification.

    A reviewer/independent verification process must establish gate results.
    This utility cannot certify truth from a flag or a URL.
    """
    blockers = []
    for name in GATE_IDS:
        item = gates.get(name, {})
        evidence = item.get('evidence', {})
        digest = evidence.get('sha256', '')
        if (item.get('status') != 'pass' or not evidence.get('artifact')
                or not isinstance(digest,str) or len(digest) != 64
                or any(c not in '0123456789abcdef' for c in digest)):
            blockers.append(name)
    return {'eligible': not blockers, 'blockers': blockers}
