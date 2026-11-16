#!/usr/bin/env python3
"""Decision-readiness section: validate the three registers, then render the pages.

Inputs (CSV, UTF-8, header must match exactly):
  readiness/data/requirements.csv   one row per requirement in the brief
  readiness/data/decisions.csv      owner decisions that gate requirements
  readiness/data/repo_review.csv    irregularities found in the repository review

Outputs (static HTML, no runtime dependencies):
  readiness/index.html, readiness/repo-review.html, readiness/decisions.html

Fail-closed: any rule that a row breaks stops the build with exit code 1 and a
list of the broken rows. Nothing is rendered from an invalid register.

Usage:
  python3 readiness/tools/build.py           validate, then write the pages
  python3 readiness/tools/build.py --check   validate, then fail if the pages on disk differ
"""
import csv
import html
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'readiness' / 'data'
OUT = ROOT / 'readiness'

REPO = 'https://github.com/sassnarep3-star/Own9'
TODAY_VERIFIED = '2026-11-16'   # date on which official pages were re-read for "Verified today" rows
OFFICIAL_HOSTS = {'www.nfl.com', 'nfl.com'}

REQ_COLS = ['id', 'group', 'requirement', 'status', 'what_exists', 'blocking_gate',
            'clearing_number', 'evidence', 'official_url', 'checked']
DEC_COLS = ['id', 'decision', 'options', 'default_if_no_answer', 'unlocks', 'why_it_matters']
RV_COLS = ['id', 'severity', 'finding', 'how_verified', 'evidence', 'source_url', 'disposition']

STATUSES = ['Verified today', 'Built · checked', 'Built · inputs absent', 'Partial', 'Not met',
            'Not built', 'Blocked · decision', 'Blocked · terms', 'Blocked · source',
            'Rejected as instructed', 'Open · unverified']
SEVERITIES = ['critical', 'high', 'medium', 'low']
REQ_ID = re.compile(r'^[A-H]-\d{2}$')
DEC_ID = re.compile(r'^DEC-\d{2}$')
RV_ID = re.compile(r'^RV-\d{2}$')
REF_REQ = re.compile(r'\b([A-H]-\d{2})\b')
REF_DEC = re.compile(r'\b(DEC-\d{2})\b')
ISO_DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
GENERATED = {'readiness/index.html', 'readiness/repo-review.html', 'readiness/decisions.html'}

NAV = [
    ('../index.html', 'Site home'),
    ('index.html', 'Decision readiness'),
    ('repo-review.html', 'Repo review'),
    ('decisions.html', 'Decisions'),
    ('../flags.html', 'Flagged for review'),
    ('../origination/index.html', 'Origination desk'),
    ('../suggestions.html', 'Suggestions'),
    ('../questions.html', 'Questions'),
]


# ---------------------------------------------------------------- loading and validation

def read_register(name, columns):
    path = DATA / name
    with path.open(encoding='utf-8', newline='') as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames != columns:
            raise SystemExit(f'{name}: header must be {columns}, found {reader.fieldnames}')
        rows = []
        for number, row in enumerate(reader, start=2):
            if None in row or any(v is None for v in row.values()):
                raise SystemExit(f'{name}: line {number} has the wrong number of fields')
            rows.append(row)
    return rows


def _path_problem(entry):
    """Return None if a repository path or https link is acceptable, else a reason."""
    if entry.startswith('https://'):
        host = urlparse(entry).hostname or ''
        if host in OFFICIAL_HOSTS or entry.startswith(REPO + '/'):
            return None
        return f'link host not allowed: {entry}'
    if entry in GENERATED:          # pages this script writes; they may not exist before the first build
        return None
    target = ROOT / entry
    if target.is_file() or target.is_dir():
        return None
    return f'path does not exist: {entry}'


def _split(value):
    return [part.strip() for part in value.split(';') if part.strip()]


