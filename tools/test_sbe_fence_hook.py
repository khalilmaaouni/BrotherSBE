#!/usr/bin/env python3
"""Regression tests for the BrotherSBE PreToolUse fence hook.

Run: python3 tools/test_sbe_fence_hook.py

Standard library only, matching the zero-dependency ethos of the tools. Kept in
its own file rather than folded into tools/test_sbe.py so the fence hook's
guarantees can be run, and be seen to fail, on their own.

TWO PROPERTIES CARRY THIS FILE, and everything else here is supporting detail.

  FAIL OPEN. A broken, missing, undecodable or unreadable fence registry must
  never block a write. This hook sits in front of every edit the operator makes,
  so a hook that failed closed on its own bug would stop the operator's own work,
  which is strictly worse than having no hook at all. Every failure mode this
  file can construct is asserted to ALLOW, and to say on stderr that it allowed
  and why. `TestFailOpen` is the whole class of it.

  IT SAYS WHY, AND THE ESCAPE WORKS. Every refusal names the fence that owns the
  file and what the writer should do instead, and this project's standing rule is
  that a named escape must be one that actually works. So the escape is not
  merely asserted to be present in the string: `test_the_named_escape_actually_
  releases_the_fence` performs it (appends LANDED to the fence line, exactly as
  STATE.template.md prescribes) and then replays the IDENTICAL payload and
  asserts it is now allowed. A refusal naming a door that does not open is the
  failure this test exists to catch.
"""
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK_PATH = os.path.join(HERE, "sbe_fence_hook.py")

# Import the module under test regardless of cwd, the same way tools/test_sbe.py
# imports sbe_telemetry.
_spec = importlib.util.spec_from_file_location("sbe_fence_hook", HOOK_PATH)
fh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fh)
sys.modules["sbe_fence_hook"] = fh

OWNER_SESSION = "owner-session-1111-2222"
MY_SESSION = "intruder-session-3333-4444"

#: A fence line in exactly the shape STATE.template.md prescribes.
FENCE_LINE = (
    "- agent: doc-writer (sole writer, session %s) | tier T1 | TTL 2026-12-31 |\n"
    "  objective: rewrite the setup guide |\n"
    "  files: docs/SETUP.md, tools/sbe_gate.py |\n"
    "  output: one commit |\n" % OWNER_SESSION)

REGISTRY_BODY = (
    "# STATE\n\n"
    "## Fence registry\n\n"
    + FENCE_LINE +
    "\n## Decisions\n"
)


def write(path, text):
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(text)


class FenceCase(unittest.TestCase):
    """A temp project with a STATE.md registry, and an environment that is put
    back exactly as it was found.

    The environment restore is not housekeeping: BROTHERSBE_REGISTRIES,
    BROTHERSBE_FENCE_SESSION and BROTHERSBE_FENCE_HOOK_OFF all change the hook's
    answer, so a test that leaked one of them would silently decide the verdict
    of the next test in the file."""

    ENV_KEYS = ("BROTHERSBE_REGISTRIES", "BROTHERSBE_FENCE_SESSION",
                "BROTHERSBE_FENCE_HOOK_OFF")

    def setUp(self):
        self._saved_env = {k: os.environ.get(k) for k in self.ENV_KEYS}
        for k in self.ENV_KEYS:
            os.environ.pop(k, None)
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        os.makedirs(os.path.join(self.root, "docs"))
        os.makedirs(os.path.join(self.root, "tools"))
        write(os.path.join(self.root, "docs", "SETUP.md"), "setup\n")
        self.registry = os.path.join(self.root, "STATE.md")
        write(self.registry, REGISTRY_BODY)

    def tearDown(self):
        for k, v in self._saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        # Restore any mode this test dropped, so the temp cleanup can remove it.
        for dirpath, dirnames, filenames in os.walk(self.root):
            for name in list(dirnames) + list(filenames):
                target = os.path.join(dirpath, name)
                try:
                    os.chmod(target, 0o700)
                except OSError:
                    # A path the test already removed. The cleanup below reports
                    # anything that actually blocks removal, so nothing is hidden
                    # by this line.
                    continue
        self._tmp.cleanup()

    # -- payload builders ---------------------------------------------------

    def payload(self, path, session=MY_SESSION, tool="Write", **extra):
        p = {"tool_name": tool,
             "tool_input": {"file_path": path, "content": "x"},
             "session_id": session,
             "cwd": self.root,
             "project_dir": self.root}
        p.update(extra)
        return p

    def decide(self, payload):
        return fh.decide(payload)

    # -- assertions ---------------------------------------------------------

    def assertDenied(self, decision, why=""):
        self.assertIsNotNone(
            decision.payload,
            "expected a DENY %s; the hook allowed the write. stderr notes: %s"
            % (why, decision.notes))
        out = decision.payload["hookSpecificOutput"]
        self.assertEqual(out["hookEventName"], "PreToolUse")
        self.assertEqual(out["permissionDecision"], "deny")
        return out["permissionDecisionReason"]

    def assertAllowed(self, decision, why=""):
        self.assertIsNone(
            decision.payload,
            "expected an ALLOW %s; the hook DENIED with: %s"
            % (why, decision.payload))
        return "\n".join(decision.notes)


