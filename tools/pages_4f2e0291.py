"""Own-lines audit, availability-source register, question ledger and costed suggestions.

Page counts in the directory are read from disk at build time, so a section that grows cannot leave a stale
number behind; the descriptions therefore name contents, not sizes.

Authored by session `arena/4f2e0291-own9`, registered additively through the shared generator so that
nothing another session owns is rewritten: `decision.html`, `questions.html`, `decisions-questions.html`,
`suggestions.html` and `availability.html` stay exactly as their authors published them. These four pages
carry what main had not measured or registered - the committed market-lines file, the official
availability sources and their checked absences, the answered/open question split, and a costed
suggestion sheet with candidate paths and a decision log.

Session `8de532d1`'s decision register is published unchanged on `decisions-questions.html` and is
deliberately not duplicated here.
"""
# Imported the same way tools/verify.py imports the generator: the caller already has
# tools/ on sys.path, so this module needs no path juggling of its own.
from lines_audit import audit
from pathlib import Path

lines = audit()
# Derived here rather than retyped into prose, so every figure on these pages comes from
# tools/lines_audit.py and can be reproduced with `python3 tools/lines_audit.py`.
cov, jn, rc, miss, push = (lines['coverage'], lines['join'], lines['settlement_recompute'],
                           lines['missing_fields'], lines['push_states'])
priced = cov['market_types']['SPREAD'] - miss['odds']['SPREAD']
unpriced_rows = miss['odds']['SPREAD'] + miss['odds']['TOTAL']
unpriced = 100 * unpriced_rows / (cov['market_types']['SPREAD'] + cov['market_types']['TOTAL'])
# Session 8de532d1's decision register is published by main on decisions-questions.html.
preserved_head = preserved_tail = preserved = ''

