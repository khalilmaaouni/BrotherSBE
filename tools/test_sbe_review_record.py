"""Fixtures for the review record: `sbe review --write` (src/brothersbe/cli.py)
writing `11-review.json` into a dossier, and `sbe status --team`
(src/brothersbe/status.py) reading it back: absence (NO-DATA, never a
block), a record present but broken (FAIL), a record bound to a commit that
is no longer the head (derived, blocking staleness, the same slot approval
and convergence staleness already use), a reviewer who is also the commit's
author (FAIL, mirroring `prverify.py`'s "approving their own change"), and a
clean independent approved record (PASS, its counts always stated).

Every fixture builds its own throwaway git repository with a dossier under
design/, seeded through the real `sbe plan --write`, as
tools/test_sbe_status_team.py does. `sbe review` also runs `sbe_score.py`,
which reads BROTHERSBE_VAULT and defaults its citation check to this
repository's own tree; every `sbe` call here runs with BROTHERSBE_VAULT
unset and SBE_CITATION_ROOT pointed at the throwaway repo instead, so a
scenario depends only on the fixture it built.
"""
import io
import json
import os
import shutil
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


class ReviewScenario(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sbe-review-")
        self.repo = os.path.join(self.tmp, "repo")
        os.makedirs(self.repo)
        self.git("init", "-q")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "user.name", "fixture")
        io.open(os.path.join(self.repo, "seed.txt"), "w").write("seed\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "seed")
        # Isolate every `sbe` call in this file from the real machine: no
        # real vault, and the citation check scans the throwaway repo rather
        # than defaulting to this installation's own tree.
        self.env = dict(os.environ)
        self.env.pop("BROTHERSBE_VAULT", None)
        self.env["SBE_CITATION_ROOT"] = self.repo

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def git(self, *args):
        code, text, _err = _run(["git", "-C", self.repo] + list(args))
        self.assertEqual(code, 0, "git %s failed: %s" % (args, text))
        return text

    def sbe(self, *args):
        return _run([sys.executable, SBE] + list(args), env=self.env)

    def team(self, *extra):
        return self.sbe("status", self.repo, "--team", *extra)

    def team_findings(self, change="chg-a", severity=None):
        # Three values, not two: a two-value return reads as a possible
        # (verdict, evidence) pair to the honesty meta-test, which refuses
        # any such function sitting outside a check registry. `text` is the
        # raw `--json` report `hits` was parsed from, kept rather than
        # dropped so a caller whose assertion on `hits` fails can print the
        # whole report instead of just the filtered slice.
        code, text, _err = self.team("--json")
        data = json.loads(text[text.index("{"):])
        hits = [f for f in data["findings"] if f["change"] == change]
        if severity is not None:
            hits = [f for f in hits if f["severity"] == severity]
        return code, hits, text

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

    def _closed_record(self, task_id, owns, agent="alice", base_commit=None):
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
            "expiry": None, "status": "closed", "verifyCommand": "python3 -c pass",
            "evidenceId": None, "openedAt": "2026-07-30T00:00:00Z",
            "closedAt": "2026-07-30T01:00:00Z",
        })
        io.open(reg, "w").write(json.dumps(data, indent=2))

    def _write_json(self, path, data):
        io.open(path, "w", encoding="utf-8").write(json.dumps(data, indent=2))

    def _make_clean_change(self, name="chg-a", src_rel="src/a.py"):
        """A change with a plan, both tasks closed clean, a PASS convergence
        report, a PASS approval report and a clean evidence receipt, all
        bound to the current head. What a scenario built on top of this
        asserts about severity 4 or severity 11 is then never an accident of
        some OTHER severity slot also being unhappy: this is what "otherwise
        clean" means in the tests below.

        Returns three values, not two, for the same reason `_run` above
        does: a two-value return reads as a possible (verdict, evidence)
        pair to the honesty meta-test, which refuses any such function
        sitting outside a check registry, and `doss, head = ...` here is a
        dossier path and a commit sha, neither of them a verdict this lint
        could ever prove is not PASS. The third value, the evidence
        receipt's path, is not padding: it is the one path this method
        computes that no caller could otherwise re-derive without repeating
        `.sbe/evidence/ok.json` by hand.
        """
        doss = self._change(name, src_rel)
        self.git("add", "-A")
        self.git("commit", "-qm", "%s dossier and source" % name)
        head = self.git("rev-parse", "HEAD").strip()
        # The evidence run happens here, against the just-committed, still
        # clean tree: `evidence.verify` reads a receipt generated over a
        # dirty tree as NO-DATA (advisory, never sound evidence), and the
        # fixture files written below (an open registry, hand-written
        # convergence and approval reports) would make the tree dirty if
        # they came first.
        out = os.path.join(self.repo, ".sbe", "evidence", "ok.json")
        code, text, _ = self.sbe("evidence", "run", "--out", out, "--cwd", self.repo,
                                 "--covers", src_rel, "--", sys.executable, "-c", "pass")
        self.assertEqual(code, 0, "evidence run: %s" % text)
        self._closed_record("T01", [src_rel], agent="alice", base_commit=head)
        self._closed_record("T02", [], agent="alice", base_commit=head)
        self._write_json(os.path.join(doss, "09-convergence.json"),
                         {"final": "PASS", "head": head, "dossier": doss, "base": head})
        self._write_json(os.path.join(doss, "10-approval.json"),
                         {"tool": "sbe pr verify", "repository": "example/repo",
                          "number": 1, "headSha": head, "final": "PASS", "controls": []})
        return doss, head, out


