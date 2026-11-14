"""Verified results feed: the only scores this project will settle a bet against.

Why this exists
---------------
A backtest, an ROI, a closing-line-value number and a demotion trigger are all functions of
*what actually happened*, matched to *what the price was*. Without a results feed there is
nothing to score predictions against, so every one of those quantities is undefined — not
small, not noisy, undefined. This module builds the feed and the verification that makes the
word "verified" mean something here.

Verification is a procedure, not a label
---------------------------------------
A result enters the feed as `verified` only when it clears checks that are run against the
data itself, all of them reproducible with `python3 -m engine.results`:

1. `publisher` — the source URL is on a league host in `engine.snapshots.LEAGUE_HOSTS`.
2. `dual_rendering` — the official page exposes each game twice (the match-link label, and
   the per-team points cells with a winner indicator). Both renderings must agree.
3. `winner_consistency` — the winner indicator sits on the higher score, and a level score is
   reported as a tie, never assigned to one side.
4. `single_appearance` — a club appears at most once in a week's slate.
5. `record_progression` — the team records printed on week N and week N+1 reconcile with the
   games completed between the two retrievals, for every club, including those on bye.
6. `winning_pct` — where a second official page prints a win percentage, it equals
   (wins + 0.5 x ties) / games to the published precision.

Anything that fails a check is kept and reported as `unverified`, with the failed check named.
Deleting a bad row would make the feed look cleaner and the evidence worse.

The same discipline is applied to the repository's historical score snapshot
(`data/raw/games.csv`, 7,548 rows): it is *not* admitted. It carries no per-game official
source, no retrieval timestamp and no confirmed licence, so it can supply arithmetic test
inputs and nothing else. That asymmetry is the point of the gate.
"""
import json
from pathlib import Path

from engine.snapshots import LEAGUE_HOSTS, SnapshotError
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
FEED = ROOT / 'evidence' / 'results'
WEEK8 = FEED / '2026-week-8-standings.json'
WEEK9 = FEED / '2026-week-9-final-scores.json'
WEEK10 = FEED / '2026-week-10-status.json'

STATUSES = ('final', 'scheduled', 'in_progress', 'postponed', 'cancelled')
MARKETS = ('SPREAD', 'TOTAL', 'MONEYLINE')


class ResultError(ValueError):
    pass


def load(path):
    return json.loads(Path(path).read_text())


def points(value, field):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ResultError(f'{field} must be a non-negative integer, got {value!r}')
    return value


def _parse_label(label, away, home):
    """Parse the official link label 'Rams 20, Commanders 13, FINAL, Sunday, November 8th'.

    Returns (away_points, home_points, status) or None when the label does not carry a score,
    which is exactly what an unplayed game looks like on the page.
    """
    parts = [p.strip() for p in str(label).split(',')]
    if len(parts) < 2:
        return None
    numbers = []
    for head in parts[:2]:
        tokens = head.split()
        digits = [t for t in tokens if t.isdigit()]
        if len(digits) != 1:
            return None
        numbers.append(int(digits[0]))
    status = next((p for p in parts if p.upper() in ('FINAL', 'FINAL/OT')), None)
    return (numbers[0], numbers[1], 'final') if status else (numbers[0], numbers[1], None)


def winning_percentage(record):
    """(W + T/2) / G, at the three-digit precision the league prints."""
    wins, losses, ties = _split(record)
    games = wins + losses + ties
    if games == 0:
        return None
    return round((wins + 0.5 * ties) / games, 3)


def _split(record):
    """Parse a league record string. The page prints '3-6' and omits the ties term when it is zero,
    so two components are a complete record here, not a truncated one."""
    parts = str(record).split('-')
    if len(parts) not in (2, 3):
        raise ResultError(f'unparsable record {record!r}')
    try:
        wins, losses = int(parts[0]), int(parts[1])
    except ValueError:
        raise ResultError(f'unparsable record {record!r}')
    ties = int(parts[2]) if len(parts) == 3 else 0
    return wins, losses, ties


