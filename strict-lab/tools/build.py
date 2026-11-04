"""Deterministic static dashboard. All tables carry scoped official citations."""
import csv
import io
import json
from html import escape as e
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAT = json.loads((ROOT/'research/catalog.json').read_text())
POLICY = json.loads((ROOT/'research/policy.json').read_text())
RUN = json.loads((ROOT/'research/run.json').read_text())
SOURCES = {s['id']: s for s in CAT['sources']}
DOWNLOADS = ROOT/'downloads'
DOWNLOADS.mkdir(exist_ok=True)


def refs(ids):
    return ''.join(f'<a class="source-link" href="{e(SOURCES[i]["url"], quote=True)}" '
                   f'title="{e(SOURCES[i]["scope"], quote=True)}">{e(i)} ↗</a>' for i in ids)


def table(key, title, headers, rows):
    """rows = (cells, evidence type, source IDs); null means withheld, never zero."""
    export = io.StringIO(newline='')
    writer = csv.writer(export)
    writer.writerow([*headers, 'Evidence type', 'Official references', 'Source coverage'])
    html_rows = []
    for cells, evidence, ids in rows:
        if not ids or any(i not in SOURCES for i in ids):
            raise ValueError(f'Unregistered source in {key}')
        writer.writerow([*['' if c is None else c for c in cells], evidence,
                         ' | '.join(SOURCES[i]['url'] for i in ids),
                         ' | '.join(SOURCES[i]['scope'] for i in ids)])
        tds = ''.join('<td class="empty" aria-label="Unverified; value withheld" title="Unverified; value withheld"></td>'
                      if c is None else f'<td>{e(str(c))}</td>' for c in cells)
        html_rows.append(f'<tr>{tds}<td><span class="badge">{e(evidence)}</span></td><td>{refs(ids)}</td></tr>')
    (DOWNLOADS/f'{key}.csv').write_text(export.getvalue())
    return f'''<section class="data-section" aria-labelledby="{key}-title"><div class="section-head"><h2 id="{key}-title">{e(title)}</h2><a class="download" href="downloads/{key}.csv" download>↓ CSV</a></div><div class="table-wrap" tabindex="0" role="region" aria-label="{e(title)}"><table><caption class="sr-only">{e(title)}. Blank values are unverified. Sources on proposal rows are contextual, not endorsements.</caption><thead><tr>{''.join(f'<th scope="col">{e(h)}</th>' for h in [*headers, 'Evidence type', 'Official references'])}</tr></thead><tbody>{''.join(html_rows)}</tbody></table></div><p class="table-count" aria-live="polite">{len(rows)} entries · Sources describe context, not proof of a strategy’s performance.</p></section>'''


def note(text, kind='notice'):
    return f'<div class="{kind}">{text}</div>'


pages = {}
# Executive summary
cards = [('strategies.html','01','Signal research','Singles, parlays and player combos'),
         ('validation.html','02','Validation gates','Evidence required before eligibility'),
         ('leaderboard.html','03','Research leaderboard','No rankings without a sealed test'),
         ('flags.html','04','Flagged for Review','Visible gaps, never hidden assumptions')]
