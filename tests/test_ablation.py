"""Synthetic-only tests for the availability ablation contract and scoring utility."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
from pathlib import Path
import unittest

from engine.ablation import (
    categorical_brier,
    evaluate_availability_ablation,
)


RESULT_URL = 'https://static.www.nfl.com/image/upload/v1794570519/gamecenter/ab5828d9-4feb-11f1-abca-2c54536568a9.pdf'
AVAILABILITY_URL = 'https://www.nfl.com/injuries/'


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def policy():
    return {
        'strategy_id': 'SYNTHETIC-AVAILABILITY-ABLATION',
        'registration_commit': 'a' * 40,
        'registered_at_utc': '2026-11-17T00:00:00Z',
        'target_id': 'synthetic-game-result',
        'shared_model_spec_sha256': digest('same-model-family'),
        'without_availability_spec_sha256': digest('without-availability'),
        'with_availability_spec_sha256': digest('with-availability'),
        'family_size': 10,
        'familywise_alpha': 0.05,
        'minimum_test_weeks': 4,
        'bootstrap_resamples': 400,
        'bootstrap_seed': 19,
    }


def synthetic_rows(n_weeks=4):
    """Deterministic fake forecasts; never an NFL result or evidence sample."""
    outcomes = ('win', 'loss', 'push', 'win')
    without = (
        {'win': .6, 'push': .2, 'loss': .2},
        {'win': .3, 'push': .2, 'loss': .5},
        {'win': .3, 'push': .4, 'loss': .3},
        {'win': .6, 'push': .2, 'loss': .2},
    )
    with_availability = (
        {'win': .8, 'push': .1, 'loss': .1},
        {'win': .1, 'push': .1, 'loss': .8},
        {'win': .1, 'push': .8, 'loss': .1},
        {'win': .8, 'push': .1, 'loss': .1},
    )
    policy_record = policy()
    first_kickoff = datetime(2027, 9, 10, 17, 0, tzinfo=timezone.utc)
    rows = []
    for index in range(n_weeks):
        week = index + 1
        kickoff = first_kickoff + timedelta(days=7 * index)
        if week == 1:
            train_week = '2026-W18'
            training_cutoff = datetime(2026, 12, 20, 0, 0, tzinfo=timezone.utc)
        else:
            train_week = f'2027-W{week - 1:02d}'
            training_cutoff = kickoff - timedelta(days=8)
        availability_at = kickoff - timedelta(hours=24)
        forecast_at = kickoff - timedelta(hours=23)
        rows.append({
            'fixture_id': f'synthetic-fixture-{week:02d}',
            'target_id': policy_record['target_id'],
            'heldout_week': f'2027-W{week:02d}',
            'train_through_week': train_week,
            'training_cutoff_utc': training_cutoff.isoformat().replace('+00:00', 'Z'),
            'availability_snapshot_utc': availability_at.isoformat().replace('+00:00', 'Z'),
            'forecast_recorded_utc': forecast_at.isoformat().replace('+00:00', 'Z'),
            'kickoff_utc': kickoff.isoformat().replace('+00:00', 'Z'),
            'result_observed_utc': (kickoff + timedelta(hours=5)).isoformat().replace('+00:00', 'Z'),
            'registration_commit': policy_record['registration_commit'],
            'shared_model_spec_sha256': policy_record['shared_model_spec_sha256'],
            'without_availability_spec_sha256': policy_record['without_availability_spec_sha256'],
            'with_availability_spec_sha256': policy_record['with_availability_spec_sha256'],
            'training_data_sha256': digest(f'synthetic-training-{week}'),
            'input_snapshot_sha256': digest(f'synthetic-inputs-{week}'),
            'input_artifact_ref': f'test-fixture://synthetic-inputs/{week}',
            'availability_snapshot_sha256': digest(f'synthetic-availability-{week}'),
            'outcome_snapshot_sha256': digest(f'synthetic-outcomes-{week}'),
            'forecast_record_sha256': digest(f'synthetic-forecast-{week}'),
            'availability_source_id': 'nfl-injury-w10',
            'availability_source_url': AVAILABILITY_URL,
            'result_source_id': 'nfl-gamebook-w10',
            'result_source_url': RESULT_URL,
            'probabilities_without_availability': without[index % len(without)],
            'probabilities_with_availability': with_availability[index % len(with_availability)],
            'outcome': outcomes[index % len(outcomes)],
        })
    return rows


class CategoricalBrierTests(unittest.TestCase):
    def test_push_is_a_separate_state(self):
        score = categorical_brier(
            {'win': .1, 'push': .8, 'loss': .1}, 'push')
        self.assertAlmostEqual(score, .06)

    def test_probability_mass_must_be_complete(self):
        with self.assertRaisesRegex(ValueError, 'sum to one'):
            categorical_brier({'win': .5, 'push': .2, 'loss': .2}, 'win')

    def test_unknown_or_missing_state_fails(self):
        with self.assertRaisesRegex(ValueError, 'exactly win, push, and loss'):
            categorical_brier({'win': .7, 'loss': .3}, 'win')
        with self.assertRaisesRegex(ValueError, 'outcome must be win'):
            categorical_brier({'win': 1, 'push': 0, 'loss': 0}, 'void')


class PairedAvailabilityAblationTests(unittest.TestCase):
    def test_synthetic_comparison_is_paired_and_never_leaderboard_eligible(self):
        result = evaluate_availability_ablation(synthetic_rows(), policy())
        self.assertEqual(result['status'], 'descriptive_ablation_only')
        self.assertEqual((result['n_games'], result['n_test_weeks']), (4, 4))
        self.assertLess(result['brier_with_availability'], result['brier_without_availability'])
        self.assertGreater(result['improvement'], 0)
        self.assertLess(result['interval']['lower'], result['interval']['upper'])
        self.assertEqual(result['direction'], 'with_availability_lower_brier')
        self.assertEqual(result['interval']['family_size'], 10)
        self.assertAlmostEqual(result['interval']['familywise_confidence'], .995)
        self.assertEqual(len(result['policy_sha256']), 64)
        self.assertEqual(len(result['forecast_corpus_sha256']), 64)
        self.assertEqual(result['registration_commit'], policy()['registration_commit'])
        self.assertFalse(result['eligible_for_leaderboard'])
        self.assertTrue(result['blockers'])

    def test_empty_corpus_returns_no_estimate(self):
        result = evaluate_availability_ablation([], policy())
        self.assertEqual(result['status'], 'blocked_no_forecasts')
        self.assertIsNone(result['improvement'])
        self.assertIsNone(result['interval'])
        self.assertFalse(result['eligible_for_leaderboard'])

    def test_too_few_holdout_weeks_returns_no_scores(self):
        result = evaluate_availability_ablation(synthetic_rows(3), policy())
        self.assertEqual(result['status'], 'blocked_insufficient_holdout_weeks')
        self.assertEqual(result['n_test_weeks'], 3)
        self.assertIsNone(result['brier_without_availability'])
        self.assertIsNone(result['improvement'])

    def test_week_bootstrap_is_deterministic(self):
        rows = synthetic_rows()
        first = evaluate_availability_ablation(rows, policy())
        second = evaluate_availability_ablation(rows, policy())
        self.assertEqual(first['interval'], second['interval'])

    def test_corpus_digest_is_stable_under_row_order_but_tracks_inputs(self):
        rows = synthetic_rows()
        original = evaluate_availability_ablation(rows, policy())['forecast_corpus_sha256']
        reversed_order = evaluate_availability_ablation(list(reversed(rows)), policy())['forecast_corpus_sha256']
        self.assertEqual(original, reversed_order)
        changed = synthetic_rows()
        changed[0]['input_artifact_ref'] = 'test-fixture://different-input'
        changed_digest = evaluate_availability_ablation(changed, policy())['forecast_corpus_sha256']
        self.assertNotEqual(original, changed_digest)

    def test_input_artifact_reference_is_required(self):
        rows = synthetic_rows()
        del rows[0]['input_artifact_ref']
        with self.assertRaisesRegex(ValueError, 'input_artifact_ref'):
            evaluate_availability_ablation(rows, policy())

    def test_registration_is_required_and_frozen(self):
        with self.assertRaisesRegex(ValueError, 'policy is missing'):
            evaluate_availability_ablation(synthetic_rows(), {'strategy_id': 'x'})
        bad = policy()
        bad['registration_commit'] = 'not-a-commit'
        with self.assertRaisesRegex(ValueError, 'full 40- or 64-character'):
            evaluate_availability_ablation(synthetic_rows(), bad)

    def test_policy_must_precede_every_forecast(self):
        frozen = policy()
        frozen['registered_at_utc'] = '2027-09-09T18:00:00Z'
        with self.assertRaisesRegex(ValueError, 'registered policy must predate'):
            evaluate_availability_ablation(synthetic_rows(), frozen)

    def test_training_week_must_precede_heldout_week(self):
        rows = synthetic_rows()
        rows[1]['train_through_week'] = '2027-W02'
        with self.assertRaisesRegex(ValueError, 'training window must end before'):
            evaluate_availability_ablation(rows, policy())

    def test_expanding_training_window_cannot_move_backwards(self):
        rows = synthetic_rows()
        rows[2]['train_through_week'] = '2026-W18'
        rows[2]['training_cutoff_utc'] = '2026-12-20T00:00:00Z'
        with self.assertRaisesRegex(ValueError, 'training windows cannot move backward'):
            evaluate_availability_ablation(rows, policy())

    def test_snapshot_and_forecast_must_be_pre_kickoff(self):
        rows = synthetic_rows()
        rows[0]['availability_snapshot_utc'] = '2027-09-10T18:00:00Z'
        with self.assertRaisesRegex(ValueError, 'availability snapshot was not available'):
            evaluate_availability_ablation(rows, policy())
        rows = synthetic_rows()
        rows[0]['forecast_recorded_utc'] = '2027-09-10T18:00:00Z'
        with self.assertRaisesRegex(ValueError, 'forecast_recorded_utc must precede'):
            evaluate_availability_ablation(rows, policy())

    def test_result_must_be_observed_after_kickoff(self):
        rows = synthetic_rows()
        rows[0]['result_observed_utc'] = '2027-09-10T16:00:00Z'
        with self.assertRaisesRegex(ValueError, 'cannot precede kickoff'):
            evaluate_availability_ablation(rows, policy())

    def test_timestamps_require_explicit_utc(self):
        rows = synthetic_rows()
        rows[0]['forecast_recorded_utc'] = '2027-09-09T18:00:00'
        with self.assertRaisesRegex(ValueError, 'must include a UTC timezone'):
            evaluate_availability_ablation(rows, policy())

    def test_nonregistered_or_nonofficial_source_is_refused(self):
        rows = synthetic_rows()
        rows[0]['availability_source_id'] = 'unregistered-source'
        rows[0]['availability_source_url'] = 'https://example.com/injuries'
        with self.assertRaisesRegex(ValueError, 'source ID is not in the verified first-party source register'):
            evaluate_availability_ablation(rows, policy())

        rows = synthetic_rows()
        rows[0]['result_source_url'] = AVAILABILITY_URL
        with self.assertRaisesRegex(ValueError, 'does not match its registered source ID'):
            evaluate_availability_ablation(rows, policy())

    def test_invalid_digest_or_variant_spec_is_refused(self):
        rows = synthetic_rows()
        rows[0]['availability_snapshot_sha256'] = 'bad'
        with self.assertRaisesRegex(ValueError, 'lowercase SHA-256'):
            evaluate_availability_ablation(rows, policy())
        rows = synthetic_rows()
        rows[0]['with_availability_spec_sha256'] = digest('different-after-registration')
        with self.assertRaisesRegex(ValueError, 'differs from the registered'):
            evaluate_availability_ablation(rows, policy())

    def test_duplicates_and_weekly_fit_drift_are_refused(self):
        rows = synthetic_rows()
        rows[1]['fixture_id'] = rows[0]['fixture_id']
        rows[1]['heldout_week'] = rows[0]['heldout_week']
        rows[1]['train_through_week'] = rows[0]['train_through_week']
        rows[1]['training_cutoff_utc'] = rows[0]['training_cutoff_utc']
        with self.assertRaisesRegex(ValueError, 'duplicate fixture/target'):
            evaluate_availability_ablation(rows, policy())
        rows = synthetic_rows()
        second_in_week = deepcopy(rows[0])
        second_in_week['fixture_id'] = 'second-synthetic-fixture-in-week'
        second_in_week['training_cutoff_utc'] = '2027-09-01T00:00:00Z'
        rows.append(second_in_week)
        with self.assertRaisesRegex(ValueError, 'share one frozen training cutoff'):
            evaluate_availability_ablation(rows, policy())

    def test_row_must_reference_the_registered_commit_and_target(self):
        rows = synthetic_rows()
        rows[0]['registration_commit'] = 'b' * 40
        with self.assertRaisesRegex(ValueError, 'does not reference the preregistered commit'):
            evaluate_availability_ablation(rows, policy())
        rows = synthetic_rows()
        rows[0]['target_id'] = 'another-target'
        with self.assertRaisesRegex(ValueError, 'preregistered target_id'):
            evaluate_availability_ablation(rows, policy())


class AblationPageTests(unittest.TestCase):
    def test_page_has_official_sources_and_no_broken_local_links(self):
        root = Path(__file__).resolve().parents[1]
        verifier_path = root / 'ablation-lab' / 'verify.py'
        spec = importlib.util.spec_from_file_location('ablation_page_verify', verifier_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        rows, links = module.verify()
        self.assertEqual(rows, 8)
        self.assertGreaterEqual(links, 20)

    def test_dashboard_labels_results_as_missing_not_zero(self):
        root = Path(__file__).resolve().parents[1]
        page = (root / 'ablation-lab' / 'index.html').read_text()
        self.assertIn('No NFL ablation result is available.', page)
        self.assertIn('Not computed; not zero.', page)
        self.assertIn('Not eligible', page)
        self.assertFalse(evaluate_availability_ablation([], policy())['eligible_for_leaderboard'])

    def test_protocol_status_table_rows_link_official_sources(self):
        root = Path(__file__).resolve().parents[1]
        lines = (root / 'docs' / 'ABLATION_PROTOCOL.md').read_text().splitlines()
        start = lines.index('| Item | State | What clears it | Official source scope |')
        rows = [line for line in lines[start + 2:] if line.startswith('|')]
        self.assertEqual(len(rows), 5)
        for line in rows:
            self.assertRegex(line, r'https://(?:www|static\.www)\.nfl\.com/')


if __name__ == '__main__':
    unittest.main()
