"""Origination engine: the eight origination requirements, implemented fail-closed.

Standard library only. Every function returns ``None`` (plus a reason) where a
value cannot be computed from a verified input: a missing market price is never
treated as zero, a missing chart slot is never filled from memory, and a
correlation is never published without the ``n`` it was computed from.

Requirement map
  R1 price snapshot store ....... ``validate_snapshot`` / ``snapshot_coverage``
  R2 verified results feed ...... ``load_results`` / ``settle`` / ``roi_readiness``
  R3 origination order .......... ``ORIGINATION_ORDER`` / ``originate``
  R4 fair, market, difference ... ``line_columns`` / ``price_columns``
  R5 signal vs staking .......... ``leaderboard_entry`` / ``rank``
  R6 depth of replacement ....... ``replacement_chain`` / ``unit_depth_index``
  R7 dependence with n .......... ``dependence_record``
  R8 demotion gate .............. ``demotion_gate``
"""

import csv
import json
from datetime import datetime
from pathlib import Path

from engine.core import (Outcome, american_to_decimal, dependence_gate, no_vig,
                         pearson, score_market)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'

# --------------------------------------------------------------------------
# Shared helpers


def parse_utc(value, field='timestamp'):
    """Accept only an explicit UTC instant. A date alone is not a capture time."""
    if not value or not isinstance(value, str):
        raise ValueError(f'{field}: a UTC instant is required, got {value!r}')
    try:
        return datetime.strptime(value.strip(), '%Y-%m-%dT%H:%M:%SZ')
    except ValueError as exc:
        raise ValueError(f'{field}: expected YYYY-MM-DDTHH:MM:SSZ, got {value!r}') from exc


def _blank(value):
    return value is None or (isinstance(value, str) and not value.strip())


def _round(value, places=4):
    return None if value is None else round(float(value), places)


# --------------------------------------------------------------------------
# R1 · Price-snapshot store — opening and closing numbers for every market we originate

PRICE_FIELDS = (
    'snapshot_id',        # stable id of the capture, one row per market per book
    'market_id',          # the market we originated: 2026-REG10-WAS-NYG-side
    'game_id',            # 2026-REG10-WAS-NYG
    'season',
    'week',
    'market_family',      # side | total | moneyline | prop
    'participant',        # side of the market the number applies to
    'book',
    'source_id',          # must be a registered source in evidence/sources.json
    'opening_line',       # handicap / total / None for moneyline
    'opening_price_american',
    'opening_captured_utc',
    'closing_line',
    'closing_price_american',
    'closing_captured_utc',
    'kickoff_utc',
    'limits_note',        # whether the quote was executable and at what limit
    'settlement_rule_version',
    'raw_hash',           # hash of the raw captured artefact
    'verified',           # 'true' only when a human or checker has read the raw artefact
)

MARKET_FAMILIES = ('side', 'total', 'moneyline', 'prop')

# Fields that must all be present for a snapshot to count as a usable open/close pair.
PAIR_REQUIRED = ('opening_price_american', 'opening_captured_utc',
                 'closing_price_american', 'closing_captured_utc', 'kickoff_utc',
                 'source_id', 'book', 'raw_hash')


