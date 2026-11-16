"""Additive content for session arena/9136b4d8-own9 (16 Nov 2026 UTC).

Executed by tools/build.py after every other page is registered. It only:

1. Registers readiness.html: one row per requirement in research/brief (source: session-9136b4d8/data/readiness.json),
   plus a Week 10 recheck section comparing official designation counts (session-9136b4d8/data/week10-recheck.json)
   with the INJ snapshot. Snapshot counts are computed here from INJ; nothing is typed in.
2. Appends Flagged for Review entries F58-F70 to flags.html.

It does NOT edit navigation, the landing page, injuries.html or any shared table. Those changes are requested
in COORDINATION.md for the integration session. Blank means unverified; nothing is inferred.
"""
import json
import re
from collections import Counter

REG = json.loads((ROOT / 'session-9136b4d8/data/readiness.json').read_text(encoding='utf-8'))
RECHECK = json.loads((ROOT / 'session-9136b4d8/data/week10-recheck.json').read_text(encoding='utf-8'))
ROWS = REG['rows']
STATES = REG['states']
OFFICIAL_URL = 'https://www.nfl.com/injuries/'
SCHEDULE_URL = 'https://www.nfl.com/schedules/2026/REG10/'
REPO_URL = 'https://github.com/sassnarep3-star/Own9'
ASOF = '16 Nov 2026'
RECHECKED = {'R09', 'R19', 'R20', 'R42', 'R47', 'R49', 'R66'}


def _count(state):
    return sum(1 for r in ROWS if r['state'] == state)


def _kind(refs):
    return 'Official source · project record' if any(r != 'repo' for r in refs) else 'Project record'


# ------------------------------------------------------------------ Week 10 counts (computed)
snap_by = {}
snap_status = {}
for r in INJ:
    snap_by[r[0]] = snap_by.get(r[0], 0) + 1
    snap_status.setdefault(r[0], Counter())[r[5]] += 1

NOTES = {
    'BAL': 'Absent from snapshot (Monday game). Withheld from the row table pending the terms review (F58).',
    'LAC': 'Absent from snapshot (Monday game). Withheld from the row table pending the terms review (F58).',
    'IND': 'Snapshot has Arden Key (Questionable). The official page shows no designation for him (F59).',
    'HOU': "Snapshot says 'Jake Hummel'; official display name is 'Jacob Hummel' (F60).",
    'LAR': "Snapshot says 'Kamren Curl'; official display name is 'Kam Curl' (F60).",
}

club_rows = []
diff_clubs = []
for t in RECHECK['teams']:
    code = t['club']
    off_n = t['Out'] + t['Doubtful'] + t['Questionable']
    snap_n = snap_by.get(code, 0)
    diff = off_n - snap_n
    if diff:
        diff_clubs.append(code)
    club_rows.append(row([code, str(t['Out']), str(t['Doubtful']), str(t['Questionable']), str(off_n),
                          str(snap_n), f'{diff:+d}' if diff else '0', NOTES.get(code, 'Same designations and names.')],
                         ('nfl-injury-w10',), 'Official source · counted by reading'))

_tot = RECHECK['official_totals']
_snap_total = len(INJ)
club_rows.append(row(['League total', str(_tot['Out']), str(_tot['Doubtful']), str(_tot['Questionable']),
                      str(_tot['designated']), str(_snap_total), f"{_tot['designated'] - _snap_total:+d}",
                      f"{RECHECK['games_listed']} games, {RECHECK['clubs_listed']} clubs on the official page"],
                     ('nfl-injury-w10',), 'Official source · counted by reading'))

assert set(diff_clubs) == {'BAL', 'LAC', 'IND'}, diff_clubs

_corr_rows = [
    row(['Remove IND "Arden Key" row (no designation on official page)', '1', 'F59: requested of the integration session'], ('nfl-injury-w10',), 'Official source · counted by reading'),
    row(['Rename HOU "Jake Hummel" to "Jacob Hummel"', '1', 'F60: display name on official page'], ('nfl-injury-w10',), 'Official source · counted by reading'),
    row(['Rename LAR "Kamren Curl" to "Kam Curl"', '1', 'F60: display name on official page'], ('nfl-injury-w10',), 'Official source · counted by reading'),
    row(['Add BAL and LAC designations (Monday game)', '12', 'F58: withheld until the terms review (F66)'], ('nfl-injury-w10',), 'Official source · counted by reading'),
]

