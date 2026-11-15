"""Session f5961230 pages: Week 10 official re-check, decision-readiness register,
landing-page summary and Flagged for Review additions.

Registered into tools/build.py via register(). Every number here is either
(a) a hand tally of the official NFL Week 10 injury page as retrieved on
2026-11-15 (8 chunks), recorded per club below, or (b) a count read from a
committed repo file. Nothing is estimated. Where a value could not be read it
is written as "not checked" rather than filled in.
"""

from collections import Counter

INJURY_SRC = 'nfl-injury-2026-11-15'

# (club, official rows, official designations, repo rows, repo designations, status)
# Official = hand tally of https://www.nfl.com/injuries/ retrieved 2026-11-15.
# Repo = session-00cf851d/data/injury_report_week10.json (retrieved 2026-11-14), counted by script.
CLUBS = [
    ('ATL', 11, 5, 11, 5), ('AZ', 15, 9, 15, 9), ('BAL', 10, 2, 10, 2), ('BUF', 14, 5, 14, 5),
    ('CAR', 12, 7, 12, 7), ('CIN', 9, 4, 9, 4), ('CLE', 12, 3, 12, 3), ('DAL', 19, 11, 19, 11),
    ('DET', 9, 5, 9, 5), ('GB', 17, 12, 17, 12), ('HOU', 16, 11, 16, 11), ('IND', 14, 7, 14, 8),
    ('JAX', 11, 4, 11, 4), ('KC', 13, 6, 13, 6), ('LAC', 19, 10, 19, 0), ('LAR', 14, 7, 14, 7),
    ('LV', 5, 2, 5, 2), ('MIA', 11, 4, 11, 4), ('MIN', 13, 8, 13, 8), ('NE', 15, 12, 15, 12),
    ('NO', 12, 6, 12, 6), ('NYG', 11, 1, 11, 1), ('NYJ', 9, 9, 9, 9), ('PIT', 8, 1, 8, 1),
    ('SEA', 15, 4, 15, 4), ('SF', 12, 8, 12, 8), ('TEN', 12, 6, 12, 6), ('WAS', 9, 2, 9, 2),
]
ABSENT = 'DEN, CHI, PHI, TB (no table in the Week 10 report; the page gives no reason)'

# Row-level differences found by comparing the repo capture with the official page.
# (club, player, field, repo value, official value)
ROW_DIFFS = [
    ('IND', 'Arden Key (DE)', 'Injury', 'Hamstring', 'blank'),
    ('IND', 'Arden Key (DE)', 'Game status', 'Questionable', 'blank'),
    ('LAC', 'Kayode Awosika (G)', 'Practice', 'Limited Participation in Practice', 'Full Participation in Practice'),
    ('LAC', 'Kayode Awosika (G)', 'Injury / Game status', 'blank / blank', 'Fibula / Questionable'),
    ('LAC', 'Bud Dupree (DE)', 'Practice', 'Did Not Participate In Practice', 'Full Participation in Practice'),
    ('LAC', 'Justin Eboigbe (DE)', 'Injury / Game status', 'blank / blank', 'Ankle / Questionable'),
    ('LAC', 'Keaton Mitchell (RB)', 'Practice', 'Limited Participation in Practice', 'Full Participation in Practice'),
    ('LAC', 'Ladd McConkey (WR)', 'Injury / Game status', 'blank / blank', 'Back / Questionable'),
    ('LAC', 'David Njoku (TE)', 'Practice', 'Limited Participation in Practice', 'Full Participation in Practice'),
    ('LAC', 'David Njoku (TE)', 'Injury / Game status', 'blank / blank', 'Fibula / Questionable'),
    ('LAC', 'Denzel Perryman (LB)', 'Injury / Game status', 'blank / blank', 'Pectoral / Questionable'),
    ('LAC', 'Trey Pipkins (T)', 'Practice', 'Did Not Participate In Practice', 'Limited Participation in Practice'),
    ('LAC', 'Trey Pipkins (T)', 'Injury / Game status', 'blank / blank', 'Not injury related - personal matter, Knee / Questionable'),
    ('LAC', 'Rodney Shelley (CB)', 'Practice', 'Limited Participation in Practice', 'Full Participation in Practice'),
    ('LAC', 'Branson Taylor (G)', 'Injury / Game status', 'blank / blank', 'Ankle / Out'),
    ('LAC', 'Brenen Thompson (WR)', 'Injury / Game status', 'blank / blank', 'Hamstring / Doubtful'),
    ('LAC', 'Isas Waxter (CB)', 'Injury / Game status', 'blank / blank', 'Ankle / Out'),
    ('LAC', 'Kendall Williamson (S)', 'Injury / Game status', 'blank / blank', 'Calf / Out'),
]


