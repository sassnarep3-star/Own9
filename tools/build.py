"""Deterministic static renderer; no network calls, no invented NFL metrics."""
import json
import sys
from html import escape as e
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.registers import impact_rank  # noqa: E402
SOURCES = {s['id']: s for s in json.loads((ROOT/'evidence/sources.json').read_text())}
SUGGESTIONS = json.loads((ROOT/'research/suggestions.json').read_text())
QUESTIONS = json.loads((ROOT/'research/decision-register.json').read_text())
BRIEF = json.loads((ROOT/'research/decision-brief.json').read_text())
AVAILABILITY = json.loads((ROOT/'evidence/lineups/was-nyg-2026-week-9-10.json').read_text())
# Map the evidence file's own citation keys onto the shared source register.
GAMEBOOK = {
    'gamebook_week9_lar_was': 'nfl-gamebook-w9-lar-was',
    'gamebook_week9_nyg_phi': 'nfl-gamebook-w9-nyg-phi',
    'gamebook_week10_was_nyg': 'nfl-gamebook-w10',
    'injury_week10': 'nfl-injury',
}
INJURY = json.loads((ROOT/'evidence/availability/injury-report-2026-week-10.json').read_text())
PAGES = {}

# Navigation grouped by what the reader is trying to do, not by file order.
NAV_GROUPS = [
    ('Decide', [('decision.html','Decision brief'),('questions.html','Questions & answers')]),
    ('Evidence', [('index.html','Overview'),('availability.html','Availability tracker'),('data.html','Data requirements'),('sources.html','Sources')]),
    ('Research', [('strategies.html','Strategies'),('correlations.html','Correlations'),('validation.html','Validation'),('leaderboard.html','Leaderboard')]),
    ('Review', [('suggestions.html','Suggestions'),('flags.html','Flagged for review'),('audit.html','Repository audit')]),
]


def table(title, headers, rows):
    output = f'<h2>{e(title)}</h2><div class="table-wrap"><table><caption class="sr-only">{e(title)}</caption><thead><tr>'
    output += ''.join(f'<th scope="col">{e(h)}</th>' for h in [*headers, 'Evidence / scope'])
    output += '</tr></thead><tbody>'
    for i, (cells, refs, kind) in enumerate(rows,1):
        output += f'<tr id="{e(title.lower().replace(" ","-"))}-{i}">'
        for j,c in enumerate(cells):
            tag = 'th scope="row"' if j == 0 else 'td'
            close = 'th' if j == 0 else 'td'
            output += f'<{tag}>{e(str(c)) if c is not None else ""}</{close}>'
        links = ' · '.join(f'<a href="{e(SOURCES[r]["url"],quote=True)}">{e(SOURCES[r]["publisher"])} ↗</a>' for r in refs)
        output += f'<td><span class="evidence-kind">{e(kind)}</span>{links}</td></tr>\n'
    return output + '</tbody></table></div>'


def row(cells, refs=('repo',), kind='Project record'):
    return cells, refs, kind


def page(file, label, title, intro, content):
    PAGES[file] = (label,title,intro,content)


