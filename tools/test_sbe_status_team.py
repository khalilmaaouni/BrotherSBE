"""Adversarial fixtures for `sbe status --team` (spec:
docs/specs/2026-07-30-sbe-status-team.md). Written BEFORE the implementation:
on the day this landed, every scenario was red because the status subcommand
had no --team flag, and none was red on a fixture bug.

Every fixture builds its own throwaway git repository with one or more
dossiers under design/, each seeded through the real `sbe plan --write`, so
the team view is always read over artifacts the real tools produced.
"""
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SBE = os.path.join(HERE, "..", "bin", "sbe")

INTAKE = {
    "answers": {"changes_contract": "n", "crosses_boundary": "n",
                "reversible_under_hour": "y", "touches_sensitive": "n",
                "consumers": "none"},
    "tier": "T1", "override": None, "override_reason": None,
}

ADR_TEMPLATE = """# ADR
## Context
x
## Decision
Serve the change from `%s`.
## Consequences
ok
"""

VERIFICATION = """| Claim this design makes | The check that proves it | When it runs |
|---|---|---|
| it answers | `python3 -c pass` | CI |
"""


def _run(argv, cwd=None, env=None):
    out = subprocess.run(argv, capture_output=True, text=True, cwd=cwd, env=env,
                         stdin=subprocess.DEVNULL, timeout=120)
    # Three values, not two: a two-value return reads as a possible
    # (verdict, evidence) pair to the honesty meta-test, which refuses any
    # such function sitting outside a check registry.
    return out.returncode, out.stdout + out.stderr, out.stderr


