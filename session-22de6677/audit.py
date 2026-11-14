#!/usr/bin/env python3
"""Structural row-citation census for a pinned repository tree.

This tool does not fetch URLs, decide whether a publisher is official, or verify
that a source entails a claim. It only measures row-level HTTPS links against
that tree's declared evidence manifest.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import subprocess
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
DEFAULT_REVISION = "b8cae8e91430375e81a7bb22fa4d18d1bd0daae2"
REPOSITORY = "https://github.com/sassnarep3-star/Own9"
PROJECT_PUBLISHER = "own9 repository (primary project record)"


class TableRows(HTMLParser):
    """Collect only data rows (rows containing at least one td)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[dict] = []
        self.current: dict | None = None
        self.current_cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "tr":
            self.current = {"id": attrs_dict.get("id") or "", "line": self.getpos()[0], "has_td": False, "links": [], "cells": []}
            self.current_cell = None
            return
        if self.current is None:
            return
        if tag in ("td", "th"):
            self.current_cell = []
            self.current["cells"].append(self.current_cell)
            if tag == "td":
                self.current["has_td"] = True
        for attr in ("href", "src"):
            value = attrs_dict.get(attr)
            if value:
                self.current["links"].append(value)

    def handle_data(self, data: str) -> None:
        if self.current_cell is not None:
            self.current_cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th"):
            self.current_cell = None
        if tag == "tr" and self.current is not None:
            if self.current["has_td"]:
                self.current["cells"] = [" ".join("".join(cell).split()) for cell in self.current["cells"]]
                self.rows.append(self.current)
            self.current = None
            self.current_cell = None


def normalize_url(value: str) -> str | None:
    """Normalize only harmless URL spelling differences for manifest matching."""
    try:
        parts = urlsplit(value)
        if parts.scheme.lower() != "https" or not parts.hostname:
            return None
        host = parts.hostname.lower()
        port = f":{parts.port}" if parts.port and parts.port != 443 else ""
        path = parts.path or "/"
        if path != "/":
            path = path.rstrip("/") or "/"
        return urlunsplit(("https", host + port, path, parts.query, ""))
    except ValueError:
        return None


def git_text(revision: str, path: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    return result.stdout


def git_files(revision: str) -> list[str]:
    result = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", revision],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    return [
        name
        for name in result.stdout.splitlines()
        if name.endswith(".html") and not name.startswith("session-22de6677/")
    ]


def publisher_is_project_record(publisher: str) -> bool:
    return publisher.strip().lower() == PROJECT_PUBLISHER


def page_section(path: str) -> str:
    parts = Path(path).parts
    return parts[0] if len(parts) > 1 else "root"