# ---------------------------------------------------------------------------
# Property 1: a genuine ownership conflict is refused, and the refusal says why.
# ---------------------------------------------------------------------------

class TestGenuineConflictIsRefused(FenceCase):

    def test_a_write_inside_another_sessions_fence_is_denied(self):
        d = self.decide(self.payload(os.path.join(self.root, "docs", "SETUP.md")))
        reason = self.assertDenied(d, "for a file another session's fence owns")
        self.assertIn("docs/SETUP.md", reason)

    def test_the_refusal_names_the_fence_that_owns_the_file(self):
        d = self.decide(self.payload(os.path.join(self.root, "docs", "SETUP.md")))
        reason = self.assertDenied(d)
        # The owner, by every handle the reader might need to go find them.
        self.assertIn("doc-writer", reason, "the refusal must name the owning agent")
        self.assertIn(OWNER_SESSION, reason, "the refusal must name the owning session")
        self.assertIn(self.registry, reason,
                      "the refusal must name the registry file the fence lives in")
        self.assertIn("L13", reason, "the refusal must name the law it enforces")

    def test_the_refusal_names_an_escape(self):
        d = self.decide(self.payload(os.path.join(self.root, "docs", "SETUP.md")))
        reason = self.assertDenied(d)
        self.assertIn("LANDED", reason,
                      "the refusal must name the closing marker that releases the fence")
        self.assertIn("ADOPTED", reason,
                      "the refusal must name the takeover marker")
        self.assertIn(MY_SESSION, reason,
                      "the takeover escape must name the session doing the taking")

    def test_the_named_escape_actually_releases_the_fence(self):
        """The escape is PERFORMED, not merely quoted.

        This is the test the whole file is built around. A refusal that names a
        door which does not open is worse than a refusal that names none, because
        the reader spends their time on it. So: deny, then close the fence the
        way the refusal said to close it, then replay the IDENTICAL payload."""
        target = os.path.join(self.root, "docs", "SETUP.md")
        before = self.decide(self.payload(target))
        reason = self.assertDenied(before, "before the fence is closed")
        self.assertIn("LANDED", reason)

        # Perform escape 2 exactly as STATE.template.md prescribes: append the
        # evidence block, marker first, to the fence line itself.
        with io.open(self.registry, "r", encoding="utf-8") as f:
            body = f.read()
        closed = body.replace(
            "  output: one commit |\n",
            "  output: one commit |\n"
            "  LANDED 2026-07-28, evidence (verbatim, run after last edit):\n"
            "    Ran 27 tests in 14.016s OK\n")
        self.assertNotEqual(body, closed, "the fixture's fence line was not found")
        write(self.registry, closed)

        after = self.decide(self.payload(target))
        self.assertAllowed(
            after, "after the fence line was closed with LANDED, which is exactly "
                   "what the refusal told the writer to do")

    def test_the_owner_of_the_fence_is_never_refused_its_own_file(self):
        d = self.decide(self.payload(os.path.join(self.root, "docs", "SETUP.md"),
                                     session=OWNER_SESSION))
        self.assertAllowed(d, "for the session the fence line names as sole writer")

    def test_an_abbreviated_session_id_in_the_registry_still_matches_its_owner(self):
        """A registry is hand-written and an operator abbreviates a UUID as often
        as they paste it. A false MISS here would refuse the rightful owner out
        of their own fence, so the match is a prefix in both directions."""
        write(self.registry, REGISTRY_BODY.replace(OWNER_SESSION, OWNER_SESSION[:8]))
        d = self.decide(self.payload(os.path.join(self.root, "docs", "SETUP.md"),
                                     session=OWNER_SESSION))
        self.assertAllowed(d, "for an owner whose id the registry abbreviated")

    def test_a_file_outside_every_fence_is_allowed(self):
        write(os.path.join(self.root, "README.md"), "readme\n")
        d = self.decide(self.payload(os.path.join(self.root, "README.md")))
        self.assertAllowed(d, "for a file no fence line claims")

    def test_a_directory_claim_covers_the_files_under_it(self):
        write(self.registry, REGISTRY_BODY.replace(
            "files: docs/SETUP.md, tools/sbe_gate.py", "files: docs/"))
        d = self.decide(self.payload(os.path.join(self.root, "docs", "SETUP.md")))
        self.assertDenied(d, "for a file under a claimed directory")

    def test_a_glob_claim_does_not_cross_a_separator_its_author_never_named(self):
        """`docs/*.md` claims docs/SETUP.md and must NOT silently swallow
        docs/guides/01-quickstart.md, which its author never named. fnmatch's '*'
        crosses '/' happily, which is why the separator guard exists."""
        os.makedirs(os.path.join(self.root, "docs", "guides"))
        write(os.path.join(self.root, "docs", "guides", "01-quickstart.md"), "g\n")
        write(self.registry, REGISTRY_BODY.replace(
            "files: docs/SETUP.md, tools/sbe_gate.py", "files: docs/*.md"))
        self.assertDenied(
            self.decide(self.payload(os.path.join(self.root, "docs", "SETUP.md"))),
            "for the file the glob names")
        self.assertAllowed(
            self.decide(self.payload(
                os.path.join(self.root, "docs", "guides", "01-quickstart.md"))),
            "for a deeper file the glob's author never named")

    def test_a_relative_path_from_a_subdirectory_is_canonicalized_before_comparison(self):
        """Comparing unresolved strings is bypassed by a relative path typed from
        a subdirectory. `../docs/SETUP.md` with cwd=tools/ is the same file."""
        d = self.decide(self.payload("../docs/SETUP.md",
                                     cwd=os.path.join(self.root, "tools")))
        self.assertDenied(d, "for a relative path that resolves into the fence")

    def test_a_dot_dot_escape_inside_an_absolute_path_is_canonicalized(self):
        weird = os.path.join(self.root, "tools", "..", "docs", "SETUP.md")
        self.assertDenied(self.decide(self.payload(weird)),
                          "for an absolute path carrying '..' into the fence")

    def test_a_multiedit_payload_is_read_to_its_nested_paths(self):
        """A MultiEdit-shaped payload whose per-edit entries carry their own
        file_path must not be reduced to the top-level path."""
        p = {"tool_name": "MultiEdit",
             "tool_input": {"file_path": os.path.join(self.root, "README.md"),
                            "edits": [{"file_path": os.path.join(
                                self.root, "docs", "SETUP.md")}]},
             "session_id": MY_SESSION, "cwd": self.root, "project_dir": self.root}
        self.assertDenied(self.decide(p), "for a fenced path nested inside the edits list")

    def test_a_write_outside_the_project_root_is_allowed(self):
        """BrotherSBE fences a project, not the filesystem."""
        with tempfile.TemporaryDirectory() as other:
            elsewhere = os.path.join(other, "SETUP.md")
            self.assertAllowed(self.decide(self.payload(elsewhere)),
                               "for a path above the project root")

    def test_a_fence_line_inside_an_html_comment_is_not_enforced(self):
        """A fence a reader of the registry cannot see must not be a fence that
        refuses them. Same rendered-text rule every other reader in this project
        applies."""
        write(self.registry, "# STATE\n\n<!--\n" + FENCE_LINE + "\n-->\n")
        self.assertAllowed(
            self.decide(self.payload(os.path.join(self.root, "docs", "SETUP.md"))),
            "for a fence line commented out of the rendered registry")

    def test_an_asterisk_bullet_fence_is_enforced(self):
        """The two bullets render identically. Enforcing only `- ` would leave a
        real fence written with `* ` unprotected, which is why this hook uses the
        broader of the two parses this project ships."""
        write(self.registry, REGISTRY_BODY.replace("- agent:", "* agent:", 1))
        self.assertDenied(
            self.decide(self.payload(os.path.join(self.root, "docs", "SETUP.md"))),
            "for a fence line written with an asterisk bullet")

    def test_an_adopted_fence_no_longer_refuses(self):
        write(self.registry, REGISTRY_BODY.replace(
            "  output: one commit |\n", "  output: one commit | ADOPTED 2026-07-28\n"))
        self.assertAllowed(
            self.decide(self.payload(os.path.join(self.root, "docs", "SETUP.md"))),
            "for a fence line closed with ADOPTED")

    def test_registries_named_by_the_env_var_are_enforced_too(self):
        """BROTHERSBE_REGISTRIES is the name the scorer and fence-lint already
        read. A fence declared there must bind here, or the three tools disagree
        about what is fenced."""
        with tempfile.TemporaryDirectory() as other:
            extra = os.path.join(other, "OTHER-STATE.md")
            write(extra, REGISTRY_BODY.replace("docs/SETUP.md", "README.md"))
            os.environ["BROTHERSBE_REGISTRIES"] = extra
            write(os.path.join(self.root, "README.md"), "r\n")
            self.assertDenied(
                self.decide(self.payload(os.path.join(self.root, "README.md"))),
                "for a fence declared in a registry named by BROTHERSBE_REGISTRIES")


