#!/usr/bin/env python3
"""Fixtures for `sbe version bump`. Run: python3 tools/test_sbe_version_bump.py

Every test builds a stand-in repository root in a temporary directory carrying
all four declaration sites and runs the real command against it, because the
defect this command exists for is a HAND edit missing one of the sites, and a
fixture that mocked the files would test the mock. The suite never runs
against this repository's own root: a passing test must not be able to move
the live version by accident.

The runner helper returns three values (exit code, stdout, stderr), the house
shape the honesty meta-test can trust: a helper collapsing to two values has
been rejected by that sweep four times in this repository's history.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
SBE = os.path.join(ROOT, "bin", "sbe")

OLD = "1.0.0-rc.8"
NEW = "1.0.0-rc.9"


def sbe_version(cwd, *args):
    """Run `sbe version <args>` in cwd. Returns (exit code, stdout, stderr),
    three values so a caller can never mistake silence for a verdict."""
    out = subprocess.run([sys.executable, SBE, "version"] + list(args),
                         cwd=cwd, capture_output=True, text=True)
    return out.returncode, out.stdout, out.stderr


def make_root(version=OLD, market_second=None, digest_version=None):
    """A stand-in repo root with the four declaration sites. market_second
    and digest_version let a fixture plant a deliberate disagreement."""
    root = tempfile.mkdtemp(prefix="sbe-vbump-")
    os.makedirs(os.path.join(root, ".claude-plugin"))
    with open(os.path.join(root, "VERSION"), "w") as fh:
        fh.write(version + "\n")
    with open(os.path.join(root, ".claude-plugin", "plugin.json"), "w") as fh:
        json.dump({"name": "brothersbe", "version": version}, fh, indent=2)
    with open(os.path.join(root, ".claude-plugin", "marketplace.json"), "w") as fh:
        json.dump({"name": "stand-in", "version": version,
                   "plugins": [{"name": "brothersbe",
                                "version": market_second or version}]}, fh, indent=2)
    with open(os.path.join(root, "DIGEST.md"), "w") as fh:
        fh.write("STAND-IN DIGEST, version %s (first line carries the pin)\n"
                 "second line stays untouched, version %s mentioned here too\n"
                 % (digest_version or version, OLD))
    return root


def read_sites(root):
    with open(os.path.join(root, "VERSION")) as fh:
        v = fh.read().strip()
    with open(os.path.join(root, ".claude-plugin", "plugin.json")) as fh:
        p = json.load(fh)["version"]
    with open(os.path.join(root, ".claude-plugin", "marketplace.json")) as fh:
        m = json.load(fh)
    with open(os.path.join(root, "DIGEST.md")) as fh:
        d = fh.readline()
    return v, p, m["version"], m["plugins"][0]["version"], d


class TestHappyPath(unittest.TestCase):
    def setUp(self):
        self.root = make_root()
        self.addCleanup(shutil.rmtree, self.root)

    def test_bump_moves_all_five_declarations_and_rereads(self):
        code, out, err = sbe_version(self.root, "bump", NEW)
        self.assertEqual(code, 0, "stdout=%r stderr=%r" % (out, err))
        v, p, m1, m2, d = read_sites(self.root)
        self.assertEqual((v, p, m1, m2), (NEW, NEW, NEW, NEW))
        self.assertIn("version " + NEW, d)
        self.assertIn("re-read: all 5 declaration(s) now read " + NEW, out)

    def test_digest_second_line_and_prose_survive(self):
        code, out, err = sbe_version(self.root, "bump", NEW)
        self.assertEqual(code, 0, "stdout=%r stderr=%r" % (out, err))
        with open(os.path.join(self.root, "DIGEST.md")) as fh:
            lines = fh.read().splitlines()
        self.assertIn(OLD, lines[1], "only line 1 is a declaration site; "
                                     "line 2 is historical prose and must keep the old text")

    def test_reminders_name_the_three_undone_steps(self):
        code, out, err = sbe_version(self.root, "bump", NEW)
        self.assertEqual(code, 0, "stdout=%r stderr=%r" % (out, err))
        for token in ("CHANGELOG.md", "replay_book.py --write", "checksums.sh"):
            self.assertIn(token, out, "reminder for %s missing" % token)

    def test_dry_run_writes_nothing(self):
        code, out, err = sbe_version(self.root, "bump", NEW, "--dry-run")
        self.assertEqual(code, 0, "stdout=%r stderr=%r" % (out, err))
        self.assertIn("would edit", out)
        v, p, m1, m2, d = read_sites(self.root)
        self.assertEqual((v, p, m1, m2), (OLD, OLD, OLD, OLD))
        self.assertIn("version " + OLD, d)


class TestRefusals(unittest.TestCase):
    def test_malformed_version_refused_by_name(self):
        root = make_root()
        self.addCleanup(shutil.rmtree, root)
        code, out, err = sbe_version(root, "bump", "v1.0.0-rc.9")
        self.assertEqual(code, 2, "stdout=%r stderr=%r" % (out, err))
        self.assertIn("REFUSED", err)
        self.assertIn("v1.0.0-rc.9", err)
        self.assertEqual(read_sites(root)[0], OLD, "a refusal must write nothing")

    def test_disagreeing_sites_refused_and_each_named(self):
        root = make_root(market_second="1.0.0-rc.7")
        self.addCleanup(shutil.rmtree, root)
        code, out, err = sbe_version(root, "bump", NEW)
        self.assertEqual(code, 1, "stdout=%r stderr=%r" % (out, err))
        self.assertIn("already disagree", err)
        self.assertIn("1.0.0-rc.7", err)
        self.assertIn(OLD, err)
        self.assertEqual(read_sites(root)[0], OLD, "a refusal must write nothing")

    def test_same_version_refused_as_a_no_op(self):
        root = make_root()
        self.addCleanup(shutil.rmtree, root)
        code, out, err = sbe_version(root, "bump", OLD)
        self.assertEqual(code, 1, "stdout=%r stderr=%r" % (out, err))
        self.assertIn("succeeds at nothing", err)

    def test_missing_site_refused_by_path(self):
        root = make_root()
        self.addCleanup(shutil.rmtree, root)
        os.remove(os.path.join(root, "DIGEST.md"))
        code, out, err = sbe_version(root, "bump", NEW)
        self.assertEqual(code, 1, "stdout=%r stderr=%r" % (out, err))
        self.assertIn("DIGEST.md", err)
        with open(os.path.join(root, "VERSION")) as fh:
            self.assertEqual(fh.read().strip(), OLD, "a refusal must write nothing")

    def test_unparseable_digest_line_reads_as_disagreement_not_a_pass(self):
        root = make_root()
        self.addCleanup(shutil.rmtree, root)
        with open(os.path.join(root, "DIGEST.md"), "w") as fh:
            fh.write("a first line with no version pin at all\n")
        code, out, err = sbe_version(root, "bump", NEW)
        self.assertEqual(code, 1, "stdout=%r stderr=%r" % (out, err))
        self.assertIn("UNREADABLE", err)

    def test_bare_version_still_prints_and_exits_zero(self):
        code, out, err = sbe_version(ROOT)
        self.assertEqual(code, 0, "stdout=%r stderr=%r" % (out, err))
        self.assertIn("evidence schema", out)


if __name__ == "__main__":
    unittest.main(verbosity=1)
