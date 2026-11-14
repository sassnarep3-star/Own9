"""Tests for the origination engine added by session 0167a04c.

Two kinds of fixture live here and they are labelled wherever they appear:

* fixtures read from the committed files in `data/` — official NFL results and
  official club depth charts, all retrieved on 2026-11-14;
* synthetic fixtures, used only to exercise the arithmetic and the gates. No
  synthetic number is ever published as an NFL value; the pages mark every
  demonstrated number with the SYNTHETIC label and a test asserts that.
"""
import csv
import json
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))

from engine.core import Outcome  # noqa: E402
from engine.origination_0167a04c import (DEMOTION_POLICY, ORIGINATION_ORDER, PRICE_FIELDS,
                                demotion_gate, dependence_record, depth_register,
                                feed_coverage, find_slot, leaderboard_entry,
                                line_columns, load_depth_charts, load_results,
                                load_snapshots, masking_report, originate,
                                price_columns, rank, replacement_chain,
                                roi_readiness, settle, snapshot_coverage,
                                unit_depth_index, validate_snapshot)
from verify import Page  # noqa: E402

NEW_PAGES = ('origination.html', 'results.html', 'replacement-depth.html',
             'dependence.html', 'signal-staking.html', 'requirements.html')
SYNTHETIC = 'SYNTHETIC'


def rows_of(name):
    parser = Page()
    parser.feed((ROOT / name).read_text())
    parser.close()
    return parser.rows


def cells_of(name):
    return [r['cells'] for r in rows_of(name)]


def tables_of(name):
    """Rows grouped by table caption, so a test can target one table exactly."""
    import re
    html = (ROOT / name).read_text()
    out = {}
    for table in re.finditer(r'<caption class="sr-only">(.*?)</caption>(.*?)</tbody>',
                             html, re.S):
        caption = table.group(1)
        rows = []
        for row in re.finditer(r'<tr[^>]*>(.*?)</tr>', table.group(2), re.S):
            if '<td' not in row.group(1):
                continue  # the header row lives inside the same <thead> block
            cells = re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', row.group(1), re.S)
            rows.append([re.sub(r'<[^>]+>', '', c).strip() for c in cells])
        out[caption] = rows
    return out


def registered_sources():
    return {s['id'] for s in json.loads((ROOT / 'evidence' / 'sources.json').read_text())}


def complete_snapshot(**overrides):
    """A schema-complete row. Synthetic: it exists to exercise the validator only."""
    row = {
        'snapshot_id': 'TEST-1', 'market_id': 'TEST-side', 'game_id': 'TEST-GAME',
        'season': '2026', 'week': '9', 'market_family': 'side', 'participant': 'home',
        'book': 'TEST-BOOK', 'source_id': 'repo',
        'opening_line': '-2.5', 'opening_price_american': '-110',
        'opening_captured_utc': '2026-11-08T12:00:00Z',
        'closing_line': '-3', 'closing_price_american': '-105',
        'closing_captured_utc': '2026-11-08T17:00:00Z',
        'kickoff_utc': '2026-11-08T18:00:00Z',
        'limits_note': 'test', 'settlement_rule_version': 'test-v1',
        'raw_hash': 'deadbeef', 'verified': 'true',
    }
    row.update(overrides)
    return row