def page_form(wins, losses, ties):
    """Render a record the way the source page renders it, so comparisons are like for like."""
    return f'{wins}-{losses}' if ties == 0 else f'{wins}-{losses}-{ties}'


def check(game):
    """Per-game verification: the page must corroborate itself before the feed trusts it."""
    checks = []
    url = str(game.get('source_url', ''))
    host = urlsplit(url).hostname
    host_ok = host in LEAGUE_HOSTS and urlsplit(url).scheme == 'https'
    checks.append({'name': 'publisher', 'pass': bool(host_ok),
                   'note': f'source host {host} is a league host' if host_ok
                           else f'source host {host!r} is not a league host'})

    away, home = game['away_abbr'], game['home_abbr']
    parsed = _parse_label(game.get('link_label', ''), away, home)
    if parsed and parsed[2] == 'final':
        a_pts, h_pts, _ = parsed
        cells = (game.get('away_points'), game.get('home_points'))
        checks.append({'name': 'dual_rendering', 'pass': (a_pts, h_pts) == cells,
                       'note': f'link label says {a_pts}-{h_pts}, score cells say '
                               f'{cells[0]}-{cells[1]}'})
        indicator = game.get('winner_indicator')
        expected = away if cells[0] > cells[1] else home if cells[1] > cells[0] else None
        checks.append({'name': 'winner_consistency', 'pass': indicator == expected,
                       'note': f'winner indicator {indicator!r}, higher score {expected!r}'})
        try:
            points(game['away_points'], 'away_points')
            points(game['home_points'], 'home_points')
            checks.append({'name': 'score_types', 'pass': True,
                           'note': 'both scores are non-negative integers'})
        except ResultError as exc:
            checks.append({'name': 'score_types', 'pass': False, 'note': str(exc)})
    else:
        # A game that is not final has no score to corroborate. That is recorded as a limit on
        # what the feed may claim, and it is not counted as a pass.
        not_final = game.get('status') != 'final'
        checks.append({'name': 'dual_rendering', 'pass': not_final,
                       'note': 'no score printed on the page; game is not final'})
        checks.append({'name': 'winner_consistency', 'pass': game.get('winner_indicator') is None,
                       'note': 'no winner indicator printed for a game that is not final'})
        checks.append({'name': 'score_types', 'pass': not_final,
                       'note': 'status carries the claim, not a score'})
    return {'checks': checks, 'verified': all(c['pass'] for c in checks)}


def single_appearance(games):
    """A club may appear at most once *in a week*. Duplicates mean a transcription error.

    Grouped by week deliberately: a club obviously appears in both the Week 9 and the Week 10
    slate, and a check that ignores the week would report 30 false problems and hide a real one.
    """
    seen, problems = {}, []
    for game in games:
        for abbr in (game['away_abbr'], game['home_abbr']):
            seen.setdefault((game.get('season'), game.get('week'), abbr), []).append(game['game_id'])
    for (_season, week, abbr), ids in sorted(seen.items(), key=lambda kv: (str(kv[0][1]), kv[0][2])):
        if len(ids) > 1:
            problems.append(f'{abbr} appears in {len(ids)} games in week {week}: {", ".join(ids)}')
    return problems


def reconcile(before, after, games):
    """Expect every club's record on the later page to equal the earlier page plus `games`.

    `games` must be exactly the games completed *between* the two retrievals — for this feed, the
    Week 10 games played after the Week 9 page's records were printed. Passing both weeks in would
    apply a result twice and reconcile to a record no page ever printed.

    This is the corroboration that makes the feed more than one page's word: two retrievals of
    the standings, taken on different pages, have to be consistent with the results between them.
    Clubs on bye are included, so a silent schedule change would also show up here.
    """
    finals = [g for g in games if g.get('status') == 'final' and g.get('verified')]
    out = []
    for abbr, start in sorted(before.items()):
        wins, losses, ties = _split(start)
        for game in finals:
            if abbr not in (game['away_abbr'], game['home_abbr']):
                continue
            if game['winner_indicator'] == abbr:
                wins += 1
            elif game['winner_indicator'] is not None:
                losses += 1
            else:
                ties += 1
        expected = page_form(wins, losses, ties)
        actual = after.get(abbr)
        out.append({'abbr': abbr, 'before': start, 'expected_after': expected, 'actual_after': actual,
                    'pass': actual == expected})
    return out


