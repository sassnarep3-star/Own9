# Price-snapshot store contract

One row per market per book per game, with **both** an opening and a closing
number. The file is committed header-only: no executable quote with provenance
has been captured, so no row may be invented to demonstrate the format.

| Rule | Why |
| --- | --- |
| Both prices required | A half-record would let an opening number be scored against a closing number that was never available. |
| Closing capture not later than kickoff | A price captured after kickoff is not a closing price. |
| Opening capture not later than closing capture | Otherwise the labels are wrong, not the market. |
| Side and total rows carry a line | Without the handicap the market cannot be settled against a score. |
| Source id, book and raw hash recorded | An untraceable number cannot be re-checked and cannot support a claim. |
| Settlement rule version recorded | Push, overtime and void rules differ by book; without them a price has no defined meaning. |

Validation is implemented in `engine/origination.py::validate_snapshot` and
exercised by `tests/test_origination.py`. Importing this file into a model, a
backtest or a leaderboard is blocked until the store holds rows that pass it.
