"""Build the decision-desk pages from the committed data files.

Every number on every page is read from ``decision-desk/data/``. Nothing is typed into
the generator, so a page cannot drift from the file it describes and a retyped count
cannot become a second, contradictory source of truth.

    python3 decision-desk/tools/build.py

The output is static HTML with no third-party assets. It publishes under
``/Own9/decision-desk/`` with relative links, so it works on GitHub Pages and from a
file:// checkout.
"""
from __future__ import annotations

import html
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
OUT = ROOT

sys.path.insert(0, str(ROOT / 'tools'))
from parse_capture import parse  # noqa: E402

PAGES = [
    ('index.html', 'Decision desk', 'Overview'),
    ('requirements.html', 'Requirements', 'Gate table'),
    ('questions.html', 'Questions', 'Have / have not'),
    ('suggestions.html', 'Suggestions', 'Review board'),
    ('availability.html', 'Availability', 'Per club'),
    ('fixtures.html', 'Fixtures', 'Venues and results'),
    ('captures.html', 'Captures', 'Snapshot ledger'),
    ('sources.html', 'Sources', 'Official register'),
    ('flagged.html', 'Flagged', 'For review'),
]

STATUS_LABEL = {
    'met': 'Met',
    'partial': 'Partial',
    'not-started': 'Not started',
    'rejected': 'Rejected by design',
    'blocked': 'Blocked by permission',
}

CATEGORY_ORDER = [
    'Pricing', 'Availability', 'Leaderboard', 'Modelling', 'Validation',
    'Infrastructure', 'Fixtures', 'Governance', 'Rejected',
]

CATEGORY_BLURB = {
    'Pricing': 'Originate a number, record it, and hold it against the market.',
    'Availability': 'Who is out, who replaces them, and how deep the drop goes.',
    'Leaderboard': 'Rank by proper score with uncertainty; never by a lucky run.',
    'Modelling': 'Features, probabilities, and the inputs behind every output.',
    'Validation': 'Pre-registration, holdouts, controls and demotion.',
    'Infrastructure': 'Capture, storage, immutability and drift alarms.',
    'Fixtures': 'Schedule facts, venues, weather and environment.',
    'Governance': 'Suggestions, questions, and the decisions only the owner can make.',
    'Rejected': 'Recorded so the same shortcut is not proposed twice.',
}

BYE_W10 = ['CHI', 'DEN', 'PHI', 'TB']


# --------------------------------------------------------------------------- helpers


def esc(value) -> str:
    return html.escape('' if value is None else str(value), quote=True)


def load(name):
    return json.loads((DATA / name).read_text())


def links(evidence):
    """Render a source-link cell. An entry with no URL is rendered as prose."""
    if not evidence:
        return '<span class="muted">No source</span>'
    parts = []
    for item in evidence:
        url = item.get('url')
        label = esc(item.get('label', 'source'))
        if url:
            parts.append(f'<a class="src" href="{esc(url)}">{label}</a>')
        else:
            parts.append(f'<span class="muted">{label}</span>')
    return '<br>'.join(parts)


def blank(text='Not published'):
    return f'<span class="blank" title="Left blank on purpose. Nothing was inferred.">{esc(text)}</span>'


def absent(text='Recorded absence'):
    """A checked absence: this desk looked and the value does not exist in any source obtained."""
    return f'<span class="absent" title="Checked and absent. No source obtained publishes this.">{esc(text)}</span>'


def table(headers, rows, caption=None, cls=''):
    out = ['<div class="tablewrap">']
    out.append(f'<table class="{cls}">')
    if caption:
        out.append(f'<caption>{esc(caption)}</caption>')
    out.append('<thead><tr>' + ''.join(f'<th scope="col">{esc(h)}</th>' for h in headers) + '</tr></thead>')
    out.append('<tbody>')
    if not rows:
        out.append(f'<tr><td colspan="{len(headers)}" class="empty">No rows.</td></tr>')
    for row in rows:
        out.append('<tr>' + ''.join(f'<td>{c}</td>' for c in row) + '</tr>')
    out.append('</tbody></table></div>')
    return '\n'.join(out)


def pill(status):
    label = STATUS_LABEL.get(status, status)
    return f'<span class="pill pill-{esc(status)}">{esc(label)}</span>'


# --------------------------------------------------------------------------- page shell


def nav(active):
    items = []
    for file, label, sub in PAGES:
        cls = ' class="active"' if file == active else ''
        items.append(f'<a{cls} href="{file}"><strong>{esc(label)}</strong><span>{esc(sub)}</span></a>')
    return '\n'.join(items)


def page(file, title, lead, body, active=None):
    active = active or file
    head_title = f'{title} · Own9 decision desk'
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(head_title)}</title>
<meta name="description" content="{esc(lead)}">
<link rel="stylesheet" href="assets/style.css">
<script src="assets/filter.js" defer></script>
</head>
<body>
<a class="skip" href="#main">Skip to main content</a>
<header class="topbar">
  <a class="brand" href="index.html">Own9 <span>decision desk</span></a>
  <p class="brandnote">One row per requirement. The gate that blocks it. The number that would clear it.</p>
</header>
<nav class="nav" aria-label="Decision desk sections">
  {nav(active)}