def pct_check(standings_pct):
    """Every published win percentage must equal (W + T/2) / G to the printed precision."""
    out = []
    for abbr, item in sorted((standings_pct or {}).items()):
        computed = winning_percentage(item['record'])
        out.append({'abbr': abbr, 'record': item['record'], 'printed': item['printed_pct'],
                    'computed': computed,
                    'pass': computed is not None and abs(computed - item['printed_pct']) < 0.0005})
    return out


def verify_game(game):
    """Attach the per-game verification outcome to a copy of the record."""
    out = dict(game)
    result = check(game)
    out['verification'] = result
    out['verified'] = result['verified']
    return out


def _week8_card_checks():
    """Each Week 8 game card must show its own winner as the higher score.

    The Week 8 page is used here only to corroborate records, and it corroborates itself first.
    """
    data = load(WEEK8)
    out = []
    for game in data['week8_games']:
        expected = (game['away'] if game['away_points'] > game['home_points']
                    else game['home'] if game['home_points'] > game['away_points'] else None)
        out.append({'match': f"{game['away']} at {game['home']}",
                    'pass': game['winner'] == expected,
                    'note': f"{game['away_points']}-{game['home_points']}, winner {game['winner']}"})
    return out


def feed():
    """The published feed: Week 9 2026 finals plus the Week 10 slate, each verified.

    Corroboration runs in both directions around Week 9: the Week 8 page's records plus the Week 9
    results must reproduce the Week 9 page's records, and the Week 9 records plus the one completed
    Week 10 game must reproduce the Week 10 page's records. Two independent retrievals of the same
    standings, tied together by the games between them, is a stronger claim than any single page.
    """
    week8, week9, week10 = load(WEEK8), load(WEEK9), load(WEEK10)
    before8 = dict(week8['records_after'])
    before9 = dict(week9['records_after'])
    after9 = dict(week9['records_after'])
    after10 = dict(week10['records_after'])
    rows = [verify_game(dict(game, week=9, season=2026, page='week-9')) for game in week9['games']]
    rows += [verify_game(dict(game, week=10, season=2026, page='week-10'))
             for game in week10['games']]
    w9_rows = [r for r in rows if r['week'] == 9]
    duplicate_problems = single_appearance(rows)
    # Only games played *after* the earlier snapshot may move its records.
    progression_into_9 = reconcile(before8, after9, w9_rows)
    progression_into_10 = reconcile(before9, after10, [r for r in rows if r['week'] == 10])
    percentages = pct_check(week10.get('standings_pct'))
    cards = _week8_card_checks()
    excluded = {abbr: {'displayed_on_week8_page': rec,
                       'reason': 'on bye in Week 8, so it appears only in the page\u2019s bye block, '
                                 'which prints records as of retrieval rather than as of the week'}
                for abbr, rec in sorted(week8['bye_block_as_retrieved'].items())}
    # Attach the prior-week records so a correlation can be built from two official legs.
    for row in rows:
        # A Week 8 baseline exists only for clubs that appear on a Week 8 game card; the four clubs
        # in that page's bye block are excluded, because that block is not an as-of-week record.
        prior = {'away': before8.get(row['away_abbr']), 'home': before8.get(row['home_abbr'])}
        row['prior_records'] = prior if all(prior.values()) else {}
        row['prior_records_excluded'] = sorted(a for a, v in prior.items() if v is None) or None
    summary = {
        'games': len(rows),
        'final': sum(1 for r in rows if r['status'] == 'final'),
        'scheduled': sum(1 for r in rows if r['status'] == 'scheduled'),
        'verified': sum(1 for r in rows if r['verified']),
        'unverified': sum(1 for r in rows if not r['verified']),
        'checks_run': sum(len(r['verification']['checks']) for r in rows),
        'checks_failed': sum(1 for r in rows for c in r['verification']['checks'] if not c['pass']),
        'duplicate_club_problems': duplicate_problems,
        'reconciliations': [
            {'name': 'week 8 records + week 9 results = week 9 records',
             'clubs_tested': len(progression_into_9),
             'clubs_agreeing': sum(1 for p in progression_into_9 if p['pass']),
             'clubs_excluded': sorted(excluded)},
            {'name': 'week 9 records + week 10 results = week 10 records',
             'clubs_tested': len(progression_into_10),
             'clubs_agreeing': sum(1 for p in progression_into_10 if p['pass']),
             'clubs_excluded': []},
        ],
        'week8_card_checks': {'run': len(cards),
                             'agreeing': sum(1 for c in cards if c['pass'])},
        'pct_checks': len(percentages),
        'pct_agreeing': sum(1 for p in percentages if p['pass']),
        'games_with_prior_records': sum(1 for r in rows if r['prior_records']),
        'week8_page': week8['source_url'],
        'week9_page': week9['source_url'], 'week10_page': week10['source_url'],
        'retrieved_utc': week10['retrieved_utc'],
        'bye_teams_week9': sorted(week9.get('bye_teams', {})),
        'bye_teams_week10': sorted(week10.get('bye_teams', {})),
    }
    return rows, summary, {'progression_into_9': progression_into_9,
                          'progression_into_10': progression_into_10,
                          'percentages': percentages, 'week8_cards': cards,
                          'week8_excluded': excluded}