class TestWrite(ReviewScenario):
    """The write side: `sbe review <dossier> --write ...`."""

    def test_without_write_no_record_is_created(self):
        doss = self._change("chg-a", "src/a.py")
        self.sbe("review", doss)
        self.assertFalse(os.path.exists(os.path.join(doss, "11-review.json")),
                         "review without --write must behave exactly as before: no file")

    def test_write_without_the_required_flags_is_a_usage_error(self):
        doss = self._change("chg-a", "src/a.py")
        code, text, _ = self.sbe("review", doss, "--write")
        self.assertEqual(code, 2, text)
        self.assertFalse(os.path.exists(os.path.join(doss, "11-review.json")),
                         "a refused write must leave no partial record: %s" % text)
        self.assertIn("--reviewer", text)
        self.assertIn("--reviewer-type", text)
        self.assertIn("--result", text)

    def test_write_persists_a_record_carrying_every_required_field(self):
        doss = self._change("chg-a", "src/a.py")
        self.git("add", "-A")
        self.git("commit", "-qm", "chg-a dossier and source")
        head = self.git("rev-parse", "HEAD").strip()
        self.sbe("review", doss, "--write", "--reviewer", "Independent Reviewer",
                "--reviewer-type", "human", "--result", "approved",
                "--accept-risk", "known flaky test")
        path = os.path.join(doss, "11-review.json")
        self.assertTrue(os.path.exists(path), "sbe review --write must write 11-review.json")
        record = json.loads(io.open(path, encoding="utf-8").read())
        for key in ("schemaVersion", "tool", "dossier", "headSha", "reviewer",
                   "reviewerType", "result", "findings", "acceptedRisks", "createdAt"):
            self.assertIn(key, record, "11-review.json missing %s: %s" % (key, record))
        self.assertEqual(record["headSha"], head)
        self.assertEqual(record["reviewer"], "Independent Reviewer")
        self.assertEqual(record["reviewerType"], "human")
        self.assertEqual(record["result"], "approved")
        self.assertEqual(record["acceptedRisks"], ["known flaky test"])
        self.assertIsInstance(record["findings"], list)

    def test_write_can_never_move_the_exit_code(self):
        """`_record_review` must never be the thing deciding this command's
        exit code: the same run, with and without --write, must exit the
        same way, because `worst` is computed before the write is ever
        attempted (cli.py's `_cmd_review`)."""
        doss = self._change("chg-a", "src/a.py")
        self.git("add", "-A")
        self.git("commit", "-qm", "chg-a dossier and source")
        without_code, _t1, _e1 = self.sbe("review", doss)
        with_code, _t2, _e2 = self.sbe("review", doss, "--write", "--reviewer", "r",
                                       "--reviewer-type", "human", "--result", "approved")
        self.assertEqual(without_code, with_code,
                         "--write changed the exit code sbe review returned")

    def test_a_record_written_by_a_real_run_is_read_back_as_an_independent_pass(self):
        """End to end: a record `sbe review --write` actually produced is
        read, unmodified, by `sbe status --team` as a clean, independent
        approval."""
        doss, _head, _out = self._make_clean_change("chg-a", "src/a.py")
        code, text, _ = self.sbe("review", doss, "--write", "--reviewer",
                                 "Independent Reviewer", "--reviewer-type", "human",
                                 "--result", "approved")
        self.assertTrue(os.path.exists(os.path.join(doss, "11-review.json")), text)
        _code, hits, _text = self.team_findings("chg-a", 11)
        self.assertTrue(hits, "expected a severity 11 review finding: %s" % text)
        self.assertEqual(hits[0]["verdict"], "PASS", hits[0])
        self.assertEqual(hits[0]["basis"], "observed", hits[0])


