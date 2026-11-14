import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from verify import Page, check

class SiteVerification(unittest.TestCase):
    def test_site(self):
        errors,rows=check()
        self.assertEqual(errors,[])
        # 306 rows: the root register plus session 8de532d1's preserved decision tables,
        # merged into questions.html and suggestions.html by the 2026-11-14 integration.
        self.assertEqual(rows,307)

    def test_decision_questions_and_suggestions(self):
        # Contributed by session arena/8de532d1-own9. Kept as written so the merged
        # pages still prove that session's content is published; only the row count
        # changed, because this release added registers around it.
        root=Path(__file__).resolve().parents[1]
        html=(root/'questions.html').read_text()
        p=Page();p.feed(html);p.close()
        self.assertEqual(len(p.rows),47)
        self.assertEqual(p.current,1)
        self.assertIn('As of 14 Nov 2026 · UTC',html)
        self.assertIn('No — critical blocker',html)
        self.assertIn('second-, third- or fourth-choice replacements',html)
        self.assertIn('no manual action',html.lower())

    def test_preserved_suggestions_table_still_published(self):
        root=Path(__file__).resolve().parents[1]
        html=(root/'suggestions.html').read_text()
        p=Page();p.feed(html);p.close()
        merged=[r for r in p.rows if r['caption']=='Improvement suggestions — review before implementation']
        self.assertEqual(len(merged),6)
        for own in ('Create a versioned source and permission register','delay awards until every gate'):
            self.assertIn(own,html)

    def test_parser(self):
        p=Page();p.feed('<main id="x"><h1>Title</h1><table><tr><td>A</td><td><a href="https://example.com">Ref</a></td></tr></table></main>')
        self.assertTrue(p.main)
        self.assertEqual(len(p.rows),1)
        self.assertEqual(p.rows[0]['links'],['https://example.com'])
        p.feed('<p id="x">Duplicate</p>')
        self.assertTrue(p.errors)
