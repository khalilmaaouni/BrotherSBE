#!/usr/bin/env python3
"""LP-0201: fixtures for `brothersbe.contracts`, the versioned JSON contract
registry for the task registry, `sbe status --json`, `sbe status --team
--json`, the work brief and the handover record. Run:
python3 tools/test_sbe_contracts.py

One fixture per surface validates REAL output, captured live through the
real engine over the golden scenario `tools/fixtures/golden-scenario/
build_scenario.py` builds (never a hand-typed dict standing in for what a
command would print): a real `git init`, the golden scenario's own dossier
and plan, then `sbe work start`/`sbe evidence run`/`sbe work finish` for T01,
`sbe work brief` for T02 (still unclaimed), `sbe status`, `sbe status
--team` and `sbe handover prepare`, the same driving discipline `tools/
test_sbe_golden_scenario.py`'s own `GoldenScenarioFixture` already holds to,
mirrored here rather than reinvented.

Every refusal fixture (`TestRefusals` below) starts from one of those SAME
real captures, `copy.deepcopy`'d so the original is never mutated, then
changes exactly one thing (an unknown `schemaVersion`, a field popped out,
an extra field added) and asserts the validator moves the way that one
change should move it. Calibration for each: the original, un-mutated copy
is re-validated as `PASS` right after the mutated copy is checked, in the
same test, which is how this suite proves the failure a mutated copy earns
comes from the mutation and not from a validator that always says `FAIL`
(and, since every mutation lives on an in-memory `copy.deepcopy`, no file
this repository tracks is ever touched, so there is nothing on disk for a
`git diff` to catch: the calibration is the re-validated original passing
inside the same test).
"""
import copy
import inspect
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
SBE = os.path.join(ROOT, "bin", "sbe")
FIXTURE_DIR = os.path.join(HERE, "fixtures", "golden-scenario")
if FIXTURE_DIR not in sys.path:
    sys.path.insert(0, FIXTURE_DIR)
import build_scenario as bs  # noqa: E402  (path setup has to come first)

sys.path.insert(0, os.path.join(ROOT, "src"))
try:
    from brothersbe import contracts as mod  # noqa: E402
finally:
    sys.path.pop(0)

OUTGOING = "alice@example.com"
RECEIVER = "bob@example.com"


# ---------------------------------------------------------------------------
# Shared fixture: one golden scenario repository, driven far enough to hand
# back one real captured document per surface. Mirrors `tools/
# test_sbe_golden_scenario.py`'s own `GoldenScenarioFixture` (the process
# helpers, the registry reader) rather than reinventing either.
# ---------------------------------------------------------------------------

class ContractsFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sbe-contracts-")
        self.repo = os.path.join(self.tmp, "repo")
        self.worktree_dir = os.path.join(self.tmp, "worktrees")
        os.makedirs(self.worktree_dir)
        built = bs.build(self.repo, SBE)
        self.assertEqual(built["validate_code"], 0,
                         "fixture setup wrote a plan `sbe plan` itself refuses; this is a "
                         "fixture bug, not an LP-0201 finding: %s" % built["validate_text"])
        self.base = built["base"]
        self.dossier = built["dossier"]
        self.plan_path = built["plan_path"]
        self.change_id = built["change_id"]

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # -- process helpers. Three values, not two: see `build_scenario.
    # run_sbe`'s own docstring for why every runner helper in this project
    # returns three values rather than a (verdict, evidence)-shaped pair.

    def sbe(self, *argv):
        return bs.run_sbe(SBE, list(argv), cwd=self.repo)

    def work(self, *argv):
        return self.sbe("work", *argv, "--cwd", self.repo)

    def worktree_path_for(self, task_id):
        return os.path.join(self.worktree_dir,
                            "%s-sbe-%s" % (os.path.basename(self.repo), task_id))

    def start_task(self, task_id, agent):
        code, text, _err = self.work("start", task_id, "--plan", self.plan_path,
                                     "--worktree-dir", self.worktree_dir, "--agent", agent)
        self.assertEqual(code, 0, "sbe work start %s failed: %s" % (task_id, text))
        return self.worktree_path_for(task_id)

    def run_evidence(self, task_id, argv, covers=None, out_name=None, kind="gate"):
        worktree = self.worktree_path_for(task_id)
        receipt = os.path.join(self.repo, ".sbe", "evidence",
                               out_name or ("%s-receipt.json" % task_id))
        extra = []
        for c in (covers or []):
            extra += ["--covers", c]
        code, text, _err = self.sbe("evidence", "run", "--out", receipt, "--kind", kind,
                                    *(extra + ["--cwd", worktree, "--"] + list(argv)))
        self.assertEqual(code, 0, "sbe evidence run for %s failed: %s" % (task_id, text))
        return receipt

    def finish_task(self, task_id):
        return self.work("finish", task_id)

    def registry(self):
        with io.open(os.path.join(self.repo, ".sbe", "tasks.json"), encoding="utf-8") as fh:
            return json.load(fh)


