# Cross-section citation coverage audit

**Review-only add-on.** This report is a structural audit of every tracked `.html` file at commit [`b8cae8e91430375e81a7bb22fa4d18d1bd0daae2`](https://github.com/sassnarep3-star/Own9/commit/b8cae8e91430375e81a7bb22fa4d18d1bd0daae2), the main-branch snapshot after PR #37. It does **not** certify that a URL is live, official, current, permitted, or relevant to the row beside it. No external page was fetched by this audit.

## Baseline findings

- 82 HTML pages and 1,748 table data rows were scanned. Header-only rows were excluded.
- The 19-page root dashboard contributes 706 data rows. The repository's root structural verifier reports the same 706 rows and confirms that every root data row contains a URL in `evidence/sources.json`. That test is structural; it does not validate reachability or whether a source entails a claim.
- Across all 1,748 rows, 938 have a non-repository URL matching the **root** evidence manifest, 573 contain a GitHub/project URL, 692 contain at least one HTTPS URL absent from that root manifest, and 11 contain no HTTPS URL in their cells. These indicators overlap and are not a partition.
- The 11 no-HTTPS candidates are in `research/flagged.html` (3), `research/props.html` (1), and `research/sources.html` (7). Their exact row text and source-file line are available in the [published report](index.html) and [row-level JSON](citation-rows.json). They are review candidates, not automatically errors: some may be proposals, blanks, or local calculations.
- The 692 rows that contain an HTTPS URL absent from the root manifest must not be called unverified just from this count. Some sibling sections maintain their own catalogs or source ledgers, and this audit intentionally does not crosswalk those registries. The count identifies a provenance-integration gap, not a source-quality verdict.

## Reproduce

Requires a full Git clone containing the pinned commit; uses only Python's standard library.

```sh
python3 session-22de6677/audit.py --revision b8cae8e91430375e81a7bb22fa4d18d1bd0daae2
python3 -m unittest discover -s session-22de6677 -p 'test_*.py' -v
```

`audit.py` reads the pinned HTML tree and `evidence/sources.json` using `git show`; it never makes HTTP requests. It regenerates `index.html`, `citation-coverage.json`, and `citation-rows.json`. Every row record includes the page path, row number/id, source line, cell text, HTTPS URLs, matching root-manifest source IDs, and the structural flags. Each page row links to its pinned HTML source; each section-summary row links every HTML page contributing to that section's count.

## Requested integration review

The active integration owner should consider linking this report from the root section directory and deciding whether any no-HTTPS row belongs on the root **Flagged for Review** page. Do not silently rewrite `research/**` or sibling sections under this audit claim. The available source row and exact page-local evidence must be reviewed by the owner before changing their content.