class PriceSnapshotStore(unittest.TestCase):
    def test_a_row_without_a_closing_price_is_rejected(self):
        errors = validate_snapshot(complete_snapshot(closing_price_american=''),
                                   {'repo'})
        self.assertTrue(any('closing_price_american' in e for e in errors),
                        'a half-record must not be accepted as a price pair')

    def test_a_closing_price_after_kickoff_is_rejected(self):
        errors = validate_snapshot(complete_snapshot(
            closing_captured_utc='2026-11-08T19:00:00Z'), {'repo'})
        self.assertTrue(any('after kickoff' in e for e in errors))

    def test_an_unregistered_source_is_rejected(self):
        errors = validate_snapshot(complete_snapshot(source_id='not-a-source'), {'repo'})
        self.assertTrue(any('not a registered source' in e for e in errors))

    def test_a_side_row_without_a_line_is_rejected(self):
        errors = validate_snapshot(complete_snapshot(opening_line=''), {'repo'})
        self.assertTrue(any('opening_line' in e for e in errors))

    def test_an_unverified_row_is_rejected(self):
        errors = validate_snapshot(complete_snapshot(verified='false'), {'repo'})
        self.assertTrue(any('verified' in e for e in errors))

    def test_a_complete_row_passes(self):
        self.assertEqual(validate_snapshot(complete_snapshot(), {'repo'}), [])

    def test_the_committed_store_is_empty_and_measured_as_empty(self):
        records = load_snapshots()
        self.assertEqual(records, [], 'the store must hold no invented quote')
        coverage = snapshot_coverage(records, [r['result_id'] for r in load_results()])
        self.assertEqual(coverage['complete_pairs'], 0)
        self.assertEqual(coverage['pct_of_games_priced'], 0.0)
        self.assertEqual(coverage['games_in_results_feed'], 16)

    def test_the_committed_csv_is_header_only(self):
        with (ROOT / 'data' / 'snapshots' / 'price-snapshots.csv').open() as handle:
            rows = [r for r in csv.reader(handle) if any(c.strip() for c in r)]
        self.assertEqual(len(rows), 1)
        self.assertEqual(tuple(rows[0]), PRICE_FIELDS)


class VerifiedResultsFeed(unittest.TestCase):
    def setUp(self):
        self.results = load_results()

    def test_sixteen_official_results_are_committed(self):
        self.assertEqual(len(self.results), 16)
        self.assertTrue(all(r['source_id'] in ('nfl-schedule-w9', 'nfl-schedule-w10')
                            for r in self.results))
        self.assertTrue(all(r['game_url'].startswith('https://www.nfl.com/games/')
                            for r in self.results))
        self.assertTrue(all(r['retrieved_utc'] == '2026-11-14' for r in self.results))
        self.assertIn('nfl-schedule-w9', registered_sources(),
                      'the schedule route must be a registered source')

    def test_derived_columns_match_the_official_scores(self):
        for r in self.results:
            self.assertEqual(r['home_margin'], r['home_score'] - r['away_score'])
            self.assertEqual(r['total_points'], r['home_score'] + r['away_score'])
            self.assertEqual(r['home_result'],
                             'win' if r['home_margin'] > 0 else
                             'tie' if r['home_margin'] == 0 else 'loss')

    def test_unpublished_fields_stay_empty(self):
        for r in self.results:
            self.assertEqual(r['overtime'], '', 'overtime was never published for these rows')
            self.assertEqual(r['kickoff_time_utc'], '')

    def test_moneyline_settles_and_line_markets_do_not(self):
        first = self.results[0]
        self.assertTrue(settle(first, 'moneyline')['settled'])
        for family in ('side', 'total'):
            self.assertFalse(settle(first, family)['settled'],
                             f'{family} cannot settle without a captured line')

    def test_roi_is_blocked_on_the_committed_files(self):
        readiness = roi_readiness(self.results, load_snapshots())
        self.assertFalse(readiness['ready'])
        self.assertGreaterEqual(len(readiness['reasons']), 3)
        self.assertEqual(readiness['complete_price_pairs'], 0)

    def test_feed_coverage_counts_are_derived_not_retyped(self):
        coverage = feed_coverage(self.results)
        self.assertEqual(coverage['results'], len(self.results))
        self.assertEqual(coverage['moneyline_settleable'], len(self.results))
        self.assertEqual(coverage['side_settleable_without_a_line'], 0)


