"""Backward-compatible entry point for the structural verifier."""
from verify import check

if __name__ == '__main__':
    errors, rows = check()
    if errors: raise SystemExit('\n'.join(errors))
    print(f'PASS: {rows} source-linked rows; deterministic pages and local links. Structural checks only.')