# ---------------------------------------------------------------------------
# One real, live capture per surface, driven through the real engine, each
# validated PASS. This IS the "one fixture per surface validating REAL
# output" the done-check names.
# ---------------------------------------------------------------------------

class TestRealFixturesValidate(ContractsFixture):
    def setUp(self):
        ContractsFixture.setUp(self)

        # T01: start, do the work, evidence it, finish clean. A populated,
        # closed task record is a far more real task registry fixture than
        # the empty one `build()` alone would leave behind.
        wt01 = self.start_task("T01", "alpha")
        bs.write(wt01, bs.BACKEND_PATH,
                "def lookup(widget_id, catalog):\n    return catalog.get(widget_id)\n")
        bs.git(wt01, "add", "-A")
        bs.git(wt01, "commit", "-qm", "backend: add the lookup service")
        self.run_evidence("T01", bs.BACKEND_VERIFY_ARGV)
        code, text, _err = self.finish_task("T01")
        self.assertEqual(code, 0, "sbe work finish T01 failed: %s" % text)

        self.registry_data = self.registry()

        code, text, _err = self.sbe("status", self.repo, "--json")
        self.assertIn(code, (0, 1), text)
        self.status_data = json.loads(text)

        code, text, _err = self.sbe("status", self.repo, "--team", "--json")
        self.assertIn(code, (0, 1), text)
        self.status_team_data = json.loads(text)

        # T02: still unclaimed (only T01 was started above), so `sbe work
        # brief` may write one for it (rule 4 in `work.cmd_brief` refuses a
        # brief for a task an OPEN registry record already owns).
        code, text, _err = self.work("brief", "--plan", self.plan_path, "--task", "T02",
                                     "--json")
        self.assertEqual(code, 0, "sbe work brief T02 failed: %s" % text)
        self.brief_data = json.loads(text)

        code, text, _err = self.sbe("handover", "prepare", self.dossier,
                                    "--outgoing", OUTGOING, "--receiver", RECEIVER)
        self.assertEqual(code, 0, "sbe handover prepare failed: %s" % text)
        with io.open(os.path.join(self.dossier, "12-handover.json"), encoding="utf-8") as fh:
            self.handover_data = json.load(fh)

    def test_task_registry_from_a_real_run_validates_pass(self):
        verdict, evidence, problems = mod.validate_task_registry(self.registry_data)
        self.assertEqual(verdict, "PASS", (evidence, problems, self.registry_data))
        self.assertEqual(problems, ())
        # Grounds the fixture: T01 really is in there, closed, so this is
        # not an empty registry accidentally validating for free.
        ids = [t["id"] for t in self.registry_data["tasks"]]
        self.assertIn("T01", ids, self.registry_data)

    def test_status_json_from_a_real_run_validates_pass(self):
        verdict, evidence, problems = mod.validate_status(self.status_data)
        self.assertEqual(verdict, "PASS", (evidence, problems, self.status_data))
        self.assertEqual(problems, ())

    def test_status_team_json_from_a_real_run_validates_pass(self):
        verdict, evidence, problems = mod.validate_status_team(self.status_team_data)
        self.assertEqual(verdict, "PASS", (evidence, problems, self.status_team_data))
        self.assertEqual(problems, ())
        # The real producer carries no schemaVersion as of 1.0.0-rc.16; this
        # fixture proves that reading, not an assumption:
        self.assertNotIn("schemaVersion", self.status_team_data, self.status_team_data)
        # The absent-version PASS evidence names the absence exactly once, in
        # its own clause: proves the branch the mutated-copy test below does
        # NOT exercise, so both halves of validate_status_team's evidence
        # sentence are pinned by a real fixture.
        self.assertIn("no schemaVersion field", evidence, evidence)

    def test_status_team_evidence_names_a_present_schema_version_without_contradicting_itself(self):
        # Regression: a copy of the SAME real capture above, with a
        # schemaVersion this registry recognizes ADDED, must still validate
        # PASS, and its evidence line must NAME that version rather than
        # asserting (in the same sentence) that no such field exists. Before
        # the fix, the note string hard-coded "no schemaVersion field ..." and
        # merely prefixed the version onto it, so a PASS with a version
        # present read: "schemaVersion '1.0', ... no schemaVersion field (not
        # yet emitted by this surface, accepted by name)": true and false in
        # one line.
        mutated = copy.deepcopy(self.status_team_data)
        mutated["schemaVersion"] = mod.STATUS_TEAM_KNOWN_SCHEMA_VERSIONS[0]
        verdict, evidence, problems = mod.validate_status_team(mutated)
        self.assertEqual(verdict, "PASS", (evidence, problems, mutated))
        self.assertEqual(problems, ())
        self.assertIn("schemaVersion %r" % mod.STATUS_TEAM_KNOWN_SCHEMA_VERSIONS[0], evidence,
                      evidence)
        self.assertNotIn("no schemaVersion field", evidence, evidence)
        # Calibration companion, in the same test: the untouched original
        # (no schemaVersion) still reads the other, correct way.
        _v, original_evidence, _p = mod.validate_status_team(self.status_team_data)
        self.assertIn("no schemaVersion field", original_evidence, original_evidence)

    def test_work_brief_json_from_a_real_run_validates_pass(self):
        verdict, evidence, problems = mod.validate_work_brief(self.brief_data)
        self.assertEqual(verdict, "PASS", (evidence, problems, self.brief_data))
        self.assertEqual(problems, ())
        self.assertEqual(self.brief_data["taskId"], "T02", self.brief_data)

    def test_handover_record_from_a_real_run_validates_pass(self):
        verdict, evidence, problems = mod.validate_handover(self.handover_data)
        self.assertEqual(verdict, "PASS", (evidence, problems, self.handover_data))
        self.assertEqual(problems, ())
        self.assertEqual(self.handover_data["status"], "prepared", self.handover_data)

    def test_the_generic_dispatcher_agrees_with_every_named_function(self):
        pairs = (
            ("task-registry", self.registry_data, mod.validate_task_registry),
            ("status", self.status_data, mod.validate_status),
            ("status-team", self.status_team_data, mod.validate_status_team),
            ("work-brief", self.brief_data, mod.validate_work_brief),
            ("handover", self.handover_data, mod.validate_handover),
        )
        for surface, data, fn in pairs:
            self.assertEqual(mod.validate(surface, data), fn(data), surface)

    # -- anti-drift: the three hand-typed field lists against their real
    # producers. `task-registry`'s and `handover`'s required fields are
    # IMPORTED (`tasks_mod.RECORD_FIELDS`, `handover_mod.SCHEMA_FIELDS`), so a
    # producer change there already breaks at import time; STATUS_FIELDS,
    # STATUS_TEAM_FIELDS and WORK_BRIEF_FIELDS are typed out by hand (no
    # exported constant exists on `status.build_report`,
    # `status.build_team_report` or `work._brief_document` to import instead,
    # per the module docstring), so nothing else in this suite would notice a
    # producer growing or dropping a field: "unknown fields are allowed" is
    # this module's own design, so a widened real document would still
    # validate PASS even while this registry silently under-covers it. Each
    # test below ties one hand-typed tuple to the SAME real, live-captured
    # document `TestRealFixturesValidate.setUp` already produced, by exact
    # key-set equality, so that gap is closed by a fixture rather than left a
    # standing trust-the-docstring claim.

    def test_status_fields_names_exactly_the_keys_a_real_status_document_carries(self):
        self.assertEqual(set(mod.STATUS_FIELDS), set(self.status_data),
                         (sorted(mod.STATUS_FIELDS), sorted(self.status_data)))

    def test_status_team_fields_names_exactly_the_keys_a_real_status_team_document_carries(self):
        self.assertEqual(set(mod.STATUS_TEAM_FIELDS), set(self.status_team_data),
                         (sorted(mod.STATUS_TEAM_FIELDS), sorted(self.status_team_data)))

    def test_work_brief_fields_names_exactly_the_keys_a_real_work_brief_document_carries(self):
        self.assertEqual(set(mod.WORK_BRIEF_FIELDS), set(self.brief_data),
                         (sorted(mod.WORK_BRIEF_FIELDS), sorted(self.brief_data)))