def validate_snapshot(record, known_sources=None, strict=True):
    """Return the list of reasons a snapshot row is not usable.

    A row with an opening number but no closing number fails: a half-record would
    let an opening line be scored against a closing line it never had. ``strict``
    also demands provenance (source, book, raw hash) and a verified flag.
    """
    errors = []
    if not isinstance(record, dict):
        return ['record is not a mapping']
    for field in PRICE_FIELDS:
        if field not in record:
            errors.append(f'missing column: {field}')
    if errors:
        return errors

    if record['market_family'] not in MARKET_FAMILIES:
        errors.append(f"market_family must be one of {MARKET_FAMILIES}")
    if _blank(record['snapshot_id']) or _blank(record['market_id']) or _blank(record['game_id']):
        errors.append('snapshot_id, market_id and game_id must all be present')

    known = known_sources
    if known is not None and record['source_id'] not in known:
        errors.append(f"source_id {record['source_id']!r} is not a registered source")

    opening_price, closing_price = record['opening_price_american'], record['closing_price_american']
    for name, value in (('opening_price_american', opening_price),
                        ('closing_price_american', closing_price)):
        if _blank(value):
            errors.append(f'{name}: no price captured — the pair is incomplete')
            continue
        try:
            american_to_decimal(int(value))
        except (TypeError, ValueError):
            errors.append(f'{name}: not a valid American price')

    stamps = {}
    for name in ('opening_captured_utc', 'closing_captured_utc', 'kickoff_utc'):
        try:
            stamps[name] = parse_utc(record[name], name)
        except ValueError as exc:
            errors.append(str(exc))

    if 'opening_captured_utc' in stamps and 'closing_captured_utc' in stamps:
        if stamps['opening_captured_utc'] > stamps['closing_captured_utc']:
            errors.append('opening_captured_utc is later than closing_captured_utc')
    if 'closing_captured_utc' in stamps and 'kickoff_utc' in stamps:
        if stamps['closing_captured_utc'] > stamps['kickoff_utc']:
            errors.append('closing_captured_utc is after kickoff: it is not a closing price')
    if 'opening_captured_utc' in stamps and 'kickoff_utc' in stamps:
        if stamps['opening_captured_utc'] > stamps['kickoff_utc']:
            errors.append('opening_captured_utc is after kickoff')

    if record['market_family'] in ('side', 'total'):
        for name in ('opening_line', 'closing_line'):
            if _blank(record[name]):
                errors.append(f'{name}: a {record["market_family"]} market needs a line')

    if strict:
        for name in ('book', 'raw_hash'):
            if _blank(record[name]):
                errors.append(f'{name}: provenance missing')
        if str(record.get('verified', '')).strip().lower() != 'true':
            errors.append('verified: the raw artefact has not been checked by a human or checker')
        if _blank(record.get('settlement_rule_version')):
            errors.append('settlement_rule_version: the rules the price settles under are unknown')
    return errors


def load_snapshots(path=None):
    """Read the snapshot store. An absent or header-only file is zero records, not an error."""
    path = Path(path) if path else DATA / 'snapshots' / 'price-snapshots.csv'
    if not path.exists():
        return []
    with path.open(newline='') as handle:
        rows = list(csv.DictReader(handle))
    return [r for r in rows if any((v or '').strip() for v in r.values())]


def snapshot_coverage(records, game_ids=None):
    """How much of the slate the store actually prices.

    ``pct_of_games_priced`` is measured against the games we have results for, so
    the number cannot be inflated by counting markets nobody settled.
    """
    known_sources = _registered_source_ids()
    complete, incomplete, reasons = [], [], []
    for record in records:
        problems = validate_snapshot(record, known_sources)
        (complete if not problems else incomplete).append(record)
        reasons.extend(problems)
    games_priced = {r.get('game_id') for r in complete}
    denominator = len(game_ids) if game_ids else len(games_priced)
    return {
        'records': len(records),
        'complete_pairs': len(complete),
        'incomplete_records': len(incomplete),
        'markets': len({r.get('market_id') for r in complete}),
        'games_priced': len(games_priced),
        'games_in_results_feed': denominator,
        'pct_of_games_priced': (100.0 * len(games_priced & set(game_ids or games_priced))
                                / denominator) if denominator else 0.0,
        'blocking_reasons': sorted(set(reasons)),
    }


def _registered_source_ids():
    manifest = ROOT / 'evidence' / 'sources.json'
    if not manifest.exists():
        return None
    return {s['id'] for s in json.loads(manifest.read_text())}


# --------------------------------------------------------------------------
# R3 · Origination order: side first, then total, then moneyline

ORIGINATION_ORDER = ('side', 'total', 'moneyline')

