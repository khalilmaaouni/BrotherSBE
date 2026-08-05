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

    def handover(self, *args):
        """LT-302.B fixtures build real `12-handover.json` records through
        the real `sbe handover` engine (mirroring `tools/test_sbe_handover.py`'s
        own `HandoverScenario.handover`), never a hand-typed JSON stand-in."""
        return self.sbe("handover", *args)

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

    def _open_record(self, task_id, owns, agent="alice", base_commit=None):
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
            "ownedPaths": owns, "readOnlyPaths": [], "baseCommit": base_commit,
            "expiry": None, "status": "open", "verifyCommand": "python3 -c pass",
            "evidenceId": None, "openedAt": "2026-07-30T00:00:00Z", "closedAt": None,
        })
        io.open(reg, "w").write(json.dumps(data, indent=2))

    def _closed_record(self, task_id, owns, agent="alice", base_commit=None,
                       forced=False):
        """A CLOSED (clean, unless forced) registry record for a task id, the
        completed-task counterpart to `_open_record`."""
        reg_dir = os.path.join(self.repo, ".sbe")
        if not os.path.isdir(reg_dir):
            os.makedirs(reg_dir)
        reg = os.path.join(reg_dir, "tasks.json")
        data = {"schemaVersion": "1.0", "tasks": []}
        if os.path.exists(reg):
            data = json.loads(io.open(reg).read())
        record = {
            "id": task_id, "agent": agent, "role": "writer", "worktree": None,
            "ownedPaths": owns, "readOnlyPaths": [], "baseCommit": base_commit,
            "expiry": None, "status": "closed", "verifyCommand": "python3 -c pass",
            "evidenceId": None, "openedAt": "2026-07-30T00:00:00Z",
            "closedAt": "2026-07-30T01:00:00Z",
        }
        if forced:
            record["forced"] = {"who": "bob", "why": "test"}
        data["tasks"].append(record)
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

    def test_designRoots_profile_adds_a_second_directory_of_dossiers(self):
        # F2: a second, in-repo directory named by .sbe/team-profile.json
        # holds its own dossier, and both changes are discovered together.
        self._change("chg-a", "src/a.py")
        alt_root = os.path.join(self.repo, "other-designs")
        doss = os.path.join(alt_root, "chg-alt")
        os.makedirs(doss)
        io.open(os.path.join(doss, "00-intake.json"), "w").write(
            json.dumps(INTAKE, indent=2))
        sbe_dir = os.path.join(self.repo, ".sbe")
        if not os.path.isdir(sbe_dir):
            os.makedirs(sbe_dir)
        io.open(os.path.join(sbe_dir, "team-profile.json"), "w").write(
            json.dumps({"designRoots": ["other-designs"]}))
        code, text, _ = self.team()
        self.assertIn("chg-a", text)
        self.assertIn("chg-alt", text, "a designRoots entry must be discovered too: %s"
                                       % text)

    def test_a_designRoots_entry_escaping_the_repo_is_refused_and_not_walked(self):
        # M3: containment. An entry resolving outside the repository root
        # (here via ..) is REFUSED by name and its dossier never surfaces.
        self._change("chg-a", "src/a.py")
        outside = os.path.join(self.tmp, "outside")
        doss = os.path.join(outside, "chg-outside")
        os.makedirs(doss)
        io.open(os.path.join(doss, "00-intake.json"), "w").write(
            json.dumps(INTAKE, indent=2))
        sbe_dir = os.path.join(self.repo, ".sbe")
        if not os.path.isdir(sbe_dir):
            os.makedirs(sbe_dir)
        io.open(os.path.join(sbe_dir, "team-profile.json"), "w").write(
            json.dumps({"designRoots": ["../outside"]}))
        code, text, err = self.team("--json")
        self.assertNotIn("chg-outside", text,
                         "an escaping designRoots entry must never be walked: %s" % text)
        data = json.loads(text[text.index("{"):])
        refusals = [f for f in data["findings"]
                   if f["basis"] == "unavailable" and "../outside" in f["evidence"]]
        self.assertTrue(refusals, "the escaping entry must be REFUSED by name, not "
                                 "silently dropped: %s" % text)
        self.assertIn("chg-a", data["changes"])
        self.assertNotIn("chg-outside", data["changes"])


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


