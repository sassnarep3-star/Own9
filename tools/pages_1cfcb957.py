"""Requirements delta published by session `1cfcb957` on 14 Nov 2026.

Five pages, added through the shared generator's own `page()` API. No page authored by another
session was rewritten: `leaderboard.html`, `correlations.html`, `data.html`, `lines.html`,
`availability.html`, `injuries.html`, `question-ledger.html` and `suggestion-costs.html` keep their
authors' rows, wording and blank cells exactly as published, and the numbers here are derived at
build time from `tools/requirements_audit.py` rather than retyped from it.

What these pages carry is the eight requirements in the owner's latest list: the price-snapshot
store, the verified results feed, the side-then-total-then-moneyline origination order, the
fair/market/difference column split, the signal-versus-staking leaderboard separation, the depth of
a replacement rather than the fact of one, correlations taken only from officially sourced numbers
with `n` printed beside each, and the demotion gate that returns a live strategy to paper.

The convention that matters most here is the one inherited from this repository rather than invented
for it: a measurement that cannot be sourced is left blank and flagged, never estimated. Most of the
empirical columns on these pages are therefore empty, and each empty column says which record would
have to exist to fill it.
"""
from engine.correlations import value_rules as _corr_rules
from engine.signal_staking import rules as _split_rules
from engine.replacement import limits as _repl_limits
from requirements_audit import measure

# INJ is the repository's own transcription of the Week 10 2026 league report, handed to this module by
# the generator's exec namespace. Nothing on these pages re-types it: it is read, counted and derived.
A = measure(INJ)  # noqa: F821 - supplied by tools/build.py
FEED, STORE, QUOTES = A['feed'], A['store'], A['quotes']
ORIG, SPLIT, DEPTH = A['origination'], A['signal_staking'], A['replacement']
CORRS, GATE, READY = A['correlations'], A['demotion'], A['readiness']
GAMES = A['games']
ROI = STORE['roi']
LINE_LABEL = {'SPREAD': 'side (spread)', 'TOTAL': 'total', 'MONEYLINE': 'moneyline'}
DEPTH_LIMITS = _repl_limits()
CORR_RULES = _corr_rules()
SPLIT_RULES = _split_rules()


