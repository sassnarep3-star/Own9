from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
class Check(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]; self.inrow=False; self.row_has_td=False; self.row_source=False; self.errors=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=='tr': self.inrow=True; self.row_has_td=False; self.row_source=False
        if tag=='td' and self.inrow: self.row_has_td=True
        if tag=='a' and 'href' in a:
            self.links.append(a['href'])
            if self.inrow and urlparse(a['href']).hostname in {'www.nfl.com','www.itl.nist.gov','www.gamblingcommission.gov.uk','docs.github.com'}: self.row_source=True
    def handle_endtag(self,tag):
        if tag=='tr':
            if self.row_has_td and not self.row_source: self.errors.append('table row missing official source')
            self.inrow=False
errors=[]
for path in Path('.').glob('*.html'):
    c=Check(); c.feed(path.read_text()); errors += [f'{path}: {e}' for e in c.errors]
    for link in c.links:
        if not urlparse(link).scheme and not Path(link.split('#')[0]).exists(): errors.append(f'{path}: missing {link}')
if len(list(Path('.').glob('*.html'))) != 5: errors.append('expected five pages')
if errors: raise SystemExit('\n'.join(errors))
print('Five pages: local links and official references in all table rows OK.')
