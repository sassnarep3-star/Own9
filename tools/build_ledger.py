"""Build the consolidated Own9 ledger site in ledger/ from data/ledger/ and research/catalog.json.

Deterministic, standard library only. Every table row must cite at least one registered
source; the build fails otherwise. Blank cells mean unverified or not published, never an estimate.

    python3 tools/build_ledger.py          # write ledger/
    python3 tools/build_ledger.py --check  # fail if committed ledger/ differs from the build
"""
from __future__ import annotations

import csv
import html
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import ledger as L  # noqa: E402

OUT = ROOT / "ledger"
AS_OF = "2026-11-14"
E = html.escape

NAV = [
    ("index", "Overview"), ("prices", "Price store"), ("lines", "Lines"), ("results", "Results"),
    ("replacements", "Injuries & depth"), ("leaderboard", "Leaderboard"), ("correlations", "Correlations"),
    ("gates", "Gates & demotion"), ("questions", "Questions"), ("suggestions", "Suggestions"),
    ("flags", "Flagged for Review"), ("sources", "Sources"),
]


# ---------------------------------------------------------------- sources
def load_sources() -> dict[str, dict]:
    reg: dict[str, dict] = {}
    cat = json.loads((ROOT / "research/catalog.json").read_text(encoding="utf-8"))
    for s in cat["sources"]:
        reg[s["id"]] = {"id": s["id"], "publisher": s.get("publisher", s.get("title", "")), "type": "Catalog source",
                        "url": s["url"], "checked": cat["as_of"], "status": "carried (research/catalog.json)",
                        "scope": s.get("title", "")}
    for s in L.load_json("sources.json")["sources"]:
        reg[s["id"]] = s  # ledger registry takes precedence
    return reg


SOURCES = load_sources()


def src_links(ids: list[str]) -> str:
    if not ids:
        return '<span class="blank" title="No source: value is blank">no source</span>'
    parts = []
    for sid in ids:
        if sid not in SOURCES:
            raise SystemExit(f"unregistered source id: {sid}")
        s = SOURCES[sid]
        parts.append(f'<a href="{E(s["url"], quote=True)}" target="_blank" rel="noopener noreferrer" '
                     f'title="{E(s.get("publisher", ""))} · {E(s.get("type", ""))}">{E(sid)} <span aria-hidden="true">↗</span></a>')
    return '<span class="links">' + " ".join(parts) + "</span>"


# ---------------------------------------------------------------- cell helpers
def blank(reason: str = "Unverified or not published: left blank, not inferred") -> str:
    return f'<span class="blank" title="{E(reason)}"><span class="sr-only">Blank: {E(reason)}</span>—</span>'


def cell(v) -> str:
    if v is None or v == "":
        return blank()
    if isinstance(v, str) and v.startswith("<"):
        return v  # pre-escaped HTML fragment built by this module
    return E(str(v))


def badge(v: str) -> str:
    low = v.lower()
    if any(k in low for k in ("not ", "blocked", "unverified", "pending", "awaiting", "unanswered", "critical", "high", "flagged", "not evaluated", "partly", "no ")):
        cls = "amber"
    elif any(k in low for k in ("answered", "verified", "read", "done", "published", "clear")):
        cls = "green"
    else:
        cls = "neutral"
    return f'<span class="badge {cls}">{E(v)}</span>'


EXPORTS: dict[str, tuple[list[str], list[list[str]]]] = {}


def plain(v) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", str(v))).strip() if v not in (None, "") else ""


def table(tid: str, title: str, columns: list[str], rows: list[dict], note: str = "") -> str:
    """rows: dict with 'cells' (list of str/HTML) and 'sources' (list of ids, required)."""
    EXPORTS[tid] = (columns + ["Sources (id and URL)"], [
        [plain(c) for c in r["cells"]] + ["; ".join(f'{i} {SOURCES[i]["url"]}' for i in r["sources"] if i in SOURCES)]
        for r in rows])
    head = "".join(f'<th scope="col">{E(c)}</th>' for c in columns + ["Source (official or named)"])
    body = []
    for i, r in enumerate(rows, 1):
        if not r.get("sources"):
            raise SystemExit(f"{tid} row {i} has no source id")
        tds = "".join(f"<td>{cell(c)}</td>" for c in r["cells"])
        body.append(f'<tr id="{E(tid)}-{i}">{tds}<td>{src_links(r["sources"])}</td></tr>')
    note_html = f'<p class="note">{note}</p>' if note else ""
    return (f'<section class="panel" id="{E(tid)}"><div class="panel-head"><div><h2>{E(title)}</h2>{note_html}</div>'
            f'<div class="tools"><input type="search" class="filter" data-table="{E(tid)}-table" placeholder="Filter rows" aria-label="Filter rows in {E(title)}">'
            f'</div></div><div class="scroll" tabindex="0" role="region" aria-label="{E(title)}">'
            f'<table id="{E(tid)}-table" class="data"><caption class="sr-only">{E(title)}. Blank cells are unverified or not published.</caption>'
            f'<thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'
            f'<p class="row-count"><span>{len(rows)} rows</span> · <a href="data/{E(tid)}.csv" download>Download CSV</a></p></section>')


