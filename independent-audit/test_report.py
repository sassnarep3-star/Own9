#!/usr/bin/env python3
"""Structural checks only; they do not verify external pages or substantive claims."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, unquote
import importlib.util
import json
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
spec = importlib.util.spec_from_file_location("audit_build", HERE / "build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)

OFFICIAL_HOSTS = {
    "github.com", "docs.github.com", "www.nfl.com", "www.nflgsis.com",
    "www.weather.gov", "sportsbook.fanatics.com", "online.stat.psu.edu",
    "www.spaceweather.gov", "scikit-learn.org", "www.amstat.org",
    "www.itl.nist.gov", "pmc.ncbi.nlm.nih.gov", "wsgc.wa.gov",
    "www.gamblingcommission.gov.uk",
}


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hrefs = []
        self.ids = set()
        self.rows = []
        self.row = None
        self.in_body = False
        self.tags = {}
        self.language = None
        self.headers_without_scope = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags[tag] = self.tags.get(tag, 0) + 1
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag == "html":
            self.language = attrs.get("lang")
        if tag in {"a", "link"} and "href" in attrs:
            self.hrefs.append(attrs["href"])
            if self.row is not None:
                self.row.append(attrs["href"])
        if tag == "tbody":
            self.in_body = True
        if tag == "tr" and self.in_body:
            self.row = []
        if tag == "th" and attrs.get("scope") != "col":
            self.headers_without_scope += 1

    def handle_endtag(self, tag):
        if tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None
        if tag == "tbody":
            self.in_body = False


def parse(path):
    p = Page()
    p.feed(path.read_text(encoding="utf-8"))
    p.close()
    return p


class AuditReportTests(unittest.TestCase):
    def setUp(self):
        self.pages = {filename: parse(HERE / filename) for _, filename, _ in build.PAGES}

    def test_generated_pages_are_current(self):
        for source, filename, label in build.PAGES:
            with self.subTest(filename=filename):
                expected = build.render_page((HERE / source).read_text(encoding="utf-8"), filename, label)
                self.assertEqual((HERE / filename).read_text(encoding="utf-8"), expected)

    def test_source_links_on_every_data_row(self):
        for filename, page in self.pages.items():
            for number, row in enumerate(page.rows, 1):
                with self.subTest(filename=filename, row=number):
                    self.assertTrue(any(urlparse(link).scheme == "https" and
                                        urlparse(link).hostname in OFFICIAL_HOSTS for link in row))

    def test_every_external_link_is_https_and_from_reviewed_publisher(self):
        for filename, page in self.pages.items():
            for link in page.hrefs:
                parsed = urlparse(link)
                if parsed.scheme:
                    with self.subTest(filename=filename, link=link):
                        self.assertEqual(parsed.scheme, "https")
                        self.assertIn(parsed.hostname, OFFICIAL_HOSTS)

    def test_local_targets_and_fragments_exist(self):
        for filename, page in self.pages.items():
            for link in page.hrefs:
                parsed = urlparse(link)
                if parsed.scheme or parsed.netloc:
                    continue
                with self.subTest(filename=filename, link=link):
                    target = (HERE / unquote(parsed.path)).resolve() if parsed.path else (HERE / filename)
                    self.assertTrue(target.is_file(), f"Missing target: {target}")
                    if parsed.fragment:
                        self.assertIn(unquote(parsed.fragment), parse(target).ids)

    def test_landmarks_headings_and_table_headers(self):
        for filename, page in self.pages.items():
            with self.subTest(filename=filename):
                self.assertEqual(page.language, "en")
                self.assertEqual(page.tags.get("main"), 1)
                self.assertEqual(page.tags.get("h1"), 1)
                self.assertEqual(page.tags.get("nav"), 1)
                self.assertEqual(page.headers_without_scope, 0)
                self.assertEqual(page.tags.get("table", 0), page.tags.get("caption", 0))

    def test_all_baseline_rows_are_reviewed(self):
        self.assertEqual(len(self.pages["audit.html"].rows), 28)
        snapshot = ROOT / "release-checks" / "audit-snapshot.json"
        if snapshot.exists():
            previous = json.loads(snapshot.read_text(encoding="utf-8"))
            self.assertEqual(sum(len(page["rows"]) for page in previous["pages"]), 28)

    def test_unlicensed_nfl_compilation_is_not_present_in_audit_directory(self):
        self.assertEqual(list(HERE.glob("*.csv")), [])

    def test_inline_renderer_escapes_unsafe_text_and_rejects_schemes(self):
        self.assertEqual(build.inline("<script>alert(1)</script>"), "&lt;script&gt;alert(1)&lt;/script&gt;")
        with self.assertRaises(ValueError):
            build.inline("[bad](javascript:alert(1))")


if __name__ == "__main__":
    unittest.main(verbosity=2)
