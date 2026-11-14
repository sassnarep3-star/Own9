"""Suggestion register added by the 2026-11-14 final integration session.

The owner asked for a place to review improvement options and choose a path
before changes are implemented. Each suggestion records the problem actually
observed in this repository, so the trade-off can be judged without re-reading
the code. Status is one of: awaiting decision, needs owner input first, or
implemented in this release.
"""


def register(build):
    table, row, page = build.table, build.row, build.page

    page('suggestions.html', 'Suggestions',
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

         + table('Implemented by this release', ['Item', 'What landed', 'Where'], [
             row(['Availability and depth section', 'Official reporting rules, transcribed Week 10 report entries, '
                  'reserve-list moves, a deficiency specification and six AV candidates.', 'Injuries & depth'],
                 ('nfl-injury', 'nfl-reserve-list'), 'New page'),
             row(['Suggestion register', 'Eighteen suggestions with cost, risk and status, plus four candidate '
                  'paths and a decision log.', 'Suggestions'], ('repo',), 'New page'),
             row(['Question ledger', 'Nineteen answered questions, six closable ones and six owner decisions, with '
                  'seven probes for missing information.', 'Questions'], ('repo',), 'New page'),
             row(['Market data audit', 'A build-time tool that measures the inherited lines file instead of '
                  'describing it, published on the own-lines page.', 'Own lines'], ('repo',), 'New tool'),
             row(['Verifier extension', 'Retrieval scope per source, enforced blank measured columns on the new '
                  'availability candidates, and publication of four new flags.', 'Flagged for review'],
                 ('repo',), 'Checker'),
             row(['Category landing', 'Reordered navigation by decision category and a directory of every published '
                  'section with its certification status.', 'Overview'], ('repo',), 'Site'),
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
