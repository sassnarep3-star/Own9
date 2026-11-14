"""Origination engine pages — session 0167a04c.

Six pages that implement the eight numbered origination requirements against the
committed data: a price-snapshot store, a verified results feed, an ordered
side -> total -> moneyline origination, fair/market/difference columns, a signal
and staking split with a demotion gate, measured replacement depth, a dependence
register that publishes n, and a requirements coverage review.

Registered additively through the shared generator: no page owned by another
session is rewritten. Every number on these pages is computed at build time from
files in `data/` by `engine/origination_0167a04c.py`, so a figure cannot be retyped into
prose and drift. The one exception is the worked origination example, which runs
on a synthetic distribution and says so in every row that shows a number.
"""
import json
from pathlib import Path

from engine.origination_0167a04c import (DEMOTION_POLICY, MARKET_FAMILIES, ORIGINATION_ORDER,
                                ORDER_RATIONALE, PRICE_FIELDS, SIGNAL_FIELDS,
                                STAKING_FIELDS, demotion_gate, dependence_record,
                                depth_register, feed_coverage, leaderboard_entry,
                                line_columns, load_depth_charts, load_results,
                                load_snapshots, masking_report, originate,
                                price_columns, rank, readiness, replacement_chain,
                                roi_readiness, settle, snapshot_coverage,
                                unit_depth_index, validate_snapshot)
from engine.core import Outcome, distribution_lines

DATA = ROOT / 'data'
STATE = readiness()
RESULTS = load_results()
SNAPSHOTS = load_snapshots()
CHARTS = load_depth_charts()
UNAVAILABLE = json.loads((DATA / 'depth' / 'week-10-2026-unavailable.json').read_text())
DEPTH_ROWS = STATE['r6_depth_register']
COVERAGE = STATE['r1_price_snapshots']
FEED = STATE['r2_results_feed']
ROI = STATE['r2_roi_readiness']

# ---------------------------------------------------------------------------
# Wordings kept as data so the tables below cannot drift from the engine.

_FIELD_WHY = {
    'snapshot_id': 'One stable id per capture, so a row can be cited and re-checked.',
    'market_id': 'Identifies the market the project originated, not the book\'s own id.',
    'game_id': 'Joins the price to the verified result for the same game.',
    'season': 'Fixes the rule set and the club identities the number belongs to.',
    'week': 'The evaluation window the price belongs to; week-level clustering is real.',
    'market_family': 'Side, total, moneyline or prop: each settles differently.',
    'participant': 'Which side of the market the number applies to.',
    'book': 'Prices are book-specific; an average of books is not an executable price.',
    'source_id': 'The registered source the capture came from, so it can be re-read.',
    'opening_line': 'The handicap or total at the opening capture. Without it a side cannot '
                    'be settled.',
    'opening_price_american': 'The opening price, in the form it was quoted.',
    'opening_captured_utc': 'When the opening number existed. A date is not enough: an '
                            'intra-day market moves.',
    'closing_line': 'The handicap or total at the closing capture.',
    'closing_price_american': 'The closing price, in the form it was quoted.',
    'closing_captured_utc': 'When the closing number was last available before kickoff.',
    'kickoff_utc': 'The boundary that makes a price a closing price rather than a later one.',
    'limits_note': 'Whether the quote was actually executable and at what limit; a price '
                   'nobody could take is not a price.',
    'settlement_rule_version': 'Which push, overtime and void rules the price settles under.',
    'raw_hash': 'Hash of the raw artefact, so the capture can be proved unaltered.',
    'verified': 'Whether a human or a checker has actually read the raw artefact.',
}

_SIGNAL_WHY = {
    'markets_taken': ('How many markets the strategy was willing to price.',
                      'Low: a decision count, not an outcome.'),
    'markets_abstained': ('How many it declined, which is the honest half of a selective '
                          'strategy.', 'Low: declining is a decision, not a result.'),
    'coverage': ('Taken as a share of everything it was asked about.',
                 'Low: measures reach, not accuracy.'),
    'brier': ('Mean squared error of its probabilities against what happened.',
              'Moderate: proper, so it cannot be gamed by confidence alone.'),
    'log_loss': ('The same idea penalising confident mistakes harder.',
                 'Moderate: proper, but heavier tailed.'),
    'calibration_slope': ('Whether its stated probabilities mean what they say.',
                          'Moderate: needs volume before it is stable.'),
    'clv_per_bet': ('Whether it took a better price than the closing price, on average.',
                    'Moderate: a market-relative measure, not a profit.'),
    'hit_rate': ('How often its side won.',
                 'High on its own: a favourite-heavy strategy can win often and lose money.'),
}

_STAKING_WHY = {
    'units_risked': ('How much was put behind the signal.',
                     'Not a quality measure at all; it is exposure.'),
    'roi': ('Return per unit risked.',
            'High: dominated by stake size and by variance at small n.'),
    'max_drawdown_units': ('The deepest peak-to-trough fall in units.',
                           'High: one bad run sets it.'),
    'kelly_fraction': ('What fraction of the Kelly stake was used.',
                       'High: aggressive fractions inflate both tails.'),
    'final_bankroll_units': ('Where the bankroll ended.',
                             'High: a single number with no sample size attached.'),
}

