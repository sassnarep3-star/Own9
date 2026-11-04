"""Builds the static GitHub Pages site from data/results/summary.json and data/source/verified_games.csv.

Run: python3 tools/analyze.py && python3 tools/build.py
Every table row carries a link to an official site (nfl.com, wsgc.wa.gov, nist.gov) in its last cell.
Third-party references are labelled as such and never stand in for an official source.
"""
import csv, json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
S = json.loads((ROOT / 'data/results/summary.json').read_text())
VERIFIED = list(csv.DictReader(open(ROOT / 'data/source/verified_games.csv', encoding='utf-8')))

NFL_SCHED = 'https://www.nfl.com/schedules'
NFL_STATS = 'https://www.nfl.com/stats/player-stats/'
NFL_GAMES = 'https://www.nfl.com/games/'
WSGC = 'https://wsgc.wa.gov/sports-wagering-frequently-asked-questions'
NIST = 'https://www.itl.nist.gov/div898/handbook/eda/section4/eda4283.htm'
THIRD_NFLVERSE = 'https://github.com/nflverse/nfldata'
THIRD_DATASETS = 'https://github.com/nflverse/nfldata/blob/master/DATASETS.md'
THIRD_GAMES = 'https://github.com/nflverse/nfldata/blob/master/data/games.csv'

P = S['parameters']
BE = P['breakeven']
TEST_T = S['strategies']
SHA = S['generated_from']['sha256']


def pct(x, d=1):
    return '—' if x is None else f'{x * 100:.{d}f}%'


def num(x, d=2):
    return '—' if x is None else f'{x:.{d}f}'


def ci(c, pc=True):
    if not c or c[0] is None:
        return '—'
    return f'{pct(c[0])} to {pct(c[1])}' if pc else f'{num(c[0], 3)} to {num(c[1], 3)}'


def link(url, label='Official source ↗'):
    return f'<a href="{escape(url)}" rel="noopener">{escape(label)}</a>'


def table(headers, rows, caption=None):
    head = ''.join(f'<th>{escape(h)}</th>' for h in headers)
    body = ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>' for r in rows)
    cap = f'<caption>{escape(caption)}</caption>' if caption else ''
    return f'<div class="table-wrap"><table>{cap}<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def tag(status):
    cls = {'FAIL': 'bad', 'PASS': 'good', 'PARTIAL': 'warn', 'NOT RUN': 'muted', 'Not validated': 'bad',
           'Unverified': 'warn', 'Flagged': 'warn', 'Verified': 'good', 'Not eligible': 'bad',
           'Computed from unverified lines': 'warn', 'Not run': 'muted', 'Verified (sample)': 'good'}.get(status, 'muted')
    return f'<span class="tag {cls}">{escape(status)}</span>'


def cell(x):
    return x


# ---------- derived numbers ----------
t2 = S['strategies']['S_T2']['periods']['test']
t1 = S['strategies']['S_T1']['periods']['test']
t3 = S['strategies']['S_T3']['periods']['test']
tr2 = S['strategies']['S_T2']['periods']['train']
fw2 = S['strategies']['S_T2']['periods']['forward']
g4 = S['gate4']
cor = S['correlations']
pl = S['parlay']
GATE_KEYS = list(S['gates']['S_T2'].keys())
strat_names = {
    'S_T1': ('S1', 'Own-line single, edge ≥ 1.0 point'),
    'S_T2': ('S2', 'Own-line single, edge ≥ 2.0 points (primary)'),
    'S_T3': ('S3', 'Own-line single, edge ≥ 3.0 points'),
    'P2_parlay': ('P2', 'Two-leg parlay, different games, same week, from S2 legs'),
}


def pass_count(key):
    g = S['gates'][key]
    return sum(1 for v in g.values() if v['status'] == 'PASS')


def test_roi(key):
    if key == 'P2_parlay':
        return pl['roi_assumed_price']
    return S['strategies'][key]['periods']['test']['roi_110']


def test_hr(key):
    if key == 'P2_parlay':
        return pl['joint_win_rate']
    return S['strategies'][key]['periods']['test']['hit_rate']


# ---------- page shell ----------
NAV = [('index.html', 'Home'), ('summary.html', 'Executive summary'), ('singles.html', 'Singles'),
       ('parlays.html', 'Parlays'), ('correlations.html', 'Correlations'), ('props.html', 'Player props'),
       ('strategies.html', 'Strategies'), ('validation.html', 'Validation'), ('leaderboard.html', 'Leaderboard'),
       ('games.html', 'Verified games'), ('sources.html', 'Sources'), ('flags.html', 'Flagged for review')]