page('availability-evidence.html', 'Availability sources',
         'Who is out, who replaces them,\nand whether that is a signal.',
         'The official reporting rules, the feeds that carry them, a Week 10 2026 snapshot transcribed from the '
         'league report, and the specification for turning a missing starter into a measurable unit deficiency. '
         'The official reporting rules, the feeds that carry them, a Week 10 2026 snapshot transcribed from the '
         'league report, and the specification for turning a missing starter into a measurable unit deficiency. '
         'Measured-result cells stay blank: no availability edge has been demonstrated.',
         '<div class="notice"><strong>Read together with Injuries &amp; depth</strong><p>Two availability pages are '
         'published and they are not alternatives. <a href="injuries.html">Injuries &amp; depth</a> carries the '
         'broad Week 10 slate and the club depth charts, and <a href="availability.html">Availability tracker</a> '
         'carries the verified Game Book lineup changes. This page records the sources themselves: which official '
         'page publishes which field, what it does not publish, and what was checked and found absent on 14 Nov '
         '2026. The 26 report rows below are the subset transcribed while reading those rules, not the full '
         'week-10 slate, so the row counts on the two pages differ by design rather than by error.</p></div>'
         + table('Official availability sources', ['Source', 'What the page publishes', 'Retrieved',
                                                 'Limits / use here'], [
             row(['Club injury report', 'Club-by-club report grouped by upcoming game, with Player, Position, '
                  'Injuries, Practice Status and Game Status columns, plus a season and week selector.',
                  '14 Nov 2026', 'Blank cells stay blank. No historical archive and no per-row timestamp is '
                  'published on the page.'], ('nfl-injury',), 'Official publication · transcribed'),
             row(['Participation and status definitions', 'Practice Report uses Did Not Participate, Limited '
                  'Participation (under 100 percent of normal repetitions) or Full Participation (100 percent). '
                  'Game Status: Questionable uncertain, Doubtful unlikely, Out will not play.', '14 Nov 2026',
                  'Defines labels only. The league attaches no probability to any label.'],
                 ('nfl-injury-def',), 'Official policy text'),
             row(['Deactivation rule', 'A player certain to play is left off the Game Status Report; if that player '
                  'is then deactivated, the club must explain to the league and faces possible discipline.',
                  '14 Nov 2026', 'The published policy text; the game-day inactive list is not on this page.'],
                 ('nfl-injury-def',), 'Official policy text'),
             row(['Reserve-list transactions', 'Dated Reserve/Injured and other reserve moves per club, by month, '
                  'with a year selector reaching 1965.', '14 Nov 2026', 'The Position column was empty on the rows '
                  'read. No severity or return timeline is published.'],
                 ('nfl-reserve-list', 'nfl-transactions'), 'Official publication · transcribed'),
             row(['Club roster status codes', 'Roster table lists Player, Number, Position, Status, Height, Weight, '
                  'Experience and College. Status values observed: ACT, DEV, PUP, RES, RSR, TRC and TRD. The page '
                  'links out to a club depth chart.', '14 Nov 2026', 'The page does not define its own codes, so '
                  'they are recorded as observed strings and never interpreted.'],
                 ('nfl-roster-status',), 'Official publication · observed'),
             row(['Reserve and elevation mechanics', 'Return designation costs four elapsed games; eight returns per '
                  'season; at most twice per player; practice squads of 16; up to three game-day elevations per '
                  'practice-squad player per season (2022 rules).', '14 Nov 2026', 'Season-ending placement, '
                  'PUP/NFI mechanics and practice-window length are not in this text and are not asserted.'],
                 ('nfl-ir-rules',), 'Official rule-change report'),
             row(['Official player statistics', 'Eleven categories: passing, rushing, receiving, fumbles, tackles, '
                  'interceptions, field goals, kickoffs, kickoff returns, punting and punt returns, by season and '
                  'week.', '14 Nov 2026', 'No snap-count, route-participation or playing-time category is offered, '
                  'so per-play rates cannot be built from this page alone.'],
                 ('nfl-stats-cats',), 'Official publication · absence noted'),
             row(['Next Gen Stats section', 'An index of advanced-metric articles and explainers, including '
                  'coverage responsibility, completion probability and expected points added.', '14 Nov 2026',
                  'An editorial index. No dataset, field list, licence or historical coverage was verified, so NGS '
                  'is not treated as an available input.'], ('nfl-ngs',), 'Official index · not a feed'),
             row(['League depth chart', 'Retrieving the club depth-chart path on NFL.com returned the site 404 '
                  'page, and team pages route depth-chart requests to club websites instead.', '14 Nov 2026',
                  'A dated negative observation of one path, recorded as a gap in our evidence. It is not proof '
                  'that no official league chart exists anywhere.'], ('nfl-no-depth-chart',),
                  'Checked · not published'),
             row(['Club depth chart', 'Position-group tables with first, second, third and fourth string columns. '
                  'The Patriots page states its 2026 chart is unofficial, is published by that site\u2019s writers '
                  'and does not necessarily reflect the organization.', '14 Nov 2026',
                  'Self-declared unofficial. Usable as a depth-ordering observation only, never as a league fact '
                  'or a settlement input.'], ('club-depth-chart',), 'Club publication · unofficial by label'),
         ])

         + table('Week 10 2026 report entries, transcribed',
                 ['Player', 'Club', 'Pos', 'Injury as listed', 'Practice status', 'Game status'], [
             row([name, club, pos, inj, prac, game], ('nfl-injury',), 'Verbatim official fields') for name, club,
                 pos, inj, prac, game in [
                 ('A.J. Brown', 'NE', 'WR', 'Ankle, Knee', 'Limited Participation in Practice', 'Questionable'),
                 ('Rhamondre Stevenson', 'NE', 'RB', 'Knee', 'Limited Participation in Practice', 'Questionable'),
                 ('TreVeyon Henderson', 'NE', 'RB', 'Illness', 'Did Not Participate In Practice', 'Out'),
                 ('Ben Brown', 'NE', 'C', 'Knee', 'Did Not Participate In Practice', 'Out'),
                 ('Carlton Davis III', 'NE', 'CB', 'Knee', 'Did Not Participate In Practice', 'Out'),
                 ('Kevin Byard', 'NE', 'S', 'Chest', 'Full Participation in Practice', 'Questionable'),
                 ('Walter Rouse', 'NE', 'T', 'Concussion', 'Limited Participation in Practice', 'Questionable'),
                 ('Brenden Schooler', 'NE', 'S', 'Hamstring', 'Limited Participation in Practice', 'Questionable'),
                 ('Greg Van Roten', 'NE', 'G', 'Hamstring', 'Full Participation in Practice', 'Questionable'),
                 ('Drake Maye', 'NE', 'QB', None, 'Full Participation in Practice', None),
                 ('Amon-Ra St. Brown', 'DET', 'WR', 'Rib', 'Limited Participation in Practice', 'Questionable'),
                 ('Kerby Joseph', 'DET', 'S', 'Knee', 'Did Not Participate In Practice', 'Out'),
                 ('D.J. Reed', 'DET', 'CB', 'Hip', 'Did Not Participate In Practice', 'Out'),
                 ('Cade Mays', 'DET', 'C', 'Ankle', 'Did Not Participate In Practice', 'Out'),
                 ('Brian Branch', 'DET', 'S', None, 'Full Participation in Practice', None),
                 ('Jared Goff', 'DET', 'QB', None, 'Full Participation in Practice', None),
                 ('Lucas Patrick', 'WAS', 'C', 'Concussion', 'Did Not Participate In Practice', 'Out'),
                 ('Colson Yankoff', 'WAS', 'TE', 'Knee', 'Did Not Participate In Practice', 'Out'),
                 ('Treylon Burks', 'WAS', 'WR', None, 'Did Not Participate In Practice', None),
                 ('Amik Robertson', 'WAS', 'CB', None, 'Limited Participation in Practice', None),
                 ('Jayden Daniels', 'WAS', 'QB', None, 'Full Participation in Practice', None),
                 ('Malik Harrison', 'NYG', 'LB', 'Groin', 'Limited Participation in Practice', 'Questionable'),
                 ('Abdul Carter', 'NYG', 'LB', None, 'Full Participation in Practice', None),
                 ('Mansoor Delane', 'KC', 'CB', 'Shoulder', 'Full Participation in Practice', 'Questionable'),
                 ('Patrick Mahomes', 'KC', 'QB', None, 'Full Participation in Practice', None),
                 ('Travis Kelce', 'KC', 'TE', None, 'Full Participation in Practice', None),
         ]])

         + table('Reserve-list moves forcing a depth promotion',
                 ['Player', 'Club', 'Dated', 'Transaction as published', 'Position as published'], [
             row([name, club, date, 'Reserve/Injured', None], ('nfl-reserve-list',), 'Verbatim official fields')
             for name, club, date in [
                 ('Puka Nacua', 'LA', '11/12'), ('Jordan Whittington', 'LA', '11/10'),
                 ('Zach Sieler', 'MIA', '11/10'), ('Malik Willis', 'MIA', '11/10'),
                 ('Gardner Minshew', 'AZ', '11/10'), ('Michael Wilson', 'AZ', '11/10'),
                 ('James Williams', 'TEN', '11/09'), ('Demond Claiborne', 'MIN', '11/09'),
                 ('Josh Palmer', 'BUF', '11/09'), ('Brian Robinson', 'ATL', '11/07'),
                 ('Jaylen Watson', 'LA', '11/07'), ('Jack Campbell', 'DET', '11/07'),
                 ('Christian Kirk', 'SF', '11/07'),
         ]])

         + table('Worked deficiency examples', ['Unit', 'Published depth order', 'Availability overlap',
                                                 'What can and cannot be claimed'], [
             row(['Patriots running back', 'Club chart lists Rhamondre Stevenson, then TreVeyon Henderson, Corey '
                  'Kiner and Lan Larison.', 'First string Questionable (knee, limited); second string Out (illness, '
                  'did not practice).', 'Third and fourth string would carry the load. The club chart is '
                  'self-declared unofficial, and no official snap data exists to size the shift.'],
                 ('club-depth-chart', 'nfl-injury'), 'Official fields + unofficial ordering'),
             row(['Patriots interior line', 'Club chart lists Jared Wilson at centre with Ben Brown second, and Ben '
                  'Brown at guard with Walter Rouse second.', 'Ben Brown Out (knee); Rouse Questionable '
                  '(concussion, limited).', 'One player occupies two depth slots, so a single absence cascades. '
                  'No injury report field records that overlap.'],
                 ('club-depth-chart', 'nfl-injury'), 'Official fields + unofficial ordering'),
             row(['Patriots cornerback', 'Club chart lists Carlton Davis III first, Marcus Jones second.',
                  'Davis Out (knee, did not practice).', 'A starting perimeter corner is confirmed absent. '
                  'Whether the opponent targets that side is not observable in official data.'],
                 ('club-depth-chart', 'nfl-injury'), 'Official fields + unofficial ordering'),
             row(['Lions secondary', None, 'Kerby Joseph Out (knee) and D.J. Reed Out (hip), both listed did not '
                  'participate.', 'Two unavailable defensive backs in one week is measurable. The Detroit depth '
                  'ordering was not retrieved in this session, so string positions remain unverified.'],
                 ('nfl-injury',), 'Official fields · ordering not retrieved'),
             row(['Lions centre', None, 'Jack Campbell placed on Reserve/Injured 11/07; Cade Mays Out (ankle) in '
                  'the 10 Nov report.', 'Both rows are centre-position entries in the sources read, so at least '
                  'two players at one position were unavailable at once. Campbell\u2019s transaction row has no '
                  'position value, so this rests on the report entry alone.'],
                 ('nfl-injury', 'nfl-reserve-list'), 'Official fields · ordering not retrieved'),
         ])

         + table('Deficiency model specification', ['Component', 'Definition', 'Input source', 'Status'], [
             row(['Availability state', 'The final game-status label per player per game, plus participation over '
                  'the week; the game-day inactive list is terminal.', 'Club injury report', 'Available, current '
                  'only'], ('nfl-injury', 'nfl-injury-def'), 'Official definitions'),
             row(['String ordering', 'Which player is first, second, third or fourth at a position.',
                  'No league source; club charts only, self-declared unofficial', 'Not officially available'],
                 ('nfl-no-depth-chart', 'club-depth-chart'), 'Checked absence / club substitute'),
             row(['Replacement quality', 'Difference between the baseline player\u2019s prior production and the '
                  'replacement\u2019s, per role.', 'Official category statistics, but they are cumulative counting '
                  'stats without a participation denominator', 'Blocked: no official per-play denominator'],
                 ('nfl-stats-cats',), 'Official limits'),
             row(['Exposure shift', 'How much playing time moves to the replacement and to the unit.',
                  'No official snap-count or participation feed located', 'Not available'],
                 ('nfl-stats-cats', 'nfl-ngs'), 'Checked absence'),
             row(['Unit deficiency index', 'Project definition: weighted sum over affected roles of baseline minus '
                  'replacement value, with unavailable components left as missing, never zero.',
                  'Project specification', 'Proposed, unvalidated'], ('repo',), 'Project specification'),
             row(['Defensive response', 'Whether an offence attacks the weakened side, and by how much.',
                  'No official targeting-by-side data in the sources read', 'Unverified'], ('nfl-ngs',),
                  'Proposal · no input found'),
         ])

         + table('Availability signal candidates', ['ID · track', 'Proposed signal', 'Official inputs required',
                                                     'Required ablation', 'Measured NFL value', 'State'], [
             row(['AV1 · Game single', 'When a first- or second-string player on one side of the ball is Out or '
                  'moved to Reserve/Injured and the replacement crosses a declared threshold, test whether the '
                  'origination line should move more than the market did.', 'Injury report, reserve list, club '
                  'roster status, prior season team and player statistics',
                  'Remove the replacement-quality term and re-run; a signal that survives without it is a '
                  'name-recognition effect, not a deficiency effect.', None, 'Unvalidated'],
                 ('nfl-injury', 'nfl-reserve-list', 'nfl-stats-cats'), 'Official inputs / proposal'),
             row(['AV2 · Player prop', 'An unavailable primary target redistributes volume to the next receiver or '
                  'the tight end; price the redistribution, not the missing player.', 'Injury report, depth '
                  'ordering, receiving statistics',
                  'Exposure-only baseline: project the replacement from snap-free counting share alone and compare.',
                  None, 'Unvalidated'], ('nfl-injury', 'club-depth-chart', 'nfl-stats-cats'),
                 'Official inputs / proposal'),
             row(['AV3 · Game single', 'Quarterback differential: the starter is Out and the replacement has fewer '
                  'than a declared number of prior career pass attempts.', 'Injury report, reserve list, passing '
                  'statistics by season', 'Split by home or away and by rest days; a uniform effect across splits '
                  'is a market-overreaction claim, a split-only effect needs a predeclared interaction.', None,
                  'Unvalidated'], ('nfl-injury', 'nfl-stats-cats'), 'Official inputs / proposal'),
             row(['AV4 · Feature, not a bet', 'Practice trajectory over the week predicts game availability, which '
                  'is an input to any availability signal rather than a tradable edge.',
                  'Daily participation reports and the final status list',
                  'Test whether trajectory adds anything to the published status label; if not, drop it.', None,
                  'Unvalidated'], ('nfl-injury-def', 'nfl-injury'), 'Official definitions / proposal'),
             row(['AV5 · Game single', 'Line-cascade detector: two or more unavailable players at the same '
                  'position, or one player occupying two depth slots.', 'Injury report, club roster, club depth '
                  'ordering', 'Hold out the cascade term and test whether the single-absence effect already '
                  'explains the movement.', None, 'Unvalidated'],
                 ('nfl-injury', 'nfl-roster-status', 'club-depth-chart'), 'Official inputs / proposal'),
             row(['AV6 · Filter', 'Separate managed rest from genuine limitation: full participation with no status '
                  'label, versus limited all week with the same label.', 'Participation report and status '
                  'definitions', 'Publish the abstention count the filter causes; a filter that only reduces '
                  'sample size is not a signal.', None, 'Unvalidated'], ('nfl-injury-def', 'nfl-injury'),
                 'Official definitions / proposal'),
         ])

         + table('Availability data contract', ['Required field', 'Needed value', 'Available today',
                                                 'Point-in-time capture required'], [
             row(['Game identifier', 'A stable key shared with scores and prices', 'Partly: the two repository '
                  'snapshots join only through an alternate identifier', 'Yes'], ('repo',), 'Repository audit'),
             row(['Report publication time', 'A timestamp proving what was known when', 'No per-row timestamp on '
                  'the report page', 'Yes: capture and hash each daily report'], ('nfl-injury',),
                  'Official scope · gap'),
             row(['Final inactive list', 'Terminal availability per game', 'Not published on the report page read',
                  'Yes'], ('nfl-injury',), 'Official scope · gap'),
             row(['Depth ordering', 'First through fourth string per position', 'Club charts only, unofficial',
                  'Yes: club pages change without notice'], ('club-depth-chart',), 'Club substitute'),
             row(['Participation denominator', 'Snaps or routes per player per game', 'No official feed located',
                  'Blocked until a licensed source exists'], ('nfl-stats-cats', 'nfl-ngs'), 'Checked absence'),
             row(['Executable price at report time', 'A quote attached to each availability event',
                  'Only 2006-2018 locally, and most of that unpriced', 'Yes: prices move as news lands'],
                 ('repo',), 'Repository audit'),
         ])

         + '<p>Reading the two transcribed tables together is the whole method: the report says who is '
           'unavailable, the reserve list says who will stay unavailable, and a depth ordering \u2014 which the '
           'league does not publish \u2014 says who has to fill in. Everything after that is modelling, and every '
           'measured column above is blank because the aligned price data has not been obtained. See <a '
           'href="questions.html">the question ledger</a> for what is answerable now and <a href="lines.html">own '
           'lines</a> for the market side.</p>')