content = '''<div class="hero"><div><p class="kicker">EXECUTIVE SUMMARY</p><h1>Evidence first.<br>Better lines follow.</h1><p class="lead">An NFL line-origination research lab. Develop signals, price joint outcomes and reward reproducible skill—not a lucky run.</p></div><div class="hero-aside"><span class="status-dot"></span><b>Research only</b><p>No strategy is validated.<br>No live lines or wagers.<br>No funded reward program.</p><a href="flags.html">See evidence gaps →</a></div></div>'''
content += note('<strong>Decision: do not deploy capital.</strong> Official reference pages were checked, but this strict-source lab has no eligible point-in-time outcomes-and-prices dataset. Measured performance and correlations are deliberately blank. Luck cannot be removed; uncertainty can be measured under stated assumptions.')
content += f'''<div class="metrics"><div><span>Candidate designs</span><b>{len(CAT['strategies']):02}</b><small>Proposals, not proven edges</small></div><div><span>Gate-eligible strategies</span><b>{sum(s['eligible'] for s in RUN['strategies']):02}</b><small>All candidates blocked</small></div><div><span>Checked references</span><b>{len(SOURCES):02}</b><small>League, methods & platform</small></div><div><span>Open review items</span><b>{len(CAT['flags']):02}</b><small>Published transparently</small></div></div>'''
content += '<div class="cards">'+''.join(f'<a href="{url}"><span>{n} / EXPLORE</span><b>{title}</b><p>{desc}</p><i aria-hidden="true">↗</i></a>' for url,n,title,desc in cards)+'</div>'
content += table('summary','Executive findings',['Area','Finding','Decision'],[
(['Origination','Use a calibrated joint score/stat distribution to derive fair probabilities and prices; executable math utilities are included, not a fitted NFL model.','Model fitting blocked'],'Project design',['NFL-SCORES','DK-MARKET']),
(['Signals','Eight candidates cover game singles, player props, cross-game parlays and same-game combos. Feature effects and correlation signs must be measured.','Unvalidated'],'Project proposal',['NFL-STATS','NFL-INJ','SCI-RHO']),
(['Skill evidence','Rank sealed-test proper-score improvement against a contemporaneous matched market baseline, with calibration, economic robustness and multiple-test control.','No eligible entries'],'Proposed policy',['SK-SCORE','SK-CAL','SM-HOLM']),
(['Primary blocker','No verified historical executable quotes, complete paired outcome sample or independent test evidence in this lab. Real ROI, CLV, correlation and reward values are withheld.','No performance claim'],'Repository finding',['NFL-STATS','DK-GENERAL']),
(['Risk','Official methods documentation is not evidence of profit. Tail sensitivity and dependent observations can invalidate naive summaries.','Paper research only'],'Methodological scope',['NIST-TAIL','SCI-RHO'])])
content += '<p class="reading"><a href="downloads/executive-summary.md" download>↓ Download executive summary</a> · <a href="requirements.html">Full requirements & repository audit →</a></p>'
pages['index.html'] = ('Overview','Executive summary',content)

# Candidate table
content = '<h1>Signal research</h1><p class="lead">Eight falsifiable designs. Each must earn eligibility independently; none is a verified betting edge.</p>'
content += note('<strong>Source boundary.</strong> League pages identify potential inputs; method references explain tools. Neither endorses these features, their direction, nor profitability. No source-derived numerical signal estimates are available.')
content += table('strategies','Candidate registry',['ID / track','Signal design','Required official evidence','Falsification test','State'],[
([f'{s["id"]} · {s["track"]}',s['name']+' — '+s['design'],s['inputs'],s['falsification'],s['status']],s['evidence'],s['sources']) for s in CAT['strategies']])
content += '<h2>Origination workflow</h2><ol class="steps"><li><b>Reconcile inputs.</b> Preserve original official snapshots and their availability times, identifiers, revision history and permitted use.</li><li><b>Fit only to earlier information.</b> Learn a joint score or stat distribution from training weeks. Shrink sparse player/team effects; tune only on a later validation window.</li><li><b>Freeze the forecast.</b> Save code, features, thresholds, probability distribution and quote before kickoff. No retroactive feature updates.</li><li><b>Price exact settlements.</b> Integrate win/push/loss or all combo settlement states. Compare with actual offered payouts, not theoretical multiplied singles.</li><li><b>Test and abstain.</b> Walk forward by week, then evaluate the untouched final trial. Missing or inadequate evidence means no entry.</li></ol>'
pages['strategies.html'] = ('Strategies','Signal research',content)

