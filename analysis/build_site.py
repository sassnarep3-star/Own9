#!/usr/bin/env python3
"""Builds the static GitHub Pages site at the repo root from data/site/*.json and verified source facts.

Run after analyze.py:  python analysis/build_site.py
Every table row carries a source link (official site or the named secondary dataset) and a
verification status. Values that are not confirmed against an official source are labelled
"Unverified" and flagged on flagged.html.
"""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT  # site is served from the repository root (GitHub Pages: main /)
DATA = ROOT / "data" / "site"
TODAY = "2026-11-04"

S = json.loads((DATA / "summary.json").read_text())
STRATS = json.loads((DATA / "strategies.json").read_text())
CORR = json.loads((DATA / "correlations.json").read_text())
OWN = json.loads((DATA / "own_lines.json").read_text())

E = html.escape

# ---------------------------------------------------------------- verified source register
SRC = {
    "wsgc_rules": ("Washington State Gambling Commission - Sports wagering requirements and rules",
                   "https://wsgc.wa.gov/tribal-partnerships/sports-wagering/sports-wagering-requirements-and-rules",
                   "Official (state regulator)"),
    "wsgc_hub": ("Washington State Gambling Commission - Sports wagering",
                 "https://wsgc.wa.gov/tribal-partnerships/sports-wagering",
                 "Official (state regulator)"),
    "nfl_rulebook": ("NFL Football Operations - 2026 NFL Rulebook",
                     "https://operations.nfl.com/rules-officiating/2026-nfl-rulebook",
                     "Official (league)"),
    "nfl_sched": ("NFL.com - Schedule (2026, Week 9 games)",
                  "https://www.nfl.com/schedules/",
                  "Official (league)"),
    "nfl_g1": ("NFL.com Game Center - Chiefs at Chargers, 2025 REG Week 1",
               "https://www.nfl.com/games/chiefs-at-chargers-2025-reg-1",
               "Official (league)"),
    "nfl_g2": ("NFL.com Game Center - Ravens at Dolphins, 2025 REG Week 9",
               "https://www.nfl.com/games/ravens-at-dolphins-2025-reg-9",
               "Official (league)"),
    "nflverse_games": ("nflverse / nfldata - data/games.csv (Lee Sharpe's nfldata; repo snapshot d5c8272)",
                       "https://github.com/nflverse/nfldata/blob/master/data/games.csv",
                       "Secondary (community dataset - not official)"),
    "nflverse_repo": ("nflverse / nfldata repository",
                      "https://github.com/nflverse/nfldata",
                      "Secondary (community dataset - not official)"),
    "nflreadr_dict": ("nflreadr - Data Dictionary: Schedules",
                      "https://nflreadr.nflverse.com/articles/dictionary_schedules.html",
                      "Secondary (package documentation)"),
    "nflreadr_rmd": ("nflreadr - dictionary_schedules.Rmd (source of the dictionary)",
                     "https://github.com/nflverse/nflreadr/blob/main/vignettes/dictionary_schedules.Rmd",
                     "Secondary (package source)"),
    "repo": ("This repository (sassnarep3-star/Own9)",
             "https://github.com/sassnarep3-star/Own9",
             "Project repository"),
}


def link(key, label=None):
    name, url, kind = SRC[key]
    return f'<a href="{E(url)}" target="_blank" rel="noopener">{E(label or name)}</a>'


def pct(x, d=1):
    return "—" if x is None else f"{x*100:.{d}f}%"


def num(x, d=2):
    return "—" if x is None else f"{x:,.{d}f}"


GATE_SHORT = {"G1_sample": "G1", "G2_wilson_lo_above_breakeven": "G2", "G3_bonferroni_p": "G3",
              "G4_stable_disc_and_halves": "G4", "G5_roi_positive_val": "G5"}


def tick(b):
    return '<span class="ok">✔</span>' if b else '<span class="bad">✘</span>'


# ---------------------------------------------------------------- page shell
NAV = [
    ("index.html", "Home"),
    ("summary.html", "Executive summary"),
    ("games.html", "Games & lines"),
    ("strategies.html", "Strategies"),
    ("correlations.html", "Correlations & parlays"),
    ("own-lines.html", "Own lines"),
    ("props.html", "Player props"),
    ("rules.html", "Rules & legal"),
    ("sources.html", "Sources"),
    ("flagged.html", "Flagged for review"),
]


def page(fname, title, body, active=None, extra_head=""):
    nav = "".join(
        f'<a href="{href}" class="{"active" if href == (active or fname) else ""}">{E(label)}</a>'
        for href, label in NAV
    )
    html_doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)} · Own9 NFL research</title>