page('lines.html', 'Own lines',
         'Originate the number.\nThen defend it.',
         'What we can compute from the market data already in this repository, what that data cannot support, and '
         'the pipeline a self-originated NFL line has to pass before it is worth a bet. Values below are computed '
         'from the committed files at build time by tools/lines_audit.py.',
         table('Market data audit', ['Measure', 'Value', 'What it means', 'Where to check'], [
             row(['Rows in the local lines snapshot', f"{lines['files']['closing_lines']['rows']:,} rows",
                  'Three market types, recorded one row per side.', 'data/raw/closing_lines.csv'], ('repo',),
                 'Computed from the file'),
             row(['Market types', ' · '.join(f'{k} {v:,}' for k, v in sorted(cov['market_types'].items())),
                  'Equal row counts per type, consistent with one pair of sides per market.',
                  'tools/lines_audit.py'], ('repo',), 'Computed from the file'),
             row(['Games and seasons covered', f"{cov['games']:,} games · {cov['season_min']}\u2013{cov['season_max']}",
                  'Coverage stops eight seasons before the current one, so no recent-season or current-week '
                  'evaluation is possible from this file.', 'data/raw/closing_lines.csv'], ('repo',),
                 'Computed from the file'),
             row(['Join to the score snapshot', f"{jn['as_named_game_id']} of {jn['total_games']} on the column "
                  f"named game_id · {jn['via_old_game_id']} of {jn['total_games']} on the alternate identifier",
                  'The published key does not join; an alternate identifier does, on every game. Any pipeline must '
                  'be written against the alternate key.', 'tools/lines_audit.py'], ('repo',),
                 'Computed from the file'),
             row(['Settlement recomputation', f"{rc['agree']['MONEYLINE']:,} / {rc['agree']['SPREAD']:,} / "
                  f"{rc['agree']['TOTAL']:,} rows agree by type",
                  'Outcomes were recomputed from the sibling score snapshot and compared row by row, with club '
                  'abbreviations normalised for 2016\u20132018 relocations.', 'tools/lines_audit.py'], ('repo',),
                 'Computed from the file'),
             row(['Rows that disagree', f"{rc['disagree_rows']} of {lines['files']['closing_lines']['rows']:,} "
                  f"({rc['disagree_pct']}%) across {rc['affected_games']} games, "
                  f"{rc['fully_inverted_games']} games fully inverted",
                  'A small, whole-game inversion pattern rather than scattered noise. Those games must be excluded '
                  'or corrected before any use.', 'tools/lines_audit.py'], ('repo',), 'Computed from the file'),
             row(['Missing prices', f"{miss['odds']['SPREAD']:,} spread and {miss['odds']['TOTAL']:,} total rows "
                  f"without odds ({priced:,} priced)",
                  'Expected value cannot be computed for a market without a price, so most of this file cannot '
                  'support an economics test.', 'tools/lines_audit.py'], ('repo',), 'Computed from the file'),
             row(['Push handling', f"spread {push['coded_0.5']['SPREAD']}, total {push['coded_0.5']['TOTAL']}, "
                  f"moneyline {push['coded_0.5']['MONEYLINE']} rows coded as a tie",
                  f"All {push['spread_push_rows_matching_margin']} spread pushes match the margin exactly, and the "
                  f"{push['moneyline_push_games']} tied games are games the score snapshot records as ties in "
                  f"overtime. The push coding is internally correct.", 'tools/lines_audit.py'], ('repo',),
                 'Computed from the file'),
             row(['File identity', lines['files']['closing_lines']['sha256'],
                  'Pinned so a later audit can prove it read the same bytes.', 'data/raw/closing_lines.csv'],
                 ('repo',), 'Computed from the file'),
             row(['Provenance and licence', 'Not recorded anywhere in the repository',
                  'No source, retrieval date or redistribution permission accompanies the file. It is quarantined '
                  'for use, not deleted, pending an owner decision.', 'COORDINATION.md'], ('repo',),
                 'Flagged · unverified'),
         ])

         + table('What a usable lines archive must contain', ['Requirement', 'Why it is required', 'Current state'], [
             row(['Timestamped open and close quotes', 'Gate 2 forbids using information published after issuance.',
                  'Absent: the snapshot carries a settled result but no quote time'], ('repo',), 'Blocking gap'),
             row(['A written sign convention', 'A home-minus-away margin and an away-minus-home margin differ only '
                  'by sign, and a wrong sign silently inverts every result.',
                  'Absent: no dictionary accompanies the file'], ('repo',), 'Blocking gap'),
             row(['Settlement rules per market', 'Push, void and reduced-payout handling changes the payout state, '
                  'not just the price.', 'Partly derivable from the tie coding; no rule text'], ('repo',),
                 'Partial'),
             row(['A joinable game key', 'Every availability, score and price record must be the same game.',
                  'Only through the alternate identifier'], ('repo',), 'Workaround documented'),
             row(['Redistribution rights', 'Publishing prices from an operator or vendor needs a licence.',
                  'Unverified for every inherited file'], ('repo',), 'Legal review needed'),
             row(['Current-season coverage', 'A line origination system is judged on live games.',
                  f'Ends at {cov["season_max"]}'], ('repo',), 'Blocking gap'),
             row(['More than one price source', 'A single book measures that book, not the market.',
                  'Single undifferentiated source'], ('repo',), 'Blocking gap'),
             row(['Immutable capture log', 'Reproducible research cannot depend on a page that can change.',
                  'None; this release adds hash pinning as the first step'], ('repo',), 'Started here'),
         ])

         + table('Own-line origination pipeline', ['Stage', 'Specification', 'Status'], [
             row(['1 · Game universe', 'One row per scheduled game with a stable key, kickoff time and both club '
                  'identifiers.', 'Primitive not yet wired to the alternate key'], ('repo',), 'Project scope'),
             row(['2 · Availability state', 'Per-player participation and game status per day, plus reserve-list '
                  'moves, captured with a timestamp before kickoff.', 'Specification only'],
                 ('nfl-injury', 'nfl-reserve-list'), 'Inputs identified'),
             row(['3 · Unit priors', 'Team-level scoring and possession rates from official statistics, adjusted for '
                  'opponent and rest.', 'Not implemented'], ('nfl-stats',), 'Proposed'),
             row(['4 · Joint score distribution', 'A grid over final home and away scores, fitted by penalised '
                  'likelihood, with overtime handled as an extension of the same grid.',
                  'Distribution-first design specified; no fit'], ('repo',), 'Design only'),
             row(['5 · Fair line extraction', 'A fair spread is the value making the cover probability the no-push '
                  'break-even, not the mean margin; a fair total sums mass above the threshold and keeps equality '
                  'as a push.', 'Implemented as arithmetic primitives with tests'], ('repo',),
                 'Unit-tested maths'),
             row(['6 · Market comparison', 'Normalise inverse decimal prices across a mutually exclusive, exhaustive '
                  'set of no-push outcomes to read the market line.', 'Implemented; no verified input to run it on'],
                 ('repo',), 'Unit-tested maths'),
             row(['7 · Quote and abstain', 'Publish the own line with an uncertainty band, and withhold whenever '
                  'availability, price or model support is missing.', 'Policy proposed'], ('holdout',), 'Proposed'),
             row(['8 · Replay and score', 'Strictly proper scoring against settled outcomes, paired with the market, '
                  'under the seven gates.', 'Blocked on data'], ('logloss', 'brier'), 'Blocked'),
         ])

         + table('Price-snapshot store — opening and closing per market', ['Field', 'Definition', 'Required for a write'], [
             row(['game_id', 'Stable game identifier shared with scores and availability', 'Yes'], ('repo',), 'Project record'),
             row(['market', 'MONEYLINE, SPREAD or TOTAL', 'Yes'], ('repo',), 'Project record'),
             row(['side', 'HOME/AWAY for moneyline/spread; OVER/UNDER for total', 'Yes'], ('repo',), 'Project record'),
             row(['line', 'Handicap or total value (absent for moneyline)', 'Yes, when market is SPREAD or TOTAL'], ('repo',), 'Project record'),
             row(['decimal_price', 'Decimal odds (must exceed 1)', 'Yes'], ('repo',), 'Project record'),
             row(['quote_utc', 'ISO-8601 UTC capture time', 'Yes'], ('repo',), 'Project record'),
             row(['operator', 'Sportsbook or venue that issued the quote', 'Yes'], ('repo',), 'Project record'),
             row(['jurisdiction', 'Regulatory jurisdiction of the quote', 'Yes'], ('repo',), 'Project record'),
             row(['opening_utc', 'When this market first opened', 'No — optional'], ('repo',), 'Project record'),
             row(['closing_utc', 'When this market closed (if known)', 'No — optional'], ('repo',), 'Project record'),
             row(['is_closing', 'True if this is the closing snapshot', 'No — defaults to false'], ('repo',), 'Project record'),
             row(['settlement_rule', 'Operator citation for push/void handling', 'No — optional'], ('repo',), 'Project record'),
         ])
         + table('Verified results feed — official outcomes', ['Field', 'Definition', 'Required for a write'], [
             row(['game_id', 'Stable game identifier shared with prices and availability', 'Yes'], ('repo',), 'Project record'),
             row(['season', 'NFL season year', 'Yes'], ('repo',), 'Project record'),
             row(['week', 'Week number (1-22)', 'Yes'], ('repo',), 'Project record'),
             row(['home_team', 'Home club identifier', 'Yes'], ('repo',), 'Project record'),
             row(['away_team', 'Away club identifier', 'Yes'], ('repo',), 'Project record'),
             row(['home_score', 'Final home score', 'Required for FINAL status'], ('repo',), 'Project record'),
             row(['away_score', 'Final away score', 'Required for FINAL status'], ('repo',), 'Project record'),
             row(['status', 'SCHEDULED, IN_PROGRESS, FINAL, POSTPONED, CANCELLED', 'Yes'], ('repo',), 'Project record'),
             row(['source_url', 'Official NFL page or Game Book URL', 'Yes'], ('repo',), 'Project record'),
             row(['retrieved_utc', 'ISO-8601 UTC capture time', 'Yes'], ('repo',), 'Project record'),
             row(['overtime', 'Whether the game went to overtime', 'No — optional'], ('repo',), 'Project record'),
             row(['total_line', 'The official total line at settlement', 'No — optional'], ('repo',), 'Project record'),
             row(['spread_line', 'The official spread line at settlement', 'No — optional'], ('repo',), 'Project record'),
         ])
         + table('Line origination order — mandated sequence', ['Step', 'Market', 'Notes'], [
             row(['1', 'Side (spread / handicap)', 'Originated first: every spread market gets its own fair line before totals are touched'], ('repo',), 'Pipeline rule'),
             row(['2', 'Total (over / under)', 'Originated second, after side; mass above threshold with equality as push'], ('repo',), 'Pipeline rule'),
             row(['3', 'Moneyline', 'Originated third, after side and total; fair price from modelled win probability'], ('repo',), 'Pipeline rule'),
         ])
         + table('Fair line / market line / difference columns', ['Market', 'Fair line', 'Market line', 'Difference'], [
             row(['Spread (home)', None, None, None], ('repo',), 'Blank until joint distribution and executable quotes exist'),
             row(['Total', None, None, None], ('repo',), 'Blank until joint distribution and executable quotes exist'),
             row(['Moneyline (home)', None, None, None], ('repo',), 'Blank until win probability and executable quotes exist'),
             row(['Moneyline (away)', None, None, None], ('repo',), 'Blank until win probability and executable quotes exist'),
         ])
         + '<p class="notice"><strong>All three columns stay blank until inputs are verified.</strong> Fair line comes from the joint score distribution (not yet fitted). Market line comes from proportional de-vig of executable quotes (no source yet). Difference is fair minus market, computed only when both exist. None is not zero; it means the value cannot be produced yet.</p>'
         + table('Current own-line standing', ['Item', 'Value', 'Disposition'], [
             row(['Numerical line published for any 2026 game', None, 'Not produced: no fitted model exists in this '
                  'repository'], ('repo',), 'Not implemented'),
             row(['Own-line error against market', None, 'Blank. An inherited secondary-data subtree reports a mean '
                  'absolute error figure, but its inputs are unverified and this dashboard does not adopt the value.'],
                 ('repo',), 'Unverified · see Flagged for Review'),
             row(['Measured correlation between legs', None, 'Blank. See the correlation register.'],
                 ('pearson',), 'Unverified'),
             row(['Strategies passing all seven gates', 'None', 'Eligibility fails closed when an input is missing.'],
                 ('repo',), 'Zero eligible'),
             row(['Backtest on the local lines snapshot', None, f"Not run: {unpriced:.1f}% of spread and total "
                  f"rows carry no price, coverage ends in {lines['coverage']['season_max']}, and provenance is "
                  'unrecorded.'], ('repo',), 'Not run'),
         ])

         + '<p>The file in <code>data/raw/</code> is a real dataset, and this release is the first to measure it '
           'instead of describing it as absent. It is also too incomplete and too undocumented to support a claim '
           'of any kind, so it is quarantined and published on <a href="flags.html">Flagged for Review</a> as F22. '
           'The decision the owner has to make is whether to licence a current source or build a prospective '
           'capture archive from now on; <a href="suggestions.html">S04</a> and <a href="suggestions.html">S05</a> '
           'set out both paths.</p>')

