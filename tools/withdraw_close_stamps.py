#!/usr/bin/env python3
"""Apply the close-stamp withdrawal to the committed Week 10 price-snapshot store.

Session 446067c4. The scheduled close bot stamped all 52 Week 10 markets with a
closed_at value although no market price existed and the stamp came after the
official 1:00 PM ET kickoff of KC @ ATL. This tool rebuilds the store as
withdraw_close_stamp(originate(...)), which is exactly what tests/test_origination.py
checks the committed file against. Run with --check to verify without writing.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.origination_elo import originate, withdraw_close_stamp, WEEK10_BOT_STAMP  # noqa: E402

RESULTS = ROOT / 'evidence/results/nfl-2026-results.json'
WEEK10 = ROOT / 'evidence/results/nfl-2026-week10.json'
STORE = ROOT / 'data/snapshots/2026-w10-price-snapshot.json'
OPENED_AT = '2026-11-14 (UTC, store deployment)'
REASON = ('No market price was recorded for any Week 10 market, so the stamp is not a close. '
          'The stamp was written at 19:31 UTC, after the 1:00 PM ET (18:00 UTC) kickoff of KC @ ATL '
          'and the 9:30 AM ET (14:30 UTC) kickoff of NE @ DET, so it cannot be called pre-kickoff.')
EVIDENCE = [
    {'url': 'https://www.nfl.com/injuries/', 'shows': 'Sunday 15 Nov 2026 slate: NE @ DET at 9:30 AM EST; KC @ ATL at 1:00 PM EST (read 2026-11-15)'},
    {'url': 'https://www.nfl.com/schedules/2026/by-week/week-10', 'shows': 'Week 10 Sunday games final or live when read on 2026-11-15 (about 23:27 UTC)'},
    {'url': 'https://github.com/sassnarep3-star/Own9/actions/runs/43752883100', 'shows': 'snapshot-close run created 2026-11-15T19:31:20Z, event schedule; the only run of that workflow on record'},
]


def build():
    return withdraw_close_stamp(originate(RESULTS, WEEK10, OPENED_AT), WEEK10_BOT_STAMP, REASON, EVIDENCE)


def main(argv):
    expected = build()
    text = json.dumps(expected, indent=2) + '\n'
    if '--check' in argv:
        ok = STORE.read_text() == text
        print('store matches regeneration' if ok else 'store DIFFERS from regeneration')
        return 0 if ok else 1
    STORE.write_text(text)
    print(f"wrote {STORE.relative_to(ROOT)}: {expected['meta']['close_audit']['markets_withdrawn']} close stamps withdrawn")
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
