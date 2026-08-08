"""The field book's own tests.

Every claim in `design/field-book/07-verification.md` that names a test names
one of these. The pattern throughout: each renderer is checked against an
INDEPENDENT reading of its source, not against itself. A test that asks the
renderer what it rendered proves the renderer is consistent with itself, which
is exactly the tautology this project spends its time refusing elsewhere.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from brothersbe import book as book_mod  # noqa: E402

#: The one place the two dash characters are written in this repository's tests,
#: so the sweep below cannot be defeated by the sweep's own source being edited
#: to look for something else.
EM_DASH, EN_DASH = u"—", u"–"


class TestCommandsRenderer(unittest.TestCase):
    def test_commands_renderer_recovers_every_cli_command(self):
        """Independent reading: the CLI's own table, asked directly."""
        from brothersbe import cli as cli_mod
        expected = set(name for name, _, _ in cli_mod.COMMANDS)
        section = book_mod.render_cli_commands(ROOT)
        rendered = set(re.findall(r"`sbe ([a-z-]+)`", section.markdown))
        self.assertEqual(expected, rendered,
                         "the rendered command table and brothersbe.cli.COMMANDS disagree")
        self.assertEqual(section.verdict, "PASS")
        self.assertEqual(section.item_count, len(expected))

    def test_the_book_subcommand_is_registered_and_passthrough(self):
        from brothersbe import cli as cli_mod
        self.assertIn("book", set(name for name, _, _ in cli_mod.COMMANDS))
        self.assertIn("book", cli_mod.PASSTHROUGH,
                      "sbe book owns its own parsing, so it must dispatch by hand")

    def test_guided_renderer_names_every_skill_directory(self):
        """Independent reading: the filesystem, not the renderer's own count."""
        skills = os.path.join(ROOT, "skills")
        expected = set(n for n in os.listdir(skills)
                       if os.path.isfile(os.path.join(skills, n, "SKILL.md")))
        section = book_mod.render_guided_commands(ROOT)
        rendered = set(re.findall(r"`/brothersbe:([a-z-]+)`", section.markdown))
        self.assertEqual(expected, rendered)


class TestRolesRenderer(unittest.TestCase):
    def test_roles_renderer_names_every_agent_file(self):
        expected = set(n[:-3] for n in os.listdir(os.path.join(ROOT, "agents"))
                       if n.endswith(".md"))
        section = book_mod.render_roles(ROOT)
        rendered = set(re.findall(r"^\| `([a-z-]+)` \|", section.markdown, re.M))
        self.assertEqual(expected, rendered)

    def test_every_reviewer_role_is_read_only_and_only_the_worker_writes(self):
        """The claim chapter 04 makes in prose, asserted against the frontmatter.

        This is the test that would have caught the defect the first generated
        run exposed: the chapter said every role was read-only while
        `implementation-worker` shipped Edit and Write.
        """
        agents = os.path.join(ROOT, "agents")
        writers = []
        for name in sorted(os.listdir(agents)):
            if not name.endswith(".md"):
                continue
            text = io.open(os.path.join(agents, name), encoding="utf-8").read()
            tools = ""
            for line in text.split("\n"):
                if line.startswith("tools:"):
                    tools = line
                    break
            if "Write" in tools or "Edit" in tools:
                writers.append(name[:-3])
        self.assertEqual(writers, ["implementation-worker"],
                         "chapter 04 states exactly one role may write; the agent "
                         "definitions now say otherwise, so the chapter is wrong")


class TestChecksRenderer(unittest.TestCase):
    def test_checks_renderer_reports_declared_severity(self):
        section = book_mod.render_checks(ROOT)
        self.assertEqual(section.verdict, "PASS")
        for row in re.findall(r"^\| `[^`]+` \| [^|]+ \| ([^|]+) \|", section.markdown, re.M):
            self.assertIn(row.strip(), ("gate", "soft"),
                          "a check reached the book without a declared severity")

    def test_no_check_row_claims_pass_as_its_empty_state(self):
        """NO-DATA is never a pass, asserted over what the book actually prints."""
        section = book_mod.render_checks(ROOT)
        empties = re.findall(r"^\| `[^`]+` \| [^|]+ \| [^|]+ \| ([^|]+) \|",
                             section.markdown, re.M)
        self.assertTrue(empties, "no empty-state column was rendered")
        self.assertNotIn("PASS", [e.strip() for e in empties])

    def test_no_source_path_is_rendered_twice_over(self):
        """The `tools/tools/...` defect the first run exposed, pinned."""
        section = book_mod.render_checks(ROOT)
        self.assertNotIn("tools/tools/", section.markdown)


class TestLimitsRenderer(unittest.TestCase):
    def test_limits_renderer_names_every_heading(self):
        text = io.open(os.path.join(ROOT, "docs", "KNOWN-LIMITS.md"),
                       encoding="utf-8").read()
        expected = len([l for l in text.split("\n") if l.startswith("## ")])
        section = book_mod.render_limits(ROOT)
        self.assertEqual(section.item_count, expected)
        self.assertGreater(expected, 0)


