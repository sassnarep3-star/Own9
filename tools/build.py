"""Deterministic static renderer; no network calls, no invented NFL metrics."""
import json
from html import escape as e
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {s['id']: s for s in json.loads((ROOT/'evidence/sources.json').read_text())}
PAGES = {}


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
<div class="cards"><a href="strategies.html"><span>01 / HYPOTHESES</span><b>Signal registry</b><p>Singles, props & joint models</p></a><a href="validation.html"><span>02 / DISCIPLINE</span><b>Seven evidence gates</b><p>Fail closed. Publish all trials.</p></a><a href="correlations.html"><span>03 / DEPENDENCE</span><b>Correlation lab</b><p>Paired evidence, not assumptions</p></a><a href="leaderboard.html"><span>04 / COMPETITION</span><b>Evidence leaderboard</b><p>No eligible entries, no awards</p></a></div>'''
     + table('Executive summary',['Decision area','Finding','Disposition'],[
         row(['Originate NFL lines','A distribution-first design is specified; tested pricing primitives exist. No fitted NFL probability model or numerical line is available.','Implemented math / model not implemented']),
         row(['Useful signals','Opponent-adjusted efficiency, pace, participation and shared game script are hypotheses; no direction, effect size or profitability is asserted.','Research proposals'],('nfl-stats','nfl-injury'),'Context only / proposed'),
         row(['Skill versus luck','Use sealed future periods, proper scoring, multiplicity control and uncertainty. These can test evidence of skill, not eliminate chance.','No skill certification'],('holdout','brier','multiplicity'),'Method support / policy proposed'),
         row(['Correlation','No verified aligned sample was obtained. Descriptive Pearson/phi code is tested only on synthetic examples.','Unverified NFL values'],('pearson','repo'),'Formula support / project record'),
         row(['Competition rewards','Separate target-matched tracks and hypothetical recognition badges are proposed. No sponsor, cash pool or awards exist.','No funded program']),
         row(['Executive recommendation','Continue as a paper-research lab. Missing provenance, prices or validation blocks eligibility—not publication of limitations.','No bets recommended'])
     ]) + '<p class="download">Read the <a href="docs/RESEARCH_SPEC.md">full research specification</a> and <a href="audit.html">repository audit</a>. All empirical gaps appear on <a href="flags.html">Flagged for Review</a>.</p>')

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
         row(['3 · Sealed test','Train on oldest seasons, tune on later data, seal latest eligible completed season. Freeze exact split and power-derived minimum sample before test.','No split/power report · Not run'],('holdout',),'Holdout support / NFL design proposed'),
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
         row(['Three or more legs','Pairwise correlations do not determine the full joint distribution. Need joint simulation or direct joint-event estimation and validation.','Not implemented'],('repo',),'Project mathematical limitation'),
         row(['Uncertainty','Publish window, eligible/excluded n, missingness and proposed week-block intervals; study dependence and power first. No interval if design invalid.','Not implemented'],('pearson','multiplicity'),'Inference context / NFL policy proposed')
     ]))

page('data.html','Data requirements','A trustworthy input contract.',
     'Source discovery is not dataset validation. No external NFL numbers have been copied into this site. The following is the acquisition contract, not a claim that inputs were acquired.',
     table('Data acquisition register',['Category','Minimum required fields','Evidence found','Readiness'],[
         row(['Outcomes and efficiency','Stable game/team/player IDs, season/type, official game-level scores, participation and stat units.','NFL publishes statistics by category and season. No game-level archive ingested.','Unverified dataset'],('nfl-stats',),'Publication verified / acquisition absent'),
         row(['Availability','Player ID, practice/game status, original publication timestamp, captured revision.','NFL injury page retrieved; blanks present. No historical point-in-time ledger.','Unverified dataset'],('nfl-injury',),'Publication verified / acquisition absent'),
         row(['Executable prices','Operator, jurisdiction, quote UTC, market/line, decimal price, stake availability, applicable settlement rules.','No qualifying official historical source obtained. NFL stats are not sportsbook odds.','Missing'],('repo','nfl-stats'),'Project gap / stats context only'),
         row(['Provenance','Source URL, retrieval UTC, original publication UTC, raw SHA-256, permissions and revision ID.','Source-reading register exists; no raw NFL observation archive or license confirmation.','Partial register only']),
         row(['Predictions and settlements','Code/config hash, training cutoff, issuance UTC, probabilities by state, official outcome link and settlement time.','No fitted model, forecast ledger or settled dataset.','Missing'])
     ]) + '<h2>Fail-closed collection</h2><p>Do not infer a blank injury as healthy, a missing quote as an available price, a void as a loss, or a missing correlation as independence. Snapshot current inputs prospectively only after source permission and capture integrity are established. A credentialed feed has not been substituted or requested from you.</p>')

page('sources.html','Sources','The evidence register.',
     'Official publisher pages read on 04 Nov 2026, with the precise claim supported and limits. A retrieved page is not a verified NFL model. Source contents can change.',
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
     ]) + '<p>Audit references point to the official project repository as the primary record for implementation findings—not to unrelated NFL documentation. See <a href="docs/RESEARCH_SPEC.md">the full specification</a> for what remains unimplemented.</p>')

page('flags.html','Flagged for Review','Uncertainty, in plain sight.',
     'Published irregularities do not block this research site. They do block empirical claims, leaderboard eligibility and any reward. No manual input is required to view the findings.',
     table('Review register',['ID / severity','Finding','Required evidence / disposition','State'],[
         row(['F01 · Critical','No official historical executable odds archive obtained.','Capture verifiable operator quotes and settlement rules; never synthesize missing prices.','Unverified']),
         row(['F02 · Critical','No point-in-time paired NFL dataset, fitted model or forecasts.','Build permissioned ingestion and provenance before fitting or assessing signals.','Not implemented'],('nfl-stats','nfl-injury','repo'),'Publisher context / project gap'),
         row(['F03 · Critical','No measured correlations, confidence intervals or joint calibration.','Acquire aligned observations; freeze leg definitions and valid dependence-aware inference.','Unverified'],('pearson','repo'),'Formula context / project gap'),
         row(['F04 · Critical','No backtest, power study, sealed test, drift tolerances or prospective replication.','All seven gates fail closed. No strategy is certified.','Not run'],('holdout','repo'),'Method support / project gap'),
         row(['F05 · Review','Official source links alone do not prove the strategy or a row’s proposal.','Scope labels retained. NFL/NIST/SciPy/sklearn pages do not endorse an NFL edge.','Published limitation']),
         row(['F06 · Review','No funded competition, sponsor, monetary rewards or actual badges awarded.','Non-cash recognition rules are hypothetical; leave cash amounts blank.','Unverified']),
         row(['F07 · Limitation','Luck cannot be removed; validation is not a guarantee of future profit.','Probabilistic forecasting and held-out evidence, not deterministic winning claims.','No promise made'],('holdout','brier'),'Uncertainty context / project limitation'),
         row(['F08 · Review','Current injury and statistics pages cannot establish what was known before historical games.','Preserve timestamped original captures and revisions; do not infer missing health fields.','Unverified historical inputs'],('nfl-injury','nfl-stats'),'Current publications / historical limitation'),
         row(['F09 · Review','Source availability and row claim support are not proved by the site checker.','Manifest records pages actually read; local checks are structural only.','Published limitation']),
         row(['F10 · Limitation','Pricing functions support full refunds, not reduced-leg payouts, dead heats or every operator rule.','Use a complete payout-state model before evaluating affected parlays.','Unsupported states rejected by scope']),
         row(['F11 · Review','Prior sessions left deployment notes and broad contextual citations.','PR #2 corrections preserved; this session re-scopes sources and records its own deploy separately.','Historical context preserved']),
         row(['F12 · Review','Overlapping PR #6 proposes numerical research from secondary data; its PR reports only two completed scores officially cross-checked.','Not integrated or certified here. Coordinate a disjoint follow-up and quarantine unsupported empirical values before publishing.','Unverified parallel proposal'])
     ]) + '<p>Independent earlier-baseline technical report: <a href="release-checks/index.html">release quality review</a>. Its stored five-page / 28-row snapshot predates this nine-page integration; it is not a current factual or deployment certification.</p><p>Separate, unintegrated proposal: <a href="https://github.com/sassnarep3-star/Own9/pull/6">PR #6 and its stated evidence limitations</a>. Its numerical findings are not adopted by this dashboard.</p>')


def render():
    files = {}
    for filename,(label,title,intro,content) in PAGES.items():
        nav = ''.join(f'<a href="{f}"'+(' aria-current="page"' if f==filename else '')+f'>{e(v[0])}</a>' for f,v in PAGES.items())
        files[filename] = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="Evidence-first NFL research dashboard. Strategies, validation, correlation requirements and transparent limitations."><title>{e(label)} · Own9 NFL Research</title><link rel="stylesheet" href="style.css"><script src="site.js" defer></script></head>
<body><a class="skip" href="#main">Skip to content</a><header><div class="shell top"><a class="brand" href="index.html"><span>O9</span> OWN9 <small> / NFL RESEARCH</small></a><span class="status-dot">Research only · no live wagers</span></div><nav class="shell" aria-label="Main navigation">{nav}</nav></header>
<main class="shell" id="main"><div class="page-meta"><span class="eyebrow">RESEARCH DESK / {e(label.upper())}</span><span>As of 04 Nov 2026 · UTC</span></div><h1>{e(title).replace(chr(10),'<br>')}</h1><p class="lead">{e(intro)}</p><div class="filter" hidden><label for="row-search">Find a table entry</label><input id="row-search" type="search" placeholder="Filter this page…" autocomplete="off"><span id="row-count" role="status" aria-live="polite"></span></div>{content}<p class="disclaimer">Research, not betting advice. No verified edge or guaranteed return. Blank empirical values are unavailable and unverified, never zero.</p></main>
<footer class="shell"><b>OWN9 / NFL RESEARCH</b><span>Evidence over assumptions · <a href="sources.html">Evidence register</a> · <a href="flags.html">Flagged for Review</a></span></footer></body></html>\n'''
    return files

if __name__ == '__main__':
    for filename,content in render().items():
        (ROOT/filename).write_text(content)
    print(f'Rendered {len(PAGES)} static pages.')
