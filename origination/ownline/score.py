"""Strategy scoring, correlation estimation and the demotion replay.

Signal and staking are scored into two separate result objects. They are never
combined into one ranking number: a staking run cannot move a signal rank.
"""

import math
import random
from collections import defaultdict

from . import metrics


# --------------------------------------------------------------------------
# Correlations
# --------------------------------------------------------------------------

def intraclass_correlation(values, groups, bootstraps=2000, seed=20261114):
    """One-way ANOVA intraclass correlation: do items in the same group share a shock?

    Returns the point estimate, group count, item count, mean group size and a
    cluster-bootstrap interval obtained by resampling whole groups.
    """
    by_group = defaultdict(list)
    for value, group in zip(values, groups):
        by_group[group].append(value)
    groups_list = [v for v in by_group.values() if len(v) > 0]
    if len(groups_list) < 5:
        return None
    grand = sum(values) / len(values)
    k_bar = len(values) / len(groups_list)
    ss_between = sum(len(g) * (sum(g) / len(g) - grand) ** 2 for g in groups_list)
    ss_within = sum(sum((x - sum(g) / len(g)) ** 2 for x in g) for g in groups_list)
    df_between = len(groups_list) - 1
    df_within = len(values) - len(groups_list)
    if df_within <= 0 or df_between <= 0:
        return None
    ms_between = ss_between / df_between
    ms_within = ss_within / df_within
    denominator = ms_between + (k_bar - 1) * ms_within
    if denominator <= 0:
        return None
    rho = (ms_between - ms_within) / denominator

    rng = random.Random(seed)
    draws = []
    n_groups = len(groups_list)
    for _ in range(bootstraps):
        sample = [groups_list[rng.randrange(n_groups)] for _ in range(n_groups)]
        flat = [x for g in sample for x in g]
        groups_sampled = []
        for i, g in enumerate(sample):
            groups_sampled.extend([i] * len(g))
        draw = _icc_point(flat, groups_sampled)
        if draw is not None:
            draws.append(draw)
    if len(draws) < 100:
        return None
    draws.sort()
    lo = draws[int(0.025 * len(draws))]
    hi = draws[int(0.975 * len(draws)) - 1]
    return {'r': rho, 'n': len(values), 'groups': len(groups_list),
            'mean_group_size': k_bar, 'lo': lo, 'hi': hi,
            'interval_method': 'cluster bootstrap over groups, 2000 resamples'}


def _icc_point(values, groups):
    by_group = defaultdict(list)
    for value, group in zip(values, groups):
        by_group[group].append(value)
    groups_list = list(by_group.values())
    if len(groups_list) < 5:
        return None
    grand = sum(values) / len(values)
    k_bar = len(values) / len(groups_list)
    ss_between = sum(len(g) * (sum(g) / len(g) - grand) ** 2 for g in groups_list)
    ss_within = sum(sum((x - sum(g) / len(g)) ** 2 for x in g) for g in groups_list)
    df_between, df_within = len(groups_list) - 1, len(values) - len(groups_list)
    if df_between <= 0 or df_within <= 0:
        return None
    ms_between, ms_within = ss_between / df_between, ss_within / df_within
    denom = ms_between + (k_bar - 1) * ms_within
    if denom <= 0:
        return None
    return (ms_between - ms_within) / denom


def out_of_sample_residuals(originations):
    """Prediction errors on the games the model never saw when it was fitted."""
    errors = []
    for entry in originations:
        rows = {r['market']: r for r in entry['rows']}
        if not rows['SIDE']['settled']:
            continue
        game = entry['game']
        margin = int(game['home_score']) - int(game['away_score'])
        total = int(game['home_score']) + int(game['away_score'])
        pred = entry['pred']
        errors.append({
            'season': rows['SIDE']['season'], 'week': rows['SIDE']['week'],
            'game_id': rows['SIDE']['game_id'],
            'margin_error': margin - pred['margin'],
            'total_error': total - pred['total'],
            'cover': 1.0 if margin > rows['SIDE']['market_line'] else (
                0.5 if margin == rows['SIDE']['market_line'] else 0.0),
            'over': 1.0 if total > rows['TOTAL']['market_line'] else (
                0.5 if total == rows['TOTAL']['market_line'] else 0.0),
        })
    return errors


