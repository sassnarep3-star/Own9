#!/usr/bin/env python3
"""Build the self-contained audit pages. No network access or dependencies required."""
from html import escape
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
PAGES = (
    ("README.md", "index.html", "Overview"),
    ("integration-handoff.md", "methodology.html", "Methodology"),
    ("dashboard-row-audit.md", "audit.html", "Row audit"),
    ("source-ledger.md", "sources.html", "Sources"),
    ("flags.md", "flags.html", "Flagged for review"),
)
TOKEN = re.compile(r"\[([^\]]+)\]\(([^\s)]+)\)|\*\*(.+?)\*\*|`([^`]+)`")


def inline(text):
    """Escape all content and render the deliberately small Markdown subset we use."""
    output = []
    pos = 0
    for match in TOKEN.finditer(text):
        output.append(escape(text[pos:match.start()]))
        label, href, strong, code = match.groups()
        if label is not None:
            if not (href.startswith("https://") or re.fullmatch(r"[a-zA-Z0-9_./-]+\.html", href)):
                raise ValueError(f"Unsupported link: {href}")
            output.append(f'<a href="{escape(href, quote=True)}">{escape(label)}</a>')
        elif strong is not None:
            output.append(f"<strong>{escape(strong)}</strong>")
        else:
            output.append(f"<code>{escape(code)}</code>")
        pos = match.end()
    output.append(escape(text[pos:]))
    return "".join(output)


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def render_markdown(markdown):
    lines = markdown.splitlines()
    if not lines or not lines[0].startswith("# "):
        raise ValueError("Each document needs a title")
    title = lines[0][2:].strip()
    result = []
    section = title
    i = 1
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith("## "):
            section = line[3:].strip()
            result.append(f"<h2>{inline(section)}</h2>")
            i += 1
            continue
        if line.startswith("### "):
            section = line[4:].strip()
            result.append(f"<h3>{inline(section)}</h3>")
            i += 1
            continue
        if line.startswith("| "):
            if i + 1 >= len(lines) or not re.fullmatch(r"[| :\-]+", lines[i + 1].strip()):
                raise ValueError(f"Malformed table in {title}: {line}")
            header = cells(line)
            result.append('<div class="table-wrap" tabindex="0" role="region" aria-label="Scrollable table">')
            result.append('<table><caption class="sr-only">' + inline(section) + '</caption><thead><tr>')
            result.extend(f'<th scope="col">{inline(cell)}</th>' for cell in header)
            result.append('</tr></thead><tbody>')
            i += 2
            while i < len(lines) and lines[i].strip().startswith("| "):
                row = cells(lines[i])
                if len(row) != len(header):
                    raise ValueError(f"Wrong number of cells in {title}: {lines[i]}")
                result.append('<tr>' + ''.join(f'<td>{inline(cell)}</td>' for cell in row) + '</tr>')
                i += 1
            result.append('</tbody></table></div>')
            continue
        if line.startswith("- "):
            result.append('<ul>')
            while i < len(lines) and lines[i].strip().startswith("- "):
                result.append(f'<li>{inline(lines[i].strip()[2:])}</li>')
                i += 1
            result.append('</ul>')
            continue
        para = []
        while i < len(lines):
            candidate = lines[i].strip()
            if not candidate or candidate.startswith(("## ", "### ", "| ", "- ")):
                break
            para.append(candidate)
            i += 1
        if not para:
            raise ValueError(f"Unexpected Markdown in {title}: {line}")
        result.append('<p>' + inline(' '.join(para)) + '</p>')
    return title, '\n'.join(result)


def render_page(source, filename, label):
    title, content = render_markdown(source)
    nav = []
    for _, href, text in PAGES:
        current = ' aria-current="page"' if href == filename else ''
        nav.append(f'<a href="{href}"{current}>{escape(text)}</a>')
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Independent source verification and research limitations for NFL line origination.">
<title>{escape(title)} · Own9 audit</title>
<link rel="stylesheet" href="audit.css">
</head>
<body>
<a class="skip" href="#content">Skip to content</a>
<header><div class="shell header-inner"><a class="brand" href="../index.html"><span>O9</span> OWN9 <small> / RESEARCH</small></a><nav aria-label="Audit navigation">{''.join(nav)}</nav></div></header>
<main id="content" class="shell"><p class="eyebrow">INDEPENDENT VERIFICATION / 04 NOV 2026</p><h1>{escape(title)}</h1>{content}</main>
<footer class="shell">Own9 · Independent review <span>Evidence is not an endorsement or a promise of profit.</span></footer>
</body>
</html>
'''


def build():
    for source, filename, label in PAGES:
        text = (HERE / source).read_text(encoding="utf-8")
        (HERE / filename).write_text(render_page(text, filename, label), encoding="utf-8")
    print(f"Built {len(PAGES)} independent audit pages.")


if __name__ == "__main__":
    build()
