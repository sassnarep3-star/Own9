"""Paired, point-in-time availability ablations for pre-registered forecasts.

This module scores supplied paired forecasts; it does not fit models, fetch NFL pages,
verify source contents, or certify eligibility. See ``docs/ABLATION_PROTOCOL.md``.
"""
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import re
from pathlib import Path
from statistics import mean
from urllib.parse import urlsplit

from engine.core import probability, week_bootstrap_ci

ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST = ROOT / 'evidence' / 'sources.json'
CATEGORIES = ('win', 'push', 'loss')
_HEX_256 = re.compile(r'^[0-9a-f]{64}$')
_COMMIT = re.compile(r'^(?:[0-9a-f]{40}|[0-9a-f]{64})$')
_WEEK = re.compile(r'^(\d{4})-W(\d{2})$')
_OFFICIAL_PUBLISHERS = {
    'nfl', 'nfl communications', 'nfl football operations',
}


_REQUIRED_POLICY = (
    'strategy_id', 'registration_commit', 'registered_at_utc', 'target_id',
    'shared_model_spec_sha256', 'without_availability_spec_sha256',
    'with_availability_spec_sha256', 'family_size', 'familywise_alpha',
    'minimum_test_weeks', 'bootstrap_resamples', 'bootstrap_seed',
)
_REQUIRED_ROW = (
    'fixture_id', 'target_id', 'heldout_week', 'train_through_week',
    'training_cutoff_utc', 'availability_snapshot_utc', 'forecast_recorded_utc',
    'kickoff_utc', 'result_observed_utc', 'registration_commit',
    'shared_model_spec_sha256', 'without_availability_spec_sha256',
    'with_availability_spec_sha256', 'training_data_sha256',
    'input_snapshot_sha256', 'availability_snapshot_sha256',
    'outcome_snapshot_sha256', 'input_artifact_ref', 'forecast_record_sha256',
    'availability_source_id', 'availability_source_url', 'result_source_id', 'result_source_url',
    'probabilities_without_availability', 'probabilities_with_availability',
    'outcome',
)
_HASH_FIELDS = (
    'shared_model_spec_sha256', 'without_availability_spec_sha256',
    'with_availability_spec_sha256', 'training_data_sha256',
    'input_snapshot_sha256', 'availability_snapshot_sha256',
    'outcome_snapshot_sha256', 'forecast_record_sha256',
)


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{field} must be a nonempty string')
    return value.strip()


def _sha256(value, field):
    value = _text(value, field)
    if not _HEX_256.fullmatch(value):
        raise ValueError(f'{field} must be a lowercase SHA-256 digest')
    return value


def _canonical_digest(value, field):
    try:
        payload = json.dumps(value, sort_keys=True, separators=(',', ':'),
                             ensure_ascii=False, allow_nan=False).encode('utf-8')
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{field} must be finite JSON data') from exc
    return sha256(payload).hexdigest()


def _utc(value, field):
    value = _text(value, field)
    try:
        parsed = datetime.fromisoformat(value[:-1] + '+00:00' if value.endswith('Z') else value)
    except ValueError as exc:
        raise ValueError(f'{field} must be an ISO-8601 UTC timestamp') from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError(f'{field} must include a UTC timezone')
    return parsed.astimezone(timezone.utc)


def _week(value, field):
    value = _text(value, field)
    match = _WEEK.fullmatch(value)
    if not match:
        raise ValueError(f'{field} must use YYYY-Wnn form')
    year, week = (int(part) for part in match.groups())
    if year < 1900 or not 1 <= week <= 22:
        raise ValueError(f'{field} must be a valid NFL season-week key (01-22)')
    return year, week