page('question-ledger.html', 'Question ledger',
         'What has to be answered\nbefore a decision is defensible.',
         'Every question splits into four states: answered from an official source, answered from this repository, '
         'open and fixable with data work, or open and needing an owner decision. A question is never closed by '
         'inference, and nothing here was answered by asking you.',
         ''
         + table('Answered from official sources', ['ID', 'Question', 'Answer now established', 'Residual uncertainty'], [
             row(['Q01', 'Does the league publish an injury report at all, and in what form?',
                  'Yes: a club-by-club report grouped by upcoming game with Player, Position, Injuries, Practice '
                  'Status and Game Status, selectable by season and week.', 'The report carries no publication '
                  'timestamp per row.'], ('nfl-injury',), 'Answered · official'),
             row(['Q02', 'What do Questionable, Doubtful and Out actually mean?',
                  'Uncertain, unlikely and will not play. Limited Participation is under 100 percent of normal '
                  'repetitions; Full Participation is 100 percent.', 'The league attaches no probability to the '
                  'labels, so any play-probability number is a model output to be estimated, never a definition.'],
                 ('nfl-injury-def',), 'Answered · official'),
             row(['Q03', 'Is a blank game-status cell the same as healthy?',
                  'No. A player certain to play is deliberately left off the status report, and the policy instead '
                  'requires an explanation if that player is later deactivated.', 'The report alone cannot '
                  'distinguish certain-to-play from unreported; the inactive list is the terminal record.'],
                 ('nfl-injury-def', 'nfl-injury'), 'Answered · official'),
             row(['Q04', 'How long does a reserve placement keep a player out?',
                  'Under the 2022 rule change a designated player returns after four elapsed games, with eight '
                  'returns permitted per club per season and at most two per player.', 'Practice-window length, '
                  'season-ending placement and playoff allocations are not in the text read.'],
                 ('nfl-ir-rules',), 'Answered · official'),
             row(['Q05', 'How do replacement players arrive, and how fast?',
                  'Practice squads of 16, elevable to the game-day roster at most three times per player per season, '
                  'plus trades, signings and waivers published as dated league transactions.',
                  'Elevation counts are per player per season; a club\u2019s remaining eligibility is not shown on '
                  'the transaction rows.'], ('nfl-ir-rules', 'nfl-transactions'), 'Answered · official'),
             row(['Q06', 'Does the league publish depth charts?',
                  'No league depth chart was found: the club depth-chart path on the league site returns a 404 and '
                  'team pages route the request to club websites.', 'A dated negative observation of one path, not a '
                  'proof of non-existence; the register carries it as F13, F17 and F19.'], ('nfl-no-depth-chart',), 'Answered · checked absence'),
             row(['Q07', 'Can a depth ordering be obtained anyway?',
                  'Only from club sites, and the one read states its chart is unofficial, written by that site\u2019s '
                  'writers and not necessarily reflecting the organization. It does provide first through fourth '
                  'string columns.', 'Opinion-based and unversioned: it can change without notice and cannot be '
                  'reconstructed for past weeks.'], ('club-depth-chart',), 'Answered · substitute source'),
             row(['Q08', 'Is there an official snap-count or participation feed?',
                  'No. The official player-statistics page exposes eleven counting categories and no playing-time '
                  'or route-participation category.', 'Per-play denominators therefore cannot be built from the '
                  'official page, which blocks per-play replacement quality.'], ('nfl-stats-cats',),
                 'Answered · checked absence'),
             row(['Q09', 'Does advanced on-field data exist at all?',
                  'A Next Gen Stats section publishes metric explainers including coverage responsibility and '
                  'expected points added.', 'It is an editorial index. No dataset, field list, licence or historical '
                  'coverage was verified, so it is not treated as an available input.'], ('nfl-ngs',),
                 'Partly answered'),
             row(['Q10', 'Are wagering lines published by the league?',
                  'No. No official league page publishes lines, so any line used here is a project output or a '
                  'licensed third-party quote.', 'This is the reason gate 1 has never passed and remains the single '
                  'largest dependency in the project.'], ('nfl-stats', 'repo'), 'Answered · structural gap'),
         ])

         + table('Answered from this repository', ['ID', 'Question', 'Answer now established', 'Residual uncertainty'], [
             row(['Q11', 'Is there any historical price data already in the repository?',
                  'Yes, and this release is the first to measure it: a closing-lines snapshot of '
                  f"{audit()['files']['closing_lines']['rows']:,} rows over "
                  f"{audit()['coverage']['games']:,} games, seasons 2006 to 2018.",
                  'Provenance, retrieval date and redistribution rights are recorded nowhere.'], ('repo',),
                 'Answered · measured locally'),
             row(['Q12', 'Is that snapshot self-consistent?',
                  f"Largely: after normalising 2016\u20132018 club abbreviations, {rc['disagree_rows']} of "
                  f"{audit()['files']['closing_lines']['rows']:,} rows ({rc['disagree_pct']}%) disagree with "
                  f"outcomes recomputed from the sibling score snapshot, concentrated in {rc['affected_games']} "
                  f"games, {rc['fully_inverted_games']} of them fully inverted.",
                  'Recomputation is a relative consistency check; the scores themselves are second-hand.'],
                 ('repo', 'nfl-gamecenter-score'), 'Answered · measured locally'),
             row(['Q13', 'Can it be used for a backtest today?',
                  'No: coverage ends in 2018, and thousands of spread and total rows carry no price, so expected '
                  'value is undefined for them.', 'A cleaned 2006\u20132018 subset could support methodology tests '
                  'only, never a claim about current markets.'], ('repo',), 'Answered · blocked'),
             row(['Q14', 'Are the two local snapshots joinable?',
                  'Not on the column named game_id: zero matches. They join on an alternate identifier for every '
                  'game in the lines file.', 'Any pipeline must be written against the alternate key, and the key '
                  'convention is undocumented.'], ('repo',), 'Answered · measured locally'),
             row(['Q15', 'Does the score snapshot have official corroboration?',
                  'Yes for the check run here: one 2018 game was compared to the official game centre and the final '
                  'score and quarter scoring matched.', 'One game of 7,548. Earlier sessions verified a handful of '
                  'others; the file is not certified row by row.'], ('nfl-gamecenter-score', 'repo'),
                 'Partly answered'),
             row(['Q16', 'Has any strategy been shown to work?',
                  'No. Every candidate in the registry is marked unvalidated, the leaderboard has no eligible '
                  'entry, and gate eligibility fails closed when an input is missing.',
                  'Inherited secondary-data subtrees report figures of their own; this dashboard does not adopt '
                  'them.'], ('repo',), 'Answered · none certified'),
             row(['Q17', 'Can luck be removed from the evaluation?',
                  'No. Sealed periods, proper scoring, multiplicity control and uncertainty bands test evidence of '
                  'skill; none of them eliminate chance.', 'Selectivity can raise the share of decisions made on '
                  'evidence, which is the honest version of the request.'], ('holdout', 'multiplicity', 'tails'),
                 'Answered · limit stated'),
             row(['Q18', 'How many live dashboards are there?',
                  'Six, built by eight sessions, each with its own flag register and none linked from the others; '
                  'the directory on the overview page maps them.', 'Content overlap is high and the sites disagree '
                  'about what has been verified.'], ('repo',), 'Answered · see directory'),
             row(['Q19', 'Does anything block publishing the honest version now?',
                  'No. All limitations are already published on Flagged for Review, and nothing on the site asserts '
                  'an unearned edge.', 'Publication of an empirical number would need a verified input first.'],
                 ('repo',), 'Answered · clear to publish'),
         ])

         + table('Open — closable with data work', ['ID', 'Question', 'What is missing', 'How to resolve',
                                                     'Blocks'], [
             row(['Q20', 'Is there an availability effect at all?', 'Timestamped reports aligned to prices and '
                  'settled outcomes over enough seasons.', 'Capture each daily report and reserve list from now on, '
                  'hash each capture, and only evaluate on data collected after the freeze.', 'Any AV candidate'],
                 ('nfl-injury', 'repo'), 'Prospective collection'),
             row(['Q21', 'How much does a backup actually change a unit?',
                  'A participation denominator and a role definition.', 'Either license a tracking feed or define '
                  'roles from published counting statistics and accept the loss of precision.', 'AV1, AV2, AV5'],
                 ('nfl-stats-cats', 'nfl-ngs'), 'Source licence'),
             row(['Q22', 'Do correlated legs move a parlay price?', 'An aligned sample of executed combos.',
                  'Build the combo ledger first: joint feasibility is unit-tested, joint NFL evidence does not '
                  'exist.', 'X1, S1'], ('pearson', 'repo'), 'Aligned sample'),
             row(['Q23', 'What sample size is needed before a claim?', 'A power study keyed to the declared '
                  'candidate family.', 'Fix the family, then derive the minimum games and weeks; publish it before '
                  'the sealed test.', 'Every gate-3 claim'], ('holdout', 'multiplicity'), 'Design freeze'),
             row(['Q24', 'Which rows in the local files are wrong?',
                  'The reason for the whole-game inversions.', 'Quarantine the affected games, document the rule '
                  'that excludes them, and re-verify against official game centres one at a time.',
                  'Any use of the local snapshot'], ('repo', 'nfl-gamecenter-score'), 'Data cleansing'),
             row(['Q25', 'Can the leaderboard reward skill rather than variance?',
                  'A frozen scoring protocol and a real submission ledger.', 'Rank on the lower bound of paired '
                  'log-loss improvement against a matched market, never on raw return.', 'Rewards'],
                 ('logloss', 'brier'), 'Protocol freeze'),
         ])

         + table('Open — needs an owner decision', ['ID', 'Question', 'Why research cannot answer it',
                                                     'Options on the table'], [
             row(['Q26', 'Which dashboard becomes canonical?',
                  'All six are internally consistent and mutually duplicative; only the owner can decide what to '
                  'keep.', 'Keep this root site and archive the rest, keep the two research pipelines and merge the '
                  'registers, or run all six with a single index.'], ('repo',), 'Path decision'),
             row(['Q27', 'Do we license current market data?',
                  'It is a budget and legal question, not a modelling one.', 'License a vendor, accept a '
                  'prospective-only archive with no history, or remain a specification-only lab.'], ('repo',),
                 'Budget decision'),
             row(['Q28', 'May the 2006\u20132018 snapshot be published or reused?',
                  'Its origin and licence are unrecorded; nothing in the repository settles it.', 'Retain '
                  'internally, delete, or obtain written permission.'], ('repo',), 'Rights decision'),
             row(['Q29', 'Are rewards ever real?', 'Funding, eligibility and tax treatment are owner choices, and '
                  'wagering participation carries legal constraints.', 'Keep recognition non-cash, or fund a '
                  'competition with published rules and a review of applicable law.'], ('repo',),
                 'Programme decision'),
             row(['Q30', 'How much uncertainty is acceptable in a published signal?',
                  'A risk appetite, not an empirical finding.', 'Publish only all-gate-pass output, or publish '
                  'exploratory output under an explicit warning label.'], ('tails', 'holdout'), 'Risk decision'),
             row(['Q32', 'Which jurisdiction governs a reward competition attached to a leaderboard?',
                  'Unresolved, and research cannot settle it. Inherited subtrees disagree: one records Washington '
                  'State limits on sports wagering outside tribal casinos, another records Singapore licensing. '
                  'This session verified neither with a regulator.',
                  'Have the applicable regulator text reviewed before any reward is offered; the site currently '
                  'offers none, so nothing is blocked today.'], ('repo',), 'Compliance decision'),
             row(['Q31', 'What happens to open pull request #18?', 'It belongs to another session and GitHub '
                  'reports it unmergeable; only the owner can decide to rebase or close it.', 'Rebase, close with '
                  'a summary, or leave open as a dated review record.'], ('repo',), 'Housekeeping decision'),
         ])

         + table('Probes to discover missing information', ['ID', 'Probe', 'What it would reveal', 'Effort'], [
             row(['P01', 'Run the lines audit in this release against an independently downloaded score snapshot.',
                  'Whether the disagreeing rows are file corruption, an upstream revision, or a settlement-rule '
                  'difference.', 'Low'], ('repo', 'nfl-gamecenter-score'), 'Project audit'),
             row(['P02', 'Capture the injury report and reserve list daily for four weeks and diff them.',
                  'Real publication times, revision frequency and how often a status changes after Friday.', 'Low'],
                 ('nfl-injury', 'nfl-reserve-list'), 'Official pages'),
             row(['P03', 'Ask whether a licensed tracking feed exposes per-player snaps by game.',
                  'Whether Q21 can ever be answered from a citable source.', 'Medium'], ('nfl-ngs',),
                 'Vendor enquiry'),
             row(['P04', 'Sample three more club depth-chart pages for the same week.',
                  'Whether club depth charts are consistent enough to serve as a proxy ordering, and how often they '
                  'contradict each other.', 'Low'], ('club-depth-chart',), 'Club sites'),
             row(['P05', 'Recompute the seven tied games that produce moneyline pushes.',
                  'Whether the tie coding is a rule or an artefact, which decides how a push is priced.', 'Low'],
                 ('repo',), 'Project audit'),
             row(['P06', 'Freeze one candidate family and derive its minimum sample before any further modelling.',
                  'How many games the project actually needs, which bounds every later decision.', 'Medium'],
                 ('holdout', 'multiplicity'), 'Design work'),
             row(['P07', 'Compare de-vigged prices against own-line output on the usable subset of the local file.',
                  'Whether origination machinery behaves as specified, independent of any edge claim.', 'Medium'],
                 ('repo',), 'Method check'),
         ])

         + '<p>Answers above are current as of 14 Nov 2026 and will drift: a status definition or reporting rule can '
           'change without notice, which is why each row links to the page it was read from rather than restating '
           'it. Unverified values are left blank throughout, never estimated.</p>'
         + '')