# Methods
content = '<h1>Pricing & dependence</h1><p class="lead">Executable primitives, explicit assumptions. These are mathematical definitions and project methods—not observed NFL estimates.</p>'
content += table('pricing','Pricing specification',['Calculation','Definition / implementation','Boundary'],[
(['American → decimal','A ≥ 100: D = 1 + A/100. A ≤ −100: D = 1 + 100/|A|.','Reject nonfinite or nonstandard inputs.'], 'Derived identity',['DK-MARKET']),
(['No-vig baseline','qᵢ = (1/Dᵢ) / Σⱼ(1/Dⱼ) for exhaustive, mutually exclusive selections in the same market and quote time.','Proportional normalization is a modeling convention, not the true probability; do not normalize unrelated legs.'],'Project convention',['SK-SCORE','DK-MARKET']),
(['Single expected return','EV per unit = p(win) × D + p(refund) − 1. Fair D = (1 − p(refund)) / p(win).','Refund means full stake return only; partial/dead-heat settlements need a separate payout-state model.'],'Derived identity',['DK-MARKET']),
(['Spread and total','For home score H, away A: home covers when H − A + handicap > 0; Over wins when H + A > total. Sum probabilities over the joint PMF; equality is a push for scoped two-way rules.','A home handicap of −3 requires a margin > 3. Missing PMF tail mass is rejected, never silently renormalized.'],'Derived settlement',['DK-MARKET']),
(['Two binary legs','P(A ∩ B) = pA pB + ρ √[pA(1−pA)pB(1−pB)]. Require max(0,pA+pB−1) ≤ joint ≤ min(pA,pB).','Nondegenerate binary legs only, no pushes/voids. Even ρ in [−1,1] may be infeasible. Pairwise correlations do not identify a 3+ leg joint distribution.'],'Derived identity',['SCI-RHO']),
(['General combo pricing','EV = Σₛ P(state s) × gross payout multiplier(s) − 1, including repriced/voided/partial settlements as explicitly defined by the operator.','Cannot infer actual same-game payout from marginal prices. No universal SGP settlement adapter is included.'],'Project specification',['DK-GENERAL','DK-MARKET']),
(['Brier and log loss','Brier = mean[(p−y)²]. Log loss = −mean[y log p + (1−y) log(1−p)]. Lower is better; compare on exactly matched rows.','Impossible exact predictions receive infinite loss in the utility; no undocumented probability clipping. Calibration curves remain necessary.'],'Method definition',['SK-SCORE','SK-CAL'])])
content += table('correlations','Correlation protocol & withheld estimates',['Pair / outcome definition','Estimator / sampling unit','N','ρ','95% interval','State'],[
(['QB passing over / receiver yards over','Phi on exact binary settled thresholds; cluster by game/week as predeclared.',None,None,None,'No verified pairs'],'Unverified',['NFL-STATS','SCI-RHO']),
(['Home cover / rushing yards over','Phi on exact quoted thresholds; no assumed positive or negative sign.',None,None,None,'No verified pairs'],'Unverified',['NFL-SCORES','SCI-RHO']),
(['Two different games / same week','Aligned ticket-level binary legs, shared-week blocks; test residual dependence and joint calibration.',None,None,None,'No verified pairs'],'Unverified',['SCI-RHO','SK-CAL'])])
content += '''<h2>How the utility estimates dependence</h2><p>Align both legs by exact game, player, market, threshold, forecast window and settlement convention. Never encode missing, push or void as a loss. Publish every exclusion and avoid survivor-only samples. Compute Pearson correlation on binary outcomes (phi); constant outcomes produce an undefined value, not zero. Pooling thresholds can confound the estimate, so predeclare homogeneous pair definitions or condition on the forecast.</p><p><code>analysis/core.py</code> includes a deterministic 95% percentile cluster bootstrap. It resamples whole declared clusters, not individual correlated bets. The exploratory minimum of 30 clusters and 2,000 replicates are project defaults, not guarantees of coverage or statistical power. A constant resample withholds the interval instead of dropping inconvenient replicates. Dependence between clusters requires larger time blocks or a different valid method. No real-data correlation report has been run.</p><h2>Implementation boundary</h2><p>Implemented: settlement-aware math, score-PMF integration, two-leg feasibility checks, phi, cluster resampling, binary scoring, Holm adjustment and structural timestamp checks. Not implemented: licensed ingestion, fitted score/player model, independent semantic source reconciliation, valid hypothesis-test generation, sealed backtest, general SGP settlement engine or automated wagering. Tests use synthetic fixtures only; they are not research findings.</p><p class="reading"><a href="https://github.com/sassnarep3-star/Own9/blob/main/strict-lab/analysis/core.py">Review mathematical code ↗</a> · <a href="research/policy.json">Policy JSON</a></p>'''
pages['methodology.html'] = ('Pricing & correlation','Pricing & dependence',content)

