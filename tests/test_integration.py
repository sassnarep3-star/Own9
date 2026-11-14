"""Regression tests for the 2026-11-14 integration release.

These check that the published pages stay faithful to the committed data and to
the official sources, and that withheld values stay withheld. They do not and
cannot certify an NFL edge, external link reachability or the correctness of a
third-party dataset.
"""
import csv
import sys
import unittest
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

from lines_audit import audit  # noqa: E402
from verify import Page, check  # noqa: E402


def parse(name):
    parser = Page()
    text = (ROOT / name).read_text()
    parser.feed(text)
    parser.close()
    return parser, text


class GeneratedSite(unittest.TestCase):
    def test_structural_pass_and_row_count(self):
        errors, rows = check()
        self.assertEqual(errors, [])
        self.assertEqual(rows, 307)

    def test_thirteen_category_pages(self):
        parser, _ = parse('index.html')
        # The brand mark repeats index.html ahead of the nav element, so drop it.
        nav = [link for link in parser.links if link.endswith('.html')][1:]
        for expected in ('injuries.html', 'lines.html', 'questions.html', 'suggestions.html'):
            self.assertIn(expected, nav, f'{expected} missing from the shared navigation')
        self.assertEqual(nav[:4], ['index.html', 'strategies.html', 'lines.html', 'injuries.html'],
                         'navigation must lead with the decision order, not insertion order')

    def test_no_manual_data_entry_anywhere(self):
        # The owner asked for no manual input: only the read-only row filter is permitted.
        for page in sorted(ROOT.glob('*.html')):
            text = page.read_text()
            self.assertNotIn('<form', text, f'{page.name} contains a form')
            self.assertNotIn('type="file"', text)
            self.assertNotIn('<textarea', text)
            self.assertNotIn('contenteditable', text)


class LinesAuditIsTruthful(unittest.TestCase):
    """The page must not drift from the file it describes."""

    def setUp(self):
        self.result = audit()

    def test_counts_recomputed_independently(self):
        with (ROOT / 'data' / 'raw' / 'closing_lines.csv').open(newline='', encoding='utf-8') as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(self.result['files']['closing_lines']['rows'], len(rows))
        self.assertEqual(self.result['coverage']['games'], len({r['game_id'] for r in rows}))
        self.assertEqual(self.result['coverage']['season_max'],
                         max(r['alt_game_id'].split('_')[0] for r in rows))
        self.assertEqual(sum(self.result['coverage']['market_types'].values()), len(rows))
        self.assertEqual(self.result['coverage']['market_types'], dict(Counter(r['type'] for r in rows)))

    def test_join_findings_are_reproducible(self):
        with (ROOT / 'data' / 'raw' / 'games.csv').open(newline='', encoding='utf-8') as handle:
            games = list(csv.DictReader(handle))
        named = {g['game_id'] for g in games}
        alternate = {g['old_game_id'] for g in games if g.get('old_game_id')}
        with (ROOT / 'data' / 'raw' / 'closing_lines.csv').open(newline='', encoding='utf-8') as handle:
            keys = {r['game_id'] for r in csv.DictReader(handle)}
        self.assertEqual(self.result['join']['as_named_game_id'], len(keys & named))
        self.assertEqual(self.result['join']['via_old_game_id'], len(keys & alternate))
        self.assertEqual(self.result['join']['as_named_game_id'], 0,
                         'the published claim that the named key does not join would be false')
        self.assertEqual(self.result['join']['via_old_game_id'], self.result['join']['total_games'])

    def test_no_claim_of_official_provenance(self):
        self.assertTrue(self.result['interpretation'][3].startswith(
            'No provenance, retrieval date or licence is recorded for the file in this repository'),
            'the audit must not claim provenance it cannot see')
        self.assertGreaterEqual(self.result['missing_fields']['odds']['SPREAD'], 1)


class AvailabilityPage(unittest.TestCase):
    def setUp(self):
        self.parser, self.text = parse('injuries.html')

    def test_transcribed_rows_cite_the_official_report(self):
        official = 'https://www.nfl.com/injuries/'
        transcribed = [r for r in self.parser.rows
                       if r['caption'] in ('Week 10 2026 report entries, transcribed',
                                           'Reserve-list moves forcing a depth promotion')]
        self.assertGreaterEqual(len(transcribed), 38)
        for row in transcribed:
            self.assertIn(official if row['caption'].startswith('Week 10')
                          else 'https://www.nfl.com/transactions/league/reserve-list/2026/11', row['links'],
                          'a transcribed row must link to the page it was copied from')

    def test_blank_cells_match_source_blanks(self):
        rows = [r for r in self.parser.rows if r['caption'] == 'Week 10 2026 report entries, transcribed']
        # Drake Maye has no listed injury and no game status on the official page.
        maye = next(r for r in rows if r['cells'][0] == 'Drake Maye')
        self.assertEqual(maye['cells'][3].strip(), '')
        self.assertEqual(maye['cells'][5].strip(), '')
        self.assertEqual(maye['cells'][4].strip(), 'Full Participation in Practice')

    def test_no_measured_availability_result_is_published(self):
        candidates = [r for r in self.parser.rows if r['caption'] == 'Availability signal candidates']
        self.assertEqual(len(candidates), 6)
        for row in candidates:
            self.assertEqual(row['cells'][4].strip(), '', f'{row["cells"][0]} carries an invented measurement')
            self.assertEqual(row['cells'][5].strip(), 'Unvalidated')

    def test_depth_chart_absence_is_stated_as_a_check_not_a_guess(self):
        self.assertIn('404', self.text)
        self.assertIn('unofficial', self.text)
        self.assertIn('https://www.nfl.com/teams/new-england-patriots/depth-chart/', self.text)


