"""Tests for the decision desk.

Run with:

    python3 -m unittest discover -s decision-desk/tests -v

The tests are deliberately boring: they assert that a number on a page came from a
committed file, that a hash still matches its bytes, that nothing marked as a proposal
has been implemented, and that the build is reproducible.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESK = ROOT / 'decision-desk'
DATA = DESK / 'data'
for entry in (str(DESK), str(DESK / 'tools')):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from parse_capture import parse  # noqa: E402

PAGES = ['index.html', 'requirements.html', 'questions.html', 'suggestions.html',
         'availability.html', 'fixtures.html', 'captures.html', 'sources.html',
         'flagged.html']


def load(name):
    return json.loads((DATA / name).read_text())


class RequirementRegister(unittest.TestCase):
    def test_every_requirement_has_a_gate_and_a_clearing_number(self):
        for r in load('requirements.json'):
            with self.subTest(id=r['id']):
                self.assertTrue(r['gate'].strip())
                self.assertTrue(r['clearing_number'].strip())
                self.assertTrue(r['evidence'])
                self.assertIn(r['status'], ('met', 'partial', 'not-started', 'rejected', 'blocked'))

    def test_ids_are_unique_and_sequential(self):
        ids = [r['id'] for r in load('requirements.json')]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids, [f'R{i:02d}' for i in range(1, len(ids) + 1)])

    def test_every_evidence_entry_has_a_url(self):
        for r in load('requirements.json'):
            for e in r['evidence']:
                with self.subTest(id=r['id'], label=e.get('label')):
                    self.assertTrue(e['url'].startswith('https://'))

    def test_status_counts_are_reported_not_hidden(self):
        statuses = {r['status'] for r in load('requirements.json')}
        self.assertIn('not-started', statuses)
        self.assertIn('partial', statuses)
        self.assertIn('blocked', statuses)

    def test_blocked_requirements_cite_the_terms_that_block_them(self):
        terms = 'https://www.nfl.com/legal/terms/'
        blocked = [r for r in load('requirements.json') if r['status'] == 'blocked']
        self.assertTrue(blocked)
        for r in blocked:
            with self.subTest(id=r['id']):
                self.assertIn(terms, [e['url'] for e in r['evidence']])


class SuggestionBoard(unittest.TestCase):
    def test_nothing_awaiting_decision_was_implemented(self):
        for s in load('suggestions.json')['suggestions']:
            with self.subTest(id=s['id']):
                self.assertFalse(s['status'].lower().startswith('implemented'))

    def test_suggestions_blocked_on_permission_name_the_terms(self):
        terms = 'https://www.nfl.com/legal/terms/'
        blocked = [s for s in load('suggestions.json')['suggestions']
                   if 'blocked on permission' in s['status'].lower()]
        self.assertTrue(blocked)
        for s in blocked:
            with self.subTest(id=s['id']):
                self.assertIn(terms, [e['url'] for e in s['evidence']])
                self.assertIn('Terms section 1.3', s['risk'])

    def test_no_path_is_chosen(self):
        for p in load('suggestions.json')['paths']:
            with self.subTest(id=p['id']):
                self.assertNotIn('chosen', p['name'].lower())

    def test_every_suggestion_has_a_cost_and_a_risk(self):
        for s in load('suggestions.json')['suggestions']:
            with self.subTest(id=s['id']):
                self.assertTrue(s['cost'].strip())
                self.assertTrue(s['risk'].strip())

    def test_decision_log_records_that_nothing_was_chosen(self):
        log = load('suggestions.json')['decision_log']
        self.assertTrue(log)
        self.assertTrue(any('No path chosen' in e['entry'] for e in log))


class CaptureIntegrity(unittest.TestCase):
    def test_manifest_hash_matches_the_committed_bytes(self):
        manifest = load('captures/manifest.json')
        hashed = [c for c in manifest['captures'] if c.get('sha256')]
        self.assertTrue(hashed)
        for c in hashed:
            path = DATA / 'captures' / c['file']
            with self.subTest(id=c['id']):
                self.assertTrue(path.exists())
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), c['sha256'])

    def test_parser_reproduces_the_committed_parse(self):
        for path in sorted((DATA / 'captures').glob('*.md')):
            fresh = parse(path)
            committed = load('parsed/injury_captures.json')[path.stem]
            with self.subTest(file=path.name):
                self.assertEqual(fresh['sha256'], committed['sha256'])
                self.assertEqual(len(fresh['rows']), len(committed['rows']))

    def test_parsed_rows_carry_the_required_fields(self):
        parsed = load('parsed/injury_captures.json')
        rows = parsed[sorted(parsed)[0]]['rows']
        self.assertGreaterEqual(len(rows), 300)
        for r in rows:
            with self.subTest(player=r['player']):
                self.assertTrue(r['team'])
                self.assertTrue(r['player'])
                self.assertTrue(r['position'])
                self.assertIn(r['practice_status'], (
                    'Full Participation in Practice',
                    'Limited Participation in Practice',
                    'Did Not Participate In Practice'))
                self.assertIn(r['game_status'], ('', 'Out', 'Doubtful', 'Questionable'))

    def test_club_count_matches_the_number_playing_that_week(self):
        parsed = load('parsed/injury_captures.json')
        clubs = parsed[sorted(parsed)[0]]['teams_published']
        self.assertEqual(len(clubs), 28)
        w10 = load('week-10-2026-results.json')
        self.assertEqual(len(clubs) + len(w10['bye_clubs']), 32)


class FixtureConsistency(unittest.TestCase):
    def test_week_11_covers_all_thirtytwo_clubs_exactly_once(self):
        w11 = load('week-11-2026-fixtures.json')
        playing = set()
        for g in w11['games']:
            playing.update((g['away'], g['home']))
        self.assertEqual(len(playing), 26)
        self.assertFalse(playing & set(w11['bye_clubs']))
        self.assertEqual(len(playing | set(w11['bye_clubs'])), 32)

    def test_week_10_covers_all_thirtytwo_clubs_exactly_once(self):
        w10 = load('week-10-2026-results.json')
        playing = set()
        for g in w10['games']:
            playing.update((g['away'], g['home']))
        self.assertEqual(len(playing), 28)
        self.assertFalse(playing & set(w10['bye_clubs']))
        self.assertEqual(len(playing | set(w10['bye_clubs'])), 32)

    def test_no_score_is_invented_for_a_game_that_had_not_kicked_off(self):
        for g in load('week-10-2026-results.json')['games']:
            with self.subTest(game=g['game_url']):
                if g['away_points'] is None:
                    self.assertIsNone(g['home_points'])
                    self.assertIn('not started', g['status'])


class Pages(unittest.TestCase):
    def test_all_pages_exist_and_self_describe(self):
        for name in PAGES:
            path = DESK / name
            with self.subTest(page=name):
                self.assertTrue(path.exists())
                text = path.read_text()
                self.assertIn('<h1>', text)
                self.assertIn('assets/style.css', text)
                self.assertIn('../index.html', text)

    def test_every_page_reaches_every_other_page(self):
        for name in PAGES:
            text = (DESK / name).read_text()
            for other in PAGES:
                with self.subTest(page=name, target=other):
                    self.assertIn(f'href="{other}"', text)

    def test_the_executive_summary_states_that_no_strategy_has_earned_a_stake(self):
        text = (DESK / 'index.html').read_text()
        self.assertIn('No strategy has earned a stake', text)

    def test_the_landing_page_carries_one_row_per_requirement(self):
        import re
        text = (DESK / 'index.html').read_text()
        body = re.search(r'<tbody>([\s\S]*?)</tbody>', text)
        self.assertIsNotNone(body)
        rows = re.findall(r'<tr>', body.group(1))
        self.assertEqual(len(rows), len(load('requirements.json')))


class BuildReproducibility(unittest.TestCase):
    def test_rebuilding_produces_identical_bytes(self):
        before = {name: (DESK / name).read_bytes() for name in PAGES}
        subprocess.run([sys.executable, str(DESK / 'tools' / 'build.py')],
                       check=True, capture_output=True, cwd=str(ROOT))
        for name, data in before.items():
            with self.subTest(page=name):
                self.assertEqual((DESK / name).read_bytes(), data)

    def test_the_verifier_passes_on_the_committed_tree(self):
        proc = subprocess.run([sys.executable, str(DESK / 'tools' / 'verify.py')],
                              capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == '__main__':
    unittest.main()