page('index.html','Overview','Evidence first.\nAn edge must be earned.',
     'An NFL line-origination lab for game singles, player props and joint bets. Built to test skill—not reward a lucky streak.',
     '''<div class="notice"><strong>Research framework · no validated strategies</strong><p>No verified historical executable odds or point-in-time paired dataset was obtained. NFL lines, measured correlations, test scores and cash rewards are intentionally blank. No wagering is enabled.</p></div>
<div class="cards"><a href="decision.html"><span>01 / DECIDE</span><b>Decision brief</b><p>16 open decisions, defaults and stopping rules</p></a><a href="questions.html"><span>02 / ASK</span><b>Questions &amp; answers</b><p>22 questions: answered, open, unpublished</p></a><a href="availability.html"><span>03 / AVAILABILITY</span><b>Who actually started</b><p>Official lineups, verified changes</p></a><a href="suggestions.html"><span>04 / REVIEW</span><b>Suggestions</b><p>Scored, falsifiable, choose before building</p></a><a href="strategies.html"><span>05 / HYPOTHESES</span><b>Signal registry</b><p>Singles, props &amp; joint models</p></a><a href="validation.html"><span>06 / DISCIPLINE</span><b>Seven evidence gates</b><p>Fail closed. Publish all trials.</p></a><a href="correlations.html"><span>07 / DEPENDENCE</span><b>Correlation lab</b><p>Paired evidence, not assumptions</p></a><a href="leaderboard.html"><span>08 / COMPETITION</span><b>Evidence leaderboard</b><p>No eligible entries, no awards</p></a></div>'''
     + table('Executive summary',['Decision area','Finding','Disposition'],[
         row(['Originate NFL lines','A distribution-first design is specified; tested pricing primitives exist. No officially verified fitted NFL probability model or numerical line is available in this dashboard.','Implemented math / model not implemented']),
         row(['Useful signals','Opponent-adjusted efficiency, pace, participation and shared game script are hypotheses; no direction, effect size or profitability is asserted.','Research proposals'],('nfl-stats','nfl-injury'),'Context only / proposed'),
         row(['Skill versus luck','Use sealed future periods, proper scoring, multiplicity control and uncertainty. These can test evidence of skill, not eliminate chance.','No skill certification'],('holdout','brier','multiplicity'),'Method support / policy proposed'),
         row(['Correlation','No verified aligned sample was obtained. Descriptive Pearson/phi code is tested only on synthetic examples.','Unverified NFL values'],('pearson','repo'),'Formula support / project record'),
         row(['Competition rewards','Separate target-matched tracks and hypothetical recognition badges are proposed. No sponsor, cash pool or awards exist.','No funded program']),
         row(['Availability tracking','Two official Game Books show four of four published starting elevens changed between Week 9 and Week 10 for WAS and NYG, and one starting slot has a fully documented replacement. The NFL publishes no depth tier, so second/third/fourth-string labels remain blank.','Verified change / tier unpublished'],('nfl-gamebook-w10','nfl-gamebook-w9-lar-was','nfl-gamebook-w9-nyg-phi'),'Direct publisher / three game books'),
         row(['Decisions and questions','16 decisions carry a default and a predeclared stopping rule. 22 questions are split into 12 answered, 8 open and 2 fields the publisher does not release.','Published registers'],
             ('repo',),'Project record'),
         row(['Suggested improvements','16 suggestions scored on decision impact and evidence cost. 12 accepted and carried by a decision, 2 deferred, 2 blocked on a missing archive or licence.','Reviewable queue'],('repo',),'Project record'),
         row(['Executive recommendation','Continue as a paper-research lab. Missing provenance, prices or validation blocks eligibility—not publication of limitations.','No bets recommended'])
     ]) + '<p class="download">Read the <a href="docs/RESEARCH_SPEC.md">full research specification</a>, the <a href="decision.html">decision brief</a> and the <a href="audit.html">repository audit</a>. Every empirical gap appears on <a href="flags.html">Flagged for Review</a>, and every proposed change is queued on <a href="suggestions.html">Suggestions</a>.</p>')

page('strategies.html','Strategies','The signal registry.',
     'Predeclared research candidates. These are designs to test, not discovered edges or recommendations. Contextual references do not endorse a strategy.',
     table('Candidate strategies',['ID / track','Proposed signal and model','Required ablation / falsification','State'],[
         row(['G1 · Game single','Opponent-adjusted past efficiency, pace and availability → regularized joint score distribution → moneyline, spread and total.','Remove efficiency, pace and availability one at a time; compare frozen baseline on later weeks.','Unvalidated'],('nfl-stats','nfl-injury'),'Official input categories / proposal'),
         row(['P1 · Player prop','Participation × opportunities × conditional efficiency; separate count and yardage distributions.','Exposure-only baseline; remove availability adjustments; audit missing participation and player-role changes.','Unvalidated'],('nfl-stats','nfl-injury'),'Official input categories / proposal'),
         row(['X1 · Cross-game parlay','Common-week latent scenarios → joint win probability. Use actual combo quote, not multiplied marginal odds.','Compare joint model with independence baseline; test held-out joint-event calibration.','Unvalidated'],('pearson','repo'),'Dependence background / proposal'),
         row(['S1 · Same-game prop combo','Shared plays, game script, team pass/rush and target allocation → joint player outcomes with accounting constraints.','Remove shared effects; check feasible combinations, joint calibration and every settlement rule.','Unvalidated'],('nfl-stats','pearson'),'Input / dependence context only'),
         row(['A1 · Selective abstention','Withhold when data, quoted price or model support is missing; freeze any edge cutoff before the final test.','Publish abstention count and coverage; evaluate the complete decision rule, not selected winners.','Unvalidated'],('holdout','repo'),'Overfit support / policy proposed')
     ]) + table('Line origination contract',['Market / calculation','Definition','Limit'],[
         row(['Home spread','With M = home score − away score and signed home handicap h, cover = P(M+h>0); push = P(M+h=0).','A fair handicap is not generally the mean margin. Numerical line unavailable.'],('repo',),'Project mathematical specification'),
         row(['Total / prop over','Sum mass strictly above the quoted threshold; retain equality as a separate push state.','Must specify overtime, participation and void rules. No numerical threshold inferred.'],('repo',),'Project mathematical specification'),
         row(['Fair decimal / expected return','Dfair = 1 + Ploss/Pwin. Net EV per unit = Pwin×(D−1) − Ploss − cost, with full refunds earning zero.','Undefined if Pwin=0; reduced-leg payouts require a full state model. Algebra tested, not an edge.'],('repo',),'Project algebra / unit tested'),
         row(['Market baseline','Normalize inverse decimal prices over every mutually exclusive exhaustive no-push outcome.','Proportional de-vig is a declared comparison convention, not verified true probability.'],('repo',),'Project baseline convention')
     ]))