def page(filename, title, eyebrow, body):
    nav = ''.join('<a href="%s"%s>%s</a>' % (f, ' class="on"' if f == filename else '', escape(t)) for f, t in NAV)
    html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)} · Own9 NFL research</title><link rel="stylesheet" href="style.css"></head>
<body><header><div class="shell top"><a class="brand" href="index.html"><span>O9</span> OWN9 <small>NFL research dashboard</small></a></div>
<nav class="shell subnav" aria-label="Main navigation">{nav}</nav></header>
<main class="shell"><div class="eyebrow">{escape(eyebrow)}</div><h1>{escape(title)}</h1>{body}</main>
<footer class="shell">Research only, not betting advice. Market-dependent figures are unverified. Data snapshot sha256 {SHA[:12]}… · Built 04 Nov 2026 · <a href="flags.html">Flagged for review</a></footer></body></html>'''
    (ROOT / filename).write_text(html, encoding='utf-8')


def notice(text, kind='warn'):
    return f'<div class="notice {kind}">{text}</div>'


def cards(items):
    return '<div class="cards">' + ''.join(
        f'<div class="card"><span>{escape(a)}</span><b>{escape(b)}</b><p>{escape(c)}</p></div>' for a, b, c in items) + '</div>'


STD_NOTICE = notice('<strong>Status: not validated.</strong> No strategy passed every validation gate. Lines used for comparison come from an unverified third-party file. Nothing here is a betting recommendation; in Washington State sports wagering is restricted (see <a href="flags.html">Flagged for review</a>).')

# ================= PAGES =================

# 1. Home / landing dashboard
kpi = cards([
    ('Strategies tested', '4', '3 own-line singles and 1 two-leg parlay'),
    ('Passing all 7 gates', '0', 'Every strategy fails or cannot run at least one gate'),
    ('Primary test hit rate', pct(t2['hit_rate']), f"S2 on {t2['bets']:,} bets, 2016–2025; breakeven at -110 is {pct(BE)}"),
    ('Own-line vs market MAE', f"+{num(g4['mae_difference'])} pts", 'Own line is less accurate than the unverified market line'),
])
home_rows = [
    [f'Own-line accuracy vs market', f"Own line MAE {num(g4['mae_own_line'])} vs market {num(g4['mae_market'])} points over {g4['n_test_games']:,} test games (2016–2025). 95% CI on difference: {num(g4['diff_ci95'][0], 3)} to {num(g4['diff_ci95'][1], 3)}.", tag('Computed from unverified lines'), link(NFL_SCHED)],
    ['Primary single-bet result', f"S2 test: {t2['wins']:,} wins, {t2['losses']:,} losses, {t2['pushes']} pushes. Hit rate {pct(t2['hit_rate'])}, 95% CI {ci(t2['ci95'])}, p = {num(t2['p_value'], 3)}.", tag('Computed from unverified lines'), link(NFL_SCHED)],
    ['Cross-game correlation', f"Same-week game pairs: phi = {num(cor['cross_game_same_week_phi'], 3)} (95% CI {num(cor['cross_game_ci95'][0], 3)} to {num(cor['cross_game_ci95'][1], 3)}), i.e. no measurable dependence.", tag('Computed from unverified lines'), link(NFL_SCHED)],
    ['Two-leg parlay', f"Joint win rate {pct(pl['joint_win_rate'])} vs {pct(pl['product_of_marginals'])} if independent; ROI at assumed price {pct(pl['roi_assumed_price'])}.", tag('Computed from unverified lines'), link(NFL_SCHED)],
    ['Player props', 'No verified prop lines or player-level dataset were retrieved; prop strategies were not run.', tag('Not run'), link(NFL_STATS)],
    ['Legal status (Washington)', 'WSGC states sports wagering is illegal outside authorized tribal casinos. Research output is not a wagering plan.', tag('Flagged'), link(WSGC, 'WSGC FAQ ↗ (manual check)')],
]
body = f'''<p class="lead">A research workspace for originating NFL lines from own models, testing them against a market baseline, and measuring correlations. The honest result so far: the simple own-line model does not beat the market, and no strategy qualifies for a leaderboard reward.</p>
{STD_NOTICE}{kpi}
<h2>Key findings</h2>{table(['Area', 'Finding', 'Status', 'Official reference'], home_rows)}
<h2>Explore</h2><div class="cards nav-cards">
<a class="card" href="summary.html"><span>01</span><b>Executive summary</b><p>Key results, limits, next steps</p></a>
<a class="card" href="singles.html"><span>02</span><b>Singles</b><p>Own-line bets by edge threshold and season</p></a>
<a class="card" href="parlays.html"><span>03</span><b>Parlays</b><p>Two-leg joint outcomes versus independence</p></a>
<a class="card" href="correlations.html"><span>04</span><b>Correlations</b><p>Cross-game and same-game dependence</p></a>
<a class="card" href="props.html"><span>05</span><b>Player props</b><p>Prop single and combo status</p></a>
<a class="card" href="validation.html"><span>06</span><b>Validation gates</b><p>Seven pass/fail gates per strategy</p></a>
<a class="card" href="leaderboard.html"><span>07</span><b>Leaderboard</b><p>Ranking with eligibility</p></a>
<a class="card" href="flags.html"><span>08</span><b>Flagged for review</b><p>Irregularities and unverified items</p></a>
</div>'''
page('index.html', 'NFL own-line research', 'NFL / OVERVIEW', body)

# 2. Executive summary
es_items = [
    f"<strong>What was built.</strong> A reproducible pipeline (tools/analyze.py) that reads a committed snapshot of game results and betting-line columns, builds a walk-forward Elo own line (no future information), and evaluates 3 single-bet thresholds plus one 2-leg parlay.",
    f"<strong>Own line vs market.</strong> Over {g4['n_test_games']:,} games in 2016–2025 the own line has a mean absolute error {num(g4['mae_own_line'])} points versus {num(g4['mae_market'])} for the market column. The gap is {num(g4['mae_difference'])} points (95% CI {num(g4['diff_ci95'][0], 3)} to {num(g4['diff_ci95'][1], 3)}). The simple model is worse than the market baseline.",
    f"<strong>Singles.</strong> Primary strategy S2 (edge ≥ 2 points) won {pct(t2['hit_rate'])} of {t2['bets']:,} test bets (CI {ci(t2['ci95'])}). The breakeven hit rate at -110 is {pct(BE)}. Test ROI at the assumed price is {pct(t2['roi_110'])}. p = {num(t2['p_value'], 3)}, far above the Bonferroni threshold of {num(P['alpha'] / P['family_size'], 4)}.",
    f"<strong>Parlays.</strong> Two-leg parlays from S2 legs won {pct(pl['joint_win_rate'])} of pairs versus {pct(pl['product_of_marginals'])} if the legs were independent (lift {num(pl['lift_vs_independence'], 3)}). The assumed-price ROI is {pct(pl['roi_assumed_price'])}.",
    f"<strong>Correlations.</strong> Same-week cross-game phi = {num(cor['cross_game_same_week_phi'], 3)} (CI includes zero). Same-game home-cover vs over phi = {num(cor['same_game']['home_cover_vs_over']['phi'], 3)} (approx. ±{num(cor['same_game']['home_cover_vs_over']['approx_ci95'], 3)}), so the measurable dependence is very small. Correlation is measured, not priced.",
    f"<strong>Forward check (2026).</strong> S2 went {fw2['wins']}-{fw2['losses']} ({pct(fw2['hit_rate'])}, n = {fw2['bets']}, p = {num(fw2['p_value'], 3)}). Too few games to conclude anything; it was not used for any decision.",
    '<strong>Luck.</strong> Randomness cannot be removed from single-game outcomes. The pipeline uses out-of-sample tests, a family-wise correction and season-level stability to avoid mistaking noise for skill. Under these tests, no skill is detected.',
    '<strong>Player props.</strong> Not run. No official prop prices were verified and no player-level dataset was retrieved in this session.',
    '<strong>Legal.</strong> The Washington State Gambling Commission describes sports wagering as illegal outside authorized tribal casinos. Any use of these results for real-money wagering or any reward program needs legal review first.',
]
body = f'''{STD_NOTICE}
<h2>Summary</h2><ol class="findings">{''.join(f'<li>{x}</li>' for x in es_items)}</ol>
<h2>Headline numbers</h2>{table(['Measure', 'Value', 'Status', 'Official reference'], [
    ['Games in own-line evaluation, 2016–2025 (REG)', f"{g4['n_test_games']:,}", tag('Computed from unverified lines'), link(NFL_SCHED)],
    ['Own-line MAE (points)', num(g4['mae_own_line']), tag('Computed from unverified lines'), link(NFL_SCHED)],
    ['Market-line MAE (points)', num(g4['mae_market']), tag('Unverified'), link(NFL_SCHED)],
    ['Primary S2 test hit rate', pct(t2['hit_rate']), tag('Computed from unverified lines'), link(NFL_SCHED)],
    ['Breakeven at -110 (assumed price)', pct(BE), tag('Unverified'), link(NFL_SCHED)],
    ['Strategies passing all 7 gates', '0 of 4', tag('Not validated'), link(NIST)],
])}
<h2>Method in brief</h2>
<ul><li>Own line: walk-forward Elo, K = 20, home field 65 Elo, 25 Elo per point, one-third reversion to 1500 each season. Parameters fixed before the test period was viewed.</li>
<li>Periods: tuning 2006–2015, sealed test 2016–2025, forward check 2026. Thresholds 1, 2, 3 points.</li>
<li>Pricing assumption: -110 on each side (not a verified sportsbook price). Breakeven {pct(BE)}.</li>
<li>Source snapshot: nflverse nfldata games.csv, sha256 <code>{escape(SHA)}</code> (third-party; see <a href="sources.html">Sources</a>).</li></ul>
<h2>Limits</h2><ul><li>Betting lines have no documented origin, so market comparisons are unverified.</li><li>Only 5 game scores were checked against official NFL pages.</li><li>No executable, timestamped prices or limits were available, so economics cannot be validated.</li></ul>
<p>Full detail: <a href="validation.html">validation gates</a>, <a href="leaderboard.html">leaderboard</a>, <a href="flags.html">flagged items</a>.</p>'''
page('summary.html', 'Executive summary', 'NFL / EXECUTIVE SUMMARY', body)

# 3. Singles
rows = []
for key in ['S_T1', 'S_T2', 'S_T3']:
    code, desc = strat_names[key]
    for per, label in [('train', 'Tuning 2006–2015'), ('test', 'Test 2016–2025'), ('forward', 'Forward 2026')]:
        d = S['strategies'][key]['periods'][per]
        rows.append([f'{code} · {label}', desc, f"{d['bets']:,}", f"{d['wins']:,}", f"{d['losses']:,}", str(d['pushes']),
                     pct(d['hit_rate']), ci(d['ci95']), num(d['p_value'], 3), pct(d['roi_110']), tag('Computed from unverified lines'), link(NFL_SCHED)])
body = f'''{STD_NOTICE}
<p class="lead">A single bet is taken when the own line differs from the market line by at least the threshold, on the side the own line favours. Pushes are excluded from hit rate. ROI uses an assumed -110 price.</p>
{table(['Strategy · period', 'Rule', 'Bets', 'Wins', 'Losses', 'Pushes', 'Hit rate', '95% CI', 'p-value', 'ROI (assumed -110)', 'Verification', 'Official reference'], rows)}
<h2>S2 by test season (primary strategy)</h2>
{table(['Season', 'Bets', 'Wins', 'Losses', 'Hit rate', '95% CI', 'Above breakeven?', 'Verification', 'Official reference'], [
    [s, f"{v['bets']:,}", str(v['wins']), str(v['losses']), pct(v['hit_rate']), ci(v['ci95']), 'Yes' if v['hit_rate'] and v['hit_rate'] > BE else 'No', tag('Computed from unverified lines'), link(NFL_SCHED)]
    for s, v in S['strategies']['S_T2']['seasons_test'].items()])}