# ---------------------------------------------------------------------------
# Property 2: FAIL OPEN. The class, not the instances.
# ---------------------------------------------------------------------------

class TestFailOpen(FenceCase):
    """Every one of these asserts the same two things: the write is ALLOWED, and
    a stderr note says it was allowed without the fence being checked, and why. A
    fail-open that is silent is only half a fail-open: the operator has to be
    able to tell "no fence owns this" apart from "the fence machinery is
    broken"."""

    def assertFailedOpen(self, decision, expect_in_reason, why):
        notes = self.assertAllowed(decision, why)
        self.assertIn("FAILING OPEN", notes,
                      "the fail-open must SAY it failed open (%s). notes: %s"
                      % (why, notes))
        self.assertIn("the fence was NOT checked", notes,
                      "the fail-open must say the fence went unchecked (%s)" % why)
        self.assertIn(expect_in_reason, notes,
                      "the fail-open must name its cause (%s). notes: %s"
                      % (why, notes))
        return notes

    # -- the three the brief names ------------------------------------------

    def test_fail_open_registry_file_absent(self):
        os.remove(self.registry)
        self.assertFailedOpen(
            self.decide(self.payload(os.path.join(self.root, "docs", "SETUP.md"))),
            "no fence registry was opened",
            "the registry file does not exist")

    def test_fail_open_registry_file_corrupt(self):
        """Corrupt two ways in one file: bytes that are not valid UTF-8, and text
        that decodes but carries no fence line this hook can read. Both are a
        registry that cannot support a decision, and neither may block a write."""
        with open(self.registry, "wb") as f:
            f.write(b"\xff\xfe\x00\x01 not utf-8 and not a fence \xc3\x28\n")
        self.assertFailedOpen(
            self.decide(self.payload(os.path.join(self.root, "docs", "SETUP.md"))),
            "none of them carries a live fence line",
            "the registry file holds undecodable bytes")

        write(self.registry, "# STATE\n\nthis file is prose and declares nothing\n")
        self.assertFailedOpen(
            self.decide(self.payload(os.path.join(self.root, "docs", "SETUP.md"))),
            "none of them carries a live fence line",
            "the registry file parses but declares no fence")

    @unittest.skipIf(os.geteuid() == 0 if hasattr(os, "geteuid") else False,
                     "running as root, which can read a mode 000 file, so this "
                     "scenario cannot be constructed here")
    def test_fail_open_registry_file_unreadable(self):
        os.chmod(self.registry, 0o000)
        self.assertFailedOpen(
            self.decide(self.payload(os.path.join(self.root, "docs", "SETUP.md"))),
            "could not be read",
            "the registry file exists and cannot be opened")

    # -- and the rest of the class ------------------------------------------

    def test_fail_open_when_the_registry_path_is_a_directory(self):
        os.remove(self.registry)
        os.makedirs(self.registry)
        self.assertFailedOpen(
            self.decide(self.payload(os.path.join(self.root, "docs", "SETUP.md"))),
            "not a regular file",
            "the registry path is a directory")

    @unittest.skipIf(os.geteuid() == 0 if hasattr(os, "geteuid") else False,
                     "running as root, which can enter a mode 000 directory")
    def test_fail_open_when_a_registry_directory_cannot_be_entered(self):
        """glob returns FEWER paths, not an error, over a directory it cannot
        enter, so a denied parent is exactly how a configured registry set
        silently becomes smaller. It must fail OPEN and name the directory, never
        decide over the registries it happened to reach."""
        with tempfile.TemporaryDirectory() as other:
            shut = os.path.join(other, "locked")
            os.makedirs(shut)
            write(os.path.join(shut, "OTHER-STATE.md"), REGISTRY_BODY)
            os.chmod(shut, 0o000)
            try:
                os.environ["BROTHERSBE_REGISTRIES"] = os.path.join(shut, "*.md")
                self.assertFailedOpen(
                    self.decide(self.payload(
                        os.path.join(self.root, "docs", "SETUP.md"))),
                    "cannot be entered",
                    "a configured registry directory cannot be entered")
            finally:
                os.chmod(shut, 0o700)

    def test_fail_open_when_a_live_fence_declares_no_file_scope(self):
        """A fence with no `files:` field fences nothing this hook can compare
        against. Treating that as "no conflict" in silence is the exact shape of
        a check passing over evidence it never examined, so it is reported."""
        write(self.registry, "# STATE\n\n- agent: doc-writer (sole writer, session %s) "
                             "| tier T1 | objective: something |\n" % OWNER_SESSION)
        d = self.decide(self.payload(os.path.join(self.root, "docs", "SETUP.md")))
        notes = self.assertAllowed(d, "a fence with no readable file scope")
        self.assertIn("no readable `files:` scope", notes)
        self.assertIn("did NOT enforce it", notes)

    def test_fail_open_when_the_payload_is_not_an_object(self):
        for bad in ([], "a string", 7, None):
            self.assertFailedOpen(self.decide(bad),
                                  "hook payload was not a JSON object",
                                  "the payload is %r" % (bad,))

    def test_fail_open_when_tool_input_is_not_an_object(self):
        self.assertFailedOpen(
            self.decide({"tool_name": "Write", "tool_input": "oops",
                         "session_id": MY_SESSION, "cwd": self.root}),
            "was not a JSON object",
            "tool_input is not an object")

    def test_fail_open_when_no_target_path_is_present(self):
        self.assertFailedOpen(
            self.decide({"tool_name": "Write", "tool_input": {"content": "x"},
                         "session_id": MY_SESSION, "cwd": self.root}),
            "no target path found",
            "the write tool's input names no path")

    def test_fail_open_when_the_session_has_no_identity(self):
        """Without a session id there is nothing to compare against a fence
        line's declared writer, and refusing every write on that basis would stop
        the operator's own work."""
        p = self.payload(os.path.join(self.root, "docs", "SETUP.md"))
        p.pop("session_id")
        self.assertFailedOpen(self.decide(p), "no session_id",
                              "the payload carries no session id")

    def test_the_disable_switch_allows_and_says_so(self):
        os.environ["BROTHERSBE_FENCE_HOOK_OFF"] = "1"
        d = self.decide(self.payload(os.path.join(self.root, "docs", "SETUP.md")))
        notes = self.assertAllowed(d, "the disable switch is set")
        self.assertIn("BROTHERSBE_FENCE_HOOK_OFF", notes)
        self.assertIn("the fence was NOT checked", notes)

    def test_no_failure_path_can_produce_a_deny(self):
        """The structural version of the property: over every malformed payload
        this file can think of, the hook is asserted never to deny. ALLOW and
        FAIL-OPEN are deliberately the same return value in decide(), and this is
        the test that would catch a future edit that split them."""
        fenced = os.path.join(self.root, "docs", "SETUP.md")
        malformed = [
            {}, {"tool_name": "Write"},
            {"tool_name": "Write", "tool_input": {}},
            {"tool_name": "Write", "tool_input": {"file_path": ""}},
            {"tool_name": "Write", "tool_input": {"file_path": None}},
            {"tool_name": None, "tool_input": {"file_path": fenced}},
            {"tool_name": "Write", "tool_input": {"file_path": fenced},
             "session_id": ""},
            {"tool_name": "Write", "tool_input": {"file_path": fenced},
             "session_id": 12345},
            {"tool_name": "Write", "tool_input": {"file_path": fenced},
             "session_id": MY_SESSION, "cwd": 99},
            {"tool_name": "Write", "tool_input": {"file_path": fenced},
             "session_id": MY_SESSION, "cwd": "/nonexistent/nowhere"},
        ]
        for p in malformed:
            self.assertAllowed(self.decide(p), "for malformed payload %r" % (p,))