<link rel="stylesheet" href="assets/style.css">
{extra_head}
</head>
<body>
<header class="top">
  <div class="brand"><a href="index.html">Own9 · NFL signal research</a></div>
  <nav>{nav}</nav>
</header>
<main>
{body}
</main>
<footer>
  <p>Research only, not betting advice. Data as of {TODAY}. Secondary-source values are labelled
  <span class="tag unv">Unverified</span>. Gambling is only legal in Washington at tribal casinos
  (see <a href="rules.html">Rules &amp; legal</a>). Problem gambling help: call or text 1-800-GAMBLER (US).</p>
  <p>Repository: <a href="https://github.com/sassnarep3-star/Own9">github.com/sassnarep3-star/Own9</a></p>
</footer>
</body>
</html>
"""
    (DOCS / fname).write_text(html_doc)


def table(headers, rows, cls="data"):
    th = "".join(f"<th>{h}</th>" for h in headers)
    trs = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="tablewrap"><table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>'


# ---------------------------------------------------------------- key numbers
val_pass = S["strategies_passing_all_gates"]
n_strat = S["strategies_tested"]
best = STRATS[0]
bv = best["val"]
mb = S["model"]
sc = S["sign_check"]
played = S["played_rows"]

# ================================================================ INDEX (landing)
cards = [
    ("summary.html", "Executive summary", "What was tested, what passed, and what it means."),
    ("games.html", "Games & lines", f"All {S['rows']:,} games {S['seasons'][0]}–{S['seasons'][1]} with verification status."),
    ("strategies.html", "Strategies", f"{n_strat} pre-specified strategies scored against validation gates."),
    ("correlations.html", "Correlations & parlays", "Outcome correlations and empirical parlay joint probabilities."),
    ("own-lines.html", "Own lines", "Our walk-forward power-rating model and this week's own lines."),
    ("props.html", "Player props", "Status of prop-bet data: not available from a verified source yet."),
    ("rules.html", "Rules & legal", "Official NFL rule changes and Washington sports-wagering law."),
    ("sources.html", "Sources", "Every source, its type, and when it was checked."),
    ("flagged.html", "Flagged for review", "Irregularities and unverified items, with links for manual review."),
]
card_html = "".join(
    f'<a class="card" href="{h}"><h3>{E(t)}</h3><p>{E(d)}</p></a>' for h, t, d in cards
)
kpis = [
    (f"{n_strat}", "strategies tested"),
    (f"{val_pass}", "pass all validation gates"),
    (pct(S["breakeven_110"], 2), "break-even win rate at -110"),
    (f"{mb['mae_model_vs_margin']:.2f} vs {mb['mae_market_vs_margin']:.2f}", "own-model vs market error (points, 2016–25)"),
]
kpi_html = "".join(f'<div class="kpi"><div class="kv">{E(v)}</div><div class="kl">{E(l)}</div></div>' for v, l in kpis)
body = f"""
<section class="hero">
  <h1>NFL signal research dashboard</h1>
  <p class="lede">Own9 builds its own NFL lines, tests simple betting strategies (single bets, parlay
  correlations, and player-prop status) against strict validation gates, and publishes every number with a source.</p>
  <p class="notice"><strong>Bottom line:</strong> none of the {n_strat} tested strategies passes all validation gates,
  and our own line model is less accurate than the market on 2016–2025 games. Nothing here is a verified betting edge.</p>
</section>
<section class="kpis">{kpi_html}</section>
<section><h2>Explore</h2><div class="cards">{card_html}</div></section>
<section>
  <h2>Sources at a glance</h2>
  <ul>
    <li>Official: {link('wsgc_rules')}; {link('nfl_rulebook')}; {link('nfl_sched')}; {link('nfl_g1')}; {link('nfl_g2')}.</li>
    <li>Secondary (not official, labelled Unverified): {link('nflverse_games')}, documented by {link('nflreadr_dict')}.</li>
  </ul>