<p>Seasons above breakeven: {sum(1 for v in S['strategies']['S_T2']['seasons_test'].values() if v['hit_rate'] and v['hit_rate'] > BE)} of 10. Gate G7 requires at least 7 of 10.</p>
<p>Row-level bet data for every test and forward bet: <a href="data/results/bets_test_and_forward.csv">bets_test_and_forward.csv</a> (third-party line data, not individually verified against official sources).</p>'''
page('singles.html', 'Single-bet strategies', 'NFL / SINGLES', body)

# 4. Parlays
body = f'''{STD_NOTICE}
<p class="lead">Two-leg parlays formed from S2 legs in the same week, from different games. A parlay wins only if both legs win. Joint outcomes are compared with the product of individual rates, the independence assumption.</p>
{table(['Measure', 'Value', 'Meaning', 'Verification', 'Official reference'], [
    ['Leg pairs evaluated', f"{pl['n_pairs']:,}", 'Pairs of S2 bets in one week from different games, 2016–2025, pushes excluded. Overlapping pairs, not independent observations.', tag('Computed from unverified lines'), link(NFL_SCHED)],
    ['Joint win rate', pct(pl['joint_win_rate']), 'Share of pairs in which both legs won.', tag('Computed from unverified lines'), link(NFL_SCHED)],
    ['Product of single-leg rates', pct(pl['product_of_marginals']), 'Expected joint rate if legs were independent.', tag('Computed from unverified lines'), link(NFL_SCHED)],
    ['Lift vs independence', num(pl['lift_vs_independence'], 3), 'Below 1 means legs won together slightly less often than independence predicts. No significance test was run on this lift.', tag('Computed from unverified lines'), link(NFL_SCHED)],
    ['Assumed decimal price', num(pl['decimal_price_assumed'], 4), 'Two legs at -110 multiplied. Real parlay prices are unknown and usually differ.', tag('Unverified'), link(NFL_SCHED)],
    ['Breakeven joint win rate', pct(pl['breakeven_joint']), 'Joint rate needed to break even at the assumed price.', tag('Unverified'), link(NFL_SCHED)],
    ['ROI at assumed price', pct(pl['roi_assumed_price']), f"Week-cluster bootstrap 95% CI {pct(pl['roi_ci95_week_bootstrap'][0])} to {pct(pl['roi_ci95_week_bootstrap'][1])}.", tag('Computed from unverified lines'), link(NFL_SCHED)],
])}
<h2>Gate result</h2><p>P2 fully passes only G3 (evaluation split). It fails G1 (unverified lines) and G6 (leg correlation not priced and family not corrected), and cannot be assessed on G4 or G5 (no joint market baseline or parlay prices). See <a href="validation.html">Validation</a>.</p>'''
page('parlays.html', 'Two-leg parlays', 'NFL / PARLAYS', body)

# 5. Correlations
cs = cor['same_game']
body = f'''{STD_NOTICE}
<p class="lead">Phi coefficient for binary outcomes (ranges from -1 to 1; 0 means no linear association). Confidence intervals show whether a value differs from zero.</p>
{table(['Pair of outcomes', 'Sample', 'Phi / r', '95% interval', 'Interpretation', 'Verification', 'Official reference'], [
    ['Home cover in one game vs home cover in another game, same week', f"{cor['cross_game_pairs']:,} pairs", num(cor['cross_game_same_week_phi'], 4), f"{num(cor['cross_game_ci95'][0], 3)} to {num(cor['cross_game_ci95'][1], 3)} (week bootstrap)", 'Zero is inside the interval: no measurable cross-game dependence.', tag('Computed from unverified lines'), link(NFL_SCHED)],
    ['Home cover vs game total over, same game', f"{cs['home_cover_vs_over']['n']:,} games", num(cs['home_cover_vs_over']['phi'], 4), f"±{num(cs['home_cover_vs_over']['approx_ci95'], 3)} (approx.)", 'Small and within sampling error.', tag('Computed from unverified lines'), link(NFL_SCHED)],
    ['Home win vs game total over, same game', f"{cs['home_win_vs_over']['n']:,} games", num(cs['home_win_vs_over']['phi'], 4), f"±{num(cs['home_win_vs_over']['approx_ci95'], 3)} (approx.)", 'Small and within sampling error.', tag('Computed from unverified lines'), link(NFL_SCHED)],
    ['Final margin vs final total (scores only)', f"{cor['score_only_n']:,} games", num(cor['score_only_margin_vs_total_r'], 4), 'not computed', 'Uses scores only, not lines. Small association.', tag('Verified (sample)'), link(NFL_SCHED)],
])}
<h2>What this means for combos</h2>
<ul><li>Pairwise dependence in this data is near zero, so independence is a reasonable baseline for cross-game parlays. The test is weak and was run on unverified lines.</li>
<li>Same-game combos (e.g. spread plus total) need a priced joint market. Only a tiny measured association exists, so none was priced.</li>
<li>Correlation alone does not price a combo. Any joint price must be validated out of sample against the actual offered price.</li></ul>'''
page('correlations.html', 'Correlations', 'NFL / CORRELATIONS', body)

# 6. Player props
body = f'''{notice('<strong>Not run.</strong> Player prop strategies were not evaluated. No verified prop prices or player-level dataset were obtained in this session. The NFL stats pages are reachable but were not used as a bulk source.', 'warn')}
<p class="lead">Prop single and prop combo strategies are part of the research scope but have no evidence yet.</p>
{table(['Strategy', 'Required evidence', 'Status', 'Official reference'], [
    ['PP1 · Player prop single', 'Official player game statistics by week, availability/injury status with timestamps, and timestamped prop prices.', tag('Not run'), link(NFL_STATS)],
    ['PP2 · Player prop + game combo', 'Paired player-game and game outcomes, void/push rules, and actual combo prices.', tag('Not run'), link(NFL_STATS)],
    ['PP3 · Same-game correlation (props)', 'Measured correlation between player stat outcomes and game outcomes, with confidence intervals.', tag('Not run'), link(NFL_STATS)],
])}
<p>Next step: obtain an official or documented, timestamped source for player statistics and availability. Until then, nothing in this table is a finding.</p>'''
page('props.html', 'Player props', 'NFL / PLAYER PROPS', body)

# 7. Strategy catalog
rows = []
catalog = [
    ('S1', 'Own-line single, edge ≥ 1 point', 'Single · game', 'S_T1'),
    ('S2', 'Own-line single, edge ≥ 2 points (primary)', 'Single · game', 'S_T2'),
    ('S3', 'Own-line single, edge ≥ 3 points', 'Single · game', 'S_T3'),
    ('P2', 'Two-leg parlay, cross-game, from S2 legs', 'Parlay', 'P2_parlay'),
    ('C1', 'Same-game combo (spread + total)', 'Combo · same game', None),
    ('PP1', 'Player prop single', 'Single · player prop', None),
    ('PP2', 'Player prop + game combo', 'Combo · props', None),
]
for code, name, typ, key in catalog:
    if key:
        status = 'Not validated'
        rows.append([code, name, typ, pct(test_hr(key)), pct(test_roi(key)), f'{pass_count(key)} of 7', tag(status), link(NFL_SCHED)])
    else:
        rows.append([code, name, typ, '—', '—', '—', tag('Not run'), link(NFL_STATS if code.startswith('PP') else NFL_SCHED)])
body = f'''{STD_NOTICE}
<p class="lead">Candidate designs and their results. Blank cells are not run, not zero. Hit rate and ROI are on the 2016–2025 test period, with ROI at the assumed -110 price.</p>
{table(['ID', 'Strategy', 'Type', 'Test win rate', 'Test ROI (assumed)', 'Gates passed', 'Status', 'Official reference'], rows)}
<h2>Pricing discipline</h2><p>For a no-push single with decimal odds D and model win probability p, expected net return per unit is p × D − 1. At -110 (D ≈ 1.909) breakeven is p ≈ {pct(BE)}. Any real price needs to be timestamped, executable and checked against that rule.</p>'''
page('strategies.html', 'Strategy catalog', 'NFL / STRATEGIES', body)

# 8. Validation gates
gdesc = {
    'G1 Provenance': ('Retain official outcomes, source links, timestamps and identifiers; reconcile revisions.', NFL_GAMES),
    'G2 Point in time': ('Every feature and price available before the forecast; code and predictions frozen before outcomes.', NFL_SCHED),
    'G3 Evaluation split': ('Train on earlier periods only; tune on a later period; seal a final test.', NIST),
    'G4 Predictive quality vs market': ('Compare with a market baseline on error and calibration, with uncertainty.', NIST),
    'G5 Economics': ('Executable timestamped prices, push/void rules and costs; report net return and drawdown.', NFL_SCHED),
    'G6 Selection control': ('Correct for multiple comparisons across the registered family; cluster by week or game.', NIST),
    'G7 Stability': ('Consistency across seasons and sensitivity checks; fail closed on sparse data.', NIST),
}
rows = []
for g in GATE_KEYS:
    rule, src = gdesc[g]
    cells = [g, rule]
    for key in ['S_T1', 'S_T2', 'S_T3', 'P2_parlay']:
        st = S['gates'][key][g]['status']
        cells.append(tag(st))
    cells.append(link(src))
    rows.append(cells)
body = f'''{STD_NOTICE}
<p class="lead">Seven gates, applied to each strategy. A strategy is eligible only if every gate is PASS. PARTIAL and NOT RUN both block eligibility.</p>
{table(['Gate', 'Predeclared requirement', 'S1', 'S2', 'S3', 'P2', 'Official reference'], rows)}
<h2>Gate detail</h2>
{table(['Strategy', 'Gate', 'Result', 'Detail', 'Official reference'], [
    [strat_names.get(k, ('P2', ''))[0] if k != 'P2_parlay' else 'P2', g, tag(S['gates'][k][g]['status']), escape(S['gates'][k][g]['note']), link(gdesc[g][1])]
    for k in ['S_T2', 'P2_parlay'] for g in GATE_KEYS])}
