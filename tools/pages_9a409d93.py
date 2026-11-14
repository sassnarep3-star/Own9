"""Session `arena/9a409d93-own9` — Week 10 price-snapshot store, replacement
chains, demotion gate, leaderboard signal/staking table, results-feed append.

Registered additively through the shared generator (same pattern as
`tools/pages_4f2e0291.py` and `tools/pages_a77d40e1.py`): nothing another
session published is rewritten. Session a77d40e1 (merged via PR #40) already
publishes the canonical results feed (`results-feed.html`), the market board,
the Week 11 snapshot store (`price-snapshots.html`), the official correlation
register (`correlations-official.html`) and the replacement-depth register, so
this module adds only what that session did not publish: the Week 10 store
opens captured before kickoff (`markets.html`), per-player replacement chains
from 19 club charts (`replacement-chains.html`), the quantitative demotion gate
(`demotion.html`), and append-only sections on `leaderboard.html` and
`results-feed.html`.

Every computed number on these pages is derived at build time from committed
evidence (the verified results feed, the snapshot store, the injury report, the
club depth charts) so the regeneration check in CI reproduces them exactly.
Market-line and difference columns stay blank on every row: the NFL publishes
no betting lines and no official market price source was obtained (F42).
"""
import json
import math
import statistics
from pathlib import Path

from engine.origination_elo import (load_results, run_elo, sample_stats, rolling_pf_pa,
                                    DEMOTION_THRESHOLDS, MARKET_ORDER)

RESULTS_PATH = ROOT / 'evidence/results/nfl-2026-results.json'
WEEK10_PATH = ROOT / 'evidence/results/nfl-2026-week10.json'
STORE_PATH = ROOT / 'data/snapshots/2026-w10-price-snapshot.json'
CHARTS_PATH = ROOT / 'evidence/depth-charts/club-depth-charts-2026-w10.json'

RESULTS = json.loads(RESULTS_PATH.read_text())
WEEK10 = json.loads(WEEK10_PATH.read_text())
STORE = json.loads(STORE_PATH.read_text())
CHARTS = json.loads(CHARTS_PATH.read_text())

GAMES = []          # (week, date, away, home, as, hs) in feed order
for _wk, _wdata in sorted(RESULTS['weeks'].items(), key=lambda kv: int(kv[0])):
    for _g in _wdata['games']:
        GAMES.append((int(_wk), _g[0], _g[1], _g[2], _g[3], _g[4]))
MARGINS = [h - a for _w, _d, _a, _h, a, h in GAMES]
TOTALS = [a + h for _w, _d, _a, _h, a, h in GAMES]
N_GAMES = len(GAMES)
TIE_COUNT = sum(1 for m in MARGINS if m == 0)
SIGMA = statistics.stdev(MARGINS)

_w10_final = [g for g in WEEK10['games'] if g['status'] == 'FINAL']
_w10_sched = [g for g in WEEK10['games'] if g['status'] != 'FINAL']
_store_markets = STORE['markets']
_type_counts = {t: sum(1 for m in _store_markets if m['market_type'] == t) for t in MARKET_ORDER}
_method_stats = STORE['meta']['method']['sample_stats']

_input_sha = STORE['meta']['inputs']['results_feed_sha256']


def _sha(path):
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fmt(x, nd=1):
    if x is None:
        return None
    return f'{x:.{nd}f}'


# ---------------------------------------------------------------------------
# replacement-depth derivation from club charts + the Week 10 report
# ---------------------------------------------------------------------------
def _norm(name):
    return (name.replace('\u2019', "'").replace('\u2018', "'")
                .replace('.', '').replace('  ', ' ').strip().lower())


def _name_match(inj_name, chart_name):
    a, b = _norm(inj_name), _norm(chart_name)
    if not a or not b:
        return False
    return a == b or a.startswith(b + ' ') or b.startswith(a + ' ')


