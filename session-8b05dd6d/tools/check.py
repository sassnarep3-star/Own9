#!/usr/bin/env python3
"""Verify the session-8b05dd6d site (standard library only).

Checks:
  1. every internal href/src resolves to a file, and any #fragment exists in that file;
  2. every data-table body row contains at least one external https link (source link);
  3. the injury CSV matches the transcribed source file row for row;
  4. the official-host allow-list is respected for external links.
It does NOT fetch external URLs. Live availability is checked separately and logged.
"""
import csv
import html.parser
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ALLOWED_HOSTS = {"www.nfl.com", "operations.nfl.com", "www.gra.gov.sg", "gra.gov.sg",
                 "www.singaporepools.com.sg", "github.com", "gov.sg"}
errors = []


class Scan(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ids, self.rows_ok, self.rows_bad, self.in_tbody, self.row_has_link = [], set(), 0, 0, 0, None
        self.table_depth = 0
        self.row_open = False

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if "id" in d:
            self.ids.add(d["id"])
        if tag in ("a", "link", "script", "img") and ("href" in d or "src" in d):
            url = d.get("href") or d.get("src")
            self.links.append(url)
            if self.row_open and url.startswith("https://"):
                self.row_has_link = True
        if tag == "tbody":
            self.in_tbody += 1
        if tag == "tr" and self.in_tbody:
            self.row_open = True
            self.row_has_link = False
        if tag == "table":
            self.table_depth += 1

    def handle_endtag(self, tag):
        if tag == "tbody":
            self.in_tbody -= 1
        if tag == "tr" and self.row_open:
            if self.row_has_link:
                self.rows_ok += 1
            else:
                self.rows_bad += 1
            self.row_open = False


pages = sorted(f for f in os.listdir(ROOT) if f.endswith(".html"))
parsed = {}
for name in pages:
    with open(os.path.join(ROOT, name), encoding="utf-8") as fh:
        text = fh.read()
    scan = Scan()
    scan.feed(text)
    parsed[name] = scan
    if scan.rows_bad:
        errors.append(f"{name}: {scan.rows_bad} table row(s) without an https source link")
    for url in scan.links:
        if url.startswith("https://") or url.startswith("http://"):
            host = re.sub(r"^https?://", "", url).split("/")[0].lower()
            if host not in ALLOWED_HOSTS and not host.endswith(".gov.sg"):
                errors.append(f"{name}: external host not on allow-list: {url}")
            continue
        if url.startswith(("mailto:", "#")):
            continue
        target, _, frag = url.partition("#")
        path = os.path.normpath(os.path.join(ROOT, target))
        if not os.path.exists(path):
            errors.append(f"{name}: missing local target {url}")
            continue
        if frag and target.endswith(".html"):
            if frag not in parsed.get(target, Scan()).ids and target in parsed:
                errors.append(f"{name}: missing fragment #{frag} in {target}")

# CSV versus source transcription
with open(os.path.join(ROOT, "data", "injury_report_week10.psv"), encoding="utf-8") as fh:
    src_rows = [l.rstrip("\n").split("|") for l in fh if l.strip() and not l.startswith("#")]
with open(os.path.join(ROOT, "data", "injuries.csv"), encoding="utf-8") as fh:
    csv_rows = list(csv.DictReader(fh))
if len(src_rows) != len(csv_rows):
    errors.append(f"injuries.csv has {len(csv_rows)} rows, source has {len(src_rows)}")
else:
    for s, c in zip(src_rows, csv_rows):
        if (s[0], s[1], s[2], s[3], s[4], s[5], s[6]) != (c["game_id"], c["team"], c["player"], c["position"],
                                                          c["injury"], c["practice"], c["game_status"]):
            errors.append(f"injuries.csv mismatch for {s[0]} {s[1]} {s[2]}")
            break

if errors:
    print("FAIL")
    for e in errors:
        print(" -", e)
    sys.exit(1)

total_rows = sum(p.rows_ok for p in parsed.values())
print(f"OK: {len(pages)} pages, {len(parsed)} scanned; {total_rows} table rows with https source links; "
      f"{len(csv_rows)} injury rows match source.")