def settle(market, side, line, game):
    """Settle one market side against a verified final. Returns 'win' | 'push' | 'loss' | None.

    Conventions are explicit because the repository's historical file does not document its own
    (see `data/raw/` findings F22-F24): `line` is the handicap the side *receives* for SPREAD,
    and the threshold the side is *over or under* for TOTAL.
    """
    if game.get('status') != 'final':
        return None
    if not game.get('verified'):
        raise SnapshotError('refusing to settle against an unverified result')
    away, home = points(game['away_points'], 'away_points'), points(game['home_points'], 'home_points')
    if market == 'MONEYLINE':
        own, other = (away, home) if side == 'AWAY' else (home, away)
        return 'win' if own > other else 'loss' if own < other else 'push'
    if line is None:
        return None
    own, other = (away, home) if side == 'AWAY' else (home, away)
    if market == 'SPREAD':
        margin = (own - other) + line
        return 'win' if margin > 0 else 'loss' if margin < 0 else 'push'
    if market == 'TOTAL':
        total = away + home
        if side == 'OVER':
            return 'win' if total > line else 'loss' if total < line else 'push'
        if side == 'UNDER':
            return 'win' if total < line else 'loss' if total > line else 'push'
        raise SnapshotError('TOTAL side must be OVER or UNDER')
    raise SnapshotError(f'unknown market {market!r}')


def settle_all(market, games):
    """Settle a whole week, reporting what could not be settled instead of skipping it."""
    out = []
    for game in games:
        for side in ('HOME', 'AWAY') if market != 'TOTAL' else ('OVER', 'UNDER'):
            line = (game.get('lines') or {}).get(market)
            out.append({'game_id': game['game_id'], 'side': side, 'line': line,
                        'result': settle(market, side, line, game) if line is not None else None})
    return out


