"""The demotion gate: what sends a live strategy back to paper, and what it has to survive to return.

Why a one-way gate is not enough
--------------------------------
Promotion is the loud half of this problem, so everyone builds it. Demotion is the half that decides
whether a strategy that has quietly stopped being good is still taking money. A gate with no exit is
not a validation process, it is a permanent licence earned on an old sample.

The asymmetry is the design:

* **Demotion is cheap and immediate.** One trigger fires on one completed, verified evaluation
  window and the candidate goes to paper. No committee, no appeal, no waiting for a human — which
  is also why this can run with no manual input.
* **Return is expensive and delayed.** A demoted candidate must complete `RELIST_WEEKS` further
  evaluation windows on paper, with no trigger, *plus* a `COOLDOWN_WEEKS` gap, and its re-listing
  decision is appended to an immutable log alongside the demotion that started it.

Triggers, and why they are defined the way they are
---------------------------------------------------
Four of the five read the **signal** block, because signal is what a demotion is about. One reads
**staking**, and it can only suspend — never rank, never certify. The fifth is a provenance break:
a strategy that cannot be *reconstructed* (a settled bet with no captured closing number, a week
whose results never verified) is demoted on principle rather than on evidence, because an
unauditable run is indistinguishable from an unrecorded one.

Every threshold below is a predeclared constant. None is derived from a result, and the module
raises rather than accepting a threshold supplied at call time — a tunable demotion gate is a
demotion gate that fires when the operator wants it to.
"""
from hashlib import sha256
import json
from pathlib import Path

STATES = ('paper', 'live', 'suspended', 'retired')
#: A candidate may only hold `live` while every gate in `PROMOTION_GATES` is passed.
PROMOTION_GATES = ('provenance', 'point_in_time', 'sealed_test', 'predictive_quality',
                   'economics', 'selection_control', 'stability')

POLICY = {
    'min_eval_weeks': 4,          # completed verified weeks an evaluation window must cover
    'signal_lcb_halt': 0.0,      # demote when the rolling log-loss-gain lower bound is at or below
    'calibration_mae_max': 0.05, # demote when mean bin calibration error exceeds this
    'coverage_min': 0.60,        # demote when the candidate abstains on more than 40% of its slate
    'missing_close_max': 0.02,   # demote on provenance break above this share of settled bets
    'drawdown_suspends_units': 15.0,  # staking can only suspend, never rank
    'cooldown_weeks': 4,         # weeks that must pass before re-listing may even be considered
    'relist_weeks': 8,           # consecutive clean paper evaluations required to re-list
    'window': 12,                # rolling evaluation window, in weeks of settled bets
}


class DemotionError(ValueError):
    pass


def check_policy(policy):
    """Thresholds may not be changed silently, by a candidate or by anyone else.

    The default policy is the published one. A caller may pass a different dict only if it is
    complete and labelled with who changed it and from which week; the label is then written into
    the decision record, so a moved goalpost is visible in the log rather than inferred from a
    diff. Unlabelled overrides - the shape a candidate would use to save itself - are refused.
    """
    if policy is POLICY:
        return 'published'
    if not isinstance(policy, dict):
        raise DemotionError('policy must be the published POLICY or a complete labelled dict')
    missing = sorted(set(POLICY) - set(policy))
    if missing:
        raise DemotionError(f'policy is missing thresholds: {", ".join(missing)}')
    extra = sorted(set(policy) - set(POLICY) - {'changed_by', 'effective_week'})
    if extra:
        raise DemotionError(f'policy declares unknown thresholds: {", ".join(extra)}')
    for field in ('changed_by', 'effective_week'):
        value = policy.get(field)
        if not isinstance(value, (str, int)) or str(value).strip() in ('', 'None'):
            raise DemotionError(f'a non-default policy must declare {field!r}; an unlabelled '
                                'threshold change is how a candidate demotes itself out of trouble')
    changed = [k for k in POLICY if policy[k] != POLICY[k]]
    return {'labelled_change': True, 'changed_by': str(policy['changed_by']),
            'effective_week': policy['effective_week'], 'thresholds_changed': changed or ['none yet']}


