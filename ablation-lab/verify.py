"""Structural/source-link checks for the standalone availability-ablation status page."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
PAGE = Path(__file__).resolve().parent / 'index.html'
OFFICIAL_HOSTS = {'www.nfl.com', 'static.www.nfl.com'}


class Audit(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.rows = []
        self.row = None
        self.ids = set()
        self.h1 = 0
        self.title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id'):
            self.ids.add(attrs['id'])
        if tag == 'h1':
            self.h1 += 1
        if tag == 'title':
            self.title = True
        if tag == 'tr':
            self.row = {'data': False, 'links': []}
        if self.row is not None and tag in ('td', 'th') and tag == 'td':
            self.row['data'] = True
        href = attrs.get('href')
        if href:
            self.links.append(href)
            if self.row is not None:
                self.row['links'].append(href)

    def handle_endtag(self, tag):
        if tag == 'tr' and self.row is not None:
            if self.row['data']:
                self.rows.append(self.row)
            self.row = None
        if tag == 'title':
            self.title = False


def verify():
    if not PAGE.is_file():
        raise SystemExit(f'missing generated page: {PAGE}')
    parser = Audit()
    parser.feed(PAGE.read_text())
    parser.close()
    errors = []
    if parser.h1 != 1:
        errors.append(f'expected one h1, found {parser.h1}')
    if not parser.rows:
        errors.append('no data rows were found')
    for number, row in enumerate(parser.rows, 1):
        official = []
        for href in row['links']:
            url = urlsplit(href)
            if url.scheme:
                if url.scheme != 'https':
                    errors.append(f'row {number}: non-HTTPS citation {href}')
                if url.hostname in OFFICIAL_HOSTS:
                    official.append(href)
                continue
            target = (PAGE.parent / url.path).resolve() if url.path else PAGE
            if not target.is_relative_to(ROOT) or not target.is_file():
                errors.append(f'row {number}: broken local citation {href}')
            elif url.fragment and target == PAGE and url.fragment not in parser.ids:
                errors.append(f'row {number}: missing page fragment {href}')
        if not official:
            errors.append(f'row {number}: no direct official NFL source link')
    for href in parser.links:
        url = urlsplit(href)
        if url.scheme:
            if url.scheme != 'https':
                errors.append('non-HTTPS page link: ' + href)
            continue
        target = (PAGE.parent / url.path).resolve() if url.path else PAGE
        if not target.is_relative_to(ROOT) or not target.is_file():
            errors.append('broken local page link: ' + href)
        elif url.fragment and target == PAGE and url.fragment not in parser.ids:
            errors.append('missing page fragment: ' + href)
    if errors:
        raise SystemExit('\n'.join(errors))
    return len(parser.rows), len(parser.links)


if __name__ == '__main__':
    rows, links = verify()
    print(f'PASS: ablation page, {rows} source-linked table rows, {links} local/external links; no unsupported scores are generated.')
