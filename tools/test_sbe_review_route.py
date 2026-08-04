#!/usr/bin/env python3
"""Fixtures for `sbe review-route`. Run: python3 tools/test_sbe_review_route.py

Every test here builds a real git repository in a temporary directory and runs
the real command against it, the same discipline `tools/test_sbe_impact.py`
follows and for the same reason: the defect this control exists for lives at
the seam between a diff and a reviewer choice, and a mocked diff would test
the mock.

Coverage, by class:

  TestSevenPriorities        one fixture per routing rule (1-7), each firing
                              alone, asserting the exact reviewer it selects.
  TestTierSelectionTable      zero triggers is always zero reviewers; T0/T1
                              caps at one even with two triggers firing; T2/T3
                              allows two.
  TestAdversarialCases         the eight cases the routing brief names by name.
  TestNeverClaimsClean         the router's own law: no PASS, ever, and a
                              mechanical-only result still says so honestly.
  TestDeterminismAndRegistry   same diff twice is byte-identical, and the
                              routing table names exactly the seven reviewers
                              this repository ships as agents.
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


class RouteFixture(unittest.TestCase):
    """A fresh repository per test, with one base commit already in it."""

    def setUp(self):
        self.repo = tempfile.mkdtemp()
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "fixture@example.invalid")
        git(self.repo, "config", "user.name", "fixture")
        write(self.repo, "README.md", "base\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "base")
        self.base = git(self.repo, "rev-parse", "HEAD")

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def commit(self, message="change"):
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", message)
        return git(self.repo, "rev-parse", "HEAD")

    def run_route(self, *extra):
        argv = [sys.executable, SBE, "review-route", self.repo, "--base", self.base, "--json"]
        out = subprocess.run(argv + list(extra), capture_output=True, text=True)
        data = json.loads(out.stdout) if out.stdout.strip().startswith("{") else None
        return out.returncode, data, out.stdout + out.stderr

    def write_bad_receipt(self, kind="gate"):
        """A receipt that parses, declares the right kind, and fails its own
        seal check: `_check_seal` in `brothersbe.evidence` recomputes the
        digest over the sealed fields and refuses a mismatch, which is
        exactly the shape a hand-typed or stale receipt takes. Placed at the
        fixed path `sbe status` and `sbe evidence verify` already read."""
        head = git(self.repo, "rev-parse", "HEAD")
        receipt = {
            "schemaVersion": "1.2", "generator": "sbe evidence run", "generatorVersion": "0.0.0",
            "runId": "0" * 64, "argv": ["true"], "argvRedactions": 0,
            "startedAt": "2020-01-01T00:00:00Z", "endedAt": "2020-01-01T00:00:01Z",
            "durationSeconds": 1.0, "exitCode": 0, "headCommit": head,
            "stdoutSha256": "0" * 64, "stderrSha256": "0" * 64, "environment": "test",
            "toolVersions": {"python": "3.9", "sbe": "0.0.0"}, "workingTreeDirty": False,
            "coveredFilesSource": "explicit --covers", "checkKinds": [kind],
            "checkKindsSource": "declared by --kind at generation time: %s" % kind,
            "coveredFiles": [],
        }
        write(self.repo, ".sbe/evidence/%s.json" % kind, json.dumps(receipt))


class TestSevenPriorities(RouteFixture):
    """One fixture per rule, each firing ALONE, so each test pins the exact
    reviewer its own rule selects with nothing else in the diff to confound
    it."""

    def test_rule_1_migration(self):
        # A path-shaped migration hit only: no CREATE/ALTER/DROP keyword in
        # the content, so this stays isolated to the db-migration detector
        # (path alone) and never also trips sql-ddl (content) or this
        # router's own migration-content detector.
        write(self.repo, "migrations/0001_add_users.sql", "-- initial migration, see ADR-12\n")
        self.commit()
        code, data, text = self.run_route()
        self.assertEqual(code, 0, text)
        self.assertEqual(data["primaryReviewer"], "migration-reviewer", text)
        self.assertIsNone(data["secondaryReviewer"], text)

    def test_rule_2_security(self):
        write(self.repo, "config/secret_config.py", "TOKEN = 'placeholder'\n")
        self.commit()
        code, data, text = self.run_route()
        self.assertEqual(code, 0, text)
        self.assertEqual(data["primaryReviewer"], "security-reviewer", text)

    def test_rule_3_data(self):
        write(self.repo, "queries/report.sql", "CREATE VIEW revenue AS SELECT 1;\n")
        self.commit()
        code, data, text = self.run_route()
        self.assertEqual(code, 0, text)
        self.assertEqual(data["primaryReviewer"], "data-reviewer", text)

    def test_rule_4_backend(self):
        write(self.repo, "api/openapi.yaml", "openapi: 3.0.0\npaths:\n  /orders: {}\n")
        self.commit()
        code, data, text = self.run_route()
        self.assertEqual(code, 0, text)
        self.assertEqual(data["primaryReviewer"], "backend-reviewer", text)

    def test_rule_5_infrastructure(self):
        write(self.repo, "infra/main.tf", "resource \"null_resource\" \"x\" {}\n")
        self.commit()
        code, data, text = self.run_route()
        self.assertEqual(code, 0, text)
        self.assertEqual(data["primaryReviewer"], "principal-architect", text)

    def test_rule_6_qa(self):
        """No weakening signal, just a significant test-only diff: 25 fresh
        assertions is enough to cross QA_SIGNIFICANT_LINES on its own."""
        lines = ["import unittest\n", "class T(unittest.TestCase):\n"]
        for i in range(12):
            lines.append("    def test_%d(self):\n        self.assertEqual(%d, %d)\n" % (i, i, i))
        write(self.repo, "tests/test_generated.py", "".join(lines))
        self.commit()
        code, data, text = self.run_route()
        self.assertEqual(code, 0, text)
        self.assertEqual(data["primaryReviewer"], "qa-reviewer", text)
        self.assertEqual(data["tier"], "T0", "a pure test-only diff must not invent a tier "
                         "no impact detector actually raised: %s" % text)

    def test_rule_7_evidence(self):
        self.write_bad_receipt("gate")
        write(self.repo, "README.md", "base\nmore words\n")
        self.commit()
        code, data, text = self.run_route()
        self.assertEqual(code, 0, text)
        self.assertEqual(data["primaryReviewer"], "evidence-auditor", text)


class TestTierSelectionTable(RouteFixture):
    def test_zero_triggers_is_zero_reviewers_at_any_tier(self):
        write(self.repo, "README.md", "base\nan ordinary sentence.\n")
        self.commit()
        code, data, text = self.run_route()
        self.assertEqual(code, 0, text)
        self.assertEqual(data["tier"], "T0", text)
        self.assertIsNone(data["primaryReviewer"], text)
        self.assertIsNone(data["secondaryReviewer"], text)
        self.assertTrue(data["mechanicalOnly"], text)

    def test_t1_caps_at_one_reviewer_even_with_two_triggers(self):
        """`queue-config` (backend, rule 4) and `infrastructure` (rule 5)
        both set the SAME intake answer (`crosses_boundary`), so together
        they still only reach T1, and T1's own cap of one reviewer has to
        win over rule 4's ordinary priority against rule 5: only backend is
        selected, and infrastructure is named lost, not silently dropped."""
        write(self.repo, "src/queue/kafka_consumer.py", "def handle(): pass\n")
        write(self.repo, "infra/main.tf", "resource \"null_resource\" \"x\" {}\n")
        self.commit()
        code, data, text = self.run_route()
        self.assertEqual(code, 0, text)
        self.assertEqual(data["tier"], "T1", text)
        self.assertEqual(data["primaryReviewer"], "backend-reviewer", text)
        self.assertIsNone(data["secondaryReviewer"], text)
        self.assertTrue(
            any("infrastructure" in u["reason"] for u in data["unmeasured"]),
            "the losing trigger must be named in unmeasured, not dropped: %s" % text)

    def test_t2_allows_two_reviewers(self):
        write(self.repo, "api/openapi.yaml", "openapi: 3.0.0\n")
        write(self.repo, "models/revenue.sql", "select 1 as revenue\n")
        self.commit()
        code, data, text = self.run_route()
        self.assertEqual(code, 0, text)
        self.assertEqual(data["tier"], "T2", text)
        self.assertEqual(data["primaryReviewer"], "data-reviewer", text)
        self.assertEqual(data["secondaryReviewer"], "backend-reviewer", text)


class TestAdversarialCases(RouteFixture):
    """The eight cases the routing brief names, one test each, named to match."""

    def test_migration_hidden_in_a_generic_file_name(self):
        write(self.repo, "scripts/cleanup_job.py",
             "def run():\n    execute('ALTER TABLE users ADD COLUMN active BOOLEAN;')\n")
        self.commit()
        code, data, text = self.run_route()
        self.assertEqual(code, 0, text)
        self.assertEqual(data["primaryReviewer"], "migration-reviewer",
                         "a migration hidden in a script must still route to "
                         "migration-reviewer: %s" % text)

    def test_api_contract_removed_rather_than_added(self):
        write(self.repo, "api/openapi.yaml",
             "openapi: 3.0.0\npaths:\n  /orders: {}\n  /refunds: {}\n")
        self.commit()
        base2 = git(self.repo, "rev-parse", "HEAD")
        write(self.repo, "api/openapi.yaml", "openapi: 3.0.0\npaths:\n  /orders: {}\n")
        self.commit("remove refunds endpoint")
        argv = [sys.executable, SBE, "review-route", self.repo, "--base", base2, "--json"]
        out = subprocess.run(argv, capture_output=True, text=True)
        data = json.loads(out.stdout)
        self.assertEqual(data["primaryReviewer"], "backend-reviewer",
                         "removing a contract endpoint must route the same as adding one: %s"
                         % out.stdout)

    def test_sql_embedded_in_python(self):
        write(self.repo, "src/reporting/query.py",
             "def totals(db):\n"
             "    return db.execute(\"SELECT id, total FROM orders WHERE total > 100\")\n")
        self.commit()
        code, data, text = self.run_route()
        self.assertEqual(code, 0, text)
        self.assertEqual(data["primaryReviewer"], "data-reviewer",
                         "SQL embedded in a .py file must route to data-reviewer even though "
                         "the path-only sql-ddl detector requires a .sql extension: %s" % text)

    def test_secret_like_fixture_values(self):
        write(self.repo, "src/config/defaults.py",
             "GITHUB_TOKEN = 'ghp_abcdefghijklmnopqrstuvwxyz012345'\n")
        self.commit()
        code, data, text = self.run_route()
        self.assertEqual(code, 0, text)
        self.assertEqual(data["primaryReviewer"], "security-reviewer",
                         "a secret-shaped value in a normally named file must still route to "
                         "security-reviewer: %s" % text)

    def test_docs_that_change_a_control_promise(self):
        write(self.repo, "docs/SECURITY.md",
             "# Security\nAll requests must be authenticated before reaching the payment "
             "service.\n")
        self.commit()
        base2 = git(self.repo, "rev-parse", "HEAD")
        write(self.repo, "docs/SECURITY.md",
             "# Security\nRequests are typically checked before reaching the payment "
             "service.\n")
        self.commit("soften the security doc")
        argv = [sys.executable, SBE, "review-route", self.repo, "--base", base2, "--json"]
        out = subprocess.run(argv, capture_output=True, text=True)
        data = json.loads(out.stdout)
        self.assertEqual(data["primaryReviewer"], "security-reviewer",
                         "a removed control promise in documentation must route to "
                         "security-reviewer even though impact.py treats .md as quiet: %s"
                         % out.stdout)

    def test_test_only_change_that_weakens_an_assertion(self):
        write(self.repo, "tests/test_orders.py",
             "def test_order_total():\n"
             "    total = compute_total()\n"
             "    assert total == 100\n")
        self.commit()
        base2 = git(self.repo, "rev-parse", "HEAD")
        write(self.repo, "tests/test_orders.py",
             "def test_order_total():\n"
             "    total = compute_total()\n"
             "    # assertion removed during a refactor\n")
        self.commit("weaken the assertion")
        argv = [sys.executable, SBE, "review-route", self.repo, "--base", base2, "--json"]
        out = subprocess.run(argv, capture_output=True, text=True)
        data = json.loads(out.stdout)
        self.assertEqual(data["primaryReviewer"], "qa-reviewer",
                         "a single removed assertion in a test-only diff must still route to "
                         "qa-reviewer, at any size: %s" % out.stdout)

    def test_mixed_backend_and_data_change(self):
        write(self.repo, "api/openapi.yaml", "openapi: 3.0.0\n")
        write(self.repo, "models/revenue.sql", "select 1 as revenue\n")
        self.commit()
        code, data, text = self.run_route()
        self.assertEqual(code, 0, text)
        self.assertEqual(
            sorted([data["primaryReviewer"], data["secondaryReviewer"]]),
            sorted(["backend-reviewer", "data-reviewer"]),
            "a mixed backend and data change must select both, not silently pick one: %s"
            % text)

    def test_three_critical_triggers_and_only_two_reviewer_slots(self):
        write(self.repo, "migrations/0002_add_flag.sql", "ALTER TABLE users ADD COLUMN x INT;\n")
        write(self.repo, "config/secret_keys.py", "KEY = 'placeholder'\n")
        write(self.repo, "reports/kpi.sql", "CREATE VIEW kpi AS SELECT 1;\n")
        self.commit()
        code, data, text = self.run_route()
        self.assertEqual(code, 0, text)
        self.assertEqual(data["primaryReviewer"], "migration-reviewer", text)
        self.assertEqual(data["secondaryReviewer"], "security-reviewer", text)
        self.assertTrue(
            any("data" in u["reason"] and "lost its slot" in u["reason"]
                for u in data["unmeasured"]),
            "the third trigger (data, rule 3) must be named as having lost its slot, never "
            "dropped in silence: %s" % text)


class TestNeverClaimsClean(RouteFixture):
    def test_verdict_is_never_the_gate_vocabulary(self):
        write(self.repo, "README.md", "base\nmore words\n")
        self.commit()
        code, data, text = self.run_route()
        self.assertEqual(code, 0, text)
        self.assertIn(data["verdict"], ("ROUTED", "NO-DATA"), text)
        self.assertNotIn(data["verdict"], ("PASS", "FAIL", "WAIVED", "REVIEW-REQUIRED"), text)

    def test_zero_reviewers_is_a_legal_result_not_an_error(self):
        write(self.repo, "README.md", "base\nmore words\n")
        self.commit()
        code, data, text = self.run_route()
        self.assertEqual(code, 0, text)
        self.assertTrue(data["mechanicalOnly"], text)
        self.assertTrue(
            any("legal result" in r for r in data["reasons"]),
            "a mechanical-only route must say in its own words that zero reviewers is a "
            "legal result, never an unexplained absence: %s" % text)

    def test_no_diff_is_no_data_never_a_crash_or_a_pass(self):
        code, data, text = self.run_route("--base", self.base, "--head", self.base)
        self.assertEqual(code, 0, text)
        self.assertEqual(data["tier"], "T0", text)

    def test_an_unsupported_file_type_is_named_unmeasured(self):
        write(self.repo, "assets/logo.svg", "<svg></svg>\n")
        self.commit()
        code, data, text = self.run_route()
        self.assertEqual(code, 0, text)
        self.assertTrue(
            any(u["file"] == "assets/logo.svg" for u in data["unmeasured"]),
            "a file type nothing here can read must be named by path in unmeasured: %s" % text)


class TestDeterminismAndRegistry(RouteFixture):
    def test_the_same_diff_routes_byte_identical_twice(self):
        write(self.repo, "api/openapi.yaml", "openapi: 3.0.0\n")
        write(self.repo, "migrations/0001_init.sql", "CREATE TABLE users (id INT);\n")
        self.commit()
        argv = [sys.executable, SBE, "review-route", self.repo, "--base", self.base, "--json"]
        first = subprocess.run(argv, capture_output=True, text=True).stdout
        second = subprocess.run(argv, capture_output=True, text=True).stdout
        self.assertEqual(first, second,
                         "the same diff must produce byte-identical output: no clock, no "
                         "random source, no model in the loop")

    def test_every_named_reviewer_is_one_of_the_seven_agent_files(self):
        sys.path.insert(0, os.path.join(ROOT, "src"))
        try:
            from brothersbe import reviewroute as mod
        finally:
            sys.path.pop(0)
        agents_dir = os.path.join(ROOT, "agents")
        on_disk = set(
            fn[:-3] for fn in os.listdir(agents_dir)
            if fn.endswith(".md") and fn != "implementation-worker.md")
        self.assertEqual(set(mod.REVIEWER_NAMES), on_disk,
                         "REVIEWER_NAMES must name exactly the reviewer agents on disk, "
                         "no more and no fewer")
        self.assertEqual(set(mod.REVIEWER_OF_TRIGGER.values()), set(mod.REVIEWER_NAMES),
                         "every reviewer the routing table can select must be one of the "
                         "seven; adding an eighth is one row in TRIGGER_RULES, never a "
                         "second table")

    def test_a_disposable_work_profile_is_recorded_but_never_decides(self):
        """`--work-profile` is accepted for provenance only: the same diff
        with and without it must select the same reviewers."""
        write(self.repo, "api/openapi.yaml", "openapi: 3.0.0\n")
        self.commit()
        _c1, plain, _t1 = self.run_route()
        _c2, profiled, _t2 = self.run_route("--work-profile", "backend")
        self.assertEqual(plain["primaryReviewer"], profiled["primaryReviewer"])
        self.assertEqual(plain["secondaryReviewer"], profiled["secondaryReviewer"])
        self.assertTrue(any("workProfile" in r for r in profiled["reasons"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
