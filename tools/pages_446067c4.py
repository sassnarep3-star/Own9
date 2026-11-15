"""Session 446067c4 — official recheck, decision-readiness table and new review flags.

Exec'd by tools/build.py with the shared helpers (page, table, row, e, PAGES, ROOT, INJ, json).
Every number on these pages is computed at build time from a committed file. Nothing here
is typed in as an observation except the official rows in data/recheck/, which carry their
read date and source link.
"""
import json
from collections import Counter

RECHECK = json.loads((ROOT / 'data/recheck/nfl-injury-w10-clubs-read-2026-11-15.json').read_text())
SCHED = json.loads((ROOT / 'data/recheck/nfl-schedule-w10-read-2026-11-15.json').read_text())
W10 = json.loads((ROOT / 'evidence/results/nfl-2026-week10.json').read_text())
RESULTS = json.loads((ROOT / 'evidence/results/nfl-2026-results.json').read_text())
STRATS = json.loads((ROOT / 'origination/data/strategies.json').read_text())
REPORT = json.loads((ROOT / 'origination/data/report.json').read_text())
STORE_446 = json.loads((ROOT / 'data/snapshots/2026-w10-price-snapshot.json').read_text())
DEPTH_EVID = json.loads((ROOT / 'evidence/depth-charts/club-depth-charts-2026-w10.json').read_text())
DEPTH_DATA = json.loads((ROOT / 'data/depth/club-depth-charts-2026-11-14.json').read_text())
LINEUPS = json.loads((ROOT / 'evidence/lineups/was-nyg-2026-week-9-10.json').read_text())

RECHECK_SRC = 'nfl-injury-recheck-2026-11-15'
SCHED_SRC = 'nfl-sched-w10-recheck-2026-11-15'
ALL_32 = {'ARI', 'ATL', 'BAL', 'BUF', 'CAR', 'CHI', 'CIN', 'CLE', 'DAL', 'DEN', 'DET', 'GB', 'HOU',
          'IND', 'JAX', 'KC', 'LAC', 'LAR', 'LV', 'MIA', 'MIN', 'NE', 'NO', 'NYG', 'NYJ', 'PHI',
          'PIT', 'SEA', 'SF', 'TB', 'TEN', 'WAS'}
ALIAS = {'AZ': 'ARI', 'LA': 'LAR'}


def _norm_team(t):
    return ALIAS.get(t, t)


# ---------------------------------------------------------------------------
# 1. Official re-read compared with the repository's explicit-status table
# ---------------------------------------------------------------------------
REPO_INJ = {}
for _t, _p, _pos, _inj, _prac, _game in INJ:
    REPO_INJ[(_t, _p)] = (_pos, _inj, _prac, _game)

_official_rows = []     # (club, player, pos, inj, prac, game, repo_verdict)
_explicit_total = 0
_explicit_match = 0
_blank_conflicts = 0
for _club, _block in RECHECK['clubs'].items():
    for _p, _pos, _inj, _prac, _game in _block['rows']:
        _repo = REPO_INJ.get((_club, _p))
        if _game:
            _explicit_total += 1
            if _repo == (_pos, _inj, _prac, _game):
                _verdict = 'Match'
                _explicit_match += 1
            elif _repo is None:
                _verdict = 'Not in repo table'
            else:
                _verdict = f'Mismatch: repo shows {_repo[3]!r}'
        else:
            if _repo is None:
                _verdict = 'Blank in both'
            else:
                _verdict = 'Mismatch: repo shows a game status'
                _blank_conflicts += 1
        _official_rows.append((_club, _p, _pos, _inj, _prac, _game, _verdict))

_repo_clubs_checked = {c for c in RECHECK['clubs']}
_official_rows_total = len(_official_rows)

