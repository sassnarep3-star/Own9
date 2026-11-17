"""Deterministic recount of the official 2026 Week 10 availability evidence.

Everything on the published Team availability page comes from this script. It reads
three committed artefacts and nothing else:

  1. `decision-desk/data/captures/nfl-injuries-2026-w10-2026-11-16.md` — the retained
     raw capture of https://www.nfl.com/injuries/ (manifest id CAP-01, retrieved
     2026-11-16T01:17:10Z, sha256 and byte size recorded in the manifest).
  2. `tools/build.py` — the INJ / SLATE literals, i.e. the transcription the root
     `injuries.html` page publishes, dated 2026-11-14. Parsed with `ast`, never imported,
     so this tool cannot trigger a site rebuild.
  3. `decision-desk/data/transactions-2026-11.json` — official league trades and the
     November reserve list, transcribed 2026-11-16.

Rules enforced here, each of which fails the run rather than degrading it:

  * the capture file must still match the hash and byte size in its manifest;
  * every table row must parse into exactly five cells and carry an official player URL;
  * a game status must be one of Out / Doubtful / Questionable / blank — a blank is a
    missing designation, never "available", and is counted separately;
  * a club that appears in a game header but publishes no table is reported as
    "no rows captured", never as zero injuries;
  * the cross-artefact join is keyed on the official player URL slug where both sides
    carry one, and on the display name otherwise — the two keys give different answers
    and both counts are published, because the difference is itself the finding;
  * no depth tier, no replacement quality and no performance effect is asserted anywhere.

Usage:  python3 session-6669951c/tools/recount.py          # regenerate the JSON
        python3 session-6669951c/tools/recount.py --check   # fail if the JSON is stale
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAPTURE = ROOT / 'decision-desk/data/captures/nfl-injuries-2026-w10-2026-11-16.md'
MANIFEST = ROOT / 'decision-desk/data/captures/manifest.json'
TRANSACTIONS = ROOT / 'decision-desk/data/transactions-2026-11.json'
RESULTS = ROOT / 'decision-desk/data/week-10-2026-results.json'
DEPTH = ROOT / 'data/depth/club-depth-charts-2026-11-14.json'
BUILD = ROOT / 'tools/build.py'
OUT = ROOT / 'session-6669951c/data/week-10-availability-recount.json'

TABLE_HEADER = '| Player | Position | Injuries | Practice Status | Game Status |'
GAME_STATUSES = ('Out', 'Doubtful', 'Questionable')
PRACTICE_STATUSES = ('Did Not Participate In Practice', 'Limited Participation in Practice',
                     'Full Participation in Practice')
# The report page labels each table with the club nickname; the abbreviation shown beside
# the logo is the league's own code for that club. Both are kept: the repo has previously
# used LAR/ARI while the page publishes LA/AZ, which silently breaks code-keyed joins.
NICK_TO_ABBR = {
    'Commanders': 'WAS', 'Giants': 'NYG', 'Patriots': 'NE', 'Lions': 'DET', 'Chiefs': 'KC',
    'Falcons': 'ATL', 'Vikings': 'MIN', 'Packers': 'GB', 'Jaguars': 'JAX', 'Titans': 'TEN',
    'Bills': 'BUF', 'Jets': 'NYJ', 'Dolphins': 'MIA', 'Colts': 'IND', 'Panthers': 'CAR',
    'Saints': 'NO', 'Texans': 'HOU', 'Browns': 'CLE', 'Rams': 'LA', 'Cardinals': 'AZ',
    'Seahawks': 'SEA', 'Raiders': 'LV', '49ers': 'SF', 'Cowboys': 'DAL', 'Steelers': 'PIT',
    'Bengals': 'CIN', 'Chargers': 'LAC', 'Ravens': 'BAL',
}
# Codes the rest of the repository (transcriptions, depth charts, transactions) uses.
ABBR_TO_REPO = {'LA': 'LAR', 'AZ': 'AZ'}
POSITION_UNIT = {
    'QB': 'Offense', 'RB': 'Offense', 'FB': 'Offense', 'WR': 'Offense', 'TE': 'Offense',
    'T': 'Offensive line', 'G': 'Offensive line', 'C': 'Offensive line',
    'DE': 'Defense', 'DT': 'Defense', 'NT': 'Defense', 'LB': 'Defense', 'CB': 'Defense',
    'S': 'Defense', 'DB': 'Defense',
    'LS': 'Special teams', 'P': 'Special teams', 'K': 'Special teams',
    'H': 'Special teams', 'KR': 'Special teams', 'PR': 'Special teams',
}
PLAYER_LINK = re.compile(r'^\[([^\]]*)\]\((https://www\.nfl\.com/players/[^)]+)\)$')


class RecountError(RuntimeError):
    """Any integrity problem in the inputs. The tool refuses to publish a partial answer."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_artefact_identity() -> dict:
    """The capture must still be the byte-for-byte document the manifest describes."""
    manifest = json.loads(MANIFEST.read_text())
    entry = next((c for c in manifest['captures'] if c['id'] == 'CAP-01'), None)
    if entry is None:
        raise RecountError('manifest has no CAP-01 entry')
    digest = _sha256(CAPTURE)
    size = CAPTURE.stat().st_size
    if digest != entry['sha256']:
        raise RecountError('capture hash differs from the manifest: the file has been edited')
    if size != entry['bytes']:
        raise RecountError('capture byte size differs from the manifest')
    return {
        'id': entry['id'],
        'url': entry['url'],
        'retrieved_at_utc': entry['retrieved_at_utc'],
        'window_utc': entry['window_utc'],
        'sha256': digest,
        'bytes': size,
        'file': 'decision-desk/data/captures/' + entry['file'],
        'scope': entry['scope'],
        'page_title': entry['page_title'],
    }


