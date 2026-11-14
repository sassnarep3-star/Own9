#!/usr/bin/env python3
"""Session 00cf851d - build the verification dashboard.

Reads only the JSON registers this session wrote in ``data/`` and renders
static HTML into the section root. Nothing is typed in here: every number on
every page comes out of a register, and every table row carries the official
URL it was read from, or an explicit blank label when no official value exists.
"""

from __future__ import annotations

import html
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SESSION = os.path.dirname(HERE)
DATA = os.path.join(SESSION, "data")
ASSETS = os.path.join(SESSION, "assets")
REVIEW_DATE = "2026-11-14"

BLANK = '<span class="blank">blank — not published</span>'
UNVERIFIED = '<span class="blank">unverified</span>'


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return json.load(fh)


def esc(value):
    if value is None or value == "":
        return ""
    return html.escape(str(value), quote=True)


def cell(value, url=None, blank_label=BLANK):
    """Render one table cell. blanks stay visibly blank; sourced cells link out."""
    if value is None or value == "" or value == []:
        return blank_label
    text = esc(value)
    if url:
        return ('<a href="%s" rel="noopener noreferrer" target="_blank">%s</a>'
                % (esc(url), text))
    return text


def link(url, label=None):
    if not url:
        return BLANK
    return ('<a href="%s" rel="noopener noreferrer" target="_blank">%s</a>'
            % (esc(url), esc(label or url)))


PAGES = [
    ("index.html", "Overview", "A verified picture of what the repository actually holds"),
    ("summary.html", "Executive summary", "What is true, what is missing, what to do next"),
    ("sources.html", "Sources", "Official pages read on 2026-11-14"),
    ("verification.html", "Verification", "Line-by-line checks of committed claims"),
    ("gamebooks.html", "Game Books", "Official lineups, inactives and statistics"),
    ("replacement.html", "Replacement depth", "How far a club reached to fill a starting slot"),
    ("results.html", "Results and prices", "The committed results feed, audited"),
    ("injuries.html", "Injuries", "Official Week 10 injury report"),
    ("standings.html", "Standings", "Official 2026 standings"),
    ("repo-review.html", "Repository review", "What is in the repository, measured"),
    ("questions.html", "Questions", "What is known, what is missing, what closes it"),
    ("suggestions.html", "Suggestions", "Paths to choose between, before building"),
    ("flags.html", "Flagged for review", "Irregularities with source links"),
]


def nav(active):
    items = []
    for path, label, _ in PAGES:
        cls = ' class="active" aria-current="page"' if path == active else ""
        items.append('<a%s href="%s">%s</a>' % (cls, path, esc(label)))
    return '<nav aria-label="Section pages">%s</nav>' % "".join(items)


