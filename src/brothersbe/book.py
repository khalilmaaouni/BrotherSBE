"""`sbe book`: the field book, generated from canonical state and nothing else.

WHY THIS EXISTS. The feature list, the roles, the checks with their
severities, the laws with their enforcement classes and the honest limits are
written out by hand today in four separate documentation surfaces, and the
copies are free to disagree. This project's whole argument is that a claim
earns trust in proportion to how mechanically it can be checked, so a
hand-typed feature list inside a document arguing for derived evidence is the
product contradicting itself in public. This module makes those enumerations
derived: parsed from the files that already define them, rendered between
explicit markers, and bound to the SHA-256 of every source read, so a source
that moves without a regenerate is a FAIL naming the section and the file.

The design is in `design/field-book/`, tier T2, and `tools/sbe_design.py`
passes on it.

WHAT IS DERIVED AND WHAT IS NOT, stated plainly because the distinction is the
product. Five sections are generated: the CLI commands, the guided commands,
the reviewer roles, the registered checks with their severities, and the
honest limits. Everything else in the book is prose a human wrote, carrying a
`verified-against` stamp that records when a human last read it. A stamp is
not a correctness claim. A chapter stamped current and wrong stays wrong, and
`--check` reports a stale stamp as NO-DATA rather than FAIL for exactly that
reason: nobody can compute whether prose went wrong, only that nobody has
looked since.

DERIVATION BY IMPORT, NOT BY REGEX, WHERE THE SOURCE ALLOWS IT. The commands
renderer imports `brothersbe.cli` and reads its `COMMANDS` table as the object
it is. The checks renderer calls `brothersbe.decisions.registries()`, the
discovery this repository already uses in `evals/test_no_data_class.py`, so a
check registered next year appears in the book on the day it is registered
rather than on the day somebody remembers to list it. Only `DIGEST.md` and
`docs/KNOWN-LIMITS.md`, which are prose, are parsed as text, and both report
NO-DATA naming the file when the parse recovers nothing.

DETERMINISM. No wall-clock is read anywhere in this module, and no absolute
path is written into any output. The same tree, generated twice, produces
byte-identical chapters, bindings and HTML. `bindings.json` therefore records
no timestamp: the question `--check` asks is whether the book matches the
sources NOW, and git already holds the history of when each binding moved.

FAIL, NO-DATA AND PASS ARE NOT INTERCHANGEABLE HERE EITHER. A source that
cannot be read or parsed is a FAIL carrying the exception. A source that reads
cleanly and yields zero items is NO-DATA naming why, never an empty table a
reader would take to mean "there are none". Only a section that read a source
and recovered items PASSes. Under `--check --strict`, only FAIL decides the
exit code, consistent with every other check this repository ships.
"""
import argparse
import hashlib
import io
import json
import os
import re
import sys

from .markdown import esc, markdown_to_html, render_inline

#: Everything this module writes lives under here, relative to the repository
#: root. One directory, so removing the feature is one `git rm -r`.
BOOK_REL = os.path.join("docs", "fieldbook")
CHAPTERS_REL = os.path.join(BOOK_REL, "chapters")
BINDINGS_REL = os.path.join(BOOK_REL, "bindings.json")
PARTS_REL = os.path.join(BOOK_REL, "parts.json")
HTML_NAME = "BrotherSBE-Field-Book.html"
#: The same book without a document wrapper, for a host that supplies its own
#: doctype, head and body. Written by the same run as the standalone page so the
#: published copy and the committed page can never be two different books.
FRAGMENT_NAME = "BrotherSBE-Field-Book.fragment.html"

#: The marker convention `program/STATUS.md` already uses, so a reader who has
#: seen one generated file in this repository recognises the second.
BEGIN_FMT = "<!-- BEGIN GENERATED FIELDBOOK %s -->"
END_FMT = "<!-- END GENERATED FIELDBOOK %s -->"

FRONT_MATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
CHAPTER_NAME_RE = re.compile(r"^\d{2}-.*\.md$")


class SourceUnreadable(Exception):
    """A bound source that could not be read or parsed.

    Raised, never defaulted. A renderer that cannot read its source has two
    options available to it if it swallows the failure, and both are the
    defect this project exists to prevent: render an empty table a reader
    takes for "there are none", or render the previous run's content and
    call it current.
    """


class Section(object):
    """One generated section: its markdown, the sources it read, and its verdict.

    `verdict` is PASS when a source was read and items were recovered, and
    NO-DATA when a source was read cleanly and recovered nothing. A FAIL never
    reaches this class: it is raised as `SourceUnreadable` and reported by the
    caller, so a section cannot quietly become an empty one.
    """

    def __init__(self, name, markdown, sources, item_count, reason):
        self.name = name
        self.markdown = markdown
        self.sources = tuple(sources)
        self.item_count = item_count
        self.reason = reason
        self.verdict = "PASS" if item_count > 0 else "NO-DATA"