# ---------------------------------------------------------------------------
# Case-insensitive filesystems: `paths_overlap` retries a missed comparison
# case-folded, but only trusts it once the filesystem confirms the fold is
# real, never on the string match alone.
# ---------------------------------------------------------------------------

class TestCaseFoldConfirmation(FenceCase):

    def test_a_real_case_collision_overlaps_at_the_unit_level(self):
        """docs/SETUP.md and docs/setup.md are one file on this machine
        (asserted by inode, the same proof the bypass fixture uses), so the
        case-folded retry must fire and `paths_overlap` must say True."""
        exact = os.path.join(self.root, "docs", "SETUP.md")
        variant = os.path.join(self.root, "docs", "setup.md")
        if not os.path.exists(variant):
            raise unittest.SkipTest(
                "this filesystem is case-sensitive; docs/setup.md is a different file here")
        self.assertEqual(os.stat(exact).st_ino, os.stat(variant).st_ino)
        self.assertTrue(fh.paths_overlap("docs/setup.md", "docs/SETUP.md", self.root),
                        "a real filesystem collision was not treated as an overlap")

    def test_a_case_folded_string_match_alone_is_never_trusted(self):
        """The Linux half of the fix: two honestly different files named
        `a.md` and `A.md` must not false-conflict just because their letters
        match once lowered. This machine's filesystem cannot construct that
        pair (case-insensitive by default), so the filesystem confirmation is
        forced to answer 'not the same entry', exactly what it would answer on
        a case-sensitive volume, and `paths_overlap` must still say False."""
        original = fh._same_entry_case_insensitive
        fh._same_entry_case_insensitive = lambda root, t, c: False
        try:
            self.assertFalse(
                fh.paths_overlap("docs/setup.md", "docs/SETUP.md", self.root),
                "a case-folded string match was trusted without filesystem confirmation")
        finally:
            fh._same_entry_case_insensitive = original

    def test_no_root_skips_the_fold_which_is_this_hooks_fail_open_bias(self):
        """A caller with no filesystem to confirm against (root=None) gets the
        exact-spelling answer only, never a guess."""
        self.assertFalse(fh.paths_overlap("docs/setup.md", "docs/SETUP.md"),
                         "the case-folded retry ran with nothing to confirm it against")