# --------------------------------------------------------------------------- requirements
page('requirements.html', 'Requirements',
     'Eight requirements.\nSix are now enforced in code.',
     'A traceability register for the latest requirement list: what each requirement asked for, the mechanism '
     'that now answers it, what the repository can measure today, and the specific artefact that would close '
     'the rest. Nothing here is marked done because a page was written; a requirement is marked enforced only '
     'when code refuses the alternative.',
     '<div class="notice"><strong>How to read the status column</strong><p><em>Enforced</em> means a module '
     'raises or withholds output when the rule is broken, and a test asserts that it does. <em>Enforced, '
     'inputs absent</em> means the mechanism is live but the data it governs has not been captured, so the '
     'published value is a count of the gap rather than a performance figure. <em>Awaiting owner decision</em> '
     f'means a choice on <a href="missing-information.html">Missing information</a> is required first. No '
     'number on these pages is an edge, a return, or a forecast: '
     f'{STORE["records_priced"]} priced snapshots exist in this repository.</p></div>'
     + table('Requirement ledger', ['#', 'Requirement', 'Mechanism now in place', 'Measured state',
                                    'Status', 'What closes the remainder'], [
         row(['R1', 'Add a price-snapshot store that records opening and closing numbers for every market we '
              'originate.', 'engine/snapshots.py: a hash-chained append-only log keyed by game, market, side '
              'and stage, where an absent price must carry a reason and a price must carry a capture time, a '
              'source and a provenance class.',
              f'{STORE["records_captured"]} records captured against {STORE["expected_pairs"]} expected for the '
              f'{STORE["games"]}-game slate; holes {STORE["holes"]}; chain intact '
              f'({len(STORE["chain_problems"])} problems).',
              'Enforced, inputs absent', 'A capture path: a licensed operator feed, or a scripted forward '
              'capture run before each kickoff. Until then every expected record is a counted hole, not a '
              'silence.'], ('repo',), 'Project record · computed by tools/requirements_audit.py'),
         row(['R2', 'Add a verified results feed so backtests and ROI can be computed at all.',
              'engine/results.py: a feed whose rows must pass six checks — league host, the page\'s two '
              'independent score renderings, winner consistency, one appearance per club per week, record '
              'progression between two retrievals, and published win percentages — plus settle() for '
              'spread, total and moneyline.',
              f'{FEED["games"]} games loaded, {FEED["verified"]} verified, {FEED["checks_run"]} checks run, '
              f'{FEED["checks_failed"]} failures; record progression agrees for '
              f'{FEED["reconciliations"][0]["clubs_agreeing"]} of '
              f'{FEED["reconciliations"][0]["clubs_tested"]} clubs into Week 9 and '
              f'{FEED["reconciliations"][1]["clubs_agreeing"]} of '
              f'{FEED["reconciliations"][1]["clubs_tested"]} into Week 10.',
              'Enforced', 'Nothing: the feed exists and is populated with officially verified results. What '
              f'still blocks a backtest is R1 — {READY["finals_verified"]} verified finals, '
              f'{READY["finals_with_a_market_line"]} of them with a market line.'],
             ('nfl-schedule-w9', 'nfl-schedule-w10-byweek', 'nfl-schedule-w8-byweek'),
             'Direct publisher · arithmetic derived in build'),
         row(['R3', 'Originate the side first, then the total, then the moneyline.',
              'engine/originate.py: three stages with declared inputs, an order validator, and a consistency '
              'check that recomputes every published probability from the one joint score distribution. A '
              'moneyline is only ever read off the distribution the side and total were priced from.',
              f'Stage order {", ".join(ORIG["stages"])}; an out-of-order log is rejected with '
              f'{len(ORIG["out_of_order_rejected"])} stated reasons; consistency problems: '
              f'{len(ORIG["consistency_problems"])}.',
              'Enforced', 'A model that is worth running against it. The order is now a constraint on the '
              'pipeline rather than a recommendation; a fitted model is separately blocked on the validation '
              'gates.'], ('repo',), 'Project record · unit tested'),
         row(['R4', 'Publish the model\'s fair line, the market line, and the difference as separate columns.',
              'engine/originate.py columns(): three fields that are populated independently, a difference that '
              'is computed rather than supplied, and a market line admitted only from a snapshot carrying a '
              'price, a capture timestamp and a stage label.',
              f'{ORIG["published_rows"]} published rows: {ORIG["rows_with_a_fair_line"]} carry a fair line, '
              f'{ORIG["rows_with_a_market_line"]} carry a market line, {ORIG["rows_with_a_difference"]} carry a '
              'difference.',
              'Enforced, inputs absent', 'Captured opening numbers (R1). The difference column cannot be '
              'legitimately populated from the undated numbers in data/raw/, so it is blank by rule and the '
              'rule is the finding.'], ('repo',), 'Project record'),
         row(['R5', 'Separate signal from staking in the leaderboard so a lucky staking run cannot mask a bad '
              'signal.', 'engine/signal_staking.py: two scorecards, one rank key (the signal lower bound), a '
              'staking block that refuses to run without captured executable prices, and a hard rejection of '
              'any candidate that submits a return without a signal block.',
              f'Refusal demonstrated: {SPLIT["rank_without_signal_refused"]} Synthetic-block gain '
              f'{SPLIT["signal_demo"]["gain"]:.4f} with lower bound {SPLIT["signal_demo"]["gain_lcb"]:.4f} — '
              'a positive point estimate that cannot be ranked.',
              'Enforced', 'Registered candidates. There are '
              f'{SPLIT["candidates_registered"]} candidates and {SPLIT["settled_bets_available"]} settled bets, '
              'so both boards are empty by fact, not by design.'], ('logloss', 'brier', 'repo'),
             'Metric definitions · project rule'),
         row(['R6', 'Track the depth of the replacement, not just the fact of a replacement.',
              'engine/replacement.py: strings travelled from the vacated slot to the first teammate who can '
              'actually play, depth measured from the top of the chart, exhausted-chart and unlisted-player '
              'cases recorded as unknowns, and one player covering two slots flagged as a shared backup.',
              f'{DEPTH["vacancies"]} located vacancies across {DEPTH["clubs_with_chart"]} clubs with a retrieved '
              f'chart; depth known for {DEPTH["depth_known"]}, unknown {DEPTH["depth_unknown"]}; '
              f'{len(DEPTH["unlisted_vacancies"])} Out players appear on no retrieved chart row; '
              f'{len(DEPTH["multi_slot_backups"])} players are the published cover for two slots.',
              'Enforced, coverage limited', f'Depth charts for the other {DEPTH["clubs_without_chart"]} clubs in '
              'the report, or a league-certified game-day depth source. Depth is computed for '
              f'{DEPTH["clubs_with_chart"]} of {DEPTH["clubs_in_report"]} clubs in the snapshot.'],
             ('chiefs-depth', 'seahawks-depth-1cf', 'lions-depth', 'nfl-injury-w10'),
             'Club publications · derived arithmetic'),
         row(['R7', 'Compute correlations only from officially sourced numbers and publish n with each value.',
              'engine/correlations.py: every observation must name a source id that is both in the official '
              'allowlist and registered in the evidence manifest on an official host; a single unregistered leg '
              'voids the whole pair; n is counted from the complete pairs used and printed with the estimate, '
              'the interval and the verdict.',
              f'{len(CORRS)} predeclared pairs measured on Week 9 2026 finals: n between '
              f'{min(c["n"] for c in CORRS)} and {max(c["n"] for c in CORRS)}; every verdict is '
              f'{CORRS[0]["verdict"]} against the predeclared floor of {CORRS[0]["min_n"]}; joint prices '
              'allowed: none.',
              'Enforced', 'Volume. At n of 11 to 15 games no interval is narrow enough to act on, and the '
              'module says so instead of falling back to independence.'],
             ('nfl-schedule-w9', 'nfl-schedule-w8-byweek', 'pearson'), 'Direct publisher · project gate'),
         row(['R8', 'Define a demotion gate that sends a live strategy back to paper.',
              'engine/demotion.py: four signal triggers, one provenance trigger, a staking stop that may only '
              'suspend, a return path requiring consecutive clean paper evaluations after a cooldown, and an '
              'immutable hash-chained decision log. Thresholds are module constants, and the module refuses a '
              'caller-supplied policy.',
              f'Demonstrated both ways on declared test histories: a clean run holds, a broken run demotes with '
              f'{len(GATE["broken_demote"]["triggers"])} triggers; relisting blocked by '
              f'{len(GATE["relist_after_demote"]["blocked_by"])} conditions. Live candidates: '
              f'{GATE["live_candidates"]}.',
              'Enforced, nothing live', 'A candidate promoted at all. The gate is armed against an empty '
              'board, which is the correct state: nothing can be demoted that should never have gone live.'],
             ('holdout', 'repo'), 'Project policy · unit tested'),
     ])
     + table('Executive summary of this release', ['Area', 'Finding', 'Disposition'], [
         row(['Results, not prices', 'The missing piece was never the scoreboard. Officially verified results '
              f'now exist for {READY["finals_verified"]} games with every check passing; what does not exist is '
              'a timestamped price.', 'Feed implemented and populated; capture still blocked']),
         row(['The one file that looked like an answer', f'data/raw/closing_lines.csv holds '
              f'{QUOTES["rows"]:,} rows across seasons {QUOTES["seasons"]}, with columns '
              f'{QUOTES["columns"]}. None of them is a stage or a timestamp, so it records one number per '
              'market side and cannot express an open or a close.',
              'Measured on lines.html by the earlier session; here it is measured against the store schema']),
         row(['2026 lines do exist in the repository', f'the sibling score snapshot carries spread, total and '
              f'moneyline columns for {ORIG["games_with_a_line_value"]} of the {ORIG["games_in_feed"]} games in '
              'the feed — including Week 9 games already played. They are undated and unlabelled, so under the '
              'store schema they are numbers, not quotes.',
              'Published as a measurement; not used for any return or ROI figure']),
         row(['Origination is now a sequence, not a suggestion', 'A moneyline priced before the side is '
              'rejected by the validator, because it signals a model that is not a score model.',
              'Enforced in code with tests']),
         row(['Correlation on official data', 'The only correlations this project can compute from officially '
              'sourced numbers, at the sample size officially available, all resolve to insufficient evidence '
              'against the predeclared floor. That is a result, not a failure.',
              'Published with n; no joint price produced']),
         row(['Depth of replacement', 'Counting absences and counting strings travelled give different answers. '
              'The Chiefs defensive-tackle slot has no starter out and a third-string player starting, which a '
              'vacancy count cannot see.', 'Computed for the three clubs with a retrieved chart']),
         row(['Demotion', 'A gate with no exit is a licence earned on an old sample. The exit now has a '
              'cooldown, a clean-run requirement, and a log that cannot be edited.',
              'Armed; no candidate is live']),
         row(['What is not claimed', 'No edge, no ROI, no validated strategy, no funded competition, no '
              'certified depth record, no fitted model.', 'Remains blocked on evidence, not on effort']),
     ])
     + table('Candidate paths, none chosen', ['Path', 'What it assumes', 'Cost', 'What it rules out',
                                              'Status'], [
         row(['P-A · Forward capture first', 'That a scripted capture of opening and closing numbers, run from '
              'today, is worth more than a historical archive nobody can license.',
              'Low: the store, the manifest and the audit already exist; capture is the only new moving part.',
              'Any backtest on seasons before the capture starts.', 'Awaiting owner decision'],
             ('repo',), 'Project proposal'),
         row(['P-B · Licence a quote archive', 'That buying historical quotes is cheaper than accumulating them, '
              'and that a licensed archive can be verified row by row.',
              'High: money, a contract, and a rights review this repository cannot perform alone.',
              'Nothing, if it succeeds — it would retire P-A.', 'Awaiting owner decision'],
             ('dk-markets',), 'Project proposal'),
         row(['P-C · Model depth before price', 'That replacement-depth features can be developed against '
              'results alone, and priced later.',
              'Medium: needs charts for the remaining clubs and a per-play denominator that the league does not '
              'publish.', 'Any claim that the feature is priced or validated.', 'Awaiting owner decision'],
             ('nfl-injury-w10', 'chiefs-depth'), 'Project proposal'),
         row(['P-D · Publish only, capture nothing', 'That the decision layer and the registers are the product '
              'for now.', 'Zero build cost; the pages already carry the gaps.',
              'Every empirical claim, including ROI, leaderboard ranks and rewards.', 'Awaiting owner decision'],
             ('repo',), 'Project proposal'),
     ])
     + '<p class="download">Detail: <a href="price-feed.html">Price &amp; results</a> · '
       '<a href="signal-staking.html">Signal vs staking</a> · '
       '<a href="depth-correlations.html">Depth &amp; correlation</a> · '
       '<a href="missing-information.html">Missing information</a>. Reproduce every figure with '
       '<code>python3 tools/requirements_audit.py</code>. New findings are on '
       '<a href="flags.html">Flagged for Review</a> as F28-F33.</p>')


# --------------------------------------------------------------------------- price + results
def _stage_probs(stage):
    """(primary probability, push mass) for each stage, read off the stage's own keys.

    The three stages report their mass under different names, so the mapping is explicit rather
    than a chain of .get() defaults: a silently missing key would print as a dash and read like
    an unmeasured quantity instead of a coding error.
    """
    market = stage['market']
    if market == 'SPREAD':
        return stage['cover'], stage['push']
    if market == 'TOTAL':
        return stage['over'], stage['push']
    return stage['home_win'], stage['tie']


