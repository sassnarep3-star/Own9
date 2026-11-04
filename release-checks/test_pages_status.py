"""Synthetic deployment metadata, not observed build results."""
import unittest
from pages_status import summarize


class PagesStatusTests(unittest.TestCase):
    def test_current_success(self):
        report = summarize({'status': 'built'}, {'status': 'built', 'commit': 'abc'}, 'abc')
        self.assertTrue(report['metadata_checks_pass'])
        self.assertFalse(report['http_content_verified'])

    def test_stale_success_fails(self):
        report = summarize({'status': 'built'}, {'status': 'built', 'commit': 'old'}, 'new')
        self.assertFalse(report['metadata_checks_pass'])

    def test_in_progress_fails(self):
        self.assertFalse(summarize({'status': 'built'}, {'status': 'building'})['metadata_checks_pass'])

    def test_site_error_fails(self):
        self.assertFalse(summarize({'status': 'errored'}, {'status': 'built'})['metadata_checks_pass'])

    def test_missing_data_fails(self):
        self.assertFalse(summarize({}, {})['metadata_checks_pass'])

    def test_no_commit_check_is_explicit(self):
        report = summarize({'status': 'built'}, {'status': 'built'})
        self.assertIsNone(report['expected_commit_matches'])

    def test_matching_deployment_required(self):
        site, build = {'status': 'built'}, {'status': 'built', 'commit': 'abc'}
        run = {'head_sha': 'abc', 'status': 'completed', 'conclusion': 'success'}
        self.assertTrue(summarize(site, build, 'abc', run)['deployment_workflow_success'])
        run['head_sha'] = 'old'
        self.assertFalse(summarize(site, build, 'abc', run)['deployment_workflow_success'])

    def test_missing_or_pending_deployment_not_verified(self):
        site, build = {'status': 'built'}, {'status': 'built', 'commit': 'abc'}
        self.assertFalse(summarize(site, build, 'abc')['deployment_workflow_success'])
        run = {'head_sha': 'abc', 'status': 'in_progress', 'conclusion': None}
        self.assertFalse(summarize(site, build, 'abc', run)['deployment_workflow_success'])

    def test_extraneous_personal_data_not_persisted(self):
        report = summarize({'status': 'built', 'secret': 'never store'},
                           {'status': 'built', 'pusher': {'email': 'private'}, 'token': 'never store'})
        self.assertNotIn('pusher', report)
        self.assertNotIn('token', report)
        self.assertNotIn('secret', report)


if __name__ == '__main__':
    unittest.main()