def _official_sources():
    """Return first-party sources explicitly registered in the root evidence manifest.

    Registration is a provenance gate, not proof that a URL entails a row or that a supplied
    hash is correct. A reviewer must verify those independently.
    """
    try:
        sources = json.loads(SOURCE_MANIFEST.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError('official source manifest is unavailable or invalid') from exc
    if not isinstance(sources, list):
        raise ValueError('official source manifest must be a list')
    registered = {}
    for source in sources:
        if (not isinstance(source, dict)
                or source.get('status') not in ('retrieved', 'inspected')
                or not all(source.get(field) for field in ('checked', 'supports', 'scope'))):
            continue
        publisher = str(source.get('publisher', '')).strip().lower()
        is_first_party = (
            publisher in _OFFICIAL_PUBLISHERS
            or 'official club site' in publisher
            or publisher.endswith('(club site)')
        )
        source_id, url = source.get('id'), source.get('url')
        parsed = urlsplit(url) if isinstance(url, str) else None
        if (is_first_party and isinstance(source_id, str) and source_id
                and parsed and parsed.scheme == 'https' and parsed.hostname
                and not parsed.username and not parsed.password):
            registered[source_id] = source
    return registered


def _official_source_url(source_id, value, field, registered_sources):
    source_id = _text(source_id, field.replace('_url', '_id'))
    source = registered_sources.get(source_id)
    if source is None:
        raise ValueError(f'{field} source ID is not in the verified first-party source register')
    value = _text(value, field)
    if value != source['url']:
        raise ValueError(f'{field} does not match its registered source ID')
    return value


def _probability_vector(value, field):
    if not isinstance(value, Mapping) or set(value) != set(CATEGORIES):
        raise ValueError(f'{field} must contain exactly win, push, and loss probabilities')
    result = {name: probability(value[name]) for name in CATEGORIES}
    if abs(sum(result.values()) - 1.0) > 1e-9:
        raise ValueError(f'{field} probabilities must sum to one')
    return result


def categorical_brier(probabilities, outcome):
    """Three-state Brier score (sum of squared one-hot errors; lower is better).

    ``probabilities`` must explicitly include win, push, and loss. A push is not silently
    discarded or treated as a win/loss. No NFL observation is bundled with this function.
    """
    vector = _probability_vector(probabilities, 'probabilities')
    outcome = _text(outcome, 'outcome')
    if outcome not in CATEGORIES:
        raise ValueError('outcome must be win, push, or loss')
    return sum((vector[name] - (1.0 if name == outcome else 0.0)) ** 2
               for name in CATEGORIES)


def _validate_policy(policy):
    if not isinstance(policy, Mapping):
        raise ValueError('a frozen, pre-registered policy is required')
    missing = [field for field in _REQUIRED_POLICY if field not in policy]
    if missing:
        raise ValueError('policy is missing: ' + ', '.join(missing))
    strategy_id = _text(policy['strategy_id'], 'strategy_id')
    commit = _text(policy['registration_commit'], 'registration_commit')
    if not _COMMIT.fullmatch(commit):
        raise ValueError('registration_commit must be a full 40- or 64-character commit hash')
    registered_at = _utc(policy['registered_at_utc'], 'registered_at_utc')
    target_id = _text(policy['target_id'], 'target_id')
    shared_spec = _sha256(policy['shared_model_spec_sha256'], 'shared_model_spec_sha256')
    without_spec = _sha256(
        policy['without_availability_spec_sha256'], 'without_availability_spec_sha256')
    with_spec = _sha256(
        policy['with_availability_spec_sha256'], 'with_availability_spec_sha256')
    if without_spec == with_spec:
        raise ValueError('the two feature-set specifications must differ')
    family_size = policy['family_size']
    if type(family_size) is not int or family_size < 1:
        raise ValueError('family_size must be a positive integer fixed at registration')
    alpha = probability(policy['familywise_alpha'])
    if not 0 < alpha < 1:
        raise ValueError('familywise_alpha must be in (0, 1)')
    minimum_weeks = policy['minimum_test_weeks']
    if type(minimum_weeks) is not int or minimum_weeks < 2:
        raise ValueError('minimum_test_weeks must be at least two chronological blocks')
    resamples = policy['bootstrap_resamples']
    if type(resamples) is not int or resamples < 100:
        raise ValueError('bootstrap_resamples must be an integer of at least 100')
    seed = policy['bootstrap_seed']
    if type(seed) is not int or seed < 0:
        raise ValueError('bootstrap_seed must be a nonnegative integer')
    return {
        'strategy_id': strategy_id,
        'registration_commit': commit,
        'registered_at': registered_at,
        'target_id': target_id,
        'shared_model_spec_sha256': shared_spec,
        'without_availability_spec_sha256': without_spec,
        'with_availability_spec_sha256': with_spec,
        'family_size': family_size,
        'familywise_alpha': alpha,
        'minimum_test_weeks': minimum_weeks,
        'bootstrap_resamples': resamples,
        'bootstrap_seed': seed,
        'simultaneous_confidence': 1.0 - alpha / family_size,
    }


def _validate_row(row, policy, registered_sources):
    if not isinstance(row, Mapping):
        raise ValueError('each forecast pair must be an object')
    missing = [field for field in _REQUIRED_ROW if field not in row]
    if missing:
        raise ValueError('forecast pair is missing: ' + ', '.join(missing))
    fixture_id = _text(row['fixture_id'], 'fixture_id')
    target_id = _text(row['target_id'], 'target_id')
    if target_id != policy['target_id']:
        raise ValueError('all rows must use the preregistered target_id')
    heldout = _week(row['heldout_week'], 'heldout_week')
    train_through = _week(row['train_through_week'], 'train_through_week')
    if train_through >= heldout:
        raise ValueError('training window must end before its chronological holdout week')

    registered_commit = _text(row['registration_commit'], 'registration_commit')
    if registered_commit != policy['registration_commit']:
        raise ValueError('forecast pair does not reference the preregistered commit')
    for field in _HASH_FIELDS:
        _sha256(row[field], field)
    for field in ('shared_model_spec_sha256', 'without_availability_spec_sha256',
                  'with_availability_spec_sha256'):
        if row[field] != policy[field]:
            raise ValueError(f'{field} differs from the registered analysis specification')
    _text(row['input_artifact_ref'], 'input_artifact_ref')

    training_cutoff = _utc(row['training_cutoff_utc'], 'training_cutoff_utc')
    availability_at = _utc(row['availability_snapshot_utc'], 'availability_snapshot_utc')
    forecast_at = _utc(row['forecast_recorded_utc'], 'forecast_recorded_utc')
    kickoff = _utc(row['kickoff_utc'], 'kickoff_utc')
    result_at = _utc(row['result_observed_utc'], 'result_observed_utc')
    if training_cutoff >= forecast_at:
        raise ValueError('training_cutoff_utc must precede forecast_recorded_utc')
    if availability_at > forecast_at:
        raise ValueError('availability snapshot was not available when the forecast was recorded')
    if policy['registered_at'] >= forecast_at:
        raise ValueError('the registered policy must predate every forecast')
    if forecast_at >= kickoff:
        raise ValueError('forecast_recorded_utc must precede kickoff_utc')
    if availability_at >= kickoff:
        raise ValueError('availability snapshot must precede kickoff_utc')
    if result_at < kickoff:
        raise ValueError('result_observed_utc cannot precede kickoff_utc')

    _official_source_url(row['availability_source_id'], row['availability_source_url'],
                          'availability_source_url', registered_sources)
    _official_source_url(row['result_source_id'], row['result_source_url'],
                         'result_source_url', registered_sources)
    outcome = _text(row['outcome'], 'outcome')
    if outcome not in CATEGORIES:
        raise ValueError('outcome must be win, push, or loss')
    without = _probability_vector(
        row['probabilities_without_availability'], 'probabilities_without_availability')
    with_availability = _probability_vector(
        row['probabilities_with_availability'], 'probabilities_with_availability')
    return {
        'fixture_id': fixture_id,
        'target_id': target_id,
        'heldout_week': heldout,
        'heldout_week_label': row['heldout_week'],
        'train_through_week': train_through,
        'training_cutoff_utc': training_cutoff,
        'outcome': outcome,
        'without': without,
        'with': with_availability,
    }


def evaluate_availability_ablation(rows, policy):
    """Compare paired, chronological forecasts with vs without verified availability.

    Rows are accepted only when both forecasts use the same registered model family,
    training-data hash, target, and holdout window; only the preregistered feature-set
    specification differs. Positive ``improvement`` means the availability-feature model
    has lower Brier loss. Uncertainty resamples whole held-out weeks and uses a Bonferroni
    simultaneous confidence level based on the preregistered family size.

    This is a descriptive ablation calculation, not a source audit, causal estimate, skill
    certification, ROI calculation, or leaderboard qualification.
    """
    frozen = _validate_policy(policy)
    if not isinstance(rows, (list, tuple)):
        raise ValueError('rows must be a list or tuple of paired forecasts')
    if not rows:
        return {
            'status': 'blocked_no_forecasts', 'n_games': 0, 'n_test_weeks': 0,
            'brier_without_availability': None, 'brier_with_availability': None,
            'improvement': None, 'interval': None, 'eligible_for_leaderboard': False,
            'blockers': ['No registered, source-hashed paired forecast rows were supplied.'],
        }

    registered_sources = _official_sources()
    validated = [_validate_row(row, frozen, registered_sources) for row in rows]
    policy_digest = _canonical_digest(
        {field: policy[field] for field in _REQUIRED_POLICY}, 'registered policy')
    canonical_rows = sorted(
        (dict(row) for row in rows),
        key=lambda row: (str(row['heldout_week']), str(row['fixture_id']), str(row['target_id'])))
    forecast_corpus_digest = _canonical_digest(canonical_rows, 'forecast corpus')
    identifiers = [(row['fixture_id'], row['target_id']) for row in validated]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError('duplicate fixture/target pair')
    frozen_fits = {}
    for row in validated:
        key = row['heldout_week']
        fit = (row['train_through_week'], row['training_cutoff_utc'])
        if key in frozen_fits and frozen_fits[key] != fit:
            raise ValueError('all fixtures in a held-out week must share one frozen training cutoff')
        frozen_fits[key] = fit
    heldout_weeks = sorted({row['heldout_week'] for row in validated})
    training_ends = [frozen_fits[week][0] for week in heldout_weeks]
    if any(later < earlier for earlier, later in zip(training_ends, training_ends[1:])):
        raise ValueError('chronological holdout training windows cannot move backward')
    if len(heldout_weeks) < frozen['minimum_test_weeks']:
        return {
            'status': 'blocked_insufficient_holdout_weeks',
            'registration_commit': frozen['registration_commit'],
            'policy_sha256': policy_digest,
            'forecast_corpus_sha256': forecast_corpus_digest,
            'n_games': len(validated), 'n_test_weeks': len(heldout_weeks),
            'brier_without_availability': None, 'brier_with_availability': None,
            'improvement': None, 'interval': None, 'eligible_for_leaderboard': False,
            'blockers': [
                f"Need at least {frozen['minimum_test_weeks']} pre-registered held-out weeks; "
                f"received {len(heldout_weeks)}."
            ],
        }

    baseline_scores = [categorical_brier(row['without'], row['outcome']) for row in validated]
    augmented_scores = [categorical_brier(row['with'], row['outcome']) for row in validated]
    paired_improvements = [baseline - augmented
                           for baseline, augmented in zip(baseline_scores, augmented_scores)]
    weeks = [row['heldout_week_label'] for row in validated]
    lower, upper = week_bootstrap_ci(
        paired_improvements,
        weeks,
        resamples=frozen['bootstrap_resamples'],
        confidence=frozen['simultaneous_confidence'],
        seed=frozen['bootstrap_seed'],
    )
    if lower > 0:
        direction = 'with_availability_lower_brier'
    elif upper < 0:
        direction = 'without_availability_lower_brier'
    else:
        direction = 'uncertain'
    return {
        'status': 'descriptive_ablation_only',
        'strategy_id': frozen['strategy_id'],
        'registration_commit': frozen['registration_commit'],
        'policy_sha256': policy_digest,
        'forecast_corpus_sha256': forecast_corpus_digest,
        'shared_model_spec_sha256': frozen['shared_model_spec_sha256'],
        'without_availability_spec_sha256': frozen['without_availability_spec_sha256'],
        'with_availability_spec_sha256': frozen['with_availability_spec_sha256'],
        'target_id': frozen['target_id'],
        'n_games': len(validated),
        'n_test_weeks': len(heldout_weeks),
        'score': 'three-state categorical Brier score; sum of squared one-hot errors',
        'brier_without_availability': mean(baseline_scores),
        'brier_with_availability': mean(augmented_scores),
        'improvement': mean(paired_improvements),
        'improvement_definition': 'Brier without availability minus Brier with availability; positive favours the latter',
        'interval': {
            'lower': lower,
            'upper': upper,
            'familywise_confidence': frozen['simultaneous_confidence'],
            'method': 'percentile bootstrap resampling whole held-out weeks',
            'resamples': frozen['bootstrap_resamples'],
            'seed': frozen['bootstrap_seed'],
            'family_size': frozen['family_size'],
        },
        'direction': direction,
        'eligible_for_leaderboard': False,
        'blockers': [
            'The registration commit is format-checked but its Git ancestry/time is not checked by this utility.',
            'Source URLs and digest formats are checked, but this utility does not inspect captured bytes or independently verify official-source entailment.',
            'Prospective paper replication, benchmark-relative skill, and the remaining leaderboard gates are not evaluated here.',
            'Week-cluster bootstrap uncertainty assumes exchangeable held-out weeks; serial drift and other dependence require a preregistered sensitivity analysis.',
        ],
    }
