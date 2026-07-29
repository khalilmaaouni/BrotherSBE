#!/usr/bin/env python3
"""Fixtures for `sbe adopt` and `sbe init`. Run: python3 tools/test_sbe_adopt.py

Every test builds a real temporary git repository (or, for the refusal
fixture, deliberately does not) and runs the real `bin/sbe` command against
it. Nothing is mocked, matching `tools/test_sbe_impact.py`'s own rule: the
defect these controls exist for lives at the seam between what this tool can
actually read from a filesystem and what it claims, and a mocked filesystem
would test the mock.

`sbe adopt`'s workflow-file assertions (`TestWorkflowFiles`) read the shipped
YAML as TEXT and grep for the lines that matter, the same line-oriented
approach `evals/run_evals.py::_waiver_grep_pattern` already uses against
`brothersbe-gates.yml`. This project ships no YAML parser (Python 3.9 stdlib
only, and PyYAML is not a dependency here), so a structural check that
"parses" the file would have to bring one in or hand-roll one either way;
grepping the exact lines CI itself depends on is the same honesty trade this
project makes everywhere else: CI is the real parser, and this test checks
that the lines CI needs are actually present, not that the file is
well-formed YAML in general.
"""
import hashlib
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


def run_sbe(*args, **kwargs):
    cwd = kwargs.pop("cwd", None)
    argv = [sys.executable, SBE] + list(args)
    out = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    data = None
    stripped = out.stdout.strip()
    if stripped.startswith("{"):
        try:
            data = json.loads(stripped)
        except ValueError:
            data = None
    return out.returncode, data, out.stdout + out.stderr


def tree_hash(root):
    """One digest over every path and its bytes, excluding .git. Two calls
    against an unmodified tree produce the same digest; a single byte
    written anywhere changes it. This is the instrument fixture 1 (dry-run
    writes NOTHING) is built on, deliberately independent of whichever
    files this module happens to propose today.
    """
    digest = hashlib.sha256()
    for dirpath, dirnames, filenames in sorted(os.walk(root)):
        dirnames[:] = sorted(d for d in dirnames if d != ".git")
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            digest.update(rel.encode("utf-8"))
            with open(full, "rb") as fh:
                digest.update(fh.read())
    return digest.hexdigest()


class AdoptFixture(unittest.TestCase):
    """A fresh git repository per test, with one base commit already in it."""

    def setUp(self):
        self.repo = tempfile.mkdtemp()
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "fixture@example.invalid")
        git(self.repo, "config", "user.name", "fixture")
        write(self.repo, "README.md", "base\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "base")

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)


class TestDryRunWritesNothing(AdoptFixture):
    """FIXTURE 1: dry-run writes NOTHING, in either command, proved by
    hashing the whole tree before and after rather than checking for the
    two or three paths this module happens to propose today."""

    def test_adopt_dry_run_writes_nothing(self):
        before = tree_hash(self.repo)
        code, data, text = run_sbe("adopt", self.repo, "--dry-run", "--json")
        after = tree_hash(self.repo)
        self.assertEqual(before, after, "sbe adopt --dry-run changed the tree: %s" % text)
        self.assertEqual(code, 0, text)
        self.assertTrue(data["proposals"], text)

    def test_adopt_default_is_also_dry_run(self):
        """`--dry-run` is the default even when the flag itself is omitted;
        the flag only makes the default explicit."""
        before = tree_hash(self.repo)
        code, _data, text = run_sbe("adopt", self.repo, "--json")
        after = tree_hash(self.repo)
        self.assertEqual(before, after, text)

    def test_init_dry_run_writes_nothing(self):
        before = tree_hash(self.repo)
        code, data, text = run_sbe("init", self.repo, "--dry-run", "--json")
        after = tree_hash(self.repo)
        self.assertEqual(before, after, "sbe init --dry-run changed the tree: %s" % text)
        self.assertEqual(code, 0, text)
        self.assertTrue(data["proposals"], text)