def validate(reqs, decisions, reviews):
    """Return a list of human-readable rule violations. Empty list means valid."""
    errors = []
    dec_ids = {d['id'] for d in decisions}
    req_ids = {r['id'] for r in reqs}

    for label, rows, pattern in (('requirement', reqs, REQ_ID),
                                 ('decision', decisions, DEC_ID),
                                 ('review', reviews, RV_ID)):
        seen = set()
        for row in rows:
            rid = row['id']
            if not pattern.match(rid):
                errors.append(f'{label} id malformed: {rid!r}')
            if rid in seen:
                errors.append(f'{label} id duplicated: {rid}')
            seen.add(rid)

    for row in reqs:
        rid = row['id']
        for field in ('group', 'requirement', 'status', 'what_exists', 'blocking_gate',
                      'clearing_number', 'checked'):
            if not row[field].strip():
                errors.append(f'{rid}: {field} is blank')
        if row['status'] not in STATUSES:
            errors.append(f'{rid}: unknown status {row["status"]!r}')
        if row['checked'] and not ISO_DATE.match(row['checked']):
            errors.append(f'{rid}: checked is not an ISO date')
        else:
            try:
                date.fromisoformat(row['checked'])
            except ValueError:
                errors.append(f'{rid}: checked is not a real date')
        evidence = _split(row['evidence'])
        official = row['official_url'].strip()
        status = row['status']

        if status == 'Verified today':
            if not official:
                errors.append(f'{rid}: "Verified today" needs an official_url')
            if row['checked'] != TODAY_VERIFIED:
                errors.append(f'{rid}: "Verified today" must carry checked={TODAY_VERIFIED}')
        if status in ('Built · checked', 'Built · inputs absent') and not evidence:
            errors.append(f'{rid}: "{status}" needs at least one evidence path')
        if status == 'Blocked · decision' and 'DEC-' not in row['blocking_gate']:
            errors.append(f'{rid}: "Blocked · decision" must name a DEC- decision')
        if status == 'Blocked · terms' and 'DEC-01' not in row['blocking_gate']:
            errors.append(f'{rid}: "Blocked · terms" must name DEC-01')
        if status == 'Rejected as instructed' and (row['clearing_number'] != 'n/a'
                                                   or row['blocking_gate'] != 'n/a'):
            errors.append(f'{rid}: "Rejected as instructed" must use n/a for gate and clearing number')

        for entry in evidence:
            problem = _path_problem(entry)
            if problem:
                errors.append(f'{rid}: {problem}')
        if official:
            problem = _path_problem(official)
            if problem is not None or not official.startswith('https://'):
                errors.append(f'{rid}: official_url must be an https link on an allowed host')

        for text_field in ('requirement', 'what_exists', 'blocking_gate', 'clearing_number'):
            for ref in REF_REQ.findall(row[text_field]):
                if ref not in req_ids:
                    errors.append(f'{rid}: {text_field} cites unknown requirement {ref}')
            for ref in REF_DEC.findall(row[text_field]):
                if ref not in dec_ids:
                    errors.append(f'{rid}: {text_field} cites unknown decision {ref}')

    for row in decisions:
        did = row['id']
        for field in ('decision', 'options', 'default_if_no_answer', 'why_it_matters'):
            if not row[field].strip():
                errors.append(f'{did}: {field} is blank')
        for ref in _split(row['unlocks'].replace(',', ';')):
            if ref not in req_ids:
                errors.append(f'{did}: unlocks unknown requirement {ref}')
        for ref in REF_DEC.findall(row['why_it_matters']):
            if ref not in dec_ids:
                errors.append(f'{did}: why_it_matters cites unknown decision {ref}')

    for row in reviews:
        rid = row['id']
        if row['severity'] not in SEVERITIES:
            errors.append(f'{rid}: unknown severity {row["severity"]!r}')
        for field in ('finding', 'how_verified', 'disposition'):
            if not row[field].strip():
                errors.append(f'{rid}: {field} is blank')
        for entry in _split(row['evidence']):
            problem = _path_problem(entry)
            if problem:
                errors.append(f'{rid}: {problem}')
        if not row['source_url'].startswith('https://'):
            errors.append(f'{rid}: source_url must be https')
        else:
            problem = _path_problem(row['source_url'])
            if problem:
                errors.append(f'{rid}: {problem}')
        for ref in REF_REQ.findall(row['disposition']):
            if ref not in req_ids:
                errors.append(f'{rid}: disposition cites unknown requirement {ref}')
        for ref in REF_DEC.findall(row['disposition']):
            if ref not in dec_ids:
                errors.append(f'{rid}: disposition cites unknown decision {ref}')
    return errors


def load():
    reqs = read_register('requirements.csv', REQ_COLS)
    decisions = read_register('decisions.csv', DEC_COLS)
    reviews = read_register('repo_review.csv', RV_COLS)
    return reqs, decisions, reviews


# ---------------------------------------------------------------- rendering

def esc(value):
    return html.escape(value, quote=True)