ORDER_RATIONALE = {
    'side': 'The margin distribution is the coarsest, most stable object the joint '
            'score distribution produces, and it settles on a number the market also '
            'quotes. It is originated first so that nothing downstream can be tuned '
            'to make a side bet look better.',
    'total': 'The total consumes the same joint distribution through a different '
             'statistic. It is originated second, after the side is frozen, so a '
             'total cannot be chosen to agree with an already-published side.',
    'moneyline': 'A moneyline price adds no information the joint does not already '
                 'contain: it is the side evaluated at a handicap of zero. Publishing '
                 'it last makes that dependence visible and auditable.',
}


def _digest(distribution):
    """Stable fingerprint of a joint PMF so later steps cannot quietly use another one.

    Built with sha256 rather than ``hash`` because Python's string hash is salted
    per process and would make the published digest non-reproducible.
    """
    import hashlib
    canonical = ';'.join(
        f'{h}-{a}:{round(float(mass), 12):.12f}'
        for (h, a), mass in sorted(distribution.items()))
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def _require_done(steps, name):
    done = {s['market'] for s in steps}
    for required in ORIGINATION_ORDER[:ORIGINATION_ORDER.index(name)]:
        if required not in done:
            raise ValueError(f'{name} was originated before {required}; the order is '
                             f'{" -> ".join(ORIGINATION_ORDER)}')


def originate(distribution, handicaps=(0,), total_lines=(), line_unit=0.5):
    """Originate side, then total, then moneyline from one frozen joint distribution.

    ``handicaps`` and ``total_lines`` are the candidate numbers to price; they are
    inputs, never outputs. Every step records the same distribution digest so a
    later page can prove all three numbers came from one frozen object.
    """
    if not distribution:
        raise ValueError('a joint score distribution is required before anything is originated')
    digest = _digest(distribution)
    steps = []

    # 1 · side
    side_rows = []
    for handicap in handicaps:
        outcome = score_market(distribution, 'spread', handicap)
        side_rows.append({'handicap': handicap, 'win': outcome.win, 'push': outcome.push,
                          'loss': outcome.loss,
                          'fair_decimal': outcome.fair_decimal() if outcome.win > 0 else None})
    steps.append({'market': 'side', 'order': 1, 'distribution_digest': digest,
                  'rationale': ORDER_RATIONALE['side'], 'rows': side_rows})

    # 2 · total
    _require_done(steps, 'total')
    total_rows = []
    for line in total_lines:
        outcome = score_market(distribution, 'total_over', line)
        total_rows.append({'total_line': line, 'win': outcome.win, 'push': outcome.push,
                           'loss': outcome.loss,
                           'fair_decimal': outcome.fair_decimal() if outcome.win > 0 else None})
    steps.append({'market': 'total', 'order': 2, 'distribution_digest': digest,
                  'rationale': ORDER_RATIONALE['total'], 'rows': total_rows})

    # 3 · moneyline — the side evaluated at a handicap of zero.
    _require_done(steps, 'moneyline')
    money = score_market(distribution, 'moneyline')
    zero_handicap = next((r for r in side_rows if r['handicap'] == 0), None)
    steps.append({'market': 'moneyline', 'order': 3, 'distribution_digest': digest,
                  'rationale': ORDER_RATIONALE['moneyline'],
                  'rows': [{'side': 'home', 'win': money.win, 'push': money.push,
                            'loss': money.loss,
                            'fair_decimal': money.fair_decimal() if money.win > 0 else None}]})

    return {
        'order': ORIGINATION_ORDER,
        'line_unit': line_unit,
        'steps': steps,
        'consistency': _consistency(steps, zero_handicap, money),
    }