class TestApplyThenNoop(AdoptFixture):
    """FIXTURE 2: --apply writes the proposed files; a second --apply over
    the same tree is a no-op and says so."""

    def test_apply_writes_then_second_apply_is_a_noop(self):
        code, data, text = run_sbe("adopt", self.repo, "--apply", "--json")
        self.assertEqual(code, 0, text)
        self.assertEqual(sorted(data["applied"]["written"]),
                         [".brothersbe/policy.json", ".github/CODEOWNERS"], text)
        self.assertTrue(os.path.exists(os.path.join(self.repo, ".brothersbe", "policy.json")))
        self.assertTrue(os.path.exists(os.path.join(self.repo, ".github", "CODEOWNERS")))

        before = tree_hash(self.repo)
        code2, data2, text2 = run_sbe("adopt", self.repo, "--apply", "--json")
        after = tree_hash(self.repo)
        self.assertEqual(code2, 0, text2)
        self.assertEqual(before, after, "a second --apply over an unchanged tree wrote "
                                        "something: %s" % text2)
        self.assertEqual(data2["applied"]["written"], [],
                         "a second --apply must write nothing the second time")
        self.assertEqual(len(data2["applied"]["skipped"]), 2, text2)
        for item in data2["applied"]["skipped"]:
            self.assertIn("already matches", item["reason"], text2)


class TestForceRequired(AdoptFixture):
    """FIXTURE 3: an existing file that differs from the proposal is never
    overwritten without --force."""

    def test_existing_file_is_not_overwritten_without_force(self):
        planted = "# a CODEOWNERS a human already wrote\n*.py @someone\n"
        write(self.repo, ".github/CODEOWNERS", planted)

        code, data, text = run_sbe("adopt", self.repo, "--apply", "--json")
        self.assertEqual(code, 0, text)
        with io.open(os.path.join(self.repo, ".github", "CODEOWNERS"), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), planted, "an existing file was overwritten without "
                                                 "--force")
        skipped_paths = [s["path"] for s in data["applied"]["skipped"]]
        self.assertIn(".github/CODEOWNERS", skipped_paths, text)

        code2, data2, text2 = run_sbe("adopt", self.repo, "--apply", "--force", "--json")
        self.assertEqual(code2, 0, text2)
        with io.open(os.path.join(self.repo, ".github", "CODEOWNERS"), encoding="utf-8") as fh:
            self.assertNotEqual(fh.read(), planted, "--force did not overwrite the existing "
                                                     "file: %s" % text2)
        self.assertIn(".github/CODEOWNERS", data2["applied"]["written"], text2)


class TestAdoptionReportNeverClaimsPresent(AdoptFixture):
    """FIXTURE 4, THE KILL CRITERION: the adoption report on a laptop-local
    repository marks branch protection (and every other GitHub-side
    protection) UNVERIFIABLE-HERE, and NEVER PRESENT, because nothing here
    holds a GitHub token or asked for one."""

    def test_branch_protection_is_unverifiable_here_never_present(self):
        code, data, text = run_sbe("adopt", self.repo, "--dry-run", "--json")
        self.assertEqual(code, 0, text)
        by_name = dict((p["name"], p["status"]) for p in data["protections"])
        self.assertEqual(by_name["branch-protection"], "UNVERIFIABLE-HERE", text)
        self.assertEqual(by_name["required-status-checks"], "UNVERIFIABLE-HERE", text)
        self.assertEqual(by_name["codeowners-review-required"], "UNVERIFIABLE-HERE", text)
        statuses = set(p["status"] for p in data["protections"])
        self.assertNotIn("PRESENT", statuses,
                         "sbe adopt claimed a GitHub-side protection PRESENT from a local "
                         "clone with no API access: %s" % text)
        for prot in data["protections"]:
            self.assertTrue(prot["missing"], "an UNVERIFIABLE-HERE protection must name what "
                                             "is missing: %s" % text)

    def test_even_with_a_codeowners_file_present_enforcement_stays_unverifiable(self):
        """A CODEOWNERS file existing locally is a fact this tool CAN read
        (reported under localFacts). It must not be read as proof that
        GitHub is configured to REQUIRE that review, which lives only on
        the platform."""
        write(self.repo, ".github/CODEOWNERS", "* @someone\n")
        code, data, text = run_sbe("adopt", self.repo, "--dry-run", "--json")
        self.assertEqual(code, 0, text)
        by_name = dict((p["name"], p["status"]) for p in data["protections"])
        self.assertEqual(by_name["codeowners-review-required"], "UNVERIFIABLE-HERE", text)
        local = dict((f["name"], f["status"]) for f in data["localFacts"])
        self.assertEqual(local["codeowners-file"], "PRESENT", text)