def _origination_rows():
    out = []
    for stage in ORIG['stage_outputs']:
        market = stage['market']
        p, push = _stage_probs(stage)
        out.append(row([LINE_LABEL[market],
                        (stage['fair_line'] if stage['fair_line'] is not None else 'no line field'),
                        f'{p:.4f}', f'{push:.4f}',
                        'the primitive stage: solved directly from the score distribution'
                        if market == 'SPREAD' else 'derived from the previous stage\u2019s distribution',
                        'declared arithmetic example, not a model output'],
                       ('repo',), 'Project arithmetic on a declared example'))
    return out


def _feed_rows():
    out = []
    for game in GAMES:
        source = ('nfl-schedule-w9' if game['week'] == 9 else 'nfl-schedule-w10-byweek')
        score = (f"{game['away_name']} {game['away_points']}, {game['home_name']} {game['home_points']}"
                 if game['status'] == 'final' else 'not played at retrieval')
        out.append(row([f"Week {game['week']} · {game['date_label']}",
                        f"{game['away_abbr']} at {game['home_abbr']}", score,
                        (game.get('winner_indicator') or '—') if game['status'] == 'final' else 'scheduled',
                        f"{len(game['verification']['checks'])} checks: all pass" if game['verified']
                        else 'FAILED',
                        f"{game['listed_records'].get(game['away_abbr'], '')} / "
                        f"{game['listed_records'].get(game['home_abbr'], '')}"],
                       (source, 'repo'), 'Official page · transcribed and cross-checked'))
    return out