def stat(label: str, value: str, sub: str) -> str:
    return f'<div class="stat"><span class="stat-label">{E(label)}</span><strong>{E(value)}</strong><small>{E(sub)}</small></div>'


def page(slug: str, title: str, kicker: str, lead: str, body: str, desc: str) -> str:
    cur = ' aria-current="page"'
    nav = "".join('<a href="%s.html"%s>%s</a>' % (s, cur if s == slug else "", E(l)) for s, l in NAV)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="{E(desc)}"><title>{E(title)} · Own9 Ledger</title>
<link rel="stylesheet" href="assets/style.css"><script src="assets/app.js" defer></script></head>
<body><a class="skip" href="#main">Skip to content</a>
<header class="top"><a class="brand" href="index.html">Own9 <span>Ledger</span></a>
<nav aria-label="Main">{nav}</nav></header>
<main id="main"><section class="intro"><p class="kicker">{E(kicker)}</p><h1>{E(title)}</h1><p class="lead">{lead}</p></section>
{body}
</main>
<footer><p>Static snapshot built from <code>data/ledger/</code> on {AS_OF}. No live odds, no bets, no recommendations. Blank = unverified or not published.</p>
<p><a href="../index.html">Repository dashboard ↗</a> · <a href="../site/index.html">Research workspace ↗</a> · <a href="https://github.com/sassnarep3-star/Own9" target="_blank" rel="noopener noreferrer">Repository ↗</a></p></footer>
</body></html>
'''


def callout(title: str, body: str, kind: str = "notice") -> str:
    return f'<aside class="callout {kind}"><strong>{E(title)}</strong><div>{body}</div></aside>'


# ---------------------------------------------------------------- data
def data():
    results = L.load_csv("results_verified.csv")
    prices = L.load_csv("price_snapshots.csv")
    reps = L.load_csv("replacements.csv")
    policy = L.load_json("policy.json")
    questions = L.load_json("questions.json")["items"]
    suggestions = L.load_json("suggestions.json")
    flags = L.load_json("flags.json")["items"]
    cat = json.loads((ROOT / "research/catalog.json").read_text(encoding="utf-8"))
    return dict(results=results, prices=prices, reps=reps, policy=policy, questions=questions,
                suggestions=suggestions, flags=flags, cat=cat)


def build() -> dict[str, str]:
    d = data()
    errs = L.validate_results(d["results"]) + L.validate_prices(d["prices"]) + L.validate_replacements(d["reps"])
    if errs:
        raise SystemExit("ledger validation failed:\n" + "\n".join(errs))
    corr = d["cat"]["correlations"]
    cov = L.coverage(d["results"], d["prices"], d["reps"], {c["id"]: 0 for c in corr})
    gate_status = {g["id"]: "not evaluated" for g in d["cat"]["gates"]}
    strategies = d["cat"]["strategies"]
    pages: dict[str, str] = {}

    # ---- Overview
    stats = "".join([
        stat("Verified results", str(cov["verified_results"]), "official final scores, Weeks 9–10"),
        stat("Price rows", str(cov["price_rows"]), f'{cov["price_games"]} games · values withheld (unverified)'),
        stat("Opening / closing", f'{cov["open_values"]} / {cov["close_values"]}', "values captured"),
        stat("Fair lines", str(cov["fair_lines"]), "published from verified inputs"),
        stat("Replacement records", str(cov["replacement_records"]), f'{cov["depth_tiers_published"]} depth tiers published'),
        stat("Correlation coefficients", str(cov["correlation_coefficients"]), f'{cov["correlation_pairs"]} pairs · n = 0 official'),
        stat("Strategies eligible", f'0 of {len(strategies)}', "signal gates not evaluated"),
        stat("Demotion thresholds set", "0", "6 triggers defined; numbers proposed"),
        stat("Wagers placed · rewards funded", "0 · 0", "by design (see jurisdiction flag)"),
    ])
    summary_rows = [
        {"cells": ["Verified results", "16 official final scores: all 15 Week 9 games and the Week 10 Thursday game. Three also agree with official Game Books.", "Weeks 1–8 and the rest of Week 10; manual check of 13 game-centre pages.", "Choose the results scope (SX03)."], "sources": ["NFL-SCHED-W9", "NFL-SCHED-W10", "NFL-GB-W10-WASNYG"]},
        {"cells": ["Price store (open and close)", "48 market rows for 8 Week 10 games. All values withheld: the only price source is a non-official DraftKings page with no timestamp.", "Opening and closing values for every originated market (none recorded).", "Choose a capture method (SX02)."], "sources": ["DK-NFL-LEAGUE"]},
        {"cells": ["Own fair line and difference", "Not published. The policy order is fixed: side, then total, then moneyline.", "Verified multi-season inputs and a fitted, calibrated model.", "Choose the data scope and model (SX03, SX04)."], "sources": ["SK-TIME"]},
        {"cells": ["Injuries and replacement depth", "12 records: Week 9 to Week 10 starter changes for Washington and the Giants, one full replacement chain (Patrick to Allegretti at centre).", "Depth tiers are not published by the NFL. League-wide starter history is absent.", "Choose the depth-tier policy (SX07)."], "sources": ["NFL-GB-W10-WASNYG", "NFL-INJURY-W10"]},
        {"cells": ["Signal and staking leaderboard", "Two separate tracks are defined; staking cannot change signal rank. No strategy is eligible.", "All eleven gates unevaluated; no forecasts or bets.", "Accept the two-track rule (SX06)."], "sources": ["SP-BOOT", "SK-CV"]},
        {"cells": ["Correlations", "Eight pairs defined; publication rule set (n always shown, coefficients only with official pairs and n ≥ 30 proposed).", "Official paired observations (n = 0 for every pair).", "Choose the minimum n (SX09)."], "sources": ["SP-R"]},
        {"cells": ["Demotion gate", "Six triggers (D1 to D6) defined; a favourable staking run cannot cancel a signal trigger.", "Numeric thresholds have not been set by the owner.", "Choose thresholds (SX05)."], "sources": ["SK-CAL", "SP-BOOT"]},
        {"cells": ["Jurisdiction", "The user's location is unconfirmed. The Penal Code (Articles 185 and 186) criminalises gambling; the statute text is verified.", "A written legal determination for any stake or reward.", "Decide the scope (SX08) before any staking step."], "sources": ["EGOV-PENAL-CODE"]},
    ]
    overview_dir = [
        ("prices.html", "Price store", "48 market rows, open and close blank"),
        ("lines.html", "Lines", "Fair, market and difference columns in order: side, total, moneyline"),
        ("results.html", "Results", "16 verified official final scores"),
        ("replacements.html", "Injuries & depth", "Starter replacements, prior status, depth-tier policy, scenarios"),
        ("leaderboard.html", "Leaderboard", "Signal and staking tracks, kept separate"),
        ("correlations.html", "Correlations", "Eight pairs with n published"),
        ("gates.html", "Gates & demotion", "Eleven validation gates and six demotion triggers"),
        ("questions.html", "Questions", "What is known, what is missing, how to find it"),
        ("suggestions.html", "Suggestions", "Options to review; nothing implemented"),
        ("flags.html", "Flagged for Review", "Irregularities with source links; does not block"),
        ("sources.html", "Sources", "Every source, its status and scope"),
    ]
    dir_rows = [{"cells": [f'<a href="{h}">{E(t)}</a>', x, "Generated from data/ledger"], "sources": ["REPO-LEDGER"]} for h, t, x in overview_dir]
    body = (
        f'<section class="stats" aria-label="Key figures">{stats}</section>'
        + callout("Read this first", "Nothing here shows a betting edge, a backtest, or a verified ROI. The project cannot produce those yet: the price archive is empty, no fair line exists, and the jurisdiction question is open. Counts are computed from the data files; the zeros for wagers and rewards are statements of policy. Blanks are unverified, not zero estimates.", "warn")
        + table("summary", "Executive summary", ["Area", "What we have (verified)", "What is missing", "Next decision"], summary_rows,
                "Each row states only what the verified files support. Source links are on the right.")
        + table("directory", "Sections", ["Section", "What it contains", "Status"], dir_rows)
        + '<section class="panel"><h2>Start here</h2><ul class="actions">'
          '<li><a href="suggestions.html">Choose a path: review the 11 suggestions and their options</a></li>'
          '<li><a href="questions.html">Work through the 15 questions with what is still missing</a></li>'
          f'<li><a href="flags.html">Read the {len(d["flags"])} new flagged findings (F28 to F39)</a></li></ul>'
          '<p class="note">Earlier dashboards still exist in the repository: see the <a href="../index.html">repository dashboard</a>, which lists them with their own findings.</p></section>'
    )
    pages["index"] = page("index", "Executive summary", "NFL · Own9 ledger · as of 14 Nov 2026",
                          "A source-linked workspace for originating NFL lines. It shows what is verified, what is blank, and what you need to decide. It places no bets and makes no recommendations.",
                          body, "Own9 ledger: executive summary, verified results, price store, leaderboard rules and decisions.")

    # ---- Prices
    price_rows = []
    for r in d["prices"]:
        price_rows.append({"cells": [r["snapshot_id"], r["game_id"], r["origination_order"], r["market"], r["side"],
                                     r["line"], r["american_odds"], r["open_line"] or None, r["open_odds"] or None,
                                     r["close_line"] or None, r["close_odds"] or None, r["observed_date_utc"],
                                     r["verification_status"]],
                           "sources": ["DK-NFL-LEAGUE"] + (["NFL-SCHED-W10"] if r["matchup_official_url"] else [])})
    body = (callout("What this table is", "The sportsbook page was read once on "
                    f"{AS_OF}. Its values are withheld: the page has no timestamp and is not an official source. Rows show market identity and status only. Opening and closing columns are empty because no archive exists.", "warn")
            + table("prices", "Price snapshot store", ["Snapshot", "Game", "Order", "Market", "Side", "Line", "Odds", "Open line", "Open odds",
                                                       "Close line", "Close odds", "Observed (UTC date)", "Status"],
                    price_rows, "Origination order: 1 side (spread), 2 total, 3 moneyline. Source: DraftKings market page (not official); "
                    "the NFL matchup page is also linked where it was read."))
    pages["prices"] = page("prices", "Price snapshot store", "Market data · opening and closing",
                           "One row per market and side. The store records opening and closing numbers when they are captured with a timestamp. Today it holds no values: every price is withheld and flagged unverified.",
                           body, "Price snapshot store with open and close columns; empty where not captured.")

    # ---- Lines
    line_rows = []
    by_game: dict[str, list[dict]] = {}
    for r in d["prices"]:
        by_game.setdefault(r["game_id"], []).append(r)
    for gid, rs in by_game.items():
        for order, mkt in ((1, "spread"), (2, "total"), (3, "moneyline")):
            sel = [x for x in rs if x["market"] == mkt]
            if mkt == "spread":
                mk = " · ".join(f'{x["side"]} {x["line"]} ({x["american_odds"]})' for x in sel)
            elif mkt == "total":
                mk = " · ".join(f'{x["side"]} {x["line"]} ({x["american_odds"]})' for x in sel)
            else:
                mk = " · ".join(f'{x["side"]} {x["american_odds"]}' for x in sel)
            line_rows.append({"cells": [order, gid, mkt, None, mk, None,
                                        "Fair line not published; difference blank"],
                              "sources": ["DK-NFL-LEAGUE", "SK-TIME"]})
    body = (callout("How the three columns are set", "<strong>Fair line</strong> is our model output (blank: no model is fitted on verified inputs). "
                    "<strong>Market line</strong> is the value from the price store (none published yet). <strong>Difference</strong> = fair minus market, computed only when both exist. "
                    "Order of origination: side first, then total, then moneyline.", "notice")
            + table("lines", "Fair line, market line and difference", ["Order", "Game", "Market", "Fair line (own model)", "Market line (observed)",
                                                                       "Difference (fair − market)", "Status"], line_rows,
                    "Blank fair lines are deliberate. A fair line would need verified inputs and a documented, frozen model (Q03)."))
    pages["lines"] = page("lines", "Line origination", "Own lines · side, total, moneyline",
                          "The model's fair line, the market line and the difference, each in its own column, in the required order.",
                          body, "Fair line, market line and difference for each game and market; fair lines not yet published.")

    # ---- Results
    res_rows = []
    for r in d["results"]:
        res_rows.append({"cells": [r["week"], r["date_local"], r["away"], r["away_score"], r["home"], r["home_score"], r["status"],
                                   r["check_method"], r["verification_status"]],
                         "sources": ["NFL-SCHED-W10" if r["week"] == "10" else "NFL-SCHED-W9"] + (
                             ["NFL-GB-W10-WASNYG"] if r["game_id"] == "2026-REG10-WAS-NYG" else
                             ["NFL-GB-W9-LARWAS"] if r["game_id"] == "2026-REG9-LA-WAS" else
                             ["NFL-GB-W9-NYGPHI"] if r["game_id"] == "2026-REG9-NYG-PHI" else [])})
    body = (callout("Coverage", "Final scores for Week 9 (15 games; Pittsburgh and Tennessee on bye) and the Week 10 Thursday game. "
                    "ROI and backtests cannot be computed from scores alone: they need prices, which the store does not yet hold.", "notice")
            + table("results", "Verified results feed", ["Week", "Date", "Away", "Score", "Home", "Score", "Status", "How checked", "Verification"],
                    res_rows, "Scores are read from the official game-centre link text on the schedule page. Game Book copies are cited where the evidence file records them."))
    pages["results"] = page("results", "Verified results feed", "Results · official scores",
                            "Final scores from official NFL pages. A game appears only when its final score is read from an official source.",
                            body, "Verified NFL results for 2026 Weeks 9 and 10 with links to official game centres.")

    # ---- Replacements / injuries
    rep_rows = []
    for r in d["reps"]:
        rep_rows.append({"cells": [r["record_id"], r["row_type"].replace("_", " "), r["team"], r["side"], r["player_out"], r["pos_out"],
                                   r["player_in"], r["pos_in"], r["pairing_basis"], r["published_cause"], r["injury_wk10"],
                                   r["practice_wk10"], r["game_status_wk10"], r["incoming_prior_status"], None, None, r["depth_note"]],
                         "sources": ["NFL-GB-W10-WASNYG"] + (["NFL-INJURY-W10"] if r["injury_wk10"] or r["practice_wk10"] else [])})
    scen_rows = []
    for it in d["cat"]["injury_tracking"]:
        scen_rows.append({"cells": [it["id"], it["area"], it["unit"], it["scenario"], it["required"], it["current"], badge(it["status"])],
                          "sources": it["source_ids"]})
    body = (callout("Depth tiers are blank on purpose", "The NFL publishes starting lineups and injury designations, not first-to-fourth string tiers. "
                    "The depth-tier columns stay empty until an official tier source exists (SX07). Chains show the evidence instead.", "warn")
            + table("replacements", "Starter replacements (Week 9 to Week 10)", ["Record", "Type", "Team", "Side", "Out", "Pos", "In", "Pos",
                                                                              "Pairing basis", "Published cause", "Injury (Wk 10)", "Practice (Wk 10)",
                                                                              "Game status (Wk 10)", "Incoming: prior status", "Tier out", "Tier in", "Note"],
                    rep_rows, "Only changes proven by a same-slot match are paired. Others are listed without a pairing.")
            + table("scenarios", "Deficiency tracking scenarios (no data yet)", ["ID", "Area", "Unit", "Scenario", "Required evidence", "Current", "Status"],
                    scen_rows, "Starter-to-backup deficiency scenarios that need point-in-time injury and roster capture. Each is unverified until that capture exists."))
    pages["replacements"] = page("replacements", "Injuries & replacement depth", "Availability · starters and backups",
                                 "Who replaced whom, in which slot, and what the NFL published about it. Depth tiers are not published, so they are left blank.",
                                 body, "Starter replacements from official Game Books and injury report, with depth-tier policy and deficiency scenarios.")

    # ---- Leaderboard
    sig_rows = []
    for s in strategies:
        passed = sum(1 for g in [f"G0{i}" for i in range(1, 10)] if gate_status.get(g) == "pass")
        sig_rows.append({"cells": [s["id"], s["name"], s["category"], f"{passed} of 9", "0", None, None, None,
                                   "Not eligible" if not L.signal_eligible({g: gate_status.get(g, "") for g in gate_status}) else "Eligible",
                                   s["status"]],
                         "sources": ["SK-CV"] + s.get("source_ids", [])[:2]})
    stk_rows = []
    for s in strategies:
        stk_rows.append({"cells": [s["id"], s["name"], "0", None, None, "Informational only: cannot change signal rank"],
                         "sources": ["SP-BOOT"] + s.get("source_ids", [])[:1]})
    body = (callout("Two tracks, kept apart", "<strong>Signal</strong> ranks strategies only on probability quality against the no-vig market, and only when every signal gate passes. "
                    "<strong>Staking</strong> shows bankroll results beside it. A staking result never changes signal rank, eligibility or any reward.", "notice")
            + table("signal", "Signal track (ranking)", ["ID", "Strategy", "Class", "Signal gates passed", "Forecasts (n)", "Log loss vs market",
                                                       "Brier score", "CLV", "Eligibility", "Status"], sig_rows,
                    "Rank column is blank for every strategy: none is eligible yet.")
            + table("staking", "Staking track (informational)", ["ID", "Strategy", "Bets (n)", "ROI", "Max drawdown", "Role"], stk_rows,
                    "No executable prices exist, so no ROI or drawdown is computed. Assumed-price figures elsewhere in the repository are not used (F30)."))
    pages["leaderboard"] = page("leaderboard", "Leaderboard · signal and staking", "Competition · skill, not luck",
                                "Strategies are ranked on signal alone. Staking is shown separately and cannot rescue a weak signal.",
                                body, "Leaderboard with signal and staking tracks kept separate; no strategy eligible yet.")

    # ---- Correlations
    corr_rows = []
    for c in corr:
        corr_rows.append({"cells": [c["id"], c["leg_a"], c["leg_b"], "0", c["pearson_r"], None, None,
                                    "not published: no paired official observations", c["note"]],
                          "sources": c["source_ids"]})
    body = (callout("Publication rule", "n is always shown. A coefficient and its 95% interval are published only when every pair comes from an official source, "
                    "n is at least 30 (proposed), and the interval is shown. Otherwise the coefficient is blank. No value is estimated from assumed prices.", "notice")
            + table("correlations", "Predeclared correlation pairs", ["ID", "Leg A", "Leg B", "n (official pairs)", "r (Pearson)", "CI low", "CI high",
                                                                      "Status", "Why this pair matters"], corr_rows,
                    "All eight pairs have n = 0. No coefficient is published."))
    pages["correlations"] = page("correlations", "Correlations (with n)", "Dependence · official paired data only",
                                 "Every coefficient is published with its n, and none is published without official paired observations.",
                                 body, "Eight predeclared correlation pairs with n published; coefficients withheld until official paired data exist.")

    # ---- Gates & demotion
    gate_rows = [{"cells": [g["id"], g["name"], g["rule"], badge(g["status"]), "signal" if g["id"] <= "G09" else "reward / forward"],
                  "sources": g["source_ids"]} for g in d["cat"]["gates"]]
    pol = d["policy"]["demotion_gate"]
    trig_rows = [{"cells": [t["id"], t["name"], t["rule"], t["threshold"], badge(t["threshold_status"])],
                  "sources": ["SK-CAL", "SP-BOOT"]} for t in pol["triggers"]]
    body = (callout("How demotion works", f'{E(pol["effect"])} {E(pol["non_offset_rule"])} {E(pol["override_rule"])}', "notice")
            + table("gates", "Validation gates G01 to G11", ["ID", "Gate", "Rule", "Status", "Track"], gate_rows,
                    "All gates are not evaluated. A strategy is eligible only after its signal gates G01 to G09 pass.")
            + table("demotion", "Demotion gate D1 to D6", ["ID", "Trigger", "Rule", "Threshold", "Threshold status"], trig_rows,
                    "A live strategy stays live only if every trigger is clear. A missing input counts as not evaluated, never clear."))
    pages["gates"] = page("gates", "Gates & demotion", "Validation · rules before rewards",
                          "Eleven validation gates decide whether a strategy may rank. Six triggers send a live strategy back to paper.",
                          body, "Eleven validation gates and the six-trigger demotion gate that sends a live strategy back to paper.")

    # ---- Questions
    q_rows = [{"cells": [q["id"], q["question"], q["answer_now"], badge(q["status"]), q["missing"], q["how_to_find"], q["blocks"]],
               "sources": q["source_ids"] or ["SK-CV"]} for q in d["questions"]]
    body = (callout("How to use this list", "Read 'Answer now' first. 'Missing' names the information still needed. 'How to find it' says how to get it without manual input from you, where possible. Blocked decisions are listed in the last column.", "notice")
            + table("questions", "Questions, answers and gaps", ["ID", "Question", "Answer now (verified)", "Status", "Missing", "How to find it", "Blocks"],
                    q_rows, "A question marked Unanswered has no answer in the verified files. A question with no source link is answered by a policy in this ledger."))
    pages["questions"] = page("questions", "Questions & answers", "Decisions · what must be known first",
                              "Fifteen questions that must be answered before a decision can reasonably be made, with what we have and what we do not.",
                              body, "Questions, answers, missing information and how to find it, before any decision.")

    # ---- Suggestions
    sx_rows = []
    for s in d["suggestions"]["items"]:
        opts = "<ul class=\"opts\">" + "".join(f'<li><strong>{E(o["id"])}.</strong> {E(o["label"])}<br><small>Trade-off: {E(o["tradeoff"])}</small></li>' for o in s["options"]) + "</ul>"
        sx_rows.append({"cells": [s["id"], s["area"], s["problem"], opts, s["effort"], s["evidence_needed"], badge(s["status"])],
                        "sources": s["sources"]})
    paths = []
    for p in d["suggestions"]["candidate_paths"]:
        paths.append({"cells": [p["id"], p["name"], "; ".join(p["steps"]), p["outcome"], "Awaiting decision"],
                      "sources": ["SK-CAL"] if p["id"] != "P1" else ["EGOV-PENAL-CODE"]})
    body = (callout("Nothing here is implemented", d["suggestions"]["note"] + " To decide, pick one option per suggestion, or a whole path, and record it in the decision log below.", "notice")
            + table("suggestions", "Suggestions to review and choose", ["ID", "Area", "Problem", "Options", "Effort", "Evidence needed", "Status"], sx_rows,
                    "Each option is a choice. Options are not ranked, and no option has been selected.")
            + table("paths", "Candidate paths (choose one)", ["ID", "Path", "Steps (options to choose)", "Outcome", "Decision"], paths,
                    "Paths group the suggestions. Recommended order is in the note below.")
            + '<section class="panel"><h2>Recommended order (a sequencing note, not a decision)</h2>'
              f'<p>{E(d["suggestions"]["recommended_order"])}</p>'
              '<h2>Decision log</h2><p class="empty-state">No decision recorded yet. To record one, add a line here or in COORDINATION.md: suggestion ID, option, date, and who decided.</p></section>')
    pages["suggestions"] = page("suggestions", "Suggestions · choose before changes", "Review queue · no change without a choice",
                                "Ways to improve the site and the decisions it supports. Each is set out with its options so that you can pick a path before anything is built.",
                                body, "Suggestions with options and candidate paths; nothing implemented until a choice is recorded.")

    # ---- Flags
    fl_rows = [{"cells": [f["id"], badge(f["severity"]), f["title"], f["detail"], f["impact"], f["disposition"], badge(f["state"])],
                "sources": f["sources"]} for f in d["flags"]]
    body = (callout("Flagged for Review", "These irregularities are published for your review. They do not block the merge. Earlier findings F01 to F27 are on the "
                    '<a href="../flags.html">repository flags page</a>. F38 notes that F01 to F13 mean different things on different pages, so cite with a register name.', "warn")
            + table("flags", "Irregularities and open items", ["ID", "Severity", "Finding", "Detail", "Impact", "Disposition", "State"], fl_rows,
                    "Each finding links to the sources that show it. Items marked owner decision need your ruling."))
    pages["flags"] = page("flags", "Flagged for Review", "Review queue · irregularities",
                          "Findings from this session with the sources that show them. They are for review after the site is live and do not block the merge.",
                          body, "Flagged for Review: irregularities F28 to F38 with source links.")

    # ---- Sources
    src_rows = []
    for sid, s in SOURCES.items():
        if s.get("checked") is None:
            continue
        src_rows.append({"cells": [sid, s.get("publisher", ""), s.get("type", ""), s.get("status", ""), s.get("checked", ""), s.get("scope", ""),
                                   f'<a href="{E(s["url"], quote=True)}" target="_blank" rel="noopener noreferrer">{E(s["url"])} <span aria-hidden="true">↗</span></a>'],
                         "sources": [sid]})
    body = (callout("How sources are labelled", "<strong>Official</strong>: the league, a government or the club. <strong>Market</strong>: a sportsbook page, "
                    "used only for price observations, never called official. <strong>Method</strong>: a reference for a definition, never for a value. "
                    "'Retrieved' means read in this session; 'carried' means read in an earlier session and recorded in the repository.", "notice")
            + table("sources", "Source register", ["ID", "Publisher", "Type", "Read status", "Checked", "Scope and limits", "Link"], src_rows,
                    "Every row in every table on this site cites an ID from this register."))
    pages["sources"] = page("sources", "Sources", "Evidence · every link",
                            "Each official, market and method source, with the date it was read and what it does and does not show.",
                            body, "Source register with status, scope and links for every ledger value.")

    return pages


def data_files() -> dict[str, bytes]:
    """Downloads: one CSV per table (exactly what the page shows) plus the store files."""
    files: dict[str, bytes] = {}
    for tid, (cols, rows) in EXPORTS.items():
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(cols)
        w.writerows(rows)
        files[f"data/{tid}.csv"] = buf.getvalue().encode("utf-8")
    for name in ("results_verified.csv", "price_snapshots.csv", "replacements.csv"):
        files[f"data/store-{name}"] = (L.LEDGER / name).read_bytes()
    for name in ("policy.json", "sources.json", "questions.json", "suggestions.json", "flags.json"):
        files[f"data/store-{name}"] = (L.LEDGER / name).read_bytes()
    return files


ASSET_CSS = """*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}body{margin:0;font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:#1d2530;background:#f5f7fa}
a{color:#0b5cad}.skip{position:absolute;left:-999px}.skip:focus{left:8px;top:8px;background:#fff;padding:6px}
.top{display:flex;flex-wrap:wrap;gap:10px 18px;align-items:center;padding:12px 20px;background:#0f2b3d;color:#fff}
.brand{color:#fff;font-weight:700;text-decoration:none;font-size:17px}.brand span{font-weight:400;opacity:.8}
.top nav{display:flex;flex-wrap:wrap;gap:4px 12px}.top nav a{color:#d6e6f2;text-decoration:none;font-size:13px;padding:3px 0}.top nav a[aria-current=page]{color:#fff;border-bottom:2px solid #5fd1b2}
main{max-width:1200px;margin:0 auto;padding:18px 16px 40px}.intro{margin-bottom:14px}.kicker{margin:0;color:#4b6170;font-size:12px;letter-spacing:.06em;text-transform:uppercase}
h1{font-size:26px;margin:4px 0 6px}h2{font-size:18px;margin:0 0 6px}.lead{font-size:16px;margin:0;max-width:820px}
.stats{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:10px;margin:12px 0}
.stat{background:#fff;border:1px solid #d8e0e8;border-radius:8px;padding:10px 12px}.stat-label{display:block;font-size:12px;color:#4b6170}.stat strong{display:block;font-size:22px}.stat small{color:#4b6170}
.callout{background:#eaf4fb;border-left:4px solid #0b5cad;padding:10px 14px;border-radius:6px;margin:12px 0}.callout.warn{background:#fff6e5;border-color:#b26a00}.callout strong{display:block;margin-bottom:2px}.callout p{margin:0}
.panel{background:#fff;border:1px solid #d8e0e8;border-radius:8px;padding:14px;margin:14px 0}.panel-head{display:flex;flex-wrap:wrap;gap:10px;justify-content:space-between;align-items:flex-start}
.note{margin:4px 0 0;color:#4b6170;font-size:13px}.tools input{padding:6px 10px;border:1px solid #b9c5d1;border-radius:6px;min-width:220px}
.scroll{overflow-x:auto;margin-top:10px;border:1px solid #e3e9ef;border-radius:6px}table{border-collapse:collapse;width:100%;font-size:13px}
th,td{padding:7px 9px;border-bottom:1px solid #edf1f5;text-align:left;vertical-align:top}th{background:#f0f4f8;position:sticky;top:0;font-weight:600}
tr:hover td{background:#fafcfe}.blank{color:#6b7885}.links a{white-space:nowrap;margin-right:6px}.row-count{font-size:12px;color:#4b6170;margin:8px 0 0}
.badge{display:inline-block;padding:1px 8px;border-radius:999px;font-size:12px;white-space:nowrap}.badge.amber{background:#fde9c7;color:#6b3f00}.badge.green{background:#d7f3e6;color:#0c5136}.badge.neutral{background:#e6ecf2;color:#23313f}
.opts{margin:0;padding-left:16px}.opts li{margin:0 0 6px}.actions li{margin:4px 0}.empty-state{color:#4b6170}
.sr-only{position:absolute;left:0;top:0;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}footer{max-width:1200px;margin:0 auto;padding:16px;color:#4b6170;font-size:12px;border-top:1px solid #d8e0e8}
:focus-visible{outline:3px solid #5fd1b2;outline-offset:2px}"""

ASSET_JS = """(function(){
  document.querySelectorAll('input.filter').forEach(function(input){
    var table=document.getElementById(input.getAttribute('data-table'));
    if(!table) return;
    input.addEventListener('input', function(){
      var q=input.value.trim().toLowerCase(); var shown=0;
      Array.prototype.forEach.call(table.tBodies[0].rows, function(row){
        var hit=!q || row.textContent.toLowerCase().indexOf(q)>-1; row.hidden=!hit; if(hit) shown++;
      });
      var count=table.parentNode.parentNode.parentNode.querySelector('.row-count span');
      if(count) count.textContent = shown + ' of ' + table.tBodies[0].rows.length + ' rows';
    });
  });
})();
"""


def render() -> dict[str, bytes | str]:
    out: dict[str, bytes | str] = {}
    for slug, content in build().items():
        out[f"ledger/{slug}.html"] = content
    out["ledger/assets/style.css"] = ASSET_CSS + "\n"
    out["ledger/assets/app.js"] = ASSET_JS
    for path, content in data_files().items():
        out[f"ledger/{path}"] = content
    return out


def main(argv: list[str]) -> int:
    files = render()
    if "--check" in argv:
        bad = []
        for rel, content in files.items():
            p = ROOT / rel
            want = content.encode() if isinstance(content, str) else content
            if not p.exists() or p.read_bytes() != want:
                bad.append(rel)
        if bad:
            print("STALE:", *bad, sep="\n  ")
            return 1
        print(f"PASS: ledger/ matches the build ({len(files)} files).")
        return 0
    for rel, content in files.items():
        p = ROOT / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content.encode() if isinstance(content, str) else content)
    print(f"Wrote {len(files)} files to ledger/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