# ---------------------------------------------------------------------------
# Refusal fixtures: a wrong schemaVersion, a missing required field, an
# absent document, the wrong top-level JSON shape, and (the other
# direction) an unknown extra field, which must NOT be refused. Every
# mutation below runs against a `copy.deepcopy` of a REAL captured document
# from `ContractsFixture`, and every test re-validates the untouched
# original as `PASS` in the same method: that is the calibration this
# house rule asks for (mutate, prove red, prove the un-mutated original
# still passes).
# ---------------------------------------------------------------------------

class TestRefusals(ContractsFixture):
    def setUp(self):
        ContractsFixture.setUp(self)
        # A lighter capture than TestRealFixturesValidate: refusal fixtures
        # mutate copies of these, so richness beyond "one real, valid
        # document per surface" buys nothing extra here.
        wt01 = self.start_task("T01", "alpha")
        bs.write(wt01, bs.BACKEND_PATH,
                "def lookup(widget_id, catalog):\n    return catalog.get(widget_id)\n")
        bs.git(wt01, "add", "-A")
        bs.git(wt01, "commit", "-qm", "backend: add the lookup service")
        self.run_evidence("T01", bs.BACKEND_VERIFY_ARGV)
        code, text, _err = self.finish_task("T01")
        self.assertEqual(code, 0, text)
        self.registry_data = self.registry()

        code, text, _err = self.sbe("status", self.repo, "--json")
        self.status_data = json.loads(text)

        code, text, _err = self.sbe("status", self.repo, "--team", "--json")
        self.status_team_data = json.loads(text)

        code, text, _err = self.work("brief", "--plan", self.plan_path, "--task", "T02",
                                     "--json")
        self.assertEqual(code, 0, text)
        self.brief_data = json.loads(text)

        code, text, _err = self.sbe("handover", "prepare", self.dossier,
                                    "--outgoing", OUTGOING, "--receiver", RECEIVER)
        self.assertEqual(code, 0, text)
        with io.open(os.path.join(self.dossier, "12-handover.json"), encoding="utf-8") as fh:
            self.handover_data = json.load(fh)

    # -- wrong schemaVersion, one surface at a time -------------------------

    def _assert_wrong_version_refused(self, validate_fn, original, name_of_field="schemaVersion"):
        mutated = copy.deepcopy(original)
        mutated[name_of_field] = "9.9"
        verdict, evidence, problems = validate_fn(mutated)
        self.assertEqual(verdict, "FAIL", evidence)
        self.assertTrue(any("9.9" in p for p in problems), problems)
        # Calibration: the untouched original still validates PASS, proving
        # the FAIL above came from the mutation and not from a validator
        # that always says FAIL.
        restored_verdict, restored_evidence, restored_problems = validate_fn(original)
        self.assertEqual(restored_verdict, "PASS", restored_evidence)
        self.assertEqual(restored_problems, ())

    def test_task_registry_with_an_unknown_schema_version_is_refused(self):
        self._assert_wrong_version_refused(mod.validate_task_registry, self.registry_data)

    def test_status_json_with_an_unknown_schema_version_is_refused(self):
        self._assert_wrong_version_refused(mod.validate_status, self.status_data)

    def test_work_brief_with_an_unknown_schema_version_is_refused(self):
        self._assert_wrong_version_refused(mod.validate_work_brief, self.brief_data)

    def test_handover_with_an_unknown_schema_version_is_refused(self):
        self._assert_wrong_version_refused(mod.validate_handover, self.handover_data)

    def test_status_team_with_a_present_but_unknown_schema_version_is_refused(self):
        # This surface carries none by default (asserted in
        # TestRealFixturesValidate); a mutated copy ADDS the field with an
        # unrecognized value, which must still be refused by name.
        mutated = copy.deepcopy(self.status_team_data)
        mutated["schemaVersion"] = "9.9"
        verdict, evidence, problems = mod.validate_status_team(mutated)
        self.assertEqual(verdict, "FAIL", evidence)
        self.assertTrue(any("9.9" in p for p in problems), problems)
        restored_verdict, _e, restored_problems = mod.validate_status_team(self.status_team_data)
        self.assertEqual(restored_verdict, "PASS", _e)
        self.assertEqual(restored_problems, ())

    # -- missing required field, one per surface -----------------------------

    def _assert_missing_field_refused(self, validate_fn, original, field):
        mutated = copy.deepcopy(original)
        del mutated[field]
        verdict, evidence, problems = validate_fn(mutated)
        self.assertEqual(verdict, "FAIL", evidence)
        self.assertTrue(any(field in p for p in problems), problems)
        restored_verdict, restored_evidence, restored_problems = validate_fn(original)
        self.assertEqual(restored_verdict, "PASS", restored_evidence)
        self.assertEqual(restored_problems, ())

    def test_task_registry_missing_tasks_is_refused(self):
        self._assert_missing_field_refused(mod.validate_task_registry, self.registry_data,
                                           "tasks")

    def test_task_registry_with_a_task_record_missing_a_field_is_refused(self):
        mutated = copy.deepcopy(self.registry_data)
        self.assertTrue(mutated["tasks"], "fixture bug: no task record to mutate")
        del mutated["tasks"][0]["role"]
        verdict, evidence, problems = mod.validate_task_registry(mutated)
        self.assertEqual(verdict, "FAIL", evidence)
        self.assertTrue(any("role" in p for p in problems), problems)
        restored_verdict, _e, restored_problems = mod.validate_task_registry(self.registry_data)
        self.assertEqual(restored_verdict, "PASS", _e)
        self.assertEqual(restored_problems, ())

    def test_task_registry_with_a_task_record_holding_an_unknown_role_is_refused(self):
        mutated = copy.deepcopy(self.registry_data)
        mutated["tasks"][0]["role"] = "owner"
        verdict, evidence, problems = mod.validate_task_registry(mutated)
        self.assertEqual(verdict, "FAIL", evidence)
        self.assertTrue(any("owner" in p for p in problems), problems)

    def test_status_json_missing_next_action_is_refused(self):
        self._assert_missing_field_refused(mod.validate_status, self.status_data, "nextAction")

    def test_status_team_json_missing_findings_is_refused(self):
        self._assert_missing_field_refused(mod.validate_status_team, self.status_team_data,
                                           "findings")

    def test_work_brief_missing_acceptance_is_refused(self):
        self._assert_missing_field_refused(mod.validate_work_brief, self.brief_data,
                                           "acceptance")

    def test_handover_missing_prepared_by_is_refused(self):
        self._assert_missing_field_refused(mod.validate_handover, self.handover_data,
                                           "preparedBy")

    # -- absent document and wrong top-level shape --------------------------

    def test_every_validator_reports_no_data_for_an_absent_document(self):
        for fn in (mod.validate_task_registry, mod.validate_status, mod.validate_status_team,
                  mod.validate_work_brief, mod.validate_handover):
            verdict, evidence, problems = fn(None)
            self.assertEqual(verdict, "NO-DATA", (fn.__name__, evidence))
            self.assertEqual(problems, ())

    def test_every_validator_refuses_a_wrong_top_level_shape_as_fail_not_no_data(self):
        # A list where a JSON object belongs is a broken claim, not an
        # absence: the same class evals/test_no_data_class.py's own
        # legacy_cases already fixes for every check in this project that
        # reads a JSON file.
        for fn in (mod.validate_task_registry, mod.validate_status, mod.validate_status_team,
                  mod.validate_work_brief, mod.validate_handover):
            verdict, evidence, problems = fn([1, 2, 3])
            self.assertEqual(verdict, "FAIL", (fn.__name__, evidence))
            self.assertTrue(problems, (fn.__name__, problems))

    def test_every_wrong_shape_problem_names_its_own_surface(self):
        # Companion to the structural guard in TestRegistryShape: every
        # validator's own wrong-shape problem string names ITS OWN surface,
        # called back to back in a fixed order so a reader can see each
        # call's evidence text does not echo a name any OTHER call in this
        # same sequence used.
        labels = {
            mod.validate_task_registry: "task registry",
            mod.validate_status: "sbe status --json document",
            mod.validate_status_team: "sbe status --team --json document",
            mod.validate_work_brief: "work brief document",
            mod.validate_handover: "handover record",
        }
        others = set(labels.values())
        for fn, own_label in labels.items():
            _v, evidence, _p = fn([1, 2, 3])
            self.assertIn(own_label, evidence, evidence)
            for other_label in others - {own_label}:
                self.assertNotIn(other_label, evidence, (own_label, other_label, evidence))

    # -- unknown fields are allowed, the other direction ---------------------

    def test_task_registry_with_an_unknown_extra_field_still_validates_pass(self):
        mutated = copy.deepcopy(self.registry_data)
        mutated["futureField"] = "something a newer tool wrote"
        mutated["tasks"][0]["futureTaskField"] = "also forward compatible"
        verdict, evidence, problems = mod.validate_task_registry(mutated)
        self.assertEqual(verdict, "PASS", evidence)
        self.assertEqual(problems, ())

    def test_handover_with_an_unknown_extra_field_still_validates_pass(self):
        mutated = copy.deepcopy(self.handover_data)
        mutated["futureField"] = "something a newer tool wrote"
        verdict, evidence, problems = mod.validate_handover(mutated)
        self.assertEqual(verdict, "PASS", evidence)
        self.assertEqual(problems, ())

    # -- the dispatcher's own refusal, a caller error rather than a finding --

    def test_the_dispatcher_refuses_an_unknown_surface_by_name(self):
        with self.assertRaises(ValueError) as ctx:
            mod.validate("not-a-real-surface", {})
        for name in mod.SURFACES:
            self.assertIn(name, str(ctx.exception))


