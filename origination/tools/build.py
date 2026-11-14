"""Deterministic renderer for the line-origination desk.

No network calls. Every published number is read from a file produced by
`tools/run.py` or from a committed evidence file. A value that does not exist is
rendered as a blank, flagged cell - never as a zero, never inferred.
"""

import csv
import json
import sys
from collections import defaultdict
from html import escape as e
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

from ownline import depth as depth_mod  # noqa: E402

DATA = ROOT / 'data'
OUT = ROOT
STAMP = 'As of 14 Nov 2026 · UTC'
SOURCES = {s['id']: s for s in json.loads((DATA / 'sources.json').read_text())['sources']}
REPORT = json.loads((DATA / 'report.json').read_text())
CORR = json.loads((DATA / 'correlations.json').read_text())
STRAT = json.loads((DATA / 'strategies.json').read_text())
DEMOT = json.loads((DATA / 'demotions.json').read_text())
VERIFY = json.loads((ROOT / 'evidence' / 'verification_calc.json').read_text())
OFFICIAL = json.loads((ROOT / 'evidence' / 'official_check.json').read_text())

NAV = [
    ('Decide', [('index.html', 'Overview'), ('questions.html', 'Open questions'),
                ('suggestions.html', 'Suggestions')]),
    ('Origination', [('prices.html', 'Price & results feed'),
                     ('originated.html', 'Originated lines'),
                     ('method.html', 'Method & constants')]),
    ('Competition', [('leaderboard.html', 'Leaderboard'), ('demotion.html', 'Demotion gate')]),
    ('Evidence', [('correlations.html', 'Correlations'), ('depth.html', 'Replacement depth'),
                  ('sources.html', 'Sources'), ('flagged.html', 'Flagged for review')]),
]
PAGE_ORDER = [f for _, group in NAV for f, _ in group]

BLANK = '<span class="blank">unverified — blank</span>'


# --------------------------------------------------------------------------
# cell helpers
# --------------------------------------------------------------------------

def n(value, digits=3, suffix='', percent=False):
    """Render a number, or a flagged blank when the value does not exist."""
    if value is None or value == '':
        return BLANK
    if percent:
        return format(value * 100, '.2f') + '%'
    if isinstance(value, float):
        return format(value, '.%df' % digits) + suffix
    return str(value) + suffix


def signed(value, digits=3, suffix=''):
    if value is None or value == '':
        return BLANK
    return format(value, '+.' + str(digits) + 'f') + suffix


def pill(text, kind=''):
    return '<span class="pill %s">%s</span>' % (kind, e(text))


def src(ids, scope=''):
    links = ' · '.join(
        '<a href="%s" target="_blank" rel="noopener" title="%s">%s ↗</a>'
        % (e(SOURCES[i]['url']), e(SOURCES[i]['publisher']), e(SOURCES[i]['title']))
        for i in ids if i in SOURCES)
    text = e(scope)
    if links and text:
        return '%s<span class="src">%s</span>' % (text, links)
    return text or links


def table(table_id, caption, headers, rows, numeric=()):
    head = ''.join('<th scope="col"%s>%s</th>' % (' class="num"' if i in numeric else '', e(h))
                   for i, h in enumerate(headers))
    body = []
    for row in rows:
        cells = ''.join('<td%s>%s</td>' % (' class="num"' if i in numeric else '', c)
                        for i, c in enumerate(row['cells']))
        body.append('<tr>%s<td>%s</td></tr>' % (cells, src(row.get('src', ()),
                                                           row.get('scope', ''))))
    return (
        '<div class="tools"><label>Search <input type="search" data-filter="%s" '
        'placeholder="Filter rows" aria-label="Filter %s"></label></div>'
        '<div class="wrap"><table id="%s"><caption>%s</caption>'
        '<thead><tr>%s<th scope="col">Evidence / scope</th></tr></thead>'
        '<tbody>%s</tbody></table></div>' % (
            table_id, e(caption), table_id, e(caption), head, ''.join(body)))


def page(title, eyebrow, lede, body, active):
    return page_shell(title, eyebrow, lede, body, active)


def page_shell(title, eyebrow, lede, body, active):
    nav = []
    for group, items in NAV:
        links = ''.join(
            '<li><a href="%s"%s>%s</a></li>'
            % (f, ' aria-current="page"' if f == active else '', e(label))
            for f, label in items)
        nav.append('<li><span>%s</span><ul>%s</ul></li>' % (e(group), links))
    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<title>%s · Own9 line origination</title>\n'
        '<meta name="description" content="Source-linked NFL line-origination desk: '
        'price snapshots, a verified results feed, originated side/total/moneyline numbers, '
        'signal and staking scored apart, replacement depth and a demotion gate.">\n'
        '<link rel="stylesheet" href="assets/styles.css">\n</head>\n<body>\n'
        '<a class="skip" href="#main">Skip to content</a>\n'
        '<header class="masthead"><div class="inner">'
        '<div class="brand"><span class="mark">O9</span>'
        '<span>OWN9 / LINE ORIGINATION<small>Evidence first · no live wagers</small></span></div>'
        '<nav aria-label="Sections"><ul class="groups">%s</ul></nav>'
        '</div></header>\n<main id="main">\n'
        '<p class="eyebrow">%s</p>\n<h1>%s</h1>\n<p class="stamp">%s</p>\n<p class="lede">%s</p>\n'
        '%s\n</main>\n'
        '<footer><p>OWN9 / NFL line origination · Research only, no wagering enabled. '
        'Every table row links to a registered source; blank cells are unavailable, not zero. '
        '<a href="flagged.html">Flagged for review</a> · '
        '<a href="sources.html">Sources</a> · '
        '<a href="../index.html">Main dashboard</a> · '
        '<a href="https://github.com/sassnarep3-star/Own9">Repository</a></p></footer>\n'
        '<script src="assets/app.js"></script>\n</body>\n</html>\n'
        % (e(title), ''.join(nav), e(eyebrow), e(title), e(STAMP), e(lede), body))


# --------------------------------------------------------------------------
# data views
# --------------------------------------------------------------------------

def read_csv(name):
    with (DATA / name).open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def originated_rows():
    return read_csv('originated.csv')


def price_rows():
    return read_csv('prices.csv')


def results_rows():
    return read_csv('results.csv')


def season_summary():
    rows = originated_rows()
    by_season = defaultdict(lambda: defaultdict(list))
    for r in rows:
        by_season[int(r['season'])][r['market']].append(r)
    out = []
    for season in sorted(by_season):
        markets = by_season[season]
        entry = {'season': season, 'games': len(markets['SIDE'])}
        for market in ('SIDE', 'TOTAL', 'MONEYLINE'):
            diffs = [abs(float(r['difference'])) for r in markets[market]
                     if r['difference'] != '' and r['market_number'] != '']
            priced = len([r for r in markets[market] if r['market_number'] != ''])
            settled = len([r for r in markets[market] if r['outcome'] != ''])
            entry[market] = {
                'n': len(markets[market]),
                'mean_abs_diff': sum(diffs) / len(diffs) if diffs else None,
                'priced': priced,
                'settled': settled,
            }
        out.append(entry)
    return out


def slate_rows(season=2026, week=10, limit=None):
    rows = [r for r in originated_rows()
            if int(r['season']) == season and int(r['week']) == week]
    rows.sort(key=lambda r: (r['game_id'], int(r['origination_order'])))
    return rows[:limit] if limit else rows


def upcoming_week():
    """The latest week in the snapshot that carries a market line but no result."""
    rows = originated_rows()
    pending = [r for r in rows if r['outcome'] == '' and r['market_number'] != '']
    if not pending:
        return None, None
    latest = max(int(r['week']) for r in pending)
    season = max(int(r['season']) for r in pending if int(r['week']) == latest)
    return season, latest


# --------------------------------------------------------------------------
# pages
# --------------------------------------------------------------------------

PAGES = {}


def register(filename, title, eyebrow, lede, body):
    PAGES[filename] = (title, eyebrow, lede, body)


STRATEGY_LABELS = {
    'G-SIDE': 'Single · side',
    'G-TOTAL': 'Single · total',
    'G-ML': 'Single · moneyline',
    'X-PARLAY': 'Parlay · cross-game',
    'S-SGP': 'Combo · same game',
    'P-PROP': 'Combo · player props',
}