</section>
"""
page("index.html", "Home", body, active="index.html")

# ================================================================ EXECUTIVE SUMMARY
wk9 = OWN["upcoming_week9_2026"]
top_edge = max(wk9, key=lambda r: abs(r["edge_home_pts"]))
best_rows = "".join(
    f"<li><strong>{E(r['id'])} {E(r['name'])}</strong>: validation n={r['val']['n']}, win {pct(r['val']['win_rate'])}, "
    f"ROI {pct(r['val']['roi'])}, p={r['val']['p_value']:.3f}; fails gates {', '.join(GATE_SHORT[k] for k,v in r['gates'].items() if not v)}.</li>"
    for r in STRATS[:3]
)
pl = {p["label"]: p for p in CORR["parlays"]}
p_home = pl["Home covers AND home wins"]
p_fav = pl["Favorite wins straight up AND covers"]
pair_map = {(p["a"], p["b"]): p for p in CORR["pairs"]}
hc_hw = pair_map.get(("home_cover", "home_win"))
body = f"""
<article class="prose">
<h1>Executive summary</h1>
<p class="meta">Prepared {TODAY} · Data: nflverse/nfldata games snapshot ({S['rows']:,} rows, {S['seasons'][0]}–{S['seasons'][1]}) ·
Code: <a href="https://github.com/sassnarep3-star/Own9/tree/main/analysis">analysis/</a></p>

<h2>1. What was asked</h2>
<p>Originate our own NFL lines, research strategies (single bets, parlays, player-prop combinations), remove luck as much as possible,
measure correlations, and rank strategies on a leaderboard with validation gates. This report covers single-game ATS, totals,
rule-based situational strategies, and our own line model. Player props are <strong>not analyzed</strong> because no verified
historical prop-line source was available (see <a href="props.html">Player props</a>).</p>

<h2>2. Method (how luck is controlled)</h2>
<ul>
  <li><strong>Pre-specified strategies only:</strong> {n_strat} rules are fixed in code and were not tuned after seeing validation results. Totals use the pre-game line, never the final total.</li>
  <li><strong>Discovery vs validation:</strong> 1999–2015 is used for a stability check; 2016–2025 is the out-of-sample window where gates are judged; 2026 completed games are a forward window (reported, not gated).</li>
  <li><strong>Gates:</strong> G1 at least {150} bets · G2 Wilson 95% lower bound above the {pct(S['breakeven_110'],2)} break-even at -110 · G3 one-sided binomial p below the Bonferroni threshold ({S['bonferroni_alpha']:.4f}) · G4 same direction in discovery and both validation halves · G5 positive ROI in validation.</li>
  <li><strong>Our own line model:</strong> time-decayed ridge team ratings with home-field, walk-forward (each game priced only with earlier games).</li>
</ul>

<h2>3. Results</h2>
<ul>
  <li><strong>Strategies passing all gates: {val_pass} of {n_strat}.</strong> Leaderboard ranking puts gate-passing strategies first, then validation ROI. Because none qualify, no strategy earns a reward under the stated rule.</li>
  <li>Top three by validation ROI (none pass):</li>
</ul>
<ul>{best_rows}</ul>
<ul>
  <li><strong>Own model vs market:</strong> mean absolute error over {mb['evaluated_games_2016_2025']:,} games (2016–2025) is
  {mb['mae_model_vs_margin']:.2f} points for our model and {mb['mae_market_vs_margin']:.2f} for the closing spread. The market was more accurate.</li>
  <li><strong>Correlations:</strong> home covering and home winning are strongly correlated
  (r = {hc_hw['r']:.2f}, 95% CI {hc_hw['ci_lo']:.2f} to {hc_hw['ci_hi']:.2f}). Two legs from the same game are not independent:
  in the sample, "home covers AND home wins" happens {pct(p_home['p_joint'])} of the time versus {pct(p_home['p_indep'])} if the legs were independent.
  Parlay math that assumes independence therefore misprices correlated legs.</li>
  <li><strong>Week 9 (2026) own lines:</strong> {len(wk9)} games priced. The largest disagreement with the market is {E(top_edge['away'])} at {E(top_edge['home'])}
  ({top_edge['edge_home_pts']:+.1f} points). That line is flagged as an outlier for review, not as a recommendation.</li>
</ul>

<h2>4. Legal context (Washington)</h2>
<p>Per the Washington State Gambling Commission, sports wagering is authorized in Washington only at tribal casinos, and mobile wagers
must be placed while the bettor is physically on the premises (geofenced). Under-18 bettors are prohibited. See
<a href="rules.html">Rules &amp; legal</a> for the verified text.</p>

<h2>5. Limits and honesty notes</h2>
<ul>
  <li>Historical betting lines are <strong>not published by the NFL</strong>, so spreads, totals, and moneylines cannot be confirmed from an official source. They are labelled Unverified everywhere.</li>
  <li>Official verification coverage is small: 2 completed game scores were checked against nfl.com, and all 15 Week 9 (2026) games were checked against the nfl.com schedule (14 match; 1 kickoff time differs and is flagged). The remaining rows are Unverified.</li>
  <li>An early draft graded totals against final scores (a look-ahead bug). It was caught and fixed before any result above was produced.</li>
  <li>A passing backtest would still need out-of-sample confirmation and real execution costs (limits, juice, and line movement) before it counted as an edge.</li>
