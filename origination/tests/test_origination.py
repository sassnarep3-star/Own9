"""Unit tests for the line-origination desk.

These test arithmetic, ordering, fail-closed behaviour and reproducibility.
They do not test NFL skill, and passing them is not a claim that any strategy
works.
"""

import csv
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))

from ownline import metrics, model, pipeline, score  # noqa: E402
from ownline import depth as depth_mod  # noqa: E402


class TestSettlement(unittest.TestCase):
    def test_spread_states(self):
        # Home favoured by 3, home wins by 7 -> home covers.
        self.assertEqual(metrics.settlement('SIDE', 24, 17, 3.0), 1.0)
        self.assertEqual(metrics.settlement('SIDE', 20, 17, 3.0), 0.5)
        self.assertEqual(metrics.settlement('SIDE', 17, 24, 3.0), 0.0)

    def test_total_states(self):
        self.assertEqual(metrics.settlement('TOTAL', 24, 17, 40.5), 1.0)
        self.assertEqual(metrics.settlement('TOTAL', 20, 20, 40.0), 0.5)
        self.assertEqual(metrics.settlement('TOTAL', 10, 13, 40.5), 0.0)

    def test_moneyline_tie_is_a_push(self):
        self.assertEqual(metrics.settlement('MONEYLINE', 17, 17, None), 0.5)

    def test_missing_line_returns_none(self):
        self.assertIsNone(metrics.settlement('SIDE', 24, 17, None))


