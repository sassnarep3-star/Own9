"""Validate availability evidence; never project a player or invent a depth tier.

Scope: two official Game Books plus one official injury-report snapshot. This
module enforces the rules the project publishes about what may and may not be
claimed from those files. It performs no modelling and produces no probability.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINEUPS = ROOT / 'evidence/lineups/was-nyg-2026-week-9-10.json'
INJURY = ROOT / 'evidence/availability/injury-report-2026-week-10.json'

PRACTICE_STATUSES = {
    'Full Participation in Practice',
    'Limited Participation in Practice',
    'Did Not Participate In Practice',
}
GAME_STATUSES = {'Out', 'Doubtful', 'Questionable'}


def _load(path):
    return json.loads(Path(path).read_text())


def validate_lineups(doc=None):
    """Return (problems, summary). Problems are fail-closed rule violations."""
    doc = doc if doc is not None else _load(LINEUPS)
    problems = []
    for block in doc['lineups']:
        for week in ('week9', 'week10'):
            eleven = block[week]
            if len(eleven) != 11:
                problems.append(f'{block["team"]} {block["side"]} {week}: {len(eleven)} starters, expected 11')
            labels = [slot for slot, _ in eleven]
            if len(set(labels)) != len(labels):
                # Duplicate position labels are legitimate (e.g. two TE, two DT)
                pass
            names = [name for _, name in eleven]
            if len(set(names)) != len(names):
                problems.append(f'{block["team"]} {block["side"]} {week}: a player is listed twice')
        for key in ('out', 'in', 'retained'):
            if not isinstance(block[key], list):
                problems.append(f'{block["team"]} {block["side"]}: {key} must be a list')
        out, inn = set(block['out']), set(block['in'])
        if out & inn:
            problems.append(f'{block["team"]} {block["side"]}: a player is both out and in')
        declared_retained = set(block['retained'])
        week9 = {name for _, name in block['week9']}
        week10 = {name for _, name in block['week10']}
        for name in sorted(out):
            if name in week10:
                problems.append(f'{block["team"]} {block["side"]}: {name} marked out but still starting in week10')
            if name not in week9:
                problems.append(f'{block["team"]} {block["side"]}: {name} marked out but was not a week9 starter')
        for name in sorted(inn):
            if name in week9:
                problems.append(f'{block["team"]} {block["side"]}: {name} marked in but already started in week9')
            if name not in week10:
                problems.append(f'{block["team"]} {block["side"]}: {name} marked in but not starting in week10')
        for week_label, names in (('week9', week9), ('week10', week10)):
            missing = declared_retained - names
            if missing:
                problems.append(f'{block["team"]} {block["side"]}: retained names not listed in {week_label}: {sorted(missing)}')
        changed = bool(out) or bool(inn)
        expected = 'changed' if changed else 'same'
        if block.get('membership_change') != expected:
            problems.append(f'{block["team"]} {block["side"]}: membership_change should be {expected}')
    return problems, {'blocks': len(doc['lineups']),
                      'changed': sum(1 for b in doc['lineups'] if b['membership_change'] == 'changed')}


def validate_injury(doc=None):
    doc = doc if doc is not None else _load(INJURY)
    problems = []
    for i, obs in enumerate(doc['observations'], 1):
        if obs['practice_status'] not in PRACTICE_STATUSES:
            problems.append(f'row {i}: unknown practice status {obs["practice_status"]!r}')
        status = obs['game_status']
        if status is not None and status not in GAME_STATUSES:
            problems.append(f'row {i}: unknown game status {status!r}')
        if not isinstance(obs['injuries'], list):
            problems.append(f'row {i}: injuries must be a list')
    teams = {o['abbr'] for o in doc['observations']}
    return problems, {'observations': len(doc['observations']), 'teams': sorted(teams)}


def replacement_tiers_are_blank(doc=None):
    """The NFL publishes no depth tier, so every tier field must stay null."""
    doc = doc if doc is not None else _load(LINEUPS)
    return all(item.get('depth_tier_of_replacement') is None for item in doc['replacement_chain'])


def validate_all():
    lineup_problems, lineup_summary = validate_lineups()
    injury_problems, injury_summary = validate_injury()
    problems = lineup_problems + injury_problems
    if not replacement_tiers_are_blank():
        problems.append('a replacement depth tier was filled in; the NFL publishes no such field')
    return problems, {**lineup_summary, **injury_summary}


if __name__ == '__main__':
    problems, summary = validate_all()
    if problems:
        raise SystemExit('\n'.join(problems))
    print(f'PASS: availability evidence valid — {summary}')