page('validation.html','Validation','Seven gates. No shortcuts.',
     'Proposed acceptance policy. Every gate is mandatory; a missing value is not a pass. Unit tests validate software arithmetic—not NFL skill.',
     table('Validation gates',['Gate','Acceptance requirement','Artifact / current state'],[
         row(['1 · Provenance','All evaluated records have official outcome URLs, IDs, units, source timestamps, raw hashes and rule snapshots; quarantine missing required records.','No qualifying dataset · Not run'],('nfl-stats','repo'),'Data context / proposed policy'),
         row(['2 · Point in time','Features and quotes available before issuance and kickoff; freeze forecasts; no same-game fold leakage.','No forecast/quote ledger · Not run'],('holdout','repo'),'Leakage support / proposed policy'),
         row(['3 · Sealed test','Train on oldest seasons, tune on later data, seal latest eligible completed season. Freeze exact split and power-derived minimum sample before test.','Blocked by decision D-10 · Not run'],('holdout','repo'),'Holdout support / dependency named'),
         row(['4 · Predictive quality','Strictly positive simultaneous lower bound for paired log-loss improvement over matched market; report Brier, calibration, n and coverage.','No predictions or intervals · Not run'],('logloss','brier'),'Metric definitions / threshold proposed'),
         row(['5 · Economics','Captured executable prices, costs and all settlement states; strictly positive simultaneous lower mean-return bound and predeclared drawdown tolerance.','No executable quotes or tolerance · Not run'],('repo','tails'),'Project policy / tail-risk context'),
         row(['6 · Selection control','Register every candidate. Proposed familywise alpha 0.05 across all primary claims; justify week-block resampling and power before the test.','No frozen family or inference · Not run'],('multiplicity',),'Error-control background / design proposed'),
         row(['7 · Stability','Frozen subgroup and degradation tolerances, prospective paper replication, missing-data/drift kill switch. No data-driven relaxation.','No tolerances or replication · Not run'],('holdout','repo'),'Generalization context / policy proposed')
     ]) + '<h2>Measuring skill without pretending to remove luck</h2><p>Report prediction quality and financial outcomes separately. A winning bet is not proof of skill; neither is a short positive-return run. Freeze the candidate family, compare matched targets, account for shared games/weeks and retain the untouched final test. The precise power study, resampling method and drift tolerances remain unimplemented and block eligibility.</p>')

page('leaderboard.html','Leaderboard','Performance must earn its rank.',
     'Four proposed tracks, matched targets, full disclosure. No strategy has passed validation. Empty metric cells mean unavailable—not zero.',
     table('Strategy leaderboard',['Track','Eligibility','Rank','Test n','Log-loss gain LCB','Net-return LCB','Reward'],[
         row([track,'Not run',None,None,None,None,None]) for track in ['G1 · Game single','P1 · Player prop','X1 · Cross-game parlay','S1 · Same-game combo']
     ]) + table('Competition policy',['Rule','Proposed treatment','State'],[
         row(['Ranking','Only all-gate-pass candidates within each matched-target track; rank by simultaneous lower confidence bound on log-loss improvement.','Not active'],('logloss','repo'),'Metric support / project rule'),
         row(['Ties','Lower Brier, then lower frozen model complexity; unresolved ties share rank. No cross-track global winner.','Proposed'],('brier','repo'),'Metric support / project rule'),
         row(['Reward','Hypothetical non-cash “research leader” badge per eligible track. None if no candidate qualifies.','No actual award']),
         row(['Funding and integrity','No sponsor, monetary pool or cash schedule. Publish pre-outcome submission hashes, all variants, exclusions and immutable test results.','Unfunded / not implemented'])
     ]))