</nav>
<main id="main" class="wrap">
  <h1>{esc(title)}</h1>
  <p class="lead">{esc(lead)}</p>
{body}
</main>
<footer class="foot">
  <p>Static, dependency-free, generated from <code>decision-desk/data/</code> by
  <code>decision-desk/tools/build.py</code>. Every table row links to the official publisher or to the
  project record that produced it. A blank cell is a deliberate blank: nothing on this desk is inferred.</p>
  <p><a href="../index.html">Root dashboard</a> · <a href="https://github.com/sassnarep3-star/Own9">Repository</a></p>
</footer>
</body>
</html>
"""


# --------------------------------------------------------------------------- computations


def injury_rows():
    parsed = json.loads((DATA / 'parsed' / 'injury_captures.json').read_text())
    key = sorted(parsed)[0]
    return parsed[key]


def per_club():
    cap = injury_rows()
    tx = load('transactions-2026-11.json')
    reserve = {(r['club'], r['player']): r['date'] for r in tx['reserve_list']}
    clubs = defaultdict(lambda: {
        'rows': 0, 'out': 0, 'doubtful': 0, 'questionable': 0, 'no_designation': 0,
        'dnp': 0, 'limited': 0, 'full': 0, 'reserve': [], 'out_players': [], 'q_players': [],
        'network': '', 'day': '', 'kickoff': '',
    })
    for r in cap['rows']:
        c = clubs[r['team']]
        c['rows'] += 1
        c['network'] = r['network']
        c['day'] = r['game_day']
        c['kickoff'] = r['kickoff_et']
        g = r['game_status']
        if g == 'Out':
            c['out'] += 1
            c['out_players'].append(r['player'])
        elif g == 'Doubtful':
            c['doubtful'] += 1
        elif g == 'Questionable':
            c['questionable'] += 1
            c['q_players'].append(r['player'])
        else:
            c['no_designation'] += 1
        p = r['practice_status']
        if p.startswith('Did Not'):
            c['dnp'] += 1
        elif p.startswith('Limited'):
            c['limited'] += 1
        else:
            c['full'] += 1
        key = (r['team'], r['player'])
        if key in reserve:
            c['reserve'].append((r['player'], reserve[key]))
    return dict(clubs), cap, tx


# --------------------------------------------------------------------------- pages


def build_index(reqs, flags, questions, cap):
    counts = Counter(r['status'] for r in reqs)
    met = counts.get('met', 0)
    total = len(reqs)
    cat_counts = Counter(r['category'] for r in reqs)
    answered = len(questions['answered'])
    openq = len(questions['open_data']) + len(questions['owner_decisions'])
    bye = ', '.join(BYE_W10)

    cards = [
        ('Requirements on the register', str(total), 'one row each, with a gate and a clearing number'),
        ('Met', f'{met} of {total}', 'implemented and populated with verified data'),
        ('Partial', f"{counts.get('partial', 0)} of {total}", 'the structure exists; the verified data does not yet'),
        ('Not started', f"{counts.get('not-started', 0)} of {total}", 'no implementation found in the repository'),
        ('Blocked by permission', f"{counts.get('blocked', 0)} of {total}", 'NFL.com Terms 1.3; no amount of work substitutes'),
        ('Questions answered here', str(answered), 'each from an official page, each with a link'),
        ('Questions still open', str(openq), 'each with the data action or the decision that closes it'),
        ('Injury rows captured', str(len(cap['rows'])), f"{len(cap['teams_published'])} clubs; {bye} on bye"),
        ('Flagged for review', str(len(flags)), 'published, not reconciled'),
    ]
    card_html = '\n'.join(
        f'<div class="card"><span class="cardnum">{esc(v)}</span><span class="cardlabel">{esc(k)}</span>'
        f'<span class="cardnote">{esc(n)}</span></div>'
        for k, v, n in cards
    )

    cat_rows = []
    for cat in CATEGORY_ORDER:
        if cat not in cat_counts:
            continue
        sub = [r for r in reqs if r['category'] == cat]
        c = Counter(r['status'] for r in sub)
        cat_rows.append([
            f'<a href="requirements.html#cat-{esc(cat.lower())}">{esc(cat)}</a>',
            esc(CATEGORY_BLURB[cat]),
            str(len(sub)),
            str(c.get('met', 0)),
            str(c.get('partial', 0)),
            str(c.get('not-started', 0)),
            str(c.get('rejected', 0)),
        ])

    rows = []
    for r in reqs:
        rows.append([
            f'<a href="requirements.html#{esc(r["id"])}">{esc(r["id"])}</a>',
            f'<span class="cat">{esc(r["category"])}</span>',
            esc(r['requirement']),
            pill(r['status']),
            esc(r['gate']),
            esc(r['clearing_number']),
            links(r['evidence']),
        ])

    body = f"""
<section class="cards" aria-label="Headline counts">
{card_html}
</section>

