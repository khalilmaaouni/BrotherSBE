#!/usr/bin/env python3
"""Build docs/book/*.md chapters into one self-contained offline HTML book.

Vendored asset: docs/book/assets/mermaid.min.js is mermaid.js version 10.9.1,
fetched from the official CDN at
https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js
on 2026-07-30, sha256 61b335a46df05a7ce1c98378f60e5f3e77a7fb608a1056997e8a649
304a936d6, verified with `node --check` (valid JavaScript, 3335717 bytes).
That fetch reached the network; this build never does. The file is a content
asset the HTML inlines, never a Python import, and never fetched at build or
read time from any URL.

What this builder converts, and nothing more: ATX headings (# through ######),
paragraphs, fenced code blocks (```lang for a language class, ```mermaid for a
diagram that becomes <pre class="mermaid">), **bold**, [text](url) links,
pipe tables with a header separator row, and flat unordered (-, *) or ordered
(1.) lists. It is a hand-rolled subset parser, not a Markdown library: inline
code spans (single backticks), nested lists, blockquotes, and images are not
part of this subset and render as literal characters if a chapter uses them.

Chapters are every docs/book/[0-9][0-9]-*.md file, read in lexical filename
order, which is the book's table of contents order. The nav is built from
each chapter's first heading (its title); nav links are in-page anchors only.
One deliberate exception to this project's no-dash rule lives beside this
file: assets/mermaid.min.js is a vendored third party library, and its
minified bytes carry whatever characters upstream shipped, including dashes
this project would never write itself. Editing a dependency's bytes to
satisfy a house style rule would be worse than the rule it satisfied, so the
asset is excluded from the dash scan by being what it is, a vendored file,
and every line of prose around it obeys the rule.

The output is one UTF-8 HTML file, self-contained: the vendored mermaid.js is
inlined into a <script> tag, styling is one inlined <style> block with a
print stylesheet, and nothing in the page loads from an external URL.

Run: python3 docs/book/build_book.py
Standard library only.
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BOOK_DIR = os.path.join(ROOT, "docs", "book")
ASSETS_DIR = os.path.join(BOOK_DIR, "assets")
OUT_NAME = "BrotherSBE-for-Dummies.html"

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
FENCE_OPEN_RE = re.compile(r"^```\s*(\S*)\s*$")
FENCE_CLOSE_RE = re.compile(r"^```\s*$")
TABLE_SEP_RE = re.compile(r"^\s*\|[\s:\-|]+\|\s*$")
UL_RE = re.compile(r"^\s*[-*]\s+(.*)$")
OL_RE = re.compile(r"^\s*\d+\.\s+(.*)$")
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
CODE_RE = re.compile(r"`([^`\n]+)`")


def esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_inline(text):
    """Escape then apply bold and link markup. Order matters: HTML escaping
    runs first, on raw text only, so the tags this function adds afterward
    are never themselves escaped."""
    text = esc(text)
    # Code spans first, and their contents are shielded from the markup passes
    # that follow: a path like `**/*.py` or a command carrying an underscore is
    # code, not emphasis, and a reader who sees literal backticks in a book
    # about precision loses confidence in every other line on the page.
    spans = []

    def _stash(match):
        spans.append(match.group(1))
        return "\x00%d\x00" % (len(spans) - 1)

    text = CODE_RE.sub(_stash, text)
    text = BOLD_RE.sub(r"<strong>\1</strong>", text)
    text = LINK_RE.sub(
        lambda m: '<a href="%s">%s</a>' % (m.group(2).replace('"', "&quot;"), m.group(1)),
        text)
    for index, body in enumerate(spans):
        text = text.replace("\x00%d\x00" % index, "<code>%s</code>" % body)
    return text


def markdown_to_html(text):
    """Convert one chapter's Markdown subset to HTML. Returns (title, html):
    title is the raw text of the first level-1 heading, undecorated, for the
    caller to use as the chapter's nav label and id."""
    lines = text.split("\n")
    i, n = 0, len(lines)
    out = []
    title = None
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        m = HEADING_RE.match(line)
        if m:
            level, heading = len(m.group(1)), m.group(2).strip()
            if title is None and level == 1:
                title = heading
            out.append("<h%d>%s</h%d>" % (level, render_inline(heading), level))
            i += 1
            continue
        m = FENCE_OPEN_RE.match(line)
        if m:
            lang = m.group(1)
            i += 1
            code_lines = []
            while i < n and not FENCE_CLOSE_RE.match(lines[i]):
                code_lines.append(lines[i])
                i += 1
            i += 1
            code = esc("\n".join(code_lines))
            if lang == "mermaid":
                out.append('<pre class="mermaid">%s</pre>' % code)
            elif lang:
                out.append('<pre><code class="language-%s">%s</code></pre>' % (lang, code))
            else:
                out.append("<pre><code>%s</code></pre>" % code)
            continue
        if line.lstrip().startswith("|") and i + 1 < n and TABLE_SEP_RE.match(lines[i + 1]):
            header = [c.strip() for c in line.strip().strip("|").split("|")]
            i += 2
            rows = []
            while i < n and lines[i].lstrip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            thead = "<tr>%s</tr>" % "".join("<th>%s</th>" % render_inline(c) for c in header)
            tbody = "".join(
                "<tr>%s</tr>" % "".join("<td>%s</td>" % render_inline(c) for c in row)
                for row in rows)
            out.append("<table><thead>%s</thead><tbody>%s</tbody></table>" % (thead, tbody))
            continue
        ordered = OL_RE.match(line) is not None
        unordered = UL_RE.match(line) is not None
        if ordered or unordered:
            items = []
            while i < n:
                om, um = OL_RE.match(lines[i]), UL_RE.match(lines[i])
                if ordered and om:
                    items.append(om.group(1))
                    i += 1
                elif unordered and um:
                    items.append(um.group(1))
                    i += 1
                else:
                    break
            tag = "ol" if ordered else "ul"
            body = "".join("<li>%s</li>" % render_inline(it) for it in items)
            out.append("<%s>%s</%s>" % (tag, body, tag))
            continue
        para = []
        while (i < n and lines[i].strip() and not HEADING_RE.match(lines[i])
               and not FENCE_OPEN_RE.match(lines[i]) and not UL_RE.match(lines[i])
               and not OL_RE.match(lines[i]) and not lines[i].lstrip().startswith("|")):
            para.append(lines[i].strip())
            i += 1
        out.append("<p>%s</p>" % render_inline(" ".join(para)))
    return title, "\n".join(out)