page('correlations.html','Correlations','Dependence is not optional.',
     'No empirical NFL correlation values are available. The tested functions are descriptive math; no default zero, inferred sign or assumed independence is used.',
     table('Correlation register',['Predeclared pair / level','Required alignment','n','Pearson / phi','Interval','Status'],[
         row(['QB pass yards ↔ receiver yards / statistics','Same game/player IDs, official game-level yardage; not season aggregates.',None,None,None,'Unverified'],('nfl-stats','pearson'),'Input / formula context'),
         row(['QB passing-over ↔ receiver receiving-over / leg wins','Same game, exact thresholds, directions and settlement rules; exclude and disclose refunds.',None,None,None,'Unverified'],('pearson','repo'),'Formula / proposed pair'),
         row(['Game total-over ↔ team player-over / leg wins','Same game and frozen lines; shared volume and game-script design needs testing.',None,None,None,'Unverified'],('pearson','repo'),'Formula / proposed pair'),
         row(['Separate-game selections / leg wins','Predeclared same-week pairs with simultaneous executable quotes; never join arbitrary rows.',None,None,None,'Unverified'],('pearson','repo'),'Formula / proposed pair'),
         row(['Strategy returns / economic outcomes','Aligned weeks, actual payout/cost/refund states; do not mix with stat or win correlations.',None,None,None,'Unverified'],('pearson','repo'),'Formula / proposed pair')
     ]) + table('Dependence protocol',['Step','Rule','Implementation'],[
         row(['Paired statistic','Pearson measures linear dependence; for nonconstant binary legs use 0/1 Pearson (phi). Constant-leg correlation is undefined.','Descriptive arithmetic tested'],('pearson',),'Direct formula support / algebra'),
         row(['Two-leg joint price','P(A∩B)=p×q+rho×sqrt(p(1−p)q(1−q)); require max(0,p+q−1) ≤ joint ≤ min(p,q).','Algebra and feasibility checks tested'],('repo',),'Project Bernoulli algebra'),
         row(['Decision gate','A Fisher-z interval is formed on the paired outcome. Only a verdict whose whole interval clears a predeclared deadband may enter a joint price; any other verdict returns no price at all.','Implemented and unit-tested on synthetic data'],('pearson','repo'),'Formula support / project implementation'),
         row(['Why not independence','Multiplying marginals asserts rho = 0. The gate exists so that a blank joint price is a true statement about missing evidence rather than a confident wrong number.','Policy implemented in engine/core.py'],('repo',),'Project policy'),
         row(['Three or more legs','Pairwise correlations do not determine the full joint distribution. Need joint simulation or direct joint-event estimation and validation.','Not implemented'],('repo',),'Project mathematical limitation'),
         row(['Uncertainty','Publish window, eligible/excluded n, missingness and proposed week-block intervals; study dependence and power first. No interval if design invalid.','Not implemented'],('pearson','multiplicity'),'Inference context / NFL policy proposed')
     ]))

page('data.html','Data requirements','A trustworthy input contract.',
     'Source discovery is not dataset validation. No external NFL numbers have been copied into this site. The following is the acquisition contract, not a claim that inputs were acquired.',
     table('Data acquisition register',['Category','Minimum required fields','Evidence found','Readiness'],[
         row(['Outcomes and efficiency','Stable game/team/player IDs, season/type, official game-level scores, participation and stat units.','NFL publishes statistics by category and season. No game-level archive ingested.','Unverified dataset'],('nfl-stats',),'Publication verified / acquisition absent'),
         row(['Availability','Player ID, practice/game status, original publication timestamp, captured revision.','NFL injury page retrieved; blanks present. Two official Game Books give a verified two-week starting lineup diff for WAS and NYG.','Partial: one club-game pair'],('nfl-injury','nfl-gamebook-w10'),'Publication verified / narrow coverage'),
         row(['Executable prices','Operator, jurisdiction, quote UTC, market/line, decimal price, stake availability, applicable settlement rules.','No qualifying official historical source obtained. NFL stats are not sportsbook odds.','Missing'],('repo','nfl-stats'),'Project gap / stats context only'),
         row(['Provenance','Source URL, retrieval UTC, original publication UTC, raw SHA-256, permissions and revision ID.','Source-reading register exists; no raw NFL observation archive or license confirmation.','Partial register only']),
         row(['Predictions and settlements','Code/config hash, training cutoff, issuance UTC, probabilities by state, official outcome link and settlement time.','No officially verified fitted model, forecast ledger or settled dataset; secondary analysis is separately flagged.','Missing'])
     ]) + '<h2>Fail-closed collection</h2><p>Do not infer a blank injury as healthy, a missing quote as an available price, a void as a loss, or a missing correlation as independence. Snapshot current inputs prospectively only after source permission and capture integrity are established. A credentialed feed has not been substituted or requested from you.</p>')

page('sources.html','Sources','The evidence register.',
     'Official publisher and reference pages read between 04 Nov and 14 Nov 2026, each with the precise claim it supports and its limits. A retrieved page is not a verified NFL model, and source contents can change.',
     table('Official source review',['Reference ID','Supported scope','Limits / evidence state','Checked UTC date'],[
         row([s['id'],s['supports'],s['scope']+' ['+s['status']+']',s['checked']],(s['id'],),'Direct publisher / checked scope') for s in SOURCES.values()
     ]) + '<p>Each row throughout the dashboard links to a publisher reference or this project’s primary repository record. Labels distinguish direct support, contextual background, mathematical specification and project proposals. The <a href="evidence/sources.json">machine-readable manifest</a> records the same scope. References do not endorse betting strategies.</p>')

