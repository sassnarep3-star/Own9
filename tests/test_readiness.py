"""Integrity tests for the 16 Nov 2026 readiness register and Week 10 recheck (session 9136b4d8)."""
import json
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
DATA = ROOT / 'session-9136b4d8' / 'data'


class ReadinessRegister(unittest.TestCase):
    def setUp(self):
        self.reg = json.loads((DATA / 'readiness.json').read_text(encoding='utf-8'))
        self.rows = self.reg['rows']

    def test_states_are_the_declared_vocabulary(self):
        allowed = set(self.reg['states'])
        self.assertTrue(all(r['state'] in allowed for r in self.rows))

    def test_ids_unique_and_rows_complete(self):
        ids = [r['id'] for r in self.rows]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 72)
        for r in self.rows:
            for key in ('group', 'requirement', 'state', 'gate', 'clears', 'evidence', 'refs'):
                self.assertTrue(r.get(key), (r['id'], key))

    def test_every_row_cites_a_registered_source(self):
        from build import SOURCES
        for r in self.rows:
            for ref in r['refs']:
                self.assertIn(ref, SOURCES, (r['id'], ref))

    def test_no_validated_strategy_claim(self):
        self.assertNotIn('validated strategy: yes', json.dumps(self.rows).lower())

    def test_r20_matches_official_designation_counts(self):
        r20 = next(r for r in self.rows if r['id'] == 'R20')
        self.assertEqual(r20['state'], 'Built')
        self.assertIn('SEA 4 and CIN 4', r20['clears'])


class WeekTenRecheck(unittest.TestCase):
    def setUp(self):
        self.rc = json.loads((DATA / 'week10-recheck.json').read_text(encoding='utf-8'))

    def test_official_totals_are_internally_consistent(self):
        teams = self.rc['teams']
        self.assertEqual(len(teams), 28)
        out = sum(t['Out'] for t in teams)
        dbt = sum(t['Doubtful'] for t in teams)
        q = sum(t['Questionable'] for t in teams)
        self.assertEqual((out, dbt, q), (70, 11, 90))
        self.assertEqual(out + dbt + q, 171)
        self.assertEqual(self.rc['official_totals']['designated'], 171)

    def test_sea_and_cin_designation_counts(self):
        by = {t['club']: t for t in self.rc['teams']}
        self.assertEqual(by['SEA']['Out'] + by['SEA']['Doubtful'] + by['SEA']['Questionable'], 4)
        self.assertEqual(by['CIN']['Out'] + by['CIN']['Doubtful'] + by['CIN']['Questionable'], 4)

    def test_snapshot_differences_are_exactly_the_flagged_ones(self):
        from build import INJ
        snap = Counter(r[0] for r in INJ)
        diffs = {}
        for t in self.rc['teams']:
            off = t['Out'] + t['Doubtful'] + t['Questionable']
            if off - snap.get(t['club'], 0):
                diffs[t['club']] = off - snap.get(t['club'], 0)
        self.assertEqual(diffs, {'BAL': 2, 'LAC': 10, 'IND': -1})
        self.assertEqual(len(INJ), 160)

    def test_no_player_names_in_recheck_register(self):
        raw = (DATA / 'week10-recheck.json').read_text(encoding='utf-8')
        for name in ('Lucas Patrick', 'Arden Key', 'Jacob Hummel', 'Brenen Thompson', 'Kerby Joseph'):
            self.assertNotIn(name, raw)


class PublishedPages(unittest.TestCase):
    def setUp(self):
        self.page = (ROOT / 'session-9136b4d8' / 'readiness.html').read_text(encoding='utf-8')

    def test_readiness_page_is_written_with_recheck_section(self):
        self.assertIn('Decision readiness', self.page)
        self.assertIn('Week 10 recheck', self.page)
        self.assertIn('https://www.nfl.com/injuries/', self.page)

    def test_readiness_page_has_no_guessed_game_links(self):
        self.assertNotIn('nfl.com/games/', self.page)

    def test_flags_f58_to_f70_are_published(self):
        html = (ROOT / 'flags.html').read_text(encoding='utf-8')
        for n in range(58, 71):
            self.assertIn(f'>F{n}<', html, f'F{n} missing')

    def test_shared_outputs_untouched(self):
        self.assertIn('Arden Key', (ROOT / 'injuries.html').read_text(encoding='utf-8'))
        self.assertNotIn('readiness.html', (ROOT / 'index.html').read_text(encoding='utf-8'))
        self.assertFalse((ROOT / 'readiness.html').exists())


if __name__ == '__main__':
    unittest.main()