def _consistency(steps, zero_handicap, money):
    """The moneyline must be the side at a handicap of zero, or the run is broken."""
    digests = {s['distribution_digest'] for s in steps}
    checks = [{
        'check': 'all three steps used one frozen joint distribution',
        'passed': len(digests) == 1,
        'detail': f'{len(digests)} distinct distribution digest(s) across {len(steps)} steps',
    }]
    if zero_handicap:
        checks.append({
            'check': 'moneyline win probability equals the side priced at a handicap of 0',
            'passed': (abs(zero_handicap['win'] - money.win) < 1e-12
                       and abs(zero_handicap['loss'] - money.loss) < 1e-12),
            'detail': f"spread@0 win={zero_handicap['win']:.6f} vs moneyline win={money.win:.6f}",
        })
    else:
        checks.append({'check': 'moneyline reconciles with the side at a handicap of 0',
                       'passed': False,
                       'detail': 'no side was priced at a handicap of 0, so the reconciliation '
                                 'cannot be performed'})
    checks.append({'check': 'every step carried the predeclared order',
                   'passed': [s['market'] for s in steps] == list(ORIGINATION_ORDER),
                   'detail': ' -> '.join(s['market'] for s in steps)})
    return checks


# --------------------------------------------------------------------------
# R4 · Model fair line, market line and the difference as three separate columns

def line_columns(market_id, model_fair_line, market_line, market_price_american=None,
                 unit='points'):
    """A point-line row. The difference is its own column and is never zero-filled."""
    if model_fair_line is None and market_line is None:
        status = 'withheld: no model line and no market line'
    elif model_fair_line is None:
        status = 'withheld: the model has not produced a line'
    elif market_line is None:
        status = 'withheld: no market line was captured, so no comparison can be made'
    else:
        status = 'published'
    difference = None
    if model_fair_line is not None and market_line is not None:
        difference = float(model_fair_line) - float(market_line)
    return {
        'market_id': market_id,
        'model_fair_line': model_fair_line,
        'market_line': market_line,
        'difference': difference,
        'difference_direction': (None if difference in (None, 0) else
                                 'model above market' if difference > 0 else 'model below market'),
        'market_price_american': market_price_american,
        'unit': unit,
        'status': status,
    }


def price_columns(market_id, outcome, market_price_american, cost=0.0):
    """A price row. Fair decimal, market decimal and the edge are separate columns."""
    if not isinstance(outcome, Outcome):
        raise TypeError('an Outcome is required; probabilities are not passed loose')
    market_decimal = None if market_price_american in (None, '') else american_to_decimal(
        int(market_price_american))
    fair = outcome.fair_decimal()
    if market_decimal is None:
        status = 'withheld: no market price was captured'
        edge = ev = None
    else:
        status = 'published'
        edge = fair - market_decimal
        ev = outcome.ev(market_decimal, cost)
    return {
        'market_id': market_id,
        'model_fair_decimal': _round(fair, 4),
        'market_decimal': _round(market_decimal, 4),
        'difference_decimal': _round(edge, 4),
        'ev_per_unit': _round(ev, 6),
        'status': status,
    }


def two_way_no_vig_market_line(prices):
    """Reference market line from a captured two-way price pair, or None.

    The implied line is derived, never assumed: without both prices the market's
    own centre is unknown and the cell stays blank.
    """
    if not prices or any(p in (None, '') for p in prices):
        return None
    decimals = [american_to_decimal(int(p)) for p in prices]
    return _round(no_vig(decimals)[0], 6)


# --------------------------------------------------------------------------
# R2 · Verified results feed and the settlement it can and cannot support

RESULT_FIELDS = ('result_id', 'season', 'week', 'game_date', 'kickoff_time_utc',
                 'away_team', 'home_team', 'away_score', 'home_score', 'home_margin',
                 'total_points', 'home_result', 'overtime', 'source_id', 'game_url',
                 'retrieved_utc')


def load_results(path=None):
    path = Path(path) if path else DATA / 'results' / 'verified-results.csv'
    if not path.exists():
        return []
    with path.open(newline='') as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row['home_score'] = int(row['home_score'])
        row['away_score'] = int(row['away_score'])
        row['home_margin'] = int(row['home_margin'])
        row['total_points'] = int(row['total_points'])
    return rows


