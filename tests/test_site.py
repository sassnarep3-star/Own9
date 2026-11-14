import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from verify import Page, check

class SiteVerification(unittest.TestCase):
    def test_site(self):
        errors,rows=check()
        self.assertEqual(errors,[])
        self.assertEqual(rows,90)

    def test_decision_questions_and_suggestions(self):
        root=Path(__file__).resolve().parents[1]
        html=(root/'questions.html').read_text()
        p=Page();p.feed(html);p.close()
        self.assertEqual(len(p.rows),14)
        self.assertEqual(p.current,1)
        self.assertIn('As of 14 Nov 2026 · UTC',html)
        self.assertIn('No — critical blocker',html)
        self.assertIn('second-, third- or fourth-choice replacements',html)
        self.assertIn('no manual action',html.lower())

    def test_parser(self):
        p=Page();p.feed('<main id="x"><h1>Title</h1><table><tr><td>A</td><td><a href="https://example.com">Ref</a></td></tr></table></main>')
        self.assertTrue(p.main)
        self.assertEqual(len(p.rows),1)
        self.assertEqual(p.rows[0]['links'],['https://example.com'])
        p.feed('<p id="x">Duplicate</p>')
        self.assertTrue(p.errors)