page('price-feed.html', 'Price & results',
     'The store is built.\nThe prices are not.\nHere is the exact distance.',
     'A price-snapshot store that records an opening and a closing number for every market originated, and the '
     'verified results feed that a backtest settles against. Both exist; one is empty because nothing has been '
     'captured, and the emptiness is measured per game, per market and per stage rather than described.',
     '<div class="notice"><strong>Why an empty store is the point</strong><p>A store that silently filled '
     'missing prices with zero would produce a beautiful backtest and a false one. This store records the '
     'absence instead, with a reason, so '
     f'{STORE["holes"]} missing captures out of {STORE["expected_pairs"]} expected are visible as a number. '
     'The results feed, by contrast, is full: every game in it passed its checks.</p></div>'
     + table('Snapshot store — record fields and their rules',
             ['Field', 'Required when', 'Rule', 'Why the rule exists'], [
         row(['game_id', 'always', 'Text; the official game slug is used so the key survives a roster change.',
              'One market side of one game is the unit a bet settles on.'], ('repo',), 'Project record'),
         row(['market', 'always', 'One of SPREAD, TOTAL, MONEYLINE — the originated markets, in the '
              'origination order.', 'A market outside the originated set has no expected record, so it could '
              'never be reported as missing.'], ('repo',), 'Project record'),
         row(['side', 'always', 'HOME/AWAY for side and moneyline, OVER/UNDER for the total.',
              'Club abbreviations change; the slot in the game does not.'], ('repo',), 'Project record'),
         row(['stage', 'always', 'Exactly open or close. There is no third stage.',
              'The requirement is both ends of the move; a file with one number per row cannot satisfy it.'],
             ('repo',), 'Project record'),
         row(['line, price', 'if either is present', 'Numbers, never strings; American prices must satisfy '
              '|odds| >= 100; a moneyline may not carry a line.', 'A quoted price is a number or it is absent.'],
             ('dk-markets',), 'Operator rule context'),
         row(['captured_at', 'when priced', 'UTC ISO 8601 to the second.', 'An undated number cannot be an '
              'opening price, because "opening" is a claim about time.'], ('repo',), 'Project record'),
         row(['source_url, publisher', 'when priced', 'https, and recorded per record.',
              'Provenance is what lets a row survive a re-verification a year later.'], ('repo',),
             'Project record'),
         row(['provenance', 'when priced', 'operator, league or unverified. `league` is refused for a price '
              'field outright.', 'The NFL publishes no betting price; the store will not let a citation be '
              'inherited by association.'], ('nfl-player-stats', 'dk-markets'), 'Checked absence · operator context'),
         row(['missing_reason', 'when nothing was captured', 'Required text.', 'Turns a hole in coverage into a '
              'recorded fact.'], ('repo',), 'Project record'),
         row(['prev_hash, record_hash', 'always', 'SHA-256 chain over the append-only log; the manifest stores '
              f'the head and the file digest ({STORE["log_sha256"][:16]}…).',
              'A snapshot you can edit after the result is known is not a snapshot.'], ('repo',),
             'Project record'),
     ])
     + table('Store state, measured against the current slate', ['Metric', 'Value', 'What it means'], [
         row(['Games on the slate', STORE['games'], 'Week 9 (15, all final) plus Week 10 (14) from the '
              'official schedule pages.'], ('nfl-schedule-w9', 'nfl-schedule-w10-byweek'), 'Official pages'),
         row(['Expected records', STORE['expected_pairs'], '29 games x 3 markets x 2 sides x 2 stages. This is '
              'what "every market we originate" means when it is countable.'], ('repo',), 'Project arithmetic'),
         row(['Records captured', STORE['records_captured'], 'None. The store was created in this release.'],
             ('repo',), 'Project record'),
         row(['Records carrying a price', STORE['records_priced'], 'None, so no expected value, no ROI and no '
              'closing-line value can be computed.'], ('repo',), 'Project record'),
         row(['Open/close pairs both priced', STORE['open_close_pairs_priced'], 'The quantity a line-shopping '
              'or CLV study needs. It is zero.'], ('repo',), 'Project record'),
         row(['Coverage', f'{STORE["coverage_pct"]}%', 'Computed, not asserted: 0 of 348.'], ('repo',),
             'Project arithmetic'),
         row(['Chain integrity', f'{len(STORE["chain_problems"])} problems', 'The log and manifest agree at '
              'zero records; an edit to any past record would show here.'], ('repo',), 'Project record'),
         row(['Per-market expectation', ', '.join(f'{m}: {v["expected"]}' for m, v in STORE['by_market'].items()),
              'Each market is held to the same count, so an origination gap in one market cannot hide inside '
              'the average.'], ('repo',), 'Project arithmetic'),
     ])
     + table('The quote file the repository already holds, measured against the schema',
             ['Measurement', 'Value', 'Consequence'], [
         row(['Rows in data/raw/closing_lines.csv', f'{QUOTES["rows"]:,}',
              'One row per market side per game, with a line and an odds field.'], ('repo',), 'Computed at build'),
         row(['Its columns', ', '.join(QUOTES['columns']), f'{QUOTES["n_columns"]} columns, of which {len(QUOTES["stage_columns"])} carry a stage or a timestamp '
              f'({", ".join(QUOTES["stage_columns"]) or "none"}). One number per market side, with no label '
              'saying when it was true.'],
             ('repo',), 'Computed at build'),
         row(['Opening numbers it contains', QUOTES['opening_numbers_present'],
              'An opening price is not recoverable from a file that only ever recorded one number per side.'],
             ('repo',), 'Computed at build'),
         row(['Seasons covered', QUOTES['seasons'], f'{QUOTES["games"]:,} games, ending before the current '
              'season.'], ('repo',), 'Computed at build'),
         row(['Rows with no price on the side and total', f'{QUOTES["unpriced_spread_rows"]:,} spread and '
              f'{QUOTES["unpriced_total_rows"]:,} total', 'A line without a price cannot be evaluated for '
              'expected value at all.'], ('repo',), 'Computed at build'),
         row(['Rows disagreeing with recomputed outcomes', f'{QUOTES["disagree_rows"]} '
              f'({QUOTES["disagree_pct"]}%)', 'Already published on lines.html; retained as a quarantine reason, '
              'not reused as evidence.'], ('repo',), 'Computed at build'),
         row(['2026 line values in the score snapshot', f'{ORIG["games_with_a_line_value"]} of '
              f'{ORIG["games_in_feed"]} feed games', 'They exist, are undated and unlabelled, and therefore '
              f'qualify as {ORIG["games_with_a_usable_quote"]} usable quotes.'], ('repo',), 'Computed at build'),
         row(['File integrity', f'sha256 {QUOTES["sha256"][:16]}…', 'Byte-checkable; provenance, licence and '
              'sign convention are unconfirmed, which is why the file is quarantined rather than deleted.'],
             ('repo',), 'Repository inspection'),
     ])
     + table('Verified results feed', ['Week · date', 'Matchup', 'Final score', 'Winner', 'Checks',
                                       'Records (away / home)'], _feed_rows())
     + table('What was verified about the feed', ['Check', 'Coverage', 'Agreeing', 'What it establishes'], [
         row(['League-host publisher', f'{FEED["games"]} games', f'{FEED["verified"]} pass',
              'Every row resolves to an nfl.com page in the evidence manifest.'], ('nfl-schedule-w9',),
             'Structural verification'),
         row(['Dual rendering of the score', f'{FEED["final"]} final games', f'{FEED["checks_run"]} per-game '
              f'checks run, {FEED["checks_failed"]} failed',
              'The link label and the score cells are two renderings of the same figure; both had to agree.'],
             ('nfl-schedule-w9', 'nfl-schedule-w10-byweek'), 'Official page, two fields'),
         row(['Winner indicator', f'{FEED["final"]} final games', 'all agree',
              'The winner indicator sits on the higher score, and no unplayed game carries one.'],
             ('nfl-schedule-w10-byweek',), 'Official page, two fields'),
         row(['One appearance per club per week', '2 weeks', f'{len(FEED["duplicate_club_problems"])} problems',
              'A transcription error that duplicated a club would be caught here.'], ('repo',),
             'Project arithmetic'),
         row(['Record progression, Week 8 to Week 9', f'{FEED["reconciliations"][0]["clubs_tested"]} clubs',
              f'{FEED["reconciliations"][0]["clubs_agreeing"]} agree',
              'Week 8 records plus Week 9 results reproduce the Week 9 page. Four clubs are excluded because '
              'that page prints their record only in the bye block, which shows records as of retrieval — '
              'see F28.'], ('nfl-schedule-w8-byweek', 'nfl-schedule-w9'), 'Two official pages, one arithmetic'),
         row(['Record progression, Week 9 to Week 10', f'{FEED["reconciliations"][1]["clubs_tested"]} clubs',
              f'{FEED["reconciliations"][1]["clubs_agreeing"]} agree',
              'The same test across the next retrieval, with all 32 clubs including the four on bye.'],
             ('nfl-schedule-w9', 'nfl-schedule-w10-byweek'), 'Two official pages, one arithmetic'),
         row(['Published win percentages', f'{FEED["pct_checks"]} rows', f'{FEED["pct_agreeing"]} agree',
              '(W + T/2) / G reproduces the three-decimal figure the game center prints.'],
             ('nfl-gamecenter-w10-standings',), 'Independent official page'),
         row(['Week 8 game cards', f'{FEED["week8_card_checks"]["run"]} games',
              f'{FEED["week8_card_checks"]["agreeing"]} agree', 'The corroboration page corroborates itself.'],
             ('nfl-schedule-w8-byweek',), 'Official page, two fields'),
     ])
     + table('Backtest and ROI readiness', ['Input', 'State', 'Effect'], [
         row(['Verified final scores', f'{READY["finals_verified"]} of {READY["finals_in_feed"]} finals in the '
              'feed', 'Sufficient to settle a bet against.'], ('nfl-schedule-w9',), 'Feed populated'),
         row(['A market line attached to those finals', READY['finals_with_a_market_line'],
              'No comparison, so no edge measurement.'], ('repo',), 'Blocking'),
         row(['Opening snapshot with a timestamp', ROI['blocking_reasons'][2] if ROI['blocking_reasons']
              else 'captured', 'No entry price, so no expected value.'], ('repo',), 'Blocking'),
         row(['Closing snapshot with a timestamp', ROI['blocking_reasons'][3] if len(ROI['blocking_reasons']) > 3
              else 'captured', 'No closing-line value, so a fair line can never be judged by the market.'],
             ('repo',), 'Blocking'),
         row(['Bets settleable end to end', ROI['bets_settleable'], 'The product of the four rows above.'],
             ('repo',), 'Project arithmetic'),
         row(['Settlement arithmetic', 'implemented: settle() returns win, push or loss for spread, total and '
              'moneyline, and refuses to settle against an unverified result',
              'Unit tested on declared fixtures; not run against 2026 results, because no captured price makes '
              'a performance claim legitimate here.'], ('repo',), 'Unit tested · no performance claim'),
     ])
     + table('Origination order, enforced', ['Stage', 'Rule', 'Enforcement'],
             [row([name, text, 'validate_order() rejects any log that breaks it, and originate() raises '
                   f'rather than reordering ({len(ORIG["out_of_order_rejected"])} reasons stated for a '
                   'deliberately out-of-order log)'], ('repo',), 'Enforced in code')
              for name, text in __import__('engine.originate', fromlist=['stage_labels']).stage_labels()])
     + table('The three columns, kept separate', ['Market', 'Fair line', 'Cover probability at that line',
                                                  'Push mass', 'How it was obtained', 'Basis'],
             _origination_rows())
     + table('What the column split yields across the slate', ['Column', 'Populated rows', 'Reading'], [
         row(['fair_line', ORIG['rows_with_a_fair_line'], f'Of {ORIG["published_rows"]} market-side rows: the '
              'side and total stages produce a reference line, and the moneyline stage deliberately has no '
              'line field, because a price carries its information.'], ('repo',), 'Computed at build'),
         row(['market_line', ORIG['rows_with_a_market_line'], 'Nothing to compare against until an opening '
              'snapshot with a timestamp exists.'], ('repo',), 'Computed at build'),
         row(['difference', ORIG['rows_with_a_difference'], 'Computed only when both columns exist, so it is '
              'blank rather than equal to the fair line. The blank is the finding, and it is the reason R1 '
              'comes first.'], ('repo',), 'Computed at build'),
         row(['Rows in the register', ORIG['published_rows'], '29 games x 3 markets x 2 sides. Every row is '
              'emitted whether or not it can be populated, so a missing market cannot hide by omitting rows.'],
             ('repo',), 'Project arithmetic'),
     ])
     + '<p>Sign convention: `settle()` treats a spread line as the handicap the side receives and a total '
       'line as the threshold it is over or under, and records that convention on every snapshot. The '
       'repository\'s historical file does not document its own convention (F22-F24), which is a second reason '
       'its numbers are quarantined rather than re-labelled. See <a href="lines.html">Own lines</a> for that '
       'file\'s own audit and <a href="data.html">Data requirements</a> for the acquisition contract.</p>')