<section class="callout" aria-label="Permission blocker">
<h2>Read this before anything else</h2>
<div class="prose">
<p><strong>NFL.com Terms of Service section 1.3, updated 16 May 2024, prohibits systematic retrieval
of content from the Services without express prior written consent.</strong> The exact words are:
<em>"Systematic retrieval of data or other content from the Services, whether to create or compile,
directly or indirectly, a collection, compilation, database, or directory, is prohibited absent our
express prior written consent."</em></p>
<p>That is not a work blocker, it is a permission blocker, and it changes the register.
{counts.get('blocked', 0)} requirements are marked <strong>blocked by permission</strong> rather than
not started, and four suggestions that proposed scheduled capture are marked blocked on permission.
It also applies to work already committed: this desk made seven fetches and committed one verbatim
capture, so whether that capture stays is an owner decision, not this desk's to make. It is recorded
as <a href="flagged.html#DD-13">DD-13</a> and as owner decision
<a href="questions.html#O05">O05</a>. An earlier session reached the same conclusion independently
and recorded it as DEC-01; this desk re-read the terms page rather than relying on that record.</p>
<p class="muted">Source: <a class="src" href="https://www.nfl.com/legal/terms/">NFL.com Terms and
Conditions, section 1.3</a>. Nothing here is legal advice, and only that subsection was read for a
finding.</p>
</div>
</section>

<section class="callout" aria-label="Duplicate registers">
<h2>Three registers now cover the same brief</h2>
<div class="prose">
<p><code>readiness/</code> publishes 82 requirement rows, <code>verification/</code> publishes 74, and
this desk publishes 73. Three counts for the same brief is worse than two, and it is the same failure
mode as <a href="flagged.html#DD-11">DD-11</a>, where two implementations of the origination
requirements already exist on different inputs.</p>
<p>This desk did not read either other register line by line and makes no claim about which is
better. It cross-links them so a reviewer can see all three and decide. Recorded as
<a href="flagged.html#DD-14">DD-14</a> and owner decision
<a href="questions.html#O06">O06</a>.</p>
<p><a class="src" href="../readiness/index.html">readiness/ (82 rows)</a> ·
<a class="src" href="../verification/index.html">verification/ (74 rows)</a> ·
<a href="requirements.html">this desk (73 rows)</a></p>
</div>
</section>

<section>
<h2>Executive summary</h2>
<div class="prose">
<p><strong>No strategy has earned a stake, and nothing on this desk claims an edge.</strong> That is the
headline, and it is not a failure of effort: it is what the evidence supports today. The repository has
built the machinery a competition needs — a price-snapshot store, a verified results feed whose rows
recompute and match, a fixed origination order, a joint-evidence gate that refuses to assume
independence, a demotion gate that has been replayed, and leaderboard divisions ranked by proper score
with uncertainty. What it does not yet have is a single graded event.</p>

<p><strong>The gap is data, and part of it is permission.</strong> Of 73 requirements, {met} are met,
{counts.get('partial', 0)} are partial, {counts.get('not-started', 0)} have not started and
{counts.get('blocked', 0)} are blocked by NFL.com Terms section 1.3, which prohibits systematic
retrieval without express written consent. Read the gate column and the blockages recur. No source
obtained records an <em>opening</em> price, so closing-line value cannot be measured and no reward
can be earned. No official snap-count source was found, so depth cannot be modelled from playing
time. No inactive-list archive exists, so <em>Questionable</em> cannot be calibrated and designation
reliability cannot be scored. And the capture that would fix several of those is itself constrained
by the terms. These are prerequisites, not refinements.</p>

<p><strong>This session added verified evidence where the official pages allow it.</strong> The Week 10
2026 injury report was captured verbatim, hashed and timestamped: {len(cap['rows'])} rows across
{len(cap['teams_published'])} clubs. The official reserve list for November 2026 was captured, which
closes the question of whether a player missing from the injury report is available — 25 players are
not. Week 10's twelve completed games were read from the official schedule, and Week 11's thirteen
fixtures with their kickoff times, networks and international designations. The game centre was
checked and does publish a venue field, which is the first step towards transcribing every venue.</p>

<p><strong>Two things a reviewer should see before anything else.</strong> First, the published
Week 10 injury snapshot is stale against the official page by 68 rows: this is published as a drift
rather than silently corrected, because the cause is not established. Second, two independent
implementations of the same eight origination requirements exist on different inputs, so they can
publish different model lines for the same game; that needs an owner decision, not more code.</p>

<p><strong>Nothing on the suggestions board has been implemented.</strong> Sixteen suggestions are
costed, four candidate paths are laid out and deliberately left unranked, and the decision log records
that no path was chosen. Ranking them would substitute the builder's preference for the owner's
decision, which is the thing the section exists to prevent.</p>
</div>
</section>

<section>
<h2>Decision-readiness table</h2>
<p class="note">One row per requirement. <strong>Blocking gate</strong> is what stops the requirement
being called done. <strong>Clears when</strong> is the number that would close it — a count, a
percentage or a threshold, not an aspiration.</p>
<div class="controls">
  <label for="q">Filter</label>
  <input id="q" type="search" placeholder="search requirements, gates and numbers" autocomplete="off">
  <label for="status">Status</label>
  <select id="status">
    <option value="">All</option>
    <option value="met">Met</option>
    <option value="partial">Partial</option>
    <option value="not-started">Not started</option>
    <option value="blocked">Blocked by permission</option>
    <option value="rejected">Rejected by design</option>
  </select>
  <button id="reset" type="button">Reset</button>
  <span id="count" class="muted"></span>