# ---------------------------------------------------------------------------
# 2. Official schedule read compared with the repository's Week 10 file
# ---------------------------------------------------------------------------
_repo_games = {(g['away'], g['home']): g for g in W10['games']}
_sched_rows = []
_official_final = 0
_repo_final = sum(1 for g in W10['games'] if g['status'] == 'FINAL')
for _g in SCHED['games']:
    _rg = _repo_games.get((_g['away'], _g['home']))
    if _g['status'] == 'FINAL':
        _official_final += 1
    _repo_status = _rg['status'] if _rg else 'absent'
    if _g['status'] == 'NOT READ':
        _cmp = 'Not read on 15 Nov'
    elif _g['status'] == 'FINAL' and _repo_status == 'FINAL':
        _cmp = 'Match'
    elif _g['status'] == 'FINAL':
        _cmp = f'Mismatch: repo still {_repo_status}'
    else:
        _cmp = f'Mismatch: repo {_repo_status}; official {_g["status"]}'
    _score = '' if _g['away_score'] is None else f"{_g['away_score']}–{_g['home_score']}"
    _sched_rows.append((f"{_g['away']} @ {_g['home']}", _g['status'], _score, _repo_status, _cmp))

_official_live = sum(1 for g in SCHED['games'] if g['status'].startswith('LIVE'))
_official_unread = sum(1 for g in SCHED['games'] if g['status'] == 'NOT READ')
_w10_mismatches = sum(1 for r in _sched_rows if r[4].startswith('Mismatch'))

# ---------------------------------------------------------------------------
# 3. Derived figures for the decision-readiness table (all read from committed files)
# ---------------------------------------------------------------------------
_feed_games = sum(len(w['games']) for w in RESULTS['weeks'].values())
_feed_weeks = sorted(int(k) for k in RESULTS['weeks'])
_markets = STORE_446['markets']
_closes = sum(1 for m in _markets if m.get('closed_at'))
_withdrawn = sum(1 for m in _markets if m.get('withdrawn_close_stamp'))
_priced = sum(1 for m in _markets if m.get('market_line') is not None)
_scored = {k: v['signal'] for k, v in STRATS.items() if 'log_loss_gain_lcb' in v.get('signal', {})}
_lcbs = [v['log_loss_gain_lcb'] for v in _scored.values()]
_positive_lcb = sum(1 for x in _lcbs if x > 0)
_bets_taken = sum(1 for v in STRATS.values() if (v.get('taken') or 0) > 0)
_regs = sum(1 for v in STRATS.values() if 'registration_commit' in v or 'registered_commit' in v)
_change_mind = sum(1 for v in STRATS.values() if 'what_would_change_our_mind' in v or 'change_our_mind' in v)
_depth_charts = set(DEPTH_EVID['charts']) | set(DEPTH_DATA['clubs'])
_depth_charts = {_norm_team(t) for t in _depth_charts}
_depth_missing = sorted(ALL_32 - _depth_charts)
_joint = REPORT['joint']
_gamebook_games = len(LINEUPS['games'])
_completed_official = _feed_games + _official_final
_sum_lcb_min = min(_lcbs) if _lcbs else None
_sum_lcb_max = max(_lcbs) if _lcbs else None

# Verify the constant claims this module makes about its inputs; fail the build if they drift.
assert len(_feed_weeks) == 9 and _feed_games == 136, (len(_feed_weeks), _feed_games)
assert len(_markets) == 52, len(_markets)
assert len(_depth_charts) + len(_depth_missing) == 32
assert _withdrawn == 52 and _closes == 0 and _priced == 0


def _pct_count(n, d):
    return f'{n} of {d}'


# ---------------------------------------------------------------------------
# 4. Page: official recheck
# ---------------------------------------------------------------------------
_recheck_notice = (
    '<div class="notice"><strong>Partial re-read, measured against the repository</strong><p>'
    f'The official Week 10 report was read again on 15 Nov 2026 for four complete club tables '
    f'(WAS, NYG, NE, DET): {_official_rows_total} player rows. Of the {_explicit_total} rows carrying an '
    f'explicit game status, {_explicit_match} match the repository table exactly. Blank-status rows '
    f'in these clubs conflicting with the repository: {_blank_conflicts}. Not re-read: chunks 2 to 8, '
    'so the published whole-report counts (254 or 279 rows; 4 or 2 no-injury sections) and the '
    'Seattle and Cincinnati rows are not re-verified here. The sandbox shell cannot reach nfl.com, '
    'so this read used the fetch tool and has no byte-level hash. Flagged as F61 and F62.</p></div>'
)