def repo_link(entry):
    """Map a repository path (or an https link) to a clickable URL."""
    if entry.startswith('https://'):
        return entry
    target = ROOT / entry
    kind = 'tree' if target.is_dir() else 'blob'
    return f'{REPO}/{kind}/main/{entry}'


def source_cell(row):
    """Every row shows at least one source link: an official URL and/or repository evidence."""
    links = []
    if row.get('official_url', '').strip():
        url = row['official_url'].strip()
        links.append(f'<a href="{esc(url)}">Official ↗</a>')
    for entry in _split(row.get('evidence', '')):
        label = entry if len(entry) < 46 else entry[:43] + '…'
        links.append(f'<a href="{esc(repo_link(entry))}">{esc(label)} ↗</a>')
    if not links:
        links.append(f'<a href="{esc(repo_link("readiness/data/requirements.csv"))}">'
                     f'No file found in repo; register row ↗</a>')
    return '<ul class="links">' + ''.join(f'<li>{link}</li>' for link in links) + '</ul>'


def status_class(status):
    if status == 'Verified today' or status == 'Built · checked':
        return 'ok'
    if status.startswith('Built') or status == 'Partial' or status == 'Rejected as instructed':
        return 'mid'
    if status == 'Open · unverified':
        return 'warn'
    return 'bad'


def page(title, lead, body, active, date_label):
    links = []
    for href, label in NAV:
        current = ' aria-current="page"' if label == active else ''
        links.append(f'<a href="{esc(href)}"{current}>{esc(label)}</a>')
    nav = ''.join(links)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Decision readiness for the Own9 NFL research brief: one row per requirement, the gate that blocks it and the number that clears it.">
<title>{esc(title)} · Own9</title>
<link rel="stylesheet" href="style.css">
</head><body>
<a class="skip" href="#main">Skip to content</a>
<header class="top"><div class="wrap"><a class="brand" href="index.html">Own9 · NFL research</a>
<span class="pill">Research only · no wagering</span></div>
<nav class="wrap navlinks" aria-label="Section navigation">{nav}</nav></header>
<main class="wrap" id="main">
<p class="eyebrow">Decision readiness · as of {esc(date_label)} UTC</p>
<h1>{esc(title)}</h1>
<p class="lead">{lead}</p>
{body}
<p class="foot">Generated by <code>readiness/tools/build.py</code> from the CSV registers in <code>readiness/data/</code>.
Research, not betting advice. A value that could not be confirmed is left blank and flagged, never inferred.</p>
</main>
<script src="app.js" defer></script>
</body></html>
'''


def counts(reqs):
    tally = {s: 0 for s in STATUSES}
    for row in reqs:
        tally[row['status']] += 1
    return tally


def render_index(reqs, decisions, reviews):
    tally = counts(reqs)
    total = len(reqs)
    built = tally['Built · checked'] + tally['Built · inputs absent']
    blocked = tally['Blocked · decision'] + tally['Blocked · terms'] + tally['Blocked · source']
    not_done = tally['Not built'] + tally['Not met'] + tally['Partial'] + tally['Open · unverified']

    tiles = ''.join(
        f'<div class="tile {status_class(s)}"><span class="num">{tally[s]}</span>'
        f'<span class="lab">{esc(s)}</span></div>'
        for s in STATUSES if tally[s])

    summary = f'''
