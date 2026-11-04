# Independent release-quality checks

This directory is an isolated technical QA contribution. It does not replace the research, modeling, substantive source audit, or final integration scopes claimed by parallel sessions. No historical NFL observations or market returns are generated here.

## Run

From the repository root, using Python 3.9 or later and no installed packages:

```sh
python3 -m unittest discover -s release-checks -p 'test_*.py' -v
python3 release-checks/audit.py --output release-checks/audit-snapshot.json
python3 release-checks/pages_status.py --expected-commit "$(git rev-parse origin/main)" --output release-checks/pages-snapshot.json
python3 release-checks/render.py
```

`audit.py` is read-only unless an output path is explicitly supplied. It inspects root HTML by default, independent of the number of pages. It records file hashes, HTML line numbers, per-row source links, and every finding. A caller can use `audit(root, files=[...])` to inspect a different set of HTML files. The published report is not included in its own frozen snapshot.

Checks include local assets, relative-directory indexes, URL-encoded paths, fragment targets, project-subpath mistakes, duplicate IDs, title/language/viewport/main/h1 presence, image alt attributes, navigation names, table headers, and contextual source presence in each data row. These are basic project-policy checks, **not** a full HTML validator, browser test, security audit, accessibility certification or factual verification service. CSS `url()`, JavaScript-generated links, `srcset`, named anchors and CSS rendering are outside scope. HTTP availability of external sources and whether a source supports its adjacent claim require separate review. An allowlisted domain does not imply that its content was checked or endorses the claim.

`pages_status.py` captures only public fields from the official GitHub API using the existing `gh` authentication. It checks the expected commit against the latest build and distinguishes completed Pages deployment workflows from a merely successful build or unrelated CI. Exit 0 requires a built site, built latest build, expected-commit match if requested, and successful matching managed Pages deployment workflow. A site that moves to custom Actions publication requires adapting the workflow selection; the script deliberately fails closed instead of guessing. This does **not** verify the public HTTP response or browser behavior.

`render.py` renders the frozen audit into `index.html`, reruns the synthetic fixture tests and stores their count/status in `test-snapshot.json`. Every original data row remains explicitly claim-support-unverified; the report never turns a present citation into a verified NFL finding. Re-running updates timestamps: these generated reports are dated observations, not a timeless certification.

## Official references reviewed on 2026-11-04

- [GitHub: What is GitHub Pages?](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages) — static hosting and project URL format.
- [GitHub: REST endpoints for Pages](https://docs.github.com/en/rest/pages/pages) — site metadata and build endpoints.
- [WHATWG HTML: links](https://html.spec.whatwg.org/multipage/links.html#links-created-by-a-and-area-elements) — `href` links and resource relationships. This is background for the checker, not certification that this implementation meets every part of the HTML Standard.

The rendered report links each audited row to its original source URLs and its exact audited repository file. Mathematical/empirical claim verification remains with the independent substantive source auditor and final integration owner.

## Integration request

Link `release-checks/index.html` from the main dashboard's Flagged for Review page. Only the shared-page owner should make that edit. This report can be visited directly without navigation changes.

## Expanded research-subsite handoff

`python3 release-checks/expand.py` audits the root pages and `research/*.html` added by another session after our baseline. It refuses to pin evidence URLs if those audited HTML files have uncommitted changes. It writes `expanded-snapshot.json` and `expanded-review.html` with exact row locations and URLs, **without copying unverified NFL numerical results**. Run `render.py` afterwards to link that review from the original report.

Its narrow-registry failures distinguish an absent HTTPS source from a present but unrecognized URL. A registry miss is neither a broken-link finding nor proof that a domain is unofficial. Official-domain additions require explicit review; secondary datasets must not be silently promoted to verified official outcomes. Dynamic JavaScript-rendered rows remain outside this static HTML scan.