</ul>

<h2>6. Recommendations</h2>
<ol>
  <li>Source verified historical closing lines and prop prices under a license that permits use (none verified yet).</li>
  <li>Resolve the flagged items on the <a href="flagged.html">Flagged for review</a> page, starting with the spread sign convention and the LV at SF kickoff mismatch.</li>
  <li>Re-run the pipeline each week (<code>python analysis/analyze.py &amp;&amp; python analysis/build_site.py</code>); the forward 2026 window will grow.</li>
</ol>
</article>
"""
page("summary.html", "Executive summary", body)

# ================================================================ GAMES (client-side table)
games_body = f"""
<section>
<h1>Games &amp; lines</h1>
<p class="meta">Source: {link('nflverse_games')} (Secondary). Status shows whether a value was confirmed against an official site.
Scores and lines are <strong>hidden by default</strong> because they are unverified. Tick the box to show them as analysis inputs.</p>
<div class="filters">
  <label>Season <select id="f-season"><option value="">All</option></select></label>
  <label>Team <input id="f-team" placeholder="e.g. BUF"></label>
  <label>Status <select id="f-status"><option value="">All</option><option value="verified">Verified</option><option value="scheduled">Scheduled</option><option value="unverified">Unverified</option></select></label>
  <label class="chk"><input type="checkbox" id="f-show"> Show unverified analysis inputs</label>
  <span id="count" class="meta"></span>
</div>
<div class="tablewrap"><table class="data" id="games-table">
<thead><tr>
<th>Season</th><th>Type</th><th>Wk</th><th>Date</th><th>Away</th><th>Home</th><th>Score (A–H)</th>
<th>Spread (home)</th><th>Total</th><th>Home ML</th><th>Own line (home)</th><th>Status</th><th>Sources</th>
</tr></thead><tbody></tbody></table></div>
<div class="pager"><button id="prev">Prev</button><span id="pg"></span><button id="next">Next</button></div>
</section>
"""
page("games.html", "Games & lines", games_body, extra_head='<script src="assets/games.js" defer></script>')

# ================================================================ STRATEGIES
rows = []
for r in STRATS:
    v = r["val"]
    gates = " ".join(
        f'<span title="{E(GATE_SHORT[k])}">{E(GATE_SHORT[k])} {"✔" if ok else "✘"}</span>' for k, ok in r["gates"].items()
    )
    passed = '<span class="tag pass">PASS</span>' if r["passed_all"] else '<span class="tag fail">FAIL</span>'
    rows.append([
        str(r["rank"]), E(r["id"]), E(r["name"]), E(r["desc"]),
        f"{r['disc']['n']:,} / {pct(r['disc']['win_rate'])}",
        f"{v['n']:,}", pct(v["win_rate"]), pct(v["wilson_lo"]), pct(v["roi"]),
        "—" if v["p_value"] is None else f"{v['p_value']:.3f}",
        f"{r['val_a']['n']:,} / {pct(r['val_a']['win_rate'])}",
        f"{r['val_b']['n']:,} / {pct(r['val_b']['win_rate'])}",
        f"{r['fwd']['n']:,} / {pct(r['fwd']['win_rate'])}",
        gates, passed,
        link("nflverse_games", "Dataset row ↗"),
    ])
strat_body = f"""
<section>
<h1>Strategy leaderboard</h1>
<p class="meta"><span class="tag unv">Unverified inputs</span> Results are computed from {link('nflverse_games')} (secondary).
Odds are assumed at -110 (break-even {pct(S['breakeven_110'],2)}). Ranking: gate-passing first, then validation ROI.
Gates: G1 n≥150 · G2 Wilson low &gt; break-even · G3 p &lt; {S['bonferroni_alpha']:.4f} (Bonferroni) · G4 same side in discovery and both validation halves · G5 ROI &gt; 0.</p>
<p><strong>Strategies passing all gates: {val_pass} of {n_strat}.</strong></p>
{table(['Rank','ID','Strategy','Rule','Discovery n / win%','Validation n','Val win%','Wilson 95% low','Val ROI','p-value','Val-A n / win%','Val-B n / win%','2026 fwd n / win%','Gates G1–G5','Result','Source'], rows)}
<h2>How to read this</h2>
<ul>
  <li>Win% excludes pushes. ROI is per 1 unit staked at -110 (win +0.909, loss −1).</li>
  <li>A high win% on a small sample (e.g. n=220) can still be luck. Gates require both size and significance.</li>
  <li>Strategy rules: S = situational, M = own-model edge vs market spread. Full rule text is in <code>analysis/analyze.py</code>.</li>