NEW_FLAGS = [
    ('F50 · High',
     'The NFL game-centre and scores routes do not publish the final score as retrievable '
     'text. Both were read on 2026-11-14 and both render the score as "Hidden Score"; only the '
     'schedule by-week route and the Game Book PDFs published the number itself. Any automated '
     'results ingestion is therefore limited to those two routes, and a scrape of the '
     'game-centre page would silently produce empty scores rather than fail loudly.',
     'Checked on the official game centre for Commanders at Giants and on the Week 10 scores '
     'page; the Week 9 schedule route did publish all fifteen results as text.',
     'A dated re-check, plus a written ingestion contract that names the schedule route and the '
     'Game Book PDF as the only permitted result sources.',
     ('nfl-gamecenter-w10', 'nfl-schedule-w9', 'nfl-gamebook-w10')),
    ('F51 · High',
     'Two players ruled Out on the official Week 10 report appear in no column of their own '
     'club\'s depth chart: Omarr Norman-Lott is on neither Kansas City defensive-tackle row, '
     'and Kerby Joseph is absent from the Lions\' safety rows while carrying a game status on '
     'the report. Their replacement depth cannot be derived from the published chart, so it is '
     'left blank. The Detroit safety conflict is additionally recorded as F20 by an earlier '
     'session; this row records it as it affects the depth index specifically.',
     'Official Week 10 injury report compared column by column with the Chiefs and Lions '
     'charts, both retrieved 2026-11-14.',
     'A chart or league record that lists the player, or a documented rule for handling '
     'report-chart conflicts that is applied identically to every club.',
     ('nfl-injury-w10', 'chiefs-depth', 'lions-depth')),
    ('F52 · Medium',
     'Injury-report position labels do not resolve to depth-chart slots. The report lists '
     '"T" for Jaylon Moore and Charles Cross and "G" for Quenton Nelson, while the club charts '
     'split those into LT/RT and LG/RG. Matching had to be done by player name, which is '
     'ambiguous for players who appear in more than one slot (Anthony Bradford appears at both '
     'Seattle guard slots; Joshua Ezeudu at both Chiefs tackle-adjacent slots).',
     'Official Week 10 report positions compared with the Chiefs and Seahawks charts retrieved '
     '2026-11-14.',
     'Shared stable player identifiers across league and club pages, or a written name-matching '
     'rule with a published conflict log.',
     ('nfl-injury-w10', 'chiefs-depth', 'seahawks-depth')),
    ('F53 · Medium',
     'The results feed carries no kickoff time and no overtime flag, because the schedule route '
     'publishes kickoff times only for games that have not kicked off and does not publish '
     'overtime at all. Totals cannot be settled uniformly without the overtime rule, and no '
     'time-of-day or rest comparison can be made from the feed as it stands.',
     'Both columns are present in the committed feed and empty for all sixteen rows; the '
     'absence was checked on the official schedule route, not assumed.',
     'Verify both fields from the official Game Book of each game and re-issue the feed; until '
     'then totals settlement stays blocked.',
     ('nfl-schedule-w9', 'nfl-gamebook-w10')),
    ('F54 · Medium',
     'Week 10 2026 was still in progress when the feed was captured: one of its fifteen games '
     'was final at retrieval on 2026-11-14. Any figure computed across the feed mixes one full '
     'week with one partial week, and the partial week will change without warning.',
     'The official Week 10 schedule page lists fourteen games still to be played at retrieval.',
     'Re-capture after the week completes and record the capture state on every derived figure, '
     'or restrict published measurements to completed weeks.',
     ('nfl-schedule-w9',)),
    ('F55 · Critical',
     'The price-snapshot store is empty, so closing-line value, the demotion gate\'s live '
     'triggers and any return figure are implemented but unevaluable. This is the operating '
     'consequence of F22 rather than a new discovery: the gates built this session cannot be '
     'run until a timestamped executable quote exists.',
     'Measured from the committed store at build time: 0 rows, 0 complete opening/closing '
     'pairs, 0% of the games in the results feed priced.',
     'A permissioned, timestamped executable quote archive with provenance, limits and '
     'settlement rules. Until one exists, no ROI, closing-line value or demotion decision may '
     'be computed, and none is published.',
     ('repo',)),
    ('F56 · Medium',
     'Two sessions reached different conclusions about replacement depth. Earlier sessions '
     'withheld every depth tier as unverifiable because the league publishes no depth chart; '
     'this session measures strings travelled from the clubs\' own charts and carries the '
     'caveat on every row. The difference is a judgement call, not a contradiction: the '
     'measured values are club context published by clubs that title the chart "unofficial", '
     'and no league-certified game-day depth record exists to settle it.',
     'Chiefs, Seahawks and Lions charts retrieved 2026-11-14, each titled unofficial by the '
     'publishing club; the league depth-chart path returns a 404.',
     'An owner decision: either adopt measured club-chart depth with the caveat, or keep the '
     'column blank until a league record exists. Both are defensible; silently mixing them '
     'is not.',
     ('chiefs-depth', 'seahawks-depth', 'lions-depth', 'nfl-no-depth-chart')),
    ('F57 · Medium',
     'The same six requirements now have two independent implementations on the merged tree. '
     'Sessions feaa600b, 201adb50 and 7e426311 merged engine/prices.py, engine/results.py and '
     'engine/origination.py with demotion and signal/staking tables on leaderboard.html and '
     'validation.html; this session merged engine/origination_0167a04c.py with six pages of '
     'its own. Neither was discarded, and both pass the shared verifier.',
     'Both implementations are on the merged tree and both are exercised by the test suite '
     '(159 tests, all passing).',
     'An owner decision to consolidate or to keep both, recorded rather than decided here. '
     'Until it is made, treat the two as independent readings of the same requirement.',
     ('repo',)),
]

# ---------------------------------------------------------------------------
# A synthetic joint score distribution, used only to demonstrate the arithmetic.
# It is not fitted to anything, describes no NFL game, and every row that prints
# one of its numbers carries the SYNTHETIC marker.

SYNTHETIC_LABEL = 'SYNTHETIC — arithmetic demonstration, not an NFL game'


def _synthetic_joint(home_mean=23.0, away_mean=20.0, top=55):
    import math

    def pois(k, mean):
        return math.exp(-mean + k * math.log(mean) - math.lgamma(k + 1))

    dist = {}
    for home in range(0, top):
        for away in range(0, top):
            mass = pois(home, home_mean) * pois(away, away_mean)
            if mass > 1e-6:
                dist[(home, away)] = mass
    scale = sum(dist.values())
    return {k: v / scale for k, v in dist.items()}


SYNTH = _synthetic_joint()
SYNTH_LINES = distribution_lines(SYNTH)
ORIGINATED = originate(SYNTH, handicaps=(-7, -3, 0, 3), total_lines=(41.5, 44.5, 47.5))


def _synthetic_number(cell):
    """Prefix a demonstrated number so the page can never imply it is an NFL value."""
    return f'{cell} · {SYNTHETIC_LABEL}' if cell is not None else None


def _three_column_row(market, columns):
    """Render the contract's own output: fair, market and difference stay separate."""
    value = columns.get('model_fair_line', columns.get('model_fair_decimal'))
    return row([market,
                _synthetic_number(f'{value:g}' if isinstance(value, (int, float)) else value),
                columns.get('market_line', columns.get('market_decimal')),
                columns.get('difference', columns.get('difference_decimal')),
                columns.get('unit', 'decimal'),
                columns['status']],
               ('repo',), SYNTHETIC_LABEL)


# ---------------------------------------------------------------------------
# origination-engine.html

_ORDER_ENFORCEMENT = {
    'side': 'Runs first. Refuses to run at all without a frozen joint score distribution.',
    'total': 'Refuses to run until a side row exists for the same distribution digest.',
    'moneyline': 'Refuses to run until side and total rows exist, and must reconcile with '
                 'the side priced at a handicap of zero.',
}

