"""Availability evidence tests. Fixtures here are SYNTHETIC except where the
committed official-source files are the subject under test."""
import copy
import unittest
from engine import availability as av


class CommittedEvidenceTests(unittest.TestCase):
    def test_committed_evidence_is_valid(self):
        problems, summary = av.validate_all()
        self.assertEqual(problems, [])
        self.assertEqual(summary['blocks'], 4)
        self.assertEqual(summary['changed'], 4)
        self.assertEqual(summary['teams'], ['DET', 'WAS'])

    def test_depth_tiers_are_never_filled(self):
        self.assertTrue(av.replacement_tiers_are_blank())

    def test_every_replacement_chain_is_sourced(self):
        doc = av._load(av.LINEUPS)
        for item in doc['replacement_chain']:
            self.assertIn('evidence', item)
            self.assertTrue(item['evidence'])

    def test_injury_snapshot_keeps_blank_semantics(self):
        doc = av._load(av.INJURY)
        blanks = [o for o in doc['observations'] if o['game_status'] is None]
        # A blank game status must exist and must not have been rewritten as healthy.
        self.assertTrue(blanks)
        for obs in blanks:
            self.assertIsNone(obs['game_status'])
        self.assertIn('not a clearance', doc['field_definitions']['game_status'])


class SyntheticRuleTests(unittest.TestCase):
    def setUp(self):
        self.doc = copy.deepcopy(av._load(av.LINEUPS))

    def test_wrong_starter_count_fails(self):
        self.doc['lineups'][0]['week10'] = self.doc['lineups'][0]['week10'][:10]
        problems, _ = av.validate_lineups(self.doc)
        self.assertTrue(any('expected 11' in p for p in problems))

    def test_duplicate_player_fails(self):
        block = self.doc['lineups'][0]
        block['week10'][0] = list(block['week10'][1])
        problems, _ = av.validate_lineups(self.doc)
        self.assertTrue(any('listed twice' in p for p in problems))

    def test_player_both_out_and_in_fails(self):
        block = self.doc['lineups'][0]
        block['in'] = block['in'] + [block['out'][0]]
        problems, _ = av.validate_lineups(self.doc)
        self.assertTrue(any('both out and in' in p for p in problems))

    def test_false_retained_claim_fails(self):
        block = self.doc['lineups'][0]
        block['retained'] = block['retained'] + ['99 X.Nobody']
        problems, _ = av.validate_lineups(self.doc)
        self.assertTrue(any('retained names not listed' in p for p in problems))

    def test_wrong_membership_label_fails(self):
        for block in self.doc['lineups']:
            block['membership_change'] = 'same'
        problems, _ = av.validate_lineups(self.doc)
        self.assertTrue(any('membership_change should be changed' in p for p in problems))

    def test_invented_depth_tier_is_rejected(self):
        doc = copy.deepcopy(av._load(av.LINEUPS))
        doc['replacement_chain'][0]['depth_tier_of_replacement'] = '2nd string'
        self.assertFalse(av.replacement_tiers_are_blank(doc))

    def test_unknown_practice_status_fails(self):
        doc = copy.deepcopy(av._load(av.INJURY))
        doc['observations'][0]['practice_status'] = 'Probable'
        problems, _ = av.validate_injury(doc)
        self.assertTrue(any('unknown practice status' in p for p in problems))

    def test_unknown_game_status_fails(self):
        doc = copy.deepcopy(av._load(av.INJURY))
        doc['observations'][0]['game_status'] = 'Likely'
        problems, _ = av.validate_injury(doc)
        self.assertTrue(any('unknown game status' in p for p in problems))


if __name__ == '__main__':
    unittest.main()
