"""Automated readiness report. Never turns missing evidence into a pass.

No model fitting or real-data backtest is performed by this readiness runner.
Future ingestion must be reviewed separately; no public arbitrary evidence
boolean can authorize a passing gate or a reward.
"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis.core import audit_record

ROOT = Path(__file__).resolve().parents[1]


def run():
    catalog = json.loads((ROOT/'research/catalog.json').read_text())
    observations = json.loads((ROOT/'research/observations.json').read_text())
    policy = json.loads((ROOT/'research/policy.json').read_text())
    records = observations['records']
    problems = []
    ids = set()
    for i, record in enumerate(records):
        problems.extend(f'row {i+1}: {e}' for e in audit_record(record))
        if record.get('id') in ids:
            problems.append(f'row {i+1}: duplicate ID')
        ids.add(record.get('id'))
    reason = 'No verified observations or executable market quotes.' if not records else (
        'Structural errors; source verification and independent gate evidence still required.' if problems else
        'Structure alone is insufficient; independent source, model and gate review not implemented.')
    report = {'schema_version': 1, 'evidence_review_date': catalog['as_of'],
              'policy_version': policy['version'], 'mode': 'readiness only; no real-data backtest',
              'records_received': len(records), 'structural_errors': problems, 'reason': reason,
              'strategies': [dict(id=s['id'], name=s['name'], track=s['track'], eligible=False,
                                  gates={g['id']: 'Blocked' for g in policy['gates']},
                                  rank=None, n=None, log_loss=None, brier=None, roi=None,
                                  rho=None, ci_low=None, ci_high=None, reward=None)
                             for s in catalog['strategies']]}
    (ROOT/'research/run.json').write_text(json.dumps(report, indent=2)+'\n')
    print(f'Readiness: BLOCKED. {len(records)} supplied records; {len(problems)} structural errors. {reason}')
    if problems:
        raise SystemExit(1)


if __name__ == '__main__':
    run()
