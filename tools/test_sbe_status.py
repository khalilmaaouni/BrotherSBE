#!/usr/bin/env python3
"""Fixtures for `sbe status`. Run: python3 tools/test_sbe_status.py

Every test here builds a real git repository in a temporary directory and runs
the real command against it. Nothing is mocked, because the defect this
control exists for lives exactly at the seam between what several other
commands recorded and what a reader has to assemble by hand, and a mocked
store would test the mock.

Evidence receipts for "a design/gate/score run happened" are generated with
the real `sbe evidence run`, over a stand-in command whose argv merely
CONTAINS the keyword ("gate", "score", ...) status.py's classifier reads.
That is deliberate and stated here once: this suite pins status's OWN argv
classifier, not `sbe_gate.py` or `sbe_score.py` themselves, which already have
their own fixtures. A real gate run would make every fixture slower and would
not exercise the classifier any more thoroughly.
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


class StatusFixture(unittest.TestCase):
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

    def sbe(self, *argv):
        out = subprocess.run([sys.executable, SBE] + list(argv), capture_output=True, text=True)
        # Three values, not two: a two-value return reads as a possible
        # (verdict, evidence) pair to the honesty meta-test, which refuses any
        # such function sitting outside a check registry.
        return out.returncode, out.stdout + out.stderr, out.stderr

    def status(self, *extra):
        return self.sbe("status", self.repo, *extra)

    def status_json(self, *extra):
        code, text, stderr = self.sbe("status", self.repo, "--json", *extra)
        data = json.loads(text) if text.strip().startswith("{") else None
        return code, data, text

    def intake(self, **answers):
        base = {"changes_contract": "n", "crosses_boundary": "n",
                "reversible_under_hour": "y", "touches_sensitive": "n", "consumers": "none"}
        base.update(answers)
        return write(self.repo, "00-intake.json", json.dumps({"answers": base}))

    def run_evidence(self, out_rel, argv_kind, exit_code=0, covers="README.md"):
        """A real receipt, written by the real `sbe evidence run`, whose argv
        contains `argv_kind` (e.g. "gate", "score") so status's classifier can
        read it. `exit_code` != 0 is produced by asking python to exit that
        code; the receipt is still sound evidence (verify PASS), it just
        records a failing run, which is the MERGE BLOCKER shape."""
        out_path = os.path.join(self.repo, out_rel)
        code, text, _ = self.sbe(
            "evidence", "run", "--out", out_path, "--covers", covers, "--cwd", self.repo,
            "--", sys.executable, "-c", "import sys; sys.exit(%d)" % exit_code, argv_kind)
        return out_path


class TestNoStores(StatusFixture):
    def test_an_empty_repo_with_no_stores_is_all_no_data_and_exits_0(self):
        code, text, _ = self.status("--base", self.base)
        self.assertEqual(code, 0, text)
        for name in ("BROKEN CLAIMS", "MERGE BLOCKERS", "ACTIVE CONFLICTS",
                     "MISSING EVIDENCE", "COMPLETED EVIDENCE"):
            self.assertIn(name, text)
        self.assertIn("NO-DATA", text)
        self.assertIn("no evidence store found", text)
        self.assertIn("no task registry found", text)
        # exit 0 is NOT a claim of a clean pass; the closing line must say so.
        self.assertIn("not the same claim as everything", text)
        self.assertIn("NEXT ACTION: nothing blocking here that this tool can see", text)

    def test_each_absent_store_marks_its_own_section_no_data_not_only_somewhere(self):
        # A single NO-DATA anywhere in the output must not vouch for every
        # section: the honesty lives per line. With no stores at all, the
        # ACTIVE CONFLICTS line itself carries NO-DATA, not just its note text.
        code, text, _ = self.status("--base", self.base)
        self.assertEqual(code, 0, text)
        for heading in ("BROKEN CLAIMS", "ACTIVE CONFLICTS", "COMPLETED EVIDENCE"):
            start = text.index(heading)
            rest = text[start:]
            end = rest.find("\n\n")
            section = rest if end < 0 else rest[:end]
            self.assertIn("NO-DATA", section,
                          "%s must say NO-DATA on its own line when its store is "
                          "absent, not rely on another section's honesty: %r"
                          % (heading, section))


class TestBrokenClaims(StatusFixture):
    def test_a_stale_receipt_is_named_under_broken_claims_and_exits_1(self):
        # BREAK: generate a sound receipt, then move HEAD, which makes the
        # receipt's bound commit stale.
        out_path = self.run_evidence(".sbe/evidence/r1.json", "score")
        write(self.repo, "unrelated.txt", "more\n")
        self.commit("advance head")
        code, text, _ = self.status("--base", self.base)
        # RED: the stale receipt must be named, and it must block.
        self.assertNotEqual(code, 0, text)
        self.assertIn("BROKEN CLAIMS", text)
        self.assertIn(os.path.relpath(out_path, self.repo), text)
        self.assertIn("not the current head", text)

    def test_a_current_receipt_is_not_named_as_broken(self):
        # RESTORE: the same receipt, verified before HEAD moves, is not broken.
        self.run_evidence(".sbe/evidence/r1.json", "score")
        code, text, _ = self.status("--base", self.base)
        self.assertNotIn("does not match the seal", text)
        broken_block = text.split("MERGE BLOCKERS:")[0]
        self.assertNotIn(".sbe/evidence/r1.json", broken_block,
                         "a current, sound receipt must not appear under BROKEN CLAIMS")


class TestTierReconciliation(StatusFixture):
    def test_a_tier_disagreement_with_no_disposition_is_a_merge_blocker(self):
        # BREAK: an intake that answers every question "no" (T0) sitting
        # beside a diff that adds an API contract file (which sbe impact
        # reads as T2).
        write(self.repo, "api/openapi.yaml", "openapi: 3.0.0\npaths:\n  /orders: {}\n")
        self.commit()
        self.intake()
        code, text, _ = self.status("--base", self.base)
        # RED.
        self.assertNotEqual(code, 0, text)
        self.assertIn("MERGE BLOCKERS", text)
        self.assertIn("intake declared T0 but the diff shows T2", text)
        self.assertIn("openapi", text)

    def test_a_valid_disposition_clears_the_tier_disagreement(self):
        # RESTORE: the same disagreement, with a disposition recorded against
        # the current head.
        write(self.repo, "api/openapi.yaml", "openapi: 3.0.0\npaths:\n  /orders: {}\n")
        head = self.commit()
        self.intake()
        write(self.repo, "disposition.json", json.dumps([{
            "detector": "openapi", "decision": "keep-lower",
            "reason": "internal fixture only, never published", "who": "the engineer",
            "head": head}]))
        code, text, _ = self.status("--base", self.base)
        # GREEN: no merge blocker from the tier reconciliation. (T0 also owes
        # no evidence, so MISSING EVIDENCE stays empty too.)
        self.assertEqual(code, 0, text)
        self.assertNotIn("intake declared", text)


class TestActiveConflicts(StatusFixture):
    def test_overlapping_open_tasks_are_named_under_active_conflicts(self):
        code, text, _ = self.sbe("task", "open", "--id", "honest", "--agent", "alpha",
                                 "--role", "writer", "--base", self.base,
                                 "--verify", "true", "--owns", "src/owned.py",
                                 "--cwd", self.repo)
        self.assertEqual(code, 0, text)
        reg_path = os.path.join(self.repo, ".sbe", "tasks.json")
        with io.open(reg_path, encoding="utf-8") as fh:
            data = json.load(fh)
        # BREAK: inject a second, overlapping open task directly into the
        # registry, the way a hand edit or a second uncoordinated agent would.
        injected = dict(data["tasks"][0])
        injected["id"] = "injected"
        injected["ownedPaths"] = ["src/"]
        data["tasks"].append(injected)
        write(self.repo, os.path.join(".sbe", "tasks.json"), json.dumps(data))
        code, text, _ = self.status("--base", self.base)
        # RED.
        self.assertNotEqual(code, 0, text)
        self.assertIn("ACTIVE CONFLICTS", text)
        self.assertIn("honest", text)
        self.assertIn("injected", text)

    def test_non_overlapping_open_tasks_are_not_named_as_conflicts(self):
        # RESTORE: two open tasks with disjoint scope.
        self.sbe("task", "open", "--id", "w1", "--agent", "a", "--role", "writer",
                "--base", self.base, "--verify", "true", "--owns", "src/a.py",
                "--cwd", self.repo)
        self.sbe("task", "open", "--id", "w2", "--agent", "b", "--role", "writer",
                "--base", self.base, "--verify", "true", "--owns", "docs/b.md",
                "--cwd", self.repo)
        code, text, _ = self.status("--base", self.base)
        # GREEN.
        self.assertEqual(code, 0, text)
        self.assertNotIn("two open writers overlap", text)


class TestForcedClose(StatusFixture):
    def test_a_forced_task_close_is_a_merge_blocker(self):
        self.sbe("task", "open", "--id", "w1", "--agent", "a", "--role", "writer",
                "--base", self.base, "--verify", "true", "--owns", "src/owned.py",
                "--cwd", self.repo)
        write(self.repo, "docs/other.md", "out of scope\n")
        self.commit()
        code, text, _ = self.sbe("task", "close", "w1", "--force", "--who", "the operator",
                                 "--why", "hotfix, accepted out of band", "--cwd", self.repo)
        self.assertEqual(code, 0, text)
        code, text, _ = self.status("--base", self.base)
        self.assertNotEqual(code, 0, text)
        self.assertIn("MERGE BLOCKERS", text)
        self.assertIn("FORCED by the operator", text)


class TestMissingEvidence(StatusFixture):
    def test_missing_evidence_for_the_declared_tier_names_the_filler(self):
        # BREAK: a T2 intake (changes_contract=y) with no evidence store at
        # all.
        self.intake(changes_contract="y")
        code, text, _ = self.status("--base", self.base)
        self.assertNotEqual(code, 0, text)
        self.assertIn("MISSING EVIDENCE", text)
        self.assertIn("design completeness check", text)
        self.assertIn("hard gate", text)
        self.assertIn("scored surface", text)
        self.assertIn("sbe evidence run", text)

    def test_a_t0_intake_owes_no_evidence(self):
        # RESTORE-shaped: a T0 intake owes nothing, so MISSING EVIDENCE stays
        # empty even with no evidence store.
        self.intake()
        code, text, _ = self.status("--base", self.base)
        self.assertEqual(code, 0, text)
        self.assertNotIn("owes one", text)


class TestCompletedEvidence(StatusFixture):
    def test_a_verifying_receipt_shows_under_completed_evidence_with_its_trust_label(self):
        self.run_evidence(".sbe/evidence/clean.json", "smoke-test", exit_code=0)
        code, text, _ = self.status("--base", self.base)
        self.assertEqual(code, 0, text)
        self.assertIn("COMPLETED EVIDENCE", text)
        self.assertIn(".sbe/evidence/clean.json", text)
        self.assertIn("trust LOCAL-ADVISORY", text)

    def test_a_receipt_recording_a_failing_run_is_a_merge_blocker_not_completed(self):
        self.run_evidence(".sbe/evidence/broke.json", "gate", exit_code=1)
        code, text, _ = self.status("--base", self.base)
        self.assertNotEqual(code, 0, text)
        self.assertIn("MERGE BLOCKERS", text)
        self.assertIn("exit code 1", text)
        completed_block = text.split("COMPLETED EVIDENCE:")[1].split("NEXT ACTION")[0]
        self.assertNotIn(".sbe/evidence/broke.json", completed_block)


class TestNextAction(StatusFixture):
    def test_next_action_tracks_broken_claims_first_when_both_are_present(self):
        out_path = self.run_evidence(".sbe/evidence/r1.json", "score")
        write(self.repo, "api/openapi.yaml", "openapi: 3.0.0\n")
        self.commit()
        self.intake()  # T0, disagrees with the diff-derived T2: a merge blocker too
        code, text, _ = self.status("--base", self.base)
        next_line = [l for l in text.splitlines() if l.startswith("NEXT ACTION")][0]
        self.assertIn("re-run", next_line, "the broken-claim remedy must win: %s" % next_line)
        self.assertIn("(BROKEN CLAIMS)", next_line)

    def test_next_action_tracks_merge_blockers_when_broken_claims_is_empty(self):
        write(self.repo, "api/openapi.yaml", "openapi: 3.0.0\n")
        self.commit()
        self.intake()
        code, text, _ = self.status("--base", self.base)
        next_line = [l for l in text.splitlines() if l.startswith("NEXT ACTION")][0]
        self.assertIn("(MERGE BLOCKERS)", next_line)

    def test_next_action_is_the_generic_line_when_everything_is_empty(self):
        code, text, _ = self.status("--base", self.base)
        next_line = [l for l in text.splitlines() if l.startswith("NEXT ACTION")][0]
        self.assertIn("nothing blocking here that this tool can see", next_line)
        self.assertIn("scope:", next_line)


class TestJsonMode(StatusFixture):
    def test_json_mode_carries_every_section_the_scope_and_the_schema_version(self):
        self.intake(changes_contract="y")
        code, data, text = self.status_json("--base", self.base)
        self.assertIsNotNone(data, text)
        for key in ("schemaVersion", "toolVersion", "generatedAt", "root", "scope",
                    "brokenClaims", "mergeBlockers", "activeConflicts", "missingEvidence",
                    "soundEvidence", "nextAction"):
            self.assertIn(key, data, text)
        self.assertIn("storesInspected", data["scope"])
        self.assertTrue(data["missingEvidence"], "a T2 intake with no evidence store must "
                                                  "populate missingEvidence")
        self.assertNotEqual(code, 0, text)


class TestPositiveSentenceGuard(StatusFixture):
    def test_every_clean_or_nodata_line_in_text_mode_names_its_scope(self):
        """The test greps the RENDERED OUTPUT, never the source: every line
        that reports a section as clean or as NO-DATA must carry a scope
        phrase, so a reader is never told "nothing here" without being told
        what was actually read."""
        # A mix: one broken claim present, several sections legitimately
        # empty, so both the item-bearing and the empty-section renderings
        # are exercised in the same run.
        self.run_evidence(".sbe/evidence/r1.json", "score")
        write(self.repo, "unrelated.txt", "more\n")
        self.commit("advance head")
        code, text, _ = self.status("--base", self.base)
        self.assertNotEqual(code, 0, text)
        candidate_lines = [l for l in text.splitlines()
                           if l.strip().startswith("clean") or l.strip().startswith("NO-DATA")]
        self.assertTrue(candidate_lines, "this fixture must exercise at least one empty "
                                         "section line: %s" % text)
        for line in candidate_lines:
            self.assertIn("scope", line.lower(),
                          "an empty-section line named nothing it inspected: %r" % line)

    def test_a_positive_evidence_line_names_its_scope_too(self):
        """The scope rule covers POSITIVE findings, not only clean and NO-DATA
        lines: a receipt reported sound must say what that soundness was
        checked against, or the strongest sentence in the output is the one
        naming the least."""
        self.run_evidence(".sbe/evidence/clean.json", "score")
        code, text, _ = self.status("--base", self.base)
        positive = [l for l in text.splitlines()
                    if "verifies as sound evidence" in l]
        self.assertTrue(positive, "this fixture must produce a sound receipt line: %s" % text)
        for line in positive:
            self.assertIn("scope:", line,
                          "a positive evidence line named nothing it inspected: %r" % line)


if __name__ == "__main__":
    unittest.main(verbosity=2)