page('audit.html','Repository audit','Review the implementation, too.',
     'The session began at commit 71236ddd74208838537d87ecfe722e578671f69f. All 11 tracked files at that checkout were read; PR #2 corrections and subsequent coordination records were preserved before integration.',
     table('Starting checkout audit',['File scope','Finding after reading contents','Action / status'],[
         row(['COORDINATION.md','Earlier session already built a framework; its old “initial README only” statement refers to an older checkout.','Preserved history, recorded handoffs and board conflicts.']),
         row(['README.md','Accurately called the old site a framework, but no executable research model existed.','Document actual math versus remaining acquisition/model gaps.']),
         row(['tools/build.py','Generated static proposals; broad NIST references did not directly substantiate every gate.','Replace generic labels with scoped evidence and explicit project policies.']),
         row(['tools/check.py','Checked local link targets and allowed source hosts only. Could not prove claim support or external reachability.','Replace with stronger structural/freshness checks; do not call this factual verification.']),
         row(['index.html / strategies.html / validation.html','Generated research concepts, not measured NFL results. Initial-repo claim needed historical context.','Re-render from reviewed specifications; no empirical values added.']),
         row(['leaderboard.html / flags.html','Empty placeholder metrics correctly withheld; no tested rank or funded reward.','Preserve blanks and add explicit validation blockers.']),
         row(['style.css','Responsive static CSS, no external scripts, trackers or data capture.','Improve current-page navigation, keyboard access, search and mobile table handling.'])
     ]) + table('Integration review',['New scope','Checks performed / acceptance','Limitation'],[
         row(['research/metrics.py / tests/','Synthetic arithmetic tests cover pricing, scoring, phi/joint feasibility, missing/nonfinite rejection and fail-closed eligibility.','No fitted model or strategy backtest.']),
         row(['evidence/ / docs/','Every manifest entry manually read in its stated scope. Full research specification separates proposals from facts.','No independent numerical NFL observation verification.']),
         row(['Site generator / checker / CI','Deterministic generation, local asset/fragment checks, all table rows have known sources, blank empirical metrics and Python test suite.','Remote reachability is not established by local checks; no automated claim-entailment certification.'])
     ]) + '<p>Later merged PR #6 added analysis/, data/raw/ and research/ pages. Those inherited empirical claims are not line-by-line certified by this session; see F12 on Flagged for Review. Audit references point to the official project repository as the primary record for implementation findings—not to unrelated NFL documentation. See <a href="docs/RESEARCH_SPEC.md">the full specification</a> for what remains unimplemented.</p>')

page('flags.html','Flagged for Review','Uncertainty, in plain sight.',
     'Published irregularities do not block this research site. They do block empirical claims, leaderboard eligibility and any reward. No manual input is required to view the findings.',
     table('Review register',['ID / severity','Finding','Required evidence / disposition','State'],[
         row(['F01 · Critical','No official historical executable odds archive obtained.','Capture verifiable operator quotes and settlement rules; never synthesize missing prices.','Unverified']),
         row(['F02 · Critical','No officially verified point-in-time paired NFL dataset, fitted model or forecasts.','Build permissioned ingestion and provenance before fitting or assessing signals.','Not implemented'],('nfl-stats','nfl-injury','repo'),'Publisher context / project gap'),
         row(['F03 · Critical','No measured correlations, confidence intervals or joint calibration.','Acquire aligned observations; freeze leg definitions and valid dependence-aware inference.','Unverified'],('pearson','repo'),'Formula context / project gap'),
         row(['F04 · Critical','No officially verified backtest, power study, sealed test, drift tolerances or prospective replication.','All seven gates fail closed. No strategy is certified.','Not run'],('holdout','repo'),'Method support / project gap'),
         row(['F05 · Review','Official source links alone do not prove the strategy or a row’s proposal.','Scope labels retained. NFL/NIST/SciPy/sklearn pages do not endorse an NFL edge.','Published limitation']),
         row(['F06 · Review','No funded competition, sponsor, monetary rewards or actual badges awarded.','Non-cash recognition rules are hypothetical; leave cash amounts blank.','Unverified']),
         row(['F07 · Limitation','Luck cannot be removed; validation is not a guarantee of future profit.','Probabilistic forecasting and held-out evidence, not deterministic winning claims.','No promise made'],('holdout','brier'),'Uncertainty context / project limitation'),
         row(['F08 · Review','Current injury and statistics pages cannot establish what was known before historical games.','Preserve timestamped original captures and revisions; do not infer missing health fields.','Unverified historical inputs'],('nfl-injury','nfl-stats'),'Current publications / historical limitation'),
         row(['F09 · Review','Source availability and row claim support are not proved by the site checker.','Manifest records pages actually read; local checks are structural only.','Published limitation']),
         row(['F10 · Limitation','Pricing functions support full refunds, not reduced-leg payouts, dead heats or every operator rule.','Use a complete payout-state model before evaluating affected parlays.','Unsupported states rejected by scope']),
         row(['F11 · Review','Prior sessions left deployment notes and broad contextual citations.','PR #2 corrections preserved; this session re-scopes sources and records its own deploy separately.','Historical context preserved']),
         row(['F12 · Review','Merged PR #6 adds a separate secondary-data analysis subtree; its PR reports only two completed scores officially cross-checked.','Inherited files preserved, but numerical findings not certified or adopted by this dashboard. Official row-level verification and rights remain unresolved.','Unverified inherited research']),
         row(['F13 · Review','The NFL publishes no depth chart or first/second/third/fourth-string designation, so the requested backup-tier tracking cannot be satisfied as specified.','Verified substitution: changed starters from official Game Books, with the tier field left blank and labelled unpublished. Published on the availability page.','Field unavailable — substituted'],('nfl-roster','nfl-gamebook-w10'),'Direct publisher / absence verified'),
         row(['F14 · Review','Three of four verified Week 10 lineup changes have no published cause, and six of seven Giants inactives carried no injury designation.','Do not infer cause from the injury report when the report itself shows no designation. Cause stays null.','Cause unpublished'],('nfl-injury','nfl-gamebook-w10'),'Direct publisher / two documents'),
         row(['F15 · Review','Official Game Books carry an NFL copyright notice restricting use.','Short excerpts only, originals linked, no republication. Formal permission not obtained.','Rights unresolved'],('nfl-gamebook-w10','nfl-capsules-pdf'),'Publisher terms'),
         row(['F16 · Review','Availability coverage is two clubs across two consecutive weeks only. Each week-over-week block compares one club against a different opponent, which is the correct comparison for a lineup diff but cannot separate a lineup effect from an opponent effect.','Coverage is a two-week demonstration, not a season dataset. Any generalisation is blocked on the archive decision D-11.','Narrow coverage'],('nfl-gamebook-w9-lar-was','nfl-gamebook-w9-nyg-phi','nfl-gamebook-w10'),'Direct publisher / three game books')
     ]) + '<p>Independent earlier-baseline technical report: <a href="release-checks/index.html">release quality review</a>. Its stored five-page / 28-row snapshot predates this nine-page integration; it is not a current factual or deployment certification.</p><p>Separate inherited, uncertified analysis: <a href="https://github.com/sassnarep3-star/Own9/pull/6">PR #6 and its stated evidence limitations</a>; <a href="research/flagged.html">its separate review register</a>. Its numerical findings are not adopted by this dashboard.</p>')