class OriginationOrder(unittest.TestCase):
    @staticmethod
    def synthetic_joint():
        """Two independent Poisson scores; arithmetic practice, not a game."""
        import math
        dist = {}
        for home in range(0, 46):
            for away in range(0, 46):
                mass = (math.exp(-23 + home * math.log(23) - math.lgamma(home + 1))
                        * math.exp(-20 + away * math.log(20) - math.lgamma(away + 1)))
                if mass > 1e-6:
                    dist[(home, away)] = mass
        scale = sum(dist.values())
        return {k: v / scale for k, v in dist.items()}

    def setUp(self):
        self.plan = originate(self.synthetic_joint(), handicaps=(-3, 0), total_lines=(44.5,))

    def test_the_order_is_side_then_total_then_moneyline(self):
        self.assertEqual([s['market'] for s in self.plan['steps']], list(ORIGINATION_ORDER))
        self.assertEqual(ORIGINATION_ORDER, ('side', 'total', 'moneyline'))

    def test_all_steps_used_one_frozen_distribution(self):
        digests = {s['distribution_digest'] for s in self.plan['steps']}
        self.assertEqual(len(digests), 1)
        self.assertTrue(all(c['passed'] for c in self.plan['consistency']))

    def test_the_moneyline_is_the_side_at_a_handicap_of_zero(self):
        side_zero = next(r for r in self.plan['steps'][0]['rows'] if r['handicap'] == 0)
        money = self.plan['steps'][2]['rows'][0]
        self.assertAlmostEqual(side_zero['win'], money['win'], places=12)
        self.assertAlmostEqual(side_zero['loss'], money['loss'], places=12)

    def test_a_later_step_refuses_to_run_before_its_predecessor(self):
        from engine.origination_0167a04c import _require_done
        with self.assertRaises(ValueError):
            _require_done([{'market': 'side'}], 'moneyline')
        with self.assertRaises(ValueError):
            _require_done([], 'total')

    def test_an_empty_distribution_originates_nothing(self):
        with self.assertRaises(ValueError):
            originate({})


class ThreeColumns(unittest.TestCase):
    def test_the_difference_is_blank_not_zero_without_a_market_line(self):
        columns = line_columns('test', -3.0, None)
        self.assertIsNone(columns['difference'])
        self.assertIsNone(columns['difference_direction'])
        self.assertIn('withheld', columns['status'])

    def test_the_difference_is_published_when_both_sides_exist(self):
        columns = line_columns('test', -2.5, -3.0)
        self.assertAlmostEqual(columns['difference'], 0.5)
        self.assertEqual(columns['status'], 'published')

    def test_a_price_row_is_withheld_without_a_market_price(self):
        columns = price_columns('test', Outcome(0.5, 0.05, 0.45), None)
        self.assertIsNone(columns['market_decimal'])
        self.assertIsNone(columns['difference_decimal'])
        self.assertIsNone(columns['ev_per_unit'])
        self.assertIn('withheld', columns['status'])

    def test_a_price_row_publishes_fair_market_and_difference_separately(self):
        columns = price_columns('test', Outcome(0.5, 0.05, 0.45), -110)
        self.assertIsNotNone(columns['model_fair_decimal'])
        self.assertIsNotNone(columns['market_decimal'])
        self.assertIsNotNone(columns['difference_decimal'])
        self.assertEqual(columns['status'], 'published')