def settle(result, market_family, line=None):
    """Settle one market against a verified result. Line-based markets need a line."""
    if market_family not in ('moneyline', 'side', 'total'):
        raise ValueError('unsupported market family')
    if market_family == 'moneyline':
        margin = result['home_margin']
    else:
        if line is None or line == '':
            return {'settled': False, 'outcome': None,
                    'reason': f'no {market_family} line was ever captured for this game, so the '
                              f'market cannot be settled'}
        line = float(line)
        margin = (result['home_margin'] + line if market_family == 'side'
                  else result['total_points'] - line)
    if margin > 0:
        outcome = 'win'
    elif margin == 0:
        outcome = 'push'
    else:
        outcome = 'loss'
    return {'settled': True, 'outcome': outcome, 'reason': 'settled from the official final score'}


def feed_coverage(results):
    """What the feed can settle today, counted rather than asserted."""
    return {
        'results': len(results),
        'weeks': sorted({r['week'] for r in results}),
        'clubs': len({r['home_team'] for r in results} | {r['away_team'] for r in results}),
        'moneyline_settleable': sum(1 for r in results if settle(r, 'moneyline')['settled']),
        'side_settleable_without_a_line': 0,
        'total_settleable_without_a_line': 0,
        'score_only_rows': len(results),
    }


def roi_readiness(results, snapshots, min_games=1000):
    """Fail-closed gate: may ROI or a backtest be computed at all?"""
    coverage = snapshot_coverage(snapshots, [r['result_id'] for r in results])
    priced = coverage['pct_of_games_priced']
    reasons = []
    if coverage['complete_pairs'] == 0:
        reasons.append('the price-snapshot store holds no complete opening/closing pair')
    if priced < 100.0:
        reasons.append(f'only {priced:.1f}% of the games in the results feed have a captured price')
    if len(results) < min_games:
        reasons.append(f'the results feed holds {len(results)} games, below the predeclared '
                       f'minimum of {min_games} for a backtest')
    if any(not (r.get('overtime') or '').strip() for r in results):
        reasons.append('overtime is not published for every row, so totals cannot be settled '
                       'uniformly until that field is verified')
    return {
        'ready': not reasons,
        'reasons': reasons,
        'results': len(results),
        'complete_price_pairs': coverage['complete_pairs'],
        'pct_of_games_priced': priced,
    }


# --------------------------------------------------------------------------
# R6 · Depth of the replacement, not just the fact of one

def load_depth_charts(path=None):
    path = Path(path) if path else DATA / 'depth' / 'club-depth-charts-2026-11-14.json'
    return json.loads(path.read_text())


def find_slot(chart, player):
    """Return (unit, slot, column index) of a player on a club chart, or None."""
    for unit, slots in chart['units'].items():
        for slot, names in slots.items():
            for index, name in enumerate(names):
                if name == player:
                    return unit, slot, index
    return None


def replacement_chain(chart, slot, unavailable, unit=None):
    """How far down the published chart the next available player sits.

    ``strings_travelled`` is the difference between the string of the highest
    available player and the first string: 0 means the chart's first string is
    available, 1 means a second-string player is the next one up, 2 means the
    chart had to go to its third string, and so on. ``None`` means the chart
    exhausted its published columns and no replacement can be named without
    inventing one.
    """
    units = chart['units'] if unit is None else {unit: chart['units'][unit]}
    for name, slots in units.items():
        if slot in slots:
            row = slots[slot]
            break
    else:
        return {'slot': slot, 'status': 'no such slot on the chart',
                'strings_travelled': None, 'replacement': None}
    out_players = {u['player'] for u in unavailable}
    unavailable_columns = [i for i, p in enumerate(row) if p in out_players]
    available = [i for i in range(len(row)) if i not in unavailable_columns]
    if not available:
        return {'slot': slot, 'unit': name, 'status': 'every published string at this slot is out',
                'strings_travelled': None, 'replacement': None,
                'chart_columns_published': len(row)}
    first = available[0]
    return {
        'slot': slot,
        'unit': name,
        'chart_columns_published': len(row),
        'unavailable_on_chart': [row[i] for i in unavailable_columns],
        'first_available_index': first,
        'replacement_string': first + 1,
        'strings_travelled': first,          # 0 = first string available
        'replacement': row[first],
        'bench_remaining_below': len([i for i in available if i > first]),
        'chain': row[:first + 1],
        'status': 'derived from the published chart order',
    }


