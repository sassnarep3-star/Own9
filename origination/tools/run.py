"""Run the whole origination desk and write every derived artefact to data/.

Deterministic: same committed inputs produce byte-identical outputs. No network,
no randomness beyond a fixed-seed bootstrap.
"""

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'origination'))

from ownline import metrics, model, pipeline, score  # noqa: E402
from ownline.data import GAMES_CSV, LINES_CSV, sha256  # noqa: E402

DATA = ROOT / 'data'

# Every derived number is frozen to SIGNIFICANT_DIGITS before it is written, so
# the committed artefacts are byte-identical on any CPython build. The maths
# library is not bit-identical across versions and C libraries: an error
# function can differ by one unit in the last place, which is far below
# anything this desk publishes (nothing is shown at more than six decimals) but
# is enough to make a regeneration check fail. Freezing the precision removes
# that noise without hiding any difference that could matter.
SIGNIFICANT_DIGITS = 9


def stabilise(value):
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, float):
        if value != value or value in (float('inf'), float('-inf')):
            return value
        return float('%.*g' % (SIGNIFICANT_DIGITS, value))
    if isinstance(value, dict):
        return {k: stabilise(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [stabilise(v) for v in value]
    return value


def _json(name, payload):
    (DATA / name).write_text(json.dumps(stabilise(payload), indent=2, sort_keys=True) + '\n')


def main():
    originations, fit_reports = pipeline.walk_forward()
    results = pipeline.results_feed()
    bets = pipeline.build_bets(originations)
    errors = score.out_of_sample_residuals(originations)

    # --- correlations -----------------------------------------------------
    margin_errors = [e['margin_error'] for e in errors]
    total_errors = [e['total_error'] for e in errors]
    rho_errors = metrics.pearson(margin_errors, total_errors)
    rho_interval = metrics.fisher_z_interval(rho_errors['r'], rho_errors['n']) if rho_errors else None
    sgp_gate = pipeline.deadband_verdict(rho_interval)

    week_groups = [e['season'] * 100 + e['week'] for e in errors]
    icc = score.intraclass_correlation(margin_errors, week_groups)
    icc_gate = pipeline.deadband_verdict(icc)

    non_push = [e for e in errors if e['cover'] != 0.5 and e['over'] != 0.5]
    phi = metrics.phi_coefficient([e['cover'] == 1.0 for e in non_push],
                                  [e['over'] == 1.0 for e in non_push])
    phi_interval = metrics.fisher_z_interval(phi['r'], phi['n']) if phi else None

    parlays, sgp = pipeline.build_joint(bets, icc_gate, sgp_gate)
    joint_bets = joint_to_bets(parlays, sgp)
    all_bets = bets + joint_bets

    # --- scoring -----------------------------------------------------------
    singles = score.score_singles(bets)
    parlay_scores = score.score_parlays(parlays)
    sgp_scores = score.score_sgp(sgp)
    combined = dict(singles)
    combined.update(parlay_scores)
    combined.update(sgp_scores)
    combined['P-PROP'] = {'signal': {'n': 0}, 'staking': {'bets': 0}, 'taken': 0,
                          'blocked': 'no official player-prop market data in this repository'}

    demotions = score.demotion_replay(
        all_bets, ('G-SIDE', 'G-TOTAL', 'G-ML', 'X-PARLAY', 'S-SGP', 'P-PROP'))
    coverage = score.coverage_by_season(originations)

    write_results_feed(results)
    write_price_store(originations)
    write_originated(originations)
    write_bets(all_bets)

    report = {
        'inputs': {
            'games.csv': {'rows': sum(1 for _ in GAMES_CSV.open()), 'sha256': sha256(GAMES_CSV)},
            'closing_lines.csv': {'rows': sum(1 for _ in LINES_CSV.open()),
                                  'sha256': sha256(LINES_CSV)},
        },
        'originations': {
            'games': len(originations),
            'markets': sum(len(o['rows']) for o in originations),
            'by_market': dict(_count(o['rows'][0]['market'] for o in originations)),
            'seasons': sorted({o['rows'][0]['season'] for o in originations}),
        },
        'results_feed': {
            'games': len(results),
            'result_matches_recompute': sum(1 for r in results if r['result_matches_recompute']),
            'total_matches_recompute': sum(1 for r in results if r['total_matches_recompute']),
            'seasons': [min(r['season'] for r in results), max(r['season'] for r in results)],
            'latest_scored_week': _latest_week(results),
        },
        'fits': fit_reports,
        'correlations': {
            'margin_total_error': {'point': rho_errors['r'] if rho_errors else None,
                                   'n': rho_errors['n'] if rho_errors else None,
                                   'interval': rho_interval,
                                   'gate': sgp_gate},
            'weekly_intraclass': icc,
            'weekly_intraclass_gate': icc_gate,
            'cover_over_phi': {'point': phi['r'] if phi else None,
                               'n': phi['n'] if phi else None,
                               'interval': phi_interval},
        },
        'strategies': combined,
        'demotions': demotions,
        'coverage': coverage,
        'joint': {
            'parlay_offered': len(parlays),
            'parlay_priced': len([p for p in parlays if p['joint'].get('priced')]),
            'sgp_offered': len(sgp),
            'sgp_priced': len([p for p in sgp if p['joint'].get('priced')]),
        },
        'constants': {
            'first_eval_season': pipeline.FIRST_EVAL_SEASON,
            'last_eval_season': pipeline.LAST_EVAL_SEASON,
            'min_train_seasons': pipeline.MIN_TRAIN_SEASONS,
            'edge_threshold': pipeline.EDGE_THRESHOLD,
            'kelly_cap': pipeline.KELLY_CAP,
            'deadband': pipeline.DEADBAND,
            'trailing_window': score.TRAILING,
            'brier_tolerance': score.BRIER_TOLERANCE,
            'drawdown_tolerance': score.DRAWDOWN_TOLERANCE,
        },
    }
    _json('report.json', report)
    _json('correlations.json', report['correlations'])
    _json('strategies.json', combined)
    _json('demotions.json', demotions)
    print(json.dumps({k: v for k, v in report.items()
                      if k in ('originations', 'results_feed', 'joint', 'correlations')},
                     indent=2, sort_keys=True))
    return report


def _count(iterable):
    out = defaultdict(int)
    for item in iterable:
        out[item] += 1
    return out


def _latest_week(results):
    latest = max(results, key=lambda r: (r['season'], r['week'], r['gameday']))
    return {'season': latest['season'], 'week': latest['week'], 'gameday': latest['gameday']}


# --------------------------------------------------------------------------
# CSV writers
# --------------------------------------------------------------------------

def write_results_feed(results):
    fields = ['game_id', 'season', 'week', 'gameday', 'home', 'away', 'home_score',
              'away_score', 'margin', 'total', 'result_matches_recompute',
              'total_matches_recompute', 'overtime']
    _csv('results.csv', fields, results)


def write_price_store(originations):
    """The price-snapshot store: one row per originated market.

    Opening numbers are left blank on purpose. The committed snapshot records a
    single price per market and no capture time, and no official opening-line
    source was obtained, so an opening value would have to be invented.
    """
    rows = []
    for entry in originations:
        for r in entry['rows']:
            rows.append({
                'snapshot_id': '%s-%s' % (r['game_id'], r['market']),
                'season': r['season'], 'week': r['week'], 'gameday': r['gameday'],
                'game_id': r['game_id'], 'home': r['home'], 'away': r['away'],
                'market': r['market'], 'origination_order': r['order'],
                'open_line': '', 'open_price': '', 'open_captured_utc': '',
                'open_source': '',
                'close_number_kind': 'price' if r['market'] == 'MONEYLINE' else 'line',
                'close_line': '' if r['market_line'] is None else r['market_line'],
                'close_price': '' if r['market_price'] is None else r['market_price'],
                'close_captured_utc': '', 'close_source': 'data/raw/games.csv',
                'close_provenance': 'committed local snapshot; upstream provenance unconfirmed',
                'model_fair_line': '' if r['model_fair_line'] is None else round(r['model_fair_line'], 3),
                'difference_model_minus_market': '' if r['difference'] is None else r['difference'],
            })
    fields = list(rows[0])
    _csv('prices.csv', fields, rows)


def write_originated(originations):
    rows = []
    for entry in originations:
        for r in entry['rows']:
            rows.append({
                'game_id': r['game_id'], 'season': r['season'], 'week': r['week'],
                'gameday': r['gameday'], 'home': r['home'], 'away': r['away'],
                'market': r['market'], 'origination_order': r['order'],
                'model_fair_line': '' if r['model_fair_line'] is None else round(r['model_fair_line'], 3),
                'market_number': '' if r['market_line'] is None else r['market_line'],
                'market_number_kind': 'price' if r['market'] == 'MONEYLINE' else 'line',
                'difference': '' if r['difference'] is None else r['difference'],
                'difference_unit': 'probability points' if r['market'] == 'MONEYLINE'
                                   else 'points',
                'model_probability': '' if r['model_probability'] is None else round(r['model_probability'], 4),
                'market_probability_devig': '' if r['market_probability_devig'] is None else round(r['market_probability_devig'], 4),
                'settled': r['settled'],
                'outcome': '' if r['outcome'] is None else r['outcome'],
            })
    _csv('originated.csv', fields=list(rows[0]), rows=rows)


def joint_to_bets(parlays, sgp):
    """Publish joint bets in the same ledger as the singles.

    A bet that is not in bets.csv was never tried, so the combinations have to
    appear here even when the gate priced none of them.
    """
    rows = []
    for kind, entries in (('X-PARLAY', parlays), ('S-SGP', sgp)):
        for entry in entries:
            joint = entry['joint']
            if not joint.get('priced'):
                continue
            legs = entry['legs']
            rows.append({
                'season': entry['season'], 'week': entry['week'],
                'gameday': legs[0]['gameday'],
                'game_id': legs[0]['game_id'] if kind == 'S-SGP'
                           else '%s+%s' % (legs[0]['game_id'], legs[1]['game_id']),
                'strategy': kind, 'market': kind,
                'side': '2 legs',
                'price': round(joint['decimal'], 4),
                'p_model': round(joint['joint'], 4),
                'p_market_devig': round(legs[0]['p_market_devig'] * legs[1]['p_market_devig'], 4),
                'break_even': round(1.0 / joint['decimal'], 4),
                'edge': round(joint['edge'], 4),
                'stake': joint['stake'], 'return': round(joint['return'], 4),
                'outcome': joint['outcome'],
                'price_provenance': 'synthesised from leg prices; no book parlay '
                                    'price exists in this repository',
            })
    return rows


def write_bets(bets):
    rows = []
    for b in bets:
        b.setdefault('price_provenance', '')
    for b in bets:
        rows.append({
            'season': b['season'], 'week': b['week'], 'gameday': b['gameday'],
            'game_id': b['game_id'], 'strategy': b['strategy'], 'market': b['market'],
            'side': b['side'], 'price': b['price'],
            'p_model': '' if b['p_model'] is None else round(b['p_model'], 4),
            'p_market_devig': '' if b['p_market_devig'] is None else round(b['p_market_devig'], 4),
            'break_even': round(b['break_even'], 4), 'edge': round(b['edge'], 4),
            'stake': b['stake'], 'return': round(b['return'], 4),
            'outcome': b['outcome'], 'price_provenance': b['price_provenance'],
        })
    _csv('bets.csv', fields=list(rows[0]), rows=rows)


def _csv(name, fields, rows):
    target = DATA / name
    with target.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(stabilise(rows))


if __name__ == '__main__':
    main()
