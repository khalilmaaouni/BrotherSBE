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
class TestGateTriggers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sbe-gate-trigger-")
        _git_repo(self.tmp)

    def test_a_fail_and_a_waiver_each_get_their_own_package(self):
        text = ("numbers   FAIL     an overstated total in report.md\n"
                "  >> migration WAIVED  .sbe-exempt names this directory: rehearsal pending\n"
                "chatter nobody parses\n")
        written = decisions_mod.record_from_run(self.tmp, text, None)
        self.assertEqual(len(written), 2, written)
        bodies = [io.open(p, encoding="utf-8").read() for p in written]
        self.assertTrue(any("FAIL" in b for b in bodies))
        self.assertTrue(any("WAIVED" in b for b in bodies))

    def test_a_pass_line_writes_no_package(self):
        text = "numbers   PASS     3 figures, each with its check run\n"
        self.assertEqual(decisions_mod.record_from_run(self.tmp, text, None), [])

    def test_lines_outside_the_grammar_are_counted_never_copied(self):
        parsed = decisions_mod.parse_verdict_lines("numbers FAIL x\nsecret: hunter2\n")
        self.assertEqual(parsed["unquotedLineCount"], 1)
        self.assertEqual(len(parsed["verdicts"]), 1)

    def test_the_cli_writes_a_package_and_says_so(self):
        result = _run([sys.executable, SBE, "gate", self.tmp], cwd=self.tmp)
        self.assertIn("decision package", result["stdout"] + result["stderr"])

    def test_no_decisions_suppresses_the_write_and_names_the_suppression(self):
        result = _run([sys.executable, SBE, "gate", "--no-decisions", self.tmp],
                      cwd=self.tmp)
        self.assertIn("no decision package was written", result["stdout"]
                      + result["stderr"])

    # The three fixtures below are not in the plan. They hold the promises Task 3
    # makes in prose and would otherwise be held by nobody: that an unmatched
    # line's TEXT never reaches the package, that a bookkeeping failure cannot
    # move a gate's exit code, and that the tee still streams.

    def test_the_text_of_an_unmatched_line_never_reaches_a_package(self):
        text = ("numbers   FAIL     an overstated total in report.md\n"
                "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMIcorrecthorse\n")
        written = decisions_mod.record_from_run(self.tmp, text, None)
        self.assertEqual(len(written), 1, written)
        body = io.open(written[0], encoding="utf-8").read()
        self.assertNotIn("wJalrXUtnFEMIcorrecthorse", body)
        self.assertIn("1 line(s)", body)

    def test_a_package_write_that_fails_leaves_the_gate_exit_code_alone(self):
        # A FILE where the decisions directory has to go, so every write under
        # it fails: exactly the bookkeeping failure that must never be allowed
        # to move a verdict. The gate itself FAILs here on an unparseable
        # manifest, so the exit code under test is a real 1 and not a 0 that
        # would have been 0 anyway.
        with io.open(os.path.join(self.tmp, ".sbe"), "w", encoding="utf-8") as fh:
            fh.write("not a directory\n")
        with io.open(os.path.join(self.tmp, "numbers-manifest.json"), "w",
                     encoding="utf-8") as fh:
            fh.write("{ not json\n")
        run = _run([sys.executable, SBE, "gate", "--strict", self.tmp], cwd=self.tmp)
        both = run["stdout"] + run["stderr"]
        self.assertEqual(run["code"], 1, both)
        self.assertIn("no decision package was written", both)
        self.assertIn("exit code is unchanged", both)

    def test_the_teeing_delegate_streams_and_keeps_a_copy(self):
        sys.path.insert(0, os.path.join(ROOT, "src"))
        from brothersbe import cli as cli_mod
        result = cli_mod.delegate_teed("sbe_gate.py", [self.tmp])
        self.assertIn("code", result)
        self.assertIn("lines", result)
        self.assertTrue(any("BROTHERSBE HARD GATES" in line for line in result["lines"]),
                        result["lines"][:5])