def unit_depth_index(chains):
    """Sum the strings travelled per unit and count what could not be resolved."""
    index = {}
    for chain in chains:
        unit = chain.get('unit') or 'unresolved'
        bucket = index.setdefault(unit, {'strings_travelled': 0, 'slots': 0,
                                         'unresolved': 0, 'bench_remaining': 0})
        bucket['slots'] += 1
        if chain.get('strings_travelled') is None:
            bucket['unresolved'] += 1
            continue
        bucket['strings_travelled'] += chain['strings_travelled']
        bucket['bench_remaining'] += chain.get('bench_remaining_below', 0)
    return index


def depth_register(charts, unavailable_by_club):
    """One row per charted player ruled out, with the depth the chart was pushed to."""
    rows = []
    for club, chart in charts['clubs'].items():
        unavailable = unavailable_by_club.get('clubs', {}).get(club, [])
        for entry in unavailable:
            found = find_slot(chart, entry['player'])
            if found is None:
                rows.append({
                    'club': club, 'player': entry['player'],
                    'report_position': entry['position'], 'game_status': entry['game_status'],
                    'slot': None, 'unit': None, 'strings_travelled': None,
                    'replacement': None, 'replacement_string': None,
                    'bench_remaining_below': None,
                    'status': 'ruled out but absent from every column of the club chart; '
                              'no replacement inferred',
                })
                continue
            unit, slot, index = found
            chain = replacement_chain(chart, slot, unavailable, unit=unit)
            rows.append({
                'club': club, 'player': entry['player'],
                'report_position': entry['position'], 'game_status': entry['game_status'],
                'slot': slot, 'unit': unit,
                'unavailable_string': index + 1,
                'strings_travelled': chain['strings_travelled'],
                'replacement': chain['replacement'],
                'replacement_string': chain.get('replacement_string'),
                'bench_remaining_below': chain.get('bench_remaining_below'),
                'status': chain['status'],
            })
    return rows


# --------------------------------------------------------------------------
# R7 · Dependence register — every value published with the n it came from

def dependence_record(label, x, y, source_id, min_n=30, confidence=0.95, deadband=0.10):
    """Correlate two officially sourced series and publish n, the interval and the gate.

    ``source_id`` is mandatory: a correlation without a source is not a number this
    project is allowed to publish. The pair must be equal length and non-constant.
    """
    if not source_id:
        raise ValueError('a dependence record requires the official source the numbers came from')
    if len(x) != len(y):
        raise ValueError('paired series of unequal length')
    if len(x) < 2:
        raise ValueError('at least two paired observations are required')
    rho = pearson(list(x), list(y))
    gate = dependence_gate(rho, len(x), min_n, confidence, deadband)
    return {
        'label': label,
        'rho': _round(rho, 4),
        'n': len(x),
        'confidence': confidence,
        'deadband': deadband,
        'min_n': min_n,
        'interval': tuple(_round(v, 4) for v in gate['interval']) if gate['interval'] else None,
        'verdict': gate['verdict'],
        'may_price_joint': gate['may_price_joint'],
        'reason': gate['reason'],
        'source_id': source_id,
    }


# --------------------------------------------------------------------------
# R5 · Signal and staking are separate columns, separate ranks, separate rewards

SIGNAL_FIELDS = ('markets_taken', 'markets_abstained', 'coverage', 'brier', 'log_loss',
                 'calibration_slope', 'clv_per_bet', 'hit_rate')
STAKING_FIELDS = ('units_risked', 'roi', 'max_drawdown_units', 'kelly_fraction',
                  'final_bankroll_units')
FORBIDDEN_IN_SIGNAL = set(STAKING_FIELDS)
FORBIDDEN_IN_STAKING = set(SIGNAL_FIELDS)


