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
        self.current=0; self.main=False; self.h1=0; self.caption=None; self.in_caption=False
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=='caption': self.in_caption=True; self.caption=''
        if tag=='tr': self.row={'data':False,'links':[],'cells':[],'caption':self.caption}
        if 'id' in a:
            if a['id'] in self.ids: self.errors.append('duplicate id: '+a['id'])
            self.ids.add(a['id'])
        if tag=='main': self.main=True
        if tag=='h1': self.h1+=1
        if a.get('aria-current')=='page': self.current+=1
        if self.row is not None and tag in ('td','th'):
            if tag=='td': self.row['data']=True
            self.row['cells'].append('')
        for attr in ('href','src'):
            if attr in a:
                self.links.append(a[attr])
                if self.row is not None: self.row['links'].append(a[attr])
    def handle_data(self, data):
        if self.in_caption and self.caption is not None: self.caption+=data
        if self.row is not None and self.row['cells']: self.row['cells'][-1]+=data
    def handle_endtag(self, tag):
        if tag=='caption': self.in_caption=False
        if tag=='tr' and self.row is not None:
            if self.row['data']: self.rows.append(self.row)
            self.row=None

def check():
    errors=[]; parsed={}; expected=render()
    manifest=json.loads((ROOT/'evidence/sources.json').read_text())
    known={s['url'] for s in manifest}
    # Hosts actually read by a session. www.patriots.com is admitted only as a
    # club-published substitute for a league depth chart that does not exist, and
    # only for the page whose own text declares the chart unofficial.
    allowed={'www.nfl.com','www.itl.nist.gov','docs.scipy.org','scikit-learn.org','docs.github.com','github.com',
             'www.patriots.com'}
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
            for row in parser.rows[:4]:
                if any(cell.strip() for cell in row['cells'][2:7]): errors.append('invented leaderboard metric')
        if filename=='correlations.html':
            for row in parser.rows[:5]:
                if any(cell.strip() for cell in row['cells'][2:5]): errors.append('invented NFL correlation metric')
        # Availability candidates must not carry a measured result: the column exists
        # so a future verified value can land in it, and it stays empty until then.
        for row in parser.rows:
            if row['caption']=='Availability signal candidates' and row['cells'][4].strip():
                errors.append('invented availability measurement: '+row['cells'][0])
            if row['caption']=='Current own-line standing' and row['cells'][1].strip() not in ('','None'):
                errors.append('own-line value asserted without a source: '+row['cells'][0])
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