_check_rows = [
    row(['Official designations', f"{_tot['designated']} players with Out, Doubtful or Questionable (Out {_tot['Out']}, Doubtful {_tot['Doubtful']}, Questionable {_tot['Questionable']}) across {RECHECK['games_listed']} games",
         'Read 16 Nov from all 8 chunks of the official page.'], ('nfl-injury-w10',), 'Official source · counted by reading'),
    row(['Snapshot rows (INJ)', f'{_snap_total} rows. {_snap_total - 1} match an official designation (2 under name variants, F60); 1 has none (IND, F59).',
         'Count is computed from INJ in tools/build.py.'], ('repo', 'nfl-injury-w10'), 'Official source / project record'),
    row(['Seattle and Cincinnati', 'Designations: SEA 4, CIN 4. Both match the snapshot.',
         'The team tables list 15 (SEA) and 9 (CIN) rostered rows; those are not designations. Earlier working notes compared rostered rows with designations (F61).'], ('nfl-injury-w10',), 'Official source · counted by reading'),
    row(['Monday game (Chargers at Ravens)', 'BAL 2 and LAC 10 designations are on the official page and absent from the snapshot.',
         'Withheld from the row table (F58).'], ('nfl-injury-w10', 'repo'), 'Official source / project record'),
]

# ------------------------------------------------------------------ readiness.html
_summary = [
    row(['What is built', f"{_count('Built')} of {len(ROWS)} requirements are built and checked in this repository. Built means present and checked here; it does not mean a model is validated or a strategy has passed a gate.",
         'No strategy has passed the seven gates. No live strategies. No bets are placed or recommended.'], ('repo',), 'Project record'),
    row(['What blocks the next decision', 'Price data: 0 priced snapshots and no opening price in any source (R01, R05). Depth: 3 of 32 club charts (R30). Depth route not chosen (R31). Frozen forecasts: 0 verified weeks (R42). Registration records: 0 (R49).',
         'The first decision to make is the price-data policy (R06). It gates R01, R03 and R07.'], ('repo',), 'Project record'),
    row(['Week 10 injury snapshot', 'Official page read 16 Nov: 171 designations. Snapshot: 160 rows, of which 159 match an official designation (2 under name variants). Changes are requested, not made (see the Week 10 section).',
         'Thirteen findings on Flagged for Review (F58 to F70).'], ('nfl-injury-w10', 'repo'), 'Official source / project record'),
    row(['Recommendation', 'Keep the desk paper-only. Do not publish a line, a backtest ROI or a bet until the price-data policy (R06) and at least one validated market line exist (R03, R07).',
         'Each row stays on this page until its clearing number is met on the record.'], ('repo',), 'Project record'),
]

_state_rows = [row([s, str(_count(s)), 'Counted from session-9136b4d8/data/readiness.json'], ('repo',), 'Project record') for s in STATES]
_top_ids = ('R01', 'R06', 'R30', 'R31', 'R42', 'R49', 'R67')
_top = [row([r['id'], r['requirement'], r['state'], r['gate'], r['clears'], r['evidence']], tuple(r['refs']), _kind(r['refs']))
        for r in ROWS if r['id'] in _top_ids]

_groups = []
for r in ROWS:
    if r['group'] not in _groups:
        _groups.append(r['group'])

_group_tables = ''.join(
    table(g, ['#', 'Requirement', 'State', 'Blocking gate', 'Number that clears it (now)', 'Evidence (file or page)'],
          [row([r['id'], r['requirement'], r['state'], r['gate'], r['clears'], r['evidence']], tuple(r['refs']), _kind(r['refs']))
           for r in ROWS if r['group'] == g])
    for g in _groups)

_recheck_html = (
    f'<div class="notice"><strong>Week 10 recheck · read {ASOF} UTC</strong>'
    f'<p>Official page: <a href="{OFFICIAL_URL}">nfl.com/injuries</a>. Counts only; no player names are republished on this page. '
    'Each club count can be checked against the official club table on that page.</p></div>'
    + table('Club-by-club counts against the official page', ['Club', 'Out', 'Doubtful', 'Questionable', 'Designated (official)', 'Snapshot rows (INJ)', 'Difference (official − snapshot)', 'Note'], club_rows)
    + table('Checks made 16 Nov', ['Check', 'Result', 'Note'], _check_rows)
    + table('Changes requested of the integration session (not made in this session)', ['Change', 'Rows', 'Reason'], _corr_rows)
    + f'<p>Official schedule ({SCHEDULE_URL}): 12 of 14 Week 10 games shown FINAL in the portion of the page read on {ASOF}. '
      'Not ingested into the results feed; the feed holds 1 Week 10 row (F62).</p>'
    + f'<p>Method: the official page was read through the fetch tool in 8 chunks on {ASOF}. Designations were counted by reading each club table. '
      'No raw hash or fetch timestamp was stored for this read (F69). The snapshot counts are computed from INJ at build time.</p>'
)

