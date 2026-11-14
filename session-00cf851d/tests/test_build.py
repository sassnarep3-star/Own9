"""Tests for the built pages, the build's determinism and the fail-closed checker."""

import hashlib
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SESSION = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SESSION, "tools"))

import build as build_mod  # noqa: E402
import check as check_mod  # noqa: E402


def digest(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


class TestPages(unittest.TestCase):
    def test_every_declared_page_was_built(self):
        for name, _, _ in build_mod.PAGES:
            self.assertTrue(os.path.exists(os.path.join(SESSION, name)), name)

    def test_the_committed_pages_match_a_fresh_build(self):
        """Deterministic regeneration: what is committed is what the build produces."""
        before = {n: digest(os.path.join(SESSION, n)) for n, _, _ in build_mod.PAGES}
        subprocess.run([sys.executable, os.path.join(SESSION, "tools", "build.py")],
                       check=True, capture_output=True)
        after = {n: digest(os.path.join(SESSION, n)) for n, _, _ in build_mod.PAGES}
        self.assertEqual(before, after)

    def test_checker_passes_on_the_built_pages(self):
        rc = subprocess.run([sys.executable, os.path.join(SESSION, "tools", "check.py")],
                            capture_output=True, text=True)
        self.assertEqual(0, rc.returncode, rc.stdout + rc.stderr)

    def test_nav_links_every_page(self):
        doc = open(os.path.join(SESSION, "index.html"), encoding="utf-8").read()
        for name, _, _ in build_mod.PAGES:
            self.assertIn('href="%s"' % name, doc, name)

    def test_assets_are_referenced_and_present(self):
        doc = open(os.path.join(SESSION, "index.html"), encoding="utf-8").read()
        for asset in ("assets/style.css", "assets/app.js"):
            self.assertIn(asset, doc)
            self.assertTrue(os.path.exists(os.path.join(SESSION, asset)), asset)


class TestStructure(unittest.TestCase):
    """Sections that are opened must be closed; nested sections silently shrink
    each one until a wide table overflows the viewport on a phone."""

    def test_every_opened_section_is_closed(self):
        import re
        for name, _, _ in build_mod.PAGES:
            doc = open(os.path.join(SESSION, name), encoding="utf-8").read()
            self.assertEqual(doc.count("<section>"), doc.count("</section>"), name)

    def test_sections_are_siblings_not_nested(self):
        import re
        for name, _, _ in build_mod.PAGES:
            doc = open(os.path.join(SESSION, name), encoding="utf-8").read()
            main = doc[doc.index("<main>"):doc.index("</main>")]
            depth = 0
            for tok in re.findall(r"<section>|</section>", main):
                depth += 1 if tok == "<section>" else -1
                self.assertLessEqual(depth, 1, "%s: sections nest" % name)

    def test_the_balancer_flattens_a_nested_sequence(self):
        flat = build_mod.balance_sections("<section>a<section>b<section>c")
        self.assertEqual("<section>a</section><section>b</section><section>c</section>", flat)

    def test_the_balancer_leaves_closed_sections_alone(self):
        self.assertEqual("<section>a</section><section>b</section>",
                         build_mod.balance_sections("<section>a</section><section>b</section>"))


class TestFailClosed(unittest.TestCase):
    """The checker must reject a page that publishes a value it cannot source."""

    def _audit(self, body):
        problems, stats = [], {"local_links": 0, "tables": 0, "rows": 0,
                               "sourced_rows": 0, "blank_rows": 0}
        check_mod.audit_html(body, "verification.html", problems, stats)
        return problems

    def test_a_sourced_row_is_accepted(self):
        doc = ('<h1>x</h1><title>x</title><nav aria-current="page"></nav>'
               '<table><tbody><tr><td>24</td>'
               '<td><a href="https://www.nfl.com/standings/">source</a></td>'
               '</tr></tbody></table>')
        self.assertEqual([], self._audit(doc))

    def test_an_explicit_blank_is_accepted(self):
        """A blank still names the source it is blank in, so the table carries a link."""
        doc = ('<h1>x</h1><title>x</title><nav aria-current="page"></nav>'
               '<table><caption>Source: '
               '<a href="https://github.com/sassnarep3-star/Own9/blob/main/data/raw/games.csv">csv</a>'
               '</caption><tbody><tr><td>Opening price</td>'
               '<td><span class="blank">blank - not published</span></td>'
               '</tr></tbody></table>')
        self.assertEqual([], self._audit(doc))

    def test_a_blank_row_is_never_counted_as_sourced(self):
        doc = ('<h1>x</h1><title>x</title><nav aria-current="page"></nav>'
               '<table><caption>Source: '
               '<a href="https://www.nfl.com/standings/">nfl</a></caption><tbody>'
               '<tr><td>Opening price</td>'
               '<td><span class="blank">blank - not published</span></td></tr>'
               '</tbody></table>')
        problems, stats = [], {"local_links": 0, "tables": 0, "rows": 0,
                               "sourced_rows": 0, "blank_rows": 0}
        check_mod.audit_html(doc, "results.html", problems, stats)
        self.assertEqual([], problems)
        self.assertEqual(0, stats["sourced_rows"])
        self.assertEqual(1, stats["blank_rows"])

    def test_an_unsourced_table_is_rejected(self):
        doc = ('<h1>x</h1><title>x</title><nav aria-current="page"></nav>'
               '<table><tbody><tr><td>Model fair line</td><td>-3.5</td>'
               '</tr></tbody></table>')
        problems = self._audit(doc)
        self.assertTrue(any("no official source link" in p for p in problems))

    def test_a_missing_heading_is_rejected(self):
        doc = '<title>x</title><nav aria-current="page"></nav>'
        self.assertTrue(any("<h1>" in p for p in self._audit(doc)))

    def test_a_broken_local_link_is_rejected(self):
        doc = ('<h1>x</h1><title>x</title><nav aria-current="page"></nav>'
               '<a href="does-not-exist.html">nope</a>')
        self.assertTrue(any("broken local link" in p for p in self._audit(doc)))


class TestNoInvention(unittest.TestCase):
    def test_blank_labels_render_where_values_are_absent(self):
        doc = open(os.path.join(SESSION, "results.html"), encoding="utf-8").read()
        self.assertIn("blank — not published", doc)
        self.assertIn("needs a fair line", doc)

    def test_no_page_prints_a_fair_line_number(self):
        """The fair-line column must stay empty until a model exists."""
        doc = open(os.path.join(SESSION, "results.html"), encoding="utf-8").read()
        self.assertNotIn(">fair<", doc)

    def test_injury_blanks_are_labelled_not_filled(self):
        doc = open(os.path.join(SESSION, "injuries.html"), encoding="utf-8").read()
        self.assertIn("blank \u2014 not published", doc)


if __name__ == "__main__":
    unittest.main()
