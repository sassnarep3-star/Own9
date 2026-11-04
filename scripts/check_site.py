"""Check generated HTML, local targets/fragments and row-level source links.

External page contents are NOT reverified by this offline checker.
"""
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'site'

class Page(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.path, self.ids, self.links, self.rows, self.errors = path, set(), [], [], []
        self.row = None
        self.in_tbody = False
        self.title = False
        self.lang = False
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'html': self.lang = attrs.get('lang') == 'en'
        if tag == 'title': self.title = True
        if 'id' in attrs:
            if attrs['id'] in self.ids: self.errors.append('duplicate ID ' + attrs['id'])
            self.ids.add(attrs['id'])
        if tag == 'tbody': self.in_tbody = True
        if tag == 'tr' and self.in_tbody: self.row = []
        for name in ('href', 'src'):
            if name in attrs: self.links.append(attrs[name])
        if tag == 'a' and self.row is not None: self.row.append(attrs.get('href',''))
    def handle_endtag(self, tag):
        if tag == 'tr' and self.row is not None:
            self.rows.append(self.row)
            self.row = None
        if tag == 'tbody': self.in_tbody = False


def check():
    catalog = json.loads((SITE / 'data/catalog.json').read_text())
    official = {s['url'] for s in catalog['sources']}
    pages = {}
    for path in SITE.glob('*.html'):
        p = Page(path)
        p.feed(path.read_text())
        pages[path.resolve()] = p
    errors, count, link_count = [], 0, 0
    for path, p in pages.items():
        errors.extend(f'{path.name}: {err}' for err in p.errors)
        if not p.title or not p.lang: errors.append(f'{path.name}: title or language missing')
        for row in p.rows:
            count += 1
            if not any(url in official for url in row):
                errors.append(f'{path.name}: data row missing direct registered official-source link')
        for href in p.links:
            link_count += 1
            url = urlsplit(href)
            if url.scheme in ('https', 'http', 'mailto'): continue
            if url.scheme or url.netloc:
                errors.append(f'{path.name}: unexpected link scheme {href}')
                continue
            target = (path.parent / unquote(url.path)).resolve() if url.path else path
            if not target.is_relative_to(ROOT.resolve()) or not target.is_file():
                errors.append(f'{path.name}: missing or escaping local target {href}')
            elif url.fragment and target in pages and unquote(url.fragment) not in pages[target].ids:
                errors.append(f'{path.name}: unknown local fragment {href}')
    for css in (SITE/'assets').glob('*.css'):
        if 'http://' in css.read_text() or 'https://' in css.read_text():
            errors.append(f'{css.name}: unexpected external CSS dependency')
    if errors:
        raise SystemExit('\n'.join(errors))
    print(f'PASS: {len(pages)} pages, {count} data rows with direct official-source links, {link_count} HTML links/resources checked; no broken local targets or fragments.')
    print('Scope: external content/status is not checked by this offline test.')
    return len(pages),count

if __name__ == '__main__': check()