def _read(path):
    """Read a file as text, or raise `SourceUnreadable` naming it."""
    try:
        return io.open(path, encoding="utf-8").read()
    except (IOError, OSError, UnicodeDecodeError) as exc:
        raise SourceUnreadable("%s could not be read (%s: %s)"
                               % (path, type(exc).__name__, exc))


def _sha256(path):
    """The SHA-256 of a file's bytes, or `SourceUnreadable` naming it."""
    try:
        with open(path, "rb") as handle:
            return hashlib.sha256(handle.read()).hexdigest()
    except (IOError, OSError) as exc:
        raise SourceUnreadable("%s could not be hashed (%s: %s)"
                               % (path, type(exc).__name__, exc))


def _rel(root, path):
    """A repository-relative path with forward slashes, on every platform.

    Absolute paths never reach a rendered file: they leak the machine that
    generated it and they break determinism across two checkouts.
    """
    return os.path.relpath(path, root).replace(os.sep, "/")


def _table(headers, rows):
    """A markdown pipe table. An empty `rows` returns the empty string, and it
    is the caller's job to render NO-DATA text instead of an empty table."""
    if not rows:
        return ""
    out = ["| %s |" % " | ".join(headers),
           "|%s|" % "|".join("---" for _ in headers)]
    for row in rows:
        out.append("| %s |" % " | ".join(cell.replace("|", "\\|") for cell in row))
    return "\n".join(out)


def _no_data(reason):
    return "**NO-DATA.** %s" % reason


# ---------------------------------------------------------------------------
# Renderers. Each returns a Section and declares the sources it read.
# ---------------------------------------------------------------------------

def render_cli_commands(root):
    """Every `sbe` subcommand, from `brothersbe.cli.COMMANDS` itself.

    Imported rather than regex-parsed: the table is a Python object in the same
    package, so reading it as one removes a parser that could be wrong about a
    line continuation or a nested parenthesis.
    """
    source = os.path.join(root, "src", "brothersbe", "cli.py")
    sha = _sha256(source)
    try:
        from . import cli as cli_mod
        commands = list(cli_mod.COMMANDS)
    except Exception as exc:
        raise SourceUnreadable("src/brothersbe/cli.py did not yield a COMMANDS table "
                               "(%s: %s)" % (type(exc).__name__, exc))
    rows = []
    for entry in sorted(commands, key=lambda item: item[0]):
        name, help_ = entry[0], entry[1]
        rows.append(("`sbe %s`" % name, " ".join(help_.split())))
    body = _table(("Command", "What it does"), rows)
    if not body:
        body = _no_data("brothersbe.cli.COMMANDS holds no command, so this table is "
                        "empty rather than short. Read src/brothersbe/cli.py.")
    reason = ("%d subcommand(s) read from brothersbe.cli.COMMANDS" % len(rows)) if rows \
        else "brothersbe.cli.COMMANDS is empty"
    return Section("cli-commands", body, [(_rel(root, source), sha)], len(rows), reason)


def render_guided_commands(root):
    """The slash commands, one per directory under `skills/`, with the first
    sentence of each SKILL.md description.

    A skills directory holding no skill is NO-DATA naming the directory, never
    an empty list a reader would take to mean the guided surface does not
    exist.
    """
    skills_dir = os.path.join(root, "skills")
    if not os.path.isdir(skills_dir):
        raise SourceUnreadable("skills/ is not a directory, so the guided command "
                               "surface could not be read")
    rows, sources = [], []
    for name in sorted(os.listdir(skills_dir)):
        skill_file = os.path.join(skills_dir, name, "SKILL.md")
        if not os.path.isfile(skill_file):
            continue
        text = _read(skill_file)
        sources.append((_rel(root, skill_file), _sha256(skill_file)))
        match = FRONT_MATTER_RE.match(text)
        description = ""
        if match:
            for line in match.group(1).split("\n"):
                if line.startswith("description:"):
                    description = line.split(":", 1)[1].strip().strip("'\"")
                    break
        first = description.split(". ")[0].strip()
        rows.append(("`/brothersbe:%s`" % name, first or "(no description declared)"))
    body = _table(("Command", "When to reach for it"), rows)
    if not body:
        body = _no_data("skills/ holds no directory carrying a SKILL.md, so no guided "
                        "command could be read. This is the absence of evidence, not "
                        "evidence that the guided surface is empty.")
    reason = ("%d guided command(s) read from skills/*/SKILL.md" % len(rows)) if rows \
        else "skills/ holds no SKILL.md"
    return Section("guided-commands", body, sources, len(rows), reason)


