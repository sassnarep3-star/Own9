# Verification register

Date: **2026-11-04 UTC**. Scope: fresh repository audit, curated source claims,
project mathematics, code tests, generated row provenance and internal links.

`catalog.json` is the canonical row/source manifest. Each source records its
publisher, exact URL, checked date, short observed excerpt and checked scope.
Every research/table row carries at least one direct official-source reference.
A source link on a project-proposal or local-audit row supplies context, **not**
external proof of that proposal or local fact. Code/Git checks verify local facts.

## Retrieval method and limitations

Sources were read via the available web-page retrieval tool. Raw outbound HTTP
from the sandbox to NFL sites failed (TLS connection closed), so an ordinary
Python crawler cannot refresh them in this environment. Tool-returned page text
was inspected for the limited claims recorded. No complete raw-page snapshots,
server timestamps, or content hashes were captured for those research readings;
these are scoped observations, not admission of a usable modeling dataset.
Software documentation uses moving stable URLs; recheck before later research.

Checked sources: NFL rulebook; NFL team statistics categories (not values); NFL
injury report schema; scikit-learn cross-validation, TimeSeriesSplit, calibration;
SciPy Pearson correlation and bootstrap; statsmodels multiple testing;
DraftKings general/market rules (retrieved Virginia scope); Washington regulator
sports wagering landing page; GitHub custom Pages workflow documentation.
All direct URLs and evidence scopes are in the catalog and Sources page.

## Retrieval irregularities

- `https://operations.nfl.com/inside-football-ops/players-teams/nfl-injury-report-policy/`
  returned 404 content. No policy details asserted. Replaced only for injury
  report schema by `https://www.nfl.com/injuries/`.
- `https://www.nist.gov/itl/sed/statistical-reference-datasets/strd-background-information/anova-general-information`
  returned page-not-found content. No NIST claim used.
- NFL statistics extraction lacked reliable headers for numerical rows. No
  numerical values admitted. The official source itself is not accused of an
  error; the limitation is in the extracted representation.
- DraftKings retrieved general rules apply to Virginia. No Washington legality,
  participation, or operator availability inferred from them.

## Verification levels

1. **Source checked:** limited stated content observed on a primary publisher's
   page. Does not mean every word of that site was audited.
2. **Project proposal:** local research policy/specification; official reference
   explains the method, not an endorsement or verified result.
3. **Code tested:** synthetic fixtures check arithmetic and fail-closed behavior;
   not a historical NFL backtest or proof of future skill.
4. **Unverified:** unavailable empirical values stay null; review flags explain
   missing evidence. An unchecked fact never becomes verified because it has a URL.

## Build checks

`python -m unittest discover -s tests -v` checks synthetic engine fixtures and
manifest invariants. `python scripts/build_site.py` emits static HTML and source
JSON. `python scripts/check_site.py` parses every output page, validates unique
IDs, local href/src paths and fragment targets, and requires an external official
source link in every data-table row. `scripts/browser_test.cjs` exercises desktop
and mobile navigation, filtering, CSV export, console errors and null metrics
when Playwright/Chromium are installed. External accessibility was checked only
for the limited source pages above via retrieval, not via a universal automated
live-link crawler. Publication/deployment status is in the coordination board.