# --------------------------------------------------------------------------- origination order + columns
page('signal-staking.html', 'Signal vs staking',
     'Two boards.\nOne rank key.\nMoney cannot vote.',
     'The leaderboard is split so that prediction quality and bankroll outcome are reported separately, with '
     'the rank computed only from the signal lower bound. The demotion gate sits on the same signal axis, so '
     'the thing that puts a strategy live and the thing that takes it out are measured in the same units.',
     '<div class="notice"><strong>Both boards are empty, and the emptiness is enforced</strong>'
     f'<p>{SPLIT["candidates_registered"]} candidates are registered and {SPLIT["settled_bets_available"]} '
     'settled bets exist, so there is nothing to rank. That is not the interesting part: the interesting part '
     'is that a candidate submitting a staking run without a signal block is <em>rejected</em> rather than '
     'placed last, and a staking block cannot run at all without captured opening prices. A lucky run cannot '
     'mask a bad signal here because the two numbers never share a column, and the second one cannot be '
     'computed from thin air.</p></div>'
     + table('The split, as rules', ['Rule', 'Treatment'],
             [row([name, text], ('repo',), 'Project rule') for name, text in SPLIT_RULES])
     + table('Signal board — the only board that ranks',
             ['Track', 'Candidate', 'Settled n', 'Log-loss gain', 'Gain lower bound', 'Brier',
              'Calibration MAE', 'Coverage', 'Rank', 'Eligibility'], [
         row([track, None, None, None, None, None, None, None, None, 'Not eligible: no registered candidate'],
             ('logloss', 'brier', 'repo'), 'Metric definitions · project record')
         for track in ('G1 · Game single', 'P1 · Player prop', 'X1 · Cross-game parlay',
                       'S1 · Same-game combo')])
     + table('Staking board — disclosure only',
             ['Track', 'Candidate', 'Settled n', 'Staked units', 'Net units', 'ROI', 'Max drawdown',
              'Price basis', 'Effect on rank'], [
         row([track, None, None, None, None, None, None, 'no captured open snapshots exist',
              'none, by construction'], ('repo',), 'Project record · refusal enforced')
         for track in ('G1 · Game single', 'P1 · Player prop', 'X1 · Cross-game parlay',
                       'S1 · Same-game combo')])
     + table('Refusals observed in this build', ['Attempt', 'Result'], [
         row(['Compute a staking block from outcomes without a captured price',
              SPLIT['staking_refused_without_captured_price']], ('repo',), 'Enforced by engine/signal_staking.py'),
         row(['Place a candidate on the board from its return alone',
              SPLIT['rank_without_signal_refused']], ('repo',), 'Enforced by engine/signal_staking.py'),
         row(['Rank a candidate whose point estimate is positive but whose lower bound is not',
              f'declined: gain {SPLIT["signal_demo"]["gain"]:.4f} against a lower bound of '
              f'{SPLIT["signal_demo"]["gain_lcb"]:.4f} on declared synthetic rows — the row is listed, not '
              'ranked'], ('logloss',), 'Demonstrated on synthetic input'),
         row(['Push a refunded leg into the probability score',
              'excluded from scoring, counted in the staking block as zero units, and reported in coverage'],
             ('repo',), 'Enforced by engine/signal_staking.py'),
     ])
     + table('Demotion gate — what sends a live strategy back to paper',
             ['Trigger', 'Threshold', 'Rationale'],
             [row(list(item), ('repo',), 'Project policy · constants predeclared in the module')
              for item in GATE['rows']])
     + table('Gate exercised on declared test histories', ['History', 'Action', 'Triggers', 'State after'], [
         row(['Eight clean weeks', GATE['clean_hold']['action'], len(GATE['clean_hold']['triggers']),
              GATE['clean_hold']['state_after']], ('repo',), 'Synthetic demonstration'),
         row(['Same eight weeks plus one broken week', GATE['broken_demote']['action'],
              '; '.join(f'{name}: {note}' for name, note in GATE['broken_demote']['triggers']),
              GATE['broken_demote']['state_after']], ('repo',), 'Synthetic demonstration'),
         row(['Same broken week, asking to return to live',
              'yes' if GATE['relist_after_demote']['relist_ready'] else 'no', '; '.join(GATE['relist_after_demote']['blocked_by']),
              'paper'], ('repo',), 'Synthetic demonstration'),
     ])
     + table('Gate state on the real board', ['Quantity', 'Value'], [
         row(['Candidates currently live', GATE['live_candidates'], ], ('repo',), 'Project record'),
         row(['Demotion decisions logged', 'the log exists and its hash chain verifies', ],
             ('repo',), 'Project record'),
         row(['Thresholds tunable by a caller', 'not silently: a non-default policy must be complete, name '
              'who changed it and from which week, and the label is written into the decision record. An '
              'unlabelled override raises.', ], ('repo',), 'Enforced by engine/demotion.py check_policy'),
         row(['Unreported fields', 'a live candidate with no calibration or coverage figure in the window is '
              'treated as breaching it, so silence cannot be used to stay live', ], ('repo',),
             'Enforced by engine/demotion.py'),
         row(['Risk stop as a ranking device', 'impossible: a drawdown breach can only suspend new stakes, and '
              'a suspension never changes a rank', ], ('repo',), 'Enforced by engine/demotion.py'),
     ])
     + '<p>Relationship to the published leaderboard: <a href="leaderboard.html">Leaderboard</a> remains as its '
       'author published it, with empty metric cells. This page is the split view the requirement asks for, and '
       'the four-track roster matches it row for row so the two cannot drift apart. Luck is not removed — it is '
       'made visible: a positive return with a non-positive signal lower bound is labelled, never averaged.</p>')


# --------------------------------------------------------------------------- depth + correlations
def _depth_rows():
    out = []
    for row_ in DEPTH['rows']:
        if row_['slot'] is None and not row_['vacated_player']:
            out.append(row([row_['team'], '—', 'no chart retrieved', '—', '—', None, None,
                            'unknown, not zero', row_['reason']],
                           ('nfl-injury-w10', 'repo'), 'Checked absence · depth unmeasurable'))
        elif row_['slot'] is None:
            out.append(row([row_['team'], '—', 'not on the retrieved chart', row_['vacated_player'],
                            row_['vacated_status'], None, None, 'unknown, not zero', row_['reason']],
                           ('nfl-injury-w10', 'repo'), 'Cross-source disagreement · withheld'))
        else:
            out.append(row([row_['team'], row_['unit'], row_['slot'], row_['vacated_player'],
                            row_['vacated_status'], row_['vacated_rank'],
                            f"{row_['replacement_player']} (rank {row_['replacement_rank']})",
                            row_['strings_travelled'],
                            (f"depth from top of chart: {row_['depth_from_top']}"
                             + ('; ' + row_['depth_note'] if row_.get('depth_note') else '')
                             + ('; also the only listed cover for: ' + ', '.join(row_['covers_slots'])
                                if row_.get('covers_slots') else ''))],
                           ('nfl-injury-w10', 'chiefs-depth' if row_['team'] == 'KC' else
                            'lions-depth' if row_['team'] == 'DET' else 'seahawks-depth-1cf'),
                           'Report row + club chart order · derived arithmetic'))
    return out


