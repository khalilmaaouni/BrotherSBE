#!/usr/bin/env python3
"""Fixtures for `sbe work`. Run: python3 tools/test_sbe_work.py

Spec of record: docs/specs/2026-07-30-sbe-work-lifecycle.md. These fixtures
assert exactly what that document says, nothing else: a disagreement between
this file and the eventual src/brothersbe/work.py is a defect in one of them,
never a negotiation settled here.

At the time this file was written, `bin/sbe` has no `work` subcommand at all,
so every invocation below fails at argument parsing (usage, exit 2) before it
reaches anything this suite actually asserts about. Every test here is
expected to FAIL against that gap (never ERROR: no import crash, no fixture
crash) because each test's FIRST assertion checks the `work` call itself, and
a failing assertion there stops the test immediately, before any later line
that assumes infrastructure (a real worktree, a real branch, a real registry
record) `sbe work start` would have created. That red is the point: tests
first, and the same test keeps proving more of the spec as work.py is built
out underneath it, with no rewrite needed here.

Two fixture techniques, both borrowed rather than invented:

  - Real dossiers and a real derived plan, built and read through the landed
    `sbe plan --write` (Loop 1), exactly mirroring the dossier body constants
    and the render_verification()/_find_task()/_find_migration_triplet()
    helpers in tools/test_sbe_plan.py. Copied here rather than imported,
    because suites in this project stay standalone; a disagreement between
    the two copies would be a defect to fix in both, not a shared import to
    chase.
  - Registry records seeded directly into .sbe/tasks.json, the same technique
    tools/test_sbe_tasks.py uses in TestOverlap to test `sbe task check`
    against a collision nothing ever opened honestly. `check`, `finish`, and
    `remove` all read that one registry file, so a scenario that would have
    been produced by `sbe work start` (an open record, a real git worktree)
    can be built directly and inspected on its own, without depending on the
    part of `sbe work` this loop has not written yet.

Every fixture builds a real git repository in a fresh tempfile.mkdtemp() (git
init, one seed commit) and, where a scenario needs one, a real git worktree
inside that same tempdir via `--worktree-dir`. Nothing here ever touches the
real repository this file lives in, and nothing is mocked: the defect this
whole command exists for lives at the seam between what a task declared and
what the tree and the registry actually show, and a mocked diff would test
the mock.
"""
import ast
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


# -- dossier body constants, copied from tools/test_sbe_plan.py rather than
# imported: suites in this project stay standalone. Only what `sbe work`
# fixtures need is kept (a single writer decision, a migration triplet, three
# verification rows), and none of it is meant to exercise plan derivation
# itself, only to hand `sbe work` a real, validation-passing plan to read.

ADR_BODY = (
    "# 03. Architecture decision record\n\n"
    "## Context\n"
    "Cache lookups are slow under normal load.\n\n"
    "## Decision\n"
    "We cache widget lookups in `src/widgets/cache.py`, backed by `config/cache.yaml`.\n\n"
    "## Consequences\n"
    "This adds one dependency to operate.\n\n"
    "## What would flip this\n"
    "If the cache hit rate falls under the agreed target.\n"
)

DATA_MODEL_BODY = (
    "# 05. Data model\n\n"
    "## Physical\n"
    "The migration adds `migrations/0001_widget_cache.sql` for the cache table.\n"
)

ROW_PLAIN = ("The cache responds within budget",
             "Run `pytest tests/test_cache_perf.py`", "Continuous")
ROW_REVERSE = ("The migration rollback restores prior state",
               "Run `python3 migrations/0001_widget_cache.sql --reverse`", "On demand")
ROW_RECONCILE = ("Reconciliation confirms row counts match",
                  "Run `python3 tools/reconcile_widget_cache.py`", "Daily")
DEFAULT_ROWS = [ROW_PLAIN, ROW_REVERSE, ROW_RECONCILE]

ADR_PATHS = ("src/widgets/cache.py", "config/cache.yaml")
PHYSICAL_PATH = "migrations/0001_widget_cache.sql"
CHANGE_DIR = "design/widget-cache"


def render_verification(rows):
    lines = ["# 07. Verification plan", "",
             "| Claim this design makes | The check that proves it | When it runs |",
             "|---|---|---|"]
    for claim, check, when in rows:
        lines.append("| %s | %s | %s |" % (claim, check, when))
    return "\n".join(lines) + "\n"