# --------------------------------------------------------------------------
# Strategy scoring — signal and staking kept apart
# --------------------------------------------------------------------------

def score_singles(bets):
    """Score the three single-market strategies."""
    out = {}
    for code in ('G-SIDE', 'G-TOTAL', 'G-ML'):
        taken = [b for b in bets if b['strategy'] == code and b['stake'] > 0]
        decided = [b for b in taken if b['outcome'] != 0.5]
        signal = _signal_block(taken, decided)
        staking = _staking_block(taken)
        out[code] = {'signal': signal, 'staking': staking, 'taken': len(taken)}
    return out


def score_parlays(parlays):
    taken, decided = [], []
    for entry in parlays:
        joint = entry['joint']
        if not joint.get('priced') or joint.get('stake', 0) <= 0:
            continue
        legs = entry['legs']
        taken.append({
            'season': entry['season'], 'week': entry['week'],
            'p_model': joint['joint'],
            'p_market_devig': legs[0]['p_market_devig'] * legs[1]['p_market_devig'],
            'outcome': 1.0 if joint['outcome'] == 1.0 else 0.0,
            'stake': joint['stake'], 'return': joint['return'],
            'kelly_stake': joint.get('kelly_stake', 0.0),
            'kelly_return': joint.get('kelly_return', 0.0),
            'decimal': joint['decimal'],
        })
        decided.append(taken[-1])
    return {'X-PARLAY': {'signal': _signal_block(taken, decided),
                         'staking': _staking_block(taken),
                         'taken': len(taken),
                         'priced': len([p for p in parlays if p['joint'].get('priced')]),
                         'offered': len(parlays)}}


def score_sgp(sgp):
    taken, decided = [], []
    for entry in sgp:
        joint = entry['joint']
        if not joint.get('priced') or joint.get('stake', 0) <= 0:
            continue
        legs = entry['legs']
        taken.append({
            'season': entry['season'], 'week': entry['week'],
            'p_model': joint['joint'],
            'p_market_devig': legs[0]['p_market_devig'] * legs[1]['p_market_devig'],
            'outcome': 1.0 if joint['outcome'] == 1.0 else 0.0,
            'stake': joint['stake'], 'return': joint['return'],
            'kelly_stake': joint.get('kelly_stake', 0.0),
            'kelly_return': joint.get('kelly_return', 0.0),
            'decimal': joint['decimal'],
        })
    return {'S-SGP': {'signal': _signal_block(taken, decided or taken),
                      'staking': _staking_block(taken),
                      'taken': len(taken),
                      'priced': len([p for p in sgp if p['joint'].get('priced')]),
                      'offered': len(sgp)}}


def _signal_block(taken, decided):
    """Prediction-quality block. Never contains a stake, a return or an ROI."""
    if not decided:
        return {'n': 0}
    outcomes = [1.0 if b['outcome'] == 1.0 else 0.0 for b in decided]
    model_probs = [b['p_model'] for b in decided]
    market_probs = [b['p_market_devig'] for b in decided if b['p_market_devig'] is not None]
    clusters = [b['season'] * 100 + b['week'] for b in decided]
    block = {
        'n': len(decided),
        'wins': int(sum(outcomes)),
        'pushes': len(taken) - len(decided),
        'hit_rate': sum(outcomes) / len(decided),
        'log_loss_model': metrics.log_loss(model_probs, outcomes),
        'brier_model': metrics.brier(model_probs, outcomes),
    }
    if len(market_probs) == len(decided):
        block['log_loss_market'] = metrics.log_loss(market_probs, outcomes)
        block['brier_market'] = metrics.brier(market_probs, outcomes)
        block['log_loss_gain'] = block['log_loss_market'] - block['log_loss_model']
        lcb = metrics.paired_log_loss_gain(model_probs, market_probs, outcomes, clusters)
        if lcb:
            block['log_loss_gain_lcb'] = lcb['lcb']
            block['log_loss_gain_se'] = lcb['se']
            block['clusters'] = lcb['clusters']
    return block