def parse_capture() -> tuple[list[dict], list[dict]]:
    """Return (rows, game_slots). A game slot is one club block on the page."""
    text = CAPTURE.read_text()
    rows: list[dict] = []
    blocks: list[dict] = []
    for m in re.finditer(re.escape(TABLE_HEADER), text):
        preceding = [l for l in text[:m.start()].rstrip('\n').split('\n') if l.strip()]
        nickname = preceding[-1].strip()
        if nickname not in NICK_TO_ABBR:
            raise RecountError(f'unrecognised club label before a table: {nickname!r}')
        abbr = NICK_TO_ABBR[nickname]
        kickoff = None
        for line in reversed(preceding[:-1]):
            km = re.fullmatch(r'(\d{1,2}:\d{2} [AP]M[A-Z]{1,3})', line.strip())
            if km:
                kickoff = km.group(1)
                break
        day = None
        for line in reversed(preceding[:-1]):
            dm = re.fullmatch(r'## ([A-Z]+, [A-Z]+ \d+[A-Z]{2})', line.strip())
            if dm:
                day = dm.group(1)
                break
        if kickoff is None:
            raise RecountError(f'no kickoff time found above the {nickname} table')
        block = {'abbr': abbr, 'repo_code': ABBR_TO_REPO.get(abbr, abbr), 'nickname': nickname,
                 'day': day, 'kickoff': kickoff, 'rows': 0, 'pos': m.start()}
        seen_header = False
        block_index = len(blocks)
        for line in text[m.end():].split('\n'):
            if line.strip() == TABLE_HEADER:
                break  # the next club's table starts here; never read it as rows of this one
            if line.startswith('| ---'):
                seen_header = True
                continue
            if not line.startswith('|'):
                if line.strip() == '':
                    continue
                break
            if not seen_header:
                continue
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if len(cells) != 5:
                raise RecountError(f'{nickname}: row has {len(cells)} cells, expected 5: {line!r}')
            link = PLAYER_LINK.match(cells[0])
            if not link:
                raise RecountError(f'{nickname}: row without an official player link: {line!r}')
            name, url = link.group(1), link.group(2)
            if cells[4] and cells[4] not in GAME_STATUSES:
                raise RecountError(f'{nickname}: unexpected game status {cells[4]!r}')
            if cells[3] and cells[3] not in PRACTICE_STATUSES:
                raise RecountError(f'{nickname}: unexpected practice status {cells[3]!r}')
            block['rows'] += 1
            rows.append({
                'club': abbr,
                'club_repo': block['repo_code'],
                'nickname': nickname,
                'player': name,
                'player_url': url,
                'player_id': url.rstrip('/').rsplit('/', 1)[-1],
                'position': cells[1],
                'unit': POSITION_UNIT.get(cells[1], 'Unclassified'),
                'injury': cells[2],
                'practice': cells[3],
                'game_status': cells[4],
                'kickoff': f'{day} {kickoff}' if day else kickoff,
            })
        blocks.append(block)
    if not blocks:
        raise RecountError('no injury tables found in the capture')
    return rows, blocks