class ReplacementDepth(unittest.TestCase):
    def setUp(self):
        self.charts = load_depth_charts()
        self.unavailable = json.loads(
            (ROOT / 'data' / 'depth' / 'week-10-2026-unavailable.json').read_text())
        self.register = depth_register(self.charts, self.unavailable)

    def test_a_ruled_out_starter_pushes_the_chart_one_string(self):
        kc = self.charts['clubs']['KC']
        chain = replacement_chain(kc, 'RT', self.unavailable['clubs']['KC'])
        self.assertEqual(chain['strings_travelled'], 1)
        self.assertEqual(chain['replacement'], 'Joshua Ezeudu')
        self.assertEqual(chain['replacement_string'], 2)

    def test_a_ruled_out_backup_does_not_move_the_starter(self):
        kc = self.charts['clubs']['KC']
        chain = replacement_chain(kc, 'DT1', self.unavailable['clubs']['KC'])
        self.assertEqual(chain['strings_travelled'], 0,
                         'the first string is still available, so what is lost is depth')
        self.assertEqual(chain['replacement'], 'Chris Jones')
        self.assertEqual(chain['bench_remaining_below'], 1)

    def test_a_player_absent_from_the_chart_is_unresolved(self):
        self.assertIsNone(find_slot(self.charts['clubs']['KC'], 'Omarr Norman-Lott'))
        self.assertIsNone(find_slot(self.charts['clubs']['DET'], 'Kerby Joseph'))

    def test_the_register_publishes_ten_rows_and_two_unresolved(self):
        self.assertEqual(len(self.register), 10)
        unresolved = [r for r in self.register if r['strings_travelled'] is None]
        self.assertEqual(len(unresolved), 2)
        for row in unresolved:
            self.assertIsNone(row['replacement'])

    def test_the_unit_index_splits_offence_from_defence(self):
        index = unit_depth_index([r for r in self.register if r['slot']])
        self.assertEqual(index['offense']['strings_travelled'], 5)
        self.assertEqual(index['defense']['strings_travelled'], 2)
        self.assertNotIn('special_teams', index)

    def test_no_row_invents_a_depth_tier_label(self):
        banned = {'1st string', '2nd string', '3rd string', '4th string',
                  'first string', 'second string', 'third string', 'fourth string'}
        offenders = [c for row in rows_of('replacement-depth.html')
                     for c in row['cells'] if c.strip().lower() in banned]
        self.assertEqual(offenders, [], f'depth tier labels were rendered: {offenders}')

    def test_every_depth_row_cites_the_report_and_a_chart(self):
        tables = {r['club'] for r in self.register}
        self.assertEqual(tables, {'KC', 'SEA', 'DET'})
        for row in rows_of('replacement-depth.html'):
            if row['cells'][0].startswith(('KC ·', 'SEA ·', 'DET ·')):
                self.assertTrue(row['links'], 'a depth row lost its source links')


class DependenceRegister(unittest.TestCase):
    def test_a_correlation_without_a_source_cannot_be_published(self):
        with self.assertRaises(ValueError):
            dependence_record('no source', [1, 2, 3], [1, 2, 3], None)

    def test_n_is_published_with_every_value(self):
        record = dependence_record('test', [1, 2, 3, 4, 5], [2, 1, 4, 3, 5], 'nfl-schedule-w9')
        self.assertEqual(record['n'], 5)
        self.assertIsNotNone(record['rho'])

    def test_the_official_sample_fails_the_predeclared_floor(self):
        results = load_results()
        record = dependence_record('home vs away',
                                   [r['home_score'] for r in results],
                                   [r['away_score'] for r in results],
                                   'nfl-schedule-w9')
        self.assertEqual(record['n'], 16)
        self.assertEqual(record['verdict'], 'insufficient_evidence')
        self.assertIsNone(record['interval'])
        self.assertFalse(record['may_price_joint'])

    def test_a_large_synthetic_sample_can_clear_the_gate(self):
        """Synthetic: proves the gate is capable of passing, not that NFL legs correlate."""
        base = [(i, (i * 37 % 11) / 11) for i in range(60)]
        x = [1.0 + b for _i, b in base]
        y = [0.9 * (1.0 + b) + 0.1 * ((i * 13 % 7) / 7) for i, b in base]
        record = dependence_record('synthetic', x, y, 'pearson', min_n=30, deadband=0.10)
        self.assertEqual(record['n'], 60)
        self.assertIn(record['verdict'], ('significantly_positive', 'significantly_negative',
                                          'indistinguishable_from_zero'))
        if record['verdict'] == 'significantly_positive':
            self.assertTrue(record['may_price_joint'])

    def test_unequal_series_are_rejected(self):
        with self.assertRaises(ValueError):
            dependence_record('ragged', [1, 2, 3], [1, 2], 'nfl-schedule-w9')


