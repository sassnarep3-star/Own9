"""Parse a verbatim NFL injury-report capture into structured rows.

Nothing here invents a value. Every field comes from a line of the committed capture
or is left as the empty string, which the pages render as "not published".
"""
from __future__ import annotations

import hashlib
import sys
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAPTURES = ROOT / 'data' / 'captures'

#: Abbreviation -> club, read off the club links published on the report page.
TEAM_LINK = re.compile(r'https://www\.nfl\.com/teams/([a-z0-9\-]+)/\) ([A-Z]{2,3}) \[([^\]]+)\]')
DAY = re.compile(r'^## ([A-Z]+DAY), ([A-Z]+) (\d+)(?:ST|ND|RD|TH)$')
TIME = re.compile(r'^(\d+:\d+ [AP]M)EST$')
ROW = re.compile(r'^\| \[([^\]]+)\]\(([^)]+)\) \| ([^|]*?) \| ([^|]*?) \| ([^|]*?) \| ([^|]*?) \|$')


def team_map(text: str) -> dict:
    """Club name -> (published abbreviation, club slug), both read off the page."""
    out = {}
    for slug, abbr, name in TEAM_LINK.findall(text):
        out[name] = (abbr, slug)
    return out


def parse(path: Path) -> dict:
    raw = path.read_bytes()
    text = raw.decode('utf-8')
    teams = team_map(text)
    rows, day, kickoff, network, current = [], None, None, None, None
    seen_team = set()
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = DAY.match(line)
        if m:
            day = f'{m.group(1).title()}, {m.group(2).title()} {m.group(3)}'
            continue
        m = TIME.match(line)
        if m:
            kickoff = m.group(1)
            network = next((x.strip() for x in lines[i + 1:i + 4] if x.strip()), '')
            continue
        # A club name is the bare heading line immediately followed by a table header,
        # and it must be one of the abbreviations published on the page.
        stripped = line.strip()
        nxt = next((x for x in lines[i + 1:i + 4] if x.strip()), '')
        if stripped in teams and nxt.startswith('| Player'):
            current = stripped
            seen_team.add(stripped)
            continue
        m = ROW.match(line)
        if m and current:
            player, url, pos, inj, pract, game = m.groups()
            rows.append({
                'game_day': day,
                'kickoff_et': kickoff,
                'network': network,
                'team': teams[current][0],
                'team_name': current,
                'team_slug': teams[current][1],
                'player': player.strip(),
                'player_url': url,
                'position': pos.strip(),
                'injury': inj.strip(),
                'practice_status': pract.strip(),
                'game_status': game.strip(),
            })
    return {
        'file': path.name,
        'sha256': hashlib.sha256(raw).hexdigest(),
        'bytes': len(raw),
        'teams_published': sorted(seen_team),
        'rows': rows,
    }


def main() -> None:
    out = {}
    for p in sorted(CAPTURES.glob('*.md')):
        out[p.stem] = parse(p)
    dest = ROOT / 'data' / 'parsed' / 'injury_captures.json'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2, sort_keys=True) + '\n')
    for stem, d in out.items():
        print(stem, d['bytes'], 'bytes', len(d['rows']), 'rows', len(d['teams_published']), 'clubs',
              'sha256=' + d['sha256'][:12])


if __name__ == '__main__':
    sys.exit(main())