</ul>
</section>
"""
page("strategies.html", "Strategies", strat_body)

# ================================================================ CORRELATIONS
pair_rows = []
for p in CORR["pairs"]:
    pair_rows.append([
        E(p["label_a"]), E(p["label_b"]), f"{p['r']:+.3f}", f"[{p['ci_lo']:+.3f}, {p['ci_hi']:+.3f}]",
        f"{p['p_value']:.2g}", f"{p['n']:,}", link("nflverse_games", "Dataset ↗"),
    ])
par_rows = []
for p in CORR["parlays"]:
    par_rows.append([
        E(p["label"]), pct(p["p_a"]), pct(p["p_b"]), pct(p["p_joint"]), pct(p["p_indep"]),
        f"{p['decimal_odds_2leg']:.3f}", f"{p['ev_per_unit_empirical']:+.3f}", f"{p['ev_per_unit_if_independent']:+.3f}",
        link("nflverse_games", "Dataset ↗"),
    ])
corr_body = f"""
<section>
<h1>Correlations &amp; parlays</h1>
<p class="meta"><span class="tag unv">Unverified inputs</span> n = {CORR['n']:,} completed games with spreads and totals, 1999–2026, pushes excluded.
Pearson correlation of 0/1 outcome indicators; 95% CIs from {CORR['bootstrap_resamples']:,} bootstrap resamples (seed {CORR['seed']}).
Source: {link('nflverse_games')}.</p>
<h2>Outcome correlations</h2>
{table(['Outcome A','Outcome B','r','95% CI','p-value','n','Source'], pair_rows)}
<h2>Two-leg parlays at -110 per leg (empirical vs independent)</h2>
<p>Joint probability is measured in the data. "Independent" multiplies the two marginal probabilities. EV is per 1 unit staked
at the 2-leg decimal price shown. Parlay pricing is an arithmetic calculation, not a quoted sportsbook price.</p>
{table(['Parlay','P(A)','P(B)','P(A and B) observed','P(A)·P(B)','2-leg decimal','EV observed','EV if independent','Source'], par_rows)}
</section>
"""
page("correlations.html", "Correlations & parlays", corr_body)

# ================================================================ OWN LINES
nfl_w9 = {
    "JAX_BAL": ("Thu Nov 5, 2026", "8:15 PM", "PRIME"),
    "CIN_ATL": ("Sun Nov 8, 2026", "9:30 AM", "NFLN (Madrid)"),
    "DEN_CAR": ("Sun Nov 8, 2026", "1:00 PM", "CBS"),
    "DAL_IND": ("Sun Nov 8, 2026", "1:00 PM", "FOX"),
    "NYJ_KC": ("Sun Nov 8, 2026", "1:00 PM", "CBS"),
    "DET_MIA": ("Sun Nov 8, 2026", "1:00 PM", "CBS"),
    "CLE_NO": ("Sun Nov 8, 2026", "1:00 PM", "CBS"),
    "NYG_PHI": ("Sun Nov 8, 2026", "1:00 PM", "FOX"),
    "LA_WAS": ("Sun Nov 8, 2026", "1:00 PM", "FOX"),
    "HOU_LAC": ("Sun Nov 8, 2026", "4:05 PM", "CBS"),
    "LV_SF": ("Sun Nov 8, 2026", "4:25 PM", "FOX"),
    "GB_NE": ("Sun Nov 8, 2026", "4:25 PM", "FOX"),
    "ARI_SEA": ("Sun Nov 8, 2026", "4:25 PM", "FOX"),
    "TB_CHI": ("Sun Nov 8, 2026", "8:20 PM", "NBC"),
    "BUF_MIN": ("Mon Nov 9, 2026", "8:15 PM", "ESPN"),
}
NFLCOM_GAME = {g["game_id"]: g["nfl_com"] for g in json.loads((DATA / "games.json").read_text()) if g.get("nfl_com")}
own_rows = []
flag_lv = []
for r in wk9:
    key = f"{r['away']}_{r['home']}"
    nd, nt, nn = nfl_w9.get(key, ("—", "—", "—"))
    kick_ds = r["gametime"]
    kick_nfl = nt
    # compare 24h dataset time with nfl.com 12h time
    def to24(t):
        h, m = t.split(" ")[0].split(":")
        h = int(h)
        if "PM" in t and h != 12:
            h += 12
        if "AM" in t and h == 12:
            h = 0
        return f"{h:02d}:{m}"
    ok_time = (kick_ds == to24(kick_nfl)) if kick_nfl != "—" else False
    match = "✔ matches nfl.com" if ok_time else "✘ kickoff differs"
    if not ok_time:
        flag_lv.append(key)
    own_rows.append([
        f"{E(r['away'])} @ {E(r['home'])}", E(nd), f"{E(kick_ds)} (data) / {E(kick_nfl)} (nfl.com)",
        match, E(nn),
        f"{r['market_spread_home']:+.1f} <span class='tag unv'>Unverified</span>",
        f"{r['own_line_home']:+.2f}", f"{r['edge_home_pts']:+.2f}",
        f"<a href='{NFLCOM_GAME[r['game_id']]}' target='_blank' rel='noopener'>nfl.com game ↗</a> · "
        f"<a href='https://www.nfl.com/schedules/' target='_blank' rel='noopener'>schedule ↗</a>",
    ])
own_body = f"""
<section>
<h1>Own lines</h1>
<h2>Method</h2>
<p>Our model rates every team with a time-decayed ridge regression on game margins plus a home-field term
(λ = {OWN['model']['lambda_ridge']}, half-life {OWN['model']['half_life_days']} days). Each historical game is priced using only games
played before it, so the back-test has no look-ahead. Home field is currently <strong>{OWN['home_field_advantage']:+.2f}</strong> points.</p>
<p>Edge = our line minus the market spread. A positive edge means our model likes the home side more than the market does.
<span class="tag unv">Unverified</span> market spreads are from {link('nflverse_games')} and are not confirmed by any official source.</p>