class TestFullSeveritySet(TeamScenario):
    """F9: severities 2 (merge blockers), 8 (ready tasks), 9 (completed
    changes) and 10 (next action, always exactly one per change)."""

    def test_an_open_tasks_scope_violation_is_a_severity_two_merge_blocker(self):
        doss = self._change("chg-a", "src/a.py")
        self.git("add", "-A")
        self.git("commit", "-qm", "chg-a dossier and source")
        head = self.git("rev-parse", "HEAD").strip()
        self._open_record("T01", ["src/a.py"], agent="alice", base_commit=head)
        io.open(os.path.join(self.repo, "src", "extra.py"), "w").write("y = 2\n")
        code, text, _ = self.team("--json")
        self.assertEqual(code, 1, text)
        data = json.loads(text[text.index("{"):])
        hits = [f for f in data["findings"]
               if f["change"] == "chg-a" and f["severity"] == 2
               and "src/extra.py" in f["detail"]]
        self.assertTrue(hits, "an out-of-scope change on an open task must surface as a "
                              "severity 2 merge blocker naming the path: %s" % text)
        self.assertEqual(hits[0]["verdict"], "FAIL", hits[0])
        self.assertEqual(hits[0]["basis"], "observed", hits[0])

    def test_a_failing_evidence_receipt_is_a_severity_two_merge_blocker_attributed(self):
        self._change("chg-a", "src/a.py")
        # A receipt generated over a dirty tree is only ever NO-DATA (advisory)
        # per evidence.verify(); commit first so the exit code can be trusted.
        self.git("add", "-A")
        self.git("commit", "-qm", "chg-a dossier and source")
        out = os.path.join(self.repo, ".sbe", "evidence", "fail.json")
        code, text, _ = self.sbe(
            "evidence", "run", "--out", out, "--cwd", self.repo, "--covers", "src/a.py",
            "--", sys.executable, "-c", "import sys; sys.exit(1)")
        self.assertEqual(code, 1, "the fixture command must fail to earn a failing "
                                  "receipt: %s" % text)
        code, text, _ = self.team("--json")
        self.assertEqual(code, 1, text)
        data = json.loads(text[text.index("{"):])
        hits = [f for f in data["findings"] if f["severity"] == 2
               and "fail.json" in f["evidence"]]
        self.assertTrue(hits, "a failing receipt must surface as a severity 2 merge "
                              "blocker: %s" % text)
        self.assertEqual(hits[0]["change"], "chg-a",
                         "a receipt covering src/a.py must attribute to the change whose "
                         "plan owns src/a.py, not the shared bucket: %s" % text)

    def test_a_fresh_plan_lists_its_tasks_as_ready_with_no_open_record(self):
        self._change("chg-a", "src/a.py")
        code, text, _ = self.team("--json")
        data = json.loads(text[text.index("{"):])
        ready = [f for f in data["findings"]
                if f["change"] == "chg-a" and f["severity"] == 8]
        self.assertTrue(ready, "a fresh plan's tasks with no registry record must list "
                              "as ready: %s" % text)
        ids = {f["evidence"] for f in ready}
        self.assertIn("task T01", ids, text)

    def test_every_plan_task_closed_clean_is_a_completed_change(self):
        self._change("chg-a", "src/a.py")
        self._closed_record("T01", ["src/a.py"], agent="alice")
        self._closed_record("T02", [], agent="alice")
        code, text, _ = self.team("--json")
        data = json.loads(text[text.index("{"):])
        completed = [f for f in data["findings"]
                    if f["change"] == "chg-a" and f["severity"] == 9]
        self.assertTrue(completed, "every plan task closed clean must surface as a "
                                  "completed change: %s" % text)
        self.assertEqual(completed[0]["verdict"], "PASS", completed[0])
        ready = [f for f in data["findings"]
                if f["change"] == "chg-a" and f["severity"] == 8]
        self.assertFalse(ready, "a task with a closed record is not a ready task: %s"
                                % text)

    def test_a_forced_close_never_counts_as_completed(self):
        self._change("chg-a", "src/a.py")
        self._closed_record("T01", ["src/a.py"], agent="alice", forced=True)
        self._closed_record("T02", [], agent="alice")
        code, text, _ = self.team("--json")
        data = json.loads(text[text.index("{"):])
        completed = [f for f in data["findings"]
                    if f["change"] == "chg-a" and f["severity"] == 9]
        self.assertFalse(completed, "a FORCED close never satisfies completion: %s" % text)

    def test_every_change_carries_exactly_one_severity_ten_next_action(self):
        self._change("chg-a", "src/a.py")
        self._change("chg-b", "src/b.py")
        code, text, _ = self.team("--json")
        data = json.loads(text[text.index("{"):])
        for name in ("chg-a", "chg-b"):
            own = [f for f in data["findings"] if f["change"] == name]
            tens = [f for f in own if f["severity"] == 10]
            self.assertEqual(len(tens), 1,
                             "exactly one severity-10 next action per change: %s" % text)
            self.assertEqual(tens[0]["basis"], "derived", tens[0])
            lower = [f for f in own if f["severity"] < 10]
            top = min(lower, key=lambda f: f["severity"])
            self.assertEqual(tens[0]["nextAction"], top["nextAction"],
                             "the severity-10 finding must actually be derived from %s's "
                             "own highest-severity finding, not a generic filler: %s"
                             % (name, text))