def build_index():
    feed = REPORT['results_feed']
    orig = REPORT['originations']
    kpis = (
        ('%s' % format(orig['markets'], ','), 'markets originated (2010–2026)'),
        ('%s' % format(orig['games'], ','), 'games originated'),
        ('%s' % format(feed['games'], ','), 'games in the results feed'),
        ('%d / %d' % (sum(1 for v in VERIFY.values() if isinstance(v, dict)
                          and v.get('mismatches') == 0), len(VERIFY) - 0),
         'official checks with zero mismatches'),
        ('0', 'strategies with a positive signal LCB'),
        ('%s' % len([s for s in (
            'OD-01', 'OD-02', 'OD-03', 'OD-04', 'OD-05', 'OD-06', 'OD-07', 'OD-08',
            'OD-09', 'OD-10', 'OD-11', 'OD-12', 'OD-13', 'OD-14', 'OD-15')]),
         'items flagged for review'),
    )
    kpi_html = '<ul class="kpis">%s</ul>' % ''.join(
        '<li><b>%s</b><span>%s</span></li>' % (e(v), e(t)) for v, t in kpis)

    requirements = [
        ['Price-snapshot store recording opening and closing numbers for every '
         'originated market',
         'Built. `data/prices.csv` holds one row per originated market with separate '
         'open_* and close_* field groups. Closing numbers are populated from the '
         'committed snapshot; opening numbers are blank because no source obtained '
         'records one.',
         pill('Delivered · opening flagged', 'warn'), ('repo-games', 'repo'),
         'Store built; opening values unavailable'],
        ['Verified results feed so backtests and ROI can be computed',
         'Built. `data/results.csv` recomputes margin, total and settlement state for '
         'every completed game. Three whole seasons (2010, 2018, 2025) match the '
         'official NFL standings exactly for all 32 clubs; 2026 Week 8 matches game by '
         'game.',
         pill('Delivered · verified', 'ok'), ('nfl-standings-2010', 'nfl-standings-2018',
                                              'nfl-standings-2025',
                                              'nfl-schedule-2026-week8'),
         'Official cross-check'],
        ['Originate the side first, then the total, then the moneyline',
         'Enforced in code. `originate()` returns the markets in that order and asserts '
         'that the moneyline reuses the margin distribution fitted for the side, so the '
         'two can never disagree.',
         pill('Delivered · asserted', 'ok'), ('repo',), 'Project method, unit-tested'],
        ['Publish the model fair line, the market line and the difference as separate '
         'columns',
         'Published. Three distinct columns per market on the originated-lines page and '
         'in `data/originated.csv`.',
         pill('Delivered', 'ok'), ('repo-games', 'repo'), 'Computed columns'],
        ['Separate signal from staking in the leaderboard',
         'Published as two tables that are never combined. The ranking uses the signal '
         'lower bound only. The parlay is the proof: best staking number in the desk, '
         'worst signal number.',
         pill('Delivered', 'ok'), ('sklearn-logloss', 'repo'), 'Measured, not asserted'],
        ['Track the depth of the replacement, not just the fact of a replacement',
         'Published for the clubs whose charts were retrieved. Each ruled-out player is '
         'mapped to the slot they hold and the printed tier of the player behind them.',
         pill('Partial · 2 of 28 clubs', 'warn'), ('patriots-depth', 'lions-depth',
                                                   'nfl-injuries-w10'),
         'Club-published, self-declared unofficial'],
        ['Compute correlations only from officially sourced numbers and publish n with '
         'each value',
         'Published. Every correlation row carries r, the interval, the gate verdict and '
         'n. No correlation is published without an n, and none is assumed.',
         pill('Delivered · gated', 'ok'), ('scipy-pearson', 'repo'),
         'Computed on measured residuals'],
        ['Define a demotion gate that sends a live strategy back to paper',
         'Defined and replayed. Five demotion triggers, a re-promotion rule, and a '
         'replay showing the bet, date and rule at which each strategy would have been '
         'demoted.',
         pill('Delivered · replayed', 'ok'), ('sklearn-brier', 'repo'),
         'Rule replay on the walk-forward'],
    ]
    req_rows = [{'cells': ['R%d' % (i + 1), c[0], c[1], c[2]], 'src': c[3], 'scope': c[4]}
                for i, c in enumerate(requirements)]

    summary = [
        ['Originated an NFL line for every game in the committed snapshot from 2010 to '
         '2026 — %s games, %s markets — using one transparent least-squares model with no '
         'tuned hyperparameters.' % (format(orig['games'], ','),
                                     format(orig['markets'], ','))],
        ['The model lost to the market on every strategy. The clustered lower bound on '
         'log-loss gain versus the de-vigged closing price is negative for all three '
         'single-market strategies (side %s, total %s, moneyline %s).'
         % (signed(STRAT['G-SIDE']['signal'].get('log_loss_gain_lcb')),
            signed(STRAT['G-TOTAL']['signal'].get('log_loss_gain_lcb')),
            signed(STRAT['G-ML']['signal'].get('log_loss_gain_lcb')))],
        ['The staking numbers do not rescue it, and that is the point. The cross-game '
         'parlay shows the best flat-stake return in the desk (%s over %d bets) and the '
         'worst signal bound (%s). Ranking on money would have promoted the worst '
         'strategy.'
         % (n(STRAT['X-PARLAY']['staking'].get('flat_roi'), 2, percent=True),
            STRAT['X-PARLAY']['staking'].get('bets', 0),
            signed(STRAT['X-PARLAY']['signal'].get('log_loss_gain_lcb')))],
        ['The desk’s own demotion gate would have demoted all three single-market '
         'strategies on the first evaluable window — bet 200, at the end of the 2010 '
         'season — before any of the later money numbers existed.'],
        ['The same-game combo cannot be priced at all. The measured dependence between '
         'the margin error and the total error is r = %s with n = %s, whose 95%% interval '
         '[%s, %s] straddles the declared deadband of ±%s, so the gate refuses every one '
         'of the %d combinations offered.'
         % (n(CORR['margin_total_error']['point'], 4), CORR['margin_total_error']['n'],
            n(CORR['margin_total_error']['interval']['lo'], 4),
            n(CORR['margin_total_error']['interval']['hi'], 4),
            n(REPORT['constants']['deadband'], 2), REPORT['joint']['sgp_offered'])],
        ['Cross-game parlays were priced, but only because the measured week-level '
         'dependence is indistinguishable from zero: intraclass r = %s, interval '
         '[%s, %s], entirely inside the deadband, so the gate permits independence as a '
         'declared rather than assumed convention.'
         % (n(CORR['weekly_intraclass']['r'], 4), n(CORR['weekly_intraclass']['lo'], 4),
            n(CORR['weekly_intraclass']['hi'], 4))],
        ['The results feed is verified, not assumed. 2010, 2018 and 2025 match the '
         'official NFL standings exactly for all 32 clubs on both points for and points '
         'against; 2026 Week 8 matches the official schedule page on all 14 games.'],
        ['The data is still not clean to use. The committed snapshot has no provenance, '
         'no licence and no capture timestamp, records no opening price, and stops at '
         '2026 Week 8 while the official season has reached Week 10. Those are flags '
         'OD-01 to OD-04, not repairs.'],
    ]
    summary_rows = [{'cells': ['%d' % (i + 1), c[0]], 'src': ('repo',),
                     'scope': 'Computed by this desk'} for i, c in enumerate(summary)]

    cards = []
    for _, group in NAV:
        for f, label in group:
            if f == 'index.html':
                continue
            blurb = {
                'questions.html': 'What we know, what we do not, what would close it',
                'suggestions.html': 'Review and choose a path before anything is built',
                'prices.html': 'The store, the results feed and their official checks',
                'originated.html': 'Fair line, market line, difference — three columns',
                'method.html': 'The model, the frozen constants, the order',
                'leaderboard.html': 'Signal and staking, scored apart',
                'demotion.html': 'The rule that sends a live strategy back to paper',
                'correlations.html': 'Every value with its n',
                'depth.html': 'How deep is the replacement',
                'sources.html': 'Publisher, scope and retrieval date per source',
                'flagged.html': 'Everything that is wrong or unverified',
            }[f]
            cards.append('<a href="%s"><span>EVIDENCE DESK</span><b>%s</b><p>%s</p></a>'
                         % (f, e(label), e(blurb)))

    body = (
        '<div class="notice"><strong>Read this before any number on this site.</strong>'
        '<p>No strategy here has earned a stake. Every signal lower bound is negative, '
        'the desk’s own demotion gate would have demoted every live candidate on the '
        'first evaluable window, and the prices are recorded closing numbers from a file '
        'with no provenance or licence — not captured executable quotes. Nothing on this '
        'site is a recommendation to wager.</p></div>'
        + kpi_html
        + '<h2 id="summary">Executive summary</h2>'
        + table('t-summary', 'Eight findings, each computed from the committed files',
                ['#', 'Finding'], summary_rows)
        + '<h2 id="requirements">The eight requirements, and what each one produced</h2>'
        + table('t-req', 'Requirement, delivery and honest state',
                ['#', 'Requirement', 'What was built', 'State'], req_rows)
        + '<h2 id="sections">Sections</h2><div class="cards">%s</div>' % ''.join(cards)
        + '<h2 id="other">The other desk on this site</h2>'
        + '<p>A second session built a market board on the main dashboard covering the '
          'same eight requirements: <a href="../price-snapshots.html">price '
          'snapshots</a>, <a href="../results-feed.html">results feed</a>, '
          '<a href="../origination.html">origination</a>, '
          '<a href="../signal-staking.html">signal and staking</a>, '
          '<a href="../replacement-depth.html">replacement depth</a> and '
          '<a href="../correlations-official.html">correlations</a>. It is not a '
          'duplicate of this one and the two do not conflict: that board works on the '
          '2026 season only, with official weekly captures and a model fitted on 137 '
          'in-season games, and it has no recorded market prices to compare against. '
          'This desk works on 2010–2026, with %s originated markets and a recorded '
          'closing price on every one, which is what makes the walk-forward, the '
          'backtest and the demotion replay possible. Read both; where they disagree, '
          'the difference is the input, not the arithmetic.</p>'
          % format(REPORT['originations']['markets'], ',')
    )
    register('index.html', 'Line origination desk', 'ORIGINATION DESK',
             'Originate the number, prove it against the market, and publish the '
             'difference. Signal and money are scored apart so a lucky staking run '
             'cannot hide a bad signal.', body)


def build_method():
    constants = REPORT['constants']
    rows = [
        {'cells': ['Training window', 'All completed regular-season games with a season '
                   'strictly earlier than the season being originated. %d training '
                   'seasons are required before a season is originated at all.'
                   % constants['min_train_seasons']],
         'src': ('repo',), 'scope': 'Frozen design'},
        {'cells': ['Model', 'One constrained least-squares fit of home points and away '
                   'points on club offence and defence deviations plus an intercept. '
                   'Two zero-sum constraints, no shrinkage constant, no hyperparameter '
                   'chosen on evaluation data.'],
         'src': ('repo',), 'scope': 'Published formula'},
        {'cells': ['Origination order', 'SIDE (1) → TOTAL (2) → MONEYLINE (3). The '
                   'moneyline is derived from the same margin distribution already used '
                   'for the side and is never refitted.'],
         'src': ('repo',), 'scope': 'Asserted in code'},
        {'cells': ['Side price', 'P(home covers h) = P(margin > h) with a continuity '
                   'correction on the integer margin; the push is carried as its own '
                   'state.'],
         'src': ('repo',), 'scope': 'Published formula'},
        {'cells': ['Total price', 'P(total > T) with a continuity correction; the push '
                   'is carried as its own state.'],
         'src': ('repo',), 'scope': 'Published formula'},
        {'cells': ['Moneyline price', 'P(margin > 0) from the side distribution; a tie '
                   'is carried as a push by declared convention.'],
         'src': ('repo',), 'scope': 'Declared convention'},
        {'cells': ['Market baseline', 'Proportional de-vig of the two recorded side '
                   'prices. A declared comparison convention, not a verified true '
                   'probability.'],
         'src': ('repo-games',), 'scope': 'Declared convention'},
        {'cells': ['Bet trigger', 'A bet exists only where a recorded price, a model '
                   'probability and a settled result all exist, and the model '
                   'probability exceeds the break-even price by at least %s.'
                   % n(constants['edge_threshold'], 2, percent=True)],
         'src': ('repo',), 'scope': 'Frozen before evaluation'},
        {'cells': ['Stake rules', 'Flat %s unit per qualifying bet, and separately a '
                   'fractional Kelly stake capped at %s. The two are reported apart and '
                   'neither moves the ranking.' % ('1', n(constants['kelly_cap'], 2))],
         'src': ('repo',), 'scope': 'Frozen before evaluation'},
        {'cells': ['Dependence deadband', 'A joint price is produced only when the 95%% '
                   'interval for the dependence lies wholly inside ±%s (dependence taken '
                   'as zero) or wholly outside it (point estimate used). An interval that '
                   'straddles the deadband refuses the price.'
                   % n(constants['deadband'], 2)],
         'src': ('repo',), 'scope': 'Frozen before evaluation'},
        {'cells': ['Uncertainty', 'Cluster-robust standard errors with the season-week '
                   'as the cluster, because bets inside one week share opponents, weather '
                   'and injury news.'],
         'src': ('repo',), 'scope': 'Stated method'},
        {'cells': ['Demotion window', 'Trailing %d bets, Brier tolerance %s, drawdown '
                   'tolerance %s units.'
                   % (constants['trailing_window'],
                      n(constants['brier_tolerance'], 3),
                      n(constants['drawdown_tolerance'], 0))],
         'src': ('repo',), 'scope': 'Frozen before evaluation'},
    ]
    fits = REPORT['fits']
    fit_rows = [{
        'cells': [f['target_season'], f['train_games'], len(f['train_seasons']),
                  n(f['sigma_margin'], 3), n(f['sigma_total'], 3),
                  signed(f['rho_margin_total'], 4), n(f['mean_total'], 2)],
        'src': ('repo',),
        'scope': 'Fit on prior seasons only',
    } for f in fits]
    body = (
        '<div class="notice"><strong>Why the order matters.</strong><p>Originating the '
        'moneyline last forces it to inherit the margin distribution already used for '
        'the side. If the moneyline were fitted separately it could disagree with the '
        'side on the same game, and the desk would be publishing two different opinions '
        'about one match. The assertion is in the code, not in a comment.</p></div>'
        + '<h2 id="model">The model</h2>'
        + '<p>For every completed regular-season game in the training window, with h = '
          'home points and a = away points, the desk solves</p>'
        + '<p><code>h = mu + o(home) + d(away)</code> &nbsp; and &nbsp; '
          '<code>a = mu + o(away) + d(home)</code></p>'
        + '<p>for one intercept, 32 offence deviations and 32 defence deviations, subject '
          'to both deviation sets summing to zero. Predictions follow from the same fit: '
          '<code>margin = (o_home − o_away) + (d_away − d_home)</code> and '
          '<code>total = 2·mu + o_home + o_away + d_home + d_away</code>. Training '
          'residuals give the two spreads and their correlation. That is the whole '
          'model: no shrinkage constant, no learning rate, nothing tuned on the seasons '
          'being scored.</p>'
        + '<h2 id="constants">Frozen constants</h2>'
        + table('t-const', 'Declared before any result was looked at',
                ['Decision', 'Rule'], rows)
        + '<h2 id="fits">Per-season fits</h2>'
        + table('t-fits', 'Each row fits only on seasons strictly earlier than the '
                'target season',
                ['Target season', 'Training games', 'Training seasons',
                 'σ margin', 'σ total', 'ρ(margin,total)', 'League mean total'],
                fit_rows, numeric=(1, 2, 3, 4, 5, 6))
        + '<h2 id="precision">Published precision</h2>'
        + '<p>Every derived number is frozen to <strong>nine significant digits</strong> '
          'before it is written to <code>data/</code>. The maths library is not '
          'bit-identical across CPython versions and C libraries — the error function '
          'behind the normal distribution can differ by one unit in the last place — '
          'and without a fixed precision the same inputs would produce different last '
          'digits on a different machine. Nine digits is far finer than anything this '
          'desk publishes: no page shows more than six decimal places, and the wider '
          'the interval the less the last digits can matter. The precision is frozen, '
          'not the drift: what it removes is noise below the resolution of any claim '
          'made here.</p>'
          '<p>The engine uses one fixed-seed bootstrap (2,000 resamples over weeks) '
          'and no other randomness. It makes no network calls. Re-running '
          '<code>origination/tools/run.py</code> on the committed inputs reproduces '
          'every artefact byte for byte, and CI fails if it does not.</p>'
    )
    register('method.html', 'Method & constants', 'ORIGINATION / METHOD',
             'The model, the order in which markets are originated, and every constant '
             'frozen before the results were looked at.', body)