page('suggestion-costs.html', 'Suggestion cost sheet',
         'Options, trade-offs,\nyour call.',
         'Improvements to this site and to the research programme, each tied to a problem that was actually '
         'observed in the repository. Nothing marked <em>Awaiting decision</em> has been implemented. The three '
         'paths at the bottom are coherent bundles rather than a single recommended route, because which one is '
         'best depends on a budget and a risk appetite only the owner holds.',
         table('How to use this register', ['Step', 'Instruction'], [
             row(['1 · Filter', 'Read the Status column first. Implemented items need no decision; the rest do.'],
                 ('repo',), 'Project record'),
             row(['2 · Pick a path', 'Compare the candidate paths below. A suggestion that belongs to a path you '
                  'have rejected can usually be dropped with it.'], ('repo',), 'Project record'),
             row(['3 · Record it', 'Add a row to the decision log, or open an issue referencing the suggestion ID. '
                  'This site publishes suggestions, not verdicts.'], ('repo',), 'Project record'),
             row(['4 · Then build', 'Implementation follows a recorded decision, so the site never changes shape '
                  'as a side effect of an agent session.'], ('repo',), 'Project record'),
         ])

         + ''
         + table('Suggestion register', ['ID · area', 'Observed problem', 'Proposed change', 'Decision value',
                                         'Cost / risk', 'Status'], [
             row(['S01 · Site structure', 'Six dashboards cover the same categories with no link between them, and '
                  'the board records more than ten coordination conflicts between sessions.',
                  'Designate one canonical site; keep the others as dated research records reachable from a single '
                  'directory.', 'A reader can tell what is current without cross-reading five flag registers.',
                  'Low cost. Risk: owners of other subtrees may object to demotion.', 'Implemented as a directory; '
                  'canonical choice pending'], ('repo',), 'Project audit'),
             row(['S02 · Evidence discipline', 'Contextual citations are used beside claims they do not prove, '
                  'which earlier reviews flagged three times.',
                  'Require every empirical value to name the file and row it came from, and let the build fail when '
                  'it cannot.', 'Stops unverified numbers reaching a published page by accident.',
                  'Low. Risk: pages show more blanks before data arrives.', 'Implemented for new pages'],
                 ('repo',), 'Project audit'),
             row(['S03 · Verification', 'The verifier checks local targets and allowed hosts only, so a dead or '
                  'rewritten official page stays green.',
                  'Add a scheduled external-reachability job that records the status code and hash of every cited '
                  'page monthly.', 'Sources can be trusted as still saying what the register claims.',
                  'Medium: needs a scheduled workflow and tolerance for page redesigns.', 'Awaiting decision'],
                 ('repo', 'pages'), 'CI change'),
             row(['S04 · Data', 'The project\u2019s single blocker is a licensed price history; nothing else can be '
                  'validated without it.', 'Acquire a current market-data source with a written licence and a '
                  'documented sign convention.', 'Unlocks gates 1, 2, 4, 5 and the whole leaderboard.',
                  'High cost, likely recurring. Risk: vendor terms may forbid republication.',
                  'Needs owner input first'], ('repo',), 'Programme decision'),
             row(['S05 · Data', 'Even without history, availability data vanishes: reports are revised and club '
                  'pages change silently.',
                  'Start a prospective capture archive now: daily hashed snapshots of the injury report, reserve '
                  'list and club depth charts.', 'Creates the only dataset the project can own outright, and it '
                  'compounds in value weekly.', 'Low cost per day. Risk: none to correctness; it is a delay to '
                  'answers until enough weeks exist.', 'Needs owner input first'],
                 ('nfl-injury', 'nfl-reserve-list', 'club-depth-chart'), 'Programme decision'),
             row(['S06 · Availability', 'The league publishes no depth chart, and the only ordering available is '
                  'self-declared unofficial.', 'Ship a deficiency index defined on official fields alone '
                  '(status, reserve moves, roster codes) and treat club ordering as an optional overlay.',
                  'Makes the injury requirement implementable without inheriting an unofficial judgement.',
                  'Medium. Risk: a weaker but honest signal.', 'Implemented as a specification'],
                 ('nfl-no-depth-chart', 'club-depth-chart'), 'Research design'),
             row(['S07 · Availability', 'Replacement quality has no official per-play denominator.',
                  'Define two variants: a counting-statistics proxy and a licensed participation version, and test '
                  'whether the second earns its licence fee.', 'Turns an unanswerable question into a measurable '
                  'comparison.', 'Medium. Risk: proxy may carry no signal at all.', 'Awaiting decision'],
                 ('nfl-stats-cats', 'nfl-ngs'), 'Research design'),
             row(['S08 · Lines', 'A 20,490-row price file sat in the repository unmeasured while every page claimed '
                  'no price data existed.',
                  'Keep the computed audit in the build so the file is described by its own numbers, and quarantine '
                  'it for use until provenance exists.', 'Removes a contradiction that would have mislead any '
                  'reviewer.', 'Low. Risk: none material.', 'Implemented in this release'], ('repo',),
                 'Project audit'),
             row(['S09 · Lines', 'Five games in that file settle opposite to the recorded scores, two of them fully '
                  'inverted.', 'Add an exclusion ledger naming the affected games and the rule that removes them, '
                  'then re-check each against official game centres.', 'Prevents silent result errors entering any '
                  'future backtest.', 'Low. Risk: reduces usable sample slightly.', 'Awaiting decision'],
                 ('repo', 'nfl-gamecenter-score'), 'Data quality'),
             row(['S10 · Methods', 'The candidate family is not frozen, so no multiplicity correction can be '
                  'justified and any result is unfalsifiable.',
                  'Freeze the candidate list, register every variant, and derive the minimum sample before the '
                  'sealed test.', 'Makes a pass mean something rather than being a selection artefact.',
                  'Medium. Risk: freezes out late ideas, which must then wait for a new family.',
                  'Awaiting decision'], ('multiplicity', 'holdout'), 'Research design'),
             row(['S11 · Methods', 'Selectivity is described but not measured, so skill and cherry-picking look '
                  'identical in output.',
                  'Report a coverage curve: for each abstention threshold publish the number of decisions, the '
                  'paired error and an uncertainty band, all frozen before the test.',
                  'This is the honest way to pursue a selectively skilled strategy.',
                  'Low. Risk: may reveal that selectivity buys nothing.', 'Awaiting decision'],
                 ('holdout', 'tails'), 'Research design'),
             row(['S12 · Competition', 'A leaderboard with rewards invites the fastest route to a number rather '
                  'than the truest.',
                  'Require a pre-outcome submission hash, one entry per model family, publication of every '
                  'excluded variant, and rank on a simultaneous lower bound.',
                  'Makes the ranking defensible as skill rather than luck or fishing.',
                  'Low. Risk: fewer entries.', 'Awaiting decision'], ('logloss', 'repo'), 'Programme design'),
             row(['S13 · Parlays', 'Correlation between legs is asserted nowhere, and pricing a combo from marginal '
                  'prices is wrong by construction.',
                  'Build a leg ledger first: exact thresholds, directions, settlement states and the actual combo '
                  'quote, then estimate dependence.', 'Prevents parlays being scored against an imaginary price.',
                  'Medium. Risk: ledger work before any result.', 'Awaiting decision'], ('pearson', 'repo'),
                 'Research design'),
             row(['S14 · Legal', 'Rights to reuse, publish and profit from third-party prices and club content are '
                  'unresolved across every inherited file.',
                  'Add a one-page rights register: per file, origin, licence text reference and permitted use.',
                  'Avoids publishing something the project cannot use.', 'Low to medium. Risk: some data may prove '
                  'unusable, which is itself the answer.', 'Awaiting decision'], ('repo',), 'Compliance'),
             row(['S15 · Operations', 'Coordination conflicts are the most repeated event in the board log.',
                  'Machine-check claims: one table, one owner per path, and a claim that expires after 60 minutes '
                  'without a commit.', 'Removes the biggest source of duplicated work across sessions.',
                  'Low. Risk: needs a small CI script.', 'Awaiting decision'], ('repo',), 'Process'),
             row(['S16 · Operations', 'The board mixes dated records with current state, so sessions keep '
                  're-discovering the baseline.',
                  'Split into a current-state header and an append-only log, with the audit tool printing the '
                  'baseline commit.', 'Cuts start-up cost for every future session.', 'Low. Risk: none material.',
                  'Partly implemented'], ('repo',), 'Process'),
             row(['S17 · Presentation', 'Pages carry one page-level date, so a reader cannot tell when a row was '
                  'read.', 'Store a retrieval date per row and render it in the evidence column.',
                  'Makes drift visible instead of implied.', 'Low. Risk: denser tables.', 'Awaiting decision'],
                 ('repo',), 'Site quality'),
             row(['S18 · Presentation', 'Findings live only as prose on pages, hard to act on.',
                  'Export each register as CSV from the same generator, so a suggestion or question can become a '
                  'tracked issue.', 'Turns the registers into a backlog without extra work.',
                  'Low. Risk: none material.', 'Awaiting decision'], ('repo',), 'Site quality'),
         ])

         + table('Candidate paths', ['Path', 'Sequence', 'What it buys', 'What it costs', 'Choose it if'], [
             row(['A · Own the evidence first', 'S05, then S01, S03, S08, S09, S14; no modelling until a captured '
                  'season exists.', 'A dataset nobody else has and a defensible starting point for gates 1 and 2.',
                  'Months before any performance figure exists.', 'You would rather be right slowly than fast, and '
                  'will not pay for a feed.'], ('nfl-injury',), 'Requires no budget'),
             row(['B · Buy the history', 'S04, S14, then S09, S10, S13, S02.',
                  'Immediate backtesting, real correlations and a leaderboard that can fill.',
                  'Recurring licence cost and dependence on vendor terms.',
                  'There is budget, and speed to a first real result matters more than ownership.'], ('repo',),
                 'Requires budget'),
             row(['C · Method before data', 'S10, S11, S12, S13, S17, S18.',
                  'A frozen design so that the first real dataset produces a valid answer rather than a first look.',
                  'Still no empirical result; risk of a beautiful protocol with nothing run through it.',
                  'You expect the data question to stay open for a while.'], ('repo',), 'Requires no licence'),
             row(['D · Consolidate only', 'S01, S15, S16, S02, S03.',
                  'One trustworthy site and an end to duplicate sessions, at almost no cost.',
                  'The research itself stays where it is: specified, unvalidated.',
                  'Right now the confusing part is the repository, not the science.'], ('repo',), 'Lowest cost'),
         ])

         + table('Implemented by this release', ['Item', 'What landed', 'Where', 'What it did not touch'], [
             row(['Availability source register', 'Ten official and club source records with their limits, 26 '
                  'transcribed Week 10 report entries, 13 reserve-list moves, a deficiency specification and six '
                  'AV candidates whose measured columns are blank.', 'Availability sources'],
                 ('nfl-injury', 'nfl-reserve-list'),
                 'Injuries & depth and Availability tracker keep their own rows and claims.'),
             row(['Suggestion cost sheet', 'Eighteen suggestions with cost, risk and status, four candidate paths '
                  'and a decision log.', 'Suggestion costs'], ('repo',),
                 'The scored Suggestions register, its 16 items and their statuses are unchanged.'),
             row(['Question ledger', 'Nineteen answered questions, six closable ones, seven owner decisions and '
                  'seven probes for missing information.', 'Question ledger'], ('repo',),
                 'Question register and Decision review were not edited.'),
             row(['Market data audit', 'A build-time tool that measures the inherited lines file instead of '
                  'describing it, published on the own-lines page.', 'Own lines'], ('repo',),
                 'No line, price, ROI or backtest was produced or claimed.'),
             row(['Review register extension', 'Six findings appended after the existing register, continuing its '
                  'numbering at F22; three overlapping findings were dropped as already recorded.',
                  'Flagged for review'], ('repo',),
                 'F01 to F21 and every row above the extension are untouched.'),
             row(['Section directory', 'A count-and-certification table of all seven published sections, with '
                  'per-section status.', 'Overview'], ('repo',),
                 'The overview\u2019s own summary and registers are unchanged; a table was appended.'),
         ])

         + table('Decision log', ['ID', 'Suggestion set', 'Decision', 'Date', 'Decided by', 'Rationale'], [
             row(['D00', 'S01 to S03, S05 to S08, S16', 'None yet: the register is published for review, and no '
                  'proposal marked Awaiting decision has been implemented.', '14 Nov 2026', 'Not yet decided',
                  'Items marked Implemented cover only what was needed to publish an accurate site.'], ('repo',),
                 'Project record'),
             row(['D01', None, None, None, None, None], ('repo',), 'Open'),
             row(['D02', None, None, None, None, None], ('repo',), 'Open'),
         ])

         + '<p>Two constraints shape every option here. Luck cannot be removed, only bounded, so any path that '
           'promises a guaranteed edge should be rejected on sight. And no official source publishes NFL wagering '
           'lines, so paths A and D differ from path B mainly in whether the price history is grown or bought. '
           'Recorded decisions should be mirrored into <code>COORDINATION.md</code> so the next session can see '
           'them.</p>')