_derived = []
_conflicts = []
for team, player, position, injury, practice, status in INJ:
    if status not in ('Out', 'Doubtful'):
        continue
    chart = CHARTS['charts'].get(team)
    if not chart:
        _conflicts.append((team, player, position, status,
                           'no retrievable club chart' if team == 'HOU'
                           else 'no chart retrieved this session (covered on injuries.html only)'
                                if team in ('KC', 'SEA', 'DET')
                           else 'no chart retrieved this session'))
        continue
    hit = None
    colist = None
    for ri, r in enumerate(chart['rows']):
        for pi, pname in enumerate(r[1:]):
            if not pname or pname in ('(blank slot-2)', '(next row)', '(empty first slot)'):
                continue
            if '/' in pname:
                if any(_name_match(player, side) for side in pname.split('/')):
                    colist = (ri, pi + 1, pname) if colist is None else 'ambiguous'
                continue
            if _name_match(player, pname):
                if hit is None:
                    hit = (ri, pi + 1, pname)   # absolute cell index in the row
                else:
                    hit = 'ambiguous'
    if hit is None:
        if colist is not None:
            _conflicts.append((team, player, position, status,
                               'co-listed tie inside one chart cell (A / B) — the chart publishes no next man up, so none is derived'
                               if colist != 'ambiguous' else
                               'name matches more than one co-listed chart cell — ambiguous, no chain derived'))
        else:
            _conflicts.append((team, player, position, status,
                               'no matching slot on the retrieved chart (dropped/IL/specialist row not published?) — no replacement inferred'))
        continue
    if hit == 'ambiguous':
        _conflicts.append((team, player, position, status,
                           'name matches more than one chart slot — ambiguous, no chain derived'))
        continue
    ri, pi, pname = hit
    crow = chart['rows'][ri]
    nxt = None
    for q in range(pi + 1, len(crow)):
        if crow[q] and crow[q] not in ('(blank slot-2)', '(next row)', '(empty first slot)'):
            nxt = crow[q]
            break
    if nxt is None:
        _conflicts.append((team, player, position, status,
                           'injured player is the last listed in their slot — no published next man up'))
        continue
    _derived.append({
        'team': team, 'player': player, 'position': position, 'status': status,
        'slot': crow[0], 'replacement': nxt, 'chart_date': chart.get('chart_date', 'no date printed on page'),
    })


def _ordinal(n):
    return {1: '1st', 2: '2nd', 3: '3rd'}.get(n, f'{n}th')


def _depth_label(team, slot, replacement):
    """Ordinal of `replacement` within all players listed under `slot` (its
    position label) on that club chart — the published tier, chart-relative."""
    chart = CHARTS['charts'][team]
    count = 0
    for r in chart['rows']:
        if r[0] != slot:
            continue
        for pname in r[1:]:
            if pname and pname not in ('(blank slot-2)', '(next row)', '(empty first slot)'):
                if _norm(pname) == _norm(replacement):
                    return f'{_ordinal(count + 1)} string (chart order)'
                count += 1
    return None


for d in _derived:
    d['depth'] = _depth_label(d['team'], d['slot'], d['replacement'])

_covered_teams = sorted({d['team'] for d in _derived})
_depth_counts = {}
for d in _derived:
    _depth_counts[d['depth']] = _depth_counts.get(d['depth'], 0) + 1

# ===========================================================================
# append-only augmentation of results-feed.html (canonical page from a77d40e1)
# — this session's Week 10 status, sample statistics and grading-readiness
# tables. The 136-game verbatim table is NOT duplicated here: the canonical
# page already renders the settled feed row by row with weekly-page links.
# ===========================================================================
_feed_stats = row([str(_method_stats['n_games']), _fmt(_method_stats['mean_total'], 2),
                   _fmt(_method_stats['mean_margin'], 2), _fmt(SIGMA, 2),
                   f'{TIE_COUNT} (rate {TIE_COUNT / N_GAMES:.4f})'],
                  ('repo',), 'Derived arithmetic from the feed above')
