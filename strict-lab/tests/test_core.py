import math
import unittest
from analysis.core import (decimal_odds, normalized_implied, expected_return,
    fair_decimal, score_lines, binary_joint, phi, cluster_correlation,
    binary_metrics, holm_adjust, audit_record, utc_time)


class Pricing(unittest.TestCase):
    def test_american(self):
        self.assertEqual(decimal_odds(150), 2.5)
        self.assertEqual(decimal_odds(-200), 1.5)
        self.assertEqual(decimal_odds(-100), 2)

    def test_american_invalid(self):
        for odds in (0, 50, -90, math.nan, math.inf, True, '100'):
            with self.subTest(odds=odds), self.assertRaises(ValueError):
                decimal_odds(odds)

    def test_baseline(self):
        self.assertEqual(normalized_implied([1.9,1.9]), [.5,.5])
        self.assertAlmostEqual(sum(normalized_implied([2,3,4])), 1)

    def test_invalid_baseline(self):
        for odds in ([], [2], [1,2], [2,math.inf]):
            with self.assertRaises(ValueError): normalized_implied(odds)

    def test_refund_ev(self):
        self.assertAlmostEqual(expected_return(.45,.1,2), 0)
        self.assertAlmostEqual(expected_return(.5,0,2.1), .05)
        self.assertEqual(fair_decimal(.45,.1), 2)
        self.assertIsNone(fair_decimal(0))
        self.assertIsNone(fair_decimal(0,1))

    def test_invalid_settlement(self):
        for args in ((.8,.3,2), (-.1,0,2), (.5,0,1), (.5,0,math.nan)):
            with self.assertRaises(ValueError): expected_return(*args)
        with self.assertRaises(ValueError): fair_decimal(.8,.3)

    def test_score_pmf_signs(self):
        # Synthetic scores. Never a historical NFL sample.
        result = score_lines([(24,21,.5),(20,20,.25),(17,24,.25)], -3, 45)
        self.assertEqual(result['moneyline']['win'], .5)
        self.assertEqual(result['moneyline']['push'], .25)
        self.assertEqual(result['moneyline']['fair_decimal'], 1.5)
        self.assertEqual(result['spread']['win'], 0)
        self.assertEqual(result['spread']['push'], .5)
        self.assertIsNone(result['spread']['fair_decimal'])
        self.assertEqual(result['total_over']['push'], .5)
        self.assertEqual(result['total_over']['loss'], .5)

    def test_bad_pmf(self):
        for pmf in ([], [(1,2,.9)], [(1,2,1.1)], [(-1,0,1)], [(1.5,0,1)],
                    [(1,2,.5),(1,2,.5)], [(True,0,1)]):
            with self.assertRaises(ValueError): score_lines(pmf)
        with self.assertRaises(ValueError): score_lines([(1,2,1)], math.nan, 3)

    def test_joint(self):
        self.assertEqual(binary_joint(.5,.5,0), .25)
        self.assertEqual(binary_joint(.5,.5,1), .5)
        self.assertEqual(binary_joint(.5,.5,-1), 0)

    def test_joint_frechet(self):
        for args in ((.9,.1,1),(.9,.9,-1),(.5,.5,1.01),(0,.5,0)):
            with self.assertRaises(ValueError): binary_joint(*args)