class DecisionRegisters(unittest.TestCase):
    def test_suggestions_are_all_triageable(self):
        parser, _ = parse('suggestions.html')
        register = [r for r in parser.rows if r['caption'] == 'Suggestion register']
        self.assertEqual(len(register), 18)
        allowed = ('Awaiting decision', 'Needs owner input first', 'Implemented in this release',
                   'Implemented as a directory; canonical choice pending', 'Implemented as a specification',
                   'Implemented as a limitation', 'Implemented for new pages', 'Partly implemented')
        for row in register:
            self.assertTrue(row['cells'][0].startswith('S'), 'every suggestion needs an ID')
            self.assertIn(row['cells'][5].strip(), allowed, f'{row["cells"][0]} status is not triageable')
            self.assertTrue(row['cells'][4].strip(), f'{row["cells"][0]} has no cost or risk stated')

    def test_paths_are_distinct_and_unranked(self):
        parser, _ = parse('suggestions.html')
        paths = [r for r in parser.rows if r['caption'] == 'Candidate paths']
        self.assertEqual(len(paths), 4)
        self.assertEqual([r['cells'][0][0] for r in paths], ['A', 'B', 'C', 'D'])
        for row in paths:
            self.assertTrue(row['cells'][4].strip(), f'{row["cells"][0]} must say when to choose it')

    def test_question_ledger_separates_answerable_from_open(self):
        parser, _ = parse('questions.html')
        captions = {r['caption'] for r in parser.rows}
        for expected in ('Decision questions and evidence gaps', 'Answered from official sources',
                         'Answered from this repository', 'Open — closable with data work',
                         'Open — needs an owner decision', 'Probes to discover missing information'):
            self.assertIn(expected, captions)
        official = [r for r in parser.rows if r['caption'] == 'Answered from official sources']
        self.assertGreaterEqual(len(official), 10)
        for row in official:
            self.assertTrue(any(link.startswith('https://www.nfl.com') or 'patriots.com' in link
                                for link in row['links']), f'{row["cells"][0]} has no official source link')

    def test_probes_exist_to_discover_missing_information(self):
        parser, _ = parse('questions.html')
        probes = [r for r in parser.rows if r['caption'] == 'Probes to discover missing information']
        self.assertGreaterEqual(len(probes), 7)

    def test_own_lines_page_publishes_no_backtest_result(self):
        parser, _ = parse('lines.html')
        standing = [r for r in parser.rows if r['caption'] == 'Current own-line standing']
        self.assertEqual(len(standing), 5)
        for row in standing:
            self.assertIn(row['cells'][1].strip(), ('', 'None'), 'a value here would need a verified source')


class HubAndFlags(unittest.TestCase):
    def test_directory_points_only_at_sections_that_exist(self):
        parser, _ = parse('index.html')
        rows = [r for r in parser.rows if r['caption'] == 'Site directory']
        self.assertEqual(len(rows), 7, 'every published section must appear in the directory')
        self.assertIn('session-8b05dd6d/index.html', ' '.join(r['cells'][0] for r in rows),
                      'a subtree merged after this session started must still be listed')
        for row in rows:
            entry = row['cells'][0].split(' · ')[1]
            self.assertTrue((ROOT / entry).is_file(), f'directory links to a missing page: {entry}')

    def test_new_flags_published(self):
        parser, text = parse('flags.html')
        extension = [r for r in parser.rows if r['caption'] == 'Review register extension · 14 Nov 2026']
        self.assertEqual(len(extension), 8)
        for flag in ('F13', 'F14', 'F15', 'F16', 'F17', 'F18', 'F19', 'F20'):
            self.assertIn(flag, text)

    def test_executive_summary_covers_the_new_requirements(self):
        parser, text = parse('index.html')
        for phrase in ('Injuries and depth', 'Replacements and backups', 'Originate NFL lines',
                       'Skill versus luck', 'Competition rewards', 'Recommendation'):
            self.assertIn(phrase, text)


if __name__ == '__main__':
    unittest.main()