class TestMetrics(unittest.TestCase):
    def test_log_loss_perfect_is_zero(self):
        self.assertAlmostEqual(metrics.log_loss([1.0, 0.0], [1.0, 0.0]), 0.0, places=9)

    def test_brier_symmetry(self):
        self.assertAlmostEqual(metrics.brier([0.5, 0.5], [1.0, 0.0]), 0.25)

    def test_cluster_robust_lcb_reports_clusters(self):
        diffs = [0.1] * 40 + [-0.1] * 40
        clusters = [i // 4 for i in range(80)]
        out = metrics.cluster_robust_lcb(diffs, clusters)
        self.assertIsNotNone(out)
        self.assertEqual(out['clusters'], 20)
        self.assertLess(out['lcb'], out['mean'])

    def test_fisher_z_interval_brackets_the_point(self):
        out = metrics.fisher_z_interval(0.4, 200)
        self.assertLess(out['lo'], 0.4)
        self.assertGreater(out['hi'], 0.4)

    def test_fisher_z_undefined_for_tiny_n(self):
        self.assertIsNone(metrics.fisher_z_interval(0.4, 3))

    def test_frechet_bounds(self):
        self.assertEqual(metrics.frechet_bounds(0.2, 0.3), (0.0, 0.2))
        lo, hi = metrics.frechet_bounds(0.8, 0.9)
        self.assertAlmostEqual(lo, 0.7)
        self.assertAlmostEqual(hi, 0.8)

    def test_joint_from_correlation_stays_in_bounds(self):
        joint = metrics.joint_from_correlation(0.8, 0.9, 1.0)
        self.assertAlmostEqual(joint, 0.8)
        joint = metrics.joint_from_correlation(0.2, 0.3, 1.0)
        self.assertAlmostEqual(joint, 0.2)

    def test_kelly_is_zero_without_an_edge(self):
        self.assertEqual(metrics.kelly_fraction(0.40, 1.9), 0.0)

    def test_kelly_is_capped(self):
        self.assertLessEqual(metrics.kelly_fraction(0.9, 10.0, cap=0.25), 0.25)

    def test_max_drawdown(self):
        # Peak of +1, trough of -1: the decline is 2 units.
        self.assertEqual(metrics.max_drawdown([1, -2, 3]), -2.0)

    def test_pearson_publishes_n(self):
        out = metrics.pearson([1, 2, 3, 4], [1, 2, 3, 4])
        self.assertEqual(out['n'], 4)
        self.assertAlmostEqual(out['r'], 1.0)

    def test_pearson_undefined_on_constant(self):
        self.assertIsNone(metrics.pearson([1, 1, 1], [1, 2, 3]))


class TestDeadbandGate(unittest.TestCase):
    def test_inside_deadband_takes_zero(self):
        verdict = pipeline.deadband_verdict({'r': 0.001, 'n': 10,
                                             'lo': -0.01, 'hi': 0.01})
        self.assertEqual(verdict['verdict'], 'use')
        self.assertEqual(verdict['point'], 0.0)

    def test_outside_deadband_uses_the_estimate(self):
        verdict = pipeline.deadband_verdict({'r': 0.3, 'n': 10,
                                             'lo': 0.2, 'hi': 0.4})
        self.assertEqual(verdict['verdict'], 'use')
        self.assertEqual(verdict['point'], 0.3)

    def test_straddling_deadband_refuses(self):
        verdict = pipeline.deadband_verdict({'r': 0.03, 'n': 10,
                                             'lo': 0.001, 'hi': 0.07})
        self.assertEqual(verdict['verdict'], 'refuse')

    def test_missing_interval_refuses(self):
        self.assertEqual(pipeline.deadband_verdict(None)['verdict'], 'refuse')


class TestModel(unittest.TestCase):
    def setUp(self):
        self.games = [
            {'home_team': 'A', 'away_team': 'B', 'home_score': '30', 'away_score': '10'},
            {'home_team': 'B', 'away_team': 'A', 'home_score': '14', 'away_score': '17'},
            {'home_team': 'A', 'away_team': 'C', 'home_score': '24', 'away_score': '21'},
            {'home_team': 'C', 'away_team': 'B', 'home_score': '7', 'away_score': '28'},
        ]
        self.state = model.fit(self.games, ['A', 'B', 'C'])

    def test_origination_order(self):
        markets, _ = model.originate(self.state, {'home_team': 'A', 'away_team': 'B'})
        self.assertEqual([m['market'] for m in markets], ['SIDE', 'TOTAL', 'MONEYLINE'])
        self.assertEqual([m['order'] for m in markets], [1, 2, 3])

    def test_moneyline_reuses_the_side_distribution(self):
        markets, _ = model.originate(self.state, {'home_team': 'A', 'away_team': 'B'})
        self.assertEqual(markets[0]['model_margin_mean'], markets[2]['model_margin_mean'])
        self.assertEqual(markets[0]['model_sigma'], markets[2]['model_sigma'])

    def test_fair_handicap_is_the_negative_margin(self):
        markets, pred = model.originate(self.state, {'home_team': 'A', 'away_team': 'B'})
        self.assertAlmostEqual(markets[0]['fair_line'], -pred['margin'])

    def test_probabilities_stay_in_unit_interval(self):
        markets, pred = model.originate(self.state, {'home_team': 'A', 'away_team': 'B'})
        self.assertGreaterEqual(markets[2]['fair_probability_home'], 0.0)
        self.assertLessEqual(markets[2]['fair_probability_home'], 1.0)

    def test_american_conversion_round_trip(self):
        price = model.fair_probability_to_american(0.75)
        self.assertAlmostEqual(1.0 / 0.75, model.american_to_decimal(price), places=2)

    def test_devig_is_a_convention_not_a_truth(self):
        self.assertAlmostEqual(model.devig_two_way(-110, -110), 0.5, places=6)
        self.assertIsNone(model.devig_two_way(None, -110))


class TestNoLeakage(unittest.TestCase):
    def setUp(self):
        self.report = json.loads((ROOT / 'data' / 'report.json').read_text())

    def test_every_fit_uses_only_earlier_seasons(self):
        for fit in self.report['fits']:
            target = fit['target_season']
            self.assertTrue(all(s < target for s in fit['train_seasons']),
                            'leakage in target season %s' % target)

    def test_minimum_training_seasons_respected(self):
        minimum = self.report['constants']['min_train_seasons']
        for fit in self.report['fits']:
            self.assertGreaterEqual(len(fit['train_seasons']), minimum)


class TestPriceStore(unittest.TestCase):
    def setUp(self):
        with (ROOT / 'data' / 'prices.csv').open(newline='', encoding='utf-8') as handle:
            self.rows = list(csv.DictReader(handle))

    def test_no_opening_value_exists(self):
        for row in self.rows:
            self.assertEqual(row['open_line'], '')
            self.assertEqual(row['open_price'], '')
            self.assertEqual(row['open_captured_utc'], '')
            self.assertEqual(row['open_source'], '')

    def test_no_capture_timestamp_exists(self):
        for row in self.rows:
            self.assertEqual(row['close_captured_utc'], '')

    def test_every_row_states_its_provenance(self):
        for row in self.rows:
            self.assertIn('unconfirmed', row['close_provenance'])

    def test_one_row_per_market(self):
        keys = {(r['game_id'], r['market']) for r in self.rows}
        self.assertEqual(len(keys), len(self.rows))


class TestDepth(unittest.TestCase):
    def test_second_string_replacement_is_read_as_second_string(self):
        rows = depth_mod.deficiency_rows()
        hit = [r for r in rows if r['player'] == 'Ben Brown' and r['slot'] == 'LG']
        self.assertEqual(len(hit), 1)
        self.assertEqual(hit[0]['replacement'], 'Walter Rouse')
        self.assertEqual(hit[0]['replacement_tier'], 2)

    def test_third_string_replacement_is_read_as_third_string(self):
        rows = depth_mod.deficiency_rows()
        hit = [r for r in rows if r['player'] == 'TreVeyon Henderson']
        self.assertEqual(len(hit), 1)
        self.assertEqual(hit[0]['replacement'], 'Corey Kiner')
        self.assertEqual(hit[0]['replacement_tier'], 3)

    def test_player_absent_from_the_chart_is_blank_not_guessed(self):
        rows = depth_mod.deficiency_rows()
        hit = [r for r in rows if r['player'] == 'Kerby Joseph']
        self.assertEqual(len(hit), 1)
        self.assertEqual(hit[0]['replacement'], '')
        self.assertIsNone(hit[0]['replacement_tier'])

    def test_every_depth_row_is_tiered_and_sourced(self):
        for row in depth_mod.depth_rows():
            self.assertIn(row['tier'], (1, 2, 3, 4))
            self.assertTrue(row['source_id'])


class TestReproducibility(unittest.TestCase):
    def test_pages_regenerate_byte_identically(self):
        env = {'PATH': '/usr/bin:/bin:/usr/local/bin'}
        for script in ('tools/run.py', 'tools/build.py'):
            result = subprocess.run([sys.executable, script], cwd=str(ROOT),
                                    capture_output=True, text=True, env=env)
            self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        check = subprocess.run([sys.executable, 'tools/verify.py'], cwd=str(ROOT),
                               capture_output=True, text=True)
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

    def test_verifier_rejects_an_invented_opening_price(self):
        """A store that invents an opening value must fail the build."""
        path = ROOT / 'data' / 'prices.csv'
        original = path.read_text(encoding='utf-8')
        try:
            lines = original.splitlines()
            header = lines[0].split(',')
            index = header.index('open_line')
            parts = lines[1].split(',')
            parts[index] = '-2.5'
            lines[1] = ','.join(parts)
            path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
            sys.path.insert(0, str(ROOT / 'tools'))
            import verify
            errors = verify.data_integrity()
            self.assertTrue(any('opening value' in e for e in errors),
                            'the verifier accepted an invented opening price')
        finally:
            path.write_text(original, encoding='utf-8')


if __name__ == '__main__':
    unittest.main(verbosity=2)
