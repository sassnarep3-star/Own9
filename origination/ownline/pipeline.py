"""End-to-end origination run: results feed, price store, walk-forward, scoring.

Everything published by this desk is produced here. The inputs are the two CSV
files committed in `data/raw/`; nothing is fetched, sampled or simulated, and no
value is written for a field the inputs do not contain.
"""

import json
from collections import defaultdict

from . import model
from . import metrics
from .data import (GAMES_CSV, LINES_CSV, all_regular_games, market_fields, norm,
                   played, regular_season, scored_games, sha256)

# --------------------------------------------------------------------------
# Frozen constants. Declared before any result is looked at, and never refitted.
# --------------------------------------------------------------------------
FIRST_EVAL_SEASON = 2010      # first season with complete recorded prices
LAST_EVAL_SEASON = 2026
MIN_TRAIN_SEASONS = 4
EDGE_THRESHOLD = 0.02         # minimum probability edge over the break-even price
KELLY_CAP = 0.25
DEADBAND = 0.05               # correlation deadband for joint pricing
STAKE_FLAT = 1.0

STRATEGIES = (
    ('G-SIDE', 'Single · side', 'Side (spread) singles on the originated handicap.'),
    ('G-TOTAL', 'Single · total', 'Totals singles on the originated game total.'),
    ('G-ML', 'Single · moneyline', 'Moneyline singles from the side distribution.'),
    ('X-PARLAY', 'Parlay · cross-game', 'Two strongest same-week side legs, joint-priced.'),
    ('S-SGP', 'Combo · same game', 'Home cover AND over, joint-priced on measured rho.'),
    ('P-PROP', 'Combo · player props', 'Player-prop combinations.'),
)

DEMOTION_RULES = (
    ('D1', 'Signal decay',
     'Trailing 200-bet clustered lower bound on log-loss gain versus the market '
     'falls to zero or below.', 'Staking stops; strategy returns to paper.'),
    ('D2', 'Calibration drift',
     'Trailing 200-bet Brier score exceeds the market baseline Brier by more '
     'than 0.005.', 'Staking stops; strategy returns to paper.'),
    ('D3', 'Drawdown breach',
     'Realised peak-to-trough decline of the flat-stake series exceeds 20 units.',
     'Staking stops; strategy returns to paper.'),
    ('D4', 'Settlement integrity',
     'Any originated market in the window settles with a missing score or an '
     'unreconciled result.', 'All strategies halt; the results feed is re-verified.'),
    ('D5', 'Coverage loss',
     'Fewer than 90% of scheduled markets in the window carry a recorded price '
     'and a settled result.', 'Strategy returns to paper until coverage recovers.'),
    ('R1', 'Re-promotion',
     'After a demotion, the strategy must pass D1, D2 and D3 again on four '
     'consecutive prospective paper weeks before staking may resume.',
     'Paper only; no stake.'),
)


# --------------------------------------------------------------------------
# 1 · Results feed
# --------------------------------------------------------------------------

def results_feed():
    """One row per completed regular-season game, recomputed from the scores."""
    rows = []
    for game in scored_games():
        home, away = int(game['home_score']), int(game['away_score'])
        margin, total = home - away, home + away
        rows.append({
            'game_id': game['game_id'],
            'season': int(game['season']),
            'week': int(game['week']),
            'gameday': game['gameday'],
            'home': norm(game['home_team']),
            'away': norm(game['away_team']),
            'home_score': home,
            'away_score': away,
            'margin': margin,
            'total': total,
            'result_matches_recompute': margin == int(game['result']),
            'total_matches_recompute': total == int(game['total']),
            'overtime': game['overtime'],
        })
    return rows


# --------------------------------------------------------------------------
# 2 · Walk-forward origination
# --------------------------------------------------------------------------

def walk_forward():
    """Fit on all prior completed seasons, originate the next, score it."""
    games = all_regular_games()
    by_season = defaultdict(list)
    for game in games:
        by_season[int(game['season'])].append(game)

    played_games = {g['game_id'] for g in scored_games()}
    seasons = sorted(by_season)
    originations = []
    fit_reports = []

    for target in range(FIRST_EVAL_SEASON, LAST_EVAL_SEASON + 1):
        train = [g for s in seasons if s < target for g in by_season[s]
                 if g['game_id'] in played_games]
        if len({int(g['season']) for g in train}) < MIN_TRAIN_SEASONS:
            continue
        teams = {norm(g['home_team']) for g in train} | {norm(g['away_team']) for g in train}
        state = model.fit(train, teams)
        fit_reports.append({
            'target_season': target,
            'train_games': state['train_games'],
            'train_seasons': sorted({int(g['season']) for g in train}),
            'sigma_margin': state['sigma_margin'],
            'sigma_total': state['sigma_total'],
            'rho_margin_total': state['rho'],
            'mean_total': 2 * state['mu'],
        })
        for game in sorted(by_season[target], key=lambda g: (int(g['week']), g['gameday'])):
            originations.append(originate_row(state, game, played_games, target))
    return originations, fit_reports