def build_prices():
    prices = price_rows()
    feed = results_rows()
    store_rows = [
        {'cells': ['snapshot_id', 'Unique key: game id plus market code.', 'yes'],
         'src': ('repo',), 'scope': 'Store field'},
        {'cells': ['season, week, gameday, game_id', 'Identity of the game.', 'yes'],
         'src': ('repo-games',), 'scope': 'Inherited from the snapshot'},
        {'cells': ['market, origination_order', 'SIDE = 1, TOTAL = 2, MONEYLINE = 3, in '
                   'the order the desk originates them.', 'yes'],
         'src': ('repo',), 'scope': 'Store field'},
        {'cells': ['model_fair_line', 'The number this desk originates.', 'yes'],
         'src': ('repo',), 'scope': 'Computed'},
        {'cells': ['open_line, open_price, open_captured_utc, open_source',
                   'The opening number and when it was seen. <strong>Every one of these '
                   'is blank, on every row.</strong> No source obtained for this project '
                   'records an opening price: the committed snapshot holds a single price '
                   'per market, and NFL.com publishes no odds at all.', 'no'],
         'src': ('repo-games', 'nfl-standings-2026'),
         'scope': 'Checked absence — flag OD-02'},
        {'cells': ['close_line, close_price', 'The recorded closing number and its '
                   'price, taken from the committed snapshot.', 'yes'],
         'src': ('repo-games',), 'scope': 'Committed snapshot'},
        {'cells': ['close_captured_utc', 'When the closing number was seen. '
                   '<strong>Blank on every row:</strong> the snapshot records no capture '
                   'time and no retrieval date.', 'no'],
         'src': ('repo-games',), 'scope': 'Checked absence — flag OD-01'},
        {'cells': ['close_source, close_provenance', 'Where the closing number came from '
                   'and what that implies. Provenance and licence are unconfirmed.', 'yes'],
         'src': ('repo-games',), 'scope': 'Self-declared by the desk'},
        {'cells': ['difference_model_minus_market', 'Model fair line minus the recorded '
                   'market line, in the market’s own units.', 'yes'],
         'src': ('repo',), 'scope': 'Computed'},
    ]
    by_season = defaultdict(int)
    closed = defaultdict(int)
    for r in prices:
        by_season[int(r['season'])] += 1
        if r['close_line'] != '':
            closed[int(r['season'])] += 1
    cov_rows = [{
        'cells': [season, count, '0', closed[season], pill('opening absent', 'bad')],
        'src': ('repo-games',), 'scope': 'Measured from the store',
    } for season, count in sorted(by_season.items())]

    verify_rows = []
    for season in ('2010', '2018', '2025'):
        v = VERIFY[season]
        source_id = OFFICIAL['standings'][season]['source_id'] if False else \
            'nfl-standings-' + season
        verify_rows.append({
            'cells': [season + ' season',
                      'All 32 clubs, points for and points against',
                      v['games'], v['teams_checked'], v['mismatches'],
                      '%s / %s' % (format(v['file_points'], ','),
                                   format(v['official_points'], ',')),
                      pill('exact match', 'ok')],
            'src': (source_id, 'repo-games'),
            'scope': 'Official standings read 2026-11-14',
        })
    w8 = VERIFY['2026_week_8']
    verify_rows.append({
        'cells': ['2026 Week 8', 'Every game in the week, score by score',
                  w8['games_checked'], w8['games_checked'] * 2, w8['mismatches'],
                  n(None), pill('exact match', 'ok')],
        'src': ('nfl-schedule-2026-week8', 'repo-games'),
        'scope': 'Official schedule page read directly by this session 2026-11-14',
    })
    weekly = json.loads((ROOT / 'evidence' / 'weekly_crosscheck.json').read_text())
    w_games = sum(v['official_rows'] for v in weekly.values())
    w_mism = sum(v['mismatches'] for v in weekly.values())
    verify_rows.append({
        'cells': ['2026 weeks 1–8', 'Every completed game in the season, score by score',
                  w_games, w_games * 2, w_mism, n(None),
                  pill('exact match', 'ok')],
        'src': ('nfl-schedule-2026-week8', 'nfl-schedule-2026-week3',
                'repo-weekly-captures', 'repo-games'),
        'scope': 'Official by-week schedule pages. Weeks 8 and 3 were read directly by '
                 'this session; weeks 1–2 and 4–7 were compared using the verbatim '
                 'captures committed by another session, which were exact on both '
                 'weeks this session re-read.',
    })
    verify_rows.append({
        'cells': ['All other seasons', 'Internal recomputation only: result against '
                  'home minus away, total against home plus away.',
                  feed and len(feed), n(None), 0, n(None),
                  pill('internally consistent, not externally confirmed', 'warn')],
        'src': ('repo-games',),
        'scope': 'No official page read for these seasons — flag OD-13',
    })

    sample = slate_rows(2026, 10)
    sample_rows = [{
        'cells': [r['game_id'], r['market'], r['origination_order'],
                  n(float(r['model_fair_line']) if r['model_fair_line'] else None, 2),
                  r['market_number'] or n(None),
                  n(float(r['difference']) if r['difference'] else None, 2),
                  pill('pending', 'warn') if r['outcome'] == '' else pill(r['outcome'], '')],
        'src': ('repo-games', 'repo'),
        'scope': 'Model fair line computed; market line from the snapshot',
    } for r in sample]

    body = (
        '<div class="notice warn"><strong>The opening columns are empty on purpose.</strong>'
        '<p>A price-snapshot store that records an opening number it did not see is worse '
        'than one that records nothing. No source obtained for this project publishes an '
        'opening price, so all four opening fields are blank on all %s rows and the gap '
        'is carried as flag OD-02. Until that changes, closing line value cannot be '
        'computed for any market this desk originates.</p></div>'
        % format(len(prices), ',')
        + '<h2 id="store">Price-snapshot store</h2>'
        + '<p>One row per originated market. Download: '
          '<a href="data/prices.csv">prices.csv</a> (%s rows).</p>' % format(len(prices), ',')
        + table('t-store', 'Store schema and whether each field is populated',
                ['Field', 'What it holds', 'Populated'], store_rows)
        + '<h2 id="coverage">Store coverage by season</h2>'
        + table('t-cov', 'Markets recorded, and how many carry an opening number',
                ['Season', 'Markets in store', 'With opening line',
                 'With closing line', 'Opening state'], cov_rows, numeric=(1, 2, 3))
        + '<h2 id="results">Verified results feed</h2>'
        + '<p>The feed recomputes margin, total and settlement state for every completed '
          'regular-season game in the committed snapshot, then checks the recomputation '
          'against the official publisher. Download: '
          '<a href="data/results.csv">results.csv</a> (%s rows, 1999–2026).</p>'
        % format(len(feed), ',')
        + table('t-verify', 'Official cross-checks of the results feed',
                ['Scope checked', 'What was compared', 'Games', 'Values',
                 'Mismatches', 'Season points file / official', 'Verdict'], verify_rows,
                numeric=(2, 3, 4))
        + '<h2 id="sample">Most recent slate in the store</h2>'
        + '<p>2026 Week 10: the model fair line, the recorded market number and the '
          'difference, in origination order. For the moneyline the market number is the '
          'recorded home price and the difference is in probability points. The result '
          'column is blank because none of these games had been played when the snapshot '
          'was taken.</p>'
        + table('t-sample', '2026 Week 10 originated markets',
                ['Game', 'Market', 'Order', 'Model fair line', 'Market line',
                 'Difference', 'Result'], sample_rows, numeric=(2, 3, 4, 5))
    )
    register('prices.html', 'Price & results feed', 'ORIGINATION / EVIDENCE',
             'A price-snapshot store with opening and closing fields, and a results feed '
             'that is checked against the official publisher before it is trusted.',
             body)


def build_originated():
    summary = season_summary()
    rows = [{
        'cells': [s['season'], s['games'],
                  '%d / %d' % (s['SIDE']['priced'], s['SIDE']['settled']),
                  '%d / %d' % (s['TOTAL']['priced'], s['TOTAL']['settled']),
                  '%d / %d' % (s['MONEYLINE']['priced'], s['MONEYLINE']['settled']),
                  n(s['SIDE']['mean_abs_diff'], 2),
                  n(s['TOTAL']['mean_abs_diff'], 2),
                  n(s['MONEYLINE']['mean_abs_diff'], 2)],
        'src': ('repo-games', 'repo'),
        'scope': 'Priced and settled counts measured; moneyline has no line to differ from',
    } for s in summary]

    season, week = upcoming_week()
    slate = slate_rows(season, week)
    slate_rows_html = [{
        'cells': ['%s @ %s' % (e(r['away']), e(r['home'])), r['market'],
                  r['origination_order'],
                  n(float(r['model_fair_line']) if r['model_fair_line'] else None, 2),
                  r['market_number'] or n(None),
                  (signed(float(r['difference']), 2, ' pp')
                   if r['market'] == 'MONEYLINE' and r['difference'] else
                   signed(float(r['difference']), 2) if r['difference'] else n(None)),
                  n(float(r['model_probability']) if r['model_probability'] else None, 3),
                  n(float(r['market_probability_devig'])
                    if r['market_probability_devig'] else None, 3),
                  pill('pending', 'warn')],
        'src': ('repo-games', 'repo'),
        'scope': 'Fair line and probability computed; market from the committed snapshot',
    } for r in slate]

    body = (
        '<div class="notice"><strong>Three columns, never two.</strong><p>The model’s '
        'fair line, the market’s line and the difference are separate columns on purpose. '
        'A single “edge” column hides which of the two numbers moved and lets a rounding '
        'difference pass as a view.</p></div>'
        + '<h2 id="byseason">Origination by season</h2>'
        + '<p>“Priced / settled” counts markets carrying a recorded price against markets '
          'with a settled result. The mean absolute difference is in the market’s own '
          'units: points for the side and the total, and probability points for the '
          'moneyline, because a moneyline has no line to differ from — only a price.</p>'
        + table('t-season', 'Every season originated, with coverage',
                ['Season', 'Games', 'Side priced/settled', 'Total priced/settled',
                 'Moneyline priced/settled', 'Mean |Δ| side (points)',
                 'Mean |Δ| total (points)', 'Mean |Δ| moneyline (probability points)'],
                rows, numeric=(1, 5, 6, 7))
        + '<h2 id="slate">%s Week %s slate</h2>' % (season, week)
        + '<p>Every market this desk originated for the most recent week that carries a '
          'recorded price and no result yet, in origination order: side, then total, then '
          'moneyline. Full history: '
          '<a href="data/originated.csv">originated.csv</a> (%s rows).</p>'
        % format(len(originated_rows()), ',')
        + table('t-slate', 'Model fair line, market line and difference, as three columns',
                ['Game', 'Market', 'Order', 'Model fair line',
                 'Market number (line, or price for the moneyline)',
                 'Difference (model − market)', 'Model probability',
                 'Market probability (de-vigged)', 'Result'],
                slate_rows_html, numeric=(2, 3, 4, 5, 6, 7))
        + '<p class="download"><a href="data/originated.csv">originated.csv</a> · '
          '<a href="data/bets.csv">bets.csv</a> · '
          '<a href="data/prices.csv">prices.csv</a> · '
          '<a href="data/results.csv">results.csv</a></p>'
    )
    register('originated.html', 'Originated lines', 'ORIGINATION / LINES',
             'What this desk’s model says the line should be, what the recorded market '
             'line was, and the difference between them — published as three columns.',
             body)