<section class="summary" aria-labelledby="exec">
<h2 id="exec">Executive summary</h2>
<ul>
<li><strong>{total} requirements</strong> from the brief are listed one row each. <strong>{built}</strong> are built and checked or built with inputs absent; <strong>{not_done}</strong> are partial, not built, not met or unverified; <strong>{blocked}</strong> are blocked by an owner decision, the NFL.com terms, or a missing source; <strong>{tally['Rejected as instructed']}</strong> are rejected as instructed; <strong>{tally['Verified today']}</strong> is verified today against an official page.</li>
<li><strong>No strategy has earned a stake.</strong> Every strategy's signal lower bound is negative (origination/data/strategies.json), and the desk's demotion gate demotes all three single-market strategies: G-ML and G-SIDE at bet 200 in 2010, and G-TOTAL at bet 200 in 2011 (RV-13).</li>
<li><strong>The highest-value finding is a gate failure.</strong> The cross-game parlay X-PARLAY is priced with rho = 0, which is an independence assumption, and it is shown with the best ROI in the desk. It should not be ranked. See RV-01 and decision DEC-03.</li>
<li><strong>There is no pre-registration.</strong> Strategy definitions, results and correlations were committed together in commit fe1067e, so no rule was frozen before it saw data (RV-02, DEC-04).</li>
<li><strong>Automated capture of NFL injury and depth pages is blocked.</strong> NFL.com Terms section 1.3 prohibit systematic retrieval for a database without prior written consent. This session built no scheduled capture. The owner must choose (DEC-01).</li>
<li><strong>Depth is not yet a usable input.</strong> None of the 32 clubs has a verified official depth chart in the repository. The three clubs in the data are labelled unofficial by their own pages (RV-05, DEC-06).</li>
<li><strong>One item is verified today:</strong> the three Lions designations (Joseph, Mays, Reed) match the official NFL injury report of 16 Nov 2026 (D-12). The Week 10 table counts remain unverified (D-13).</li>
<li><strong>Decisions needed:</strong> eight owner decisions (DEC-01 to DEC-08). Each one lists a default that applies if no answer is given. See the <a href="decisions.html">decisions page</a>.</li>
</ul>
</section>'''

    head_cells = ['ID', 'Requirement', 'Status', 'Blocking gate', 'Number that clears it', 'Sources']
    rows = []
    for row in reqs:
        cls = status_class(row['status'])
        what = esc(row['what_exists'])
        rows.append(
            f'<tr id="row-{esc(row["id"])}" data-status="{esc(row["status"])}" '
            f'data-search="{esc((row["id"] + " " + row["group"] + " " + row["requirement"] + " " + row["blocking_gate"]).lower())}">'
            f'<th scope="row"><span class="id">{esc(row["id"])}</span>'
            f'<span class="group">{esc(row["group"])}</span></th>'
            f'<td><p>{esc(row["requirement"])}</p>'
            f'<details><summary>What exists in the repo</summary><p>{what}</p></details></td>'
            f'<td><span class="chip {cls}">{esc(row["status"])}</span></td>'
            f'<td>{esc(row["blocking_gate"])}</td>'
            f'<td>{esc(row["clearing_number"])}</td>'
            f'<td>{source_cell(row)}</td></tr>')
    status_options = ''.join(
        f'<option value="{esc(s)}">{esc(s)}</option>' for s in STATUSES if tally[s])
    table = f'''
<section aria-labelledby="table-title">
<h2 id="table-title">Readiness register · one row per requirement</h2>
<div class="filters" role="search">
<label for="q">Find a row</label><input id="q" type="search" placeholder="Search requirement, gate or ID" autocomplete="off">
<label for="status">Status</label><select id="status"><option value="">All statuses</option>{status_options}</select>
<span id="count" role="status" aria-live="polite"></span>
</div>
<div class="tablewrap"><table class="register">
<thead><tr>{''.join(f'<th scope="col">{esc(h)}</th>' for h in head_cells)}</tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>
</section>'''

    lead = ('One row per requirement from the brief: the status, the decision or evidence that blocks it, '
            'the number that would clear it, and the source. Statuses are checked against files in this repository. '
            'No number here is an edge, a return or a forecast.')
    body = f'''
<section class="tiles" aria-label="Counts by status">{tiles}</section>
{summary}
{table}'''
    return page('Decision readiness', lead, body, 'Decision readiness', TODAY_VERIFIED)


def render_repo_review(reviews):
    rows = []
    for row in reviews:
        rows.append(
            f'<tr id="{esc(row["id"].lower())}"><th scope="row"><span class="id">{esc(row["id"])}</span></th>'
            f'<td><span class="chip sev-{esc(row["severity"])}">{esc(row["severity"])}</span></td>'
            f'<td>{esc(row["finding"])}</td><td>{esc(row["how_verified"])}</td>'
            f'<td>{esc(row["disposition"])}</td><td>{source_cell(row)}</td></tr>')
    table = f'''