def originate_row(state, game, played_games, target_season):
    """Originate one game and attach the recorded quote and the settled result."""
    markets, pred = model.originate(state, game)
    quote = market_fields(game)
    settled = game['game_id'] in played_games
    home_score = int(game['home_score']) if settled else None
    away_score = int(game['away_score']) if settled else None

    out = []
    for market in markets:
        priced = model.price_against_quote(market, quote, pred)
        row = {
            'game_id': game['game_id'],
            'season': int(game['season']),
            'week': int(game['week']),
            'gameday': game['gameday'],
            'home': norm(game['home_team']),
            'away': norm(game['away_team']),
            'market': market['market'],
            'order': market['order'],
            'model_fair_line': market['fair_line'],
            'model_probability': None,
            'model_push_probability': None,
            'market_line': None,
            'market_price': None,
            'market_probability_devig': None,
            'difference': None,
            'settled': settled,
            'outcome': None,
            'home_score': home_score,
            'away_score': away_score,
        }
        if priced:
            row['model_probability'] = priced['p_win']
            row['model_push_probability'] = priced['p_push']
        if market['market'] == 'SIDE':
            row['market_line'] = quote['spread_line']
            row['market_price'] = quote['home_spread_odds']
            row['market_probability_devig'] = model.devig_two_way(
                quote['home_spread_odds'], quote['away_spread_odds'])
        elif market['market'] == 'TOTAL':
            row['market_line'] = quote['total_line']
            row['market_price'] = quote['over_odds']
            row['market_probability_devig'] = model.devig_two_way(
                quote['over_odds'], quote['under_odds'])
        else:
            # The recorded price is the market's number for this market.
            row['market_line'] = quote['home_moneyline']
            row['market_price'] = quote['home_moneyline']
            row['market_probability_devig'] = model.devig_two_way(
                quote['home_moneyline'], quote['away_moneyline'])
        if market['market'] == 'MONEYLINE':
            # A moneyline has no line, only a price, so the honest difference is
            # in probability points rather than in an invented point spread.
            if row['model_probability'] is not None \
                    and row['market_probability_devig'] is not None:
                row['difference'] = round(
                    100.0 * (row['model_probability'] - row['market_probability_devig']), 3)
        elif row['market_line'] is not None and row['model_fair_line'] is not None:
            row['difference'] = round(row['model_fair_line'] - row['market_line'], 3)
        if settled and priced and row['market_line'] is not None:
            row['outcome'] = metrics.settlement(market['market'], home_score,
                                                away_score, row['market_line'])
        elif settled and market['market'] == 'MONEYLINE' and priced:
            row['outcome'] = metrics.settlement('MONEYLINE', home_score, away_score, None)
        out.append(row)
    return {'game': game, 'rows': out, 'pred': pred, 'quote': quote,
            'fit_season': target_season}


# --------------------------------------------------------------------------
# 3 · Bet construction
# --------------------------------------------------------------------------

def build_bets(originations):
    """Turn originated markets into candidate bets under the frozen trigger rule.

    A bet exists only where a recorded price, a model probability and a settled
    result all exist. Anything missing leaves the bet uncreated, not zeroed.
    """
    bets = []
    for entry in originations:
        game, quote, pred = entry['game'], entry['quote'], entry['pred']
        settled = entry['rows'][0]['settled']
        home_score = int(game['home_score']) if settled else None
        away_score = int(game['away_score']) if settled else None
        for row in entry['rows']:
            if not settled or row['model_probability'] is None or row['outcome'] is None:
                continue
            market = row['market']
            if market == 'SIDE':
                sides = _side_bets(quote, pred, row, home_score, away_score, game)
            elif market == 'TOTAL':
                sides = _total_bets(quote, pred, row, home_score, away_score, game)
            else:
                sides = _moneyline_bets(quote, pred, row, home_score, away_score, game)
            for bet in sides:
                if bet:
                    bets.append(bet)
    bets.sort(key=lambda b: (b['season'], b['week'], b['game_id'], b['market'], b['side']))
    return bets