new_flags = table('Review register extension · 14 Nov 2026 (session 4f2e0291)', ['ID / severity', 'Finding',
                         'Required evidence / disposition', 'State'], [
    row(['F22 · Critical', f"data/raw/closing_lines.csv holds {lines['files']['closing_lines']['rows']:,} "
         'historical quote rows, which contradicts F01 ("no official historical executable odds archive obtained") '
         'and F18 ("no executable historical price or point-in-time quote ledger exists"). It covers '
         f"{lines['coverage']['season_min']}\u2013{lines['coverage']['season_max']} only, joins to scores only "
         f"through an alternate identifier, has no price on {lines['missing_fields']['odds']['SPREAD']:,} "
         f"spread and {lines['missing_fields']['odds']['TOTAL']:,} total rows, and "
         f"{lines['settlement_recompute']['disagree_rows']} rows ({lines['settlement_recompute']['disagree_pct']}%)"
         ' disagree with outcomes recomputed from the sibling score snapshot. The archive is unusable for a claim, '
         'but it is not absent, and the register should say so.',
         'Quarantined for use, not deleted. F01 and F18 should be restated as "an undocumented, unlicensed, '
         '2006\u20132018 and mostly unpriced local file exists; nothing verified does". Provenance, licence, sign '
         'convention and coverage must be settled by the owner (Q28, S08, S09) before it supports any claim.',
         'Flagged · owner decision'],
        ('repo',), 'Computed by tools/lines_audit.py at build time'),
    row(['F23 · Review', 'No README, dataset note or manifest entry documents that file; the commit that added '
         'it describes only the games snapshot.', 'Record origin, retrieval date and permitted use, or remove '
         'the file.', 'Flagged'], ('repo',), 'Repository inspection'),
    row(['F24 · Review', 'The sibling score snapshot is byte-identical to the nflverse file whose hash is '
         'recorded on the coordination board, so its identity is checkable, but its upstream licence was never '
         'confirmed by any session.', 'Confirm redistribution rights before republication.', 'Flagged'],
        ('repo',), 'Hash compared locally'),
    row(['F25 · Critical', 'No official participation or snap-count category exists among the eleven published '
         'statistics categories, so replacement quality has no per-play denominator. The depth-chart findings '
         'above (F13, F17\u2013F19) do not close this: a lineup names starters, not snaps.',
         'Licence a tracking feed, or accept a counting-statistics proxy and disclose the loss of precision '
         '(S07, Q21).', 'Blocked on source'], ('nfl-stats-cats', 'nfl-ngs'), 'Checked absence'),
    row(['F26 · Review', 'Pull request #18 (independent-audit scope) is open, was last updated 10 days ago, and '
         'GitHub reports it unmergeable; its pages are therefore not on the published site. This session cannot '
         'rebase another session\u2019s branch.', 'Owner should rebase or close it (Q31). No link was added to a '
         'path that would 404.', 'Flagged · handoff'], ('repo',), 'Repository inspection'),
    row(['F27 · Review', 'Seven sections now duplicate overlapping categories with separate registers, and the '
         'board records repeated coordination conflicts between them; this session\u2019s own findings were '
         'renumbered to F22\u2013F27 in this merge for exactly that reason.',
         'This release publishes a directory with per-section certification status instead of silently merging '
         'them; the canonical choice is S01, a decision the register leaves open.', 'Awaiting owner decision'],
        ('repo',), 'Repository inspection'),
])


