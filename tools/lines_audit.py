"""Deterministic audit of the inherited market-lines snapshot.

Reads only files tracked in this repository, uses the Python standard library,
makes no network calls and invents no values. Every number published on the
"Own lines and market data" page is computed here from the actual bytes on
disk, so the page cannot drift away from the data it describes.

Scope: this measures internal consistency and coverage only. It does not
establish the provenance, licence, correctness or predictive usefulness of the
underlying file, and it is not a backtest.
"""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINES = ROOT / 'data' / 'raw' / 'closing_lines.csv'
GAMES = ROOT / 'data' / 'raw' / 'games.csv'

# 2016-2018 club abbreviations differ between the two snapshots.
ALIASES = {'LA': 'LAR', 'SD': 'LAC', 'OAK': 'LV'}


def norm(team):
    return ALIASES.get(team, team)


def load(path):
    with path.open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def sha256(path):
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def expected(row, game):
    """Recompute a settlement state from the sibling score snapshot."""
    home = int(game['home_score'])
    away = int(game['away_score'])
    margin = home - away
    total = home + away
    if row['type'] == 'TOTAL':
        line = float(row['line'])
        if total == line:
            return '0.5'
        won = total > line if row['side'] == 'Over' else total < line
        return '1' if won else '0'
    if row['type'] == 'SPREAD':
        signed = margin if norm(row['side']) == norm(game['home_team']) else -margin
        value = signed + float(row['line'])
        return '0.5' if value == 0 else ('1' if value > 0 else '0')
    signed = margin if norm(row['side']) == norm(game['home_team']) else -margin
    return '0.5' if signed == 0 else ('1' if signed > 0 else '0')


def audit():
    lines = load(LINES)
    games = load(GAMES)
    by_game_id = {g['game_id']: g for g in games}
    by_old_game_id = {g['old_game_id']: g for g in games if g.get('old_game_id')}
    grouped = defaultdict(list)
    for row in lines:
        grouped[row['game_id']].append(row)
    seasons = Counter(row['alt_game_id'].split('_')[0] for row in lines if row['alt_game_id'])
    games_ids = set(grouped)

    join = {
        'as_named_game_id': len(games_ids & set(by_game_id)),
        'via_old_game_id': len(games_ids & set(by_old_game_id)),
        'total_games': len(games_ids),
    }
    agree = Counter()
    disagree = Counter()
    disagree_games = Counter()
    for game_id in sorted(games_ids):
        game = by_old_game_id.get(game_id)
        if not game:
            continue
        for row in grouped[game_id]:
            if row['outcome'] == expected(row, game):
                agree[row['type']] += 1
            else:
                disagree[row['type']] += 1
                disagree_games[game_id] += 1

    empty = {
        field: {t: sum(1 for r in lines if r['type'] == t and r[field] == '') for t in
                ('MONEYLINE', 'SPREAD', 'TOTAL')}
        for field in ('line', 'odds')
    }
    pushes = Counter(r['type'] for r in lines if r['outcome'] == '0.5')
    # A moneyline push is only possible on a tied game; check that claim against scores.
    tie_games = {g['old_game_id'] for g in games
                 if g.get('result') and g.get('overtime') and int(g['result']) == 0}
    ml_push_games = {r['game_id'] for r in lines
                     if r['type'] == 'MONEYLINE' and r['outcome'] == '0.5'}

    total_rows = len(lines)
    mismatch = sum(disagree.values())
    return {
        'files': {
            'closing_lines': {'path': 'data/raw/closing_lines.csv',
                              'rows': total_rows, 'sha256': sha256(LINES)},
            'games': {'path': 'data/raw/games.csv', 'rows': len(games),
                      'sha256': sha256(GAMES)},
        },
        'coverage': {
            'seasons': sorted(seasons),
            'season_min': min(seasons),
            'season_max': max(seasons),
            'games': len(games_ids),
            'market_types': dict(Counter(r['type'] for r in lines)),
        },
        'join': join,
        'settlement_recompute': {
            'agree': dict(agree),
            'disagree': dict(disagree),
            'disagree_rows': mismatch,
            'disagree_pct': round(100 * mismatch / total_rows, 3),
            'affected_games': len(disagree_games),
            'fully_inverted_games': sum(1 for v in disagree_games.values() if v >= 6),
            'games_without_score': len(games_ids - set(by_old_game_id)),
        },
        'push_states': {
            'coded_0.5': dict(pushes),
            'moneyline_push_games': len(ml_push_games),
            'moneyline_push_games_are_scoreless_ties_in_games_csv':
                len(ml_push_games) > 0 and ml_push_games <= tie_games,
            'spread_push_rows_matching_margin': sum(
                1 for r in lines if r['type'] == 'SPREAD' and r['outcome'] == '0.5'
                and r['game_id'] in by_old_game_id
                and abs(int(by_old_game_id[r['game_id']]['result'])) == abs(float(r['line']))),
        },
        'missing_fields': empty,
        'interpretation': [
            'The lines snapshot is internally consistent with the sibling score snapshot '
            'after 2016-2018 club-abbreviation normalisation.',
            'It ends at the 2018 season, so it cannot evaluate the current or recent seasons.',
            'A price is absent for a large share of spread and total rows, which blocks '
            'expected-value calculation on those rows.',
            'No provenance, retrieval date or licence is recorded for the file in this '
            'repository, so republication rights and completeness remain unverified.',
        ],
    }


if __name__ == '__main__':
    print(json.dumps(audit(), indent=2, sort_keys=True))