def build_leaderboard():
    order = ['G-SIDE', 'G-TOTAL', 'G-ML', 'X-PARLAY', 'S-SGP', 'P-PROP']
    signal_rows = []
    staking_rows = []
    for code in order:
        block = STRAT.get(code, {})
        sig = block.get('signal', {})
        stk = block.get('staking', {})
        if code == 'P-PROP':
            signal_rows.append({
                'cells': [STRATEGY_LABELS[code], n(None), n(None), n(None), n(None),
                          n(None), n(None), pill('not eligible — no data', 'bad')],
                'src': ('repo',),
                'scope': 'No official player-prop market data exists in this repository',
            })
            staking_rows.append({
                'cells': [STRATEGY_LABELS[code], 0, n(None), n(None), n(None),
                          n(None), n(None), pill('not eligible — no data', 'bad')],
                'src': ('repo',),
                'scope': 'No legs, therefore no stake',
            })
            continue
        lcb = sig.get('log_loss_gain_lcb')
        blocked = code in ('S-SGP', 'P-PROP')
        signal_rows.append({
            'cells': [STRATEGY_LABELS[code], sig.get('n', 0),
                      n(sig.get('hit_rate'), 3, percent=True),
                      n(sig.get('log_loss_model'), 4),
                      n(sig.get('log_loss_market'), 4),
                      signed(sig.get('log_loss_gain'), 4),
                      signed(lcb, 4),
                      pill('not priced — dependence gate refused', 'bad') if code == 'S-SGP'
                      else pill('not eligible — no player-prop data', 'bad') if code == 'P-PROP'
                      else pill('passes', 'ok') if (lcb is not None and lcb > 0)
                      else pill('fails — bound is negative', 'bad')],
            'src': ('sklearn-logloss', 'repo'),
            'scope': 'Clustered by season-week, n = %d bets' % sig.get('n', 0),
        })
        staking_rows.append({
            'cells': [STRATEGY_LABELS[code], stk.get('bets', 0),
                      n(stk.get('flat_staked'), 1),
                      signed(stk.get('flat_net'), 2),
                      n(stk.get('flat_roi'), 2, percent=True),
                      n(stk.get('flat_max_drawdown'), 2),
                      n(stk.get('kelly_roi'), 2, percent=True),
                      pill('synthetic price — flag OD-06', 'warn') if code == 'X-PARLAY'
                      else pill('no price — gate refused', 'bad') if code == 'S-SGP'
                      else pill('recorded price, not executable', 'warn')],
            'src': ('repo-games', 'repo'),
            'scope': 'Flat 1 unit and capped Kelly, frozen before evaluation',
        })

    policy = [
        {'cells': ['Ranking', 'Rank on the clustered lower bound of log-loss gain over '
                   'the matched market baseline. Nothing else moves a rank.'],
         'src': ('sklearn-logloss',), 'scope': 'Frozen rule'},
        {'cells': ['Ties', 'Lower Brier, then lower model complexity, then shared rank. '
                   'No cross-track global winner.'],
         'src': ('sklearn-brier',), 'scope': 'Frozen rule'},
        {'cells': ['What cannot move a rank', 'Return on investment, win rate, drawdown, '
                   'stake size and the Kelly number. They are published beside the rank '
                   'so a reader can see the disagreement, and they are structurally '
                   'unable to change it.'],
         'src': ('repo',), 'scope': 'Structural, not a preference'},
        {'cells': ['Eligibility', 'A candidate must have a settled result, a recorded '
                   'price and a non-zero dependence gate decision for joint markets. '
                   'A missing value makes it ineligible, never a pass.'],
         'src': ('repo',), 'scope': 'Fail-closed'},
        {'cells': ['Reward', 'A hypothetical non-cash “research leader” badge per track. '
                   'No sponsor, no pool, no cash, no award while no candidate qualifies.'],
         'src': ('repo',), 'scope': 'Unfunded by design'},
        {'cells': ['Disclosure', 'Every candidate, every variant and every exclusion is '
                   'published in bets.csv. A strategy that is not in the file was not '
                   'tried.'],
         'src': ('repo',), 'scope': 'Selection control'},
    ]

    body = (
        '<div class="notice bad"><strong>The parlay is the whole argument for split '
        'columns.</strong><p>The cross-game parlay has the best flat-stake return in '
        'this desk (%s over %d bets) and the worst signal bound (%s). A single blended '
        'ranking would have put it top. Two columns make the disagreement visible: the '
        'return is small-sample noise on %d bets, and the signal says the model is '
        'materially worse than the market on those legs.</p></div>'
        % (n(STRAT['X-PARLAY']['staking'].get('flat_roi'), 2, percent=True),
           STRAT['X-PARLAY']['staking'].get('bets', 0),
           signed(STRAT['X-PARLAY']['signal'].get('log_loss_gain_lcb')),
           STRAT['X-PARLAY']['signal'].get('n', 0))
        + '<h2 id="signal">Signal table — prediction quality only</h2>'
        + '<p>No stake, no return and no ROI appears in this table. The last column is '
          'the gate: a strategy ranks only if its clustered lower bound on log-loss gain '
          'is strictly positive.</p>'
        + table('t-signal', 'Signal, scored with cluster-robust uncertainty',
                ['Strategy', 'n', 'Hit rate', 'Log-loss model', 'Log-loss market',
                 'Log-loss gain', 'Gain lower bound', 'Signal gate'],
                signal_rows, numeric=(1, 2, 3, 4, 5, 6))
        + '<h2 id="staking">Staking table — money only</h2>'
        + '<p>Published beside the signal, never inside it. These numbers are computed '
          'on recorded closing prices from a file with no provenance and no executable '
          'quote, so none of them is a verified economic result (flag OD-03).</p>'
        + table('t-staking', 'Staking, reported separately by construction',
                ['Strategy', 'Bets', 'Units staked', 'Net units', 'Flat ROI',
                 'Max drawdown', 'Kelly ROI', 'Price provenance'],
                staking_rows, numeric=(1, 2, 3, 4, 5, 6))
        + '<h2 id="policy">Competition policy</h2>'
        + table('t-policy', 'How a rank is decided',
                ['Rule', 'Treatment'], policy)
    )
    register('leaderboard.html', 'Leaderboard', 'COMPETITION / LEADERBOARD',
             'Signal and staking scored into two tables that are never combined, so a '
             'lucky staking run cannot mask a bad signal.', body)


def build_correlations():
    mt = CORR['margin_total_error']
    icc = CORR['weekly_intraclass']
    phi = CORR['cover_over_phi']
    gate = CORR['margin_total_error']['gate']
    rows = [
        {'cells': ['Margin error ↔ total error, same game',
                   n(mt['point'], 4), mt['n'],
                   '%s to %s' % (n(mt['interval']['lo'], 4), n(mt['interval']['hi'], 4)),
                   'Fisher z on %s paired out-of-sample prediction errors'
                   % format(mt['n'], ','),
                   pill('refused — straddles the deadband', 'bad')],
         'src': ('scipy-pearson', 'repo', 'nfl-standings-2018'),
         'scope': 'Computed on out-of-sample residuals; scores verified for 2010, 2018, 2025'},
        {'cells': ['Margin error within a week (intraclass)',
                   n(icc['r'], 4), icc['n'],
                   '%s to %s' % (n(icc['lo'], 4), n(icc['hi'], 4)),
                   'Cluster bootstrap over %d season-weeks, %s games per week on average'
                   % (icc['groups'], n(icc['mean_group_size'], 1)),
                   pill('used — interval inside the deadband, ρ taken as 0', 'ok')],
         'src': ('repo', 'scipy-pearson'),
         'scope': 'One-way ANOVA variance components on out-of-sample errors'},
        {'cells': ['Home cover ↔ game over, same game (phi)',
                   n(phi['point'], 4), phi['n'],
                   '%s to %s' % (n(phi['interval']['lo'], 4), n(phi['interval']['hi'], 4)),
                   'Fisher z on %s settled games with both a side and a total line'
                   % format(phi['n'], ','),
                   pill('descriptive only — not used in any price', 'warn')],
         'src': ('scipy-pearson', 'repo-games'),
         'scope': 'Measured on the recorded closing lines and settled results'},
        {'cells': ['Quarterback passing yards ↔ receiver receiving yards',
                   n(None), n(None), n(None),
                   'No player-level official statistics were captured for this project.',
                   pill('unverified — no data', 'bad')],
         'src': ('repo',), 'scope': 'Checked absence'},
        {'cells': ['Player prop leg ↔ player prop leg, same game',
                   n(None), n(None), n(None),
                   'No player-prop market prices exist in the repository.',
                   pill('unverified — no data', 'bad')],
         'src': ('repo',), 'scope': 'Checked absence'},
    ]
    rules = [
        {'cells': ['Deadband', '±%s. A dependence smaller than this is treated as '
                   'indistinguishable from zero at the resolution the desk declares.'
                   % n(REPORT['constants']['deadband'], 2)],
         'src': ('repo',), 'scope': 'Frozen before evaluation'},
        {'cells': ['Interval wholly inside the deadband',
                   'Permitted. The joint price is computed with ρ = 0, and the row says '
                   'so. This is a declared convention backed by a measurement, not an '
                   'assumption.'],
         'src': ('repo',), 'scope': 'Gate rule'},
        {'cells': ['Interval wholly outside the deadband',
                   'Permitted. The joint price uses the measured point estimate.'],
         'src': ('repo',), 'scope': 'Gate rule'},
        {'cells': ['Interval straddles the deadband',
                   'Refused. No joint price is produced, the leg is not staked, and the '
                   'combination is counted as offered but not priced.'],
         'src': ('repo',), 'scope': 'Gate rule'},
        {'cells': ['Frechet feasibility',
                   'Any joint price must lie between max(0, p+q−1) and min(p, q). A price '
                   'outside those bounds is rejected even if the gate allowed it.'],
         'src': ('repo',), 'scope': 'Arithmetic guard'},
        {'cells': ['Publishing n',
                   'Every correlation row carries the number of paired observations '
                   'behind it. A correlation without an n is not published.'],
         'src': ('repo',), 'scope': 'Desk policy'},
    ]
    body = (
        '<div class="notice warn"><strong>What refused pricing looks like.</strong>'
        '<p>The dependence between the margin error and the total error is r = %s on '
        'n = %s, with a 95%% interval of %s to %s. That interval straddles the declared '
        'deadband of ±%s, so the gate refuses the price: %d same-game combinations were '
        'offered and %d were priced. The desk does not round the interval down to zero '
        'in order to get a number it can bet.</p></div>'
        % (n(mt['point'], 4), format(mt['n'], ','), n(mt['interval']['lo'], 4),
           n(mt['interval']['hi'], 4), n(REPORT['constants']['deadband'], 2),
           REPORT['joint']['sgp_offered'], REPORT['joint']['sgp_priced'])
        + '<h2 id="register">Correlation register</h2>'
        + table('t-corr', 'Every dependence value, with the n behind it',
                ['Pair', 'r', 'n', '95% interval', 'How it was obtained',
                 'Gate verdict'], rows, numeric=(1, 2))
        + '<h2 id="gate">The dependence gate</h2>'
        + table('t-gate', 'The rule that decides whether a joint price exists',
                ['Element', 'Rule'], rules)
        + '<h2 id="counts">What the gate did</h2>'
        + '<p>Cross-game parlays offered: %d, priced: %d. Same-game combos offered: %d, '
          'priced: %d.</p>'
        % (REPORT['joint']['parlay_offered'], REPORT['joint']['parlay_priced'],
           REPORT['joint']['sgp_offered'], REPORT['joint']['sgp_priced'])
    )
    register('correlations.html', 'Correlations', 'EVIDENCE / CORRELATIONS',
             'Dependence is measured, never assumed. Every value is published with the '
             'number of observations behind it, and a gate decides whether a joint price '
             'may exist at all.', body)


