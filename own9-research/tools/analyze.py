"""Reproducible NFL own-line research pipeline (pure Python 3 standard library).

Inputs : data/source/games.csv  (nflverse/nfldata snapshot, see data/source/SOURCE.md)
Outputs: data/results/*.json and *.csv consumed by tools/build.py

Design (all parameters predeclared here, before any test-period result was viewed):
  * Own line = Elo rating model, walk-forward (ratings use only games completed before kickoff).
    K=20, home-field 65 Elo, 25 Elo per point of margin, 1/3 mean reversion between seasons.
  * Market baseline = spread_line / total_line columns of the source file. These columns have NO
    documented origin in the repository, so every market-dependent figure is labelled UNVERIFIED.
  * Tuning period 2006-2015; sealed test period 2016-2025; forward check 2026 (games with scores).
  * Single-bet pricing assumes -110 both sides (an assumption, not a verified sportsbook price).
  * Edge thresholds T in {1,2,3} points; T=2 is the primary single strategy.
"""
import csv, json, math, random, hashlib
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'data/source/games.csv'
OUT = ROOT / 'data/results'
OUT.mkdir(parents=True, exist_ok=True)

K, HFA, SCALE, REVERT = 20.0, 65.0, 25.0, 2 / 3
TRAIN = (2006, 2015)
TEST = (2016, 2025)
FORWARD = 2026
THRESHOLDS = [1.0, 2.0, 3.0]
PRIMARY_T = 2.0
DEC_110 = 1 + 100 / 110          # decimal price for -110
BREAKEVEN = 1 / DEC_110          # 0.5238
N_FAMILY = 4                     # S1, S2, S3, P2 registered in the test family
ALPHA = 0.05
random.seed(20261104)


def sha256(p):
    h = hashlib.sha256()
    h.update(Path(p).read_bytes())
    return h.hexdigest()


def num(x):
    return None if x in ('', None) else float(x)


def norm_cdf(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def binom_two_sided(k, n):
    """Exact two-sided binomial p-value vs p=0.5."""
    if n == 0:
        return 1.0
    pmf = [math.comb(n, i) / 2 ** n for i in range(n + 1)]
    p_obs = pmf[k]
    return min(1.0, sum(p for p in pmf if p <= p_obs * (1 + 1e-12)))


def wilson(k, n, z=1.96):
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(c - h, 4), round(c + h, 4))


def phi(a, b):
    """Phi coefficient from paired binary outcomes."""
    n11 = sum(1 for x, y in zip(a, b) if x and y)
    n10 = sum(1 for x, y in zip(a, b) if x and not y)
    n01 = sum(1 for x, y in zip(a, b) if not x and y)
    n00 = sum(1 for x, y in zip(a, b) if not x and not y)
    den = math.sqrt((n11 + n10) * (n01 + n00) * (n11 + n01) * (n10 + n00))
    return 0.0 if den == 0 else (n11 * n00 - n10 * n01) / den


# ---------- 1. load and sort ----------
raw = list(csv.DictReader(open(SRC, encoding='utf-8')))
games = [r for r in raw if r['home_score'] != '' and r['away_score'] != '']
games.sort(key=lambda r: (int(r['season']), r['gameday'], r['game_id']))

