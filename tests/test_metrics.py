import math
import unittest
from research.metrics import (expected_return, fair_decimal, proportional_no_vig,
    binary_scores, pearson, binary_joint, joint_from_phi, eligible, GATES)

class ResearchMath(unittest.TestCase):
    # Synthetic arithmetic examples, never NFL measurements.
    def test_ev_and_push(self):
        self.assertAlmostEqual(expected_return(.6,.4,0,2), .2)
        self.assertAlmostEqual(expected_return(.5,.4,.1,1.8), 0)
        self.assertAlmostEqual(fair_decimal(.5,.4,.1),1.8)
        self.assertIsNone(fair_decimal(0,1))
        self.assertEqual(expected_return(0,0,1,2),0)
    def test_ev_invalid(self):
        for args in [(.6,.5,0,2),(-.1,1,.1,2),(.5,.5,0,1),(.5,.5,0,math.inf)]:
            with self.assertRaises(ValueError): expected_return(*args)
        with self.assertRaises(ValueError): expected_return(.5,.5,0,2,-1)
    def test_baseline(self):
        self.assertEqual(proportional_no_vig([1.9,1.9]),[.5,.5])
        with self.assertRaises(ValueError): proportional_no_vig([2])
    def test_scores(self):
        result=binary_scores([0,1,1,0],[.1,.9,.8,.3])
        self.assertAlmostEqual(result['brier'],.0375) # official sklearn example
        self.assertAlmostEqual(binary_scores([0,1],[.5,.5])['log_loss'],math.log(2))
        self.assertEqual(binary_scores([0,1],[0,1])['log_loss'],0)
        self.assertEqual(binary_scores([1],[0])['log_loss'],math.inf)
    def test_invalid_scores(self):
        for ys,ps in [([],[]),([1],[.5,.6]),([None],[.5]),([1],[math.nan]),([0],[1.1])]:
            with self.assertRaises(ValueError): binary_scores(ys,ps)
    def test_correlations(self):
        self.assertEqual(pearson([0,1],[0,1]),1)
        self.assertEqual(pearson([0,1],[1,0]),-1)
        self.assertIsNone(pearson([1,1],[0,1]))
        self.assertEqual(binary_joint([0,0,1,1],[0,1,0,1]),{'n':4,'phi':0.,'joint_win':.25})
    def test_invalid_pairs(self):
        for x,y in [([1],[1]),([0,1],[1]),([math.nan,1],[0,1])]:
            with self.assertRaises(ValueError): pearson(x,y)
        with self.assertRaises(ValueError): binary_joint([0,1],[0,None])
    def test_joint(self):
        self.assertAlmostEqual(joint_from_phi(.5,.5,0),.25)
        self.assertAlmostEqual(joint_from_phi(.5,.5,1),.5)
        with self.assertRaises(ValueError): joint_from_phi(.9,.1,1)
        with self.assertRaises(ValueError): joint_from_phi(1,.5,0)
    def test_fail_closed(self):
        self.assertFalse(eligible({}))
        gates=dict.fromkeys(GATES,True)
        self.assertTrue(eligible(gates))
        gates['holdout']='pass'
        self.assertFalse(eligible(gates))

if __name__ == '__main__': unittest.main()