# This session's eight findings are appended to the review register page itself, because the
# requirement is that every flagged item appears on "Flagged for Review". Their rows are left
# untouched and no wording is rewritten: the table is added after the last existing block.
PAGES['flags.html'] = (*PAGES['flags.html'][:3],
                       PAGES['flags.html'][3]
                       + '<p class="download">F22 to F27 below were raised by session 4f2e0291 on 14 Nov 2026. They '
                         'continue the numbering above rather than editing it; three findings this '
                         'session had also raised are not repeated here because F13, F17\u2013F19 '
                         'and F21 already record them.</p>'
                       + new_flags)

# The ledger page points at that register instead of restating it, so a finding has one home.
PAGES['question-ledger.html'] = (*PAGES['question-ledger.html'][:3],
                                 PAGES['question-ledger.html'][3]
                                 + '<p class="download">The six irregularities this session adds (F22 to F27) '
                                   'are published on <a href="flags.html">Flagged for Review</a> with the evidence '
                                   'each one still needs; the market figures behind F22 are on '
                                   '<a href="lines.html">Own lines</a> and reproduce with '
                                   '<code>python3 tools/lines_audit.py</code>.</p>')


SECTIONS = [
    ('.', 'Root dashboard', 'The published decision layer: a decision brief, three question registers, a '
     'suggestion register with costs and falsifiers, a costed suggestion sheet, the availability tracker, the '
     'Week 10 injury and depth page, the official-source register behind both, the own-lines market audit, '
     'validation gates, leaderboard, correlations, data contract, sources, audit and flags.'),
    ('site', 'Additive lab', 'Pricing primitives, gate structure and its own dashboard, from the a54b6387 '
     'integration session.'),
    ('research', 'Research pipeline', 'Secondary-data analysis pipeline and its generated pages, from the '
     '75504db2 session.'),
    ('own9-research', 'Duplicated pipeline', 'A self-contained copy of the pipeline and its pages, from the '
     'd66f6c4f session.'),
    ('strict-lab', 'Withholding lab', 'A lab that publishes no unverified measurement at all, from the '
     '80085c01 session.'),
    ('release-checks', 'Release reviews', 'Two dated technical review reports on structure, links and deployment '
     'metadata, from the e908995d session.'),
    ('session-8b05dd6d', 'Week 10 availability subtree', 'An isolated subtree: transcribed week 10 injury rows, '
     'starter-replacement notes, schedule checks and a Singapore legal note, from the 8b05dd6d session.'),
]

