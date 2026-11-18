"""Structural checks for the public root dashboard's committed HTML tables.

The root-site verifier checks links and source rows, while the verification subsite's
unit suite covers only its own directory. Keep table geometry for every root page in
scope so a cell cannot silently shift into a neighbouring heading.
"""
from html.parser import HTMLParser
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TableWidths(HTMLParser):
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


class RootTableIntegrity(unittest.TestCase):
    def test_every_root_page_table_row_matches_its_header_width(self):
        failures = []
        pages = sorted(ROOT.glob('*.html'))
        self.assertTrue(pages, 'expected committed root dashboard HTML pages')
        for page in pages:
            parser = TableWidths()
            parser.feed(page.read_text(encoding='utf-8'))
            for table_number, table in enumerate(parser.tables, 1):
                if not table['headers']:
                    failures.append(f'{page.name} table {table_number}: no column headers')
                    continue
                for row_number, width in enumerate(table['rows'], 1):
                    if width != table['headers']:
                        failures.append(
                            f'{page.name} table {table_number} row {row_number}: '
                            f'{width} cells vs {table["headers"]} headers'
                        )
        self.assertEqual(failures, [], '\n'.join(failures))


if __name__ == '__main__':
    unittest.main()