class WorkFixture(unittest.TestCase):
    """A fresh repository, a fresh dossier, and a worktree-dir, all inside one
    tempdir per test. The plan itself is derived per-test (never in setUp): a
    real command failure here would be a fixture bug, and unittest reports
    every exception raised inside setUp as an ERROR regardless of its type, so
    the one call this suite genuinely expects to keep succeeding (`sbe plan`,
    landed in Loop 1) is asserted inside the test body instead, exactly like
    tools/test_sbe_plan.py already does for the same reason.
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.repo = os.path.join(self.tmp, "repo")
        os.makedirs(self.repo)
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "fixture@example.invalid")
        git(self.repo, "config", "user.name", "fixture")
        write(self.repo, "README.md", "base\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "base")
        self.base = git(self.repo, "rev-parse", "HEAD")
        self.worktree_dir = os.path.join(self.tmp, "worktrees")
        os.makedirs(self.worktree_dir)
        self.dossier = self._write_dossier()
        self.change_id = os.path.basename(self.dossier)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # -- process helpers. Three values, not two: a two-value return here
    # would read as a possible (verdict, evidence) pair to the honesty
    # meta-test in evals/test_no_data_class.py, exactly the reason
    # tools/test_sbe_tasks.py's sbe() and tools/test_sbe_plan.py's sbe() are
    # both 3-tuples. This is the same shape, mirrored, not reinvented.

    def sbe(self, *argv):
        out = subprocess.run([sys.executable, SBE] + list(argv), capture_output=True, text=True)
        return out.returncode, out.stdout + out.stderr, out.stderr

    def work(self, *argv):
        return self.sbe("work", *argv, "--cwd", self.repo)

    # -- dossier and plan -----------------------------------------------------

    def _write_dossier(self):
        answers = {"changes_contract": "n", "crosses_boundary": "n",
                   "reversible_under_hour": "y", "touches_sensitive": "n",
                   "consumers": "none"}
        intake = {"answers": answers, "binding": {"head": self.base}}
        write(self.repo, os.path.join(CHANGE_DIR, "00-intake.json"), json.dumps(intake))
        write(self.repo, os.path.join(CHANGE_DIR, "03-adr.md"), ADR_BODY)
        write(self.repo, os.path.join(CHANGE_DIR, "05-data-model.md"), DATA_MODEL_BODY)
        write(self.repo, os.path.join(CHANGE_DIR, "07-verification.md"),
              render_verification(DEFAULT_ROWS))
        return os.path.join(self.repo, CHANGE_DIR)

    def _plan(self):
        """(plan dict, plan path, the command's own output). Three values, not
        two, for the same reason every process helper here is a 3-tuple: see
        the module docstring on `sbe()`."""
        plan_path = os.path.join(self.dossier, "08-plan.json")
        code, out, _err = self.sbe("plan", self.dossier, "--write", "--cwd", self.repo)
        self.assertEqual(code, 0, "fixture setup could not derive a plan through the "
                                  "landed `sbe plan --write`; this is a fixture bug, not "
                                  "the `sbe work` gap this suite exists to prove: %s" % out)
        with io.open(plan_path, encoding="utf-8") as fh:
            plan = json.load(fh)
        return plan, plan_path, out

    def _save_plan(self, plan_path, plan):
        with io.open(plan_path, "w", encoding="utf-8") as fh:
            json.dump(plan, fh)

    def _find_task(self, plan, task_id):
        for t in plan["tasks"]:
            if t.get("id") == task_id:
                return t
        self.fail("no task %r in plan: %s" % (task_id, plan))

    def _find_reviewer(self, plan):
        for t in plan["tasks"]:
            if t.get("role") == "reviewer":
                return t
        self.fail("expected at least one reviewer task: %s" % plan)

    def _find_migration_triplet(self, plan):
        """(forward, reverse, reconciliation). Copied from
        tools/test_sbe_plan.py's own helper of the same name: forward is
        found by the path it owns, reverse and reconciliation by the
        dependency edge plus what their acceptance text mentions, never by a
        hardcoded task id, because id assignment is the planner's business,
        not this suite's."""
        forward = None
        for t in plan["tasks"]:
            if PHYSICAL_PATH in (t.get("owns") or []):
                forward = t
                break
        self.assertIsNotNone(forward, "expected a migration forward task owning %r: %s"
                             % (PHYSICAL_PATH, plan))
        reverse = None
        reconciliation = None
        for t in plan["tasks"]:
            if t is forward:
                continue
            depends = t.get("dependsOn") or []
            if forward["id"] not in depends:
                continue
            blob = " ".join(t.get("acceptance") or []).lower()
            if "rollback" in blob or "reverse" in blob:
                reverse = t
            elif "reconcil" in blob:
                reconciliation = t
        self.assertIsNotNone(reverse,
                             "expected a reverse task depending on the forward task: %s" % plan)
        self.assertIsNotNone(reconciliation,
                             "expected a reconciliation task depending on the forward task: %s"
                             % plan)
        return forward, reverse, reconciliation

    # -- registry: the single source of task state, per the spec. Some
    # scenarios seed a record directly into .sbe/tasks.json rather than through
    # `sbe work start`, exactly the way tools/test_sbe_tasks.py's TestOverlap
    # seeds a collision directly to test `sbe task check` in isolation: the
    # part of `sbe work` that would have produced this record honestly is not
    # the part under test in those scenarios.

    def _registry_path(self):
        return os.path.join(self.repo, ".sbe", "tasks.json")

    def _registry(self):
        with io.open(self._registry_path(), encoding="utf-8") as fh:
            return json.load(fh)

    def _record(self, task_id):
        for t in self._registry()["tasks"]:
            if t.get("id") == task_id:
                return t
        return None

    def _seed(self, record):
        path = self._registry_path()
        if os.path.exists(path):
            with io.open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        else:
            data = {"schemaVersion": "1.0", "tasks": []}
        data["tasks"].append(record)
        write(self.repo, os.path.join(".sbe", "tasks.json"), json.dumps(data))

    def _base_record(self, task_id, **overrides):
        record = {
            "id": task_id, "agent": "alpha", "role": "writer", "worktree": None,
            "ownedPaths": [], "readOnlyPaths": [], "baseCommit": self.base,
            "expiry": None, "status": "open", "verifyCommand": "true",
            "evidenceId": None, "openedAt": "2026-07-30T00:00:00Z", "closedAt": None,
        }
        record.update(overrides)
        return record

    # -- real git worktrees, for scenarios that need one to exist before the
    # `sbe work` call under test runs. Always created inside self.worktree_dir,
    # itself inside self.tmp: the repo law this loop is bound by says a
    # worktree dir lives inside the tempdir, never in the real repo tree.

    def _worktree_for(self, task_id, commit=None):
        path = os.path.join(self.worktree_dir, "wt-%s" % task_id)
        git(self.repo, "worktree", "add", "--detach", "-q", path, commit or self.base)
        return path

    def branch_exists(self, name):
        out = subprocess.run(["git", "rev-parse", "--verify", "--quiet",
                              "refs/heads/" + name],
                             cwd=self.repo, capture_output=True, text=True)
        return out.returncode == 0

    def worktree_path_for(self, task_id):
        """The path `sbe work start` is documented to create the worktree at:
        <worktree-dir>/<repo-name>-sbe-<task-id>."""
        return os.path.join(self.worktree_dir,
                            "%s-sbe-%s" % (os.path.basename(self.repo), task_id))


class TestStartValid(WorkFixture):
    def test_start_on_a_valid_plan_task_opens_branch_worktree_record_and_prints_the_contract(self):
        plan, plan_path, _out = self._plan()
        reviewer = self._find_reviewer(plan)  # owns nothing: legal for a reviewer to start
        code, text, _ = self.work("start", reviewer["id"], "--plan", plan_path,
                                  "--worktree-dir", self.worktree_dir, "--agent", "alpha")
        self.assertEqual(code, 0, text)

        branch = "sbe/%s/%s" % (self.change_id, reviewer["id"])
        self.assertTrue(self.branch_exists(branch),
                        "expected branch %s to exist: %s" % (branch, text))
        worktree = self.worktree_path_for(reviewer["id"])
        self.assertTrue(os.path.isdir(worktree),
                        "expected a dedicated worktree at %s: %s" % (worktree, text))

        record = self._record(reviewer["id"])
        self.assertIsNotNone(record, "expected an open registry record for %s: %s"
                             % (reviewer["id"], text))
        self.assertEqual(record["status"], "open", record)
        self.assertEqual(record["role"], reviewer["role"], record)
        self.assertEqual(sorted(record["ownedPaths"] or []), sorted(reviewer["owns"] or []),
                         record)
        self.assertEqual(record["worktree"], worktree, record)

        for acceptance in reviewer["acceptance"]:
            self.assertIn(acceptance, text, "expected acceptance criterion printed: %s" % text)
        for cmd in reviewer["verificationCommands"]:
            self.assertIn(cmd, text, "expected verification command printed: %s" % text)
        for src in reviewer["dossierSources"]:
            self.assertIn(src, text, "expected dossier source printed: %s" % text)


class TestStartRefusals(WorkFixture):
    def test_start_refuses_an_unknown_task_id(self):
        _plan, plan_path, _out = self._plan()
        code, text, _ = self.work("start", "T99-not-in-plan", "--plan", plan_path,
                                  "--worktree-dir", self.worktree_dir, "--agent", "alpha")
        self.assertEqual(code, 2, text)
        self.assertIn("T99-not-in-plan", text)

    def test_start_refuses_when_a_dependency_is_not_yet_closed(self):
        plan, plan_path, _out = self._plan()
        forward, reverse, _recon = self._find_migration_triplet(plan)
        code, text, _ = self.work("start", reverse["id"], "--plan", plan_path,
                                  "--worktree-dir", self.worktree_dir, "--agent", "alpha")
        self.assertNotEqual(code, 0, text)
        self.assertIn(forward["id"], text)

    def test_start_refuses_when_a_dependency_was_force_closed(self):
        plan, plan_path, _out = self._plan()
        forward, reverse, _recon = self._find_migration_triplet(plan)
        self._seed(self._base_record(forward["id"], status="closed",
                                     ownedPaths=forward["owns"],
                                     forced={"who": "operator", "why": "hotfix, accepted "
                                                                       "out of band",
                                            "at": "2026-07-30T00:00:00Z", "verdict": "FAIL",
                                            "violations": []}))
        code, text, _ = self.work("start", reverse["id"], "--plan", plan_path,
                                  "--worktree-dir", self.worktree_dir, "--agent", "alpha")
        self.assertNotEqual(code, 0, text)
        self.assertIn(forward["id"], text)
        self.assertIn("forced", text.lower(),
                      "a FORCED close must not read as a satisfied dependency")

    def test_start_refuses_an_existing_branch_collision(self):
        plan, plan_path, _out = self._plan()
        t01 = self._find_task(plan, "T01")
        branch = "sbe/%s/%s" % (self.change_id, t01["id"])
        git(self.repo, "branch", branch)
        code, text, _ = self.work("start", t01["id"], "--plan", plan_path,
                                  "--worktree-dir", self.worktree_dir, "--agent", "alpha")
        self.assertNotEqual(code, 0, text)
        self.assertIn(branch, text)

    def test_start_refuses_an_existing_worktree_directory_collision(self):
        plan, plan_path, _out = self._plan()
        t01 = self._find_task(plan, "T01")
        worktree = self.worktree_path_for(t01["id"])
        os.makedirs(worktree)
        code, text, _ = self.work("start", t01["id"], "--plan", plan_path,
                                  "--worktree-dir", self.worktree_dir, "--agent", "alpha")
        self.assertNotEqual(code, 0, text)
        self.assertIn(worktree, text)

    def test_start_refuses_an_already_open_registry_record(self):
        plan, plan_path, _out = self._plan()
        t01 = self._find_task(plan, "T01")
        self._seed(self._base_record(t01["id"], ownedPaths=t01["owns"]))
        code, text, _ = self.work("start", t01["id"], "--plan", plan_path,
                                  "--worktree-dir", self.worktree_dir, "--agent", "alpha")
        self.assertNotEqual(code, 0, text)
        self.assertIn(t01["id"], text)


class TestReviewerCannotOwn(WorkFixture):
    def test_start_refuses_a_reviewer_task_that_owns_paths(self):
        plan, _plan_path, _out = self._plan()
        reviewer = self._find_reviewer(plan)
        reviewer["owns"] = ["docs/should-not-be-owned.md"]
        edited_path = os.path.join(self.dossier, "08-plan-reviewer-owns.json")
        self._save_plan(edited_path, plan)
        code, text, _ = self.work("start", reviewer["id"], "--plan", edited_path,
                                  "--worktree-dir", self.worktree_dir, "--agent", "alpha")
        self.assertNotEqual(code, 0, text)
        self.assertIn(reviewer["id"], text)
        self.assertIn("reviewer", text.lower())


class TestCheck(WorkFixture):
    def test_check_names_an_out_of_scope_shell_write_and_reports_not_closable(self):
        plan, _plan_path, _out = self._plan()
        t01 = self._find_task(plan, "T01")
        worktree = self._worktree_for(t01["id"])
        self._seed(self._base_record(t01["id"], worktree=worktree, ownedPaths=t01["owns"],
                                     baseCommit=self.base, verifyCommand="true"))
        owned_rel = t01["owns"][0]
        write(worktree, owned_rel, "changed, in scope\n")
        git(worktree, "add", "-A")
        git(worktree, "commit", "-qm", "in scope edit")
        write(worktree, "docs/sneaky.md", "never declared\n")  # plain open(), no tool
        code, text, _ = self.work("check", t01["id"])
        self.assertEqual(code, 1, text)
        self.assertIn(owned_rel, text)
        self.assertIn("docs/sneaky.md", text)
        self.assertIn("NOT CLOSABLE", text)


class TestFinishRefusals(WorkFixture):
    def test_finish_refuses_on_out_of_scope_writes_naming_the_paths(self):
        plan, _plan_path, _out = self._plan()
        t01 = self._find_task(plan, "T01")
        worktree = self._worktree_for(t01["id"])
        self._seed(self._base_record(t01["id"], worktree=worktree, ownedPaths=t01["owns"],
                                     baseCommit=self.base, verifyCommand="true"))
        write(worktree, "docs/sneaky.md", "never declared\n")
        git(worktree, "add", "-A")
        git(worktree, "commit", "-qm", "sneaky")
        code, text, _ = self.work("finish", t01["id"])
        self.assertNotEqual(code, 0, text)
        self.assertIn("docs/sneaky.md", text)

    def test_finish_refuses_as_no_data_when_the_verification_receipt_is_absent(self):
        plan, _plan_path, _out = self._plan()
        t01 = self._find_task(plan, "T01")
        worktree = self._worktree_for(t01["id"])
        self._seed(self._base_record(t01["id"], worktree=worktree, ownedPaths=t01["owns"],
                                     baseCommit=self.base, verifyCommand="true"))
        write(worktree, t01["owns"][0], "changed, in scope\n")
        git(worktree, "add", "-A")
        git(worktree, "commit", "-qm", "in scope, no receipt")
        code, text, _ = self.work("finish", t01["id"])
        self.assertNotEqual(code, 0, text)
        self.assertIn("NO-DATA", text)
        self.assertIn("true", text, "the verify command must be named, not just NO-DATA")


class TestFinishIntegration(WorkFixture):
    def test_finish_with_scope_kept_and_a_real_receipt_closes_clean_and_unblocks_a_dependent(self):
        plan, _plan_path, _out = self._plan()
        forward, reverse, _recon = self._find_migration_triplet(plan)
        # The dossier never states a check command for the forward migration
        # task itself: only 07-verification rows carry commands, and those
        # become separate reviewer tasks (see the derivation spec, rule 3 vs
        # rule 2). Adding one here is the general plan SHAPE the spec
        # documents (every task record may carry verificationCommands),
        # never a derivation rule this suite invents.
        forward["verificationCommands"] = ["true"]
        forward["requiredEvidence"] = ["command-receipt"]
        edited_path = os.path.join(self.dossier, "08-plan-with-verify.json")
        self._save_plan(edited_path, plan)

        code, text, _ = self.work("start", forward["id"], "--plan", edited_path,
                                  "--worktree-dir", self.worktree_dir, "--agent", "alpha")
        self.assertEqual(code, 0, text)
        worktree = self.worktree_path_for(forward["id"])

        owned_rel = forward["owns"][0]
        write(worktree, owned_rel, "-- forward migration, in scope\n")
        git(worktree, "add", "-A")
        git(worktree, "commit", "-qm", "forward migration, in scope")

        # The receipt is written to the repository's OWN evidence store, not
        # into the worktree's tracked tree: a receipt is metadata about the
        # run, not a file the task declared it owns, and the postcondition
        # must not have to special-case it the way it special-cases its own
        # registry file.
        receipt_path = os.path.join(self.repo, ".sbe", "evidence", "forward-receipt.json")
        code, text, _ = self.sbe("evidence", "run", "--out", receipt_path,
                                 "--cwd", worktree, "--", "true")
        self.assertEqual(code, 0, text)

        code, text, _ = self.work("finish", forward["id"])
        self.assertEqual(code, 0, text)
        record = self._record(forward["id"])
        self.assertEqual(record["status"], "closed", record)
        self.assertNotIn("forced", record, "a clean finish must not look forced")

        code, text, _ = self.work("start", reverse["id"], "--plan", edited_path,
                                  "--worktree-dir", self.worktree_dir, "--agent", "beta")
        self.assertEqual(code, 0,
                         "the forward task is now closed clean, so its dependent must be "
                         "able to start: %s" % text)


class TestForceFinish(WorkFixture):
    def test_finish_force_closes_marks_forced_visible_in_check_and_never_satisfies_a_dependent(self):
        plan, plan_path, _out = self._plan()
        forward, reverse, _recon = self._find_migration_triplet(plan)
        worktree = self._worktree_for(forward["id"])
        self._seed(self._base_record(forward["id"], worktree=worktree,
                                     ownedPaths=forward["owns"], baseCommit=self.base,
                                     verifyCommand="true"))
        write(worktree, "docs/out-of-scope.md", "never declared\n")
        git(worktree, "add", "-A")
        git(worktree, "commit", "-qm", "out of scope, forced through")

        code, text, _ = self.work("finish", forward["id"], "--force",
                                  "--who", "operator", "--why", "hotfix, accepted out of band")
        self.assertEqual(code, 0, text)
        self.assertIn("FORCED", text)
        record = self._record(forward["id"])
        self.assertEqual(record["status"], "closed", record)

        code, text, _ = self.work("check", forward["id"])
        self.assertIn("FORCED", text, "a forced close must print FORCED loudly in check too")

        code, text, _ = self.work("start", reverse["id"], "--plan", plan_path,
                                  "--worktree-dir", self.worktree_dir, "--agent", "beta")
        self.assertNotEqual(code, 0,
                           "a FORCED close of a dependency must never satisfy a dependent's "
                           "start: %s" % text)
        self.assertIn(forward["id"], text)
        self.assertIn("forced", text.lower())


class TestRemove(WorkFixture):
    def test_remove_refuses_an_open_task(self):
        plan, _plan_path, _out = self._plan()
        t01 = self._find_task(plan, "T01")
        worktree = self._worktree_for(t01["id"])
        self._seed(self._base_record(t01["id"], worktree=worktree, ownedPaths=t01["owns"],
                                     status="open"))
        code, text, _ = self.work("remove", t01["id"])
        self.assertNotEqual(code, 0, text)
        self.assertTrue(os.path.isdir(worktree),
                        "an open task's worktree must never be removed")

    def test_remove_refuses_a_dirty_closed_worktree_without_override(self):
        plan, _plan_path, _out = self._plan()
        t01 = self._find_task(plan, "T01")
        worktree = self._worktree_for(t01["id"])
        self._seed(self._base_record(t01["id"], worktree=worktree, ownedPaths=t01["owns"],
                                     status="closed"))
        write(worktree, "uncommitted.txt", "dirty\n")  # never committed
        code, text, _ = self.work("remove", t01["id"])
        self.assertNotEqual(code, 0, text)
        self.assertTrue(os.path.isdir(worktree),
                        "a dirty worktree must survive a refused remove")

    def test_remove_with_override_dirty_succeeds_and_records_the_reason(self):
        plan, _plan_path, _out = self._plan()
        t01 = self._find_task(plan, "T01")
        worktree = self._worktree_for(t01["id"])
        self._seed(self._base_record(t01["id"], worktree=worktree, ownedPaths=t01["owns"],
                                     status="closed"))
        write(worktree, "uncommitted.txt", "dirty\n")
        reason = "cleanup after an accepted hotfix"
        code, text, _ = self.work("remove", t01["id"], "--override-dirty", reason)
        self.assertEqual(code, 0, text)
        self.assertFalse(os.path.isdir(worktree),
                         "an overridden remove must delete the worktree")
        record = self._record(t01["id"])
        self.assertEqual(record.get("overrideDirty"), reason,
                         "the override reason must be recorded on the registry record, "
                         "permanent visible history: %s" % record)


def _find_unreviewable_git_argv(source):
    """Static analysis, one level deeper than the plain List/Tuple-literal
    scan above. That scan is blind to a call site that builds its argv one
    step removed from a literal, e.g.:

        sub = "mer" + "ge"
        _git([sub, "origin", branch], root)

    where the List IS a literal, but its first element is a concatenation,
    not an ast.Constant string, so the earlier check's `isinstance(head,
    ast.Constant)` guard silently lets it through (the audit's own
    mutation proved this: it goes red only once this function exists).

    Returns a list of human-readable violation strings, empty when every
    call resolves to a str literal head. A call is walked when its func is
    `_git` by Name (as imported and used in src/brothersbe/work.py) or by
    Attribute (module.method access), matching however this codebase might
    spell the call. The argv argument is followed through at most one
    simple `name = <expr>` assignment (and through an `a if cond else b`
    conditional of literals, the one pattern src/brothersbe/work.py itself
    uses at its `sbe work remove` call site) so a legitimate
    variable-holding-a-literal-list is not a false positive; anything this
    resolver cannot trace back to a literal string head (a concatenation,
    a function call, an unresolved name) is reported as unreviewable."""
    tree = ast.parse(source)

    def is_git_call_func(func):
        if isinstance(func, ast.Name) and func.id == "_git":
            return True
        if isinstance(func, ast.Attribute) and func.attr == "_git":
            return True
        return False

    def literal_head_is_safe(list_or_tuple):
        if not isinstance(list_or_tuple, (ast.List, ast.Tuple)) or not list_or_tuple.elts:
            return False
        head = list_or_tuple.elts[0]
        return isinstance(head, ast.Constant) and isinstance(head.value, str)

    # Every simple `name = <expr>` assignment in the module, keyed by name,
    # so a call site passing a variable can be traced to the nearest
    # preceding assignment rather than being invisible to this check. This
    # is a best-effort, whole-module resolution (not scope-aware): sufficient
    # for the straight-line style this module is written in, and it never
    # needs to be more than that to catch the shape the audit found.
    assigns_by_name = {}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)):
            assigns_by_name.setdefault(node.targets[0].id, []).append(
                (node.lineno, node.value))

    def resolve_is_safe(expr, before_line, depth=0):
        if depth > 4:
            return False
        if isinstance(expr, (ast.List, ast.Tuple)):
            return literal_head_is_safe(expr)
        if isinstance(expr, ast.IfExp):
            return (resolve_is_safe(expr.body, before_line, depth + 1)
                    and resolve_is_safe(expr.orelse, before_line, depth + 1))
        if isinstance(expr, ast.Name):
            candidates = [pair for pair in assigns_by_name.get(expr.id, [])
                          if pair[0] <= before_line]
            if not candidates:
                return False
            candidates.sort(key=lambda pair: pair[0])
            return resolve_is_safe(candidates[-1][1], before_line, depth + 1)
        return False

    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not is_git_call_func(node.func):
            continue
        if not node.args:
            violations.append(
                "_git call at line %d passes no argv argument at all" % node.lineno)
            continue
        if not resolve_is_safe(node.args[0], node.lineno):
            violations.append(
                "_git call at line %d builds its argv head from something this law "
                "cannot read as a literal string (a concatenation, a function call, "
                "or a variable it cannot trace to one): a variable-built git "
                "subcommand is unreviewable by this law" % node.lineno)
    return violations


