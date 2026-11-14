import importlib.util
import json
import unittest
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("audit.py")
spec = importlib.util.spec_from_file_location("citation_audit", MODULE_PATH)
audit = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(audit)


class DocumentLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.ids = set()
        self.duplicate_ids = []
        self.h1_count = 0
        self.main_count = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
        if "id" in attrs:
            if attrs["id"] in self.ids:
                self.duplicate_ids.append(attrs["id"])
            self.ids.add(attrs["id"])
        self.h1_count += tag == "h1"
        self.main_count += tag == "main"


class ParserTests(unittest.TestCase):
    def test_counts_only_data_rows_and_keeps_row_location(self):
        parser = audit.TableRows()
        parser.feed(
            '<table><tr><th>Heading</th><th>Other</th></tr>'
            '<tr id="row-1"><th>Fact</th><td><a href="https://www.nfl.com/x">NFL</a></td></tr></table>'
        )
        self.assertEqual(len(parser.rows), 1)
        self.assertEqual(parser.rows[0]["id"], "row-1")
        self.assertGreater(parser.rows[0]["line"], 0)
        self.assertIn("https://www.nfl.com/x", parser.rows[0]["links"])
        self.assertEqual(parser.rows[0]["cells"], ["Fact", "NFL"])

    def test_url_normalization_is_https_only_and_conservative(self):
        self.assertEqual(
            audit.normalize_url("https://EXAMPLE.com/path/#section"),
            "https://example.com/path",
        )
        self.assertIsNone(audit.normalize_url("http://example.com/path"))
        self.assertIsNone(audit.normalize_url("not a url"))


class PinnedTreeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = audit.audit_tree(audit.DEFAULT_REVISION)

    def test_census_counts_are_reproducible_for_the_pinned_tree(self):
        self.assertEqual(self.report["page_count"], 82)
        self.assertEqual(self.report["data_row_count"], 1700)
        self.assertTrue(self.report["counts_overlap"])
        self.assertEqual(
            self.report["coverage"],
            {
                "rows_with_root_manifest_publisher": 933,
                "rows_with_project_record": 526,
                "rows_with_https_absent_from_root_manifest": 692,
                "rows_without_https": 11,
            },
        )

    def test_root_dashboard_count_matches_its_structural_verifier_baseline(self):
        root = next(item for item in self.report["sections"] if item["section"] == "root")
        self.assertEqual(root["data_rows"], 658)
        self.assertEqual(root["rows_without_https"], 0)

    def test_every_data_row_is_in_machine_readable_output(self):
        self.assertEqual(len(self.report["rows"]), self.report["data_row_count"])
        self.assertTrue(all(item["source_line"] > 0 for item in self.report["rows"]))
        self.assertTrue(all("page" in item and "row_number" in item for item in self.report["rows"]))

    def test_no_https_candidates_are_individually_locatable(self):
        candidates = [item for item in self.report["rows"] if item["has_no_https"]]
        self.assertEqual(len(candidates), 11)
        self.assertTrue(all(item["page"] and item["source_line"] for item in candidates))
        self.assertTrue(any(item["page"] == "research/sources.html" for item in candidates))

    def test_rendered_report_has_a_source_link_in_every_data_row(self):
        parser = audit.TableRows()
        parser.feed(audit.render_html(self.report))
        parser.close()
        self.assertTrue(parser.rows)
        for row in parser.rows:
            self.assertTrue(
                any(link.startswith("https://github.com/sassnarep3-star/Own9/blob/") for link in row["links"]),
                row["id"],
            )

    def test_rendered_report_has_landmarks_and_no_broken_local_links(self):
        content = audit.render_html(self.report)
        parser = DocumentLinks()
        parser.feed(content)
        self.assertEqual(parser.h1_count, 1)
        self.assertEqual(parser.main_count, 1)
        self.assertEqual(parser.duplicate_ids, [])
        base = Path(__file__).resolve().parent
        for link in parser.links:
            parsed = urlsplit(link)
            if parsed.scheme:
                self.assertEqual(parsed.scheme, "https", link)
                continue
            target = (base / unquote(parsed.path)).resolve() if parsed.path else (base / "index.html")
            self.assertTrue(target.is_relative_to(audit.ROOT), link)
            self.assertTrue(target.is_file(), link)

    def test_committed_outputs_match_the_pinned_generator(self):
        coverage_path = Path(__file__).with_name("citation-coverage.json")
        rows_path = Path(__file__).with_name("citation-rows.json")
        page_path = Path(__file__).with_name("index.html")
        self.assertTrue(coverage_path.exists())
        self.assertTrue(rows_path.exists())
        self.assertTrue(page_path.exists())
        stored_coverage = json.loads(coverage_path.read_text())
        expected_coverage = dict(self.report)
        expected_coverage.pop("rows")
        self.assertEqual(stored_coverage, expected_coverage)
        self.assertEqual(json.loads(rows_path.read_text()), self.report["rows"])
        self.assertEqual(page_path.read_text(), audit.render_html(self.report))


if __name__ == "__main__":
    unittest.main()
