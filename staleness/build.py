#!/usr/bin/env python3
"""Validate staleness/register.csv and render staleness/index.html.

Fails closed: every row must carry at least one https link on an allowed
official host (NFL.com or the club site), a known status, and a read date.
Rows with status 'Unverified' must leave the official value blank.
Run:  python3 staleness/build.py            (writes index.html)
      python3 staleness/build.py --check    (validates only)
"""
import csv, html, re, sys
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
ALLOWED_HOSTS = {"www.nfl.com", "static.www.nfl.com", "www.baltimoreravens.com"}
STATUSES = {
    "Confirmed: placed on IR", "Confirmed", "Contradicted: repo blank is stale",
    "Confirmed on official club chart; chart has no as-of date",
    "Flagged: trade record and roster code do not reconcile on the page",
    "Flagged: log as served is incomplete",
}
COLUMNS = ["id", "club", "player", "item", "repo_value", "official_value",
           "status", "source_url", "source_note", "date_read_utc"]


def load(path=HERE / "register.csv"):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def validate(rows):
    errors = []
    ids = set()
    for r in rows:
        rid = r.get("id", "?")
        if set(r.keys()) != set(COLUMNS):
            errors.append(f"{rid}: columns {sorted(r.keys())} != {COLUMNS}")
        if rid in ids:
            errors.append(f"{rid}: duplicate id")
        ids.add(rid)
        if r.get("status") not in STATUSES:
            errors.append(f"{rid}: unknown status {r.get('status')!r}")
        urls = [u.strip() for u in (r.get("source_url") or "").split("|") if u.strip()]
        if not urls:
            errors.append(f"{rid}: no source link")
        for u in urls:
            p = urlparse(u)
            if p.scheme != "https" or p.hostname not in ALLOWED_HOSTS:
                errors.append(f"{rid}: source not on an allowed official host: {u}")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", r.get("date_read_utc") or ""):
            errors.append(f"{rid}: missing or malformed date_read_utc")
    return errors


def render(rows):
    def cell(v):
        return html.escape(v or "")

    def links(v):
        out = []
        for u in [x.strip() for x in v.split("|") if x.strip()]:
            out.append(f'<a href="{html.escape(u)}" rel="noopener">{html.escape(urlparse(u).hostname)} ↗</a>')
        return "<br>".join(out)

    body = []
    for r in rows:
        flag = "flag" if r["status"].startswith(("Flagged", "Contradicted")) else ""
        body.append(
            f'<tr class="{flag}"><td>{cell(r["id"])}</td><td>{cell(r["club"])}</td>'
            f'<td>{cell(r["player"])}</td><td>{cell(r["item"])}</td>'
            f'<td>{cell(r["repo_value"])}</td><td>{cell(r["official_value"])}</td>'
            f'<td><strong>{cell(r["status"])}</strong></td>'
            f'<td>{links(r["source_url"])}<br><small>{cell(r["source_note"])}</small></td>'
            f'<td>{cell(r["date_read_utc"])}</td></tr>')
    return PAGE.replace("__ROWS__", "\n".join(body)).replace("__COUNT__", str(len(rows)))


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Baltimore QB depth: stale-row check | Own9</title>
<style>
body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:0;color:#1d2330;background:#f7f8fa;line-height:1.45}
header,main{max-width:1200px;margin:0 auto;padding:18px}
header{padding-bottom:0}
h1{font-size:1.5rem;margin:.2rem 0}
a{color:#0b5cad}
.note{background:#fff;border:1px solid #d9dee7;border-radius:8px;padding:12px 14px;margin:12px 0}
table{width:100%;border-collapse:collapse;background:#fff;font-size:.9rem}
th,td{border:1px solid #d9dee7;padding:8px;text-align:left;vertical-align:top}
th{background:#eef2f7}
tr.flag td:first-child{border-left:4px solid #c2410c}
small{color:#4b5563}
</style></head>
<body>
<header>
<p><a href="../index.html">&larr; Own9 home</a></p>
<h1>Baltimore QB depth: stale-row check against official sources</h1>
<div class="note">
<strong>What this page shows.</strong> Each row compares a value in the repository with an official NFL.com or club-site value, read on the date shown. Blank means unverified. Nothing is inferred. The rows answer one question from the brief: which published depth rows are stale against official transactions, injury-reserve status and game documents.
<br><strong>Scope.</strong> Baltimore QB only (__COUNT__ rows). Other clubs are not covered by this page. Reads are single manual page views on 2026-11-18, not systematic captures.
<br><strong>Status key.</strong> Confirmed = official source agrees. Contradicted = repo value is stale. Flagged = official pages do not reconcile or are incomplete; for review.
</div>
</header>
<main>
<table>
<thead><tr><th>ID</th><th>Club</th><th>Player</th><th>Item</th><th>Repo value (as published)</th><th>Official value</th><th>Status</th><th>Source (official)</th><th>Read (UTC)</th></tr></thead>
<tbody>
__ROWS__
</tbody></table>
<p class="note"><strong>Not changed here.</strong> The shared files <code>data/board/replacement_depth.csv</code> and <code>replacement-depth.html</code> still show Brissett's replacement as blank (S-03). Correcting them belongs to the integration session. Flagged for review: the club depth chart carries no as-of date (S-04) and the roster status code TRC is not defined on the page (S-08).</p>
</main></body></html>
"""


def main():
    rows = load()
    errors = validate(rows)
    if errors:
        print("FAIL", *errors, sep="\n  ")
        return 1
    if "--check" in sys.argv:
        print(f"PASS {len(rows)} rows")
        return 0
    (HERE / "index.html").write_text(render(rows), encoding="utf-8")
    print(f"wrote index.html ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