class TestNoMergeLaw(unittest.TestCase):
    """Source-level: nothing in the work code path ever runs git merge, rebase,
    push, or deploy (CHANGELOG and KNOWN-LIMITS both say deploy is guarded
    too, so the forbidden set must say so mechanically). Matched against the
    shape this codebase actually constructs git argv in (a list or tuple
    literal whose FIRST element is the subcommand, e.g. ["merge", branch],
    the way src/brothersbe/tasks.py's own _git() is called), never against
    plain substring search: a docstring or comment that merely mentions the
    word "merge" must not trip this, and does not, because neither is a
    List/Tuple AST node."""

    def test_work_module_never_constructs_a_merge_rebase_or_push_argv(self):
        path = os.path.join(ROOT, "src", "brothersbe", "work.py")
        self.assertTrue(os.path.exists(path),
                        "src/brothersbe/work.py does not exist yet; there is nothing to "
                        "grep for the no-merge law against")
        with io.open(path, encoding="utf-8") as fh:
            source = fh.read()
        tree = ast.parse(source, filename=path)
        forbidden = ("merge", "rebase", "push", "deploy")
        hits = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.List, ast.Tuple)) or not node.elts:
                continue
            head = node.elts[0]
            if isinstance(head, ast.Constant) and isinstance(head.value, str):
                word = head.value.lower()
                if word in forbidden:
                    hits.append("%s (line %d)" % (word, node.lineno))
        self.assertEqual(hits, [],
                         "src/brothersbe/work.py constructs git argv starting with a "
                         "forbidden subcommand: %s. sbe work must never merge, rebase onto "
                         "the default branch, push, or deploy." % ", ".join(hits))

    def test_work_module_never_builds_git_argv_head_from_something_unreadable(self):
        """The gap the audit found: the scan above only recognises an
        ast.Constant string sitting directly as the first element of a
        List/Tuple literal. A subcommand built one step removed (string
        concatenation, a helper call, an unresolved variable) is invisible
        to it and must be caught here instead."""
        path = os.path.join(ROOT, "src", "brothersbe", "work.py")
        self.assertTrue(os.path.exists(path),
                        "src/brothersbe/work.py does not exist yet; there is nothing to "
                        "check against the unreviewable-argv law")
        with io.open(path, encoding="utf-8") as fh:
            source = fh.read()
        violations = _find_unreviewable_git_argv(source)
        self.assertEqual(violations, [],
                         "src/brothersbe/work.py builds a git argv head in a way this "
                         "law cannot read statically, so it cannot be reviewed for a "
                         "hidden merge/rebase/push/deploy: %s" % "; ".join(violations))

    def test_calibration_concat_built_merge_argv_is_caught_by_the_unreviewable_law(self):
        """Calibration, per the audit's own mutation: assign a concat-built
        "merge" subcommand to a plain variable and pass that straight to
        _git(...), on a scratch copy of the real file written to a tempdir,
        never on src/brothersbe/work.py itself. The unreviewable-argv check
        must go red for exactly this shape, proving it actually bites rather
        than passing vacuously."""
        real_path = os.path.join(ROOT, "src", "brothersbe", "work.py")
        with io.open(real_path, encoding="utf-8") as fh:
            real_source = fh.read()
        self.assertEqual(_find_unreviewable_git_argv(real_source), [],
                         "calibration precondition failed: the real file must already "
                         "be clean before a mutated scratch copy of it is checked")

        scratch_dir = tempfile.mkdtemp()
        try:
            mutated_source = real_source + (
                "\n\n"
                "def _scratch_mutation_concat_built_merge(root):\n"
                "    sub = 'mer' + 'ge'\n"
                "    argv = [sub, 'origin', 'main']\n"
                "    return _git(argv, root)\n")
            scratch_path = os.path.join(scratch_dir, "work_mutated_scratch_copy.py")
            with io.open(scratch_path, "w", encoding="utf-8") as fh:
                fh.write(mutated_source)
            with io.open(scratch_path, encoding="utf-8") as fh:
                reloaded = fh.read()
            violations = _find_unreviewable_git_argv(reloaded)
        finally:
            shutil.rmtree(scratch_dir, ignore_errors=True)

        self.assertTrue(violations,
                        "calibration failed: a concat-built merge subcommand assigned "
                        "to a variable and passed straight to _git(...) must be caught, "
                        "and it was not; the mutation never went red")
        self.assertTrue(
            any("unreviewable" in v for v in violations),
            "calibration failed: the violation message must say a variable-built git "
            "subcommand is unreviewable by this law: %s" % violations)


if __name__ == "__main__":
    unittest.main(verbosity=2)