def audit_tree(revision: str) -> dict:
    files = git_files(revision)
    if not files:
        raise ValueError(f"No HTML pages found at revision {revision}")

    manifest = json.loads(git_text(revision, "evidence/sources.json"))
    source_by_url: dict[str, list[dict]] = defaultdict(list)
    for source in manifest:
        normalized = normalize_url(source.get("url", ""))
        if normalized:
            source_by_url[normalized].append(source)

    pages: list[dict] = []
    row_details: list[dict] = []
    all_rows = Counter()
    for path in sorted(files):
        content = git_text(revision, path)
        parser = TableRows()
        parser.feed(content)
        parser.close()
        page_counts = Counter()
        for row_number, row in enumerate(parser.rows, 1):
            links = row["links"]
            secure_links = [link for link in links if normalize_url(link)]
            manifest_matches = []
            for link in secure_links:
                manifest_matches.extend(source_by_url.get(normalize_url(link), []))
            manifest_matches = list({item["id"]: item for item in manifest_matches}.values())
            is_project = any(publisher_is_project_record(item.get("publisher", "")) for item in manifest_matches)
            is_publisher = any(not publisher_is_project_record(item.get("publisher", "")) for item in manifest_matches)
            has_github = any((urlsplit(link).hostname or "").lower() in {"github.com", "raw.githubusercontent.com"}
                             for link in secure_links)
            unregistered = any(not source_by_url.get(normalize_url(link), []) for link in secure_links)
            no_https = not bool(secure_links)
            page_counts["data_rows"] += 1
            page_counts["rows_with_root_manifest_publisher"] += bool(is_publisher)
            page_counts["rows_with_project_record"] += bool(is_project or has_github)
            page_counts["rows_with_https_absent_from_root_manifest"] += bool(unregistered)
            page_counts["rows_without_https"] += no_https
            row_details.append({
                "page": path,
                "row_number": row_number,
                "source_line": row["line"],
                "row_id": row["id"],
                "text": " | ".join(cell for cell in row["cells"] if cell),
                "https_links": secure_links,
                "manifest_source_ids": sorted(item["id"] for item in manifest_matches),
                "has_manifest_publisher": bool(is_publisher),
                "has_project_record": bool(is_project or has_github),
                "has_https_absent_from_root_manifest": bool(unregistered),
                "has_no_https": no_https,
            })
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        record = {
            "path": path,
            "section": page_section(path),
            "sha256": digest,
            **{key: int(page_counts[key]) for key in (
                "data_rows",
                "rows_with_root_manifest_publisher",
                "rows_with_project_record",
                "rows_with_https_absent_from_root_manifest",
                "rows_without_https",
            )},
        }
        pages.append(record)
        all_rows.update(page_counts)

    section_counts: dict[str, Counter] = defaultdict(Counter)
    for page in pages:
        section_counts[page["section"]].update({
            key: page[key] for key in (
                "data_rows",
                "rows_with_root_manifest_publisher",
                "rows_with_project_record",
                "rows_with_https_absent_from_root_manifest",
                "rows_without_https",
            )
        })
    sections = [
        {"section": name, **{key: int(counts[key]) for key in (
            "data_rows",
            "rows_with_root_manifest_publisher",
            "rows_with_project_record",
            "rows_with_https_absent_from_root_manifest",
            "rows_without_https",
        )}}
        for name, counts in sorted(section_counts.items())
    ]
    return {
        "revision": revision,
        "manifest_entries": len(manifest),
        "page_count": len(pages),
        "data_row_count": int(all_rows["data_rows"]),
        "coverage": {
            key: int(all_rows[key]) for key in (
                "rows_with_root_manifest_publisher",
                "rows_with_project_record",
                "rows_with_https_absent_from_root_manifest",
                "rows_without_https",
            )
        },
        "counts_overlap": True,
        "limitations": [
            "The scan measures HTML structure and HTTPS-link presence only; it does not request any URL.",
            "A URL in the root manifest is not automatically an official NFL source, current source, or proof that a cited claim is entailed. Several sibling sections also maintain their own catalogs or source ledgers, which are not crosswalked here.",
            "GitHub/project-record links document repository artifacts and are not counted as external publisher evidence.",
            "Rows without HTTPS links may be proposals, placeholders, or intentionally source-free; they require human claim-level review before being called defects. Other published sections may also keep their own catalogs or source ledgers, which this root-manifest match does not crosswalk.",
            "Only tracked .html files at the pinned Git tree are included. Data files and linked external pages are not semantically audited.",
        ],
        "sections": sections,
        "pages": pages,
        "rows": row_details,
    }


def github_blob(revision: str, path: str) -> str:
    return f"{REPOSITORY}/blob/{revision}/{path}"