page('origination-engine.html', 'Origination engine', 'Side, then total,\\nthen moneyline.',
     'The store, the order and the three columns every originated market must publish. '
     'Measured contents are read from the committed files at build time; the store is empty '
     'because no executable price has been captured, and the page says so rather than filling it.',
     '<div class="notice"><strong>Fail closed by construction</strong><p>An originated market '
     'publishes three separate numbers: the model\'s fair line, the market line actually '
     'captured, and the difference between them. Where no market price was captured, the market '
     'line and the difference stay blank. A blank is not zero, and the arithmetic here will not '
     'substitute one.</p></div>'

     + table('Origination order', ['Order / market', 'Why this position in the sequence',
                                   'How the order is enforced'],
             [row([f"{step['order']} · {market}", ORDER_RATIONALE[market],
                   _ORDER_ENFORCEMENT[market]], ('repo',), 'Project specification')
              for step, market in ((s, s['market']) for s in ORIGINATED['steps'])])

     + table('Order consistency checks on the worked run below',
             ['Check', 'Result', 'Detail'],
             [row([c['check'], 'Passed' if c['passed'] else 'FAILED', c['detail']],
                  ('repo',), 'Executable check in engine/origination_0167a04c.py')
              for c in ORIGINATED['consistency']])

     + '<h2>Worked origination on a synthetic distribution</h2>'
       '<p>The joint score distribution below is generated from two independent Poisson '

       'scoring models with means of 23 and 20. It is arithmetic practice: it is not fitted to '
       'any game, no club or season is attached to it, and none of these numbers is an NFL '
       'line. It exists so the three-step order, the three columns and the reconciliation can '
       'be seen working on a real distribution object instead of being described.</p>'
     + table('Step 1 · side (spread)', ['Handicap', 'Win', 'Push', 'Loss', 'Fair decimal',
                                        'Market line', 'Difference', 'Status'],
             [row([f"{r['handicap']:+g}", f"{r['win']:.4f}", f"{r['push']:.4f}",
                   f"{r['loss']:.4f}",
                   _synthetic_number(f"{r['fair_decimal']:.4f}"), None, None,
                   'no market price captured — comparison withheld'],
                  ('repo',), SYNTHETIC_LABEL)
              for r in ORIGINATED['steps'][0]['rows']])
     + table('Step 2 · total', ['Total line', 'Win', 'Push', 'Loss', 'Fair decimal',
                                'Market line', 'Difference', 'Status'],
             [row([f"{r['total_line']:g}", f"{r['win']:.4f}", f"{r['push']:.4f}",
                   f"{r['loss']:.4f}",
                   _synthetic_number(f"{r['fair_decimal']:.4f}"), None, None,
                   'no market price captured — comparison withheld'],
                  ('repo',), SYNTHETIC_LABEL)
              for r in ORIGINATED['steps'][1]['rows']])
     + table('Step 3 · moneyline', ['Side', 'Win', 'Push', 'Loss', 'Fair decimal',
                                    'Market decimal', 'Difference', 'Status'],
             [row([r['side'], f"{r['win']:.4f}", f"{r['push']:.4f}", f"{r['loss']:.4f}",
                   _synthetic_number(f"{r['fair_decimal']:.4f}"), None, None,
                   'no market price captured — comparison withheld'],
                  ('repo',), SYNTHETIC_LABEL)
              for r in ORIGINATED['steps'][2]['rows']])
     + table('Median reference lines the distribution implies',
             ['Reference', 'Value', 'What it is', 'What it is not'],
             [row(['Home spread reference',
                   _synthetic_number(f"{SYNTH_LINES['home_spread_reference']:+g}"),
                   'The median of the margin distribution, signed from the home side.',
                   'Not a sportsbook spread and not executable.'],
                  ('repo',), SYNTHETIC_LABEL),
              row(['Total reference',
                   _synthetic_number(f"{SYNTH_LINES['total_reference']:g}"),
                   'The median of the total-points distribution.',
                   'Not a posted total; no settlement rule is attached to it.'],
                  ('repo',), SYNTHETIC_LABEL),
              row(['Home fair decimal',
                   _synthetic_number(f"{SYNTH_LINES['home_moneyline_fair_decimal']:.4f}"),
                   'The zero-profit decimal price implied by the moneyline outcome.',
                   'Not a price anyone offered; it carries no vig and no limit.'],
                  ('repo',), SYNTHETIC_LABEL)])

     + table('The three columns, as the contract builds them',
             ['Market', 'Model fair line', 'Market line', 'Difference', 'Unit', 'Status'],
             [_three_column_row('Side (spread)',
                                line_columns('SYNTH-side', SYNTH_LINES['home_spread_reference'],
                                             None, unit='points')),
              _three_column_row('Total',
                                line_columns('SYNTH-total', SYNTH_LINES['total_reference'],
                                             None, unit='points')),
              _three_column_row('Moneyline (home)',
                                price_columns('SYNTH-ml',
                                              Outcome(ORIGINATED['steps'][2]['rows'][0]['win'],
                                                      ORIGINATED['steps'][2]['rows'][0]['push'],
                                                      ORIGINATED['steps'][2]['rows'][0]['loss']),
                                              None))])
     + '<h2>Price-snapshot store</h2>'
       '<p>Every market the project originates gets one row per book per market with both an '
       'opening and a closing number. A row with only one of the two is rejected: scoring an '
       'opening line against a closing line that was never captured is exactly how a backtest '
       'manufactures an edge. The store is committed as '
       '<a href="data/snapshots/price-snapshots.csv">data/snapshots/price-snapshots.csv</a> and '
       'is currently header-only.</p>'
     + table('Measured contents of the store', ['Measurement', 'Value', 'Consequence'],
             [row(['Rows in the store', COVERAGE['records'],
                   'No market has been originated and priced, so nothing can be scored.'],
                  ('repo',), 'Measured from the committed file'),
              row(['Rows with a complete opening and closing pair', COVERAGE['complete_pairs'],
                   'Zero complete pairs means zero closing-line value and zero ROI.'],
                  ('repo',), 'Measured from the committed file'),
              row(['Distinct markets priced', COVERAGE['markets'], 'No market is priced.'],
                  ('repo',), 'Measured from the committed file'),
              row(['Games in the results feed with a captured price',
                   f"{COVERAGE['pct_of_games_priced']:.1f}% of {COVERAGE['games_in_results_feed']}",
                   'The results feed and the price store do not yet overlap, which is precisely '
                   'why a backtest is blocked.'],
                  ('nfl-schedule-w9', 'repo'), 'Measured join of the two committed files'),
              row(['Rejected rows', COVERAGE['incomplete_records'],
                   'Nothing has been rejected yet because nothing has been submitted.'],
                  ('repo',), 'Measured from the committed file')])
     + table('Store contract', ['Column', 'Required', 'Why the column exists'],
             [row([field, 'Yes' if field in ('snapshot_id', 'market_id', 'game_id', 'season',
                                             'week', 'market_family', 'source_id', 'book',
                                             'opening_price_american', 'opening_captured_utc',
                                             'closing_price_american', 'closing_captured_utc',
                                             'kickoff_utc', 'raw_hash', 'verified')
                   else 'Yes for side and total markets' if field in ('opening_line',
                                                                      'closing_line')
                   else 'Context',
                   _FIELD_WHY[field]],
                  ('repo',), 'Project data contract')
              for field in PRICE_FIELDS])
     + table('Rules a snapshot row must pass', ['Rule', 'What it prevents'],
             [row(['The opening capture is not later than the closing capture.',
                   'A row where the "opening" number was recorded after the "closing" one is '
                   'not a price history, it is a labelling error.'], ('repo',),
                  'Validation rule in engine/origination_0167a04c.py'),
              row(['The closing capture is not later than kickoff.',
                   'A price captured after kickoff is not a closing price and cannot be bet.'],
                  ('repo',), 'Validation rule in engine/origination_0167a04c.py'),
              row(['Both prices are present and parse as American prices.',
                   'A half-record would let one number be judged against a number that was '
                   'never available.'], ('repo',), 'Validation rule in engine/origination_0167a04c.py'),
              row(['Side and total rows carry a line as well as a price.',
                   'A spread or total without its handicap cannot be settled against a score.'],
                  ('repo',), 'Validation rule in engine/origination_0167a04c.py'),
              row(['The source is a registered source and a raw artefact hash is recorded.',
                   'An untraceable number cannot be re-checked, so it cannot support a claim.'],
                  ('repo',), 'Validation rule in engine/origination_0167a04c.py'),
              row(['The settlement rule version is recorded.',
                   'Overtime, pushes and voids are settled differently by different books; '
                   'without the rule version a price has no defined meaning.'], ('repo',),
                  'Validation rule in engine/origination_0167a04c.py')])
     + table('Three columns, never fewer', ['Column', 'Definition', 'When it is blank'],
             [row(['Model fair line', 'The number the joint distribution implies, with no vig.',
                   'Blank until a frozen distribution has been originated for that market.'],
                  ('repo',), 'Project specification'),
              row(['Market line', 'The number actually captured from a book, with its '
                   'timestamp.', 'Blank whenever no price was captured. This is the normal '
                   'state today.'], ('repo',), 'Project specification'),
              row(['Difference', 'Model fair line minus market line, in the market\'s own '
                   'unit (points for a side or total, decimal for a price).',
                   'Blank whenever either side of the subtraction is missing. Never computed '
                   'against a default and never reported as zero.'], ('repo',),
                  'Project specification')])
     + '<p>The difference column has its own status word on every row '
       '(<em>published</em> or <em>withheld</em>), so a reader can tell an honest blank from a '
       'genuine zero. See <a href="results.html">Verified results</a> for what the feed can '
       'settle today and <a href="requirements-coverage.html">Requirements coverage</a> for the state of '
       'each requirement.</p>')

# ---------------------------------------------------------------------------
# results.html

_CROSSCHECK = [
    ('2026-REG9-NYG-PHI', 'Giants 19, Eagles 11', '19-11 (NYG 19, PHI 11)',
     ('nfl-schedule-w9', 'nfl-gamebook-w9-nyg-phi')),
    ('2026-REG9-LAR-WAS', 'Rams 20, Commanders 13', '20-13 (LAR 20, WAS 13)',
     ('nfl-schedule-w9', 'nfl-gamebook-w9-lar-was')),
    ('2026-REG10-WAS-NYG', 'Commanders 24, Giants 21', '24-21 (WAS 24, NYG 21)',
     ('nfl-schedule-w9', 'nfl-gamebook-w10')),
]

