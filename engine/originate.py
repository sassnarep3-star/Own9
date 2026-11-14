"""Origination order — side, then total, then moneyline — and the fair/market/difference columns.

Why an order at all
-------------------
Pricing a game from three separate models produces three separate errors and no way to tell which
one to believe. Pricing it from one joint score distribution means the markets are consistent by
construction: the moneyline cannot contradict the side, because the moneyline *is* the side's
distribution read at line 0. So the order here is not cosmetic sequencing:

1. `side`      — the home handicap, i.e. the disagreement about the margin. This is the primitive.
2. `total`     — the agreed scoring volume, read off the same distribution.
3. `moneyline` — derived from the same distribution. It is the last stage precisely so it can never
                  be fitted independently, and a log that prices the moneyline first is rejected.

A moneyline fitted first is the tell of a model that was never a score model at all.

The columns
-----------
`columns()` produces the three published fields as genuinely separate values — `fair_line`,
`market_line`, `difference` — plus the units and status needed to read them. The rule that matters:
**a missing value stays missing.** If there is no market line, `difference` is null with a reason;
it is never `fair_line − 0`, and a null is never written as `0.0`, because a difference of zero is
a claim (we agree with the market) while a null is a fact (we have nothing to compare to).

The published fair line is a *reference* line: a median of the model's own margin distribution at
the half-point grid. It is not an executable price and must not be shown next to a profit figure.
"""
from engine.core import distribution_lines, finite, score_market
from engine.snapshots import pair_index

#: The mandated order. Any deviation is an error, not a style choice.
STAGE_ORDER = ('side', 'total', 'moneyline')
#: Which store market each origination stage is allowed to touch, and in what direction.
STAGE_MARKET = {'side': 'SPREAD', 'total': 'TOTAL', 'moneyline': 'MONEYLINE'}
#: Half-point grid: the only line increment a spread or total is quoted on in this market.
GRID = 0.5
#: Smallest movement worth calling a difference on this grid. Below it, the model and the market
#: are the same number at any quoted precision, and saying "difference: 0.05" would be noise.
MINIMUM_TICK = 0.5


class OriginationError(ValueError):
    pass


def _grid_candidates(centre, span=6.0):
    """Half-point values within `span` of a continuous centre, nearest first."""
    low = int((centre - span) / GRID) * GRID
    out = []
    value = low
    while value <= centre + span + 1e-12:
        out.append(round(value, 4))
        value += GRID
    return sorted(out, key=lambda v: (abs(v - centre), v))


def fair_side(distribution):
    """Fair home handicap on the quoted grid: the line that best splits the cover probability.

    Ties on the line are push mass, reported rather than redistributed, because a sportsbook
    refunds them and a model that quietly renormalises is describing a different bet.
    """
    reference = distribution_lines(distribution)['home_spread_reference']
    best = None
    for line in _grid_candidates(reference):
        outcome = score_market(distribution, 'spread', line)
        # Compare the win and loss masses with the push mass excluded from both: the fair handicap
        # is where the non-push action is level, which is the definition the market quotes against.
        denominator = outcome.win + outcome.loss
        imbalance = abs(outcome.win - outcome.loss) / denominator if denominator else 1.0
        candidate = {'line': line, 'win': outcome.win, 'loss': outcome.loss,
                     'push': outcome.push, 'imbalance': imbalance}
        if best is None or (candidate['imbalance'], abs(candidate['line']),
                            candidate['line']) < (best['imbalance'], abs(best['line']), best['line']):
            best = candidate
    if best is None:
        raise OriginationError('no candidate line for this distribution')
    return {'stage': 'side', 'market': 'SPREAD', 'fair_line': best['line'],
            'cover': best['win'], 'push': best['push'], 'non_cover': best['loss'],
            'imbalance': best['imbalance'], 'continuous_reference': reference,
            'grid': GRID, 'sign_convention': 'home handicap received (negative = home favourite)'}


def fair_total(distribution):
    """Fair team-total line on the grid, from the same joint distribution as the side."""
    reference = distribution_lines(distribution)['total_reference']
    best = None
    for line in _grid_candidates(reference):
        outcome = score_market(distribution, 'total_over', line)
        denominator = outcome.win + outcome.loss
        imbalance = abs(outcome.win - outcome.loss) / denominator if denominator else 1.0
        candidate = {'line': line, 'over': outcome.win, 'push': outcome.push,
                     'under': outcome.loss, 'imbalance': imbalance}
        if best is None or (candidate['imbalance'], abs(candidate['line'] - reference),
                            candidate['line']) < (best['imbalance'],
                                                   abs(best['line'] - reference), best['line']):
            best = candidate
    return {'stage': 'total', 'market': 'TOTAL', 'fair_line': best['line'],
            'over': best['over'], 'under': best['under'], 'push': best['push'],
            'imbalance': best['imbalance'], 'continuous_reference': reference, 'grid': GRID,
            'sign_convention': 'points scored by both teams, overtime included per ticket rules'}


