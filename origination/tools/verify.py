"""Structural and claim-integrity verifier for the line-origination desk.

It checks what can be checked offline: that every published row carries a
registered source, that local links and fragments resolve, that pages are
reproducible byte for byte, and that the desk does not publish a number its own
data files contradict. It does not check external reachability, and it does not
certify that a source says what a row claims - only that the row cites one.
"""

import csv
import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

from build import DATA, PAGES, render  # noqa: E402

SOURCES = {s['id']: s for s in json.loads((DATA / 'sources.json').read_text())['sources']}
KNOWN = {s['url'] for s in SOURCES.values()}
ALLOWED_HOSTS = {urlsplit(u).hostname for u in KNOWN}


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.ids = set()
        self.rows = []
        self.errors = []
        self.row = None
        self.in_tbody = False
        self.h1 = 0
        self.main = False
        self.current = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a:
            if a['id'] in self.ids:
                self.errors.append('duplicate id: ' + a['id'])
            self.ids.add(a['id'])
        if tag == 'h1':
            self.h1 += 1
        if tag == 'main':
            self.main = True
        if a.get('aria-current') == 'page':
            self.current += 1
        if tag == 'tbody':
            self.in_tbody = True
        if tag == 'tr' and self.in_tbody:
            self.row = []
        for name in ('href', 'src'):
            if name in a:
                self.links.append(a[name])
                if self.row is not None:
                    self.row.append(a[name])

    def handle_endtag(self, tag):
        if tag == 'tr' and self.row is not None:
            self.rows.append(self.row)
            self.row = None
        if tag == 'tbody':
            self.in_tbody = False


def check_rows(page_name, page, errors):
    for index, row in enumerate(page.rows, 1):
        if not any(link in KNOWN for link in row):
            errors.append('%s: row %d has no registered source link' % (page_name, index))


def main():
    errors = []
    expected = render()
    parsed = {}
    for filename, content in expected.items():
        path = ROOT / filename
        if not path.exists():
            errors.append(filename + ': missing generated file')
            continue
        if path.read_text(encoding='utf-8') != content:
            errors.append(filename + ': stale generated file, run tools/build.py')
        page = Page()
        page.feed(path.read_text(encoding='utf-8'))
        page.close()
        parsed[filename] = page
        errors.extend('%s: %s' % (filename, m) for m in page.errors)
        if page.h1 != 1:
            errors.append(filename + ': expected exactly one h1')
        if not page.main:
            errors.append(filename + ': no main landmark')
        if page.current != 1:
            errors.append(filename + ': expected exactly one current nav item')
        if not page.rows:
            errors.append(filename + ': no data rows published')
        check_rows(filename, page, errors)

    # Navigation completeness: every page reachable, every nav target real.
    index = parsed.get('index.html')
    if index:
        for filename in expected:
            if filename != 'index.html' and filename not in index.links:
                errors.append('index.html: no link to ' + filename)

    for filename, page in parsed.items():
        for link in page.links:
            u = urlsplit(link)
            if u.scheme:
                if u.scheme != 'https':
                    errors.append('%s: non-HTTPS link %s' % (filename, link))
                elif u.hostname not in ALLOWED_HOSTS:
                    errors.append('%s: unregistered publisher host %s' % (filename, link))
                continue
            target = unquote(u.path) or filename
            path = (ROOT / target).resolve()
            # Links may reach the parent repository root (the main dashboard) but
            # nothing outside it.
            if not (path.is_relative_to(ROOT) or path.is_relative_to(REPO)) \
                    or not path.is_file():
                errors.append('%s: broken local link %s' % (filename, link))
            if u.fragment and target in parsed and unquote(u.fragment) not in parsed[target].ids:
                errors.append('%s: missing fragment %s' % (filename, link))

    errors.extend(data_integrity())
    return errors


def data_integrity():
    """Numbers published on the pages must agree with the files behind them."""
    errors = []
    report = json.loads((DATA / 'report.json').read_text())

    def read(name):
        with (DATA / name).open(newline='', encoding='utf-8') as handle:
            return list(csv.DictReader(handle))

    prices = read('prices.csv')
    originated = read('originated.csv')
    bets = read('bets.csv')
    results = read('results.csv')

    # The price store must contain exactly one row per originated market.
    if len(prices) != len(originated):
        errors.append('price store and originated file disagree on market count')
    if len(prices) != report['originations']['markets']:
        errors.append('report market count disagrees with prices.csv')

    # No opening value may ever be populated: no source provides one.
    opened = [r for r in prices if r['open_line'] or r['open_price']
              or r['open_captured_utc'] or r['open_source']]
    if opened:
        errors.append('price store has %d rows with an opening value; no source '
                      'provides one' % len(opened))

    # No capture timestamp may be populated either.
    stamped = [r for r in prices if r['close_captured_utc']]
    if stamped:
        errors.append('price store has %d rows with a capture timestamp; the snapshot '
                      'records none' % len(stamped))

    # Every market must be in the required origination order.
    by_game = {}
    for r in originated:
        by_game.setdefault(r['game_id'], []).append(r)
    for game_id, rows in by_game.items():
        order = [r['market'] for r in sorted(rows, key=lambda x: int(x['origination_order']))]
        if order != ['SIDE', 'TOTAL', 'MONEYLINE']:
            errors.append('%s: origination order is %s' % (game_id, order))
            break

    # The results feed must agree with the scores it was built from.
    for r in results:
        if r['result_matches_recompute'] != 'True' or r['total_matches_recompute'] != 'True':
            errors.append('results feed row %s failed its own recomputation' % r['game_id'])
            break

    # Bet counts by strategy must match the published signal block.
    taken = {}
    for b in bets:
        if float(b['stake']) > 0:
            taken[b['strategy']] = taken.get(b['strategy'], 0) + 1
    for code, block in report['strategies'].items():
        if code in ('P-PROP', 'S-SGP'):
            continue
        published = block.get('taken', 0)
        if taken.get(code, 0) != published:
            errors.append('%s: bets.csv has %d taken bets, report says %d'
                          % (code, taken.get(code, 0), published))

    # No correlation may be published without an n.
    corr = report['correlations']
    for key in ('margin_total_error', 'cover_over_phi'):
        if corr[key].get('n') in (None, 0):
            errors.append('correlation %s published without an n' % key)
    if corr['weekly_intraclass'] and not corr['weekly_intraclass'].get('n'):
        errors.append('intraclass correlation published without an n')

    # A refused gate must mean zero priced combinations.
    if corr['margin_total_error']['gate']['verdict'] == 'refuse' \
            and report['joint']['sgp_priced'] != 0:
        errors.append('gate refused but combinations were priced')

    return errors


if __name__ == '__main__':
    problems = main()
    if problems:
        raise SystemExit('\n'.join(problems))
    pages = render()
    rows = sum(len(Page().feed('')) if False else 0 for _ in ())
    total = 0
    for filename in pages:
        p = Page()
        p.feed((ROOT / filename).read_text(encoding='utf-8'))
        p.close()
        total += len(p.rows)
    print('PASS: %d pages; %d source-linked rows; local assets/fragments; '
          'origination order; blank-by-policy openings; data integrity.'
          % (len(pages), total))
    print('Scope: structural and internal-consistency checks only. Not external '
          'reachability or factual entailment.')
