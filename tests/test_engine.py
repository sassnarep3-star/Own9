"""ALL numerical fixtures in these tests are SYNTHETIC, not NFL observations."""
import math
import unittest
from engine.core import *


class PricingTests(unittest.TestCase):
    def test_american(self):
        self.assertAlmostEqual(american_to_decimal(-110), 1+100/110)
        self.assertEqual(american_to_decimal(150),2.5)
        for x in [-110,-250,100,150,900]:
            self.assertAlmostEqual(decimal_to_american(american_to_decimal(x)),x)
    def test_bad_odds(self):
        for x in [0,50,-99,float('nan'),float('inf'),True]:
            with self.assertRaises(ValueError): american_to_decimal(x)
        for x in [-1,0,1,float('nan')]:
            with self.assertRaises(ValueError): decimal_to_american(x)
    def test_vig(self):
        self.assertEqual(no_vig([1.91,1.91]),[.5,.5])
        self.assertAlmostEqual(sum(no_vig([2,3,4])),1)
    def test_bad_vig(self):
        for x in [[],[2],[1,2],[float('nan'),2]]:
            with self.assertRaises(ValueError): no_vig(x)
    def test_ev_push(self):
        o=Outcome(.5,.1,.4)
        self.assertAlmostEqual(o.fair_decimal(),1.8)
        self.assertAlmostEqual(o.ev(1.8),0)
        self.assertAlmostEqual(o.ev(2,.02),.08)
    def test_degenerate_outcomes(self):
        self.assertIsNone(Outcome(0,1,0).fair_decimal())
        self.assertEqual(Outcome(1,0,0).fair_decimal(),1)
    def test_bad_outcomes(self):
        for triple in [(.5,.5,.5),(-.1,.5,.6),(float('nan'),0,1)]:
            with self.assertRaises(ValueError): Outcome(*triple)
        with self.assertRaises(ValueError): Outcome(.5,0,.5).ev(1)
        with self.assertRaises(ValueError): Outcome(.5,0,.5).ev(2,-.1)
    def test_discrete_lines(self):
        d={(24,21):.4,(21,21):.1,(17,24):.5}
        self.assertEqual(score_market(d,'moneyline'),Outcome(.4,.1,.5))
        self.assertEqual(score_market(d,'spread',-3),Outcome(0,.4,.6))
        self.assertEqual(score_market(d,'total_over',42),Outcome(.4,.1,.5))
        self.assertEqual(distribution_lines(d)['home_spread_reference'],7)
        self.assertEqual(distribution_lines(d)['total_reference'],41)
    def test_bad_pmfs(self):
        for d in [{},{(1,2):.2},{(-1,2):1},{(1.1,2):1},{(1,2):float('nan')},{(True,2):1}]:
            with self.assertRaises(ValueError): score_market(d,'moneyline')
        with self.assertRaises(ValueError): score_market({(1,2):1},'other')
    def test_binary_joint(self):
        self.assertEqual(bernoulli_joint(.5,.5,0),.25)
        self.assertEqual(bernoulli_joint(.5,.5,1),.5)
        self.assertEqual(bernoulli_joint(.5,.5,-1),0)
    def test_impossible_joint(self):
        for triple in [(.9,.1,1),(1,.5,0),(.5,.5,2),(-.1,.5,0)]:
            with self.assertRaises(ValueError): bernoulli_joint(*triple)
    def test_joint_samples(self):
        self.assertEqual(sample_joint_hit([[True,True],[True,False],[False,True]]),1/3)
        for x in [[],[[]],[[True],[True,False]],[[1,0]]]:
            with self.assertRaises(ValueError): sample_joint_hit(x)


class ValidationTests(unittest.TestCase):
    def test_correlation(self):
        self.assertEqual(pearson([1,2,3],[2,4,6]),1)
        self.assertEqual(pearson([1,2,3],[6,4,2]),-1)
        self.assertIsNone(pearson([1,1],[2,3]))
        with self.assertRaises(ValueError): pearson([1],[2])
        with self.assertRaises(ValueError): pearson([1,2],[2])
    def test_scores(self):
        self.assertEqual(probability_scores([0,1],[0,1]),{'brier':0,'log_loss':0})
        self.assertEqual(probability_scores([.5,.5],[0,1])['brier'],.25)
        self.assertAlmostEqual(probability_scores([.5,.5],[0,1])['log_loss'],math.log(2))
        self.assertEqual(probability_scores([0],[1])['log_loss'],float('inf'))
    def test_bad_scores(self):
        for p,y in [([],[]),([.5],[2]),([2],[1]),([.5],[True]),([float('nan')],[1]),([.5],[])]:
            with self.assertRaises(ValueError): probability_scores(p,y)
    def test_bins(self):
        bins=reliability_bins([0,.5,1],[0,1,1],2)
        self.assertEqual(bins[0]['n'],1)
        self.assertEqual(bins[1]['n'],2)
        self.assertIsNone(reliability_bins([0],[0],3)[1]['hit_rate'])
    def test_holm(self):
        out=holm_adjust([.04,.01,.03])
        for x,y in zip(out,[.06,.03,.06]): self.assertAlmostEqual(x,y)
        self.assertEqual(holm_adjust([]),[])
        self.assertEqual(holm_adjust([1,1]),[1,1])
    def test_bootstrap(self):
        a=week_bootstrap_ci([1,2,3,4],['w1','w1','w2','w2'],seed=1)
        self.assertEqual(a,week_bootstrap_ci([1,2,3,4],['w1','w1','w2','w2'],seed=1))
        self.assertEqual(a,(1.5,3.5))
        self.assertEqual(week_bootstrap_ci([2,2],['w1','w2']),(2,2))
    def test_bad_bootstrap(self):
        for v,w in [([],[]),([1],[1]),([1,2],[1]),([1,2],['',2])]:
            with self.assertRaises(ValueError): week_bootstrap_ci(v,w)
    def test_folds(self):
        weeks=[(2025,1),(2025,1),(2025,2),(2025,3),(2025,3),(2025,4)]
        folds=list(walk_forward(weeks,1,1))
        self.assertEqual(folds,[([0,1],[3,4]),([0,1,2],[5])])
        for train,test in folds: self.assertLess(max(weeks[i] for i in train),min(weeks[i] for i in test))
    def test_fail_closed(self):
        self.assertEqual(len(eligibility({})['blockers']),11)
        self.assertFalse(eligibility({g:{'status':'pass'} for g in GATE_IDS})['eligible'])
        gates={g:{'status':'pass','evidence':{'artifact':'synthetic-test-only','sha256':'a'*64}} for g in GATE_IDS}
        self.assertTrue(eligibility(gates)['eligible'])
        gates['G01']['evidence']['sha256']='invalid'
        self.assertEqual(eligibility(gates)['blockers'],['G01'])


if __name__=='__main__': unittest.main()