def _ranked():
    return sorted(enumerate(sorted(SUGGESTIONS['suggestions'], key=impact_rank), 1), key=lambda t: t[0])


def _suggestion_summary():
    counts = {k: sum(1 for x in SUGGESTIONS['suggestions'] if x['status'] == k)
              for k in ('accepted','deferred','blocked_on_evidence','proposed','rejected')}
    cells = ''.join(f'<div><b>{counts[k]}</b><span>{STATE_LABEL[k]}</span></div>'
                    for k in ('accepted','deferred','blocked_on_evidence','proposed','rejected'))
    return f'<div class="stats">{cells}</div>'


def _counts_strip():
    counts = {k: sum(1 for q in QUESTIONS['questions'] if q['state'] == k)
              for k in QUESTIONS['states']}
    cells = ''.join(f'<div><b>{counts[k]}</b><span>{STATE_LABEL[k]}</span></div>' for k in QUESTIONS['states'])
    return f'<div class="stats">{cells}</div>'


def _standing_constraints():
    items = ''.join(f'<li>{e(x)}</li>' for x in BRIEF['standing_constraints'])
    return f'<h2>Standing constraints</h2><ul class="rules">{items}</ul>'


def _lineup_tables():
    out = ['<h2>Starting-lineup comparison, Week 9 to Week 10</h2>',
           '<p>Each block lists the eleven players the NFL printed as starters for that side of the ball in the official Game Book. Order inside a block carries no meaning beyond the published print order.</p>']
    for b in AVAILABILITY['lineups']:
        week9 = ', '.join(f'{slot} {name}' for slot, name in b['week9'])
        week10 = ', '.join(f'{slot} {name}' for slot, name in b['week10'])
        rows = [
            row([f'{b["abbr"]} {b["side"]} · Week 9 starters', week9, 'Official Game Book',
                 'Baseline lineup'], (GAMEBOOK[b['week9_source']],), 'Direct publisher / game book'),
            row([f'{b["abbr"]} {b["side"]} · Week 10 starters', week10, 'Official Game Book',
                 'Compared lineup'], (GAMEBOOK[b['week10_source']],), 'Direct publisher / game book'),
            row([f'{b["abbr"]} {b["side"]} · left the starting eleven', ', '.join(b['out']) or 'None',
                 'Computed set difference', 'Verified change'], (GAMEBOOK[b['week9_source']],GAMEBOOK[b['week10_source']]), 'Both game books'),
            row([f'{b["abbr"]} {b["side"]} · entered the starting eleven', ', '.join(b['in']) or 'None',
                 'Computed set difference', 'Verified change'], (GAMEBOOK[b['week9_source']],GAMEBOOK[b['week10_source']]), 'Both game books'),
        ]
        note = b.get('note')
        block = table(f'{b["team"]} — {b["side"]}', ['Scope','Players as published','Method','Reading'], rows)
        if note:
            block += f'<p class="note">{e(note)}</p>'
        out.append(block)
    return ''.join(out)