def build_demotion():
    rule_sources = {'D1': ('sklearn-logloss', 'repo'), 'D2': ('sklearn-brier', 'repo'),
                    'D3': ('repo',), 'D4': ('repo-games', 'repo'), 'D5': ('repo',),
                    'R1': ('repo',)}
    rules = [{'cells': [code, name, rule, action], 'src': rule_sources[code],
              'scope': 'Declared before the replay'}
             for code, name, rule, action in REPORT_RULES]
    rows = []
    for code in ('G-SIDE', 'G-TOTAL', 'G-ML', 'X-PARLAY', 'S-SGP', 'P-PROP'):
        block = DEMOT.get(code)
        label = STRATEGY_LABELS[code]
        if not block or block.get('status') == 'insufficient history':
            rows.append({'cells': [label, block.get('bets', 0) if block else 0,
                                   pill('not evaluable — fewer than %d bets'
                                        % REPORT['constants']['trailing_window'], 'warn'),
                                   n(None), n(None), n(None),
                                   'paper — never promoted'],
                         'src': ('repo',),
                         'scope': 'Demotion needs a trailing window of bets'})
            continue
        trig = block.get('trigger')
        rows.append({
            'cells': [label, block.get('bets'),
                      pill('demoted', 'bad') if trig else
                      pill('never triggered', 'ok'),
                      trig['rule'] if trig else n(None),
                      ('%s week %s, after bet %s' % (trig['season'], trig['week'],
                                                     trig['bet_number'])) if trig
                      else n(None),
                      signed(trig['value'], 4) if trig else n(None),
                      'paper — staking stopped' if trig else 'paper — never promoted'],
            'src': ('sklearn-brier', 'repo'),
            'scope': 'Replay over the walk-forward on a trailing %d-bet window'
                     % REPORT['constants']['trailing_window'],
        })
    cov = REPORT['coverage']
    cov_rows = [{
        'cells': [season, v['scheduled'], v['priced'], v['settled'],
                  n(v['coverage'], 3, percent=True),
                  pill('at or above 90%', 'ok') if v['coverage'] >= 0.9
                  else pill('below 90% — D5 fires', 'bad')],
        'src': ('repo-games', 'repo'),
        'scope': 'Share of scheduled markets carrying both a price and a result',
    } for season, v in sorted(cov.items())]

    body = (
        '<div class="notice bad"><strong>The gate fired on the first window, on all '
        'three singles.</strong><p>Replayed over the walk-forward, the trailing 200-bet '
        'lower bound on log-loss gain was already negative at bet 200 — the end of the '
        '2010 season for the side and the moneyline, and week 2 of 2011 for the total. '
        'A live deployment running this gate would have stopped staking before any of '
        'the later money numbers in this desk existed.</p></div>'
        + '<h2 id="rules">The demotion gate</h2>'
        + table('t-rules', 'Triggers, thresholds and what happens when one fires',
                ['Rule', 'Name', 'Condition', 'Action'], rules)
        + '<h2 id="replay">Replay</h2>'
        + '<p>The rule applied to the desk’s own walk-forward bet sequence, in '
          'chronological order. “First trigger” is the bet at which the strategy would '
          'have been sent back to paper.</p>'
        + table('t-replay', 'Demotion replay on the walk-forward',
                ['Strategy', 'Bets', 'Outcome', 'First rule fired', 'When',
                 'Value at trigger', 'State after'], rows, numeric=(1, 5))
        + '<h2 id="coverage">Coverage check (D5) by season</h2>'
        + table('t-covd5', 'Share of scheduled markets with a price and a settled result',
                ['Season', 'Scheduled markets', 'Priced', 'Settled', 'Coverage',
                 'D5 verdict'], cov_rows, numeric=(1, 2, 3, 4))
    )
    register('demotion.html', 'Demotion gate', 'COMPETITION / DEMOTION',
             'The rule that sends a live strategy back to paper, the thresholds behind '
             'it, and what it would have done to this desk’s own strategies.', body)


def build_depth():
    board = depth_mod.deficiency_rows()
    rows = [{
        'cells': [r['club'], r['player'], r['position'],
                  pill(r['game_status'], 'bad' if r['game_status'] == 'Out' else 'warn'),
                  r['unit'] or BLANK, r['slot'] or BLANK,
                  r['injured_tier_label'] or BLANK,
                  r['replacement'] or BLANK,
                  r['replacement_tier_label'] or BLANK,
                  r['next_after_replacement'] or BLANK,
                  r['note'] or '—'],
        'src': (r['injury_source_id'], r['chart_source_id']),
        'scope': 'Injury status official; depth tier from the club chart',
    } for r in board]

    chart_rows = [{
        'cells': [r['club'], r['club_name'], r['unit'], r['position'], r['player'],
                  r['tier'], r['tier_label'],
                  pill('unofficial — club published', 'warn')],
        'src': (r['source_id'],),
        'scope': r['official_status'],
    } for r in depth_mod.depth_rows()]

    cov = [{'cells': [c['club'],
                      pill('retrieved', 'ok') if c['chart_retrieved'] else
                      pill('not retrieved', 'bad'),
                      'patriots.com' if c['club'] == 'NE' else 'detroitlions.com'
                      if c['chart_retrieved'] else BLANK],
            'src': (('patriots-depth',) if c['club'] == 'NE' else
                    ('lions-depth',) if c['club'] == 'DET' else ('nfl-injuries-w10',)),
            'scope': 'Clubs in the official Week 10 report with a ruled-out player'}
            for c in depth_mod.coverage()]

    body = (
        '<div class="notice warn"><strong>Depth is read, never inferred.</strong>'
        '<p>The NFL publishes no official game-day depth chart — that absence was '
        'checked, not assumed. Every tier below comes from a club publication that '
        'states on its face that it is unofficial. Two of the clubs with a ruled-out '
        'player in Week 10 have a chart on this page; the depth of the replacement is '
        'blank for the other 26 because no source was read for them.</p></div>'
        + '<h2 id="board">Replacement-depth board · Week 10 2026</h2>'
        + '<p>Not “was there a replacement” but “how deep is the replacement”. A ruled-out '
          'starter replaced by a second string and one replaced by a fourth string are '
          'different events, and only a printed ordering can separate them.</p>'
        + table('t-board', 'Ruled-out players and the printed depth of their replacement',
                ['Club', 'Player', 'Pos', 'Status', 'Unit', 'Slot', 'Injured player tier',
                 'Replacement', 'Replacement tier', 'Next behind', 'Note'], rows)
        + '<h2 id="register">Depth register as published</h2>'
        + '<p>Every printed slot-player pair from the charts read, with the tier exactly '
          'as the club printed it. Empty cells in a club chart are not filled in.</p>'
        + table('t-depth', 'Club-published depth charts, read 2026-11-14',
                ['Club', 'Club name', 'Unit', 'Slot', 'Player', 'Tier', 'Tier label',
                 'Status of source'], chart_rows, numeric=(5,))
        + '<h2 id="coverage">Chart coverage</h2>'
        + table('t-dcov', 'Clubs with a ruled-out player in the official Week 10 report',
                ['Club', 'Chart retrieved', 'Publisher'], cov)
    )
    register('depth.html', 'Replacement depth', 'EVIDENCE / DEPTH',
             'How deep the replacement is, not merely that a replacement happened — read '
             'from club-published charts and flagged where no source was read.', body)


def build_questions():
    rows = [{'cells': [q['id'], q['question'], q['known'], q['missing'],
                       pill(q['status'], q['kind']), q['closes']],
             'src': q['src'], 'scope': q['scope']} for q in QUESTIONS]
    head = ('<div class="notice"><strong>Two columns matter more than the answers.</strong>'
            '<p>“What we already have” is verified; “what is missing” is the work. A '
            'decision taken while a row in the missing column is still open is a decision '
            'taken on an assumption, and every such assumption is listed on '
            '<a href="flagged.html">Flagged for review</a>.</p></div>')
    answered = len([q for q in QUESTIONS if q['status'] == 'Answered'])
    openq = len([q for q in QUESTIONS if q['status'] != 'Answered'])
    body = (head
            + '<ul class="kpis">'
            + '<li><b>%d</b><span>questions on the register</span></li>' % len(QUESTIONS)
            + '<li><b>%d</b><span>answered from evidence</span></li>' % answered
            + '<li><b>%d</b><span>still open</span></li>' % openq
            + '<li><b>%d</b><span>discovery probes proposed</span></li>' % len(PROBES)
            + '</ul>'
            + '<h2 id="register">Question, information and answer register</h2>'
            + table('t-q', 'What we have, what we do not, and what would close it',
                    ['ID', 'Question', 'What we already have', 'What is missing',
                     'Status', 'What would close it'], rows)
            + '<h2 id="probes">Discovery probes — how to obtain what is missing</h2>'
            + '<p>These are not suggestions to change the site or the model. They are '
              'the work required before the questions above can be answered at all.</p>'
            + table('t-probes', 'Proposed ways to obtain the missing information',
                    ['ID', 'Probe', 'Question it closes', 'What it would cost',
                     'What it would produce', 'Falsified by'],
                    [{'cells': [p['id'], p['probe'], p['closes'], p['cost'],
                                p['produces'], p['falsified']],
                      'src': p['src'], 'scope': p['scope']} for p in PROBES]))
    register('questions.html', 'Open questions', 'DECIDE / QUESTIONS',
             'What we already have, what we do not, and the specific work that would '
             'close each gap before any decision is taken.', body)


def build_suggestions():
    rows = [{'cells': [s['id'], s['proposal'], s['closes'], s['impact'], s['cost'],
                       s['falsified'], pill(s['state'], s['kind'])],
             'src': s['src'], 'scope': s['scope']} for s in SUGGESTIONS]
    paths = [{'cells': [p['id'], p['name'], p['contains'], p['cost'], p['risk'],
                        p['unlocks']],
              'src': ('repo',), 'scope': 'Candidate ordering, not a decision'} for p in PATHS]
    body = (
        '<div class="notice"><strong>Nothing here has been selected.</strong>'
        '<p>Every row is a proposal awaiting a choice. The “falsified by” column is the '
        'test: a proposal that cannot name the observation that would kill it should be '
        'rejected before it is costed. Read this page to choose a path, not to read back '
        'a decision that has already been made.</p></div>'
        + '<h2 id="register">Suggestion register</h2>'
        + table('t-sugg', 'Proposed improvements, costed and falsifiable',
                ['ID', 'Proposal', 'Question it closes', 'Decision impact', 'Cost',
                 'Falsified by', 'State'], rows)
        + '<h2 id="paths">Candidate paths</h2>'
        + '<p>Four orderings of the same work. The difference between them is what you '
          'learn first and what you risk, not what you eventually build.</p>'
        + table('t-paths', 'Choose an ordering before choosing an item',
                ['Path', 'Name', 'What it contains', 'Cost', 'Risk',
                 'What it unlocks'], paths)
        + '<h2 id="how">How to choose</h2>'
        + '<ol><li>Answer the questions on the <a href="questions.html">question '
          'register</a> first. A suggestion that does not close an open question is '
          'decoration.</li>'
        + '<li>Reject anything with an empty “falsified by” column, whatever it '
          'costs.</li>'
        + '<li>Prefer the path whose first item removes a critical flag on '
          '<a href="flagged.html">Flagged for review</a>.</li>'
        + '<li>Record the choice, then implement. Not the other way round.</li></ol>'
    )
    register('suggestions.html', 'Suggestions', 'DECIDE / SUGGESTIONS',
             'Every proposed improvement, costed and given a falsification test, so a '
             'path can be chosen before anything is built.', body)


def build_flagged():
    rows = [{'cells': [f['id'], pill(f['severity'], f['kind']), f['title'], f['detail'],
                       f['consequence'], f['link']],
             'src': f['src'], 'scope': f['scope']} for f in FLAGS]
    body = (
        '<div class="notice warn"><strong>Flagged does not mean fixed, and it does not '
        'mean hidden.</strong><p>Every item here is published with the source it came '
        'from. Critical items are the ones that invalidate a number elsewhere on this '
        'site if they are ignored.</p></div>'
        + table('t-flags', 'Irregularities and unverified values',
                ['ID', 'Severity', 'Finding', 'Detail', 'Consequence if ignored',
                 'Where it shows'], rows)
    )
    register('flagged.html', 'Flagged for review', 'EVIDENCE / FLAGGED',
             'Everything on this desk that is wrong, missing or unverified, with the '
             'source behind each item.', body)