def render_roles(root):
    """The reviewer roles, from the YAML front matter of `agents/*.md`."""
    agents_dir = os.path.join(root, "agents")
    if not os.path.isdir(agents_dir):
        raise SourceUnreadable("agents/ is not a directory, so no role could be read")
    rows, sources = [], []
    for name in sorted(os.listdir(agents_dir)):
        if not name.endswith(".md"):
            continue
        path = os.path.join(agents_dir, name)
        text = _read(path)
        sources.append((_rel(root, path), _sha256(path)))
        match = FRONT_MATTER_RE.match(text)
        if not match:
            raise SourceUnreadable("agents/%s carries no YAML front matter, so its "
                                   "role could not be read. A role rendered from a "
                                   "guess is worse than a missing one" % name)
        fields = {}
        for line in match.group(1).split("\n"):
            if ":" in line and not line.startswith(" "):
                key, value = line.split(":", 1)
                fields[key.strip()] = value.strip().strip("'\"")
        description = fields.get("description", "")
        sentences = [s.strip() for s in description.split(". ") if s.strip()]
        purpose = sentences[0] if sentences else "(no description declared)"
        covers = ". ".join(sentences[1:]) if len(sentences) > 1 else ""
        rows.append(("`%s`" % fields.get("name", name[:-3]), purpose,
                     covers or "(not stated)", fields.get("tools", "(not stated)")))
    body = _table(("Role", "What it is for", "What it covers", "Tools it may use"), rows)
    if not body:
        body = _no_data("agents/ holds no markdown file, so no role could be read.")
    reason = ("%d role(s) read from agents/*.md" % len(rows)) if rows \
        else "agents/ holds no markdown file"
    return Section("roles", body, sources, len(rows), reason)


def render_checks(root):
    """Every registered check, its severity and the registry that declares it.

    Discovery is `brothersbe.decisions.registries()`, the same rule
    `evals/test_no_data_class.py` applies, so this table is not a written list
    and cannot fall behind one.
    """
    try:
        from . import decisions as decisions_mod
        found = decisions_mod.registries()
    except Exception as exc:
        raise SourceUnreadable("the check registries could not be discovered "
                               "(%s: %s)" % (type(exc).__name__, exc))
    declarations = found.get("declarations", {})
    problems = found.get("problems", [])
    rows, sources, seen = [], [], set()
    for name in sorted(declarations):
        for entry in declarations[name]:
            check = entry.get("check")
            absolute = entry.get("path")
            # `source` is already tools-relative in some entries and carries the
            # `tools/` prefix in others, so it is not a safe thing to prefix
            # blindly: doing that printed `tools/tools/sbe_plan.py`. The
            # absolute path relativized against the root is unambiguous.
            source_rel = (_rel(root, absolute) if absolute
                          else str(entry.get("source", "(not recorded)")))
            severity = getattr(check, "severity", None) or "(not declared)"
            empty = getattr(check, "empty_expect", None) or "(not declared)"
            rows.append(("`%s`" % name, source_rel, severity, empty))
            if absolute and absolute not in seen and os.path.isfile(absolute):
                seen.add(absolute)
                sources.append((_rel(root, absolute), _sha256(absolute)))
    outside = sorted(path for path, _ in sources if path.startswith(".."))
    if outside:
        # The registries were discovered against a DIFFERENT tree than the one
        # being documented, which happens when the package is imported from an
        # installation while `sbe book` is pointed somewhere else. Recording a
        # path that climbs out of the root would bind this book to files the
        # reader's repository does not contain, and the binding would then be
        # unreproducible on any other checkout. That is a FAIL, not a path.
        raise SourceUnreadable(
            "the check registries resolved to %d file(s) outside the repository "
            "being documented (%s). The book would be describing another tree's "
            "checks. Run `sbe book` from inside the repository you mean, or "
            "import brothersbe from it." % (len(outside), ", ".join(outside[:3])))
    body = _table(("Check", "Declared in", "Severity", "Verdict when its evidence is absent"),
                  rows)
    if not body:
        body = _no_data("no registry under tools/ declared a check. That is the absence "
                        "of a reading, not a finding that this project registers none.")
    reason = "%d check declaration(s) across %d registry file(s)" % (len(rows), len(sources))
    if problems:
        reason += "; %d registry problem(s) reported by the discovery: %s" % (
            len(problems), " | ".join(problems[:3]))
    return Section("checks", body, sources, len(rows), reason)


def render_limits(root):
    """The honest limits, one row per `##` heading in `docs/KNOWN-LIMITS.md`.

    The headings are the limits; the body under each stays in that file, and
    the book links to it rather than restating it, so there is one copy.
    """
    source = os.path.join(root, "docs", "KNOWN-LIMITS.md")
    text = _read(source)
    sha = _sha256(source)
    rows = []
    for line in text.split("\n"):
        if line.startswith("## "):
            heading = line[3:].strip()
            law = ""
            match = re.search(r"\((L\d+)\)\s*$", heading)
            if match:
                law = match.group(1)
                heading = heading[:match.start()].strip()
            rows.append((heading, law or "(no law named)"))
    body = _table(("The limit, as it is stated", "Law it qualifies"), rows)
    if not body:
        body = _no_data("docs/KNOWN-LIMITS.md holds no level-two heading, so no limit "
                        "could be read from it. Read the file directly.")
    reason = ("%d limit(s) read from docs/KNOWN-LIMITS.md" % len(rows)) if rows \
        else "docs/KNOWN-LIMITS.md holds no level-two heading"
    return Section("limits", body, [(_rel(root, source), sha)], len(rows), reason)