_results_feed_append = (
    table('Week 10 status — session arena/9a409d93-own9 (14 Nov 2026)',
          ['Item', 'Count', 'Note'], [
        row(['Completed', str(len(_w10_final)), 'WAS 24 @ NYG 21 (Thu 12 Nov) — final on the official Week 10 page'],
            ('repo', 'nfl-sched-w10'), 'Official schedule page'),
        row(['Scheduled, not yet played', str(len(_w10_sched)),
             'Kickoffs 15–16 Nov; the Week 10 snapshot store (markets.html) covers these 13 games'],
            ('repo', 'nfl-sched-w10'), 'Official schedule page'),
    ])
    + table('Sample statistics of the official feed (elo-v1 inputs, derived)',
            ['Games n', 'Mean total', 'Mean home margin', 'σ of margins', 'Ties'], [_feed_stats])
    + table('Grading readiness — what ROI/backtests still need',
            ['Requirement', 'State', 'Blocker if missing'], [
        row(['Executable market prices', '0 rows — no official or licensed price source exists',
             'Every market_line and diff column stays blank; ROI/CLV remain uncomputable (F01/F42)'],
            ('repo',), 'Project gap / no source'),
        row(['Settlement rules', 'Operator push conventions registered as context only',
             'A chosen grading operator and jurisdiction must be decided before any grade'],
            ('dk-markets', 'repo'), 'Operator context / decision pending'),
        row(['Point-in-time capture', 'Week 10 store opened 2026-11-14 pre-kickoff (open snapshots only so far)',
             'Close capture is scheduled via .github/workflows/snapshot.yml; earlier weeks were never captured'],
            ('repo',), 'Project record'),
        row(['Per-row re-check', 'Structural cross-checks pass (weekly counts, bye arithmetic, 32 teams)',
             'Independent game-centre re-check proposed as S-21 before any settlement use'],
            ('repo',), 'Verification scope'),
    ])
    + '<p class="download">Week 10 opens: <a href="markets.html">W10 snapshots</a> · '
      'live-discipline rules: <a href="demotion.html">Demotion gate</a>.</p>')
PAGES['results-feed.html'] = (*PAGES['results-feed.html'][:3],
                              PAGES['results-feed.html'][3] + _results_feed_append)

# ===========================================================================
# markets.html — price snapshot store
# ===========================================================================
_schema_rows = [
    row(['market_id', 'Stable per-market key (season-week-away-home-TYPE[-side]).', 'Deterministic join key across open and close snapshots.'], ('repo',), 'Store schema'),
    row(['model_fair', 'The model\u2019s fair number at the snapshot: fair home spread (points), fair total (points) or fair two-way American price.', 'Computed output of the elo-v1 method from official scores; unvalidated, no edge claim (F43).'], ('repo',), 'Store schema'),
    row(['market_line', 'The market\u2019s quoted number at the snapshot.', 'Always blank: no official market price source exists; never inferred (F01/F42).'], ('repo',), 'Store schema'),
    row(['diff', 'model_fair − market_line.', 'Blank whenever market_line is blank — the difference of an unavailable value is unavailable.'], ('repo',), 'Store schema'),
    row(['opened_at / closed_at', 'UTC timestamps of the open and close snapshots.', 'Open = store deployment (2026-11-14). Close = scheduled pre-kickoff capture; null until captured.'], ('repo',), 'Store schema'),
    row(['status', 'Snapshot lifecycle state.', 'open · close capture pending — for all 52 Week 10 markets at deployment.'], ('repo',), 'Store schema'),
]
_market_rows = []
for m in _store_markets:
    _market_rows.append(row(
        [m['market_id'], m['game'], m['market_type'], m['selection'],
         f"{m['model_fair']} ({m['model_fair_units']})",
         m['market_line'], m['diff'],
         m['opened_at'], m['closed_at'], m['status']],
        ('repo', 'nfl-sched-w10'), 'Store row / official slate'))
_order_row = row([' → '.join(f'{t} ({_type_counts[t]})' for t in MARKET_ORDER),
                  'Side first, then the total, then the moneyline — emitted in that fixed order',
                  'engine/origination.py enforces the order; a test fails if any total precedes a side or any moneyline precedes a total'],
                 ('repo',), 'Origination contract / tested')
_tnf_row = row(['WAS 24 @ NYG 21 (Thu 12 Nov) — FINAL',
                'Not originated: kickoff preceded store deployment (2026-11-14)',
                'No open or close can exist for a market the store never held (F46)'],
               ('repo', 'nfl-sched-w10'), 'Official schedule / store policy')

