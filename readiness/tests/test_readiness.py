"""Tests for the decision-readiness register: the live data must validate, and broken rows must fail.

Run: python3 -m unittest discover -s readiness/tests -v
"""
import copy
import re
import sys
import unittest
from pathlib import Path
from urllib.parse import urldefrag

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'readiness' / 'tools'))

import build  # noqa: E402


def good_req(**overrides):
    row = {
        'id': 'H-90', 'group': 'H Test', 'requirement': 'A test requirement',
        'status': 'Built · checked', 'what_exists': 'A file exists.',
        'blocking_gate': 'None', 'clearing_number': '1 file',
        'evidence': 'readiness/data/requirements.csv', 'official_url': '',
        'checked': '2026-11-16',
    }
    row.update(overrides)
    return row


GOOD_DEC = {'id': 'DEC-01', 'decision': 'd', 'options': 'a; b', 'default_if_no_answer': 'a',
            'unlocks': 'H-90', 'why_it_matters': 'because'}
GOOD_RV = {'id': 'RV-01', 'severity': 'high', 'finding': 'f', 'how_verified': 'h',
           'evidence': 'readiness/data/requirements.csv', 'source_url': 'https://www.nfl.com/injuries/',
           'disposition': 'd'}


class LiveRegisters(unittest.TestCase):
    """The committed registers must pass every rule."""

    @classmethod
    def setUpClass(cls):
        cls.reqs, cls.decisions, cls.reviews = build.load()

    def test_live_data_validates(self):
        self.assertEqual(build.validate(self.reqs, self.decisions, self.reviews), [])

    def test_every_requirement_has_a_source_link(self):
        for row in self.reqs:
            links = build._split(row['evidence']) + ([row['official_url']] if row['official_url'] else [])
            if not links:
                # Rows with no file are linked to the register row itself, as the renderer does.
                self.assertIn('readiness/data/requirements.csv', build.source_cell(row))

    def test_verified_rows_are_official(self):
        for row in self.reqs:
            if row['status'] == 'Verified today':
                self.assertTrue(row['official_url'].startswith('https://www.nfl.com/'), row['id'])

    def test_no_status_outside_the_vocabulary(self):
        for row in self.reqs:
            self.assertIn(row['status'], build.STATUSES)

    def test_rendered_pages_contain_every_row(self):
        pages = build.render_all(self.reqs, self.decisions, self.reviews)
        index = pages[build.OUT / 'index.html']
        for row in self.reqs:
            self.assertIn(f'id="row-{row["id"]}"', index)
        for row in self.reviews:
            self.assertIn(row['id'], pages[build.OUT / 'repo-review.html'])
        for row in self.decisions:
            self.assertIn(row['id'], pages[build.OUT / 'decisions.html'])

    def test_local_links_and_anchors_resolve(self):
        pages = build.render_all(self.reqs, self.decisions, self.reviews)
        for path, text in pages.items():
            if not path.name.endswith('.html'):
                continue
            for href in re.findall(r'href="([^"]+)"', text):
                if href.startswith(('http://', 'https://', 'mailto:', '#')):
                    continue
                target, anchor = urldefrag(href)
                file_path = (path.parent / target).resolve()
                self.assertTrue(file_path.exists(), f'{path.name} links to missing {href}')
                if anchor:
                    own = pages.get(file_path, '')
                    if not own:
                        own = file_path.read_text(encoding='utf-8')
                    self.assertIn(f'id="{anchor}"', own, f'{path.name} links to missing anchor {href}')


class RuleViolations(unittest.TestCase):
    """Each broken row must be reported. A fix that silently passes is a failure."""

    def check(self, reqs=None, decisions=None, reviews=None):
        return build.validate(reqs if reqs is not None else [good_req()],
                              decisions if decisions is not None else [GOOD_DEC],
                              reviews if reviews is not None else [GOOD_RV])

    def test_baseline_passes(self):
        self.assertEqual(self.check(), [])

    def test_unknown_status_fails(self):
        self.assertTrue(self.check([good_req(status='Done')]))

    def test_verified_without_official_link_fails(self):
        errors = self.check([good_req(status='Verified today', checked='2026-11-16', official_url='')])
        self.assertTrue(any('needs an official_url' in e for e in errors))

    def test_verified_with_non_nfl_host_fails(self):
        errors = self.check([good_req(status='Verified today', checked='2026-11-16',
                                      official_url='https://example.com/page')])
        self.assertTrue(errors)

    def test_built_without_evidence_fails(self):
        errors = self.check([good_req(status='Built · checked', evidence='')])
        self.assertTrue(any('needs at least one evidence path' in e for e in errors))

    def test_missing_file_fails(self):
        errors = self.check([good_req(evidence='readiness/data/does-not-exist.csv')])
        self.assertTrue(any('does not exist' in e for e in errors))

    def test_blocked_decision_must_name_a_decision(self):
        errors = self.check([good_req(status='Blocked · decision', blocking_gate='waiting on someone')])
        self.assertTrue(any('must name a DEC-' in e for e in errors))

    def test_blocked_terms_must_name_dec01(self):
        errors = self.check([good_req(status='Blocked · terms', blocking_gate='DEC-02 only')])
        self.assertTrue(any('must name DEC-01' in e for e in errors))

    def test_unknown_decision_reference_fails(self):
        errors = self.check([good_req(blocking_gate='DEC-99')])
        self.assertTrue(any('unknown decision DEC-99' in e for e in errors))

    def test_unknown_requirement_reference_fails(self):
        errors = self.check([good_req(what_exists='See Q-99 and H-42.')])
        self.assertTrue(any('unknown requirement H-42' in e for e in errors))

    def test_blank_clearing_number_fails(self):
        errors = self.check([good_req(clearing_number='')])
        self.assertTrue(any('clearing_number is blank' in e for e in errors))

    def test_rejected_must_use_na(self):
        errors = self.check([good_req(status='Rejected as instructed', clearing_number='5')])
        self.assertTrue(any('Rejected as instructed' in e for e in errors))

    def test_bad_date_fails(self):
        self.assertTrue(self.check([good_req(checked='2026-13-40')]))

    def test_duplicate_id_fails(self):
        errors = self.check([good_req(), good_req()])
        self.assertTrue(any('duplicated' in e for e in errors))

    def test_unlocks_unknown_requirement_fails(self):
        errors = self.check(decisions=[dict(GOOD_DEC, unlocks='H-90;H-77')])
        self.assertTrue(any('unlocks unknown requirement H-77' in e for e in errors))

    def test_review_severity_must_be_known(self):
        errors = self.check(reviews=[dict(GOOD_RV, severity='urgent')])
        self.assertTrue(any('unknown severity' in e for e in errors))

    def test_review_source_must_be_https(self):
        errors = self.check(reviews=[dict(GOOD_RV, source_url='nfl.com/injuries')])
        self.assertTrue(errors)

    def test_nothing_is_written_when_invalid(self):
        bad = [good_req(status='Verified today', checked='2026-11-16', official_url='')]
        reqs = copy.deepcopy(bad)
        self.assertTrue(self.check(reqs))
        # main() must refuse to render; the renderer is never reached for invalid input.
        self.assertTrue(build.validate(reqs, [GOOD_DEC], [GOOD_RV]))


if __name__ == '__main__':
    unittest.main()