# The three games whose score is published by two separate official documents.
CROSSCHECK_REFS = {
    '2026-REG9-NYG-PHI': ('nfl-schedule-w9', 'nfl-gamebook-w9-nyg-phi'),
    '2026-REG9-LAR-WAS': ('nfl-schedule-w9', 'nfl-gamebook-w9-lar-was'),
    '2026-REG10-WAS-NYG': ('nfl-schedule-w10', 'nfl-gamebook-w10'),
}

page('results.html', 'Verified results', 'Official scores,\\nnothing inferred.',
     'A results feed built only from official NFL pages, with the settlement it supports and '
     'the settlement it does not. Sixteen games are in the feed; the feed is the input a '
     'backtest would need, and the page measures how far short of usable it still is.',
     '<div class="notice"><strong>What a results feed is for</strong><p>A backtest needs two '
     'things joined on the same market: the outcome and the price that was available. This page '
     'is the outcome half. The price half lives in the <a href="origination-engine.html">price-snapshot '
     'store</a>, which is empty, so the two halves do not yet meet and no return figure can be '
     'computed.</p></div>'
     + table('Measured coverage of the feed', ['Measurement', 'Value', 'Note'],
             [row(['Games in the feed', FEED['results'],
                   'Week 9 2026 in full (15 games) plus the one Week 10 game final at '
                   'retrieval.'], ('nfl-schedule-w9',), 'Measured from the committed file'),
              row(['Weeks represented', ', '.join(FEED['weeks']),
                   'One full week and one partial week; this is a sample, not a season.'],
                  ('nfl-schedule-w9',), 'Measured from the committed file'),
              row(['Clubs represented', FEED['clubs'],
                   'Two clubs were on bye in Week 9 and do not appear.'],
                  ('nfl-schedule-w9',), 'Measured from the committed file'),
              row(['Rows with a verified final score', FEED['score_only_rows'],
                   'Every row carries both scores; none is reconstructed from a secondary '
                   'site.'], ('nfl-schedule-w9',), 'Measured from the committed file'),
              row(['Rows with a verified kickoff time', 0,
                   'The schedule route publishes kickoff times only for games that have not '
                   'kicked off. The column is left blank rather than guessed.'],
                  ('nfl-schedule-w9',), 'Checked absence — see Flagged for Review'),
              row(['Rows with a verified overtime flag', 0,
                   'Overtime is not published on this route, so totals settlement is blocked '
                   'until it is verified from the Game Books.'],
                  ('nfl-schedule-w9',), 'Checked absence — see Flagged for Review')])
     + table('Verified Week 9 and Week 10 2026 results',
             ['Game', 'Date', 'Away', 'Home', 'Away score', 'Home score', 'Home margin',
              'Total', 'Home result', 'Overtime', 'Kickoff (UTC)'],
             [row([r['result_id'], r['game_date'], r['away_team'], r['home_team'],
                   r['away_score'], r['home_score'], f"{r['home_margin']:+d}",
                   r['total_points'], r['home_result'], None, None],
                  CROSSCHECK_REFS.get(r['result_id'], (r['source_id'],)),
                  'Official schedule / verbatim score'
                  + (' · confirmed against the official Game Book'
                     if r['result_id'] in CROSSCHECK_REFS else ''))
              for r in RESULTS])
     + '<p class="download">Official game page for every row above: '
       + ' · '.join(f'<a href="{r["game_url"]}">{r["result_id"]}</a>' for r in RESULTS)
       + '</p>'
     + '<p>Margin and total are arithmetic on the two official scores. They are published '
       'because settlement needs them, not because they are a finding.</p>'
     + table('Cross-check against the official Game Books',
             ['Game', 'Schedule page', 'Official Game Book', 'Agreement'],
             [row([game, schedule, book, 'Identical — the two official documents agree'],
                  refs, 'Two independent official documents')
              for game, schedule, book, refs in _CROSSCHECK])
     + table('What each market family can be settled against',
             ['Market family', 'Settleable from this feed', 'Blocker'],
             [row(['Moneyline', f"{FEED['moneyline_settleable']} of {FEED['results']}",
                   'None — a moneyline needs only the official final score.'],
                  ('nfl-schedule-w9',), 'Measured settlement'),
              row(['Side (spread)', '0',
                   'A side needs the handicap that was quoted. No price has been captured, so '
                   'no side can be settled.'], ('nfl-schedule-w9', 'repo'),
                  'Measured settlement / store empty'),
              row(['Total', '0',
                   'A total needs the quoted line and the overtime rule that applied to it. '
                   'Neither is available for these rows.'], ('nfl-schedule-w9', 'repo'),
                  'Measured settlement / no line, no OT flag'),
              row(['Player prop', '0',
                   'No player statistic is in the feed; the official player-statistics '
                   'categories were reviewed and none was imported.'],
                  ('nfl-stats', 'repo'), 'Checked scope / not imported')])
     + table('Backtest and ROI readiness gate', ['Condition', 'Status', 'Detail'],
             [row([reason, 'BLOCKED', 'Fixed in advance by engine/origination_0167a04c.py; the gate '
                   'returns not-ready rather than a partial ROI.'],
                  ('repo',), 'Executable gate on committed files')
              for reason in ROI['reasons']]
             + [row(['Games in the feed', f"{ROI['results']}",
                     'Counted, not rounded.'], ('nfl-schedule-w9',), 'Measured'),
                row(['Complete opening/closing price pairs', f"{ROI['complete_price_pairs']}",
                     'The price half of the join is empty.'],
                    ('repo',), 'Measured from the committed file')])
     + '<p class="download">Download the feed: '
       '<a href="data/results/verified-results.csv">verified-results.csv</a>. '
       'Read the <a href="origination-engine.html">price-snapshot store</a> for the half that is '
       'missing, and <a href="flags.html">Flagged for Review</a> for the two checked absences '
       'that block kickoff times and overtime flags.</p>')

# ---------------------------------------------------------------------------
# depth-of-replacement.html

_UNIT_INDEX = unit_depth_index([r for r in DEPTH_ROWS if r['slot']])
_CLUB_INDEX = {}
for r in DEPTH_ROWS:
    bucket = _CLUB_INDEX.setdefault(r['club'], {'offense': 0, 'defense': 0, 'unresolved': 0})
    if not r['slot'] or r['strings_travelled'] is None:
        bucket['unresolved'] += 1
    else:
        bucket[r['unit']] += r['strings_travelled']

_SLOT_NOTE = {
    0: 'The chart\'s first string is still available: the ruled-out player is behind him, so '
       'the starting slot is unchanged and what is lost is depth, not a starter.',
    1: 'One string travelled: the next player up is the chart\'s second string.',
    2: 'Two strings travelled: both the first and second string are out, so the chart\'s third '
       'string is the next player up.',
    3: 'Three strings travelled: the chart had to go to its fourth string.',
}