def _claims():
    s = INJURY_SRC
    return [
        ('"Published counts are stale: 254 rows and 4 no-injury sections versus 279 rows and 2 sections live"',
         'Not reproduced',
         'Neither 254 nor 279 appears on any current page (injuries.html, site/injuries.html, availability.html). The live official page has 347 player rows in 28 club tables; the repo capture also has 347 rows. No club table has zero injury descriptions, so the "4" and "2" section counts could not be reproduced.',
         ['nfl-injury', s]),
        ('"Only 6 of 254 report rows carry a game designation"',
         'Contradicted by the official page',
         'The live official page gives 171 player rows with an Out, Doubtful or Questionable game status. The repo capture gives 162 (its Chargers rows are blank, and it has one Colts entry the official page does not show).',
         ['nfl-injury', s]),
        ('"Seattle and Cincinnati are shown as injury-free while listing 15 and 4 players"',
         'Not reproduced',
         'Seattle lists 15 players and 4 injuries (Cross, Darnold, Nelson, Williams); Cincinnati lists 9 players and 4 with injuries (Davis, Dugger, Iosivas, Parker II). Both appear with injuries on the root injuries.html page.',
         ['nfl-injury', 'repo']),
        ('"Kerby Joseph, Cade Mays and D.J. Reed are published with a blank game-status cell"',
         'Not reproduced on current pages',
         'The official page lists all three as Out (Joseph: Knee; Mays: Ankle; Reed: Hip). The root injuries.html and availability.html pages and the session-00cf851d page show Out for all three.',
         ['nfl-injury', 'repo']),
        ('"Lamar Jackson and Tyler Huntley still listed at QB in Baltimore depth" (VR-17, VR-26; VQ-07)',
         'Not checked',
         'No Baltimore depth chart was retrieved in this session. The official NFL roundup headline "Ravens officially place Lamar Jackson on injured reserve" is linked from the injury page; it is evidence of IR, not of the depth-chart row.',
         ['nfl-news-jackson-injured-reserve', 'repo']),
        ('"The Texans publish depth as an image" (SG-05 / depth-source item)',
         'Reproduced',
         'The Houston Texans depth-chart page is headed "Unofficial Depth Chart" and the chart is an image. No authorised structured source was found, so the chart was not transcribed.',
         ['houston-depth-image']),
        ('"Malik Willis is absent from the weekly report because he is on injured reserve" (VR-25; VQ-06)',
         'Supported by an official headline only',
         'NFL headline: "Dolphins place QB Malik Willis (groin) on injured reserve; Kyle McCord in line for first start". The transactions log was not checked.',
         ['nfl-news-willis-injured-reserve']),
        ('"Lock, McCord and Brissett: dated starter changes" (VR-24, VR-25; VQ-05)',
         'Partly supported',
         'Lock: headlines state Darnold is ruled out and Lock is expected to start, and that Lock has no injury designation and will start. McCord: "in line for first start" (headline). Brissett: no matching item found on the injury page; not checked further.',
         ['nfl-news-darnold-ruled-out-lock-start', 'nfl-news-lock-no-designation', 'nfl-news-willis-injured-reserve']),
        ('"The Colts\' Week 10 release documents two starting-receiver trades" and "Packers prepend jersey numbers" (roster and depth items)',
         'Not checked',
         'No Colts transaction or Packers depth page was retrieved in this session. Both remain unverified.',
         ['nfl-transactions', 'repo']),
        ('"The 136-game log"',
         'Not found in repo',
         'No file or page in the repository is a 136-game log. The repository lists 121 completed 2026 games (README, verified against the by-week schedule pages).',
         ['nfl-schedule-w10', 'repo']),
        ('Reference IDs "VR-04 … VR-26" and "VQ-05 … VQ-08"',
         'Not traceable',
         'None of these identifiers appears in any repository file, and the official pages checked do not use them. Claims tied only to these IDs are unverified.',
         ['repo']),
    ]


def _claim_rows(row):
    return [row(
        [claim, verdict, evidence],
        tuple(srcs),
        'Verified against the official page' if verdict.startswith('Reproduced') else
        ('Contradicted' if 'Contradicted' in verdict else 'Unverified / not reproduced')
    ) for claim, verdict, evidence, srcs in _claims()]


def _club_rows(row):
    out = []
    for club, orow, odes, rrow, rdes in CLUBS:
        match = (orow == rrow and odes == rdes)
        status = 'Match on counts' if match else 'Mismatch'
        note = ''
        if club == 'IND':
            note = 'Arden Key: repo shows a Hamstring injury and Questionable; official page shows neither (see row diffs).'
        if club == 'LAC':
            note = 'All 19 repo injury and game-status cells blank; official page lists 10 designations; 6 practice wordings differ.'
        if club in ('SEA', 'CIN', 'DET'):
            note = 'Row-level comparison also done: identical injury, practice and game-status values.'
        out.append(row(
            [club, orow, odes, rrow, rdes, status, note],
            ('nfl-injury', 'repo'),
            'Official count (hand tally) and repo count (script)'
        ))
    return out


def _row_diff_rows(row):
    return [row(
        [club, player, field, repo_v, off_v],
        ('nfl-injury', 'repo'),
        'Row-level difference'
    ) for club, player, field, repo_v, off_v in ROW_DIFFS]


