#!/usr/bin/env python3
"""The comparative benchmark harness, against the defects it exists to catch.

Run: python3 benchmarks/test_sbe_bench.py

WHAT THIS GUARDS. Three properties, each of which is the difference between a
benchmark and a press release, and each of which was calibrated by putting
the defect back and watching the assertion fail before it was restored.

  1. A planted defect that a run MISSES is counted as missed. The tempting
     defect is scoring only what a run reported, which makes every estate
     look perfect and makes "defects missed" a column of zeroes.
  2. A measure that cannot be computed reports NO-DATA, never zero. The
     tempting defect is `len(items or [])`, which turns an absent file into
     the claim that nothing happened.
  3. A report whose PROVENANCE column is empty REFUSES to render as a
     comparison, writing nothing. The tempting defect is rendering it with a
     warning, because a warning is one copy and paste away from being gone.

Plus the ground truth's own integrity, which is upstream of all three: every
declared defect must land at the file and line it declares, carrying the
source text it declares, the built tree must name no defect anywhere, and no
markdown an operator is handed may name a planted file-plus-line pair. That
last one is not decoration. Matching is by file and line window and never by
wording, so an example finding sitting on a planted location scores as FOUND
for whoever pastes it, which is how four of the nine defects were briefly
unmissable by anyone who read their own runbook.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)

import fixture_repo  # noqa: E402
import report  # noqa: E402
import score_run  # noqa: E402

DEFECTS_PATH = os.path.join(HERE, "defects.json")
SCENARIOS_PATH = os.path.join(HERE, "scenarios.json")
RESULTS_PATH = os.path.join(HERE, "RESULTS.md")


def read_json(path):
    with open(path, "r") as handle:
        return json.load(handle)


# The textual half of the operator-document leak guard, in one place.
#
# The first version of that guard read only ```json fences. That left the very
# defect it exists to stop reachable by deleting four characters: the same
# example finding pasted into an UNTAGGED ``` fence leaked exactly as hard,
# scored exactly the same FOUND, and the guard reported clean. So nothing
# below consults a fence, its tag, or whether there is a fence at all. Each
# form is matched against the WHOLE document, and each is a way a reader can
# carry a file-and-line pair out of a document and into a findings.json:
#
#   keyed   a record carrying a file key and a line key, in any fence, under
#           any tag, or inline in a sentence: {"file": "a/b.sql", "line": 9}
#   colon   the a/b.sql:9 form, which is how an editor and a compiler print it
#   prose   the path and the words "line 9" in one sentence, in either order
#
# The extraction is deliberately blind to the planted set: it pulls every
# file-and-line pair a document names and the caller intersects that with
# defects.json. A scan that went looking only for the nine planted paths would
# find nothing in a clean directory, and nothing is also what a scan that was
# never running would find.
_PATHISH = r"[A-Za-z0-9_.~<>+-]+(?:/[A-Za-z0-9_.~<>+-]+)+"
_LINE_KEY = r"[\"']?\blines?[\"']?\s*[:=]?\s*[\"']?(\d+)"
_FILE_KEY = r"[\"']?\bfiles?[\"']?\s*[:=]\s*[\"']?([^\"'\n,}\]]+?)[\"']?\s*(?=[,}\]\n])"

# (form name, pattern, which group holds the path, which group holds the line)
REFERENCE_FORMS = (
    ("keyed", re.compile(_FILE_KEY + r"[^{}]{0,200}?" + _LINE_KEY), 1, 2),
    ("keyed", re.compile(_LINE_KEY + r"[^{}]{0,200}?" + _FILE_KEY), 2, 1),
    ("colon", re.compile(r"(" + _PATHISH + r"):(\d+)(?![\d:])"), 1, 2),
    ("prose", re.compile(r"(" + _PATHISH + r")[^\n]{0,60}?" + _LINE_KEY), 1, 2),
    ("prose", re.compile(_LINE_KEY + r"[^\n]{0,60}?(" + _PATHISH + r")"), 2, 1),
)


def write_run(run_dir, files):
    """Writes a run directory. `files` maps filename to a JSON-able object;
    a filename mapped to None is deliberately NOT written, which is how the
    absent-evidence cases below are built."""
    os.makedirs(run_dir)
    for name, blob in files.items():
        if blob is None:
            continue
        with open(os.path.join(run_dir, name), "w") as handle:
            handle.write(json.dumps(blob))
    return run_dir


class TempTreeCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sbe-bench-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)


class GroundTruthIsReal(TempTreeCase):
    """Upstream of every other assertion here. If the manifest and the bytes
    disagree, every 'found' and every 'missed' below is measuring a line that
    is not where it says it is."""

    def setUp(self):
        super(GroundTruthIsReal, self).setUp()
        self.out = os.path.join(self.tmp, "fixture")
        written, problem = fixture_repo.build(self.out)
        self.assertEqual(problem, "", "the fixture would not build: %s" % problem)
        self.written = written
        self.defects = read_json(DEFECTS_PATH)["defects"]

    def test_declared_lines_hold_their_declared_anchor(self):
        for defect in self.defects:
            path = os.path.join(self.out, defect["file"].replace("/", os.sep))
            self.assertTrue(os.path.isfile(path),
                            "%s declares file %s, which the builder never wrote"
                            % (defect["id"], defect["file"]))
            with open(path, "r") as handle:
                lines = handle.read().split("\n")
            index = defect["line"] - 1
            self.assertTrue(0 <= index < len(lines),
                            "%s declares line %d of %s, which holds only %d line(s)"
                            % (defect["id"], defect["line"], defect["file"], len(lines)))
            self.assertEqual(
                lines[index].strip(), defect["anchor"].strip(),
                "%s declares line %d of %s as %r; the built tree holds %r there. The ground "
                "truth and the bytes have drifted, so every found and missed count scored "
                "against this defect is measuring the wrong line"
                % (defect["id"], defect["line"], defect["file"], defect["anchor"],
                   lines[index].strip()))

    def test_the_built_tree_names_no_defect_anywhere(self):
        """An estate that can grep for the answer is not being measured."""
        for rel in self.written:
            path = os.path.join(self.out, rel.replace("/", os.sep))
            with open(path, "r") as handle:
                body = handle.read()
            for marker in fixture_repo.FORBIDDEN_MARKERS:
                self.assertNotIn(marker, body,
                                 "%s in the built fixture carries the marker %r, which hands "
                                 "any estate the answer for free" % (rel, marker))
            for defect in self.defects:
                self.assertNotIn(defect["id"] + " ", body,
                                 "%s names defect id %s" % (rel, defect["id"]))

    def test_every_scenario_owns_declared_defects_and_no_defect_is_orphaned(self):
        scenarios = read_json(SCENARIOS_PATH)["scenarios"]
        declared = set(d["id"] for d in self.defects)
        owned = set()
        for scenario in scenarios:
            ids = scenario.get("defect_ids") or []
            self.assertTrue(ids, "scenario %s owns no defect, so a run of it can never miss "
                                 "anything" % scenario["id"])
            for defect_id in ids:
                self.assertIn(defect_id, declared,
                              "scenario %s claims defect %s, which defects.json does not "
                              "declare" % (scenario["id"], defect_id))
                owned.add(defect_id)
        self.assertEqual(sorted(declared - owned), [],
                         "defect(s) %s are planted and belong to no scenario, so no run can "
                         "ever be scored against them" % sorted(declared - owned))

    def test_the_builder_refuses_a_non_empty_directory_and_this_checkout(self):
        busy = os.path.join(self.tmp, "busy")
        os.makedirs(busy)
        with open(os.path.join(busy, "someones-work.txt"), "w") as handle:
            handle.write("real work\n")
        _written, problem = fixture_repo.build(busy)
        self.assertIn("not empty", problem, problem)
        _written, problem = fixture_repo.build(os.path.join(ROOT, "benchmarks", "would-be-here"))
        self.assertIn("never built into this repository", problem, problem)


class AMissedDefectIsCountedAsMissed(TempTreeCase):
    """Property 1. S1 plants two defects; a run that names one of them has
    missed the other, and the harness has to say so by id."""

    def setUp(self):
        super(AMissedDefectIsCountedAsMissed, self).setUp()
        self.defects, self.scenarios, problem = score_run.load_ground_truth()
        self.assertEqual(problem, "", problem)

    def score(self, files):
        run_dir = write_run(os.path.join(self.tmp, "run"), files)
        record, problem = score_run.score(run_dir, self.defects, self.scenarios)
        self.assertEqual(problem, "", problem)
        return record

    def test_naming_one_of_two_counts_the_other_as_missed(self):
        record = self.score({
            "run.json": {"run_id": "r1", "scenario": "S1-migration",
                         "estate": "brothersbe", "provenance": "A Named Operator"},
            "findings.json": {"findings": [
                {"file": "db/migrations/0002_split_customer_name.up.sql", "line": 9,
                 "note": "drops the column with no backfill"}]},
        })
        self.assertEqual(record["measures"]["defects_found"]["value"], 1,
                         record["measures"]["defects_found"])
        self.assertEqual(record["measures"]["defects_missed"]["value"], 1,
                         record["measures"]["defects_missed"])
        self.assertEqual(record["detail"]["defects"]["missed_ids"], ["D2"],
                         "the missed defect has to be named by id, or a reader cannot tell "
                         "WHICH one went unfound: %r" % record["detail"]["defects"])

    def test_an_empty_findings_list_misses_everything_planted(self):
        """An empty list is DATA: the run reported nothing, so both planted
        defects are missed. This is the case that only exists because the
        defects were planted in advance."""
        record = self.score({
            "run.json": {"run_id": "r2", "scenario": "S1-migration",
                         "estate": "vanilla-claude-code", "provenance": "A Named Operator"},
            "findings.json": {"findings": []},
        })
        self.assertEqual(record["measures"]["defects_found"]["value"], 0)
        self.assertEqual(record["measures"]["defects_missed"]["value"], 2,
                         record["measures"]["defects_missed"])
        self.assertEqual(record["detail"]["defects"]["missed_ids"], ["D1", "D2"])

    def test_a_finding_at_the_wrong_line_does_not_count_as_found(self):
        record = self.score({
            "run.json": {"run_id": "r3", "scenario": "S1-migration",
                         "estate": "feature-dev", "provenance": "A Named Operator"},
            "findings.json": {"findings": [
                {"file": "db/migrations/0002_split_customer_name.up.sql", "line": 2}]},
        })
        self.assertEqual(record["measures"]["defects_found"]["value"], 0,
                         "line 2 is seven lines from the declared line 9, well outside the "
                         "declared window of 2, and must not be credited")
        self.assertEqual(record["measures"]["defects_missed"]["value"], 2)

    def test_a_finding_naming_no_line_is_unmatched_rather_than_credited(self):
        record = self.score({
            "run.json": {"run_id": "r4", "scenario": "S1-migration",
                         "estate": "superpowers", "provenance": "A Named Operator"},
            "findings.json": {"findings": [
                {"file": "db/migrations/0002_split_customer_name.up.sql",
                 "note": "something about this migration feels wrong"}]},
        })
        self.assertEqual(record["measures"]["defects_found"]["value"], 0)
        self.assertEqual(len(record["detail"]["defects"]["unmatched_findings"]), 1)
        self.assertIn("no whole-number line",
                      record["detail"]["defects"]["unmatched_findings"][0]["why"])

    def test_a_finding_in_another_scenarios_file_is_not_credited_here(self):
        record = self.score({
            "run.json": {"run_id": "r5", "scenario": "S1-migration",
                         "estate": "brothersbe", "provenance": "A Named Operator"},
            "findings.json": {"findings": [
                {"file": "ops/alerts.yaml", "line": 12}]},
        })
        self.assertEqual(record["measures"]["defects_found"]["value"], 0,
                         "D9 lives at ops/alerts.yaml:12 but belongs to S4; crediting it in "
                         "an S1 run would let one lucky sweep score every scenario")
        self.assertEqual(record["measures"]["defects_missed"]["value"], 2)


class AnUncomputableMeasureReportsNoData(TempTreeCase):
    """Property 2. Every measure, one at a time, with its evidence removed."""

    def setUp(self):
        super(AnUncomputableMeasureReportsNoData, self).setUp()
        self.defects, self.scenarios, problem = score_run.load_ground_truth()
        self.assertEqual(problem, "", problem)

    def score(self, files, name="run"):
        run_dir = write_run(os.path.join(self.tmp, name), files)
        record, problem = score_run.score(run_dir, self.defects, self.scenarios)
        self.assertEqual(problem, "", problem)
        return record

    def assert_no_data(self, record, measure_id):
        entry = record["measures"][measure_id]
        self.assertEqual(entry["verdict"], score_run.NO_DATA,
                         "%s read %r with value %r; an absence must never be reported as a "
                         "computed measure" % (measure_id, entry["verdict"], entry["value"]))
        self.assertIsNone(entry["value"],
                          "%s reported NO-DATA and still carried the value %r. A renderer "
                          "doing `value or 0` would print that absence as a zero"
                          % (measure_id, entry["value"]))
        self.assertTrue(entry["reason"].strip(),
                        "%s reported NO-DATA with no reason, which tells a reader nothing "
                        "about what to go and capture" % measure_id)

    def test_a_run_with_nothing_but_run_json_reads_no_data_everywhere(self):
        record = self.score({"run.json": {"run_id": "bare", "scenario": "S1-migration",
                                          "estate": "brothersbe",
                                          "provenance": "A Named Operator"}})
        for measure_id in score_run.MEASURE_IDS:
            self.assert_no_data(record, measure_id)

    def test_missing_tokens_is_no_data_not_zero(self):
        record = self.score({"run.json": {"run_id": "t", "scenario": "S1-migration",
                                          "estate": "brothersbe", "provenance": "Named"},
                             "tokens.json": None})
        self.assert_no_data(record, "tokens_total")

    def test_half_a_token_total_is_no_data_not_the_half_that_exists(self):
        record = self.score({"run.json": {"run_id": "t2", "scenario": "S1-migration",
                                          "estate": "brothersbe", "provenance": "Named"},
                             "tokens.json": {"input": 1000}})
        self.assert_no_data(record, "tokens_total")
        self.assertIn("half", record["measures"]["tokens_total"]["reason"])

    def test_an_unjudged_block_makes_false_blocks_no_data(self):
        record = self.score({"run.json": {"run_id": "b", "scenario": "S1-migration",
                                          "estate": "brothersbe", "provenance": "Named"},
                             "blocks.json": {"blocks": [
                                 {"what": "refused the migration", "justified": False},
                                 {"what": "refused the merge"}]}})
        self.assert_no_data(record, "false_blocks")

    def test_judged_blocks_do_compute(self):
        """The other direction, so the NO-DATA above is a real distinction and
        not a measure that never computes at all."""
        record = self.score({"run.json": {"run_id": "b2", "scenario": "S1-migration",
                                          "estate": "brothersbe", "provenance": "Named"},
                             "blocks.json": {"blocks": [
                                 {"what": "a", "justified": False, "judged_by": "Named"},
                                 {"what": "b", "justified": True, "judged_by": "Named"}]}})
        self.assertEqual(record["measures"]["false_blocks"]["verdict"], score_run.VALUE)
        self.assertEqual(record["measures"]["false_blocks"]["value"], 1)

    def test_a_backwards_clock_is_no_data_not_a_negative_duration(self):
        record = self.score({"run.json": {"run_id": "c", "scenario": "S1-migration",
                                          "estate": "brothersbe", "provenance": "Named"},
                             "timing.json": {"started_at": "2026-08-07T10:00:00+09:00",
                                             "ended_at": "2026-08-07T09:00:00+09:00"}})
        self.assert_no_data(record, "wall_clock_seconds")

    def test_an_unparseable_artifact_is_no_data_carrying_the_reason(self):
        run_dir = write_run(os.path.join(self.tmp, "broken"),
                            {"run.json": {"run_id": "x", "scenario": "S1-migration",
                                          "estate": "brothersbe", "provenance": "Named"}})
        with open(os.path.join(run_dir, "corrections.json"), "w") as handle:
            handle.write("this is not json")
        record, problem = score_run.score(run_dir, self.defects, self.scenarios)
        self.assertEqual(problem, "", problem)
        self.assert_no_data(record, "corrections")
        self.assertIn("did not parse", record["measures"]["corrections"]["reason"])

    def test_an_undeclared_scenario_makes_both_defect_measures_no_data(self):
        record = self.score({"run.json": {"run_id": "s", "scenario": "S9-invented",
                                          "estate": "brothersbe", "provenance": "Named"},
                             "findings.json": {"findings": []}})
        self.assert_no_data(record, "defects_found")
        self.assert_no_data(record, "defects_missed")

    def test_no_data_does_not_block(self):
        """The house law, exercised on the real CLI: a run whose measures are
        almost all absent still SCORES, exit 0. NO-DATA is never a block."""
        run_dir = write_run(os.path.join(self.tmp, "cli"),
                            {"run.json": {"run_id": "cli", "scenario": "S1-migration",
                                          "estate": "brothersbe", "provenance": "Named"}})
        out = subprocess.run([sys.executable, os.path.join(HERE, "score_run.py"),
                              "--run", run_dir], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0,
                         "score_run exited %d over a run whose measures are absent; NO-DATA "
                         "is never a block. stderr: %s" % (out.returncode, out.stderr))
        self.assertIn("NO-DATA", out.stderr)


class AnEmptyProvenanceRefusesToRender(TempTreeCase):
    """Property 3. The column that makes the four-column table quotable is the
    column that makes it refusable."""

    def scored(self, scenario, estate, provenance):
        return {"schema": "sbe-bench-scored/1", "run_id": "%s-%s" % (scenario, estate),
                "scenario": scenario, "estate": estate, "provenance": provenance,
                "measures": dict((m, {"verdict": "VALUE", "value": 1, "reason": "x"})
                                 for m in score_run.MEASURE_IDS)}

    def full_grid(self, provenance_for=None):
        scenarios, estates, _measures, problem = report.load_plan()
        self.assertEqual(problem, "", problem)
        records = []
        for scenario in scenarios:
            for estate in estates:
                who = "A Named Operator"
                if provenance_for is not None:
                    who = provenance_for(scenario["id"], estate["id"])
                records.append(self.scored(scenario["id"], estate["id"], who))
        return records

    def test_one_empty_provenance_cell_refuses_the_whole_comparison(self):
        def who(scenario, estate):
            if (scenario, estate) == ("S3-data-pipeline", "superpowers"):
                return ""
            return "A Named Operator"
        text, refusal = report.render(self.full_grid(who), mode="comparison")
        self.assertEqual(text, "",
                         "the renderer produced a comparison AND a refusal; a partly rendered "
                         "table is one copy and paste away from being published")
        self.assertIn("REFUSED", refusal)
        self.assertIn("S3-data-pipeline / superpowers", refusal,
                      "the refusal has to name the row, or nobody can fix it: %r" % refusal)

    def test_whitespace_is_not_a_person(self):
        def who(scenario, estate):
            return "   " if estate == "feature-dev" else "A Named Operator"
        text, refusal = report.render(self.full_grid(who), mode="comparison")
        self.assertEqual(text, "")
        self.assertIn("names nobody", refusal)

    def test_an_unrun_row_also_refuses_the_comparison(self):
        text, refusal = report.render([], mode="comparison")
        self.assertEqual(text, "")
        self.assertIn("UNRUN", refusal)

    def test_a_fully_attributed_grid_does_render(self):
        """The other direction. Without this, the refusal above could be a
        renderer that never renders anything."""
        text, refusal = report.render(self.full_grid(), mode="comparison")
        self.assertEqual(refusal, "", refusal)
        self.assertIn("STATUS: COMPLETE", text)
        self.assertIn("PROVENANCE", text)

    def test_status_mode_renders_the_unrun_grid_and_says_unrun(self):
        text, refusal = report.render([], mode="status")
        self.assertEqual(refusal, "", refusal)
        self.assertIn("STATUS: UNRUN", text)
        self.assertIn("This evaluation is UNRUN", text)
        self.assertNotIn("STATUS: PENDING", text.upper(),
                         "the unrun state must be stated as UNRUN; pending is a promise and "
                         "unrun is a fact")

    def test_the_cli_refuses_a_comparison_and_writes_nothing(self):
        out_path = os.path.join(self.tmp, "should-not-exist.md")
        out = subprocess.run([sys.executable, os.path.join(HERE, "report.py"),
                              "--scored", os.path.join(HERE, "runs"),
                              "--mode", "comparison", "--out", out_path],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 2, out.stdout + out.stderr)
        self.assertFalse(os.path.lexists(out_path),
                         "the CLI refused and still wrote %s" % out_path)
        self.assertIn("REFUSED", out.stderr)


class ARunOutsideTheGridIsNamedNotDropped(unittest.TestCase):
    """A scored record whose scenario or estate id the plan does not declare.

    Found by rendering a real scored run with one character changed in its
    estate id: the row it belonged to went back to UNRUN, the record appeared
    nowhere, and the header read STATUS: UNRUN over a directory holding a run
    a named person had done. `collect` already refuses to lose a record it
    could not parse; this is the same loss one layer down.
    """

    def scored(self, scenario, estate):
        return {"schema": "sbe-bench-scored/1", "run_id": "%s-%s-20260807" % (scenario, estate),
                "scenario": scenario, "estate": estate, "provenance": "A Named Operator",
                "measures": dict((m, {"verdict": "VALUE", "value": 1, "reason": "x"})
                                 for m in score_run.MEASURE_IDS)}

    def test_a_misspelled_estate_is_named_in_the_status_report(self):
        text, refusal = report.render([self.scored("S1-migration", "brother-sbe")],
                                      mode="status")
        self.assertEqual(refusal, "", refusal)
        self.assertIn("sit outside the grid", text,
                      "the record placed in no row is not named anywhere in the report, so "
                      "a real run vanished and the report said nothing")
        self.assertIn("S1-migration-brother-sbe-20260807", text,
                      "the orphan section has to name the run, or nobody can fix it")
        self.assertIn("'brother-sbe' is not declared", text)

    def test_a_record_outside_the_grid_refuses_a_comparison(self):
        records = []
        scenarios, estates, _m, problem = report.load_plan()
        self.assertEqual(problem, "", problem)
        for scenario in scenarios:
            for estate in estates:
                records.append(self.scored(scenario["id"], estate["id"]))
        records.append(self.scored("S1-migration", "brother-sbe"))
        text, refusal = report.render(records, mode="comparison")
        self.assertEqual(text, "",
                         "a comparison rendered over a set that silently lost a run is a "
                         "comparison of something else")
        self.assertIn("REFUSED", refusal)
        self.assertIn("brother-sbe", refusal)

    def test_a_grid_with_no_orphan_still_renders(self):
        """The other direction, so the refusal above is a distinction rather
        than a renderer that stopped rendering."""
        scenarios, estates, _m, problem = report.load_plan()
        self.assertEqual(problem, "", problem)
        records = [self.scored(s["id"], e["id"]) for s in scenarios for e in estates]
        text, refusal = report.render(records, mode="comparison")
        self.assertEqual(refusal, "", refusal)
        self.assertNotIn("sit outside the grid", text)


class TheShippedReportIsHonest(unittest.TestCase):
    """What a release document is allowed to quote today."""

    def setUp(self):
        self.assertTrue(os.path.isfile(RESULTS_PATH), "%s does not exist" % RESULTS_PATH)
        with open(RESULTS_PATH, "r") as handle:
            self.text = handle.read()

    def test_it_says_the_evaluation_is_unrun(self):
        self.assertIn("STATUS: UNRUN", self.text)
        self.assertIn("This evaluation is UNRUN", self.text)

    def data_rows(self):
        """Table rows whose first cell is a DECLARED scenario id.

        The first version of this matched `line.startswith("| S")`, which also
        matched the header row starting `| Scenario |`: the count came out one
        too high and the first cell compared was the column label, not a
        measure. A grid's header is not one of its rows.
        """
        ids = set(s["id"] for s in read_json(SCENARIOS_PATH)["scenarios"])
        rows = []
        for line in self.text.split("\n"):
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells and cells[0] in ids:
                rows.append((line, cells))
        return rows

    def test_every_measure_cell_reads_no_data(self):
        rows = self.data_rows()
        self.assertTrue(rows, "the shipped report has no scenario rows at all")
        for row, cells in rows:
            for cell in cells[2:-1]:
                self.assertEqual(cell, report.NO_DATA,
                                 "the shipped report carries the measure %r in row %r; it "
                                 "ships with every measure NO-DATA until a real run fills it"
                                 % (cell, row))
            self.assertEqual(cells[-1], report.UNRUN,
                             "the shipped report carries the provenance %r in row %r"
                             % (cells[-1], row))

    def test_it_carries_one_row_per_scenario_estate_pair(self):
        scenarios, estates, _m, problem = report.load_plan()
        self.assertEqual(problem, "", problem)
        rows = self.data_rows()
        self.assertEqual(len(rows), len(scenarios) * len(estates),
                         "the shipped report shows %d row(s) for a %d by %d grid"
                         % (len(rows), len(scenarios), len(estates)))

    def test_the_shipped_report_is_what_the_renderer_produces_now(self):
        """Stops the report from being hand-edited into something the code
        would never emit."""
        text, refusal = report.render([], mode="status")
        self.assertEqual(refusal, "", refusal)
        self.assertEqual(text, self.text,
                         "benchmarks/RESULTS.md differs from what report.py renders from an "
                         "empty runs directory; regenerate it rather than editing it")


class TheRunbooksMatchTheDefinitions(unittest.TestCase):
    """An operator runs the markdown. The scorer reads the JSON. A prompt that
    drifts between them makes four columns that were never comparable."""

    def setUp(self):
        self.scenarios = read_json(SCENARIOS_PATH)["scenarios"]

    def test_every_scenario_has_a_runbook_that_exists(self):
        for scenario in self.scenarios:
            path = os.path.join(HERE, scenario["runbook"].replace("/", os.sep))
            self.assertTrue(os.path.isfile(path),
                            "scenario %s names runbook %s, which does not exist"
                            % (scenario["id"], scenario["runbook"]))

    def test_the_pasted_prompt_is_the_declared_prompt(self):
        for scenario in self.scenarios:
            path = os.path.join(HERE, scenario["runbook"].replace("/", os.sep))
            with open(path, "r") as handle:
                body = handle.read()
            self.assertIn("```text\n", body,
                          "%s has no ```text block, so there is no prompt an operator can "
                          "paste verbatim" % scenario["runbook"])
            block = body.split("```text\n", 1)[1].split("```", 1)[0].strip()
            self.assertEqual(block, scenario["task_prompt"].strip(),
                             "the prompt in %s has drifted from scenarios.json; the four "
                             "estates would be answering different questions"
                             % scenario["runbook"])

    def test_every_runbook_warns_the_operator_off_the_ground_truth(self):
        for scenario in self.scenarios:
            path = os.path.join(HERE, scenario["runbook"].replace("/", os.sep))
            with open(path, "r") as handle:
                body = handle.read()
            self.assertIn("Do not read that file before the run", body,
                          "%s does not warn the operator off the ground truth"
                          % scenario["runbook"])

    def planted_locations(self):
        """Every (path, line) an operator document may not name, keyed to the
        defect ids sitting there.

        Expanded over each defect's declared WINDOW, not just its declared
        line, because score_run.match_findings credits anything inside the
        window. A guard that checked only the exact line would pass over an
        example one line off that still scores as FOUND.
        """
        pairs = {}
        for defect in read_json(DEFECTS_PATH)["defects"]:
            path = score_run.normalise_path(defect["file"])
            window = defect.get("line_window")
            if isinstance(window, bool) or not isinstance(window, int) or window < 0:
                window = 0
            for line in range(defect["line"] - window, defect["line"] + window + 1):
                if line >= 0:
                    pairs.setdefault((path, line), []).append(defect["id"])
        return pairs

    def operator_documents(self):
        """Every markdown file under benchmarks/, with its text.

        That is the set an operator is handed or sent to: the four runbooks,
        the two READMEs the runbooks point at for artifact shapes, and the
        rendered report. defects.json is deliberately NOT in the set, because
        it IS the answers and the runbooks tell the operator to read it only
        afterwards; neither are the .py sources, whose fixtures have to name
        real planted locations in order to test the matcher at all.
        """
        docs = []
        for dirpath, dirnames, filenames in os.walk(HERE):
            dirnames[:] = [d for d in dirnames
                           if not d.startswith(".") and d != "__pycache__"]
            for name in sorted(filenames):
                if not name.endswith(".md"):
                    continue
                path = os.path.join(dirpath, name)
                rel = os.path.relpath(path, HERE).replace(os.sep, "/")
                try:
                    with open(path, "r", encoding="utf-8") as handle:
                        docs.append((rel, handle.read()))
                except OSError as exc:
                    self.fail("%s could not be read (%s), so it went unscanned and this "
                              "guard would have reported clean over a document nobody "
                              "opened" % (rel, type(exc).__name__))
        return docs

    def json_examples(self, rel, body):
        """Every ```json fence in a document, parsed.

        A fence that will not parse FAILS here rather than being skipped: the
        operator is told to copy these blocks, so an unparseable one is a
        defect of its own, and a silent skip would let a leak hide inside
        broken JSON.
        """
        blocks = []
        for index, part in enumerate(body.split("```json\n")[1:]):
            raw = part.split("```", 1)[0]
            try:
                blocks.append(json.loads(raw))
            except ValueError as exc:
                self.fail("json example %d in %s does not parse (%s); an operator is told "
                          "to copy it verbatim" % (index + 1, rel, exc))
        return blocks

    def named_locations(self, body):
        """Every (normalised path, line, form) the WHOLE document names.

        No fence is consulted, because the fence tag is not what makes a pair
        copyable. A ```json fence, an untagged ``` fence and a bare sentence
        all hand a reader the same file and the same line, and score_run
        credits all three identically. See REFERENCE_FORMS above for the forms
        and for why this one is blind to the planted set.
        """
        found = []
        for form, pattern, path_group, line_group in REFERENCE_FORMS:
            for match in pattern.finditer(body):
                path = score_run.normalise_path(match.group(path_group))
                if path:
                    found.append((path, int(match.group(line_group)), form))
        return found

    def file_line_pairs(self, blob):
        """Every (normalised path, line) an example carries, at any depth."""
        found = []
        if isinstance(blob, dict):
            path, line = blob.get("file"), blob.get("line")
            if (isinstance(path, str) and isinstance(line, int)
                    and not isinstance(line, bool)):
                found.append((score_run.normalise_path(path), line))
            for value in blob.values():
                found.extend(self.file_line_pairs(value))
        elif isinstance(blob, list):
            for value in blob:
                found.extend(self.file_line_pairs(value))
        return found

    def test_no_operator_document_names_a_planted_location(self):
        """The measure this whole harness exists for, guarded at its one soft
        spot.

        score_run matches on file plus line window and never reads wording, so
        any example finding an operator can paste that happens to sit on a
        planted location scores as FOUND for every estate. Four of the nine
        defects were unmissable that way (the runbooks' own findings.json
        examples), and two more sat in benchmarks/runs/README.md, which the
        runbooks send the operator to.

        This parses the planted set out of defects.json, never hardcoding a
        location, and asserts that no markdown here names any of those
        file-plus-line pairs ANYWHERE in the document: in a ```json fence, in
        an untagged fence, under any other tag, or in plain prose. The scan
        deliberately does not look at fences, because the first version of it
        did: it read ```json blocks only, so the leak it exists to stop came
        back by dropping the word json off the fence and the guard still
        reported clean.
        """
        planted = self.planted_locations()
        self.assertTrue(planted,
                        "defects.json yielded no planted location, so this guard examined "
                        "nothing; that is NO-DATA, not a clean scan")
        docs = self.operator_documents()
        self.assertTrue(docs,
                        "no markdown was found under benchmarks/, so this guard scanned no "
                        "document at all; that is NO-DATA, not a clean scan")
        scanned = set(rel for rel, _body in docs)
        for scenario in self.scenarios:
            self.assertIn(scenario["runbook"], scanned,
                          "runbook %s was not among the %d document(s) scanned, so this "
                          "guard reported on a set that excludes the file it exists for"
                          % (scenario["runbook"], len(docs)))
        self.assertIn("runs/README.md", scanned,
                      "runs/README.md was not scanned, and it is the file every runbook "
                      "sends the operator to for artifact shapes")
        offenders, parsed_pairs, named_pairs = [], 0, 0
        for rel, body in docs:
            for blob in self.json_examples(rel, body):
                pairs = self.file_line_pairs(blob)
                parsed_pairs += len(pairs)
                for pair in pairs:
                    if pair in planted:
                        offenders.append(
                            "%s carries the example finding %s:%d, which is planted defect "
                            "%s; an operator pasting it scores that defect FOUND for every "
                            "estate" % (rel, pair[0], pair[1], ", ".join(planted[pair])))
            for path, line, form in self.named_locations(body):
                named_pairs += 1
                if (path, line) in planted:
                    offenders.append(
                        "%s names %s:%d in a %s reference, which is planted defect %s; "
                        "matching is by file and line window and never by wording, so "
                        "whoever copies it scores that defect FOUND for every estate"
                        % (rel, path, line, form, ", ".join(planted[(path, line)])))
        self.assertTrue(parsed_pairs,
                        "not one file-and-line pair was found in any json example across %d "
                        "document(s), so the half of this guard that parses the examples "
                        "compared nothing; that is NO-DATA, not a clean scan" % len(docs))
        self.assertTrue(named_pairs,
                        "the whole-document scan matched no file-and-line reference of any "
                        "form across %d document(s), so the half of this guard that does "
                        "not depend on a fence tag compared nothing; that is NO-DATA, not "
                        "a clean scan" % len(docs))
        deduped = sorted(set(offenders))
        self.assertEqual(deduped, [], "; ".join(deduped))

    def test_the_estates_named_are_the_four_the_founder_named(self):
        estates = [e["id"] for e in read_json(SCENARIOS_PATH)["estates"]]
        self.assertEqual(sorted(estates),
                         sorted(["vanilla-claude-code", "feature-dev", "superpowers",
                                 "brothersbe"]),
                         "the estate list has drifted from the four being compared: %r"
                         % estates)


class NoDashesAnywhere(unittest.TestCase):
    """House law, checked on this directory's own bytes rather than trusted.

    The two characters are built from their codepoints rather than typed. The
    first version typed them as literals and this file then failed its own
    check, which is the same self-match tools/sbe_score.py's lint solves by
    skipping itself; a skip would have left this file unchecked, so the
    characters are constructed instead and every file here is really scanned.
    """
    DASHES = (chr(0x2014), chr(0x2013))

    def test_no_em_or_en_dash_in_any_file_here(self):
        offenders = []
        for dirpath, dirnames, filenames in os.walk(HERE):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")
                           and d != "__pycache__"]
            for name in sorted(filenames):
                if name.endswith(".pyc"):
                    continue
                path = os.path.join(dirpath, name)
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as handle:
                        body = handle.read()
                except OSError as exc:
                    offenders.append("%s could not be read (%s)"
                                     % (os.path.relpath(path, HERE), type(exc).__name__))
                    continue
                for dash in self.DASHES:
                    if dash in body:
                        offenders.append("%s carries %r"
                                         % (os.path.relpath(path, HERE), dash))
        self.assertEqual(offenders, [], "; ".join(offenders))


if __name__ == "__main__":
    unittest.main(verbosity=2)
