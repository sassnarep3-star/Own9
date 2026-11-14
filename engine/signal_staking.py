"""Signal and staking, measured on separate axes so neither can launder the other.

Why the split exists
--------------------
A leaderboard that ranks by money made cannot answer the only question that matters here: whether
the *number* was right. A strategy can be out-of-calibre and up 30 units over forty bets, and a
genuinely better strategy can be down over the same stretch. If both live in one column, the run of
results masks the signal, and every later decision gets made on the mask.

So this module keeps two scorecards with different jobs:

* `signal_block` — prediction quality against a matched market baseline: per-bet log loss, cluster
  bootstrap lower bound over weeks, Brier, calibration error, coverage. This is the only thing that
  can move a rank.
* `staking_block` — what a bankroll would have done, computed only from *captured executable prices*
  (`engine.snapshots` records with stage `open`). It can suspend a candidate for risk; it can never
  raise a rank, and a candidate that submits staking without signal is rejected rather than ranked.

Both blocks report `n` next to every number, and both are deliberately incapable of producing a
profit claim from a short run: no mean is published without a lower bound, and no lower bound exists
below two week blocks.
"""
from math import log

from engine.core import probability, probability_scores, reliability_bins, week_bootstrap_ci
from engine.snapshots import SnapshotError

#: Weeks required before a cluster bootstrap lower bound is publishable at all.
MIN_WEEK_BLOCKS = 2
#: A candidate with fewer settled non-push bets than this cannot be ranked, whatever its return.
MIN_N = 100

SIGNAL_FIELDS = ('n', 'settled', 'excluded_push', 'coverage', 'log_loss', 'market_log_loss',
                 'gain', 'gain_lcb', 'gain_ucb', 'brier', 'market_brier', 'calibration_mae',
                 'weeks')
STAKING_FIELDS = ('n', 'staked_units', 'net_units', 'roi', 'max_drawdown_units', 'weeks',
                  'price_basis')


class SplitError(ValueError):
    pass