def _news_rows(row):
    items = [
        ('Thu 5 Nov', 'Ravens officially place Lamar Jackson on injured reserve', 'nfl-news-jackson-injured-reserve'),
        ('Fri 6 Nov', 'Sam Darnold ruled out for Seahawks Week 10 game vs. Raiders; Drew Lock expected to start again', 'nfl-news-darnold-ruled-out-lock-start'),
        ('Sat 14 Nov', 'Patriots place RB TreVeyon Henderson (illness) on injured reserve', 'nfl-news-henderson-injured-reserve'),
        ('Sun 15 Nov', 'Drew Lock (elbow/oblique) has no injury designation, will start for Seahawks vs. Raiders', 'nfl-news-lock-no-designation'),
        ('Undated headline', 'Dolphins place QB Malik Willis (groin) on injured reserve; Kyle McCord in line for first start', 'nfl-news-willis-injured-reserve'),
    ]
    return [row(
        [date, headline, 'Headline only: an official NFL article exists, but the transaction or depth row was not checked'],
        (src,),
        'Official headline (announced-starter evidence)'
    ) for date, headline, src in items]


# (group, requirement, status, blocking gate, number that clears it, source ids)
READINESS = [
    ('Prices and results', 'Price-snapshot store: opening and closing numbers for every originated market', 'Partial', 'No executable price source exists; the close job now refuses to mark markets closed (F58)', '1 pre-kickoff opening and 1 closing quote for each of the 52 Week 10 markets (currently 0)', ('repo',)),
    ('Prices and results', 'Verified results feed for backtests and ROI', 'Partial', 'ROI needs prices; earlier seasons were only spot-checked', 'Every game in the backtest window matched to an official page (2026: 121 games per README)', ('nfl-schedule-w10',)),
    ('Prices and results', 'Originate side, then total, then moneyline', 'Built', 'None', 'n/a (order enforced by tests)', ('repo',)),
    ('Prices and results', 'Fair line, market line and difference as three separate columns', 'Partial', 'Market line empty on all 52 rows (gate: row 1)', '52 market lines with source', ('repo',)),
    ('Prices and results', 'Decide the price-data policy before any backtest is published', 'Blocked: decision', 'No policy text exists in the repo (search finds 0 matches)', '1 ratified policy document dated before the backtest', ('repo',)),
    ('Prices and results', 'Turn the "136-game log" into the pre-registered backtest corpus', 'Blocked: data', 'No 136-game log exists in the repo (F62)', 'A corpus file whose every row links to an official game page', ('nfl-schedule-w10',)),
    ('Prices and results', 'Vig-free market consensus against the originated fair line', 'Blocked: data', 'No market prices (gate: row 1)', 'Market prices for the 52 markets', ('dk-markets',)),
    ('Prices and results', 'Price a line ourselves and publish the residual against the market on a schedule', 'Partial', 'Model fair published; residual blank because no market line', 'Residual for 52 markets, published on schedule', ('repo',)),
    ('Injuries and availability', 'Store every injury-report read with its clock time; publish the delta, never the level', 'Not started', 'Only two dated captures exist (repo 2026-11-14; this session 2026-11-15)', '2+ timestamped captures per player per week, with deltas computed', ('nfl-injury',)),
    ('Injuries and availability', 'Immutable multi-day availability snapshots with retained hashes (Wed–Fri, then daily)', 'Not started', 'No retained raw captures with hashes; no scheduled injury job', 'A capture for each of Wed, Thu, Fri and Sat in each week, each with a SHA-256', ('nfl-injury',)),
    ('Injuries and availability', 'Injury signal as a surprise (change), never as a level', 'Not started', 'Depends on the repeated captures above', 'Pairs of captures for each player with a designation change', ('repo',)),
    ('Injuries and availability', 'Re-capture and republish the Week 10 injury tables', 'Partial', 'Counts re-verified this session; repo still has LAC and IND row errors (F59, F60)', '0 field-level differences from the official page for all 28 clubs (currently 18 field-level differences in 2 clubs)', ('nfl-injury-2026-11-15',)),
    ('Injuries and availability', 'Only 6 of 254 rows carry a game designation (brief)', 'Contradicted', 'Official page shows 171 of 347 rows with a designation', 'n/a: the claim is contradicted (F61)', ('nfl-injury-2026-11-15',)),
    ('Injuries and availability', 'Injury designation reliability before use as a feature (play rate per designation)', 'Blocked: data', 'No archived past-season reports or inactive lists in the repo', 'Designation-to-play records across at least one full past season, with intervals', ('nfl-injury-def',)),
    ('Injuries and availability', 'Archive weekly injury reports for past seasons', 'Blocked: data', 'Not in the repo; terms of use not read', 'Archived reports for each past week', ('nfl-injury',)),
    ('Injuries and availability', 'Capture official inactive lists and snap counts', 'Blocked: data', 'No inactive list or snap-count capture; official snap-count source not verified', 'Inactive list for each of the 14 Week 10 games', ('nfl-gamecenter-w10',)),
    ('Injuries and availability', 'Official Game Books for actual starters and game-day status', 'Partial', 'Three Game Books are in the repo (README: Week 9 LAR–WAS, Week 9 NYG–PHI, Week 10 WAS–NYG)', '14 Week 10 Game Books', ('nfl-gamebook-w10',)),
    ('Injuries and availability', 'Availability graph: who was expected to start and who actually did', 'Partial', 'Lineups cover WAS and NYG (Weeks 9–10); the injury excerpt covers WAS and DET only (availability.html)', '32 clubs for each game in scope', ('repo',)),
    ('Injuries and availability', 'Stale depth rows flagged against the official transactions log', 'Not started', 'Transactions log not captured; Baltimore rows not checked', 'Each depth row checked against a dated transaction, for 32 clubs', ('nfl-transactions',)),
    ('Injuries and availability', 'Reserve list captured so "not listed" never means "available"', 'Partial', 'Reserve list not captured; IR for Willis appears only in a headline', 'Reserve-list entries captured for 32 clubs', ('nfl-news-willis-injured-reserve', 'nfl-reserve-list')),
    ('Injuries and availability', 'Announced-starter evidence field (not an inferred replacement)', 'Partial', 'Headlines found for SEA (Lock) and MIA (McCord); Brissett not found', 'A dated announcement for each starter change, with the article linked', ('nfl-news-darnold-ruled-out-lock-start', 'nfl-news-willis-injured-reserve')),
    ('Injuries and availability', 'Populate the three missing Lions designations', 'Verified: no change needed', 'None: the official page and the current pages all show Out', '0 blank Lions designations (confirmed)', ('nfl-injury-2026-11-15',)),
    ('Injuries and availability', 'Per-team view: starters out, replacements named, net injury count', 'Partial', 'Team burden is derived; replacement names need a depth source (row below)', '32 team rows with a starter-out field and a named replacement', ('repo',)),
    ('Injuries and availability', 'Stop publishing raw row-level injury data until the terms are read (public analysis vs private data)', 'Blocked: decision', 'Terms of use for the report rows not read; raw rows are published now (rights note: excerpt only)', 'Terms read and recorded; raw rows moved to a private store', ('nfl-injury',)),
    ('Depth and roster', '32-team roster and IR sweep before any team-level model is trusted', 'Partial', '28 of 32 clubs appear in the Week 10 report; the 4 absent clubs have no published reason', '32 of 32 club roster and IR pages captured with dates', ('nfl-injury-2026-11-15', 'nfl-roster')),
    ('Depth and roster', 'Model depth slots as groups, not a single starter', 'Not started', 'No grouped depth model; slot ties not yet checked', 'Every slot with more than one rank-1 player kept as a group', ('repo',)),
    ('Depth and roster', 'Model depth from playing time, not jersey order', 'Not started', 'No snap-count source captured', 'Snap share for each player on all 32 clubs', ('nfl-player-stats',)),
    ('Depth and roster', 'Official depth-chart register with date and source on every row', 'Partial', 'Charts retrieved for KC, SEA and DET (club pages self-labelled unofficial); 19 more club charts per replacement-chains.html', '32 clubs with a dated, sourced chart', ('chiefs-depth', 'seahawks-depth', 'lions-depth')),
    ('Depth and roster', 'Resolve the depth-order source (route a: club pages; route b: snap counts) before the backup-deficiency feature', 'Blocked: data', 'Route a: charts retrieved for 3 clubs, which the clubs label unofficial; route b has no captured source', 'One route verified for all 32 clubs', ('nfl-depth-chart-404',)),
    ('Depth and roster', 'Texans depth chart (image) and Packers jersey-number prefix', 'Blocked: data', 'Texans chart is an image labelled Unofficial; no authorised structured source found', 'A structured source for the Texans chart (currently 0)', ('houston-depth-image',)),
    ('Depth and roster', 'Shared and empty depth slots represented faithfully', 'Not started', 'Not checked this session', 'Shared (2 players) and empty (0 players) slots kept as their own values', ('repo',)),
    ('Depth and roster', 'Roster turnover as a first-class event (versioned against the last official roster event)', 'Not started', 'Transactions log not captured; Colts trades not checked', 'Dated transaction records for each club', ('nfl-transactions',)),
    ('Depth and roster', 'Matchup deficiency matrix (1st–4th string, offence and defence)', 'Blocked: data', 'Depends on the depth-order source (row above)', '32 clubs with four strings each', ('repo',)),
    ('Schedule, venue and environment', 'Fixture context from published schedule facts only', 'Partial', 'Schedule pages listed as sources; features not built', 'Feature row for each of the 14 Week 10 games', ('nfl-schedule-w10',)),
    ('Schedule, venue and environment', 'Venue of every fixture transcribed from the official game centre and published', 'Not started', 'Not transcribed', 'Venue for every fixture in scope', ('nfl-gamecenter-w10',)),
    ('Schedule, venue and environment', 'Publish the league schedule announcement beside the live schedule page', 'Not started', 'Not captured', 'Dated announcement linked beside each schedule page', ('nfl-schedule-w10',)),
    ('Schedule, venue and environment', 'Stadium roof and surface with the hourly NWS wind and precipitation overlay', 'Not started', 'Not captured', 'Roof and surface for each home venue, and hourly NWS grids for each game', ('repo',)),
    ('Schedule, venue and environment', 'Kickoff and declared onside-kick regime filter (2026 priors)', 'Not started', 'Rule text not checked against the 2026 rulebook', 'Rule-change line checked in the official rulebook', ('nfl-rulebook',)),
    ('Models and strategies', 'Pre-register every strategy; freeze the rule text and commit hash before the window opens', 'Partial', 'No frozen registration commit found for an evaluation window', 'Count of rules frozen with a commit hash before their window (not counted this session)', ('repo',)),
    ('Models and strategies', 'Store every model output as a probability plus its inputs', 'Partial', 'Store keeps fair numbers and an input hash; no per-game probability ledger', 'Every output stored with probability and input hash', ('repo',)),
    ('Models and strategies', 'Singles-only shadow baseline, frozen before kickoff', 'Partial', 'No forecasts recorded before kickoff', 'Recorded forecast for every game in the test window, timestamped before kickoff', ('repo',)),
    ('Models and strategies', 'Opponent-aware ratings from game-level results', 'Built (not validated)', 'No out-of-sample test against prices yet', 'Out-of-sample error against the market on the frozen window', ('repo',)),
    ('Models and strategies', 'Injury and personnel ablations instead of fixed penalties', 'Not started', 'No fitted model exists to ablate', 'Identical model with and without features, chronological holdout, with intervals', ('repo',)),
    ('Models and strategies', 'Train, validation and final holdout seasons', 'Not started', 'Season split not defined in the repo', 'Three disjoint season sets with dates recorded', ('repo',)),
    ('Models and strategies', 'Parlays and prop combos behind a joint-evidence gate', 'Built (gate)', 'No validated joint probability; the dependence gate refuses to price (dependence.html)', 'A validated joint probability and the operator void/push rules', ('repo',)),
    ('Models and strategies', 'Leaderboard divisions with proper scores and uncertainty (singles, parlays, SGP, props)', 'Not started', 'No Brier skill computed on settled NFL forecasts', 'Lower bound on benchmark-relative Brier skill above zero, per division', ('brier',)),
    ('Models and strategies', 'Separate signal from staking on the leaderboard', 'Built', 'None (signal-vs-staking.html)', 'n/a', ('repo',)),
    ('Models and strategies', 'Demotion gate that sends a live strategy back to paper', 'Built', 'No live strategy exists', 'n/a until a strategy goes live', ('repo',)),
    ('Models and strategies', 'Two-sided "what would change our mind" field on every strategy', 'Not started', 'Field not present in the repo (search finds 0 matches)', 'One entry per registered strategy, with both sides', ('repo',)),
    ('Models and strategies', 'Control baseline (random picks, favourites) on every leaderboard run', 'Not started', 'No control run found in the engine', 'Control run recorded with each leaderboard run', ('repo',)),
    ('Models and strategies', '"Removal of luck" panel on the dashboard', 'Not started', 'Needs validated samples', 'Interval on benchmark-relative skill that excludes zero', ('repo',)),
    ('Models and strategies', 'Weekly "what changed" diff of the snapshot', 'Not started', 'Only one weekly store exists', 'Two consecutive weekly snapshots to diff', ('repo',)),
    ('Models and strategies', 'Publish each model total under two estimators with a gap column until walk-forward picks one', 'Not started', 'One total estimator is published', 'Both estimators and the gap column for each total', ('repo',)),
    ('Models and strategies', 'Two-stage leaderboard: proper-score qualification, then prospective CLV/ROI escrow', 'Blocked: data', 'No prospective closing prices', 'Prospective sample with closing prices, per the stage-1 gate', ('repo',)),
    ('Models and strategies', 'Own lines competition with rewards', 'Blocked: decision', 'No funded programme (README)', 'A funding decision and validated strategies', ('repo',)),
    ('Models and strategies', 'Correlations computed only from official numbers, published with n', 'Partial', 'Four correlations published; all fail the predeclared floor (dependence.html)', 'Correlation with n and interval on an official sample', ('repo',)),
    ('Quality, process and governance', 'Drift alarm on every scraper (row counts and required fields)', 'Partial', 'Structure checks only; the Week 10 row errors passed CI (F65)', 'Row-count assertion for each club against the live page, failing the build on mismatch', ('repo',)),
    ('Quality, process and governance', 'Snapshot store kept outside the static site, with freshness and schema alerts', 'Partial', 'Store is in the repo; no alert; no external archive', 'External immutable archive and one alert wired to a source change', ('repo',)),
    ('Quality, process and governance', 'Point-in-time ledger for injuries, depth and inactives', 'Partial', 'Price ledger holds 0 records; injury ledger not built', 'One ledger entry per capture', ('repo',)),
    ('Quality, process and governance', 'Suggestions section for review before any change', 'Built', 'None', 'n/a', ('repo',)),
    ('Quality, process and governance', 'Clear questions, information and answers before a decision', 'Built', 'Open items remain (questions.html)', 'Each open question has an owner and a source', ('repo',)),
    ('Quality, process and governance', 'Executive summary', 'Built', 'None', 'n/a', ('repo',)),
    ('Quality, process and governance', 'Flagged for Review page with source links', 'Built', 'None', 'n/a', ('repo',)),
    ('Quality, process and governance', 'Reject: depth order from jersey number, experience or salary (SG-05)', 'Rejected in brief', 'Rejection recorded in the brief', 'n/a', ('repo',)),
    ('Quality, process and governance', 'Reject: ranking strategies by season-long ROI (SG-03)', 'Rejected in brief', 'Rejection recorded in the brief', 'n/a', ('repo',)),
    ('Quality, process and governance', 'Pull request merged to main with the site verified', 'Blocked: decision', 'The brief makes the merge conditional on all tasks being done; they are not (see COORDINATION.md)', 'All rows above at Built, Verified or Rejected', ('repo',)),
]