def _replacement_table():
    rows = []
    for item in AVAILABILITY['replacement_chain']:
        injury = item['injury_report_week10']
        rows.append(row([
            f'{item["player_out"]} ({item["position"]}, {item["team"]})',
            f'Week 10 report: {", ".join(injury["injuries"]) or "blank"} · {injury["practice_status"]} · game status {injury["game_status"] or "blank"}',
            'Yes — printed under Not Active' if item['independently_inactive'] else 'Not established',
            (f'{item["replacement_started"]} ({item["replacement_number"]})' if item['replacement_started'] else 'No starting slot changed'),
            item['depth_tier_of_replacement'],
            item['evidence'],
        ], ('nfl-gamebook-w10','nfl-injury'), 'Direct publisher / two documents'))
    return ('<h2>Replacement chains the official record supports</h2>'
            '<p>Three players were both ruled out on the official report and printed under Not Active in the same week. Only one of them occupied a starting slot in the previous game, so only one produced a verified replacement starter.</p>'
            + table('Verified replacement chains',['Player out','Official Week 10 designation','Independently inactive','Replacement that started','Replacement depth tier','Evidence trail'],rows)
            + '<p>The depth-tier column is populated with blanks on purpose. The NFL roster page publishes number, position, roster status, height, weight, age and college — and nothing that ranks a backup. Filling this column would require inventing a field, so it stays empty and the limitation is published instead.</p>')

def _counterexamples():
    practice = AVAILABILITY['practice_status_counterexample']
    inactive = AVAILABILITY['no_designation_inactive_counterexample'][0]
    rows = [
        row([f'{p["player"]} ({p["position"]}, {p["team"]})',
             f'Injuries: {", ".join(p["injury_report_week10"]["injuries"]) or "blank"} · {p["injury_report_week10"]["practice_status"]} · game status {p["injury_report_week10"]["game_status"] or "blank"}',
             p['week10_outcome'], p['lesson']],
            ('nfl-injury', GAMEBOOK[p['source']]), 'Direct publisher / two documents')
        for p in practice
    ]
    rows.append(row([f'{inactive["team"]} inactive list',
        f'{inactive["inactives_without_any_week10_injury_designation"]} of {inactive["inactive_count"]} inactives had no Week 10 injury designation',
        ', '.join(inactive['inactive_list']), inactive['lesson']],
        (GAMEBOOK[inactive['source']], 'nfl-injury'), 'Direct publisher / two documents'))
    return ('<h2>Two official counterexamples</h2>'
            '<p>These are kept because they each kill a shortcut that would otherwise look reasonable. Both are re-checkable against the linked documents.</p>'
            + table('Where the naive reading fails',['Case','Official designation','What actually happened','Lesson for the model'],rows))


def _injury_table():
    rows = []
    for obs in INJURY['observations']:
        rows.append(row([f'{obs["player"]} · {obs["position"]} · {obs["abbr"]}',
                         ', '.join(obs['injuries']) or None,
                         obs['practice_status'],
                         obs['game_status'],
                         'Blank as published — not a clearance' if obs['game_status'] is None else 'Designation published'],
                        ('nfl-injury',), 'Direct publisher / weekly report'))
    return ('<h2>Official Week 10 injury report excerpt</h2>'
            f'<p>{e(INJURY["document_title"])}, two club tables only, retrieved {e(INJURY["retrieved_utc"])}. A blank game-status cell reproduces the published table and means no designation was shown — it does not mean the player was cleared.</p>'
            + table('Official injury observations',['Player / position / club','Injuries as published','Practice status','Game status','How to read the cell'],rows))


STATE_LABEL = {
    'decided': 'Decided',
    'decided_pending_data': 'Decided · waiting on data',
    'deferred': 'Deferred',
    'blocked': 'Blocked',
    'answered': 'Answered',
    'open_discoverable': 'Open · discoverable',
    'unknown_unpublished': 'Unknown · not published',
    'accepted': 'Accepted',
    'proposed': 'Proposed',
    'rejected': 'Rejected',
    'blocked_on_evidence': 'Blocked on evidence',
}


def _decision_rows():
    for d in BRIEF['decisions']:
        yield row([f'{d["id"]} · {d["decision"]}', d['default_if_nothing_changes'],
                   d['evidence_required'], d['current_blocker'] or 'None for the decision itself',
                   d['stopping_rule'], STATE_LABEL[d['state']], d['suggestion']])


page('decision.html','Decision brief','What to decide,\nand what would stop it.',
     'Every live decision this project supports, with the default if nothing changes and the stopping rule fixed before the evidence arrives. Nothing here is a recommendation to bet.',
     '<div class="notice"><strong>Default position: do nothing</strong><p>No decision below authorises a wager, a published line, or a reward. Where a decision is blocked, the honest action is to keep the field blank and work on the blocker.</p></div>'
     + table('Decision queue',['Decision','Default if nothing changes','Evidence required','Current blocker','Stopping rule (fixed in advance)','State','Suggestion'],list(_decision_rows()))
     + '<h2>Why a brief instead of a research summary</h2><p>A research summary records what was done. A brief records what is still open and what would end it. Without the second, an unknown can persist indefinitely because no row owns it. Every entry above names the artefact that would settle it, so the next action is visible without asking anyone.</p>'
     + _standing_constraints())