def readiness(games=None, snapshot_audit=None):
    """What the feed can and cannot do right now, measured rather than asserted."""
    rows = feed()[0] if games is None else games
    finals = [g for g in rows if g['status'] == 'final']
    verified_finals = [g for g in finals if g['verified']]
    with_lines = [g for g in verified_finals if (g.get('lines') or {}).get('SPREAD') is not None]
    out = {
        'finals_in_feed': len(finals),
        'finals_verified': len(verified_finals),
        'finals_with_a_market_line': len(with_lines),
        'backtest_ready': bool(verified_finals) and bool(with_lines),
    }
    if snapshot_audit is not None:
        out['snapshots_priced'] = snapshot_audit['records_priced']
        out['snapshots_expected'] = snapshot_audit['expected_pairs']
        out['blocking_reasons'] = []
        if not verified_finals:
            out['blocking_reasons'].append('no verified finals in the feed')
        if not with_lines:
            out['blocking_reasons'].append(
                'no verified final has a market line attached, so there is nothing to compare a '
                'fair line with and no ROI denominator')
        if not snapshot_audit['records_priced']:
            out['blocking_reasons'].append(
                f"the snapshot store holds 0 priced records against {snapshot_audit['expected_pairs']} "
                'expected captures for this slate')
        out['roi_computable'] = bool(verified_finals) and bool(with_lines) and snapshot_audit[
            'records_priced'] > 0
    return out


def history_key(game):
    """`2026_09_LAR_WAS` - the identifier convention the repository score snapshot uses."""
    return "%s_%02d_%s_%s" % (game['season'], int(game['week']), game['away_abbr'], game['home_abbr'])


def read_history():
    """The repository's own score/line snapshot, keyed by its own ids, read-only.

    Loaded and never repaired: a blank score stays blank, because a snapshot that had not seen the
    game yet is the evidence that this file is a point-in-time dump rather than a results feed.
    """
    import csv
    path = ROOT / 'data' / 'raw' / 'games.csv'
    if not path.exists():
        return {}
    with path.open() as handle:
        return {row['game_id']: row for row in csv.DictReader(handle)}


def join_line_snapshot(games=None):
    """What the verified feed can actually reach for a price, counted rather than asserted.

    The repository's historical snapshot carries spread, total and moneyline columns, and it is not
    confined to old seasons - it holds 2026 rows too. That changes the shape of the gap from "no
    lines" to "lines whose capture time and stage are unrecorded", which is a different fix. The
    store cannot accept an undated, unlabelled number as an opening or closing price, so this
    reports how much of the slate has a *value* and how much has a *usable quote*.
    """
    rows = feed()[0] if games is None else games
    history = read_history()
    priced_fields = ('spread_line', 'total_line', 'home_moneyline', 'away_moneyline')
    joined = []
    for game in rows:
        match = history.get(history_key(game))
        joined.append({'game_id': game['game_id'], 'week': game['week'], 'status': game['status'],
                       'verified': game['verified'], 'in_history': match is not None,
                       'lines': {f: ((match or {}).get(f) or None) for f in priced_fields} if match else {},
                       'scored_in_history': bool(match and match.get('home_score')),
                       'quote_timestamp_present': False, 'stage_labelled': False})
    with_value = [j for j in joined if any(v for v in j['lines'].values())]
    return {
        'history_rows': len(history),
        'games_in_feed': len(joined),
        'games_joined_to_history': sum(1 for j in joined if j['in_history']),
        'games_with_a_line_value': len(with_value),
        'games_with_a_usable_quote': 0,
        'usable_quote_definition': 'a line value carrying both a capture timestamp and an open/close '
                                   'stage label; the snapshot records neither, so no row qualifies',
        'games_already_scored_in_history': sum(1 for j in joined if j['scored_in_history']),
        'note': 'the snapshot holds 2026 rows with line columns, including games already completed; '
                'under the store schema those are undated, unlabelled numbers, not quotes',
    }


if __name__ == '__main__':
    rows, summary, detail = feed()
    print(json.dumps({'summary': summary,
                      'readiness': readiness(rows),
                      'join': join_line_snapshot(rows),
                      'progression_mismatches': [p for key in ('progression_into_9',
                                                               'progression_into_10')
                                                 for p in detail[key] if not p['pass']],
                      'pct_mismatches': [p for p in detail['percentages'] if not p['pass']],
                      'failures': [{'game_id': r['game_id'],
                                    'failed': [c['name'] for c in r['verification']['checks']
                                               if not c['pass']]}
                                   for r in rows if not r['verified']]},
                     indent=2, sort_keys=True))