page('markets.html', 'W10 snapshots', 'Every market we originate, opened and closed.',
     'The price-snapshot store records opening and closing numbers for every market '
     'Own9 originates: the model\u2019s fair line, the market line, and their difference '
     'as separate columns. Market columns are blank by policy — no official market '
     'price exists — and never inferred.',
     '<div class="notice"><strong>Model outputs, not market prices</strong><p>The '
     'model_fair column is the deterministic output of the predeclared elo-v1 method '
     'computed from the verified official results feed. It is unvalidated and claims '
     'no edge; the market_line and diff columns are blank on every row because the NFL '
     'publishes no betting lines and no officially verifiable price archive was '
     'obtained (F01, F42). Acquiring that archive is suggestion S-17.</p></div>'
     + table('Store schema (data/snapshots/2026-w10-price-snapshot.json)',
             ['Field', 'Meaning', 'Policy'], _schema_rows)
     + table('Origination order (fixed)',
             ['Emission order this week', 'Rule', 'Enforcement'], [_order_row])
     + table('Week 10 2026 snapshot — 52 originated markets (open)',
             ['Market ID', 'Game', 'Type', 'Selection', 'Model fair', 'Market line', 'Diff',
              'Opened (UTC)', 'Closed (UTC)', 'Status'], _market_rows)
     + table('Markets not originated', ['Game', 'Why', 'Disposition'], [_tnf_row])
     + table('elo-v1 method (predeclared, computed from official scores only)',
             ['Input / constant', 'Value', 'Meaning'], [
         row(['Inputs', '136 verified final scores (weeks 1–9)',
              'Official schedule-page transcriptions only; no secondary feeds'],
             ('repo',), 'Official inputs'),
         row(['Elo start / K / HFA', '1500 / 20 / 50 Elo',
              'Predeclared conventions; HFA ≈ 2.0 points at the 25-Elo-per-point conversion'],
             ('repo',), 'Predeclared constants'),
         row(['MOV multiplier', 'ln(margin+1) × 2.2 ÷ (1 + 0.43 × rating gap / 400)',
              'Margins scale the update; ties update without a margin signal'],
             ('repo',), 'Predeclared convention'),
         row(['Fair spread', '(R_home + 50 − R_away) / 25', 'Points; negative = home gives points'],
             ('repo',), 'Formula'),
         row(['Fair total', 'shrink 0.5 × mean(PF/PA halves, last 4 games) + 0.5 × league mean total',
             'League mean total of the official sample: ' + _fmt(_method_stats['mean_total'], 2)],
             ('repo',), 'Formula / sample statistic'),
         row(['Fair moneylines', f'(1 − tie rate) × Φ(spread ÷ σ), σ = {_fmt(SIGMA, 2)} points',
              'Residual tie mass pushes; σ from the 136-game official sample (n published with it)'],
             ('repo', 'dk-markets'), 'Formula / settlement context'),
         row(['Sample stats (n = 136)', f"σ margin {_fmt(SIGMA, 2)} · mean total {_fmt(_method_stats['mean_total'], 2)} · "
              f"mean margin {_fmt(_method_stats['mean_margin'], 2)} · ties {TIE_COUNT}",
              'Published with every derived value; unvalidated in-sample statistics'],
             ('repo',), 'Sample statistics'),
     ])
     + table('Close-capture automation (no manual input; schedules the a77d40e1 F30 close-run gap for this store)',
             ['Piece', 'Behaviour', 'Guardrail'], [
         row(['tools/snapshot_close.py', 'Recomputes fair numbers at close from the same inputs and records closed_at before kickoff',
              'Refuses to overwrite an open row with a changed model id or input hash'],
             ('repo',), 'Project record'),
         row(['.github/workflows/snapshot.yml', 'Scheduled pre-kickoff Sunday 16:45 UTC and daily 16:00 UTC; commits only under data/snapshots/**',
              'Fails closed: a run with unexpected file changes aborts the commit'],
             ('repo',), 'Scheduled workflow'),
     ]))

# ===========================================================================
# replacement-depth.html — depth of the replacement
# ===========================================================================
_depth_rows = []
for d in sorted(_derived, key=lambda x: (x['team'], x['player'])):
    _depth_rows.append(row(
        [d['team'], f"{d['player']} ({d['status']})", f"{d['slot']} (chart slot)",
         d['replacement'], d['depth'] or '', d['chart_date']],
        ('repo', f"{d['team'].lower()}-depth"), 'Report + club chart / derived chain'))
