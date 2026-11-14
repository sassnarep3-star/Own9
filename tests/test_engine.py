"""ALL numerical fixtures in these tests are SYNTHETIC, not NFL observations."""
import math
import unittest
from engine.core import *
from engine.core import _normal_quantile


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


class DependenceGateTests(unittest.TestCase):
    """SYNTHETIC values only. No NFL correlation is asserted anywhere here."""
    def test_normal_quantile(self):
        self.assertAlmostEqual(_normal_quantile(.975),1.959963985,places=6)
        self.assertAlmostEqual(_normal_quantile(.5),0,places=9)
        self.assertAlmostEqual(_normal_quantile(.025),-1.959963985,places=6)
        for p in (0,1,-.1,1.1):
            with self.assertRaises(ValueError): _normal_quantile(p)
    def test_interval_shrinks_with_n(self):
        wide=correlation_interval(.4,25); narrow=correlation_interval(.4,2500)
        self.assertLess(narrow[1]-narrow[0],wide[1]-wide[0])
        self.assertTrue(wide[0]<.4<wide[1] and narrow[0]<.4<narrow[1])
    def test_interval_degenerate(self):
        self.assertIsNone(correlation_interval(.4,3))
        self.assertIsNone(correlation_interval(1,100))
        for r in (.4,):
            with self.assertRaises(ValueError): correlation_interval(r,100,confidence=0)
    def test_fisher_bounds(self):
        for r in (-1,1,2):
            with self.assertRaises(ValueError): fisher_z(r)
        self.assertAlmostEqual(fisher_z(0),0)
    def test_gate_directional(self):
        self.assertEqual(dependence_gate(.30,400,200,.95,.05)['verdict'],'significantly_positive')
        self.assertEqual(dependence_gate(-.30,400,200,.95,.05)['verdict'],'significantly_negative')
    def test_gate_zero_not_used(self):
        g=dependence_gate(.005,400,200,.95,.05)
        self.assertEqual(g['verdict'],'indistinguishable_from_zero')
        self.assertFalse(g['may_price_joint'])
    def test_gate_insufficient(self):
        g=dependence_gate(.9,10,200)
        self.assertEqual(g['verdict'],'insufficient_evidence')
        self.assertIsNone(g['interval'])
        self.assertFalse(g['may_price_joint'])
    def test_gate_rejects_bad_input(self):
        for args in ((1.5,100,20),(.2,100,2),(.2,100,20,.95,-.1)):
            with self.assertRaises(ValueError): dependence_gate(*args)
    def test_joint_price_refuses_independence_default(self):
        blocked=dependence_gate(.005,400,200,.95,.05)
        self.assertIsNone(joint_price_from_dependence(.5,.5,blocked))
        self.assertIsNone(joint_price_from_dependence(.5,.5,None))
        self.assertIsNone(joint_price_from_dependence(.5,.5,{}))
    def test_joint_price_when_gate_passes(self):
        allowed=dependence_gate(.30,400,200,.95,.05)
        p=joint_price_from_dependence(.5,.5,allowed)
        self.assertAlmostEqual(p,.25+.30*.25)  # sqrt(.25*.25)=.25
        lo,hi=max(0,.5+.5-1),min(.5,.5)
        self.assertTrue(lo<=p<=hi)
    def test_joint_price_with_negative_dependence(self):
        allowed=dependence_gate(-.40,400,200,.95,.05)
        self.assertAlmostEqual(joint_price_from_dependence(.5,.5,allowed),.25-.40*.25)


if __name__=='__main__': unittest.main()