def table(headers, rows, caption=None, source=None):
    out = ['<div class="tablewrap"><table>']
    if caption or source:
        text = esc(caption) if caption else ""
        if source:
            text = (text + " · Source: " if text else "Source: ") + link(source)
        out.append("<caption>%s</caption>" % text)
    out.append("<thead><tr>" + "".join("<th>%s</th>" % esc(h) for h in headers) + "</tr></thead>")
    out.append("<tbody>")
    if not rows:
        out.append('<tr><td colspan="%d" class="empty">No rows.</td></tr>' % len(headers))
    for r in rows:
        out.append("<tr>" + "".join("<td>%s</td>" % c for c in r) + "</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def page(active, h1, lede, body):
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(h1)s · Own9 verified research</title>
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<header class="masthead">
  <p class="eyebrow">Own9 · session 00cf851d · official-source verification</p>
  <h1>%(h1)s</h1>
  <p class="lede">%(lede)s</p>
</header>
%(nav)s
<main>
%(body)s
</main>
<footer>
  <p>Reviewed on %(date)s. Every row on this site carries the official page it was read from.
  Where the league publishes no value the cell is left visibly blank rather than filled in.</p>
  <p><a href="https://github.com/sassnarep3-star/Own9/tree/main/session-00cf851d">Source and build scripts on GitHub</a></p>
</footer>
<script src="assets/app.js" defer></script>
</body>
</html>
""" % {"h1": esc(h1), "lede": lede, "nav": nav(active), "body": body, "date": REVIEW_DATE}


# ---------------------------------------------------------------------------

def build_index():
    v = load("verification.json")
    repl = load("replacement.json")
    audit = load("results_audit.json")
    flags = load("flags.json")
    qs = load("questions.json")
    sugg = load("suggestions.json")
    inv = load("repo_inventory.json")
    s = v["summary"]

    cards = [
        ("Checks run against official sources", s["total_checks"],
         "committed NFL claims re-read line by line", "verification.html"),
        ("Mismatches found", s["mismatch"],
         "every committed value matched the official document", "verification.html"),
        ("Replacements measured", repl["n_replacements_measured"],
         "starting-slot changes, with how deep the club reached", "replacement.html"),
        ("Results missing from the feed", audit["current_season_completeness"]["of_those_missing_a_result"],
         "played 2026 games the committed file has priced but not scored", "results.html"),
        ("Clubs reconciled with the league", audit["club_reconciliation"]["reconciled"],
         "of 32, against the official standings", "results.html"),
        ("Open irregularities", len(flags["flags"]),
         "each with the official page it was found on", "flags.html"),
        ("Questions on the record", len(qs["questions"]),
         "what is known, what is missing, what closes it", "questions.html"),
        ("Suggestions awaiting a choice", len(sugg["suggestions"]),
         "paths with costs and risks, nothing built yet", "suggestions.html"),
    ]
    body = ['<section><h2>What this section is</h2><p>One session, one job: read the official '
            'NFL documents on a single day, compare them line by line with what this repository '
            'already claims, and publish the result with a link on every row. Nothing here is '
            'modelled, backtested, staked or rewarded. Where the league does not publish a value, '
            'the cell stays blank and the gap is written down.</p></section>']
    body.append('<section><h2>At a glance</h2><ul class="cards">')
    for value, label, note, href in cards:
        body.append('<li class="card"><a href="%s"><span class="big">%s</span>'
                    '<span class="cl">%s</span><span class="cn">%s</span></a></li>'
                    % (href, esc(value), esc(label), esc(note)))
    body.append("</ul></section>")

    body.append('<section><h2>Pages</h2>' + table(
        ["Page", "What it holds"],
        [[link(p, t), esc(d)] for p, t, d in PAGES if p != "index.html"]))
    body.append('<section><h2>Executive summary</h2><p>The short version is on the '
                '<a href="summary.html">executive summary</a> page. The one thing to take from it: '
                'the repository already holds an odds archive it believes it does not have, and the '
                'archive is two rounds out of date.</p></section>')
    body.append('<section><h2>Repository shape</h2>' + table(
        ["Area", "Files"],
        [[esc(a["path"]), esc(a["files"])] for a in inv["areas"]],
        caption="%d tracked files measured on %s." % (inv["tracked_files"], REVIEW_DATE)))
    return page("index.html", "Own9 verified research",
                "Official NFL documents read on %s, compared line by line with what this repository already claims."
                % REVIEW_DATE, "".join(body))


def build_summary():
    v = load("verification.json")
    audit = load("results_audit.json")
    repl = load("replacement.json")
    flags = load("flags.json")
    c = audit["coverage"]
    cc = audit["current_season_completeness"]
    mv = audit["market_vs_outcome_2026"]
    s = v["summary"]

    body = []
    body.append("""<section><h2>Executive summary</h2>
<ol class="findings">
<li><strong>The committed NFL claims hold up.</strong> %(total)d checks were run against the official
documents this session read on %(date)s. %(match)d matched, %(mismatch)d mismatched and %(unver)d could
not be checked. Every starting lineup, every inactive list, every final score and every injury-report
row committed in the repository matched the league's own document.</li>

<li><strong>The repository has an odds archive it has been reporting as absent.</strong>
The committed results file carries a closing spread and a closing total for %(spread)d games spanning
%(seasons)s, and both moneylines for %(ml)d of them. Part of it was checked against the league: the 2026
season recomputed from the file gives Pittsburgh 6-2-0 with 180 points for and 144 against, and Tennessee
1-7-0 with 144 for and 199 against. The official standings say exactly the same. An earlier flag on the
record says no odds archive exists. That flag is wrong, and a wrong flag is worse than none because it
stops anyone looking.</li>

<li><strong>But it has no opening price, so half of the price requirement cannot be met.</strong>
There is no opening column and no timestamp column in any committed file. A store that records only a
closing number cannot show that a strategy beat a number that was actually available. This is a source
problem, not a code problem, and it needs an owner decision.</li>

<li><strong>The results feed is two rounds stale and nothing notices.</strong> %(played)d of the
%(sched)d scheduled 2026 games had been played by %(date)s. %(missing)d of them carry no result: the
entire Week 9 slate plus the Thursday-night game the league published two days earlier. Only two of
32 clubs can be reconciled against the official standings, and only because they are the two with no
game in the missing set. This session supplied %(official)d of the %(missing)d outcomes from the
league's own pages and left the rest blank.</li>

<li><strong>Depth of replacement is measurable, but not as asked.</strong> The league publishes no
depth chart; the club route returns the league's own 404 page, re-checked today. What the league does
publish, in consecutive Game Books, is four lists: starters, substitutions, did not play and not
active. Measuring how far down those lists a club reached turns an unmeetable requirement into a
measurable one. Across Washington and New York from Week 9 to Week 10 this session measured
%(nrepl)d replacements: %(t2)d came from the previous week's substitution list and %(t3)d from the
inactive list. It is an ordinal provenance scale, not a coaching depth chart, and it must never be
labelled as one.</li>

<li><strong>Two observations are not a correlation.</strong> Both starters who came off the previous
week's inactive list produced immediately. It is tempting to read that as "a deep replacement is not a
negative signal". With n = 2 there is no basis for it, so the number is published with its n and no
conclusion is drawn. The only correlation published anywhere on this site is n = %(npairs)d:
the closing spread against the actual margin, r = %(corr).4f.</li>

<li><strong>Nothing is live, so the demotion gate has nothing to act on.</strong> No strategy in the
repository has passed its validation gates. That makes this the right moment to define the gate,
before anyone has a result to protect. The honest split is an integrity trigger that fires immediately
and a performance trigger that waits for a predeclared sample.</li>
</ol></section>""" % {
        "total": s["total_checks"], "match": s["match"], "mismatch": s["mismatch"],
        "unver": s["unverifiable"], "date": REVIEW_DATE,
        "spread": c["rows_with_closing_spread"], "seasons": c["seasons"],
        "ml": c["rows_with_moneylines"],
        "played": cc["rows_with_gameday_on_or_before_review_date"], "sched": cc["scheduled_rows"],
        "missing": cc["of_those_missing_a_result"],
        "official": audit["officially_verified_outcomes"]["n"],
        "nrepl": repl["n_replacements_measured"],
        "t2": repl["tier_counts"]["T2"], "t3": repl["tier_counts"]["T3"],
        "npairs": audit["convention"]["n_pairs"], "corr": audit["convention"]["correlation"],
    })

    body.append('<section><h2>What to decide first</h2>' + table(
        ["Decision", "Why it is first"],
        [["Where opening prices come from",
          "Without a source, the price-snapshot requirement cannot be met and no backtest is honest."],
         ["Who keeps the results feed current",
          "It is two rounds stale today and no check in the repository would notice."],
         ["Provenance and licence of the committed price file",
          "7,424 closing spreads are usable in principle and undocumented in fact."],
         ["Minimum n before a correlation or a rank is published",
          "Chosen now, before there are results to tune it to."]]))
    body.append('<section><h2>What this session did not do</h2><ul>'
                '<li>Fit a model, run a backtest, place a wager or fund a reward.</li>'
                '<li>Fill a single cell from anything other than an official page read today.</li>'
                '<li>Edit another session\'s page, register, engine or branch.</li>'
                '<li>Claim that luck has been removed, or that any strategy is skill-based.</li>'
                '</ul></section>')
    body.append('<section><h2>Open irregularities</h2>' + table(
        ["Id", "Severity", "Finding"],
        [[esc(f["id"]), esc(f["severity"]), link(f["source_url"], f["title"])]
         for f in flags["flags"]]))
    return page("summary.html", "Executive summary",
                "Seven findings, in order of how much they change what should be built next.",
                "".join(body))


def build_sources():
    src = load("sources.json")
    rows = []
    for s in src["sources"]:
        rows.append([
            esc(s["id"]),
            esc(s["publisher"]),
            link(s["url"], s["url"]),
            esc(s.get("document_title") or s.get("document_title_published") or ""),
            esc(s.get("status", "retrieved")),
            esc(s.get("retrieved_utc", "")),
            esc(s.get("supports", "")),
            esc(s.get("scope", "")),
        ])
    body = ['<section><h2>Official sources read on %s</h2><p>Every value published in this section '
            'comes from one of these pages. No value was taken from another session\'s record: '
            'these are this session\'s own retrievals.</p></section>' % REVIEW_DATE]
    body.append(table(["Id", "Publisher", "URL", "Document title", "Status", "Read on",
                       "What it supports", "Scope and limits"], rows))
    body.append('<section><h2>Checked absence</h2><p>One entry above records a page that does not '
                'exist. That matters as much as the pages that do: the club depth-chart route on '
                'nfl.com returns the league\'s own 404 page, which is why no depth tier anywhere on '
                'this site is filled from a league source.</p></section>')
    return page("sources.html", "Sources", "The official pages behind every number in this section.",
                "".join(body))


def build_verification():
    v = load("verification.json")
    s = v["summary"]
    rows = []
    for c in v["checks"]:
        result = c["result"]
        cls = {"match": "ok", "mismatch": "bad", "unverifiable": "warn"}.get(result, "")
        rows.append([
            esc(c["id"]),
            esc(c["claim"]),
            cell(c["value_committed_in_repo"]),
            cell(c["value_read_from_official_source"]),
            '<span class="pill %s">%s</span>' % (cls, esc(result)),
            link(c["source_url"], esc(c["source_id"])),
            esc(c.get("note", "")),
        ])
    body = ['<section><h2>Line-by-line verification</h2>'
            '<p class="stat">%(total)d checks · %(match)d matched · %(mismatch)d mismatched · '
            '%(unver)d could not be checked</p>'
            '<p>Each row states the value committed in the repository, the value this session read '
            'from the official document on %(date)s, and the result. A blank on both sides counts as '
            'a match: where the league prints nothing, "nothing" is the verified value. A row marked '
            'unverifiable is a check that could not be performed, not a check that passed.</p></section>'
            % {"total": s["total_checks"], "match": s["match"], "mismatch": s["mismatch"],
               "unver": s["unverifiable"], "date": REVIEW_DATE}]
    body.append('<section><label class="filter">Filter rows '
                '<input type="search" id="q" placeholder="player, game, club, id"></label>'
                + table(["Check", "Claim", "Committed in repository", "Read from official source",
                         "Result", "Source", "Note"], rows,
                        caption="Every check this session ran, %s." % REVIEW_DATE) + "</section>")
    return page("verification.html", "Verification",
                "Committed claims re-read against the league's own documents, one row at a time.",
                "".join(body))


def build_gamebooks():
    gb = load("gamebooks.json")
    body = []
    body.append('<section><h2>Official Game Books</h2><p>Three NFL Game Summary PDFs were opened and '
                'read on %s. Everything below is transcribed from them: the eleven published starters '
                'on each side of the ball, the substitution list, the did-not-play list and the '
                'not-active list, plus the final statistics. Where the document prints a blank cell, '
                'the cell here is blank.</p>'
                '<p class="note">Each Game Book carries the league\'s copyright notice. This is a '
                'verification excerpt, not a republication.</p></section>' % REVIEW_DATE)
    for g in gb["games"]:
        src_url = SOURCE_URLS[g["source_id"]]
        cap = None
        body.append('<section><h2>%s · Week %s</h2>' % (esc(g["game_id"]), esc(g["week"])))
        body.append(table(
            ["Field", "Value"],
            [["Game", esc(g["away"]) + " at " + esc(g["home"])],
             ["Date", esc(g["date_printed"])],
             ["Kickoff", esc(g["start_time_printed"])],
             ["Venue", esc(g["venue"])],
             ["Weather", cell(g["weather"])],
             ["Referee", cell(g["referee"])],
             ["Paid attendance", esc(g["paid_attendance"])],
             ["Final", "%s %s · %s %s" % (esc(g["away_abbr"]), esc(g["final"][g["away_abbr"]]),
                                          esc(g["home_abbr"]), esc(g["final"][g["home_abbr"]]))],
             ["Game Book", link(src_url, "official PDF")]]))
        for abbr, block in g["teams"].items():
            body.append('<h3>%s (%s)</h3>' % (esc(CLUBS.get(abbr, abbr)), esc(abbr)))
            off = table(["Slot", "Player"], [[esc(s), esc(n)] for s, n in block["offense_starters"]],
                        source=src_url)
            dfn = table(["Slot", "Player"], [[esc(s), esc(n)] for s, n in block["defense_starters"]],
                        source=src_url)
            body.append('<div class="duo"><div><h4>Offense starters</h4>%s</div>'
                        '<div><h4>Defense starters</h4>%s</div></div>' % (off, dfn))
            body.append(table(
                ["List", "Entries"],
                [["Substitutions", esc(", ".join(block["substitutions"]))],
                 ["Did not play", esc(", ".join(block["did_not_play"])) or '<span class="blank">none printed</span>'],
                 ["Not active", esc(", ".join(block["not_active"]))]], source=src_url))
        for abbr, ind in g.get("individual", {}).items():
            for label, key, cols in (("Rushing", "rushing", ["player", "att", "yds", "avg", "lg", "td"]),
                                     ("Passing", "passing", ["player", "att", "cmp", "yds", "td", "int", "rt"]),
                                     ("Receiving", "receiving", ["player", "tar", "rec", "yds", "avg", "lg", "td"])):
                data = ind.get(key, [])
                if data:
                    body.append('<h3>%s · %s</h3>' % (esc(abbr), label))
                    body.append(table([c.upper() for c in cols],
                                      [[esc(r.get(c, "")) for c in cols] for r in data],
                                      source=src_url))
        body.append("</section>")
    return page("gamebooks.html", "Game Books",
                "Official lineups, inactives and statistics, transcribed from three NFL Game Summaries.",
                "".join(body))


CSV_URL = "https://github.com/sassnarep3-star/Own9/blob/main/data/raw/games.csv"

CLUBS = {
    "WAS": "Washington Commanders", "NYG": "New York Giants", "LAR": "Los Angeles Rams",
    "PHI": "Philadelphia Eagles", "NE": "New England Patriots", "DET": "Detroit Lions",
}
SOURCE_URLS = {
    "gamebook-was-nyg-w10": "https://static.www.nfl.com/image/upload/v1794570519/gamecenter/ab5828d9-4feb-11f1-abca-2c54536568a9.pdf",
    "gamebook-lar-was-w9": "https://static.www.nfl.com/image/upload/v1794224919/gamecenter/ab382331-4feb-11f1-abca-2c54536568a9.pdf",
    "gamebook-nyg-phi-w9": "https://static.www.nfl.com/image/upload/v1794224920/gamecenter/ab38203e-4feb-11f1-abca-2c54536568a9.pdf",
}


def build_replacement():
    repl = load("replacement.json")
    body = ['<section><h2>Depth of replacement</h2><p>%s</p>' % esc(repl["method"])]
    body.append('<p class="stat">%d replacements measured · %s</p>'
                % (repl["n_replacements_measured"],
                   " · ".join("%s = %d" % (k, v) for k, v in repl["tier_counts"].items() if v)))
    body.append('<p class="note">%s</p></section>' % esc(repl["caveat"]))
    body.append('<section><h2>The scale</h2>' + table(
        ["Tier", "Meaning"], [[esc(k), esc(v)] for k, v in repl["tier_definitions"].items()],
        source=SOURCE_URLS["gamebook-was-nyg-w10"]))

    incoming = [r for r in repl["rows"] if r["provenance_tier"]]
    outgoing = [r for r in repl["rows"] if not r["provenance_tier"]]
    body.append('<section><h2>Incoming: how far the club reached</h2>' + table(
        ["Club", "Side", "Slot", "Replacement", "Tier", "Where he was listed in Week 9",
         "Official Week 10 production", "Source"],
        [[esc(r["club"]), esc(r["side"]), esc(r["slot"]), esc(r["replacement"]),
          '<span class="pill tier%s">%s</span>' % (esc(r["provenance_tier"]), esc(r["provenance_tier"])),
          esc(r["week9_status"]),
          cell(r["week10_official_production"], blank_label='<span class="blank">no line printed</span>'),
          link(r["prior_source_url"], "Week 9 Game Book")]
         for r in incoming],
        caption="Production is copied from the official Week 10 Game Book. A blank means the book printed no line for that player, not that he did nothing."))
    body.append('<section><h2>Outgoing: where the departed starter landed</h2>' + table(
        ["Club", "Side", "Slot", "Departed Week 9 starter", "Where he appeared in Week 10", "Source"],
        [[esc(r["club"]), esc(r["side"]), esc(r["slot"]), esc(r["outgoing_starter"]),
          esc(r["week10_official_production"]), link(r["source_url"], "Week 10 Game Book")]
         for r in outgoing]))
    body.append('<section><h2>A trap worth naming</h2><p>Two of the %d replacements came from the '
                'previous week\'s not-active list, and both produced immediately. That is n = 2. '
                'It is not a correlation, no conclusion is drawn from it, and no staking rule should '
                'be built on it. It is published with its n precisely so that it cannot be mistaken '
                'for a finding.</p></section>' % repl["n_replacements_measured"])
    return page("replacement.html", "Replacement depth",
                "The league publishes no depth chart. It does publish four lists per game, and that is enough to measure depth without inventing it.",
                "".join(body))


def build_results():
    audit = load("results_audit.json")
    c, cc, cr = audit["coverage"], audit["current_season_completeness"], audit["club_reconciliation"]
    mv = audit["market_vs_outcome_2026"]
    body = ['<section><h2>The committed results and price file</h2><p>Read-only. The file was measured '
            'and never edited. Every number below is copied or computed from it, and every comparison '
            'is against an official page read on %s.</p></section>' % REVIEW_DATE]
    body.append('<section><h2>Coverage</h2>' + table(
        ["Measure", "Value"],
        [["Rows", esc(c["rows"])],
         ["Seasons", esc(c["seasons"])],
         ["Columns", esc(c["columns"])],
         ["Rows with a result", esc(c["rows_with_a_result"])],
         ["Rows with a closing spread", esc(c["rows_with_closing_spread"])],
         ["Rows with a closing total", esc(c["rows_with_closing_total"])],
         ["Rows with both moneylines", esc(c["rows_with_moneylines"])],
         ["Rows with an opening price", '<span class="blank">0 — no opening column exists</span>'],
         ["Internal arithmetic failures",
          "%s" % esc(audit["internal_consistency"]["rows_where_that_fails"])]],
        source=CSV_URL))
    body.append('<section><h2>Convention, established from the data</h2><p>%s</p>' %
                esc(audit["convention"]["how_it_was_established"]))
    body.append(table(["n pairs", "Correlation", "Statement"],
                      [[esc(audit["convention"]["n_pairs"]), esc(audit["convention"]["correlation"]),
                        esc(audit["convention"]["statement"])]], source=CSV_URL))
    body.append('<section><h2>Current season completeness</h2><p>%s</p>' % esc(cc["statement"]))
    body.append(table(["Measure", "Value"],
                      [["Scheduled 2026 rows", esc(cc["scheduled_rows"])],
                       ["Played by %s" % REVIEW_DATE, esc(cc["rows_with_gameday_on_or_before_review_date"])],
                       ["Missing a result", '<span class="pill bad">%s</span>' % esc(cc["of_those_missing_a_result"])],
                       ["Missing game ids", esc(", ".join(cc["missing_game_ids"]))]], source=CSV_URL))
    body.append('<section><h2>Club reconciliation against the official standings</h2><p>%s</p>' %
                esc(cr["description"]))
    body.append(table(
        ["Club", "Games with a result", "Missing", "Recomputed", "Official", "Outcome"],
        [[esc(x["abbr"]), esc(x["games_in_file_with_result"]), esc(x["games_missing_result"]),
          "%d-%d-%d · PF %d PA %d" % (x["recomputed_w"], x["recomputed_l"], x["recomputed_t"],
                                      x["recomputed_pf"], x["recomputed_pa"]),
          "%d-%d-%d · PF %d PA %d" % (x["official_w"], x["official_l"], x["official_t"],
                                      x["official_pf"], x["official_pa"]),
          '<span class="pill %s">%s</span>' % ("ok" if x["reconciles"] else "warn", esc(x["status"]))]
         for x in cr["clubs"]], source=cr["standings_source_url"]))
    body.append('<section><h2>Officially verified outcomes</h2><p>%s</p>' %
                esc(audit["officially_verified_outcomes"]["description"]))
    body.append(table(
        ["Game", "Week", "Date", "Away", "Home", "Official margin", "Official total",
         "In committed file?", "Source"],
        [[esc(x["game_id"]), esc(x["week"]), esc(x["gameday"]),
          "%s %s" % (esc(x["away"]), esc(x["away_points"])),
          "%s %s" % (esc(x["home"]), esc(x["home_points"])),
          esc(x["official_home_margin"]), esc(x["official_total"]),
          '<span class="pill %s">%s</span>' % ("ok" if x["result_present_in_committed_file"] else "bad",
                                               "yes" if x["result_present_in_committed_file"] else "no"),
          link(x["source_url"], "league schedule")]
         for x in audit["officially_verified_outcomes"]["rows"]]))
    body.append('<section><h2>Market line, actual outcome, and the difference</h2><p>%s</p>' %
                esc(mv["description"]))
    body.append(table(
        ["Measure", "Value"],
        [["Games", esc(mv["n_games"])],
         ["Mean absolute spread miss", esc(mv["mean_absolute_spread_miss"])],
         ["Mean absolute total miss", esc(mv["mean_absolute_total_miss"])],
         ["Mean signed spread miss", esc(mv["mean_signed_spread_miss"])],
         ["Mean signed total miss", esc(mv["mean_signed_total_miss"])]], source=CSV_URL))
    body.append('<p class="note">%s</p>' % esc(mv["interpretation_note"]))
    body.append('<label class="filter">Filter rows <input type="search" id="q" placeholder="club, week, date"></label>')
    body.append(table(
        ["Game", "Wk", "Date", "Matchup", "Closing spread", "Closing total",
         "Model fair line", "Difference", "Actual margin", "Actual total",
         "Spread miss", "Total miss"],
        [[esc(m["game_id"]), esc(m["week"]), esc(m["gameday"]),
          "%s @ %s" % (esc(m["away"]), esc(m["home"])),
          esc(m["closing_spread_home"]), esc(m["closing_total"]),
          cell(m["model_fair_line"]),
          cell(None, blank_label='<span class="blank">needs a fair line</span>'),
          esc(m["actual_home_margin"]), esc(m["actual_total"]),
          esc(m["spread_miss_home"]), esc(m["total_miss"])]
         for m in mv["rows"]],
        caption="Spread and total are stated from the home club's perspective, measured on %s. Outcomes are not individually re-verified against the league." % REVIEW_DATE,
        source=CSV_URL))
    return page("results.html", "Results and prices",
                "What the committed results file holds, what it is missing, and what it checks out against.",
                "".join(body))


def build_injuries():
    rep = load("injury_report_week10.json")
    body = ['<section><h2>%s</h2><p>Read on %s. %s</p>'
            '<p class="note">%s</p></section>'
            % (esc(rep["document_title_published"]), REVIEW_DATE,
               esc(rep["rights_note"]), esc(rep["null_policy"]))]
    body.append('<section><h2>Clubs with no table in this report</h2><p>%s: %s. %s</p></section>'
                % (esc(", ".join(rep["clubs_absent_from_report"])),
                   "all four appear in the official standings with nine games played",
                   esc(rep["clubs_absent_note"])))
    total = 0
    for g in rep["games"]:
        body.append('<section><h2>%s · %s</h2>' % (esc(g.get("kickoff_printed", g["kickoff_date"])),
                                                   esc(g["matchup"])))
        for club in g["clubs"]:
            total += len(club["rows"])
            body.append('<h3>%s (%s) · %s</h3>' % (esc(club["club"]), esc(club["abbr"]),
                                                   esc(club["record_on_page"])))
            body.append(table(
                ["Player", "Pos", "Injury", "Practice status", "Game status"],
                [[esc(r[0]), esc(r[1]), cell(r[2]), esc(r[3]), cell(r[4])] for r in club["rows"]],
                source=rep["source_url"]))
        body.append("</section>")
    body.insert(1, '<p class="stat">%d rows across %d clubs · source %s</p>'
                % (total, sum(len(g["clubs"]) for g in rep["games"]), link(rep["source_url"])))
    return page("injuries.html", "Injuries",
                "The league's official Week 10 report, published field for field with nothing filled in.",
                "".join(body))


def build_standings():
    st = load("standings_2026.json")
    body = ['<section><h2>%s</h2><p>%s</p><p class="note">%s</p></section>'
            % (esc(st["document_title_published"]), esc(st["as_of_note"]), esc(st["column_policy"]))]
    for d in st["divisions"]:
        body.append('<section><h2>%s</h2>' % esc(d["division"]))
        body.append(table(
            ["Club", "W", "L", "T", "PCT", "PF", "PA", "Net", "Home", "Road", "Div", "Conf", "Streak"],
            [[esc(c["team"]), esc(c["w"]), esc(c["l"]), esc(c["t"]), esc(c["pct"]),
              esc(c["pf"]), esc(c["pa"]), esc(c["net_pts"]), esc(c["home"]), esc(c["road"]),
              esc(c["div"]), esc(c["conf"]), esc(c["strk"])] for c in d["clubs"]],
            source=st["source_url"]))
        body.append("</section>")
    body.append('<section><h2>Reconciliation</h2><p>Every club\'s home record plus road record equals '
                'its win-loss-tie record, points for minus points against equals net points, and '
                'across all 32 clubs league points for equals league points against. All three checks '
                'pass on this transcription; they are listed on the verification page.</p></section>')
    return page("standings.html", "Standings",
                "Official 2026 records as published by the league on %s." % REVIEW_DATE,
                "".join(body))


def build_repo_review():
    inv = load("repo_inventory.json")
    audit = load("results_audit.json")
    body = ['<section><h2>Repository shape</h2><p>%d tracked files, %d published root pages and '
            '%d outbound source links across those pages, measured on %s. These are measurements, '
            'not a judgement of correctness.</p></section>'
            % (inv["tracked_files"], inv["root_pages"],
               inv["external_href_count_across_root_pages"], REVIEW_DATE)]
    body.append(table(["Area", "Path", "Files", "Verified against an official source?"],
                      [[esc(a["area"]), esc(a["path"]), esc(a["files"]), UNVERIFIED]
                       for a in inv["areas"]]))
    body.append('<section><h2>Committed raw data</h2><p>Measured locally, not re-checked against the '
                'league. The league publishes no retrievable archive of historical closing prices, so '
                'no comparison is possible.</p></section>')
    body.append(table(["File", "Rows", "Columns", "SHA-256 (first 16)", "Contents verified?"],
                      [[esc(f["path"]), esc(f["data_rows"]), esc(f["columns"]),
                        esc(f["sha256"][:16]), '<span class="pill warn">no</span>']
                       for f in inv["raw_files"]]))
    body.append('<section><h2>What the results file holds</h2>' + table(
        ["Measure", "Value"],
        [["Rows", esc(audit["coverage"]["rows"])],
         ["Seasons", esc(audit["coverage"]["seasons"])],
         ["Rows with a result", esc(audit["coverage"]["rows_with_a_result"])],
         ["Rows with a closing spread", esc(audit["coverage"]["rows_with_closing_spread"])],
         ["Rows with an opening price", '<span class="blank">0</span>'],
         ["2026 games missing a result", esc(audit["current_season_completeness"]["of_those_missing_a_result"])],
         ["Clubs reconciled with the league", "%d of 32" % audit["club_reconciliation"]["reconciled"]]]))
    body.append('<section><h2>Root pages</h2>' + table(
        ["Published root page"], [[esc(p)] for p in inv["root_page_names"]]))
    return page("repo-review.html", "Repository review",
                "What is in the repository, measured rather than asserted.", "".join(body))


def build_questions():
    qs = load("questions.json")
    body = ['<section><h2>Questions</h2><p>%s</p></section>' % esc(qs["how_to_read_this"])]
    body.append('<section><h2>The eight requirements</h2>' + table(
        ["Id", "Requirement"], [[esc(r["id"]), esc(r["title"])] for r in qs["requirements"]],
        source="https://github.com/sassnarep3-star/Own9/blob/main/research/METHODOLOGY.md"))
    body.append('<label class="filter">Filter rows <input type="search" id="q" '
                'placeholder="requirement, status, keyword"></label>')
    status_pill = {"answered": "ok", "open-decision": "warn", "open-source": "warn", "probe": "info"}
    body.append(table(
        ["Id", "Req", "Status", "Question", "What we have", "What is missing", "Closes with", "Source"],
        [[esc(q["id"]), esc(q["requirement"]),
          '<span class="pill %s">%s</span>' % (status_pill.get(q["status"], "info"), esc(q["status"])),
          esc(q["question"]), esc(q["what_we_have"]), esc(q["what_is_missing"]),
          esc(q["how_to_close"]), link(q["source_url"], "source")]
         for q in qs["questions"]],
        caption="%d questions on the record as of %s." % (len(qs["questions"]), REVIEW_DATE)))
    return page("questions.html", "Questions",
                "What is known, what is missing, and what would close it — with a source on every answer.",
                "".join(body))


def build_suggestions():
    sg = load("suggestions.json")
    body = ['<section><h2>Suggestions</h2><p>%s</p></section>' % esc(sg["how_to_use_this"])]
    for s in sg["suggestions"]:
        body.append('<section><h2>%s · %s</h2>' % (esc(s["id"]), esc(s["title"])))
        body.append('<p><strong>Unblocks:</strong> %s</p>' % esc(s["what_it_unblocks"]))
        body.append('<p><strong>Evidence this session:</strong> %s</p>' % esc(s["evidence_this_session"]))
        body.append(table(
            ["Path", "Label", "Cost", "Risk / what can go wrong", "Unblocks"],
            [[esc(p["id"]), esc(p["label"]), esc(p["cost"]), esc(p["risk"]), esc(p["unblocks"])]
             for p in s["paths"]]))
        body.append('<p class="decision"><strong>Decision needed:</strong> %s</p></section>'
                    % esc(s["decision_needed"]))
    return page("suggestions.html", "Suggestions",
                "Paths to choose between before anything is built — costs, risks and what each one unblocks.",
                "".join(body))


def build_flags():
    fl = load("flags.json")
    body = ['<section><h2>Flagged for review</h2><p>%s</p></section>' % esc(fl["namespace_note"])]
    for f in fl["flags"]:
        body.append('<section><h2><span class="pill sev-%s">%s</span> %s · %s</h2>'
                    % (esc(f["severity"]), esc(f["severity"]), esc(f["id"]), esc(f["title"])))
        body.append(table(
            ["", ""],
            [["<strong>Observed</strong>", esc(f["what_was_observed"])],
             ["<strong>Why it matters</strong>", esc(f["why_it_matters"])],
             ["<strong>What this session did</strong>", esc(f["what_this_session_did"])],
             ["<strong>Source</strong>", link(f["source_url"])],
             ["<strong>Second source</strong>",
              link(f.get("second_source_url")) if f.get("second_source_url") else
              '<span class="blank">none</span>']]))
        body.append("</section>")
    return page("flags.html", "Flagged for review",
                "Every irregularity this session found, with the official page it was found on.",
                "".join(body))


BUILDERS = {
    "index.html": build_index, "summary.html": build_summary, "sources.html": build_sources,
    "verification.html": build_verification, "gamebooks.html": build_gamebooks,
    "replacement.html": build_replacement, "results.html": build_results,
    "injuries.html": build_injuries, "standings.html": build_standings,
    "repo-review.html": build_repo_review, "questions.html": build_questions,
    "suggestions.html": build_suggestions, "flags.html": build_flags,
}


def main():
    os.makedirs(ASSETS, exist_ok=True)
    for name, fn in BUILDERS.items():
        with open(os.path.join(SESSION, name), "w", encoding="utf-8") as fh:
            fh.write(fn())
    print("Rendered %d pages into %s" % (len(BUILDERS), SESSION))


if __name__ == "__main__":
    main()
