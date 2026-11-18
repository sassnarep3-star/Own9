#!/usr/bin/env python3
"""Build the per-team availability view from data/week11.json.

Counts only. Every number in data/week11.json is a count read from a named official
page on the read date. The generator validates the arithmetic and fails closed:
any mismatch raises instead of publishing a value it cannot reconcile.

Usage:
    python3 team-view/build.py          # write team-view/index.html
    python3 team-view/build.py --check  # validate only
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / 'data' / 'week11.json'
OUT = HERE / 'index.html'

EXPECTED_CLUBS = 32
EXPECTED_BYES = {'ATL', 'CLE', 'GB', 'LAR', 'NE', 'SEA'}  # schedule page, "Teams on Bye", Week 11
PRACTICE_KEYS = ('Did Not Participate In Practice', 'Limited Participation in Practice',
                 'Full Participation in Practice')
GAME_KEYS = ('Out', 'Doubtful', 'Questionable', 'blank')
TEAM_URL = 'https://www.nfl.com/teams/{slug}/'


class ValidationError(Exception):
    pass


def load() -> dict:
    return json.loads(DATA.read_text(encoding='utf-8'))


def validate(d: dict) -> None:
    clubs = d['clubs']
    if len(clubs) != EXPECTED_CLUBS:
        raise ValidationError(f'expected {EXPECTED_CLUBS} clubs, found {len(clubs)}')
    abbrs = [c['abbr'] for c in clubs]
    if len(set(abbrs)) != len(abbrs):
        raise ValidationError('duplicate club abbreviation')
    byes = {c['abbr'] for c in clubs if c['bye']}
    if byes != EXPECTED_BYES:
        raise ValidationError(f'bye set {sorted(byes)} differs from schedule {sorted(EXPECTED_BYES)}')
    for c in clubs:
        if c['bye']:
            if 'report' in c or 'rows' in c:
                raise ValidationError(f"{c['abbr']}: bye club must not carry report fields")
            continue
        report = c.get('report')
        if report == 'No Injuries Reported':
            if 'rows' in c:
                raise ValidationError(f"{c['abbr']}: 'No Injuries Reported' with rows")
        elif report == 'Club table published':
            p = c['practice']
            if set(p) != set(PRACTICE_KEYS):
                raise ValidationError(f"{c['abbr']}: practice keys {sorted(p)}")
            if sum(p.values()) != c['rows']:
                raise ValidationError(f"{c['abbr']}: practice counts {sum(p.values())} != rows {c['rows']}")
            g = c['game_status']
            if set(g) != set(GAME_KEYS):
                raise ValidationError(f"{c['abbr']}: game-status keys {sorted(g)}")
            if sum(g.values()) != c['rows']:
                raise ValidationError(f"{c['abbr']}: game-status counts {sum(g.values())} != rows {c['rows']}")
        else:
            raise ValidationError(f"{c['abbr']}: unknown report state {report!r}")
    if not d.get('flags'):
        raise ValidationError('no flags present')


def row_html(c: dict, d: dict) -> str:
    team_link = TEAM_URL.format(slug=c['slug'])
    src = (f'<a href="{d["schedule_source_url"]}">schedule</a> · <a href="{team_link}">club</a>'
           if c['bye'] else
           f'<a href="{d["injury_source_url"]}">injury report</a> · <a href="{team_link}">club</a>')
    if c['bye']:
        status, rows, dnp, lp, fp, out, dbt, q = 'Bye (Week 11)', '—', '—', '—', '—', '—', '—', '—'
    elif c['report'] == 'No Injuries Reported':
        status, rows = 'No Injuries Reported', '0'
        dnp, lp, fp, out, dbt, q = '0', '0', '0', '0', '0', '0'
    else:
        p, g = c['practice'], c['game_status']
        status, rows = 'Club table published', str(c['rows'])
        dnp = str(p['Did Not Participate In Practice'])
        lp = str(p['Limited Participation in Practice'])
        fp = str(p['Full Participation in Practice'])
        out, dbt, q = str(g['Out']), str(g['Doubtful']), str(g['Questionable'])
    cells = [
        f'<th scope="row">{html.escape(c["name"])} <span class="abbr">{c["abbr"]}</span></th>',
        f'<td>{html.escape(status)}</td>',
        f'<td class="n">{rows}</td>',
        f'<td class="n">{dnp}</td>',
        f'<td class="n">{lp}</td>',
        f'<td class="n">{fp}</td>',
        f'<td class="n">{out}</td>',
        f'<td class="n">{dbt}</td>',
        f'<td class="n">{q}</td>',
        '<td class="blank" aria-label="unverified">unverified</td>',
        '<td class="blank" aria-label="unverified">unverified</td>',
        f'<td class="src">{src}</td>',
    ]
    return '<tr>' + ''.join(cells) + '</tr>'


def render(d: dict) -> str:
    rows = '\n'.join(row_html(c, d) for c in d['clubs'])
    flags = '\n'.join(
        f'<li><strong>{html.escape(f["id"])}</strong> ({html.escape(f["severity"])}): {html.escape(f["text"])}</li>'
        for f in d['flags'])
    playing = [c for c in d['clubs'] if not c['bye']]
    tables = sum(1 for c in playing if c.get('report') == 'Club table published')
    total_rows = sum(c['rows'] for c in playing if 'rows' in c)
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Per-team availability, Week 11 | Own9</title>
<style>
body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 0; color: #1d2630; background: #f6f7f9; }}
header, main {{ max-width: 1200px; margin: 0 auto; padding: 16px; }}
header {{ padding-bottom: 0; }}
a {{ color: #0b5cad; }}
h1 {{ font-size: 1.6rem; margin: 8px 0; }}
.note {{ background: #fff8e1; border: 1px solid #f0d98a; padding: 10px 14px; border-radius: 6px; }}
.kpis {{ display: flex; gap: 12px; flex-wrap: wrap; margin: 14px 0; }}
.kpi {{ background: #fff; border: 1px solid #dde2e8; border-radius: 6px; padding: 10px 14px; min-width: 150px; }}
.kpi b {{ display: block; font-size: 1.4rem; }}
.wrap {{ overflow-x: auto; background: #fff; border: 1px solid #dde2e8; border-radius: 6px; }}
table {{ border-collapse: collapse; width: 100%; font-size: 0.92rem; }}
th, td {{ padding: 8px 10px; border-bottom: 1px solid #eef1f4; text-align: left; vertical-align: top; }}
thead th {{ background: #eef2f6; position: sticky; top: 0; }}
td.n {{ text-align: right; font-variant-numeric: tabular-nums; }}
td.blank {{ color: #8a6d00; font-style: italic; }}
.abbr {{ color: #66727f; font-size: 0.8rem; margin-left: 4px; }}
td.src a {{ white-space: nowrap; }}
section {{ margin-top: 22px; }}
</style>
</head>
<body>
<header>
<p><a href="../index.html">← Own9 home</a></p>
<h1>Per-team availability, Week 11 (2026)</h1>
<p class="note"><strong>Counts only.</strong> Read manually from the official NFL pages on {html.escape(d['read_utc'])} UTC. Blank or “unverified” means the source does not publish the value. A blank game status is not a clearance. Starters out and replacements are not shown: no verified official depth chart or starter list exists in this repository.</p>
<div class="kpis">
  <div class="kpi"><b>{EXPECTED_CLUBS}</b>clubs</div>
  <div class="kpi"><b>{len(playing)}</b>playing this week</div>
  <div class="kpi"><b>{len(EXPECTED_BYES)}</b>on bye (schedule page)</div>
  <div class="kpi"><b>{tables}</b>clubs with a published table</div>
  <div class="kpi"><b>{total_rows}</b>listed player rows (counts only)</div>
</div>
</header>
<main>
<div class="wrap">
<table>
<thead><tr>
<th scope="col">Club</th>
<th scope="col">Report state</th>
<th scope="col">Rows</th>
<th scope="col">DNP</th>
<th scope="col">LP</th>
<th scope="col">FP</th>
<th scope="col">Out</th>
<th scope="col">Doubtful</th>
<th scope="col">Questionable</th>
<th scope="col">Starters out</th>
<th scope="col">Replacements named</th>
<th scope="col">Source</th>
</tr></thead>
<tbody>
{rows}
</tbody>
</table>
</div>
<section>
<h2>How to read this table</h2>
<ul>
<li>DNP = Did Not Participate in Practice; LP = Limited Participation; FP = Full Participation. These are the practice labels the report publishes.</li>
<li>Out, Doubtful and Questionable are the published game-status labels. A blank cell in the report is shown as a count in “Rows” but is not counted as any status.</li>
<li>“Starters out” and “Replacements named” are left unverified on purpose. Filling them needs an official source for starters and game-day status (NFL Game Books or an official depth chart), which this repository does not hold (see DEC-06 and RV-05 in the readiness register).</li>
<li>Bye clubs are taken from the official schedule page only.</li>
</ul>
</section>
<section>
<h2>Flags for review</h2>
<ul>
{flags}
</ul>
<p>Sources: <a href="https://www.nfl.com/injuries/">https://www.nfl.com/injuries/</a> · <a href="https://www.nfl.com/schedules/2026/REG11/">https://www.nfl.com/schedules/2026/REG11/</a></p>
</section>
</main>
</body>
</html>
'''


def main(argv: list[str]) -> int:
    d = load()
    try:
        validate(d)
    except ValidationError as e:
        print(f'FAIL: {e}', file=sys.stderr)
        return 1
    if '--check' in argv:
        print(f'PASS: {len(d["clubs"])} clubs, {len(EXPECTED_BYES)} byes, {len(d["flags"])} flags')
        return 0
    OUT.write_text(render(d), encoding='utf-8')
    print(f'wrote {OUT.relative_to(HERE.parent)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