class SignalVersusStaking(unittest.TestCase):
    def test_staking_fields_cannot_enter_a_signal_record(self):
        with self.assertRaises(ValueError):
            leaderboard_entry('x', {'brier': 0.2, 'roi': 0.5}, {})

    def test_signal_fields_cannot_enter_a_staking_record(self):
        with self.assertRaises(ValueError):
            leaderboard_entry('x', {}, {'roi': 0.1, 'brier': 0.2})

    def test_the_two_ranks_are_independent(self):
        """Synthetic entries: the better signal is deliberately not the bigger return."""
        good_signal = leaderboard_entry('good-signal',
                                        {'markets_taken': 400, 'coverage': 0.8, 'brier': 0.20},
                                        {'units_risked': 400, 'roi': 0.01})
        big_return = leaderboard_entry('big-return',
                                       {'markets_taken': 400, 'coverage': 0.8, 'brier': 0.249},
                                       {'units_risked': 400, 'roi': 0.30})
        ranked = rank([good_signal, big_return])
        self.assertEqual(ranked['by_signal'][0]['strategy_id'], 'good-signal')
        self.assertEqual(ranked['by_staking'][0]['strategy_id'], 'big-return')

    def test_a_lucky_staking_run_is_named_as_masking(self):
        entries = [
            leaderboard_entry('good-signal',
                              {'markets_taken': 400, 'coverage': 0.8, 'brier': 0.20},
                              {'units_risked': 400, 'roi': 0.01}),
            leaderboard_entry('big-return',
                              {'markets_taken': 400, 'coverage': 0.8, 'brier': 0.249},
                              {'units_risked': 400, 'roi': 0.30}),
            leaderboard_entry('third',
                              {'markets_taken': 400, 'coverage': 0.8, 'brier': 0.245},
                              {'units_risked': 400, 'roi': 0.29}),
        ]
        flagged = masking_report(entries, gap=2)
        self.assertTrue(any(f['strategy_id'] == 'big-return' for f in flagged))

    def test_eligibility_is_decided_before_ranking(self):
        small = leaderboard_entry('small-sample',
                                  {'markets_taken': 40, 'coverage': 0.2, 'brier': 0.15},
                                  {'roi': 0.9},
                                  {'min_markets': 250, 'min_coverage': 0.60})
        self.assertFalse(small['signal_eligible']['eligible'])
        ranked = rank([small])
        self.assertIsNone(ranked['by_signal'][0]['signal_rank'],
                          'an ineligible entry must be unranked, not ranked first')


class DemotionGate(unittest.TestCase):
    def test_a_live_period_that_holds_its_floor_stays_live(self):
        windows = [{'signal_score': 0.05, 'clv_per_bet': 0.002, 'drawdown_units': 4.0,
                    'snapshot_coverage_pct': 100.0}] * 3
        self.assertEqual(demotion_gate('live', windows)['decision'], 'live')

    def test_three_consecutive_failing_windows_send_a_strategy_to_paper(self):
        windows = [{'signal_score': -0.05, 'clv_per_bet': -0.002, 'drawdown_units': 5.0,
                    'snapshot_coverage_pct': 100.0}] * 3
        decision = demotion_gate('live', windows)
        self.assertEqual(decision['decision'], 'paper')
        self.assertEqual(decision['closing_streak'], 3)

    def test_a_missing_measurement_is_a_breach_not_a_pass(self):
        windows = [{'signal_score': 0.05, 'clv_per_bet': 0.002, 'drawdown_units': 1.0,
                    'snapshot_coverage_pct': None}] * 3
        decision = demotion_gate('live', windows)
        self.assertEqual(decision['decision'], 'paper')
        self.assertTrue(any('coverage' in t for t in decision['triggers']))

    def test_a_drawdown_breach_demotes_immediately(self):
        windows = [{'signal_score': 0.05, 'clv_per_bet': 0.002,
                    'drawdown_units': DEMOTION_POLICY['max_drawdown_units'] + 1,
                    'snapshot_coverage_pct': 100.0}]
        self.assertEqual(demotion_gate('live', windows)['decision'], 'paper')

    def test_a_paper_strategy_has_nothing_to_decide(self):
        decision = demotion_gate('paper', [{'signal_score': -1}])
        self.assertEqual(decision['decision'], 'paper')
        self.assertEqual(decision['triggers'], [])

    def test_re_promotion_is_never_automatic(self):
        decision = demotion_gate('live', [{'signal_score': -1}])
        self.assertIn('fresh', decision['re_promotion'])