# ---------- 2. walk-forward Elo: pre-game own margin ----------
ratings = defaultdict(lambda: 1500.0)
last_season = None
rows = []
for r in games:
    s = int(r['season'])
    if last_season is not None and s != last_season:
        for t in list(ratings):
            ratings[t] = 1500 + (ratings[t] - 1500) * REVERT
    last_season = s
    h, a = r['home_team'], r['away_team']
    hfa = 0.0 if r['location'] == 'Neutral' else HFA
    rh, ra = ratings[h], ratings[a]
    own_margin = (rh - ra + hfa) / SCALE            # pre-game own line (home-positive)
    hs, as_ = int(r['home_score']), int(r['away_score'])
    res = hs - as_
    tot = hs + as_
    rows.append(dict(game_id=r['game_id'], season=s, week=int(r['week']), game_type=r['game_type'],
                     gameday=r['gameday'], away=a, home=h, away_score=as_, home_score=hs,
                     result=res, total=tot, own_line=round(own_margin, 2),
                     market_line=num(r['spread_line']), total_line=num(r['total_line'])))
    e = 1 / (1 + 10 ** (-(rh - ra + hfa) / 400))
    sc = 1.0 if res > 0 else (0.0 if res < 0 else 0.5)
    ratings[h] = rh + K * (sc - e)
    ratings[a] = ra - K * (sc - e)

# ---------- 3. sanity checks on sign conventions ----------
reg_lines = [x for x in rows if x['game_type'] == 'REG' and x['market_line'] is not None]
n = len(reg_lines)
mx = sum(x['market_line'] for x in reg_lines) / n
my = sum(x['result'] for x in reg_lines) / n
cov = sum((x['market_line'] - mx) * (x['result'] - my) for x in reg_lines) / n
sx = math.sqrt(sum((x['market_line'] - mx) ** 2 for x in reg_lines) / n)
sy = math.sqrt(sum((x['result'] - my) ** 2 for x in reg_lines) / n)
sign_corr = cov / (sx * sy)
checks = dict(sign_check_corr_line_vs_result=round(sign_corr, 4),
              sign_convention_ok=sign_corr > 0)  # documented: positive spread_line = home favoured, result = home - away

# ---------- 4. evaluation rows ----------
ev = [x for x in rows if x['game_type'] == 'REG' and x['market_line'] is not None
      and TRAIN[0] <= x['season'] <= FORWARD]
for x in ev:
    x['edge'] = round(x['own_line'] - x['market_line'], 2)
    x['cover_margin'] = x['result'] - x['market_line']   # >0 home covers


def bet_record(x, T):
    if abs(x['edge']) < T - 1e-9:
        return None
    side = 'HOME' if x['edge'] > 0 else 'AWAY'
    cm = x['cover_margin'] if side == 'HOME' else -x['cover_margin']
    outcome = 'PUSH' if cm == 0 else ('WIN' if cm > 0 else 'LOSS')
    return side, outcome


def stats(bets):
    w = sum(1 for b in bets if b[1] == 'WIN')
    l = sum(1 for b in bets if b[1] == 'LOSS')
    p = sum(1 for b in bets if b[1] == 'PUSH')
    d = w + l
    hr = w / d if d else None
    roi = ((w * (DEC_110 - 1)) - l) / d if d else None
    return dict(bets=len(bets), wins=w, losses=l, pushes=p,
                hit_rate=round(hr, 4) if hr is not None else None,
                ci95=wilson(w, d), p_value=round(binom_two_sided(w, d), 4) if d else None,
                roi_110=round(roi, 4) if roi is not None else None)


def in_period(x, per):
    return per[0] <= x['season'] <= per[1]


strategies = {}
bet_rows = []
for T in THRESHOLDS:
    key = f'S_T{T:g}'
    per_period = {}
    seasonal = {}
    for name, per in [('train', TRAIN), ('test', TEST), ('forward', (FORWARD, FORWARD))]:
        recs = []
        for x in ev:
            if not in_period(x, per):
                continue
            b = bet_record(x, T)
            if b:
                recs.append(b)
                if name == 'test' or name == 'forward':
                    bet_rows.append(dict(strategy=key, game_id=x['game_id'], season=x['season'], week=x['week'],
                                         away=x['away'], home=x['home'], own_line=x['own_line'],
                                         market_line=x['market_line'], edge=x['edge'], side=b[0], outcome=b[1]))
        per_period[name] = stats(recs)
    for s in range(TEST[0], TEST[1] + 1):
        seasonal[s] = stats([bet_record(x, T) for x in ev if x['season'] == s and bet_record(x, T)])
    strategies[key] = dict(threshold=T, periods=per_period,
                           seasons_test={str(k): v for k, v in seasonal.items()})

