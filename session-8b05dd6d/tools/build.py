#!/usr/bin/env python3
"""Build the session-8b05dd6d static dashboard (standard library only).

Inputs : data/*.psv  (hand-transcribed from official NFL.com / GRA pages; see sources.html)
Outputs: *.html pages, data/*.csv exports, assets/style.css
Every data row carries a source link. Blank cells are unverified, never inferred.
"""
import csv
import collections
import html
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
RETRIEVED = "2026-11-14"
INJ_URL = "https://www.nfl.com/injuries/"
SCHED_URL = "https://www.nfl.com/schedules/2026/REG10"
GRA_URL = "https://www.gra.gov.sg/harm-minimisation/unlawful-remote-gambling-activities"
SP_URL = "https://www.singaporepools.com.sg/"

POS_GROUP = {
    "QB": "QB", "RB": "RB", "FB": "RB", "WR": "WR", "TE": "TE",
    "T": "OL", "G": "OL", "C": "OL", "DT": "DL", "DE": "DL",
    "LB": "LB", "CB": "DB", "S": "DB", "K": "ST", "P": "ST", "LS": "ST",
}
GROUPS = ["QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB", "ST"]


def esc(value):
    return html.escape(str(value), quote=True)


def a(url, label=None):
    return f'<a href="{esc(url)}" rel="noopener">{esc(label or url)}</a>'


def read_psv(name, width):
    rows = []
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("|")
            if len(parts) != width:
                raise SystemExit(f"{name}:{n} has {len(parts)} fields, expected {width}")
            rows.append(parts)
    return rows


# ---------- load and cross-check data ----------
GAMES = read_psv("games_week10.psv", 8)
GAME = {g[0]: g for g in GAMES}
INJ = read_psv("injury_report_week10.psv", 7)
NEWS = read_psv("nfl_news_headlines.psv", 3)
STARTERS = read_psv("starter_replacements.psv", 7)

for row in INJ:
    gid, team = row[0], row[1]
    if gid not in GAME:
        raise SystemExit(f"unknown game {gid}")
    if team not in (GAME[gid][5], GAME[gid][6]):
        raise SystemExit(f"team {team} not in {gid}")
    if row[3] not in POS_GROUP:
        raise SystemExit(f"unmapped position {row[3]}")

INJ_ROWS = []
for gid, team, player, pos, injury, practice, status in INJ:
    g = GAME[gid]
    INJ_ROWS.append({
        "game_id": gid, "matchup": f"{g[4]} ({g[1]}, {g[2]} ET, {g[3]})",
        "team": team, "player": player, "position": pos, "group": POS_GROUP[pos],
        "injury": injury, "practice": practice, "game_status": status,
        "starter_backup": "", "source": INJ_URL,
    })


def exposure():
    """Counts from the verified injury rows only. Not starter-adjusted."""
    teams = collections.OrderedDict()
    for g in GAMES:
        for t in (g[5], g[6]):
            teams[t] = {"game": g[0], "matchup": g[4], "Out": 0, "Doubtful": 0,
                        "Questionable": 0, "listed": 0,
                        "grp": collections.Counter()}
    for r in INJ_ROWS:
        t = teams[r["team"]]
        t["listed"] += 1
        if r["game_status"] in ("Out", "Doubtful", "Questionable"):
            t[r["game_status"]] += 1
        if r["game_status"] in ("Out", "Doubtful"):
            t["grp"][r["group"]] += 1
    return teams


EXPO = exposure()
COUNTS = collections.Counter(r["game_status"] for r in INJ_ROWS)
TOTAL_ROWS = len(INJ_ROWS)
NOT_INJURY = sum(1 for r in INJ_ROWS if "Not injury related" in r["injury"])
GAME_COUNT = len(GAMES)

# ---------- layout ----------
NAV = [
    ("index.html", "Overview"),
    ("summary.html", "Executive summary"),
    ("injuries.html", "Injuries"),
    ("games.html", "Games"),
    ("starters.html", "Starters & backups"),
    ("strategies.html", "Strategies & lines"),
    ("questions.html", "Questions"),
    ("suggestions.html", "Suggestions"),
    ("repo-review.html", "Repo review"),
    ("sources.html", "Sources"),
    ("flags.html", "Flagged for Review"),
]


def page(filename, title, active, body):
    links = []
    for href, label in NAV:
        current = ' aria-current="page"' if href == active else ""
        links.append(f'<a href="{href}"{current}>{esc(label)}</a>')
    nav = "".join(links)
    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · NFL injury & strategy dashboard</title>