def chapter_files():
    names = os.listdir(BOOK_DIR)
    chapters = sorted(n for n in names if re.match(r"^\d{2}-.*\.md$", n))
    return chapters


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>BrotherSBE for Dummies</title>
<style>
body { font-family: Georgia, "Times New Roman", serif; max-width: 46em; margin: 0 auto;
  padding: 1em 2em 4em; line-height: 1.5; color: #1a1a1a; }
nav { border-bottom: 1px solid #ccc; margin-bottom: 2em; padding-bottom: 1em; }
nav a { display: inline-block; margin: 0 1em 0.5em 0; font-family: sans-serif;
  font-size: 0.9em; text-decoration: none; color: #205; }
h1, h2, h3 { font-family: sans-serif; }
section { border-top: 1px solid #eee; padding-top: 1.5em; margin-top: 2em; }
pre { background: #f4f4f4; padding: 0.8em; overflow-x: auto; }
table { border-collapse: collapse; margin: 1em 0; }
th, td { border: 1px solid #ccc; padding: 0.4em 0.7em; text-align: left; }
pre.mermaid { background: #fff; text-align: center; }
@media print {
  nav { display: none; }
  section { page-break-before: always; border-top: none; }
  a { color: inherit; text-decoration: none; }
  pre { white-space: pre-wrap; }
}
</style>
</head>
<body>
<nav>
%(nav)s
</nav>
%(sections)s
<script>
%(mermaid_js)s
</script>
<script>
if (window.mermaid) { mermaid.initialize({ startOnLoad: true }); }
</script>
</body>
</html>
"""


def build_book(root):
    """Build the book from docs/book/*.md under root. Returns a three-tuple
    (out_path, chapter_count, note): out_path is None and chapter_count 0 if
    no chapters exist yet, with note naming that absence rather than writing
    an empty book."""
    book_dir = os.path.join(root, "docs", "book")
    names = sorted(n for n in os.listdir(book_dir) if re.match(r"^\d{2}-.*\.md$", n))
    if not names:
        return None, 0, "no chapters found matching docs/book/[0-9][0-9]-*.md"
    chapters = []
    for name in names:
        path = os.path.join(book_dir, name)
        text = io.open(path, encoding="utf-8").read()
        title, body = markdown_to_html(text)
        slug = name[:-3]
        if title is None:
            title = slug
        chapters.append({"slug": slug, "title": title, "html": body})
    mermaid_path = os.path.join(book_dir, "assets", "mermaid.min.js")
    mermaid_js = io.open(mermaid_path, encoding="utf-8").read()
    nav = "\n".join('<a href="#%s">%s</a>' % (c["slug"], render_inline(c["title"]))
                    for c in chapters)
    sections = "\n".join('<section id="%s">\n%s\n</section>' % (c["slug"], c["html"])
                         for c in chapters)
    page = PAGE % {"nav": nav, "sections": sections, "mermaid_js": mermaid_js}
    out_path = os.path.join(book_dir, OUT_NAME)
    io.open(out_path, "w", encoding="utf-8").write(page)
    note = "wrote %s from %d chapter(s), mermaid.js inlined offline" % (OUT_NAME, len(chapters))
    return out_path, len(chapters), note


def main():
    out_path, count, note = build_book(ROOT)
    if out_path is None:
        sys.stderr.write("build_book: %s\n" % note)
        return 1
    sys.stdout.write("built %s from %d chapter(s)\n" % (OUT_NAME, count))
    return 0


if __name__ == "__main__":
    sys.exit(main())