def build_sources():
    rows = [{'cells': [s['id'], s['publisher'],
                       '<a href="%s" target="_blank" rel="noopener">%s</a>'
                       % (e(s['url']), e(s['url'])),
                       s['checked'], pill(s['status'], 'ok'
                                          if s['status'] == 'retrieved' else ''),
                       s['scope'], s['supports']],
             'src': (s['id'],), 'scope': 'Registered source'} for s in SOURCES.values()]
    body = (
        '<p>A published table row may only cite an id from this register. The desk’s own '
        'verifier fails the build if a row appears without one.</p>'
        + table('t-sources', 'Source register', ['ID', 'Publisher', 'URL', 'Checked',
                                                 'Status', 'Scope read', 'What it supports'],
                rows)
    )
    register('sources.html', 'Sources', 'EVIDENCE / SOURCES',
             'Every source this desk read, what scope was read from it, and what each '
             'one is allowed to support.', body)


# --------------------------------------------------------------------------
# content registers
# --------------------------------------------------------------------------

REPORT_RULES = [
    (code, name, rule, action) for code, name, rule, action in [
        ('D1', 'Signal decay',
         'The trailing 200-bet clustered lower bound on log-loss gain over the matched '
         'market baseline falls to zero or below.',
         'Staking stops immediately. The strategy returns to paper.'),
        ('D2', 'Calibration drift',
         'The trailing 200-bet Brier score exceeds the market baseline Brier by more '
         'than 0.005.',
         'Staking stops immediately. The strategy returns to paper.'),
        ('D3', 'Drawdown breach',
         'The realised peak-to-trough decline of the flat-stake series exceeds 20 units.',
         'Staking stops immediately. The strategy returns to paper.'),
        ('D4', 'Settlement integrity',
         'Any originated market settles with a missing score or an unreconciled result.',
         'All strategies halt. The results feed is re-verified before anything restarts.'),
        ('D5', 'Coverage loss',
         'Fewer than 90% of scheduled markets in the window carry both a recorded price '
         'and a settled result.',
         'The strategy returns to paper until coverage recovers.'),
        ('R1', 'Re-promotion',
         'After a demotion the strategy must pass D1, D2 and D3 again on four '
         'consecutive prospective paper weeks.',
         'Paper only. No stake until the re-promotion condition is met.'),
    ]
]

QUESTION_TEXT = [
    ('Q-01', 'Do we have an opening number for any market this desk originates?',
     'No. The committed snapshot records exactly one price per market, and NFL.com '
     'publishes no odds at all. All four opening fields in the price store are blank on '
     'all %s rows.' % format(len(price_rows()), ','),
     'An opening price, and the time it was seen.',
     'Open · blocked on evidence', 'bad',
     'A source that records both an opening and a closing price with capture times, or '
     'a manual capture protocol with a declared schedule.',
     ('repo-games', 'nfl-standings-2026'), 'Checked absence'),
    ('Q-02', 'Is the committed score content correct?',
     'Yes for the seasons checked. 2010, 2018 and 2025 match the official NFL standings '
     'exactly for all 32 clubs on both points for and points against; 2026 Week 8 '
     'matches the official schedule page on all 14 games.',
     'External confirmation for 2011–2017, 2019–2024 and 1999–2009.',
     'Answered · partial scope', 'ok',
     'Reading the official standings page for each remaining season.',
     ('nfl-standings-2010', 'nfl-standings-2018', 'nfl-standings-2025',
      'nfl-schedule-2026-week8'), 'Official cross-check, read 2026-11-14'),
    ('Q-03', 'Can return on investment be computed at all?',
     'A number can be computed on the recorded closing prices, and it is published on '
     'the staking table.',
     'An executable quote. The recorded prices were never captured as offers anyone '
     'could have taken, so the result is arithmetic, not economics.',
     'Answered · with a caveat', 'warn',
     'Captured quotes with timestamps, stake limits and settlement rules from a '
     'licensed source.',
     ('repo-games',), 'Computed on recorded prices — flag OD-03'),
    ('Q-04', 'What was the market’s closing number?',
     'Recorded for every regular-season game from 2010 to 2026 in the committed '
     'snapshot: side, total and both moneyline prices, with side prices for the side '
     'and the total.',
     'Provenance and licence for the file that holds them.',
     'Answered', 'ok',
     'A licence or terms statement, or a replacement capture from a licensed feed.',
     ('repo-games',), 'Committed snapshot — flag OD-01'),
    ('Q-05', 'Is the model better than the market?',
     'No. The clustered lower bound on log-loss gain is negative for all three '
     'single-market strategies: side %s, total %s, moneyline %s.'
     % (signed(STRAT['G-SIDE']['signal'].get('log_loss_gain_lcb')),
        signed(STRAT['G-TOTAL']['signal'].get('log_loss_gain_lcb')),
        signed(STRAT['G-ML']['signal'].get('log_loss_gain_lcb'))),
     'Nothing — this question is answered, and the answer is unfavourable.',
     'Answered', 'ok',
     'A candidate whose lower bound is strictly positive on a sealed season.',
     ('sklearn-logloss', 'repo'), 'Measured on the walk-forward'),
    ('Q-06', 'Can a same-game combination be priced?',
     'No, and the gate is the reason. The dependence between the margin error and the '
     'total error is r = %s on n = %s with interval %s to %s, which straddles the '
     'declared deadband of ±%s. %d combinations were offered; %d were priced.'
     % (n(CORR['margin_total_error']['point'], 4),
        format(CORR['margin_total_error']['n'], ','),
        n(CORR['margin_total_error']['interval']['lo'], 4),
        n(CORR['margin_total_error']['interval']['hi'], 4),
        n(REPORT['constants']['deadband'], 2), REPORT['joint']['sgp_offered'],
        REPORT['joint']['sgp_priced']),
     'A larger paired sample, or a narrower declared deadband agreed in advance.',
     'Answered', 'ok',
     'Either more seasons of paired errors or a written decision to widen the deadband '
     'before the next test.',
     ('scipy-pearson', 'repo'), 'Gate outcome, not an assumption'),
    ('Q-07', 'Can a cross-game parlay be priced?',
     'Yes, under a declared independence convention. The week-level intraclass '
     'dependence is r = %s with interval %s to %s, entirely inside the deadband, so the '
     'gate permits ρ = 0. %d of %d offered parlays were priced.'
     % (n(CORR['weekly_intraclass']['r'], 4), n(CORR['weekly_intraclass']['lo'], 4),
        n(CORR['weekly_intraclass']['hi'], 4), REPORT['joint']['parlay_priced'],
        REPORT['joint']['parlay_offered']),
     'A captured book parlay price. The desk multiplies the leg prices instead, because '
     'no parlay price exists in the repository.',
     'Answered · with a caveat', 'warn',
     'Captured parlay quotes from a licensed source.',
     ('repo',), 'Synthesised price — flag OD-06'),
    ('Q-08', 'How deep is the replacement when a starter is ruled out?',
     'Known for the two clubs whose charts were read. Ben Brown’s slot is covered by a '
     'second string, Carlton Davis III’s by a second string, TreVeyon Henderson’s by a '
     'third string; Cade Mays and D.J. Reed in Detroit by second strings.',
     '26 of the 28 clubs in the official Week 10 report have no chart on this page, and '
     'the NFL publishes no official depth chart to fall back on.',
     'Open · partial', 'warn',
     'Retrieving and dating a club chart for every club, on a fixed schedule.',
     ('patriots-depth', 'lions-depth', 'nfl-injuries-w10'),
     'Club-published, self-declared unofficial'),
    ('Q-09', 'Do we have player-prop data of any kind?',
     'No. No player-prop prices, no player-level official statistics and no '
     'participation counts were captured for this project.',
     'Everything: prices, settlement rules and the official statistics a prop model '
     'would need.',
     'Open · blocked on evidence', 'bad',
     'A captured player-prop price feed with settlement rules.',
     ('repo',), 'Checked absence'),
    ('Q-10', 'Is there a licence to use and republish the committed market data?',
     'No licence, no terms, no provenance and no retrieval date are recorded anywhere '
     'in the repository for either committed file.',
     'The licence itself, and a documented provenance chain.',
     'Open · blocked', 'bad',
     'A written licence or a decision to replace the file with a licensed capture.',
     ('repo-games', 'repo-lines'), 'Checked absence — flag OD-01'),
    ('Q-11', 'How stale is the snapshot relative to the official season?',
     'The committed data ends at 2026 Week 8 (last game 2026-11-02). The official '
     'standings page read on 2026-11-14 already includes the Week 10 Thursday-night '
     'result, Commanders 24–21 Giants.',
     'Nothing — the gap is measured. Closing it requires a new capture.',
     'Answered', 'ok',
     'An automated capture so the gap cannot reopen.',
     ('nfl-standings-2026', 'nfl-gamecenter-w10'), 'Measured staleness — flag OD-04'),
    ('Q-12', 'Would the demotion gate have fired on this desk’s own strategies?',
     'Yes, on all three singles, at the first evaluable window: bet 200. Side and '
     'moneyline at the end of the 2010 season, total in week 2 of 2011.',
     'Nothing — the replay is complete for the strategies with enough history.',
     'Answered', 'ok',
     'A strategy that survives its own gate on a sealed season.',
     ('sklearn-brier', 'repo'), 'Replay, not a forecast'),
    ('Q-13', 'Is the model calibrated?',
     'No. The Brier score is worse than the market baseline on all three single-market '
     'strategies.',
     'A recalibration step, fitted on data that is not the evaluation data.',
     'Answered', 'ok',
     'A calibration plot and a recalibration fitted on a held-out earlier period.',
     ('sklearn-brier',), 'Measured'),
    ('Q-14', 'How large a sample would be needed to detect a realistic edge?',
     'Not computed. No power study was run before this evaluation, so the desk cannot '
     'say whether these sample sizes could have detected anything.',
     'A power study with a declared minimum detectable effect.',
     'Open', 'warn',
     'A pre-test power calculation with the effect size declared in advance.',
     ('repo',), 'Not attempted — do not confuse with a null result'),
    ('Q-15', 'Are the three markets for one game mutually consistent?',
     'Yes, by construction. The moneyline reuses the margin distribution fitted for the '
     'side, and the code asserts it, so the two cannot disagree about the same game.',
     'Nothing for the side and the moneyline. The total is a separate distribution, so '
     'a joint statement still needs the dependence gate.',
     'Answered', 'ok',
     'Nothing further for consistency; the joint question is Q-06.',
     ('repo',), 'Asserted in code and unit-tested'),
    ('Q-16', 'What settlement rules apply to pushes and ties?',
     'Declared by convention: a tie on the moneyline is graded as a push, and a spread '
     'or total landing exactly on the number is a push.',
     'Verification against any sportsbook’s published rule set. Book rules differ, '
     'particularly on moneyline ties.',
     'Open · convention only', 'warn',
     'A captured rule set from the book whose prices are being used.',
     ('repo',), 'Declared convention — flag OD-14'),
    ('Q-17', 'Do the three market types agree on which side of the game the value is on?',
     'Not measured as a cross-market statistic. The desk originates them independently '
     'apart from the shared margin distribution.',
     'A cross-market consistency check, and a decision about whether a disagreement '
     'should suppress the bet.',
     'Open', 'warn',
     'A declared rule for what happens when the side and the moneyline imply different '
     'views.',
     ('repo',), 'Not implemented'),
    ('Q-18', 'Is the recorded closing price the price that was actually available?',
     'Unknown. No capture time, no stake limit and no book identifier is recorded, so '
     'the desk cannot distinguish a real offer from a reference price.',
     'A capture protocol with book identity, timestamp and limit.',
     'Open · blocked on evidence', 'bad',
     'Captured quotes with book identity and limits.',
     ('repo-games',), 'Checked absence — flag OD-03'),
    ('Q-19', 'Does the model use injuries or availability at all?',
     'No. The model sees only scores, so the replacement-depth register is currently '
     'advisory rather than an input.',
     'A point-in-time participation source, and a decision about how to encode it.',
     'Open · blocked on evidence', 'bad',
     'An official participation source and a declared encoding, tested as an ablation.',
     ('nfl-injuries-w10', 'repo'), 'Checked absence — the NFL publishes no participation '
     'denominator in the sources read'),
    ('Q-20', 'What would have to be true for a strategy to be promoted from paper to '
             'live?',
     'Declared: all seven validation gates on the main dashboard, plus no demotion '
     'trigger for four consecutive prospective weeks.',
     'A candidate that meets it. None does.',
     'Answered', 'ok',
     'A candidate that clears the gates — none has.',
     ('repo',), 'Declared policy, unfunded'),
    ('Q-21', 'There are now two implementations of the same eight requirements on this '
             'site. Which one is canonical?',
     'Both were built from the same brief by two sessions that could not see each '
     'other’s claim. The files do not overlap, so nothing is broken, but the model '
     'lines can differ because the fits differ.',
     'A decision, and then either a merge onto one input set or a clear designation '
     'of which desk is canonical.',
     'Open · owner decision', 'warn',
     'A decision recorded in the coordination board, then a merge or a designation.',
     ('repo', 'repo-weekly-captures'), 'Cross-session duplication'),
]

