"""Synthetic HTML fixtures only. These tests contain no NFL observations."""
import tempfile
import unittest
from pathlib import Path
from audit import Page, audit, contextual_source


SOURCE = 'https://www.nfl.com/stats/'


def document(body='', lang='en'):
    return f'''<!doctype html><html lang="{lang}"><head><title>Fixture</title>
    <meta name="viewport" content="width=device-width"></head><body>
    <nav aria-label="Main"><a href="index.html">Home</a></nav><main><h1>Fixture</h1>{body}</main></body></html>'''


class ReleaseAuditTests(unittest.TestCase):
    def run_fixture(self, body='', extra=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'index.html').write_text(document(body))
            for name, content in (extra or {}).items():
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                (root / name).write_text(content)
            return audit(root)

    def codes(self, result):
        return {finding['code'] for finding in result['findings']}

    def test_minimum_document_passes(self):
        self.assertEqual(self.run_fixture()['errors'], 0)

    def test_empty_site_fails(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertIn('no-pages', self.codes(audit(root)))

    def test_local_asset_and_query(self):
        result = self.run_fixture('<link rel="stylesheet" href="style.css?v=2">', {'style.css': 'body{}'})
        self.assertEqual(result['errors'], 0)

    def test_missing_asset_fails(self):
        self.assertIn('missing-target', self.codes(self.run_fixture('<script src="absent.js"></script>')))

    def test_valid_same_page_fragment(self):
        self.assertEqual(self.run_fixture('<p id="goal">Target</p><a href="#goal">Go</a>')['errors'], 0)

    def test_missing_fragment_fails(self):
        self.assertIn('missing-fragment', self.codes(self.run_fixture('<a href="#absent">Go</a>')))

    def test_fragment_in_other_page(self):
        result = self.run_fixture('<a href="other.html#goal">Go</a>', {'other.html': document('<p id="goal">Target</p>')})
        self.assertEqual(result['errors'], 0)

    def test_directory_index(self):
        result = self.run_fixture('<a href="sub/">Go</a>', {'sub/index.html': document()})
        self.assertEqual(result['errors'], 0)

    def test_duplicate_ids_fail(self):
        self.assertIn('duplicate-id', self.codes(self.run_fixture('<p id="a"></p><p id="a"></p>')))

    def test_project_root_url_fails(self):
        self.assertIn('project-root-link', self.codes(self.run_fixture('<a href="/Own9/">Go</a>')))

    def test_encoded_traversal_fails(self):
        self.assertIn('outside-site', self.codes(self.run_fixture('<a href="%2e%2e/outside.html">Go</a>')))

    def test_empty_link_fails(self):
        self.assertIn('empty-link', self.codes(self.run_fixture('<a href="">Go</a>')))

    def test_unsafe_scheme_fails(self):
        self.assertIn('unsafe-scheme', self.codes(self.run_fixture('<a href="javascript:alert(1)">Go</a>')))

    def test_missing_alt_fails(self):
        result = self.run_fixture('<img src="image.svg">', {'image.svg': '<svg/>'})
        self.assertIn('missing-alt', self.codes(result))

    def test_source_does_not_verify_claim(self):
        result = self.run_fixture(f'<table><tr><th>Claim</th></tr><tr><td>Unvalidated idea <a href="{SOURCE}">Context</a></td></tr></table>')
        self.assertEqual(result['errors'], 0)
        self.assertEqual(result['rows_with_claim_support_unverified'], 1)
        self.assertEqual(result['pages'][0]['rows'][0]['claim_support'], 'unverified; link presence only')

    def test_missing_row_source_fails(self):
        result = self.run_fixture('<table><tr><th>Claim</th></tr><tr><td>Missing source</td></tr></table>')
        self.assertIn('row-no-source', self.codes(result))

    def test_headers_required(self):
        result = self.run_fixture(f'<table><tr><td><a href="{SOURCE}">Context</a></td></tr></table>')
        self.assertIn('table-no-headers', self.codes(result))

    def test_only_exact_source_domains_and_repositories(self):
        for url in [SOURCE, 'https://github.com/sassnarep3-star/Own9/blob/main/index.html',
                    'https://docs.github.com/en/pages/']:
            self.assertTrue(contextual_source(url), url)
        for url in ['https://www.nfl.com.evil.test/stats/', 'https://www.nfl.com@evil.test/',
                    'http://www.nfl.com/stats/', 'https://github.com/random/unreviewed',
                    'https://www.nfl.com:444/stats/', 'https://www.nfl.com:invalid/']:
            self.assertFalse(contextual_source(url), url)

    def test_missing_landmarks_and_language_fail(self):
        page = Page('<html><title></title><p>No landmarks</p></html>')
        codes = {f['code'] for f in page.findings}
        self.assertTrue({'missing-language', 'missing-title', 'missing-viewport', 'heading-count',
                         'main-count', 'missing-nav'}.issubset(codes))

    def test_named_navigation_warning(self):
        page = Page(document().replace('aria-label="Main"', ''))
        self.assertTrue(any(f['code'] == 'unnamed-nav' and f['severity'] == 'warning' for f in page.findings))

    def test_snapshot_changes_with_content(self):
        self.assertNotEqual(self.run_fixture()['pages'][0]['sha256'],
                            self.run_fixture('<p>Changed</p>')['pages'][0]['sha256'])


if __name__ == '__main__':
    unittest.main()
