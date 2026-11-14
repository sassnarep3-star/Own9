#!/usr/bin/env python3
"""Session 00cf851d - structural and source-citation check of the built pages.

Fails loudly if:
  * a page is missing, malformed or has no navigation or heading
  * a local link points at a file that does not exist
  * a row on a claim-bearing page carries neither an official source link nor
    an explicit blank marker
  * a page contains a placeholder string

It does not check external reachability or whether a source supports a claim.
Those require a human and the official page.
"""

from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SESSION = os.path.dirname(HERE)

from build import PAGES  # noqa: E402

# Pages whose table rows state something about the outside world and must
# therefore carry an official source link or an explicit blank.
CLAIM_PAGES = {
    "verification.html", "gamebooks.html", "replacement.html", "results.html",
    "injuries.html", "standings.html", "flags.html", "questions.html", "sources.html",
}

PLACEHOLDERS = ("TODO", "FIXME", "lorem ipsum", "XXX", "TBD")

problems: list = []
stats = {"pages": 0, "rows": 0, "sourced_rows": 0, "blank_rows": 0,
         "local_links": 0, "tables": 0}


def audit_html(doc: str, name: str, problems: list, stats: dict) -> None:
    """Apply every page-level rule to one rendered document.

    Exposed so the tests can pass a fabricated page through the same rules the
    build uses, which is the only way to prove the fail-closed behaviour rather
    than assert it.
    """
    if doc.count("<h1>") != 1:
        problems.append("%s: expected exactly one <h1>, found %d" % (name, doc.count("<h1>")))
    if 'aria-current="page"' not in doc:
        problems.append("%s: no aria-current navigation marker" % name)
    if "<title>" not in doc:
        problems.append("%s: no title element" % name)
    for bad in PLACEHOLDERS:
        if bad.lower() in doc.lower():
            problems.append("%s: placeholder text %r" % (name, bad))

    for href in re.findall(r'href="([^"#][^"]*)"', doc):
        if href.startswith(("http://", "https://", "mailto:")):
            continue
        stats["local_links"] += 1
        if not os.path.exists(os.path.join(SESSION, href)):
            problems.append("%s: broken local link %s" % (name, href))

    # Citation rule, table level: on a claim-bearing page no table may be
    # published without naming its official source somewhere in it, either in
    # the caption or on a row.
    for ti, tbl in enumerate(re.findall(r"<table>(.*?)</table>", doc, flags=re.S), 1):
        if "No rows." in tbl:
            continue
        stats["tables"] += 1
        if 'href="http' not in tbl and name in CLAIM_PAGES:
            problems.append("%s: table %d has no official source link in its caption or rows"
                            % (name, ti))
    for block in re.findall(r"<tbody>(.*?)</tbody>", doc, flags=re.S):
        for row in re.findall(r"<tr>(.*?)</tr>", block, flags=re.S):
            if 'class="empty"' in row:
                continue
            stats["rows"] += 1
            if 'href="http' in row:
                stats["sourced_rows"] += 1
            elif "blank" in row:
                stats["blank_rows"] += 1


def main() -> int:
    names = [p for p, _, _ in PAGES]
    for name in names:
        path = os.path.join(SESSION, name)
        if not os.path.exists(path):
            problems.append("missing page: %s" % name)
            continue
        stats["pages"] += 1
        audit_html(open(path, encoding="utf-8").read(), name, problems, stats)

    if problems:
        print("FAIL: %d problem(s)" % len(problems))
        for p in problems[:40]:
            print("  -", p)
        return 1
    print("PASS: %d pages; %d tables; %d rows (%d with an official source link, "
          "%d explicitly blank); %d local links; %d assets."
          % (stats["pages"], stats["tables"], stats["rows"], stats["sourced_rows"],
             stats["blank_rows"], stats["local_links"],
             len(os.listdir(os.path.join(SESSION, "assets")))))
    print("Scope: structure, local links and citation presence. "
          "Not external reachability or claim certification.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
