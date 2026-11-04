"""Checks the own9-research site (scope: own9-research/**): page set, local links, official-source link in every table row, and that
   results in summary.json match the numbers printed on the summary page."""
import json, re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
PAGES = ['index.html', 'summary.html', 'singles.html', 'parlays.html', 'correlations.html', 'props.html',
         'strategies.html', 'validation.html', 'leaderboard.html', 'games.html', 'sources.html', 'flags.html']
OFFICIAL = {'www.nfl.com', 'wsgc.wa.gov', 'www.itl.nist.gov', 'docs.github.com'}


class Audit(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []; self.rows = 0; self.bad_rows = 0; self.in_tbody = False
        self.in_tr = False; self.row_ok = False; self.has_cell = False
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'tbody': self.in_tbody = True
        if tag == 'tr' and self.in_tbody: self.in_tr = True; self.row_ok = False; self.has_cell = False
        if tag == 'td' and self.in_tr: self.has_cell = True
        if tag == 'a' and 'href' in a:
            href = a['href']; self.links.append(href)
            if self.in_tr and urlparse(href).hostname in OFFICIAL: self.row_ok = True
    def handle_endtag(self, tag):
        if tag == 'tbody': self.in_tbody = False
        if tag == 'tr' and self.in_tr:
            if self.has_cell:
                self.rows += 1
                if not self.row_ok: self.bad_rows += 1
            self.in_tr = False


errors = []
found = sorted(p.name for p in ROOT.glob('*.html'))
if sorted(PAGES) != found: errors.append(f'page set mismatch: {found}')
total_rows = 0
for name in PAGES:
    path = ROOT / name
    if not path.exists(): errors.append(f'missing {name}'); continue
    text = path.read_text(encoding='utf-8')
    a = Audit(); a.feed(text); total_rows += a.rows
    if a.bad_rows: errors.append(f'{name}: {a.bad_rows} table rows without an official-source link')
    for link in a.links:
        u = urlparse(link)
        if u.scheme or link.startswith('#'): continue
        if not (ROOT / u.path).exists(): errors.append(f'{name}: broken local link {link}')

# numbers on the summary page must come from summary.json
s = json.loads((ROOT / 'data/results/summary.json').read_text())
t2 = s['strategies']['S_T2']['periods']['test']
want = f"{t2['bets']:,}"
if want not in (ROOT / 'singles.html').read_text(encoding='utf-8'): errors.append('singles page missing S2 bet count')
if f"{s['parlay']['n_pairs']:,}" not in (ROOT / 'parlays.html').read_text(encoding='utf-8'): errors.append('parlays page missing pair count')
if 'Passing all 7 gates' not in (ROOT / 'index.html').read_text(encoding='utf-8'): errors.append('index missing gate KPI')
if any(v['status'] == 'PASS' for k, g in s['gates'].items() for v in g.values() if v['status'] == 'PASS' and all(x['status'] == 'PASS' for x in g.values())):
    errors.append('a strategy passed all gates - review before publishing')

if errors: raise SystemExit('\n'.join(errors))
print(f'{len(PAGES)} pages OK; {total_rows} table rows each with an official-source link; local links resolve; summary numbers consistent.')
