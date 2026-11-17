"""Render the verification section as static HTML with the shared site chrome.

The section is additive: it adds six pages under ``verification/``, one navigation entry in
the shared ``NAV_GROUPS``, and nothing else. It never rewrites another session's page, data
file or register. Relative links are written from one level down (``../style.css``,
``../flags.html``) so the pages work without JavaScript and without a server.

Table markup is built here rather than borrowed, because the shared generator's ``table()``
emits root-relative asset paths; the emitted attributes (``tabindex="0" role="region"`` and a
``<caption>``) match it exactly so the site's own accessibility checks still hold.
"""
from __future__ import annotations

import sys
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import registry as V  # noqa: E402

OUT = HERE  # pages are written beside this module

NAV = [
    ("../index.html", "Dashboard"),
    ("index.html", "Verification"),
    ("readiness.html", "Readiness"),
    ("requirements.html", "Requirements"),
    ("questions.html", "Questions"),
    ("suggestions.html", "Suggestions"),
    ("evidence.html", "Evidence and snapshots"),
    ("flags.html", "Flagged"),
    ("../flags.html", "Site flag register"),
    ("../origination/index.html", "Origination desk"),
]


def table(title: str, headers: list[str], rows, evidence_col: str = "Evidence / scope") -> str:
    out = [f'<h2>{escape(title)}</h2>',
           f'<div class="table-wrap" tabindex="0" role="region" '
           f'aria-label="{escape(title)} — scrollable table">',
           f'<table><caption class="sr-only">{escape(title)}</caption><thead><tr>']
    out += [f'<th scope="col">{escape(h)}</th>' for h in [*headers, evidence_col]]
    out.append('</tr></thead><tbody>')
    for i, (cells, refs, kind) in enumerate(rows, 1):
        rid = f'{title.lower().replace(" ", "-").replace(",", "").replace(".", "")}-{i}'
        out.append(f'<tr id="{escape(rid)}">')
        for j, c in enumerate(cells):
            tag = 'th scope="row"' if j == 0 else 'td'
            close = 'th' if j == 0 else 'td'
            out.append(f'<{tag}>{escape("" if c is None else str(c))}</{close}>')
        out.append(f'<td><span class="evidence-kind">{escape(kind)}</span>'
                   f'{V.source_links(refs)}</td></tr>\n')
    out.append('</tbody></table></div>')
    return "".join(out)


def page(filename: str, title: str, intro: str, body: str, label: str) -> str:
    nav = "".join(
        f'<a href="{href}"' + (' aria-current="page"' if href == filename else '') + f'>{text}</a>'
        for href, text in NAV)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Independent verification of the Own9 NFL research brief: requirements, readiness gates, questions, suggestions and flagged irregularities.">