def _common(row, game, side, price, p_win, p_push, outcome_side):
    decimal = model.american_to_decimal(price)
    if not decimal or decimal <= 1 or p_win is None:
        return None
    break_even = 1.0 / decimal
    edge = p_win - break_even
    stake = STAKE_FLAT if edge >= EDGE_THRESHOLD else 0.0
    kelly = metrics.kelly_fraction(p_win, decimal, KELLY_CAP) if edge >= EDGE_THRESHOLD else 0.0
    if outcome_side == 0.5:
        ret = 0.0
    elif outcome_side == 1.0:
        ret = (decimal - 1.0) * stake
    else:
        ret = -stake
    return {
        'game_id': row['game_id'], 'season': row['season'], 'week': row['week'],
        'gameday': row['gameday'], 'home': row['home'], 'away': row['away'],
        'strategy': {'SIDE': 'G-SIDE', 'TOTAL': 'G-TOTAL',
                     'MONEYLINE': 'G-ML'}[row['market']],
        'market': row['market'], 'side': side, 'price': price, 'decimal': decimal,
        'p_model': p_win, 'p_push': p_push or 0.0,
        'p_market_devig': row['market_probability_devig'],
        'break_even': break_even, 'edge': edge,
        'outcome': outcome_side, 'stake': stake, 'return': ret,
        'kelly_stake': kelly,
        'kelly_return': ((decimal - 1.0) * kelly if outcome_side == 1.0
                         else (-kelly if outcome_side == 0.0 else 0.0)),
        'model_fair_line': row['model_fair_line'], 'market_line': row['market_line'],
    }


def _side_bets(quote, pred, row, hs, as_, game):
    h = row['market_line']
    if h is None:
        return [None]
    mu, sigma = pred['margin'], pred['sigma_margin']
    home_cover = metrics.settlement('SIDE', hs, as_, h)
    p_home = model.probability_above_integer(h, mu, sigma)
    p_away = model.probability_below_integer(h, mu, sigma)
    p_push = model.probability_equal_integer(h, mu, sigma)
    out = []
    home_bet = _common(row, game, 'home', quote['home_spread_odds'], p_home, p_push,
                       home_cover)
    away_outcome = None if home_cover is None else (0.5 if home_cover == 0.5 else 1.0 - home_cover)
    away_bet = _common(row, game, 'away', quote['away_spread_odds'], p_away, p_push,
                       away_outcome)
    for bet in (home_bet, away_bet):
        if bet:
            bet['p_market_devig'] = (row['market_probability_devig'] if bet['side'] == 'home'
                                     else (1 - row['market_probability_devig']
                                           if row['market_probability_devig'] is not None else None))
            out.append(bet)
    return out or [None]


def _total_bets(quote, pred, row, hs, as_, game):
    t = row['market_line']
    if t is None:
        return [None]
    mu, sigma = pred['total'], pred['sigma_total']
    over_state = metrics.settlement('TOTAL', hs, as_, t)
    p_over = model.probability_above_integer(t, mu, sigma)
    p_under = model.probability_below_integer(t, mu, sigma)
    p_push = model.probability_equal_integer(t, mu, sigma)
    out = []
    over_bet = _common(row, game, 'over', quote['over_odds'], p_over, p_push, over_state)
    under_state = None if over_state is None else (0.5 if over_state == 0.5 else 1.0 - over_state)
    under_bet = _common(row, game, 'under', quote['under_odds'], p_under, p_push, under_state)
    for bet in (over_bet, under_bet):
        if bet:
            bet['p_market_devig'] = (row['market_probability_devig'] if bet['side'] == 'over'
                                     else (1 - row['market_probability_devig']
                                           if row['market_probability_devig'] is not None else None))
            out.append(bet)
    return out or [None]


def _moneyline_bets(quote, pred, row, hs, as_, game):
    state = metrics.settlement('MONEYLINE', hs, as_, None)
    p_home = row['model_probability']
    p_tie = row['model_push_probability'] or 0.0
    p_away = None if p_home is None else 1.0 - p_home - p_tie
    out = []
    home_bet = _common(row, game, 'home', quote['home_moneyline'], p_home, p_tie, state)
    away_state = None if state is None else (0.5 if state == 0.5 else 1.0 - state)
    away_bet = _common(row, game, 'away', quote['away_moneyline'], p_away, p_tie, away_state)
    for bet in (home_bet, away_bet):
        if bet:
            bet['p_market_devig'] = (row['market_probability_devig'] if bet['side'] == 'home'
                                     else (1 - row['market_probability_devig']
                                           if row['market_probability_devig'] is not None else None))
            out.append(bet)
    return out or [None]