<section aria-labelledby="rv">
<h2 id="rv">Irregularities for review</h2>
<p>Published for review. None of them blocks the merge of this section. Each one lists how it was checked and the link to inspect.</p>
<div class="tablewrap"><table class="register">
<thead><tr><th scope="col">ID</th><th scope="col">Severity</th><th scope="col">Finding</th><th scope="col">How it was verified</th><th scope="col">Disposition</th><th scope="col">Sources</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>
</section>
<section aria-labelledby="scope">
<h2 id="scope">What this review did not cover</h2>
<ul>
<li>Not every file has been read line by line. The repository holds several hundred files across several sub-sites. This review read the files that the brief's requirements depend on, and it lists the ones it read.</li>
<li>Full row counts of the NFL injury report were not re-verified. Doing so needs systematic retrieval, which DEC-01 must authorise first.</li>
<li>No club depth-chart page was read for any club that is not already in the repository.</li>
</ul>
</section>'''
    lead = ('Repository review: the irregularities found, how each was checked, and where to inspect it. '
            'Checked on 16 Nov 2026 UTC.')
    return page('Repo review', lead, table, 'Repo review', TODAY_VERIFIED)


def render_decisions(decisions, reqs):
    req_ids = {r['id'] for r in reqs}
    rows = []
    for row in decisions:
        unlocks = [u.strip() for u in row['unlocks'].replace(',', ';').split(';') if u.strip()]
        links = ''.join(f'<a href="index.html#row-{esc(u)}">{esc(u)}</a> ' for u in unlocks if u in req_ids)
        rows.append(
            f'<tr id="{esc(row["id"].lower())}"><th scope="row"><span class="id">{esc(row["id"])}</span></th>'
            f'<td>{esc(row["decision"])}</td><td>{esc(row["options"])}</td>'
            f'<td><strong>{esc(row["default_if_no_answer"])}</strong></td>'
            f'<td class="unlocks">{links}</td><td>{esc(row["why_it_matters"])}</td></tr>')
    table = f'''