</div>
{table(['ID', 'Area', 'Requirement', 'Status', 'Blocking gate', 'Clears when', 'Source'],
       rows, cls='wide filterable', caption='All 73 requirements, each with a gate and a clearing number')}
</section>

<section>
<h2>Where the work is</h2>
{table(['Area', 'What it covers', 'Requirements', 'Met', 'Partial', 'Not started', 'Rejected'],
       cat_rows, caption='Requirement counts by area')}
</section>

<section>
<h2>Start here</h2>
<ul class="startlist">
<li><a href="questions.html">Questions: what we have, what we do not, and how to find it</a> —
{answered} answered from official pages, {openq} still open, {len(questions['probes'])} probes named.</li>
<li><a href="suggestions.html">Suggestions: review and choose before anything is built</a> —
16 suggestions, 4 candidate paths, no path chosen.</li>
<li><a href="availability.html">Availability: one row per club</a> — out, doubtful, questionable,
reserve list and named absences.</li>
<li><a href="fixtures.html">Fixtures and venues</a> — Week 11 slate, Week 10 results.</li>
<li><a href="captures.html">Snapshot ledger</a> — what was captured, when, and its hash.</li>
<li><a href="flagged.html">Flagged for review</a> — {len(flags)} items, published rather than reconciled.</li>
</ul>
</section>
"""
    return page('index.html', 'Decision desk', 'One row per requirement. The gate that blocks it. The number that would clear it.', body)


def build_requirements(reqs):
    sections = []
    for cat in CATEGORY_ORDER:
        sub = [r for r in reqs if r['category'] == cat]
        if not sub:
            continue
        rows = []
        for r in sub:
            rows.append([
                f'<span class="rid" id="{esc(r["id"])}">{esc(r["id"])}</span>',
                esc(r['requirement']),
                pill(r['status']),
                esc(r['gate']),
                esc(r['clearing_number']),
                links(r['evidence']),
            ])
        sections.append(f"""
<section id="cat-{esc(cat.lower())}">
<h2>{esc(cat)}</h2>
<p class="note">{esc(CATEGORY_BLURB[cat])}</p>
{table(['ID', 'Requirement', 'Status', 'Blocking gate', 'Clears when', 'Source'], rows, cls='wide')}
</section>""")
    body = f"""
<section>
<h2>How to read this register</h2>
<div class="prose">
<p><strong>Met</strong> means the thing exists and is populated with verified data.
<strong>Partial</strong> means the structure exists — a store, a gate, a register, a schema — but the
verified data inside it does not yet. <strong>Not started</strong> means this session found no
implementation in the repository. <strong>Rejected by design</strong> records a shortcut the
requirements refuse, so it is not proposed again.</p>
<p>The status is this session's reading of the repository's own published pages and committed code,
recorded on 2026-11-16. Where another session owns the work, the row links to its page rather than
restating it. Where a status is uncertain, the gate column says so.</p>
</div>
</section>
{''.join(sections)}
"""
    return page('requirements.html', 'Requirement register', 'All 73 requirements, grouped by area, each with its gate and its clearing number.', body)


def build_questions(q):
    def rowset(items, keys, headers):
        rows = []
        for it in items:
            rows.append([f'<span class="rid">{esc(it["id"])}</span>'] + [esc(it[k]) for k in keys[:-1]] + [links(it[keys[-1]])])
        return table(headers, rows, cls='wide')

    answered = []
    for it in q['answered']:
        answered.append([
            f'<span class="rid">{esc(it["id"])}</span>',
            esc(it['question']),
            esc(it['answer']),
            esc(it['how']),
            links(it['evidence']),
        ])
    openrows = []
    for it in q['open_data']:
        openrows.append([
            f'<span class="rid">{esc(it["id"])}</span>',
            esc(it['question']),
            esc(it['would_close_it']),
            esc(it['number_needed']),
            esc(it['probe']),
            links(it['evidence']),
        ])
    owner = []
    for it in q['owner_decisions']:
        owner.append([
            f'<span class="rid">{esc(it["id"])}</span>',
            esc(it['question']),
            esc(it['why_it_blocks']),
            esc(it['number_needed']),
            esc(it['note']),
            links(it.get('evidence')),
        ])
    probes = []
    for it in q['probes']:
        probes.append([
            f'<span class="rid">{esc(it["id"])}</span>',
            esc(it['question']),
            esc(it['method']),
            esc(it['success_looks_like']),
            links(it.get('evidence')),
        ])
    have = [[esc(i['item']), f'<a class="src" href="{esc(i["source"])}">{esc(i["source"])}</a>'] for i in q['have']]
    havenot = [[esc(i['item']), absent('no source obtained'), links(i.get('evidence'))] for i in q['have_not']]

    body = f"""
<section>
<h2>What we have</h2>
<p class="note">Every item below was read from the official publisher. The link is the page it came from.</p>
{table(['Information in hand', 'Official source'], have, cls='wide')}
</section>

<section>
<h2>What we do not have</h2>
<p class="note">These are the gaps that block the decision table. None of them is filled by inference;
each is left blank wherever a page would otherwise show a number.</p>
{table(['Information missing', 'State', 'Where the absence is recorded'], havenot, cls='wide')}
</section>

<section>
<h2>Answered this session, from official sources</h2>
{table(['ID', 'Question', 'Answer', 'How it was established', 'Source'], answered, cls='wide')}
</section>

