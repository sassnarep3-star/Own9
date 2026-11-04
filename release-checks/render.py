#!/usr/bin/env python3
"""Render a dated, explicitly limited release audit. No external facts inferred."""
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
GITHUB = 'https://github.com/sassnarep3-star/Own9'
DOCS = 'https://docs.github.com/en/rest/pages/pages'


def anchor(url, text):
    return f'<a href="{escape(url, quote=True)}">{escape(text)}</a>'


def table(headers, rows):
    return '<div class="scroll"><table><thead><tr>' + ''.join(
        f'<th scope="col">{escape(h)}</th>' for h in headers
    ) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in row) + '</tr>' for row in rows) + '</tbody></table></div>'


def main():
    audit = json.loads((HERE / 'audit-snapshot.json').read_text())
    # Do not publish a snapshot as current if its audited source files changed.
    for page in audit['pages']:
        actual_hash = hashlib.sha256((ROOT / page['path']).read_bytes()).hexdigest()
        if actual_hash != page['sha256']:
            raise SystemExit(f'Stale audit: {page["path"]} changed. Run audit.py again.')
    pages_path = HERE / 'pages-snapshot.json'
    pages = json.loads(pages_path.read_text()) if pages_path.exists() else None
    result = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', str(HERE), '-p', 'test_*.py'],
                            cwd=ROOT, text=True, capture_output=True)
    count = re.search(r'Ran (\d+) tests?', result.stderr)
    test = {'checked_at_utc': datetime.now(timezone.utc).isoformat(),
            'count': int(count.group(1)) if count else None,
            'passed': result.returncode == 0 and count is not None,
            'scope': 'synthetic HTML and deployment metadata fixtures only; no observed NFL outcomes'}
    (HERE / 'test-snapshot.json').write_text(json.dumps(test, indent=2) + '\n')
    if not test['passed']:
        raise SystemExit('Fixture tests failed; refusing to publish a passing report.\n' + result.stderr)
    commit = audit['checkout_commit'] or 'main'
    intro = f'''<p class="eyebrow">OWN9 / RELEASE QUALITY</p><h1>Links are not evidence.</h1>
<p class="lead">An independent technical audit of the research dashboard. A valid link can point to a page that does not support its neighboring claim. No NFL strategy is certified by these checks.</p>
<div class="notice"><strong>Flagged for Review — all {audit['rows_with_claim_support_unverified']} audited row claims remain substantively unverified by this checker.</strong> Link presence is a structural test only. Empirical NFL correlations, odds, performance and rewards are not created or verified here.</div>
<p>Frozen source audit: {escape(audit['checked_at_utc'])}. Checkout {anchor(GITHUB + '/tree/' + commit, commit[:12])}. {anchor('audit-snapshot.json', 'Machine-readable audit')} · {anchor('README.md', 'Scope and commands')}.</p>'''
    summary = [
        ['Root HTML pages inspected', str(len(audit['pages'])), 'Local snapshot', anchor(GITHUB + '/tree/' + commit, 'Audited repository')],
        ['Structural errors / warnings', f'{audit["errors"]} / {audit["warnings"]}', 'Limited project-policy checks', anchor(GITHUB + '/blob/main/release-checks/audit.py', 'Checker source')],
        ['Synthetic regression tests', str(test['count']), 'Passed; fixtures are not NFL observations', anchor(GITHUB + '/tree/main/release-checks', 'Test source')],
        ['Verified NFL strategy claims', '', 'Unverified; outside technical checker scope', anchor(GITHUB + '/blob/' + commit + '/leaderboard.html', 'Audited leaderboard')],
    ]
    content = intro
    if (HERE / 'expanded-review.html').exists():
        content += '<div class="notice"><strong>New pages need separate review.</strong> A parallel session subsequently added a research subsite. ' + anchor('expanded-review.html', 'Read expanded-site source-policy findings') + '. The frozen five-page audit below does not certify that later work.</div>'
    content += '<h2>Executive findings</h2>' + table(['Check', 'Value', 'Meaning', 'Official / project source'], summary)
    if pages:
        content += '<h2>GitHub Pages metadata snapshot</h2><p>This is a dated API observation, not a public HTTP or browser test. Later commits may have newer deployments.</p>'
        deployment_rows = [
            ['Site status', escape(pages['site_status'] or ''), escape(pages['checked_at_utc']), anchor(pages['sources'][0], 'Official site API')],
            ['Latest build', escape(pages['build_status'] or ''), escape(pages['build_commit'] or ''), anchor(pages['sources'][1], 'Official build API')],
            ['Expected commit match', 'Yes' if pages['expected_commit_matches'] else '', escape(pages['expected_commit'] or ''), anchor(DOCS, 'API documentation')],
            ['Matching deployment workflow', 'Success' if pages['deployment_workflow_success'] else '', escape(pages['workflow_conclusion'] or 'Unverified'), anchor(pages['workflow_run_url'] or DOCS, 'Official workflow record')],
            ['Public HTTP content', '', 'Not tested by metadata script; requires separate observation', anchor(DOCS, 'Metadata scope')],
        ]
        content += table(['Check', 'Value', 'Detail', 'Official source'], deployment_rows)
    publication_path = HERE / 'publication.json'
    if publication_path.exists():
        publication = json.loads(publication_path.read_text())
        content += '<h2>Publication record and flagged deployment notices</h2><p>Dated observation for the initial release-quality publication, not a promise about future deployments. ' + anchor('publication.json', 'Machine-readable publication record') + '.</p>'
        publication_rows = [
            ['Release-quality PR', escape(publication['pr_state']), escape(publication['merge_commit']), anchor(publication['pr_url'], 'Official pull request')],
            ['Pages deployment', escape(publication['deployment_conclusion']), 'Build and deploy jobs completed successfully', anchor(publication['deployment_url'], 'Official deployment run')],
        ]
        for observation in publication['public_content_observed']:
            publication_rows.append(['Public content observation', anchor(observation['url'], 'Published content'), escape(observation['expected_content_observed']), anchor(publication['pr_url'], 'Published source PR')])
        for notice in publication['nonblocking_annotations']:
            publication_rows.append(['Flagged for Review', 'Nonblocking platform notice', escape(notice), anchor(publication['deployment_url'], 'Official run annotation')])
        content += table(['Item', 'Result', 'Observed detail', 'Official project source'], publication_rows)
        content += '<p>Public content was observed separately using the fetch-page tool, not by the metadata checker. Record saved: ' + escape(publication['http_observation_recorded_at_utc']) + '. This is not a browser, visual or full-site HTTP test.</p>'
    content += '<h2>Files inspected</h2>' + table(['File', 'SHA-256', 'Data rows', 'Official project source'], [
        [escape(p['path']), '<code>' + p['sha256'] + '</code>', str(len(p['rows'])),
         anchor(GITHUB + '/blob/' + commit + '/' + p['path'], 'Audited file')]
        for p in audit['pages']])
    if audit['findings']:
        content += '<h2>Technical findings</h2>' + table(['File / line', 'Severity', 'Finding', 'Official project source'], [
            [escape(f'{f["path"]}:{f["line"]}'), escape(f['severity']), escape(f['detail']),
             anchor(GITHUB + '/blob/' + commit + '/' + f['path'] + '#L' + str(f['line']), 'Audited location')]
            for f in audit['findings']])
    else:
        content += '<p>No failures were detected by the implemented structural checks. This is not a full HTML, accessibility, security, or content-verification pass.</p>'
    inventory = []
    for page in audit['pages']:
        for number, row in enumerate(page['rows'], 1):
            original = anchor(GITHUB + '/blob/' + commit + '/' + page['path'] + '#L' + str(row['line']), 'Original HTML')
            sources = '<br>'.join(anchor(url, url) for url in row['sources'])
            inventory.append([escape(f'{page["path"]} · row {number} · line {row["line"]}'),
                              escape(row['text']), 'Unverified — link presence only', sources + '<br>' + original])
    content += '<h2>Every audited data row</h2><p>Verbatim normalized row text, not endorsed findings. Each row retains the links it actually contained. Original compressed HTML can place several rows on one source line.</p>'
    content += table(['Location', 'Audited row text', 'Claim-support status', 'Original references / official project source'], inventory)
    content += '<h2>Boundaries and sources</h2><p>External link availability and claim entailment were not checked automatically. No numerical value was filled in for missing NFL observations. These checks cannot remove luck, prove a betting edge or fund rewards.</p><ul>'
    for url, text in [
        ('https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages', 'GitHub Pages: static hosting and project URLs'),
        (DOCS, 'Official Pages REST API: metadata and build status'),
        ('https://html.spec.whatwg.org/multipage/links.html#links-created-by-a-and-area-elements', 'WHATWG HTML: hyperlink semantics'),
    ]:
        content += '<li>' + anchor(url, text) + '</li>'
    content += '</ul><p>Official documentation above was read on 2026-11-04. It provides background; it does not independently certify this checker or the research dashboard.</p>'
    html = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Release quality · Own9</title><style>
