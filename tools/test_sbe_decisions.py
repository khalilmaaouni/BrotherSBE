"""Adversarial fixtures for decision packages, `sbe explain` and `sbe lineage`
(spec: docs/specs/2026-07-30-team-docs-collab-book-design.md, Feature 2).
Written BEFORE the implementation: on the day this lands, every scenario is red
because src/brothersbe/decisions.py does not exist, and none is red on a
fixture bug.

Every helper here returns ONE dict or three values, never a two-value tuple:
a two-value return reads as a possible (verdict, evidence) pair to the honesty
meta-test in evals/test_no_data_class.py, which refuses any such function
sitting outside a check registry.
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SBE = os.path.join(ROOT, "bin", "sbe")
sys.path.insert(0, os.path.join(ROOT, "src"))

from brothersbe import decisions as decisions_mod  # noqa: E402


def _run(argv, cwd=None):
    out = subprocess.run(argv, capture_output=True, text=True, cwd=cwd,
                         stdin=subprocess.DEVNULL, timeout=180)
    return {"code": out.returncode, "stdout": out.stdout, "stderr": out.stderr}


def _git_repo(path):
    subprocess.run(["git", "-C", path, "init", "-q"], check=True)
    subprocess.run(["git", "-C", path, "config", "user.email", "e@e"], check=True)
    subprocess.run(["git", "-C", path, "config", "user.name", "T"], check=True)
    with io.open(os.path.join(path, "seed.txt"), "w", encoding="utf-8") as fh:
        fh.write("seed\n")
    subprocess.run(["git", "-C", path, "add", "-A"], check=True)
    subprocess.run(["git", "-C", path, "commit", "-qm", "seed"], check=True)


class TestPackageWriter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sbe-decisions-")
        _git_repo(self.tmp)

    def _trigger(self, verdict):
        return {"kind": "gate", "check": "numbers", "verdict": verdict,
                "verdictLine": "numbers %s an overstated total in report.md" % verdict,
                "otherLines": ["some unquotable chatter", "more chatter"],
                "dossier": None}

    def test_a_package_is_a_dict_with_every_named_section(self):
        pkg = decisions_mod.build_package(self.tmp, self._trigger("FAIL"))
        for key in ("id", "slug", "dir", "verdictLine", "evidence", "inputs",
                    "risks", "whatWouldFlipIt", "checklist", "boundCommit",
                    "location", "locationReason", "unquotedLineCount", "notes"):
            self.assertIn(key, pkg)
        self.assertEqual(pkg["unquotedLineCount"], 2,
                         "lines outside the verdict grammar are counted, not copied")

    def test_a_waived_check_is_waived_in_the_package_and_never_pass(self):
        pkg = decisions_mod.build_package(self.tmp, self._trigger("WAIVED"))
        self.assertIn("WAIVED", pkg["verdictLine"])
        self.assertNotIn("PASS", pkg["verdictLine"])

    def test_a_trigger_with_no_verdict_line_is_no_data_not_a_package_that_reads_clean(self):
        trigger = self._trigger("FAIL")
        trigger["verdictLine"] = ""
        pkg = decisions_mod.build_package(self.tmp, trigger)
        self.assertIn("NO-DATA", pkg["verdictLine"])
        self.assertIn("NO-DATA", "\n".join(pkg["notes"]))

    def test_ids_are_allocated_from_disk_and_the_file_lands_where_it_says(self):
        first = decisions_mod.write_package(
            self.tmp, decisions_mod.build_package(self.tmp, self._trigger("FAIL")))
        second = decisions_mod.write_package(
            self.tmp, decisions_mod.build_package(self.tmp, self._trigger("FAIL")))
        self.assertTrue(os.path.isfile(first))
        self.assertTrue(os.path.isfile(second))
        self.assertNotEqual(os.path.dirname(first), os.path.dirname(second))
        self.assertIn(os.path.join(".sbe", "decisions"), first,
                      "with no 00-intake.json there is no project to name")
        body = io.open(first, encoding="utf-8").read()
        self.assertIn("bound to commit", body)
        # Escapes, not the glyphs themselves: this repository bans both
        # characters from every file, including the test that checks for them.
        for banned in ("\u2014", "\u2013"):
            self.assertNotIn(banned, body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
