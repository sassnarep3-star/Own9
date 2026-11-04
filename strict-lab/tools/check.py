"""Offline structural verification, not semantic verification of external facts."""
import csv
import json
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, unquote

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {'www.nfl.com', 'docs.scipy.org', 'scikit-learn.org', 'www.statsmodels.org',
           'sportsbook.draftkings.com', 'www.itl.nist.gov',
           'www.gamblingcommission.gov.uk', 'docs.github.com'}


class Check(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links=[]; self.ids=set(); self.inrow=False; self.row_data=False
        self.row_sources=[]; self.all_row_sources=[]; self.rows=0; self.errors=[]; self.empty_cells=0
        self.current_cell=None; self.cell_text=''; self.in_td=False
        self.lang=False; self.has_title=False; self.has_main=False

    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=='html': self.lang=a.get('lang')=='en'
        if tag=='title': self.has_title=True
        if tag=='main': self.has_main=True
        if 'id' in a:
            if a['id'] in self.ids: self.errors.append('duplicate ID: '+a['id'])
            self.ids.add(a['id'])
        for key in ('href','src'):
            if key in a: self.links.append(a[key])
        if tag=='tr': self.inrow=True; self.row_data=False; self.row_sources=[]
        if tag=='td':
            self.row_data=True; self.in_td=True; self.current_cell=a; self.cell_text=''
        if tag=='a' and self.inrow and 'source-link' in a.get('class','').split():
            self.row_sources.append(a.get('href',''))
            self.all_row_sources.append(a.get('href',''))

    def handle_data(self, data):
        if self.in_td: self.cell_text += data

    def handle_endtag(self, tag):
        if tag=='td':
            if not self.cell_text.strip():
                self.empty_cells+=1
                if self.current_cell.get('aria-label')!='Unverified; value withheld':
                    self.errors.append('blank value missing explicit unverified label')
            self.in_td=False
        if tag=='tr':
            if self.row_data:
                self.rows+=1
                if not self.row_sources: self.errors.append('table row missing scoped official citation')
            self.inrow=False


def check_all():
    errors=[]
    cat=json.loads((ROOT/'research/catalog.json').read_text())
    policy=json.loads((ROOT/'research/policy.json').read_text())
    report=json.loads((ROOT/'research/run.json').read_text())
    sources={s['id']:s for s in cat['sources']}
    urls={s['url'] for s in sources.values()}
    if len(sources)!=len(cat['sources']): errors.append('duplicate source IDs')
    if len(urls)!=len(sources): errors.append('duplicate source URLs')
    for source in sources.values():
        parsed=urlparse(source['url'])
        if parsed.scheme!='https' or parsed.hostname not in ALLOWED:
            errors.append('unapproved official source '+source['id'])
        for k in ('title','publisher','kind','excerpt','scope','checked_at','status'):
            if not source.get(k): errors.append(f'missing source field {source["id"]}: {k}')
    for group in ('strategies','flags','requirements'):
        ids=set()
        for item in cat[group]:
            if item['id'] in ids: errors.append(f'duplicate {group} ID')
            ids.add(item['id'])
            if not item.get('sources') or any(s not in sources for s in item['sources']):
                errors.append(f'unknown source in {item["id"]}')
    # No missing observation evidence can produce a numeric measurement or rank.
    if report['records_received']==0:
        for s in report['strategies']:
            if s['eligible'] or any(s[k] is not None for k in
                    ('rank','n','log_loss','brier','roi','rho','ci_low','ci_high','reward')):
                errors.append('invented metric with no observations: '+s['id'])
            if set(s['gates'])!={g['id'] for g in policy['gates']} or any(v!='Blocked' for v in s['gates'].values()):
                errors.append('invalid gate status')
    expected={'index.html','strategies.html','methodology.html','validation.html',
              'leaderboard.html','sources.html','requirements.html','flags.html'}
    if {p.name for p in ROOT.glob('*.html')}!=expected: errors.append('unexpected/missing page')
    parsed_pages={}
    for filename in expected:
        if not (ROOT/filename).exists(): continue
        parser=Check(); parser.feed((ROOT/filename).read_text()); parsed_pages[filename]=parser
        errors.extend(f'{filename}: {err}' for err in parser.errors)
        if not (parser.lang and parser.has_title and parser.has_main): errors.append(f'{filename}: accessibility structure missing')
        for source in parser.all_row_sources:
            if source not in urls: errors.append(f'{filename}: unregistered source')
    # Reparse all row links (not just the last row) against source registry.
    for filename,parser in parsed_pages.items():
        for link in parser.links:
            parsed=urlparse(link)
            if parsed.scheme or parsed.netloc:
                if parsed.scheme!='https': errors.append(f'{filename}: non-HTTPS link {link}')
                if parsed.hostname in ALLOWED and link not in urls:
                    errors.append(f'{filename}: unregistered official link {link}')
                continue
            target=ROOT/unquote(parsed.path) if parsed.path else ROOT/filename
            if not target.resolve().is_relative_to(ROOT.parent): errors.append(f'{filename}: escaping local link')
            elif not target.is_file(): errors.append(f'{filename}: missing local asset {link}')
            if parsed.fragment and target.suffix=='.html' and target.name in parsed_pages:
                if unquote(parsed.fragment) not in parsed_pages[target.name].ids:
                    errors.append(f'{filename}: broken fragment {link}')
    csv_rows=0
    for path in (ROOT/'downloads').glob('*.csv'):
        with path.open(newline='') as f:
            rows=list(csv.DictReader(f))
        csv_rows+=len(rows)
        for row in rows:
            if not row.get('Official references') or any(url not in urls for url in row['Official references'].split(' | ')):
                errors.append(f'{path.name}: missing/unregistered CSV sources')
            if not row.get('Source coverage') or not row.get('Evidence type'):
                errors.append(f'{path.name}: missing scope/evidence')
    html_rows=sum(p.rows for p in parsed_pages.values())
    if csv_rows!=html_rows: errors.append('CSV and HTML row counts differ')
    if errors: raise SystemExit('\n'.join(errors))
    return len(parsed_pages),html_rows,sum(p.empty_cells for p in parsed_pages.values())


if __name__=='__main__':
    # Regeneration must be deterministic and match checked-in artifacts.
    paths=[*ROOT.glob('*.html'),*ROOT.glob('downloads/*'),ROOT/'research/run.json']
    original={p:p.read_bytes() for p in paths}
    subprocess.run([sys.executable,str(ROOT/'tools/run_analysis.py')],check=True,cwd=ROOT)
    subprocess.run([sys.executable,str(ROOT/'tools/build.py')],check=True,cwd=ROOT)
    changed=[str(p.relative_to(ROOT)) for p,b in original.items() if p.read_bytes()!=b]
    if changed: raise SystemExit('Stale generated artifacts: '+', '.join(changed))
    pages,rows,empty=check_all()
    print(f'PASS: {pages} pages, {rows} cited table rows, {empty} explicitly withheld cells; '
          'all local links/fragments/assets and CSVs valid; deterministic build. '
          'External facts require scoped source review, not this check.')