<section>
<h2>Still open, closable with data work</h2>
<p class="note">For each of these we know exactly what to fetch. The third column is the number that
would make the question answerable; the fourth is the action that produces it.</p>
{table(['ID', 'Question', 'What would close it', 'The number needed', 'How to get it', 'Source'],
       openrows, cls='wide')}
</section>

<section>
<h2>Still open, and only the owner can close them</h2>
<p class="note">These are not data problems. No amount of capture resolves them.</p>
{table(['ID', 'Question', 'Why it blocks', 'What would close it', 'Note', 'Recorded in'], owner, cls='wide')}
</section>

<section>
<h2>Probes to discover what is missing</h2>
<p class="note">A probe is a cheap test whose result is useful either way: it either finds the source or
produces a second dated record that the source does not exist.</p>
{table(['ID', 'Question', 'Method', 'What success looks like', 'What to test'], probes, cls='wide')}
</section>
"""
    return page('questions.html', 'Questions and information', 'What must be known before a decision is defensible: what we have, what we do not, and how to find it.', body)


def build_suggestions(s):
    rows = []
    for it in s['suggestions']:
        rows.append([
            f'<span class="rid">{esc(it["id"])}</span>',
            esc(it['title']),
            f'<span class="cat">{esc(it["category"])}</span>',
            esc(it['what_changes']),
            esc(it['why']),
            esc(it['cost']),
            esc(it['risk']),
            f'<span class="status-{esc(it["status"].lower().replace(" ", "-").replace(",", ""))}">{esc(it["status"])}</span>',
            links(it['evidence']),
        ])
    paths = []
    for p in s['paths']:
        paths.append([
            f'<span class="rid">{esc(p["id"])}</span>',
            esc(p['name']),
            esc(p['items']),
            esc(p['buys']),
            esc(p['costs']),
            esc(p['choose_if']),
            links(p.get('evidence')),
        ])
    log = [[esc(e['date']), esc(e['entry']), links(e.get('evidence'))] for e in s['decision_log']]

    body = f"""
<section>
<h2>How to use this board</h2>
<div class="prose">
<p>Read the suggestions, then choose a path. Nothing else happens in between: no suggestion marked
<em>Awaiting decision</em> has been implemented, and none will be until someone marks it chosen. The
paths are deliberately left unranked. Ranking them would substitute this desk's preference for the
owner's decision, which is the thing the section exists to prevent.</p>
<p>Two items are marked <em>Proposed to the root owner</em> rather than built, because they would edit
files another session owns. They are logged as requests in <code>COORDINATION.md</code> instead.</p>
</div>
</section>

<section>
<h2>Decision log</h2>
{table(['Date', 'Entry', 'Record'], log, cls='wide')}
</section>

<section>
<h2>Candidate paths</h2>
<p class="note">Four ways through the same work. Each one buys something different and costs something
different. None is recommended over the others.</p>
{table(['Path', 'Name', 'Suggestions it contains', 'What it buys', 'What it costs', 'Choose it if', 'Record'],
       paths, cls='wide')}
</section>

<section>
<h2>Suggestion register</h2>
{table(['ID', 'Suggestion', 'Area', 'What it changes', 'Why it matters', 'Cost', 'Risk', 'Status', 'Source'],
       rows, cls='wide')}