class TestOtherTriggers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sbe-other-trigger-")
        _git_repo(self.tmp)

    def test_a_forced_close_leaves_a_package_naming_who_why_and_the_violations(self):
        record = {"id": "T01", "agent": "writer-a", "role": "writer",
                  "forced": {"who": "a human", "why": "shipped under a deadline",
                             "verdict": "FAIL", "violations": ["src/other.py"],
                             "at": "2026-07-31T00:00:00Z"}}
        path = decisions_mod.record_forced_close(self.tmp, record)
        body = io.open(path, encoding="utf-8").read()
        for expected in ("a human", "shipped under a deadline", "src/other.py", "FAIL"):
            self.assertIn(expected, body)
        self.assertNotIn("PASS", body)

    def test_an_impact_run_with_nothing_decided_writes_nothing(self):
        quiet = {"verdict": "PASS", "disagreements": [], "proposedTier": "T1",
                 "humanTier": "T1", "headCommit": None}
        self.assertIsNone(decisions_mod.record_tier_decision(self.tmp, quiet, None))

    def test_a_review_required_impact_writes_a_package_naming_the_detector(self):
        raised = {"verdict": "REVIEW-REQUIRED", "proposedTier": "T3", "humanTier": "T1",
                  "headCommit": None,
                  "disagreements": [{"detector": "schema-migration", "file": "db/001.sql",
                                     "disposition": "missing"}]}
        path = decisions_mod.record_tier_decision(self.tmp, raised, None)
        body = io.open(path, encoding="utf-8").read()
        self.assertIn("schema-migration", body)
        self.assertIn("T1", body)
        self.assertIn("T3", body)

    # The fixtures below are not in the plan. They hold the sentences Task 4
    # makes in prose and would otherwise be held by nobody: that a forced close
    # cannot be recorded as a pass whatever the record claims, that a disposed
    # tier raise is WAIVED rather than the PASS the report printed, and that a
    # package write on either path cannot move an exit code.

    def test_a_forced_record_claiming_pass_is_recorded_no_data_and_the_claim_is_named(self):
        """`sbe task close --force` returns before the forced branch on PASS, so
        a record reaching here claiming PASS is a caller that did not run the
        postcondition. Copying that word into a FORCED package would print a
        clean verdict over a close nobody's diff cleared."""
        record = {"id": "T02", "agent": "writer-a", "role": "writer",
                  "forced": {"who": "a human", "why": "the deadline",
                             "verdict": "PASS", "violations": ["src/other.py"],
                             "at": "2026-07-31T00:00:00Z"}}
        path = decisions_mod.record_forced_close(self.tmp, record)
        body = io.open(path, encoding="utf-8").read()
        self.assertIn("- verdict recorded by the run: NO-DATA\n", body)
        self.assertIn("PASS", body, "the word the record claimed is named, never silently "
                                    "dropped")

    def test_a_close_record_with_no_forced_block_is_no_data_and_names_what_would_fill_it(self):
        record = {"id": "T03", "agent": "writer-a", "role": "writer"}
        path = decisions_mod.record_forced_close(self.tmp, record)
        body = io.open(path, encoding="utf-8").read()
        self.assertIn("- verdict recorded by the run: NO-DATA\n", body)
        self.assertIn("--force --who --why", body)
        self.assertNotIn("PASS", body)

    def test_a_disposed_raise_is_waived_never_the_pass_the_report_printed(self):
        """impact prints PASS once every disagreement carries a disposition. The
        decision this package records is that suppression, and a suppression is
        WAIVED. Recording the report's PASS here would be a package that reads
        clean over a control a human switched off."""
        disposed = {"verdict": "PASS", "proposedTier": "T3", "humanTier": "T1",
                    "headCommit": None,
                    "disagreements": [{"detector": "db-migration", "file": "db/001.sql",
                                       "disposition": "recorded"}]}
        path = decisions_mod.record_tier_decision(self.tmp, disposed, None)
        self.assertIsNotNone(path)
        body = io.open(path, encoding="utf-8").read()
        self.assertIn("- verdict recorded by the run: WAIVED\n", body)
        self.assertIn("db-migration", body)

    def test_a_tier_package_never_quotes_a_line_the_caller_did_not_compose(self):
        """The tier path is handed a REPORT, not a terminal capture. Everything
        it prints is composed from that report's own named fields, and the
        package says so, because a section headed "quoted" that carries
        something nobody quoted is the same defect as an uncounted line."""
        raised = {"verdict": "REVIEW-REQUIRED", "proposedTier": "T3", "humanTier": "T1",
                  "headCommit": None, "disagreements": [],
                  "chatter": "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMIcorrecthorse"}
        path = decisions_mod.record_tier_decision(self.tmp, raised, None)
        body = io.open(path, encoding="utf-8").read()
        self.assertNotIn("wJalrXUtnFEMIcorrecthorse", body)
        self.assertIn("composed from the impact report's own fields", body)

    def test_a_forced_close_through_the_cli_writes_a_package_and_keeps_its_exit_code(self):
        sha = subprocess.run(["git", "-C", self.tmp, "rev-parse", "HEAD"],
                             capture_output=True, text=True, check=True).stdout.strip()
        _run([sys.executable, SBE, "task", "open", "--id", "w1", "--agent", "a",
              "--role", "writer", "--base", sha, "--verify", "true",
              "--owns", "owned.txt", "--cwd", self.tmp], cwd=self.tmp)
        with io.open(os.path.join(self.tmp, "outside.txt"), "w", encoding="utf-8") as fh:
            fh.write("written outside the declaration\n")
        result = _run([sys.executable, SBE, "task", "close", "w1", "--force",
                       "--who", "the operator", "--why", "hotfix, out of band",
                       "--cwd", self.tmp], cwd=self.tmp)
        both = result["stdout"] + result["stderr"]
        self.assertEqual(result["code"], 0, both)
        self.assertIn("FORCED", both)
        self.assertIn("decision package written", both)
        written = [line.split("decision package written:")[1].strip()
                   for line in both.splitlines() if "decision package written:" in line]
        self.assertEqual(len(written), 1, both)
        body = io.open(written[0], encoding="utf-8").read()
        self.assertIn("the operator", body)
        self.assertIn("outside.txt", body)

    def test_a_package_write_that_fails_leaves_the_forced_close_exit_code_alone(self):
        # A FILE where the decisions directory has to go, so every write under
        # it fails. `.sbe` also holds the registry, so the close itself is run
        # first, in a repository whose `.sbe` is still a directory, and the file
        # is planted between the close and nothing else by pointing the writer
        # at a root whose `.sbe` cannot hold a directory.
        record = {"id": "T04", "agent": "a", "role": "writer",
                  "forced": {"who": "a human", "why": "the deadline", "verdict": "FAIL",
                             "violations": ["src/other.py"], "at": "2026-07-31T00:00:00Z"}}
        with io.open(os.path.join(self.tmp, ".sbe"), "w", encoding="utf-8") as fh:
            fh.write("not a directory\n")
        with self.assertRaises(decisions_mod.DecisionUnwritable):
            decisions_mod.record_forced_close(self.tmp, record)
        # And the CLI path swallows nothing while changing nothing: the close
        # exits on its own verdict and the failure is printed by name.
        from brothersbe import tasks as tasks_mod
        printed = []
        original = tasks_mod.sys.stdout.write
        try:
            tasks_mod.sys.stdout.write = lambda s: printed.append(s)
            tasks_mod._record_forced_close(self.tmp, record)
        finally:
            tasks_mod.sys.stdout.write = original
        joined = "".join(printed)
        self.assertIn("no decision package was written", joined)
        self.assertIn("DecisionUnwritable", joined)
        self.assertIn("exit code is unchanged", joined)

    def test_impact_in_json_mode_keeps_stdout_parseable(self):
        """`sbe impact --json` stdout is a document callers parse. A human
        sentence appended to it would break every one of them, so the package
        line goes to stderr there and to stdout otherwise."""
        with io.open(os.path.join(self.tmp, "00-intake.json"), "w", encoding="utf-8") as fh:
            json.dump({"answers": {"changes_contract": "n", "crosses_boundary": "n",
                                   "reversible_under_hour": "y", "touches_sensitive": "n",
                                   "consumers": "none"}}, fh)
        with io.open(os.path.join(self.tmp, "0002_add_partner_id.sql"), "w",
                     encoding="utf-8") as fh:
            fh.write("ALTER TABLE orders ADD COLUMN partner_id TEXT;\n")
        subprocess.run(["git", "-C", self.tmp, "add", "-A"], check=True)
        subprocess.run(["git", "-C", self.tmp, "commit", "-qm", "migration"], check=True)
        base = subprocess.run(["git", "-C", self.tmp, "rev-parse", "HEAD~1"],
                              capture_output=True, text=True, check=True).stdout.strip()
        result = _run([sys.executable, SBE, "impact", self.tmp, "--base", base,
                       "--intake", os.path.join(self.tmp, "00-intake.json"), "--json"],
                      cwd=self.tmp)
        data = json.loads(result["stdout"])
        self.assertEqual(data["verdict"], "REVIEW-REQUIRED", result["stdout"])
        self.assertIn("decision package written", result["stderr"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