#: The renderers, in a fixed order so two runs render the same sections in the
#: same sequence. A renderer added here is picked up by generation, by the
#: drift check and by the HTML emitter without a second registration.
RENDERERS = (
    ("cli-commands", render_cli_commands),
    ("guided-commands", render_guided_commands),
    ("roles", render_roles),
    ("checks", render_checks),
    ("limits", render_limits),
)


# ---------------------------------------------------------------------------
# Chapters
# ---------------------------------------------------------------------------

def read_chapters(root):
    """Every chapter file, parsed into its front matter and body.

    A chapters directory that does not exist, or holds no chapter, is raised
    rather than rendered as an empty book.
    """
    chapters_dir = os.path.join(root, CHAPTERS_REL)
    if not os.path.isdir(chapters_dir):
        raise SourceUnreadable("%s is not a directory, so the book has no chapters"
                               % CHAPTERS_REL.replace(os.sep, "/"))
    names = sorted(n for n in os.listdir(chapters_dir) if CHAPTER_NAME_RE.match(n))
    if not names:
        raise SourceUnreadable("%s holds no file matching NN-slug.md, so there is no "
                               "book to build" % CHAPTERS_REL.replace(os.sep, "/"))
    chapters = []
    for name in names:
        path = os.path.join(chapters_dir, name)
        text = _read(path)
        match = FRONT_MATTER_RE.match(text)
        if not match:
            raise SourceUnreadable("%s carries no YAML front matter, so its part and "
                                   "its verified-against stamp could not be read"
                                   % _rel(root, path))
        fields = {}
        for line in match.group(1).split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                fields[key.strip()] = value.strip().strip("'\"")
        chapters.append({
            "name": name,
            "path": path,
            "slug": fields.get("slug", name[:-3]),
            "title": fields.get("title", name[:-3]),
            "part": fields.get("part", "0"),
            "stamp": fields.get("verified-against", ""),
            "front": match.group(0),
            "body": text[match.end():],
        })
    return chapters


def read_parts(root):
    """The part titles, in order. A missing or unparseable file is raised."""
    path = os.path.join(root, PARTS_REL)
    text = _read(path)
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise SourceUnreadable("%s is not valid JSON (%s), so the book's parts could "
                               "not be ordered" % (PARTS_REL.replace(os.sep, "/"), exc))
    if not isinstance(data, dict) or not data:
        raise SourceUnreadable("%s holds no part, so there is nothing to order the "
                               "chapters into" % PARTS_REL.replace(os.sep, "/"))
    return data


def splice(body, name, rendered):
    """Replace the content between a section's markers, leaving everything else
    byte-identical.

    Returns `(new_body, found)`. Author prose outside the markers is never
    touched: the whole point of a marker pair is that a regenerate is safe to
    run over a file somebody is in the middle of writing.
    """
    begin, end = BEGIN_FMT % name, END_FMT % name
    start = body.find(begin)
    if start < 0:
        return body, False
    stop = body.find(end, start)
    if stop < 0:
        raise SourceUnreadable("a chapter opens the generated section %r and never "
                               "closes it; an unterminated marker would swallow the "
                               "rest of the chapter" % name)
    return body[:start] + begin + "\n\n" + rendered.rstrip() + "\n\n" + body[stop:], True


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def generate(root):
    """Render every section into its chapter and write the bindings.

    Returns `(sections, chapters, notes)`. Raises `SourceUnreadable` on any
    FAIL, which the caller reports; nothing here degrades to a partial book.
    """
    chapters = read_chapters(root)
    sections, notes = [], []
    for name, renderer in RENDERERS:
        section = renderer(root)
        sections.append(section)
        placed = 0
        for chapter in chapters:
            new_body, found = splice(chapter["body"], name, section.markdown)
            if found:
                chapter["body"] = new_body
                placed += 1
        if placed == 0:
            raise SourceUnreadable("no chapter carries the markers for the generated "
                                   "section %r, so it was rendered and had nowhere to "
                                   "go. A section nobody displays is a section nobody "
                                   "checks" % name)
        if placed > 1:
            raise SourceUnreadable("%d chapters carry the markers for the generated "
                                   "section %r; one section has one home, or the two "
                                   "copies can disagree" % (placed, name))
        notes.append("%s: %s (%s)" % (name, section.verdict, section.reason))

    for chapter in chapters:
        io.open(chapter["path"], "w", encoding="utf-8").write(
            chapter["front"] + chapter["body"])

    bindings = {}
    for section in sections:
        bindings[section.name] = {
            "sources": [{"path": path, "sha256": sha} for path, sha in section.sources],
            "item_count": section.item_count,
            "verdict": section.verdict,
        }
    io.open(os.path.join(root, BINDINGS_REL), "w", encoding="utf-8").write(
        json.dumps(bindings, indent=2, sort_keys=True) + "\n")
    return sections, chapters, notes


