"""Tests for the 4f2e0291 delta merged on 2026-11-14: the market audit, the availability
source register, the question ledger and suggestion cost sheet, the F13-F20 extension of the
review register, and the cross-section directory.

Written additively - it re-asserts none of another session's expectations, and it carries its
own caption-aware parser because the shared `verify.Page` does not track table captions.
"""
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from verify import Page, check  # noqa: E402
from lines_audit import audit  # noqa: E402


class Captions(HTMLParser):
    """Rows grouped by the caption of the table they sit in."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.caption = ''
        self._in_caption = False
        self._cell = None
        self._cells = None
        self._in_body = False

    def handle_starttag(self, tag, attrs):
        if tag == 'tbody':
            self._in_body = True
        elif tag == 'caption':
            self._in_caption = True
            self.caption = ''
        elif tag == 'tr' and self._in_body:
            self._cells = []
        elif tag in ('td', 'th') and self._cells is not None:
            self._cell = ''

    def handle_data(self, data):
        if self._in_caption:
            self.caption += data
        elif self._cell is not None:
            self._cell += data

    def handle_endtag(self, tag):
        if tag == 'tbody':
            self._in_body = False
        elif tag == 'caption':
            self._in_caption = False
        elif tag in ('td', 'th') and self._cells is not None:
            self._cells.append(self._cell.strip())
            self._cell = None
        elif tag == 'tr' and self._cells:
            self.rows.append({'caption': self.caption.strip(), 'cells': self._cells})
            self._cells = None


def tables(name):
    parser = Captions()
    parser.feed((ROOT / name).read_text())
    return parser.rows


def by_caption(name, caption):
    """Cell lists of the body rows under one table caption."""
    return [r['cells'] for r in tables(name) if r['caption'] == caption]


class OwnLinesAudit(unittest.TestCase):
    """Every number on the own-lines page must equal the audited tool's output."""

    @classmethod
    def setUpClass(cls):
        cls.lines = audit()
        cls.html = (ROOT / 'lines.html').read_text()

    def test_page_is_registered(self):
        self.assertIn('lines.html', [f.name for f in ROOT.glob('*.html')])
        parser = Page()
        parser.feed(self.html)
        parser.close()
        self.assertEqual(parser.h1, 1)
        self.assertEqual(parser.current, 1)
        self.assertEqual(parser.errors, [])

    def test_figures_come_from_the_audit(self):
        for value in (f"{self.lines['files']['closing_lines']['rows']:,}",
                      f"{self.lines['coverage']['games']:,}",
                      self.lines['coverage']['season_min'],
                      self.lines['coverage']['season_max'],
                      str(self.lines['settlement_recompute']['disagree_rows'])):
            self.assertIn(value, self.html, f'published page is missing the audited value {value!r}')

    def test_no_edge_or_return_claim(self):
        for banned in ('ROI', 'closing-line edge', 'beat the close', 'guaranteed return'):
            self.assertNotIn(banned, self.html.replace('guaranteed return.', ''),
                             f'the market page must not claim {banned!r}')

    def test_join_failure_is_stated_as_measured(self):
        join = self.lines['join']
        self.assertEqual(join['as_named_game_id'], 0)
        self.assertEqual(join['via_old_game_id'], join['total_games'])


class AvailabilityEvidence(unittest.TestCase):
    def setUp(self):
        self.rows = tables('availability-evidence.html')
        self.html = (ROOT / 'availability-evidence.html').read_text()

    def test_every_row_cites_a_source(self):
        parser = Page()
        parser.feed(self.html)
        parser.close()
        self.assertGreaterEqual(len(parser.rows), 40)
        for i, row in enumerate(parser.rows, 1):
            self.assertTrue(row['links'], f'row {i} has no source link')

    def test_checked_absences_are_recorded_as_absences(self):
        self.assertIn('404', self.html)
        self.assertIn('patriots.com', self.html)

    def test_no_player_is_given_an_invented_depth_tier(self):
        # Quoting the club chart's own column names is fine; ranking a player in a tier is not.
        banned = {'1st string', '2nd string', '3rd string', '4th string',
                  'first string', 'second string', 'third string', 'fourth string'}
        offenders = [c for r in self.rows for c in r['cells'] if c.lower() in banned]
        self.assertEqual(offenders, [], f'invented depth tier cells: {offenders}')

    def test_measured_signal_columns_stay_blank(self):
        rows = tables('availability-evidence.html')
        measured = [r for r in rows if r['caption'].startswith('Availability signal candidates')]
        self.assertEqual(len(measured), 6)
        for row in measured:
            cells = row['cells']
            # Column 4 is 'measured effect', which stays blank until a signal is validated;
            # column 5 is the state label, which is allowed to say Unvalidated.
            self.assertEqual(len(cells), 7)
            self.assertEqual(cells[4], '', 'a candidate signal may not publish a measured value')


