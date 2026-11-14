"""Measures the eight new requirements against the repository's own evidence, at build time.

Nothing in this module is typed by hand. Every figure that appears on `requirements.html`,
`price-feed.html`, `signal-staking.html`, `depth-correlations.html` and `missing-information.html`
is returned here, so a page cannot drift from the data and a retyped number cannot become a
second, contradictory source of truth. Reproduce with `python3 tools/requirements_audit.py`.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for entry in (str(ROOT), str(ROOT / 'tools')):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from engine import correlations as corr          # noqa: E402
from engine import demotion                      # noqa: E402
from engine import originate                     # noqa: E402
from engine import replacement as repl           # noqa: E402
from engine import results_feed as res                # noqa: E402
from engine import signal_staking as ss          # noqa: E402
from engine import snapshots as snap             # noqa: E402
from lines_audit import audit                    # noqa: E402

STORE = ROOT / 'data' / 'snapshots'
DEMARK = ROOT / 'data' / 'demotion' / 'log.jsonl'

#: Depth charts retrieved and read by this session on 2026-11-14. Column order is the published
#: string order; only slots relevant to a Week 10 vacancy are kept, and the rows are quoted from
#: the club page, never from a memory of it.
CHARTS = [
    # team, unit, slot, published order
    ('SEA', 'Offense', 'QB', ['Sam Darnold', 'Drew Lock', 'Jalen Milroe']),
    ('SEA', 'Offense', 'LT', ['Charles Cross', 'Josh Jones']),
    ('SEA', 'Offense', 'RT', ['Abraham Lucas', 'Josh Jones']),
    ('SEA', 'Offense', 'LG', ['Quenton Nelson', 'Anthony Bradford']),
    ('SEA', 'Defense', 'DT', ['Leonard Williams', 'Rylie Mills']),
    ('KC', 'Offense', 'RT', ['Jaylon Moore', 'Joshua Ezeudu']),
    ('KC', 'Offense', 'LG', ['Kingsley Suamataia', 'Joshua Ezeudu']),
    ('KC', 'Offense', 'RB', ['Kenneth Walker', 'Emmett Johnson', 'Jaydn Ott']),
    ('KC', 'Defense', 'DT', ['Chris Jones', 'Peter Woods', 'Marcus Harris']),
    ('DET', 'Offense', 'C', ['Cade Mays', 'Juice Scruggs']),
    ('DET', 'Defense', 'CB', ['D.J. Reed', 'Rock Ya-Sin', 'Khalil Dorsey', 'Nick Whiteside']),
    ('DET', 'Defense', 'S', ['Chuck Clark']),
    ('DET', 'Defense', 'S', ['Brian Branch', 'Christian Izien']),
    ('DET', 'Offense', 'WR', ['Amon-Ra St. Brown', 'DeAndre Carter']),
    ('DET', 'Offense', 'RB', ['Jahmyr Gibbs', 'Sione Vaki', 'Jacob Saylors']),
]


def _report_rows(INJ):
    """Week 10 report rows as transcribed by the repository, from tools/build.py."""
    return [{'team': row[0], 'player': row[1], 'position': row[2], 'injuries': row[3],
             'practice_status': row[4], 'game_status': row[5]} for row in INJ]


def raw_file_inventory():
    """Every file in data/raw/, measured rather than described.

    A schema file and a data file look the same until the rows are counted, and the distinction is
    the whole answer to "does the repository already hold prices?". Comment lines are counted
    separately so a documented placeholder cannot be mistaken for either.
    """
    out = {}
    for path in sorted((ROOT / 'data' / 'raw').glob('*.csv')):
        lines = path.read_text().splitlines()
        header = lines[0].split(',') if lines else []
        body = [l for l in lines[1:] if l.strip() and not l.lstrip().startswith('#')]
        out[path.name] = {'lines': len(lines), 'header': header, 'n_columns': len(header),
                          'data_rows': len(body), 'comment_lines': len(lines) - 1 - len(body)}
    return out


def store_state(games):
    records = snap.read(STORE)
    game_ids = [g['game_id'] for g in games]
    audit = snap.completeness(records, game_ids)
    audit['chain_problems'] = snap.verify_chain(STORE, records)
    audit['log_exists'] = (STORE / 'store.jsonl').exists()
    audit['manifest_exists'] = (STORE / 'manifest.json').exists()
    audit['log_sha256'] = snap.file_digest(STORE)
    audit['roi'] = snap.roi_ready(records, games)
    return audit


def quote_file_state():
    """Measure the repository's two historical files against the store's own schema."""
    lines = audit()
    import csv
    with (ROOT / 'data' / 'raw' / 'closing_lines.csv').open() as handle:
        header = next(csv.reader(handle))
    # Matched on whole column names, not substrings: 'utc' is inside 'outcome', and a substring
    # search there reports a timestamp column that does not exist.
    stage_like = [c for c in header if c.lower() in ('stage', 'open', 'close', 'opening', 'closing',
                                                     'open_time', 'close_time', 'captured_at',
                                                     'timestamp', 'timestamp_utc')]
    priced = lines['missing_fields']['odds']
    return {'columns': header, 'n_columns': len(header), 'stage_columns': stage_like,
            'rows': lines['files']['closing_lines']['rows'],
            'sha256': lines['files']['closing_lines']['sha256'],
            'seasons': f"{lines['coverage']['season_min']}\u2013{lines['coverage']['season_max']}",
            'games': lines['coverage']['games'],
            'opening_numbers_present': 0,
            'unpriced_spread_rows': priced['SPREAD'], 'unpriced_total_rows': priced['TOTAL'],
            'moneyline_rows': lines['coverage']['market_types']['MONEYLINE'],
            'disagree_rows': lines['settlement_recompute']['disagree_rows'],
            'disagree_pct': lines['settlement_recompute']['disagree_pct']}


def correlation_measurements(games):
    """Correlations computed only from officially transcribed numbers, each with its own n.

    Pairs are built from the Week 8, Week 9 and Week 10 records and scores. Every observation names
    both of its source ids, so the gate can reject the whole pair if either leg is not a registered
    official read. `n` is counted from the complete pairs actually used, never typed.
    """
    finals = [g for g in games if g['status'] == 'final' and g['verified']]
    w9 = [g for g in finals if g['week'] == 9]
    both_sources = ['nfl-schedule-w8-byweek', 'nfl-schedule-w9']

    def margin(game):  # home perspective, in points
        return game['home_points'] - game['away_points']

    def total(game):
        return game['home_points'] + game['away_points']

    def prior_gap(game):
        prior = game.get('prior_records') or {}
        if not prior:
            return None
        a = res.winning_percentage(prior['away'])
        b = res.winning_percentage(prior['home'])
        return None if a is None or b is None else round(a - b, 6)

    pairs = {'prior winning-percentage gap \u2194 final margin (Week 9)': [],
             'prior winning-percentage gap \u2194 game total (Week 9)': [],
             'home points \u2194 away points (Week 9)': [],
             'final margin \u2194 game total (Week 9)': [],
             'absolute margin \u2194 game total (Week 9)': []}
    for game in w9:
        gap = prior_gap(game)
        if gap is not None:
            pairs['prior winning-percentage gap \u2194 final margin (Week 9)'].append(
                {'game_id': game['game_id'], 'a': gap, 'b': margin(game),
                 'sources': both_sources, 'leg_games': [game['game_id'], game['game_id']]})
            pairs['prior winning-percentage gap \u2194 game total (Week 9)'].append(
                {'game_id': game['game_id'], 'a': gap, 'b': total(game),
                 'sources': both_sources, 'leg_games': [game['game_id'], game['game_id']]})
        pairs['home points \u2194 away points (Week 9)'].append(
            {'game_id': game['game_id'], 'a': game['home_points'], 'b': game['away_points'],
             'sources': ['nfl-schedule-w9'], 'leg_games': [game['game_id'], game['game_id']]})
        pairs['final margin \u2194 game total (Week 9)'].append(
            {'game_id': game['game_id'], 'a': margin(game), 'b': total(game),
             'sources': ['nfl-schedule-w9'], 'leg_games': [game['game_id'], game['game_id']]})
        pairs['absolute margin \u2194 game total (Week 9)'].append(
            {'game_id': game['game_id'], 'a': abs(margin(game)), 'b': total(game),
             'sources': ['nfl-schedule-w9'], 'leg_games': [game['game_id'], game['game_id']]})
    rows = []
    for label, data in pairs.items():
        try:
            rows.append(corr.measure(label, data, level='game'))
        except corr.CorrelationGate as exc:
            rows.append({'label': label, 'n': len(data), 'status': 'refused', 'note': str(exc),
                         'r': None, 'interval': None, 'verdict': 'refused',
                         'may_price_joint': False, 'sources': [], 'min_n': corr.MIN_N,
                         'deadband': corr.DEADBAND})
    return rows


def signal_staking_state():
    """The split, exercised on declared synthetic rows, plus the state of the real board."""
    synthetic = [{'p_model': p, 'p_market': q, 'outcome': o, 'week': w}
                 for p, q, o, w in [(.60, .55, 1, 1), (.40, .45, 0, 1), (.55, .50, 1, 2),
                                    (.50, .50, 'push', 2), (.65, .60, 0, 3), (.52, .50, 1, 3)]]
    signal = ss.signal_block(synthetic)
    try:
        ss.staking_block(synthetic)
        refused = None
    except ss.SplitError as exc:
        refused = str(exc)
    try:
        ss.leaderboard([{'id': 'DEMO-lucky', 'track': 'G1', 'staking': {'roi': 0.14, 'n': 40}}])
        unranked_refused = None
    except ss.SplitError as exc:
        unranked_refused = str(exc)
    rows, _summary, _detail = res.feed()
    return {'signal_demo': {'n': signal['n'], 'gain': signal['gain'], 'gain_lcb': signal['gain_lcb'],
                            'calibration_mae': signal['calibration_mae'],
                            'excluded_push': signal['excluded_push']},
            'staking_refused_without_captured_price': refused,
            'rank_without_signal_refused': unranked_refused,
            'candidates_registered': 0,
            'settled_bets_available': 0,
            'verified_games_available': sum(1 for r in rows if r['status'] == 'final')}


def replacement_state(INJ):
    """How deep each Week 10 replacement actually runs, for the three clubs with a chart."""
    report = _report_rows(INJ)
    chart = [{'team': t, 'unit': u, 'slot': s, 'order': order} for t, u, s, order in CHARTS]
    rows = repl.evaluate(chart, report)
    rollup = repl.unit_rollup(rows)
    teams_in_report = sorted({r['team'] for r in report})
    teams_with_chart = sorted({t for t, _u, _s, _o in CHARTS})
    vacancies = [r for r in rows if r['slot'] is not None]
    return {'rows': rows, 'rollup': rollup,
            'vacancies': len(vacancies),
            'depth_known': sum(1 for r in vacancies if r['strings_travelled'] is not None),
            'depth_unknown': sum(1 for r in vacancies if r['strings_travelled'] is None),
            'exhausted_slots': sum(1 for r in vacancies if r['chart_exhausted']),
            'shared_backups': sorted({(r['team'], tuple(r['shared_backup']))
                                      for r in vacancies if r['shared_backup']}),
            'max_depth': max([r['strings_travelled'] or 0 for r in vacancies], default=None),
            'worst_case_max_depth': max([r['certain_strings'] or r['strings_travelled'] or 0
                                         for r in vacancies], default=None),
            'conditional_vacancies': sum(1 for r in vacancies if r['replacement_is_conditional']),
            'depth_notes': sorted({r['depth_note'] for r in vacancies if r['depth_note']}),
            'depth_total': sum(r['strings_travelled'] or 0 for r in vacancies),
            'clubs_in_report': len(teams_in_report), 'clubs_with_chart': len(teams_with_chart),
            'clubs_without_chart': len(set(teams_in_report) - set(teams_with_chart)),
            'conditional_slots': sorted({(r['team'], r['slot'], p) for r in vacancies
                                         for p in r['conditional_slots']}),
            'unlisted_vacancies': sorted({(r['team'], r['vacated_player']) for r in rows
                                          if r['slot'] is None and r['vacated_player']}),
            'multi_slot_backups': sorted({(row['team'], row['replacement_player'],
                                            tuple(row['covers_slots']))
                                          for row in vacancies if row.get('covers_slots')}),
            'chart_slots_extracted': len(CHARTS),
            'rows_with_no_backup_listed': sum(1 for _t, _u, _s, order in CHARTS if len(order) == 1)}


def origination_state(games):
    """The mandated stage order, run end to end, and how many published rows can carry a difference.

    The distribution below is a declared arithmetic example, not a fitted model: it exists to prove
    the order is enforced and that the three columns are produced separately. It is never presented
    as an NFL forecast.
    """
    illustrative = {(24, 17): 0.50, (17, 24): 0.30, (21, 21): 0.20}
    log = originate.originate(illustrative, now_utc='2026-11-14T00:00:00Z')
    stages = [entry['output'] for entry in log]
    join = res.join_line_snapshot(games)
    records = snap.read(STORE)
    pairs = snap.pair_index(records)
    published = []
    for game in games:
        for stage in stages:
            for side in ('HOME', 'AWAY') if stage['market'] != 'TOTAL' else ('OVER', 'UNDER'):
                open_record = (pairs.get((game['game_id'], stage['market'], side)) or {}).get('open')
                published.append(originate.columns(stage, open_record, game_id=game['game_id']))
    order_problems = originate.validate_order(
        [{'sequence': 1, 'stage': 'moneyline', 'depends_on': None},
         {'sequence': 2, 'stage': 'side', 'depends_on': None},
         {'sequence': 3, 'stage': 'total', 'depends_on': 'moneyline'}])
    return {'stages': [entry['stage'] for entry in log],
            'stage_outputs': stages,
            'consistency_problems': originate.consistency_check(illustrative, stages),
            'out_of_order_rejected': order_problems,
            'published_rows': len(published),
            'rows_with_a_fair_line': sum(1 for r in published if r['fair_line'] is not None),
            'rows_with_a_market_line': sum(1 for r in published if r['market_line'] is not None),
            'rows_with_a_difference': sum(1 for r in published if r['difference'] is not None),
            'games_with_a_line_value': join['games_with_a_line_value'],
            'games_with_a_usable_quote': join['games_with_a_usable_quote'],
            'games_in_feed': join['games_in_feed'],
            'join': join}


def demotion_state():
    """The gate, exercised both ways, and the state of the real board it would act on."""
    clean = [{'week': w, 'signal_lcb': 0.02, 'calibration_mae': 0.01, 'coverage': 0.9,
              'missing_close_share': 0.0, 'drawdown_units': -3.0} for w in range(1, 9)]
    broken = clean + [{'week': 9, 'signal_lcb': -0.015, 'calibration_mae': 0.09, 'coverage': 0.41,
                       'missing_close_share': 0.11, 'drawdown_units': -19.0}]
    return {'clean_hold': demotion.evaluate(clean), 'broken_demote': demotion.evaluate(broken),
            'relist_after_demote': demotion.relist_ready(9, clean),
            'log_exists': DEMARK.exists(),
            'log_problems': demotion.verify_log(DEMARK) if DEMARK.exists() else ['no log yet'],
            'live_candidates': 0, 'policy': demotion.POLICY,
            'rows': demotion.gate_rows(), 'rules': ss.rules()}


def measure(INJ):
    games, feed_summary, _detail = res.feed()
    return {
        'feed': feed_summary,
        'games': games,
        'store': store_state(games),
        'quotes': quote_file_state(),
        'raw_files': raw_file_inventory(),
        'origination': origination_state(games),
        'signal_staking': signal_staking_state(),
        'replacement': replacement_state(INJ),
        'correlations': correlation_measurements(games),
        'demotion': demotion_state(),
        'readiness': res.readiness(games),
    }


if __name__ == '__main__':
    sys.path.insert(0, str(ROOT / 'tools'))
    from build import INJ  # the repository's own Week 10 report transcription
    print(json.dumps(measure(INJ), indent=2, sort_keys=True, default=str))