# Validation
source_gates = [['NFL-SCORES','DK-GENERAL'],['NFL-INJ','SK-TIME'],['SK-TIME'],['SCI-BOOT','SK-CAL'],['SK-SCORE','SCI-BOOT'],['DK-MARKET','NIST-TAIL'],['SM-HOLM','SCI-RHO'],['SK-TIME','SK-SCORE']]
content = '<h1>Validation gates</h1><p class="lead">Eligibility is earned by evidence, not assigned by a high hit rate. Every gate is currently blocked.</p>'
content += note('<strong>Fail closed.</strong> The readiness runner checks structure only and deliberately cannot promote a strategy, even if records are later added. Independent provenance, model and experiment review must exist before any pass. Build success is not scientific validation.')
content += table('gates','Proposed promotion policy',['Gate','Evidence required','Result'],[
([g['id']+' · '+g['name'],g['requirement'],'Blocked · no independent evidence'],'Proposed policy',source_gates[i]) for i,g in enumerate(POLICY['gates'])])
content += table('data-contract','Point-in-time data contract',['Field group','Required content','Fail condition'],[
(['Identity','Unique prediction/ticket ID, game ID, strategy version, player IDs and exact line/leg IDs; settlement convention and market track.','Duplicates, mismatched lines or missing identifiers.'],'Project specification',['NFL-SCORES','DK-MARKET']),
(['Information timing','feature_available_at ≤ forecast_at; quote_at ≤ forecast_at < kickoff_at < outcome_at; timezone-aware ISO 8601 timestamps.','Missing timestamps, future features, or predictions recorded after kickoff. Quote staleness limits must be preregistered.'],'Project specification',['SK-TIME']),
(['Source artifacts','Official outcome URL, operator quote and rules URLs, original response snapshots, SHA-256 hashes, revision history and independent semantic reconciliation.','A URL/hash alone is not verification. Source or usage rights not established.'],'Project specification',['NFL-STATS','DK-GENERAL']),
(['Prices and settlement','Exact offered decimal payout, stake/limit availability, cost model and every leg settlement including push, void and repricing.','Unavailable quote, inferred combo payout, undocumented settlement or altered quote.'],'Project specification',['DK-MARKET','DK-GENERAL']),
(['Frozen evaluation','Training cutoff, validation/test week IDs, code and model hashes, all trials, probability outputs, raw scores, baseline and dependence-aware uncertainty.','Reused test set, cherry-picked variants, unsupported confidence bounds or omitted failures.'],'Project specification',['SK-TIME','SM-HOLM'])])
content += '<h2>Stopping and drift</h2><p>Specify observation horizon, effect size, power, alpha allocation, minimum opportunity coverage, calibration tolerance, price-delay stress and maximum exposure before testing. These strategy-specific numerical limits are not yet selected or validated. Do not stop early when results look attractive. A missing feature, stale quote, failed reconciliation, changed settlement rule or unsupported market suspends the strategy. Recalibration requires a new version and a fresh untouched evaluation.</p>'
pages['validation.html'] = ('Validation gates','Validation gates',content)

# Leaderboard
content = '<h1>Research leaderboard</h1><p class="lead">A competition design for reproducible forecasting. No eligible strategy, measured rank or funded prize exists.</p>'
content += note('<strong>No winners declared.</strong> All eight entries are unranked. Empty cells are unavailable—not zero performance, zero correlation or a zero-dollar reward.')
content += table('leaderboard','Unranked candidate entries',['Rank','Strategy / track','Gate status','Test N','Log loss','ROI','ρ','Reward'],[
([s['rank'],f'{s["id"]} · {s["name"]} / {s["track"]}','0 of 8 passed',s['n'],s['log_loss'],s['roi'],s['rho'],s['reward']], 'No evaluation', ['SK-SCORE','SCI-RHO']) for s in RUN['strategies']])
content += table('competition','Proposed competition rules',['Rule','Policy'],[
(['Registration','Freeze version, feature list, complete family of variants, market track, opportunity universe, coverage requirement and prediction deadline before results. Include every registered candidate, including failures.'],'Project proposal',['SK-TIME','SM-HOLM']),
(['Matched tracks','Separate game singles, player props, cross-game parlays and same-game combos. Score against the same market/line/time baseline on matched tickets; do not compare raw log loss across different event difficulties.'],'Project proposal',['SK-SCORE']),
(['Ranking','Only all-gate passers can rank. Within each matched track, rank by the 95% cluster-bootstrap lower confidence bound of mean(baseline log loss − strategy log loss). Publish point estimate, interval, coverage, calibration, economic results and all exclusions.'],'Project proposal',['SK-SCORE','SCI-BOOT']),
(['Ties and safeguards','Predeclare numerical tie tolerance; tied intervals receive shared rank, not an arbitrary winner. No reward for wager volume, leverage or a favorable short-term return alone. Independent reproduction required.'],'Project proposal',['SK-SCORE','UKGC']),
(['Rewards',POLICY['reward_policy']],'Project proposal',['GH-PAGES','SK-SCORE'])])
pages['leaderboard.html'] = ('Leaderboard','Research leaderboard',content)