def leaderboard_entry(strategy_id, signal, staking, signal_gates=None):
    """Split a submission into a signal record and a staking record.

    Neither may carry the other's numbers, so a lucky staking run cannot lift a
    signal rank and a good signal cannot be buried by a staking choice.
    """
    if not isinstance(signal, dict) or not isinstance(staking, dict):
        raise TypeError('signal and staking must both be mappings')
    leaked = FORBIDDEN_IN_SIGNAL & set(signal)
    if leaked:
        raise ValueError(f'staking field(s) in the signal record: {sorted(leaked)}')
    leaked = FORBIDDEN_IN_STAKING & set(staking)
    if leaked:
        raise ValueError(f'signal field(s) in the staking record: {sorted(leaked)}')
    for field in SIGNAL_FIELDS:
        signal.setdefault(field, None)
    for field in STAKING_FIELDS:
        staking.setdefault(field, None)
    gates = signal_gates or {}
    return {
        'strategy_id': strategy_id,
        'signal': signal,
        'staking': staking,
        'signal_eligible': _signal_eligible(signal, gates),
    }


def _signal_eligible(signal, gates):
    reasons = []
    min_markets = gates.get('min_markets', 0)
    min_coverage = gates.get('min_coverage', 0.0)
    if signal.get('markets_taken') is None or signal['markets_taken'] < min_markets:
        reasons.append(f'fewer than {min_markets} markets taken')
    if signal.get('coverage') is None or signal['coverage'] < min_coverage:
        reasons.append(f'coverage below {min_coverage:.0%}')
    if signal.get('brier') is None:
        reasons.append('no proper scoring rule reported')
    return {'eligible': not reasons, 'reasons': reasons}


def signal_score(entry, baseline_brier=0.25):
    """Skill score from a proper scoring rule only. Staking never enters it."""
    brier = (entry.get('signal') or {}).get('brier')
    if brier is None:
        return None
    return 1.0 - float(brier) / float(baseline_brier)


def rank(entries, baseline_brier=0.25):
    """Two rankings from one submission set, published side by side."""
    scored = []
    for entry in entries:
        scored.append({
            'strategy_id': entry['strategy_id'],
            'signal_score': signal_score(entry, baseline_brier),
            'signal_eligible': entry['signal_eligible']['eligible'],
            'staking_roi': (entry.get('staking') or {}).get('roi'),
            'staking_units': (entry.get('staking') or {}).get('units_risked'),
        })
    by_signal = sorted((s for s in scored if s['signal_score'] is not None),
                       key=lambda s: -s['signal_score'])
    for position, row in enumerate(by_signal, 1):
        row['signal_rank'] = position if row['signal_eligible'] else None
    by_roi = sorted((s for s in scored if s['staking_roi'] is not None),
                    key=lambda s: -s['staking_roi'])
    for position, row in enumerate(by_roi, 1):
        row['staking_rank'] = position
    return {'by_signal': by_signal, 'by_staking': by_roi}


def masking_report(entries, baseline_brier=0.25, gap=2):
    """Flag any entry whose staking rank is far better than its signal rank."""
    ranked = rank(entries, baseline_brier)
    signal_position = {r['strategy_id']: i for i, r in enumerate(ranked['by_signal'], 1)}
    staking_position = {r['strategy_id']: i for i, r in enumerate(ranked['by_staking'], 1)}
    flagged = []
    for strategy, staking_rank in staking_position.items():
        sig = signal_position.get(strategy)
        if sig is not None and sig - staking_rank >= gap:
            flagged.append({'strategy_id': strategy, 'signal_rank': sig,
                            'staking_rank': staking_rank,
                            'note': 'staking rank leads the signal rank by '
                                    f'{sig - staking_rank} places; treat the ROI rank as a '
                                    'staking result, not as evidence of signal'})
    return flagged


# --------------------------------------------------------------------------
# R8 · Demotion gate: send a live strategy back to paper

