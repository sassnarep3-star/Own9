"""Session `arena/9a409d93-own9` — origination store and demotion-gate tests.

These are arithmetic and contract tests: they verify the order guarantee, the
blank-market-line policy, the demotion thresholds' boundary behaviour and the
store's declared provenance against the committed feed. They do not (and
cannot) validate the elo-v1 model's predictive quality.
"""
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'evidence/results/nfl-2026-results.json'
WEEK10 = ROOT / 'evidence/results/nfl-2026-week10.json'
STORE = ROOT / 'data/snapshots/2026-w10-price-snapshot.json'

from engine.origination_elo import (originate, load_results, run_elo, sample_stats,
                                fair_moneylines, demotion_gate, DEMOTION_THRESHOLDS,
                                MARKET_ORDER)

OPENED_AT = '2026-11-14 (UTC, store deployment)'


def _fresh_store():
    # Pure regeneration from committed inputs: no close has been recorded.
    return originate(RESULTS, WEEK10, OPENED_AT)


def _expected_store():
    from tools.withdraw_close_stamps import build
    return build()


class LoadResults(unittest.TestCase):
    def test_feed_is_the_declared_official_sample(self):
        data, games = load_results(RESULTS)
        self.assertIn('weeks', data)
        self.assertEqual(set(data['weeks']), {str(w) for w in range(1, 10)})
        counts = {}
        for g in games:
            counts[g['week']] = counts.get(g['week'], 0) + 1
        self.assertEqual(counts, {1: 16, 2: 16, 3: 16, 4: 16, 5: 15,
                                  6: 14, 7: 14, 8: 14, 9: 15})
        self.assertTrue(all(g['away_score'] >= 0 and g['home_score'] >= 0 for g in games))

    def test_thirty_two_teams(self):
        _, games = load_results(RESULTS)
        teams = {g['away'] for g in games} | {g['home'] for g in games}
        self.assertEqual(len(teams), 32)


class EloArithmetic(unittest.TestCase):
    def test_deterministic_ratings(self):
        _, games = load_results(RESULTS)
        self.assertEqual(run_elo(games), run_elo(games))

    def test_thirty_two_ratings_and_hfa_shows(self):
        _, games = load_results(RESULTS)
        ratings = run_elo(games)
        self.assertEqual(len(ratings), 32)
        s = sample_stats(games)
        # Equal ratings: home carries the 50-Elo HFA = +2.0 points.
        equal = {t: 1500.0 for t in ratings}
        self.assertAlmostEqual(__import__('engine.origination_elo', fromlist=['fair_spread'])
                               .fair_spread(equal, 'KC', 'BUF'), 2.0, places=9)


class MoneylineFairPrices(unittest.TestCase):
    def test_probabilities_partition_the_mass(self):
        s = sample_stats(load_results(RESULTS)[1])
        ml = fair_moneylines(-3.0, s['sigma_margin'], s['tie_rate'])
        self.assertAlmostEqual(ml['p_home'] + ml['p_away'] + ml['p_tie'], 1.0, places=12)

    def test_bigger_home_spread_moves_both_prices(self):
        s = sample_stats(load_results(RESULTS)[1])
        near = fair_moneylines(-1.0, s['sigma_margin'], s['tie_rate'])
        far = fair_moneylines(-14.0, s['sigma_margin'], s['tie_rate'])
        # A larger home favour shortens the away price and lengthens the home price.
        self.assertGreater(far['home_american'], near['home_american'])
        self.assertLess(far['away_american'], near['away_american'])


