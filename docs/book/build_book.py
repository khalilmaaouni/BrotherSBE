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

# The Markdown subset renderer moved to `src/brothersbe/markdown.py` when
# `sbe book` came to need the identical dialect. Two copies of a renderer are
# two renderers free to disagree, which is the drift the field book exists to
# remove, so this script imports the one that ships rather than keeping a
# second. `src/` is mounted here because this file runs as a script from the
# repository root and is not itself part of the installed package.
sys.path.insert(0, os.path.join(ROOT, "src"))

from brothersbe.markdown import (  # noqa: E402
    esc, markdown_to_html, render_inline)


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
