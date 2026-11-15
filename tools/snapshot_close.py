#!/usr/bin/env python3
"""Close-capture for the price-snapshot store (no manual input).

Run by the scheduled workflow before kickoff (see
.github/workflows/snapshot.yml). For every market whose status is still
"open · close capture pending" this script:

  1. re-checks the store's declared method constants against the live
     engine/origination_elo.py — if the constants or the origination order
     changed, it refuses to close anything (fail closed);
  2. recomputes the model fair number for that market from the committed
     results feed, using the declared method;
  3. records `closed_at` and sets the status to "closed · pre-kickoff capture" — only for a market that has a recorded market price (session 446067c4: an unpriced market is skipped and nothing is written),
     and — only when the recomputed fair differs from the open fair, which
     can happen if the feed has grown since deployment — adds
     `model_fair_close` and `close_inputs_sha256` so both decision points
     stay reproducible.

Idempotent: markets already closed are never touched, and the script writes
the file only when something changed. Exit codes: 0 = closed or nothing to
do, 1 = guard failure or write error.
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.origination_elo import (ELO_START, K, HFA_ELO, ELO_PER_POINT, TOTAL_SHRINK,
                                TOTAL_WINDOW, MOV_SCALER, MOV_RATING_SCALE,
                                MARKET_ORDER, load_results, run_elo, sample_stats,
                                rolling_pf_pa, fair_spread, fair_total, fair_moneylines)

DEFAULT_STORE = ROOT / 'data/snapshots/2026-w10-price-snapshot.json'
DEFAULT_RESULTS = ROOT / 'evidence/results/nfl-2026-results.json'

OPEN_STATUS = 'open · close capture pending'
CLOSED_STATUS = 'closed · pre-kickoff capture'


def _declared_constants(meta):
    c = meta['method']['constants']
    return {
        'elo_start': c['elo_start'], 'k': c['k'], 'hfa_elo': c['hfa_elo'],
        'elo_per_point': c['elo_per_point'], 'total_shrink': c['total_shrink'],
        'total_window': c['total_window'], 'mov_scaler': c['mov_scaler'],
        'mov_rating_scale': c['mov_rating_scale'],
    }


def close_store(store_path=DEFAULT_STORE, results_path=DEFAULT_RESULTS, at=None):
    store = json.loads(Path(store_path).read_text())
    meta = store['meta']
    guards = [
        (meta['method']['id'] == 'elo-v1', 'method id changed since deployment'),
        (meta['origination_order'] == list(MARKET_ORDER), 'origination order changed'),
        (_declared_constants(meta) == {
            'elo_start': ELO_START, 'k': K, 'hfa_elo': HFA_ELO,
            'elo_per_point': ELO_PER_POINT, 'total_shrink': TOTAL_SHRINK,
            'total_window': TOTAL_WINDOW, 'mov_scaler': MOV_SCALER,
            'mov_rating_scale': MOV_RATING_SCALE}, 'declared constants changed'),
    ]
    for ok, why in guards:
        if not ok:
            print(f'REFUSED: {why} — close capture aborted, store untouched', file=sys.stderr)
            return 1

    data, games = load_results(Path(results_path))
    sha = hashlib.sha256(Path(results_path).read_bytes()).hexdigest()
    sha_changed = sha != meta['inputs']['results_feed_sha256']
    ratings = run_elo(games)
    stats = sample_stats(games)
    rollings = rolling_pf_pa(games)
    sigma, tie_rate = stats['sigma_margin'], stats['tie_rate']

    at = at or datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    changed = 0
    unpriced = 0
    for m in store['markets']:
        if m['status'] != OPEN_STATUS:
            continue
        if m.get('market_line') is None:
            # A close is a recorded market price taken before kickoff. A timestamp
            # with no price is not a close, so nothing is stamped (session 446067c4).
            unpriced += 1
            continue
        mid = m['market_id']  # 2026-w10-<AWAY>-<HOME>-<TYPE[-SIDE]>
        parts = mid.split('-')
        away, home = parts[2], parts[3]
        if mid.endswith('-SPREAD'):
            mtype = 'SPREAD'
        elif mid.endswith('-TOTAL'):
            mtype = 'TOTAL'
        elif mid.endswith('-ML-HOME') or mid.endswith('-ML-AWAY'):
            mtype = 'MONEYLINE'
        else:
            print(f'REFUSED: unrecognised market id {mid!r}', file=sys.stderr)
            return 1
        if mtype == 'SPREAD':
            fair = round(fair_spread(ratings, home, away), 1)
        elif mtype == 'TOTAL':
            fair = round(fair_total(stats, rollings, home, away), 1)
        elif mtype == 'MONEYLINE':
            side = 'home' if m['market_id'].endswith('ML-HOME') else 'away'
            spread = fair_spread(ratings, home, away)
            ml = fair_moneylines(spread, sigma, tie_rate)
            fair = ml[f'{side}_american']
        else:
            print(f'REFUSED: unknown market type {mtype!r}', file=sys.stderr)
            return 1
        m['closed_at'] = at
        m['status'] = CLOSED_STATUS
        if fair != m['model_fair']:
            m['model_fair_close'] = fair
            if sha_changed:
                m['close_inputs_sha256'] = sha
        changed += 1

    if changed:
        Path(store_path).write_text(json.dumps(store, indent=2) + '\n')
    print(f'closed {changed} markets at {at} (feed sha {"changed" if sha_changed else "unchanged"})')
    if unpriced:
        print(f'NOT CLOSED: {unpriced} open markets have no recorded market price; '
              'no close stamp written (a stamp without a price is not a close)')
    return 0


def main(argv):
    store = Path(argv[1]) if len(argv) > 1 else DEFAULT_STORE
    results = Path(argv[2]) if len(argv) > 2 else DEFAULT_RESULTS
    at = argv[3] if len(argv) > 3 else None
    return close_store(store, results, at)


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