class OriginationOrder(unittest.TestCase):
    def setUp(self):
        self.store = _fresh_store()

    def test_side_first_then_total_then_moneyline(self):
        types = [m['market_type'] for m in self.store['markets']]
        self.assertEqual(types, sorted(types, key=MARKET_ORDER.index))

    def test_counts_and_uniqueness(self):
        markets = self.store['markets']
        self.assertEqual(len(markets), 52)
        self.assertEqual(sum(m['market_type'] == 'SPREAD' for m in markets), 13)
        self.assertEqual(sum(m['market_type'] == 'TOTAL' for m in markets), 13)
        self.assertEqual(sum(m['market_type'] == 'MONEYLINE' for m in markets), 26)
        self.assertEqual(len({m['market_id'] for m in markets}), 52)

    def test_no_lines_no_diff_no_close(self):
        for m in self.store['markets']:
            self.assertIsNone(m['market_line'], m['market_id'])
            self.assertIsNone(m['market_line_source'], m['market_id'])
            self.assertIsNone(m['diff'], m['market_id'])

    def test_pre_kickoff_game_is_not_originated(self):
        ids = {m['market_id'] for m in self.store['markets']}
        self.assertFalse(any('-WAS-NYJ-' in i for i in ids),
                         'the Thursday game completed before the store existed')

    def test_declared_input_hash_matches_the_feed(self):
        store = self.store
        self.assertEqual(store['meta']['inputs']['results_feed_sha256'],
                         hashlib.sha256(RESULTS.read_bytes()).hexdigest())

    def test_committed_store_matches_regeneration(self):
        committed = json.loads(STORE.read_text())
        self.assertEqual(committed, _expected_store(),
                         'the committed store must be exactly what the committed inputs produce, '
                         'with the documented close-stamp withdrawal applied')

    def test_no_market_carries_a_close_without_a_price(self):
        for m in self.store['markets']:
            self.assertIsNone(m['closed_at'], m['market_id'])
            self.assertNotIn('closed', m['status'], m['market_id'])
            self.assertIsNone(m['market_line'], m['market_id'])

    def test_withdrawn_stamps_are_kept_as_audit_fields(self):
        committed = json.loads(STORE.read_text())
        audit = committed['meta']['close_audit']
        self.assertEqual(audit['markets_withdrawn'], 52)
        self.assertEqual(audit['bot_stamp_utc'], '2026-11-15 19:31 UTC')
        self.assertTrue(all(m['withdrawn_close_stamp'] == audit['bot_stamp_utc']
                            for m in committed['markets']))
        self.assertTrue(any('18:00 UTC' in e for e in [audit['reason']]))

    def test_unpriced_close_is_refused_by_close_tool(self):
        import shutil
        import tempfile
        sys.path.insert(0, str(ROOT))
        from tools.snapshot_close import close_store, OPEN_STATUS
        with tempfile.TemporaryDirectory() as d:
            store = json.loads(STORE.read_text())
            for m in store['markets']:
                m['status'] = OPEN_STATUS
                m['closed_at'] = None
            tmp = Path(d) / 'store.json'
            tmp.write_text(json.dumps(store))
            before = tmp.read_text()
            self.assertEqual(close_store(tmp, RESULTS, '2026-11-15 14:00 UTC'), 0)
            self.assertEqual(tmp.read_text(), before, 'an unpriced close must write nothing')
            shutil.rmtree(d, ignore_errors=True)


class DemotionGateBoundaries(unittest.TestCase):
    def test_too_few_bets_is_unmonitorable(self):
        t = {'n_bets': DEMOTION_THRESHOLDS['min_trailing_bets'] - 1, 'roi_flat': 0.5,
             'mean_edge': 1.0, 'clv_rate': 0.9, 'brier': 0.2, 'feed_age_days': 1}
        self.assertEqual(demotion_gate(t), ('unmonitorable', t and ['trailing bets 19 < 20; '
                                            'demotion gate cannot evaluate (fail-closed)']))

    def test_healthy_window_stays_live(self):
        t = {'n_bets': 20, 'roi_flat': 0.02, 'mean_edge': 0.8, 'clv_rate': 0.55,
             'brier': 0.24, 'feed_age_days': 1}
        self.assertEqual(demotion_gate(t), ('keep_live', ['all thresholds inside bounds']))

    def test_roi_floor_is_strictly_below(self):
        base = {'n_bets': 20, 'mean_edge': 0.8, 'clv_rate': 0.55, 'brier': 0.24,
                'feed_age_days': 1}
        self.assertEqual(demotion_gate({**base, 'roi_flat': -0.10})[0], 'keep_live')
        self.assertEqual(demotion_gate({**base, 'roi_flat': -0.10001})[0], 'demote_to_paper')

    def test_edge_at_zero_demotes(self):
        base = {'n_bets': 20, 'roi_flat': 0.0, 'clv_rate': 0.55, 'brier': 0.24,
                'feed_age_days': 1}
        self.assertEqual(demotion_gate({**base, 'mean_edge': 0.001})[0], 'keep_live')
        self.assertEqual(demotion_gate({**base, 'mean_edge': 0.0})[0], 'demote_to_paper')

    def test_brier_ceiling_is_base_plus_tolerance(self):
        base = {'n_bets': 20, 'roi_flat': 0.0, 'mean_edge': 0.8, 'clv_rate': 0.55,
                'feed_age_days': 1}
        tol = DEMOTION_THRESHOLDS['brier_tolerance']
        self.assertEqual(demotion_gate({**base, 'brier': 0.25 + tol})[0], 'keep_live')
        self.assertEqual(demotion_gate({**base, 'brier': 0.2501 + tol})[0], 'demote_to_paper')

    def test_stale_feed_demotes_and_reasons_accumulate(self):
        t = {'n_bets': 20, 'roi_flat': -0.5, 'mean_edge': -1.0, 'clv_rate': 0.0,
             'brier': 0.9, 'feed_age_days': 30}
        decision, reasons = demotion_gate(t)
        self.assertEqual(decision, 'demote_to_paper')
        self.assertEqual(len(reasons), 5)


if __name__ == '__main__':
    unittest.main()