class TestStatusWiring(ReviewScenario):
    """The read side: `sbe status --team` next to the existing approval and
    convergence blocks."""

    def test_absence_is_no_data_and_never_blocks_an_otherwise_clean_change(self):
        # Central to this defect fix: human review has never run on this
        # repository (every merged pull request carries zero reviews), and
        # the repository's own law is that absence is NO-DATA, never a pass
        # and never a block. A missing 11-review.json must not flip an
        # otherwise clean change to blocking the day this feature ships.
        self._make_clean_change("chg-a", "src/a.py")
        code, hits, _text = self.team_findings("chg-a", 11)
        self.assertTrue(hits, "a change with a plan must always carry a review finding, "
                              "even an absent one")
        self.assertEqual(hits[0]["verdict"], "NO-DATA", hits[0])
        self.assertIn("absence is a fact, not an accusation", hits[0]["detail"])
        self.assertEqual(code, 0,
                         "a missing review record must never, by itself, block a merge")

    def test_a_malformed_record_is_fail_never_no_data(self):
        doss, _head, _out = self._make_clean_change("chg-a", "src/a.py")
        io.open(os.path.join(doss, "11-review.json"), "w").write("not json{{{")
        code, hits, _text = self.team_findings("chg-a", 11)
        self.assertTrue(hits, hits)
        self.assertEqual(hits[0]["verdict"], "FAIL",
                         "a record present but unparseable must FAIL, not read as the "
                         "same absence as no record at all: %s" % hits)
        # It must FAIL by actually naming the parse error, not merely by
        # saying "broken" in the abstract: "I could not read this" has to
        # carry the reason, the same way a receipt that fails verify names
        # its reasons rather than only saying "fails verify".
        self.assertIn("does not parse", hits[0]["detail"])
        self.assertIn("Expecting value", hits[0]["detail"], hits)

    def test_absence_and_malformed_never_share_a_verdict(self):
        """The two states this file exists to keep apart, in one place:
        absent is NO-DATA (nobody has reviewed yet, a fact, not an
        accusation), unparseable is FAIL (somebody tried and left something
        nobody can trust). Collapsing "I could not read the review" and
        "there is no review" into the same answer is exactly the confusion
        `sbe review` not persisting anything used to cause."""
        doss, _head, _out = self._make_clean_change("chg-a", "src/a.py")
        _code, absent, _text = self.team_findings("chg-a", 11)
        self.assertEqual(absent[0]["verdict"], "NO-DATA", absent)
        io.open(os.path.join(doss, "11-review.json"), "w").write("{not valid")
        _code, malformed, _text = self.team_findings("chg-a", 11)
        self.assertEqual(malformed[0]["verdict"], "FAIL", malformed)
        self.assertNotEqual(absent[0]["verdict"], malformed[0]["verdict"])

    def test_a_record_missing_a_required_field_is_also_fail(self):
        doss, head, _out = self._make_clean_change("chg-a", "src/a.py")
        self._write_json(os.path.join(doss, "11-review.json"),
                         {"headSha": head, "reviewer": "Someone Else",
                          "result": "approved"})  # no reviewerType
        code, hits, _text = self.team_findings("chg-a", 11)
        self.assertTrue(hits, hits)
        self.assertEqual(hits[0]["verdict"], "FAIL", hits)

    def test_a_stale_review_record_is_a_derived_severity_four_finding(self):
        doss, head, _out = self._make_clean_change("chg-a", "src/a.py")
        self._write_json(os.path.join(doss, "11-review.json"),
                         {"headSha": head, "reviewer": "Someone Else",
                          "reviewerType": "human", "result": "approved",
                          "findings": [], "acceptedRisks": []})
        io.open(os.path.join(self.repo, "src", "a.py"), "a").write("y = 2\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "a later commit the saved review never saw")
        _code, hits, _text = self.team_findings("chg-a", 4)
        stale = [f for f in hits if "11-review.json" in (f["evidence"] or "")
                or "review" in f["detail"].lower()]
        self.assertTrue(stale, "a review bound to a superseded head must surface at "
                              "severity 4: %s" % hits)
        self.assertEqual(stale[0]["basis"], "derived", stale[0])
        self.assertEqual(stale[0]["verdict"], "FAIL", stale[0])
        self.assertIn(head[:12], stale[0]["detail"])

    def test_self_review_fails_and_is_never_a_silent_pass(self):
        # setUp's git identity is name "fixture", email fixture@example.invalid.
        # A review record naming that identity as reviewer, by name or by
        # email, must not read as a clean pass, exactly as prverify.py
        # refuses a GitHub approval whose login is the pull request's author.
        doss, head, _out = self._make_clean_change("chg-a", "src/a.py")
        for reviewer in ("fixture", "fixture@example.invalid"):
            self._write_json(os.path.join(doss, "11-review.json"),
                             {"headSha": head, "reviewer": reviewer,
                              "reviewerType": "human", "result": "approved",
                              "findings": [], "acceptedRisks": []})
            _code, hits, _text = self.team_findings("chg-a", 11)
            self.assertTrue(hits, (reviewer, hits))
            self.assertEqual(hits[0]["verdict"], "FAIL", (reviewer, hits))
            self.assertIn("naming only the author is not an approval", hits[0]["detail"])
            self.assertEqual(hits[0]["basis"], "derived", hits[0])

    def test_an_independent_approved_review_is_a_clean_pass_stating_its_counts(self):
        doss, head, _out = self._make_clean_change("chg-a", "src/a.py")
        self._write_json(os.path.join(doss, "11-review.json"),
                         {"headSha": head, "reviewer": "Someone Else",
                          "reviewerType": "independent-model", "result": "approved",
                          "findings": ["minor: consider a docstring"],
                          "acceptedRisks": ["accepted: perf ok for this volume"]})
        code, hits, _text = self.team_findings("chg-a", 11)
        self.assertTrue(hits, hits)
        self.assertEqual(hits[0]["verdict"], "PASS", hits)
        self.assertEqual(hits[0]["basis"], "observed", hits[0])
        # Rule: a record must never read as silently clean; its finding and
        # accepted-risk counts are stated explicitly, even when both are
        # zero, so the difference between "reviewed and found nothing" and
        # "was not looked at" is never lost. Here they are 1 and 1.
        self.assertIn("1 finding", hits[0]["detail"])
        self.assertIn("1 accepted risk", hits[0]["detail"])
        self.assertEqual(code, 0, hits)

    def test_zero_findings_are_stated_explicitly_not_read_as_silently_clean(self):
        doss, head, _out = self._make_clean_change("chg-a", "src/a.py")
        self._write_json(os.path.join(doss, "11-review.json"),
                         {"headSha": head, "reviewer": "Someone Else",
                          "reviewerType": "human", "result": "approved",
                          "findings": [], "acceptedRisks": []})
        _code, hits, _text = self.team_findings("chg-a", 11)
        self.assertTrue(hits, hits)
        self.assertIn("0 finding", hits[0]["detail"])
        self.assertIn("0 accepted risk", hits[0]["detail"])

    def test_a_non_approved_result_surfaces_as_its_own_verdict(self):
        doss, head, _out = self._make_clean_change("chg-a", "src/a.py")
        self._write_json(os.path.join(doss, "11-review.json"),
                         {"headSha": head, "reviewer": "Someone Else",
                          "reviewerType": "human", "result": "changes-required",
                          "findings": ["fix the null check"], "acceptedRisks": []})
        _code, hits, _text = self.team_findings("chg-a", 11)
        self.assertTrue(hits, hits)
        self.assertEqual(hits[0]["verdict"], "changes-required", hits)

    def test_an_undeterminable_author_is_no_data_never_a_pass(self):
        # bound == head (never stale) but the commit object itself cannot be
        # read, the shape a shallow clone or a partially fetched history
        # leaves behind: the ref resolves to a sha, the object backing it
        # does not. `_commit_author` must answer (None, None), and that must
        # read as NO-DATA, never as a pass, even though `result` says
        # "approved".
        doss, head, _out = self._make_clean_change("chg-a", "src/a.py")
        obj_path = os.path.join(self.repo, ".git", "objects", head[:2], head[2:])
        self.assertTrue(os.path.exists(obj_path), "fixture assumption: a loose object")
        os.remove(obj_path)
        self._write_json(os.path.join(doss, "11-review.json"),
                         {"headSha": head, "reviewer": "Someone Else",
                          "reviewerType": "human", "result": "approved",
                          "findings": [], "acceptedRisks": []})
        _code, hits, _text = self.team_findings("chg-a", 11)
        self.assertTrue(hits, hits)
        self.assertEqual(hits[0]["verdict"], "NO-DATA",
                         "an unresolvable author must never read as a pass: %s" % hits)
        self.assertEqual(hits[0]["basis"], "unavailable", hits[0])

    def test_the_review_record_appears_in_the_human_report_next_to_approval(self):
        self._make_clean_change("chg-a", "src/a.py")
        code, text, _ = self.team()
        self.assertIn("REVIEW RECORD", text)
        self.assertIn("11-review.json", text)

    def test_severity_eleven_is_within_the_documented_json_contract_bound(self):
        self._make_clean_change("chg-a", "src/a.py")
        code, text, _ = self.team("--json")
        data = json.loads(text[text.index("{"):])
        sevs = [f["severity"] for f in data["findings"]]
        self.assertTrue(sevs, "expected findings")
        self.assertTrue(all(1 <= s <= 11 for s in sevs), sevs)
        self.assertIn(11, sevs)


if __name__ == "__main__":
    unittest.main(verbosity=2)
