#!/usr/bin/env python3
"""Fixtures for `sbe task`. Run: python3 tools/test_sbe_tasks.py

Every test here builds a real git repository in a temporary directory and runs
the real command against it. Nothing is mocked, because the defect this control
exists for lives exactly at the seam between what a writer declared and what
the tree actually shows, and a mocked diff would test the mock.

The point being pinned, in one sentence: a Bash-made write outside declared
scope is detected AFTER THE FACT by reading the diff, so the fixtures write
files with plain open() calls, exactly the way a shell edit lands, and never
through any tool the fence hook could have seen.
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import shutil
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
SBE = os.path.join(ROOT, "bin", "sbe")


def git(cwd, *args):
    out = subprocess.run(["git"] + list(args), cwd=cwd, capture_output=True, text=True)
    if out.returncode != 0:
        raise AssertionError("git %s failed in %s: %s" % (" ".join(args), cwd, out.stderr))
    return out.stdout.strip()


def write(cwd, rel, body):
    path = os.path.join(cwd, rel)
    directory = os.path.dirname(path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(body)
    return path


class TaskFixture(unittest.TestCase):
    """A fresh repository per test, with one base commit already in it."""

    def setUp(self):
        self.repo = tempfile.mkdtemp()
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "fixture@example.invalid")
        git(self.repo, "config", "user.name", "fixture")
        write(self.repo, "README.md", "base\n")
        write(self.repo, "src/owned.py", "x = 1\n")
        write(self.repo, "docs/other.md", "prose\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "base")
        self.base = git(self.repo, "rev-parse", "HEAD")

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def commit(self, message="change"):
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", message)
        return git(self.repo, "rev-parse", "HEAD")

    def sbe(self, *argv):
        out = subprocess.run([sys.executable, SBE, "task"] + list(argv) +
                             ["--cwd", self.repo], capture_output=True, text=True)
        # Three values, not two: a two-value return reads as a possible
        # (verdict, evidence) pair to the honesty meta-test, which refuses any
        # such function sitting outside a check registry.
        return out.returncode, out.stdout + out.stderr, out.stderr

    def open_task(self, task_id="w1", agent="alpha", role="writer", owns=("src/owned.py",),
                  base=None, extra=()):
        argv = ["open", "--id", task_id, "--agent", agent, "--role", role,
                "--base", base or self.base, "--verify", "python3 -m pytest"]
        for p in owns:
            argv += ["--owns", p]
        argv += list(extra)
        return self.sbe(*argv)

    def registry(self):
        with io.open(os.path.join(self.repo, ".sbe", "tasks.json"),
                     encoding="utf-8") as fh:
            return json.load(fh)


class TestRoundTrip(TaskFixture):
    def test_open_list_close_round_trip_clean_diff_closes_clean(self):
        code, text, _ = self.open_task()
        self.assertEqual(code, 0, text)
        code, text, _ = self.sbe("list")
        self.assertEqual(code, 0, text)
        self.assertIn("w1", text)
        self.assertIn("alpha", text)
        write(self.repo, "src/owned.py", "x = 2\n")
        self.commit()
        code, text, _ = self.sbe("close", "w1")
        self.assertEqual(code, 0, text)
        self.assertIn("PASS", text)
        self.assertIn("Closed clean", text)
        record = [t for t in self.registry()["tasks"] if t["id"] == "w1"][0]
        self.assertEqual(record["status"], "closed", record)
        self.assertTrue(record["closedAt"], "a closed task must carry its closedAt")
        self.assertNotIn("forced", record, "a clean close must not look forced")


class TestTheDefect(TaskFixture):
    def test_a_bash_made_edit_outside_owned_paths_is_named_at_close(self):
        """THE DEFECT THIS CONTROL EXISTS FOR. The write below goes through
        plain open(), the way a shell edit lands, past every pre-write hook.
        The close reads the diff and names it anyway."""
        self.open_task()
        write(self.repo, "src/owned.py", "x = 2\n")
        write(self.repo, "docs/other.md", "sneaky\n")  # plain open(), no tool
        self.commit()
        code, text, _ = self.sbe("close", "w1")
        self.assertNotEqual(code, 0, "an out-of-scope write must not close clean")
        self.assertIn("VIOLATION", text)
        self.assertIn("docs/other.md", text, "the violation must be named by path")
        record = [t for t in self.registry()["tasks"] if t["id"] == "w1"][0]
        self.assertEqual(record["status"], "open", "the task must stay open on FAIL")

    def test_an_uncommitted_edit_counts_via_the_porcelain_path(self):
        self.open_task()
        write(self.repo, "docs/other.md", "uncommitted sneak\n")  # never committed
        code, text, _ = self.sbe("close", "w1")
        self.assertNotEqual(code, 0,
                            "an uncommitted out-of-scope edit must count; the porcelain "
                            "union exists for exactly this")
        self.assertIn("docs/other.md", text)

    def test_a_rename_counts_both_sides(self):
        self.open_task(owns=("src/owned.py", "src/renamed.py"))
        git(self.repo, "mv", "docs/other.md", "docs/moved.md")
        self.commit()
        code, text, _ = self.sbe("close", "w1")
        self.assertNotEqual(code, 0, text)
        self.assertIn("docs/other.md", text, "the old side of a rename must be named")
        self.assertIn("docs/moved.md", text, "the new side of a rename must be named")


class TestOverlap(TaskFixture):
    def test_a_second_open_with_an_overlapping_owned_path_is_refused(self):
        self.open_task(task_id="first", owns=("src/",))
        code, text, _ = self.open_task(task_id="second", owns=("src/owned.py",))
        self.assertNotEqual(code, 0, "two open writers over one path is the collision "
                                     "this registry exists to refuse")
        self.assertIn("first", text, "the refusal must name the colliding task id")
        code, text, _ = self.sbe("list")
        self.assertNotIn("second", text, "a refused open must not be recorded")

    def test_check_catches_a_collision_injected_directly_into_the_json(self):
        """The registry is one JSON file anybody can edit. `check` is the scan
        that catches what `open` never saw."""
        self.open_task(task_id="honest", owns=("src/owned.py",))
        data = self.registry()
        injected = dict(data["tasks"][0])
        injected["id"] = "injected"
        injected["ownedPaths"] = ["src/"]
        data["tasks"].append(injected)
        write(self.repo, os.path.join(".sbe", "tasks.json"), json.dumps(data))
        code, text, _ = self.sbe("check")
        self.assertNotEqual(code, 0, "an injected collision must fail the scan")
        self.assertIn("COLLISION", text)
        self.assertIn("honest", text)
        self.assertIn("injected", text)


class TestNoData(TaskFixture):
    def test_a_base_commit_that_does_not_resolve_is_no_data_never_a_pass(self):
        self.open_task(base="0" * 40)
        write(self.repo, "src/owned.py", "x = 2\n")
        self.commit()
        code, text, _ = self.sbe("close", "w1")
        self.assertNotEqual(code, 0, "an unresolvable base must block, never pass")
        self.assertIn("NO-DATA", text)
        self.assertIn("not a pass", text)
        record = [t for t in self.registry()["tasks"] if t["id"] == "w1"][0]
        self.assertEqual(record["status"], "open", record)


class TestForce(TaskFixture):
    def test_force_records_the_disposition_and_marks_the_close_forced(self):
        self.open_task()
        write(self.repo, "docs/other.md", "out of scope\n")
        self.commit()
        code, text, _ = self.sbe("close", "w1", "--force", "--who", "the operator",
                              "--why", "hotfix, accepted out of band")
        self.assertEqual(code, 0, text)
        self.assertIn("FORCED", text)
        record = [t for t in self.registry()["tasks"] if t["id"] == "w1"][0]
        self.assertEqual(record["status"], "closed", record)
        self.assertEqual(record["forced"]["who"], "the operator", record)
        self.assertEqual(record["forced"]["why"], "hotfix, accepted out of band", record)
        self.assertIn("docs/other.md", record["forced"]["violations"],
                      "the forced record must carry what it waived")

    def test_force_without_who_and_why_is_refused(self):
        self.open_task()
        write(self.repo, "docs/other.md", "out of scope\n")
        self.commit()
        code, text, _ = self.sbe("close", "w1", "--force")
        self.assertNotEqual(code, 0, "a forced close with no author and no reason is an "
                                     "off switch, not a decision")


class TestReviewerSeparation(TaskFixture):
    def test_a_reviewer_cannot_open_owning_the_evidence_store(self):
        code, text, _ = self.open_task(task_id="rev", role="reviewer",
                                    owns=(".sbe/evidence/receipt.json",))
        self.assertNotEqual(code, 0, text)
        self.assertIn("evidence store", text)

    def test_a_reviewer_diff_touching_a_receipt_fails_even_with_force(self):
        self.open_task(task_id="rev", role="reviewer", owns=("docs/",))
        write(self.repo, ".sbe/evidence/receipt.json", "{\"forged\": true}\n")
        code, text, _ = self.sbe("close", "rev", "--force", "--who", "x", "--why", "y")
        self.assertNotEqual(code, 0, "force may not waive the reviewer-receipt class")
        self.assertIn("RECEIPT-VIOLATION", text)
        self.assertIn("may NOT waive", text)
        record = [t for t in self.registry()["tasks"] if t["id"] == "rev"][0]
        self.assertEqual(record["status"], "open", record)


class TestFenceView(TaskFixture):
    def test_the_fence_view_renders_agent_per_line_from_the_registry(self):
        self.open_task(task_id="w1", agent="alpha", owns=("src/owned.py",))
        self.open_task(task_id="w2", agent="beta", owns=("docs/",))
        code, text, _ = self.sbe("fence")
        self.assertEqual(code, 0, text)
        lines = [l for l in text.splitlines() if l.startswith("- ")]
        self.assertEqual(len(lines), 2, text)
        for line in lines:
            self.assertIn("agent", line,
                          "the existing fence lint recognizes a live fence by the word "
                          "'agent'; a line without it is invisible to it")
            self.assertIn("files:", line, "a fence with no files: scope fences nothing")
        self.assertIn("src/owned.py", text)


class TestCorruptRegistry(TaskFixture):
    def test_a_corrupt_registry_is_refused_with_the_reason_and_never_reset(self):
        write(self.repo, os.path.join(".sbe", "tasks.json"), "{not json at all")
        code, text, _ = self.sbe("list")
        self.assertNotEqual(code, 0, "a corrupt registry must refuse, never read as empty")
        self.assertIn("does not parse", text)
        with io.open(os.path.join(self.repo, ".sbe", "tasks.json"),
                     encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "{not json at all",
                             "the refusal must not silently reset the file")

    def test_an_unknown_schema_version_is_refused(self):
        write(self.repo, os.path.join(".sbe", "tasks.json"),
              json.dumps({"schemaVersion": "9.9", "tasks": []}))
        code, text, _ = self.sbe("open", "--id", "w1", "--agent", "a", "--role", "writer",
                              "--base", self.base, "--verify", "true")
        self.assertNotEqual(code, 0, text)
        self.assertIn("schema version", text)


class TestTheOneOverlapRule(TaskFixture):
    def test_the_overlap_rule_is_imported_rather_than_reimplemented(self):
        """Two overlap rules would drift apart on the first change to either.
        This fails if the registry ever grows a local copy of the fence hook's
        paths_overlap."""
        sys.path.insert(0, os.path.join(ROOT, "src"))
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        try:
            from brothersbe import tasks as mod
            import sbe_fence_hook
            self.assertIs(mod.paths_overlap, sbe_fence_hook.paths_overlap)
        finally:
            sys.path.pop(0)
            sys.path.pop(0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
