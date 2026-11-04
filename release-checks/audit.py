#!/usr/bin/env python3
"""Read-only release checks. A citation URL is NEVER proof of its claim."""
import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

# Narrow contextual-source allowlist, not a trust score or a verification label.
SOURCE_HOSTS = {"www.nfl.com", "www.itl.nist.gov", "www.gamblingcommission.gov.uk",
                "docs.github.com", "html.spec.whatwg.org", "api.github.com"}
SOURCE_REPOS = {"sassnarep3-star/Own9", "github/docs", "whatwg/html"}


def contextual_source(url):
    try:
        p = urlsplit(url)
        if p.scheme != "https" or p.username or p.password or p.port not in (None, 443):
            return False
        if p.hostname in SOURCE_HOSTS:
            return True
        return p.hostname == "github.com" and "/".join(p.path.strip("/").split("/")[:2]) in SOURCE_REPOS
    except ValueError:
        return False


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.links = []
        self.rows = []
        self.findings = []
        self.lang = ""
        self.viewport = False
        self.title = []
        self.in_title = False
        self.h1 = 0
        self.main = 0
        self.nav = 0
        self.row = None
        self.table_headers = []
        self.feed(text)
        self.close()
        if not self.lang:
            self.issue("missing-language", "html lang is absent")
        if not "".join(self.title).strip():
            self.issue("missing-title", "Document title is empty")
        if not self.viewport:
            self.issue("missing-viewport", "Responsive viewport metadata is absent")
        if self.h1 != 1:
            self.issue("heading-count", f"Expected one h1; found {self.h1}")
        if self.main != 1:
            self.issue("main-count", f"Expected one main landmark; found {self.main}")
        if not self.nav:
            self.issue("missing-nav", "Navigation landmark is absent")

    def issue(self, code, detail, severity="error"):
        self.findings.append({"code": code, "line": self.getpos()[0], "severity": severity, "detail": detail})

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            if a["id"] in self.ids:
                self.issue("duplicate-id", a["id"])
            self.ids.add(a["id"])
        if tag == "html":
            self.lang = a.get("lang", "").strip()
        if tag == "meta" and a.get("name", "").lower() == "viewport":
            self.viewport = bool(a.get("content"))
        if tag == "title":
            self.in_title = True
        if tag == "h1":
            self.h1 += 1
        if tag == "main":
            self.main += 1
        if tag == "nav":
            self.nav += 1
            if not (a.get("aria-label") or a.get("aria-labelledby")):
                self.issue("unnamed-nav", "Name navigation landmarks", "warning")
        if tag == "img" and "alt" not in a:
            self.issue("missing-alt", "Image has no alt attribute")
        if tag == "table":
            self.table_headers.append(0)
        if tag == "th" and self.table_headers:
            self.table_headers[-1] += 1
        if tag == "tr":
            self.row = {"line": self.getpos()[0], "cells": 0, "text": [], "sources": []}
        if tag == "td" and self.row is not None:
            self.row["cells"] += 1
        for attribute in ("href", "src"):
            if attribute in a and tag in {"a", "area", "link", "img", "script", "iframe", "source"}:
                link = a[attribute].strip()
                self.links.append({"url": link, "line": self.getpos()[0]})
                if self.row is not None and tag == "a" and contextual_source(link):
                    self.row["sources"].append(link)

    def handle_data(self, data):
        if self.in_title:
            self.title.append(data)
        if self.row is not None:
            self.row["text"].append(data)

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag == "table" and self.table_headers:
            if not self.table_headers.pop():
                self.issue("table-no-headers", "Table has no th cells")
        if tag == "tr" and self.row is not None:
            if self.row["cells"]:
                self.row["text"] = " ".join(" ".join(self.row["text"]).split())
                self.row["sources"] = list(dict.fromkeys(self.row["sources"]))
                self.row["claim_support"] = "unverified; link presence only"
                if not self.row["sources"]:
                    self.issue("row-no-source", "Data row has no recognized contextual source")
                self.rows.append(self.row)
            self.row = None


def audit(root, files=None):
    root = Path(root).resolve()
    files = sorted(files if files is not None else root.glob("*.html"))
    parsed = {}
    pages = []
    findings = []
    for path in files:
        path = Path(path).resolve()
        text = path.read_text(encoding="utf-8")
        parsed[path] = Page(text)
        pages.append({"path": str(path.relative_to(root)),
                      "sha256": hashlib.sha256(text.encode()).hexdigest(),
                      "rows": parsed[path].rows, "link_count": len(parsed[path].links)})
    if not pages:
        findings.append({"path": ".", "line": 0, "severity": "error", "code": "no-pages", "detail": "No HTML pages found"})
    for path, page in list(parsed.items()):
        name = str(path.relative_to(root))
        findings.extend({"path": name, **issue} for issue in page.findings)
        for link in page.links:
            url = link["url"]
            code = detail = None
            try:
                parts = urlsplit(url)
                if not url:
                    code, detail = "empty-link", "Empty href/src"
                elif parts.scheme in {"http", "https"} or parts.netloc:
                    # Availability is deliberately not inferred from URL syntax.
                    if not parts.hostname:
                        code, detail = "malformed-external", url
                elif parts.scheme in {"mailto", "tel"}:
                    continue
                elif parts.scheme:
                    code, detail = "unsafe-scheme", url
                elif parts.path.startswith("/"):
                    code, detail = "project-root-link", f"Project Pages links must not assume domain root: {url}"
                else:
                    target = (path.parent / unquote(parts.path)).resolve() if parts.path else path
                    if not target.is_relative_to(root):
                        code, detail = "outside-site", url
                    else:
                        if target.is_dir():
                            target = target / "index.html"
                        if not target.is_file():
                            code, detail = "missing-target", url
                        elif parts.fragment and target.suffix == ".html":
                            target_page = parsed.get(target)
                            if target_page is None:
                                target_page = Page(target.read_text(encoding="utf-8"))
                            fragment = unquote(parts.fragment)
                            if fragment not in target_page.ids and fragment.lower() != "top":
                                code, detail = "missing-fragment", url
            except ValueError as exc:
                code, detail = "invalid-url", str(exc)
            if code:
                findings.append({"path": name, "line": link["line"], "severity": "error", "code": code, "detail": detail})
    return {"schema_version": 1, "scope": "root HTML by default; no external HTTP or semantic claim verification",
            "pages": pages, "findings": findings,
            "errors": sum(f["severity"] == "error" for f in findings),
            "warnings": sum(f["severity"] == "warning" for f in findings),
            "rows_with_claim_support_unverified": sum(len(p["rows"]) for p in pages)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit(args.root)
    report["checked_at_utc"] = datetime.now(timezone.utc).isoformat()
    try:
        report["checkout_commit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=args.root, text=True).strip()
        report["audited_files_modified"] = bool(subprocess.check_output(
            ["git", "status", "--porcelain", "--", *[p["path"] for p in report["pages"]]], cwd=args.root, text=True).strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        report["checkout_commit"] = None
        report["audited_files_modified"] = None
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f'{len(report["pages"])} pages; {report["errors"]} errors; {report["warnings"]} warnings; '
          f'{report["rows_with_claim_support_unverified"]} row claims remain unverified by this checker.')
    for finding in report["findings"]:
        print(f'{finding["severity"]}: {finding["path"]}:{finding["line"]}: {finding["code"]}: {finding["detail"]}')
    return int(bool(report["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
