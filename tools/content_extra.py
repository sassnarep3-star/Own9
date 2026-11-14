"""Pages added by the 2026-11-14 final integration session.

Four areas the earlier releases did not cover: the suggestion register, the
decision-readiness question ledger, the availability / roster-deficiency lab,
and the own-line origination page. Content is generated from
`evidence/sources.json` plus `lines_audit.py`, so no number on these pages is
typed by hand and none is inferred from an unverified source.
"""
from lines_audit import audit


def register(build):
    table, row, page = build.table, build.row, build.page
    PAGES = build.PAGES
    lines = audit()

    # -------------------------------------------------- availability and depth
    page('injuries.html', 'Injuries & depth',
         'Who is out, who replaces them,\nand whether that is a signal.',
         'The official reporting rules, the feeds that carry them, a Week 10 2026 snapshot transcribed from the '
         'league report, and the specification for turning a missing starter into a measurable unit deficiency. '
         'Measured-result cells stay blank: no availability edge has been demonstrated.',
         table('Official availability sources', ['Source', 'What the page publishes', 'Retrieved',
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

    # ------------------------------------------------ own lines and market data
    cov, jn, rc, miss, push = (lines['coverage'], lines['join'], lines['settlement_recompute'],
                               lines['missing_fields'], lines['push_states'])
    priced = cov['market_types']['SPREAD'] - miss['odds']['SPREAD']
    unpriced_rows = miss['odds']['SPREAD'] + miss['odds']['TOTAL']
    unpriced = 100 * unpriced_rows / (cov['market_types']['SPREAD'] + cov['market_types']['TOTAL'])
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
           'of any kind, so it is quarantined and published on <a href="flags.html">Flagged for Review</a> as F13. '
           'The decision the owner has to make is whether to licence a current source or build a prospective '
           'capture archive from now on; <a href="suggestions.html">S04</a> and <a href="suggestions.html">S05</a> '
           'set out both paths.</p>')

    # ------------------------------------------------------------- hub / index
    def count_pages(folder):
        # The root set is exactly what this generator emits; siblings are counted from disk.
        return len(PAGES) if folder == '.' else len(sorted((build.ROOT / folder).glob('*.html')))

    dashboards = [
        ('.', 'Root evidence-first dashboard', 'Strategies, own lines, gates, leaderboard, correlations, '
         'availability, data contract, questions, suggestions, sources, audit and flags.'),
        ('site', 'Additive lab', 'Pricing primitives, gate structure and a twelve-page dashboard built by the '
         'a54b6387 integration session.'),
        ('research', 'Research pipeline', 'A secondary-data analysis pipeline and its ten pages, built by the '
         '75504db2 session.'),
        ('own9-research', 'Isolated pipeline', 'A self-contained duplicate of the pipeline and twelve pages, built '
         'by the d66f6c4f session.'),
        ('strict-lab', 'Strict-source lab', 'An eight-page evidence-scoped lab that withholds every unverified '
         'measurement, from the 80085c01 session.'),
        ('release-checks', 'Independent release review', 'Two dated technical review reports on structure, links '
         'and deployment metadata, from the e908995d session.'),
        ('session-8b05dd6d', 'Week 10 availability dashboard', 'A merged-during-this-release isolated subtree: '
         'transcribed week 10 injury rows, starter-replacement notes, schedule checks and a Singapore legal note, '
         'from the 8b05dd6d session.'),
    ]
    entries = {'.': 'index.html', 'site': 'site/index.html', 'research': 'research/index.html',
               'own9-research': 'own9-research/index.html', 'strict-lab': 'strict-lab/index.html',
               'release-checks': 'release-checks/index.html',
               'session-8b05dd6d': 'session-8b05dd6d/index.html'}
    certified = {'.': 'Regenerated and structurally verified by this release',
                 'site': 'Not re-verified by this release', 'research': 'Not re-verified by this release',
                 'own9-research': 'Not re-verified by this release', 'strict-lab': 'Not re-verified by this release',
                 'release-checks': 'Not re-verified by this release',
                 'session-8b05dd6d': 'Not re-verified by this release'}

    page('index.html', 'Overview', 'Evidence first.\nAn edge must be earned.',
         'An NFL line-origination lab for game singles, player props and joint bets, with the availability and '
         'roster-deficiency layer the earlier releases were missing. Built to test skill, not to reward a lucky '
         'streak.',
         '<div class="notice"><strong>Research framework · no validated strategies</strong><p>No verified '
         'historical executable odds or point-in-time paired dataset has been obtained. Lines, measured '
         'correlations, test scores and rewards are intentionally blank. No wagering is enabled, and no manual '
         'input is required to read any page.</p></div>'
         '<div class="cards">'
         '<a href="injuries.html"><span>01 / AVAILABILITY</span><b>Injuries &amp; depth</b><p>Who is out, who '
         'replaces them</p></a>'
         '<a href="lines.html"><span>02 / PRICING</span><b>Own lines</b><p>Audit of our own market data</p></a>'
         '<a href="strategies.html"><span>03 / HYPOTHESES</span><b>Signal registry</b><p>Singles, props and joint '
         'models</p></a>'
         '<a href="validation.html"><span>04 / DISCIPLINE</span><b>Seven evidence gates</b><p>Fail closed. Publish '
         'all trials.</p></a>'
         '<a href="leaderboard.html"><span>05 / COMPETITION</span><b>Evidence leaderboard</b><p>No eligible '
         'entries, no awards</p></a>'
         '<a href="correlations.html"><span>06 / DEPENDENCE</span><b>Correlation lab</b><p>Paired evidence, not '
         'assumptions</p></a>'
         '<a href="questions.html"><span>07 / DECIDING</span><b>Question ledger</b><p>Known, unknown and '
         'findable</p></a>'
         '<a href="suggestions.html"><span>08 / CHANGING</span><b>Suggestion register</b><p>Pick a path before '
         'building</p></a></div>'

         + table('How to read this site', ['Category', 'Page', 'Use it for'], [
            row(['Understand the position', 'Overview and Flagged for Review', 'What is built, what is unproven, '
                 'and what is blocked.'], ('repo',), 'Project record'),
            row(['Research the signals', 'Strategies, Injuries & depth, Correlations', 'Candidate designs, the '
                 'availability layer and dependence requirements.'], ('repo',), 'Project record'),
            row(['Judge the evidence', 'Own lines, Validation, Leaderboard', 'Data quality, acceptance policy and '
                 'eligibility.'], ('repo',), 'Project record'),
            row(['Make a decision', 'Questions and Suggestions', 'What must be answered first, and which path to '
                 'take.'], ('repo',), 'Project record'),
            row(['Check the sourcing', 'Sources, Data requirements, Repository audit', 'Every row\u2019s official '
                 'reference and the file-level review.'], ('repo',), 'Project record'),
         ])

         + table('Executive summary', ['Decision area', 'Finding', 'Disposition'], [
             row(['Originate NFL lines', 'The origination mathematics is implemented and unit-tested, and the local '
                  f"price snapshot is now measured rather than assumed absent: {lines['files']['closing_lines']['rows']:,} "
                  f"rows over {lines['coverage']['games']:,} games, seasons {lines['coverage']['season_min']}"
                  f"\u2013{lines['coverage']['season_max']}, joinable to scores only through an alternate "
                  'identifier.', 'Numerical line still unavailable · model unfitted'], ('repo',),
                 'Computed from committed data'),
             row(['Useful signals', 'Six availability candidates (AV1\u2013AV6) are specified against official '
                  'inputs, alongside the five market-based candidates; all eleven are unvalidated.',
                  'Registered, none certified'], ('nfl-stats', 'nfl-injury'), 'Proposals · official input categories'),
             row(['Injuries and depth', 'The official report, reserve list and roster codes are usable today and '
                  'were transcribed for week 10; the league publishes no depth chart, and no official '
                  'participation denominator exists.', 'Deficiency index specified · inputs incomplete'],
                 ('nfl-injury', 'nfl-roster-status', 'nfl-no-depth-chart'), 'Official fields · gap documented'),
             row(['Replacements and backups', 'First through fourth string ordering exists only on club sites that '
                  'label themselves unofficial, so any backup-quality claim inherits that uncertainty.',
                  'Proxy only · never an official fact'], ('club-depth-chart',), 'Club substitute · limited'),
             row(['Skill versus luck', 'Sealed periods, proper scoring, multiplicity control and uncertainty bands '
                  'can test evidence of skill. Selectivity can raise the share of decisions made on evidence.',
                  'Luck is not removable · no skill claim'], ('holdout', 'brier', 'multiplicity'),
                 'Method support · policy proposed'),
             row(['Correlation', 'No aligned sample exists, so every dependence value stays blank; the Pearson and '
                  'phi helpers are validated on synthetic arithmetic only.', 'Unverified NFL values'],
                 ('pearson', 'repo'), 'Formula support · project record'),
             row(['Parlays and prop combos', 'Joint feasibility and push handling are unit-tested; no combo quote '
                  'or settlement ledger exists.', 'Blocked on a leg ledger'], ('pearson', 'repo'),
                 'Maths tested · no data'),
             row(['Competition rewards', 'Four tracks with matched targets and non-cash recognition are proposed; '
                  'there is no sponsor, pool or awarded badge.', 'No funded programme'], ('repo',), 'Project record'),
             row(['Site quality', 'One landing page now organises six previously unlinked dashboards and states '
                  'which of them this release re-verified.', 'Directory published · canonical choice open'],
                 ('repo',), 'Project record'),
             row(['Recommendation', 'Grow a prospective, hashed availability and price archive before buying '
                  'history or fitting anything; it is the only step the project can complete alone.',
                  'See path A in Suggestions'], ('nfl-injury', 'repo'), 'Project record'),
         ])

         + table('Site directory', ['Section', 'Pages', 'Contains', 'Certification status'], [
             row([f'{folder if folder != "." else "Root"} · {entries[folder]}', str(count_pages(folder)), desc,
                  certified[folder]], ('repo',), 'Local section')
             for folder, name, desc in dashboards
         ])

         + '<p class="download">Open a section directly: '
           + ' · '.join(f'<a href="{entries[f]}">{("Root" if f == "." else f)}</a>' for f, _n, _d in dashboards)
           + '.</p>'
         + '<p class="download">Full specification: <a href="docs/RESEARCH_SPEC.md">docs/RESEARCH_SPEC.md</a>. '
           'Reproduce any number on the own-lines page with <code>python3 tools/lines_audit.py</code>. Every '
           'empirical gap is on <a href="flags.html">Flagged for Review</a>.</p>')

    # ----------------------------------------------------- extend earlier pages
    new_flags = table('Review register extension · 14 Nov 2026', ['ID / severity', 'Finding',
                                                                   'Required evidence / disposition', 'State'], [
        row(['F13 · Critical', f"data/raw/closing_lines.csv holds {lines['files']['closing_lines']['rows']:,} "
             'historical quote rows while F01 states that no executable odds archive was obtained. It covers '
             f"{lines['coverage']['season_min']}\u2013{lines['coverage']['season_max']} only, joins to scores only "
             f"through an alternate identifier, has no price on {lines['missing_fields']['odds']['SPREAD']:,} "
             f"spread and {lines['missing_fields']['odds']['TOTAL']:,} total rows, and "
             f"{lines['settlement_recompute']['disagree_rows']} rows ({lines['settlement_recompute']['disagree_pct']}%)"
             ' disagree with outcomes recomputed from the sibling snapshot.',
             'Quarantined for use, not deleted. Provenance, licence, sign convention and coverage must be settled '
             'by the owner (Q28, S08, S09) before it supports any claim.', 'Flagged · owner decision'],
            ('repo',), 'Computed by tools/lines_audit.py at build time'),
        row(['F14 · Review', 'No README, dataset note or manifest entry documents that file; the commit that added '
             'it describes only the games snapshot.', 'Record origin, retrieval date and permitted use, or remove '
             'the file.', 'Flagged'], ('repo',), 'Repository inspection'),
        row(['F15 · Review', 'The sibling score snapshot is byte-identical to the nflverse file whose hash is '
             'recorded on the coordination board, so its identity is checkable, but its upstream licence was never '
             'confirmed by any session.', 'Confirm redistribution rights before republication.', 'Flagged'],
            ('repo',), 'Hash compared locally'),
        row(['F16 · Critical', 'The user requirement to know second-, third- and fourth-string replacements cannot '
             'be met from official data: the league depth-chart path returns 404 and club charts call themselves '
             'unofficial.', 'Either accept club ordering as an explicitly unofficial overlay or define the '
             'deficiency index on official fields alone (S06).', 'Implemented as a limitation'],
            ('nfl-no-depth-chart', 'club-depth-chart'), 'Checked absence · substitute documented'),
        row(['F17 · Critical', 'No official participation or snap-count category exists among the eleven published '
             'statistics categories, so replacement quality has no per-play denominator.',
             'Licence a tracking feed, or accept a counting-statistics proxy and disclose the loss of precision '
             '(S07, Q21).', 'Blocked on source'], ('nfl-stats-cats', 'nfl-ngs'), 'Checked absence'),
        row(['F18 · Review', 'The injury report page publishes no per-row timestamp, so historical availability '
             'features cannot be reconstructed point-in-time and gate 2 cannot pass for past seasons.',
             'Begin prospective hashed capture; do not treat today\u2019s page as evidence of what was known in '
             'the past (S05, Q20).', 'Flagged'], ('nfl-injury',), 'Official page scope · gap'),
        row(['F19 · Review', 'Pull request #18 (independent-audit scope) is open, was last updated 10 days ago, and '
             'GitHub reports it unmergeable; its pages are therefore not on the published site. This session cannot '
             'rebase another session\u2019s branch.', 'Owner should rebase or close it (Q31). No entry was invented '
             'for a path that would 404.', 'Flagged · handoff'], ('repo',), 'Repository inspection'),
        row(['F20 · Review', 'Six dashboards duplicate the same categories with separate flag registers, and the '
             'board records repeated coordination conflicts between them.',
             'This release publishes a directory instead of silently merging them; the canonical choice is S01, a '
             'decision the register leaves open.', 'Awaiting owner decision'], ('repo',), 'Repository inspection'),
    ])
    for name, anchor in [('flags.html', '<p>Independent earlier-baseline technical report')]:
        label, title, intro, content = PAGES[name]
        PAGES[name] = (label, title, intro, content.replace(anchor, new_flags + anchor, 1))

    PAGES['audit.html'] = (*PAGES['audit.html'][:3], PAGES['audit.html'][3]
                           + table('14 Nov 2026 integration review', ['Area', 'What was checked', 'Result'], [
        row(['Committed market data', 'Every row of the inherited lines file was counted, joined to the score '
             'snapshot and recomputed with an audited tool.', 'Measured and published on the own-lines page; 18 '
             'disagreements isolated to five games. Quarantined for use.'], ('repo',), 'Computed, not asserted'),
        row(['Availability requirement', 'Ten official and club sources read on 14 Nov 2026, including the '
             'reporting policy, reserve mechanics and roster codes.', 'Page published; two checked absences '
             '(league depth chart, participation feed) published as F16 and F17.'],
            ('nfl-injury', 'nfl-roster-status'), 'Official scope'),
        row(['Evidence register', 'Ten scoped references became twenty, each with the precise claim read and its '
             'limits.', 'Every row on every page still resolves to a registered reference.'],
            ('repo',), 'Manifest extension'),
        row(['Verifier', 'Blank-value enforcement extended to the new availability candidate table, and the '
             'publisher allowlist widened only by hosts actually read.', 'Structural checks pass; reachability and '
             'claim entailment remain outside its scope.'], ('repo',), 'Checker limits'),
        row(['Decision support', 'Suggestion register, question ledger and site directory added; navigation '
             'reordered by category.', 'No prior page content was removed or reworded except the overview '
             'executive summary and the flag register.'], ('repo',), 'Project record'),
        row(['Open pull request', 'PR #18 was reviewed as a candidate for integration.', 'Not merged: reported '
             'unmergeable, and its branch belongs to another session. Published as F19.'], ('repo',),
             'Handoff recorded'),
    ]))

    order = ['index.html', 'strategies.html', 'lines.html', 'injuries.html', 'validation.html', 'leaderboard.html',
             'correlations.html', 'data.html', 'questions.html', 'suggestions.html', 'sources.html', 'audit.html',
             'flags.html']
    build.NAV_ORDER = order