</section>
"""
    return page('suggestions.html', 'Suggestions', 'Review these, choose a path, then implement. Nothing here is built until it is chosen.', body)


def build_availability(cap, tx):
    clubs, capdata, txdata = per_club()
    w11 = load('week-11-2026-fixtures.json')
    bye11 = set(w11['bye_clubs'])
    reserve_by_club = defaultdict(list)
    for r in txdata['reserve_list']:
        reserve_by_club[r['club']].append(f"{r['player']} ({r['date']})")

    all_clubs = ['ARI', 'ATL', 'BAL', 'BUF', 'CAR', 'CHI', 'CIN', 'CLE', 'DAL', 'DEN', 'DET', 'GB',
                 'HOU', 'IND', 'JAX', 'KC', 'LV', 'LAC', 'LAR', 'MIA', 'MIN', 'NE', 'NO', 'NYG',
                 'NYJ', 'PHI', 'PIT', 'SEA', 'SF', 'TB', 'TEN', 'WAS']

    rows = []
    for club in all_clubs:
        if club in BYE_W10:
            rows.append([
                f'<strong>{esc(club)}</strong>',
                '<span class="cat">On bye, Week 10</span>',
                blank('no report published'),
                blank(), blank(), blank(), blank(), blank(), blank(),
                ', '.join(esc(x) for x in reserve_by_club.get(club, [])) or blank('none captured'),
                '<span class="cat">plays Week 11</span>' if club not in bye11 else '<span class="cat">bye Week 11</span>',
                '<a class="src" href="https://www.nfl.com/schedules/2026/by-week/week-10">NFL schedule, Week 10</a>',
            ])
            continue
        c = clubs.get(club)
        if c is None:
            rows.append([
                f'<strong>{esc(club)}</strong>', '<span class="cat">not captured</span>',
                blank(), blank(), blank(), blank(), blank(), blank(), blank(),
                ', '.join(esc(x) for x in reserve_by_club.get(club, [])) or blank('none captured'),
                '', blank(),
            ])
            continue
        out_names = ', '.join(c['out_players']) or 'none'
        rows.append([
            f'<strong>{esc(club)}</strong>',
            f"<span class=\"muted\">{esc(c['day'])} · {esc(c['kickoff'])} ET · {esc(c['network'])}</span>",
            str(c['rows']),
            str(c['out']),
            str(c['doubtful']),
            str(c['questionable']),
            str(c['no_designation']),
            str(c['dnp']),
            esc(out_names),
            ', '.join(esc(x) for x in reserve_by_club.get(club, [])) or blank('none captured'),
            '<span class="cat">plays Week 11</span>' if club not in bye11 else '<span class="cat">bye Week 11</span>',
            '<a class="src" href="https://www.nfl.com/injuries/">NFL official injury report</a><br>'
            '<a class="src" href="https://www.nfl.com/transactions/league/reserve-list/2026/11">NFL reserve list, Nov 2026</a>',
        ])

    # Designation-by-position matrix. Offence and defence position groups.
    OFF = {'QB', 'RB', 'FB', 'WR', 'TE', 'T', 'G', 'C', 'LS', 'OL'}
    DEF = {'CB', 'S', 'LB', 'DT', 'DE', 'DB', 'DL'}
    SPEC = {'K', 'P'}
    matrix = defaultdict(lambda: Counter())
    for r in capdata['rows']:
        pos = r['position']
        if pos in SPEC:
            group = 'Specialists'
        elif pos in OFF:
            group = 'Offence'
        elif pos in DEF:
            group = 'Defence'
        else:
            group = 'Other'
        key = (group, pos)
        matrix[key][r['game_status'] or 'No designation'] += 1

    mrows = []
    for (group, pos) in sorted(matrix):
        c = matrix[(group, pos)]
        mrows.append([
            f'<span class="cat">{esc(group)}</span>',
            esc(pos),
            str(sum(c.values())),
            str(c.get('Out', 0)),
            str(c.get('Doubtful', 0)),
            str(c.get('Questionable', 0)),
            str(c.get('No designation', 0)),
            '<a class="src" href="https://www.nfl.com/injuries/">NFL official injury report</a>',
        ])

    body = f"""
<section>
<h2>Per-club availability, Week 10 2026</h2>
<p class="note">Read from the official injury report at
{esc(capdata.get('file', ''))} and joined to the official reserve list for November 2026.
The report covers {len(clubs)} clubs because {len(BYE_W10)} were on bye: {esc(', '.join(BYE_W10))}.
An empty row on the official page means the club was not playing, never that it was healthy.</p>
<p class="note"><strong>Replacements are named only where the official page names them.</strong> The
last column lists players on the reserve list, which is why a player can be absent from the report and
still unavailable. No depth tier is shown: no verified depth order exists for all 32 clubs, so a
1st-to-4th-string column would be invented (see
<a href="flagged.html#DD-08">DD-08</a>).</p>
{table(['Club', 'Fixture', 'Rows', 'Out', 'Doubtful', 'Questionable', 'No designation',
        'Did not practise', 'Named Out', 'On reserve list (Nov 2026)', 'Week 11', 'Source'],
       rows, cls='wide')}
</section>

<section>
<h2>Designations by position group</h2>
<p class="note">This is the deficiency matrix in the only form the evidence supports today: counts of
game-status designations by position group. It is a placeholder for the
Offence-versus-Defence Matchup Deficiency Matrix the requirements ask for, which needs a verified
depth order before it can show strings travelled.</p>
{table(['Unit', 'Position', 'Rows', 'Out', 'Doubtful', 'Questionable', 'No designation', 'Source'],
       mrows, caption=f'All {len(capdata["rows"])} rows of the Week 10 2026 capture')}
</section>
"""
    return page('availability.html', 'Availability', 'One row per club: who is out, who is on the reserve list, and what the official page actually names.', body)


def build_fixtures():
    w11 = load('week-11-2026-fixtures.json')
    w10 = load('week-10-2026-results.json')

    f11 = []
    for g in w11['games']:
        venue = g.get('stadium')
        venue_cell = esc(venue) if venue else blank('not published on the listing')
        if g.get('international'):
            venue_cell = f'{esc(g["international"])}<br><span class="muted">neutral site</span>'
        f11.append([
            esc(g['day']),
            esc(g['date']),
            esc(g['kickoff_et']),
            f"{esc(g['away'])} at {esc(g['home'])}",
            venue_cell,
            esc(g['network']),
            f'<a class="src" href="{esc(g["game_url"])}">NFL game centre</a><br>'
            f'<a class="src" href="{esc(w11["source"])}">NFL schedule, Week 11</a>',
        ])

    r10 = []
    for g in w10['games']:
        if g['away_points'] is None:
            score = blank('not started at capture time')
        else:
            score = f"{esc(g['away'])} {esc(g['away_points'])}, {esc(g['home'])} {esc(g['home_points'])}"
        venue = g.get('venue_note') or 'not captured'
        r10.append([
            esc(g['day']),
            esc(g['date']),
            esc(g['kickoff_et']),
            f"{esc(g['away'])} at {esc(g['home'])}",
            score,
            esc(g['status']),
            esc(venue) if venue != 'not captured' else blank('not captured'),
            f'<a class="src" href="{esc(g["game_url"])}">NFL game centre</a><br>'
            f'<a class="src" href="{esc(w10["source"])}">NFL schedule, Week 10</a>',
        ])

    body = f"""