STATUS_ORDER = ['Built', 'Built (gate)', 'Built (not validated)', 'Verified: no change needed', 'Partial', 'Not started',
                'Blocked: data', 'Blocked: decision', 'Contradicted', 'Rejected in brief']


def _status_counts():
    c = Counter(r[2] for r in READINESS)
    return c


def _readiness_rows(row):
    return [row(
        [group, req, status, gate, clears],
        srcs,
        'Requirement status (repo evidence)'
    ) for group, req, status, gate, clears, srcs in READINESS]


def _summary_rows(row):
    counts = _status_counts()
    meaning = {
        'Built': 'Implemented in the repo; no validated result claimed',
        'Partial': 'Some of the requirement exists; the gate is stated in the row',
        'Not started': 'Nothing in the repo meets this requirement',
        'Blocked: data': 'Needs a source that is not in the repo or not reachable',
        'Blocked: decision': 'Needs an owner decision before work can proceed',
        'Contradicted': 'The brief states a figure the official page does not show',
        'Rejected in brief': 'The brief itself rejects this approach',
    }
    out = []
    for status in ['Built', 'Built (gate)', 'Built (not validated)', 'Verified: no change needed', 'Partial',
                   'Not started', 'Blocked: data', 'Blocked: decision', 'Contradicted', 'Rejected in brief']:
        if counts.get(status):
            out.append(row([status, str(counts[status]), meaning.get(status, 'See row status')], ('repo',), 'Count from the table below'))
    return out


