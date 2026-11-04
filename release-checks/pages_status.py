#!/usr/bin/env python3
"""Capture public GitHub Pages metadata through gh; never capture credentials.

A successful build is NOT an HTTP/browser smoke test. Commit equality is required
when --expected-commit is supplied, so an older deployment cannot pass as current.
"""
import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = 'sassnarep3-star/Own9'


def summarize(site, build, expected_commit=None, workflow_run=None):
    same_commit = build.get('commit') == expected_commit if expected_commit else None
    success = site.get('status') == 'built' and build.get('status') == 'built'
    if expected_commit:
        success = success and same_commit
    run = workflow_run or {}
    deployment_success = (bool(success) and run.get('head_sha') == build.get('commit')
                          and run.get('status') == 'completed' and run.get('conclusion') == 'success')
    return {
        'repository': REPO,
        'site_url': site.get('html_url'),
        'site_status': site.get('status'),
        'source': site.get('source'),
        'build_type': site.get('build_type'),
        'build_status': build.get('status'),
        'build_commit': build.get('commit'),
        'build_created_at': build.get('created_at'),
        'build_updated_at': build.get('updated_at'),
        'build_api_url': build.get('url'),
        'build_error': (build.get('error') or {}).get('message'),
        'expected_commit': expected_commit,
        'expected_commit_matches': same_commit,
        'metadata_checks_pass': bool(success),
        'deployment_workflow_success': deployment_success,
        'workflow_run_url': run.get('html_url'),
        'workflow_status': run.get('status'),
        'workflow_conclusion': run.get('conclusion'),
        'http_content_verified': False,
        'limitation': 'GitHub API metadata only. HTTP response, page content and browser behavior are not checked.',
        'sources': [f'https://api.github.com/repos/{REPO}/pages',
                    f'https://api.github.com/repos/{REPO}/pages/builds/latest',
                    'https://docs.github.com/en/rest/pages/pages#get-the-latest-pages-build'],
    }


def api(endpoint):
    result = subprocess.run(['gh', 'api', endpoint], check=True, text=True, capture_output=True)
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-commit')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        site = api(f'repos/{REPO}/pages')
        build = api(f'repos/{REPO}/pages/builds/latest')
        runs = api(f'repos/{REPO}/actions/runs?head_sha={build.get("commit", "")}&per_page=30')
        # This repository currently uses GitHub's managed legacy Pages workflow.
        # Do not mistake an unrelated successful CI workflow for a Pages deployment.
        run = next((r for r in runs.get('workflow_runs', [])
                    if r.get('path') == 'dynamic/pages/pages-build-deployment'), None)
        report = summarize(site, build, args.expected_commit, run)
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as exc:
        # Do not dump subprocess stdout/stderr: this tool persists only public fields.
        print(f'Unable to read Pages metadata ({type(exc).__name__}); deployment remains unverified.')
        return 2
    report['checked_at_utc'] = datetime.now(timezone.utc).isoformat()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0 if report['metadata_checks_pass'] and report['deployment_workflow_success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