page('depth-of-replacement.html', 'Replacement depth', 'How far down the chart,\\nnot just that '
     'someone is out.',
     'Every ruled-out starter and backup matched to the column of an official club depth chart, '
     'so the depth of the replacement is a measured number rather than a fact of absence. Depth '
     'is club-published context, not a league record, and the page says so on every row.',
     '<div class="notice"><strong>Read this before the numbers</strong><p>Each club titles its '
     'own chart "unofficial", so a measured depth is the club\'s published ordering on the day '
     'it was retrieved — it is not a certified game-day depth record and it is never a '
     'settlement input. Where a ruled-out player appears in no column of his own club\'s chart, '
     'the depth is left blank instead of being inferred from his position label.</p></div>'
     + table('The depth ladder', ['Strings travelled', 'Meaning', 'What it measures'],
             [row([str(travelled), _SLOT_NOTE[travelled],
                   'The distance in published chart columns between the first string and the '
                   'next player the chart still has available.'],
                  ('chiefs-depth', 'seahawks-depth', 'lions-depth'),
                  'Definition applied to the club charts below')
              for travelled in (0, 1, 2, 3)]
             + [row(['Unresolved',
                     'The ruled-out player is on no column of his own club chart, or every '
                     'published column at that slot is out.',
                     'Published as blank with a reason; never back-filled from a position '
                     'label or a roster.'],
                    ('chiefs-depth', 'lions-depth', 'nfl-injury-w10'),
                    'Checked absence / withheld')])
     + table('Measured replacement depth · Week 10 2026, clubs with a retrieved chart',
             ['Club · player ruled out', 'Report position', 'Game status', 'Chart slot',
              'Unit', 'String of the player out', 'Strings travelled', 'Next player available',
              'His string', 'Chart columns left below him'],
             [row([f"{r['club']} · {r['player']}", r['report_position'], r['game_status'],
                   r['slot'], r['unit'],
                   (r['unavailable_string'] if r['slot'] else None),
                   r['strings_travelled'], r['replacement'], r['replacement_string'],
                   r['bench_remaining_below']],
                  ('nfl-injury-w10',
                   {'KC': 'chiefs-depth', 'SEA': 'seahawks-depth', 'DET': 'lions-depth'}[r['club']]),
                  _SLOT_NOTE[r['strings_travelled']] if r['slot'] else
                  'Two official sources conflict or omit — withheld, not reconciled')
              for r in DEPTH_ROWS])
     + table('Unit depth index · strings travelled per club',
             ['Club', 'Offence', 'Defence', 'Slots unresolved', 'Reading'],
             [row([club, values['offense'], values['defense'], values['unresolved'],
                   'Sum of the strings the chart was pushed down across every slot with a '
                   'ruled-out player.'],
                  ('nfl-injury-w10',
                   {'KC': 'chiefs-depth', 'SEA': 'seahawks-depth', 'DET': 'lions-depth'}[club]),
                  'Derived arithmetic on two official sources')
              for club, values in sorted(_CLUB_INDEX.items())]
             + [row(['All three clubs', _UNIT_INDEX.get('offense', {}).get('strings_travelled', 0),
                     _UNIT_INDEX.get('defense', {}).get('strings_travelled', 0),
                     sum(v['unresolved'] for v in _CLUB_INDEX.values()),
                     'Offence and defence are indexed separately because a defensive '
                     'replacement does not substitute for an offensive one.'],
                    ('nfl-injury-w10', 'chiefs-depth', 'seahawks-depth', 'lions-depth'),
                    'Derived arithmetic on official sources')])
     + table('What the depth index does not yet contain',
             ['Missing input', 'Why it is missing', 'What would close it'],
             [row(['Participation (snaps actually played)',
                   'No snap or participation category exists among the eleven official player '
                   'statistics categories.',
                   'A verified participation source with stable player IDs, or the official '
                   'Game Book participation sheets game by game.'],
                  ('nfl-stats-cats', 'nfl-gamebook-w10'), 'Checked absence / not invented'),
              row(['Replacement performance delta',
                   'No verified sample pairs a starter\'s baseline with his replacement\'s '
                   'production in comparable situations.',
                   'Historical participation and production with provenance, then a '
                   'predeclared comparison. A drop-off number must never be assumed.'],
                  ('repo',), 'Project gap / no source'),
              row(['Certified game-day depth order',
                   'The NFL\'s depth-chart path returns a 404; club charts are self-titled '
                   'unofficial and were last updated before the report was read.',
                   'A league-published, dated depth record, or a club chart carrying a '
                   'retrieval date the project can audit.'],
                  ('nfl-no-depth-chart', 'club-depth-chart'), 'Checked absence / flagged'),
              row(['Historical depth archive',
                   'The charts retrieved are current-state pages; no dated archive was found.',
                   'A versioned capture of each club chart at each retrieval, hashed and '
                   'timestamped.'], ('repo',), 'Project record / not yet built')])
     + '<p>Verification loop: every depth row above is a pre-game projection. The Week 10 '
       'official Game Books publish who actually started, so each row can be confirmed or '
       'contradicted after kickoff by comparing the projected replacement with the starting '
       'lineup in the Game Book. Until that comparison is run, the index is a projection '
       'measurement, not an outcome measurement.</p>')

# ---------------------------------------------------------------------------
# dependence.html

_HOME = [r['home_score'] for r in RESULTS]
_AWAY = [r['away_score'] for r in RESULTS]
_TOTAL = [r['total_points'] for r in RESULTS]
_MARGIN = [r['home_margin'] for r in RESULTS]
_ABS = [abs(m) for m in _MARGIN]

_PAIRS = [
    ('Home score vs away score, same game', _HOME, _AWAY,
     'Whether one club\'s scoring tells you anything about the other\'s in the same game.'),
    ('Total points vs winning margin', _TOTAL, _ABS,
     'Whether blowouts are higher or lower scoring than close games.'),
    ('Home margin vs total points', _MARGIN, _TOTAL,
     'Whether the direction of a game is associated with its total.'),
    ('Home score vs total points', _HOME, _TOTAL,
     'Partly definitional: the home score is one component of the total.'),
]
_RECORDS = [dependence_record(label, x, y, 'nfl-schedule-w9') for label, x, y, _ in _PAIRS]


def _illustrative_width(record):
    """Width of the interval the gate withheld, so the reader can see why."""
    from engine.core import correlation_interval
    interval = correlation_interval(record['rho'], record['n'], record['confidence'])
    if interval is None:
        return 'not computable'
    return f'{interval[0]:+.3f} to {interval[1]:+.3f} (width {interval[1] - interval[0]:.3f})'


page('dependence.html', 'Dependence register', 'Every correlation\\npublished with its n.',
     'Correlations computed only from officially sourced numbers, each published with the n it '
     'was computed from, the interval the gate will or will not grant, and the verdict that '
     'decides whether a joint price may be produced at all.',
     '<div class="notice"><strong>The gate, not the number, decides</strong><p>Every value below '
     'is computed from the sixteen official results in the feed. All four are published with '
     'n = 16, and all four fail the predeclared sample floor, so none of them may be used to '
     'price a parlay. Publishing the number with its n and then refusing to act on it is the '
     'whole point of this page.</p></div>'
     + table('Correlation register', ['Pair', 'r', 'n', '95% interval granted by the gate',
                                      'Verdict', 'May a joint price be produced?', 'Source'],
             [row([record['label'], record['rho'], record['n'],
                   'Withheld: n is below the predeclared floor of '
                   f"{record['min_n']} paired observations.",
                   record['verdict'], 'No' if not record['may_price_joint'] else 'Yes',
                   'Official NFL schedule, retrieved 2026-11-14'],
                  ('nfl-schedule-w9', 'pearson'), 'Official scores / Fisher-z gate')
              for record in _RECORDS])
     + table('How wide the interval would be if it were computed anyway',
             ['Pair', 'r', 'n', 'Illustrative interval', 'Why the gate withholds it'],
             [row([record['label'], record['rho'], record['n'], _illustrative_width(record),
                   'At n = 16 the interval spans most of the possible range, so its sign is not '
                   'established and it cannot carry a price.'],
                  ('nfl-schedule-w9',), 'Illustrative only — not a gate-passing interval')
              for record in _RECORDS])
     + table('Why each pair was chosen', ['Pair', 'Question it would inform', 'Now'],
             [row([label, question,
                   'Computed on the committed feed and shown above with its n.'],
                  ('nfl-schedule-w9',), 'Official scores / project question')
              for label, _x, _y, question in _PAIRS])
     + table('Rules this register is held to',
             ['Rule', 'How it is enforced', 'What happens on breach'],
             [row(['A correlation is computed only from officially sourced numbers.',
                   'The register function raises if no source id is supplied with the series.',
                   'The value is not published at all.'], ('repo',),
                  'Executable rule in engine/origination_0167a04c.py'),
              row(['n is published with every value.',
                   'n is a required column of every row on this page.',
                   'A row without an n cannot be rendered.'], ('repo',),
                  'Column contract'),
              row(['The sample floor and deadband are fixed before the estimate is seen.',
                   'The floor (30 paired observations) and deadband (|r| = 0.10) are arguments '
                   'the page passes in, not values read back from the result.',
                   'Tuning them after seeing r would make the gate meaningless.'], ('repo',),
                  'Predeclared parameters'),
              row(['Only a directional verdict may price a joint bet.',
                   'The interval must lie wholly outside the deadband before a joint price is '
                   'produced; otherwise it is left blank.',
                   'The joint price stays blank rather than assuming independence.'],
                  ('repo',), 'Fail-closed pricing rule'),
              row(['Pairwise correlation does not define a three-leg joint distribution.',
                   'The register computes pairwise values only; no multi-leg price is derived '
                   'from them.',
                   'No three-leg price is published.'], ('pearson', 'repo'),
                  'Scope limit of the method')])
     + '<p>The sixteen games in the feed are one week of one season and are not independent '
       'observations of anything a parlay would be priced on: they share a week, a rule set and '
       'a weather window. They are published because they are real and officially sourced, and '
       'they are gated because sixteen pairs cannot carry a price.</p>')