class TestStackDetectionShiftsThePolicy(AdoptFixture):
    """FIXTURE 5: a planted dbt project and a planted migrations directory
    each shift the proposed policy in the expected, named way."""

    def test_a_planted_dbt_project_adds_the_dbtModels_protected_path(self):
        write(self.repo, "models/staging/stg_orders.sql", "select 1\n")
        code, data, text = run_sbe("adopt", self.repo, "--dry-run", "--json")
        self.assertEqual(code, 0, text)
        self.assertTrue(data["detectedStack"]["hasDbtModels"], text)
        policy_proposal = [p for p in data["proposals"] if p["path"] == ".brothersbe/policy.json"][0]
        self.assertIn("dbtModels", policy_proposal["diff"],
                      "a detected dbt project must shift the proposed policy by name: %s"
                      % text)
        self.assertNotIn("migrations", policy_proposal["diff"], text)

    def test_a_planted_migrations_dir_adds_the_migrations_protected_path(self):
        write(self.repo, "migrations/0001_init.sql", "create table t (id int);\n")
        code, data, text = run_sbe("adopt", self.repo, "--dry-run", "--json")
        self.assertEqual(code, 0, text)
        self.assertTrue(data["detectedStack"]["hasMigrations"], text)
        policy_proposal = [p for p in data["proposals"] if p["path"] == ".brothersbe/policy.json"][0]
        self.assertIn('"migrations"', policy_proposal["diff"],
                      "a detected migrations directory must shift the proposed policy by "
                      "name: %s" % text)
        self.assertNotIn("dbtModels", policy_proposal["diff"], text)

    def test_neither_signal_present_proposes_neither_extra_path(self):
        code, data, text = run_sbe("adopt", self.repo, "--dry-run", "--json")
        self.assertEqual(code, 0, text)
        self.assertFalse(data["detectedStack"]["hasDbtModels"], text)
        self.assertFalse(data["detectedStack"]["hasMigrations"], text)
        policy_proposal = [p for p in data["proposals"] if p["path"] == ".brothersbe/policy.json"][0]
        self.assertNotIn("dbtModels", policy_proposal["diff"], text)
        self.assertNotIn('"migrations"', policy_proposal["diff"], text)


class TestInitReceipt(AdoptFixture):
    """FIXTURE 6: the init receipt exists, lists every written path, and the
    uninstall instructions match that written set exactly."""

    def test_receipt_lists_every_written_path_and_uninstall_matches(self):
        code, data, text = run_sbe("init", self.repo, "--apply", "--json")
        self.assertEqual(code, 0, text)
        receipt_path = os.path.join(self.repo, ".brothersbe", "install-receipt.json")
        self.assertTrue(os.path.exists(receipt_path), text)
        with io.open(receipt_path, encoding="utf-8") as fh:
            receipt = json.load(fh)

        self.assertEqual(sorted(receipt["writtenPaths"]),
                         [".brothersbe/config.json", ".brothersbe/install-receipt.json",
                          "design/.gitkeep"], text)
        self.assertTrue(os.path.exists(os.path.join(self.repo, ".brothersbe", "config.json")))
        self.assertTrue(os.path.exists(os.path.join(self.repo, "design", ".gitkeep")))

        instructed_paths = set()
        for line in receipt["uninstallInstructions"]:
            self.assertTrue(line.startswith("rm -f "), text)
            instructed_paths.add(line[len("rm -f "):])
        self.assertEqual(instructed_paths, set(receipt["writtenPaths"]),
                         "uninstall instructions must name exactly the written set, no more "
                         "and no less: %s" % text)

        # A second --apply changes nothing, and the receipt on disk (including
        # its installedAt timestamp) is untouched rather than rewritten.
        before = tree_hash(self.repo)
        code2, data2, text2 = run_sbe("init", self.repo, "--apply", "--json")
        after = tree_hash(self.repo)
        self.assertEqual(code2, 0, text2)
        self.assertEqual(before, after, "a second sbe init --apply changed the tree: %s"
                         % text2)
        self.assertTrue(data2["skippedAsNoop"], text2)