# ---------------------------------------------------------------------------
# The declared tool surface, including the gap that is declared rather than
# papered over.
# ---------------------------------------------------------------------------

class TestToolSurface(FenceCase):

    def test_bash_is_not_gated(self):
        """The skill's own sentence says this hook does not gate Bash, and the
        sentence has to stay true. A shell command can write any file and no
        reliable parse of arbitrary shell exists, so gating it would be a
        guarantee this file cannot keep. It is a declared gap, in docs/HOOKS.md,
        and this test is what stops it becoming an undeclared one."""
        self.assertNotIn("Bash", fh.WRITE_TOOLS)
        p = {"tool_name": "Bash",
             "tool_input": {"command": "echo x > %s"
                                       % os.path.join(self.root, "docs", "SETUP.md")},
             "session_id": MY_SESSION, "cwd": self.root, "project_dir": self.root}
        d = self.decide(p)
        self.assertAllowed(d, "Bash is outside this hook's tool surface")
        self.assertEqual(d.notes, [],
                         "a non-write tool must be silent, not loud: a stderr line "
                         "per Bash call is noise the operator learns to ignore")

    def test_read_only_tools_are_silent(self):
        for tool in ("Read", "Grep", "Glob", "TodoWrite", "WebFetch"):
            d = self.decide({"tool_name": tool,
                             "tool_input": {"file_path": os.path.join(
                                 self.root, "docs", "SETUP.md")},
                             "session_id": MY_SESSION, "cwd": self.root})
            self.assertAllowed(d, "%s is not a write tool" % tool)
            self.assertEqual(d.notes, [], "%s must be silent" % tool)

    def test_every_declared_write_tool_is_gated(self):
        for tool in sorted(fh.WRITE_TOOLS):
            key = "notebook_path" if tool == "NotebookEdit" else "file_path"
            p = {"tool_name": tool,
                 "tool_input": {key: os.path.join(self.root, "docs", "SETUP.md")},
                 "session_id": MY_SESSION, "cwd": self.root, "project_dir": self.root}
            self.assertDenied(self.decide(p), "for write tool %s" % tool)