<h2>Back-test, 2016–2025</h2>
{table(['Measure','Value','Source'], [
    ['Games evaluated', f"{mb['evaluated_games_2016_2025']:,}", link('nflverse_games', 'Dataset ↗')],
    ['Own model: mean absolute error vs actual margin', f"{mb['mae_model_vs_margin']:.3f} pts", link('nflverse_games', 'Dataset ↗')],
    ['Market spread: mean absolute error vs actual margin', f"{mb['mae_market_vs_margin']:.3f} pts", link('nflverse_games', 'Dataset ↗')],
])}
<p>Conclusion: the market spread is more accurate than our model. The model shows no edge yet, and its
signals are not used for recommendations.</p>

<h2>Week 9 (2026) — our own lines vs schedule check</h2>
<p>Schedule, kickoff time, and network are checked against the NFL schedule page. Spreads are Unverified.</p>
{table(['Game','Date (nfl.com)','Kickoff','Schedule check','Network (nfl.com)','Market spread (home)','Own line (home)','Edge (pts)','Sources'], own_rows)}

<h2>Current team ratings (our model, through 2026 Week 8)</h2>
{table(['Rank','Team','Rating (pts vs avg)','Source'],
       [[str(i+1), E(t['team']), f"{t['rating']:+.2f}", link('nflverse_games', 'Dataset ↗')] for i, t in enumerate(OWN['ratings_now'])])}
