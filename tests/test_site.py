import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path


class _TableWidths(HTMLParser):
    """Collect column-header and row widths for a single page's tables."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.tables = []
        self.current = None
        self.row_width = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'table':
            if self.depth == 0:
                self.current = {'headers': 0, 'rows': []}
            self.depth += 1
        elif self.depth and tag == 'tr':
            self.row_width = 0
        elif self.depth and tag in ('td', 'th') and self.row_width is not None:
            try:
                colspan = int(attrs.get('colspan', '1'))
            except ValueError:
                colspan = 0
            self.row_width += colspan
            if tag == 'th' and attrs.get('scope') == 'col':
                self.current['headers'] += colspan

    def handle_endtag(self, tag):
        if self.depth and tag == 'tr' and self.row_width is not None:
            self.current['rows'].append(self.row_width)
            self.row_width = None
        elif tag == 'table' and self.depth:
            self.depth -= 1
            if self.depth == 0:
                self.tables.append(self.current)
                self.current = None
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from verify import Page, check

class SiteVerification(unittest.TestCase):
    def test_every_root_page_table_row_matches_its_header_width(self):
        root = Path(__file__).resolve().parents[1]
        pages = sorted(root.glob('*.html'))
        self.assertTrue(pages, 'expected committed root dashboard HTML pages')
        failures = []
        for page in pages:
            parser = _TableWidths()
            parser.feed(page.read_text(encoding='utf-8'))
            for table_number, table in enumerate(parser.tables, 1):
                if not table['headers']:
                    failures.append(f'{page.name} table {table_number}: no column headers')
                    continue
                for row_number, width in enumerate(table['rows'], 1):
                    if width != table['headers']:
                        failures.append(
                            f'{page.name} table {table_number} row {row_number}: '
                            f"{width} cells vs {table['headers']} headers"
                        )
        self.assertEqual(failures, [], '\n'.join(failures))

    def test_site(self):
        errors,rows=check()
        self.assertEqual(errors,[])
        # Row count grows as verified evidence is added; it must never shrink silently.
        self.assertGreaterEqual(rows,458)

    def test_live_to_paper_demotion_gate_is_fail_closed_and_sourced(self):
        root=Path(__file__).resolve().parents[1]
        html=(root/'leaderboard.html').read_text()
        p=Page();p.feed(html);p.close()
        self.assertIn('Live-to-paper demotion gate',html)
        self.assertIn('Immediately stop new live issuance',html)
        self.assertIn('Missing/invalid evidence counts as not passing',html)
        self.assertIn('live activation is blocked until frozen',html)
        self.assertIn('Full requalification against all seven frozen gates',html)
        gate_rows=[r for r in p.rows if r['cells'] and r['cells'][0].startswith((
            'Integrity or operational breach:', 'Scheduled validation:', 'Re-entry after a performance demotion'))]
        self.assertEqual(len(gate_rows),3)
        self.assertTrue(all('https://github.com/sassnarep3-star/Own9' in r['links'] for r in gate_rows))
        self.assertIn('not operationally active',html)

    def test_preserved_decision_questions_page(self):
        # Session 8de532d1's page is preserved verbatim in substance on its own
        # route, because this session's questions.html is a different register.
        root=Path(__file__).resolve().parents[1]
        html=(root/'decisions-questions.html').read_text()
        p=Page();p.feed(html);p.close()
        self.assertEqual(len(p.rows),14)
        self.assertEqual(p.current,1)
        self.assertIn('As of 14 Nov 2026 · UTC',html)
        self.assertIn('No — critical blocker',html)
        self.assertIn('second-, third- or fourth-choice replacements',html)
        self.assertIn('no manual action',html.lower())
    def test_injury_snapshot_integrity(self):
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
        from build import INJ, burden_rows, SLATE
        self.assertEqual(len(INJ),160)
        self.assertEqual(len(SLATE),14)
        allowed={'Out','Doubtful','Questionable'}
        self.assertTrue(all(r[5] in allowed for r in INJ))
        self.assertEqual(len({(r[0],r[1]) for r in INJ}),len(INJ),'duplicate player rows')
        burden=burden_rows()
        self.assertEqual(len(burden),29)
        teams,total=burden[:-1],burden[-1]
        self.assertEqual(total[0],'League total')
        self.assertEqual(total[1:],(66,10,84,81,76,3,160))
        self.assertEqual(sum(t[7] for t in teams),160)
        html=(Path(__file__).resolve().parents[1]/'injuries.html').read_text()
        p=Page();p.feed(html);p.close()
        self.assertEqual(len(p.rows),226)
        self.assertIn('self-labeled',html)
        self.assertIn('F19',html)

    def test_landing_page_summary_uses_current_registers(self):
        root=Path(__file__).resolve().parents[1]
        sys.path.insert(0,str(root))
        from engine.registers import validate as validate_registers
        from build import render
        problems, counts=validate_registers()
        self.assertEqual(problems,[])
        html=render()['index.html']
        self.assertEqual((root/'index.html').read_text(),html,
                         'published landing page is stale relative to its generator')
        self.assertIn(f"{counts['decisions']} registered decisions",html)
        self.assertIn(f"{counts['questions']} questions",html)
        self.assertIn(f"{counts['suggestions']} scored, falsifiable options",html)
        self.assertIn(f"{counts['question_states']['answered']} answered",html)
        self.assertIn('Source dates are shown on each evidence page',html)
        self.assertNotIn('16 open decisions',html)
        self.assertNotIn('22 questions: answered, open, unpublished',html)

    def test_subsite_navigation_links(self):
        root=Path(__file__).resolve().parents[1]
        for sub in ('site/review.html','strict-lab/flags.html','research/flagged.html',
                    'own9-research/flags.html','release-checks/index.html','independent-audit/flags.html'):
            self.assertTrue((root/sub).is_file(),sub)
        flags=(root/'flags.html').read_text()
        for sub in ('site/review.html','strict-lab/flags.html','research/flagged.html',
                    'own9-research/flags.html','independent-audit/flags.html'):
            self.assertIn(sub,flags)

    def test_parser(self):
        p=Page();p.feed('<main id="x"><h1>Title</h1><table><tr><td>A</td><td><a href="https://example.com">Ref</a></td></tr></table></main>')
        self.assertTrue(p.main)
        self.assertEqual(len(p.rows),1)
        self.assertEqual(p.rows[0]['links'],['https://example.com'])
        p.feed('<p id="x">Duplicate</p>')
        self.assertTrue(p.errors)
