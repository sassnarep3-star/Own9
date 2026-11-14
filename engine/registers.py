"""Validate the suggestion, decision and question registers.

These registers are advisory content, so the failure mode to guard against is
not a wrong number but an unsupported assertion: a suggestion accepted with no
recorded decision, a question marked answered with no source, a decision with
no stopping rule. Every check here fails closed.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUGGESTIONS = ROOT / 'research/suggestions.json'
DECISIONS = ROOT / 'research/decision-register.json'
BRIEF = ROOT / 'research/decision-brief.json'

SUGGESTION_STATUSES = {'proposed', 'accepted', 'rejected', 'deferred', 'blocked_on_evidence'}
QUESTION_STATES = {'answered', 'open_discoverable', 'unknown_unpublished'}
DECISION_STATES = {'decided', 'decided_pending_data', 'deferred', 'blocked'}
SCORES = (1, 2, 3)
QUESTION_BASES = {'publisher', 'project_mathematics', 'project_record'}


def load():
    return (json.loads(SUGGESTIONS.read_text()),
            json.loads(DECISIONS.read_text()),
            json.loads(BRIEF.read_text()))


def known_source_ids():
    return {s['id'] for s in json.loads((ROOT / 'evidence/sources.json').read_text())}


def impact_rank(suggestion):
    """Sort key: highest impact, lowest evidence-readiness cost, least blocking.

    Lower is better. All three inputs are predeclared 1-3 integers recorded by
    hand, never derived from a result.
    """
    return (-suggestion['impact'], suggestion['evidence_cost'], suggestion['reversibility_cost'])


def validate(suggestions=None, questions=None, brief=None, sources=None):
    suggestions = suggestions if suggestions is not None else json.loads(SUGGESTIONS.read_text())
    questions = questions if questions is not None else json.loads(DECISIONS.read_text())
    brief = brief if brief is not None else json.loads(BRIEF.read_text())
    known = sources if sources is not None else known_source_ids()
    problems = []

    s_items = suggestions['suggestions']
    ids = [s['id'] for s in s_items]
    if len(set(ids)) != len(ids):
        problems.append('duplicate suggestion id')
    for s in s_items:
        if s['status'] not in SUGGESTION_STATUSES:
            problems.append(f'{s["id"]}: unknown status {s["status"]!r}')
        for field in ('title', 'problem', 'proposal', 'why_it_improves_decisions',
                      'cost', 'falsified_by'):
            if not str(s.get(field, '')).strip():
                problems.append(f'{s["id"]}: empty {field}')
        for field in ('impact', 'evidence_cost', 'reversibility_cost'):
            if s.get(field) not in SCORES:
                problems.append(f'{s["id"]}: {field} must be 1, 2 or 3')
        # An accepted or deferred idea must point at the decision that carries it.
        if s['status'] in ('accepted', 'deferred') and not s.get('decision_ref'):
            problems.append(f'{s["id"]}: {s["status"]} without a decision reference')
        if s['status'] == 'blocked_on_evidence' and not s.get('needs'):
            problems.append(f'{s["id"]}: blocked with no named missing artefact')

    d_rows = questions['questions']
    qids = [q['id'] for q in d_rows]
    if len(set(qids)) != len(qids):
        problems.append('duplicate question id')
    for q in d_rows:
        if q['state'] not in QUESTION_STATES:
            problems.append(f'{q["id"]}: unknown state {q["state"]!r}')
        if not q.get('question'):
            problems.append(f'{q["id"]}: missing question text')
        if not q.get('sources'):
            problems.append(f'{q["id"]}: no source reference')
        for ref in q.get('sources', []):
            if ref not in known:
                problems.append(f'{q["id"]}: unregistered source {ref}')
        basis = q.get('basis', 'publisher')
        if basis not in QUESTION_BASES:
            problems.append(f'{q["id"]}: unknown basis {basis!r}')
        if q['state'] == 'answered':
            if not str(q.get('answer') or '').strip():
                problems.append(f'{q["id"]}: answered with no answer text')
            # A publisher-based answer needs a real publisher, not only the repo.
            if basis == 'publisher' and not set(q.get('sources', [])) - {'repo'}:
                problems.append(f'{q["id"]}: answered with no publisher source')
            if basis != 'publisher' and not q.get('basis_note'):
                problems.append(f'{q["id"]}: non-publisher basis needs a basis_note')
        else:
            if q.get('answer') is not None:
                problems.append(f'{q["id"]}: unfinished question must leave answer null')
            if not q.get('blocked_by'):
                problems.append(f'{q["id"]}: unfinished question must state the blocker')

    b_rows = brief['decisions']
    bids = [d['id'] for d in b_rows]
    if len(set(bids)) != len(bids):
        problems.append('duplicate decision id')
    suggestion_ids = set(ids)
    for d in b_rows:
        if d['state'] not in DECISION_STATES:
            problems.append(f'{d["id"]}: unknown state {d["state"]!r}')
        if not d.get('decision'):
            problems.append(f'{d["id"]}: missing decision text')
        if not d.get('default_if_nothing_changes'):
            problems.append(f'{d["id"]}: no default action')
        if not d.get('evidence_required'):
            problems.append(f'{d["id"]}: no evidence requirement')
        if not d.get('stopping_rule'):
            problems.append(f'{d["id"]}: no stopping rule')
        if d.get('suggestion') not in suggestion_ids:
            problems.append(f'{d["id"]}: unknown suggestion {d.get("suggestion")}')
        # A blocked decision has to name the blocker.
        if d['state'] == 'blocked' and not d.get('current_blocker'):
            problems.append(f'{d["id"]}: blocked without naming the blocker')

    referenced = {d['suggestion'] for d in b_rows}
    for s in s_items:
        if s['status'] == 'accepted' and s['id'] not in referenced:
            problems.append(f'{s["id"]}: accepted but no decision references it')

    counts = {state: sum(1 for q in d_rows if q['state'] == state)
              for state in sorted(QUESTION_STATES)}
    summary = {
        'suggestions': len(s_items),
        'decisions': len(b_rows),
        'questions': len(d_rows),
        'question_states': counts,
        'accepted': sum(1 for s in s_items if s['status'] == 'accepted'),
        'blocked_suggestions': sum(1 for s in s_items if s['status'] == 'blocked_on_evidence'),
        'deferred': sum(1 for s in s_items if s['status'] == 'deferred'),
        'blocked_decisions': sum(1 for d in b_rows if d['state'] == 'blocked'),
    }
    return problems, summary


if __name__ == '__main__':
    problems, summary = validate()
    if problems:
        raise SystemExit('\n'.join(problems))
    print('PASS: registers valid —', summary)