class TeamScenario(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sbe-team-")
        self.repo = os.path.join(self.tmp, "repo")
        os.makedirs(self.repo)
        self.git("init", "-q")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "user.name", "fixture")
        io.open(os.path.join(self.repo, "seed.txt"), "w").write("seed\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "seed")

    def tearDown(self):
        reg = os.path.join(self.repo, ".sbe", "tasks.json")
        if os.path.exists(reg):
            os.chmod(reg, stat.S_IRUSR | stat.S_IWUSR)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def git(self, *args):
        code, text, _err = _run(["git", "-C", self.repo] + list(args))
        self.assertEqual(code, 0, "git %s failed: %s" % (args, text))
        return text

    def sbe(self, *args):
        return _run([sys.executable, SBE] + list(args))

    def team(self, *extra):
        code, text, err = self.sbe("status", self.repo, "--team", *extra)
        if "unrecognized arguments" in text:
            self.fail("sbe status has no --team flag yet: %s" % text.strip())
        return code, text, err

    def _change(self, name, src_rel):
        doss = os.path.join(self.repo, "design", name)
        os.makedirs(doss)
        io.open(os.path.join(doss, "00-intake.json"), "w").write(
            json.dumps(INTAKE, indent=2))
        io.open(os.path.join(doss, "03-adr.md"), "w").write(ADR_TEMPLATE % src_rel)
        io.open(os.path.join(doss, "07-verification.md"), "w").write(VERIFICATION)
        src = os.path.join(self.repo, src_rel)
        parent = os.path.dirname(src)
        if parent and not os.path.isdir(parent):
            os.makedirs(parent)
        io.open(src, "w").write("x = 1\n")
        code, text, _ = self.sbe("plan", doss, "--write", "--cwd", self.repo)
        self.assertEqual(code, 0, "plan --write for %s: %s" % (name, text))
        return doss

    def _open_record(self, task_id, owns, agent="alice"):
        """Seed an open registry record directly, the same technique the
        registry's own suite uses for states only real runs could otherwise
        produce."""
        reg_dir = os.path.join(self.repo, ".sbe")
        if not os.path.isdir(reg_dir):
            os.makedirs(reg_dir)
        reg = os.path.join(reg_dir, "tasks.json")
        data = {"schemaVersion": "1.0", "tasks": []}
        if os.path.exists(reg):
            data = json.loads(io.open(reg).read())
        data["tasks"].append({
            "id": task_id, "agent": agent, "role": "writer", "worktree": None,
            "ownedPaths": owns, "readOnlyPaths": [], "baseCommit": None,
            "expiry": None, "status": "open", "verifyCommand": "python3 -c pass",
            "evidenceId": None, "openedAt": "2026-07-30T00:00:00Z", "closedAt": None,
        })
        io.open(reg, "w").write(json.dumps(data, indent=2))

    def _forced_record(self, task_id):
        reg_dir = os.path.join(self.repo, ".sbe")
        if not os.path.isdir(reg_dir):
            os.makedirs(reg_dir)
        reg = os.path.join(reg_dir, "tasks.json")
        data = {"schemaVersion": "1.0", "tasks": []}
        if os.path.exists(reg):
            data = json.loads(io.open(reg).read())
        data["tasks"].append({
            "id": task_id, "agent": "bob", "role": "writer", "worktree": None,
            "ownedPaths": ["src/x.py"], "readOnlyPaths": [], "baseCommit": None,
            "expiry": None, "status": "closed-forced", "verifyCommand": "",
            "evidenceId": None, "openedAt": "2026-07-30T00:00:00Z",
            "closedAt": "2026-07-30T01:00:00Z", "forced": True,
        })
        io.open(reg, "w").write(json.dumps(data, indent=2))


class TestDiscoveryAndOrdering(TeamScenario):
    def test_two_changes_are_listed_together_each_with_a_next_action(self):
        self._change("chg-a", "src/a.py")
        self._change("chg-b", "src/b.py")
        code, text, _ = self.team()
        self.assertIn("chg-a", text)
        self.assertIn("chg-b", text)
        self.assertGreaterEqual(text.count("next action"), 2, text)

    def test_the_human_output_is_deterministic(self):
        self._change("chg-a", "src/a.py")
        self._change("chg-b", "src/b.py")
        _code, first, _ = self.team()
        _code, second, _ = self.team()
        self.assertEqual(first, second, "no timestamps, no ordering jitter")

    def test_a_missing_plan_names_sbe_plan_as_the_next_action_not_an_error(self):
        doss = os.path.join(self.repo, "design", "bare")
        os.makedirs(doss)
        io.open(os.path.join(doss, "00-intake.json"), "w").write(
            json.dumps(INTAKE, indent=2))
        code, text, _ = self.team()
        self.assertEqual(code, 0, text)
        self.assertIn("sbe plan", text)


class TestConflictsAndForced(TeamScenario):
    def test_overlapping_open_tasks_across_changes_is_a_scope_conflict_naming_both(self):
        self._change("chg-a", "src/shared.py")
        self._change("chg-b", "src/b.py")
        self._open_record("T01", ["src/shared.py"], agent="alice")
        self._open_record("T90", ["src/shared.py"], agent="bob")
        code, text, _ = self.team()
        self.assertEqual(code, 1, text)
        self.assertIn("src/shared.py", text)
        self.assertIn("alice", text)
        self.assertIn("bob", text)

    def test_a_forced_closure_prints_forced_in_the_team_view(self):
        self._change("chg-a", "src/a.py")
        self._forced_record("T01")
        _code, text, _ = self.team()
        self.assertIn("FORCED", text)


class TestEvidenceAndConvergence(TeamScenario):
    def test_a_plan_with_no_convergence_report_is_no_data_at_severity_six_not_pass(self):
        self._change("chg-a", "src/a.py")
        code, text, _ = self.team()
        self.assertEqual(code, 1, "an unexamined convergence must block: %s" % text)
        self.assertIn("sbe converge", text)
        self.assertNotIn("convergence PASS", text)

    def test_a_stale_approval_report_is_derived_not_observed(self):
        doss = self._change("chg-a", "src/a.py")
        io.open(os.path.join(doss, "10-approval.json"), "w").write(json.dumps({
            "tool": "sbe pr verify", "repository": "example/repo", "number": 1,
            "headSha": "0" * 40, "final": "PASS", "controls": []}))
        _code, _text, _ = self.team()
        code, text, _ = self.team("--json")
        data = json.loads(text[text.index("{"):])
        stale = [f for f in data["findings"]
                 if f["change"] == "chg-a" and "approval" in f["evidence"].lower()
                 and f["basis"] == "derived"]
        self.assertTrue(stale, "an approval bound to another sha must surface as a "
                               "derived staleness finding: %s" % text)


class TestJsonContractAndExit(TeamScenario):
    def test_every_finding_carries_the_full_contract(self):
        self._change("chg-a", "src/a.py")
        code, text, _ = self.team("--json")
        data = json.loads(text[text.index("{"):])
        self.assertTrue(data["findings"], "a change with a plan yields findings")
        for f in data["findings"]:
            for key in ("change", "severity", "verdict", "evidence", "commit",
                        "owner", "nextAction", "basis"):
                self.assertIn(key, f, "finding missing %s: %s" % (key, f))
            self.assertIn(f["basis"], ("observed", "derived", "unavailable"))
            self.assertTrue(1 <= int(f["severity"]) <= 10, f)
        sevs = [int(f["severity"]) for f in data["findings"]]
        self.assertEqual(sevs, sorted(sevs), "most severe first, deterministic")

    def test_a_tree_with_only_low_severity_findings_exits_zero(self):
        doss = os.path.join(self.repo, "design", "bare")
        os.makedirs(doss)
        io.open(os.path.join(doss, "00-intake.json"), "w").write(
            json.dumps(INTAKE, indent=2))
        code, text, _ = self.team()
        self.assertEqual(code, 0, text)

    def test_an_unreadable_registry_is_an_unavailable_finding_and_a_nonzero_exit(self):
        self._change("chg-a", "src/a.py")
        self._open_record("T01", ["src/a.py"])
        reg = os.path.join(self.repo, ".sbe", "tasks.json")
        os.chmod(reg, 0)
        try:
            code, text, _ = self.team("--json")
            self.assertEqual(code, 1, text)
            data = json.loads(text[text.index("{"):])
            unavailable = [f for f in data["findings"] if f["basis"] == "unavailable"]
            self.assertTrue(unavailable,
                            "an unreadable registry must surface, not vanish: %s" % text)
        finally:
            os.chmod(reg, stat.S_IRUSR | stat.S_IWUSR)

    def test_team_makes_no_network_calls_by_construction(self):
        body = io.open(os.path.join(HERE, "..", "src", "brothersbe",
                                    "status.py"), encoding="utf-8").read()
        for needle in ("urllib", "http.client", "socket", "api.github.com"):
            self.assertNotIn(needle, body,
                             "status must read the estate, never the network")


if __name__ == "__main__":
    unittest.main(verbosity=2)
