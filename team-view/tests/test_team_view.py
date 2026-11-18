"""Regression tests for the per-team availability view (Week 11, read 2026-11-18)."""
import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build', HERE / 'build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class TeamViewTests(unittest.TestCase):
    def setUp(self):
        self.d = build.load()

    def test_validates(self):
        build.validate(self.d)

    def test_thirty_two_clubs_and_schedule_byes(self):
        self.assertEqual(len(self.d['clubs']), 32)
        byes = {c['abbr'] for c in self.d['clubs'] if c['bye']}
        self.assertEqual(byes, {'ATL', 'CLE', 'GB', 'LAR', 'NE', 'SEA'})

    def test_club_tables_arithmetic(self):
        by = {c['abbr']: c for c in self.d['clubs']}
        ind = by['IND']
        self.assertEqual(ind['rows'], 11)
        self.assertEqual(ind['practice'], {'Did Not Participate In Practice': 8,
                                           'Limited Participation in Practice': 2,
                                           'Full Participation in Practice': 1})
        hou = by['HOU']
        self.assertEqual(hou['rows'], 15)
        self.assertEqual(hou['practice']['Did Not Participate In Practice'], 6)
        self.assertEqual(hou['practice']['Limited Participation in Practice'], 1)
        self.assertEqual(hou['practice']['Full Participation in Practice'], 8)

    def test_no_out_or_doubtful_published(self):
        for c in self.d['clubs']:
            if 'game_status' in c:
                self.assertEqual(c['game_status']['Out'], 0)
                self.assertEqual(c['game_status']['Doubtful'], 0)
                self.assertEqual(c['game_status']['blank'], c['rows'])

    def test_playing_clubs_without_table_read_no_injuries(self):
        for c in self.d['clubs']:
            if not c['bye'] and c.get('report') != 'Club table published':
                self.assertEqual(c['report'], 'No Injuries Reported', c['abbr'])

    def test_every_row_has_source_links(self):
        page = build.render(self.d)
        self.assertEqual(page.count('<tr>') - 1, 32)  # header row excluded
        self.assertEqual(page.count('href="https://www.nfl.com/teams/'), 32)
        self.assertEqual(page.count('href="https://www.nfl.com/injuries/">injury report'), 26)
        self.assertEqual(page.count('href="https://www.nfl.com/schedules/2026/REG11/">schedule'), 6)

    def test_unverified_fields_are_blank_not_zero(self):
        page = build.render(self.d)
        self.assertEqual(page.count('class="blank" aria-label="unverified"'), 64)

    def test_fail_closed_on_mismatch(self):
        bad = build.load()
        for c in bad['clubs']:
            if c.get('report') == 'Club table published':
                c['rows'] += 1
                break
        with self.assertRaises(build.ValidationError):
            build.validate(bad)

    def test_fail_closed_on_bye_mismatch(self):
        bad = build.load()
        for c in bad['clubs']:
            if c['abbr'] == 'ATL':
                c['bye'] = False
                c['report'] = 'No Injuries Reported'
        with self.assertRaises(build.ValidationError):
            build.validate(bad)

    def test_flags_include_unverified_starters(self):
        ids = {f['id'] for f in self.d['flags']}
        self.assertIn('TV-05', ids)
        self.assertIn('TV-01', ids)


if __name__ == '__main__':
    unittest.main()