page('questions.html','Questions & answers','What must be known\nbefore deciding.',
     'A single register of the questions that have to be answered before a decision is reasonable, split into what is answered, what is still discoverable, and what the publisher does not release.',
     _counts_strip() + table('Question register',[
         'ID / group','Question','Information needed','Answer, if verified','Blocker / why not','State'],
         [row([f'{q["id"]} · {q["group"]}', q['question'], q['information_needed'],
               q.get('answer'), q.get('blocked_by') or 'Answered — see source', STATE_LABEL[q['state']]],
              tuple(q['sources']), 'Source for this row')
          for q in QUESTIONS['questions']])
     + '<p>A blank answer cell means the question is genuinely unanswered. It is not zero, not "no difference", and not a value to be filled in later from memory. Answers are limited to what the linked source actually states.</p>')

def _suggestion_rows():
    ordered = sorted(SUGGESTIONS['suggestions'], key=impact_rank)
    for i, s in enumerate(ordered, 1):
        yield row([f'{s["id"]} · #{i} · {s["category"]}', s['title'], s['problem'],
                   s['why_it_improves_decisions'], s['cost'], s['falsified_by'],
                   STATE_LABEL[s['status']]],
                  ('repo',), 'Project record')


def _suggestion_needs_rows():
    for s in SUGGESTIONS['suggestions']:
        if s.get('needs'):
            yield row([s['id'], s['title'], '; '.join(s['needs'])], ('repo',), 'Project record')


page('suggestions.html','Suggestions','Review before implementing.',
     'Every proposed improvement, scored on decision impact and evidence cost, with the statement that would falsify it. Select from this register rather than implementing by instinct.',
     '<div class="notice"><strong>How to use this page</strong><p>Read the "why it improves decisions" and "falsified by" columns first. A suggestion that cannot name what would falsify it should be rejected regardless of how appealing it sounds. Accepted items already have a matching decision on the Decision Brief.</p></div>'
     + _suggestion_summary()
     + table('Suggestion register',['ID / rank','Proposal','Problem it solves','Why it improves decisions','Cost','Falsified by','Status'], list(_suggestion_rows()))
     + table('What each suggestion still needs',['ID','Proposal','Missing artefact before it can proceed'], list(_suggestion_needs_rows()))
     + '<p>The ranking is predeclared: decision impact first, then evidence cost, then how hard the change is to undo. Scores are recorded by hand at 1–3 and are never derived from a result, so the order cannot be reverse-engineered to favour a finding.</p>')

page('availability.html','Availability tracker','Who actually started,\nnot who was listed.',
     'Official Game Book lineups compared across consecutive weeks, plus the official Week 10 injury report. Replacement depth tiers are blank because the NFL does not publish them.',
     '<div class="notice"><strong>The request was second, third and fourth string</strong><p>The NFL publishes a game-day starting lineup and a roster status code. It does not publish a depth chart, a starter flag per snap, or any first/second/third/fourth-string designation. This page therefore reports the verified part — who started, who left the lineup and who entered — and leaves every depth tier blank rather than guessing.</p></div>'
     + _lineup_tables() + _replacement_table() + _counterexamples() + _injury_table())

def render():
    files = {}
    for filename,(label,title,intro,content) in PAGES.items():
        nav = ''.join(
            f'<span class="nav-group"><span class="nav-label">{e(group)}</span>'
            + ''.join(f'<a href="{f}"'+(' aria-current="page"' if f==filename else '')+f'>{e(label)}</a>' for f,label in items)
            + '</span>' for group,items in NAV_GROUPS)
        files[filename] = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="Evidence-first NFL research dashboard. Strategies, validation, correlation requirements and transparent limitations."><title>{e(label)} · Own9 NFL Research</title><link rel="stylesheet" href="style.css"><script src="site.js" defer></script></head>
<body><a class="skip" href="#main">Skip to content</a><header><div class="shell top"><a class="brand" href="index.html"><span>O9</span> OWN9 <small> / NFL RESEARCH</small></a><span class="status-dot">Research only · no live wagers</span></div><nav class="shell" aria-label="Main navigation">{nav}</nav></header>
<main class="shell" id="main"><div class="page-meta"><span class="eyebrow">RESEARCH DESK / {e(label.upper())}</span><span>Evidence retrieved to 14 Nov 2026 · UTC</span></div><h1>{e(title).replace(chr(10),'<br>')}</h1><p class="lead">{e(intro)}</p><div class="filter" hidden><label for="row-search">Find a table entry</label><input id="row-search" type="search" placeholder="Filter this page…" autocomplete="off"><span id="row-count" role="status" aria-live="polite"></span></div>{content}<p class="disclaimer">Research, not betting advice. No verified edge or guaranteed return. Blank empirical values are unavailable and unverified, never zero.</p></main>
<footer class="shell"><b>OWN9 / NFL RESEARCH</b><span>Evidence over assumptions · <a href="sources.html">Evidence register</a> · <a href="flags.html">Flagged for Review</a></span></footer></body></html>\n'''
    return files

if __name__ == '__main__':
    for filename,content in render().items():
        (ROOT/filename).write_text(content)
    print(f'Rendered {len(PAGES)} static pages.')