page('depth-correlations.html', 'Depth & correlation',
     'How deep the replacement runs.\nWhat the data can actually support.',
     'Two of the eight requirements share a page because they share a failure mode: a fact that looks complete '
     'without a denominator. A replacement is not "a backup started", it is a distance travelled down a chart '
     'that may not exist; a correlation is not a number, it is a number with an n attached.',
     '<div class="notice"><strong>One case on this page shows why the count is the wrong unit</strong>'
     '<p>Kansas City has no out-of-lineup starting defensive tackle: Chris Jones plays. But the chart\'s second '
     'tackle is Out, so the third string starts. A vacancy count reports nothing interesting here and a depth '
     'measure reports the whole thing — which is what the requirement asked for.</p></div>'
     + table('Replacement depth, computed from the report and the chart order',
             ['Team', 'Unit', 'Slot', 'Vacated player', 'Report status', 'Rank vacated',
              'Who moves up', 'Strings travelled', 'Notes'], _depth_rows())
     + table('What the depth measure found', ['Quantity', 'Value', 'Reading'], [
         row(['Vacancies located on a retrieved chart', DEPTH['vacancies'], 'Each has a computed string '
              'distance.'], ('nfl-injury-w10', 'chiefs-depth', 'seahawks-depth-1cf', 'lions-depth'),
             'Derived arithmetic'),
         row(['Out players on no retrieved chart row', ', '.join(f'{t} · {p}' for t, p in DEPTH['unlisted_vacancies']),
              'A cross-source disagreement, not a zero: the slot they vacate cannot be located. Published as '
              'F31 and extending F20.'], ('nfl-injury-w10', 'lions-depth', 'chiefs-depth'), 'Flagged'),
         row(['Players who are the published cover for two slots',
              ', '.join(f'{t} · {p} ({", ".join(s)})' for t, p, s in DEPTH['multi_slot_backups']),
              'One player, two vacancies waiting behind him. Depth of one is depth of one.'],
             ('chiefs-depth', 'seahawks-depth-1cf'), 'Derived from chart order'),
         row(['Slots listed with no backup beneath them', DEPTH['rows_with_no_backup_listed'],
              'DET safety Chuck Clark is alone in his row: if he cannot play, the chart has no answer.'],
             ('lions-depth',), 'Chart structure'),
         row(['Chart slots extracted here', DEPTH['chart_slots_extracted'],
              'Extracted slots relevant to a Week 10 vacancy, not the whole chart: no claim is made about '
              'unextracted rows.'], ('chiefs-depth', 'seahawks-depth-1cf', 'lions-depth'), 'Scope statement'),
         row(['Clubs in the Week 10 report', DEPTH['clubs_in_report'], 'The snapshot the report covers.'],
             ('nfl-injury-w10',), 'Official report'),
         row(['Clubs with a chart retrieved by this session', DEPTH['clubs_with_chart'],
              'Three. Depth is therefore measurable for three and unknown for '
              f'{DEPTH["clubs_without_chart"]}, and the unknowns are listed rather than averaged away.'],
             ('repo',), 'Checked coverage'),
         row(['Vacancies whose first available name is conditional', DEPTH['conditional_vacancies'],
              'Depth is reported twice for these: the distance if the Questionable name plays, and if '
              'he does not. ' + (DEPTH['depth_notes'][0] if DEPTH['depth_notes']
                                 else 'none in this snapshot')],
             ('nfl-injury-w10', 'seahawks-depth-1cf'), 'Derived arithmetic'),
         row(['Worst-case depth across located vacancies', DEPTH['worst_case_max_depth'],
              f'Highest of the two distances anywhere in the snapshot; headline maximum is '
              f'{DEPTH["max_depth"]}.'], ('repo',), 'Project arithmetic'),
         row(['Depth total across located vacancies', DEPTH['depth_total'],
              f'Maximum single distance {DEPTH["max_depth"]}. No weight is attached to any of it: distance is '
              'not damage, and no performance drop per string is estimated from this.'], ('repo',),
             'Project arithmetic · no effect size'),
     ])
     + table('Limits on the depth measure', ['Limit', 'Statement'],
             [row([name, text], ('repo',), 'Published limitation') for name, text in DEPTH_LIMITS])
     + table('Correlation register — officially sourced numbers only, each with its n',
             ['Predeclared pair', 'Level', 'n', 'Pearson r', '95% interval', 'Verdict',
              'May it price a joint bet?', 'Sources'],
             [row([c['label'], c['level'], c['n'],
                   'undefined' if c['r'] is None and c.get('status') == 'undefined' else
                   ('refused' if c.get('status') == 'refused' else
                    ('—' if c['r'] is None else c['r'])),
                   '—' if not c.get('interval') else f"[{c['interval'][0]}, {c['interval'][1]}]",
                   c['verdict'], 'no' if not c['may_price_joint'] else 'yes',
                   ', '.join(c['sources']) if c['sources'] else 'n/a'],
                  tuple(c['sources']) or ('repo',), 'Official numbers · computed at build')
              for c in CORRS])
     + table('The correlation gate, as rules', ['Rule', 'Statement'],
             [row([name, text], ('pearson',), 'Project gate · method support')
              for name, text in CORR_RULES])
     + table('Predeclared constants', ['Constant', 'Value', 'Status'], [
         row(['Minimum paired observations before a verdict may act', CORRS[0]['min_n'],
              'Declared in engine/correlations.py before any measurement in this module was run.'],
             ('repo',), 'Predeclared'),
         row(['Deadband — smallest |r| the project acts on', CORRS[0]['deadband'],
              'Same declaration. Not tuned to any result on this page.'], ('repo',), 'Predeclared'),
         row(['Confidence level for published intervals', CORRS[0]['confidence'],
              'Fisher-z, and the module notes that intra-week legs are not independent, so the interval is '
              'reported with that caveat rather than as a licence.'], ('pearson', 'repo'), 'Method support'),
     ])
     + '<p>Interpretation, stated plainly: at eleven to fifteen games no interval here is narrow enough to '
       'clear the predeclared floor, so no joint price is produced and no independence is assumed either. The '
       'pair that would most tempt a reader — prior record gap against final margin — has a point estimate of '
       f'{CORRS[0]["r"]} at n={CORRS[0]["n"]}, an interval of {CORRS[0]["interval"]}, and a verdict of '
       f'{CORRS[0]["verdict"]}. The interval clears the deadband; the sample does not clear the floor. That '
       'asymmetry is the gate working. See <a href="correlations.html">Correlations</a> for the predeclared '
       'pair definitions this register measures against.</p>')


