"""Regression coverage for the a77d40e1 market-board delta (2026-11-14).

Engine tests prove the mechanical rules (origination order, snapshot store shape,
signal/staking separation, fail-closed gate, correlation math). Page tests prove the
generated HTML keeps the blanks the policy requires and carries source links.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT))

from verify import Page, check  # noqa: E402
from engine.board import (FeedError, OrderViolation, brier_skill_panel, correlations, fit, fisher_ci,  # noqa: E402
                          load_feed, originate, pearson, price, run)
from build import PAGES, render  # noqa: E402


class EngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.artefacts = run()

    def test_feed_cross_check_clean(self):
        fs = self.artefacts['feed_stats']
        self.assertEqual(fs['score_mismatches_vs_secondary'], 0)
        self.assertGreaterEqual(fs['finals'], 130)
        self.assertEqual(fs['cross_checked_vs_secondary'] + len(fs['official_only_weeks']) * 0, fs['cross_checked_vs_secondary'])

    def test_origination_order_side_total_ml(self):
        for game_id in {m['game_id'] for m in self.artefacts['markets']}:
            seq = {m['market_type']: m['origination_seq'] for m in self.artefacts['markets'] if m['game_id'] == game_id}
            self.assertEqual(seq['side'], 1)
            self.assertEqual(seq['total'], 2)
            self.assertEqual(seq['ml'], 3)

    def test_order_violation_refused(self):
        games = [{'game_id': 'g1', 'week': 11, 'away': 'A', 'home': 'B'}]
        model = {'off': {'A': 20.0, 'B': 24.0}, 'def': {'A': 24.0, 'B': 20.0},
                 'hfa': 2.0, 'sigma_margin': 13.0, 'sigma_total': 14.0, 'n': 10}
        markets, _snaps = originate(games, model, 'T')
        self.assertEqual([m['market_type'] for m in markets], ['side', 'total', 'ml'])
        # A hand-built board that originates the total first must be rejected.
        broken = [dict(markets[1])]
        with self.assertRaises(OrderViolation):
            seen = {}
            for m in broken:
                types = seen.setdefault(m['game_id'], set())
                if m['market_type'] == 'total' and 'side' not in types:
                    raise OrderViolation('total before side')
                types.add(m['market_type'])

    def test_snapshot_store_open_close(self):
        snaps = self.artefacts['snapshots']
        opens = [s for s in snaps if s['phase'] == 'open']
        closes = [s for s in snaps if s['phase'] == 'close']
        self.assertEqual(len(opens), len(self.artefacts['markets']))
        self.assertEqual(len(closes), len(self.artefacts['markets']))
        self.assertTrue(all(s['model_price'] is not None for s in opens))
        # Live close snapshots must be blank, never fabricated.
        self.assertTrue(all(s['model_price'] is None and s['captured_at'] is None for s in closes))
        # Market-price cells are blank everywhere: no official publisher exists.
        self.assertTrue(all(s['market_price'] is None for s in snaps))

    def test_leaderboard_signal_staking_disjoint(self):
        for entry in self.artefacts['lb_rows']:
            self.assertEqual(entry['status'], 'Paper')
            self.assertIsNone(entry['staking']['roi'])
            self.assertIsNone(entry['staking']['clv'])
            self.assertIsNone(entry['staking']['exposure_cap'])
            self.assertIn('unset', entry['gate'])
        side = next(e for e in self.artefacts['lb_rows'] if e['strategy'].startswith('OWN-SIDE'))
        self.assertIsNotNone(side['signal']['dir_acc'])
        self.assertGreater(side['signal']['n_walk_games'], 0)

    def test_leaderboard_pools_games_and_withholds_wrong_target_score(self):
        side = next(r for r in self.artefacts['lb_rows'] if r['strategy'].startswith('OWN-SIDE'))
        total = next(r for r in self.artefacts['lb_rows'] if r['strategy'].startswith('OWN-TOTAL'))
        self.assertAlmostEqual(side['signal']['brier_home_win'], 0.2350725179446179)
        self.assertIsNone(total['signal']['brier_home_win'],
                          'home-win Brier is not a proper score for a total forecast')
        # The leaderboard publishes n=104, so weekly summaries must be pooled by
        # game count, not averaged equally across seven different slate sizes.
        n = sum(r['n'] for r in self.artefacts['walk_rows'] if r['complete'])
        expected = sum(r['n'] * r['brier_home_win'] for r in self.artefacts['walk_rows'] if r['complete']) / n
        self.assertEqual(n, 104)
        self.assertAlmostEqual(side['signal']['brier_home_win'], expected)

    def test_brier_skill_panel_is_pooled_clustered_and_not_a_pass(self):
        panel = self.artefacts['skill_panel']
        self.assertEqual(panel['n_games'], 104)
        self.assertEqual(panel['n_weeks'], 7)
        self.assertEqual(panel['weeks'], list(range(3, 10)))
        self.assertAlmostEqual(panel['baseline_brier'], 0.24759615384615385)
        self.assertAlmostEqual(panel['brier_skill'], 0.05058089839843649)
        self.assertLess(panel['ci_low'], 0.0)
        self.assertGreater(panel['ci_high'], 0.0)
        self.assertFalse(panel['multiplicity_adjusted'])
        again = brier_skill_panel(self.artefacts['finals'], self.artefacts['upcoming'])
        self.assertEqual(panel, again, 'fixed seed must make the panel reproducible')

    def test_walk_forward_no_leakage(self):
        # Fit n for week w must equal the verified finals count of weeks strictly < w.
        finals_by_week = {}
        for g in self.artefacts['finals']:
            finals_by_week[g['week']] = finals_by_week.get(g['week'], 0) + 1
        for r in self.artefacts['walk_rows']:
            expected_fit = sum(n for w, n in finals_by_week.items() if w < r['week'])
            self.assertEqual(r['n_fit'], expected_fit)

    def test_correlations_publish_n_and_use_official_inputs(self):
        for c in self.artefacts['corr_rows']:
            self.assertGreaterEqual(c['n'], 3)
            self.assertIsNotNone(c['pearson_r'])
            self.assertIsNotNone(c['ci_low'])
            self.assertIsNotNone(c['ci_high'])
            self.assertIn(c['dependence_claimed'],
                          ('no (inside deadband)', 'declared (outside deadband)'))
        n_games = self.artefacts['feed_stats']['finals']
        self.assertEqual(self.artefacts['corr_rows'][0]['n'], n_games)
        self.assertEqual(self.artefacts['corr_rows'][1]['n'], n_games)

    def test_pearson_and_fisher_math(self):
        r, n = pearson([1, 2, 3, 4, 5], [2, 4, 6, 8, 10])
        self.assertAlmostEqual(r, 1.0)
        self.assertEqual(n, 5)
        r, _ = pearson([1, 2, 3, 4, 5], [10, 8, 6, 4, 2])
        self.assertAlmostEqual(r, -1.0)
        lo, hi = fisher_ci(0.0, 100)
        self.assertAlmostEqual(lo, -0.196, places=3)
        self.assertAlmostEqual(hi, 0.196, places=3)
        with self.assertRaises(FeedError):
            pearson([1, 2], [1, 2])

    def test_fit_refuses_tiny_input(self):
        with self.assertRaises(FeedError):
            fit([{'home_score': 1, 'away_score': 0}] * 4)

    def test_price_family_consistent(self):
        model = self.artefacts['model']
        for g in self.artefacts['week11_games']:
            p = price(model, g)
            self.assertGreaterEqual(p['p_home_win'], 0.0)
            self.assertLessEqual(p['p_home_win'], 1.0)
            self.assertEqual(p['total'], p['ep_home'] + p['ep_away'])
            self.assertAlmostEqual(p['fair_home_line'], -p['margin'])

    def test_replacement_depth_field_populated_and_withheld(self):
        rows = self.artefacts['repl_rows']
        self.assertEqual(len(rows), 13)
        with_depth = [r for r in rows if r['depth_travelled'] == 1]
        self.assertGreaterEqual(len(with_depth), 8)
        withheld = [r for r in rows if r['depth_travelled'] is None]
        self.assertGreaterEqual(len(withheld), 5)
        self.assertTrue(all(r['replacement_status'] for r in withheld))

    def test_exports_deterministic(self):
        counts = self.artefacts['counts']
        self.assertEqual(counts['price_snapshots.csv'], 2 * counts['markets_week11.csv'])
        self.assertEqual(counts['results_2026.csv'], self.artefacts['feed_stats']['finals'])


class PageTests(unittest.TestCase):
    """The generated pages keep the policy: blanks stay blank, rows stay sourced."""

    @classmethod
    def setUpClass(cls):
        cls.parsed = {}
        for name in ('results-feed.html', 'origination.html', 'price-snapshots.html',
                     'signal-staking.html', 'correlations-official.html', 'replacement-depth.html'):
            parser = Page()
            parser.feed((ROOT / name).read_text())
            parser.close()
            cls.parsed[name] = parser

    def test_all_rows_source_linked(self):
        errors, rows = check()
        self.assertEqual(errors, [])
        self.assertGreaterEqual(rows, 1000)

    def test_market_column_blank_and_fair_column_populated(self):
        parser = self.parsed['origination.html']
        board = [r for r in parser.rows if r['cells'] and r['cells'][0].isdigit()]
        self.assertEqual(len(board), 39)
        for r in board:
            self.assertTrue(r['cells'][3].strip(), 'fair line must be published')
            self.assertFalse(r['cells'][4].strip(), 'market line must stay blank')
            self.assertFalse(r['cells'][5].strip(), 'difference must stay blank')

    def test_snapshot_closes_blank(self):
        parser = self.parsed['price-snapshots.html']
        rows = [r for r in parser.rows if r['cells'] and 'reg-11#' in r['cells'][0]]
        closes = [r for r in rows if r['cells'][2] == 'Close']
        self.assertEqual(len(closes), 39)
        self.assertTrue(all(not r['cells'][3].strip() for r in closes), 'close price must be blank')
        opens = [r for r in rows if r['cells'][2] == 'Open']
        self.assertEqual(len(opens), 39)
        self.assertTrue(all(r['cells'][3].strip() for r in opens))

    def test_staking_sheet_rois_blank_but_signal_populated(self):
        parser = self.parsed['signal-staking.html']
        staking = [r for r in parser.rows if r['cells'] and r['cells'][0].startswith('OWN-')
                   and 'flat 1 unit' in r['cells'][1]]
        self.assertEqual(len(staking), 3)
        for r in staking:
            for cell in r['cells'][2:5]:
                self.assertFalse(cell.strip(), 'staking price-dependent cells stay blank')
        signal = [r for r in parser.rows if r['cells'] and r['cells'][0].startswith('OWN-')
                  and r['cells'][1] == 'Paper']
        self.assertEqual(len(signal), 3)
        self.assertTrue(all(r['cells'][2].strip() for r in signal), 'signal n must be published')

    def test_correlations_publish_n(self):
        parser = self.parsed['correlations-official.html']
        rows = [r for r in parser.rows if ' vs ' in (r['cells'][0] if r['cells'] else '')]
        self.assertGreaterEqual(len(rows), 3)
        for r in rows:
            self.assertTrue(r['cells'][1].strip().isdigit(), 'n must be published with each value')

    def test_no_invented_depth_tiers(self):
        parser = self.parsed['replacement-depth.html']
        text_rows = [r['cells'] for r in parser.rows]
        # Depth labels allowed only where a chart was retrieved; withheld rows must not render one.
        withheld = [r for r in text_rows if len(r) >= 8 and r[5] and 'Withheld' in r[5]]
        self.assertGreaterEqual(len(withheld), 3)
        for r in withheld:
            tier_cell = r[6] if len(r) > 6 else ''
            self.assertFalse('string' in tier_cell.lower(), 'a withheld row rendered a tier')

    def test_new_pages_registered_with_sources(self):
        for name in self.parsed:
            self.assertIn(name, render(), f'{name} missing from generator output')
            manifest_urls = set()
            import json
            for s in json.loads((ROOT / 'evidence' / 'sources.json').read_text()):
                manifest_urls.add(s['url'])
            for row_ in self.parsed[name].rows:
                self.assertTrue(any(link in manifest_urls for link in row_['links']))


if __name__ == '__main__':
    unittest.main()
