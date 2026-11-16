#!/usr/bin/env python3
"""Generate review-23b64c60/index.html (repo review, isolated session output).

Counts are measured from the git index at build time. Live official-source
observations are copied from the fetch record below (retrieved 2026-11-16 with
the fetch tool) and are labelled as observations, not as database facts.
Run from the repository root:  python3 review-23b64c60/build.py
"""
import collections
import html
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = pathlib.Path(__file__).resolve().parent / "index.html"
RETRIEVED = "2026-11-16"


def tracked() -> list[str]:
    return subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.split()


def inventory(files: list[str]):
    html_by_tree = collections.Counter()
    for f in files:
        if f.endswith(".html"):
            top = f.split("/", 1)[0] if "/" in f else "(repo root)"
            html_by_tree[top] += 1
    return html_by_tree


def esc(s) -> str:
    return html.escape(str(s), quote=True)


LIVE_CHECKS = [
    # (claim, repo location, official URL, live observation, result)
    (
        "Lions: Kerby Joseph (S, Knee) Out",
        "evidence/availability/injury-report-2026-week-10.json (DET rows)",
        "https://www.nfl.com/injuries/",
        "Week 10 DET table: Kerby Joseph, S, Knee, Did Not Participate In Practice, Out",
        "Match (retired flag VR-08 for this row)",
    ),
    (
        "Lions: Cade Mays (C, Ankle) Out",
        "evidence/availability/injury-report-2026-week-10.json (DET rows)",
        "https://www.nfl.com/injuries/",
        "Week 10 DET table: Cade Mays, C, Ankle, Did Not Participate In Practice, Out",
        "Match (retired flag VR-08 for this row)",
    ),
    (
        "Lions: D.J. Reed (CB, Hip) Out",
        "evidence/availability/injury-report-2026-week-10.json (DET rows)",
        "https://www.nfl.com/injuries/",
        "Week 10 DET table: D.J. Reed, CB, Hip, Did Not Participate In Practice, Out",
        "Match (retired flag VR-08 for this row)",
    ),
    (
        "Commanders: Lucas Patrick (C, Concussion) Out",
        "evidence/availability/injury-report-2026-week-10.json (WAS rows)",
        "https://www.nfl.com/injuries/",
        "Week 10 WAS table: Lucas Patrick, C, Concussion, Did Not Participate In Practice, Out",
        "Match",
    ),
    (
        "Commanders: Colson Yankoff (TE, Knee) Out",
        "evidence/availability/injury-report-2026-week-10.json (WAS rows)",
        "https://www.nfl.com/injuries/",
        "Week 10 WAS table: Colson Yankoff, TE, Knee, Did Not Participate In Practice, Out",
        "Match",
    ),
    (
        "Giants: Malik Harrison (LB, Groin) Questionable",
        "Not in the committed evidence excerpt (it holds two club tables only)",
        "https://www.nfl.com/injuries/",
        "Week 10 NYG table: Malik Harrison, LB, Groin, Limited Participation in Practice, Questionable",
        "Live value observed; repo has no row to compare, so it is not verified against the repo",
    ),
    (
        "Commanders 24, Giants 21, FINAL, Thu Nov 12 2026",
        "evidence/sources.json id nfl-schedule-w10; results feed",
        "https://www.nfl.com/schedules/2026/by-week/week-10",
        "Headline: Commanders 24, Giants 21, FINAL, Thursday, November 12th",
        "Match",
    ),
]

RETIRED_OR_CHANGED = [
    "VR-08 (Lions game-status cells blank) is stale: the committed evidence and the live NFL page both show Out for Joseph, Mays and Reed.",
]