class TestEvidenceAndConvergence(TeamScenario):
    def test_a_plan_with_no_convergence_report_is_no_data_at_severity_six_not_pass(self):
        self._change("chg-a", "src/a.py")
        code, text, _ = self.team()
        self.assertEqual(code, 1, "an unexamined convergence must block: %s" % text)
        self.assertIn("sbe converge", text)
        self.assertNotIn("convergence PASS", text)
        # F3: the audit found a mutation that folds this finding's severity
        # from 6 down to 2 without any test noticing; assert the exact number.
        code, text, _ = self.team("--json")
        data = json.loads(text[text.index("{"):])
        conv = [f for f in data["findings"]
               if f["change"] == "chg-a" and "09-convergence.json" in (f["evidence"] or "")]
        self.assertTrue(conv, "expected a convergence finding naming 09-convergence.json "
                              "for chg-a: %s" % text)
        self.assertEqual(conv[0]["severity"], 6,
                         "an unexamined convergence report must be severity 6, not folded "
                         "into another slot: %s" % text)

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
            # 1..11, not 1..10: severity 11 is the review-record slot, added
            # deliberately OUTSIDE 1..6 (see TEAM_SEVERITIES in status.py) so
            # a missing review, which is every one of this repository's nine
            # merged pull requests to date, reads as NO-DATA and never as a
            # block.
            self.assertTrue(1 <= int(f["severity"]) <= 11, f)
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