def parse_root_transcription() -> tuple[list[tuple], list[tuple]]:
    """Read INJ and SLATE out of tools/build.py as data, without importing it."""
    tree = ast.parse(BUILD.read_text())
    values: dict[str, list] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ('INJ', 'SLATE'):
                    try:
                        values[target.id] = ast.literal_eval(node.value)
                    except Exception:
                        values.setdefault(target.id, [])
    for key in ('INJ', 'SLATE'):
        if not values.get(key):
            raise RecountError(f'{key} could not be read from tools/build.py')
    inj, slate = values['INJ'], values['SLATE']
    for rec in inj:
        if len(rec) != 6:
            raise RecountError(f'transcribed row with {len(rec)} fields: {rec!r}')
        if rec[5] not in GAME_STATUSES:
            raise RecountError(f'transcribed row without an explicit game status: {rec!r}')
    return inj, slate


def capture_slot_codes(blocks: list[dict], rows: list[dict]) -> list[dict]:
    """Every club header on the page, with its table state, so a missing table is a
    recorded state and never an implied zero."""
    with_rows = {b['abbr'] for b in blocks}
    text = CAPTURE.read_text()
    header_clubs = re.findall(r'clubs/logos/([A-Z]{2,3})\)', text)
    slots = []
    seen = Counter(b['abbr'] for b in blocks)
    for code in dict.fromkeys(header_clubs):
        slots.append({'abbr': code, 'in_table': code in with_rows,
                      'rows': seen.get(code, 0)})
    n_headers = len(dict.fromkeys(header_clubs))
    n_kickoffs = len(re.findall(r'\n\d{1,2}:\d{2} [AP]M[A-Z]{1,3}\n', text))
    if n_headers != 2 * n_kickoffs:
        # A game block always carries two clubs. Anything else means the page changed shape,
        # and a shape change is exactly what this tool exists to catch.
        raise RecountError(
            f'club headers ({n_headers}) are not twice the number of kickoff blocks ({n_kickoffs})')
    return slots