</section>
"""
page("own-lines.html", "Own lines", own_body)

# ================================================================ PROPS
props_body = f"""
<section>
<h1>Player props &amp; prop combos</h1>
<p class="notice"><strong>Status: not analyzed.</strong> No verified source of historical player-prop lines was reachable from this
session. Official NFL sources do not publish sportsbook prop prices. Rows below are intentionally blank.</p>
{table(['Prop market','Example line','Price (American)','Historical sample n','Hit rate','Correlation to game lines','Verification','Source'], [
    ['Player passing yards','—','—','—','—','—','<span class="tag unv">Unverified</span> blank','<a href="https://www.nfl.com/stats/player-stats/" target="_blank" rel="noopener">NFL.com player stats ↗ (stats only, no prices)</a>'],
    ['Player rushing yards','—','—','—','—','—','<span class="tag unv">Unverified</span> blank','<a href="https://www.nfl.com/stats/player-stats/" target="_blank" rel="noopener">NFL.com player stats ↗ (stats only, no prices)</a>'],
    ['Player receptions','—','—','—','—','—','<span class="tag unv">Unverified</span> blank','<a href="https://www.nfl.com/stats/player-stats/" target="_blank" rel="noopener">NFL.com player stats ↗ (stats only, no prices)</a>'],
    ['Anytime touchdown','—','—','—','—','—','<span class="tag unv">Unverified</span> blank','<a href="https://www.nfl.com/stats/player-stats/" target="_blank" rel="noopener">NFL.com player stats ↗ (stats only, no prices)</a>'],
    ['Same-game prop combo (SGP)','—','—','—','—','—','<span class="tag unv">Unverified</span> blank','—'],
])}
<p>To fill this page, provide a licensed historical prop-price source. Until then no prop strategy can be graded, and no prop
correlation value is claimed.</p>
</section>
"""
page("props.html", "Player props", props_body)

# ================================================================ RULES & LEGAL
rules_body = f"""
<section>
<h1>Rules &amp; legal</h1>
<p class="meta">Each row was checked against the linked official page on {TODAY}.</p>
<h2>Washington sports-wagering law</h2>
{table(['Finding (verified)','Source'], [
 ['Washington law authorizes sports wagering "on a very limited basis by restricting it to tribal casinos" (HB 2638, 2020).', link('wsgc_rules')],
 ['Each tribal gaming operation must use a geofence so mobile sports wagers can only be placed while the patron is physically on the premises.', link('wsgc_rules')],
 ['Prohibited participants include anyone under 18 years of age, agents or proxies, and athletes whose performance may affect the outcome.', link('wsgc_rules')],
 ['Washington prohibits wagers on events where the outcome is already determined ("past postings").', link('wsgc_rules')],
 ['Washington law has never allowed bracket pools, office sports pools, or fantasy sports.', link('wsgc_rules')],
 ['Bookmaking (accepting bets as a business, charging a fee/vigorish) is illegal in Washington.', link('wsgc_rules')],
 ['Sports wagering vendors and tribal operations are licensed/regulated through the Commission; full menu at the Commission hub.', link('wsgc_hub')],
])}
<p class="notice">Practical effect for a Seattle-area user: the strategies on this site cannot be placed through an online or
out-of-state app from Washington under the rules above. Check current WSGC guidance before acting on anything here.</p>

<h2>NFL 2026 rulebook (official)</h2>
{table(['Rule change (verified on the official rulebook page)','Rule','Source'], [
 ['Modifies alignment requirements for receiving-team players in the setup zone on a kickoff or safety kick.','6-1-3', link('nfl_rulebook')],
 ['Modifies the dead ball spot after a touchback when the kickoff is from the 50-yard line.','6-1-5', link('nfl_rulebook')],
 ['Permits the kicking team to declare an onside kick at any time during the game.','6-1-6', link('nfl_rulebook')],
 ['Permits League personnel to consult with on-field officials on potential disqualification for flagrant acts.','19-2', link('nfl_rulebook')],
])}