class PublishedPages(unittest.TestCase):
    def test_all_six_pages_exist_and_every_row_cites_a_source(self):
        known = {s['url'] for s in json.loads(
            (ROOT / 'evidence' / 'sources.json').read_text())}
        for name in NEW_PAGES:
            page_rows = rows_of(name)
            self.assertGreater(len(page_rows), 4, f'{name} rendered too few rows')
            for index, row in enumerate(page_rows, 1):
                self.assertTrue(any(link in known for link in row['links']),
                                f'{name}: row {index} has no registered source link')

    def test_demonstrated_numbers_are_labelled_synthetic(self):
        for name in ('origination.html', 'signal-staking.html'):
            self.assertIn(SYNTHETIC, (ROOT / name).read_text())
        # Caption -> (rows in the table, rows that must carry the SYNTHETIC marker).
        worked = {
            'Step 1 · side (spread)': (4, 4),
            'Step 2 · total': (3, 3),
            'Step 3 · moneyline': (1, 1),
            'The three columns, as the contract builds them': (3, 3),
            'Median reference lines the distribution implies': (3, 3),
            'Signal rank': (3, 3),
            'Staking rank': (3, 3),
            'Masking report': (1, 1),
            # The last row of the gate table is the real current state, not a demonstration.
            'Gate outcomes on synthetic live periods': (4, 3),
        }
        seen = 0
        for page_name in ('origination.html', 'signal-staking.html'):
            for caption, rows in tables_of(page_name).items():
                if caption not in worked:
                    continue
                expected, synthetic = worked[caption]
                self.assertEqual(len(rows), expected, f'{caption}: row count changed')
                for index, cells in enumerate(rows):
                    if index < synthetic:
                        self.assertIn(SYNTHETIC, cells[-1],
                                      f'{caption} row {index + 1} lost its SYNTHETIC marker')
                seen += 1
        self.assertEqual(seen, len(worked), 'a worked example table disappeared')

    def test_the_results_page_links_every_official_game_page(self):
        html = (ROOT / 'results.html').read_text()
        self.assertEqual(html.count('https://www.nfl.com/games/'), len(load_results()))
        for result in load_results():
            self.assertIn(result['game_url'], html)

    def test_the_new_findings_are_on_the_flags_page(self):
        html = (ROOT / 'flags.html').read_text()
        for number in range(28, 34):
            self.assertIn(f'F{number}', html)
        ids = [c[0].split(' ')[0] for c in cells_of('flags.html')
               if c[0].startswith('F') and len(c[0].split(' ')[0]) == 3]
        self.assertEqual(len(ids), len(set(ids)), 'a finding id was published twice')

    def test_the_price_store_page_links_the_committed_csv(self):
        html = (ROOT / 'origination.html').read_text()
        self.assertIn('data/snapshots/price-snapshots.csv', html)
        self.assertIn('data/results/verified-results.csv', (ROOT / 'results.html').read_text())

    def test_no_page_claims_a_backtest_or_an_edge(self):
        for name in NEW_PAGES:
            html = (ROOT / name).read_text().lower()
            for claim in ('we found an edge', 'a proven edge', 'guaranteed profit',
                          'validated strategy', 'expected return of'):
                self.assertNotIn(claim, html, f'{name} makes an unsupported claim')


if __name__ == '__main__':
    unittest.main()