# ---------- 5. model vs market accuracy (gate 4) ----------
def mae(vals):
    return sum(abs(v) for v in vals) / len(vals)

test_ev = [x for x in ev if in_period(x, TEST)]
train_ev = [x for x in ev if in_period(x, TRAIN)]
mae_model = mae([x['result'] - x['own_line'] for x in test_ev])
mae_market = mae([x['result'] - x['market_line'] for x in test_ev])
# season-cluster bootstrap for the MAE difference
by_season = defaultdict(list)
for x in test_ev:
    by_season[x['season']].append(x)
seasons = sorted(by_season)
boot = []
for _ in range(2000):
    samp = [random.choice(seasons) for _ in seasons]
    diffs = []
    for s in samp:
        for x in by_season[s]:
            diffs.append(abs(x['result'] - x['own_line']) - abs(x['result'] - x['market_line']))
    boot.append(sum(diffs) / len(diffs))
boot.sort()
gate4 = dict(n_test_games=len(test_ev), mae_own_line=round(mae_model, 3), mae_market=round(mae_market, 3),
             mae_difference=round(mae_model - mae_market, 3),
             diff_ci95=[round(boot[50], 3), round(boot[1949], 3)])

# ---------- 6. correlations ----------
def pair_phi_within_week(group_key, values):
    """pooled phi over all same-week pairs of different games"""
    groups = defaultdict(list)
    for x in test_ev:
        groups[group_key(x)].append(x)
    pairs_a, pairs_b = [], []
    week_pairs = {}
    for g, xs in groups.items():
        pp_a, pp_b = [], []
        for i in range(len(xs)):
            for j in range(i + 1, len(xs)):
                va, vb = values(xs[i]), values(xs[j])
                if va is None or vb is None:
                    continue
                pp_a.append(va); pp_b.append(vb)
        if pp_a:
            week_pairs[g] = (pp_a, pp_b)
            pairs_a += pp_a; pairs_b += pp_b
    p = phi(pairs_a, pairs_b)
    keys = list(week_pairs)
    bs = []
    for _ in range(1000):
        aa, bb = [], []
        for k in [random.choice(keys) for _ in keys]:
            aa += week_pairs[k][0]; bb += week_pairs[k][1]
        bs.append(phi(aa, bb))
    bs.sort()
    return round(p, 4), [round(bs[25], 4), round(bs[974], 4)], len(pairs_a)


def cover_val(x):
    cm = x['cover_margin']
    return None if cm == 0 else cm > 0


cross_phi, cross_ci, cross_n = pair_phi_within_week(lambda x: (x['season'], x['week']), cover_val)

def over_val(x):
    if x['total_line'] is None or x['total'] == x['total_line']:
        return None
    return x['total'] > x['total_line']

same_phi = {}
v = [(cover_val(x), over_val(x)) for x in test_ev]
v = [(a, b) for a, b in v if a is not None and b is not None]
same_phi['home_cover_vs_over'] = dict(phi=round(phi([a for a, _ in v], [b for _, b in v]), 4), n=len(v), approx_ci95=round(1.96 / math.sqrt(len(v)), 4))
pw = [(x['result'] > 0, x['total'] > (x['total_line'] or 0)) for x in test_ev if x['total_line'] is not None and x['result'] != 0]
same_phi['home_win_vs_over'] = dict(phi=round(phi([a for a, _ in pw], [b for _, b in pw]), 4), n=len(pw), approx_ci95=round(1.96 / math.sqrt(len(pw)), 4))

