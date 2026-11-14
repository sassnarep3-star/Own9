import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from verify import Page, check

class SiteVerification(unittest.TestCase):
    def test_site(self):
        errors,rows=check()
        self.assertEqual(errors,[])
        self.assertEqual(rows,330)

    def test_decision_questions_and_suggestions(self):
        root=Path(__file__).resolve().parents[1]
        html=(root/'questions.html').read_text()
        p=Page();p.feed(html);p.close()
        self.assertEqual(len(p.rows),14)
        self.assertEqual(p.current,1)
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
        self.assertIn('F14',html)

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