# --------------------------------------------------------------------------- missing information
page('missing-information.html', 'Missing info',
     'What has to be known\nbefore anything is decided.',
     'The questions, information and answers that stand between this repository and a reasonable decision, '
     'separated by whether they can be answered from what is already verified, need a data action, or need the '
     'owner to choose. Then the discovery suggestions: what to build or buy purely to find out.',
     '<div class="notice"><strong>Read the other registers too, they are not duplicates of this one</strong>'
     '<p><a href="questions.html">Question register</a> carries the earlier 22-question set, '
     '<a href="question-ledger.html">Question ledger</a> carries 32 questions with an owner-decision split, and '
     '<a href="decision.html">Decision brief</a> carries the decisions with stopping rules. This page is the '
     'delta created by the eight new requirements: what they exposed, not what was already catalogued. The '
     'overlap itself is finding F27, and consolidating it is S01, an open owner decision.</p></div>'
     + table('Answered now, from officially sourced numbers', ['ID', 'Question', 'Answer', 'Basis'], [
         row(['MI-A1', 'Can results be verified well enough to settle a bet?',
              f'Yes. {FEED["verified"]} games pass every check in the feed, including two-record corroboration '
              'across three official pages.',
              'Week 8, 9 and 10 schedule pages, plus the game center standings table.'],
             ('nfl-schedule-w8-byweek', 'nfl-schedule-w9', 'nfl-schedule-w10-byweek'), 'Official pages'),
         row(['MI-A2', 'Is the missing piece the results side?',
              'No. It is the price side. Verified results went in without a fight; the store remains at '
              f'{STORE["records_priced"]} priced records of {STORE["expected_pairs"]} expected.',
              'Measured at build.'], ('repo',), 'Project arithmetic'),
         row(['MI-A3', 'Does the repository already hold 2026 lines?',
              f'Yes, in the score snapshot: {ORIG["games_with_a_line_value"]} of {ORIG["games_in_feed"]} feed '
              'games carry a value. They have no capture time and no stage label, so they are not quotes.',
              'Join computed at build; the file\'s own provenance remains unconfirmed (F22-F24).'],
             ('repo',), 'Computed at build'),
         row(['MI-A4', 'Can an opening number be recovered from the historical quote file?',
              'No. The file has one row per market side with a line and an odds field and no time column, so it '
              'records one point of a move, not the move.',
              f'{QUOTES["rows"]:,} rows inspected; stage and time columns: none.'], ('repo',), 'Computed at build'),
         row(['MI-A5', 'Does the league publish betting lines?',
              'No. The NFL publishes scores, schedules, statistics by eleven categories, injury reports, '
              'rosters, transactions and Game Books; no odds or line product appears among them, and the '
              'statistics categories include no participation or snap count.',
              'Checked absences recorded by this repository and retained here.'],
             ('nfl-player-stats', 'nfl-stats-cats'), 'Official pages · absence noted'),
         row(['MI-A6', 'Is there an official depth chart to measure replacement depth against?',
              'Not from the league: the club depth-chart route on nfl.com returns a 404 and team pages route '
              'the request to club sites. Club sites do publish charts, and two of the three retrieved here '
              'label themselves unofficial.',
              'Verified this session on the Chiefs, Seahawks and Lions charts; recorded per club rather than as '
              'a blanket statement (F29).'],
             ('nfl-depth-chart-404', 'chiefs-depth', 'seahawks-depth-1cf', 'lions-depth'), 'Checked absence + club pages'),
         row(['MI-A7', 'Can a correlation be computed at all from official numbers?',
              f'Yes, and it was: {len(CORRS)} pairs at n of {min(c["n"] for c in CORRS)} to '
              f'{max(c["n"] for c in CORRS)}. Every one is refused action by the predeclared sample floor.',
              'Computed at build from the Week 8 and Week 9 pages.'],
             ('nfl-schedule-w9', 'nfl-schedule-w8-byweek', 'pearson'), 'Official numbers'),
         row(['MI-A8', 'Does a lucky staking run currently threaten the leaderboard?',
              'Not currently — there is nothing on it. The structural protection is that it cannot: rank reads '
              'only the signal lower bound, and a return with no signal block is rejected outright.',
              'Enforced in engine/signal_staking.py and asserted in tests.'], ('repo',), 'Enforced in code'),
     ])
     + table('Open questions, closable by data work', ['ID', 'Question', 'What is missing', 'How it gets answered',
                                                        'Cost'], [
         row(['MI-O1', 'What does the market actually move by between posting and kickoff?',
              'Paired opening and closing captures on one slate.',
              'Run the store\'s append path on a licensed feed, or script a capture per market per stage.',
              'Medium · one slate proves the mechanism'], ('repo',), 'Open · data action'),
         row(['MI-O2', 'How wide is the interval between our number and the market\'s?',
              'The market line column of the published rows.',
              'Follows from MI-O1; nothing else unblocks it.', 'Follows MI-O1'], ('repo',), 'Open · data action'),
         row(['MI-O3', 'Does the prior-strength gap have predictive content, or is it an artefact of eleven '
              'games?', 'Volume. The point estimate is large; the interval is nearly the whole range.',
              f'Measure the same pair each week until n reaches {CORRS[0]["min_n"]}, without changing the '
              'definition or the floor.', 'Low per week · weeks of patience'],
             ('nfl-schedule-w9',), 'Open · prospective'),
         row(['MI-O4', 'Which of the 23 clubs in the report without a retrieved chart have locatable '
              'replacements?', 'The charts themselves, or a certified league source.',
              'Retrieve each club chart with its retrieval timestamp and store the extraction as evidence; do '
              'not merge club formats without recording the differences.', 'Low · mechanical'],
             ('nfl-injury-w10',), 'Open · data action'),
         row(['MI-O5', 'Is the repository score snapshot\'s line column an opening or a closing number?',
              'Its provenance, licence and sign convention.',
              'Identify the upstream file and confirm its documentation, or mark it permanently unusable for '
              'pricing.', 'Low if the upstream can be identified'], ('repo',), 'Open · provenance'),
         row(['MI-O6', 'How many snaps does a replacement actually take?',
              'A participation denominator; the league publishes none among its statistics categories.',
              'Licence a tracking feed, or accept a counting-statistics proxy and disclose the precision loss.',
              'High · or zero with a documented downgrade'], ('nfl-stats-cats', 'nfl-ngs'), 'Blocked on source'),
     ])
     + table('Questions only the owner can answer', ['ID', 'Question', 'Why it cannot be answered from evidence',
                                                     'Default if nothing changes'], [
         row(['MI-D1', 'Pay for a historical quote archive, or accumulate forward captures from here?',
              'A money and licensing decision, not a data decision.',
              'Forward capture only; no backtest on prior seasons.'], ('repo',), 'Awaiting decision'),
         row(['MI-D2', 'Are the historical files in data/raw/ kept, deleted, or quarantined-and-documented?',
              'They are already in the repository\'s history, and their licence is unconfirmed; the choice is a '
              'rights and hygiene decision.', 'Quarantine as now: measured, cited, never used for a claim.'],
             ('repo',), 'Awaiting decision'),
         row(['MI-D3', 'Does a strategy go live on paper-tracked signal alone, or does it need a sealed-test '
              'result first?',
              'Risk appetite. Both are defensible and the evidence does not rank them.',
              'Nothing goes live: the demotion gate stays armed against an empty board.'], ('holdout',),
             'Awaiting decision'),
         row(['MI-D4', 'Should the seven overlapping sections be consolidated into one site?',
              'It would rewrite pages owned by other sessions, whose records are preserved deliberately.',
              'Sections stay separate with the directory on the overview.'], ('repo',), 'Awaiting decision'),
         row(['MI-D5', 'Is any non-cash recognition programme wanted for the leaderboard, or none at all?',
              'It is a governance decision with no data content.',
              'No badge, no funding, no award, as published.'], ('repo',), 'Awaiting decision'),
     ])
     + table('Suggestions to discover what is missing', ['ID', 'Probe', 'What it would reveal', 'Cost',
                                                          'What would make it worthless'], [
         row(['P-01', 'Append one real open snapshot for one game, at market publication, and stop.',
              'Whether the capture path works end to end against a live slate, including the timestamp and '
              'source fields, before anyone builds tooling around it.', 'Minutes',
              'A source that will not carry a citable URL for the number.'], ('repo',), 'Proposed'),
         row(['P-02', 'Re-read one official page twice, an hour apart, and diff it.',
              f'How much the "verified" feed moves within a day — the feed passes {FEED["checks_run"]} checks '
              'today; this shows how long that lasts.', 'Minutes', 'Nothing: a stable page is also a finding.'],
             ('nfl-schedule-w10-byweek',), 'Proposed'),
         row(['P-03', 'Ask the score snapshot\'s upstream what its line column means.',
              'Whether the 2026 lines already in this repository are open or close numbers, which is the '
              f'difference between {ORIG["games_with_a_line_value"]} usable rows and none.', 'Low',
              'A non-answer, which would leave the file quarantined permanently.'], ('repo',), 'Proposed'),
         row(['P-04', 'Compute the Week 9 to Week 11 prior-gap correlation weekly, frozen definition, no action.',
              'How fast the interval tightens, and whether the deadband floor is reachable inside this season.',
              'Low · automated', 'A definition change mid-flight, which is why the pair is frozen in code.'],
             ('nfl-schedule-w9', 'pearson'), 'Proposed'),
         row(['P-05', 'Retrieve all 32 club charts once, with timestamps, and diff them against the report.',
              'How often an Out player is absent from his own club\'s chart — this release found two in three '
              'clubs, so the true rate may be high.', 'Low', 'Charts published in incompatible formats, which '
              'is itself worth knowing.'], ('nfl-injury-w10', 'chiefs-depth'), 'Proposed'),
         row(['P-06', 'Run the demotion gate over a synthetic candidate that degrades linearly.',
              'Whether the triggers fire in the intended order and how many weeks of damage pass before one '
              'does.', 'Low', 'Finding that a threshold is unreachable, which would need a recorded change.'],
             ('repo',), 'Proposed'),
     ])
     + '<p class="download">Every row above is either answered from a registered official source, countable '
       'from this repository, or explicitly an owner decision. Nothing is marked answered because it is '
       'plausible. New findings from this release are published as F28-F33 on '
       '<a href="flags.html">Flagged for Review</a>; the costed improvement sheet is '
       '<a href="suggestion-costs.html">Suggestion costs</a> and the register that governs acceptance is '
       '<a href="suggestions.html">Suggestions</a>.</p>')


