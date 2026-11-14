# session-00cf851d — official-source verification

An independent section of Own9. One job: read the official NFL documents on a
single day, compare them line by line with what this repository already claims,
and publish the result with a link on every row.

Live at <https://sassnarep3-star.github.io/Own9/session-00cf851d/>.

## What this section is not

It is not a model, a backtest, a leaderboard, a staking plan or a competition.
No wager is placed and no reward is funded. Nothing here removes luck or
certifies any strategy as skill-based. Every one of those belongs to another
section of this repository.

## What it does

| Page | What it holds |
| --- | --- |
| [Overview](index.html) | Landing page, the numbers at a glance, repository shape |
| [Executive summary](summary.html) | Seven findings in the order they change what should be built next |
| [Sources](sources.html) | The official pages read on 2026-11-14, with what each one supports |
| [Verification](verification.html) | 369 line-by-line checks of committed claims against official documents |
| [Game Books](gamebooks.html) | Official lineups, inactives and statistics from three NFL Game Books |
| [Replacement depth](replacement.html) | How far down the official lists a club reached to fill a starting slot |
| [Results and prices](results.html) | The committed results file, audited and reconciled against the league |
| [Injuries](injuries.html) | The official Week 10 injury report, field for field |
| [Standings](standings.html) | Official 2026 standings |
| [Repository review](repo-review.html) | What is in the repository, measured rather than asserted |
| [Questions](questions.html) | What is known, what is missing, and what would close it |
| [Suggestions](suggestions.html) | Paths to choose between, with costs and risks, nothing built |
| [Flagged for review](flags.html) | Twelve irregularities, each with the official page it was found on |

## The rule this section follows

If the league does not publish a value, the cell stays blank and the gap is
written down. It is never filled from inference, from a news report, or from
another session's record.

That rule is enforced, not asserted. `tools/check.py` fails the build if a
table on a claim-bearing page is published without naming its official source,
and `tests/test_build.py` proves the failure by passing fabricated pages
through the same rules.

## Reproducing it

```sh
python3 session-00cf851d/tools/analysis.py       # verify committed claims, measure replacement depth
python3 session-00cf851d/tools/results_audit.py  # audit the committed results and price file
python3 session-00cf851d/tools/build.py          # render the pages
python3 session-00cf851d/tools/check.py          # structural and citation checks
python3 -m unittest discover -s session-00cf851d/tests
```

The build is deterministic: re-running it reproduces the committed pages
byte for byte, and a test asserts that.

## Scope

Files owned by this session and nothing else: everything under
`session-00cf851d/`, plus append-only entries in `COORDINATION.md` and one
additive step in `.github/workflows/quality.yml`.

`data/raw/games.csv` is opened read-only. It is never edited.