_conflict_rows = [row([t, f'{p} ({pos}, {st})', reason], ('repo', 'nfl-injury-w10'),
                      'Report + chart conflict / withheld')
                  for t, p, pos, st, reason in _conflicts]
_absence_rows = [
    row(['HOU', 'Page titled "Unofficial Depth Chart" but no tabular chart rendered',
         'Checked absence recorded; no replacement inferred'], ('hou-depth-absence',), 'Checked absence'),
    row(['nfl.com', 'League depth-chart route 404s (verified 2026-11-04 and re-checked 14 Nov)',
         'Club sites are the only retrievable official-publisher charts'], ('nfl-no-depth-chart',), 'Checked absence'),
]
_cov_teams = sorted({r[0] for r in INJ if r[0] in CHARTS['charts']})
page('replacement-chains.html', 'Replacement chains', 'Not just who replaced — how deep.',
     'For every Week 10 Out/Doubtful player, the depth of the player who replaces them, '
     'derived only where a club-published depth chart places both players. Chains are '
     'chart-relative: club charts are self-labelled unofficial and mostly undated, so '
     'tiers are published order, not certified game-day depth.',
     '<div class="notice"><strong>How a chain is derived</strong><p>Replacement = the next '
     'player published after the injured player in their depth-chart slot row. Depth = that '
     'replacement\u2019s ordinal among the players listed at the same position label on the chart '
     '(e.g. second player at RB = \u201c2nd string (chart order)\u201d). Where the injured player is '
     'absent from the chart, tied in a co-listed cell, or last in the slot, no chain is derived '
     'and the row is published under conflicts with the reason — never resolved by inference. '
     'Chart-relative labels are weaker than certified game-day depth (F13, F44).</p></div>'
     + table(f'Derived replacement chains ({len(_depth_rows)} chains across {len(_covered_teams)} clubs)',
             ['Team', 'Unavailable player (report)', 'Chart slot', 'Replacement (chart order)',
              'Depth of replacement', 'Chart date'], _depth_rows)
     + table('Coverage of the Week 10 report',
             ['Clubs with Out/Doubtful players', 'Clubs with a derived chart chain', 'Clubs relying on the earlier three-chart evidence'], [
         row([str(len({r[0] for r in INJ if r[5] in ('Out', 'Doubtful')})),
              str(len(_covered_teams)),
              'KC, SEA, DET (published on injuries.html) + WAS via Game Book evidence'],
             ('nfl-injury-w10', 'repo'), 'Report coverage / derived arithmetic'),
     ])
     + table('Depth distribution of derived replacements',
             ['Depth label', 'Chains'], [row([k or 'unlabelled', str(v)], ('repo',), 'Derived counts')
                                         for k, v in sorted(_depth_counts.items())])
     + table('Conflicts and withheld chains (published, never reconciled)',
             ['Team', 'Player (report status)', 'Why no chain is derived'], _conflict_rows)
     + table('Checked absences', ['Source', 'Finding', 'Disposition'], _absence_rows)
     + '<p class="download">The two-week Game Book substitution evidence (who actually started, '
       'verified at the lineup level) remains on <a href="availability.html">Availability tracker</a>; '
       'the broad Week 10 slate and the first three club charts are on '
       '<a href="injuries.html">Injuries &amp; depth</a>; the source-level register is on '
       '<a href="availability-evidence.html">Availability sources</a>.</p>')

# ===========================================================================
# demotion.html — live → paper gate
# ===========================================================================
_th_rows = [row([k, str(v), _meaning], ('repo',), 'Predeclared threshold') for k, v, _meaning in [
    ('min_trailing_bets', DEMOTION_THRESHOLDS['min_trailing_bets'],
     'Below 20 trailing graded bets the gate refuses to decide (unmonitorable — fail-closed).'),
    ('roi_floor', DEMOTION_THRESHOLDS['roi_floor'],
     'Trailing-20 flat-stake ROI below −10% returns the strategy to paper.'),
    ('edge_floor', DEMOTION_THRESHOLDS['edge_floor'],
     'Trailing mean (model − market) edge ≤ 0 returns the strategy to paper.'),
    ('clv_rate_floor', DEMOTION_THRESHOLDS['clv_rate_floor'],
     'Closing-line value positive in fewer than 40% of trailing bets demotes.'),
    ('brier_ceiling_base', DEMOTION_THRESHOLDS['brier_ceiling_base'],
     'Trailing Brier above base + tolerance demotes (calibration drift).'),
    ('brier_tolerance', DEMOTION_THRESHOLDS['brier_tolerance'],
     'Added to the Brier base to form the ceiling.'),
    ('feed_staleness_days', DEMOTION_THRESHOLDS['feed_staleness_days'],
     'A results feed older than 7 days demotes to paper (fail-closed on data).'),
]]
from engine.origination_elo import demotion_gate as _gate_fn
_ex1 = _gate_fn({'n_bets': 20, 'roi_flat': 0.02, 'mean_edge': 0.8, 'clv_rate': 0.55,
                 'brier': 0.24, 'feed_age_days': 1})