# ---------------------------------------------------------------------------
# The wire protocol, exercised as Claude Code actually invokes it: a subprocess
# with a JSON payload on stdin.
# ---------------------------------------------------------------------------

class TestWireProtocol(FenceCase):

    def run_hook(self, payload, env_extra=None):
        env = dict(os.environ)
        env.pop("BROTHERSBE_REGISTRIES", None)
        env.update(env_extra or {})
        # A Python-side timeout, not the `timeout` command, which does not exist
        # on this platform. A hook that hangs is a hook that hangs the editor, so
        # the bound is part of the contract and not a test convenience.
        return subprocess.run(
            [sys.executable, HOOK_PATH],
            input=json.dumps(payload), capture_output=True, text=True,
            timeout=60, env=env, cwd=self.root)

    def test_a_deny_lands_on_stdout_as_json_at_exit_zero(self):
        r = self.run_hook(self.payload(os.path.join(self.root, "docs", "SETUP.md")))
        self.assertEqual(r.returncode, 0,
                         "the hook must always exit 0; exit 2 means the hook "
                         "itself failed, and every failure here is a fail-open")
        obj = json.loads(r.stdout)
        out = obj["hookSpecificOutput"]
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("LANDED", out["permissionDecisionReason"])

    def test_stdout_carries_the_decision_and_nothing_else(self):
        """Claude Code parses stdout as JSON. A diagnostic there corrupts the
        protocol, which is why every note goes to stderr."""
        os.remove(self.registry)
        r = self.run_hook(self.payload(os.path.join(self.root, "docs", "SETUP.md")))
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, "",
                         "an allow writes NOTHING to stdout; got: %r" % r.stdout)
        self.assertIn("FAILING OPEN", r.stderr)

    def test_empty_stdin_fails_open_at_exit_zero(self):
        r = subprocess.run([sys.executable, HOOK_PATH], input="",
                           capture_output=True, text=True, timeout=60, cwd=self.root)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, "")
        self.assertIn("FAILING OPEN", r.stderr)
        self.assertIn("stdin was empty", r.stderr)

    def test_unparseable_stdin_fails_open_at_exit_zero(self):
        r = subprocess.run([sys.executable, HOOK_PATH], input="{not json",
                           capture_output=True, text=True, timeout=60, cwd=self.root)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, "")
        self.assertIn("FAILING OPEN", r.stderr)
        self.assertIn("not valid JSON", r.stderr)

    def test_the_fences_subcommand_reports_without_touching_stdout(self):
        r = subprocess.run([sys.executable, HOOK_PATH, "fences", self.root],
                           capture_output=True, text=True, timeout=60, cwd=self.root)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, "",
                         "diagnostics must never reach the decision channel")
        self.assertIn("doc-writer", r.stderr)
        self.assertIn("1 live fence line(s) enforceable", r.stderr)

    def test_an_unknown_subcommand_is_refused_rather_than_read_as_a_hook_call(self):
        r = subprocess.run([sys.executable, HOOK_PATH, "claim"], input="",
                           capture_output=True, text=True, timeout=60, cwd=self.root)
        self.assertEqual(r.returncode, 2)
        self.assertIn("unknown command", r.stderr)