def check(root, version):
    """Compare every binding against its source, and every stamp against VERSION.

    Returns a list of `(verdict, name, sentence)`. A moved source is a FAIL. A
    stale stamp is NO-DATA, because nobody can compute whether prose went
    wrong, only that nobody has looked since.
    """
    results = []
    bindings_path = os.path.join(root, BINDINGS_REL)
    if not os.path.isfile(bindings_path):
        return [("NO-DATA", "bindings",
                 "%s does not exist, so no generated section could be compared against "
                 "its source. Run `sbe book` to create it."
                 % BINDINGS_REL.replace(os.sep, "/"))]
    text = _read(bindings_path)
    try:
        bindings = json.loads(text)
    except ValueError as exc:
        return [("FAIL", "bindings",
                 "%s exists and is not valid JSON (%s). A broken claim is not an absent "
                 "one." % (BINDINGS_REL.replace(os.sep, "/"), exc))]
    if not bindings:
        results.append(("NO-DATA", "bindings",
                        "%s records no section, so nothing was compared."
                        % BINDINGS_REL.replace(os.sep, "/")))

    declared = set(name for name, _ in RENDERERS)
    recorded = set(bindings)
    for missing in sorted(declared - recorded):
        results.append(("FAIL", missing,
                        "the section %r is declared by a renderer and recorded in no "
                        "binding, so the book is missing a section it claims to "
                        "generate. Run `sbe book`." % missing))
    for extra in sorted(recorded - declared):
        results.append(("FAIL", extra,
                        "the binding records the section %r, which no renderer declares "
                        "any more. Run `sbe book`." % extra))

    for name in sorted(recorded & declared):
        entry = bindings[name]
        sources = entry.get("sources") or []
        if not sources:
            results.append(("NO-DATA", name,
                            "the section %r records no source, so nothing about it "
                            "could be compared." % name))
            continue
        moved, absent = [], []
        for item in sources:
            path = os.path.join(root, item.get("path", "").replace("/", os.sep))
            if not os.path.isfile(path):
                absent.append(item.get("path", ""))
                continue
            if _sha256(path) != item.get("sha256"):
                moved.append(item.get("path", ""))
        if absent:
            results.append(("FAIL", name,
                            "the section %r was rendered from %s, which no longer "
                            "exist(s). The book is describing a file that is gone."
                            % (name, ", ".join(absent))))
        elif moved:
            results.append(("FAIL", name,
                            "the section %r was rendered from %s, which has changed "
                            "since. Run `sbe book` and commit the result."
                            % (name, ", ".join(moved))))
        elif entry.get("item_count", 0) == 0:
            results.append(("NO-DATA", name,
                            "the section %r matches its %d source(s) and recovered no "
                            "item, so it renders NO-DATA rather than an empty table."
                            % (name, len(sources))))
        else:
            results.append(("PASS", name,
                            "the section %r matches all %d of its source(s), %d item(s) "
                            "rendered." % (name, len(sources), entry.get("item_count", 0))))

    for chapter in read_chapters(root):
        stamp = chapter["stamp"]
        if not stamp:
            results.append(("NO-DATA", chapter["slug"],
                            "the chapter %s declares no verified-against stamp, so "
                            "nothing records when a human last read it."
                            % chapter["name"]))
        elif stamp != version:
            results.append(("NO-DATA", chapter["slug"],
                            "the chapter %s was verified against %s and this tree is "
                            "%s. Prose staleness is reported, never enforced: no tool "
                            "computes whether the words went wrong."
                            % (chapter["name"], stamp, version)))
        else:
            results.append(("PASS", chapter["slug"],
                            "the chapter %s carries a verified-against stamp matching "
                            "%s. That records when a human last read it, not that they "
                            "were right." % (chapter["name"], version)))
    return results


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