# --------------------------------------------------------------------------
# 4 · Joint bets (parlays and same-game combos)
# --------------------------------------------------------------------------

def build_joint(bets, weekly_rho, sgp_rho):
    """Price two-leg combinations only when the dependence gate allows it."""
    parlays, sgp = [], []
    by_week = defaultdict(list)
    for bet in bets:
        if bet['market'] == 'SIDE' and bet['stake'] > 0:
            by_week[(bet['season'], bet['week'])].append(bet)
    for key in sorted(by_week):
        legs = sorted(by_week[key], key=lambda b: -b['edge'])[:2]
        if len(legs) < 2:
            continue
        joint = _price_pair(legs[0], legs[1], weekly_rho)
        parlays.append({'season': key[0], 'week': key[1], 'legs': legs, 'joint': joint})

    by_game = defaultdict(dict)
    for bet in bets:
        if bet['market'] in ('SIDE', 'TOTAL') and bet['stake'] > 0:
            key = (bet['season'], bet['week'], bet['game_id'])
            by_game[key][bet['market']] = bet
    for key in sorted(by_game):
        pair = by_game[key]
        if 'SIDE' not in pair or 'TOTAL' not in pair:
            continue
        # Same-game combo legs: the home side covering and the over landing.
        if pair['SIDE']['side'] != 'home' or pair['TOTAL']['side'] != 'over':
            continue
        joint = _price_pair(pair['SIDE'], pair['TOTAL'], sgp_rho)
        sgp.append({'season': key[0], 'week': key[1], 'game_id': key[2],
                    'legs': [pair['SIDE'], pair['TOTAL']], 'joint': joint})
    return parlays, sgp


def _price_pair(leg_a, leg_b, dependence):
    """Gaussian-copula joint price, gated on the declared deadband rule."""
    if dependence is None or dependence.get('verdict') != 'use':
        return {'priced': False, 'reason': dependence.get('reason') if dependence else None,
                'rho': dependence.get('point') if dependence else None}
    p = leg_a['p_model']
    q = leg_b['p_model']
    rho = dependence['point']
    joint = metrics.joint_from_correlation(p, q, rho)
    if joint is None:
        return {'priced': False, 'reason': 'joint undefined', 'rho': rho}
    lo, hi = metrics.frechet_bounds(p, q)
    if not (lo - 1e-9 <= joint <= hi + 1e-9):
        return {'priced': False, 'reason': 'outside Frechet bounds', 'rho': rho}
    decimal = leg_a['decimal'] * leg_b['decimal']
    both = 1.0 if (leg_a['outcome'] == 1.0 and leg_b['outcome'] == 1.0) else 0.0
    edge = joint - 1.0 / decimal
    stake = STAKE_FLAT if edge >= EDGE_THRESHOLD else 0.0
    ret = (decimal - 1.0) * stake if both else (-stake if stake else 0.0)
    if leg_a['outcome'] == 0.5 or leg_b['outcome'] == 0.5:
        ret = 0.0
    kelly = metrics.kelly_fraction(joint, decimal, KELLY_CAP) if edge >= EDGE_THRESHOLD else 0.0
    kelly_return = ((decimal - 1.0) * kelly if both else
                    (-kelly if kelly else 0.0))
    return {
        'priced': True, 'joint': joint, 'rho': rho, 'decimal': decimal,
        'p_leg_a': p, 'p_leg_b': q, 'edge': edge, 'stake': stake, 'return': ret,
        'outcome': both, 'bounds': [lo, hi],
        'kelly_stake': kelly, 'kelly_return': kelly_return,
    }


def deadband_verdict(interval, deadband=DEADBAND):
    """Apply the predeclared dependence gate to a correlation interval."""
    if interval is None:
        return {'verdict': 'refuse', 'reason': 'no interval', 'point': None}
    lo, hi, point = interval['lo'], interval['hi'], interval['r']
    if lo > deadband or hi < -deadband:
        return {'verdict': 'use', 'reason': 'interval clears the deadband', 'point': point}
    if lo >= -deadband and hi <= deadband:
        return {'verdict': 'use', 'reason': 'interval inside the deadband, rho taken as 0',
                'point': 0.0}
    return {'verdict': 'refuse', 'reason': 'interval straddles the deadband', 'point': point}
