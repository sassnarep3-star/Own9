"""The origination model: one least-squares fit, three markets, in a fixed order.

Published formula (no tuned hyperparameters, nothing fitted on the season it scores)
-------------------------------------------------------------------------------
For every completed regular-season game in the training window, with
h = home points and a = away points, solve the ordinary least-squares problem

    h_i = mu + o_home(i) + d_away(i)
    a_i = mu + o_away(i) + d_home(i)

for the 65 unknowns mu, o_t (offence deviation) and d_t (defence deviation, i.e.
points allowed above average), subject to sum(o) = 0 and sum(d) = 0. The
constraints are imposed as heavily weighted rows, so the fit is an ordinary
least-squares solve with no shrinkage constant and no hyperparameter chosen on
evaluation data.

Predictions follow from the same fit:

    margin_hat = (o_home - o_away) + (d_away - d_home)
    total_hat  = 2*mu + o_home + o_away + d_home + d_away

Residuals on the training window give sigma_margin, sigma_total and their
correlation rho. Those three numbers, plus the two point estimates, are the
entire model. Nothing else is fitted.

Origination order (required)
----------------------------
1. SIDE    - the fair handicap is -margin_hat; the quoted handicap is scored
             against the margin distribution.
2. TOTAL   - the fair total is total_hat; the quoted total is scored against
             the total distribution.
3. MONEYLINE - derived from the SAME margin distribution already used for the
             side, so the moneyline can never disagree with the side number.
             It is deliberately not refitted.

The moneyline being last is not cosmetic: it is the consistency condition that
stops the three markets from Contradicting each other. `originate()` asserts it.
"""

import math
from collections import defaultdict

from .data import norm

# Market codes, in the order they must be originated.
ORDER = ('SIDE', 'TOTAL', 'MONEYLINE')


# --------------------------------------------------------------------------
# Dense linear algebra, standard library only.
# --------------------------------------------------------------------------