_lions_note = (
    '<div class="notice"><strong>Lions game-status cells (VR-08, VR-12)</strong><p>'
    'Kerby Joseph (S), Cade Mays (C) and D.J. Reed (CB) are printed as <em>Out</em> in the official '
    'Game Status column on 15 Nov 2026. The repository table carries the same three entries as Out. '
    'The blank cells from the earlier audit are no longer present in the repository table.</p></div>'
)

_recheck_rows = [
    row([club, p, pos, inj or '', prac, game or '', verdict],
        (RECHECK_SRC, 'repo'), 'Official re-read · compared')
    for club, p, pos, inj, prac, game, verdict in _official_rows
]

_kickoff_rows = [
    row(['KC @ ATL', 'Sunday 15 Nov, "1:00 PMEST" as printed', '18:00 UTC (EST is UTC−5)',
         'The bot stamp (19:31 UTC) came 91 minutes after this kickoff.'],
        (RECHECK_SRC, 'repo'), 'Official page + store record'),
    row(['NE @ DET', 'Sunday 15 Nov, "9:30 AMEST" as printed', '14:30 UTC',
         'The bot stamp came about five hours after this kickoff.'],
        (RECHECK_SRC, 'repo'), 'Official page + store record'),
]

_sched_table_rows = [
    row([g, st, sc or '', rs, cmp], (SCHED_SRC, 'repo'), 'Official schedule read · compared')
    for g, st, sc, rs, cmp in _sched_rows
]

_recheck_summary = [
    row(['Official rows re-read (4 complete clubs)', str(_official_rows_total), 'Chunk 1 of 8 only'], (RECHECK_SRC,), 'Official re-read'),
    row(['Explicit-status rows matched to repo', _pct_count(_explicit_match, _explicit_total), 'Exact match on position, injury, practice and game status'], (RECHECK_SRC, 'repo'), 'Compared'),
    row(['Week 10 games FINAL, official schedule read', _pct_count(_official_final, len(SCHED['games'])),
         f'{_official_live} live (Q4) and {_official_unread} not read on 15 Nov'], (SCHED_SRC,), 'Official schedule read'),
    row(['Week 10 games FINAL in the repository file', _pct_count(_repo_final, len(W10['games'])),
         f'{_w10_mismatches} official status values differ from the repository file'], ('repo',), 'Compared'),
]

_recheck_content = (
    _recheck_notice + _lions_note
    + table('Re-read summary', ['Measure', 'Value', 'Scope'], _recheck_summary)
    + table('Kickoff times used for the close-stamp withdrawal', ['Game', 'Kickoff as printed', 'UTC', 'Consequence'], _kickoff_rows)
    + table('Official Week 10 schedule read on 15 Nov 2026', ['Game (away @ home)', 'Official status', 'Score (away–home)', 'Repository Week 10 file', 'Comparison'], _sched_table_rows)
    + table('Official player rows re-read (WAS, NYG, NE, DET)', ['Club', 'Player', 'Position', 'Injuries', 'Practice status', 'Game status', 'Repository table'], _recheck_rows)
    + '<p class="download">Context: <a href="markets.html">Close-stamp withdrawal</a> · '
      '<a href="flags.html">Flagged for Review</a> · <a href="availability.html">Availability tracker</a>.</p>'
)

page('injury-recheck.html', 'Official recheck',
     'Week 10 re-read, row by row.',
     'Read on 15 Nov 2026 from the official NFL pages, then compared with the repository. Partial by design: '
     'four clubs and the Week 10 schedule. Nothing here fills a blank in the repository.',
     _recheck_content)

