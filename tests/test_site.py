import json
import sys
import unittest
from html.parser import HTMLParser
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

    def test_suggestions_page_is_decision_ready_and_source_linked(self):
        root=Path(__file__).resolve().parents[1]
        page=root/'site'/'suggestions.html'
        self.assertTrue(page.is_file(), 'run scripts/build_site.py before testing')
        catalog=json.loads((root/'site'/'data'/'catalog.json').read_text())
        official={source['url'] for source in catalog['sources']}

        class Rows(HTMLParser):
            def __init__(self):
                super().__init__(); self.rows=[]; self.row=None; self.links=[]; self.in_cell=False
            def handle_starttag(self,tag,attrs):
                attrs=dict(attrs)
                if tag=='tr': self.row={'text':'','links':[]}
                elif tag=='td' and self.row is not None: self.in_cell=True
                elif tag=='a' and self.row is not None: self.row['links'].append(attrs.get('href',''))
            def handle_data(self,data):
                if self.row is not None: self.row['text']+=' '+data
            def handle_endtag(self,tag):
                if tag=='td': self.in_cell=False
                elif tag=='tr' and self.row is not None:
                    if self.row['text'].strip(): self.rows.append(self.row)
                    self.row=None

        parsed=Rows(); parsed.feed(page.read_text())
        data_rows=[row for row in parsed.rows if any(f'D{i:02}' in row['text'] for i in range(1,11))]
        self.assertEqual(len(data_rows),10)
        for row in data_rows:
            self.assertTrue(any(link in official for link in row['links']), row['text'])
            self.assertIn('proposed',row['text'])
            self.assertIn('decision pending',row['text'])
        full=page.read_text().lower()
        for phrase in ('what is missing','how to discover','second-','third-','fourth-string',
                       'correlation','alternatives','not prove a suggested strategy works'):
            self.assertIn(phrase,full)
        self.assertIn('suggestions.html', (root/'site'/'index.html').read_text())