def _exec_points():
    return [
        'The Week 10 injury page is live and readable. On 15 Nov 2026 it lists 14 games, 28 club tables and 347 player rows, of which 171 carry an Out, Doubtful or Questionable designation. Four clubs (DEN, CHI, PHI, TB) have no table.',
        'The repo capture of the same report agrees on row totals (347) and on 26 of 28 club counts. Two clubs differ: the Chargers (19 rows, every injury and designation cell blank) and the Colts (one designation the official page does not show).',
        'Several claims in the brief are not reproduced (254/279 rows, "4 vs 2" no-injury sections, Seattle and Cincinnati injury-free, the three blank Lions designations). The Lions designations are in fact Out on the official page and on the current pages.',
        'The tracker cannot yet show who was out or replaced in a way that is time-stamped and replayable: there is one dated capture plus this session\'s capture, no hashes, and no scheduled injury job.',
        'Prices are the binding gate. No market line exists, so no fair-line residual, closing-line value, ROI or skill score can be published. The price-close job was writing "closed" with no price; that has been stopped and flagged (F58).',
        'Depth charts are in the repo for 3 clubs (self-labelled unofficial by the clubs), with 19 more retrieved per replacement-chains.html, against 32 needed. Snap counts are not captured. The depth-order route is therefore not yet decided, and the backup-deficiency feature cannot be built on verified data.',
        'Nothing here is a betting recommendation. No strategy has passed a validation gate, and no reward is funded.',
    ]