# ---------------------------------------------------------------------------
# 5. Decision-readiness table on the overview (one row per requirement)
# ---------------------------------------------------------------------------
_readiness = [
    row(['Price-snapshot store: opening and closing numbers for every originated market',
         f'{len(_markets)} markets opened with model fair numbers only; {_priced} market prices; {_closes} valid closes; {_withdrawn} bot stamps withdrawn',
         'No official market-price source or archive (F01, F42). The close bot now writes nothing for an unpriced market (F58).',
         'All 52 markets with a priced open and a priced pre-kickoff close, each with a source and a raw hash'],
        ('repo', 'nfl-injury-recheck-2026-11-15'), 'Store record · gate'),
    row(['Verified results feed for backtests and ROI',
         f'{_feed_games} official finals in the versioned feed (weeks {_feed_weeks[0]}–{_feed_weeks[-1]}); Week 10 file holds {_repo_final} of {len(W10["games"])} as FINAL, the official schedule read shows {_official_final} (F60)',
         'Week 10 finals not ingested. Ingesting them changes the origination inputs, so a new versioned feed is needed first.',
         'Every completed 2026 game in one versioned feed, each with a per-game official link'],
        ('repo', SCHED_SRC), 'Results feed · gate'),
    row(['Origination order: side, then total, then moneyline',
         '13 spreads → 13 totals → 26 moneylines, emitted in that order',
         'None. The order is enforced in code and tested.',
         'Already met'],
        ('repo',), 'Origination contract · tested'),
    row(['Fair line, market line and difference as separate columns',
         f'{len(_markets)} fair values; {_priced} market lines; {_priced} differences',
         'The market-price gate above',
         '52 market lines, each with a capture time and source'],
        ('repo',), 'Market board · gate'),
    row(['Signal separated from staking in the leaderboard',
         f'Separated in the desk. {_positive_lcb} of {len(_scored)} scored strategies have a positive clustered lower bound on log-loss gain (range {_sum_lcb_min:.3f} to {_sum_lcb_max:.3f}); {len(STRATS) - _bets_taken} of {len(STRATS)} entries have no bets',
         'No strategy has a positive signal bound, and no priced market exists to stake against',
         'A positive clustered lower bound, with n and a holdout, on a strategy registered before its window'],
        ('repo',), 'Leaderboard · gate'),
    row(['Demotion gate: a live strategy goes back to paper',
         f'Implemented. {sum(1 for v in STRATS.values() if (v.get("taken") or 0) > 0)} strategies with bets; 0 live strategies; minimum 20 graded bets before any decision',
         'No live strategy exists',
         'A live strategy reaching 20 graded bets'],
        ('repo',), 'Demotion gate · implemented'),
    row(['Pre-registration: definition frozen by a commit before results are seen',
         f'{_regs} of {len(STRATS)} strategy entries carry a registration commit',
         'No commit records a definition before the evaluation window; the desk scored its strategies on the 2010–2026 history in the repository',
         'A commit hash per strategy, dated before its evaluation window'],
        ('repo',), 'Strategy registry · gate'),
    row(['Two-sided "what would change our mind" on every strategy',
         f'{_change_mind} of {len(STRATS)} strategy entries',
         'The field is not in the registry',
         f'{len(STRATS)} of {len(STRATS)} entries with both sides written before the window'],
        ('repo',), 'Strategy registry · gate'),
    row(['Correlations from official numbers, with n published',
         f'n is published on every correlation value; joint pricing: parlays {_joint["parlay_priced"]} of {_joint["parlay_offered"]} priced, same-game parlays {_joint["sgp_priced"]} of {_joint["sgp_offered"]} priced',
         'The same-game-parlay interval straddles the predeclared deadband, so the gate refuses to price it',
         'An interval clear of the deadband for each joint price offered'],
        ('repo',), 'Correlation gate · refused'),
    row(['Injury-report time series: captured daily from Wednesday to kickoff, with clock time',
         '1 full Week 10 read dated 14 Nov 2026 (day only, no clock time) and 1 partial re-read on 15 Nov (four clubs); no scheduled injury-capture job exists (F62)',
         'No capture job, no hashes, no clock times',
         'Daily captures Wednesday to Sunday for one full week, each with a clock time and a raw hash'],
        ('repo', 'nfl-injury'), 'Capture record · gate'),
    row(['Official Game Books for actual starters, inactives and game-day status',
         f'{_gamebook_games} Game Books read (Weeks 9–10); {_gamebook_games} of {_completed_official} official finals',
         'Game Books have not been captured for the other finals',
         f'{_completed_official} of {_completed_official} completed games'],
        ('repo', 'nfl-gamebook-w10'), 'Game Book evidence · gate'),
    row(['Snap counts (playing time as the starter proxy)',
         '0 snap-count records in the repository',
         'No official snap-count capture',
         'Snap counts for every completed 2026 game'],
        ('repo',), 'Evidence record · gate'),
    row(['Official depth-chart register with date and source per row',
         f'{len(_depth_charts)} of 32 clubs have a club-site chart, all self-labelled unofficial; {len(_depth_missing)} clubs have none; 0 official NFL depth charts (the NFL depth-chart route returns a 404)',
         'No authorised official source for depth order',
         '32 of 32 clubs from an official source, with date and source on each row'],
        ('repo', 'nfl-depth-chart-404'), 'Depth register · gate'),
    row(['Venue of every fixture, from the official game centre',
         '0 venues transcribed from the game centre; data/raw/games.csv has a location column of unknown provenance (F01)',
         'No game-centre transcription has been done',
         '272 regular-season fixtures (32 clubs × 17 games ÷ 2)'],
        ('repo', 'nfl-sched-w10'), 'Venue record · gate'),
    row(['Roof, surface and NWS hourly weather overlay',
         '0 official roof designations and 0 weather forecasts captured for 2026 games; roof and surface columns exist in data/raw/games.csv of unknown provenance',
         'No official roof capture and no NWS forecast capture',
         'Official roof and surface for each game, plus the NWS hourly forecast at kickoff'],
        ('repo',), 'Overlay record · gate'),
    row(['Injury designation reliability, measured before use as a feature',
         '0 seasons joined to official inactive lists',
         'No archived past-season designations',
         'At least one full season joined, with a confidence interval per designation'],
        ('repo',), 'Reliability record · gate'),
    row(['Archive of past-season weekly injury reports',
         '0 past-season report archives in the repository',
         'Archives not captured',
         'At least one complete past season, each report with a clock time and hash'],
        ('repo',), 'Archive record · gate'),
    row(['Injury-hub reads stored with clock time, publishing the change, not the level',
         '2 reads: the 14 Nov full report (dated to the day) and the 15 Nov partial re-read; 0 changes measured',
         'Only one read exists',
         'At least two clock-timed reads of the same report'],
        ('repo',), 'Capture record · gate'),
    row(['Roster turnover as a versioned event',
         '0 roster events in a dated register',
         'No roster-event register',
         'A dated 2026 register of trades, releases and reserve moves'],
        ('repo', 'nfl-transactions'), 'Roster record · gate'),
    row(['Model output stored as a probability plus its inputs',
         f'{len(_markets)} fair numbers; 0 per-row probabilities; inputs hashed at store level only',
         'The store schema has no per-row probability field',
         '52 of 52 rows with a probability and an input hash'],
        ('repo',), 'Store schema · gate'),
    row(['Point-in-time ledger with clock times',
         'Store timestamps are dates only, e.g. "2026-11-14 (UTC, store deployment)" (F64)',
         'Clock times are not recorded',
         'A UTC clock time on every open and close row'],
        ('repo',), 'Store schema · gate'),
]