_readiness_body = (
    f'<div class="notice"><strong>Read this first</strong><p>One row per requirement in the 16 Nov 2026 brief. The state describes this repository only. '
    f'Rows {", ".join(sorted(RECHECKED))} were re-checked on {ASOF}. The other rows keep the evidence recorded before this session and are open for re-check.</p></div>'
    + table('Executive summary', ['Area', 'Finding', 'Consequence'], _summary)
    + table('State count', ['State', 'Requirements', 'How it was counted'], _state_rows)
    + table('Top blockers and clearing numbers', ['#', 'Requirement', 'State', 'Blocking gate', 'Number that clears it (now)', 'Evidence (file or page)'], _top)
    + _group_tables
    + '<h2>Week 10 recheck</h2>' + _recheck_html
)

# Published in this session's folder, not at the root: the root navigation belongs to the integration session.
_READINESS_DOC = (
    '<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
    '<meta name="description" content="Decision readiness for the Own9 NFL research repository, 16 Nov 2026."><title>Decision readiness · Own9 NFL Research</title>'
    '<link rel="stylesheet" href="../style.css"><script src="../site.js" defer></script></head>\n'
    '<body><a class="skip" href="#main">Skip to content</a><header><div class="shell top"><a class="brand" href="../index.html"><span>O9</span> OWN9 <small> / NFL RESEARCH</small></a>'
    '<span class="status-dot">Research only · no live wagers</span></div>'
    '<nav class="shell" aria-label="Session pages"><span class="nav-group"><span class="nav-label">Session 9136b4d8</span>'
    '<a href="readiness.html" aria-current="page">Decision readiness</a><a href="../flags.html">Flagged for review</a><a href="../index.html">Overview</a></span></nav></header>\n'
    '<main class="shell" id="main"><div class="page-meta"><span class="eyebrow">RESEARCH DESK / DECISION READINESS</span>'
    f'<span>As of {ASOF} · UTC</span></div><h1>Decision readiness.<br>One row per requirement.</h1>'
    '<p class="lead">Each requirement in the brief, its state in this repository, the gate that blocks it, and the number that would clear it. '
    'Blank or zero means unverified, never a pass. Published here, outside the root navigation, until the integration session adds it.</p>'
    + _readiness_body +
    '<p class="disclaimer">Research, not betting advice. No verified edge or guaranteed return. Blank empirical values are unavailable and unverified, never zero.</p></main></body></html>\n'
)
(ROOT / 'session-9136b4d8').mkdir(parents=True, exist_ok=True)
(ROOT / 'session-9136b4d8' / 'readiness.html').write_text(_READINESS_DOC, encoding='utf-8')

# ------------------------------------------------------------------ F65 (computed) and Flagged for Review F58-F70
_row_re = re.compile(r'<tr[^>]*>(.*?)</tr>', re.S)
_href_re = re.compile(r'href="([^"]+)"')
_repo_only = 0
_with_links = 0
_scan = [_c for _f, (_l, _t, _i, _c) in PAGES.items() if _f != 'flags.html'] + [_READINESS_DOC]
for _c in _scan:
    for _tr in _row_re.findall(_c):
        _hrefs = [h.split('#')[0].rstrip('/') for h in _href_re.findall(_tr)]
        if not _hrefs:
            continue
        _with_links += 1
        if all(h == REPO_URL for h in _hrefs):
            _repo_only += 1

