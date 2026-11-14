"""Decision-support pages added by the 2026-11-14 final integration session.

Two registers the repository did not previously have: the question ledger that
separates what is answerable today from what is blocked, and the suggestion
register the owner uses to pick a path before any change is implemented.
"""
from lines_audit import audit


def register(build):
    table, row, page = build.table, build.row, build.page
    rc = audit()['settlement_recompute']
    # Session 8de532d1's decision register is published unchanged, ahead of the
    # answered / open split this release adds.
    preserved_head = getattr(build, 'DECISION_NOTICE', '') + getattr(build, 'DECISION_QUESTIONS', '')
    preserved_tail = getattr(build, 'DECISION_OUTCOME', '')

    # ------------------------------------------------------ question ledger
    page('questions.html', 'Questions',
         'What has to be answered\nbefore a decision is defensible.',
         'Every question splits into four states: answered from an official source, answered from this repository, '
         'open and fixable with data work, or open and needing an owner decision. A question is never closed by '
         'inference, and nothing here was answered by asking you.',
         preserved_head
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
                  'proof of non-existence; recorded as F16.'], ('nfl-no-depth-chart',), 'Answered · checked absence'),
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
         + preserved_tail)
