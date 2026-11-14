"""Register tests: the failure mode is an unsupported assertion, not a bad number."""
import copy
import json
import unittest
from engine import registers as rg

S, Q, B = rg.load()


class CommittedRegisterTests(unittest.TestCase):
    def test_committed_registers_are_valid(self):
        problems, summary = rg.validate(S, Q, B)
        self.assertEqual(problems, [])
        # 16 through session 4f2e0291; +5 proposed by session 9a409d93
        # (price archive, close capture, sealed backtest, signal/staking
        # adoption, game-centre row verification).
        self.assertEqual(summary['suggestions'], 21)
        self.assertEqual(summary['decisions'], 21)
        # 22 through session 4f2e0291; +2 open questions by session 9a409d93
        # (grading operator, re-promotion thresholds).
        self.assertEqual(summary['questions'], 24)

    def test_every_suggestion_has_a_falsification_statement(self):
        for item in S['suggestions']:
            self.assertTrue(item['falsified_by'].strip(), item['id'])

    def test_every_suggestion_is_scored(self):
        for item in S['suggestions']:
            for field in ('impact', 'evidence_cost', 'reversibility_cost'):
                self.assertIn(item[field], (1, 2, 3), item['id'])

    def test_every_decision_has_a_default_and_stopping_rule(self):
        for d in B['decisions']:
            self.assertTrue(d['default_if_nothing_changes'].strip(), d['id'])
            self.assertTrue(d['stopping_rule'].strip(), d['id'])

    def test_unfinished_questions_leave_the_answer_blank(self):
        for q in Q['questions']:
            if q['state'] != 'answered':
                self.assertIsNone(q['answer'], q['id'])
                self.assertTrue(q['blocked_by'].strip(), q['id'])

    def test_question_state_counts_match_the_rows(self):
        _, summary = rg.validate(S, Q, B)
        counted = summary['question_states']
        self.assertEqual(sum(counted.values()), len(Q['questions']))

    def test_no_question_cites_an_unregistered_source(self):
        known = rg.known_source_ids()
        for q in Q['questions']:
            for ref in q['sources']:
                self.assertIn(ref, known, q['id'])


class SyntheticFailureTests(unittest.TestCase):
    def setUp(self):
        self.s, self.q, self.b = (copy.deepcopy(S), copy.deepcopy(Q), copy.deepcopy(B))

    def problems(self):
        return rg.validate(self.s, self.q, self.b)[0]

    def test_bad_status_rejected(self):
        self.s['suggestions'][0]['status'] = 'shipped'
        self.assertTrue(any('unknown status' in p for p in self.problems()))

    def test_missing_falsification_rejected(self):
        self.s['suggestions'][0]['falsified_by'] = ''
        self.assertTrue(any('empty falsified_by' in p for p in self.problems()))

    def test_blocked_suggestion_must_name_missing_artefact(self):
        for item in self.s['suggestions']:
            if item['status'] == 'blocked_on_evidence':
                item['needs'] = []
        self.assertTrue(any('blocked with no named missing artefact' in p for p in self.problems()))

    def test_answered_without_source_rejected(self):
        for q in self.q['questions']:
            if q['state'] == 'answered' and q.get('basis', 'publisher') == 'publisher':
                q['sources'] = ['repo']
                break
        self.assertTrue(any('no publisher source' in p for p in self.problems()))

    def test_unanswered_cannot_carry_an_answer(self):
        for q in self.q['questions']:
            if q['state'] == 'open_discoverable':
                q['answer'] = 'Guessed value'
                break
        self.assertTrue(any('must leave answer null' in p for p in self.problems()))

    def test_decision_without_stopping_rule_rejected(self):
        self.b['decisions'][0]['stopping_rule'] = ''
        self.assertTrue(any('no stopping rule' in p for p in self.problems()))

    def test_blocked_decision_must_name_blocker(self):
        for d in self.b['decisions']:
            if d['state'] == 'blocked':
                d['current_blocker'] = None
                break
        self.assertTrue(any('blocked without naming the blocker' in p for p in self.problems()))

    def test_accepted_suggestion_must_be_referenced(self):
        self.s['suggestions'].append({
            **copy.deepcopy(self.s['suggestions'][0]), 'id': 'S-99',
            'status': 'accepted', 'decision_ref': 'D-01'})
        self.assertTrue(any('accepted but no decision references it' in p for p in self.problems()))

    def test_unknown_suggestion_reference_rejected(self):
        self.b['decisions'][0]['suggestion'] = 'S-404'
        self.assertTrue(any('unknown suggestion' in p for p in self.problems()))

    def test_score_out_of_range_rejected(self):
        self.s['suggestions'][0]['impact'] = 5
        self.assertTrue(any('impact must be 1, 2 or 3' in p for p in self.problems()))


class OrderingTests(unittest.TestCase):
    def test_ranking_puts_high_impact_low_cost_first(self):
        a = {'impact': 1, 'evidence_cost': 3, 'reversibility_cost': 3}
        b = {'impact': 3, 'evidence_cost': 1, 'reversibility_cost': 1}
        self.assertLess(rg.impact_rank(b), rg.impact_rank(a))

    def test_ranking_is_deterministic(self):
        items = sorted(S['suggestions'], key=rg.impact_rank)
        self.assertEqual([i['id'] for i in items],
                         [i['id'] for i in sorted(S['suggestions'], key=rg.impact_rank)])


if __name__ == '__main__':
    unittest.main()
