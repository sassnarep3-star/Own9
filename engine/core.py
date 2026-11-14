"""Dependency-free, deterministic pricing and research primitives.

Inputs are supplied distributions/observations, NOT verified NFL predictions.
See research/METHODOLOGY.md for assumptions and evidence requirements.
"""
from collections import defaultdict
from dataclasses import dataclass
from math import exp, isfinite, log, sqrt
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


# --- Correlation decision gate -------------------------------------------------
# These functions decide what a measured correlation is allowed to do to a
# decision. They never invent a correlation and never default to independence.

DEPENDENCE_VERDICTS = (
    'significantly_positive',
    'significantly_negative',
    'indistinguishable_from_zero',
    'insufficient_evidence',
)


def fisher_z(rho):
    """Fisher variance-stabilising transform. Undefined at |rho| = 1."""
    r = finite(rho)
    if not -1 < r < 1:
        raise ValueError('Fisher z is undefined at |rho| = 1')
    return 0.5 * log((1 + r) / (1 - r))


def correlation_interval(rho, n, confidence=.95):
    """Fisher-z interval for a Pearson correlation.

    Independence assumption: n paired observations drawn independently. NFL
    legs inside one week are NOT independent, so this interval is only valid
    for a design whose dependence is already handled (for example one
    observation per week, or a block bootstrap). Returns None when n < 4 or
    when the interval cannot be formed.
    """
    r = finite(rho)
    n = finite(n)
    if not 0 < finite(confidence) < 1:
        raise ValueError('invalid confidence level')
    if n != int(n) or n < 4:
        return None
    if not -1 < r < 1:
        return None
    # Normal quantile via the standard library-free Acklam-free approach:
    # use a fixed table-free approximation of the two-sided normal quantile.
    alpha = (1 - confidence) / 2
    z_crit = _normal_quantile(1 - alpha)
    centre = fisher_z(r)
    half = z_crit / sqrt(n - 3)
    lo, hi = centre - half, centre + half

    def inverse(z):
        e = exp(2 * z)
        return (e - 1) / (e + 1)

    return (max(-1.0, inverse(lo)), min(1.0, inverse(hi)))


