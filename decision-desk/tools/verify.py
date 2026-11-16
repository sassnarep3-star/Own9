"""Verify the decision-desk pages against the committed data.

The verifier is the drift alarm for this desk (requirement R63). It is pinned to
expected row counts and required fields, and it fails loudly rather than publishing a
blank. Exit code 0 means every check passed.

    python3 decision-desk/tools/verify.py
"""
from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
PAGES = ['index.html', 'requirements.html', 'questions.html', 'suggestions.html',
         'availability.html', 'fixtures.html', 'captures.html', 'sources.html',
         'flagged.html']

EXPECTED_REQUIREMENTS = 73
EXPECTED_FLAGS = 14
MIN_INJURY_ROWS = 300
EXPECTED_REPORT_CLUBS = 28

FAILURES: list[str] = []
CHECKS = 0


def check(condition: bool, message: str) -> bool:
    global CHECKS
    CHECKS += 1
    if not condition:
        FAILURES.append(message)
        print(f'FAIL  {message}')
    return condition


class Page(HTMLParser):
    """Collects links, ids, headings and table rows from one page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.fragments: list[str] = []
        self.ids: list[str] = []
        self.tables = 0
        self.rows = 0
        self.headings: list[str] = []
        self._in_row = False
        self._capture: str | None = None
        self._text = ''
        self.script_depth = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'a':
            href = a.get('href', '')
            if href:
                if href.startswith('#'):
                    self.fragments.append(href[1:])
                else:
                    self.links.append(href)
        if tag == 'script':
            self.script_depth += 1
        if 'id' in a:
            self.ids.append(a['id'])
        if tag == 'table':
            self.tables += 1
        if tag == 'tr':
            self._in_row = True
        if tag in ('h1', 'h2'):
            self._capture = tag
            self._text = ''

    def handle_endtag(self, tag):
        if tag == 'script' and self.script_depth:
            self.script_depth -= 1
        if tag == 'tr':
            self._in_row = False
        if tag in ('h1', 'h2') and self._capture == tag:
            self.headings.append(self._text.strip())
            self._capture = None

    def handle_data(self, data):
        if self._capture:
            self._text += data
        if self._in_row:
            self.rows += 1


def load(name):
    return json.loads((DATA / name).read_text())


def main() -> int:
    print('== data integrity ==')

    reqs = load('requirements.json')
    check(len(reqs) == EXPECTED_REQUIREMENTS,
          f'requirements.json has {len(reqs)} rows, expected {EXPECTED_REQUIREMENTS}')
    for r in reqs:
        check(bool(r.get('gate')), f"{r['id']} has no blocking gate")
        check(bool(r.get('clearing_number')), f"{r['id']} has no clearing number")
        check(bool(r.get('evidence')), f"{r['id']} has no evidence link")
        check(r['status'] in ('met', 'partial', 'not-started', 'rejected', 'blocked'),
              f"{r['id']} has an unrecognised status {r['status']!r}")
    ids = [r['id'] for r in reqs]
    check(len(set(ids)) == len(ids), 'requirement ids are not unique')

    flags = load('flags.json')
    check(len(flags) == EXPECTED_FLAGS, f'flags.json has {len(flags)} rows, expected {EXPECTED_FLAGS}')
    for f in flags:
        check(bool(f.get('evidence')), f"{f['id']} has no evidence link")

    q = load('questions.json')
    check(len(q['answered']) >= 1, 'no answered questions')
    check(len(q['open_data']) >= 1, 'no open data questions')
    check(len(q['owner_decisions']) >= 1, 'no owner decisions')
    check(len(q['probes']) >= 1, 'no probes')
    check(len(q['have']) >= 1, 'no have-items')
    check(len(q['have_not']) >= 1, 'no have-not items')
    for item in q['answered']:
        check(bool(item.get('evidence')), f"{item['id']} has no evidence link")

    s = load('suggestions.json')
    check(len(s['suggestions']) >= 1, 'no suggestions')
    check(len(s['paths']) >= 2, 'fewer than two candidate paths')
    implemented = [x for x in s['suggestions'] if x['status'].lower().startswith('implemented')]
    check(not implemented,
          f'suggestions marked implemented must not exist on a review board: {[x["id"] for x in implemented]}')
    chosen = [p for p in s['paths'] if 'chosen' in p['name'].lower()]
    check(not chosen, 'a candidate path is marked chosen')

    # The capture: pinned row counts and required fields. This is the drift alarm.
    parsed = json.loads((DATA / 'parsed' / 'injury_captures.json').read_text())
    key = sorted(parsed)[0]
    rows = parsed[key]['rows']
    check(len(rows) >= MIN_INJURY_ROWS,
          f'injury capture parsed {len(rows)} rows, below the pinned floor of {MIN_INJURY_ROWS}')
    check(len(parsed[key]['teams_published']) == EXPECTED_REPORT_CLUBS,
          f"capture parsed {len(parsed[key]['teams_published'])} clubs, expected {EXPECTED_REPORT_CLUBS}")
    required = ('player', 'position', 'practice_status', 'game_status', 'team')
    for r in rows:
        for field in required:
            if field == 'game_status' or field == 'injury':
                continue  # legitimately blank on the official page
            if not r.get(field):
                FAILURES.append(f'a capture row is missing the required field {field!r}')
                print(f'FAIL  capture row missing required field {field!r}: {r}')
                break
        if r['practice_status'] not in ('Full Participation in Practice',
                                        'Limited Participation in Practice',
                                        'Did Not Participate In Practice'):
            FAILURES.append(f"unexpected practice status {r['practice_status']!r}")
            print(f"FAIL  unexpected practice status {r['practice_status']!r}")
        if r['game_status'] not in ('', 'Out', 'Doubtful', 'Questionable'):
            FAILURES.append(f"unexpected game status {r['game_status']!r}")
            print(f"FAIL  unexpected game status {r['game_status']!r}")

    # Fixtures and results must be internally consistent.
    w11 = load('week-11-2026-fixtures.json')
    teams = set()
    for g in w11['games']:
        teams.update((g['away'], g['home']))
    check(len(teams) == 26, f'Week 11 has {len(teams)} playing clubs, expected 26')
    check(not (teams & set(w11['bye_clubs'])), 'a club is both playing and on bye in Week 11')
    check(len(teams | set(w11['bye_clubs'])) == 32, 'Week 11 club coverage is not 32')

    w10 = load('week-10-2026-results.json')
    t10 = set()
    for g in w10['games']:
        t10.update((g['away'], g['home']))
    check(len(t10) == 28, f'Week 10 has {len(t10)} playing clubs, expected 28')
    check(not (t10 & set(w10['bye_clubs'])), 'a club is both playing and on bye in Week 10')

    print('\n== pages ==')
    pages: dict[str, Page] = {}
    for name in PAGES:
        path = ROOT / name
        if not check(path.exists(), f'{name} is missing'):
            continue
        text = path.read_text()
        check('<h1>' in text, f'{name} has no h1')
        check('assets/style.css' in text, f'{name} does not reference the stylesheet')
        check('../index.html' in text, f'{name} does not link back to the root dashboard')
        p = Page()
        p.feed(text)
        pages[name] = p
        check(p.tables >= 1, f'{name} has no tables')

    # Every page except the index must appear in the index navigation, and the
    # navigation must reach every page.
    nav_targets = set(PAGES)
    for name, p in pages.items():
        hrefs = set(p.links)
        missing = nav_targets - hrefs
        check(not missing, f'{name} navigation does not reach {sorted(missing)}')

    print('\n== links ==')
    local_assets = set()
    for name, p in pages.items():
        for href in p.links:
            if href.startswith(('http://', 'https://', 'mailto:')):
                check(href.startswith('https://'),
                      f'{name} links to a non-https url: {href}')
                continue
            if href.startswith('#'):
                continue
            target = (ROOT / href.split('#')[0]).resolve()
            check(target.exists(), f'{name} links to a missing local file: {href}')
            local_assets.add(href.split('#')[0])

    # In-page fragments must resolve on the page that uses them.
    for name, p in pages.items():
        for frag in p.fragments:
            if frag:
                check(frag in p.ids, f'{name} links to a missing fragment #{frag}')

    print('\n== source coverage ==')
    # Every table row on the data pages must carry at least one link, or an explicit
    # not-published marker. A row with neither is an unsourced claim.
    for name in ('requirements.html', 'questions.html', 'suggestions.html',
                 'availability.html', 'fixtures.html', 'flagged.html'):
        if name not in pages:
            continue
        text = (ROOT / name).read_text()
        bodies = re.findall(r'<tbody>([\s\S]*?)</tbody>', text)
        unsourced = 0
        for body in bodies:
            for tr in re.findall(r'<tr>([\s\S]*?)</tr>', body):
                if '<a ' in tr or 'class="blank"' in tr or 'class="absent"' in tr:
                    continue
                if 'class="empty"' in tr:
                    continue
                unsourced += 1
                print(f'FAIL  {name}: row with no source link and no blank marker: {tr[:160]}')
        check(unsourced == 0, f'{name} has {unsourced} rows with no source link, no blank marker and no recorded-absence marker')

    print()
    if FAILURES:
        print(f'{len(FAILURES)} of {CHECKS} checks FAILED')
        return 1
    print(f'all {CHECKS} checks passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