<section aria-labelledby="dec">
<h2 id="dec">Owner decisions</h2>
<p>Each decision lists the default that applies if no answer is given. The default is a conservative choice: it keeps unverified numbers off the site.</p>
<div class="tablewrap"><table class="register">
<thead><tr><th scope="col">ID</th><th scope="col">Decision</th><th scope="col">Options</th><th scope="col">Default if no answer</th><th scope="col">Rows it unlocks</th><th scope="col">Why it matters</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>
</section>'''
    lead = ('Eight decisions gate most of the open rows. None of them can be answered from data alone; '
            'each one names the default that applies until the owner chooses.')
    return page('Owner decisions', lead, table, 'Decisions', TODAY_VERIFIED)


APP_JS = '''(function () {
  var q = document.getElementById('q');
  var s = document.getElementById('status');
  var count = document.getElementById('count');
  if (!q || !s) { return; }
  var rows = Array.prototype.slice.call(document.querySelectorAll('table.register tbody tr'));
  function apply() {
    var term = q.value.trim().toLowerCase();
    var status = s.value;
    var shown = 0;
    rows.forEach(function (row) {
      var okText = !term || (row.getAttribute('data-search') || '').indexOf(term) !== -1;
      var okStatus = !status || row.getAttribute('data-status') === status;
      var show = okText && okStatus;
      row.hidden = !show;
      if (show) { shown += 1; }
    });
    if (count) { count.textContent = shown + ' of ' + rows.length + ' rows shown'; }
  }
  q.addEventListener('input', apply);
  s.addEventListener('change', apply);
  apply();
})();
'''

CSS = '''*{box-sizing:border-box}
:root{--ink:#14202b;--muted:#4a5a68;--line:#d7dee5;--bg:#f6f8fa;--card:#fff;--ok:#1d6b3a;--okbg:#e4f4ea;--mid:#1f4f8a;--midbg:#e5eefa;--warn:#7a5300;--warnbg:#fff4d6;--bad:#8a1c1c;--badbg:#fbe6e6}
body{margin:0;font:16px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:var(--ink);background:var(--bg)}
a{color:#0b5cad}
.skip{position:absolute;left:-999px}.skip:focus{left:8px;top:8px;background:#fff;padding:6px 10px;z-index:9}
.wrap{max-width:1200px;margin:0 auto;padding:0 20px}
.top{background:#0f2a3d;color:#fff;padding:12px 0}
.top .wrap{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px}
.brand{color:#fff;font-weight:700;text-decoration:none}
.pill{font-size:13px;background:#1e4a66;border-radius:999px;padding:3px 10px}
.navlinks{display:flex;flex-wrap:wrap;gap:6px 14px;padding-top:10px;padding-bottom:10px}
.navlinks a{color:#0f2a3d;text-decoration:none;padding:4px 8px;border-radius:6px;background:#fff;border:1px solid var(--line);font-size:14px}
.navlinks a[aria-current="page"]{background:#0f2a3d;color:#fff;border-color:#0f2a3d}
main{padding-bottom:40px}
.eyebrow{font-size:13px;letter-spacing:.04em;text-transform:uppercase;color:var(--muted);margin:24px 0 4px}
h1{font-size:30px;line-height:1.2;margin:0 0 8px}
h2{font-size:21px;margin:30px 0 10px}
.lead{color:var(--muted);max-width:880px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:18px 0}
.tile{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px;display:flex;flex-direction:column}
.tile .num{font-size:26px;font-weight:700}
.tile .lab{font-size:13px;color:var(--muted)}
.tile.ok{border-top:4px solid var(--ok)}.tile.mid{border-top:4px solid var(--mid)}.tile.warn{border-top:4px solid var(--warn)}.tile.bad{border-top:4px solid var(--bad)}
.summary{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:6px 20px 14px}
.summary li{margin:6px 0}
.filters{display:flex;flex-wrap:wrap;gap:8px 10px;align-items:center;margin:10px 0}
.filters label{font-weight:600;font-size:14px}
.filters input,.filters select{font:inherit;padding:6px 8px;border:1px solid #9aa8b4;border-radius:6px;min-width:220px}
.filters input:focus,.filters select:focus,a:focus{outline:3px solid #f0b400;outline-offset:2px}
#count{font-size:14px;color:var(--muted)}
.tablewrap{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:10px}
table.register{border-collapse:collapse;width:100%;font-size:14px}
table.register th,table.register td{border-bottom:1px solid var(--line);padding:9px 10px;text-align:left;vertical-align:top}
table.register thead th{background:#eef2f6;position:sticky;top:0;font-size:13px}
table.register tbody tr:nth-child(even){background:#fafbfc}
table.register tbody th{width:110px;font-weight:400}
.id{font-weight:700;display:block;font-family:ui-monospace,Menlo,Consolas,monospace}
.group{display:block;font-size:12px;color:var(--muted);margin-top:2px}
details{margin-top:6px;font-size:13px;color:var(--muted)}
details summary{cursor:pointer;color:#0b5cad}
details p{margin:4px 0 0}
.chip{display:inline-block;border-radius:999px;padding:2px 9px;font-size:12px;font-weight:600;white-space:nowrap}
.chip.ok{background:var(--okbg);color:var(--ok)}.chip.mid{background:var(--midbg);color:var(--mid)}
.chip.warn{background:var(--warnbg);color:var(--warn)}.chip.bad{background:var(--badbg);color:var(--bad)}
.chip.sev-critical{background:var(--badbg);color:var(--bad)}.chip.sev-high{background:#fde9d5;color:#7a3500}
.chip.sev-medium{background:var(--warnbg);color:var(--warn)}.chip.sev-low{background:var(--midbg);color:var(--mid)}
ul.links{list-style:none;margin:0;padding:0;font-size:13px}
ul.links li{margin:0 0 3px}
.unlocks a{margin-right:6px;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:13px}
.foot{font-size:13px;color:var(--muted);margin-top:24px}
[hidden]{display:none!important}
@media (max-width:700px){h1{font-size:24px}table.register th,table.register td{padding:7px}}
'''


def render_all(reqs, decisions, reviews):
    return {
        OUT / 'index.html': render_index(reqs, decisions, reviews),
        OUT / 'repo-review.html': render_repo_review(reviews),
        OUT / 'decisions.html': render_decisions(decisions, reqs),
        OUT / 'style.css': CSS,
        OUT / 'app.js': APP_JS,
    }


def main(argv):
    reqs, decisions, reviews = load()
    errors = validate(reqs, decisions, reviews)
    if errors:
        print('readiness: validation failed; nothing was written', file=sys.stderr)
        for error in errors:
            print('  - ' + error, file=sys.stderr)
        return 1
    pages = render_all(reqs, decisions, reviews)
    if '--check' in argv:
        stale = [str(p.relative_to(ROOT)) for p, text in pages.items()
                 if not p.exists() or p.read_text(encoding='utf-8') != text]
        if stale:
            print('readiness: pages on disk differ from the registers; run the build: ' + ', '.join(stale),
                  file=sys.stderr)
            return 1
        print(f'readiness: valid, {len(reqs)} requirements, {len(decisions)} decisions, '
              f'{len(reviews)} review items; pages up to date')
        return 0
    for path, text in pages.items():
        path.write_text(text, encoding='utf-8')
    print(f'readiness: valid, wrote {len(pages)} files for {len(reqs)} requirements')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