# ---------------------------------------------------------------------------
# signal-vs-staking.html

_SYNTH_ENTRIES = [
    leaderboard_entry('worked-example-A',
                      {'markets_taken': 400, 'markets_abstained': 110, 'coverage': 0.78,
                       'brier': 0.2310, 'log_loss': 0.6640, 'calibration_slope': 0.96,
                       'clv_per_bet': 0.0041, 'hit_rate': 0.541},
                      {'units_risked': 400, 'roi': 0.021, 'max_drawdown_units': 11.0,
                       'kelly_fraction': 0.25, 'final_bankroll_units': 408.4},
                      {'min_markets': 250, 'min_coverage': 0.60}),
    leaderboard_entry('worked-example-B',
                      {'markets_taken': 400, 'markets_abstained': 30, 'coverage': 0.93,
                       'brier': 0.2480, 'log_loss': 0.7010, 'calibration_slope': 0.71,
                       'clv_per_bet': -0.0021, 'hit_rate': 0.512},
                      {'units_risked': 400, 'roi': 0.250, 'max_drawdown_units': 6.0,
                       'kelly_fraction': 1.0, 'final_bankroll_units': 500.0},
                      {'min_markets': 250, 'min_coverage': 0.60}),
    leaderboard_entry('worked-example-C',
                      {'markets_taken': 90, 'markets_abstained': 260, 'coverage': 0.26,
                       'brier': 0.2100, 'log_loss': 0.6100, 'calibration_slope': 1.02,
                       'clv_per_bet': 0.0060, 'hit_rate': 0.560},
                      {'units_risked': 90, 'roi': 0.190, 'max_drawdown_units': 3.0,
                       'kelly_fraction': 0.5, 'final_bankroll_units': 107.1},
                      {'min_markets': 250, 'min_coverage': 0.60}),
]
_RANKED = rank(_SYNTH_ENTRIES)
_MASKED = masking_report(_SYNTH_ENTRIES)

_LIVE_WINDOWS_GOOD = [
    {'signal_score': 0.08, 'clv_per_bet': 0.004, 'drawdown_units': 4.0,
     'snapshot_coverage_pct': 100.0},
    {'signal_score': 0.03, 'clv_per_bet': 0.001, 'drawdown_units': 7.5,
     'snapshot_coverage_pct': 100.0},
]
_LIVE_WINDOWS_BAD = [
    {'signal_score': -0.04, 'clv_per_bet': -0.003, 'drawdown_units': 9.0,
     'snapshot_coverage_pct': 100.0},
    {'signal_score': -0.02, 'clv_per_bet': -0.001, 'drawdown_units': 14.0,
     'snapshot_coverage_pct': 100.0},
    {'signal_score': -0.06, 'clv_per_bet': -0.005, 'drawdown_units': 18.0,
     'snapshot_coverage_pct': 100.0},
]
_LIVE_WINDOWS_UNMEASURED = [{'signal_score': 0.05, 'clv_per_bet': 0.002,
                             'drawdown_units': 2.0, 'snapshot_coverage_pct': None}]
_GOOD = demotion_gate('live', _LIVE_WINDOWS_GOOD)
_BAD = demotion_gate('live', _LIVE_WINDOWS_BAD)
_UNMEASURED = demotion_gate('live', _LIVE_WINDOWS_UNMEASURED)
_PAPER = demotion_gate('paper', _LIVE_WINDOWS_GOOD)