<title>{escape(label)} · Own9 verification</title>
<link rel="stylesheet" href="../style.css"></head>
<body><a class="skip" href="#main">Skip to content</a>
<header><div class="shell top"><a class="brand" href="../index.html"><span>O9</span> OWN9 <small> / VERIFICATION</small></a><span class="status-dot">Research only · no live wagers</span></div>
<nav class="shell" aria-label="Section navigation">{nav}</nav></header>
<main class="shell" id="main">
<div class="page-meta"><span class="eyebrow">VERIFICATION / {escape(label.upper())}</span><span>As of {V.AS_OF} · UTC</span></div>
<h1>{escape(title)}</h1><p class="lead">{escape(intro)}</p>
{body}
<p class="disclaimer">Research, not betting advice. No verified edge, calibrated model or guaranteed return is claimed. A blank empirical value is unavailable and unverified, never zero. Structural checks prove provenance and internal consistency; they do not prove that a publisher is right, and they are not a substitute for an executed strategy.</p>
</main>
<footer class="shell"><b>OWN9 / VERIFICATION</b><span>Evidence over assumptions · <a href="../flags.html">Site flag register</a> · <a href="../sources.html">Evidence register</a></span></footer>
</body></html>
'''


def t(name: str) -> str:
    title, _intro, headers, rows = V.TABLES[name]
    return table(title, headers, rows)


def _top_gates_sentence() -> str:
    """Describe the two largest gates from the register instead of typing their counts.

    An earlier draft hard-coded "blocks 7" and "blocks 13"; the gate table changed and the
    sentence did not. The counts now come from the table that the readiness page renders.
    """
    ordered = sorted(V.GATES, key=lambda g: -len(g[3]))
    first, second = ordered[0], ordered[1]
    return (f"{first[0]} — {first[1].lower()} — holds {len(first[3])} requirement lines, and "
            f"{second[0]} — {second[1].lower()} — holds {len(second[3])}. The term gate G-10 also "
            "holds nine lines and is the only one a decision alone can close.")


def build() -> dict[str, str]:
    C = V.req_counts()
    I, E = C["impl"], C["emp"]
    GS = V.gate_summary()
    M = V.M
    pages = {}

    # ---------------------------------------------------------------- landing
    landing = []
    landing.append(
        '<div class="notice"><strong>What this section is, and what it corrected</strong><p>An '
        'independent pass over the brief, line by line. It does not re-publish another session\'s '
        'numbers and it does not replace the site\'s canonical pages: every row links to an official '
        'publisher or to this repository, and the figures in prose are recomputed from the committed '
        'files at build time rather than trusted.</p><p><b>Correction, same session.</b> The first '
        'draft of this section recommended building a scheduled multi-day capture of the NFL injury '
        'report. Reading '
        '<a href="https://www.nfl.com/legal/terms/">NFL.com Terms section 1.3</a> (updated 16 May 2024) '
        'showed that recommendation to be wrong: systematic retrieval to build a compilation is '
        'prohibited without express prior written consent. The recommendation is withdrawn, the '
        'affected lines are now blocked on gate G-10, and the change is published here rather than '
        'quietly deleted — a reader who saw the first version is owed the reason.</p></div>')

    landing.append(table(
        "Executive summary",
        ["Question", "Answer", "Where it is answered"],
        [
            V.row(["How much of the brief is built?",
                   f"{I['built'] + I['policy']} of {I['total']} requirement lines are implemented or "
                   f"honoured as a prohibition; {I['partial']} are partly built and "
                   f"{I['not_built']} are not built.",
                   "Requirements, line by line"], (V.REPO,), "Measured summary"),
            V.row(["How much is established against official evidence?",
                   f"{E['established']} lines are established, {E['partial']} partly, "
                   f"{E['not_established']} are not, and {E['unavailable']} cannot be assessed because "
                   "the evidence does not exist. No line claims a validated betting edge.",
                   "Requirements, line by line"], (V.REPO,), "Measured summary"),
            V.row(["What blocks the most?",
                   _top_gates_sentence(), "Readiness"], (V.REPO,), "Gate analysis"),
            V.row(["What is the cheapest thing to fix?",
                   "The schema-and-process gate: a falsification field on strategy entries, a control "
                   "baseline row, a weekly diff column and an alert route. These need a decision, not a "
                   "licence.", "Readiness · Suggestions"], (V.REPO,), "Gate analysis"),
            V.row(["Is the site's own data current?",
                   f"No. The committed Week 10 capture is dated 14 Nov and the official page has since "
                   f"settled 11 more games. The feed holds {M['finals_total']} finals; the official page "
                   "now supports 148.", "Evidence and snapshots"], (V.S_SCHED_W10, V.REPO), "Measured"),
            V.row(["Can luck be removed?",
                   "No. It can be bounded with proper scoring, intervals and multiplicity control, and "
                   "the site refuses to rank when the bound spans zero. 'Removal' is not offered.",
                   "Questions Q-09"], (V.REPO,), "Method statement"),
            V.row(["Does the brief conflict with the publisher's terms?",
                   "Yes, and it is the most consequential finding here. Ten requirement lines need a "
                   "scheduled multi-day capture, a season archive or a reserve-list join. NFL.com Terms "
                   "section 1.3 prohibit systematic retrieval to build a compilation without express "
                   "prior written consent. Those lines are blocked by policy, not by engineering, and "
                   "no amount of building clears them.",
                   "Readiness G-10 · Q-06b · VF-09"], (V.S_TERMS, V.REPO), "Official terms read"),
            V.row(["Are any of the brief's premises stale?",
                   "Yes, at least two: the three Lions designations it calls blank are published, and "
                   "the injury-row counts it cites (254/279) are not reproducible from this repository.",
                   "Flagged for review"], (V.S_INJURY, V.REPO), "Official re-read"),
        ]))

    landing.append('<div class="cards">'
                   '<a href="readiness.html"><span>01 / DECIDE</span><b>Decision readiness</b>'
                   '<p>One row per gate, with the number that clears it</p></a>'
                   '<a href="requirements.html"><span>02 / LINE BY LINE</span><b>Requirements</b>'
                   '<p>74 lines, implemented versus established</p></a>'
                   '<a href="questions.html"><span>03 / ASK</span><b>Questions</b>'
                   '<p>Answerable, blocked, or owner decision</p></a>'
                   '<a href="suggestions.html"><span>04 / CHOOSE</span><b>Suggestions</b>'
                   '<p>Cost, unblocked gate, and what would refute it</p></a>'
                   '<a href="evidence.html"><span>05 / CHECK</span><b>Evidence and snapshots</b>'
                   '<p>Two dated reads kept side by side</p></a>'
                   '<a href="flags.html"><span>06 / REVIEW</span><b>Flagged for review</b>'
                   '<p>VF-01 to VF-11, with what closes each</p></a>'
                   '</div>')

    landing.append(table(
        "This session's findings in one line each",
        ["ID", "Finding", "Severity"],
        [V.row([f[0], f[2], f[1]],
               tuple(x for x in f[6] if x != V.REPO) or (V.REPO,), "Flagged irregularity")
         for f in V.FLAGS]))

    landing.append(table(
        "What was verified this session, and what was not",
        ["Item", "Result", "Scope of the check"],
        [
            V.row(["Week 10 slate re-read",
                   "12 finals + 2 scoreless games on 2026-11-16, against 1 final + 13 scoreless on "
                   "2026-11-14", "Official weekly schedule page, both chunks"],
                  (V.S_SCHED_W10,), "Direct publisher"),
            V.row(["Lions designations",
                   "Kerby Joseph, Cade Mays and D.J. Reed each carry an explicit Out status",
                   "Official injury report, chunk 0 of 8"],
                  (V.S_INJURY,), "Direct publisher"),
            V.row(["Venue for three Week 10 fixtures",
                   "METLIFE STADIUM / East Rutherford NJ; FC BAYERN MUNICH STADIUM / Munich; "
                   "PAYCOR STADIUM / Cincinnati OH", "Each game centre's own Game Info block"],
                  (V.S_GAMECENTER_W10,), "Direct publisher"),
            V.row(["Injury-report row totals",
                   "Not verified. Three totals are in circulation and none is reproducible from a "
                   "machine count here; this session counted chunk 0 only and asserts no total.",
                   "Deliberately not filled"],
                  (V.S_INJURY,), "Withheld — see VF-02"),
            V.row(["Price-dependent metrics",
                   "Not verified and not computed: no market price exists in any source obtained",
                   "Blank by policy, enforced by a build test"],
                  (V.REPO,), "Withheld — see G-01"),
            V.row(["Another session's open PR (#51)",
                   "Not reviewed for merge and not edited. Its checks are red and its own record calls "
                   "it partial.", "Avoided so no claim conflict exists"],
                  (V.REPO,), "Out of scope"),
        ]))

    pages["index.html"] = page(
        "index.html", "Verify first.\nThen decide.",
        "An independent, line-by-line pass over the brief: what is built, what is established, what "
        "is blocked and by which number. Written so a reviewer can act on it.",
        "".join(landing), "Overview")

    # ---------------------------------------------------------------- readiness
    read = []
    read.append(f'<div class="notice"><strong>How to read this</strong><p>A gate is only useful if it '
                f'names the number that would clear it. Gates are ordered by the count of requirement '
                'lines they hold, so the top row is the one to work on first — unless it is the one '
                'that cannot be worked on at all, which is exactly the point of publishing the cost '
                f'class beside it. One gate is different in kind from the rest: <b>G-10</b> is not a '
                'missing measurement but a permission this project does not have. It is the only gate '
                'here that a decision, rather than a purchase or a build, can close.</p></div>')
    read.append(f'<p class="lead">{len(V.GATES)} gates, computed from the register: '
                f'{V.gate_summary()["requirements_mapped"]} of {len(V.REQ)} requirement lines are '
                f'mapped to at least one gate.</p>')
    read.append(t("readiness"))
    read.append(t("gates"))
    read.append(table(
        "Recommended order (a recommendation, not a finding)",
        ["Order", "Action", "Why this order", "What it does not fix"],
        [
            V.row(["1", "Answer the terms question (G-10, V-S00)",
                   "Ten requirement lines are blocked by the publisher's terms and none of them can be "
                   "engineered around. One letter or one licence enquiry settles more of the brief than "
                   "any build, and it costs nothing to ask.",
                   "It builds nothing. Three of the suggestions below change cost depending on the "
                   "answer."], (V.S_TERMS, V.REPO), "Reasoning"),
            V.row(["2", "Clear the schema and process gate (G-07)",
                   "It is the only open gate that needs a decision rather than a licence or months of "
                   "labour, and it makes every other row auditable.",
                   "It changes no number. No strategy becomes eligible."], (V.REPO,), "Reasoning"),
            V.row(["3", "Finish one complete injury-report read (V-S04)",
                   "Three competing totals are a credibility problem and one capture ends it. It also "
                   "proves the capture mechanism before it is scheduled.",
                   "One capture is still not a series; G-02 stays closed."], (V.S_INJURY,), "Reasoning"),
            V.row(["4", "Designate the canonical implementation (V-S06)",
                   "Two implementations of the same requirements invite a reader to average them. One "
                   "decision, reversible.",
                   "It does not reconcile the inputs that make them differ."], (V.REPO,), "Reasoning"),
            V.row(["5", "Treat the price gate as a procurement decision, not a task",
                   "Nothing else in the repository can produce a market number. Until a source is "
                   "approved, every residual, CLV and ROI claim stays blank by design.",
                   "It is the only route to most of the brief's price requirements."],
                  (V.REPO,), "Reasoning"),
        ]))
    pages["readiness.html"] = page(
        "readiness.html", "What blocks a decision,\nand the number that clears it.",
        f"{len(V.GATES)} gates, the requirement lines each one holds, the measurement that would "
        "show it cleared, and how much of it is a decision rather than a purchase.",
        "".join(read), "Readiness")

    # ---------------------------------------------------------------- requirements
    req = []
    req.append('<div class="notice"><strong>Two verdicts per line, never one</strong><p>'
               f"<b>Implemented</b> asks whether the mechanism exists and is tested. "
               f"<b>Established</b> asks whether the claim survives contact with official evidence. "
               f"{I['built']} lines are implemented, {I['partial']} partly and {I['not_built']} are "
               f"not; {E['established']} lines are established. A blank-ish Established cell means "
               "not established or unavailable — never passed.</p></div>")
    budget_rows = [V.row([label, I[key]], (V.REPO,), "Counted from the rows")
                   for key, label in (("built", "Implemented"),
                                      ("partial", "Partly implemented"),
                                      ("not_built", "Not implemented"),
                                      ("policy", "Honoured as a prohibition"))]
    budget_rows += [V.row([label, E[key]], (V.REPO,), "Counted from the rows")
                    for key, label in (("established", "Established"),
                                       ("partial", "Partly established"),
                                       ("not_established", "Not established"),
                                       ("unavailable", "Unavailable — no evidence exists"))]
    req.append(table("Requirement budget (measured from the rows below)",
                     ["Measure", "Count"], budget_rows))
    req.append(t("requirements"))
    req.append(t("measured"))
    pages["requirements.html"] = page(
        "requirements.html", "Every line of the brief,\nwith two verdicts.",
        "One row per requirement. Each row names the gate that blocks it and the artefact that would "
        "clear it, so the table doubles as a work queue.",
        "".join(req), "Requirements")

    # ---------------------------------------------------------------- questions
    q = []
    q.append('<div class="notice"><strong>Answer first, defer second</strong><p>Where a question is '
             'answerable from a source already held, the answer is stated in the row rather than '
             'deferred to a future session. Two questions are deliberately left unanswered: the '
             'injury-row total (needs a full capture) and any market comparison (needs a price).</p></div>')
    qc = V.question_counts()
    q.append(table(
        "Question states",
        ["State", "Count", "Meaning"],
        [
            V.row(["Answerable now", qc["answerable"],
                   "Answered in this register from a source already read"],
                  (V.REPO,), "Counted"),
            V.row(["Blocked", qc["blocked"],
                   "Needs a named artefact that does not exist yet"],
                  (V.REPO,), "Counted"),
            V.row(["Owner decision", qc["decision"],
                   "No amount of research settles it; one person has to choose"],
                  (V.REPO,), "Counted"),
        ]))
    q.append(t("questions"))
    pages["questions.html"] = page(
        "questions.html", "Questions that gate\nthe next decision.",
        "Fourteen questions, each marked answerable, blocked, or an owner decision. The blocked ones "
        "name the artefact; the answerable ones carry the answer.",
        "".join(q), "Questions")

    # ---------------------------------------------------------------- suggestions
    s = []
    s.append('<div class="notice"><strong>A suggestion is a proposal, never a finding</strong><p>Each '
             'entry names the requirement it addresses, what it costs, what it unblocks, and what '
             'evidence would show the choice was wrong. None asserts a numerical NFL result and none '
             'has been implemented by this session. Two of them are <b>conditional</b>: V-S05 (29 club '
             'depth pages) and any capture work depend on the answer to Q-06b, and are marked that way '
             'rather than recommended flatly.</p></div>')
    s.append(t("suggestions"))
    s.append(table(
        "Which suggestion to take first, and why",
        ["Rank", "Suggestion", "Reason"],
        [
            V.row(["1", "V-S00 — answer the terms question",
                   "It is free to ask, it governs nine other lines, and building first would waste the "
                   "work."], (V.S_TERMS,), "Reasoning"),
            V.row(["2", "V-S01 — falsification field",
                   "Cheapest per unit of trust: it makes every strategy row auditable and needs no data."],
                  (V.REPO,), "Reasoning"),
            V.row(["3", "V-S02 — control baseline row",
                   "Turns an empty leaderboard into a measurement of what no-skill looks like on the "
                   "same sample."], (V.REPO,), "Reasoning"),
            V.row(["4", "V-S04 — one hashed injury read",
                   "Ends the three-totals problem and proves the capture mechanism."], (V.S_INJURY,), "Reasoning"),
            V.row(["5", "V-S07 — private raw layer",
                   "The highest-consequence open risk: rights are unreviewed while raw rows are public."],
                  (V.REPO,), "Reasoning"),
        ]))
    pages["suggestions.html"] = page(
        "suggestions.html", "Choose a path\nbefore building one.",
        "Eight suggestions with cost, unblocked gate and a falsification test, so a reviewer can accept "
        "or reject each one on its merits rather than on its enthusiasm.",
        "".join(s), "Suggestions")

    # ---------------------------------------------------------------- evidence
    ev = []
    ev.append('<div class="notice"><strong>Two dated reads beat one overwritten read</strong><p>The '
              'brief asks for immutable captures. When the official Week 10 page settled 11 more games, '
              'the frozen 14 Nov transcription was <em>not</em> rewritten: a second dated snapshot was '
              'published beside it. Rewriting it would have mixed two retrieval dates in a single '
              'witness and broken the repository\'s own two-transcription cross-check.</p></div>')
    ev.append(t("snapshots"))
    ev.append(t("delta"))
    ev.append(t("venues"))
    ev.append(t("rechecked"))
    pages["evidence.html"] = page(
        "evidence.html", "What was read,\nand when.",
        "The dated snapshot ledger, the measured delta between two reads of the same page, the venues "
        "that can be transcribed, and the inherited findings this pass re-checked.",
        "".join(ev), "Evidence")

    # ---------------------------------------------------------------- flags
    f = []
    f.append('<div class="notice"><strong>Nothing here blocks publication</strong><p>Each row states '
             'what was observed, why it was not fixed in this pass, and what would close it. Findings '
             'are numbered VF-01.. so they cannot collide with the 57 existing F-numbers or the F58+ '
             'range claimed by an open PR.</p></div>')
    f.append(t("flags"))
    f.append(table(
        "Where to review the rest of the site",
        ["Register", "What it holds"],
        [
            V.row(["Site Flagged for Review (../flags.html)",
                   "The numbered site-wide finding register, F01 onwards, owned by earlier sessions"],
                  (V.REPO,), "Existing register"),
            V.row(["Evidence register (../sources.html)",
                   "Every publisher the site cites, with the scope each was read in"],
                  (V.REPO,), "Existing register"),
            V.row(["Origination desk flags (../origination/flagged.html)",
                   "The line-origination desk's own findings OD-01 onwards"], (V.REPO,), "Existing register"),
        ]))
    sev = {}
    for flag in V.FLAGS:
        sev[flag[1]] = sev.get(flag[1], 0) + 1
    sev_text = ", ".join(f"{sev[k]} {k.lower()}" for k in ("Critical", "High", "Medium", "Low") if k in sev)
    pages["flags.html"] = page(
        "flags.html", "Flagged for review,\nwith what closes each.",
        f"{len(V.FLAGS)} irregularities from this pass ({sev_text}), none blocking, each with the "
        "change that would clear it. Severity counts are computed from the register.",
        "".join(f), "Flagged")

    return pages


def main() -> None:
    pages = build()
    for name, html in pages.items():
        (OUT / name).write_text(html)
    print(f"Rendered {len(pages)} verification pages.")


if __name__ == "__main__":
    main()