def fair_moneyline(distribution):
    """Fair moneyline, derived from the same distribution rather than fitted separately.

    Returns null prices when the model puts zero mass on winning or on losing, because a fair price
    for an impossible outcome is not infinity in a table — it is the absence of a price.
    """
    outcome = score_market(distribution, 'moneyline')
    fair_home = outcome.fair_decimal()
    return {'stage': 'moneyline', 'market': 'MONEYLINE',
            'fair_line': None,  # a moneyline has no line; the price carries the information
            'home_win': outcome.win, 'tie': outcome.push, 'away_win': outcome.loss,
            'fair_decimal_home': fair_home,
            'fair_decimal_away': None if outcome.loss == 0 else 1 + outcome.win / outcome.loss,
            'depends_on': 'the joint score distribution also used by side and total'}


def originate(distribution, *, now_utc=None):
    """Run the three stages in the mandated order and return an auditable ledger."""
    stages = [fair_side(distribution), fair_total(distribution), fair_moneyline(distribution)]
    log = [{'sequence': i + 1, 'stage': stage['stage'], 'market': stage['market'],
            'produced_utc': now_utc, 'output': stage,
            'depends_on': None if i == 0 else STAGE_ORDER[i - 1]}
           for i, stage in enumerate(stages)]
    problems = validate_order(log) + consistency_check(distribution, stages)
    if problems:
        raise OriginationError('origination rejected: ' + '; '.join(problems))
    return log


def validate_order(log):
    """Return a list of order violations. Empty means the log could only have been written in order."""
    problems = []
    seen = {}
    for index, entry in enumerate(log, 1):
        stage = entry.get('stage')
        if stage not in STAGE_ORDER:
            problems.append(f'entry {index}: unknown stage {stage!r}')
            continue
        if entry.get('sequence') != index:
            problems.append(f'entry {index}: sequence field says {entry.get("sequence")!r}')
        if stage in seen:
            problems.append(f'entry {index}: stage {stage} originated twice')
        seen[stage] = index
    positions = [STAGE_ORDER.index(entry['stage']) for entry in log
                     if entry.get('stage') in STAGE_ORDER]
    if positions != sorted(positions):
        problems.append('stages are out of order: ' + ' -> '.join(e['stage'] for e in log))
    for entry in log:
        stage = entry.get('stage')
        if stage == 'moneyline' and entry.get('depends_on') != 'total':
            problems.append('moneyline must be declared as derived from the total stage, not fitted '
                            'independently')
        if stage == 'total' and entry.get('depends_on') != 'side':
            problems.append('total must declare the side stage as its input')
        if stage == 'side' and entry.get('depends_on') is not None:
            problems.append('side is the primitive stage and may depend on nothing')
    if 'side' in seen and 'moneyline' in seen and seen['moneyline'] < seen['side']:
        problems.append('moneyline recorded before side')
    return problems


def consistency_check(distribution, stages):
    """The order earns its keep only if the three prices agree with each other.

    Recomputes each stage's published probabilities from the distribution and requires them to match
    what was recorded. A model that quotes a -7 favourite beside a 50/50 moneyline is internally
    inconsistent and this catches it without knowing anything about the game.
    """
    by_stage = {s['stage']: s for s in stages}
    problems = []
    for stage in STAGE_ORDER:
        if stage not in by_stage:
            problems.append(f'{stage} stage missing')
    if problems:
        return problems
    side = score_market(distribution, 'spread', by_stage['side']['fair_line'])
    total = score_market(distribution, 'total_over', by_stage['total']['fair_line'])
    money = score_market(distribution, 'moneyline')
    checks = [('side win', by_stage['side']['cover'], side.win),
              ('side loss', by_stage['side']['non_cover'], side.loss),
              ('side push', by_stage['side']['push'], side.push),
              ('total over', by_stage['total']['over'], total.win),
              ('total under', by_stage['total']['under'], total.loss),
              ('moneyline home', by_stage['moneyline']['home_win'], money.win),
              ('moneyline tie', by_stage['moneyline']['tie'], money.push),
              ('moneyline away', by_stage['moneyline']['away_win'], money.loss)]
    for name, published, recomputed in checks:
        if published is None or abs(finite(published) - recomputed) > 1e-9:
            problems.append(f'{name}: published {published!r} does not reproduce from the '
                            'distribution ({recomputed:.6f})')
    # The side and the moneyline must be the same bet at different lines: at a zero handicap the
    # win mass has to equal the moneyline home-win mass.
    zero = score_market(distribution, 'spread', 0)
    if abs(zero.win - money.win) > 1e-9 or abs(zero.loss - money.loss) > 1e-9:
        problems.append('line-0 spread probabilities differ from the moneyline probabilities, so '
                        'the stages were not priced from one distribution')
    return problems