<link rel="stylesheet" href="assets/style.css">
<script src="assets/app.js" defer></script></head>
<body><a class="skip" href="#main">Skip to content</a>
<header class="top"><div class="wrap"><a class="brand" href="index.html">NFL Dashboard</a>
<span class="tag">Research only · no wagering advice · data as of {RETRIEVED} (UTC)</span></div>
<nav class="wrap nav" aria-label="Main navigation">{nav}</nav></header>
<main class="wrap" id="main">
<h1>{esc(title)}</h1>
{body}
</main>
<footer class="wrap foot">Built from official NFL.com pages and the Singapore Gambling Regulatory Authority (GRA) site. Blank cells are unverified and are never inferred.
Generated by <code>tools/build.py</code>.</footer></body></html>
"""
    with open(os.path.join(ROOT, filename), "w", encoding="utf-8") as fh:
        fh.write(doc)


def table(headers, rows, caption, table_id=None, search=False):
    head = "".join(f'<th scope="col">{esc(h)}</th>' for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    sid = f' id="{table_id}"' if table_id else ""
    tools = ""
    if search:
        tools = (f'<div class="tools"><label for="{table_id}-q">Filter rows</label>'
                 f'<input id="{table_id}-q" type="search" data-filter="{table_id}" '
                 f'placeholder="e.g. Seahawks, Out, QB" autocomplete="off">'
                 f'<span class="count" data-count="{table_id}"></span></div>')
    return (f'{tools}<div class="table-wrap"><table{sid}><caption class="sr-only">{esc(caption)}</caption>'
            f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>")


def src(url, label):
    return a(url, label)


def badge(text, kind="flag"):
    return f'<span class="badge {kind}">{esc(text)}</span>'


def unverified():
    return badge("Unverified", "flag")


# ---------- pages ----------
def build_injuries():
    rows = []
    for r in INJ_ROWS:
        rows.append([
            esc(r["matchup"]), esc(r["team"]), esc(r["player"]), esc(r["position"]),
            esc(r["group"]), esc(r["injury"]), esc(r["practice"]),
            f'<b class="st-{r["game_status"].lower()}">{esc(r["game_status"])}</b>',
            "",  # starter/backup: official source not captured -> blank
            src(INJ_URL, "nfl.com injury report"),
        ])
    headers = ["Game", "Team", "Player", "Pos", "Group", "Injury (as listed)",
               "Practice (as listed)", "Game status", "Starter / backup (blank = unverified)",
               "Source"]
    body = (
        f'<div class="notice"><strong>Official source, Week 10 2026.</strong> '
        f'Transcribed from {src(INJ_URL, "nfl.com/injuries")} (all eight pages read on {RETRIEVED}). '
        f'Only players with an injury entry or a game status are listed ({TOTAL_ROWS} rows across '
        f'{GAME_COUNT} games). The page shows no update time. Players without an entry, and players '
        f'shown as "Did Not Participate" with no designation, are omitted. Starter and backup columns '
        f'are blank because the injury report does not state them.</div>'
        f'<div class="cards small">'
        f'<div><span>Out</span><b>{COUNTS["Out"]}</b></div>'
        f'<div><span>Doubtful</span><b>{COUNTS["Doubtful"]}</b></div>'
        f'<div><span>Questionable</span><b>{COUNTS["Questionable"]}</b></div>'
        f'<div><span>"Not injury related" entries</span><b>{NOT_INJURY}</b></div></div>'
        f'<h2>Position-group exposure (Out + Doubtful, counted from the rows below)</h2>'
        f'<p class="note">Counts are arithmetic on the listed rows. They are not starter-adjusted, '
        f'so they do not show whether a backup is actually replacing a starter. Every count is linked to the same official report.</p>'
        + exposure_table() +
        f'<h2>All listed injury rows</h2>'
        + table(headers, rows, "Week 10 injury report rows", "inj", search=True)
        + news_block()
    )
    page("injuries.html", "Injury report · Week 10 (2026)", "injuries.html", body)


def exposure_table():
    headers = ["Team", "Game", "Listed", "Out", "Doubtful", "Questionable"] + GROUPS + ["Source"]
    rows = []
    for team, e in EXPO.items():
        cells = [esc(team), esc(e["matchup"]), str(e["listed"]), str(e["Out"]),
                 str(e["Doubtful"]), str(e["Questionable"])]
        cells += [str(e["grp"].get(g, 0)) if e["grp"].get(g, 0) else "0" for g in GROUPS]
        cells.append(src(INJ_URL, "nfl.com injury report"))
        rows.append(cells)
    return table(headers, rows, "Position-group exposure by team", "expo", search=True)


def news_block():
    rows = [[esc(h), src(u, "NFL.com")] for h, u, _ in NEWS]
    return ('<h2>Official NFL.com headlines linked from the injury page</h2>'
            '<p class="note">Headline text only, as shown on the injury page. Article bodies were not opened. '
            'Treat each headline as NFL.com wording, not a confirmed inactives list.</p>'
            + table(["Headline (as shown)", "Source"], rows, "NFL.com headlines", "news", search=True))


def build_games():
    rows = []
    for g in GAMES:
        rows.append([esc(g[0]), esc(g[1]), esc(g[2]), esc(g[3]), esc(g[4]),
                     esc(g[5]), esc(g[6]), esc(g[7]), src(SCHED_URL, "nfl.com schedule (Week 10)")])
    body = ('<div class="notice"><strong>Matchups and kickoff times checked against the NFL.com Week 10 schedule.</strong> '
            'Away team is listed first, as on nfl.com. The Thursday game is already final on the schedule, so its '
            'injury statuses are historical and may not reflect pre-game inactives. Its kickoff and network come from the injury page only.</div>'
            + table(["Game", "Date (ET)", "Kickoff", "Network", "Matchup (nfl.com)", "Away", "Home",
                     "Schedule check", "Source"], rows, "Week 10 games", "games", search=True))
    page("games.html", "Week 10 games · checked against NFL.com", "games.html", body)


def link_label(url):
    if "/injuries" in url:
        return "NFL injury report"
    if "/schedules" in url:
        return "NFL schedule"
    if "/stats" in url:
        return "NFL stats"
    return "NFL.com article"


def build_starters():
    rows = []
    for team, pos, starter, status, repl, urls, level in STARTERS:
        link = " · ".join(src(u.strip(), link_label(u.strip())) for u in urls.split(";"))
        rows.append([esc(team), esc(pos), esc(starter), esc(status),
                     esc(repl) if repl else "", "",  # blank = unverified (replacement)
                     link, esc(level)])
    body = (
        '<div class="notice"><strong>Backup-for-starter events, only where NFL.com states them.</strong> '
        'The NFL pages retrieved do not give depth charts or starter lists, so the team-wide '
        'starter/backup table is blank. Only QB and WR examples found in NFL.com headlines are shown. '
        'Blank cells are unverified.</div>'
        + table(["Team", "Pos", "Starter (as reported)", "Status (as reported)",
                 "Replacement (as reported)", "Official depth-chart check", "Source(s)", "Verification level"],
                rows, "Starter replacement register", "starters", search=True)
        + '<h2>Gap: team-wide depth charts</h2>'
        '<p>No official depth chart, starter list or game-day inactives article was captured for Week 10. '
        'Every 2nd/3rd-string classification is therefore '
        f'{unverified()} until a source is added. See the Questions page (Q03, Q06, Q09).</p>'
    )
    page("starters.html", "Starters, backups & replacement register", "starters.html", body)


def build_strategies():
    headers = ["Bet type / approach", "What it would need", "Input status", "Source(s) for inputs",
               "Edge / ROI", "Correlation", "Gate result", "Status"]
    rows = [
        ["Game side (spread) — own line origination",
         "Verified closing and opening prices, scores, timestamps", "Blank — no verified price source",
         src("https://www.nfl.com/schedules/2026/REG10", "NFL schedule (scores)") + " (scores only)",
         "", "", "", badge("Not started", "flag")],
        ["Game total (over/under)",
         "Verified prices and final totals", "Blank — no verified price source",
         src("https://www.nfl.com/schedules/2026/REG10", "NFL schedule (scores)") + " (scores only)",
         "", "", "", badge("Not started", "flag")],
        ["Moneyline",
         "Verified prices", "Blank — no verified price source", src(INJ_URL, "nfl.com injuries (checked; no prices)") + " · " + src(SCHED_URL, "nfl.com schedule (checked; no prices)"),
         "", "", "", badge("Not started", "flag")],
        ["Two-leg or multi-leg parlay",
         "Verified prices for each leg plus paired outcomes to measure correlation",
         "Blank", src(SCHED_URL, "nfl.com schedule (checked; no prices)"), "", "", "", badge("Not started", "flag")],
        ["Player prop (yardage, TDs)",
         "Verified player stats per game and verified prop prices",
         "Stats partly reachable (nfl.com/stats); prices blank",
         src("https://www.nfl.com/stats/team-stats/", "NFL stats (team pages)"), "", "", "", badge("Not started", "flag")],
        ["Injury-driven signal (starter Out, backup starts)",
         "Starter/backup list per team per week; injury history; outcome data",
         "Week 10 injury rows captured; starter list blank; history not archived",
         src(INJ_URL, "NFL injury report") + "; " + src("https://www.nfl.com/news/sam-darnold-ruled-out-for-seahawks-week-10-game-vs-raiders-drew-lock-expected-to-start-again", "NFL.com headline"),
         "", "", "", badge("Blocked by missing data", "flag")],
    ]
    body = (
        '<div class="notice"><strong>Leaderboard status: no strategy has been tested or validated.</strong> '
        'No ROI, correlation, p-value or gate result is reported, because no verified price history exists in this dashboard. '
        'Empty fields are unverified, never zero.</div>'
        '<h2>Singapore legal position (read before any use)</h2>'
        '<div class="notice warn"><p>The Gambling Regulatory Authority states: it is unlawful for any person to provide unlicensed remote gambling services '
        'in or from Singapore, or from outside Singapore to persons situated in Singapore. Singapore Pools (Private) Limited is the only operator '
        'licensed by GRA to provide remote gambling services. It is also an offence for any person in Singapore to take part in unlicensed remote '
        f'gambling activities. Source: {src(GRA_URL, "GRA: Unlawful Remote Gambling Activities")}. '
        f'Singapore Pools official site: {src(SP_URL, "singaporepools.com.sg")}.</p>'
        '<p>Nothing in this dashboard is betting advice. Any wagering decision is the owner\'s, and must comply with Singapore law.</p></div>'
        '<h2>Strategy registry (all unvalidated)</h2>'
        + table(headers, rows, "Strategy registry", "strat")
        + '<h2>Validation gates</h2>'
        '<p>The repository states different gate counts: the root site says seven, and site/ and parts of the research say eleven. '
        'The research subsite uses G1–G5. No gate list is treated as authoritative here until the owner decides (see Questions Q13 and Repo review).</p>'
    )
    page("strategies.html", "Strategies, lines & validation status", "strategies.html", body)


def build_questions():
    headers = ["#", "Question", "What we know (verified, with source)", "What is missing",
               "How to resolve (proposal)", "Status", "Source"]
    rows = []
    for q in QUESTIONS:
        status = badge(q[5], "decide" if "Decision" in q[5] else "flag")
        links = " · ".join(src(u, l) for u, l in QSRC[q[0]])
        rows.append([esc(q[0]), esc(q[1]), esc(q[2]), esc(q[3]), esc(q[4]), status, links])
    body = ('<p class="lead">Questions that must be answered before any decision can reasonably be made. '
            'Each row says what is known, what is missing, and how to close the gap.</p>'
            + table(headers, rows, "Questions and information gaps", "questions", search=True))
    page("questions.html", "Questions & information gaps", "questions.html", body)


def build_suggestions():
    headers = ["#", "Suggestion", "Why it helps", "Cost / risk", "Options for the owner", "Status", "Basis (source)"]
    rows = []
    for s in SUGGESTIONS:
        basis = src(SSRC[s[0]][0], SSRC[s[0]][1])
        rows.append([esc(s[0]), esc(s[1]), esc(s[2]), esc(s[3]), esc(s[4]), badge("Proposed — not implemented", "decide"), basis])
    body = ('<p class="lead">Proposals only. None of these has been implemented. '
            'Choose the path you want first; each option is listed beside its suggestion.</p>'
            + table(headers, rows, "Suggestions for review", "sugg", search=True))
    page("suggestions.html", "Suggestions for review (not implemented)", "suggestions.html", body)


def build_repo_review():
    headers = ["Path", "What it is", "Finding", "Verification", "Link"]
    rows = []
    for path, what, finding, verif, link in REPO:
        rows.append([esc(path), esc(what), esc(finding), esc(verif), link])
    body = ('<p class="lead">Repository review (read on 2026-11-14). Each row cites the file path in GitHub. '
            'Findings are about the repository itself, not about NFL data.</p>'
            + table(headers, rows, "Repository review", "repo", search=True))
    page("repo-review.html", "Repository review", "repo-review.html", body)


def build_sources():
    headers = ["Source", "What was checked", "Date checked (UTC)", "Limit of this check"]
    rows = []
    for url, what, limit in SOURCES:
        rows.append([src(url, url), esc(what), RETRIEVED, esc(limit)])
    body = ('<p class="lead">Every source below was opened by the build session on the date shown. '
            'Pages are live and may change; the date is the verification date.</p>'
            + table(headers, rows, "Sources", "sources", search=True))
    page("sources.html", "Sources & verification log", "sources.html", body)


def build_flags():
    headers = ["#", "Item", "Why flagged", "Evidence / link", "Status"]
    rows = []
    for fid, item, why, link in FLAGS:
        rows.append([esc(fid), esc(item), esc(why), link, badge("Needs review", "decide")])
    body = ('<div class="notice warn"><strong>Flagged for Review.</strong> These items do not block publication. '
            'They are published so the owner can review them, with source links, and request changes.</div>'
            + table(headers, rows, "Flagged items", "flags", search=True))
    page("flags.html", "Flagged for Review", "flags.html", body)


def build_summary():
    items = "".join(f"<li>{x}</li>" for x in SUMMARY)
    body = (f'<div class="notice"><strong>Bottom line.</strong> The official Week 10 data is captured and cross-checked. '
            f'The model and strategy work is not done, because the verified inputs it needs are missing. '
            f'Nothing here recommends a bet.</div>'
            f'<h2>Key points</h2><ul class="points">{items}</ul>'
            f'<h2>Decisions needed from the owner</h2>'
            + table(["#", "Decision", "Options", "Where (page)", "Basis (source)"],
                    [[esc(d[0]), esc(d[1]), esc(d[2]), src(DSRC[d[0]], d[3]), src(*DBASIS[d[0]])] for d in DECISIONS],
                    "Decisions", "dec")
            + f'<p class="note">Figures are counts from the Week 10 rows. Source list: {src("sources.html", "Sources page")}.</p>')
    page("summary.html", "Executive summary", "summary.html", body)


def build_index():
    cards = [
        ("summary.html", "01", "Executive summary", "Bottom line, key points, decisions"),
        ("injuries.html", "02", "Injuries", f"{TOTAL_ROWS} official rows · Week 10"),
        ("games.html", "03", "Games", f"{GAME_COUNT} matchups checked vs NFL.com"),
        ("starters.html", "04", "Starters & backups", "Official replacements only · gaps blank"),
        ("strategies.html", "05", "Strategies & lines", "0 validated · no verified prices"),
        ("questions.html", "06", "Questions", f"{len(QUESTIONS)} open information gaps"),
        ("suggestions.html", "07", "Suggestions", f"{len(SUGGESTIONS)} proposals · not implemented"),
        ("repo-review.html", "08", "Repo review", f"{len(REPO)} files reviewed with links"),
        ("sources.html", "09", "Sources", f"{len(SOURCES)} official / legal sources logged"),
        ("flags.html", "10", "Flagged for Review", f"{len(FLAGS)} items for the owner"),
    ]
    card_html = "".join(f'<a class="card" href="{h}"><span>{n}</span><b>{esc(t)}</b><p>{esc(d)}</p></a>'
                        for h, n, t, d in cards)
    body = (
        '<div class="notice warn"><strong>Research only. No wagering advice.</strong> '
        f'Singapore law: unlicensed remote gambling is unlawful, and Singapore Pools is the only GRA-licensed remote operator. '
        f'{src(GRA_URL, "GRA source")}</div>'
        '<p class="lead">An evidence dashboard for NFL injuries, depth gaps, and strategy research. '
        'Every row links to an official source. Missing values stay blank and are flagged.</p>'
        f'<div class="cards">{card_html}</div>'
        '<h2>At a glance</h2>'
        + table(["Area", "Status", "Detail", "Source"], [
            ["Injury report (Week 10)", badge("Captured & cross-checked", "ok"), f"{TOTAL_ROWS} rows across {GAME_COUNT} games; statuses as displayed on NFL.com", src(INJ_URL, "nfl.com/injuries")],
            ["Starter / backup depth", badge("Gap", "flag"), "No official depth chart captured; team-wide classification left blank", src(INJ_URL, "nfl.com/injuries (checked; no depth chart)")],
            ["Betting lines & prices", badge("Gap", "flag"), "No verified price source in this dashboard", src(SCHED_URL, "nfl.com schedule (checked; no prices)")],
            ["Strategies validated", badge("None", "flag"), "0 strategies tested or validated", src("https://github.com/sassnarep3-star/Own9/blob/arena/8b05dd6d-own9/session-8b05dd6d/data/games_week10.psv", "project record (no validation data)")],
            ["Singapore legality", badge("Decision needed", "decide"), "Only Singapore Pools is licensed (GRA)", src(GRA_URL, "GRA")],
        ], "Status at a glance", "glance")
    )
    page("index.html", "Overview", "index.html", body)


# ---------- content ----------
QSRC = {
    "Q01": [(SP_URL, "singaporepools.com.sg"), (GRA_URL, "GRA")],
    "Q02": [(GRA_URL, "GRA")],
    "Q03": [(INJ_URL, "nfl.com injuries")],
    "Q04": [(INJ_URL, "nfl.com injuries"), ("https://www.nfl.com/news/ravens-qb-tyler-huntley-out-for-season-turf-toe-injury", "NFL.com headline")],
    "Q05": [(INJ_URL, "nfl.com injuries")],
    "Q06": [("https://www.nfl.com/news/nfl-week-9-inactives-players-ruled-out-sunday-2026-season", "NFL.com Week 9 inactives")],
    "Q07": [(INJ_URL, "nfl.com injuries")],
    "Q08": [(SCHED_URL, "nfl.com schedule"), ("https://www.nfl.com/stats/team-stats/", "nfl.com stats")],
    "Q09": [(INJ_URL, "nfl.com injuries (no definition found)")],
    "Q10": [("https://github.com/sassnarep3-star/Own9/blob/main/index.html", "root index"), ("https://github.com/sassnarep3-star/Own9/tree/main/site", "site/")],
    "Q11": [("https://github.com/sassnarep3-star/Own9", "repository (no LICENSE)")],
    "Q12": [(SP_URL, "singaporepools.com.sg"), (GRA_URL, "GRA")],
    "Q13": [("https://github.com/sassnarep3-star/Own9/blob/main/docs/RESEARCH_SPEC.md", "RESEARCH_SPEC.md (not line-reviewed)")],
    "Q14": [("https://github.com/sassnarep3-star/Own9", "repository")],
}
SSRC = {
    "S01": (GRA_URL, "GRA"), "S02": (INJ_URL, "nfl.com injuries"), "S03": (INJ_URL, "nfl.com injuries"),
    "S04": ("https://www.nfl.com/news/nfl-week-9-inactives-players-ruled-out-sunday-2026-season", "NFL.com inactives"),
    "S05": ("https://github.com/sassnarep3-star/Own9/tree/main/site", "site/"),
    "S06": ("https://github.com/sassnarep3-star/Own9/blob/main/index.html", "root index"),
    "S07": ("https://github.com/sassnarep3-star/Own9/blob/main/docs/RESEARCH_SPEC.md", "RESEARCH_SPEC.md"),
    "S08": (INJ_URL, "nfl.com injuries"), "S09": (SP_URL, "singaporepools.com.sg"),
    "S10": (INJ_URL, "nfl.com injuries"), "S11": (GRA_URL, "GRA"),
}
DSRC = {"D1": "questions.html", "D2": "suggestions.html", "D3": "questions.html", "D4": "questions.html", "D5": "repo-review.html"}
DBASIS = {
    "D1": (GRA_URL, "GRA"), "D2": ("https://github.com/sassnarep3-star/Own9/tree/arena/8b05dd6d-own9/session-8b05dd6d", "session folder (project record)"),
    "D3": ("https://github.com/sassnarep3-star/Own9/blob/main/index.html", "root index"),
    "D4": (INJ_URL, "nfl.com injuries"), "D5": ("https://github.com/sassnarep3-star/Own9/tree/main/site", "site/"),
}

QUESTIONS = [
    ["Q01", "Where can a verified, timestamped betting line for each NFL game be obtained?",
     "The NFL.com injury and schedule pages checked contain no betting lines. GRA: Singapore Pools is the only licensed remote operator.",
     "Price history, timestamps and whether Singapore Pools publishes the NFL markets needed",
     "Check Singapore Pools' official product and pricing pages before any design work.", "Unanswered"],
    ["Q02", "Is the owner allowed to act on any strategy?",
     "GRA: unlicensed remote gambling is unlawful in or from Singapore; taking part is an offence (fine up to $10,000, up to 6 months' jail, or both).",
     "The owner's purpose (research only, or real wagers)", "Owner decision. Seek legal advice before any real-money use.", "Decision required"],
    ["Q03", "Who are the starters and backups for each team this week?",
     "The injury report gives statuses but not starter or backup roles.",
     "Official depth chart or starter list for each team, timestamped", "Capture NFL.com team depth charts or game-day inactives (Suggestion S03).", "Unverified"],
    ["Q04", "Does the injury report include players on injured reserve?",
     "Lamar Jackson (BAL) and Malik Willis (MIA) do not appear in the Week 10 tables, though NFL.com headlines say they were placed on IR.",
     "The report's scope definition", "Find NFL's published injury-report rules and confirm scope. Until then, treat the report as possibly incomplete.", "Unresolved"],
    ["Q05", "When was the Week 10 injury report last updated?",
     "The page shows no update timestamp.", "Update times for each snapshot", "Capture snapshots at fixed times with the capture time recorded (S02).", "Unresolved"],
    ["Q06", "Do game-day inactives match the injury report's Out list?",
     "NFL.com publishes 'Week N inactives' articles; Week 8 and Week 9 headlines were seen on the injury page.",
     "The Week 10 inactives article was not retrieved in this session", "Retrieve the Week 10 inactives article and compare it with the report (S04).", "Open"],
    ["Q07", "Is there a machine-readable injury history for backtests?",
     "The injury page offers week selectors for 2026 back to 1965.",
     "A verified archive and confirmation of NFL terms of use", "Confirm NFL terms; archive weekly from now on (S02).", "Open"],
    ["Q08", "Are NFL scores and stats acceptable as official grading data?",
     "The Week 10 schedule was checked against the injury page; the Thursday final score (24-21) is on the schedule. The 2026 team stats page loads.",
     "A complete verified results history; terms for reuse", "Pull weekly schedule results and verify each row against NFL.com.", "Partly verified"],
    ["Q09", "What counts as a '2nd or 3rd string backup'?",
     "No official page retrieved defines depth tiers.", "A definition the owner accepts, and a source for it",
     "Owner decision on the definition; then capture the source (Suggestion S03).", "Decision required"],
    ["Q10", "Which validation gate list is authoritative?",
     "Repository files state seven gates (root) and eleven (site/ and parts of research); the research subsite uses G1–G5.",
     "One agreed gate list", "Owner decision; then one generated gate registry (Suggestion S06).", "Decision required"],
    ["Q11", "Can the repository's secondary NFL dataset be reused?",
     "No LICENSE file exists in the repository (file listing, 2026-11-14). data/raw/games.csv is a copy of an external dataset.",
     "Upstream licence confirmation", "Check the upstream repository licence; otherwise remove or label the copy.", "Open"],
    ["Q12", "Which sports-betting markets are offered to Singapore residents?",
     "Singapore Pools is the only GRA-licensed remote operator. Its product list was not checked on its own site in this session.",
     "The official Singapore Pools product list", "Check the official Singapore Pools site (Q01).", "Unverified"],
    ["Q13", "What must a strategy show before it counts as skill?",
     "Repository gate definitions conflict (Q10). No strategy has been tested.",
     "Pre-registered test rules: sample size, metric, holdout period, multiple-testing correction", "Owner decision on the rules before any test (Suggestion S07).", "Decision required"],
    ["Q14", "Is a paid or licensed data budget available?",
     "Not stated anywhere in the repository.", "Budget decision", "Owner decision. The dashboard works without paid data.", "Decision required"],
]

SUGGESTIONS = [
    ["S01", "Add a legal-status gate: no strategy is marked actionable for a Singapore resident unless the owner confirms a lawful channel.",
     "Stops the dashboard implying that offshore betting is an option.", "Low", "Approve / Modify / Reject"],
    ["S02", "Archive each official injury-report snapshot (raw HTML, capture time, SHA-256 hash) at fixed times.",
     "Makes injury history verifiable and enables backtests (Q05, Q07).", "Storage; needs a capture schedule", "Approve / Defer / Reject"],
    ["S03", "Capture official team depth charts each week, and fill starter/backup cells only from that source.",
     "Fills the largest gap (2nd/3rd-string analysis).", "Source format and terms need checking (Q03, Q09)", "Approve / Defer / Reject"],
    ["S04", "Capture the Week N inactives article and join it to the injury report.",
     "Shows which Out players were actually ruled out for kickoff (Q06).", "Manual-looking step if not automated", "Approve / Defer / Reject"],
    ["S05", "Consolidate the repository's overlapping dashboards into one canonical site; archive the rest with a note.",
     "Removes contradictory counts and duplicate data (Repo review).", "Affects other sessions' work; needs owner decision", "Consolidate / Keep separate / Defer"],
    ["S06", "Generate one gate registry from a single file, and let every page read from it.",
     "Resolves the 7 vs 11 gate conflict (Q10).", "Low; requires choosing the list", "Adopt one list / Defer"],
    ["S07", "Pre-register each strategy (hypothesis, data source, date range, metric, holdout) before any test.",
     "Separates testing from fitting, the main protection against luck.", "Discipline, not cost", "Approve / Modify"],
    ["S08", "Restrict the injury signal to pre-stated events: a listed starter is Out and a named backup starts, with the outcome window fixed in advance.",
     "A narrow, testable signal instead of a broad one.", "Needs starter data first (Q03)", "Approve / Defer"],
    ["S09", "Only if the owner chooses a lawful channel: record Singapore Pools prices, if its terms allow, using owner-supplied records.",
     "Gives a legal price source, the main missing input.", "Terms and legality must be checked first (Q01, Q02)", "Approve after legal check / Reject"],
    ["S10", "Show a 'last verified' date and snapshot link on every row.",
     "Lets a reviewer see how old each value is.", "Low", "Approve / Modify"],
    ["S11", "Add the Singapore responsible-gambling and GRA links to the overview page.",
     "Makes the legal and harm-minimisation context visible at the start.", "Low", "Approve / Reject"],
]

REPO = [
    ["README.md", "Root project overview",
     "Refers to the root dashboard and says 'Live dashboard' without date context; its figures predate this session.",
     "Read in full.", src("https://github.com/sassnarep3-star/Own9/blob/main/README.md", "GitHub")],
    ["COORDINATION.md", "Shared task board across sessions",
     "Over 300 lines of superseded boards; several 'done' and 'needs review' items conflict about status.",
     "Read the section headers and the latest claims.", src("https://github.com/sassnarep3-star/Own9/blob/main/COORDINATION.md", "GitHub")],
    ["index.html (root)", "Root overview page",
     "Says 'As of 04 Nov 2026', but the current date is 14 Nov 2026.",
     "Read the page text.", src("https://github.com/sassnarep3-star/Own9/blob/main/index.html", "GitHub")],
    ["site/ (leaderboard, audit)", "Dashboard from another session",
     "States 'eleven gates'; the root states 'seven' (see Q10).",
     "Searched text in the file.", src("https://github.com/sassnarep3-star/Own9/tree/main/site", "GitHub")],
    ["research/", "Research subsite (secondary data)",
     "Uses G1–G5 gates; relies on an unlicensed secondary dataset copy (Q11).",
     "Read the catalog and flagged files.", src("https://github.com/sassnarep3-star/Own9/tree/main/research", "GitHub")],
    ["own9-research/", "Parallel research subsite",
     "Holds its own copy of games data (data/source/games.csv), duplicating other copies.",
     "Listed the directory.", src("https://github.com/sassnarep3-star/Own9/tree/main/own9-research", "GitHub")],
    ["data/raw/games.csv", "Secondary dataset copy",
     "No licence in the repository (see Q11).", "Listed; licence absent.", src("https://github.com/sassnarep3-star/Own9/blob/main/data/raw/games.csv", "GitHub")],
    ["LICENSE", "Repository licence file",
     "Missing. The repository has no licence file.", "Directory listing, 2026-11-14.", src("https://github.com/sassnarep3-star/Own9", "GitHub repository")],
    ["evidence/sources.json", "Machine-readable source manifest",
     "Lists nfl.com/injuries and nfl.com/stats; both were reachable on 2026-11-14.",
     "Read the NFL URL entries.", src("https://github.com/sassnarep3-star/Own9/blob/main/evidence/sources.json", "GitHub")],
    ["research/catalog.json", "Source catalog from another session",
     "Cites operations.nfl.com 2026 rulebook; the page loaded on 2026-11-14 (page 1 of 3).",
     "Fetched cited URL.", src("https://github.com/sassnarep3-star/Own9/blob/main/research/catalog.json", "GitHub")],
    [".github/workflows/pages.yml", "Pages build workflow",
     "Runs on main and a fixed session branch; this folder is published automatically and is not covered by its checks.",
     "Read the file.", src("https://github.com/sassnarep3-star/Own9/blob/main/.github/workflows/pages.yml", "GitHub")],
    ["session-8b05dd6d/", "This session's additive dashboard",
     "New folder only. No other session's files edited.", "Built and link-checked by tools/check.py.",
     src("https://github.com/sassnarep3-star/Own9/tree/arena/8b05dd6d-own9/session-8b05dd6d", "GitHub branch")],
]

SOURCES = [
    ("https://www.nfl.com/injuries/", "All eight pages of the Week 10 2026 injury report read; every listed row transcribed.",
     "The page shows no update time. Statuses are as displayed at the time of reading."),
    ("https://www.nfl.com/schedules/2026/REG10", "Week 10 2026 schedule: matchups, kickoff times, networks, Thursday final score. Fetch returned the nfl.com/schedules page.",
     "Week 10 only. Kickoff times for the Thursday game were taken from the injury page."),
    ("https://www.nfl.com/news/sam-darnold-ruled-out-for-seahawks-week-10-game-vs-raiders-drew-lock-expected-to-start-again",
     "Headline text, as listed on the injury page, for starter/backup examples.", "Headline only; article bodies not opened."),
    ("https://www.nfl.com/news/drew-lock-no-injury-designation-seahawks-raiders", "Headline text (as listed on the injury page).", "Headline only."),
    ("https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-friday-nov-13", "Headline text (Nov 13 roundup).", "Headline only; conflicting week range (6-10) flagged."),
    ("https://www.nfl.com/news/ravens-lamar-jackson-right-thumb-out-6-9-weeks-expects-to-return-this-season", "Headline text (NFL Network via NFL.com).", "Headline only; conflicting week range (6-9) flagged."),
    ("https://www.nfl.com/news/dolphins-place-qb-malik-willis-groin-on-injured-reserve-kyle-mccord-in-line-for-first-start", "Headline text.", "Headline only."),
    ("https://www.nfl.com/stats/team-stats/", "2026 REG team stats page loaded (offense passing table).", "Reachability only; no stats used."),
    ("https://operations.nfl.com/rules-officiating/2026-nfl-rulebook", "Loaded page 1 of 3 (2026 rule-change table).", "Reachability only; no rules used."),
    (GRA_URL, "Read: unlawful remote gambling, Singapore Pools as the only licensed operator, penalties.", "Official GRA page; not legal advice."),
    ("https://www.gra.gov.sg/", "Homepage read; regulated products list includes Lottery & Betting.", "Context only."),
    ("https://www.singaporepools.com.sg/", "Linked as the official operator site; not opened in this session.", "Product list unverified (Q12)."),
]

FLAGS = [
    ["F01", "Thursday game statuses are stale", "The nfl.com schedule shows Commanders 24, Giants 21 (Final), but the injury page still lists game statuses for that game.",
     src(SCHED_URL, "schedule") + " · " + src(INJ_URL, "injury report")],
    ["F02", "Injured-reserve players not in the report", "Lamar Jackson (BAL) and Malik Willis (MIA) are absent from the tables, while NFL.com headlines say they were placed on injured reserve.",
     src("https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-thursday-nov-5", "Nov 5 roundup") + " · " + src("https://www.nfl.com/news/dolphins-place-qb-malik-willis-groin-on-injured-reserve-kyle-mccord-in-line-for-first-start", "Willis headline")],
    ["F03", "Conflicting Lamar Jackson timelines", "NFL.com headlines give 6-9 weeks (NFL Network) and 6-10 weeks (Ravens confirm, Nov 13).",
     src("https://www.nfl.com/news/ravens-lamar-jackson-right-thumb-out-6-9-weeks-expects-to-return-this-season", "6-9 weeks") + " · " + src("https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-friday-nov-13", "6-10 weeks")],
    ["F04", "Puka Nacua listed without designation", "The report shows no injury or game status, while the headline says he is likely to go on injured reserve.",
     src(INJ_URL, "injury report") + " · " + src("https://www.nfl.com/news/rams-wr-puka-nacua-likely-to-be-placed-on-injured-reserve-with-turf-toe-sprained-mcl-and-pcl", "headline")],
    ["F05", "Garrett Wilson: ruled out vs questionable", "A Nov 6 headline says ruled out; the Week 10 report shows Concussion, Full Participation, Questionable. Dates differ.",
     src("https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-friday-nov-6", "Nov 6") + " · " + src(INJ_URL, "report")],
    ["F06", "No update timestamp on the injury page", "Snapshots cannot be dated from the page itself.", src(INJ_URL, "injury report")],
    ["F07", "Patriots at Lions venue unclear", "The schedule groups this game under an 'International Game, Munich' heading. The venue was not confirmed.",
     src(SCHED_URL, "schedule")],
    ["F08", "'Not injury related' entries", f"{NOT_INJURY} rows say 'Not injury related' (e.g., resting, personal matter). They are counted as Out in the totals, as displayed.",
     src(INJ_URL, "injury report")],
    ["F09", "Singapore legal status", "Only Singapore Pools is GRA-licensed for remote gambling. Taking part in unlicensed remote gambling is an offence for a person in Singapore. Owner must decide purpose.",
     src(GRA_URL, "GRA")],
    ["F10", "Conflicting validation-gate counts in the repository", "Root says seven; site/ says eleven; research uses G1–G5.",
     src("https://github.com/sassnarep3-star/Own9/blob/main/index.html", "root index") + " · " + src("https://github.com/sassnarep3-star/Own9/tree/main/site", "site/")],
    ["F11", "No repository licence", "No LICENSE file. A secondary NFL dataset copy is in data/raw/.", src("https://github.com/sassnarep3-star/Own9", "repository")],
    ["F12", "Overlapping dashboards", "Several parallel sites (root, site/, research/, own9-research/, strict-lab/, release-checks/) cover the same topics with different numbers.",
     src("https://github.com/sassnarep3-star/Own9/blob/main/COORDINATION.md", "COORDINATION.md")],
    ["F13", "Stale date on root overview", "Root index says 'As of 04 Nov 2026'; today is 14 Nov 2026.", src("https://github.com/sassnarep3-star/Own9/blob/main/index.html", "root index")],
    ["F14", "Earlier claims not re-verified here", "Other sessions' empirical results and flagged mismatches (e.g., a 2026 Week 9 kickoff) were not re-checked in this session.",
     src("https://github.com/sassnarep3-star/Own9/blob/main/COORDINATION.md", "COORDINATION.md")],
]

DECISIONS = [
    ["D1", "Purpose of this work: research only, or real wagers?", "Research only / real wagers (requires legal advice and a Singapore Pools channel)", "Questions Q02"],
    ["D2", "Which suggestions to implement", "Approve / Modify / Reject each of S01–S11", "Suggestions"],
    ["D3", "Which validation gate list is official", "Adopt one list / Defer", "Questions Q10"],
    ["D4", "Definition of '2nd or 3rd string backup'", "Owner definition", "Questions Q09"],
    ["D5", "Consolidate overlapping dashboards", "Consolidate / Keep separate", "Repo review"],
]

SUMMARY = [
    f"<b>Official injury data captured:</b> {TOTAL_ROWS} rows across {GAME_COUNT} Week 10 games from the NFL.com injury report. {COUNTS['Out']} Out, {COUNTS['Doubtful']} Doubtful, {COUNTS['Questionable']} Questionable. Each row links to the report.",
    "<b>Schedule cross-check:</b> all 14 matchups match the NFL.com Week 10 schedule. The 13 Sunday and Monday kickoff times and networks match it too. For the Thursday game, the schedule shows the final score (Commanders 24, Giants 21), and its kickoff and network come from the injury page only.",
    "<b>Depth gap:</b> the NFL pages checked do not state starters or backups for teams. Starter/backup cells are blank. Only NFL.com-stated QB and WR replacements are shown (Starters page).",
    "<b>Injured-reserve scope is unclear:</b> Lamar Jackson and Malik Willis are absent from the report, though headlines say they went on IR. This must be resolved before the report is treated as complete.",
    "<b>No line origination yet:</b> no verified price source is in this dashboard. The NFL pages carry no betting lines. Zero strategies are tested or validated.",
    "<b>Singapore law:</b> GRA states that only Singapore Pools is licensed for remote gambling, and that taking part in unlicensed remote gambling is an offence. Any use of this work for wagering is an owner decision that must comply with that law.",
    "<b>Repository:</b> several sites contradict each other (gate counts, dates, duplicate data), and there is no licence file (Repo review).",
]


def build_all():
    os.makedirs(os.path.join(ROOT, "assets"), exist_ok=True)
    build_index()
    build_summary()
    build_injuries()
    build_games()
    build_starters()
    build_strategies()
    build_questions()
    build_suggestions()
    build_repo_review()
    build_sources()
    build_flags()
    # CSV exports
    export_csv("injuries.csv", ["game_id", "matchup", "team", "player", "position", "group", "injury",
                                "practice", "game_status", "starter_backup", "source"],
               [[r[k] for k in ["game_id", "matchup", "team", "player", "position", "group", "injury",
                                "practice", "game_status", "starter_backup", "source"]] for r in INJ_ROWS])
    export_csv("games.csv", ["game_id", "day_date_et", "kickoff_et", "network", "matchup", "away", "home",
                             "schedule_check", "source"],
               [g + [SCHED_URL] for g in GAMES])


def export_csv(name, header, rows):
    with open(os.path.join(DATA, name), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


if __name__ == "__main__":
    build_all()
    print(f"built {len(os.listdir(ROOT))} entries; injury rows={TOTAL_ROWS}; games={GAME_COUNT}")
