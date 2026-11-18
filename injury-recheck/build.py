#!/usr/bin/env python3
"""Compare the official Week 10 2026 rows (data/recheck.json) with the repository's
published snapshot table (../injuries.html) and write index.html.

Verdicts are computed, not typed: a row is 'match' only when team, player, injury,
practice and game status all equal the official row. Stdlib only.
"""
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def read_repo_rows(path):
    """Return {(team, player): {...}} from the 'explicit Game Status' table in injuries.html."""
    s = open(path, encoding="utf-8").read()
    anchor = "Week 10 2026 availability snapshot (players with an explicit Game Status)</h2>"
    i = s.index(anchor)
    j = s.index("</table>", i)
    out = {}
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", s[i:j], re.S)[1:]:
        cells = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip()
                 for c in re.findall(r"<(?:th|td)[^>]*>(.*?)</(?:th|td)>", row, re.S)]
        if len(cells) < 6:
            continue
        team, player, pos, injury, practice, game = cells[:6]
        out[(team, player)] = {"position": pos, "injury": injury, "practice": practice, "game": game}
    return out


def compare(official, repo):
    results = []
    for r in official["official_rows"]:
        key = (r["team"], r["player"])
        rr = repo.get(key)
        if rr is None:
            if r["game"] == "":
                verdict = "consistent (no game status; not in table by design)"
            else:
                verdict = "MISSING from repo table"
            repo_text = "not in table"
        else:
            same = (rr["injury"] == r["injury"] and rr["practice"] == r["practice"]
                    and rr["game"] == r["game"])
            verdict = "match" if same else "MISMATCH"
            repo_text = f'{rr["injury"] or "(blank)"} | {rr["practice"]} | {rr["game"] or "(blank)"}'
        results.append({**r, "repo_text": repo_text, "verdict": verdict})
    return results


def esc(x):
    return html.escape(str(x), quote=True)


def page(official, results):
    src = official["source_url"]
    counts = {}
    for r in results:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    rows = []
    for r in results:
        off = f'{r["injury"] or "(blank)"} | {r["practice"]} | {r["game"] or "(blank)"}'
        flags = ", ".join(r["flag_refs"]) or "-"
        cls = "ok" if r["verdict"].startswith(("match", "consistent")) else "bad"
        rows.append(
            f'<tr class="{cls}"><th scope="row">{esc(r["club"])} · {esc(r["player"])} ({esc(r["position"])})</th>'
            f'<td>{esc(r["game_section"])}</td><td>{esc(off)}</td><td>{esc(r["repo_text"])}</td>'
            f'<td><strong>{esc(r["verdict"])}</strong></td><td>{esc(flags)}</td>'
            f'<td><a href="{esc(src)}">NFL.com official report ↗</a> (chunk {r["chunk"]})</td></tr>'
        )
    news = []
    for n in official["official_absence_and_news"]:
        news.append(
            f'<tr><th scope="row">{esc(n["player"])} ({esc(n["club"])})</th><td>{esc(n["official_fact"])}</td>'
            f'<td>{esc(n["official_news_headline"])}</td><td>{esc(", ".join(n["flag_refs"]))}</td>'
            f'<td><a href="{esc(n["official_news_url"])}">NFL.com news ↗</a> (chunk {n["chunk"]})</td></tr>'
        )
    irr = []
    for x in official["irregularities"]:
        irr.append(
            f'<tr><th scope="row">{esc(x["id"])}</th><td>{esc(x["severity"])}</td><td>{esc(x["text"])}</td>'
            f'<td><a href="{esc(x["source_url"])}">source ↗</a></td></tr>'
        )
    summary = " · ".join(f"{esc(k)}: {v}" for k, v in sorted(counts.items()))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Week 10 injury rows — official re-check · Own9</title>
<link rel="stylesheet" href="../style.css">
<style>tr.bad td strong{{color:#8a1c1c}} tr.ok td strong{{color:#1d6b34}} table{{font-size:14px}} td,th{{vertical-align:top}}</style>
</head><body>
<main class="shell" id="main">
<p><a href="../index.html">← Own9 home</a> · <a href="../availability.html">Availability tracker</a> · <a href="../flags.html">Flagged for Review</a></p>
<h1>Week 10 injury rows: re-checked against the official NFL report</h1>
<p class="lead">Each row below was read from the official NFL.com Week 10 2026 injury report on {esc(official["read_date_utc"])} (UTC) and compared, field by field, with the snapshot table on <a href="../injuries.html">injuries.html</a>. The verdict is computed by <code>injury-recheck/build.py</code>, not typed.</p>
<div class="notice"><strong>Scope.</strong> This checks selected rows and the claims the flag register makes about them. It does <strong>not</strong> re-count the full report (the brief's 254 / 279 totals remain open), and it is not a historical archive. Values that could not be read are blank, never inferred.</div>
<p><strong>Rows checked:</strong> {len(results)} · {summary}</p>
<h2>1. Official row against repository row</h2>
<div class="table-wrap" tabindex="0" role="region" aria-label="Row checks"><table>
<thead><tr><th scope="col">Club · player</th><th scope="col">Game (as listed)</th><th scope="col">Official: injury | practice | game status</th><th scope="col">Repository (injuries.html): same fields</th><th scope="col">Verdict</th><th scope="col">Flag refs</th><th scope="col">Evidence</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>
<h2>2. Absence and news claims</h2>
<div class="table-wrap" tabindex="0" role="region" aria-label="Absence and news checks"><table>
<thead><tr><th scope="col">Player</th><th scope="col">Official report fact</th><th scope="col">Official news headline (read same day)</th><th scope="col">Flag refs</th><th scope="col">Evidence</th></tr></thead>
<tbody>{''.join(news)}</tbody></table></div>
<h2>3. Irregularities found in this check</h2>
<div class="table-wrap" tabindex="0" role="region" aria-label="Irregularities"><table>
<thead><tr><th scope="col">ID</th><th scope="col">Severity</th><th scope="col">Finding</th><th scope="col">Source</th></tr></thead>
<tbody>{''.join(irr)}</tbody></table></div>
<h2>4. Not done here (open)</h2>
<ul>
<li>Full row count and section count of the Week 10 report (not re-counted).</li>
<li>Any Week 11 capture. The site's Week 11 status is not verified here.</li>
<li>Scheduled or repeated capture. NFL.com Terms section 1.3 prohibits systematic retrieval for compiling a database without consent; see the repository decision DEC-01 on the readiness page.</li>
</ul>
<p>Re-run: <code>python3 injury-recheck/build.py</code> and <code>python3 -m unittest discover -s injury-recheck/tests</code>.</p>
</main></body></html>
"""


def main():
    official = json.load(open(os.path.join(HERE, "data", "recheck.json"), encoding="utf-8"))
    repo = read_repo_rows(os.path.join(ROOT, "injuries.html"))
    results = compare(official, repo)
    out = os.path.join(HERE, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page(official, results))
    bad = [r for r in results if r["verdict"] in ("MISMATCH",) or r["verdict"].startswith("MISSING")]
    print(f"wrote {out}: {len(results)} rows, {len(bad)} disagreements")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