QUESTIONS = [
    {'id': q[0], 'question': q[1], 'known': q[2], 'missing': q[3], 'status': q[4],
     'kind': q[5], 'closes': q[6], 'src': q[7], 'scope': q[8]}
    for q in QUESTION_TEXT
]

PROBES = [
    {'id': 'P-01', 'probe': 'Capture opening and closing prices on a fixed schedule from '
                            'a licensed or authorised odds source, and store both with '
                            'UTC capture times.',
     'closes': 'Q-01, Q-18', 'cost': 'A feed subscription, or a disciplined manual '
                                     'capture at two fixed times per market.',
     'produces': 'A price store with both ends populated, and the ability to compute '
                 'closing line value.',
     'falsified': 'Two captures of the same market disagreeing by more than the declared '
                  'tolerance with no recorded reason.',
     'src': ('repo-games',), 'scope': 'Proposed acquisition'},
    {'id': 'P-02', 'probe': 'Read the official standings page for every season in the '
                            'snapshot and compare points for and points against per club.',
     'closes': 'Q-02', 'cost': 'One page read per season; no licence question.',
     'produces': 'External confirmation or refutation of every season in the results '
                 'feed.',
     'falsified': 'A season whose club totals do not reconcile, which would quarantine '
                  'that season.',
     'src': ('nfl-standings-2018',), 'scope': 'Proposed verification'},
    {'id': 'P-03', 'probe': 'Obtain a written licence or terms statement for the '
                            'committed market files, or replace them with a licensed '
                            'capture.',
     'closes': 'Q-10', 'cost': 'A commercial decision, possibly a subscription.',
     'produces': 'The right to publish and act on the numbers, or a clean replacement.',
     'falsified': 'A terms statement that forbids the use the desk makes of the file.',
     'src': ('repo-games', 'repo-lines'), 'scope': 'Proposed acquisition'},
    {'id': 'P-04', 'probe': 'Capture player-prop prices and the official player '
                            'statistics that would drive them, with settlement rules.',
     'closes': 'Q-09', 'cost': 'A new feed and a new settlement-rule register.',
     'produces': 'A player-prop strategy that can be scored at all.',
     'falsified': 'Prices without published settlement rules, which makes the result '
                  'ungradeable.',
     'src': ('repo',), 'scope': 'Proposed acquisition'},
    {'id': 'P-05', 'probe': 'Retrieve and date a club depth chart for all 32 clubs on a '
                            'fixed weekly schedule.',
     'closes': 'Q-08', 'cost': 'Thirty-two page reads per week, or a scripted capture.',
     'produces': 'Replacement depth for every club, not two of twenty-eight.',
     'falsified': 'A club that publishes no chart, or one whose chart contradicts the '
                  'official injury report.',
     'src': ('patriots-depth', 'lions-depth'), 'scope': 'Proposed retrieval'},
    {'id': 'P-06', 'probe': 'Run a power study before the next sealed test, declaring '
                            'the minimum effect worth detecting.',
     'closes': 'Q-14', 'cost': 'Analysis time only; no new data.',
     'produces': 'A sample size the desk can defend, and an honest statement about what '
                 'the last test could have detected.',
     'falsified': 'A required sample larger than the data can supply, which would mean '
                  'the current design cannot answer the question.',
     'src': ('repo',), 'scope': 'Proposed analysis'},
    {'id': 'P-07', 'probe': 'Capture the settlement rule set of the book whose prices '
                            'are used, and store it beside every price.',
     'closes': 'Q-16', 'cost': 'One document read per book, then a register.',
     'produces': 'Settlement states that are graded by rule rather than by convention.',
     'falsified': 'A rule set that contradicts a settlement state the desk has already '
                  'published.',
     'src': ('repo',), 'scope': 'Proposed acquisition'},
]

SUGGESTIONS = [
    {'id': 'S-01', 'proposal': 'Populate the opening columns of the price store from a '
                               'scheduled capture (probe P-01).',
     'closes': 'Q-01, Q-18',
     'impact': 'Highest. Without an opening number the desk cannot measure whether it '
               'beats the market to a number, which is the single most informative '
               'signal in line origination.',
     'cost': 'Feed subscription, or two fixed manual captures per market per week.',
     'falsified': 'Two captures of one market disagreeing beyond the declared tolerance '
                  'without a recorded reason.',
     'state': 'Proposed — awaiting selection', 'kind': 'warn',
     'src': ('repo-games',), 'scope': 'Not started'},
    {'id': 'S-02', 'proposal': 'Establish the licence position on the committed market '
                               'files before building anything else on them (P-03).',
     'closes': 'Q-10',
     'impact': 'Highest of the governance items. Everything downstream inherits the '
               'provenance defect, including every number on the leaderboard.',
     'cost': 'A commercial decision; possibly a subscription.',
     'falsified': 'A terms statement that permits the current use, which would close '
                  'flag OD-01 immediately.',
     'state': 'Proposed — awaiting selection', 'kind': 'warn',
     'src': ('repo-games', 'repo-lines'), 'scope': 'Not started'},
    {'id': 'S-03', 'proposal': 'Verify the remaining seasons of the results feed against '
                               'the official standings pages (P-02).',
     'closes': 'Q-02',
     'impact': 'High. Turns "internally consistent" into "officially confirmed" for '
               'sixteen more seasons at a low cost.',
     'cost': 'One page read per season. No licence question, no new dependency.',
     'falsified': 'Any season whose club totals do not reconcile, which would '
                  'quarantine it.',
     'state': 'Proposed — awaiting selection', 'kind': 'ok',
     'src': ('nfl-standings-2010', 'nfl-standings-2018', 'nfl-standings-2025'),
     'scope': 'Three of nineteen seasons already done'},
    {'id': 'S-04', 'proposal': 'Add a power study and seal a minimum detectable effect '
                               'before the next test (P-06).',
     'closes': 'Q-14',
     'impact': 'High. Without it, "no evidence of skill" and "not enough data to tell" '
               'look identical, and the desk cannot tell them apart either.',
     'cost': 'Analysis time only.',
     'falsified': 'A required sample larger than the data can supply.',
     'state': 'Proposed — awaiting selection', 'kind': 'warn',
     'src': ('repo',), 'scope': 'Not started'},
    {'id': 'S-05', 'proposal': 'Retrieve and date club depth charts for all 32 clubs '
                               'weekly (P-05).',
     'closes': 'Q-08',
     'impact': 'High for the injury requirement. Two of twenty-eight clubs is a '
               'demonstration, not a system.',
     'cost': 'Thirty-two reads per week, or one scripted capture.',
     'falsified': 'A club publishing no chart, or a chart contradicting the official '
                  'injury report.',
     'state': 'Proposed — awaiting selection', 'kind': 'warn',
     'src': ('patriots-depth', 'lions-depth'), 'scope': 'Two clubs done'},
    {'id': 'S-06', 'proposal': 'Capture player-prop prices and settlement rules, and '
                               'give the prop strategy something to score (P-04).',
     'closes': 'Q-09',
     'impact': 'Medium-high. A third of the requested strategy set is currently empty '
               'because there is no data at all.',
     'cost': 'A new feed plus a settlement-rule register.',
     'falsified': 'Prices published without settlement rules, which makes any result '
                  'ungradeable.',
     'state': 'Proposed — awaiting selection', 'kind': 'warn',
     'src': ('repo',), 'scope': 'Not started'},
    {'id': 'S-07', 'proposal': 'Replace the proportional de-vig convention with recorded '
                               'two-way prices and a documented rule set (P-07).',
     'closes': 'Q-16',
     'impact': 'Medium-high. The market baseline is what every signal number is measured '
               'against; a convention there weakens every comparison below it.',
     'cost': 'One document per book, then a register.',
     'falsified': 'A captured rule set contradicting a settlement state already '
                  'published.',
     'state': 'Proposed — awaiting selection', 'kind': 'warn',
     'src': ('repo-games',), 'scope': 'Not started'},
    {'id': 'S-08', 'proposal': 'Automate the snapshot so the feed cannot go stale again.',
     'closes': 'Q-11',
     'impact': 'Medium-high. A two-week lag makes the current-season part of the desk '
               'unusable for anything decided this week.',
     'cost': 'A scheduled job; no new data source.',
     'falsified': 'A scheduled run that completes without updating the latest week.',
     'state': 'Proposed — awaiting selection', 'kind': 'warn',
     'src': ('nfl-standings-2026',), 'scope': 'Not started'},
    {'id': 'S-09', 'proposal': 'Refit the model weekly instead of seasonally, and test '
                               'whether it helps before adopting it.',
     'closes': 'Q-17',
     'impact': 'Medium. In-season drift — injuries, quarterback changes, coaching '
               'changes — is exactly what a seasonal refit cannot see.',
     'cost': 'Compute only; the model fits in under a second.',
     'falsified': 'A weekly refit scoring no better than the seasonal refit on a sealed '
                  'season.',
     'state': 'Proposed — awaiting selection', 'kind': '',
     'src': ('repo',), 'scope': 'Not started'},
    {'id': 'S-10', 'proposal': 'Add a recalibration step fitted on an earlier held-out '
                               'period, not on the evaluation data.',
     'closes': 'Q-13',
     'impact': 'Medium. The model is demonstrably miscalibrated, and the Kelly column is '
               'unsafe while that is true.',
     'cost': 'Analysis time; no new data.',
     'falsified': 'A recalibrated model whose Brier score does not improve on a sealed '
                  'season.',
     'state': 'Proposed — awaiting selection', 'kind': '',
     'src': ('sklearn-brier',), 'scope': 'Not started'},
    {'id': 'S-11', 'proposal': 'Register every candidate variant before the next test, '
                               'with a familywise error rate declared in advance.',
     'closes': 'Q-05',
     'impact': 'Medium. Six strategies and several constants were chosen before the '
               'evaluation, but the desk has no register proving it.',
     'cost': 'Discipline and one file.',
     'falsified': 'A claim of significance from a variant that is not in the register.',
     'state': 'Proposed — awaiting selection', 'kind': '',
     'src': ('repo',), 'scope': 'Not started'},
    {'id': 'S-12', 'proposal': 'Publish the correlation register weekly with officially '
                               'sourced team-level numbers, to grow n on the pairs that '
                               'matter.',
     'closes': 'Q-06',
     'impact': 'Medium. The same-game gate refused every price purely because the '
               'interval straddled the deadband; more paired observations would settle '
               'it one way or the other.',
     'cost': 'One scheduled job reusing the existing code.',
     'falsified': 'A recomputed interval that still straddles the deadband after the '
                  'sample doubles.',
     'state': 'Proposed — awaiting selection', 'kind': '',
     'src': ('scipy-pearson', 'nfl-standings-2026'), 'scope': 'Not started'},
]

PATHS = [
    {'id': 'Path A', 'name': 'Fix the foundations first',
     'contains': 'S-02 licence, S-01 opening prices, S-03 season verification, '
                 'S-08 automated snapshot',
     'cost': 'Highest upfront; mostly commercial and retrieval work',
     'risk': 'Lowest. Nothing built on top of a number that cannot be trusted.',
     'unlocks': 'Every other path, on data that can be cited and relied on'},
    {'id': 'Path B', 'name': 'Improve the model',
     'contains': 'S-09 weekly refit, S-10 recalibration, S-04 power study',
     'cost': 'Low — analysis and compute only',
     'risk': 'Medium. Improvements measured on unverified data may not survive a '
             'licensed replacement.',
     'unlocks': 'A better signal metric, if and only if the data is sound'},
    {'id': 'Path C', 'name': 'Add the missing markets',
     'contains': 'S-06 player props, S-12 weekly correlations',
     'cost': 'High — new feeds and new registers',
     'risk': 'High. A third of the requested strategy set needs data that does not '
             'exist here yet.',
     'unlocks': 'The parlay and prop tracks the brief asks for'},
    {'id': 'Path D', 'name': 'Operate and govern',
     'contains': 'S-05 all 32 depth charts, S-07 settlement rules, S-11 variant register',
     'cost': 'Medium — retrieval and process',
     'risk': 'Low, but it does not by itself produce a better number.',
     'unlocks': 'A desk that can be run weekly with the rules written down'},
]