def render_html(report: dict) -> str:
    revision = report["revision"]
    no_https = report["coverage"]["rows_without_https"]
    absent_from_root_manifest = report["coverage"]["rows_with_https_absent_from_root_manifest"]
    publisher_rows = report["coverage"]["rows_with_root_manifest_publisher"]
    project_rows = report["coverage"]["rows_with_project_record"]

    page_rows = []
    for item in report["pages"]:
        path = item["path"]
        page_url = f"../{html.escape(path, quote=True)}"
        source_url = html.escape(github_blob(revision, path), quote=True)
        page_rows.append(
            "<tr>"
            f"<th scope=\"row\"><a href=\"{page_url}\">{html.escape(path)}</a></th>"
            f"<td>{html.escape(item['section'])}</td>"
            f"<td>{item['data_rows']}</td>"
            f"<td>{item['rows_with_root_manifest_publisher']}</td>"
            f"<td>{item['rows_with_project_record']}</td>"
            f"<td>{item['rows_with_https_absent_from_root_manifest']}</td>"
            f"<td>{item['rows_without_https']}</td>"
            f"<td><a href=\"{source_url}\">Pinned HTML source ↗</a><br><code>{item['sha256'][:12]}</code></td>"
            "</tr>"
        )
    section_rows = []
    for item in report["sections"]:
        name = item["section"]
        source_pages = [page for page in report["pages"] if page["section"] == name]
        source_links = "<br>".join(
            f"<a href=\"{html.escape(github_blob(revision, page['path']), quote=True)}\">{html.escape(Path(page['path']).name)} ↗</a>"
            for page in source_pages
        )
        section_rows.append(
            "<tr>"
            f"<th scope=\"row\">{html.escape(name)}</th>"
            f"<td>{item['data_rows']}</td>"
            f"<td>{item['rows_with_root_manifest_publisher']}</td>"
            f"<td>{item['rows_with_project_record']}</td>"
            f"<td>{item['rows_with_https_absent_from_root_manifest']}</td>"
            f"<td>{item['rows_without_https']}</td>"
            f"<td>{source_links}</td>"
            "</tr>"
        )

    no_https_rows = [row for row in report["rows"] if row["has_no_https"]]
    exception_rows = []
    for row in no_https_rows:
        page_url = "../" + quote(row["page"], safe="/")
        if row["row_id"]:
            page_url += "#" + quote(row["row_id"], safe="-._~")
        source_url = html.escape(github_blob(revision, row["page"]) + f"#L{row['source_line']}", quote=True)
        excerpt = row["text"][:260] + ("…" if len(row["text"]) > 260 else "")
        exception_rows.append(
            "<tr>"
            f"<th scope=\"row\"><a href=\"{html.escape(page_url, quote=True)}\">{html.escape(row['page'])} · row {row['row_number']}</a></th>"
            f"<td>{html.escape(row['row_id'] or 'no row id')}</td>"
            f"<td>{html.escape(excerpt)}</td>"
            f"<td><a href=\"{source_url}\">Pinned source HTML ↗</a></td>"
            "</tr>"
        )

    notes = "".join(f"<li>{html.escape(note)}</li>" for note in report["limitations"])
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Structural citation coverage census for all tracked Own9 HTML pages at a pinned commit.">
<title>Site-wide citation census · Own9 review</title>
<style>
:root{{color-scheme:light;--ink:#182437;--muted:#56657a;--line:#d8e0e9;--paper:#fff;--wash:#f3f6fa;--blue:#1f5da8;--amber:#80510e;--red:#8e3434}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--wash);color:var(--ink);font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}}
header,main,footer{{max-width:1240px;margin:auto;padding:1.1rem}}header{{padding-top:2rem}}a{{color:var(--blue);text-underline-offset:.16em}}a:focus-visible,button:focus-visible,select:focus-visible{{outline:3px solid #c37d00;outline-offset:3px}}
.kicker{{font-size:.76rem;font-weight:800;letter-spacing:.1em;color:var(--blue);text-transform:uppercase}}h1{{font-size:clamp(2rem,4vw,3rem);line-height:1.1;margin:.35rem 0 .8rem}}h2{{font-size:1.3rem;margin:1.8rem 0 .4rem}}p{{max-width:86ch}}.meta,.muted{{color:var(--muted)}}.box{{background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:1rem 1.15rem;margin:1rem 0}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(185px,1fr));gap:.75rem;margin:1rem 0}}.card{{background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:1rem}}.card b{{display:block;font-size:1.7rem;line-height:1.2}}.card span{{color:var(--muted);font-size:.9rem}}
.table-wrap{{overflow:auto;background:var(--paper);border:1px solid var(--line);border-radius:12px}}.table-wrap:focus-visible{{outline:3px solid #c37d00;outline-offset:2px}}table{{width:100%;border-collapse:collapse;min-width:880px}}caption{{text-align:left;padding:.8rem;font-weight:700}}th,td{{padding:.62rem .7rem;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}thead th{{background:#edf2f8;position:sticky;top:0}}tbody tr:nth-child(even){{background:#fafbfd}}code{{font-size:.78rem;overflow-wrap:anywhere}}
.callout{{border-left:5px solid var(--amber);background:#fff8e8;padding:.85rem 1rem}}.warning{{color:var(--red);font-weight:700}}.nav{{display:flex;flex-wrap:wrap;gap:.8rem}}footer{{color:var(--muted);font-size:.9rem;padding-bottom:2rem}}
@media(max-width:680px){{header,main,footer{{padding-left:.8rem;padding-right:.8rem}}.card b{{font-size:1.4rem}}}}
</style>
</head>
<body>
<header><div class="kicker">Own9 · independent structural review</div><h1>Site-wide citation census</h1>
<p class="meta">Pinned source tree: <code>{html.escape(revision)}</code> · {report['page_count']} tracked HTML pages · {report['data_row_count']} HTML data rows · {report['manifest_entries']} declared source-manifest entries.</p>
<nav class="nav" aria-label="Related pages"><a href="../index.html">Main dashboard</a><a href="../sources.html">Root source register</a><a href="../flags.html">Flagged for Review</a><a href="https://github.com/sassnarep3-star/Own9/blob/{html.escape(revision, quote=True)}/evidence/sources.json">Pinned source manifest ↗</a></nav></header>
<main>
<section aria-labelledby="summary"><h2 id="summary">What this measures</h2>
<p>This is an automated, reproducible count of source-link <em>structure</em>, not a certification of the claims on these pages. It separates links matching a root-manifest non-repository publisher from links to the project repository, external HTTPS URLs absent from the root evidence manifest, and rows with no HTTPS URL in their cells. These are overlapping indicators, not a partition.</p>
<div class="cards" aria-label="Census totals">
<div class="card"><b>{report['page_count']}</b><span>HTML pages scanned</span></div>
<div class="card"><b>{report['data_row_count']}</b><span>Data rows (header-only rows excluded)</span></div>
<div class="card"><b>{publisher_rows}</b><span>Rows with a root-manifest non-repository publisher URL</span></div>
<div class="card"><b>{project_rows}</b><span>Rows with a GitHub/project URL</span></div>
<div class="card"><b>{absent_from_root_manifest}</b><span>Rows with an HTTPS URL absent from the root manifest</span></div>
<div class="card"><b>{no_https}</b><span>Rows with no HTTPS URL in their cells</span></div>
</div>
<div class="box callout"><strong>Interpretation guardrail.</strong> A source link can be wrong, stale, unavailable, or irrelevant to the adjacent value. This census does not fetch or validate any link, check source entailment, or mark every non-publisher row as defective. The root dashboard's 658-row baseline is separately checked by its own structural verifier. URLs from sibling catalogs count as absent from the root manifest here unless they also appear in it.</div>
</section>
<section aria-labelledby="groups"><h2 id="groups">By published section</h2><div class="table-wrap" role="region" aria-label="Citation counts by published section" tabindex="0"><table><caption>Overlapping citation indicators; source cell links every HTML page contributing to that section's totals</caption><thead><tr><th scope="col">Section</th><th scope="col">Data rows</th><th scope="col">Root-manifest publisher URL</th><th scope="col">GitHub/project URL</th><th scope="col">HTTPS URL absent from root manifest</th><th scope="col">No HTTPS URL</th><th scope="col">Source</th></tr></thead><tbody>{''.join(section_rows)}</tbody></table></div></section>
<section aria-labelledby="pages"><h2 id="pages">Page-by-page census</h2><div class="table-wrap" role="region" aria-label="Page-by-page citation census" tabindex="0"><table><caption>Each row links to the page view and to its exact HTML source at the pinned commit</caption><thead><tr><th scope="col">Page</th><th scope="col">Section</th><th scope="col">Data rows</th><th scope="col">Root-manifest publisher URL</th><th scope="col">GitHub/project URL</th><th scope="col">HTTPS URL absent from root manifest</th><th scope="col">No HTTPS URL</th><th scope="col">Reproducibility</th></tr></thead><tbody>{''.join(page_rows)}</tbody></table></div></section>
<section aria-labelledby="no-source"><h2 id="no-source">Rows without an HTTPS source link in their cells</h2><p>These {no_https} data rows are review candidates, not automatically confirmed errors: some may be proposals, placeholders, or rows whose evidence is intentionally recorded elsewhere. Each item links to the original row when it has an HTML id, and to the pinned source file.</p><div class="table-wrap" role="region" aria-label="Rows without an HTTPS source link" tabindex="0"><table><caption>Row-level exceptions for manual review</caption><thead><tr><th scope="col">Page / row</th><th scope="col">HTML id</th><th scope="col">Text excerpt</th><th scope="col">Source</th></tr></thead><tbody>{''.join(exception_rows)}</tbody></table></div></section>
<section aria-labelledby="limits"><h2 id="limits">Scope and limitations</h2><div class="box"><ul>{notes}</ul><p>To reproduce the census from a full git clone: <code>python3 session-22de6677/audit.py --revision {html.escape(revision)}</code>. The machine-readable outputs are <a href="citation-coverage.json">page/section counts</a> and <a href="citation-rows.json">all {report['data_row_count']} row records</a>. Hashes are SHA-256 of each source HTML file as read from the pinned tree.</p></div></section>
</main>
<footer>Research-only publication QA · No betting recommendations or NFL performance conclusions. All empirical facts remain subject to the linked publisher source and its specific scope.</footer>
</body></html>'''


def write_report(revision: str) -> dict:
    report = audit_tree(revision)
    OUT.mkdir(parents=True, exist_ok=True)
    rows = report.pop("rows")
    (OUT / "citation-coverage.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "citation-rows.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report["rows"] = rows
    (OUT / "index.html").write_text(render_html(report), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", default=DEFAULT_REVISION, help="Git commit or tree to scan (default: main at 2026-11-14 baseline)")
    args = parser.parse_args()
    report = write_report(args.revision)
    print(json.dumps({
        "revision": report["revision"],
        "pages": report["page_count"],
        "data_rows": report["data_row_count"],
        **report["coverage"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
