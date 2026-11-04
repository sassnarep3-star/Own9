"""Dependency-free, explicit-settlement research math.

Official formula references are recorded in evidence/sources.json.
All inputs here are supplied numbers, not verified NFL observations.
"""
import math
from statistics import mean


def probability(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError('Probability must be a finite number in [0, 1]')
    return value


def expected_return(win, loss, refund, decimal_odds, cost=0):
    """Per unit: win*(D-1) - loss - cost; push/void refund earns zero.

    Only valid when all refunds return the full stake. Reduced parlay payouts
    and dead heats need separate settlement states, not this function.
    """
    for p in (win, loss, refund):
        probability(p)
    if not math.isclose(win + loss + refund, 1, abs_tol=1e-12, rel_tol=0):
        raise ValueError('Exhaustive settlement probabilities must sum to one')
    if not math.isfinite(decimal_odds) or decimal_odds <= 1:
        raise ValueError('Decimal odds must be finite and > 1')
    if not math.isfinite(cost) or cost < 0:
        raise ValueError('Cost must be finite and nonnegative')
    return win * (decimal_odds - 1) - loss - cost


def fair_decimal(win, loss, refund=0):
    expected_return(win, loss, refund, 2)  # validate settlement states
    return None if win == 0 else 1 + loss / win


def proportional_no_vig(prices):
    """Declared baseline, not true probabilities; exhaustive no-push markets only."""
    prices = list(prices)
    if len(prices) < 2 or any(not math.isfinite(d) or d <= 1 for d in prices):
        raise ValueError('Need >=2 finite decimal prices >1 for all outcomes')
    implied = [1/d for d in prices]
    return [p / sum(implied) for p in implied]


def binary_scores(outcomes, predictions):
    outcomes, predictions = list(outcomes), list(predictions)
    if not outcomes or len(outcomes) != len(predictions):
        raise ValueError('Nonempty aligned arrays required')
    if any(y not in (0, 1) for y in outcomes):
        raise ValueError('Only settled binary outcomes; no pushes or voids')
    losses = []
    for y, p in zip(outcomes, predictions):
        probability(p)
        q = p if y else 1-p
        losses.append(-math.log(q) if q else math.inf)
    return {'n': len(outcomes), 'brier': mean((p-y)**2 for y,p in zip(outcomes,predictions)),
            'log_loss': mean(losses)}


def pearson(x, y):
    x, y = list(x), list(y)
    if len(x) != len(y) or len(x) < 2:
        raise ValueError('Need >=2 aligned pairs')
    if any(not math.isfinite(v) for v in x+y):
        raise ValueError('Missing or nonfinite observations are not allowed')
    a, b = mean(x), mean(y)
    sx = sum((v-a)**2 for v in x)
    sy = sum((v-b)**2 for v in y)
    if sx == 0 or sy == 0:
        return None  # undefined, not zero
    return max(-1., min(1., sum((u-a)*(v-b) for u,v in zip(x,y))/math.sqrt(sx*sy)))


def binary_joint(x, y):
    """Paired settled legs only; descriptive sample statistic, not a forecast."""
    x, y = list(x), list(y)
    if len(x) != len(y) or len(x) < 2 or any(v not in (0,1) for v in x+y):
        raise ValueError('Need >=2 paired binary settlements')
    return {'n': len(x), 'phi': pearson(x,y), 'joint_win': mean(a*b for a,b in zip(x,y))}


def joint_from_phi(p, q, rho):
    """Two Bernoulli legs ONLY. Reject infeasible joint distributions."""
    probability(p); probability(q)
    if not math.isfinite(rho) or not -1 <= rho <= 1:
        raise ValueError('Invalid correlation')
    if p in (0,1) or q in (0,1):
        raise ValueError('Correlation undefined for a constant leg')
    joint = p*q + rho*math.sqrt(p*(1-p)*q*(1-q))
    if joint < max(0,p+q-1)-1e-12 or joint > min(p,q)+1e-12:
        raise ValueError('Infeasible Bernoulli correlation')
    return max(max(0,p+q-1), min(min(p,q),joint))


GATES = ('provenance','point_in_time','holdout','prediction','economics','selection','stability')

def eligible(gates):
    """Fail closed. No implicit truthiness; no eligibility with missing gates."""
    return set(gates) == set(GATES) and all(gates[g] is True for g in GATES)