_ex2 = _gate_fn({'n_bets': 20, 'roi_flat': -0.14, 'mean_edge': -0.3, 'clv_rate': 0.35,
                 'brier': 0.28, 'feed_age_days': 2})
_ex3 = _gate_fn({'n_bets': 6, 'roi_flat': 0.05, 'mean_edge': 0.9, 'clv_rate': 0.6,
                 'brier': 0.23, 'feed_age_days': 1})
_ex_rows = [
    row(['Healthy trailing window', str(_ex1[0]), '; '.join(_ex1[1])], ('repo',),
        'Synthetic example of the rule — not NFL data'),
    row(['Drawdown + negative edge + weak CLV', str(_ex2[0]), '; '.join(_ex2[1])], ('repo',),
        'Synthetic example of the rule — not NFL data'),
    row(['Too few graded bets to monitor', str(_ex3[0]), '; '.join(_ex3[1])], ('repo',),
        'Synthetic example of the rule — not NFL data'),
]
page('demotion.html', 'Demotion gate', 'A live strategy earns its place every week.',
     'The demotion gate sends a live strategy back to paper on predeclared, testable '
     'triggers — trailing return, edge decay, closing-line value, calibration drift or '
     'a stale feed. No strategy is live, so the gate is defined and armed but has never '
     'triggered. The leaderboard\u2019s policy gate (a77d40e1) covers integrity and '
     'operational breaches; the quantitative thresholds here cover performance decay \u2014 '
     'both end in the same paper state.',
     table('Demotion thresholds (engine/origination_elo.py, predeclared)',
           ['Threshold', 'Value', 'Meaning'], _th_rows)
     + table('Behaviour of the gate (synthetic inputs — arithmetic examples, not NFL observations)',
             ['Scenario', 'Decision', 'Reasons recorded'], _ex_rows)
     + table('Current status', ['Check', 'State'], [
         row(['Live strategies', 'None', 'No strategy has passed the seven validation gates, so nothing is live to demote'],
             ('repo',), 'Project record'),
         row(['Gate state', 'Defined, armed, never triggered',
              'Unit tests exercise all three outcomes; the promotion path stays the seven gates on validation.html'],
             ('repo',), 'Project record'),
         row(['Re-promotion', 'Not defined yet',
              'A demoted strategy must re-clear the validation gates; re-promotion thresholds are an open owner decision (question Q-24)'],
             ('repo',), 'Open decision'),
     ])
     + '<p class="download">Related: the <a href="validation.html">seven validation gates</a> '
       '(promotion), the <a href="leaderboard.html">signal-vs-staking leaderboard</a> the gate '
       'protects, and the <a href="markets.html">snapshot store</a> that timestamps when a '
       'decision was made.</p>')

# ===========================================================================
# append-only augmentations
# ===========================================================================
_signal_table = table('Signal vs staking — two scores, never blended',
                      ['Score', 'Inputs', 'What it can and cannot say'], [
    row(['Signal score (ranking input)', 'Flat 1-unit stake ROI, mean (model − market) edge, CLV-positive rate, calibration (Brier), graded n',
         'Measures whether the selection is good; a lucky staking run cannot move it. Blank until the seven gates pass on a sealed period.'],
        ('repo',), 'Leaderboard design / metrics withheld'),
    row(['Staking score (published beside, never ranked on)', 'Stake-weighted ROI under the declared staking plan, stake-weighted hit rate, max drawdown, staking variance',
         'Measures money management on top of the same graded bets; variance here is attributable to staking, not signal. Blank until a strategy is live.'],
        ('repo',), 'Leaderboard design / metrics withheld'),
    row(['Blending rule', 'Rank and rewards use the signal score only',
         'The demotion gate (demotion.html) polices live entries; staking luck cannot mask a deteriorating signal and signal luck cannot justify a staking plan.'],
        ('repo',), 'Leaderboard design / project rule'),
])
PAGES['leaderboard.html'] = (*PAGES['leaderboard.html'][:3],
                             PAGES['leaderboard.html'][3] + _signal_table
                             + '<p class="download">Companion pages: <a href="signal-staking.html">Signal vs staking '
                               '(a77d40e1)</a> · <a href="validation.html">Validation</a> · '
                               '<a href="demotion.html">Demotion gate</a>.</p>')