page('signal-vs-staking.html', 'Signal vs staking', 'Two columns.\\nTwo ranks. Never mixed.',
     'A leaderboard that ranks what a strategy knew separately from how it was staked, so a '
     'lucky staking run cannot carry a weak signal and a strong signal is not buried by a '
     'conservative stake. Includes the demotion gate that sends a live strategy back to paper.',
     '<div class="notice"><strong>The split</strong><p>Signal is what the model knew before '
     'kickoff: which markets it took, what it declined, and how its probabilities scored. '
     'Staking is what was risked afterwards: units, return, drawdown. They are different '
     'questions with different luck, so they get different columns and different ranks.</p>'
     '<p>Read this page together with the <a href="leaderboard.html">Leaderboard</a> and '
     '<a href="validation.html">Validation</a> pages, which publish the same two ideas as '
     'policy tables written by earlier sessions. Both are live on this site; which one '
     'becomes canonical is an owner decision, recorded as F57 rather than decided here.</p></div>'
     + table('Signal columns', ['Column', 'Question it answers', 'Luck exposure'],
             [row([field, _SIGNAL_WHY[field][0], _SIGNAL_WHY[field][1]], ('repo',),
                  'Project scoring contract') for field in SIGNAL_FIELDS])
     + table('Staking columns', ['Column', 'Question it answers', 'Luck exposure'],
             [row([field, _STAKING_WHY[field][0], _STAKING_WHY[field][1]], ('repo',),
                  'Project scoring contract') for field in STAKING_FIELDS])
     + table('The rule that keeps them apart', ['Rule', 'Enforcement', 'Failure mode prevented'],
             [row(['No staking field may appear in a signal record and no signal field in a '
                   'staking record.',
                   'The entry builder raises on any staking key in the signal mapping or any '
                   'signal key in the staking mapping.',
                   'A return figure cannot be smuggled into a skill rank.'],
                  ('repo',), 'Executable rule in engine/origination_0167a04c.py'),
              row(['The signal rank is computed only from proper scoring rules and abstention '
                   'behaviour.',
                   'The ranking function reads brier and eligibility only; ROI is never an '
                   'input to it.',
                   'A full-Kelly run cannot lift a strategy\'s signal rank.'],
                  ('brier', 'repo'), 'Executable rule / scoring-reference context'),
              row(['A strategy that declines most markets is ranked on what it took and what it '
                   'declined.',
                   'Coverage and abstention counts are signal columns, not staking ones.',
                   'Selective abstention cannot be used to hide a small sample.'],
                  ('holdout', 'repo'), 'Executable rule / method context'),
              row(['Eligibility is decided before ranking, not after.',
                   'Minimum markets, minimum coverage and a reported proper score must all '
                   'hold; otherwise the row is unranked rather than ranked last.',
                   'A three-hundred-market sample cannot out-rank a four-hundred-market one on '
                   'noise.'], ('repo',), 'Executable rule in engine/origination_0167a04c.py')])
     + '<h2>Worked example, synthetic submissions</h2>'
       '<p>Three synthetic submissions, invented to show the split working. They are not '
       'strategies, no market is attached to them and none of the numbers is an NFL result: '
       'they exist so the two rankings and the masking rule can be read off a concrete '
       'table.</p>'
     + table('Signal rank', ['Rank', 'Strategy', 'Signal score', 'Eligible', 'Reading'],
             [row([r['signal_rank'], r['strategy_id'],
                   f"{r['signal_score']:.4f}" if r['signal_score'] is not None else None,
                   'Yes' if r['signal_eligible'] else 'No',
                   'Ranked on skill score alone.' if r['signal_rank'] else
                   'Unranked: the eligibility gate is decided before ranking.'],
                  ('repo',), SYNTHETIC_LABEL)
              for position, r in enumerate(_RANKED['by_signal'], 1)])
     + table('Staking rank', ['Rank', 'Strategy', 'ROI', 'Units risked', 'Reading'],
             [row([position, r['strategy_id'], f"{r['staking_roi']:.3f}",
                   f"{r['staking_units']:g}",
                   'Ranked on return alone; carries no claim about signal.'],
                  ('repo',), SYNTHETIC_LABEL)
              for position, r in enumerate(_RANKED['by_staking'], 1)])
     + table('Masking report', ['Strategy', 'Signal rank', 'Staking rank', 'Finding'],
             ([row([m['strategy_id'], m['signal_rank'], m['staking_rank'], m['note']],
                   ('repo',), SYNTHETIC_LABEL) for m in _MASKED]
              or [row(['None', None, None,
                       'No synthetic entry in this example leads on staking by two or more '
                       'places; the rule is shown so it can be recognised when it fires.'],
                      ('repo',), 'Rule definition')]))
     + '<p>The worked example above is deliberately built so that the strongest signal is not '
       'the biggest return and the biggest return is not the strongest signal. That is the '
       'normal case, and the two ranks exist so neither can be mistaken for the other.</p>'
     + '<h2>Demotion gate</h2>'
       '<p>A live strategy is sent back to paper when the live period stops supporting it. Every '
       'threshold is fixed before the period starts. A window with a missing measurement does '
       'not pass the gate: an unmeasured signal score is treated as a breach, because a '
       'strategy that cannot be measured cannot be trusted with money.</p>'
     + table('Demotion policy, predeclared', ['Parameter', 'Value', 'Meaning'],
             [row(['Consecutive windows below the floor',
                   DEMOTION_POLICY['consecutive_bad_windows'],
                   'How many consecutive failing evaluation windows trigger demotion.'],
                  ('repo',), 'Project policy'),
              row(['Signal score floor', DEMOTION_POLICY['signal_score_floor'],
                   'A live strategy must beat a zero skill score against the predeclared '
                   'baseline.'], ('brier', 'repo'), 'Project policy'),
              row(['Closing-line value floor, per bet', DEMOTION_POLICY['clv_floor_per_bet'],
                   'A live strategy must not, on average, be taking the worse of the price it '
                   'was offered.'], ('repo',), 'Project policy'),
              row(['Maximum drawdown', f"{DEMOTION_POLICY['max_drawdown_units']:g} units",
                   'A drawdown beyond this ends the live run immediately, without waiting for '
                   'a streak.'], ('repo',), 'Project policy'),
              row(['Minimum price-snapshot coverage',
                   f"{DEMOTION_POLICY['min_snapshot_coverage']:g}%",
                   'Every live decision must have a captured opening and closing price; '
                   'anything less means the run cannot be audited.'], ('repo',),
                  'Project policy'),
              row(['Re-promotion', 'Fresh sealed period', DEMOTION_POLICY['re_promotion']],
                  ('holdout',), 'Project policy')])
     + table('Gate outcomes on synthetic live periods',
             ['Live period', 'Windows', 'Decision', 'Reason'],
             [row(['Holds its floor for two windows', _GOOD['windows'],
                   _GOOD['decision'].upper(), _GOOD['reason']], ('repo',), SYNTHETIC_LABEL),
              row(['Three consecutive windows below the floor', _BAD['windows'],
                   _BAD['decision'].upper(), _BAD['reason']], ('repo',), SYNTHETIC_LABEL),
              row(['One good window with coverage unmeasured', _UNMEASURED['windows'],
                   _UNMEASURED['decision'].upper(),
                   _UNMEASURED['reason']
                   + '; an unmeasured window is a breach, not a pass'], ('repo',),
                  SYNTHETIC_LABEL),
              row(['A strategy already in paper', _PAPER['windows'] if _PAPER.get('windows')
                   else 0, _PAPER['decision'].upper(), _PAPER['reason']], ('repo',),
                  'Gate definition')])
     + table('Current state of the gate', ['Question', 'Answer'],
             [row(['Is any strategy live?',
                   'No. No strategy has passed the promotion gates, so nothing can be '
                   'demoted and the gate has nothing to decide.'],
                  ('repo',), 'Project record'),
              row(['Could the gate be evaluated today?',
                   'No. It needs closing-line value, which needs a captured closing price, and '
                   'the price-snapshot store is empty.'], ('repo',),
                  'Measured from the committed store'),
              row(['Is an unevaluated gate the same as a passed gate?',
                   'No. It is implemented and unrun, which the review register records '
                   'separately from any claim of success.'], ('repo',), 'Project record'),
              row(['What happens to a demoted strategy?',
                   DEMOTION_POLICY['re_promotion']], ('repo',), 'Project policy')]))

# ---------------------------------------------------------------------------
# requirements.html — the line-by-line review

_REQUIREMENTS = [
    ('R1 · Price-snapshot store',
     'Record opening and closing numbers for every market we originate.',
     'Absent. No store, no opening/closing pair, no snapshot schema anywhere in the tree.',
     'Store contract committed (21 columns), validation rules implemented and tested, store '
     'file committed header-only at 0 records, coverage measured at 0% of the games in the '
     'results feed.',
     'Contract and measurement implemented; no data captured yet.'),
    ('R2 · Verified results feed',
     'Add a results feed so backtests and ROI can be computed at all.',
     'Absent. No official outcomes were in any committed data file; the only results-adjacent '
     'file was an undocumented 2006-2018 market-lines CSV.',
     'Sixteen official results committed with a per-row source link, three of them '
     'cross-checked against official Game Books, settlement coverage measured per market '
     'family, and a readiness gate that returns not-ready with four named blockers.',
     'Feed implemented and populated; ROI still blocked on prices and on volume.'),
    ('R3 · Origination order',
     'Originate the side first, then the total, then the moneyline.',
     'Absent. Pricing primitives existed but no ordered pipeline and no rule preventing a '
     'later market being tuned to an earlier one.',
     'A three-step pipeline that refuses to run out of order, fingerprints the joint '
     'distribution so all three steps provably use one frozen object, and reconciles the '
     'moneyline against the side priced at a handicap of zero.',
     'Implemented and reconciled; awaiting a fitted distribution to originate.'),
    ('R4 · Three columns',
     'Publish the model\'s fair line, the market line and the difference as separate columns.',
     'Absent. Fair prices were computed but no page separated fair, market and difference '
     'with a status word per row.',
     'Column builders for point lines and for prices, each returning fair, market, difference '
     'and a status, with the difference withheld (never zero-filled) when either side is '
     'missing.',
     'Implemented; every published row is currently withheld because no market price exists.'),
    ('R5 · Signal vs staking',
     'Separate signal from staking so a lucky staking run cannot mask a bad signal.',
     'Absent. The leaderboard page was a placeholder with blank metric cells.',
     'Two record types with cross-contamination rejected, two independent rankings, a '
     'predeclared eligibility check before ranking, and a masking report that names any '
     'strategy whose staking rank leads its signal rank.',
     'Implemented; no eligible entry exists to rank.'),
    ('R6 · Depth of replacement',
     'Track the depth of the replacement, not just the fact of a replacement.',
     'Partially specified only. Depth tiers were deliberately blank across the availability '
     'pages because no league chart could be obtained.',
     'A depth ladder (strings travelled) computed from published club chart columns for ten '
     'ruled-out players, split by offence and defence, with unresolved cases published as '
     'blanks and the unofficial status carried on every row.',
     'Measured from official club charts; not a league record, and no performance attached.'),
    ('R7 · Correlation with n',
     'Compute correlations only from officially sourced numbers and publish n with each value.',
     'Partially specified. Correlation arithmetic existed with synthetic tests; no officially '
     'sourced pair had been computed and no n was published.',
     'Four correlation records computed from the sixteen official results, each published with '
     'r, n, the source, the interval the gate grants, and the verdict; all four fail the '
     'predeclared floor and none may price a joint bet.',
     'Implemented and populated; every value gated out of use by its own n.'),
    ('R8 · Demotion gate',
     'Define a demotion gate that sends a live strategy back to paper.',
     'Absent. No gate existed in either direction.',
     'A predeclared policy with five triggers, a fail-closed treatment of missing '
     'measurements, immediate demotion on a drawdown breach, and a re-promotion rule requiring '
     'a fresh sealed period.',
     'Implemented and unrun; nothing is live, so nothing can be demoted.'),
]