_readiness_intro = (
    '<div class="notice"><strong>Decision readiness, one row per requirement</strong><p>'
    'Each number is computed at build time from a committed file. The gate column names what blocks the '
    'requirement; the last column names the measurable number that would clear it. Nothing here is a '
    'performance claim, and no requirement is marked met unless its test or record exists in the repository.</p></div>'
)
_readiness_block = (
    _readiness_intro
    + table('Decision readiness', ['Requirement', 'Measured now', 'Gate that blocks it', 'Number that would clear it'], _readiness)
)

_index_entry = PAGES['index.html']
PAGES['index.html'] = (*_index_entry[:3], _readiness_block + _index_entry[3])

# ---------------------------------------------------------------------------
# 6. Flags for review (new, F58–F66)
# ---------------------------------------------------------------------------
_flags_rows = [
    row(['F58 · Critical',
         'The close bot stamped all 52 Week 10 markets "closed · pre-kickoff capture" with no market price. The stamp (19:31 UTC) came after the 1:00 PM ET kickoff of KC @ ATL.',
         'Stamps withdrawn (closed_at null; kept as withdrawn_close_stamp). tools/snapshot_close.py writes nothing for an unpriced market. Real closes need priced captures before kickoff.',
         'Withdrawn · open for the priced-capture requirement'],
        ('repo', 'nfl-injury-recheck-2026-11-15'), 'Corrected in this session'),
    row(['F59 · High',
         'The quality gate was red on main: test_committed_store_matches_regeneration failed because the bot had changed the committed store and the test still expected every market open. The bot commit (39d8649) triggered the Pages build but no "Research quality" run, so the failure was not reported.',
         'Test now checks the committed store against withdraw_close_stamp(originate(...)); added tests for the withdrawal and for the refusal of unpriced closes. Regenerated pages committed.',
         'Fixed on this branch; CI result recorded in COORDINATION.md'],
        ('repo',), 'Corrected in this session'),
    row(['F60 · High',
         f'The repository Week 10 results file holds {_repo_final} of 14 games as FINAL. The official schedule, read 15 Nov 2026, shows {_official_final} FINAL, {_official_live} live and {_official_unread} not read.',
         'A new versioned results feed for 2026 weeks 10 onward. Ingesting into the origination feed would change its input hash, so it is not done in place.',
         'Open'],
        ('repo', SCHED_SRC), 'Open'),
    row(['F61 · High',
         'The Week 10 injury re-read covers four of 32 clubs (44 rows; chunk 1 of 8). The whole-report counts (254 or 279 rows, 4 or 2 no-injury sections) and the Seattle and Cincinnati rows are not re-verified.',
         'Full re-read of all eight chunks, with a raw hash and a clock time per read. Blocked on the capture job in F62.',
         'Open · partial re-read published'],
        (RECHECK_SRC, 'repo'), 'Open'),
    row(['F62 · High',
         'No scheduled capture of the official injury report exists. The only scheduled workflow captures prices. The sandbox shell cannot reach nfl.com, so this session could not create a hashed raw capture.',
         'A capture workflow that writes raw bytes, a clock time and a hash on every run, tested in GitHub Actions on Wednesday to Sunday before it is relied on.',
         'Open'],
        ('repo', 'nfl-injury'), 'Open'),
    row(['F63 · Medium',
         'markets.html stated a close workflow schedule of "Sunday 16:45 UTC and daily 16:00 UTC". The workflow file runs at 14:00 UTC daily and 23:30 UTC on Thursdays.',
         'Text corrected to match the workflow file in this session. The file is the source of truth.',
         'Corrected in this session'],
        ('repo',), 'Corrected in this session'),
    row(['F64 · Medium',
         'Store timestamps are dates only ("2026-11-14 (UTC, store deployment)"). A pre-kickoff claim cannot be checked from the store alone.',
         'Clock times in UTC on every open and close, with the source time from the workflow run.',
         'Open'],
        ('repo',), 'Open'),
    row(['F65 · Medium',
         'Pull request #38 (arena/22de6677-own9, "Add pinned, all-section citation coverage audit") is open and was created by another session. It was not reviewed or changed here.',
         'Owner decision: merge, rebase or close.',
         'Open · outside this session'],
        ('repo',), 'Open'),
    row(['F66 · Medium',
         'The sandbox shell cannot reach nfl.com (TLS handshake fails). Official pages were read only through the fetch tool. Read results are recorded with their read date and no byte-level hash.',
         'A capture that runs where nfl.com is reachable, such as the workflow in F62.',
         'Limitation · recorded'],
        ('nfl-injury-recheck-2026-11-15',), 'Limitation'),
]

_flags_entry = PAGES['flags.html']
PAGES['flags.html'] = (*_flags_entry[:3],
                       _flags_entry[3]
                       + '<h2>Session 446067c4 findings (15 Nov 2026)</h2>'
                       + table('Session 446067c4 register', ['ID / severity', 'Finding', 'Required evidence / disposition', 'State'], _flags_rows))