# Sources
content = '<h1>Evidence library</h1><p class="lead">Official league, operator, regulator and maintainer references. Checked 04 November 2026; coverage is limited to the sections described below.</p>'
content += note('<strong>What “checked” means:</strong> retrieved and inspected the cited section, including soft-404 checks. It does not mean the whole document, every linked page, a historical dataset or a strategy result has been verified. Official software documentation is not official NFL data. Dynamic pages may change.')
content += table('sources','Source-by-source verification ledger',['ID / publisher','Authority','Document / inspected excerpt','Coverage and limitations','Checked'],[
([s['id']+' · '+s['publisher'],s['kind'],s['title']+' — “'+s['excerpt']+'”',s['scope'],s['checked_at']],s['status'],[s['id']]) for s in CAT['sources']])
content += '<h2>Evidence policy</h2><p>Observed values require an exact official record and independently reconciled snapshot. Proposed models and mathematical derivations are labeled as such; references provide only their stated context. Unknown observed values remain blank. League pages are not odds feeds. An HTTP 200 response is not enough: the rejected injury-policy URL returned an NFL 404 document. A known-bad URL is recorded as text on the review page rather than presented as a verified source.</p><p class="reading"><a href="research/catalog.json" download>↓ Full evidence catalog (JSON)</a> · <a href="research/run.json" download>↓ Readiness report (JSON)</a></p>'
pages['sources.html'] = ('Evidence library','Evidence library',content)

# Requirements
content = '<h1>Requirements & audit</h1><p class="lead">Delivery, scientific readiness and unresolved evidence are separate states. A live site does not imply a validated betting system.</p>'
content += table('requirements','Requirement-by-requirement delivery',['ID','Requirement','Delivery / limitation','Status'],[
([r['id'],r['requirement'],r['delivery'],r['status']],'Project audit',r['sources']) for r in CAT['requirements']])
content += table('repo-audit','Repository review by file scope',['Scope','Finding / verification','Limit'],[
(['Initial checkout','Only README.md (# Own9). After full-history fetch, main contained PR #1 dashboard, generator, checker and coordination log. Existing work was retained.','This is a local Git observation; platform reference is context, not external proof.'],'Repository observation',['GH-PAGES']),
(['Inherited tools/build.py','Generic contextual links were attached to proposals; NIST case-study scope mismatch was identified. Reworked into a structured catalog with explicit evidence labels.','A citation attached to a row never proves all of its claims.'],'Code review',['SK-SCORE']),
(['Inherited tools/check.py','Checked source hostname presence and local anchor filenames only, with a hardcoded five-page count. Replaced with schema, citation, fragment, asset, empty-value and deterministic build checks.','Static checks do not verify source truth or scientific adequacy.'],'Code review',['GH-PAGES']),
(['analysis/core.py + tests','Reviewed mathematical and boundary behavior; synthetic unit tests cover signs, refunds, feasibility, missingness, constant correlation, chronology and invalid inputs.','No trained model or real-data backtest in this lab; full SGP settlement engine not provided.'],'Code review',['SCI-RHO','SK-SCORE']),
(['research/*.json','Source scopes, candidate proposals, policy, empty observations and fail-closed readiness report separated. No actual NFL performance numbers are seeded.','No record is treated as independently verified on the basis of metadata alone.'],'Artifact review',['NFL-STATS','DK-GENERAL']),
(['Pages & automation','Lab build/check/test/readiness commands run without secrets or manual input. Existing main publishing is preserved; no lab-specific scheduled workflow is installed.','Root integration owners control site navigation, workflows and packaging. Lab scheduling is a documented integration request.'],'Implementation',['GH-PAGES'])])
content += '<p class="reading"><a href="https://github.com/sassnarep3-star/Own9/blob/main/COORDINATION.md">Coordination log & PR record ↗</a> · <a href="https://github.com/sassnarep3-star/Own9/actions">Build and deployment evidence ↗</a></p>'
pages['requirements.html'] = ('Requirements & audit','Requirements & audit',content)

# Review
content = '<h1>Flagged for Review</h1><p class="lead">Known limitations, evidence gaps and irregularities. Published transparently; these do not block delivery of the research site.</p>'
content += note('<strong>Unverified means withheld.</strong> There is no recommendation to place a bet. No claim of guaranteed profit, removed luck, legal eligibility, real reward funding or completed empirical validation is made.', 'notice amber')
content += '<p class="reading"><a href="../release-checks/index.html">Independent release-quality baseline →</a> · <a href="../index.html">Main repository site →</a></p><p>This section is an isolated strict-source research proposal, not a certification of other sessions’ exploratory datasets or root-site models. The independent release report is a dated baseline, not a check of this newer section.</p>'
content += table('flags','Open review register',['ID / item','Finding','Handling / next evidence','State'],[
([f['id']+' · '+f['item'],f['finding'],f['resolution'],f['status']],'Flagged finding',f['sources']) for f in CAT['flags']])
pages['flags.html'] = ('Flagged for Review','Flagged for Review',content)