class StatisticalMethods(unittest.TestCase):
    def test_phi(self):
        self.assertEqual(phi([(0,0),(1,1)]), 1)
        self.assertEqual(phi([(0,1),(1,0)]), -1)
        self.assertEqual(phi([(0,0),(0,1),(1,0),(1,1)]), 0)

    def test_undefined_phi(self):
        self.assertIsNone(phi([]))
        self.assertIsNone(phi([(1,0),(1,1)]))
        with self.assertRaises(ValueError): phi([(1,None)])

    def test_sparse_bootstrap(self):
        result = cluster_correlation([('g1',0,0),('g2',1,1)])
        self.assertEqual(result['n'],2)
        self.assertEqual(result['rho'],1)
        self.assertIsNone(result['ci_low'])
        self.assertEqual(result['status'],'insufficient evidence')

    def test_missing_bootstrap(self):
        result = cluster_correlation([])
        self.assertIsNone(result['rho'])
        self.assertIsNone(result['ci_high'])

    def test_cluster_bootstrap_reproducible(self):
        rows = [(str(i), i%2, (i//2)%2) for i in range(80)]
        a = cluster_correlation(rows,200,9)
        b = cluster_correlation(rows,200,9)
        self.assertEqual(a,b)
        self.assertEqual(a['status'],'exploratory estimate')
        self.assertLessEqual(a['ci_low'],0)
        self.assertGreaterEqual(a['ci_high'],0)

    def test_degenerate_bootstrap_withholds(self):
        result = cluster_correlation([('a',0,0),('b',1,1)],100,9,2)
        self.assertIsNone(result['ci_low'])
        self.assertIn('degenerate',result['status'])

    def test_bad_bootstrap(self):
        with self.assertRaises(ValueError): cluster_correlation([('',0,1)])
        with self.assertRaises(ValueError): cluster_correlation([],10)

    def test_metrics(self):
        result = binary_metrics([.5,.5],[0,1])
        self.assertEqual(result['brier'], .25)
        self.assertAlmostEqual(result['log_loss'], math.log(2))
        self.assertEqual(binary_metrics([0,1],[0,1])['log_loss'], 0)
        self.assertTrue(math.isinf(binary_metrics([0],[1])['log_loss']))

    def test_bad_metrics(self):
        for p,y in (([],[]),([.5],[]),([.5],[2]),([1.2],[1])):
            with self.assertRaises(ValueError): binary_metrics(p,y)

    def test_holm(self):
        self.assertEqual(holm_adjust([.01,.04,.03]), [.03,.06,.06])
        self.assertEqual(holm_adjust([]), [])
        self.assertEqual(holm_adjust([.9,.9]),[1,1])
        with self.assertRaises(ValueError): holm_adjust([math.nan])


class PointInTime(unittest.TestCase):
    def record(self):
        return dict(id='synthetic-1',game_id='synthetic-game',strategy_id='test',
            feature_available_at='2020-01-01T10:00:00Z',quote_at='2020-01-01T10:30:00Z',
            forecast_at='2020-01-01T11:00:00Z',kickoff_at='2020-01-01T12:00:00Z',
            outcome_at='2020-01-01T16:00:00Z',source_url='https://www.nfl.com/stats/',
            quote_source_url='https://sportsbook.draftkings.com/',
            rules_url='https://sportsbook.draftkings.com/help/general-betting-rules/market-rules',
            snapshot_sha256='a'*64,outcome='win')

    def test_structural_validity_not_truth(self):
        self.assertEqual(audit_record(self.record()), [])

    def test_missing(self):
        self.assertIn('missing quote_at',audit_record({}))

    def test_leakage(self):
        row=self.record(); row['feature_available_at']='2020-01-01T13:00:00Z'
        self.assertIn('point-in-time ordering violated',audit_record(row))

    def test_quote_after_forecast(self):
        row=self.record(); row['quote_at']='2020-01-01T11:01:00Z'
        self.assertIn('point-in-time ordering violated',audit_record(row))

    def test_forecast_at_kickoff_fails(self):
        row=self.record(); row['forecast_at']=row['kickoff_at']
        self.assertIn('point-in-time ordering violated',audit_record(row))

    def test_timezone(self):
        with self.assertRaises(ValueError): utc_time('2020-01-01T00:00:00')
        row=self.record(); row['forecast_at']='not a date'
        self.assertIn('invalid timestamp',audit_record(row))

    def test_url_and_hash_and_settlement(self):
        row=self.record(); row.update(source_url='http://example.com', snapshot_sha256='bad',outcome='?')
        self.assertEqual(len(audit_record(row)),3)


if __name__ == '__main__': unittest.main()