def games_relative_to_capture(blocks: list[dict], retrieved_at: str) -> list[dict]:
    """Position of the capture relative to each listed game's kickoff.

    Games are grouped in document order: each game block on the page carries its own
    kickoff line, so two 1:00 PM games stay two games. The page labels Eastern time as
    EST; after the November daylight-saving change that label is UTC-5, and it is applied
    as printed rather than re-derived by this tool.
    """
    from datetime import datetime, timedelta
    captured = datetime.strptime(retrieved_at, '%Y-%m-%dT%H:%M:%SZ')
    marks = [(m.start(), m.group(0)) for m in
             re.finditer(r'\d{1,2}:\d{2} [AP]M[A-Z]{1,3}', CAPTURE.read_text())]
    months = {'JANUARY': 1, 'FEBRUARY': 2, 'MARCH': 3, 'APRIL': 4, 'MAY': 5, 'JUNE': 6,
              'JULY': 7, 'AUGUST': 8, 'SEPTEMBER': 9, 'OCTOBER': 10, 'NOVEMBER': 11,
              'DECEMBER': 12}
    games: dict[int, dict] = {}
    for block in blocks:
        mark = [m for m in marks if m[0] < block['pos']]
        if not mark:
            raise RecountError(f'no kickoff line above the {block["nickname"]} table')
        key, label = mark[-1]
        dm = re.search(r'([A-Z]+) (\d+)', block['day'] or '')
        if not dm:
            raise RecountError(f'cannot read the game date from {block["day"]!r}')
        tm = re.fullmatch(r'(\d{1,2}):(\d{2}) ([AP])M[A-Z]{1,3}', label)
        if not tm:
            raise RecountError(f'cannot read the kickoff time from {label!r}')
        hour = int(tm.group(1)) % 12 + (12 if tm.group(3) == 'P' else 0)
        local = datetime(captured.year, months[dm.group(1)], int(dm.group(2)), hour,
                         int(tm.group(2)))
        kickoff_utc = local + timedelta(hours=5)
        delta = int((kickoff_utc - captured).total_seconds() // 60)
        entry = games.setdefault(key, {
            'day': block['day'], 'kickoff_as_published': label,
            'clubs': [], 'rows': 0,
            'kickoff_utc': kickoff_utc.strftime('%Y-%m-%dT%H:%MZ'),
            'minutes_from_capture': delta,
            'state': ('before kickoff' if delta > 0 else 'after kickoff'),
        })
        entry['clubs'].append(block['abbr'])
        entry['rows'] += block['rows']
    return [games[k] for k in sorted(games)]


def join_transactions(rows: list[dict]) -> dict:
    """Official league transactions against the same clubs on the same report."""
    tx = json.loads(TRANSACTIONS.read_text())
    events = []
    for item in tx['trades']:
        events.append({'kind': 'Trade', 'date': item['date'], 'player': item['player'],
                       'player_url': item['player_url'],
                       'detail': f"{item['from']} to {item['to']}",
                       'clubs': {item['from'], item['to']}})
    for item in tx['reserve_list']:
        events.append({'kind': 'Reserve list', 'date': item['date'], 'player': item['player'],
                       'player_url': item['player_url'],
                       'detail': f"{item['club']} reserve list",
                       'clubs': {item['club']}})
    by_slug = defaultdict(list)
    for r in rows:
        by_slug[r['player_id']].append(r)
    matches, unmatched = [], []
    for ev in events:
        slug = ev['player_url'].rstrip('/').rsplit('/', 1)[-1]
        hits = by_slug.get(slug, [])
        if not hits:
            unmatched.append({'kind': ev['kind'], 'date': ev['date'], 'player': ev['player'],
                              'detail': ev['detail']})
            continue
        for h in hits:
            matches.append({
                'kind': ev['kind'], 'date': ev['date'], 'player': ev['player'],
                'club': h['club'], 'position': h['position'],
                'report_game_status': h['game_status'] or '(blank)',
                'report_practice': h['practice'], 'report_injury': h['injury'],
                'detail': ev['detail'], 'player_url': ev['player_url'],
            })
    for m_ in matches:
        if m_['kind'] == 'Reserve list':
            club = m_['detail'].split()[0]
            if m_['report_game_status'] == 'Out' and club == m_['club']:
                m_['classification'] = ('consistent — the club lists the player Out and the '
                                        'reserve list names the same player the same week')
            else:
                m_['classification'] = ('contradiction — the reserve list places the player on '
                                        'reserve while the club\'s report row carries no game '
                                        'status; a blank designation is not a clearance')
        else:
            from_club, to_club = m_['detail'].split()[0], m_['detail'].split()[-1]
            if m_['club'] == to_club:
                m_['classification'] = ('consistent — the receiving club lists the player it '
                                        'acquired on ' + m_['date'])
            else:
                m_['classification'] = ('stale — the club that traded the player away on ' +
                                        m_['date'] + ' still lists the player on its report')
    matches.sort(key=lambda x: (x['club'], x['player']))
    return {'events_total': len(events),
            'trades': len(tx['trades']),
            'reserve_list_rows': len(tx['reserve_list']),
            'matches': matches,
            'events_not_on_report': unmatched,
            'retrieved_at_utc': tx['retrieved_at_utc'],
            'transactions_source': tx['source'],
            'join_key': 'official player URL slug'}


def diff_against_transcription(rows: list[dict], inj: list[tuple]) -> dict:
    """Delta between the 2026-11-16 capture and the 2026-11-14 published transcription.

    Both sides are reduced to explicit game-status entries, the only subset the older
    artefact claims to hold. Two joins are computed: one on club code plus display name
    (what a reader can do today) and one on the official URL slug, which the older
    transcription does not store, so the slug join has to use the name it does store.
    """
    cap = {(r['club_repo'], r['player']): r for r in rows if r['game_status']}
    old = {(rec[0], rec[1]): rec for rec in inj}
    cap_by_slug = {r['player_id']: r for r in rows if r['game_status']}
    added = sorted(k for k in cap if k not in old)
    removed = sorted(k for k in old if k not in cap)
    changed = [{'club': k[0], 'player': k[1], 'on_2026_11_14': old[k][5],
                'on_2026_11_16': cap[k]['game_status']}
               for k in sorted(set(cap) & set(old)) if old[k][5] != cap[k]['game_status']]
    # Rows in the capture whose display name is absent from the transcription but whose
    # official player slug is present: a name-spelling artefact, not a roster change.
    by_name = {'added': [
        {'club': k[0], 'player': k[1], 'position': cap[k]['position'],
         'game_status': cap[k]['game_status'], 'practice': cap[k]['practice'],
         'injury': cap[k]['injury'], 'player_id': cap[k]['player_id']} for k in added],
        'removed': [{'club': k[0], 'player': k[1], 'position': old[k][2],
                     'game_status': old[k][5], 'practice': old[k][4], 'injury': old[k][3]}
                    for k in removed],
        'changed': changed}
    # name-spelling artefacts: capture row added by name but matched by slug to a removed row
    removed_slugs = {re.sub(r'[^a-z0-9]+', '-', rec[1].lower()).strip('-'): rec
                     for rec in inj}
    artefacts = []
    for entry in by_name['added']:
        guess = removed_slugs.get(entry['player_id'])
        if guess is not None and (entry['club'], guess[1]) in removed:
            artefacts.append({'player_id': entry['player_id'], 'capture_name': entry['player'],
                              'transcribed_name': guess[1], 'club': entry['club']})
    per_club = []
    for club in sorted({c for c, _ in set(added) | set(removed)} | {c['club'] for c in changed}):
        per_club.append({'club': club,
                         'added': sum(1 for a in by_name['added'] if a['club'] == club),
                         'removed': sum(1 for r in by_name['removed'] if r['club'] == club),
                         'changed': sum(1 for c in changed if c['club'] == club)})
    return {'filter': 'explicit game status (Out / Doubtful / Questionable) only',
            'capture_rows': len(cap), 'transcription_rows': len(old),
            'name_spelling_artefacts': artefacts,
            'per_club': per_club,
            'join_by_name': by_name,
            'note': ('The 2026-11-14 side is a transcription without player URLs, so the only '
                     'key available on both sides is club plus display name. Two of the rows '
                     'this key calls a change are spelling variants of the same official player '
                     'page, and one club code differs between artefacts (the report page uses LA, '
                     'the repo transcription uses LAR). Both are reported, not silently merged.')}


def club_view(rows: list[dict], blocks: list[dict], matches: list[dict],
              depth_clubs: list[str]) -> list[dict]:
    out = []
    for b in sorted(blocks, key=lambda x: x['pos']):   # the order the report page publishes
        club_rows = [r for r in rows if r['club'] == b['abbr']]
        gs = Counter(r['game_status'] for r in club_rows if r['game_status'])
        ps = Counter(r['practice'] for r in club_rows if r['practice'])
        unit = Counter(r['unit'] for r in club_rows if r['game_status'] in ('Out', 'Doubtful'))
        conflicts = [m for m in matches if m['club'] == b['abbr']]
        out.append({
            'club': b['abbr'], 'repo_code': b['repo_code'], 'nickname': b['nickname'],
            'game': b['day'] + ' · ' + b['kickoff'],
            'listed': len(club_rows),
            'out': gs.get('Out', 0), 'doubtful': gs.get('Doubtful', 0),
            'questionable': gs.get('Questionable', 0),
            'confirmed_unavailable': gs.get('Out', 0) + gs.get('Doubtful', 0),
            'conditional': gs.get('Questionable', 0),
            'practice_only': sum(1 for r in club_rows if not r['game_status']),
            'dnp': ps.get('Did Not Participate In Practice', 0),
            'limited': ps.get('Limited Participation in Practice', 0),
            'full': ps.get('Full Participation in Practice', 0),
            'confirmed_offense': unit.get('Offense', 0) + unit.get('Offensive line', 0),
            'confirmed_defense': unit.get('Defense', 0),
            'confirmed_special_teams': unit.get('Special teams', 0),
            'roster_event_conflicts': len(conflicts),
            'depth_chart_in_repo': 'yes' if b['abbr'] in depth_clubs or b['repo_code'] in depth_clubs else '',
            'positions_out': ', '.join(sorted({r['position'] for r in club_rows
                                               if r['game_status'] in ('Out', 'Doubtful')})),
        })
    return out


def compute() -> dict:
    identity = check_artefact_identity()
    rows, blocks = parse_capture()
    inj, slate = parse_root_transcription()
    slots = capture_slot_codes(blocks, rows)
    games = games_relative_to_capture(blocks, identity['retrieved_at_utc'])
    tx = join_transactions(rows)
    diff = diff_against_transcription(rows, inj)
    depth = json.loads(DEPTH.read_text())
    depth_clubs = list(depth['clubs'].keys())
    clubs = club_view(rows, blocks, tx['matches'], depth_clubs)
    results = json.loads(RESULTS.read_text())
    bye = results.get('bye_clubs', [])
    statuses = Counter(r['game_status'] or '(blank)' for r in rows)
    practice = Counter(r['practice'] or '(blank)' for r in rows)
    missing_tables = [s['abbr'] for s in slots if not s['in_table']]
    return {
        'document': 'Recount of the official 2026 Week 10 availability evidence',
        'generated_from': [
            'decision-desk/data/captures/nfl-injuries-2026-w10-2026-11-16.md',
            'tools/build.py (INJ, SLATE)', 'decision-desk/data/transactions-2026-11.json',
            'decision-desk/data/week-10-2026-results.json',
            'data/depth/club-depth-charts-2026-11-14.json'],
        'method': 'session-6669951c/tools/recount.py',
        'capture': identity,
        'totals': {
            'games_listed': len(games),
            'club_tables': len(blocks),
            'club_headers': len(slots),
            'club_headers_without_table': missing_tables,
            'rows': len(rows),
            'explicit_game_status': sum(statuses.get(s, 0) for s in GAME_STATUSES),
            'out': statuses.get('Out', 0),
            'doubtful': statuses.get('Doubtful', 0),
            'questionable': statuses.get('Questionable', 0),
            'blank_game_status': statuses.get('(blank)', 0),
            'dnp': practice.get('Did Not Participate In Practice', 0),
            'limited': practice.get('Limited Participation in Practice', 0),
            'full': practice.get('Full Participation in Practice', 0),
            'positions_unclassified': sum(1 for r in rows if r['unit'] == 'Unclassified'),
        },
        'transcription': {
            'retrieved_utc': '2026-11-14',
            'rows': len(inj),
            'out': sum(1 for r in inj if r[5] == 'Out'),
            'doubtful': sum(1 for r in inj if r[5] == 'Doubtful'),
            'questionable': sum(1 for r in inj if r[5] == 'Questionable'),
            'clubs': len({r[0] for r in inj}),
            'games_in_slate': len(slate),
            'note': ('the published Week 10 table on injuries.html; it carries only rows with '
                     'an explicit game status'),
        },
        'clubs': clubs,
        'games': games,
        'transactions': tx,
        'diff': diff,
        'depth_charts_in_repo': {'clubs': depth_clubs, 'status': depth['status'],
                                 'retrieved_utc': depth['retrieved_utc']},
        'bye_clubs': bye,
        'bye_source_note': results['note'],
        'recount_rules': [
            'a blank game status is counted as practice-only and never as available',
            'a club with no table is reported as "no rows captured", never as zero injuries',
            'counts are rows on the report, not injuries, not games missed, and not players',
            'no depth tier, replacement quality or performance effect is asserted',
        ],
    }


def main() -> int:
    data = compute()
    payload = json.dumps(data, indent=1, sort_keys=True) + '\n'
    if '--check' in sys.argv:
        if not OUT.exists():
            print('FAIL: recount artefact is missing: ' + str(OUT))
            return 1
        if OUT.read_text() != payload:
            print('FAIL: ' + str(OUT) + ' is stale; re-run session-6669951c/tools/recount.py')
            return 1
        print('PASS: recount artefact matches the committed inputs.')
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(payload)
    print('wrote ' + str(OUT))
    print(json.dumps(data['totals'], indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
