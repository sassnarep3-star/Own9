# NFL injury & strategy dashboard (session 8b05dd6d)

Live (after GitHub Pages deploys from `main`): https://sassnarep3-star.github.io/Own9/session-8b05dd6d/

Research only. Nothing here is betting advice. Singapore law: only Singapore Pools is GRA-licensed for remote gambling.

## Contents

| Page | What it holds |
| --- | --- |
| `index.html` | Landing page with status at a glance |
| `summary.html` | Executive summary and owner decisions |
| `injuries.html` | Week 10 2026 official injury report rows (160), position-group exposure, NFL.com headlines |
| `games.html` | 14 Week 10 games checked against the NFL.com schedule |
| `starters.html` | Starter/backup replacements that NFL.com states; team-wide depth gap left blank |
| `strategies.html` | Strategy registry (none validated), Singapore legal position, gate-count conflict |
| `questions.html` | Information gaps with sources |
| `suggestions.html` | Proposals for review; none implemented |
| `repo-review.html` | Repository review with file links |
| `sources.html` | Sources and dates checked |
| `flags.html` | Flagged for Review |

## Data and rebuild

- `data/*.psv` are the transcribed source rows (the single source of truth). `data/*.csv` are generated exports.
- `python3 tools/build.py` regenerates all pages (standard library only).
- `python3 tools/check.py` verifies internal links, that every table row has an https source link, and that the CSV matches the transcription. It does not fetch external URLs.

## Rules applied

- Every table row carries a source link. Blank cells are unverified and are never inferred.
- Only players with an injury entry or a game status are listed. Starter/backup columns are blank because the injury report does not state them.
- Headline text is recorded as shown; article bodies were not opened.