def _staking_block(taken):
    """Money block. Separate from signal by construction and by page layout."""
    if not taken:
        return {'bets': 0}
    flat_returns = [b['return'] for b in taken]
    flat_stakes = [b['stake'] for b in taken]
    kelly_returns = [b['kelly_return'] for b in taken]
    kelly_stakes = [b['kelly_stake'] for b in taken]
    return {
        'bets': len(taken),
        'flat_staked': sum(flat_stakes),
        'flat_net': sum(flat_returns),
        'flat_roi': metrics.roi(flat_returns, flat_stakes),
        'flat_max_drawdown': metrics.max_drawdown(flat_returns),
        'kelly_staked': sum(kelly_stakes),
        'kelly_net': sum(kelly_returns),
        'kelly_roi': metrics.roi(kelly_returns, kelly_stakes),
        'kelly_max_drawdown': metrics.max_drawdown(kelly_returns),
    }


# --------------------------------------------------------------------------
# Demotion replay
# --------------------------------------------------------------------------

TRAILING = 200
BRIER_TOLERANCE = 0.005
DRAWDOWN_TOLERANCE = 20.0


def demotion_replay(bets, strategies, trailing=TRAILING):
    """Walk the chronological bet sequence and find the first demotion trigger."""
    out = {}
    for code in strategies:
        sequence = [b for b in bets if b['strategy'] == code and b['stake'] > 0]
        out[code] = _replay_one(sequence, trailing)
    return out


def _replay_one(sequence, trailing):
    if len(sequence) < trailing:
        return {'status': 'insufficient history',
                'bets': len(sequence), 'required': trailing,
                'trigger': None, 'trailing_windows': 0}
    triggers = defaultdict(int)
    first = None
    cumulative = 0.0
    peak = 0.0
    for i in range(trailing - 1, len(sequence)):
        window = sequence[i - trailing + 1:i + 1]
        decided = [b for b in window if b['outcome'] != 0.5]
        index = i + 1
        if len(decided) >= 30:
            outcomes = [1.0 if b['outcome'] == 1.0 else 0.0 for b in decided]
            model_probs = [b['p_model'] for b in decided]
            market_probs = [b['p_market_devig'] for b in decided if b['p_market_devig'] is not None]
            clusters = [b['season'] * 100 + b['week'] for b in decided]
            if len(market_probs) == len(decided):
                lcb = metrics.paired_log_loss_gain(model_probs, market_probs,
                                                   outcomes, clusters)
                if lcb and lcb['lcb'] <= 0:
                    triggers['D1'] += 1
                    first = first or _first(first, index, sequence, 'D1', lcb['lcb'])
                brier_model = metrics.brier(model_probs, outcomes)
                brier_market = metrics.brier(market_probs, outcomes)
                if brier_model - brier_market > BRIER_TOLERANCE:
                    triggers['D2'] += 1
                    first = first or _first(first, index, sequence, 'D2',
                                            brier_model - brier_market)
        cumulative = sum(b['return'] for b in sequence[:i + 1])
        peak = max(peak, cumulative)
        if cumulative - peak < -DRAWDOWN_TOLERANCE:
            triggers['D3'] += 1
            first = first or _first(first, index, sequence, 'D3', cumulative - peak)
        if first:
            break
    return {'status': 'demoted' if first else 'never triggered',
            'bets': len(sequence), 'trailing_windows': len(sequence) - trailing + 1,
            'trigger': first, 'trigger_counts': dict(triggers)}


def _first(current, index, sequence, rule, value):
    if current:
        return current
    bet = sequence[index - 1]
    return {'rule': rule, 'bet_number': index, 'season': bet['season'],
            'week': bet['week'], 'gameday': bet['gameday'],
            'value': value, 'action': 'demote to paper, staking stops'}


def coverage_by_season(originations):
    """D5 coverage: share of scheduled markets carrying a price and a result."""
    out = {}
    for entry in originations:
        for row in entry['rows']:
            season = row['season']
            slot = out.setdefault(season, {'scheduled': 0, 'priced': 0, 'settled': 0})
            slot['scheduled'] += 1
            if row['market_line'] is not None or row['market_price'] is not None:
                slot['priced'] += 1
            if row['settled'] and row['outcome'] is not None:
                slot['settled'] += 1
    for season, slot in out.items():
        slot['coverage'] = slot['settled'] / slot['scheduled'] if slot['scheduled'] else None
    return out
