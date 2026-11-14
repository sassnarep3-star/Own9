"""Tests for the requirements delta of session 1cfcb957, merged 2026-11-14.

Each test asserts a *refusal* or an equality against a recomputed figure, because that is the class
of claim these engines make: they do not produce numbers so much as they prevent particular numbers
from being produced. Nothing here asserts a preference about wording, and no test re-derives a
value that the module already computed by copy-pasting its arithmetic — where a figure is checked,
it is checked against the evidence file or the audit, not against a literal that could drift.

Run with: python3 -m unittest discover -s tests
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))

from engine import correlations as corr          # noqa: E402
from engine import demotion                      # noqa: E402
from engine import originate                     # noqa: E402
from engine import replacement as repl           # noqa: E402
from engine import results_feed as res                # noqa: E402
from engine import signal_staking as ss          # noqa: E402
from engine import snapshots as snap             # noqa: E402
import requirements_audit                        # noqa: E402
from verify import Page                          # noqa: E402

NEW_PAGES = ('requirements.html', 'price-feed.html', 'signal-and-staking.html', 'depth-correlations.html',
             'missing-information.html')
CAPTURED = {'captured_at': '2026-11-05T13:00:00Z', 'source_url': 'https://www.nfl.com/x',
            'publisher': 'NFL'}


def priced(**overrides):
    kwargs = {'line': -2.5, 'price': -110}
    kwargs.update(CAPTURED)
    kwargs.update(overrides)
    return snap.make('det-at-sea-2026-reg-10', 'SPREAD', 'HOME', 'open', **kwargs)


class SnapshotStore(unittest.TestCase):
    """Requirement 1: the store's rules are the requirement."""

    def test_priced_record_requires_capture_time(self):
        for field in ('captured_at', 'source_url', 'publisher', 'provenance'):
            void = {k: v for k, v in CAPTURED.items() if k != field} | ({'provenance': None}
                                                                        if field == 'provenance' else {})
            with self.subTest(field=field), self.assertRaises(snap.SnapshotError):
                snap.make('g', 'SPREAD', 'HOME', 'open', line=-2.5, price=-110, **void)

    def test_absence_must_be_reasoned(self):
        with self.assertRaises(snap.SnapshotError):
            snap.make('g', 'SPREAD', 'HOME', 'open')
        record = snap.make('g', 'SPREAD', 'HOME', 'open',
                           missing_reason='no licensed feed for this slate')
        self.assertIsNone(record['price'])
        self.assertIsNone(record['line'])
        self.assertEqual(record['provenance'], 'unverified')

    def test_moneyline_carries_no_line_and_side_markets_must(self):
        with self.assertRaises(snap.SnapshotError):
            snap.make('g', 'MONEYLINE', 'HOME', 'open', line=-2.5, price=-110, **CAPTURED)
        with self.assertRaises(snap.SnapshotError):
            snap.make('g', 'TOTAL', 'OVER', 'open', price=-110, **CAPTURED)

    def test_sub_even_price_is_refused(self):
        with self.assertRaises(snap.SnapshotError):
            snap.make('g', 'SPREAD', 'HOME', 'open', line=-2.5, price=-50, **CAPTURED)

    def test_league_provenance_is_inadmissible_for_a_price(self):
        # The NFL publishes no betting price; the store will not let a citation transfer by association.
        with self.assertRaises(snap.SnapshotError):
            priced(provenance='league')

    def test_non_https_source_is_refused(self):
        with self.assertRaises(snap.SnapshotError):
            priced(source_url='http://www.nfl.com/x')

    def test_line_and_price_cannot_be_strings(self):
        with self.assertRaises(snap.SnapshotError):
            priced(line='-2.5')
        with self.assertRaises(snap.SnapshotError):
            priced(price='minus 110')

    def test_expectation_is_per_market_side_and_stage(self):
        expected = snap.expected_records(['a', 'b'])
        self.assertEqual(len(expected), 2 * 3 * 2 * 2)
        self.assertEqual(len({k[1] for k in expected}), 3, 'every originated market must be expected')

    def test_completeness_counts_holes_instead_of_ignoring_them(self):
        game_ids = ['a', 'b']
        audit = snap.completeness([], game_ids)
        self.assertEqual(audit['expected_pairs'], 24)
        self.assertEqual(audit['holes'], 24)
        self.assertEqual(audit['coverage_pct'], 0.0)
        half = [snap.make('a', 'SPREAD', 'HOME', 'open', missing_reason='no feed'),
                snap.make('a', 'SPREAD', 'HOME', 'close', missing_reason='no feed')]
        audit = snap.completeness(half, game_ids)
        self.assertEqual(audit['holes'], 22)
        self.assertAlmostEqual(audit['coverage_pct'], 2 / 24 * 100, places=2)

    def test_roi_refuses_with_named_reasons(self):
        games = [{'game_id': 'a', 'status': 'final', 'verified': True}]
        ready = snap.roi_ready([priced()], games)
        self.assertFalse(ready['ready'])
        self.assertTrue(ready['blocking_reasons'], 'a refusal must say what is missing')

    def test_devig_needs_both_sides(self):
        # One price cannot be normalised: a half market devigged into 50/50 would invent a baseline.
        self.assertIsNone(snap.devig_open([]))
        self.assertIsNone(snap.devig_open([priced(price=-110)]))
        self.assertIsNone(snap.devig_open([priced(price=-110), None]))
        pair = [dict(priced(price=-110), market='MONEYLINE', line=None),
                dict(priced(price=-105), market='MONEYLINE', line=None)]
        both = snap.devig_open(pair)
        self.assertEqual(len(both), 2, f'devig must return one probability per side, got {both!r}')
        self.assertAlmostEqual(sum(both), 1.0, places=9, msg='a devigged pair must close to one')
        self.assertGreater(both[0], both[1], 'the side priced at -110 carries more implied probability '
                                             'than the side priced at -105')

    def test_the_chain_reports_a_duplicate_capture_and_an_edit(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            snap.init(store)
            snap.append(store, priced())
            self.assertEqual(snap.verify_chain(store), [])
            snap.append(store, priced())               # same game/market/side/stage
            self.assertTrue(any('duplicate capture' in p for p in snap.verify_chain(store)),
                            'one market side at one stage may be captured once')
            with self.assertRaises(snap.SnapshotError):
                snap.append(store, priced())           # a broken chain refuses further appends
            lines = (store / 'store.jsonl').read_text().splitlines()
            tampered = json.loads(lines[1])
            tampered['price'] = -200
            (store / 'store.jsonl').write_text('\n'.join([lines[0]] + [json.dumps(tampered)]) + '\n')
            problems = snap.verify_chain(store, snap.read(store))
            self.assertTrue(any('hash does not match' in p for p in problems),
                            'an edited record must stop matching its own hash')


class VerifiedResultsFeed(unittest.TestCase):
    """Requirement 2: the feed exists, and its checks are the deliverable."""

    @classmethod
    def setUpClass(cls):
        cls.rows, cls.summary, cls.detail = res.feed()

    def test_every_row_in_the_feed_passes_every_check(self):
        self.assertEqual(self.summary['checks_failed'], 0)
        self.assertEqual(self.summary['unverified'], 0)
        self.assertEqual(self.summary['verified'], self.summary['games'])
        self.assertGreater(self.summary['checks_run'], self.summary['games'],
                           'a feed with one check per game is not a verification')

    def test_both_record_progressions_agree(self):
        for item in self.summary['reconciliations']:
            self.assertEqual(item['clubs_tested'], item['clubs_agreeing'], item['name'])
        self.assertEqual(self.detail['progression_mismatches'] if 'progression_mismatches' in self.detail
                         else [], [])
        for key in ('progression_into_9', 'progression_into_10'):
            self.assertTrue(all(p['pass'] for p in self.detail[key]), key)

    def test_week8_bye_clubs_are_excluded_and_said_so(self):
        first = self.summary['reconciliations'][0]
        self.assertEqual(first['clubs_tested'], 28)
        self.assertEqual(first['clubs_excluded'], ['HOU', 'NO', 'NYG', 'SF'],
                         'the bye block prints records as of retrieval, not as of the week (F28)')
        self.assertEqual(self.summary['reconciliations'][1]['clubs_tested'], 32,
                         'the Week 9 to Week 10 pair covers all 32 clubs')

    def test_only_completed_games_move_a_record(self):
        w10 = [r for r in self.rows if r['week'] == 10]
        self.assertEqual(sum(1 for r in w10 if r['status'] == 'final'), 1)
        self.assertEqual(len(w10), 14)

    def test_winning_percentage_counts_a_tie_as_half(self):
        self.assertEqual(res.winning_percentage('5-3-1'), round(5.5 / 9, 3))
        self.assertEqual(res.winning_percentage('6-2'), 0.75)
        self.assertEqual(res.page_form(*res._split('5-3-1')), '5-3-1')
        self.assertEqual(res.page_form(6, 2, 0), '6-2', 'the page omits a zero tie column')

    def test_single_appearance_is_per_week(self):
        self.assertEqual(self.summary['duplicate_club_problems'], [])
        games = [dict(r, season=2026) for r in self.rows if r['week'] == 9] + \
                [dict(self.rows[0], game_id='dup', season=2026)]
        self.assertTrue(res.single_appearance(games), 'a duplicated club inside one week must be caught')

    def test_settlement_conventions(self):
        game = {'status': 'final', 'verified': True, 'away_points': 33, 'home_points': 10}
        self.assertEqual(res.settle('MONEYLINE', 'AWAY', None, game), 'win')
        self.assertEqual(res.settle('MONEYLINE', 'HOME', None, game), 'loss')
        # 33-10 = 23, so a 23-point handicap received is exactly a push on both sides.
        self.assertEqual(res.settle('SPREAD', 'AWAY', -23, game), 'push')
        self.assertEqual(res.settle('SPREAD', 'HOME', 23, game), 'push')
        self.assertEqual(res.settle('SPREAD', 'HOME', 22.5, game), 'loss')
        self.assertEqual(res.settle('SPREAD', 'AWAY', -22.5, game), 'win')
        self.assertEqual(res.settle('TOTAL', 'OVER', 43, game), 'push')
        self.assertEqual(res.settle('TOTAL', 'UNDER', 43, game), 'push')
        self.assertEqual(res.settle('SPREAD', 'HOME', 20.5, dict(game, home_points=11)), 'loss')

    def test_unplayed_and_unverified_games_cannot_be_settled(self):
        self.assertIsNone(res.settle('MONEYLINE', 'HOME', None,
                                     {'status': 'scheduled', 'verified': True,
                                      'away_points': None, 'home_points': None}))
        with self.assertRaises(snap.SnapshotError):
            res.settle('MONEYLINE', 'HOME', None, {'status': 'final', 'verified': False,
                                                   'away_points': 3, 'home_points': 10})

    def test_evidence_files_record_both_page_renderings(self):
        for path in (res.WEEK8, res.WEEK9, res.WEEK10):
            payload = json.loads(path.read_text())
            games = payload.get('games') or payload.get('week8_games')
            for game in games:
                self.assertIn('link_label', game)
                self.assertTrue({'winner', 'winner_indicator'} & set(game),
                                'a rendered page gives the winner twice: the label and the indicator')

    def test_two_independent_transcriptions_of_the_same_pages_agree(self):
        # data/board/raw/week-NN.txt was committed by session a77d40e1 through PR #40. Agreement
        # between it and this feed is a second witness; it is not the same transcription read twice.
        cross, weeks = res.cross_check(self.rows, {9: {'PIT', 'TEN'},
                                                   10: {'CHI', 'DEN', 'PHI', 'TB'}})
        self.assertEqual(cross['captures_present'], 2, 'the second witness must actually be present')
        self.assertEqual(cross['games_compared'], cross['games_agreeing'])
        self.assertEqual(cross['games_compared'], self.summary['games'])
        self.assertEqual(cross['problems'], [])
        self.assertEqual((cross['bye_agreeing'], cross['bye_weeks_compared']), (2, 2))
        self.assertEqual({w['week'] for w in weeks}, {9, 10})

    def test_a_captains_name_with_digits_does_not_vanish(self):
        # A narrower character class once dropped both San Francisco games and looked like the other
        # session had lost two rows. Team names carry digits, so the parser must too.
        capture = res.read_raw_capture(9)
        self.assertIn('raiders-at-49ers-2026-reg-9', capture['games'])
        self.assertEqual(capture['games']['raiders-at-49ers-2026-reg-9']['home_points'], 38)

    def test_an_absent_capture_is_reported_as_absent_not_as_agreement(self):
        empty = res.read_raw_capture(53)
        self.assertFalse(empty['present'])
        self.assertEqual(empty['games'], {})

    def test_a_changed_field_would_be_caught_by_the_cross_check(self):
        tampered = [dict(r) for r in self.rows]
        for row in tampered:
            if row['week'] == 9:
                row['home_points'] = (row['home_points'] or 0) + 1
                break
        cross, _weeks = res.cross_check(tampered)
        self.assertTrue(cross['problems'], 'the second witness must fail when a score is wrong')
        self.assertLess(cross['games_agreeing'], cross['games_compared'])

    def test_join_reports_the_undated_lines_as_the_gap_they_are(self):
        join = res.join_line_snapshot(self.rows)
        self.assertEqual(join['games_in_feed'], len(self.rows))
        self.assertEqual(join['games_with_a_usable_quote'], 0,
                         'no captured, stage-labelled open number exists in this repository')
        self.assertLessEqual(join['games_with_a_line_value'], join['games_in_feed'])

    def test_backtest_is_not_ready_and_says_why(self):
        ready = res.readiness(self.rows)
        self.assertFalse(ready['backtest_ready'])
        self.assertEqual(ready['finals_with_a_market_line'], 0)
        self.assertEqual(ready['finals_verified'], ready['finals_in_feed'])


class OriginationOrder(unittest.TestCase):
    """Requirements 3 and 4: a sequence, and three columns that cannot merge."""

    DIST = {(24, 17): 0.5, (17, 24): 0.3, (21, 21): 0.2}

    def test_the_stage_order_is_the_mandated_one(self):
        log = originate_log = originate.originate(self.DIST, now_utc='2026-11-14T00:00:00Z')
        self.assertEqual([e['stage'] for e in log], ['side', 'total', 'moneyline'])
        self.assertEqual([e['depends_on'] for e in log], [None, 'side', 'total'])

    def test_out_of_order_is_rejected_with_reasons(self):
        problems = originate.validate_order([
            {'sequence': 1, 'stage': 'moneyline', 'depends_on': None},
            {'sequence': 2, 'stage': 'side', 'depends_on': None},
            {'sequence': 3, 'stage': 'total', 'depends_on': 'moneyline'}])
        self.assertTrue(problems)
        self.assertTrue(any('out of order' in p for p in problems))
        self.assertTrue(any('derived from the total' in p for p in problems),
                        'a moneyline must be declared as derived, not fitted')

    def test_unknown_stage_and_undeclared_dependencies_are_rejected(self):
        problems = originate.validate_order([{'sequence': 1, 'stage': 'quarter', 'depends_on': None},
                                            {'sequence': 2, 'stage': 'side', 'depends_on': 'total'},
                                            {'sequence': 3, 'stage': 'total', 'depends_on': None}])
        self.assertIn('entry 1: unknown stage \'quarter\'', problems)
        self.assertTrue(any('side is the primitive' in p for p in problems))
        self.assertTrue(any('total must declare' in p for p in problems))
        self.assertEqual(originate.validate_order(
            [{'sequence': 1, 'stage': 'side', 'depends_on': None},
             {'sequence': 2, 'stage': 'total', 'depends_on': 'side'},
             {'sequence': 3, 'stage': 'moneyline', 'depends_on': 'total'}]), [])

    def test_fair_lines_sit_on_the_published_grid(self):
        stages = {e['output']['market']: e['output'] for e in originate.originate(self.DIST)}
        for market in ('SPREAD', 'TOTAL'):
            line = stages[market]['fair_line']
            self.assertAlmostEqual((line * 2) % 1, 0.0, msg=f'{market} line {line} off the half-point grid')
        self.assertIsNone(stages['MONEYLINE']['fair_line'], 'a moneyline has no line field')

    def test_probabilities_survive_the_consistency_check_and_tampering_does_not(self):
        stages = [e['output'] for e in originate.originate(self.DIST)]
        self.assertEqual(originate.consistency_check(self.DIST, stages), [])
        tampered = [dict(stages[0]), dict(stages[1]), dict(stages[2])]
        tampered[0]['cover'] = 0.99
        self.assertTrue(originate.consistency_check(self.DIST, tampered),
                        'a published probability must be reproducible from the distribution')

    def test_difference_is_none_rather_than_fair_minus_zero(self):
        out = originate.difference(-2.5, None)
        self.assertIsNone(out['difference'])
        self.assertTrue(out['reason'])
        self.assertEqual(originate.difference(-2.5, -3.0)['difference'], 0.5)

    def test_columns_admit_only_a_captured_open_line(self):
        fair = originate.fair_side(self.DIST)
        undated = dict(priced(), captured_at=None, stage='close')
        row = originate.columns(fair, undated, game_id='g')
        self.assertIsNone(row['market_line'])
        self.assertEqual(row['status'], 'blank')
        fair_line = fair['fair_line']
        row = originate.columns(fair, dict(priced(), line=fair_line), game_id='g')
        self.assertEqual(row['market_line'], fair_line)
        self.assertEqual(row['status'], 'measured')
        self.assertEqual(row['difference'], 0.0)
        sharper = originate.columns(fair, dict(priced(), line=fair_line - 1.5), game_id='g')
        self.assertAlmostEqual(sharper['difference'], 1.5)
        self.assertEqual(sharper['direction'], 'model higher')
        self.assertEqual(abs(sharper['difference_ticks']), 3, 'one tick is a half point')

    def test_a_bare_number_is_not_a_market_line(self):
        row = originate.columns(originate.fair_side(self.DIST),
                                {'line': -3.0, 'price': -115, 'stage': 'open'}, game_id='g')
        self.assertIsNone(row['market_line'], 'a record without captured_at is not an open quote')


class SignalStakingSplit(unittest.TestCase):
    """Requirement 5: the two boards, and the refusals that keep them apart."""

    BETS = [{'p_model': .60, 'p_market': .55, 'outcome': 1, 'week': 1},
            {'p_model': .40, 'p_market': .45, 'outcome': 0, 'week': 1},
            {'p_model': .55, 'p_market': .50, 'outcome': 1, 'week': 2},
            {'p_model': .50, 'p_market': .50, 'outcome': 'push', 'week': 2},
            {'p_model': .65, 'p_market': .60, 'outcome': 0, 'week': 3}]

    def test_push_is_excluded_from_scoring_and_counted(self):
        block = ss.signal_block(self.BETS)
        self.assertEqual(block['n'], 4)
        self.assertEqual(block['excluded_push'], 1)
        self.assertEqual(block['status'], 'measured')

    def test_one_week_gets_no_interval(self):
        block = ss.signal_block([b for b in self.BETS if b['week'] == 1])
        self.assertIsNone(block['gain_lcb'])
        self.assertIn('interval_note', block)

    def test_staking_refuses_anything_that_is_not_a_captured_open_price(self):
        with self.assertRaises(ss.SplitError):
            ss.staking_block(self.BETS)
        with self.assertRaises(ss.SplitError):
            ss.staking_block(self.BETS[:1], {None: dict(priced(), stage='close')})
        with self.assertRaises(ss.SplitError):
            ss.staking_block(self.BETS[:1], {None: dict(priced(), captured_at=None)})
        from engine.core import american_to_decimal
        ok = ss.staking_block([dict(self.BETS[0], bet_id='b1')], {'b1': priced()})
        self.assertEqual(ok['settled'], 1)
        self.assertEqual(ok['price_basis'], 'captured open snapshots')
        self.assertAlmostEqual(ok['net_units'], american_to_decimal(-110) - 1, places=9)
        losing = ss.staking_block([dict(self.BETS[4], bet_id='b1')], {'b1': priced()})
        self.assertAlmostEqual(losing['net_units'], -1.0, places=9)

    def test_a_refund_is_zero_units_not_a_win(self):
        push = ss.staking_block([{'outcome': 'push', 'week': 1, **priced()}])
        self.assertEqual(push['net_units'], 0.0)
        self.assertEqual(push['push_refunded'], 1)

    def test_money_cannot_buy_a_rank(self):
        with self.assertRaises(ss.SplitError):
            ss.leaderboard([{'id': 'rich', 'track': 'G1', 'staking': {'roi': 0.4, 'n': 500}}])

    def test_positive_point_estimate_with_a_flat_lcb_is_not_ranked(self):
        signal = ss.signal_block(self.BETS)
        board = ss.leaderboard([{'id': 'demo', 'track': 'G1', 'signal': signal,
                                 'staking': ss.staking_block([dict(b, bet_id=f'b{i}', **priced())
                                                              for i, b in enumerate(self.BETS)])}])
        row = board['rows'][0]
        self.assertFalse(row['ranked'])
        self.assertIsNone(row['rank'])
        self.assertTrue(row['disqualification'])
        self.assertEqual(board['sort_key'].split(';')[0], 'signal_gain_lcb descending')

    def test_rules_name_both_boards(self):
        names = dict(ss.rules())
        joined = ' '.join(names.values()).lower()
        for token in ('push', 'signal', 'staking'):
            self.assertIn(token, joined)


class ReplacementDepth(unittest.TestCase):
    """Requirement 6: distance travelled, and an honest unknown."""

    REPORT = [{'team': 'SEA', 'player': 'Sam Darnold', 'position': 'QB', 'injuries': 'Ribs',
               'practice_status': '—', 'game_status': 'Out'},
              {'team': 'SEA', 'player': 'Drew Lock', 'position': 'QB', 'injuries': '—',
               'practice_status': '—', 'game_status': 'Questionable'}]
    CHART = [{'team': 'SEA', 'unit': 'Offense', 'slot': 'QB',
              'order': ['Sam Darnold', 'Drew Lock', 'Jalen Milroe']}]

    def test_another_out_name_below_the_slot_is_walked_past(self):
        both_out = [{'team': 'SEA', 'player': 'Sam Darnold', 'position': 'QB', 'injuries': 'Ribs',
                     'practice_status': '—', 'game_status': 'Out'},
                    {'team': 'SEA', 'player': 'Drew Lock', 'position': 'QB', 'injuries': '—',
                     'practice_status': '—', 'game_status': 'Out'}]
        rows = repl.evaluate(self.CHART, both_out)
        qb = [r for r in rows if r['slot'] == 'QB'][0]
        self.assertEqual(qb['replacement_player'], 'Jalen Milroe',
                         'the replacement is the next name who can play, not the next name printed')
        self.assertEqual(qb['strings_travelled'], 2)
        self.assertEqual(qb['depth_from_top'], 3)
        self.assertFalse(qb['chart_exhausted'])

    def test_a_conditional_name_below_the_slot_reports_two_distances(self):
        rows = repl.evaluate(self.CHART, self.REPORT)   # Lock is Questionable
        qb = [r for r in rows if r['slot'] == 'QB'][0]
        self.assertEqual(qb['replacement_player'], 'Drew Lock')
        self.assertEqual(qb['strings_travelled'], 1)
        self.assertEqual(qb['certain_replacement'], 'Jalen Milroe')
        self.assertEqual(qb['certain_strings'], 2)
        self.assertTrue(qb['replacement_is_conditional'])
        self.assertIn('Questionable', qb['depth_note'])
        self.assertIn('if he plays', qb['depth_note'])
        rollup = repl.unit_rollup(rows)[0]
        self.assertEqual((rollup['max_depth'], rollup['worst_case_max_depth']), (1, 2))
        self.assertEqual(rollup['conditional_vacancies'], 1)

    def test_questionable_alone_does_not_vacate_a_slot(self):
        rows = repl.evaluate(self.CHART, [self.REPORT[1]])
        self.assertEqual([r for r in rows if r['slot'] == 'QB' and r['replacement_player']], [])

    def test_exhausted_chart_and_shared_backup_are_reported(self):
        chart = [{'team': 'SEA', 'unit': 'Offense', 'slot': slot,
                  'order': ['Charles Cross', 'Josh Jones']} for slot in ('LT', 'RT')]
        report = [{'team': 'SEA', 'player': 'Charles Cross', 'position': 'T', 'injuries': 'Ankle',
                   'practice_status': '—', 'game_status': 'Out'}]
        rows = repl.evaluate(chart, report)
        self.assertEqual({r['replacement_player'] for r in rows if r['slot']}, {'Josh Jones'})
        self.assertTrue(all(r['strings_travelled'] == 1 for r in rows if r['slot'] == 'LT'))
        exhausted = repl.evaluate([{'team': 'SEA', 'unit': 'Defense', 'slot': 'S',
                                    'order': ['Chuck Clark']}],
                                  [{'team': 'SEA', 'player': 'Chuck Clark', 'position': 'S',
                                    'injuries': '—', 'practice_status': '—', 'game_status': 'Out'}])
        row = [r for r in exhausted if r['slot'] == 'S'][0]
        self.assertTrue(row['chart_exhausted'])
        self.assertIsNone(row['replacement_player'])

    def test_no_chart_means_unknown_not_zero(self):
        rows = repl.evaluate([], [{'team': 'GB', 'player': 'X', 'position': 'LB', 'injuries': '—',
                                    'practice_status': '—', 'game_status': 'Out'}])
        self.assertTrue(rows)
        self.assertIsNone(rows[0]['strings_travelled'])
        self.assertFalse(rows[0]['sourced'])
        self.assertTrue(rows[0]['reason'])

    def test_off_chart_unavailable_player_is_a_recorded_unknown(self):
        rows = repl.evaluate(self.CHART, [{'team': 'SEA', 'player': 'Nobody On Chart', 'position': 'TE',
                                           'injuries': '—', 'practice_status': '—',
                                           'game_status': 'Doubtful'}])
        match = [r for r in rows if r['vacated_player'] == 'Nobody On Chart']
        self.assertEqual(len(match), 1)
        self.assertIsNone(match[0]['slot'])
        self.assertIsNone(match[0]['strings_travelled'])

    def test_two_statuses_for_one_player_raise(self):
        with self.assertRaises(repl.ReplacementError):
            repl.statuses_by_player([{'team': 'SEA', 'player': 'A', 'game_status': 'Out'},
                                     {'team': 'SEA', 'player': 'A', 'game_status': 'Questionable'}])

    def test_string_label_refuses_to_invent_a_tier(self):
        self.assertEqual(repl.string_label(3), '3rd')
        for bad in (9, 0, '3', 1.5, True):
            with self.subTest(rank=bad), self.assertRaises(repl.ReplacementError):
                repl.string_label(bad)

    def test_rollup_reports_the_known_share(self):
        rows = repl.evaluate(self.CHART, self.REPORT)
        rollup = repl.unit_rollup(rows)
        self.assertEqual(rollup[0]['depth_known_share'], 1.0)
        self.assertEqual(rollup[0]['depth_unknown'], 0)
        self.assertEqual(rollup[0]['vacancies'], 1)


class CorrelationGate(unittest.TestCase):
    """Requirement 7: official numbers only, and n printed with everything."""

    def pairs(self, n=4, **overrides):
        base = [{'game_id': f'g{i}', 'a': i, 'b': 10 - i, 'sources': ['nfl-schedule-w9'],
                 'leg_games': [f'g{i}', f'g{i}']} for i in range(1, n + 1)]
        return [dict(p, **overrides) for p in base]

    def test_n_comes_from_the_complete_pairs_used(self):
        rows = self.pairs(4, ) + [{'game_id': 'g9', 'a': 5, 'b': None,
                                  'sources': ['nfl-schedule-w9'], 'leg_games': ['g9', 'g9']}]
        out = corr.measure('test pair', rows)
        self.assertEqual(out['n'], 4)
        self.assertEqual(out['dropped_incomplete'], 1)

    def test_an_unregistered_source_voids_the_pair_set(self):
        with self.assertRaises(corr.CorrelationGate):
            corr.measure('test pair', self.pairs(3, sources=['some-blog']))
        with self.assertRaises(corr.CorrelationGate):
            corr.measure('test pair', self.pairs(3, sources=[]))

    def test_manifest_registration_is_required_not_assumed(self):
        # Allowlisted but never registered as a read record: refused, because a name in a string
        # is not evidence that anybody retrieved a page.
        with self.assertRaises(corr.CorrelationGate) as ctx:
            corr.resolve_sources(['nfl-schedule-w7'])
        self.assertIn('not in the official allowlist', str(ctx.exception))
        registered = {entry['id'] for entry in json.loads((ROOT / 'evidence' / 'sources.json').read_text())}
        for source in sorted(corr.OFFICIAL_SOURCES & registered):
            pass  # the allowlist is a subset check, not an equality; the real test is below
        self.assertTrue(corr.resolve_sources(['nfl-schedule-w9'], field_class='score'))

    def test_club_host_may_not_source_a_score_field(self):
        with self.assertRaises(corr.CorrelationGate):
            corr.resolve_sources(['chiefs-depth'], field_class='score')
        self.assertTrue(corr.resolve_sources(['chiefs-depth'], field_class='availability'))

    def test_legs_from_different_games_are_refused(self):
        rows = self.pairs(3)
        rows[0]['leg_games'] = ['g1', 'other-game']
        with self.assertRaises(corr.CorrelationGate):
            corr.require_alignment(rows)
        with self.assertRaises(corr.CorrelationGate):
            corr.require_alignment(self.pairs(2, game_id='g1'))

    def test_constant_leg_is_undefined_not_zero(self):
        rows = [{'game_id': f'g{i}', 'a': 1.0, 'b': b, 'sources': ['nfl-schedule-w9'],
                 'leg_games': [f'g{i}', f'g{i}']} for i, b in enumerate([1, 2, 3, 1, 2], 1)]
        out = corr.measure('constant leg', rows)
        self.assertEqual(out['verdict'], 'undefined_constant_leg')
        self.assertIsNone(out['r'])
        self.assertFalse(out['may_price_joint'])

    def test_tiny_samples_never_authorise_a_joint_price(self):
        out = corr.measure('test pair', self.pairs(6))
        self.assertEqual(out['n'], 6)
        self.assertFalse(out['may_price_joint'])
        self.assertIsNone(corr.joint_probability(out, 0.6, 0.55),
                          'the joint route must be closed when the gate has not opened')

    def test_predeclared_constants_are_the_published_ones(self):
        self.assertEqual(corr.MIN_N, 30)
        self.assertEqual(corr.DEADBAND, 0.10)
        self.assertEqual(corr.CONFIDENCE, 0.95)

    def test_measured_register_values_match_the_audit(self):
        audit = requirements_audit.measure(__import__('build').INJ)
        rows = tables_cells('depth-correlations.html', 'Correlation register', prefix=True)
        self.assertEqual(len(rows), len(audit['correlations']))
        for cells, measured in zip(rows, audit['correlations']):
            self.assertEqual(cells[2], str(measured['n']))


class DemotionGate(unittest.TestCase):
    """Requirement 8: one trigger demotes, and the way back is earned."""

    CLEAN = [{'week': w, 'signal_lcb': 0.02, 'calibration_mae': 0.01, 'coverage': 0.9,
              'missing_close_share': 0.0, 'net_units': 1.0, 'drawdown_units': -3.0}
             for w in range(1, 9)]

    def test_a_clean_window_holds(self):
        out = demotion.evaluate(self.CLEAN)
        self.assertEqual(out['action'], 'hold')
        self.assertEqual(out['state_after'], 'live')

    def test_any_single_trigger_demotes(self):
        for field, value in (('signal_lcb', -0.01), ('calibration_mae', 0.09), ('coverage', 0.2),
                            ('missing_close_share', 0.5)):
            broken = self.CLEAN[:-1] + [dict(self.CLEAN[-1], **{field: value})]
            out = demotion.evaluate(broken)
            with self.subTest(field=field):
                self.assertEqual(out['action'], 'demote')
                self.assertEqual(out['state_after'], 'paper')
                self.assertEqual([t[0] for t in out['triggers']], [
                    {'signal_lcb': 'signal', 'calibration_mae': 'calibration', 'coverage': 'coverage',
                     'missing_close_share': 'provenance'}[field]])

    def test_silence_is_not_a_pass(self):
        sparse = [{'week': w} for w in range(1, 9)]
        out = demotion.evaluate(sparse)
        self.assertEqual(out['action'], 'demote')
        named = {t[0] for t in out['triggers']}
        self.assertIn('signal', named)
        self.assertIn('calibration', named)
        self.assertIn('coverage', named)

    def test_drawdown_suspends_and_cannot_rank(self):
        rows = self.CLEAN[:-1] + [dict(self.CLEAN[-1], drawdown_units=-19.0)]
        out = demotion.evaluate(rows)
        self.assertEqual(out['action'], 'suspend')
        self.assertEqual(out['state_after'], 'suspended')
        self.assertEqual(out['triggers'], [], 'risk is not merit')

    def test_relisting_needs_the_cooldown_and_a_clean_run(self):
        soon = demotion.relist_ready(9, [dict(e, triggers=[]) for e in self.CLEAN[:4]])
        self.assertFalse(soon['relist_ready'])
        self.assertEqual(len(soon['blocked_by']), 2)
        dirty = demotion.relist_ready(1, [dict(e, triggers=[('signal', 'x')]) for e in self.CLEAN[1:9]])
        self.assertFalse(dirty['relist_ready'])
        ready = demotion.relist_ready(1, [{'week': w, 'triggers': []} for w in range(2, 15)])
        self.assertTrue(ready['relist_ready'])

    def test_policy_cannot_be_moved_silently(self):
        self.assertEqual(demotion.check_policy(demotion.POLICY), 'published')
        with self.assertRaises(demotion.DemotionError):
            demotion.check_policy({**demotion.POLICY, 'signal_lcb_halt': -9.0})
        with self.assertRaises(demotion.DemotionError):
            demotion.check_policy({'min_eval_weeks': 4})
        labelled = demotion.check_policy({**demotion.POLICY, 'signal_lcb_halt': -9.0,
                                          'changed_by': 'owner 2026-11-14', 'effective_week': 12})
        self.assertEqual(labelled['thresholds_changed'], ['signal_lcb_halt'])
        self.assertEqual(demotion.evaluate(self.CLEAN, policy={**demotion.POLICY, 'signal_lcb_halt': -9.0,
                                                               'changed_by': 'owner', 'effective_week': 12}
                                           )['policy_label']['changed_by'], 'owner')

    def test_promotion_needs_an_artifact_per_gate(self):
        bare = demotion.promotable('X', {g: {'passed': True} for g in demotion.PROMOTION_GATES})
        self.assertFalse(bare['promotable'])
        self.assertEqual(len(bare['gates_without_artifact']), len(demotion.PROMOTION_GATES))
        hash64 = 'a' * 64
        full = demotion.promotable('X', {g: {'artifact': 'evidence/x.json', 'sha256': hash64}
                                        for g in demotion.PROMOTION_GATES})
        self.assertTrue(full['promotable'])

    def test_the_decision_log_is_append_only(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'log.jsonl'
            decision = {'candidate': 'X', 'action': 'demote', 'week': 9,
                        'triggers': [['signal', 'lcb below zero']]}
            first = demotion.append_log(path, decision)
            demotion.append_log(path, {'candidate': 'X', 'action': 'hold', 'week': 10, 'triggers': []})
            self.assertEqual(demotion.verify_log(path), [])
            self.assertEqual(first['previous_hash'], None)
            self.assertEqual(len(demotion.read_log(path)), 2)
            lines = path.read_text().splitlines()
            tampered = json.loads(lines[1])
            tampered['entry']['action'] = 'promote'
            path.write_text(lines[0] + '\n' + json.dumps(tampered) + '\n')
            self.assertTrue(demotion.verify_log(path), 'an edited decision must be detectable')


class ParallelImplementations(unittest.TestCase):
    """PR #37 landed a second set of contracts for the same requirements. Both are kept, and the
    differences between them are measured here so neither can be read as the other."""

    def test_the_two_results_modules_coexist_and_only_one_is_a_feed(self):
        from engine import results as schema_module
        self.assertTrue(hasattr(schema_module, 'VerifiedResult'))
        self.assertFalse(hasattr(schema_module, 'feed'),
                         'the schema module must not be mistaken for the populated feed')
        self.assertTrue(hasattr(res, 'feed') and hasattr(res, 'settle'))

    def test_one_quote_is_both_open_and_close_in_the_other_store(self):
        from engine.prices import MarketType, PriceSnapshot, PriceStore, Side
        one = PriceSnapshot(game_id='g1', market=MarketType.SPREAD, side=Side.HOME, line=-2.5,
                            decimal_price=1.91, quote_utc='2026-11-12T18:00:00Z', operator='X',
                            jurisdiction='WA')
        store = PriceStore()
        store.add(one)
        opening, closing = (store.opening('g1', MarketType.SPREAD, Side.HOME),
                            store.closing('g1', MarketType.SPREAD, Side.HOME))
        self.assertIs(opening, closing, 'both accessors resolve to the same single capture')
        self.assertEqual(store.missing_fields_report()['markets_with_both_open_and_close'], 0,
                         'the guard exists on the store itself, and a caller must read it')
        # The same slate in this session's store: the second stage is a counted hole, not a zero move.
        captured = dict(priced(), game_id='g', prev_hash=None, record_hash='x' * 64)
        audit = snap.completeness([captured], ['g'])
        self.assertEqual(audit['open_close_pairs_priced'], 0)
        self.assertEqual(audit['holes'], 11, 'twelve expected captures minus the one recorded')

    def test_the_two_raw_schema_files_carry_no_rows(self):
        inventory = requirements_audit.raw_file_inventory()
        for name in ('price_snapshots.csv', 'verified_results.csv'):
            self.assertEqual(inventory[name]['data_rows'], 0,
                             f'{name} is documented as a schema; a data row would change that claim')
            self.assertGreater(inventory[name]['comment_lines'], 0)

    def test_the_other_session_contracts_still_refuse_holes(self):
        from engine.prices import MarketType, PriceSnapshot, Side
        from engine.results import GameStatus, VerifiedResult
        with self.assertRaises(ValueError):
            PriceSnapshot(game_id='g', market=MarketType.MONEYLINE, side=Side.HOME, line=-2.5,
                          decimal_price=1.9, quote_utc='2026-11-12T18:00:00Z', operator='X',
                          jurisdiction='WA')
        with self.assertRaises(ValueError):
            PriceSnapshot(game_id='g', market=MarketType.SPREAD, side=Side.HOME, line=-2.5,
                          decimal_price=1.9, quote_utc='', operator='X', jurisdiction='WA')
        with self.assertRaises(ValueError):
            VerifiedResult(game_id='g', season=2026, week=9, home_team='SEA', away_team='DET',
                           home_score=None, away_score=3, status=GameStatus.FINAL,
                           source_url='https://www.nfl.com/x', retrieved_utc='2026-11-14')
        ok = VerifiedResult(game_id='g', season=2026, week=9, home_team='SEA', away_team='DET',
                            home_score=38, away_score=19, status=GameStatus.FINAL,
                            source_url='https://www.nfl.com/x', retrieved_utc='2026-11-14')
        self.assertEqual((ok.margin, ok.total_points), (19, 57))


class PublishedPages(unittest.TestCase):
    """The five new pages exist, and they publish the audit's numbers rather than new ones."""

    @classmethod
    def setUpClass(cls):
        cls.audit = requirements_audit.measure(__import__('build').INJ)

    def test_the_site_now_publishes_every_sessions_pages(self):
        rendered = sorted(f.name for f in ROOT.glob('*.html'))
        # Relaxed by session 0167a04c: six further pages were added after this delta was merged,
        # so a fixed total no longer measures anything. The floor keeps the original intent.
        self.assertGreaterEqual(len(rendered), 30,
                                '15 from the first board, 4 from 4f2e0291, 6 from a77d40e1, '
                                '5 from this session')
        # Both signal pages exist because both were authored: main's announcement and this session\u2019s
        # enforcement. The path that collided was this session\u2019s, so this session moved.
        for name in ('signal-staking.html', 'signal-and-staking.html'):
            self.assertIn(name, rendered)

    def test_all_five_pages_exist_and_are_structurally_clean(self):
        for name in NEW_PAGES:
            with self.subTest(page=name):
                html = (ROOT / name).read_text()
                parser = Page()
                parser.feed(html)
                parser.close()
                self.assertEqual(parser.errors, [])
                self.assertEqual(parser.h1, 1)
                self.assertEqual(parser.current, 1, f'{name} must mark itself current in the nav')

    def test_the_requirement_ledger_covers_all_eight(self):
        rows = tables_cells('requirements.html', 'Requirement ledger')
        self.assertEqual([r[0] for r in rows], [f'R{i}' for i in range(1, 9)])
        for row in rows:
            self.assertIn(row[4], ('Enforced', 'Enforced, inputs absent', 'Enforced, coverage limited',
                                   'Enforced, nothing live'), row[4])

    def test_the_store_page_publishes_the_measured_hole_count(self):
        html = (ROOT / 'price-feed.html').read_text()
        store = self.audit['store']
        self.assertIn(str(store['expected_pairs']), html)
        self.assertIn(str(store['holes']), html)
        self.assertIn(f'{store["coverage_pct"]}%', html)

    def test_the_parallel_stores_are_compared_not_merged(self):
        rows = tables_cells('price-feed.html', 'The two stores that now exist, field by field')
        self.assertEqual(len(rows), 6)
        joined = ' '.join(' '.join(r) for r in rows)
        self.assertIn('counted hole', joined)
        self.assertIn('markets_with_both_open_and_close', joined)

    def test_the_difference_column_is_publicly_blank(self):
        rows = tables_cells('price-feed.html', 'What the column split yields across the slate')
        values = {r[0]: r[1] for r in rows}
        self.assertEqual(values['market_line'], str(self.audit['origination']['rows_with_a_market_line']))
        self.assertEqual(values['difference'], '0')
        self.assertGreater(int(values['fair_line']), 0)

    def test_the_staking_page_publishes_the_refusals_it_claims(self):
        html = (ROOT / 'signal-and-staking.html').read_text()
        self.assertIn('no measured signal block', html)
        self.assertIn('no price record', html)
        self.assertEqual(len(tables_cells('signal-and-staking.html', 'Signal board — the only board that ranks')), 4)
        self.assertEqual(len(tables_cells('signal-and-staking.html', 'Staking board — disclosure only')), 4)

    def test_every_correlation_row_prints_an_n(self):
        rows = tables_cells('depth-correlations.html', 'Correlation register — officially sourced numbers '
                                                        'only, each with its n')
        self.assertTrue(rows)
        for row in rows:
            self.assertTrue(row[2].isdigit(), f'missing n in {row[0]}')
            self.assertEqual(row[6], 'no', 'no joint price may be authorised at this sample size')

    def test_replacement_depth_page_names_the_unmeasurable_cases(self):
        html = (ROOT / 'depth-correlations.html').read_text()
        self.assertIn('unknown, not zero', html)
        for _team, player in self.audit['replacement']['unlisted_vacancies']:
            self.assertIn(player, html, f'the Off-player with no chart row must be named, not dropped: {player}')

    def test_new_flags_are_appended_after_the_existing_register(self):
        rows = tables_cells('flags.html', 'Register continuation · raised 14 Nov 2026 by session '
                                           '1cfcb957')
        self.assertEqual([r[0].split(' ')[0] for r in rows],
                         [f'F{n}' for n in range(32, 42)],
                         'this register must continue main\u2019s numbering without a gap or a reuse')
        self.assertEqual(len([r for r in rows if 'Critical' in r[0]]), 2,
                         'the price gap and the accessibility repair are the two blocking findings')

    def test_every_scrollable_table_region_is_keyboard_reachable(self):
        # The site's own axe check rejects a scrollable region with nothing focusable in it. Naming
        # and focusing the wrap at the generator is what keeps a future linkless wide table passing.
        import re
        for path in sorted(ROOT.glob('*.html')):
            html = path.read_text()
            for match in re.finditer(r'<div class="table-wrap"([^>]*)>', html):
                attrs = match.group(1)
                with self.subTest(page=path.name):
                    self.assertIn('tabindex="0"', attrs)
                    self.assertIn('role="region"', attrs)
                    self.assertIn('aria-label=', attrs)
        ids = [r['cells'][0].split(' ')[0] for r in all_rows('flags.html')
               if r['cells'][0].startswith('F') and len(r['cells'][0].split(' ')[0]) == 3]
        self.assertEqual(len(ids), len(set(ids)), 'the review register has duplicate finding ids')

    def test_the_leaderboard_page_was_not_rewritten(self):
        # This session may only append a pointer; the other session's empty metric cells are evidence.
        html = (ROOT / 'leaderboard.html').read_text()
        self.assertIn('signal-and-staking.html', html, 'the split is useless if the board does not point to it')
        self.assertIn('empty by fact', (ROOT / 'requirements.html').read_text())
        rows = all_rows('leaderboard.html')
        self.assertTrue(rows, 'the leaderboard must still publish its tables')

    def test_the_index_gives_each_new_page_a_row(self):
        rows = tables_cells('index.html', 'Requirements added on 14 Nov 2026 (session 1cfcb957)')
        self.assertEqual([r[0] for r in rows], list(NEW_PAGES))

    def test_no_measured_economic_claim_appears_anywhere(self):
        for name in NEW_PAGES:
            html = (ROOT / name).read_text()
            for banned in ('closing-line edge', 'beat the close', 'guaranteed profit',
                           'expected value of', 'annualised return'):
                self.assertNotIn(banned, html, f'{name} must not claim {banned!r}')


def all_rows(name):
    from html.parser import HTMLParser

    class Captions(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.rows, self.caption, self._in_caption = [], '', False
            self._cell = self._cells = None
            self._in_body = False

        def handle_starttag(self, tag, attrs):
            if tag == 'tbody':
                self._in_body = True
            elif tag == 'caption':
                self._in_caption, self.caption = True, ''
            elif tag == 'tr' and self._in_body:
                self._cells = []
            elif tag in ('td', 'th') and self._cells is not None:
                self._cell = ''

        def handle_data(self, data):
            if self._in_caption:
                self.caption += data
            elif self._cell is not None:
                self._cell += data

        def handle_endtag(self, tag):
            if tag == 'tbody':
                self._in_body = False
            elif tag == 'caption':
                self._in_caption = False
            elif tag in ('td', 'th') and self._cells is not None:
                self._cells.append(self._cell.strip())
                self._cell = None
            elif tag == 'tr' and self._cells:
                self.rows.append({'caption': self.caption.strip(), 'cells': self._cells})
                self._cells = None

    parser = Captions()
    parser.feed((ROOT / name).read_text())
    return parser.rows


def tables_cells(name, caption, prefix=False):
    match = (lambda c: c.startswith(caption)) if prefix else (lambda c: c == caption)
    return [r['cells'] for r in all_rows(name) if match(r['caption'])]


if __name__ == '__main__':
    unittest.main(verbosity=2)