# score-only correlation (no lines needed): home margin vs total, test period
sc = [x for x in rows if x['game_type'] == 'REG' and in_period(x, TEST)]
mxr = sum(x['result'] for x in sc) / len(sc); mxt = sum(x['total'] for x in sc) / len(sc)
cv = sum((x['result'] - mxr) * (x['total'] - mxt) for x in sc) / len(sc)
sr = math.sqrt(sum((x['result'] - mxr) ** 2 for x in sc) / len(sc))
st = math.sqrt(sum((x['total'] - mxt) ** 2 for x in sc) / len(sc))
score_corr = round(cv / (sr * st), 4)

corr = dict(cross_game_same_week_phi=cross_phi, cross_game_ci95=cross_ci, cross_game_pairs=cross_n,
            same_game=same_phi, score_only_margin_vs_total_r=score_corr, score_only_n=len(sc))

# ---------- 7. parlays: 2-leg, different games, same week, from S_T2 bets ----------
primary = [b for b in bet_rows if b['strategy'] == 'S_T2' and b['outcome'] != 'PUSH' and TEST[0] <= b['season'] <= TEST[1]]
byweek = defaultdict(list)
for b in primary:
    byweek[(b['season'], b['week'])].append(b)
pairs = []
week_list = []
for k, bs in byweek.items():
    wk = []
    for i in range(len(bs)):
        for j in range(i + 1, len(bs)):
            if bs[i]['game_id'] == bs[j]['game_id']:
                continue
            both = bs[i]['outcome'] == 'WIN' and bs[j]['outcome'] == 'WIN'
            wk.append(1.0 if both else 0.0)
    if wk:
        week_list.append((k, wk))
        pairs += wk
p_pair = sum(pairs) / len(pairs) if pairs else None
marg = [1.0 if b['outcome'] == 'WIN' else 0.0 for b in primary]
p_marg = sum(marg) / len(marg) if marg else None
lift = p_pair / (p_marg ** 2) if pairs else None
parlay_odds = DEC_110 ** 2
parlay_roi = (p_pair * parlay_odds - 1) if p_pair is not None else None
bs_roi = []
for _ in range(1000):
    samp = [random.choice(week_list) for _ in week_list]
    vals = [v for _, wk in samp for v in wk]
    if vals:
        bs_roi.append(sum(vals) / len(vals) * parlay_odds - 1)
bs_roi.sort()
parlay = dict(legs=2, primary_strategy='S_T2', n_pairs=len(pairs), joint_win_rate=round(p_pair, 4) if p_pair is not None else None,
              product_of_marginals=round(p_marg ** 2, 4) if p_marg is not None else None,
              lift_vs_independence=round(lift, 4) if lift is not None else None,
              breakeven_joint=round(1 / parlay_odds, 4), decimal_price_assumed=round(parlay_odds, 4),
              roi_assumed_price=round(parlay_roi, 4) if parlay_roi is not None else None,
              roi_ci95_week_bootstrap=[round(bs_roi[25], 4), round(bs_roi[974], 4)] if bs_roi else None)

# ---------- 8. forward check (2026, games with scores) ----------
fw = strategies['S_T2']['periods']['forward']