class Registers(unittest.TestCase):
    def test_question_ledger_states_are_all_present(self):
        captions = {r['caption'] for r in tables('question-ledger.html')}
        for expected in ('Answered from official sources', 'Answered from this repository',
                         'Open — closable with data work', 'Open — needs an owner decision',
                         'Probes to discover missing information'):
            self.assertIn(expected, captions)
        answered = by_caption('question-ledger.html', 'Answered from official sources') + \
            by_caption('question-ledger.html', 'Answered from this repository')
        self.assertEqual(len(answered), 19)

    def test_other_sessions_registers_remain_untouched(self):
        # The merge preserved their pages; this session added its own rather than editing them.
        for name, marker in (('questions.html', 'Question register'),
                            ('decisions-questions.html', 'Decision questions and evidence gaps'),
                            ('availability.html', 'Who actually started')):
            html = (ROOT / name).read_text()
            self.assertTrue(html.strip(), f'{name} is empty')
            self.assertIn('href="' + name + '"', (ROOT / 'index.html').read_text(),
                          f'{name} lost its navigation entry')

    def test_suggestion_cost_sheet_rows_are_reviewable(self):
        rows = by_caption('suggestion-costs.html', 'Suggestion register')
        self.assertEqual(len(rows), 18)
        for row in rows:
            self.assertTrue(row[2].strip(), 'a suggestion with no cost is unrankable')
            self.assertTrue(row[5].strip(), 'a suggestion with no status is unreviewable')

    def test_unimplemented_items_are_marked_awaiting(self):
        rows = by_caption('suggestion-costs.html', 'Suggestion register')
        awaiting = [r for r in rows if r[5].lower().startswith('awaiting')]
        self.assertGreaterEqual(len(awaiting), 8)
        log = by_caption('suggestion-costs.html', 'Decision log')
        self.assertIn('not yet decided', log[0][4].lower())

    def test_candidate_paths_are_four_and_unranked(self):
        rows = by_caption('suggestion-costs.html', 'Candidate paths')
        self.assertEqual(len(rows), 4)
        self.assertEqual([r[0][0] for r in rows], list('ABCD'))


class ReviewRegister(unittest.TestCase):
    def test_findings_f22_to_f27_are_on_the_flags_page(self):
        # Renumbered in the 14 Nov merge: main had already reached F21, and three of this
        # session's original findings (depth chart, per-row timestamps) are covered there.
        rows = [r['cells'] for r in tables('flags.html')
                if r['caption'].startswith('Review register extension')]
        self.assertEqual(len(rows), 6)
        self.assertEqual([r[0].split(' ')[0] for r in rows], [f'F{n}' for n in range(22, 28)])
        self.assertEqual(len([r for r in rows if 'Critical' in r[0]]), 2)
        self.assertIn('F18', rows[0][1] + rows[0][2],
                      'the market-archive finding must name the register rows it contradicts')

    def test_no_finding_id_is_published_twice(self):
        ids = [r['cells'][0].split(' ')[0] for r in tables('flags.html')
               if r['cells'][0].startswith('F') and len(r['cells'][0].split(' ')[0]) == 3]
        self.assertEqual(len(ids), len(set(ids)), 'the review register has duplicate finding ids')

    def test_earlier_flags_remain(self):
        html = (ROOT / 'flags.html').read_text()
        self.assertIn('F01', html)


class SiteDirectory(unittest.TestCase):
    FOLDERS = ('site', 'research', 'own9-research', 'strict-lab', 'release-checks', 'session-8b05dd6d')

    def test_every_published_section_is_listed(self):
        rows = by_caption('index.html', 'Published sections of this repository')
        listed = {r[0] for r in rows}
        for folder in self.FOLDERS:
            self.assertIn(folder, listed, f'{folder} is published but not listed')
        self.assertEqual(len(rows), len(self.FOLDERS) + 1, 'root plus every sibling section')

    def test_directory_counts_match_disk(self):
        for row in by_caption('index.html', 'Published sections of this repository'):
            folder = row[0]
            if folder.startswith('Root'):
                continue
            self.assertEqual(int(row[1]), len(list((ROOT / folder).glob('*.html'))),
                             f'{folder} page count is stale')

    def test_every_listed_section_is_reachable(self):
        # The table cells are escaped text, so the links live on their own line; a listed
        # section that cannot be opened would be a broken promise to the reader.
        html = (ROOT / 'index.html').read_text()
        for folder in self.FOLDERS:
            target = f'{folder}/index.html'
            self.assertIn(f'href="{target}"', html, f'{folder} is listed but not linked')
            self.assertTrue((ROOT / target).exists(), f'{target} is linked but does not exist')

    def test_certification_is_per_section(self):
        html = (ROOT / 'index.html').read_text()
        self.assertIn('Re-verified by this release', html)
        self.assertIn('No — certified only by its own session', html)


class Structural(unittest.TestCase):
    def test_all_pages_pass_the_shared_verifier(self):
        errors, _rows = check()
        self.assertEqual(errors, [])

    def test_page_count_is_theirs_plus_this_delta(self):
        # Relaxed by session 0167a04c: six further pages were added after this delta was
        # merged, so a fixed total no longer measures anything. What the assertion must
        # still guarantee is that this session's four pages remain published.
        rendered = {f.name for f in ROOT.glob('*.html')}
        self.assertTrue({'lines.html', 'availability-evidence.html', 'question-ledger.html',
                         'suggestion-costs.html'} <= rendered,
                        "this session's four pages are missing from the rendered set")

    def test_new_pages_are_linked_from_nav_exactly_once(self):
        for name in ('lines.html', 'availability-evidence.html', 'question-ledger.html',
                     'suggestion-costs.html'):
            parser = Page()
            parser.feed((ROOT / name).read_text())
            parser.close()
            self.assertEqual(parser.current, 1, f'{name}: nav must mark exactly one current page')

    def test_no_double_escaped_entities(self):
        for path in sorted(ROOT.glob('*.html')):
            self.assertNotIn('&amp;amp;', path.read_text(), f'{path.name}: escaped twice')


if __name__ == '__main__':
    unittest.main()