#: The visual identity, and why it is this one rather than a default.
#:
#: The subject is evidence: three verdicts, derived tables, receipts, a spec
#: sheet you consult rather than a story you read once. So the ground is a COOL
#: paper with a blue bias and the accent is a blueprint indigo, not the warm
#: cream and terracotta that generated documents converge on. Semantic colour
#: (pass, no-data, fail) is deliberately separate from the accent, so a verdict
#: never reads as branding.
#:
#: Three type roles, all from system stacks: a tight grotesque for headings
#: (spec-sheet voice), a serif for running prose (this book is long and gets
#: read end to end), and a monospace for anything that is data: paths, stamps,
#: verdicts, source bindings. A webfont inlined as a data URI would be the
#: richer choice and is refused here for a stated reason: this file regenerates
#: at every loop close and is committed, so a few hundred kilobytes of base64
#: would land in the diff on every regenerate.
#:
#: The one structural device is the rail on a derived block. It is not
#: decoration. It marks the boundary between what a human asserted and what was
#: derived from a file, which is the entire thesis of this book, made visible on
#: every page that carries one.
_STYLE = """
:root{
--paper:#f1f4f6;--card:#ffffff;--ink:#141a20;--muted:#59646f;--rule:#d5dce3;
--accent:#1e5687;--accent-soft:#e4ecf4;--code-bg:#e9eef3;
--pass:#1a6f4b;--nodata:#8a6612;--fail:#9e2a2a}
@media (prefers-color-scheme:dark){:root{
--paper:#0e1216;--card:#151b21;--ink:#e4eaf0;--muted:#8fa0af;--rule:#232c35;
--accent:#77b2e6;--accent-soft:#16222e;--code-bg:#131a21;
--pass:#54cf95;--nodata:#dcb85c;--fail:#ef8a8a}}
:root[data-theme=dark]{
--paper:#0e1216;--card:#151b21;--ink:#e4eaf0;--muted:#8fa0af;--rule:#232c35;
--accent:#77b2e6;--accent-soft:#16222e;--code-bg:#131a21;
--pass:#54cf95;--nodata:#dcb85c;--fail:#ef8a8a}
:root[data-theme=light]{
--paper:#f1f4f6;--card:#ffffff;--ink:#141a20;--muted:#59646f;--rule:#d5dce3;
--accent:#1e5687;--accent-soft:#e4ecf4;--code-bg:#e9eef3;
--pass:#1a6f4b;--nodata:#8a6612;--fail:#9e2a2a}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--paper);color:var(--ink);
font:16.5px/1.68 ui-serif,Charter,"Iowan Old Style",Georgia,serif;
-webkit-font-smoothing:antialiased;overflow-x:hidden}
.fb-wrap{display:grid;grid-template-columns:15.5rem minmax(0,1fr);gap:3.5rem;
max-width:78rem;margin:0 auto;padding:2.5rem 1.5rem 7rem;align-items:start}
.fb-nav{position:sticky;top:2rem;max-height:calc(100vh - 4rem);overflow-y:auto;
font-family:ui-sans-serif,system-ui,-apple-system,sans-serif;font-size:.81rem;
border-right:1px solid var(--rule);padding-right:1.25rem}
.fb-nav .part{display:flex;gap:.55rem;align-items:baseline;margin:1.4rem 0 .45rem;
color:var(--muted);text-transform:uppercase;letter-spacing:.11em;font-size:.63rem;
font-weight:650}
.fb-nav .part:first-child{margin-top:0}
.fb-nav .part b{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
font-weight:650;color:var(--accent);font-variant-numeric:tabular-nums}
.fb-nav a{display:block;padding:.22rem 0 .22rem .7rem;color:var(--ink);
text-decoration:none;border-left:2px solid var(--rule);line-height:1.35}
.fb-nav a:hover,.fb-nav a:focus-visible{color:var(--accent);
border-left-color:var(--accent);outline:none}
.fb-main{min-width:0;max-width:44rem}
.fb-main h1{font-family:ui-sans-serif,system-ui,sans-serif;font-size:1.85rem;
font-weight:650;line-height:1.15;margin:0 0 .5rem;letter-spacing:-.021em;
text-wrap:balance}
.fb-main h2{font-family:ui-sans-serif,system-ui,sans-serif;font-size:1.22rem;
font-weight:650;margin:2.6rem 0 .7rem;letter-spacing:-.013em;text-wrap:balance}
.fb-main h3{font-family:ui-sans-serif,system-ui,sans-serif;font-size:1rem;
font-weight:650;margin:1.9rem 0 .45rem;letter-spacing:-.006em}
.fb-main p{margin:0 0 1.05rem}
.fb-main ul,.fb-main ol{margin:0 0 1.05rem;padding-left:1.3rem}
.fb-main li{margin:0 0 .4rem}
.fb-main a{color:var(--accent);text-underline-offset:2px}
.fb-main code{background:var(--code-bg);padding:.09em .34em;border-radius:3px;
font:.84em ui-monospace,SFMono-Regular,Menlo,monospace}
.fb-main pre{background:var(--card);padding:.95rem 1.1rem;border-radius:4px;
overflow-x:auto;border:1px solid var(--rule);border-left:3px solid var(--accent);
margin:0 0 1.3rem}
.fb-main pre code{background:none;padding:0;font-size:.79rem;line-height:1.6}
.fb-tablewrap{overflow-x:auto;margin:0 0 1.4rem;border:1px solid var(--rule);
border-radius:4px;background:var(--card)}
.fb-main table{border-collapse:collapse;width:100%;
font-family:ui-sans-serif,system-ui,sans-serif;font-size:.82rem;
font-variant-numeric:tabular-nums}
.fb-main th,.fb-main td{text-align:left;padding:.58rem .8rem;
border-bottom:1px solid var(--rule);vertical-align:top;line-height:1.45}
.fb-main tr:last-child td{border-bottom:none}
.fb-main th{font-weight:650;color:var(--muted);text-transform:uppercase;
letter-spacing:.07em;font-size:.65rem;background:var(--accent-soft);
white-space:nowrap}
.fb-sec{scroll-margin-top:1.5rem;padding-bottom:1.2rem}
.fb-sec+.fb-sec{border-top:1px solid var(--rule);padding-top:2.6rem;margin-top:1rem}
.fb-eyebrow{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.66rem;
letter-spacing:.1em;text-transform:uppercase;color:var(--accent);margin:0 0 .3rem;
font-variant-numeric:tabular-nums}
.fb-masthead{border-bottom:2px solid var(--ink);padding-bottom:1.3rem;
margin-bottom:2.2rem}
.fb-masthead .sub{color:var(--muted);font-size:.94rem;margin:0;max-width:38rem}
.fb-stamp{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.68rem;
color:var(--muted);letter-spacing:.02em;margin:1.4rem 0 0;
border-top:1px dotted var(--rule);padding-top:.5rem}
.fb-derived{border-left:3px solid var(--accent);background:var(--accent-soft);
padding:.9rem 1rem .35rem;margin:1.3rem 0;border-radius:0 4px 4px 0}
.fb-derived-lbl{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
font-size:.63rem;text-transform:uppercase;letter-spacing:.11em;color:var(--accent);
margin:0 0 .6rem;display:block}
.fb-prov{border:1px solid var(--rule);border-radius:4px;background:var(--card);
padding:1rem 1.15rem;margin:0 0 2.2rem}
.fb-prov h2{margin:0 0 .7rem;font-size:.95rem;
font-family:ui-sans-serif,system-ui,sans-serif;font-weight:650}
.fb-prov ul{list-style:none;margin:0;padding:0;display:grid;gap:.5rem}
.fb-prov li{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.72rem;
line-height:1.5;word-break:break-word}
.fb-chip{display:inline-block;padding:.05rem .4rem;border-radius:2px;
font-size:.63rem;letter-spacing:.06em;font-weight:650;border:1px solid currentColor}
.fb-PASS{color:var(--pass)}
.fb-NODATA{color:var(--nodata)}
.fb-FAIL{color:var(--fail)}
.fb-src{color:var(--muted);display:block}
@media(max-width:900px){.fb-wrap{grid-template-columns:1fr;gap:1.75rem;
padding:1.5rem 1.1rem 4rem}
.fb-nav{position:static;max-height:none;border-right:none;padding-right:0;
border-bottom:1px solid var(--rule);padding-bottom:1.1rem}
.fb-main{max-width:none}}
@media(prefers-reduced-motion:reduce){*{animation:none!important;
transition:none!important}}
"""