class TestDriftCheck(unittest.TestCase):
    """These build their own tree, so nothing here depends on the state of the
    working copy and nothing here writes into it."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sbe-fieldbook-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.tree = os.path.join(self.tmp, "repo")
        for rel in ("VERSION", "DIGEST.md", "docs/KNOWN-LIMITS.md"):
            dest = os.path.join(self.tree, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy(os.path.join(ROOT, rel), dest)
        for rel in ("src/brothersbe", "agents", "skills", "tools",
                    "docs/fieldbook"):
            shutil.copytree(os.path.join(ROOT, rel), os.path.join(self.tree, rel),
                            ignore=shutil.ignore_patterns("__pycache__"))
        self.version = io.open(os.path.join(self.tree, "VERSION"),
                               encoding="utf-8").read().strip()

    def _generate(self):
        """Generate in a SUBPROCESS whose package resolves to the copied tree.

        Not a convenience. Registry discovery mounts `tools/` from wherever
        `brothersbe` was imported, so generating in this process would document
        THIS repository's checks while writing them into the copy, and the
        renderer now refuses exactly that. A fresh interpreter with the copy on
        its path makes the tree self-consistent, which is the only honest way
        to test a generator whose whole job is deriving from its own repository.
        """
        env = dict(os.environ, PYTHONPATH=os.path.join(self.tree, "src"))
        env.pop("BROTHERSBE_REGISTRIES", None)
        out = subprocess.run(
            [sys.executable, "-c",
             "import sys; from brothersbe import book; sys.exit(book.main(sys.argv[1:]))",
             self.tree],
            capture_output=True, text=True, env=env, cwd=self.tree, timeout=300)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        return out.returncode

    def _check(self, *flags):
        env = dict(os.environ, PYTHONPATH=os.path.join(self.tree, "src"))
        out = subprocess.run(
            [sys.executable, "-c",
             "import sys; from brothersbe import book; sys.exit(book.main(sys.argv[1:]))",
             self.tree, "--check"] + list(flags),
            capture_output=True, text=True, env=env, cwd=self.tree, timeout=300)
        return out.returncode, out.stdout + out.stderr

    def test_check_fails_when_a_bound_source_moves(self):
        self.assertEqual(self._generate(), 0)
        agent = os.path.join(self.tree, "agents", "qa-reviewer.md")
        text = io.open(agent, encoding="utf-8").read()
        io.open(agent, "w", encoding="utf-8").write(text + "\nA later edit.\n")
        results = book_mod.check(self.tree, self.version)
        fails = [(name, sentence) for verdict, name, sentence in results
                 if verdict == "FAIL"]
        self.assertTrue(fails, "a moved bound source must FAIL, not pass quietly")
        self.assertTrue(any("roles" == name for name, _ in fails))
        self.assertTrue(any("agents/qa-reviewer.md" in sentence for _, sentence in fails),
                        "the FAIL must name the file that moved: %s" % fails)

    def test_a_deleted_bound_source_fails_naming_it(self):
        self.assertEqual(self._generate(), 0)
        os.remove(os.path.join(self.tree, "agents", "qa-reviewer.md"))
        fails = [s for v, _, s in book_mod.check(self.tree, self.version) if v == "FAIL"]
        self.assertTrue(any("no longer exist" in s for s in fails), fails)

    def test_a_stale_stamp_is_no_data_and_never_fail(self):
        self.assertEqual(self._generate(), 0)
        chapter = os.path.join(self.tree, "docs", "fieldbook", "chapters",
                               "00-the-brief.md")
        text = io.open(chapter, encoding="utf-8").read()
        io.open(chapter, "w", encoding="utf-8").write(
            text.replace("verified-against: %s" % self.version,
                         "verified-against: 0.0.1-ancient"))
        results = book_mod.check(self.tree, self.version)
        stale = [(v, s) for v, n, s in results if n == "the-brief"]
        self.assertEqual(len(stale), 1)
        self.assertEqual(stale[0][0], "NO-DATA",
                         "prose staleness is reported, never enforced")

    def test_an_unparseable_bindings_file_is_fail_not_no_data(self):
        self.assertEqual(self._generate(), 0)
        path = os.path.join(self.tree, book_mod.BINDINGS_REL)
        io.open(path, "w", encoding="utf-8").write("{not json")
        results = book_mod.check(self.tree, self.version)
        self.assertEqual(results[0][0], "FAIL",
                         "a broken claim is not an absent one")

    def test_a_missing_bindings_file_is_no_data_not_fail(self):
        self.assertEqual(self._generate(), 0)
        os.remove(os.path.join(self.tree, book_mod.BINDINGS_REL))
        results = book_mod.check(self.tree, self.version)
        self.assertEqual(results[0][0], "NO-DATA")

    def test_strict_exits_nonzero_on_fail_and_zero_on_no_data(self):
        self.assertEqual(self._generate(), 0)
        chapter = os.path.join(self.tree, "docs", "fieldbook", "chapters",
                               "00-the-brief.md")
        text = io.open(chapter, encoding="utf-8").read()
        io.open(chapter, "w", encoding="utf-8").write(
            text.replace("verified-against: %s" % self.version,
                         "verified-against: 0.0.1-ancient"))
        self.assertEqual(book_mod.main([self.tree, "--check", "--strict"]), 0,
                         "NO-DATA must never decide the exit code")
        agent = os.path.join(self.tree, "agents", "qa-reviewer.md")
        io.open(agent, "a", encoding="utf-8").write("\ndrift\n")
        self.assertEqual(book_mod.main([self.tree, "--check", "--strict"]), 1)

    def test_two_runs_produce_byte_identical_output(self):
        self.assertEqual(self._generate(), 0)
        html = os.path.join(self.tree, book_mod.BOOK_REL, book_mod.HTML_NAME)
        first_html = io.open(html, encoding="utf-8").read()
        first_bind = io.open(os.path.join(self.tree, book_mod.BINDINGS_REL),
                             encoding="utf-8").read()
        self.assertEqual(self._generate(), 0)
        self.assertEqual(first_html, io.open(html, encoding="utf-8").read(),
                         "generation is not deterministic")
        self.assertEqual(first_bind,
                         io.open(os.path.join(self.tree, book_mod.BINDINGS_REL),
                                 encoding="utf-8").read())

    def test_author_prose_survives_a_regenerate(self):
        self.assertEqual(self._generate(), 0)
        chapter = os.path.join(self.tree, "docs", "fieldbook", "chapters",
                               "03-the-commands.md")
        sentinel = "\nA sentinel sentence the generator must never touch.\n"
        io.open(chapter, "a", encoding="utf-8").write(sentinel)
        self.assertEqual(self._generate(), 0)
        self.assertIn(sentinel, io.open(chapter, encoding="utf-8").read())

    def test_a_section_with_no_home_fails_rather_than_rendering_nowhere(self):
        chapter = os.path.join(self.tree, "docs", "fieldbook", "chapters",
                               "04-the-roles.md")
        text = io.open(chapter, encoding="utf-8").read()
        io.open(chapter, "w", encoding="utf-8").write(
            text.replace(book_mod.BEGIN_FMT % "roles", "").replace(
                book_mod.END_FMT % "roles", ""))
        try:
            book_mod.generate(self.tree)
        except book_mod.SourceUnreadable as exc:
            # Asserted on the message, not merely on the exception type: the
            # renderers run in a fixed order and `roles` splices before
            # `checks` renders, so a bare assertRaises here would also be
            # satisfied by an unrelated failure later in the same run.
            self.assertIn("roles", str(exc))
            self.assertIn("nowhere to", str(exc))
        else:
            self.fail("a section whose markers are gone must be raised, not "
                      "rendered into nothing")


class TestEmittedHtml(unittest.TestCase):
    def setUp(self):
        self.html = io.open(os.path.join(ROOT, book_mod.BOOK_REL, book_mod.HTML_NAME),
                            encoding="utf-8").read()

    def test_html_requests_no_external_host(self):
        for attr in ("src=", "href="):
            for match in re.findall(attr + r'"([^"]+)"', self.html):
                self.assertFalse(match.startswith(("http://", "https://", "//")),
                                 "the page must open offline; %s reaches a host" % match)

    def test_every_chapter_reaches_the_page(self):
        chapters = book_mod.read_chapters(ROOT)
        self.assertGreaterEqual(len(chapters), 16)
        for chapter in chapters:
            self.assertIn('id="%s"' % chapter["slug"], self.html)

    def test_the_page_names_the_sources_every_generated_table_came_from(self):
        self.assertIn("src/brothersbe/cli.py", self.html)
        self.assertIn("docs/KNOWN-LIMITS.md", self.html)


class TestProseHygiene(unittest.TestCase):
    def test_no_em_or_en_dash_in_any_chapter(self):
        offenders = []
        for chapter in book_mod.read_chapters(ROOT):
            text = io.open(chapter["path"], encoding="utf-8").read()
            if EM_DASH in text or EN_DASH in text:
                offenders.append(chapter["name"])
        self.assertEqual(offenders, [])

    def test_every_chapter_declares_a_part_that_parts_json_names(self):
        parts = book_mod.read_parts(ROOT)
        for chapter in book_mod.read_chapters(ROOT):
            self.assertIn(chapter["part"], parts,
                          "%s declares part %r, which parts.json does not name"
                          % (chapter["name"], chapter["part"]))

    def test_the_bindings_file_records_every_declared_renderer(self):
        bindings = json.loads(io.open(os.path.join(ROOT, book_mod.BINDINGS_REL),
                                      encoding="utf-8").read())
        self.assertEqual(sorted(bindings), sorted(n for n, _ in book_mod.RENDERERS))


class TestCliSurface(unittest.TestCase):
    def test_sbe_book_check_runs_from_the_command_line(self):
        out = subprocess.run([sys.executable, os.path.join(ROOT, "bin", "sbe"),
                              "book", "--check"],
                             capture_output=True, text=True, cwd=ROOT, timeout=180)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("FIELD BOOK DRIFT CHECK", out.stdout)


if __name__ == "__main__":
    unittest.main()