def difference(fair_line, market_line):
    """The third published column, computed — never supplied.

    Both inputs must be numbers or both must be None; a fair line beside a missing market line is a
    difference of unknown size, and the honest field is null with a reason.
    """
    if fair_line is None or market_line is None:
        missing = 'fair line not published (no validated model)' if fair_line is None else \
                  'no market line captured'
        if fair_line is None and market_line is None:
            missing = 'neither a fair line nor a market line exists'
        return {'fair_line': fair_line, 'market_line': market_line, 'difference': None,
                'difference_ticks': None, 'direction': 'not comparable', 'status': 'blank',
                'reason': missing}
    fair, market = finite(fair_line), finite(market_line)
    delta = round(fair - market, 6)
    return {'fair_line': fair, 'market_line': market, 'difference': delta,
            'difference_ticks': int(round(delta / MINIMUM_TICK)) if MINIMUM_TICK else None,
            'direction': 'model higher' if delta > 0 else 'model lower' if delta < 0 else 'equal',
            'status': 'measured', 'reason': None}


def columns(fair, market_record, *, game_id=None):
    """Build one published row: fair line, market line, and the difference, as separate columns.

    `market_record` is a snapshot-store record (stage `open`) or None. The market line is admitted
    only from a record that carries a price *and* a capture timestamp *and* a stage label, which is
    the whole point of keeping the columns separate: the difference column cannot be populated by
    an undated number that happens to look like a line.
    """
    if market_record is None:
        market_line, market_status = None, 'no snapshot record for this market side'
    elif market_record.get('price') is None:
        market_line, market_status = None, 'snapshot exists but carries no price'
    elif not market_record.get('captured_at'):
        market_line, market_status = None, 'snapshot carries no capture timestamp'
    else:
        market_line, market_status = market_record.get('line'), 'captured'
    row = {'game_id': game_id, 'market': fair['market'], 'stage': fair['stage']}
    row.update(difference(fair.get('fair_line'), market_line))
    row['market_status'] = market_status
    row['fair_line_basis'] = 'reference line from the model distribution; not an executable price'
    return row


def rows_from_store(distributions, records, game_ids):
    """Originate every market for every game in the slate and join it to the captured store."""
    pairs = pair_index(records)
    out = []
    for game_id in game_ids:
        stages = originate(distributions[game_id])
        for entry in stages:
            market = STAGE_MARKET[entry['stage']]
            for side in ('HOME', 'AWAY') if market != 'TOTAL' else ('OVER', 'UNDER'):
                stage_records = pairs.get((game_id, market, side), {})
                open_record = stage_records.get('open')
                out.append({'game_id': game_id, 'entry': entry['sequence'],
                            'side': side, 'close_present': 'close' in stage_records,
                            **columns(entry['output'], open_record, game_id=game_id)})
    return out


def stage_labels():
    """Human-readable statement of the order, for the published page."""
    return [
        ('1 · side', 'Price the disagreement about the margin first: the home handicap, with push '
         'mass reported separately instead of being split across the two sides.'),
        ('2 · total', 'Read scoring volume off the same distribution the side was priced from, so '
         'the two cannot disagree about how many points are coming.'),
        ('3 · moneyline', 'Derive win/tie/loss probabilities from that distribution. Never a '
         'separate fit: a moneyline priced first is a different model wearing the same jersey.'),
    ]


__all__ = ['STAGE_ORDER', 'STAGE_MARKET', 'GRID', 'MINIMUM_TICK', 'OriginationError',
           'fair_side', 'fair_total', 'fair_moneyline', 'originate', 'validate_order',
           'consistency_check', 'difference', 'columns', 'rows_from_store', 'stage_labels']