def _chapter_html(chapter):
    """One chapter's HTML, with derived blocks wrapped so a reader can see the
    boundary between what a human asserted and what was read from a file.

    The body is SPLIT on the markers and each piece converted separately,
    rather than converting the whole chapter and then trying to find the
    markers in the output. The marker is an HTML comment, so a whole-body
    conversion would have left it inside a paragraph and the wrapper would have
    had to be recovered by string surgery on rendered HTML, which is the class
    of thing that works until a chapter is worded slightly differently.
    """
    body, out = chapter["body"], []
    cursor = 0
    while True:
        begin = body.find("<!-- BEGIN GENERATED FIELDBOOK ", cursor)
        if begin < 0:
            out.append(_convert(body[cursor:]))
            break
        out.append(_convert(body[cursor:begin]))
        name_end = body.find(" -->", begin)
        name = body[begin + len("<!-- BEGIN GENERATED FIELDBOOK "):name_end]
        stop = body.find(END_FMT % name, name_end)
        if stop < 0:
            # Cannot happen after `generate`, which raises on an unterminated
            # marker. Handled anyway rather than silently truncating a chapter.
            out.append(_convert(body[begin:]))
            break
        inner = body[name_end + len(" -->"):stop]
        out.append('<div class="fb-derived"><span class="fb-derived-lbl">'
                   "Derived, not written: %s</span>\n%s</div>"
                   % (esc(name), _convert(inner)))
        cursor = stop + len(END_FMT % name)
    return "\n".join(piece for piece in out if piece.strip())


def _convert(markdown_text):
    """Markdown to HTML with tables wrapped so wide ones scroll inside their own
    container and the page body never scrolls sideways."""
    if not markdown_text.strip():
        return ""
    _, html = markdown_to_html(markdown_text)
    html = html.replace("<table>", '<div class="fb-tablewrap"><table>')
    return html.replace("</table>", "</table></div>")


def _body_html(chapters, parts, sections, version):
    """Everything inside `<body>`, shared by the standalone page and the
    publishable fragment so the two can never present different books."""
    by_part = {}
    for chapter in chapters:
        by_part.setdefault(chapter["part"], []).append(chapter)
    order = sorted(by_part, key=lambda key: (len(key), key))

    nav, body = [], []
    for part in order:
        nav.append('<div class="part"><b>%s</b> %s</div>'
                   % (esc(part), esc(parts.get(part, "Part %s" % part))))
        for chapter in by_part[part]:
            nav.append('<a href="#%s">%s</a>' % (esc(chapter["slug"]),
                                                 render_inline(chapter["title"])))
            body.append(
                '<section class="fb-sec" id="%s">\n'
                '<p class="fb-eyebrow">Part %s &middot; %s</p>\n%s\n'
                '<p class="fb-stamp">%s &middot; verified against %s</p>\n</section>'
                % (esc(chapter["slug"]), esc(part),
                   esc(parts.get(chapter["part"], "")), _chapter_html(chapter),
                   esc(chapter["name"]), esc(chapter["stamp"] or "no stamp")))

    prov = ['<div class="fb-prov">',
            "<h2>What in this book was derived rather than written</h2>",
            "<ul>"]
    for section in sections:
        prov.append('<li><span class="fb-chip fb-%s">%s</span> <strong>%s</strong>, '
                    '%d item(s)<span class="fb-src">%s</span></li>'
                    % (section.verdict.replace("-", ""), esc(section.verdict),
                       esc(section.name), section.item_count,
                       esc(", ".join(path for path, _ in section.sources))))
    prov.append("</ul></div>")

    return (
        '<div class="fb-wrap">\n<nav class="fb-nav">%s</nav>\n<main class="fb-main">\n'
        '<div class="fb-masthead"><h1>The BrotherSBE Field Book</h1>\n'
        '<p class="sub">What it is, what it actually enforces, and how to run it '
        "on your project. Generated from version %s of the repository: every "
        "table below names the file it was read from.</p></div>\n%s\n%s\n"
        "</main>\n</div>"
        % ("\n".join(nav), esc(version), "\n".join(prov), "\n".join(body)))