DEMOTION_POLICY = {
    'consecutive_bad_windows': 3,     # windows below the signal floor before demotion
    'signal_score_floor': 0.0,        # skill score a live strategy must beat
    'clv_floor_per_bet': 0.0,         # closing-line value must not be negative on average
    'max_drawdown_units': 20.0,       # bankroll drawdown that ends a live run
    'min_snapshot_coverage': 100.0,   # % of live decisions that must have a captured price
    're_promotion': 'a demoted strategy must pass every promotion gate again on a fresh '
                    'sealed period; it is never restored automatically',
}


def demotion_gate(track, windows, policy=None):
    """Decide whether a live strategy stays live.

    Fail-closed: a window with a missing measurement is a measurement that cannot
    clear the gate, so it counts as a breach. A strategy with no live windows at
    all is not live, and the gate says so rather than guessing.
    """
    policy = dict(DEMOTION_POLICY if policy is None else policy)
    if track != 'live':
        return {'track': track, 'decision': track, 'triggers': [],
                'reason': 'the strategy is not live, so the demotion gate has nothing to decide',
                're_promotion': policy['re_promotion']}
    if not windows:
        return {'track': track, 'decision': 'paper', 'triggers': ['no live evaluation window'],
                'reason': 'nothing has been measured in the live period',
                're_promotion': policy['re_promotion']}

    triggers, streak = [], 0
    for index, window in enumerate(windows, 1):
        score = window.get('signal_score')
        clv = window.get('clv_per_bet')
        drawdown = window.get('drawdown_units')
        coverage = window.get('snapshot_coverage_pct')
        breached = False
        if score is None:
            triggers.append(f'window {index}: signal score was not measured')
            breached = True
        elif score <= policy['signal_score_floor']:
            triggers.append(f'window {index}: signal score {score} at or below the floor '
                            f"{policy['signal_score_floor']}")
            breached = True
        if clv is None:
            triggers.append(f'window {index}: closing-line value was not measured')
            breached = True
        elif clv < policy['clv_floor_per_bet']:
            triggers.append(f'window {index}: closing-line value {clv} below the floor')
            breached = True
        if drawdown is None:
            triggers.append(f'window {index}: drawdown was not measured')
            breached = True
        elif drawdown > policy['max_drawdown_units']:
            triggers.append(f'window {index}: drawdown {drawdown} units exceeds '
                            f"{policy['max_drawdown_units']}")
            breached = True
        if coverage is None:
            triggers.append(f'window {index}: price-snapshot coverage was not measured')
            breached = True
        elif coverage < policy['min_snapshot_coverage']:
            triggers.append(f'window {index}: only {coverage}% of live decisions had a captured '
                            'price')
            breached = True
        streak = streak + 1 if breached else 0

    demote = streak >= int(policy['consecutive_bad_windows']) or bool(
        triggers and any('drawdown' in t and 'exceeds' in t for t in triggers))
    return {
        'track': track,
        'decision': 'paper' if demote else 'live',
        'windows': len(windows),
        'closing_streak': streak,
        'triggers': triggers,
        'policy': policy,
        'reason': ('demoted: ' + '; '.join(triggers[-int(policy['consecutive_bad_windows']):])
                   if demote else 'no demotion condition met in the evaluated windows'),
        're_promotion': policy['re_promotion'],
    }


# --------------------------------------------------------------------------
# Roll-up used by the page and the tests

def readiness():
    """One dict describing, from the committed files only, how far each requirement got."""
    results = load_results()
    snapshots = load_snapshots()
    coverage = snapshot_coverage(snapshots, [r['result_id'] for r in results])
    charts = load_depth_charts()
    unavailable = json.loads((DATA / 'depth' / 'week-10-2026-unavailable.json').read_text())
    register = depth_register(charts, unavailable)
    roi = roi_readiness(results, snapshots)
    return {
        'r1_price_snapshots': coverage,
        'r2_results_feed': feed_coverage(results),
        'r2_roi_readiness': roi,
        'r3_order': ORIGINATION_ORDER,
        'r6_depth_register_rows': len(register),
        'r6_depth_register': register,
        'r6_unit_index': unit_depth_index(
            [r for r in register if r['slot']] ),
    }
