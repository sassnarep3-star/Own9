from html import escape
from pathlib import Path

NFL='https://www.nfl.com/stats/'
NIST='https://www.itl.nist.gov/div898/handbook/eda/section4/eda4283.htm'
TAIL='https://www.itl.nist.gov/div898/handbook/eda/section3/eda35b.htm'
SAFE='https://www.gamblingcommission.gov.uk/about-us/guide/consumer-voice-2020-exploring-online-staking'
PAGES='https://docs.github.com/en/pages/getting-started-with-github-pages/about-github-pages'

def row(*cells, source):
    return '<tr>'+''.join('<td>'+escape(str(c))+'</td>' for c in cells)+f'<td><a href="{source}">Official source ↗</a></td></tr>'
def table(headers, rows):
    return '<div class="table-wrap"><table><thead><tr>'+''.join('<th>'+escape(h)+'</th>' for h in [*headers,'Reference'])+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'

pages={
'index.html': ('Overview','Executive summary', '''<p class="lead">A research workspace for originating NFL lines and testing whether strategies add predictive value—not a promise of profit.</p><div class="notice"><strong>Research status: not validated.</strong> No historical odds dataset, executable forecasts, backtest, correlation estimates, or live bets are available in this repository. No strategy has passed the gates.</div><div class="cards"><a href="strategies.html"><span>01 / RESEARCH</span><b>Strategy concepts</b><p>Singles, parlays and player props</p></a><a href="validation.html"><span>02 / PROCESS</span><b>Validation gates</b><p>How evidence earns a place</p></a><a href="leaderboard.html"><span>03 / RESULTS</span><b>Leaderboard</b><p>Evidence before rewards</p></a><a href="flags.html"><span>04 / REVIEW</span><b>Flagged for review</b><p>Open gaps and limitations</p></a></div><h2>At a glance</h2>'''+table(['Area','Finding','Status'],[
row('Repository','Initial checkout contained only a README; no model or dataset to audit.','Reviewed',source=PAGES),
row('Line origination','Proposed probability models require time-stamped inputs and market prices before validation.','Not implemented',source=NFL),
row('Skill versus luck','Out-of-sample testing and uncertainty can reduce misinterpretation; they cannot eliminate luck.','Proposed',source=NIST),
row('Correlation','No paired game-level sample was verified; no values are reported.','Unverified',source=NFL),
row('Risk','This is research, not betting advice; set limits and never risk money needed for essentials.','Safety',source=SAFE)])),
'strategies.html':('Strategies','Signal research', '''<p class="lead">Candidate designs, not verified edges. Official references identify data or statistical background; they do not endorse these strategies.</p>'''+table(['Candidate','Proposed signal and line','Required evidence','Status'],[
row('Single · game','Model a distribution of team scores from prior team performance, availability and home/away; derive win, spread and total probabilities.','Point-in-time inputs, historical executable prices and settlement rules.','Unvalidated',source=NFL),
row('Single · player prop','Model volume and efficiency conditional on expected participation; price the full outcome distribution, including push and void cases.','Official player game statistics, availability timestamps and prop quotes.','Unvalidated',source=NFL),
row('Parlay · different games','Estimate joint win probability; compare with actual offered payout rather than assuming independence.','Paired outcomes, concurrent quotes and joint out-of-sample calibration.','Unvalidated',source=NIST),
row('Combo · same game props','Jointly simulate shared game and player usage; estimate joint outcomes and settlement.','Paired player-game data, injury/void rules and actual combo prices.','Unvalidated',source=NFL)])+'''<h2>Pricing discipline</h2><p>For a no-push single with decimal odds D and model win probability p, expected net return per unit is p × D − 1. This is a mathematical proposal, not a verified market opportunity; pushes and voids require separate outcome probabilities. A fair no-push decimal price is 1/p. Margin, limits, availability and price movement matter.</p>'''),
'validation.html':('Validation','Evidence gates', '''<p class="lead">Proposed policy. Gates are intentionally strict and do not certify profit or eliminate randomness.</p>'''+table(['Gate','Predeclared requirement','Current result'],[
row('1 · Provenance','Retain original official outcomes, source links, snapshots, timestamps, identifiers and applicable permissions; reconcile revisions.','Not run',source=NFL),
row('2 · Point in time','Every feature and price must have been available before the forecast; freeze code and predictions before outcomes.','Not run',source=NFL),
row('3 · Evaluation','Train on earlier periods only; tune on a later validation period; seal a later test period. Report all folds and missingness.','Not run',source=NIST),
row('4 · Predictive quality','Compare against a predeclared market baseline with log loss, Brier score and calibration; report sample size and uncertainty.','Not run',source=NIST),
row('5 · Economics','Use executable timestamped prices, market-specific push/void rules and costs. Report net return, drawdown and uncertainty, not only hit rate.','Not run',source=SAFE),
row('6 · Selection control','Register the full candidate family and correct for multiple comparisons; cluster or block resampling by game/week; reserve a final untouched test.','Not run',source=NIST),
row('7 · Stability','Check seasons, market types and sensitivity to price, injury and lineup revisions. Fail closed on sparse data or drift.','Not run',source=NIST)])+'''<h2>Correlation protocol</h2><p>For each predeclared pair of binary leg outcomes, align by game and settlement, report sample size, Pearson/phi correlation, a game-clustered confidence interval and the observation window. Estimate joint win probability directly and validate it out of sample; a pairwise correlation alone does not price a multi-leg parlay. Do not substitute zero for missing estimates.</p>'''),
'leaderboard.html':('Leaderboard','Evidence before rewards', '''<p class="lead">A proposed competition framework; no competition or funded reward program exists yet.</p>'''+table(['Strategy','Gate status','Test score','Correlation','Reward'],[
row('Game single','Not run','','','',source=NFL),row('Player prop single','Not run','','','',source=NFL),row('Cross-game parlay','Not run','','','',source=NIST),row('Same-game prop combo','Not run','','','',source=NFL)])+'''<p>Blank cells mean unavailable, not zero. Proposed ranking: among strategies passing every gate, order by improvement in out-of-sample log loss against a matched market baseline; publish uncertainty, sample size, return and drawdown alongside it. Predeclare ties and eligibility before evaluation. Rewards should only be hypothetical until a sponsor and rules exist.</p>'''),
'flags.html':('Flagged for Review','Open items', '''<p class="lead">Unverified fields remain blank throughout this site. These items do not represent claims of a verified betting edge.</p>'''+table(['Item','Irregularity / next evidence','Status'],[
row('Historical market prices','No official, timestamped and executable historical price source was obtained.','Unverified',source=NFL),
row('Model and evaluation','No ingestion, trained model, predictions, backtest or independent test was present in the initial repository.','Not implemented',source=NFL),
row('Correlation values','No verified paired observations or estimates are available.','Unverified',source=NIST),
row('Strategy rewards','No competition rules, sponsor or rewards were verified.','Unverified',source=PAGES),
row('Luck','No statistical procedure can remove randomness from individual outcomes; confidence intervals quantify uncertainty under assumptions.','Limitation',source=NIST),
row('Source scope','NFL stats provide outcome context, not sportsbook odds or proof of strategy profitability.','Review',source=NFL),
row('Tail risk','Skew and heavy tails can distort summaries; inspect return distributions rather than relying on averages alone.','Review',source=TAIL)]) )}

nav=''.join(f'<a href="{href}">{escape(info[0])}</a>' for href,info in pages.items())
for filename,(label,title,content) in pages.items():
    Path(filename).write_text(f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)} · Own9</title><link rel="stylesheet" href="style.css"></head><body><header><div class="shell top"><a class="brand" href="index.html"><span>O9</span> OWN9 <small> / NFL RESEARCH</small></a><nav aria-label="Main navigation">{nav}</nav></div></header><main class="shell"><div class="eyebrow">NFL / {escape(label.upper())}</div><h1>{escape(title)}</h1>{content}</main><footer class="shell">OWN9 · Research workspace <span>Evidence over assumptions · Reviewed 04 Nov 2026</span></footer></body></html>''')