_flag_rows = [
    row(['F58', 'Monday game missing from the Week 10 snapshot. The official page lists 12 designations for it (BAL 2, LAC 10); the snapshot has no rows for either club.',
         f'Read the BAL and LAC tables on the official page {ASOF}.', 'Counted on readiness.html. Not added to the row table until the terms are read (F66). Integration session to decide.'],
        ('nfl-injury-w10', 'repo'), 'Official source / project record'),
    row(['F59', 'Arden Key (IND) shown as Questionable with a Hamstring injury in the snapshot. The official IND table lists him with no injury, Full Participation in Practice and a blank Game Status (no designation).',
         f'Read the IND table on the official page {ASOF}.', 'Row should be removed. Requested of the integration session; not edited here (shared table).'],
        ('nfl-injury-w10', 'repo'), 'Official source / project record'),
    row(['F60', 'Two names differ from the official display text: HOU "Jake Hummel" (official: Jacob Hummel; URL slug jake-hummel) and LAR "Kamren Curl" (official: Kam Curl; URL slug kamren-curl). Status matches in both cases.',
         f'Compared each snapshot name with the display name on the official page {ASOF}.', 'Display name should be used. Requested of the integration session.'],
        ('nfl-injury-w10', 'repo'), 'Official source / project record'),
    row(['F61', 'Count statements conflict across the project. tests/test_site.py pins 160 snapshot rows; the official page has 171 designations; the snapshot holds 160 rows. Working notes compared SEA 15 and CIN 9 (rostered rows) with designations; the designation counts are SEA 4 and CIN 4, and they match.',
         f'Counted the official page {ASOF}; compared with INJ.', 'Use designation counts (Out, Doubtful, Questionable) in all text. Rostered-row counts must not be labelled as injuries.'],
        ('nfl-injury-w10', 'repo'), 'Official source / project record'),
    row(['F62', 'Results feed is stale. data/board/results_2026.csv holds one Week 10 row. The official schedule page shows 12 of 14 Week 10 games FINAL in the portion read.',
         f'Read the official schedule page {ASOF} (chunk 0 of 2).', 'Not ingested here. Ingestion needs a dated, versioned update and a source row per game.'],
        ('repo',), 'Project record'),
    row(['F63', 'Date stamps disagree. Local build dates index.html and data.html as 04 Nov 2026 and injuries.html as 14 Nov 2026 (KEEP_DATE_14 in tools/build.py). The live landing page reads "As of 04 Nov 2026".',
         'Compared the date in each generated page with the build list and the live page.', 'Pages changed on 16 Nov carry 16 Nov. Other pages are unchanged. A capture date per page is suggested to the integration session.'],
        ('repo',), 'Project record'),
    row(['F64', 'Duplicate pages and count sources. Three signal pages (signal-and-staking, signal-staking, signal-vs-staking) cover the same ground. index.html says 29 verified games; data/results/verified-results.csv has 16 rows; the origination desk results feed holds 7,088 games; data/raw/games.csv has 7,547 data rows.',
         'Listed the pages in the navigation and compared each count with its file.', 'Not merged. The owner should name one canonical page and one source for each count.'],
        ('repo',), 'Project record'),
    row(['F65', f'{_repo_only} of {_with_links} table rows with a link cite only the project repository, not an official source. The brief requires an official source on every row.',
         'Counted at build time from the generated pages (this module).', 'Labelled Project record and not counted as verified. Owner decision whether repository citations are acceptable on analysis rows.'],
        ('repo',), 'Project record'),
    row(['F66', 'Row-level official data is published. injuries.html shows the designation rows verbatim. The rights note on the evidence excerpt says it is a short verification excerpt, not a republication, and not a licensed as-of archive. The brief asks for raw row-level data to stay private until the terms are read.',
         'Read the rights note in evidence/availability/injury-report-2026-week-10.json.', 'No rows were added or removed here. Owner decision: keep, remove, or move raw rows to a private store.'],
        ('nfl-injury-w10', 'repo'), 'Official source / project record'),
    row(['F67', 'Access limit. nfl.com is not on this sandbox\'s outbound allowlist, so official pages were read through the fetch tool. The 171 designations were counted by reading, not by script.',
         'Checked the outbound host list for this session.', 'A reviewer should recount from the official link. A capture job with network access to the official host would remove this limit.'],
        ('nfl-injury-w10',), 'Official source · counted by reading'),
    row(['F68', 'Backtest numbers in the leaderboard data. data/board/leaderboard.csv row OWN-SIDE (status Paper, 104 walk-forward games) carries a Brier score of 0.2355 and directional accuracy of 0.6346. The brief forbids backtest numbers on the leaderboard. The value 0.2355 does not appear in leaderboard.html.',
         'Read data/board/leaderboard.csv; searched leaderboard.html for the value.', 'Not removed here. Owner decision whether data files count as the leaderboard.'],
        ('repo',), 'Project record'),
    row(['F69', 'No hash or fetch time for the official reads. The nfl-injury-w10 source row says checked 14 Nov; no raw hash was stored for that read or for the 16 Nov read. The snapshot store is empty.',
         'Searched data/snapshots/ and session folders for hashes of these reads.', 'Open. Needs the capture job in R13. No hash has been invented.'],
        ('nfl-injury-w10', 'repo'), 'Official source / project record'),
    row(['F70', 'Hand-set row counts in tests. tests/test_site.py pins INJ at 160 rows and injuries.html at 226 rows. A source change would not raise an alarm. tools/verify.py checks structure only, as its own output says.',
         'Read tests/test_site.py and tools/verify.py.', 'Pins left as they are (this session changes no shared table). A source-driven alarm needs the capture job (R61).'],
        ('repo',), 'Project record'),
]
_flags_table = table(f'Irregularities found {ASOF} (F58 to F70)', ['ID', 'Irregularity', 'What was checked', 'Disposition'], _flag_rows)
_f_label, _f_title, _f_intro, _f_content = PAGES['flags.html']
PAGES['flags.html'] = (_f_label, _f_title, _f_intro, _f_content + _flags_table)