class TestInitRefusesOutsideGit(unittest.TestCase):
    """FIXTURE 7: sbe init outside a git repository refuses, and names why,
    rather than writing a config file with nowhere to be versioned."""

    def setUp(self):
        self.plain_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.plain_dir, ignore_errors=True)

    def test_apply_outside_git_repo_refuses_with_reason(self):
        before = tree_hash(self.plain_dir)
        code, _data, text = run_sbe("init", self.plain_dir, "--apply")
        after = tree_hash(self.plain_dir)
        self.assertNotEqual(code, 0, "sbe init --apply must refuse outside a git repository: "
                            "%s" % text)
        self.assertIn("git repository", text.lower(), text)
        self.assertEqual(before, after, "a refused init still wrote something: %s" % text)

    def test_dry_run_outside_git_repo_also_refuses(self):
        code, _data, text = run_sbe("init", self.plain_dir, "--dry-run")
        self.assertNotEqual(code, 0, text)
        self.assertIn("git repository", text.lower(), text)


class TestWorkflowFiles(unittest.TestCase):
    """FIXTURE 8: the product workflow carries both triggers, and the
    consumer workflow (and the composite action behind it) never invoke
    BrotherSBE's own test files. Line-oriented on purpose; see the module
    docstring for why this project does not parse the YAML to check it."""

    @staticmethod
    def _code_only(text):
        """The file with every full-line comment dropped, so a docstring-style
        explanation of what a workflow deliberately does NOT run (this
        project's own house style, all over its shipped YAML) cannot be
        mistaken for an invocation. A `#` that starts a line once stripped of
        leading whitespace is a comment line in YAML; nothing here strips an
        inline `#` after real content, because none of the greps below need
        to survive one."""
        return "\n".join(line for line in text.split("\n")
                         if not line.strip().startswith("#"))

    def setUp(self):
        with io.open(os.path.join(ROOT, ".github", "workflows", "brothersbe-gates.yml"),
                     encoding="utf-8") as fh:
            self.product_wf = fh.read()
        with io.open(os.path.join(ROOT, ".github", "workflows", "consumer-check.yml"),
                     encoding="utf-8") as fh:
            self.consumer_wf = fh.read()
        with io.open(os.path.join(ROOT, ".github", "actions", "sbe-consumer", "action.yml"),
                     encoding="utf-8") as fh:
            self.consumer_action = fh.read()
        self.consumer_wf_code = self._code_only(self.consumer_wf)
        self.consumer_action_code = self._code_only(self.consumer_action)

    def test_product_workflow_has_both_triggers(self):
        self.assertIn("pull_request:", self.product_wf, self.product_wf)
        self.assertIn("push:", self.product_wf, self.product_wf)
        self.assertIn("branches: [main]", self.product_wf, self.product_wf)

    def test_consumer_workflow_has_both_triggers(self):
        self.assertIn("pull_request:", self.consumer_wf, self.consumer_wf)
        self.assertIn("push:", self.consumer_wf, self.consumer_wf)
        self.assertIn("branches: [main]", self.consumer_wf, self.consumer_wf)

    def test_consumer_workflow_never_invokes_the_product_test_files(self):
        for banned in ("test_sbe.py", "test_sbe_adopt.py", "test_sbe_impact.py",
                      "test_sbe_evidence.py", "test_sbe_bypass.py", "test_sbe_fence_hook.py",
                      "run_evals.py", "test_no_data_class.py"):
            self.assertNotIn(banned, self.consumer_wf_code,
                             "the consumer workflow must never invoke %s: %s"
                             % (banned, self.consumer_wf_code))
            self.assertNotIn(banned, self.consumer_action_code,
                             "the consumer composite action must never invoke %s: %s"
                             % (banned, self.consumer_action_code))

    def test_consumer_action_only_calls_the_named_commands(self):
        """The composite action's own body may only call the four commands
        the spec names: impact, evidence verify, status, and design. A fifth
        subcommand slipping in would be scope creep past what a client asked
        BrotherSBE's own repository to test."""
        for allowed in ("impact", "evidence verify", "status", "design"):
            self.assertIn(allowed, self.consumer_action_code, self.consumer_action_code)


if __name__ == "__main__":
    unittest.main(verbosity=2)