def solve(matrix, rhs):
    """Gaussian elimination with partial pivoting. matrix is n x n, rhs length n."""
    n = len(rhs)
    aug = [list(matrix[i]) + [rhs[i]] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-12:
            raise ValueError('singular normal equations at column %d' % col)
        aug[col], aug[pivot] = aug[pivot], aug[col]
        inv = 1.0 / aug[col][col]
        for j in range(col, n + 1):
            aug[col][j] *= inv
        for r in range(n):
            if r == col:
                continue
            factor = aug[r][col]
            if factor == 0.0:
                continue
            for j in range(col, n + 1):
                aug[r][j] -= factor * aug[col][j]
    return [aug[i][n] for i in range(n)]


def normal_equations(rows, teams):
    """Build and solve the constrained least-squares system.

    rows: iterable of (feature_index -> coefficient, target) pairs.
    constraints: (index, weight) pairs forced to zero with a large weight.
    """
    idx = {t: i for i, t in enumerate(teams)}
    return idx


def fit(games, teams, constraint_weight=1e6):
    """Least-squares fit of the offence/defence system.

    games: [{'home','away','home_score','away_score'}]
    Returns dict with mu, o, d, residuals and scale estimates.
    """
    teams = sorted(teams)
    n_teams = len(teams)
    # unknowns: [mu, o_0..o_{n-1}, d_0..d_{n-1}]
    p = 1 + 2 * n_teams
    off = {t: 1 + i for i, t in enumerate(teams)}
    dfn = {t: 1 + n_teams + i for i, t in enumerate(teams)}

    ata = [[0.0] * p for _ in range(p)]
    atb = [0.0] * p

    def accumulate(features, target, weight=1.0):
        keys = list(features)
        for a in keys:
            ca = features[a]
            atb[a] += weight * ca * target
            for b in keys:
                ata[a][b] += weight * ca * features[b]

    for game in games:
        home, away = norm(game['home_team']), norm(game['away_team'])
        if home not in off or away not in off:
            continue
        hs, as_ = float(game['home_score']), float(game['away_score'])
        accumulate({0: 1.0, off[home]: 1.0, dfn[away]: 1.0}, hs)
        accumulate({0: 1.0, off[away]: 1.0, dfn[home]: 1.0}, as_)

    # sum(o) = 0 and sum(d) = 0, imposed as heavily weighted zero-target rows.
    for base, mapping in ((1, off), (1 + n_teams, dfn)):
        feats = {mapping[t]: 1.0 for t in teams}
        accumulate(feats, 0.0, weight=constraint_weight)

    beta = solve(ata, atb)
    mu = beta[0]
    o = {t: beta[off[t]] for t in teams}
    d = {t: beta[dfn[t]] for t in teams}

    # Training residuals, used only to estimate the predictive spread.
    res_m, res_t, n = [], [], 0
    for game in games:
        home, away = norm(game['home_team']), norm(game['away_team'])
        if home not in off or away not in off:
            continue
        hs, as_ = float(game['home_score']), float(game['away_score'])
        m_hat = (o[home] - o[away]) + (d[away] - d[home])
        t_hat = 2 * mu + o[home] + o[away] + d[home] + d[away]
        res_m.append((hs - as_) - m_hat)
        res_t.append((hs + as_) - t_hat)
        n += 1
    return {
        'mu': mu, 'offence': o, 'defence': d,
        'sigma_margin': _sd(res_m), 'sigma_total': _sd(res_t),
        'rho': _corr(res_m, res_t), 'train_games': len(games), 'train_rows': n,
        'residual_margin': res_m, 'residual_total': res_t,
    }


def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def _sd(xs):
    if len(xs) < 2:
        return None
    m = _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def _corr(xs, ys):
    if len(xs) < 3:
        return None
    mx, my = _mean(xs), _mean(ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None
    return sxy / math.sqrt(sxx * syy)


# --------------------------------------------------------------------------
# Distribution helpers
# --------------------------------------------------------------------------

def norm_cdf(x, mu, sigma):
    if sigma is None or sigma <= 0:
        return None
    return 0.5 * (1.0 + math.erf((x - mu) / (sigma * math.sqrt(2.0))))


def probability_above_integer(threshold, mu, sigma):
    """P(X > threshold) for an integer-valued X, with a continuity correction."""
    return _clip(1.0 - norm_cdf(threshold + 0.5, mu, sigma))


def probability_below_integer(threshold, mu, sigma):
    return _clip(norm_cdf(threshold - 0.5, mu, sigma))


def probability_equal_integer(threshold, mu, sigma):
    upper = norm_cdf(threshold + 0.5, mu, sigma)
    lower = norm_cdf(threshold - 0.5, mu, sigma)
    return _clip(upper - lower)


def probability_strictly_positive(mu, sigma):
    """P(margin > 0) for an integer margin with a tie mass at zero."""
    return _clip(1.0 - norm_cdf(0.5, mu, sigma))


def probability_tie(mu, sigma):
    return probability_equal_integer(0, mu, sigma)


def joint_normal_above(a_thresh, b_thresh, mu_a, mu_b, sigma_a, sigma_b, rho):
    """P(A > a, B > b) for a bivariate normal, by 20-point Gauss-Legendre-free
    Simpson integration on the conditional. rho must be a measured number."""
    if None in (sigma_a, sigma_b, rho) or sigma_a <= 0 or sigma_b <= 0:
        return None
    if not -0.999 < rho < 0.999:
        return None
    # Integrate P(B>b | A=x) phi((x-mu_a)/sigma_a) dx over x in [a, a+8 sigma].
    lo = a_thresh + 0.5
    hi = a_thresh + 0.5 + 10.0 * sigma_a
    steps = 400
    h = (hi - lo) / steps
    total = 0.0
    for i in range(steps + 1):
        x = lo + i * h
        z = (x - mu_a) / sigma_a
        density = math.exp(-0.5 * z * z) / (sigma_a * math.sqrt(2.0 * math.pi))
        cond_mu = mu_b + rho * sigma_b * z
        cond_sigma = sigma_b * math.sqrt(1.0 - rho * rho)
        cond = 1.0 - norm_cdf(b_thresh + 0.5, cond_mu, cond_sigma)
        weight = 1.0 if i in (0, steps) else (4.0 if i % 2 else 2.0)
        total += weight * density * cond
    return _clip(total * h / 3.0)


def _clip(value):
    if value is None:
        return None
    return min(1.0, max(0.0, value))


# --------------------------------------------------------------------------
# Origination
# --------------------------------------------------------------------------

def predict(fit_state, home, away):
    home, away = norm(home), norm(away)
    o, d, mu = fit_state['offence'], fit_state['defence'], fit_state['mu']
    margin = (o.get(home, 0.0) - o.get(away, 0.0)) + (d.get(away, 0.0) - d.get(home, 0.0))
    total = 2 * mu + o.get(home, 0.0) + o.get(away, 0.0) + d.get(home, 0.0) + d.get(away, 0.0)
    return {'margin': margin, 'total': total,
            'sigma_margin': fit_state['sigma_margin'],
            'sigma_total': fit_state['sigma_total'],
            'rho': fit_state['rho']}


def originate(fit_state, game):
    """Originate one game's markets in the required order.

    Returns a list of market dicts in ORDER: SIDE, TOTAL, MONEYLINE. The
    moneyline reuses the margin distribution from step 1 by construction.
    """
    home, away = game['home_team'], game['away_team']
    pred = predict(fit_state, home, away)
    markets = []

    # 1 · SIDE ---------------------------------------------------------------
    fair_handicap = -pred['margin']           # home favoured by margin_hat
    markets.append({
        'market': 'SIDE', 'order': 1,
        'fair_line': fair_handicap,
        'fair_probability_home_cover': None,   # filled once a quote exists
        'model_margin_mean': pred['margin'],
        'model_sigma': pred['sigma_margin'],
    })

    # 2 · TOTAL --------------------------------------------------------------
    markets.append({
        'market': 'TOTAL', 'order': 2,
        'fair_line': pred['total'],
        'fair_probability_over': None,
        'model_total_mean': pred['total'],
        'model_sigma': pred['sigma_total'],
    })

    # 3 · MONEYLINE ----------------------------------------------------------
    p_home = probability_strictly_positive(pred['margin'], pred['sigma_margin'])
    p_tie = probability_tie(pred['margin'], pred['sigma_margin'])
    markets.append({
        'market': 'MONEYLINE', 'order': 3,
        'fair_line': fair_probability_to_american(p_home) if p_home else None,
        'fair_probability_home': p_home,
        'fair_probability_tie': p_tie,
        'model_margin_mean': pred['margin'],   # identical to step 1 by design
        'model_sigma': pred['sigma_margin'],   # identical to step 1 by design
    })

    assert [m['market'] for m in markets] == list(ORDER), 'origination order violated'
    assert markets[2]['model_margin_mean'] == markets[0]['model_margin_mean'], \
        'moneyline must reuse the side distribution'
    return markets, pred


def price_against_quote(market, quote, pred):
    """Score an originated market against a recorded quote. No quote, no price."""
    if market['market'] == 'SIDE':
        h = quote.get('spread_line')
        if h is None:
            return None
        mu, sigma = pred['margin'], pred['sigma_margin']
        return {
            'side': 'home', 'quote_line': h,
            'p_win': probability_above_integer(h, mu, sigma),
            'p_push': probability_equal_integer(h, mu, sigma),
        }
    if market['market'] == 'TOTAL':
        t = quote.get('total_line')
        if t is None:
            return None
        mu, sigma = pred['total'], pred['sigma_total']
        return {
            'side': 'over', 'quote_line': t,
            'p_win': probability_above_integer(t, mu, sigma),
            'p_push': probability_equal_integer(t, mu, sigma),
        }
    price = quote.get('home_moneyline')
    if price is None:
        return None
    return {
        'side': 'home', 'quote_line': None,
        'p_win': market['fair_probability_home'],
        'p_push': market['fair_probability_tie'],
    }


def fair_probability_to_american(p):
    """Fair American price for probability p. No margin, no vig."""
    if p is None or p <= 0 or p >= 1:
        return None
    decimal = 1.0 / p
    if decimal >= 2.0:
        return round((decimal - 1.0) * 100)
    return round(-100.0 / (decimal - 1.0))


def american_to_decimal(price):
    if price is None:
        return None
    if price > 0:
        return 1.0 + price / 100.0
    if price < 0:
        return 1.0 + 100.0 / abs(price)
    return None


def devig_two_way(price_a, price_b):
    """Proportional de-vig. A declared comparison convention, not a true price."""
    da, db = american_to_decimal(price_a), american_to_decimal(price_b)
    if not da or not db or da <= 1 or db <= 1:
        return None
    ia, ib = 1.0 / da, 1.0 / db
    return ia / (ia + ib)