# ---------------------------------------------------------------------------
# The registry itself: shape independent of any one captured document.
# ---------------------------------------------------------------------------

class TestRegistryShape(unittest.TestCase):
    def test_contracts_schema_version_is_the_integer_one(self):
        self.assertIsInstance(mod.CONTRACTS_SCHEMA_VERSION, int)
        self.assertEqual(mod.CONTRACTS_SCHEMA_VERSION, 1)

    def test_surfaces_names_exactly_the_five_known_surfaces(self):
        self.assertEqual(set(mod.SURFACES),
                         {"task-registry", "status", "status-team", "work-brief", "handover"})
        self.assertEqual(set(mod.VALIDATORS), set(mod.SURFACES))

    def test_every_validator_returns_the_house_three_tuple(self):
        for surface in mod.SURFACES:
            result = mod.validate(surface, None)
            self.assertIsInstance(result, tuple)
            self.assertEqual(len(result), 3, (surface, result))
            verdict, evidence, problems = result
            self.assertIn(verdict, mod.VERDICTS, surface)
            self.assertIsInstance(evidence, str, surface)
            self.assertIsInstance(problems, tuple, surface)

    def test_no_module_level_mutable_surface_label_survives_a_call(self):
        # Regression: `_shape_problem` used to read "which surface is this"
        # off a module-level, mutable, shared list (`_CURRENT_SURFACE_LABEL`,
        # a single object every `validate_*` call reassigned right before
        # calling `_shape_problem`). Two `validate_*` calls interleaved (two
        # threads, one paused between setting the label and reading it back)
        # could then have the SECOND call's wrong-shape problem string name
        # whichever surface set that shared state last, not its own; nothing
        # about a single-threaded, non-interleaved call sequence can exercise
        # that race (each call sets its own label immediately before its own
        # read), so this pins the STRUCTURAL fix instead: the shared object
        # is gone from the module entirely, and `_shape_problem` takes the
        # surface name as an explicit parameter, so there is no shared slot
        # left for a second call to race on.
        called = mod.validate_work_brief([1, 2, 3])  # exercises the code path
        self.assertEqual(called[0], "FAIL", called)
        self.assertFalse(hasattr(mod, "_CURRENT_SURFACE_LABEL"),
                         "a module-level mutable surface label still exists on "
                         "brothersbe.contracts; two validate_* calls in flight at "
                         "once can cross-contaminate each other's problem text")
        params = list(inspect.signature(mod._shape_problem).parameters)
        self.assertIn("label", params,
                      "_shape_problem(%s) no longer takes the surface name as an "
                      "explicit parameter" % ", ".join(params))


if __name__ == "__main__":
    unittest.main()
