"""Read-only access to the market/score snapshot committed in the repository.

Both files are inputs, never outputs. Nothing in this module invents a value:
every field it returns is read from the bytes on disk, and the files' upstream
provenance is unconfirmed, which is published as a flag rather than repaired.
"""

import csv
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GAMES_CSV = ROOT / 'data' / 'raw' / 'games.csv'
LINES_CSV = ROOT / 'data' / 'raw' / 'closing_lines.csv'

# 2016-2018 club abbreviations differ between the two committed snapshots.
ALIASES = {'LA': 'LAR', 'SD': 'LAC', 'OAK': 'LV'}


def norm(team):
    """Normalise a club abbreviation to the post-relocation code."""
    return ALIASES.get(team, team)


def sha256(path):
    digest = hashlib.sha256()
    digest.update(Path(path).read_bytes())
    return digest.hexdigest()


def load_games():
    with GAMES_CSV.open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def load_lines():
    with LINES_CSV.open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def regular_season(rows):
    return [r for r in rows if r['game_type'] == 'REG']


def played(rows):
    """Games with both final scores present in the snapshot."""
    return [r for r in rows if r['home_score'] != '' and r['away_score'] != '']


def scored_games():
    """Regular-season games with final scores, sorted chronologically."""
    rows = played(regular_season(load_games()))
    rows.sort(key=lambda r: (int(r['season']), int(r['week']), r['gameday'], r['game_id']))
    return rows


def all_regular_games():
    rows = regular_season(load_games())
    rows.sort(key=lambda r: (int(r['season']), int(r['week']), r['gameday'], r['game_id']))
    return rows


def market_fields(row):
    """Return the recorded market numbers for a game row, or None fields.

    A blank string means the snapshot records no value. Nothing is imputed.
    """
    def num(value):
        return None if value in ('', None) else float(value)

    return {
        'spread_line': num(row.get('spread_line', '')),      # +ve means home favoured
        'total_line': num(row.get('total_line', '')),
        'home_moneyline': num(row.get('home_moneyline', '')),
        'away_moneyline': num(row.get('away_moneyline', '')),
        'home_spread_odds': num(row.get('home_spread_odds', '')),
        'away_spread_odds': num(row.get('away_spread_odds', '')),
        'over_odds': num(row.get('over_odds', '')),
        'under_odds': num(row.get('under_odds', '')),
    }