# ---------------------------------------------------------------------------
# Housekeeping the project asserts about itself elsewhere, asserted here for the
# two files this port adds.
# ---------------------------------------------------------------------------

class TestShippedFileHygiene(unittest.TestCase):

    FILES = (HOOK_PATH,
             os.path.join(HERE, "test_sbe_fence_hook.py"),
             os.path.join(os.path.dirname(HERE), "docs", "HOOKS.md"))

    def test_no_em_or_en_dashes(self):
        # The two characters are built with chr(), never typed. Spelling them as
        # literals would put them in this file, and this file is one of the files
        # the rule covers: the test would then fail on its own assertion text,
        # which is a false alarm that teaches the reader to weaken the rule.
        banned = ((chr(0x2014), "em dash"), (chr(0x2013), "en dash"))
        for path in self.FILES:
            if not os.path.isfile(path):
                self.fail("%s is missing; the port ships all three" % path)
            with io.open(path, "r", encoding="utf-8") as f:
                body = f.read()
            for ch, name in banned:
                self.assertNotIn(ch, body, "%s carries an %s" % (path, name))

    def test_the_hook_imports_nothing_outside_the_standard_library(self):
        """BrotherSBE is standalone by design: clone it and it works with nothing
        else installed. The only non-stdlib names this file may reach for are its
        own siblings under tools/, and those are loaded by path at call time."""
        import ast
        with io.open(HOOK_PATH, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=HOOK_PATH)
        allowed = set(sys.builtin_module_names) | {
            "fnmatch", "json", "os", "posixpath", "re", "sys", "importlib",
            "importlib.util", "glob", "ast", "io", "subprocess", "stat"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    self.assertIn(a.name.split(".")[0], allowed,
                                  "%s is not a standard library module" % a.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                self.assertIn(node.module.split(".")[0], allowed,
                              "%s is not a standard library module" % node.module)

    def test_the_hook_makes_no_network_call_and_runs_no_subprocess(self):
        with io.open(HOOK_PATH, "r", encoding="utf-8") as f:
            body = f.read()
        for forbidden in ("subprocess", "urllib", "socket", "http.client",
                          "os.system", "os.popen"):
            self.assertNotIn(
                "import " + forbidden, body,
                "the hook must make no network call and run no subprocess; it "
                "runs in front of every edit")


class TestHelpMeansHelp(unittest.TestCase):
    """`-h` used to start with a dash, miss the command table, and fall into
    HOOK mode: the tool sat reading stdin for a JSON payload nobody was going
    to send, then failed open, and `fences --bogus` was read as a directory
    named --bogus and reported "no fence is enforceable", exit 0. Help is not
    an error and a flag is not a directory. The bare hook invocation is
    untouched: it still fails open on an empty stdin, because a hook must
    never block a session. Calibrated by reinjecting the missing help branch:
    the help fixture failed (usage absent, hook fail-open text present)
    before the fix was restored, the restore verified against the
    pre-recorded `git hash-object` of the fixed file."""

    def _run(self, *argv):
        out = subprocess.run([sys.executable, HOOK_PATH] + list(argv),
                             capture_output=True, text=True, stdin=subprocess.DEVNULL)
        return out.returncode, out.stdout, out.stderr

    def test_help_exits_0_with_usage_on_stderr_and_a_clean_stdout(self):
        """Usage goes to stderr because stdout is the hook's decision channel:
        a usage text on stdout would corrupt the protocol if this ever ran in
        the hook slot with a stray flag."""
        for argv in (("-h",), ("--help",), ("fences", "-h")):
            code, stdout, stderr = self._run(*argv)
            self.assertEqual(code, 0, "%s exited %d: %s"
                             % (" ".join(argv), code, stdout + stderr))
            self.assertIn("usage: sbe_fence_hook.py", stderr,
                          "%s printed no usage on stderr: %r" % (" ".join(argv), stderr))
            self.assertEqual(stdout, "",
                             "%s wrote to stdout, the decision channel" % " ".join(argv))

    def test_a_bad_flag_on_fences_exits_2_instead_of_reading_it_as_a_directory(self):
        code, stdout, stderr = self._run("fences", "--bogus")
        self.assertEqual(code, 2, "fences --bogus exited %d: %s" % (code, stdout + stderr))
        self.assertIn("unrecognized flag", stderr)
        self.assertEqual(stdout, "", "the refusal leaked onto the decision channel")

    def test_the_bare_hook_invocation_still_fails_open(self):
        code, stdout, stderr = self._run()
        self.assertEqual(code, 0,
                         "the bare hook invocation must never block a session; it "
                         "exited %d: %s" % (code, stderr))
        self.assertIn("FAILING OPEN", stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