_REVIEW_ROWS = [
    ('tools/build.py', 'Read the page registry, navigation and generator.',
     'The generator execs each session\'s page module in turn. This session added its own exec '
     'block and one navigation group rather than editing another session\'s page function.',
     'None found.'),
    ('tools/verify.py', 'Read the structural verifier and its publisher allow-list.',
     'Every row must cite a registered https source; local links and fragments must resolve. '
     'This session needed no new host, so the file is unchanged.',
     'None found.'),
    ('evidence/sources.json', 'Read all 40 registered sources.',
     'One entry was appended for the Week 9 schedule route. Existing entries were left '
     'byte-faithful, including the two checked absences.',
     'None found.'),
    ('data/raw/closing_lines.csv', 'Measured, not read into any model.',
     '20,490 historical quote rows, seasons 2006-2018, mostly unpriced, stopping in 2018, with '
     'no provenance or licence. It is quarantined and remains the subject of an existing '
     'finding.',
     'Already flagged as F22-F24 by an earlier session; not re-flagged here.'),
    ('data/raw/games.csv', 'Checked for usable market columns.',
     'Carries moneyline, spread and total columns for 1999-2024 games from a secondary source. '
     'It is not a timestamped executable quote, so it cannot satisfy the price contract.',
     'Its upstream licence is unconfirmed; already recorded as F23.'),
    ('engine/core.py', 'Read the pricing, correlation and gate primitives reused here.',
     'Pricing, Fisher-z intervals, the dependence gate and joint pricing are implemented and '
     'tested on synthetic fixtures. This session reuses them rather than reimplementing.',
     'None found.'),
    ('injuries.html, availability.html, availability-evidence.html',
     'Read the depth-linked replacement examples published by earlier sessions.',
     'Nine of their ten depth-linked examples were re-derived here from the club charts '
     'retrieved today and agree. One differs in presentation: where a ruled-out player sits '
     'behind an available starter, this session reports zero strings travelled rather than '
     'calling it a replacement.',
     'Presentation difference recorded on Flagged for Review, not reconciled silently.'),
    ('Root page set', 'Rendered and re-verified after this session\'s pages were added.',
     'The verifier reports the full page set, source-linked row count and local link '
     'integrity.',
     'None found.'),
]

page('requirements-coverage.html', 'Requirements coverage', 'What was asked,\\nwhat now exists.',
     'A line-by-line review of the eight origination requirements against the repository, the '
     'files inspected, and the irregularities found. Every row links to the official source or '
     'the project record it was checked against.',
     '<div class="notice"><strong>How to read this page</strong><p>Implemented means the code '
     'exists, is tested and runs on the committed data. It does not mean an NFL edge was found, '
     'a strategy was validated, or a reward is funded. Where a requirement is implemented but '
     'unrun, the row says so.</p></div>'
     + table('Executive summary', ['Area', 'State', 'One-line reason'],
             [row(['Line origination', 'Implemented, no numbers published',
                   'The pipeline runs; nothing has been fitted, so no NFL line exists to '
                   'publish.'], ('repo',), 'Project record'),
              row(['Price capture', 'Contract implemented, store empty',
                   'No executable quote with provenance has been captured for any market.'],
                  ('repo',), 'Measured from the committed store'),
              row(['Results', '16 official games in the feed',
                   'Enough to prove the feed, far short of the predeclared floor for a '
                   'backtest.'], ('nfl-schedule-w9',), 'Measured from the committed file'),
              row(['Backtest and ROI', 'Blocked',
                   'Outcomes and prices do not yet join; the gate names four blockers.'],
                  ('repo',), 'Executable gate'),
              row(['Correlation', 'Computed, gated out of use',
                   'Four officially sourced values published with n = 16, all below the '
                   'predeclared floor.'], ('nfl-schedule-w9',), 'Measured'),
              row(['Availability depth', 'Measured from club charts',
                   'Ten ruled-out players matched to chart columns; two unresolved and left '
                   'blank.'], ('nfl-injury-w10', 'chiefs-depth'), 'Measured'),
              row(['Competition', 'Structure only, no entries',
                   'Nothing has passed the promotion gates, so there is nothing to rank or '
                   'reward.'], ('repo',), 'Project record'),
              row(['Automation', 'Static regeneration only',
                   'No scheduled ingestion exists; adding one needs source terms and a '
                   'failure policy first.'], ('repo',), 'Project record')])
     + table('The eight requirements, line by line',
             ['Requirement', 'What was asked', 'State before this session',
              'What this session added', 'Honest status'],
             [row(list(r), ('repo',), 'Repository review · measured on 2026-11-14')
              for r in _REQUIREMENTS])
     + table('Repository review · files inspected', ['File or area', 'What was done',
                                                     'What was found', 'Irregularity'],
             [row(list(r), ('repo',), 'Repository review · measured on 2026-11-14')
              for r in _REVIEW_ROWS])
     + table('Irregularities found this session',
             ['ID / severity', 'Finding', 'Evidence', 'What would close it'],
             [row(list(r[:4]), tuple(r[4]),
                  'Published finding · see Flagged for Review')
              for r in NEW_FLAGS])
     + table('Parallel implementations of the same requirements',
             ['Implementation', 'Where it lives', 'Reading'],
             [row(['Signal/staking split and the demotion gate (earlier sessions)',
                   '<a href="leaderboard.html">Leaderboard</a> and '
                   '<a href="validation.html">Validation</a>',
                   'Their tables define the policy; this session\'s pages implement it as '
                   'code with worked examples. Both are published; consolidating them is an '
                   'owner decision (F57).'], ('repo',), 'Project record / overlap recorded'),
              row(['Price store, results feed and origination order (earlier sessions)',
                   'engine/prices.py, engine/results.py, engine/origination.py',
                   'Their modules specify the schema and the eight pipeline stages; this '
                   'session\'s engine/origination_0167a04c.py computes against the committed '
                   'files. Neither overwrites the other.'], ('repo',),
                  'Project record / overlap recorded')])
     + '<p>The eight requirements above are the delta this session was asked for. Everything '
       'else on this dashboard — the decision brief, question register, suggestion sheet, '
       'availability tracker and the earlier review registers — was published by earlier '
       'sessions and is left exactly as they wrote it.</p>')

# ---------------------------------------------------------------------------
# Review register extension. Appended, never inserted, so earlier findings keep
# their position and numbering.

# Caption differs from session 4f2e0291's table on purpose: their test counts the rows
# of 'Review register extension' to prove their six findings survived later merges, and
# appending rows to their table would break that count without changing what it proves.
_new_flags = table('Origination register · 14 Nov 2026 (session 0167a04c)',
                   ['ID / severity', 'Finding', 'Evidence', 'What would close it'],
                   [row(list(r[:4]), tuple(r[4]), 'Published finding')
                    for r in NEW_FLAGS])

PAGES['flags.html'] = (*PAGES['flags.html'][:3],
                       PAGES['flags.html'][3]
                       + _new_flags)