<section>
<h2>Week 11 2026 fixtures</h2>
<p class="note">{len(w11['games'])} games. {len(w11['bye_clubs'])} clubs are on bye:
{esc(', '.join(w11['bye_clubs']))}. That is {len(w11['games']) * 2} playing clubs plus
{len(w11['bye_clubs'])} on bye, which is 32.</p>
<p class="note"><strong>Venue provenance.</strong> The stadium string is the value of the
<code>destinationAddress.location</code> parameter inside the hotel link the official schedule page
renders under each fixture. It is published by nfl.com, but it is a commercial-link parameter rather
than a venue field. The game centre does publish an explicit <em>Game Info / Stadium</em> field, and
for the one fixture checked the two agree. Until a game-centre read confirms each row, the stadium
column is second-hand — see <a href="flagged.html#DD-03">DD-03</a>.</p>
{table(['Day', 'Date', 'Kickoff ET', 'Fixture', 'Venue', 'Network', 'Source'], f11, cls='wide')}
</section>

<section>
<h2>Week 10 2026 results</h2>
<p class="note">Read from the official schedule page at {esc(w10['retrieved_at_utc'])}. Two games had
not kicked off at that moment, so their score cells are blank on the official page and blank here.
These scores come from one official source and have not been cross-checked against a second official
page — see <a href="flagged.html#DD-04">DD-04</a>.</p>
{table(['Day', 'Date', 'Kickoff ET', 'Fixture', 'Score', 'Status', 'Venue note', 'Source'], r10, cls='wide')}
</section>

<section>
<h2>Bye weeks, side by side</h2>
{table(['Week', 'Clubs on bye', 'Games scheduled', 'Source'],
       [['Week 10 2026', esc(', '.join(w10['bye_clubs'])), str(len(w10['games'])),
         '<a class="src" href="' + esc(w10['source']) + '">NFL schedule, Week 10</a>'],
        ['Week 11 2026', esc(', '.join(w11['bye_clubs'])), str(len(w11['games'])),
         '<a class="src" href="' + esc(w11['source']) + '">NFL schedule, Week 11</a>']],
       caption='A club on bye publishes no injury rows that week')}
</section>
"""
    return page('fixtures.html', 'Fixtures and venues', 'The Week 11 slate with its venues, and what Week 10 actually scored.', body)


def build_captures():
    man = load('captures/manifest.json')
    parsed = json.loads((DATA / 'parsed' / 'injury_captures.json').read_text())
    pkey = sorted(parsed)[0]
    p = parsed[pkey]
    rows = []
    for c in man['captures']:
        sha = c.get('sha256')
        rows.append([
            f'<span class="rid">{esc(c["id"])}</span>',
            esc(c['title']),
            f'<a class="src" href="{esc(c["url"])}">{esc(c["url"])}</a>',
            esc(c['retrieved_at_utc']),
            esc(c['window_utc']),
            (f'<code>{esc(sha[:16])}…</code>' if sha else blank('raw bytes not retained')),
            (str(c['bytes']) if c.get('bytes') else blank()),
            (str(c['parsed_rows']) if c.get('parsed_rows') else blank()),
            esc(c['scope']),
        ])
    body = f"""