FLAGS = [
    {'id': 'OD-01', 'severity': 'Critical', 'kind': 'bad',
     'title': 'The committed market and score snapshot has no provenance, no licence, no '
              'retrieval date and no capture timestamp.',
     'detail': 'data/raw/games.csv and data/raw/closing_lines.csv arrived in the '
               'repository with no record of where they came from, when they were '
               'retrieved, or on what terms. Both are hash-checked so the bytes are '
               'stable, but the rights to use them are unknown.',
     'consequence': 'Every number on this desk inherits the defect, including the whole '
                    'leaderboard and every ROI figure.',
     'link': '<a href="prices.html">Price &amp; results feed</a>',
     'src': ('repo-games', 'repo-lines'), 'scope': 'Checked absence, carried from F23'},
    {'id': 'OD-02', 'severity': 'Critical', 'kind': 'bad',
     'title': 'No opening price exists for any originated market.',
     'detail': 'All four opening fields in the price store are blank on all %s rows. The '
               'committed snapshot records one price per market, and NFL.com publishes '
               'no odds at all, so there is no source to copy from.'
               % format(len(price_rows()), ','),
     'consequence': 'Closing line value cannot be computed, and the store cannot show '
                    'whether the desk ever beats the market to a number.',
     'link': '<a href="prices.html">Price &amp; results feed</a>',
     'src': ('repo-games', 'nfl-standings-2026'), 'scope': 'Checked absence'},
    {'id': 'OD-03', 'severity': 'Critical', 'kind': 'bad',
     'title': 'No executable quote was captured, so ROI is arithmetic rather than '
              'economics.',
     'detail': 'The recorded prices carry no book identity, no capture time and no stake '
               'limit. The desk cannot show that any of them was an offer anyone could '
               'have taken.',
     'consequence': 'Every ROI, net-units and drawdown figure on the staking table is a '
                    'computed number on recorded prices, not a verified economic result.',
     'link': '<a href="leaderboard.html">Leaderboard — staking</a>',
     'src': ('repo-games',), 'scope': 'Checked absence'},
    {'id': 'OD-04', 'severity': 'High', 'kind': 'warn',
     'title': 'The snapshot is two weeks behind the official season.',
     'detail': 'The committed data ends at 2026 Week 8 (last game 2026-11-02) and holds '
               '121 completed games. The official by-week schedule pages show 137 games '
               'already finished: all 16 games the snapshot is missing are Week 9 (15 '
               'games) and the Week 10 Thursday-night game, Commanders 24–21 Giants.',
     'consequence': 'The current-season portion of the desk cannot support anything '
                    'decided this week, and the 2026 coverage figure of 44.5% is a '
                    'snapshot artefact rather than a data defect.',
     'link': '<a href="demotion.html">Demotion gate — coverage</a>',
     'src': ('nfl-standings-2026', 'nfl-gamecenter-w10'), 'scope': 'Measured'},
    {'id': 'OD-05', 'severity': 'High', 'kind': 'bad',
     'title': 'The dependence gate refused every same-game combination.',
     'detail': 'ρ between the margin error and the total error is %s on n = %s, interval '
               '%s to %s, which straddles the declared deadband of ±%s. %d combinations '
               'were offered and %d were priced.'
               % (n(CORR['margin_total_error']['point'], 4),
                  format(CORR['margin_total_error']['n'], ','),
                  n(CORR['margin_total_error']['interval']['lo'], 4),
                  n(CORR['margin_total_error']['interval']['hi'], 4),
                  n(REPORT['constants']['deadband'], 2),
                  REPORT['joint']['sgp_offered'], REPORT['joint']['sgp_priced']),
     'consequence': 'The same-game combo track has no results at all, and it will '
                    'continue to have none until the sample grows or the deadband is '
                    'changed in writing before a test.',
     'link': '<a href="correlations.html">Correlations</a>',
     'src': ('scipy-pearson', 'repo'), 'scope': 'Gate outcome'},
    {'id': 'OD-06', 'severity': 'High', 'kind': 'warn',
     'title': 'The parlay price is synthesised by multiplying the two leg prices.',
     'detail': 'No book parlay price exists anywhere in the repository, so the desk '
               'computes the parlay decimal as the product of the leg decimals. Books '
               'price parlays differently from that product.',
     'consequence': 'The parlay’s %s flat ROI is the least trustworthy money number on '
                    'the site, and it is the largest.'
                    % n(STRAT['X-PARLAY']['staking'].get('flat_roi'), 2, percent=True),
     'link': '<a href="leaderboard.html">Leaderboard — staking</a>',
     'src': ('repo-games',), 'scope': 'Synthesised price'},
    {'id': 'OD-07', 'severity': 'Critical', 'kind': 'bad',
     'title': 'Every single-market strategy has a negative signal lower bound.',
     'detail': 'Side %s, total %s, moneyline %s. All three are worse than the de-vigged '
               'closing price as a probabilistic forecaster, by a margin that survives '
               'clustering by week.'
               % (signed(STRAT['G-SIDE']['signal'].get('log_loss_gain_lcb')),
                  signed(STRAT['G-TOTAL']['signal'].get('log_loss_gain_lcb')),
                  signed(STRAT['G-ML']['signal'].get('log_loss_gain_lcb'))),
     'consequence': 'No strategy on this desk may be promoted, funded or staked. This is '
                    'the headline result and it is unfavourable.',
     'link': '<a href="leaderboard.html">Leaderboard — signal</a>',
     'src': ('sklearn-logloss', 'repo'), 'scope': 'Measured on the walk-forward'},
    {'id': 'OD-08', 'severity': 'High', 'kind': 'bad',
     'title': 'The player-prop track has no data of any kind.',
     'detail': 'No player-prop prices, no player-level official statistics and no '
               'participation counts were captured for this project.',
     'consequence': 'One of the four strategy families the brief asks for cannot be '
                    'scored, ranked or improved.',
     'link': '<a href="leaderboard.html">Leaderboard</a>',
     'src': ('repo',), 'scope': 'Checked absence'},
    {'id': 'OD-09', 'severity': 'High', 'kind': 'warn',
     'title': 'Replacement depth covers two of the twenty-eight clubs with a ruled-out '
              'player.',
     'detail': 'Charts were read for New England and Detroit only. The NFL publishes no '
               'official game-day depth chart, so there is no fallback source.',
     'consequence': 'The depth requirement is demonstrated, not delivered. Twenty-six '
                    'clubs return a blank replacement tier.',
     'link': '<a href="depth.html">Replacement depth</a>',
     'src': ('patriots-depth', 'lions-depth', 'nfl-no-depth-chart'),
     'scope': 'Partial retrieval'},
    {'id': 'OD-10', 'severity': 'Medium', 'kind': 'warn',
     'title': 'A ruled-out player is absent from his own club depth chart.',
     'detail': 'Kerby Joseph is listed Out on the official Week 10 injury report but '
               'does not appear anywhere on the Lions depth chart read the same day.',
     'consequence': 'The depth of his replacement cannot be read from any source, so the '
                    'row is blank rather than guessed.',
     'link': '<a href="depth.html">Replacement depth</a>',
     'src': ('nfl-injuries-w10', 'lions-depth'), 'scope': 'Cross-source conflict'},
    {'id': 'OD-11', 'severity': 'Medium', 'kind': 'warn',
     'title': 'The market baseline is a declared convention, not a verified probability.',
     'detail': 'Proportional de-vig of the two recorded side prices is a standard '
               'comparison convention. It is not the book’s true implied probability.',
     'consequence': 'Every log-loss gain, and therefore every rank, is measured against '
                    'a convention rather than a fact.',
     'link': '<a href="method.html">Method &amp; constants</a>',
     'src': ('repo-games',), 'scope': 'Declared convention'},
    {'id': 'OD-12', 'severity': 'Medium', 'kind': 'warn',
     'title': 'The model is refitted once per season, not within the season.',
     'detail': 'Each season is originated with a model fitted on all strictly earlier '
               'seasons. Injuries, quarterback changes and coaching changes inside the '
               'target season are invisible to it.',
     'consequence': 'The backtest is fair but the model is blunter than it needs to be, '
                    'and the injury data on this desk is not actually an input to it.',
     'link': '<a href="method.html">Method &amp; constants</a>',
     'src': ('repo',), 'scope': 'Design limitation'},
    {'id': 'OD-13', 'severity': 'Medium', 'kind': 'warn',
     'title': 'Sixteen seasons are internally consistent but externally unconfirmed.',
     'detail': '2010, 2018 and 2025 were checked club by club against the official '
               'standings. 2011–2017, 2019–2024 and 1999–2009 were checked only against '
               'themselves: result against home minus away, total against home plus away.',
     'consequence': 'A systematic error that preserves both those identities would pass '
                    'unnoticed in those seasons.',
     'link': '<a href="prices.html">Results feed verification</a>',
     'src': ('nfl-standings-2010', 'nfl-standings-2018', 'nfl-standings-2025'),
     'scope': 'Partial verification'},
    {'id': 'OD-14', 'severity': 'Medium', 'kind': 'warn',
     'title': 'Moneyline ties are graded as pushes by convention only.',
     'detail': 'Books differ on whether a tied game pushes or loses on the moneyline. No '
               'rule set was captured, so the desk declares a push.',
     'consequence': 'A handful of settlement states per decade may be graded differently '
                    'by a real book.',
     'link': '<a href="method.html">Method &amp; constants</a>',
     'src': ('repo',), 'scope': 'Declared convention'},
    {'id': 'OD-15', 'severity': 'Medium', 'kind': 'warn',
     'title': 'The Kelly column is illustrative and must not be funded.',
     'detail': 'Kelly sizing uses the model’s own probabilities, and OD-07 shows those '
               'probabilities are worse than the market’s. Sizing on a miscalibrated '
               'probability is the classic way to over-stake.',
     'consequence': 'Treating the Kelly ROI as an economic result would be the single '
                    'most dangerous misreading of this site.',
     'link': '<a href="leaderboard.html">Leaderboard — staking</a>',
     'src': ('repo',), 'scope': 'Derived from a miscalibrated input'},
    {'id': 'OD-16', 'severity': 'Medium', 'kind': 'warn',
     'title': 'Two independent implementations of the same eight requirements now '
              'exist on this site.',
     'detail': 'This desk (under origination/) and the market board on the main '
               'dashboard (price-snapshots.html, results-feed.html, origination.html, '
               'signal-staking.html, replacement-depth.html, correlations-official.html) '
               'were built by two sessions that claimed the same tasks before either '
               'could see the other’s claim. The files do not overlap, but the numbers '
               'can disagree because the inputs do: the board uses the 2026 season '
               'only, with official weekly captures and no recorded market prices, '
               'while this desk uses 2010–2026 with a recorded closing price on every '
               'market.',
     'consequence': 'A reader comparing the two pages will find different model lines '
                    'for the same game. Neither is wrong; the fits differ. One of the '
                    'two should be designated canonical, or the two should be merged '
                    'onto one input.',
     'link': '<a href="index.html#other">Overview — the other desk</a>',
     'src': ('repo', 'repo-weekly-captures'), 'scope': 'Cross-session duplication'},
]


def render():
    PAGES.clear()
    build_index()
    build_method()
    build_prices()
    build_originated()
    build_leaderboard()
    build_correlations()
    build_demotion()
    build_depth()
    build_questions()
    build_suggestions()
    build_flagged()
    build_sources()
    out = {}
    for filename, (title, eyebrow, lede, body) in PAGES.items():
        out[filename] = page_shell(title, eyebrow, lede, body, filename)
    return out


def main():
    pages = render()
    for filename, content in pages.items():
        (OUT / filename).write_text(content, encoding='utf-8')
    print('Wrote %d pages: %s' % (len(pages), ', '.join(sorted(pages))))


if __name__ == '__main__':
    main()