def register(page, table, row, PAGES, page_date_override):
    # ---- Week 10 official re-check ------------------------------------------------
    club_tbl = table(
        'Club-by-club counts against the official page',
        ['Club', 'Official rows', 'Official designations', 'Repo rows', 'Repo designations', 'Result', 'Note'],
        _club_rows(row),
    )
    counts_tbl = table(
        'Totals',
        ['Measure', 'Official page (15 Nov 2026)', 'Repo capture (14 Nov 2026)', 'Root injuries.html text', 'Brief'],
        [row(['Player rows', '347', '347', 'not stated', '279 (live) / 254 (published)'],
             ('nfl-injury', 'repo'), 'Count'),
         row(['Rows with an Out / Doubtful / Questionable designation', '171', '162', '160 (stated)', '6 of 254'],
             ('nfl-injury', 'repo'), 'Count'),
         row(['Club tables', '28 (14 games)', '28 (14 games)', 'not stated', 'not stated'],
             ('nfl-injury', 'repo'), 'Count'),
         row(['Club tables with no injury description at all', '0', '0', 'not stated', '4 (published) / 2 (live), per brief'],
             ('nfl-injury', 'repo'), 'Count'),
         row(['Clubs absent from the report', ABSENT, ABSENT, 'not stated', 'not stated'],
             ('nfl-injury', 'repo'), 'Count')])
    claims_tbl = table(
        'Claims in the brief, checked one by one',
        ['Claim as stated', 'Verdict', 'What the sources show'],
        _claim_rows(row),
    )
    diffs_tbl = table(
        'Row-level differences (repo capture vs official page)',
        ['Club', 'Player', 'Field', 'Repo capture', 'Official page'],
        _row_diff_rows(row),
    )
    news_tbl = table(
        'Official NFL headlines on starters and reserve status (announced-starter evidence)',
        ['Date (as shown)', 'Headline as published', 'What it does and does not establish'],
        _news_rows(row),
    )
    week10 = (
        '<div class="notice"><strong>Re-verified 15 Nov 2026 against the official page · derived counts only</strong>'
        '<p>The row-level table of the full league report is not republished here: the source notes that it is an excerpt and '
        'that its terms have not yet been read (see F66). Only counts, differences and headlines are shown, each with a link.</p></div>'
        + counts_tbl + claims_tbl + club_tbl + diffs_tbl + news_tbl
        + '<h2>Not re-verified in this session</h2><p>Row-level comparison was done for SEA, CIN, DET, IND and LAC. For the other 23 clubs, '
          'only row and designation counts were compared; a full row-level pass is still open (F69). No Game Book, depth chart, transaction or '
          'snap count was retrieved for this page.</p>'
    )
    page('week10-recheck.html', 'Week 10 re-check',
         'Week 10 re-checked\nagainst the official page',
         'The official NFL injury report, read on 15 Nov 2026, compared with the repo capture. Derived counts, verdicts and differences only, each linked.',
         week10)
    page_date_override['week10-recheck.html'] = '15 Nov 2026'

    # ---- Decision readiness register ------------------------------------------------
    exec_html = '<h2>Executive summary</h2><ul class="plain">' + ''.join(f'<li>{p}</li>' for p in _exec_points()) + '</ul>'
    readiness_tbl = table(
        'Decision readiness: one row per requirement',
        ['Area', 'Requirement', 'Status', 'Blocking gate', 'Number that clears it'],
        _readiness_rows(row),
    )
    summary_tbl = table(
        'Readiness at a glance',
        ['Status', 'Rows', 'Meaning'],
        _summary_rows(row),
    )
    status_note = ('<p class="download">Status key: <b>Built</b> = implemented, no validated result claimed · <b>Partial</b> = some of it exists · '
                   '<b>Not started</b> · <b>Blocked</b> = needs a source or an owner decision · <b>Contradicted</b> = the brief states a figure the official page does not show · '
                   '<b>Rejected in brief</b> = the brief rejects it. See <a href="questions.html">questions</a>, <a href="suggestions.html">suggestions</a> and '
                   '<a href="flags.html">Flagged for Review</a>.</p>')
    readiness_body = exec_html + summary_tbl + status_note + readiness_tbl
    page('readiness.html', 'Decision readiness',
         'Decision readiness\nwhat blocks what',
         'One row per requirement in the brief: the status, the gate that blocks it and the number that would clear it. Blank means not checked.',
         readiness_body)
    page_date_override['readiness.html'] = '15 Nov 2026'

    # ---- Landing page summary ------------------------------------------------------
    counts = _status_counts()
    landing = ('<h2>Decision readiness</h2><p>Of ' + str(len(READINESS)) + ' requirement rows, '
               + str(counts.get('Built', 0) + counts.get('Built (gate)', 0) + counts.get('Built (not validated)', 0)
                     + counts.get('Verified: no change needed', 0))
               + ' are built or verified, ' + str(counts.get('Partial', 0)) + ' are partial, '
               + str(counts.get('Not started', 0)) + ' are not started, '
               + str(counts.get('Blocked: data', 0) + counts.get('Blocked: decision', 0)) + ' are blocked, '
               + str(counts.get('Contradicted', 0)) + ' contradicted by the official page and '
               + str(counts.get('Rejected in brief', 0)) + ' rejected in the brief. '
               '<a href="readiness.html">Open the full register</a> · <a href="week10-recheck.html">Week 10 re-check</a>.</p>')
    if 'index.html' in PAGES:
        label, title, intro, content = PAGES['index.html']
        PAGES['index.html'] = (label, title, intro, content + landing)

    # ---- Flagged for Review additions ----------------------------------------------
    flags_rows = [
        row(['F58 · High', 'The scheduled close job set 52 Week 10 markets to "closed · pre-kickoff capture" with no market price. The job only wrote a timestamp (19:31 UTC, 15 Nov), which is after the 9:30 and 1:00 PM ET kickoffs printed on the official page. The store is restored to its open state, and the job now refuses to write without a closing-price source.',
             'Open-state store restored; job guarded; no closing price claimed.'], ('nfl-injury-2026-11-15', 'repo'), 'Verification finding'),
        row(['F59 · High', 'Chargers rows in the repo capture (session 00cf851d) have every injury and game-status cell blank (19 of 19). The official page lists 10 designations and differs on practice wording for 6 players. Probable cause: a capture taken before later designations were posted; the repo has no per-row timestamp, so this cannot be confirmed.',
             'Listed row by row on the Week 10 re-check page. Not corrected in another session\'s file; request logged.'], ('nfl-injury-2026-11-15', 'repo'), 'Verification finding'),
        row(['F60 · Medium', 'Colts: Arden Key is shown with a Hamstring injury and Questionable on the repo capture and on the root injuries page. The official page shows neither. Cannot tell whether the official page changed or the capture was early.',
             'Shown as a row difference on the Week 10 re-check page.'], ('nfl-injury-2026-11-15', 'repo'), 'Verification finding'),
        row(['F61 · High', 'The brief\'s figures (254 rows, 279 rows, "6 of 254 carry a designation", "4 no-injury sections") do not appear on any current page, and the official page shows 347 rows with 171 designations. The root injuries.html states 160 designated players; the repo capture gives 162. Three different totals are published for the same report.',
             'Claims table on the Week 10 re-check page. Source of the brief figures is unknown: please identify it.'], ('nfl-injury-2026-11-15', 'repo'), 'Verification finding'),
        row(['F62 · Medium', 'The "136-game log" in the brief is not in the repo. The repo lists 121 completed 2026 games. The backtest corpus therefore cannot be built from the repo as it stands.',
             'Listed on the readiness register.'], ('nfl-schedule-w10', 'repo'), 'Unverified item'),
        row(['F63 · High', 'Reference IDs VR-04 to VR-26 and VQ-05 to VQ-08 used in the brief do not appear in any repository file or checked official page. Claims tied only to those IDs are unverified.',
             'Please supply the document that defines these IDs.'], ('repo',), 'Unverified item'),
        row(['F64 · Medium', 'The price-data policy (a precondition for publishing any backtest) and the two-sided "what would change our mind" field are not present in the repo (searches return 0 matches).',
             'Counted as blocked on the readiness register.'], ('repo',), 'Unverified item'),
        row(['F65 · High', 'The Week 10 row errors passed every check in CI. tools/verify.py tests structure and links, not whether values match the live official report, so no drift alarm exists for the injury parser.',
             'Readiness row: scraper drift alarm (partial).'], ('nfl-injury-2026-11-15', 'repo'), 'Process gap'),
        row(['F66 · Medium', 'Terms of use for the NFL injury report have not been read. The repo publishes row-level transcriptions of it on injuries.html and availability.html, and its own rights note calls them an excerpt. The public/private split requested in the brief is therefore not yet in place.',
             'Blocked on the readiness register; the terms have to be read before rows are republished.'], ('nfl-injury', 'repo'), 'Rights question'),
        row(['F67 · Low', 'tools/build.py defines the index page and the page() helper twice; the second definition silently overrides the first, so part of the landing text is dead code.',
             'Recorded; not changed in this session (shared generator).'], ('repo',), 'Repo irregularity'),
        row(['F68 · Low', 'The close-capture schedule is described two ways: tools/pages_9a409d93.py says "Sunday 16:45 UTC and daily 16:00 UTC", while .github/workflows/snapshot.yml runs at 14:00 UTC daily and 23:30 UTC Thursday.',
             'Recorded; the workflow is now a no-op until a price source exists.'], ('repo',), 'Repo irregularity'),
        row(['F69 · Medium', 'Row-level comparison of the Week 10 capture against the official page was completed for 5 clubs (SEA, CIN, DET, IND, LAC). The other 23 clubs were compared on row and designation counts only.',
             'Open item; a full row-level pass is required before the repo table is called verified.'], ('nfl-injury-2026-11-15',), 'Verification gap'),
        row(['F70 · Medium', 'Texans depth chart is an image labelled "Unofficial Depth Chart" on the official club site. It cannot be transcribed without an authorised structured source. The Packers jersey-number prefix and the Colts trades were not checked.',
             'Blocked on the depth-source decision.'], ('houston-depth-image',), 'Unverified item'),
    ]
    flags_tbl = table('Added 15 Nov 2026 (session f5961230)', ['Finding', 'What is known and what is not', 'Next step'], flags_rows)
    label, title, intro, content = PAGES['flags.html']
    PAGES['flags.html'] = (label, title, intro, content + flags_tbl)