<h2>Parameters (predeclared)</h2>
<ul><li>Elo: K = {P['K']}, home field {P['home_field_elo']} Elo, {P['elo_per_point']} Elo per point, season reversion {round(P['season_reversion'], 3)}.</li>
<li>Periods: tuning {P['train'][0]}–{P['train'][1]}, test {P['test'][0]}–{P['test'][1]}, forward {P['forward']}.</li>
<li>Family size for correction: {P['family_size']}; alpha {P['alpha']}; Bonferroni threshold {num(P['alpha'] / P['family_size'], 4)}.</li></ul>'''
page('validation.html', 'Validation gates', 'NFL / VALIDATION', body)

# 9. Leaderboard
order = sorted(['S_T1', 'S_T2', 'S_T3', 'P2_parlay'], key=lambda k: test_roi(k), reverse=True)
rows = []
for i, k in enumerate(order, 1):
    code = strat_names[k][0]
    rows.append([str(i), code, strat_names[k][1], f"{(S['strategies'][k]['periods']['test']['bets'] if k != 'P2_parlay' else pl['n_pairs']):,}",
                 pct(test_hr(k)), pct(test_roi(k)), f'{pass_count(k)} of 7', tag('Not eligible'), link(NFL_SCHED)])
body = f'''{notice('<strong>No eligible strategy.</strong> Ranking is by test ROI at the assumed price, shown for transparency only. Strategies must pass all 7 gates before ranking for any reward. No reward program, sponsor or prize has been verified.', 'bad')}
<p class="lead">A competition framework: rank eligible strategies by out-of-sample improvement against the market baseline, with uncertainty, sample size and drawdown reported.</p>
{table(['Rank (by test ROI)', 'ID', 'Strategy', 'Test sample', 'Test win rate', 'Test ROI (assumed)', 'Gates passed', 'Eligibility', 'Official reference'], rows)}
<p>Reward status: none. Blank values are unverified. Rewards are hypothetical until rules, a sponsor and legal review exist.</p>'''
page('leaderboard.html', 'Leaderboard', 'NFL / LEADERBOARD', body)

# 10. Verified games
rows = []
for v in VERIFIED:
    rows.append([v['matchup'], v['date'], f"{v['nfl_away_score']}–{v['nfl_home_score']}", f"{v['data_away_score']}–{v['data_home_score']}",
                 tag('Verified (sample)') if v['match'] == 'yes' else tag('Flagged'), link(v['official_url'], 'NFL game center ↗')])
body = f'''<p class="lead">Five games checked line by line against official NFL game-center pages. Each score matched the snapshot. Lines are not shown because no official line source exists.</p>
{table(['Game (away at home)', 'Date (NFL.com)', 'Final score (NFL.com)', 'Final score (snapshot)', 'Match', 'Official source'], rows)}
<p>Sample verification covers {len(VERIFIED)} of {S['generated_from']['rows_with_scores']:,} scored games in the snapshot. The remaining games are unverified third-party rows and are not presented as verified facts.</p>'''
page('games.html', 'Verified games', 'NFL / VERIFIED GAMES', body)

# 11. Sources
body = f'''<p class="lead">Source register. Official sources are NFL.com, the Washington State Gambling Commission and NIST. Third-party data is labelled.</p>
{table(['Source', 'Type', 'What it supports', 'Retrieved / check', 'Official reference'], [
    ['NFL game centers (nfl.com/games)', 'Official', 'Five final scores in the verified sample', '04 Nov 2026 via fetch', link(NFL_GAMES)],
    ['NFL schedules (nfl.com/schedules)', 'Official', 'Season schedule context; 2026 Week 9 game list observed', '04 Nov 2026 via fetch', link(NFL_SCHED)],
    ['NFL player stats (nfl.com/stats/player-stats)', 'Official', 'Player-level stat pages (not used as a bulk source)', '04 Nov 2026 via fetch', link(NFL_STATS)],
    ['Washington State Gambling Commission FAQ', 'Official (regulator)', 'Legal status of sports wagering in Washington', 'Indexed excerpt only; direct fetch returned Access denied', link(WSGC, 'WSGC FAQ ↗')],
    ['NIST Handbook 1.4.2.8.3 (randomness and autocorrelation)', 'Official (government)', 'Randomness and autocorrelation testing reference', '04 Nov 2026 via fetch', link(NIST)],
    ['nflverse nfldata games.csv (snapshot in data/source/games.csv)', 'Third party (open data)', 'Scores, game metadata and betting-line columns; sha256 {escape(SHA)}', 'Downloaded 04 Nov 2026 from codeload.github.com', link(NFL_SCHED, 'Official season context ↗')],
    ['nflverse nfldata DATASETS.md', 'Third party documentation', 'Column definitions; line origin not documented', 'Read 04 Nov 2026', link(NFL_SCHED, 'Official season context ↗')],
])}
<h2>Downloads</h2><ul>
<li><a href="data/source/games.csv">games.csv (snapshot)</a></li>
<li><a href="data/results/summary.json">summary.json (all computed results)</a></li>
<li><a href="data/results/bets_test_and_forward.csv">bets_test_and_forward.csv</a></li>
<li><a href="data/results/games_test_2016_2026.csv">games_test_2016_2026.csv</a></li></ul>
<p>Reproduce: <code>python3 tools/analyze.py &amp;&amp; python3 tools/build.py &amp;&amp; python3 tools/check.py</code></p>
<p>Third-party references: <a href="{THIRD_NFLVERSE}">nflverse/nfldata</a>, <a href="{THIRD_DATASETS}">DATASETS.md</a>, <a href="{THIRD_GAMES}">games.csv</a>.</p>'''
page('sources.html', 'Sources', 'NFL / SOURCES', body)

# 12. Flags
flags = [
    ('F1', 'Betting-line origin undocumented', 'spread_line and total_line have no documented source in the snapshot; DATASETS.md describes columns but not provenance. All market-dependent results are unverified.', NFL_SCHED, 'Unverified'),
    ('F2', 'Documentation date range mismatch', 'Third-party DATASETS.md (nflverse/nfldata) says games data begins with the 2006 season; the file contains games from 1999 onward.', NFL_SCHED, 'Flagged'),
    ('F3', 'Scores mostly unverified', f"Only {len(VERIFIED)} of {S['generated_from']['rows_with_scores']:,} scored games were checked against nfl.com. The rest are third-party values.", NFL_GAMES, 'Unverified'),
    ('F4', 'Washington State sports wagering restriction', 'WSGC states sports wagering is illegal outside authorized tribal casinos and describes gambling as prize, chance and consideration. The page returned Access denied to the fetch tool, so this rests on an indexed excerpt and needs manual confirmation. Legal review is needed before any real-money use or reward program.', WSGC, 'Flagged'),
    ('F5', 'Price and parlay assumptions', 'ROI uses -110 on each side. Parlay pricing assumes the product of legs at that price. Actual prices, limits and vig are unknown.', NFL_SCHED, 'Unverified'),
    ('F6', 'Player props not evaluated', 'No prop lines or player-level dataset were verified. Prop strategies are not run.', NFL_STATS, 'Not run'),
    ('F7', 'Forward check is tiny', f"2026 forward sample: {fw2['bets']} bets. Result {pct(fw2['hit_rate'])} with p = {num(fw2['p_value'], 3)}. Not evidence of skill.", NFL_SCHED, 'Flagged'),
    ('F8', 'Season URL redirects', 'https://www.nfl.com/schedules/2025 redirected to the current 2026 schedule page when fetched. Season-specific links were not used.', NFL_SCHED, 'Flagged'),
    ('F9', 'Upstream data license not verified', 'The nflverse nfldata repository was downloaded without a confirmed license for redistribution. Verify before publishing data beyond this site. Third-party source: nflverse/nfldata.', NFL_SCHED, 'Unverified'),
    ('F11', 'Carried forward: source scope', 'Contextual references (NIST, nfl.com, WSGC) support methods and context. They do not show that any strategy, reward or proposal works. Earlier review wording (source scope) still applies.', NFL_SCHED, 'Needs review'),
    ('F12', 'Carried forward: NFL page scope', 'The nfl.com stats page is dynamic. No point-in-time stats snapshot is kept here. This site stores only the 5 verified game pages and the third-party games file.', NFL_STATS, 'Needs review'),
    ('F13', 'Carried forward: tail risk', 'Skew and heavy tails can distort averages. Margin and bet-return distributions were summarised by hit rate and ROI only; no distribution-level review was done.', NFL_SCHED, 'Needs review'),
    ('F14', 'Carried forward: luck', 'Randomness cannot be removed from single-game outcomes. Confidence intervals quantify uncertainty under assumptions; they do not remove luck.', NIST, 'Limitation'),
    ('F15', 'Independent release-quality report', 'A separate read-only HTML/link/accessibility report on the shared pages, from another session, is published at release-checks/index.html. It checks structure and source presence only. It does not verify factual claims. Open the report: <a href="release-checks/index.html">release-checks/index.html</a>.', 'https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages', 'Needs review'),
    ('F10', 'Own-line model underperforms market', f"MAE gap {num(g4['mae_difference'])} points (CI {num(g4['diff_ci95'][0], 3)} to {num(g4['diff_ci95'][1], 3)}). This is a finding, not a bug, but it blocks every strategy that relies on the model.", NFL_SCHED, 'Flagged'),
]
body = f'''{notice('<strong>Flagged for Review.</strong> These items do not block publication. Each row shows what needs checking and where. Please review and request changes.', 'warn')}
{table(['ID', 'Item', 'Irregularity or gap', 'Status', 'Official reference'], [
    [f, t, d, tag(s), link(u)] for f, t, d, u, s in flags])}
<h2>Coordination</h2><p>This session is the only one working on the NFL research task on this branch. Open PR #2 from another session is noted in COORDINATION.md and was not merged or changed by this session.</p>'''
page('flags.html', 'Flagged for review', 'NFL / FLAGGED FOR REVIEW', body)

print('built', len(NAV), 'pages')
