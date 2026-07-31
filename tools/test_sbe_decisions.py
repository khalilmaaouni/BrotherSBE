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
from importlib.machinery import SourceFileLoader

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


class TestDecidingCode(unittest.TestCase):
    def test_a_shipped_check_names_its_file_lines_and_carries_the_excerpt(self):
        code = decisions_mod.deciding_code("numbers")
        self.assertTrue(code["file"].endswith("sbe_gate.py"))
        self.assertGreater(code["lastLine"], code["firstLine"])
        self.assertIn("def gate_numbers", code["excerpt"])

    def test_an_unknown_check_is_no_data_and_never_an_invented_span(self):
        code = decisions_mod.deciding_code("not-a-real-check")
        self.assertEqual(code["excerpt"], "")
        self.assertIn("NO-DATA", code["note"])
        self.assertIsNone(code["file"])

    def test_the_flowchart_is_mermaid_and_names_the_check_it_drew(self):
        chart = decisions_mod.logic_flowchart("numbers")
        self.assertTrue(chart.lstrip().startswith("flowchart"))
        self.assertIn("numbers", chart)

    # ---- Fixtures beyond the plan's three, each holding one sentence the
    # implementation makes and nothing else would catch. ----

    def test_the_excerpt_is_the_functions_own_lines_at_the_span_it_names(self):
        """The span is a pointer a reader OPENS. If the numbers do not address
        the excerpt in the file itself, the package sends a reviewer to the
        wrong lines, which is worse than printing no span at all."""
        code = decisions_mod.deciding_code("numbers")
        with io.open(code["file"], encoding="utf-8") as fh:
            file_lines = fh.readlines()
        span = "".join(file_lines[code["firstLine"] - 1:code["lastLine"]])
        self.assertEqual(span, code["excerpt"])

    def test_the_flowchart_draws_only_parts_the_registry_declares(self):
        """Every box comes from a declaration: what the check reads, the verdict
        its empty evidence gets, and its severity. A box nobody declared is a
        picture, not a record."""
        chart = decisions_mod.logic_flowchart("numbers")
        self.assertIn("NO-DATA", chart, "the declared empty-evidence verdict")
        self.assertIn("gate", chart, "the declared severity")
        self.assertIn("numbers-manifest.json", chart,
                      "the evidence the check declares it reads")

    def test_an_unknown_check_gets_no_flowchart_and_says_why(self):
        chart = decisions_mod.logic_flowchart("not-a-real-check")
        self.assertIn("NO-DATA", chart)
        self.assertIn("not-a-real-check", chart)
        self.assertFalse(chart.lstrip().startswith("flowchart"),
                         "a check nobody resolved gets a named absence, never a drawing")

    def test_a_check_name_two_registries_declare_says_so_rather_than_picking_quietly(self):
        """`migration` is declared by BOTH tools/sbe_gate.py and
        tools/sbe_plan.py. Resolving one of them in silence would print a span
        from a file the reader was not thinking about."""
        code = decisions_mod.deciding_code("migration")
        self.assertIsNotNone(code["file"])
        self.assertIn("sbe_plan.py", code["note"] + (code["file"] or ""))
        self.assertIn("sbe_gate.py", code["note"] + (code["file"] or ""))

    def test_neither_helper_starts_a_subprocess_to_read_the_logic(self):
        """The kill criterion of this module, held as a fixture rather than as a
        sentence in a docstring. `_git` is the only door in this module through
        which a child process is started, so a run that cannot open that door
        and still answers is a run that read files and nothing else."""
        original = decisions_mod._git

        def refuse(*a, **kw):
            raise AssertionError("deciding_code and logic_flowchart started a process")

        decisions_mod._git = refuse
        try:
            code = decisions_mod.deciding_code("numbers")
            chart = decisions_mod.logic_flowchart("numbers")
        finally:
            decisions_mod._git = original
        self.assertIn("def gate_numbers", code["excerpt"])
        self.assertTrue(chart.lstrip().startswith("flowchart"))

    def test_the_package_carries_the_deciding_code_and_the_flowchart(self):
        tmp = tempfile.mkdtemp(prefix="sbe-deciding-")
        _git_repo(tmp)
        pkg = decisions_mod.build_package(
            tmp, {"kind": "gate", "check": "numbers", "verdict": "FAIL",
                  "verdictLine": "numbers FAIL an overstated total in report.md",
                  "otherLines": [], "dossier": None})
        self.assertIn("def gate_numbers", pkg["decidingCode"]["excerpt"])
        self.assertTrue(pkg["logicFlowchart"].lstrip().startswith("flowchart"))
        with io.open(decisions_mod.write_package(tmp, pkg), encoding="utf-8") as fh:
            body = fh.read()
        self.assertIn("def gate_numbers", body)
        self.assertIn("```mermaid", body)
        # Escapes, not the glyphs themselves, for the reason stated in
        # TestPackageWriter above: this repository bans both characters from
        # every file, including the test that checks for them.
        for banned in ("\u2014", "\u2013"):
            self.assertNotIn(banned, body)

    def test_a_fenced_block_is_longer_than_any_fence_inside_it(self):
        """An excerpt of real source can carry a fence of its own, and a three
        tick fence around it would close the block early and spill the rest of
        the deciding function into the document as prose."""
        block = decisions_mod._fenced("a = '''```not the end```'''\n", "python")
        opener = block.splitlines()[0]
        self.assertTrue(opener.startswith("````"), opener)
        self.assertEqual(block.splitlines()[-1], opener[:-len("python")])

    def test_the_discovery_rule_here_and_in_the_honesty_meta_test_agree(self):
        """decisions.registries() cannot IMPORT evals/test_no_data_class.py: that
        module imports every module under tools/, this one among them, and this
        one imports brothersbe.decisions, so the import would be a cycle. The
        two therefore state the same rule twice, and this fixture is what stops
        the second copy from drifting: it asks both for their registries and
        fails on any disagreement, so a rule changed there goes red here."""
        meta = SourceFileLoader(
            "sbe_no_data_class_for_decisions",
            os.path.join(ROOT, "evals", "test_no_data_class.py")).load_module()
        modules, failures = meta.load_tool_modules()
        self.assertEqual(failures, [], "the meta-test could not import part of tools/")
        registries, defects = meta.discover_registries(modules)
        self.assertEqual(defects, [], defects)
        theirs = set()
        for source, attr, table in registries:
            for check_name in table:
                theirs.add(("tools/%s" % source, attr, check_name))
        found = decisions_mod.registries()
        self.assertEqual(found["problems"], [], found["problems"])
        mine = set()
        for check_name, entries in found["declarations"].items():
            for entry in entries:
                mine.add((entry["source"], entry["registry"], check_name))
        self.assertEqual(mine, theirs,
                         "the two discoveries disagree, so one of them is reading a registry "
                         "the other cannot see")
        self.assertTrue(mine, "neither discovery found a registry at all")

    def test_a_package_for_a_check_nobody_ships_says_no_data_in_both_sections(self):
        tmp = tempfile.mkdtemp(prefix="sbe-deciding-unknown-")
        _git_repo(tmp)
        pkg = decisions_mod.build_package(
            tmp, {"kind": "forced-close", "check": "", "verdict": "FAIL",
                  "verdictLine": "a human forced this closed", "otherLines": [],
                  "dossier": None})
        with io.open(decisions_mod.write_package(tmp, pkg), encoding="utf-8") as fh:
            body = fh.read()
        self.assertIn("NO-DATA", pkg["decidingCode"]["note"])
        self.assertIn("NO-DATA", pkg["logicFlowchart"])
        self.assertNotIn("```mermaid", body,
                         "no fenced diagram is drawn where no logic was read")


if __name__ == "__main__":
    unittest.main(verbosity=2)