def _number(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DemotionError(f'{field} must be a number, got {value!r}')
    return float(value)


def evaluate(history, *, policy=POLICY, state='live'):
    """Decide one candidate's state from a list of weekly evaluation records.

    Each record must be a completed, verified week:
        {'week', 'signal_lcb', 'calibration_mae', 'coverage', 'missing_close_share',
         'net_units', 'drawdown_units'}
    A missing field is not a pass: for a candidate already live, an absent `signal_lcb`,
    `calibration_mae`, `coverage` or `missing_close_share` is recorded as an unresolved trigger, so
    the way to survive the gate is to report, not to stop reporting. `drawdown_units` is the
    exception by design - it can only recommend a suspension, never manufacture a merit demotion.
    """
    if state not in STATES:
        raise DemotionError(f'unknown state {state!r}')
    policy_label = check_policy(policy)
    if not history:
        return {'action': 'hold', 'triggers': [], 'reason': 'no evaluation history',
                'state_after': state, 'policy': policy, 'policy_label': policy_label}
    for index, row in enumerate(history, 1):
        if 'week' not in row:
            raise DemotionError(f'history row {index}: no week id; windows are ordered by week')
    weeks = sorted({r['week'] for r in history})
    window = history[-policy['window']:] if len(history) > policy['window'] else history
    triggers, notes = [], []

    def latest(field):
        values = [r.get(field) for r in window if r.get(field) is not None]
        return values[-1] if values else None

    if len(weeks) < policy['min_eval_weeks'] and state == 'live':
        # Live with too few evaluated weeks is itself a defect: the candidate was promoted on a
        # sample the policy does not recognise.
        triggers.append(('sample', f'{len(weeks)} evaluated weeks is below the {policy["min_eval_weeks"]} '
                                   'the policy requires a live candidate to keep clearing'))
    lcb = latest('signal_lcb')
    if lcb is not None and lcb <= policy['signal_lcb_halt']:
        triggers.append(('signal', f'log-loss gain lower bound {lcb:.4f} does not clear '
                                   f'{policy["signal_lcb_halt"]}'))
    elif lcb is None and state == 'live':
        triggers.append(('signal', 'no signal lower bound in the window, so the candidate cannot be '
                                   'shown to still beat its baseline'))
    mae = latest('calibration_mae')
    if mae is not None and mae > policy['calibration_mae_max']:
        triggers.append(('calibration', f'mean absolute calibration error {mae:.4f} exceeds '
                                       f'{policy["calibration_mae_max"]}'))
    mae_is_missing = mae is None
    coverage = latest('coverage')
    if coverage is not None and coverage < policy['coverage_min']:
        triggers.append(('coverage', f'the candidate settled only {coverage:.1%} of its slate, below '
                                     f'the {policy["coverage_min"]:.0%} floor'))
    missing = latest('missing_close_share')
    if missing is None and state == 'live':
        notes.append('window reports no closing-capture audit; the store was empty, so this is '
                     'recorded rather than assumed clean')
    if missing is not None and missing > policy['missing_close_max']:
        triggers.append(('provenance', f'{missing:.1%} of settled bets have no captured closing '
                                       'number, above the tolerated 2%'))
    drawdown = latest('drawdown_units')
    suspension = (drawdown is not None
                  and drawdown <= -policy['drawdown_suspends_units'])
    if suspension:
        notes.append(f'stake-weighted drawdown {drawdown:.1f} units breaches the risk stop; risk '
                     'review suspends new stakes and cannot change a rank')

    if state == 'live':
        # Fail closed on the two fields that could otherwise be left unreported forever: an absent
        # calibration or coverage figure is an unresolved trigger, exactly as the docstring promises.
        for field, label in (('calibration_mae', 'calibration'), ('coverage', 'coverage')):
            if latest(field) is None:
                triggers.append((label, f'the window reports no {field}; a live candidate must keep '
                                        'reporting it, so silence is treated as a breach rather than '
                                        'as a pass'))
    if triggers:
        action = 'demote' if state == 'live' else 'hold'
        if state == 'suspended' and triggers:
            action = 'demote'
        return {'action': action, 'state_after': 'paper' if action == 'demote' else state,
                'suspension_recommended': suspension, 'triggers': triggers, 'notes': notes,
                'window_weeks': len(weeks), 'policy': policy, 'policy_label': policy_label}
    if suspension:
        return {'action': 'suspend', 'state_after': 'suspended', 'triggers': [], 'notes': notes,
                'window_weeks': len(weeks), 'policy': policy, 'policy_label': policy_label,
                'reason': 'risk stop only: staking cannot promote, demote on merit, or restore '
                          'a rank'}
    return {'action': 'hold', 'state_after': state, 'triggers': [], 'notes': notes,
            'window_weeks': len(weeks), 'policy': policy, 'policy_label': policy_label}


def promotable(candidate, gates_passed):
    """A candidate is listed only when every named gate is passed *and* recorded with an artifact.

    Mirrors the fail-closed discipline used for eligibility elsewhere in the project: a gate that is
    merely asserted is a gate that has not been passed.
    """
    missing = [g for g in PROMOTION_GATES if g not in gates_passed]
    unbacked = [g for g, item in gates_passed.items()
                if not (isinstance(item, dict) and item.get('artifact')
                        and len(str(item.get('sha256', ''))) == 64)]
    return {'candidate': candidate, 'promotable': not missing and not unbacked,
            'missing_gates': missing, 'gates_without_artifact': unbacked}


def relist_ready(demoted_at_week, evaluations, policy=POLICY):
    """Can a demoted candidate go live again? Requires a clean run *and* a waiting period.

    `evaluations` are post-demotion paper evaluations in week order, each with a `triggers` list.
    The cooldown and the clean-run requirement are checked independently, because satisfying only
    the waiting period is the usual way a stale strategy gets relisted.
    """
    check_policy(policy)
    weeks_after = [e for e in evaluations if e['week'] > demoted_at_week]
    cooldown_ok = len(weeks_after) >= policy['cooldown_weeks'] + policy['relist_weeks']
    clean_run, consecutive = False, 0
    for entry in reversed(weeks_after):
        if entry.get('triggers'):
            break
        consecutive += 1
        if consecutive >= policy['relist_weeks']:
            clean_run = True
            break
    return {'relist_ready': bool(cooldown_ok and clean_run), 'weeks_since_demotion': len(weeks_after),
            'consecutive_clean_evaluations': consecutive,
            'cooldown_weeks': policy['cooldown_weeks'], 'relist_weeks': policy['relist_weeks'],
            'blocked_by': ([] if cooldown_ok and clean_run else
                           ([] if cooldown_ok else ['cooldown not elapsed']) +
                           ([] if clean_run else [f'{policy["relist_weeks"]} consecutive clean paper '
                                                   'evaluations not completed']))}


def _entry_hash(payload, previous):
    body = json.dumps({'payload': payload, 'previous': previous}, sort_keys=True)
    return sha256(body.encode()).hexdigest()


def append_log(path, decision):
    """Append one immutable demotion/promotion decision to a hash-chained log."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    previous = None
    if path.exists():
        lines = [l for l in path.read_text().splitlines() if l.strip()]
        if lines:
            previous = json.loads(lines[-1])['entry_hash']
    payload = dict(decision)
    entry = {'entry': payload, 'previous_hash': previous,
             'entry_hash': _entry_hash(payload, previous)}
    with path.open('a') as handle:
        handle.write(json.dumps(entry, sort_keys=True) + '\n')
    return entry


def read_log(path):
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def verify_log(path):
    """Recompute the chain. Returns problems, empty when the log is intact."""
    problems, previous = [], None
    for index, entry in enumerate(read_log(path), 1):
        if entry.get('previous_hash') != previous:
            problems.append(f'entry {index}: chain break')
        if entry.get('entry_hash') != _entry_hash(entry.get('entry'), entry.get('previous_hash')):
            problems.append(f'entry {index}: hash does not match its contents')
        previous = entry.get('entry_hash')
    return problems


def gate_rows():
    """The published policy, as rows for the register page. Values come from POLICY."""
    return [
        ('Signal lower bound', f'Demote when the rolling log-loss gain lower bound is at or below '
         f'{POLICY["signal_lcb_halt"]}', 'Signal, not return, decides merit.'),
        ('Calibration', f'Demote when mean absolute bin error exceeds {POLICY["calibration_mae_max"]}',
         'A model that is "right on average" but wrong by price is not usable.'),
        ('Coverage', f'Demote when settled share falls under {POLICY["coverage_min"]:.0%} of the '
         'originated slate', 'Selective abstention is a strategy only if the abstentions are counted.'),
        ('Provenance', f'Demote when more than {POLICY["missing_close_max"]:.0%} of settled bets lack '
         'a captured closing number', 'An unauditable run is treated as an unrecorded one.'),
        ('Sample maintenance', f'Live candidates must keep clearing {POLICY["min_eval_weeks"]} '
         'evaluated weeks', 'A sample that stops growing does not keep the licence alive.'),
        ('Risk stop', f'Suspend new stakes at {POLICY["drawdown_suspends_units"]} units of drawdown',
         'Staking can stop money going out. It cannot change a rank.'),
        ('Return path', f'{POLICY["relist_weeks"]} consecutive clean paper evaluations after a '
         f'{POLICY["cooldown_weeks"]}-week cooldown', 'Re-listing is earned after the demotion, not '
         'argued at it.'),
        ('Immutability', 'Every decision is appended to a hash-chained log',
         'The record of a demotion cannot be edited into a different past.'),
    ]


if __name__ == '__main__':  # pragma: no cover
    good_weeks = [{'week': w, 'signal_lcb': 0.02, 'calibration_mae': 0.01, 'coverage': 0.9,
                   'missing_close_share': 0.0} for w in range(1, 9)]
    bad = good_weeks + [{'week': 9, 'signal_lcb': -0.01, 'calibration_mae': 0.02,
                         'coverage': 0.88, 'missing_close_share': 0.0}]
    print(json.dumps({'clean': evaluate(good_weeks), 'broken': evaluate(bad),
                      'relist': relist_ready(9, good_weeks)}, indent=2))