:root{font:16px/1.6 system-ui,sans-serif;color:#192b3c;background:#f5f7fa}*{box-sizing:border-box}body{margin:0}a{color:#006d68;overflow-wrap:anywhere}header{background:white;border-bottom:1px solid #dce4eb;padding:20px max(22px,calc((100vw - 1200px)/2))}nav{display:flex;gap:22px;flex-wrap:wrap}main{max-width:1244px;margin:auto;padding:48px 22px 80px}h1{font-size:clamp(2.3rem,6vw,4rem);line-height:1.1;letter-spacing:-.04em;margin:12px 0 22px}h2{margin-top:42px}.eyebrow{font-size:.75rem;letter-spacing:.14em;font-weight:800;color:#006d68}.lead{max-width:850px;color:#526578;font-size:1.15rem}.notice{padding:20px;background:#fff4da;border:1px solid #e8cd83;border-radius:10px;margin:28px 0}.scroll{overflow-x:auto;border:1px solid #dce4eb;border-radius:10px;background:white}table{border-collapse:collapse;width:100%;text-align:left;font-size:.84rem}th,td{padding:14px;border-bottom:1px solid #e5ebf0;vertical-align:top;min-width:125px}th{background:#edf3f5;font-size:.75rem}td:nth-child(2){max-width:650px}code{font-size:.72rem;overflow-wrap:anywhere}footer{max-width:1244px;margin:auto;padding:20px 22px;color:#526578}
</style></head><body><header><nav aria-label="Audit navigation"><a href="../index.html">Own9 overview</a><a href="../flags.html">Flagged for Review</a><a href="index.html" aria-current="page">Release quality</a></nav></header><main>''' + content + '</main><footer>Dated technical evidence · Not betting advice · Missing values stay blank</footer></body></html>'
    (HERE / 'index.html').write_text(html, encoding='utf-8')
    print(f'Rendered {len(inventory)} original row records; {test["count"]} synthetic tests passed.')


if __name__ == '__main__':
    main()