PAGES['index.html'] = (*PAGES['index.html'][:3],
                       PAGES['index.html'][3]
                       + '<div class="notice"><strong>Added 14 Nov 2026 (session arena/9a409d93-own9)</strong>'
                         '<p>Complements to the a77d40e1 market-board delta: a Week 10-specific '
                         '<a href="markets.html">price-snapshot store</a> whose opens were captured before the '
                         'Week 10 kickoffs (52 markets, fair line / market line / difference as separate columns, '
                         'side → total → moneyline origination order) with scheduled pre-kickoff close capture; '
                         '<a href="replacement-chains.html">replacement chains</a> deriving the replacement '
                         '<em>and its chart depth</em> for the Week 10 injury report from 19 newly retrieved club '
                         'charts; a quantitative <a href="demotion.html">demotion gate</a> with unit-tested '
                         'thresholds behind the leaderboard\u2019s policy gate; and a signal/staking table on '
                         '<a href="leaderboard.html">the leaderboard</a>. Market-line columns are blank '
                         'everywhere: no official price source exists (F42).</p></div>')

_flags_append = table('Session findings F42–F47 (arena/9a409d93-own9, 14 Nov 2026)',
                      ['ID / severity', 'Finding', 'Required evidence / disposition', 'State'], [
    row(['F42 · Critical', 'No official or licensed market-price source exists, so every market_line and diff column in the snapshot store is blank and ROI/CLV remain uncomputable.',
         'Acquire a timestamped, permissioned price archive with settlement rules (S-17); never infer prices.', 'Unverified'], ('repo',), 'Project gap / no source'),
    row(['F43 · Review', 'The elo-v1 fair numbers are unvalidated model outputs from a 136-game in-sample official feed; they are not market prices and carry no edge claim.',
         'Sealed multi-season validation before any leaderboard eligibility; constants were predeclared, not tuned.', 'Unvalidated model output'], ('repo',), 'Model artefact / no claim'),
    row(['F44 · Review', 'Club depth charts are self-labelled unofficial and mostly undated on the page; derived replacement depths are chart-relative, not certified game-day depth.',
         'Point-in-time chart archives per week would be needed before any availability-weighted signal.', 'Chart-relative only'], (f'{_covered_teams[0].lower()}-depth', 'repo'), 'Publisher limitation'),
    row(['F45 · Review', 'Houston publishes no retrievable depth-chart table in the fetched content; several injured players are absent from their own club charts.',
         'Checked absences are recorded; no replacement was inferred for any of them.', 'Checked absence'], ('hou-depth-absence', 'repo'), 'Checked absence'),
    row(['F46 · Review', 'The Week 10 Thursday game kicked off before the store existed, so no open/close snapshot can exist for it.',
         'Future weeks get opens at deployment and closes from the scheduled capture (.github/workflows/snapshot.yml — also the scheduled close run a77d40e1\u2019s F30 asks for, adopted here for the Week 10 store).', 'Never originated'], ('repo',), 'Store policy'),
    row(['F47 · Review', 'The results feed was transcribed from official weekly pages with structural cross-checks (weekly counts, bye arithmetic, 32 teams); per-game independent re-checks against game centres were not performed.',
         'S-21 proposes a per-row game-centre re-check before any ROI use; see also a77d40e1\u2019s F28 (per-row revision timestamps).', 'Structurally consistent'], ('repo',), 'Verification scope'),
])
PAGES['flags.html'] = (*PAGES['flags.html'][:3],
                       PAGES['flags.html'][3] + _flags_append)