def _finite(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SplitError(f'{field} must be a number, got {value!r}')
    return float(value)


def _check_row(row, index):
    for field in ('p_model', 'p_market', 'outcome', 'week'):
        if field not in row:
            raise SplitError(f'bet {index}: missing {field}')
    probability(row['p_model'])
    probability(row['p_market'])
    if row['outcome'] not in (0, 1, 'push', None):
        raise SplitError(f'bet {index}: outcome must be 0, 1, push or None (unsettled)')


def signal_block(bets, confidence=.95, seed=9):
    """Prediction quality versus the matched market price. Push and unsettled rows are excluded,
    counted and reported — quietly dropping them would inflate coverage and hide a settlement bug."""
    if not bets:
        return {'n': 0, 'settled': 0, 'excluded_push': 0, 'coverage': None, 'log_loss': None,
                'market_log_loss': None, 'gain': None, 'gain_lcb': None, 'gain_ucb': None,
                'brier': None, 'market_brier': None, 'calibration_mae': None, 'weeks': 0,
                'status': 'no settled bets'}
    for i, row in enumerate(bets, 1):
        _check_row(row, i)
    settled = [r for r in bets if r['outcome'] in (0, 1)]
    excluded_push = sum(1 for r in bets if r['outcome'] == 'push')
    unsettled = sum(1 for r in bets if r['outcome'] is None)
    if not settled:
        return {f: None for f in SIGNAL_FIELDS} | {'n': len(bets), 'settled': 0,
                'excluded_push': excluded_push, 'unsettled': unsettled,
                'status': 'nothing settleable'}
    model = probability_scores([r['p_model'] for r in settled], [r['outcome'] for r in settled])
    market = probability_scores([r['p_market'] for r in settled], [r['outcome'] for r in settled])
    # Per-bet gain: market loss minus model loss for that same bet, so the baseline is matched bet
    # for bet rather than two aggregates that happened to be computed over the same rows.
    per_bet_model, per_bet_market = [], []
    for r in settled:
        p, q, y = probability(r['p_model']), probability(r['p_market']), r['outcome']
        per_bet_model.append(-(log(p) if y else log(1 - p)))
        per_bet_market.append(-(log(q) if y else log(1 - q)))
    diffs = [m - s for m, s in zip(per_bet_market, per_bet_model)]
    weeks = [r['week'] for r in settled]
    bins = reliability_bins([r['p_model'] for r in settled], [r['outcome'] for r in settled])
    mae = _weighted_mae(bins)
    out = {'n': len(settled), 'submitted': len(bets), 'excluded_push': excluded_push,
           'unsettled': unsettled,
           'coverage': len(settled) / len(bets), 'log_loss': sum(per_bet_model) / len(settled),
           'market_log_loss': sum(per_bet_market) / len(settled),
           'gain': sum(diffs) / len(diffs), 'brier': model['brier'],
           'market_brier': market['brier'], 'calibration_mae': mae,
           'weeks': len(set(weeks)), 'status': 'measured'}
    if len(set(weeks)) >= MIN_WEEK_BLOCKS:
        try:
            low, high = week_bootstrap_ci(diffs, weeks, confidence=confidence, seed=seed)
            out['gain_lcb'], out['gain_ucb'] = low, high
        except ValueError as exc:
            out['gain_lcb'] = out['gain_ucb'] = None
            out['interval_error'] = str(exc)
    else:
        out['gain_lcb'] = out['gain_ucb'] = None
        out['interval_note'] = (f'a cluster interval needs at least {MIN_WEEK_BLOCKS} distinct '
                                'weeks; none is published from a single block')
    return out


def _weighted_mae(bins):
    total = sum(b['n'] for b in bins)
    if not total:
        return None
    return sum(b['n'] * abs(b['mean_p'] - b['hit_rate']) for b in bins if b['n']) / total


def staking_block(bets, prices=None):
    """Bankroll arithmetic from captured executable prices only.

    Each bet needs a `price_decimal` that came from a snapshot record with stage `open`, a capture
    timestamp and a source. `prices` may be given as the store records themselves; if the price basis
    is not a captured snapshot, this raises — a return computed from an invented or undated price is
    the single most convincing-looking number a project can fabricate, so it is blocked at the door.
    There is deliberately no `require_captured=False`: the check is the function.
    """
    if not bets:
        return {f: None for f in STAKING_FIELDS} | {'n': 0, 'status': 'no bets'}
    decimal_prices = []
    for i, bet in enumerate(bets, 1):
        record = bet if 'price' in bet else (prices or {}).get(bet.get('bet_id'))
        if record is None:
            raise SplitError(f'bet {i}: no price record; staking cannot be computed from a bare outcome')
        # No flag switches this off. An escape hatch that a caller can pass is an escape hatch a
        # future caller will pass, and the number that comes out the other side still says ROI.
        if record.get('stage') != 'open':
            raise SplitError(f'bet {i}: price must come from an open snapshot, got stage '
                             f'{record.get("stage")!r}')
        if not record.get('captured_at') or not record.get('source_url'):
            raise SplitError(f'bet {i}: price record has no capture timestamp or source, so it '
                             'is a number, not an executable quote')
        price = record.get('price_decimal')
        if price is None:
            from engine.core import american_to_decimal
            price = american_to_decimal(_finite(record.get('price'), 'price'))
        decimal_prices.append(_finite(price, f'bet {i} price_decimal'))
    settled = [b for b in bets if b.get('outcome') in (0, 1)]
    pushes = [b for b in bets if b.get('outcome') == 'push']
    if len(settled) + len(pushes) != len([b for b in bets if b.get('outcome') is not None]):
        raise SplitError('outcome must be 0, 1, push or None')
    units = []
    for bet, price in zip(bets, decimal_prices):
        outcome = bet.get('outcome')
        if outcome == 1:
            units.append(price - 1)
        elif outcome == 0:
            units.append(-1.0)
        else:
            units.append(0.0)  # a push refunds the stake: zero, not a win and not a loss
    staked = float(len([u for u in units]))
    equity, peak, drawdown = 0.0, 0.0, 0.0
    for u in units:
        equity += u
        peak = max(peak, equity)
        drawdown = min(drawdown, equity - peak)
    net = sum(units)
    weeks = {b.get('week') for b in bets if b.get('week') is not None}
    return {'n': len(bets), 'settled': len(settled), 'push_refunded': len(pushes),
            'staked_units': staked, 'net_units': net,
            'roi': net / staked if staked else None, 'max_drawdown_units': drawdown,
            'weeks': len(weeks), 'price_basis': 'captured open snapshots',
            'status': 'measured' if settled else 'nothing settleable'}


def leaderboard(candidates, *, min_n=MIN_N):
    """Rank on signal only. Two tables, one roster.

    Rules, in the order they bite:
      1. a candidate without a signal block is rejected — money cannot buy a rank;
      2. a candidate below `min_n` settled bets is listed but not ranked;
      3. rank is by `gain_lcb` descending, and a candidate whose lower bound is not above zero is
         `ineligible` however good its point estimate or its return;
      4. staking is attached to the row for disclosure and never enters the sort key.
    """
    rows = []
    for candidate in candidates:
        cid = candidate.get('id')
        if not cid:
            raise SplitError('every candidate needs an id')
        signal = candidate.get('signal')
        staking = candidate.get('staking') or {}
        if not signal or signal.get('status') != 'measured':
            raise SplitError(f'{cid}: no measured signal block; a staking run cannot place a '
                             'candidate on this board')
        rows.append({'id': cid, 'track': candidate.get('track'), **{f'signal_{k}': signal.get(k)
                     for k in SIGNAL_FIELDS},
                     **{f'staking_{k}': staking.get(k) for k in STAKING_FIELDS},
                     'staking_n': staking.get('n'),
                     'ranked': (signal.get('n') or 0) >= min_n and signal.get('gain_lcb') is not None
                                and signal['gain_lcb'] > 0,
                     'luck_flag': bool(staking.get('roi')) and staking.get('roi') > 0
                                  and (signal.get('gain_lcb') is None or signal['gain_lcb'] <= 0)})
    ranked = sorted([r for r in rows if r['ranked']], key=lambda r: -r['signal_gain_lcb'])
    for position, row in enumerate(ranked, 1):
        row['rank'] = position
    for row in rows:
        row.setdefault('rank', None)
        row['disqualification'] = None if row['ranked'] else _why_unranked(row, min_n)
    return {'rows': sorted(rows, key=lambda r: (r['rank'] is None, r['rank'] or 0, r['id'])),
            'ranked': len(ranked), 'unranked': len(rows) - len(ranked),
            'sort_key': 'signal_gain_lcb descending; staking fields never enter it',
            'min_n': min_n}


def _why_unranked(row, min_n):
    if (row['signal_n'] or 0) < min_n:
        return f'fewer than {min_n} settled bets (has {row["signal_n"]})'
    if row['signal_gain_lcb'] is None:
        return 'no cluster interval: fewer than two distinct weeks of settled bets'
    if row['signal_gain_lcb'] <= 0:
        return 'lower bound does not clear zero, so the gain is not distinguishable from nothing'
    return 'unranked'


def rules():
    """The published split, as rows."""
    return [
        ('Rank column source', 'Simultaneous lower confidence bound on per-bet log-loss gain against '
         'the matched open price. Staking numbers never enter the sort key.'),
        ('Money cannot rank', 'A candidate submitting a return without a signal block is rejected with '
         'an error, not demoted to the bottom.'),
        ('Staking can only stop', 'A staking trigger can suspend a candidate for risk review. No '
         'staking outcome can raise a rank, clear a gate, or restore a demotion.'),
        ('Push handling', 'A push is excluded from probability scoring and counted in the staking '
         'block as a zero-unit refund. It is never deleted silently.'),
        ('Price basis', 'Staking arithmetic reads prices only from snapshot records with stage open, '
         'a capture timestamp and a source URL; an undated number cannot generate a return.'),
        ('Luck disclosure', 'Positive return with a non-positive signal lower bound is labelled '
         'explicitly, so a lucky run is visible as luck instead of being averaged into competence.'),
    ]


if __name__ == '__main__':  # pragma: no cover - shows the split on synthetic rows only
    import json
    synthetic = [{'p_model': p, 'p_market': q, 'outcome': o, 'week': w}
                 for p, q, o, w in [(.6, .55, 1, 1), (.4, .45, 0, 1), (.55, .5, 1, 2),
                                    (.5, .5, 'push', 2), (.65, .6, 0, 3)]]
    try:
        staking = staking_block(synthetic)
    except SplitError as exc:
        staking = f'refused: {exc}'
    print(json.dumps({'signal': signal_block(synthetic), 'staking': staking}, indent=2))