class TestHandoverIntegration(TeamScenario):
    """LT-302.B: the smallest possible read path so `sbe status --team` can
    report whether ownership of each change is moving, and to whom, over a
    real `12-handover.json` the real `sbe handover` engine wrote. The
    result is a purely additive top-level `handover` list, never folded
    into the severity 1..11 `findings` list: every test here also reasserts
    the 1..11 contract `TestJsonContractAndExit` already pins, so this
    class cannot pass by silently widening that range.
    """

    def _handover_for(self, data, name):
        self.assertIn("handover", data, data)
        hits = [h for h in data["handover"] if h["change"] == name]
        self.assertEqual(len(hits), 1, "exactly one handover entry per change: %s"
                                       % data["handover"])
        return hits[0]

    def _assert_severity_contract_holds(self, data):
        for f in data["findings"]:
            self.assertTrue(1 <= int(f["severity"]) <= 11,
                            "a handover entry must never widen the findings severity "
                            "range: %s" % f)

    def test_no_handover_needed_is_reported_per_change_and_never_blocks(self):
        self._change("chg-a", "src/a.py")
        code, text, _ = self.team("--json")
        data = json.loads(text[text.index("{"):])
        entry = self._handover_for(data, "chg-a")
        self.assertEqual(entry["status"], "none", entry)
        self.assertIsNone(entry["stale"], entry)
        self.assertIn("no handover", entry["detail"], entry)
        self.assertIn("never a block", entry["detail"], entry)
        self._assert_severity_contract_holds(data)

    def test_a_prepared_handover_reads_prepared_and_awaiting_receiver(self):
        doss = self._change("chg-a", "src/a.py")
        self.git("add", "-A")
        self.git("commit", "-qm", "chg-a dossier and source")
        code, text, _ = self.handover("prepare", doss, "--outgoing", "alice@example.com",
                                      "--receiver", "bob@example.com")
        self.assertEqual(code, 0, text)
        code, text, _ = self.team("--json")
        data = json.loads(text[text.index("{"):])
        entry = self._handover_for(data, "chg-a")
        self.assertEqual(entry["status"], "prepared", entry)
        self.assertFalse(entry["stale"], entry)
        self.assertIn("awaiting receiver", entry["detail"], entry)
        self.assertEqual(entry["outgoingOwner"], "alice@example.com", entry)
        self.assertEqual(entry["intendedReceiver"], "bob@example.com", entry)
        self._assert_severity_contract_holds(data)

    def test_a_stale_prepared_handover_is_named_without_widening_the_severity_range(self):
        doss = self._change("chg-a", "src/a.py")
        self.git("add", "-A")
        self.git("commit", "-qm", "chg-a dossier and source")
        code, text, _ = self.handover("prepare", doss, "--outgoing", "alice@example.com",
                                      "--receiver", "bob@example.com")
        self.assertEqual(code, 0, text)
        io.open(os.path.join(self.repo, "unrelated.txt"), "w").write("more\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "advance head past the prepared handover")
        code, text, _ = self.team("--json")
        data = json.loads(text[text.index("{"):])
        entry = self._handover_for(data, "chg-a")
        self.assertEqual(entry["status"], "prepared", entry)
        self.assertTrue(entry["stale"], entry)
        self.assertIn("stale", entry["detail"], entry)
        self._assert_severity_contract_holds(data)

    def test_an_acknowledged_handover_reads_acknowledged(self):
        doss = self._change("chg-a", "src/a.py")
        self.git("add", "-A")
        self.git("commit", "-qm", "chg-a dossier and source")
        self.handover("prepare", doss, "--outgoing", "alice@example.com",
                      "--receiver", "bob@example.com")
        code, text, _ = self.handover("acknowledge", doss, "--receiver", "bob@example.com")
        self.assertEqual(code, 0, text)
        code, text, _ = self.team("--json")
        data = json.loads(text[text.index("{"):])
        entry = self._handover_for(data, "chg-a")
        self.assertEqual(entry["status"], "acknowledged", entry)
        self.assertIn("acknowledged", entry["detail"], entry)
        self._assert_severity_contract_holds(data)

    def test_a_rejected_handover_reads_rejected(self):
        doss = self._change("chg-a", "src/a.py")
        self.git("add", "-A")
        self.git("commit", "-qm", "chg-a dossier and source")
        self.handover("prepare", doss, "--outgoing", "alice@example.com",
                      "--receiver", "bob@example.com")
        code, text, _ = self.handover("reject", doss, "--receiver", "bob@example.com",
                                      "--reason", "not ready yet")
        self.assertEqual(code, 0, text)
        code, text, _ = self.team("--json")
        data = json.loads(text[text.index("{"):])
        entry = self._handover_for(data, "chg-a")
        self.assertEqual(entry["status"], "rejected", entry)
        self.assertIn("not ready yet", entry["detail"], entry)
        self._assert_severity_contract_holds(data)

    def test_two_changes_each_carry_their_own_independent_handover_entry(self):
        doss_a = self._change("chg-a", "src/a.py")
        self._change("chg-b", "src/b.py")
        self.git("add", "-A")
        self.git("commit", "-qm", "both dossiers")
        self.handover("prepare", doss_a, "--outgoing", "alice@example.com",
                      "--receiver", "bob@example.com")
        code, text, _ = self.team("--json")
        data = json.loads(text[text.index("{"):])
        a_entry = self._handover_for(data, "chg-a")
        b_entry = self._handover_for(data, "chg-b")
        self.assertEqual(a_entry["status"], "prepared", a_entry)
        self.assertEqual(b_entry["status"], "none",
                         "chg-b must read its own absence, not chg-a's prepared record: %s"
                         % b_entry)


class TestPerChangeEvidenceScoping(TeamScenario):
    """LANE B-004, reproduced against the plain (non---team) `sbe status`
    (`build_report`), whose CR-06 dossier path used to consult
    `_scan_evidence`'s single GLOBAL `kindsCovered` for every discovered
    dossier: a gate receipt scoped to one dossier's own owned file cleared a
    SIBLING dossier's obligation too, purely because both dossiers
    consulted the same set in the same run. `test_sbe_status.py`'s own
    `TestDossierDiscovery` already pins the flat single-dossier layout's
    byte-identical output; kept out of this class on purpose.
    """

    def status(self, *extra):
        return self.sbe("status", self.repo, "--json", *extra)

    def _t2_dossier(self, name, src_rel):
        doss = self._change(name, src_rel)
        answers = dict(INTAKE["answers"])
        answers["changes_contract"] = "y"  # T2: owes design, gate and score
        io.open(os.path.join(doss, "00-intake.json"), "w").write(
            json.dumps({"answers": answers}, indent=2))
        return doss

    def _missing_gate(self, data, name):
        return [m for m in data["missingEvidence"]
               if m["finding"].startswith("dossier %s: " % name)
               and "hard gate" in m["finding"]]

    def _two_committed_t2_dossiers(self):
        self._t2_dossier("chg-a", "src/a.py")
        self._t2_dossier("chg-b", "src/b.py")
        self.git("add", "-A")
        self.git("commit", "-qm", "both T2 dossiers and their source")

    def _gate_receipt(self, out_rel, covers):
        out = os.path.join(self.repo, out_rel)
        code, text, _ = self.sbe(
            "evidence", "run", "--out", out, "--cwd", self.repo, "--covers", covers,
            "--kind", "gate", "--", sys.executable, "-c", "import sys; sys.exit(0)")
        self.assertEqual(code, 0, "the fixture receipt must verify sound: %s" % text)
        return out

    def test_a_receipt_scoped_to_one_dossier_no_longer_clears_a_siblings_gate_obligation(self):
        # THE BUG, reproduced: chg-a's receipt used to clear chg-b's
        # obligation too, purely because both were discovered together.
        self._two_committed_t2_dossiers()
        self._gate_receipt(".sbe/evidence/gate-a.json", "src/a.py")

        code, text, _ = self.status()
        data = json.loads(text[text.index("{"):])
        a_gate, b_gate = self._missing_gate(data, "chg-a"), self._missing_gate(data, "chg-b")

        self.assertFalse(a_gate, "the receipt covers src/a.py, chg-a's own plan ownership: "
                                 "it must clear chg-a's gate obligation: %s" % text)
        self.assertTrue(b_gate, "chg-a's receipt must never clear chg-b's gate obligation "
                                "just because both were discovered together: %s" % text)
        self.assertIn("chg-a", b_gate[0]["finding"],
                     "the finding must name where the matching receipt landed, not stay "
                     "silent about a receipt that plainly exists: %s" % text)
        self.assertNotEqual(code, 0, text)

    def test_a_same_numbered_task_id_in_a_sibling_plan_does_not_borrow_the_claim(self):
        # `sbe plan --write` always numbers a dossier's first task "T01", so
        # BOTH dossiers derive a task of their own also called "T01". An id
        # match alone must not let a registry record claim a sibling's
        # obligation; its OWN ownedPaths must overlap that dossier's plan.
        self._two_committed_t2_dossiers()
        out = self._gate_receipt(".sbe/evidence/gate-claimed.json", "seed.txt")
        run_id = json.loads(io.open(out, encoding="utf-8").read())["runId"]
        reg = os.path.join(self.repo, ".sbe", "tasks.json")
        io.open(reg, "w").write(json.dumps({"schemaVersion": "1.0", "tasks": [{
            "id": "T01", "agent": "alice", "role": "writer", "worktree": None,
            "ownedPaths": ["src/a.py"], "readOnlyPaths": [], "baseCommit": None,
            "expiry": None, "status": "closed", "verifyCommand": "python3 -c pass",
            "evidenceId": run_id, "openedAt": "2026-07-30T00:00:00Z",
            "closedAt": "2026-07-30T01:00:00Z"}]}))

        code, text, _ = self.status()
        data = json.loads(text[text.index("{"):])
        a_gate, b_gate = self._missing_gate(data, "chg-a"), self._missing_gate(data, "chg-b")

        self.assertFalse(a_gate, "chg-a's own T01 record claims this receipt, and its "
                                 "ownedPaths (src/a.py) is chg-a's own plan: %s" % text)
        self.assertTrue(b_gate, "chg-b also derives its own T01 task, but the claiming "
                                "record's ownedPaths name chg-a's file, not chg-b's: an id "
                                "match alone must never borrow the claim: %s" % text)

    def test_a_receipt_attributable_to_no_dossier_stays_unscoped_and_clears_nothing(self):
        self._two_committed_t2_dossiers()
        self._gate_receipt(".sbe/evidence/gate-unscoped.json", "seed.txt")

        code, text, _ = self.status()
        data = json.loads(text[text.index("{"):])
        for name in ("chg-a", "chg-b"):
            hits = self._missing_gate(data, name)
            self.assertTrue(hits, "seed.txt is owned by neither plan: must clear neither "
                                  "dossier's gate obligation: %s" % text)
            self.assertIn("unscoped", hits[0]["finding"],
                         "an unscoped receipt must be named as such, never silently dropped "
                         "or silently allowed to clear an obligation: %s" % text)


class TestCanonicalNextAction(TeamScenario):
    """LANE C1 (B-003): one canonical next action.

    Reproduced before `lifecycle.py` existed: a dossier whose ONLY
    outstanding obligation is review (evidence complete for its declared
    tier, both plan tasks closed clean, convergence and approval both PASS
    and bound to the current head, no `11-review.json` written yet) got
    THREE different answers. Plain `sbe status` never looks at task or
    review state at all, so it read the dossier's one clean evidence
    receipt and said "no action; this receipt is sound evidence" --
    clean-reading, not review-pending. `sbe status --team`'s own severity-10
    finding picked the MINIMUM raw team-severity number among this change's
    other findings, and severity 9 ("completed changes": every plan task
    closed clean) sorts below severity 11 ("review record") as a bare
    integer, so it said "nothing left to do for this change; open a PR" --
    also wrong, because review had not run. Only `/brothersbe:next`'s own
    prose ladder, which checks team's severity 11 directly rather than
    severity 10, would have said "run review".

    Both machine surfaces must now agree: `build_report`'s `nextActionDetail`
    and `build_team_report`'s severity-10 finding are both derived through
    `lifecycle.reduce_next_action`, so they can no longer read the same
    recorded state two different ways.
    """

    def status(self, *extra):
        code, text, _err = self.sbe("status", self.repo, "--json", *extra)
        return code, json.loads(text[text.index("{"):]), text

    def _review_pending_dossier(self):
        # A real plan, over a real dossier, exactly like every other fixture
        # in this file (`_change`), committed so the evidence receipt below
        # verifies clean rather than NO-DATA over a dirty tree.
        name = "review-pending"
        doss = self._change(name, "src/reviewme.py")
        self.git("add", "-A")
        self.git("commit", "-qm", "%s dossier and source" % name)
        head = self.git("rev-parse", "HEAD").strip()

        # Evidence complete for every kind the declared tier owes, over the
        # clean tree above, so MISSING EVIDENCE never fires on either
        # surface and the evidence-store scan sees sound, not broken,
        # evidence.
        out = os.path.join(self.repo, ".sbe", "evidence", "all.json")
        code, text, _ = self.sbe(
            "evidence", "run", "--out", out, "--cwd", self.repo,
            "--covers", "src/reviewme.py", "--kind", "design", "--kind", "gate",
            "--kind", "score", "--", sys.executable, "-c", "pass")
        self.assertEqual(code, 0, "the fixture receipt must verify sound: %s" % text)

        # `sbe plan --write` derives two tasks for this dossier (T01 owning
        # the source file, T02 the verification-only task); both closed
        # clean, so neither an active nor a ready task remains.
        self._closed_record("T01", ["src/reviewme.py"], agent="alice", base_commit=head)
        self._closed_record("T02", [], agent="alice", base_commit=head)

        # Convergence and approval both PASS, bound to the current head, so
        # neither outranks review on team's own ladder -- written directly,
        # the same technique `_open_record`/`_closed_record` already use for
        # a state only a real run would otherwise produce.
        io.open(os.path.join(doss, "09-convergence.json"), "w").write(
            json.dumps({"final": "PASS", "head": head}))
        io.open(os.path.join(doss, "10-approval.json"), "w").write(
            json.dumps({"headSha": head, "final": "PASS"}))

        # No 11-review.json: review is the one thing left undone.
        return name

    def test_review_pending_is_the_same_action_id_on_both_surfaces(self):
        name = self._review_pending_dossier()

        code, data, text = self.status()
        self.assertIn("nextActionDetail", data, text)
        self.assertNotIn("nothing blocking here", data["nextAction"],
                         "a dossier whose only obligation is review must never read as "
                         "clean: %s" % text)
        self.assertEqual(data["nextActionDetail"]["actionId"], "run-review", text)

        code, team_text, _ = self.team("--json")
        team_data = json.loads(team_text[team_text.index("{"):])
        tens = [f for f in team_data["findings"]
               if f["change"] == name and f["severity"] == 10]
        self.assertEqual(len(tens), 1, team_text)
        self.assertEqual(tens[0]["actionId"], "run-review",
                         "team's own severity-10 must not let severity 9 (\"completed "
                         "changes\") outrank severity 11 (\"review record\") by raw integer "
                         "comparison: %s" % team_text)

        self.assertEqual(data["nextActionDetail"]["actionId"], tens[0]["actionId"],
                         "plain status and team status must name the SAME next action for "
                         "the same dossier: status=%r team=%r"
                         % (data["nextActionDetail"]["actionId"], tens[0]["actionId"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