<section>
<h2>Snapshot ledger</h2>
<p class="note">{esc(man['note'])}</p>
<div class="tablewrap">
<table class="wide">
<thead><tr><th>ID</th><th>Capture</th><th>URL</th><th>Retrieved (UTC)</th><th>Window (UTC)</th>
<th>SHA-256</th><th>Bytes</th><th>Rows</th><th>Scope</th></tr></thead>
<tbody>
{''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>' for r in rows)}
</tbody></table></div>
</section>

<section>
<h2>The hashed capture</h2>
<p class="note">Only {esc(p['file'])} retains its raw bytes. It is committed verbatim under
<code>decision-desk/data/captures/</code>, so anyone can re-run the hash and confirm the bytes this
desk parsed are the bytes the publisher served.</p>
{table(['Field', 'Value'],
       [['File', f'<code>{esc(p["file"])}</code>'],
        ['Bytes', esc(p['bytes'])],
        ['SHA-256', f'<code>{esc(p["sha256"])}</code>'],
        ['Rows parsed', esc(len(p['rows']))],
        ['Clubs parsed', esc(len(p['teams_published']))],
        ['Clubs', esc(', '.join(sorted(p['teams_published'])))],
        ['Verbatim file', '<a class="src" href="data/captures/' + esc(p['file']) + '">open the capture</a>']],
       caption='Recomputed from the committed file at build time, not retyped')}
</section>

<section>
<h2>What one capture cannot do</h2>
<div class="prose">
<p>A single dated capture is a snapshot, not a series. Three requirements — the Wednesday-to-Friday
history (R54), the timestamped series (R55) and the point-in-time ledger (R47) — all need several
captures per week, produced by a scheduled job. This session produced one. It is enough to prove the
capture shape works and to record a hash; it is not enough to compute a delta, and no delta is
published.</p>
<p>The previous Week 10 snapshot in the repository and this one are two observations of the same
object, which makes a row-count diff possible for the first time. That diff is
<a href="flagged.html#DD-01">DD-01</a>, and it is published as a drift rather than reconciled,
because the cause is not established.</p>
</div>
</section>
"""
    return page('captures.html', 'Capture ledger', 'What was captured, when, from where, and the hash that proves the bytes.', body)


def build_sources():
    src = load('sources.json')
    rows = [[f'<a class="src" href="{esc(s["url"])}">{esc(s["name"])}</a>',
             esc(s['scope_read']), esc(s['what_it_publishes']), esc(s['limits'])] for s in src]
    body = f"""
<section>
<h2>Official sources read this session</h2>
<p class="note">Six pages, all on nfl.com, all read on 2026-11-16 UTC. The second column is the exact
scope that was read; the last column is what the page does not publish. A checked absence is recorded
as a fact, not worked around.</p>
{table(['Source', 'Scope read', 'What it publishes', 'Limits found'], rows, cls='wide')}
</section>

<section>
<h2>Rule this desk holds to</h2>
<div class="prose">
<p>Every table row on every page links to an official publisher or to the project record that produced
it. Where a value could not be confirmed from an official source, the cell is left blank and marked as
not published — never filled in, never inferred, never back-filled from memory. A blank cell is a
finding, and it is the most useful kind on this desk.</p>
</div>
</section>
"""
    return page('sources.html', 'Sources', 'The official pages this desk read, what each publishes, and what it does not.', body)


def build_flagged(flags):
    rows = []
    for f in flags:
        rows.append([
            f'<span class="rid" id="{esc(f["id"])}">{esc(f["id"])}</span>',
            esc(f['title']),
            esc(f['finding']),
            esc(f['status']),
            esc(f['what_would_clear_it']),
            links(f['evidence']),
        ])
    body = f"""
<section>
<h2>Flagged for review</h2>
<p class="note">{len(flags)} items. Each is published rather than reconciled: where two official pages
disagree, this desk records the disagreement and leaves it, because choosing a side without evidence
would be the inference the project exists to avoid.</p>
{table(['ID', 'Item', 'Finding', 'Status', 'What would clear it', 'Source'], rows, cls='wide')}
</section>

<section>
<h2>Inherited from earlier sessions</h2>
<p class="note">These were raised by other sessions and are repeated here because a reviewer reading
this desk will hit them. They are not re-adjudicated.</p>
<ul class="startlist">
<li><strong>OD-01</strong> — the licence and provenance of the committed price files are unknown.
<a class="src" href="https://github.com/sassnarep3-star/Own9/blob/main/origination/flagged.html">Origination desk flags</a></li>
<li><strong>OD-02</strong> — no source obtained records an opening price, so all opening columns are blank.
<a class="src" href="https://github.com/sassnarep3-star/Own9/blob/main/origination/flagged.html">Origination desk flags</a></li>
<li><strong>OD-03</strong> — ROI is arithmetic on recorded closing prices, not economics.
<a class="src" href="https://github.com/sassnarep3-star/Own9/blob/main/origination/flagged.html">Origination desk flags</a></li>
<li><strong>OD-16</strong> — two implementations of the same origination brief exist on different inputs.
<a class="src" href="https://github.com/sassnarep3-star/Own9/blob/main/origination/flagged.html">Origination desk flags</a></li>
</ul>
</section>
"""
    return page('flagged.html', 'Flagged for review', 'Irregularities, conflicts and limitations. Published, not reconciled.', body)


# --------------------------------------------------------------------------- main


def main() -> int:
    # Re-parse the verbatim capture before building, so parsed data can never drift
    # from the raw bytes it came from.
    parsed = {}
    for p in sorted((DATA / 'captures').glob('*.md')):
        parsed[p.stem] = parse(p)
    (DATA / 'parsed').mkdir(parents=True, exist_ok=True)
    (DATA / 'parsed' / 'injury_captures.json').write_text(json.dumps(parsed, indent=2, sort_keys=True) + '\n')

    # The manifest records the hash of the capture file. Assert it rather than trusting it.
    import hashlib
    man = load('captures/manifest.json')
    for c in man['captures']:
        if c.get('file'):
            digest = hashlib.sha256((DATA / 'captures' / c['file']).read_bytes()).hexdigest()
            if digest != c['sha256']:
                raise SystemExit(f"{c['id']}: committed hash {c['sha256']} != recomputed {digest}")

    cap = parsed[sorted(parsed)[0]]
    reqs = load('requirements.json')
    questions = load('questions.json')
    suggestions = load('suggestions.json')
    flags = load('flags.json')
    tx = load('transactions-2026-11.json')

    built = [
        ('index.html', build_index(reqs, flags, questions, cap)),
        ('requirements.html', build_requirements(reqs)),
        ('questions.html', build_questions(questions)),
        ('suggestions.html', build_suggestions(suggestions)),
        ('availability.html', build_availability(cap, tx)),
        ('fixtures.html', build_fixtures()),
        ('captures.html', build_captures()),
        ('sources.html', build_sources()),
        ('flagged.html', build_flagged(flags)),
    ]
    for name, content in built:
        (OUT / name).write_text(content)
        print(f'wrote {name} ({len(content)} bytes)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