<h2>Official schedule checks</h2>
<p>The 2026 Week 9 slate (15 games) and kickoff times are checked on the NFL schedule page; the results are on the
<a href="own-lines.html">Own lines</a> page. One kickoff time differs and is flagged.</p>
</section>
"""
page("rules.html", "Rules & legal", rules_body)

# ================================================================ SOURCES
src_rows = []
for key, (name, url, kind) in SRC.items():
    checked = TODAY
    src_rows.append([E(name), f'<a href="{E(url)}" target="_blank" rel="noopener">{E(url)}</a>', E(kind), E(checked),
                     {"nfl_g1": "Score matched (KC 21, LAC 27)",
                      "nfl_g2": "Score matched (BAL 28, MIA 6)",
                      "nfl_sched": "15 Week 9 games: 14 match, 1 kickoff mismatch (LV @ SF)",
                      "nflverse_games": "Used for analysis; 2 scores verified; lines Unverified",
                      "nflreadr_dict": "Result = home − away and total confirmed; spread_line definition not retrieved",
                      "wsgc_rules": "Quoted on Rules page",
                      "nfl_rulebook": "2026 rule-change table on Rules page",
                      "wsgc_hub": "Hub link only",
                      "nflreadr_rmd": "Dictionary source file (no spread definition in fetched text)",
                      "nflverse_repo": "Repository snapshot d5c8272",
                      "repo": "Repository reviewed; README minimal"}.get(key, "")])
sources_body = f"""
<section>
<h1>Source register</h1>
<p class="meta">Official = league or state regulator. Secondary = community dataset, labelled Unverified unless a value was matched to an official page.</p>
{table(['Source','URL','Type','Checked','What was checked'], src_rows)}
<h2>Dataset snapshot</h2>
{table(['Item','Value'], [
  ['Rows (games)', f"{S['rows']:,}"],
  ['Season range', f"{S['seasons'][0]}–{S['seasons'][1]}"],
  ['Completed games', f"{S['played_rows']:,}"],
  ['Scheduled (no result yet)', f"{S['scheduled_rows']:,}"],
  ['Duplicate game IDs', str(S['duplicate_game_ids'])],
  ['Upstream snapshot', 'nflverse/nfldata commit d5c8272 (cloned, 2026-11-04)'],
  ['Local copy', '<code>data/raw/games.csv</code>'],
])}
</section>
"""
page("sources.html", "Sources", sources_body)

# ================================================================ FLAGGED FOR REVIEW
M = S["missing"]
jax_edge = [r["edge_home_pts"] for r in wk9 if r["away"] == "JAX"][0]
flags = [
    ("F1", "High", "Spread sign convention not confirmed from the official field definition",
     f"Data behaviour: correlation of margin with spread_line = {sc['corr_result_spread_2016_2025']:.3f} (2016–25); "
     f"mean(margin − spread) = {sc['mean_margin_minus_spread_2016_2025']:.2f}. The fetched nflreadr dictionary shows result and total definitions but not spread_line.",
     [link('nflreadr_dict'), link('nflreadr_rmd'), link('nflverse_games')]),
    ("F2", "High", "All betting-line values (spread, total, moneyline) are unverified",
     "No official NFL or Washington source publishes historical lines. Every line is labelled Unverified and hidden by default on the Games page.",
     [link('nflverse_games')]),
    ("F3", "High", "LV at SF (2026 Week 9) kickoff differs",
     "Dataset gametime 16:05 vs NFL.com 4:25 PM for Raiders at 49ers on Sun Nov 8, 2026.",
     [link('nfl_sched'), link('nflverse_games')]),
    ("F4", "Medium", "Extreme market line JAX @ BAL (2026 Week 9)",
     f"Dataset spread −10.0 with BAL as home team (under the convention in F1 this means BAL is a 10-point underdog). Our model's edge on this game is {jax_edge:+.1f} points. Cannot be verified; treat as a data error until confirmed.",
     [link('nfl_sched'), link('nflverse_games')]),
    ("F5", "Medium", "Verification coverage is small",
     "Only 2 completed game scores (2025 Week 1 and Week 9) were checked against nfl.com out of "
     f"{S['played_rows']:,} completed rows. The remainder are Unverified.",
     [link('nfl_g1'), link('nfl_g2')]),
    ("F6", "Medium", "Missing values in the dataset",
     f"Moneyline blank in {M['home_moneyline']:,} rows; temperature blank in {M['temp']:,} rows (affects the cold-weather strategy); "
     f"kickoff time blank in {M['gametime']:,}; roof blank in {M['roof']}; spread/total blank in {M['spread_line']}.",
     [link('nflverse_games')]),
    ("F7", "Low", "Repository has no license and minimal README",
     "The repository README contains only the title. No LICENSE file exists in the repo or in the upstream nfldata clone, so reuse rights for the data are unconfirmed.",
     [link('repo'), link('nflverse_repo')]),
    ("F8", "Low", "Early look-ahead bug (corrected)",
     "A first draft graded total-based rules against final totals, giving 98% win rates. Fixed by using pre-game lines; all reported results are from the corrected run.",
     [link('repo')]),
    ("F9", "Info", "Player-prop data not available",
     "No verified source of historical prop lines was found. The props strategy and correlations are not analyzed.",
     [link('nfl_sched')]),
    ("F10", "Info", "2026 Week 18 rows are dated 2027",
     "Expected: the dictionary says the season year is the year the season starts, so January games carry the next calendar year. Listed for transparency.",
     [link('nflreadr_dict')]),
]
flag_rows = [[E(i), E(sev), E(t), d, "; ".join(srcs)] for i, sev, t, d, srcs in flags]
flagged_body = f"""
<section>
<h1>Flagged for review</h1>
<p class="notice">These items are published for manual review and do not block the site. Each has the source links needed to check it.</p>
{table(['ID','Severity','Item','Detail','Source links'], flag_rows)}
<h2>Unverified items by count</h2>
{table(['Item','Count','Status'], [
  ['Rows with a betting line (dataset, all seasons)', f"{S['rows']-M['spread_line']:,}", '<span class="tag unv">Unverified</span>'],
  ['Completed game scores checked on nfl.com', '2', '<span class="tag ver">Verified</span>'],
  ['Week 9 (2026) games checked on nfl.com schedule', '15', '<span class="tag ver">Verified (14 match; 1 mismatch)</span>'],
])}
</section>
"""
page("flagged.html", "Flagged for review", flagged_body)

print("site pages written:", len(NAV), "in", DOCS)