nav_icons = ['◫','⌁','∑','◇','≡','⊞','✓','!']
for filename, (label,title,content) in pages.items():
    nav = ''.join(f'<a href="{href}"'+(' aria-current="page"' if href==filename else '')+f'><span aria-hidden="true">{icon}</span>{e(data[0])}</a>' for (href,data),icon in zip(pages.items(),nav_icons))
    search = '' if filename=='index.html' else '<div class="toolbar"><label for="table-search">Search this page</label><input type="search" id="table-search" placeholder="Filter entries…" autocomplete="off"><span>All rows shown without JavaScript</span></div>'
    (ROOT/filename).write_text(f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="description" content="Own9 NFL research: source-linked strategy proposals, pricing methods, fail-closed validation and transparent evidence gaps."><title>{e(title)} · Own9 NFL Lab</title><link rel="stylesheet" href="style.css"><script src="app.js" defer></script></head><body>
<a class="skip" href="#main-content">Skip to content</a><aside class="sidebar"><a class="brand" href="index.html"><span>O9</span><div>OWN9<small>NFL RESEARCH LAB</small></div></a><p class="nav-label">WORKSPACE</p><nav aria-label="Main navigation">{nav}</nav><div class="sidebar-note"><span class="status-dot"></span> Evidence over assumptions<p>Research proposals only.<br>No wagering or profit promises.</p><a href="https://github.com/sassnarep3-star/Own9">View repository ↗</a></div></aside>
<div class="workspace"><header class="masthead"><span>NFL LAB <b>/ {e(label)}</b></span><span class="review-date">Evidence review · 04 Nov 2026 <i>RESEARCH ONLY</i></span></header><main id="main-content"><div class="eyebrow">WORKSPACE / {e(label.upper())}</div>{search}{content}</main><footer><span>OWN9 / NFL RESEARCH</span><span>Blank values = unverified · No strategy has passed validation</span></footer></div></body></html>''')

summary = '''# Own9 NFL Lab — Executive summary

Evidence review: 2026-11-04 UTC.

## Decision
Do not deploy capital. This is a research framework with tested mathematical
utilities, not a verified NFL pricing model or profitable betting system. Luck
cannot be removed. No independently verified point-in-time market dataset,
trained model, measured correlation, sealed backtest or funded reward exists in
this strict-source lab. Other sessions’ exploratory work is outside its scope.

## Research design
Eight candidate designs cover opponent-adjusted game lines, availability,
schedule/rest, player volume × efficiency, role changes, cross-game parlays,
QB/receiver combinations and game-script/player combinations. Each has official
input requirements and falsification tests. These are hypotheses, not facts.

## Validation and competition
All eight evidence gates must pass: provenance, information timing, chronological
holdout, power/calibration, predictive improvement, economic robustness,
multiple-testing/dependence controls and prospective replication. Within matched
market tracks, proposed ranking uses a lower confidence bound on improvement in
proper forecast loss against contemporaneous market prices. Rewards are proposed
noncash recognition only, with no funded program or winners.

## What works today
Static dashboard; source-linked tables and CSV exports; score-PMF price
integration; refund-aware EV; two-leg joint feasibility; phi and cluster bootstrap;
Brier/log loss; Holm adjustment; timestamp checks; fail-closed readiness report;
synthetic unit tests; deterministic build and local-link checks. Root integration
owners control automated publication; no lab-specific workflow is installed.

## Evidence boundary
Official NFL pages establish potential input fields, not sportsbook prices or
historical quote availability. Official maintainer docs establish statistical
method definitions, not NFL edges. DraftKings rules inspected include a Virginia
scope and must not be generalized to Washington or any other jurisdiction.
The inherited NIST heat-flow citation was overly broad; a candidate NFL injury
policy URL soft-404ed. Both are recorded on Flagged for Review. Actual unknown
values are null/blank, never estimated and presented as observations.

## Manual-review source links
'''
summary += '\n'.join(f'- {s["id"]}: {s["url"]}\n  Scope: {s["scope"]}' for s in CAT['sources'])+'\n\nSee sources.html, flags.html and research/catalog.json for the full ledger.\n'
(DOWNLOADS/'executive-summary.md').write_text(summary)
print(f'Built {len(pages)} pages and {len(list(DOWNLOADS.glob("*.csv")))} source-linked CSV tables.')