def _landing(folder):
    """Landing page of a section, preferring an index.html that exists on disk."""
    if folder == '.':
        return 'index.html'
    candidate = f'{folder}/index.html'
    return candidate if (Path(ROOT) / candidate).exists() else f'{folder}/'


# Computed from SECTIONS so the links cannot drift from the table above them.
_section_links = [(_landing(folder), name) for folder, name, _desc in SECTIONS]

# The directory is appended to the overview so a reader can see that these sections overlap and which of them
# this release actually re-verified; the overview's own content is left untouched.
_directory = table('Published sections of this repository', ['Section', 'Pages', 'What it holds',
                                                             'Re-verified by this release'], [
    row([folder if folder != '.' else 'Root dashboard',
         str(len(PAGES) if folder == '.' else len(sorted((Path(ROOT) / folder).glob('*.html')))),
         desc,
         'Yes — regenerated and structurally verified' if folder == '.' else
         'No — certified only by its own session'], ('repo',), 'Local section')
    for folder, _name, desc in SECTIONS
])
PAGES['index.html'] = (*PAGES['index.html'][:3],
                       PAGES['index.html'][3]
                       + '<p>Seven artefacts are published under <code>/Own9/</code> because parallel sessions each '
                         'built their own. Nothing here merges them: the table records what each contains and who '
                         'certified it, so a reader knows which page is current for which question. Consolidating '
                         'them into one canonical site is an open owner decision.</p>'
                       + _directory
                       # The table cells are escaped text by design, so the links are given their own line.
                       + '<p class="download">Open a section: '
                       + ' · '.join(f'<a href="{e(entry, quote=True)}">{e(name)}</a>'
                                    for entry, name in _section_links)
                       + '.</p>')