IRREGULARITIES = [
    (
        "Identifier gap",
        "The VR-, VQ- and SG- identifiers cited in the review brief (for example VR-17, VR-26, VQ-07, VR-24, VR-25, VQ-05, SG-03, SG-05) appear nowhere in the repository (0 matches on a full-text search of tracked files). They cannot be traced to a register, so none of those cited items is verified here.",
        "Repository search, this session. Request: the owner should publish the VR/VQ/SG register or its file location.",
    ),
    (
        "Week 10 snapshot described as 'full'",
        "README.md describes injuries.html as 'the full Week 10 2026 injury report snapshot'. injuries.html shows 'players with an explicit Game Status' only, and the committed evidence file is a two-club excerpt (18 observations: WAS 9, DET 9) whose rights_note says it is 'not a republication of the full league report'.",
        "evidence/availability/injury-report-2026-week-10.json (rights_note); injuries.html section heading; https://www.nfl.com/injuries/",
    ),
    (
        "Row counts (254 vs 279) not re-verified",
        "The live NFL injury page is served in 8 chunks. This review read chunk 0 only (WAS, NYG, NE, DET, and part of KC). The 254 vs 279 row counts and the 4 vs 2 'no injury' sections were NOT re-counted, so VR-04 to VR-07 remain unverified.",
        "https://www.nfl.com/injuries/",
    ),
    (
        "README counts stale",
        "README says 'Nineteen pages' and '105 Python tests'. This session measured 39 root HTML pages and 282 passing root unit tests (python3 -m unittest discover -s tests). The committed README numbers do not match the tree.",
        "README.md; tests/ (run output recorded below)",
    ),
    (
        "Parallel publication trees",
        "Ten HTML trees publish overlapping content (root, origination/, site/, research/, own9-research/, strict-lab/, independent-audit/, release-checks/, session-00cf851d/, session-8b05dd6d/). Two implementations of the same eight requirements already exist (noted on the board as Q-21 / OD-16). Duplicate pages can disagree.",
        "Measured in the inventory below; COORDINATION.md (session 2c3cef39 completion record).",
    ),
    (
        "Coordination board size and branch naming",
        "COORDINATION.md is about 220 KB across 64 sections, and the board prescribes session-<id>/<task> branches, which the environment does not allow for this session. This session uses only arena/23b64c60-own9.",
        "COORDINATION.md; environment branch rule.",
    ),
    (
        "Data licence unknown",
        "data/raw/*.csv have no licence or provenance on record (OD-01 on the board). Scores were matched to the official NFL publisher; the right to use the files was not established.",
        "COORDINATION.md (session 2c3cef39, open item 2).",
    ),
    (
        "No opening prices",
        "The price-snapshot contract (data/snapshots/CONTRACT.md) is header-only. No opening or closing quote with provenance is committed, so no closing-line value or executable ROI can be computed.",
        "data/snapshots/CONTRACT.md; price-snapshots.html.",
    ),
]

BASELINE = [
    ("python3 -m unittest discover -s tests", "Ran 282 tests: OK"),
    ("python3 tools/verify.py", "PASS: 39 fresh pages; 1755 source-linked rows; local assets/fragments"),
    ("python3 scripts/check_site.py", "PASS: 15 pages, 147 data rows with direct official-source links, 551 links checked"),
    ("python3 tools/build.py, scripts/build_site.py, research/make_catalog.py", "Exit 0, no git diff: outputs reproduce from source"),
    ("origination: run.py, build.py, verify.py, unittest", "PASS: 12 pages, 442 source-linked rows; Ran 38 tests: OK"),
]


