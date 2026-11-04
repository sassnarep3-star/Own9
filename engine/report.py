"""Generate a fail-closed status report; never synthesize missing performance."""
import json
from pathlib import Path
from engine.core import eligibility


def report(catalog):
    return {'as_of': catalog['as_of'], 'mode': 'research only — no empirical results',
            'eligible_count': 0,
            'strategies': [{'id': s['id'], 'name': s['name'], **eligibility({}),
                            'rank': None, 'roi': None, 'correlation': None,
                            'reward': None, 'reason': 'No verified as-of historical observations or quotes; gates not evaluated.'}
                           for s in catalog['strategies']]}


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    print(json.dumps(report(json.loads((root/'research/catalog.json').read_text())),indent=2,ensure_ascii=False))
