"""Structural verification only, never a truth/claim-entailment checker."""
import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
from build import ROOT, render

class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links=[]; self.ids=set(); self.errors=[]; self.row=None; self.rows=[]
        self.current=0; self.main=False; self.h1=0
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if 'id' in a:
            if a['id'] in self.ids: self.errors.append('duplicate id: '+a['id'])
            self.ids.add(a['id'])
        if tag=='main': self.main=True
        if tag=='h1': self.h1+=1
        if a.get('aria-current')=='page': self.current+=1
        if tag=='tr': self.row={'data':False,'links':[],'cells':[]}
        if self.row is not None and tag in ('td','th'):
            if tag=='td': self.row['data']=True
            self.row['cells'].append('')
        for attr in ('href','src'):
            if attr in a:
                self.links.append(a[attr])
                if self.row is not None: self.row['links'].append(a[attr])
    def handle_data(self, data):
        if self.row is not None and self.row['cells']: self.row['cells'][-1]+=data
    def handle_endtag(self, tag):
        if tag=='tr' and self.row is not None:
            if self.row['data']: self.rows.append(self.row)
            self.row=None

def check():
    errors=[]; parsed={}; expected=render()
    manifest=json.loads((ROOT/'evidence/sources.json').read_text())
    known={s['url'] for s in manifest}
    allowed={'docs.github.com','docs.scipy.org','github.com','media.nfl.com','operations.nfl.com','scikit-learn.org','sportsbook.draftkings.com','static.www.nfl.com','wsgc.wa.gov','www.chiefs.com','www.detroitlions.com','www.itl.nist.gov','www.nfl.com','www.patriots.com','www.seahawks.com','www.statsmodels.org'}
    if len({s['id'] for s in manifest}) != len(manifest): errors.append('duplicate source id')
    for s in manifest:
        if urlsplit(s['url']).scheme!='https' or urlsplit(s['url']).hostname not in allowed:
            errors.append('unapproved publisher URL: '+s['url'])
        if s['status'] not in ('retrieved','inspected') or not all(s.get(k) for k in ('checked','supports','scope')):
            errors.append('incomplete evidence entry '+s['id'])
    actual={p.name for p in ROOT.glob('*.html')}
    if actual != set(expected): errors.append('HTML page set differs from generator')
    for filename,content in expected.items():
        p=ROOT/filename
        if not p.exists() or p.read_text()!=content: errors.append(filename+': stale generated file')
        if not p.exists(): continue
        parser=Page();parser.feed(p.read_text());parser.close();parsed[filename]=parser
        errors.extend(filename+': '+msg for msg in parser.errors)
        if not parser.main or parser.h1!=1 or parser.current!=1: errors.append(filename+': landmark/title/current-nav error')
        for i,row in enumerate(parser.rows,1):
            if not any(link in known for link in row['links']): errors.append(f'{filename}: row {i} has no registered publisher reference')
        if filename=='leaderboard.html':
            # Two tables: signal metrics (6 data cols + evidence) and staking metrics (6 data cols + evidence).
            # First 4 rows are signal table; next 4 are staking table.
            # Signal table: Track(0), Eligibility(1), Log-loss gain LCB(2), Brier(3), Calibration(4), Coverage(5), Evidence(6).
            for row in parser.rows[:4]:
                if any(cell.strip() for cell in row['cells'][2:6]): errors.append('invented leaderboard signal metric')
            # Staking table: Track(0), Net-return LCB(1), Max drawdown(2), Win rate(3), ROI(4), Turnover(5), Evidence(6).
            for row in parser.rows[4:8]:
                if any(cell.strip() for cell in row['cells'][1:6]): errors.append('invented leaderboard staking metric')
        if filename=='correlations.html':
            for row in parser.rows[:5]:
                if any(cell.strip() for cell in row['cells'][2:5]): errors.append('invented NFL correlation metric')
        if filename=='availability.html':
            # The NFL publishes no depth tier, so no row may render one.
            banned = ('1st string','2nd string','3rd string','4th string',
                      'second string','third string','fourth string')
            tiers = [c.strip() for r in parser.rows for c in r['cells']
                     if c.strip().lower() in banned]
            if tiers:
                errors.append('availability: an invented depth tier was rendered: '+', '.join(tiers))
        if filename=='suggestions.html':
            for r in parser.rows:
                cells = [c.strip() for c in r['cells']]
                if len(cells) >= 7 and ('S-' in cells[0]):
                    if not cells[5]:
                        errors.append('suggestions: a row has no falsification statement')
        if filename=='questions.html':
            for r in parser.rows:
                cells = [c.strip() for c in r['cells']]
                if len(cells) >= 6 and cells[0].startswith('Q-'):
                    answered = cells[5] == 'Answered'
                    if not answered and cells[3]:
                        errors.append('questions: an unanswered row rendered an answer')
                    if answered and not cells[3]:
                        errors.append('questions: an answered row rendered no answer')
        if filename=='decision.html':
            for r in parser.rows:
                cells = [c.strip() for c in r['cells']]
                if len(cells) >= 7 and cells[0].startswith('D-'):
                    if not cells[4]:
                        errors.append('decision: a row has no stopping rule')
    for filename,parser in parsed.items():
        for link in parser.links:
            u=urlsplit(link)
            if u.scheme:
                if u.scheme!='https': errors.append(filename+': non-HTTPS link '+link)
                continue # external references were read manually, not checked here
            target=unquote(u.path) or filename
            path=(ROOT/target).resolve()
            if not path.is_relative_to(ROOT) or not path.is_file(): errors.append(filename+': broken asset/link '+link)
            if u.fragment and target in parsed and unquote(u.fragment) not in parsed[target].ids:
                errors.append(filename+': missing fragment '+link)
    return errors, sum(len(p.rows) for p in parsed.values())

if __name__=='__main__':
    errors,rows=check()
    if errors: sys.exit('\n'.join(errors))
    print(f'PASS: {len(render())} fresh pages; {rows} source-linked rows; local assets/fragments; nav landmarks; empirical blanks.')
    print('Scope: structural checks only. Not external reachability or factual claim certification.')
