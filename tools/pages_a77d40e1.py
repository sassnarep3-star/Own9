"""Market-board delta for session `arena/a77d40e1-own9`, registered additively on 2026-11-14.

Six pages computed from the verified results feed in ``data/board/`` (official league
schedule pages transcribed verbatim into ``data/board/raw/week-NN.txt``): the results feed,
the Week 11 origination board (side -> total -> moneyline), the price-snapshot store, the
signal-vs-staking leaderboard split, correlations from official numbers only, and the
replacement-depth register. Session 201adb50's schema sections on ``lines.html`` and
session feaa600b's live-to-paper gate on ``leaderboard.html``/``validation.html`` are the
policy this delta computes against; neither page is rewritten here.

Empirical policy: blank where no official source provides a value (market lines, ROI,
CLV, exposure caps, unverified depth tiers); never zero, never inferred. Every number
this module prints is either (a) transcribed from an official page (with the weekly
schedule source cited), (b) a frozen-model output labelled as such, or (c) blank.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(ROOT)))  # engine/ is importable from the repository root
from engine.board import BUILD_TS, CODE_TO_NAME, run as board_run  # noqa: E402

BOARD = board_run()
FS = BOARD["feed_stats"]
MD = BOARD["model"]
W11 = BOARD["week11_games"]

# Registered source id per week (w9/w10 pre-existed on the shared register).
_WEEK_SRC = {1: 'nfl-schedule-w1', 2: 'nfl-schedule-w2', 3: 'nfl-schedule-w3', 4: 'nfl-schedule-w4',
             5: 'nfl-schedule-w5', 6: 'nfl-schedule-w6', 7: 'nfl-schedule-w7', 8: 'nfl-schedule-w8',
             9: 'nfl-schedule-w9', 10: 'nfl-schedule-w10', 11: 'nfl-schedule-w11'}


def _pct(x, digits=1):
    return '' if x is None else f'{100 * x:.{digits}f}%'


def _f(x, digits=2):
    return '' if x is None else f'{x:.{digits}f}'


def _n(x):
    return '' if x is None else f'{x:g}'


# ------------------------------------------------------------------ results feed

def _result_rows():
    for g in sorted(BOARD["finals"], key=lambda g: (g["week"], g["kickoff_date"], g["game_id"])):
        yield row([f'W{g["week"]}', g["kickoff_date"], CODE_TO_NAME[g["away"]], g["away_score"],
                   f'at {CODE_TO_NAME[g["home"]]}', g["home_score"],
                   g["home_score"] + g["away_score"], g["home_score"] - g["away_score"]],
                  (_WEEK_SRC[g["week"]],), 'Official page · transcribed 2026-11-14')


def _pending_rows():
    for g in sorted(BOARD["upcoming"], key=lambda g: (g["week"], g["kickoff_date"], g["game_id"])):
        yield row([f'W{g["week"]}', g["kickoff_date"], g.get("kickoff_time", ''),
                   CODE_TO_NAME[g["away"]], f'at {CODE_TO_NAME[g["home"]]}',
                   g.get("network", '')],
                  (_WEEK_SRC[g["week"]],), 'Official page · schedule only')


page('results-feed.html', 'Results feed', 'Settled results,\nverified at the source.',
     'Every 2026 final transcribed from the official league schedule pages on 14 Nov 2026, with the feed '
     'that makes walk-forward scoring, backtests and ROI computable at all. Blank cells stay blank.',
     '<div class="notice"><strong>What this feed is · what it is not</strong><p>Settled finals for '
     f'{FS["finals"]} games (Weeks 1&ndash;9 complete, plus the one settled Week 10 game) were transcribed '
     'verbatim from the official league schedule pages on 14 Nov 2026; the per-game official game-centre '
     'URLs are in the committed feed CSV <code>data/board/results_2026.csv</code>. '
     f'{FS["cross_checked_vs_secondary"]} of the finals also matched the committed secondary snapshot '
     f'row-for-row; {FS["score_mismatches_vs_secondary"]} disagreed. The secondary file has no scores for '
     'Weeks 9&ndash;10 (it is stale), so those finals rest on the official transcription alone. The feed '
     'carries results only: it contains no odds, and the league publishes none.</p></div>'
     + table('Feed integrity summary', ['Measure', 'Value', 'Meaning'], [
         row(['Verified finals in feed', FS["finals"], 'Weeks 1-9 complete slates plus the settled Week 10 Thursday game.'], ('repo',), 'Computed by engine/board.py at build time'),
         row(['Cross-checked against committed secondary snapshot', FS["cross_checked_vs_secondary"], 'Weeks 1-8 rows also present with scores in data/raw/games.csv; all matched exactly.'], ('repo',), 'Build-time comparison'),
         row(['Score disagreements vs secondary', FS["score_mismatches_vs_secondary"], 'Zero disagreements found on rows the secondary file scores.'], ('repo',), 'Build-time comparison'),
         row(['Official-only finals (secondary stale)', len(BOARD["finals"]) - FS["cross_checked_vs_secondary"], 'Weeks 9-10 finals rest on the official transcription alone; flagged for review (F29).'], ('nfl-schedule-w9', 'nfl-schedule-w10', 'repo'), 'Source-scope difference'),
         row(['Scheduled games pending (W10 remainder + W11)', FS["pending"], 'Scores blank until the league publishes finals; never inferred.'], ('nfl-schedule-w10', 'nfl-schedule-w11'), 'Official schedule · transcribed'),
     ])
     + table('Verified 2026 results (settle inputs)', ['Week', 'Kickoff date', 'Away club', 'Away pts', 'Home club', 'Home pts', 'Total', 'Margin (home - away)'],
             list(_result_rows()))
     + table('Scheduled games pending settlement', ['Week', 'Kickoff date', 'Kickoff (ET as listed)', 'Away club', 'Home club', 'Network'],
             list(_pending_rows()))
     + '<p>Settlement rules this feed enables: a side market settles against the published final margin, a total against the published final sum, a moneyline against the published winner. What the feed cannot supply is an executable market price, so ROI and CLV stay blank (see <a href="signal-staking.html">Signal vs staking</a>).</p>')


# --------------------------------------------------------------- origination board

def _board_rows():
    for m in BOARD["markets"]:
        game = next(g for g in W11 if g["game_id"] == m["game_id"])
        label = {"side": "Side (home handicap)", "total": "Total (over/under line)", "ml": "Moneyline (home, American)"}[m["market_type"]]
        if m["market_type"] in ("side", "total"):
            price = f'{_f(m["model_price"], 1)} (unrounded {_f(m["model_price_unrounded"], 2)})'
        else:
            price = f'{m["model_price"]:+d} (implied p(home win) {_f(m["model_price_unrounded"], 3)})'
        yield row([m["origination_seq"], f'{CODE_TO_NAME[game["away"]]} at {CODE_TO_NAME[game["home"]]} '
                   f'({game["kickoff_date"]})', label, price, None, None, m["n_fit"], m["market_id"]],
                  (_WEEK_SRC[11], 'repo'), 'Schedule official / model output')


page('origination.html', 'Market board', 'Own lines for Week 11,\noriginated in a fixed order.',
     'The model\u2019s fair line, the market line and the difference as separate columns, originated side '
     'first, then the total, then the moneyline. The market column is blank on purpose: the league publishes no wagering lines and no book of record has been approved.',
     '<div class="notice"><strong>Why the market column is blank</strong><p>The model\u2019s fair line is '
     'published below as a model output. The market line is blank because no official league source '
     'publishes wagering prices and the owner has not approved a book of record (open decisions S04/S05, '
     'Q28); the difference column is therefore also blank. Those cells stay blank &mdash; never zero, '
     'never guessed. The origination order is enforced by <code>engine/board.py</code>, which refuses to '
     'create a total market for a game whose side market does not exist, and a moneyline whose total does '
     'not exist.</p></div>'
     + table('Frozen model parameters (fit on the verified feed only)', ['Parameter', 'Value', 'n (verified finals used)', 'Definition'], [
         row(['Home-field advantage (hfa)', _f(MD["hfa"], 3) + ' points', MD["n"], 'Mean home margin across the verified finals in the fit set.'], ('repo',), 'Model parameter · fitted on official results'),
         row(['Margin residual sigma', _f(MD["sigma_margin"], 3) + ' points', MD["n"], 'Standard deviation of (actual margin - predicted margin) on the same fit.'], ('repo',), 'Model parameter'),
         row(['Total residual sigma', _f(MD["sigma_total"], 3) + ' points', MD["n"], 'Standard deviation of (actual total - predicted total) on the same fit.'], ('repo',), 'Model parameter'),
         row(['Points model', 'ep(home) = (off(home) + def(away)) / 2; ep(away) symmetric', MD["n"], 'off/def are per-game points scored/allowed averages over the fit set; all inputs official.'], ('repo',), 'Frozen specification'),
         row(['Fit set', 'Weeks 1-9 finals + the settled Week 10 Thursday game', MD["n"], 'No other data enters the fit; no prior-season data is used (flagged F31).'], ('repo',), 'Frozen specification'),
     ])
     + table('Week 11 origination board (39 markets, originated ' + BUILD_TS + ')',
             ['Order', 'Game', 'Market', 'Fair line (model)', 'Market line (de-vig)', 'Difference (fair - market)', 'n (fit)', 'Market ID'],
             list(_board_rows()))
     + '<p>Origination order per game is visible in the Order column: every side is seq 1, every total seq 2, every moneyline seq 3. The mechanical enforcement and its regression tests live in <code>engine/board.py</code> and <code>tests/test_board.py</code>. These are model prices for a paper board: no wager is placed, enabled or recommended, and the walk-forward record for this model family is on <a href="signal-staking.html">Signal vs staking</a>.</p>')


# ------------------------------------------------------------------ snapshot store

def _snapshot_rows():
    for s in BOARD["snapshots"]:
        captured = s["captured_at"] or ''
        yield row([s["market_id"], {"side": "Side", "total": "Total", "ml": "Moneyline"}[s["market_type"]],
                   "Open" if s["phase"] == "open" else "Close",
                   _f(s["model_price"], 1) if s["phase"] == "open" else (f'{s["model_price"]:+d}' if s["model_price"] is not None else None),
                   None, captured or None],
                  ('nfl-schedule-w11', 'repo'), 'Store record / model output')


page('price-snapshots.html', 'Price snapshots', 'Open and close,\nevery market we originate.',
     'The snapshot store: one open and one close record per originated market. Open records are captured '
     'at origination; Week 11 close records are pending by design and stay blank until the close policy runs.',
     '<div class="notice"><strong>Store policy</strong><p>Every market the board originates gets exactly '
     'two snapshot rows: <em>open</em>, captured at origination (' + BUILD_TS + '), and <em>close</em>, to be '
     'captured at the frozen close policy (re-price at kickoff minus 60 minutes). Week 11 close rows exist '
     'with blank prices because the close re-price has not run &mdash; recording a number now would '
     'fabricate a price that no process produced (flagged F30). Market-price cells are blank throughout: '
     'no official source publishes them. The store is append-only; a close row never overwrites its open '
     'row.</p></div>'
     + table('Store coverage audit (computed at build time)', ['Measure', 'Value', 'Meaning'], [
         row(['Markets originated for Week 11', len(BOARD["markets"]), '13 games x 3 markets (side, total, moneyline), in the enforced order.'], ('repo',), 'Computed by engine/board.py'),
         row(['Open snapshots captured', sum(1 for s in BOARD["snapshots"] if s["phase"] == "open"), 'One per market, captured at origination with the frozen model price.'], ('repo',), 'Store record'),
         row(['Close snapshots pending', sum(1 for s in BOARD["snapshots"] if s["phase"] == "close" and s["model_price"] is None), 'Blank by design until the close policy run; never fabricated.'], ('repo',), 'Store record'),
         row(['Market-price cells (all phases)', 0, 'Blank everywhere: no book of record, no official publisher of wagering prices (F22 lineage).'], ('repo',), 'Policy'),
     ])
     + table('Price-snapshot store (78 records)', ['Market ID', 'Market', 'Phase', 'Model price (ours)', 'Market price (book)', 'Captured at (UTC)'],
             list(_snapshot_rows()))
     + '<p>For the walk-forward diagnostics (Weeks 3-10) the store records open prices only: the close re-price would need a weekly verified availability feed that does not exist yet (F25/F30 lineage), and re-using the open inputs unchanged would fake a re-price that never happened.</p>')


# ---------------------------------------------------------------- signal vs staking

def _walk_rows():
    for r in BOARD["walk_rows"]:
        yield row([f'W{r["week"]}', r["n_fit"], r["n"], f'of {r["expected_games"]}',
                   'Complete' if r["complete"] else 'Partial (in progress at retrieval)',
                   _pct(r["dir_acc"]), _f(r["brier_home_win"], 4), _f(r["mae_margin"], 2), _f(r["mae_total"], 2),
                   _f(r["mean_fair_line_bias_vs_result"], 2)],
                  ('nfl-schedule-w9', 'nfl-schedule-w10', 'repo'), 'Scored on official results')


def _signal_rows():
    for entry in BOARD["lb_rows"]:
        sig = entry["signal"]
        yield row([entry["strategy"], entry["status"], sig["n_walk_games"],
                   _pct(sig["dir_acc"]) if sig["dir_acc"] is not None else None,
                   sig["n_dir"] if sig["n_dir"] else None,
                   _f(sig["mae"], 2) if sig["mae"] is not None else None,
                   _f(sig["brier_home_win"], 4)],
                  ('nfl-schedule-w9', 'nfl-schedule-w10', 'repo', 'brier'), 'Computed on official results')


def _staking_rows():
    for entry in BOARD["lb_rows"]:
        st = entry["staking"]
        yield row([entry["strategy"], st["plan"], None, None, None, entry["gate"]],
                  ('repo',), 'Plan descriptor / blanks by policy')


page('signal-staking.html', 'Signal vs staking', 'A lucky staking run\ncannot mask a bad signal.',
     'Two disjoint sheets: the signal sheet scores what the model predicted against official results; the '
     'staking sheet describes how money would be planned. Neither can move the other, and every price-dependent staking figure is blank because no executable prices exist.',
     '<div class="notice"><strong>The separation rule</strong><p>Signal metrics are computed from official '
     'results only (walk-forward: each week priced on strictly earlier verified finals). Staking metrics '
     'would need executable market prices to mean anything &mdash; ROI, CLV and exposure caps are blank, '
     'not zero. A staking plan cannot be promoted on the strength of a signal score, and a profitable '
     'staking run (once prices exist) cannot rescue a signal that fails. Live activation is additionally '
     'gated by the live-to-paper gate on <a href="leaderboard.html">Leaderboard</a> (session feaa600b, '
     'PR #34): its operating parameters are unset, so every entry stays Paper.</p></div>'
     + table('Signal sheet (walk-forward weeks 3-9 complete slates, scored on official results)',
             ['Strategy', 'Status', 'n (walk-forward games)', 'Directional accuracy', 'n (directional picks)', 'Mean absolute error', 'Brier (home win)'],
             list(_signal_rows()))
     + table('Staking sheet (plan only; price-dependent cells blank by policy)',
             ['Strategy', 'Staking plan', 'ROI (blank: no executable prices)', 'CLV (blank: no closing prices)', 'Exposure cap (unset)', 'Gate status'],
             list(_staking_rows()))
     + table('Walk-forward diagnostic record (official results only)',
             ['Week', 'n (fit set)', 'n (settled games evaluated)', 'Slate coverage', 'Slate state', 'Directional accuracy', 'Brier (home win)', 'MAE margin (pts)', 'MAE total (pts)', 'Mean fair-line bias vs result (pts)'],
             list(_walk_rows()))
     + '<p>Reading the diagnostics: directional accuracy above one half is not evidence of edge on its own '
       '&mdash; with no executable prices there is no cost line to clear, and partial slates (Week 10 here) '
       'are shown but never folded into the aggregate. These figures are a baseline for future strategies, '
       'published in full so any selection effect would be visible. Luck is bounded, not removed: the '
       'sealed-holdout, multiplicity and stability gates on <a href="validation.html">Validation</a> still '
       'apply before any live claim.</p>'
     + table('Questions the board raises before any decision (BQ register, this release)',
             ['ID', 'Question', 'Information needed', 'Discovery suggestion', 'State'], [
         row(['BQ1', 'Which book of record should supply market prices for the fair-vs-market difference, CLV and ROI?', 'An owner-approved source licence and its retention policy.', 'Paths S04/S05 on Suggestion costs already cost the two options; pick one before the next snapshot run.', 'Owner decision (Q28 lineage)'], ('repo',), 'Registered question'),
         row(['BQ2', 'When does the close-snapshot run execute, and by what process?', 'A scheduled job (e.g. a GitHub Actions cron at kickoff-60min) and a failure policy.', 'Prototype a scheduled workflow on the existing Pages workflow pattern; dry-run before enabling.', 'Open · discoverable'], ('pages',), 'Registered question'),
         row(['BQ3', 'How far back can a verified results archive be built from official pages alone?', 'Per-week official schedule pages for prior seasons (the league keeps them browsable).', 'Extend data/board/raw/ one season at a time, cross-checking every week as done for 2026 weeks 1-8.', 'Open · discoverable'], ('nfl-schedule-w9',), 'Registered question'),
         row(['BQ4', 'Can a weekly verified availability feed be archived to support close re-pricing?', 'Weekly snapshots of the official injury report (it is not published historically).', 'Snapshot the official report every Wednesday/Friday/Saturday into evidence/availability/ before kickoff.', 'Open · discoverable'], ('nfl-injury-w10',), 'Registered question'),
         row(['BQ5', 'Should official weather (NWS) enter the total model as an input?', 'A verified point-in-time forecast archive per stadium.', 'api.weather.gov is a free official source; archive forecasts at the same close-policy instant.', 'Open · discoverable'], ('repo',), 'Registered question'),
         row(['BQ6', 'What deadband and joint-price rule should govern parlay pricing?', 'A predeclared threshold (currently 0.10) and an owner decision to freeze it.', 'Compare with the strict-lab dependence gate before freezing; document one rule in one place.', 'Awaiting owner decision'], ('repo',), 'Registered question'),
     ])
     + table('Suggestions raised by this release (review before implementing; not adopted)',
             ['ID', 'Suggestion', 'Why it improves decisions', 'Cost / risk', 'Status'], [
         row(['BS1', 'Approve a book of record for market prices (BQ1).', 'Unblocks the fair-vs-market difference, CLV, ROI and the leaderboard economics gate.', 'Licensing cost unknown; wrong book choice would corrupt every downstream metric.', 'Awaiting decision'], ('repo',), 'Proposal'),
         row(['BS2', 'Automate weekly results ingestion with a scheduled verification job.', 'Removes hand-transcription risk; the build-time cross-check then runs every week.', 'Low; reuses the existing CI pattern. Risk: league page layout changes.', 'Awaiting decision'], ('repo',), 'Proposal'),
         row(['BS3', 'Schedule the close-snapshot run at kickoff-60min (BQ2).', 'Completes the open/close store as required by the snapshot contract.', 'Low compute; needs a failure alert so close rows do not silently stay blank.', 'Awaiting decision'], ('repo',), 'Proposal'),
         row(['BS4', 'Archive the official weekly injury report three times a week (BQ4).', 'Builds the availability feed that close re-pricing and deficiency signals need (F25 lineage).', 'Medium; storage grows weekly and conflicts must be preserved, not reconciled.', 'Awaiting decision'], ('nfl-injury-w10',), 'Proposal'),
         row(['BS5', 'Archive official NWS forecasts per stadium at the close instant (BQ5).', 'Gives the total model a defensible exogenous input with official provenance.', 'Low-medium; archive discipline required to stay point-in-time honest.', 'Awaiting decision'], ('repo',), 'Proposal'),
         row(['BS6', 'Freeze one correlation deadband + joint-price rule across the project (BQ6).', 'Stops three sections from drifting into three different dependence policies (F27 lineage).', 'Low; needs cross-session agreement, not code.', 'Awaiting decision'], ('repo',), 'Proposal'),
     ]))


# --------------------------------------------------- correlations from official data


page('correlations-official.html', 'Correlations (official)', 'Dependence, measured\nonly where sourced.',
     'Pearson correlations computed exclusively from the verified official results feed, with n published '
     'next to every value, a Fisher-z interval, and a predeclared deadband that refuses to claim dependence inside it.',
     '<div class="notice"><strong>Provenance rule</strong><p>Every input to this table is a final score '
     'from the verified feed on <a href="results-feed.html">Results feed</a>. No model output, no '
     'secondary-source number and no assumed zero enters the computation. n is printed with every value. '
     'A pair whose |r| falls inside the predeclared 0.10 deadband gets no dependence claim &mdash; the '
     'joint price for such combinations stays blank rather than assuming independence. The correlation '
     'method reference is the published scipy.stats.pearsonr definition; the implementation here is '
     'dependency-free and unit-tested against textbook values.</p></div>'
     + table('Correlation register (official numbers only)', ['Predeclared pair', 'n', 'Pearson r', '95% CI (Fisher z)', 'Deadband', 'Dependence claim'], [
         row([c["pair"], c["n"], _f(c["pearson_r"], 4),
              f'({_f(c["ci_low"], 4)}, {_f(c["ci_high"], 4)})', f'{c["deadband"]:.2f}', c["dependence_claimed"]],
              ('nfl-schedule-w9', 'nfl-schedule-w10', 'pearson', 'repo'),
              'Official results / method reference') for c in BOARD["corr_rows"]
     ])
     + '<p>Interpretation guardrails: the margin-total correlation is negative because high-scoring games '
       'tend to be closer than blowouts in this 2026 sample, but n=137 is one partial season &mdash; the '
       'interval ('
     + f'{_f(BOARD["corr_rows"][0]["ci_low"], 3)}, {_f(BOARD["corr_rows"][0]["ci_high"], 3)})'
     + ') still straddles values that would support materially different parlay pricing, so no joint '
       'price is issued from it. Consecutive-week margin persistence sits inside the deadband: the '
       'project claims no momentum dependence from this sample. These values are descriptive statistics '
       'of official results, not edges, and they are recomputed at every build.</p>')


# ------------------------------------------------------------- replacement depth

def _depth_rows():
    for r in BOARD["repl_rows"]:
        depth = {1: '2nd string (1 tier)', 2: '3rd string (2 tiers)', 3: '4th string (3 tiers)'}.get(r["depth_travelled"])
        refs = ['nfl-injury-w10']
        if r["team"] == 'WAS':
            refs += ['nfl-gamebook-w9-lar-was', 'nfl-gamebook-w10']
        if r["chart"].startswith('SEA'):
            refs.append('seahawks-depth')
        if r["chart"].startswith('KC'):
            refs.append('chiefs-depth')
        if r["chart"].startswith('DET'):
            refs.append('lions-depth')
        if r["team"] in ('MIA', 'BAL'):
            refs.append('nfl-reserve-list')
        refs.append('repo')
        yield row([CODE_TO_NAME.get(r["team"], r["team"]), r["slot"], r["outgoing"], r["outgoing_status"],
                   r["replacement"] or None, r["replacement_status"], depth, r["chart"]],
                  tuple(refs), 'Committed evidence · both sources cited')


page('replacement-depth.html', 'Replacement depth', 'Not just who replaced,\nhow deep the drop went.',
     'A structured register of starter replacements: the depth tier the replacement was published at, so '
     'a second-string drop and a fourth-string drop are never treated as the same event. Blank where no club depth chart was retrieved; never inferred.',
     '<div class="notice"><strong>Why depth travelled is the tracked field</strong><p>The fact of a '
     'replacement is verifiable from the official injury report, Game Books and league news. What changes '
     'a unit\u2019s expected performance is how far down the published order the replacement came from: a '
     '2nd-string centre is a different deficiency from a 4th-string one. This register stores '
     '<code>depth_travelled</code> (1 = 2nd string, 2 = 3rd, 3 = 4th) as a first-class field for every '
     'replacement where an official club depth chart supports it, and leaves it blank where no chart was '
     'retrieved (WAS, MIA, BAL, GB) or where the two official sources conflict (DET safety, F14). The '
     'Washington centre row is the strongest evidence in the register: both the outgoing and incoming '
     'starts are printed in official Game Books, though its tier stays blank because no WAS chart exists '
     'on the league site (checked 404, F19 lineage).</p></div>'
     + table('Replacement-depth register (Week 10 2026 snapshot, retrieved 2026-11-14)',
             ['Club', 'Slot (published order)', 'Outgoing starter', 'Outgoing status', 'Replacement', 'Replacement status', 'Depth travelled', 'Depth source'],
             list(_depth_rows()))
     + table('Depth-travelled summary (computed)', ['Depth travelled', 'Count', 'Clubs'], [
         row(['2nd string (1 tier)', sum(1 for r in BOARD["repl_rows"] if r["depth_travelled"] == 1),
              'SEA (4), KC (2), DET (2)'], ('seahawks-depth', 'chiefs-depth', 'lions-depth'), 'Computed from register'),
         row(['3rd string (2 tiers)', sum(1 for r in BOARD["repl_rows"] if r["depth_travelled"] == 2), 'None observed this week'], ('nfl-injury-w10',), 'Computed from register'),
         row(['4th string (3 tiers)', sum(1 for r in BOARD["repl_rows"] if r["depth_travelled"] == 3), 'None observed this week'], ('nfl-injury-w10',), 'Computed from register'),
         row(['Blank (not derivable)', sum(1 for r in BOARD["repl_rows"] if r["depth_travelled"] is None),
              'WAS (no chart; Game Book evidence only), DET S (source conflict), MIA, BAL, GB (no chart retrieved)'], ('nfl-gamebook-w10', 'repo'), 'Withheld · never inferred'),
     ])
     + '<p>Deficiency use: the defence-deficiency and offence-deficiency scores specified on '
       '<a href="injuries.html">Injuries &amp; depth</a> consume this register as input; no performance '
       'weighting exists yet (no participation denominator, F25), so no injury-adjusted edge is asserted '
       'anywhere. The register is a point-in-time Week 10 snapshot; statuses change before kickoff and '
       'must be re-snapshotted (BS4 proposes the archive job).</p>')


# --------------------------------------------------- flags + overview appends

new_flags = table('Review register extension · 14 Nov 2026 (session a77d40e1)',
                  ['ID / severity', 'Finding', 'Required evidence / disposition', 'State'], [
    row(['F28 · Review', 'The verified results feed (137 finals) is a single-day transcription (2026-11-14) of the '
         'official schedule pages, which publish no per-row revision timestamp. League stat corrections after '
         'publication would silently invalidate any settlement computed from a stale copy.',
         'Re-retrieve before any settlement-dependent use; adopt the scheduled re-verification job (BS2) so the '
         'feed is dated every week rather than once.', 'Flagged'],
        ('nfl-schedule-w9', 'nfl-schedule-w10', 'repo'), 'Publisher scope'),
    row(['F29 · Review', 'The committed secondary snapshot data/raw/games.csv is stale: it carries no scores for '
         'Weeks 9-10 of 2026. The 121 rows it does score matched the official transcription exactly (zero '
         'disagreements), so the cross-check is sound where the file is current.',
         'Keep the file quarantined (F22/F23/F24 unchanged) and treat Weeks 9-10 finals as official-only until the '
         'file is refreshed by its owner.', 'Flagged'],
        ('nfl-schedule-w9', 'nfl-schedule-w10', 'repo'), 'Source-scope difference'),
    row(['F30 · Review', 'Week 11 close snapshots are pending by design: the close policy (re-price at kickoff-60min) '
         'has no scheduled run, so the store cannot yet produce close numbers for live markets. Recording one now '
         'would fabricate a price no process produced.',
         'Schedule the close run (BS3/BQ2) before the Week 11 kickoffs, or accept open-only records for this week '
         'and say so on the store page.', 'Flagged · owner decision'],
        ('repo',), 'Process gap'),
    row(['F31 · Review', 'Every model parameter (hfa, residual sigmas) is fitted on the 2026 verified feed only '
         '(n=137): no prior-season fit, no out-of-sample calibration beyond the walk-forward weeks, and '
         'directional accuracy 63.5% (n=104, weeks 3-9) is a descriptive diagnostic, not evidence of edge. No '
         'executable prices exist, so ROI/CLV remain blank and no luck-adjusted claim is possible.',
         'Extend the verified archive (BQ3), run the sealed-holdout and multiplicity gates on Validation before any '
         'live claim, and keep the board paper-only until then.', 'Flagged'],
        ('repo',), 'Scientific boundary'),
])

PAGES['flags.html'] = (*PAGES['flags.html'][:3],
                       PAGES['flags.html'][3]
                       + '<p class="download">F28 to F31 below were raised by session a77d40e1 on 14 Nov 2026. They '
                         'continue the register numbering rather than editing it; the F22-F27 block above is '
                         'session 4f2e0291\u2019s and is left untouched.</p>'
                       + new_flags)

_board_pages = [
    ('results-feed.html', 'Results feed', 'Verified 2026 finals (137) transcribed from official schedule pages; '
     'the settle input every backtest and ROI computation was missing; integrity counts computed at build time.'),
    ('origination.html', 'Market board', 'Week 11 fair lines for 39 markets originated side -> total -> moneyline '
     'by the frozen model; fair / market / difference as separate columns with market and difference blank by policy.'),
    ('price-snapshots.html', 'Price snapshots', 'The open/close snapshot store: 39 open records captured at '
     'origination, 39 close records pending by design, market-price cells blank (no official publisher).'),
    ('signal-staking.html', 'Signal vs staking', 'Disjoint signal sheet (walk-forward on official results, n=104) '
     'and staking sheet (plan only; ROI/CLV blank); the live-to-paper gate applied fail-closed; new BQ/BS registers.'),
    ('correlations-official.html', 'Correlations (official)', 'Pearson r with n and Fisher-z intervals computed '
     'only from officially sourced finals; deadband refuses dependence claims inside 0.10.'),
    ('replacement-depth.html', 'Replacement depth', 'The depth travelled by each Week 10 starter replacement '
     '(8 chart-derived, 5 withheld), stored as a first-class field with both sources cited per row.'),
]
_directory = table('Market-board delta · 14 Nov 2026 (session a77d40e1)',
                   ['Page', 'What it holds', 'Certification'], [
    row([label, desc, 'Computed from official sources at build time; blanks preserved'], ('repo',), 'This session')
    for _f_html, label, desc in _board_pages
])
PAGES['index.html'] = (*PAGES['index.html'][:3],
                       PAGES['index.html'][3]
                       + '<p class="download">The market-board delta below was added by session a77d40e1 on '
                         '14 Nov 2026: '
                       + ' · '.join(f'<a href="{fname}">{e(label)}</a>' for fname, label, _d in _board_pages)
                       + '.</p>'
                       + _directory)