def render_html(root, chapters, parts, sections, version):
    """One self-contained page. No external host is contacted, so it opens from
    a file path with no network."""
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        "<title>The BrotherSBE Field Book</title>\n"
        "<style>%s</style>\n</head>\n<body>\n%s\n</body>\n</html>\n"
        % (_STYLE, _body_html(chapters, parts, sections, version)))


def render_fragment(root, chapters, parts, sections, version):
    """The same book without the document wrapper, for a host that supplies its
    own `<!doctype>`, `<head>` and `<body>`.

    Same style block and same body, so a reader of the published copy and a
    reader of the committed page are looking at one book rather than two that
    happen to share a name.
    """
    return ("<title>The BrotherSBE Field Book</title>\n<style>%s</style>\n%s\n"
            % (_STYLE, _body_html(chapters, parts, sections, version)))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def repo_root(start):
    """The repository root: the nearest ancestor holding a VERSION file and a
    src/brothersbe directory. Never a silently substituted git worktree top."""
    current = os.path.abspath(start)
    while True:
        if (os.path.isfile(os.path.join(current, "VERSION"))
                and os.path.isdir(os.path.join(current, "src", "brothersbe"))):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            raise SourceUnreadable("no repository root above %s carries both a VERSION "
                                   "file and src/brothersbe" % os.path.abspath(start))
        current = parent


def _parser():
    parser = argparse.ArgumentParser(
        prog="sbe book",
        description="Generate the field book from canonical state, or check it "
                    "for drift. Absent evidence is NO-DATA and never a pass.")
    parser.add_argument("path", nargs="?", default=".",
                        help="the repository to read (default: the current one)")
    parser.add_argument("--check", action="store_true",
                        help="do not write; compare every generated section against "
                             "its source and every chapter stamp against VERSION")
    parser.add_argument("--strict", action="store_true",
                        help="with --check, exit nonzero on a FAIL. NO-DATA never "
                             "decides the exit code")
    return parser


def main(rest, exit_ok=0, exit_failed=1, exit_usage=2):
    args = _parser().parse_args(rest)
    try:
        root = repo_root(args.path)
        version = _read(os.path.join(root, "VERSION")).strip()
    except SourceUnreadable as exc:
        sys.stderr.write("sbe book: %s\n" % exc)
        return exit_usage

    if args.check:
        try:
            results = check(root, version)
        except SourceUnreadable as exc:
            sys.stdout.write("  drift      FAIL     %s\n" % exc)
            return exit_failed if args.strict else exit_ok
        sys.stdout.write("BROTHERSBE FIELD BOOK DRIFT CHECK  (advisory unless --strict; "
                         "NO-DATA is never a pass)\n")
        failed = 0
        for verdict, name, sentence in results:
            if verdict == "FAIL":
                failed += 1
            sys.stdout.write("  %-26s %-8s %s\n" % (name, verdict, sentence))
        sys.stdout.write("  %d section and chapter verdict(s), %d FAIL\n"
                         % (len(results), failed))
        if failed and args.strict:
            return exit_failed
        return exit_ok

    try:
        sections, chapters, notes = generate(root)
        parts = read_parts(root)
    except SourceUnreadable as exc:
        sys.stderr.write("sbe book: %s\n" % exc)
        return exit_failed
    out_path = os.path.join(root, BOOK_REL, HTML_NAME)
    io.open(out_path, "w", encoding="utf-8").write(
        render_html(root, chapters, parts, sections, version))
    fragment_path = os.path.join(root, BOOK_REL, FRAGMENT_NAME)
    io.open(fragment_path, "w", encoding="utf-8").write(
        render_fragment(root, chapters, parts, sections, version))
    for note in notes:
        sys.stdout.write("  %s\n" % note)
    sys.stdout.write("wrote %s and %s from %d chapter(s) and %d generated section(s)\n"
                     % (_rel(root, out_path), _rel(root, fragment_path),
                        len(chapters), len(sections)))
    return exit_ok
