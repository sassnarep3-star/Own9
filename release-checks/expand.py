#!/usr/bin/env python3
"""Read-only technical handoff for the research subsite added after our baseline.

Preserve only row locations/URLs, not unverified NFL numerical outputs.
"""
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.parse import urlsplit
from audit import audit

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / 'release-checks'
GITHUB = 'https://github.com/sassnarep3-star/Own9'


def main():
    files = sorted(ROOT.glob('*.html')) + sorted((ROOT / 'research').glob('*.html'))
    report = audit(ROOT, files)
    paths = [str(p.relative_to(ROOT)) for p in files]
    if subprocess.check_output(['git', 'status', '--porcelain', '--', *paths], cwd=ROOT, text=True).strip():
        raise SystemExit('Audited source pages have uncommitted changes; commit them before pinning evidence URLs.')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    locations = []
    for page in report['pages']:
        for number, row in enumerate(page['rows'], 1):
            if not row['sources']:
                external = [u for u in row['links'] if urlsplit(u).scheme == 'https' and urlsplit(u).hostname]
                locations.append({'path': page['path'], 'row': number, 'line': row['line'],
                                  'links': row['links'],
                                  'classification': 'outside narrow contextual registry' if external else 'no HTTPS source link in row'})
    counts = Counter(f['code'] for f in report['findings'])
    broken = [f for f in report['findings'] if f['code'] in {'missing-target', 'missing-fragment', 'outside-site', 'invalid-url'}]
    snapshot = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'source_commit': commit,
                'scope': 'Root HTML and research/*.html only; not every file in the repository',
                'files': [{'path': p['path'], 'sha256': p['sha256']} for p in report['pages']],
                'finding_counts': dict(counts), 'local_target_failures': broken,
                'rows_needing_source_policy_review': locations,
                'limitation': 'Registry failures do not establish that a URL is broken or unofficial. No external source claim verification. No unverified NFL numerical values reproduced.'}
    (HERE / 'expanded-snapshot.json').write_text(json.dumps(snapshot, indent=2) + '\n')
    base = f'{GITHUB}/blob/{commit}/'
    def link(url, text):
        return f'<a href="{escape(url, quote=True)}">{escape(text)}</a>'
    def table(headers, rows):
        return '<div class="scroll"><table><thead><tr>' + ''.join(f'<th scope="col">{escape(h)}</th>' for h in headers) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in row) + '</tr>' for row in rows) + '</tbody></table></div>'
    rows = [
        ['Local targets / fragments', str(len(broken)), 'No target failures detected in this bounded static scan; this is not a browser or HTTP test.', link(GITHUB + '/tree/' + commit, 'Audited source tree')],
        ['Source-registry gate', str(counts['row-no-source']), 'Review required. Counts include unknown official domains, secondary dataset links and rows without links. Do not treat this as a count of broken links or factual errors.', link(GITHUB + '/blob/main/release-checks/audit.py', 'Narrow checker policy')],
        ['Rows without any HTTPS citation', str(sum(r['classification'] == 'no HTTPS source link in row' for r in locations)), 'Each must gain a directly supporting official citation or remain blank and explicitly unverified, per the user requirement.', link(base + 'research/sources.html#L22', 'Example source-free table')],
        ['Unnamed navigation landmarks', str(counts['unnamed-nav']), 'Basic accessibility warning; does not establish full accessibility compliance or failure.', link(base + 'research/index.html#L13', 'Navigation example')],
        ['Verified-only presentation', '', 'Needs owner review: research/correlations.html displays numerical outputs while labeling inputs unverified. The user requested blank values until official confirmation. This audit does not certify those outputs and does not repeat them.', link(base + 'research/correlations.html#L19', 'Source status and output table')],
    ]
    content = '<h1>Flagged for Review: expanded site</h1><p>A separate dated handoff for the research subsite added after the original five-page audit. The original frozen audit is not a certification of these newer pages.</p>'
    content += '<p>Checked ' + escape(snapshot['checked_at_utc']) + ' at ' + link(GITHUB + '/tree/' + commit, commit[:12]) + '. ' + link('expanded-snapshot.json', 'Machine-readable locations and URLs') + '.</p>'
    content += table(['Check', 'Count / value', 'Interpretation', 'Official project evidence'], rows)
    content += '<h2>Rows requiring source-policy review</h2><p>Only row locations and URLs are retained here; no unverified NFL numerical result is copied. An unrecognized official source must be evaluated and added explicitly; secondary datasets cannot simply be promoted to verified official outcomes.</p>'
    content += table(['Location', 'Reason', 'URLs present (not endorsed)', 'Official project source'], [
        [escape(f'{r["path"]} · row {r["row"]} · line {r["line"]}'), escape(r['classification']),
         '<br>'.join(link(u, u) for u in r['links']), link(base + r['path'] + '#L' + str(r['line']), 'Original row')]
        for r in locations])
    content += '<h2>Owner handoff</h2><p>Research files are owned by the research session. This session has not changed them. Required follow-up: satisfy official-source/blank-value policy, add source links to every dataset-summary row, name navigation landmarks and retain missingness flags. These review items do not block publication.</p>'
    html = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Expanded site review · Own9</title><style>body{font:16px/1.6 system-ui,sans-serif;color:#1b3042;background:#f6f8fa;margin:0}main,nav{max-width:1200px;margin:auto;padding:24px}h1{font-size:2.4rem;line-height:1.15}a{color:#006d68;overflow-wrap:anywhere}.scroll{overflow-x:auto;background:white;border:1px solid #dce4eb;margin:24px 0}table{width:100%;border-collapse:collapse;text-align:left;font-size:.85rem}td,th{padding:14px;border-bottom:1px solid #e3e9ee;vertical-align:top;min-width:150px}th{background:#edf3f5}nav{display:flex;gap:24px;flex-wrap:wrap}</style></head><body><nav aria-label="Review navigation"><a href="../index.html">Own9 overview</a><a href="index.html">Original release audit</a><a href="../research/flagged.html">Research flagged items</a></nav><main>' + content + '</main></body></html>'
    (HERE / 'expanded-review.html').write_text(html)
    print(f'{len(files)} bounded pages; {len(broken)} broken targets; {len(locations)} source-policy rows; {counts["unnamed-nav"]} navigation warnings.')


if __name__ == '__main__':
    main()