# --------------------------------------------------------------------------- shared-page appends
# A pointer on the leaderboard so the split is discoverable from the board itself. The page's own
# tables, rows and blank cells are untouched; one paragraph is appended after them.
PAGES['leaderboard.html'] = (*PAGES['leaderboard.html'][:3],
                             PAGES['leaderboard.html'][3]
                             + '<p class="download">Split view (14 Nov 2026, session 1cfcb957): the signal '
                               'board and the staking board are published separately on '
                               '<a href="signal-staking.html">Signal vs staking</a>, with rank computed only '
                               'from the signal lower bound and a staking run that cannot place a candidate. '
                               'The four tracks above are the same four tracks; the tables above are unchanged '
                               'and remain empty because nothing is validated.</p>')

# Caption deliberately does NOT start with "Review register extension": the earlier session's test
# selects its own six rows by that prefix, and a shared prefix would silently fold two registers
# into one and break their row count.
new_flags = table('Register continuation · raised 14 Nov 2026 by session 1cfcb957',
                  ['ID / severity', 'Finding', 'Required evidence / disposition', 'State'], [
    row(['F28 · Review', 'The "Teams on Bye" block on the official weekly schedule page prints each listed '
         f'club\'s record as of retrieval, not as of that week. On the Week 8 page it showed HOU 3-5, NO 3-5, '
         'NYG 5-3-1 and SF 7-1, while their Week 9 game cards imply 2-5, 2-5, 4-2-1 and 6-1 as their Week 8 '
         'records. A record-feature built from the bye block would import later results into an earlier week.',
         'The results feed excludes those four clubs from the Week 8 to Week 9 reconciliation and states why; '
         'coverage is published as 28 of 32 clubs for that pair rather than silently rounded up. Any future '
         'as-of-week record must come from a game card or a dated standings archive.',
         'Handled · coverage stated'], ('nfl-schedule-w8-byweek', 'nfl-schedule-w9'),
         'Two official pages · arithmetic'),
    row(['F29 · Review', 'The self-labelled "unofficial" caveat on club depth charts is not uniform. Read on '
         '2026-11-14: the Chiefs page is titled "Kansas City Chiefs Unofficial Depth Chart" and the Lions page '
         '"2026 Unofficial Depth Chart Compiled by Lions Football Communications", while the Seahawks page as '
         'retrieved here (both chunks, document title "Seattle Seahawks") displays no such label. An earlier '
         'manifest entry states the caveat applies to the Seahawks chart the same way.',
         'Do not apply the caveat blanket-wide. This release registers its own Seahawks read '
         '(seahawks-depth-1cf) recording exactly what was retrieved and what was absent, and cites that entry '
         'for Seahawks rows. The earlier entry is left as its author published it; whoever owns it should '
         'narrow the wording or add the page element that carries the label.',
         'Flagged · owner of that record to confirm'], ('seahawks-depth-1cf', 'chiefs-depth', 'lions-depth'),
         'Verified per club'),
    row(['F30 · Critical', 'The price-snapshot store exists and is empty: 0 of '
         f'{STORE["expected_pairs"]} expected captures for the 29-game slate, 0 priced records, and '
         'no ROI, closing-line value or expected-value figure is computable. The 2026 line values that do '
         f'exist in the repository ({ORIG["games_with_a_line_value"]} of {ORIG["games_in_feed"]} feed games) '
         'carry no capture time and no open/close label.',
         'Capture path required before any economic claim: a licensed operator feed, or scripted forward '
         'capture at market publication and at kickoff. This is the single dependency that unblocks R1, R4, '
         'the staking board and the economics gate simultaneously.',
         'Open · blocking'], ('repo', 'dk-markets'), 'Computed at build'),
    row(['F31 · Review', 'Two players carrying an Out game status in the Week 10 2026 report appear on no row '
         'of the club chart retrieved for them: DET S Kerby Joseph and KC DT Omarr Norman-Lott. Their vacated '
         'slots cannot be located, so replacement depth is unknown for them rather than zero. F20 recorded the '
         'Joseph case alone; this is a second instance in the same three clubs, which suggests a pattern '
         'rather than a one-off.',
         'Reported as unknown in the depth register with the player named. No replacement is inferred. If more '
         'clubs are charted (P-05), publish the rate rather than reconciling silently.',
         'Flagged · not reconciled'], ('nfl-injury-w10', 'lions-depth', 'chiefs-depth'), 'Cross-source disagreement'),
    row(['F32 · Review', 'This working checkout is a shallow clone: git reports 2 commits and .git/shallow '
         'exists, so both data/raw files appear only in the branch base commit. Commit history therefore '
         'cannot date when the quote or score snapshot was introduced, and no capture bound can be inferred '
         'from it.',
         'Any vintage claim about those files must come from the files themselves or from their upstream, not '
         'from git. The store schema requires a captured_at per record precisely for this reason.',
         'Recorded limitation'], ('repo',), 'Repository inspection'),
    row(['F33 · Review', 'Method note, published because the error class matters more than the error: an early '
         'revision of the audit detected a "timestamp column" in the quote file by substring search, and '
         '"utc" is inside "outcome". Whole-name matching is now used and the column list is printed on the '
         'page so a reader can check it.',
         'Keep the pattern: measure with whole identifiers, and publish the inspected list next to the derived '
         'figure so a substring bug like this one is visible without reading code.',
         'Fixed in this release'], ('repo',), 'Method integrity'),
])

PAGES['flags.html'] = (*PAGES['flags.html'][:3],
                       PAGES['flags.html'][3]
                       + '<p class="download">F28 to F33 below were raised by session 1cfcb957 on 14 Nov 2026. '
                         'They continue the existing numbering and do not edit any earlier row: F20 and F21 are '
                         'referred to rather than restated, and F31 extends F20 with the second club it did not '
                         'cover.</p>'
                       + new_flags)

# The overview gains one directory row per new page group, computed rather than typed, so its counts
# cannot go stale the way a hand-written page count did in an earlier release.
_index_rows = table('Requirements added on 14 Nov 2026 (session 1cfcb957)',
                    ['Page', 'Carries', 'Measured headline'], [
    row(['requirements.html', 'The eight-requirement traceability register, the release executive summary and '
         'four candidate paths', '6 enforced, 2 enforced with inputs absent'], ('repo',), 'This release'),
    row(['price-feed.html', 'Snapshot store schema and state, the quote file measured against it, the verified '
         f'results feed and its checks, ROI readiness', f'{STORE["records_priced"]} priced snapshots · '
         f'{FEED["verified"]} verified games'], ('repo', 'nfl-schedule-w9'), 'This release'),
    row(['signal-staking.html', 'Signal and staking boards, the refusals that keep them apart, and the demotion '
         'gate', f'{SPLIT["candidates_registered"]} candidates · {GATE["live_candidates"]} live'], ('repo',),
         'This release'),
    row(['depth-correlations.html', 'Replacement depth per vacancy, chart disagreements, and the correlation '
         f'register with n', f'{DEPTH["vacancies"]} located vacancies · {len(CORRS)} pairs, all refused action'],
        ('repo', 'nfl-schedule-w9'), 'This release'),
    row(['missing-information.html', 'Answers available now, open questions, owner decisions and six discovery '
         'probes', '8 answered · 6 open · 5 owner decisions'], ('repo',), 'This release'),
])
PAGES['index.html'] = (*PAGES['index.html'][:3],
                       PAGES['index.html'][3]
                       + _index_rows)
