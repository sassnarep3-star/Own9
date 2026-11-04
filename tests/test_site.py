import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from verify import Page, check

class SiteVerification(unittest.TestCase):
    def test_site(self):
        errors,rows=check()
        self.assertEqual(errors,[])
        self.assertEqual(rows,76)
    def test_parser(self):
        p=Page();p.feed('<main id="x"><h1>Title</h1><table><tr><td>A</td><td><a href="https://example.com">Ref</a></td></tr></table></main>')
        self.assertTrue(p.main)
        self.assertEqual(len(p.rows),1)
        self.assertEqual(p.rows[0]['links'],['https://example.com'])
        p.feed('<p id="x">Duplicate</p>')
        self.assertTrue(p.errors)