# ---------- 9. gates ----------
def gates_for(key, info):
    t = info['periods']['test']
    seasons_hit = sum(1 for s in info['seasons_test'].values() if s['hit_rate'] is not None and s['hit_rate'] > BREAKEVEN)
    seasons_n = sum(1 for s in info['seasons_test'].values() if s['hit_rate'] is not None)
    g6_pass = t['p_value'] is not None and t['p_value'] < ALPHA / N_FAMILY
    return {
        'G1 Provenance': dict(status='FAIL', note='Market lines (spread_line, total_line) have no documented origin in the repository; line-dependent results are unverified.'),
        'G2 Point in time': dict(status='PARTIAL', note='Own line uses only earlier games (verified by code). Lines are closing-type values with no timestamp, so timing of execution is unknown.'),
        'G3 Evaluation split': dict(status='PASS', note=f'Tuning {TRAIN[0]}-{TRAIN[1]}, sealed test {TEST[0]}-{TEST[1]}, forward {FORWARD}.'),
        'G4 Predictive quality vs market': dict(status='PASS' if gate4['mae_difference'] < 0 and gate4['diff_ci95'][1] < 0 else 'FAIL',
                                              note=f"Own-line MAE minus market MAE = {gate4['mae_difference']} points (95% CI {gate4['diff_ci95'][0]} to {gate4['diff_ci95'][1]})."),
        'G5 Economics': dict(status='NOT RUN', note='No executable, timestamped sportsbook prices or limits were verified; -110 is an assumption.'),
        'G6 Selection control': dict(status='PASS' if g6_pass else 'FAIL', note=f"Test p-value {t['p_value']} vs Bonferroni threshold {round(ALPHA / N_FAMILY, 4)} (family of {N_FAMILY})."),
        'G7 Stability': dict(status='PASS' if seasons_hit >= 7 and seasons_n == 10 else 'FAIL', note=f'{seasons_hit} of {seasons_n} test seasons above breakeven {round(BREAKEVEN, 4)}; rule requires 7 of 10.'),
    }

gates = {k: gates_for(k, v) for k, v in strategies.items()}
gates['P2_parlay'] = {
    'G1 Provenance': dict(status='FAIL', note='Depends on unverified market lines.'),
    'G2 Point in time': dict(status='PARTIAL', note='Legs chosen from pre-game own lines; joint prices not available.'),
    'G3 Evaluation split': dict(status='PASS', note='Test period only; no tuning on the parlay.'),
    'G4 Predictive quality vs market': dict(status='NOT RUN', note='No market joint-probability baseline.'),
    'G5 Economics': dict(status='NOT RUN', note='No executable parlay prices; price assumes independence of legs x -110 each.'),
    'G6 Selection control': dict(status='FAIL', note='Leg correlation not priced; family not corrected.'),
    'G7 Stability': dict(status='NOT RUN', note='Pairs overlap within weeks; not evaluated by season.'),
}

# ---------- 10. write outputs ----------
summary = dict(
    generated_from=dict(file='data/source/games.csv', sha256=sha256(SRC), rows_total=len(raw), rows_with_scores=len(games)),
    parameters=dict(K=K, home_field_elo=HFA, elo_per_point=SCALE, season_reversion=REVERT, train=TRAIN, test=TEST,
                    forward=FORWARD, thresholds=THRESHOLDS, primary_threshold=PRIMARY_T, pricing='-110 both sides (assumed)',
                    breakeven=round(BREAKEVEN, 4), family_size=N_FAMILY, alpha=ALPHA),
    checks=checks, strategies=strategies, gate4=gate4, correlations=corr, parlay=parlay, forward_2026_primary=fw,
    gates=gates,
)
(OUT / 'summary.json').write_text(json.dumps(summary, indent=2))

with open(OUT / 'bets_test_and_forward.csv', 'w', newline='') as f:
    wr = csv.DictWriter(f, fieldnames=list(bet_rows[0].keys()))
    wr.writeheader(); wr.writerows(bet_rows)

with open(OUT / 'games_test_2016_2026.csv', 'w', newline='') as f:
    cols = ['game_id', 'season', 'week', 'gameday', 'away', 'home', 'away_score', 'home_score', 'total', 'own_line', 'market_line', 'total_line', 'edge']
    wr = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
    wr.writeheader()
    for x in test_ev + [y for y in ev if y['season'] == FORWARD]:
        wr.writerow({**x, 'gameday': x['gameday']})

print(json.dumps(dict(checks=checks, gate4=gate4, corr=corr, parlay=parlay,
                      primary_test=strategies['S_T2']['periods']['test'], forward=fw), indent=1))
for k, v in strategies.items():
    print(k, 'test', v['periods']['test'])
print('gates S_T2', {k: v['status'] for k, v in gates['S_T2'].items()})