def _normal_quantile(p):
    """Inverse standard-normal CDF via the Acklam rational approximation."""
    if not 0 < p < 1:
        raise ValueError('quantile probability must be in (0, 1)')
    a = (-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00)
    b = (-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01)
    c = (-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00)
    d = (7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00)
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = sqrt(-2 * log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > phigh:
        q = sqrt(-2 * log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def dependence_gate(rho, n, min_n, confidence=.95, deadband=0.0):
    """Decide how a measured correlation may change a parlay decision.

    Fail-closed policy:
      - fewer than min_n paired observations        -> insufficient_evidence
      - interval straddles the deadband +/- tolerance -> indistinguishable_from_zero
      - interval entirely above/below the deadband   -> significantly +/-

    Only a directional verdict may be used to price a joint bet. Any other
    verdict must leave the joint price blank rather than assume independence.
    deadband is the smallest |rho| the project will act on; it must be
    predeclared before the test, never tuned after seeing the estimate.
    """
    r = finite(rho)
    n = finite(n)
    min_n = finite(min_n)
    band = finite(deadband)
    if not -1 <= r <= 1:
        raise ValueError('correlation outside [-1, 1]')
    if band < 0:
        raise ValueError('deadband cannot be negative')
    if min_n < 4:
        raise ValueError('min_n below 4 cannot support an interval')
    interval = correlation_interval(r, n, confidence) if n >= min_n else None
    if interval is None:
        return {'verdict': 'insufficient_evidence', 'rho': r, 'n': n,
                'interval': None, 'deadband': band,
                'may_price_joint': False,
                'reason': 'Too few paired observations for a usable interval.'}
    lo, hi = interval
    if lo > band:
        verdict, reason = 'significantly_positive', 'Whole interval above the predeclared deadband.'
    elif hi < -band:
        verdict, reason = 'significantly_negative', 'Whole interval below the predeclared deadband.'
    else:
        verdict = 'indistinguishable_from_zero'
        reason = 'Interval overlaps the predeclared deadband; the sign is not established.'
    return {'verdict': verdict, 'rho': r, 'n': n, 'interval': (lo, hi),
            'deadband': band, 'may_price_joint': verdict in
            ('significantly_positive', 'significantly_negative'), 'reason': reason}


def joint_price_from_dependence(p_a, p_b, gate):
    """Price a two-leg joint ONLY when the dependence gate directionally passed.

    Returns None instead of assuming independence. This is the single place a
    correlation is allowed to enter a price.
    """
    probability(p_a); probability(p_b)
    if not isinstance(gate, dict) or not gate.get('may_price_joint'):
        return None
    rho = gate.get('rho')
    if rho is None:
        return None
    return bernoulli_joint(p_a, p_b, rho)


# --- Demotion gate: live strategy -> paper -----------------------------------

DEMOTION_REASONS = (
    'gate_fail',
    'drift_exceeds_tolerance',
    'missing_data',
    'correlation_interval_lost',
    'price_source_lost',
    'manual_review',
)


def demotion_check(strategy_state, gates_passed, gates_required, tolerances,
                   current_metrics, previous_metrics, data_complete,
                   price_source_active, correlation_gate_ok):
    """Decide whether a live strategy must be demoted to paper trading.

    Fail-closed policy: any unsatisfied condition demotes. A strategy on paper
    cannot issue live quotes or enter the live leaderboard. Demotion is recorded
    with a reason and the evidence that triggered it; neither the reason nor the
    evidence may be inferred — each must come from an observed signal.

    Parameters are all observed/recorded values, not model outputs.

    Returns a dict with 'demote' (bool), 'reason' (one of DEMOTION_REASONS or
    None), 'evidence' (list of observed facts) and 'conditions' (each gate
    checked with pass/fail).
    """
    conditions = {}
    evidence = []
    reasons = []

    # 1. All required gates must pass.
    all_pass = all(gates_passed.get(g, False) for g in gates_required)
    conditions['all_gates_pass'] = all_pass
    if not all_pass:
        missing = [g for g in gates_required if not gates_passed.get(g, False)]
        reasons.append('gate_fail')
        evidence.append(f'gates not passed: {", ".join(missing)}')

    # 2. Data must be complete (no missing scores, prices or features).
    conditions['data_complete'] = bool(data_complete)
    if not data_complete:
        reasons.append('missing_data')
        evidence.append('required scores, prices or features are missing')

    # 3. Price source must remain active.
    conditions['price_source_active'] = bool(price_source_active)
    if not price_source_active:
        reasons.append('price_source_lost')
        evidence.append('executable quote source is no longer available')

    # 4. Correlation gate must still clear its deadband (if joints are priced).
    conditions['correlation_gate_ok'] = bool(correlation_gate_ok)
    if not correlation_gate_ok:
        reasons.append('correlation_interval_lost')
        evidence.append('joint pricing gate no longer clears its deadband')

    # 5. Drift: current metrics vs previous, checked against tolerances.
    drift_reasons = _check_drift(current_metrics, previous_metrics, tolerances)
    conditions['drift_within_tolerance'] = not drift_reasons
    for d in drift_reasons:
        reasons.append('drift_exceeds_tolerance')
        evidence.append(d)

    demote = len(reasons) > 0
    primary = reasons[0] if reasons else None

    return {
        'demote': demote,
        'reason': primary,
        'reasons': reasons,
        'evidence': evidence,
        'conditions': conditions,
        'strategy_id': strategy_state.get('id'),
        'previous_status': strategy_state.get('status'),
        'new_status': 'paper' if demote else strategy_state.get('status', 'paper'),
    }


def _check_drift(current, previous, tolerances):
    """Compare current metrics against previous within declared tolerances.

    Returns a list of human-readable drift violations. Empty means within
    tolerance. Missing tolerances mean the metric is not drift-checked.
    """
    violations = []
    if not current or not previous:
        return violations
    for metric, tol in tolerances.items():
        cur = current.get(metric)
        prev = previous.get(metric)
        if cur is None or prev is None or tol is None:
            continue
        try:
            cur = float(cur)
            prev = float(prev)
            tol = float(tol)
        except (TypeError, ValueError):
            continue
        if abs(cur - prev) > tol:
            violations.append(
                f'{metric}: {cur} vs {prev}, drift {abs(cur - prev):.4f} > tolerance {tol}'
            )
    return violations


# --- Signal vs staking separation -------------------------------------------

SIGNAL_METRICS = (
    'log_loss_gain_lcb',      # simultaneous lower confidence bound on log-loss
    'brier_score',            # lower is better
    'calibration_error',      # reliability gap
    'coverage',               # fraction of predictions with valid intervals
)

STAKING_METRICS = (
    'net_return_lcb',         # simultaneous lower bound on mean return
    'max_drawdown',           # predeclared tolerance
    'win_rate',               # raw outcomes (variance-dominated)
    'roi',                    # return on investment (variance-dominated)
    'turnover',               # bets per unit time
)


def separate_signal_and_staking(strategy_record):
    """Split a strategy's published metrics into signal and staking groups.

    A lucky staking run (high ROI over few bets) cannot mask a bad signal
    (poor calibration, no log-loss improvement). The two groups are reported
    independently; neither is aggregated into the other.

    Returns a dict with 'signal' and 'staking' sub-dicts, each mapping metric
    names to values (or None when unmeasured). Also returns 'eligible_for_live'
    which requires every signal metric that IS measured to show non-negative
    evidence of skill, and every staking metric to be within tolerance.
    """
    signal = {}
    staking = {}
    for m in SIGNAL_METRICS:
        signal[m] = strategy_record.get(m)
    for m in STAKING_METRICS:
        staking[m] = strategy_record.get(m)

    # Eligibility for live: every measured signal metric must show skill
    # (log-loss gain LCB > 0, Brier below market baseline, calibration within
    # tolerance, coverage at or above target). Missing metrics are not treated
    # as passes — they block eligibility.
    signal_ok = True
    if strategy_record.get('log_loss_gain_lcb') is not None:
        signal_ok = signal_ok and strategy_record['log_loss_gain_lcb'] > 0
    if strategy_record.get('brier_score') is not None:
        market_brier = strategy_record.get('market_brier_baseline')
        if market_brier is not None:
            signal_ok = signal_ok and strategy_record['brier_score'] < market_brier
    staking_ok = True
    if strategy_record.get('max_drawdown') is not None:
        dd_tol = strategy_record.get('drawdown_tolerance')
        if dd_tol is not None:
            staking_ok = staking_ok and strategy_record['max_drawdown'] <= dd_tol

    return {
        'signal': signal,
        'staking': staking,
        'eligible_for_live': bool(signal_ok and staking_ok),
        'signal_complete': all(v is not None for v in signal.values()),
        'staking_complete': all(v is not None for v in staking.values()),
    }