def table(headers, rows) -> str:
    head = "".join(f"<th scope='col'>{esc(h)}</th>" for h in headers)
    body = []
    for r in rows:
        cells = []
        for c in r:
            cells.append(f"<td>{c}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    return f"<div class='tw'><table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"


def link(url: str) -> str:
    return f"<a href='{esc(url)}' rel='noopener'>{esc(url)}</a>"


def main() -> None:
    files = tracked()
    inv = inventory(files)
    total_html = sum(inv.values())
    inv_rows = [(k, str(v)) for k, v in sorted(inv.items(), key=lambda kv: (-kv[1], kv[0]))]
    inv_rows.append(("All HTML pages", str(total_html)))
    inv_rows.append(("All tracked files", str(len(files))))

    live_rows = [
        (esc(a), esc(b), link(c), esc(d), esc(e)) for a, b, c, d, e in LIVE_CHECKS
    ]
    irr_rows = [(esc(a), esc(b), esc(c)) for a, b, c in IRREGULARITIES]
    base_rows = [(esc(a), esc(b)) for a, b in BASELINE]

    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Repo review · Own9 (session 23b64c60)</title>
<style>
body{{font:16px/1.5 system-ui,-apple-system,Segoe UI,sans-serif;margin:0;color:#1d2330;background:#f6f7f9}}
header,main{{max-width:1100px;margin:0 auto;padding:18px}}
header{{background:#14213d;color:#fff}}
h1{{margin:0;font-size:1.6rem}} h2{{margin-top:2rem;border-bottom:2px solid #d9dde5;padding-bottom:4px}}
.card{{background:#fff;border:1px solid #d9dde5;border-radius:8px;padding:14px 18px}}
.tw{{overflow-x:auto}}
table{{border-collapse:collapse;width:100%;background:#fff;font-size:.92rem}}
th,td{{border:1px solid #d9dde5;padding:6px 8px;text-align:left;vertical-align:top}}
th{{background:#eef1f6}}
.flag{{color:#8a3b00;font-weight:600}}
nav a{{color:#fff;margin-right:14px}}
</style>
</head>
<body>
<header>
<h1>Repo review · Own9</h1>
<p>Session 23b64c60 · branch <code>arena/23b64c60-own9</code> · observations dated {RETRIEVED}</p>
<nav><a href='../index.html'>Dashboard</a><a href='../flags.html'>Flagged for Review</a><a href='../sources.html'>Sources</a></nav>
</header>
<main>

<h2>Executive summary</h2>
<div class='card'>
<ul>
<li><strong>The committed build is reproducible.</strong> Every generator re-runs with no diff, and the root test suite (282 tests), the root verifier, the link checker and the origination desk (38 tests) all pass on this branch.</li>
<li><strong>Live spot checks agree with the repo on all 5 Week 10 injury rows that have a repo counterpart, and on the Week 10 final score. A sixth live row (Giants) has no repo counterpart.</strong> The NFL injury page showing Joseph, Mays and D.J. Reed as Out means flag VR-08 is out of date. The Giants row was observed live but has no repo counterpart to compare.</li>
<li><strong>The repo overstates two things.</strong> The README calls the Week 10 Injury page 'full', but it is a filtered subset of an 18-observation two-club excerpt. README counts (19 pages, 105 tests) do not match the tree (39 root HTML pages, 282 tests).</li>
<li><strong>Most of the brief cannot be verified from this repo.</strong> The VR/VQ/SG identifiers are not in the repository, the full 32-club injury history is absent, there are no opening prices, and the data licence is unknown. Those items stay blank or unverified; none is filled in here.</li>
<li><strong>Nothing here is a betting recommendation.</strong> No strategy has passed a validation gate, and this review does not establish any edge, correlation or ROI.</li>
</ul>
</div>

<h2>1 · Inventory (measured at build time from git ls-files)</h2>
<p>Counts come from the git index, not from memory. The HTML pages are spread across ten publication trees, which is the main structural risk to a single source of truth.</p>
{table(['Tree', 'HTML pages'], inv_rows)}

<h2>2 · Baseline checks run on this branch</h2>
<p>Recorded from this session's runs. Re-running them regenerates the same results because the outputs are deterministic.</p>
{table(['Command', 'Result'], base_rows)}

<h2>3 · Live official-source spot check ({RETRIEVED})</h2>
<p>Each row names the repo claim, its committed location, the official page, the live observation, and the result. <strong>Only the rows listed here were checked</strong>; the remaining Week 10 rows are not verified by this review.</p>
{table(['Claim', 'Repo location', 'Official source', 'Live observation', 'Result'], live_rows)}
<p>{'<br>'.join(esc(x) for x in RETIRED_OR_CHANGED)}</p>

<h2>4 · Irregularities flagged for review</h2>
<p class='flag'>These do not block anything and are not repaired here. Each entry has its source.</p>
{table(['Item', 'Finding', 'Source / where to check'], irr_rows)}

<h2>5 · Unverified items (left blank, not inferred)</h2>
<ul>
<li>Full Week 10 injury row count (254 vs 279) and the sections with no injuries (4 vs 2): not re-counted; see the flag above.</li>
<li>The VR-, VQ- and SG- items in the brief: no register in the repo, so no source can be checked.</li>
<li>Any opening price, any closing-line value, any executable ROI: no source committed.</li>
<li>Injury-report history by week beyond the single Week 10 excerpt; no multi-day snapshot store with raw hashes is committed.</li>
</ul>

<h2>6 · Requests for the integration owner (not edited in this session)</h2>
<ul>
<li>Link this page from <code>flags.html</code> (Flagged for Review) and from the root navigation.</li>
<li>Correct the README counts and the 'full Week 10 snapshot' wording, or label them as the excerpt they are.</li>
<li>Publish or locate the VR/VQ/SG register, or confirm those identifiers were never committed.</li>
</ul>

<h2>7 · Manual review links</h2>
<ul>
<li><a href='https://www.nfl.com/injuries/'>NFL injury report, Week 10 2026</a></li>
<li><a href='https://www.nfl.com/schedules/2026/by-week/week-10'>NFL schedule, Week 10 2026</a></li>
<li><a href='https://github.com/sassnarep3-star/Own9/blob/main/COORDINATION.md'>COORDINATION.md on main</a></li>
</ul>

<p class='card'>Generated by <code>review-23b64c60/build.py</code>. This page is an observation log for {RETRIEVED}. It is not a certification of any claim in the repository.</p>
</main>
</body>
</html>
"""
    OUT.write_text(doc, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {total_html} HTML pages measured, {len(files)} tracked files")


if __name__ == "__main__":
    main()
