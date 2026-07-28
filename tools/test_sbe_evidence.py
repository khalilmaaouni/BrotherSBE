#!/usr/bin/env python3
"""Fixtures for `sbe evidence`. Run: python3 tools/test_sbe_evidence.py

Every test here builds a real git repository in a temporary directory, runs a
real command through the real wrapper, and verifies the receipt that came out.
Nothing is mocked, because the defect this control exists for lives exactly at
the seam between a command and a claim about it, and a mocked subprocess would
test the mock.

Receipts are written OUTSIDE the repository under test, on purpose. A receipt
written into the tree it covers makes that tree dirty, and every later run then
reports NO-DATA for a reason that has nothing to do with the work.

The fixture set follows the shape the brief asks for: the defect (a hand-written
receipt), the sound case, a stale commit, a stale file, a dirty tree, malformed
receipts, a vacuous required field, and the assertion that raw output never
reaches the file.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
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


class EvidenceFixture(unittest.TestCase):
    """A fresh repository per test, one base commit and one change commit in it,
    plus a scratch directory outside the repository for receipts."""

    def setUp(self):
        self.repo = tempfile.mkdtemp()
        self.out = tempfile.mkdtemp()
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "fixture@example.invalid")
        git(self.repo, "config", "user.name", "fixture")
        write(self.repo, "README.md", "base\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "base")
        self.base = git(self.repo, "rev-parse", "HEAD")
        write(self.repo, "src/service.py", "def handle():\n    return 1\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "the work this receipt will cover")
        self.head = git(self.repo, "rev-parse", "HEAD")

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)
        shutil.rmtree(self.out, ignore_errors=True)

    def receipt_path(self, name="receipt.json"):
        return os.path.join(self.out, name)

    def run_sbe(self, *argv, **kwargs):
        """The CompletedProcess, not a pair.

        Deliberately not `(code, text)`: `evals/test_no_data_class.py` reads
        every two-value return in `tools/` as a possible (verdict, evidence)
        pair it cannot prove is never PASS, and it is right to. Returning the
        process object says what this is.
        """
        env = dict(os.environ)
        env.update(kwargs.get("env") or {})
        return subprocess.run([sys.executable, SBE] + list(argv), capture_output=True,
                              text=True, env=env)

    @staticmethod
    def output(proc):
        return proc.stdout + proc.stderr

    def generate(self, command=None, out=None, extra=(), env=None):
        """Run a real command through the wrapper and return (path, code, text)."""
        out = out or self.receipt_path()
        command = command or ["python3", "-c", "print('the suite ran')"]
        argv = ["evidence", "run", "--out", out, "--cwd", self.repo,
                "--base", self.base] + list(extra) + ["--"] + list(command)
        proc = self.run_sbe(*argv, env=env)
        return out, proc.returncode, self.output(proc)

    def verify(self, path=None, extra=()):
        path = path or self.receipt_path()
        proc = self.run_sbe("evidence", "verify", path, "--cwd", self.repo, "--json", *extra)
        text = self.output(proc)
        blob = text[text.index("{"):text.rindex("}") + 1] if "{" in text else "{}"
        return proc.returncode, json.loads(blob), text

    def load(self, path=None):
        with io.open(path or self.receipt_path(), encoding="utf-8") as fh:
            return json.load(fh)

    def save(self, data, path=None):
        path = path or self.receipt_path()
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(data, indent=2, sort_keys=True))
        return path

    def reseal(self, data):
        """Recompute the seal so a fixture can isolate ONE control.

        Without this, every edit to a receipt trips the seal as well as the
        thing being tested, and a fixture that fires two controls proves neither.
        """
        sys.path.insert(0, os.path.join(ROOT, "src"))
        try:
            from brothersbe import evidence as mod
            data["runId"] = mod.compute_seal(data)
        finally:
            sys.path.pop(0)
        return data


class TestTheDefect(EvidenceFixture):
    """THE DEFECT THIS CONTROL EXISTS FOR: a receipt can be typed by the same
    agent whose work it verifies, and a fabricated duration, exit code and
    digest satisfy the schema, so a gate PASSes on a run nobody performed."""

    def _plausible(self):
        return {
            "schemaVersion": "1.0",
            "generator": "sbe evidence run",
            "generatorVersion": "1.0.0-rc.1",
            "repository": {"remote": None, "remoteNote": "none", "root": self.repo},
            "baseCommit": self.base,
            "headCommit": self.head,
            "argv": ["pytest", "-q"],
            "startedAt": "2026-07-29T09:00:00Z",
            "endedAt": "2026-07-29T09:00:12Z",
            "startedAtEpoch": 1785315600.0,
            "endedAtEpoch": 1785315612.0,
            "durationSeconds": 12.0,
            "exitCode": 0,
            "toolVersions": {"python": "3.9.6", "sbe": "1.0.0-rc.1"},
            "environment": "macOS-26.5.2-arm64-arm-64bit",
            "stdoutSha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b785"
                            "2b855",
            "stderrSha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b785"
                            "2b855",
            "stdoutBytes": 0,
            "stderrBytes": 0,
            "workingTreeDirty": False,
            "workingTreeDetail": "0 uncommitted path(s)",
            "ciRunId": None,
            "coveredFiles": [{"path": "src/service.py", "sha256": "0" * 64, "note": None}],
            "coveredFilesSource": "the diff",
        }

    def test_a_hand_written_receipt_carrying_no_seal_cannot_pass(self):
        """The receipt is plausible in every field a schema can check. It was
        never produced by a wrapper, and no command ever ran."""
        self.save(self._plausible())
        code, data, text = self.verify()
        self.assertEqual(data["verdict"], "FAIL", text)
        self.assertEqual(code, 1, "a receipt nobody's command produced must not exit 0")
        self.assertIn("runId", json.dumps(data["reasons"]), text)

    def test_a_hand_written_receipt_with_an_invented_seal_cannot_pass(self):
        """The forger knows a runId is expected and types one that looks like a
        digest. Guessing a SHA256 is not writing one."""
        forged = self._plausible()
        forged["runId"] = "f" * 64
        self.save(forged)
        code, data, text = self.verify()
        self.assertEqual(data["verdict"], "FAIL", text)
        self.assertIn("does not match the seal", json.dumps(data["reasons"]), text)

    def test_editing_a_real_receipts_exit_code_breaks_its_seal(self):
        """The likeliest real-world forgery: take a receipt from a run that
        failed and change the one field the gate reads."""
        self.generate(command=["python3", "-c", "import sys; sys.exit(3)"])
        doctored = self.load()
        self.assertEqual(doctored["exitCode"], 3)
        doctored["exitCode"] = 0
        self.save(doctored)
        code, data, text = self.verify()
        self.assertEqual(data["verdict"], "FAIL", text)
        self.assertIn("does not match the seal", json.dumps(data["reasons"]), text)

    def test_the_wrapper_exit_code_is_the_commands_own(self):
        """A failing command must not be laundered into a passing evidence step
        by the fact that a receipt got written about it."""
        _path, code, text = self.generate(
            command=["python3", "-c", "import sys; sys.exit(3)"])
        self.assertEqual(code, 1, text)
        self.assertEqual(self.load()["exitCode"], 3, text)


class TestTheSoundCase(EvidenceFixture):
    def test_a_generated_receipt_verifies_pass_at_the_same_commit(self):
        """The control has to be silent on honest work, or engineers switch it
        off, which is the failure mode that costs the most and shows the least."""
        _path, code, text = self.generate()
        self.assertEqual(code, 0, text)
        code, data, text = self.verify()
        self.assertEqual(data["verdict"], "PASS", text)
        self.assertEqual(code, 0, text)
        self.assertIn("src/service.py",
                      json.dumps(self.load()["coveredFiles"]),
                      "the default coverage is the files changed between base and head")

    def test_the_receipt_records_what_the_run_actually_did(self):
        receipt = self.load(self.generate()[0])
        self.assertEqual(receipt["exitCode"], 0)
        self.assertEqual(receipt["headCommit"], self.head)
        self.assertEqual(receipt["baseCommit"], self.base)
        self.assertGreater(receipt["durationSeconds"], 0,
                           "a wrapper that ran the command knows how long it took")
        self.assertTrue(receipt["startedAt"].endswith("Z"), receipt["startedAt"])
        self.assertTrue(receipt["endedAt"].endswith("Z"), receipt["endedAt"])
        self.assertEqual(receipt["toolVersions"]["python"], "%d.%d.%d" % sys.version_info[:3])
        self.assertTrue(receipt["environment"].strip())

    def test_show_names_the_trust_level_every_time(self):
        path, _code, _text = self.generate()
        proc = self.run_sbe("evidence", "show", path)
        text = self.output(proc)
        self.assertEqual(proc.returncode, 0, text)
        self.assertIn("LOCAL-ADVISORY", text,
                      "a local receipt read as authoritative is the reader being misled by "
                      "the layout rather than the content")
        self.assertIn("trust", text)

    def test_a_ci_run_id_on_a_clean_tree_reads_as_protected(self):
        path, _code, _text = self.generate(env={"SBE_CI_RUN_ID": "gha-4471"})
        self.assertEqual(self.load(path)["ciRunId"], "gha-4471")
        text = self.output(self.run_sbe("evidence", "show", path))
        self.assertIn("PROTECTED-CI", text, text)


class TestStaleness(EvidenceFixture):
    def test_a_receipt_from_an_earlier_commit_fails(self):
        """A receipt only counts as evidence for the commit it was generated
        against. The new commit here touches a file the receipt does not cover,
        so the commit binding is the only control that can fire."""
        self.generate()
        write(self.repo, "docs/notes.md", "unrelated\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "a later commit")
        code, data, text = self.verify()
        self.assertEqual(data["verdict"], "FAIL", text)
        self.assertEqual(code, 1, text)
        self.assertIn("not the current head", json.dumps(data["reasons"]), text)

    def test_a_covered_file_changed_after_the_run_fails(self):
        self.generate()
        time.sleep(0.01)
        write(self.repo, "src/service.py", "def handle():\n    return 2\n")
        code, data, text = self.verify()
        self.assertEqual(data["verdict"], "FAIL", text)
        self.assertEqual(code, 1, text)
        blob = json.dumps(data["reasons"])
        self.assertIn("src/service.py", blob, text)
        self.assertIn("after the evidence was made", blob, text)

    def test_a_deleted_covered_file_fails_rather_than_vanishing(self):
        self.generate()
        os.remove(os.path.join(self.repo, "src", "service.py"))
        code, data, text = self.verify()
        self.assertEqual(data["verdict"], "FAIL", text)
        self.assertIn("no longer exists", json.dumps(data["reasons"]), text)


class TestDirtyTree(EvidenceFixture):
    def test_a_receipt_made_on_a_dirty_tree_is_no_data_and_never_a_pass(self):
        """A dirty-tree receipt covers a state that was never committed and
        nobody else can reproduce. Advisory is NO-DATA here, not a pass."""
        write(self.repo, "src/service.py", "def handle():\n    return 99\n")
        self.generate()
        code, data, text = self.verify()
        self.assertEqual(data["verdict"], "NO-DATA", text)
        self.assertNotEqual(data["verdict"], "PASS")
        self.assertTrue(self.load()["workingTreeDirty"], text)
        self.assertIn("dirty", json.dumps(data["reasons"]), text)

    def test_strict_makes_that_no_data_block(self):
        write(self.repo, "src/service.py", "def handle():\n    return 99\n")
        self.generate()
        code, data, text = self.verify(extra=("--strict",))
        self.assertEqual(data["verdict"], "NO-DATA", text)
        self.assertEqual(code, 1,
                         "under --strict a NO-DATA must block, or protected CI is protecting "
                         "nothing")

    def test_a_ci_run_id_does_not_promote_a_dirty_run(self):
        write(self.repo, "src/service.py", "def handle():\n    return 99\n")
        path, _code, _text = self.generate(env={"SBE_CI_RUN_ID": "gha-9001"})
        text = self.output(self.run_sbe("evidence", "show", path))
        self.assertIn("LOCAL-ADVISORY", text,
                      "a CI job over uncommitted edits is a local run wearing a badge")


class TestMalformed(EvidenceFixture):
    def test_a_receipt_that_is_not_json_fails(self):
        self.save_raw = write(self.out, "receipt.json", "{not json at all")
        code, data, text = self.verify()
        self.assertEqual(data["verdict"], "FAIL", text)
        self.assertEqual(code, 1, text)
        self.assertIn("does not parse", json.dumps(data["reasons"]), text)

    def test_an_unknown_schema_version_fails_rather_than_being_ignored(self):
        self.generate()
        data = self.load()
        data["schemaVersion"] = "9.9"
        self.reseal(data)
        self.save(data)
        code, out, text = self.verify()
        self.assertEqual(out["verdict"], "FAIL", text)
        self.assertIn("not one this build reads", json.dumps(out["reasons"]), text)

    def test_a_missing_receipt_is_reported_and_never_a_pass(self):
        code, data, text = self.verify(path=os.path.join(self.out, "nothing-here.json"))
        self.assertEqual(data["verdict"], "FAIL", text)
        self.assertIn("absent evidence is NO-DATA, never a pass", json.dumps(data["reasons"]),
                      text)

    def test_a_json_array_is_not_a_receipt(self):
        self.save_raw = write(self.out, "receipt.json", "[1, 2, 3]")
        code, data, text = self.verify()
        self.assertEqual(data["verdict"], "FAIL", text)
        self.assertIn("a receipt is a JSON object", json.dumps(data["reasons"]), text)


class TestVacuousFields(EvidenceFixture):
    def test_a_vacuous_required_field_fails_and_names_the_field(self):
        """Resealed on purpose, so the required-field control is the only one
        that can fire and the fixture proves that control rather than the seal."""
        self.generate()
        data = self.load()
        data["environment"] = "   "
        self.reseal(data)
        self.save(data)
        code, out, text = self.verify()
        self.assertEqual(out["verdict"], "FAIL", text)
        blob = json.dumps(out["reasons"])
        self.assertIn("environment", blob, text)
        self.assertNotIn("does not match the seal", blob,
                         "the seal was recomputed, so only the vacuity control should fire")

    def test_a_placeholder_is_not_an_answer(self):
        self.generate()
        data = self.load()
        data["generator"] = "TODO"
        self.reseal(data)
        self.save(data)
        code, out, text = self.verify()
        self.assertEqual(out["verdict"], "FAIL", text)
        self.assertIn("generator", json.dumps(out["reasons"]), text)

    def test_a_zero_exit_code_is_an_answer_and_not_an_absence(self):
        """The direction of error that would break honest work: `0` and `False`
        record something, and a vacuity test using truthiness would reject every
        passing run."""
        self.generate()
        data = self.load()
        self.assertEqual(data["exitCode"], 0)
        self.assertIs(data["workingTreeDirty"], False)
        code, out, text = self.verify()
        self.assertEqual(out["verdict"], "PASS", text)


class TestNoRawOutputLeak(EvidenceFixture):
    SECRET = "sk-live-DEADBEEFCAFE0123456789"

    def _printer(self, stream="stdout"):
        """A command that prints the secret WITHOUT carrying it in its argv.

        The first version of this fixture passed the secret on the command line
        and failed, correctly: `argv` is recorded verbatim, by design and by the
        brief, so a secret typed into a command lands in the receipt no matter
        what the output policy says. That limit is now pinned by its own test
        below and stated in `docs/KNOWN-LIMITS.md`. This fixture tests the thing
        the output policy actually promises: what the command PRINTS.
        """
        holder = write(self.out, "held-secret.txt", self.SECRET)
        return write(self.out, "print_%s.py" % stream,
                     "import io, sys\n"
                     "body = io.open(%r, encoding='utf-8').read()\n"
                     "sys.%s.write(body)\n" % (holder, stream))

    def test_a_secret_printed_by_the_command_never_reaches_the_receipt(self):
        """A receipt is the one artifact everybody is encouraged to share, so a
        token printed by the command must not be persisted into it. Digests
        prove the same bytes came back and carry none of them."""
        path, _code, _text = self.generate(command=["python3", self._printer("stdout")])
        with io.open(path, encoding="utf-8") as fh:
            raw = fh.read()
        self.assertNotIn(self.SECRET, raw,
                         "the receipt persisted the command's raw output, which ships the "
                         "secret to everybody the receipt is shown to")
        self.assertNotIn("DEADBEEF", raw, raw)
        import hashlib
        expected = hashlib.sha256(self.SECRET.encode("utf-8")).hexdigest()
        self.assertEqual(self.load(path)["stdoutSha256"], expected,
                         "the digest must still prove which bytes came back")
        self.assertEqual(self.load(path)["stdoutBytes"], len(self.SECRET))

    def test_stderr_is_digested_too(self):
        path, _code, _text = self.generate(command=["python3", self._printer("stderr")])
        with io.open(path, encoding="utf-8") as fh:
            raw = fh.read()
        self.assertNotIn(self.SECRET, raw, "stderr leaked into the receipt")
        import hashlib
        self.assertEqual(self.load(path)["stderrSha256"],
                         hashlib.sha256(self.SECRET.encode("utf-8")).hexdigest())
        self.assertEqual(self.load(path)["stdoutSha256"],
                         hashlib.sha256(b"").hexdigest(),
                         "an empty stream still gets a digest, so silence and 'not recorded' "
                         "cannot be confused")

    def test_argv_is_recorded_verbatim_which_is_a_limit_not_a_leak_to_ignore(self):
        """The honest other half. `argv` is the exact command, recorded as run,
        because a receipt whose command was paraphrased proves nothing about
        what happened. So a credential passed ON the command line IS persisted.
        This test exists so that limit is a decision somebody made rather than a
        surprise somebody finds."""
        path, _code, _text = self.generate(
            command=["python3", "-c", "print('token=%s')" % self.SECRET])
        with io.open(path, encoding="utf-8") as fh:
            raw = fh.read()
        self.assertIn(self.SECRET, raw,
                      "argv is recorded verbatim; if that ever stops being true the limit in "
                      "docs/KNOWN-LIMITS.md has to change with it")
        self.assertEqual(raw.count(self.SECRET), 1,
                         "the secret is in argv and nowhere else: the printed copy still went "
                         "to a digest")


class TestTheInvariant(EvidenceFixture):
    """One sentence, and the whole control is built to keep it true: a receipt
    only counts as evidence for the commit it was generated against, by a
    wrapper that ran the command itself."""

    def test_there_is_no_way_to_hand_the_wrapper_a_duration_or_an_exit_code(self):
        proc = self.run_sbe("evidence", "run", "--out", self.receipt_path(),
                            "--duration", "12", "--", "python3", "-c", "pass")
        self.assertNotEqual(proc.returncode, 0,
                            "a flag that lets the caller state a duration would reopen the "
                            "whole defect")

    def test_run_without_a_command_refuses_rather_than_writing_an_empty_receipt(self):
        proc = self.run_sbe("evidence", "run", "--out", self.receipt_path(),
                            "--cwd", self.repo)
        self.assertEqual(proc.returncode, 2, self.output(proc))
        self.assertFalse(os.path.exists(self.receipt_path()),
                         "a refused run must not leave a receipt behind")

    def test_the_seal_covers_the_fields_a_forger_would_choose(self):
        sys.path.insert(0, os.path.join(ROOT, "src"))
        try:
            from brothersbe import evidence as mod
            for field in ("argv", "exitCode", "durationSeconds", "headCommit",
                          "stdoutSha256", "coveredFiles", "workingTreeDirty"):
                self.assertIn(field, mod.SEALED_FIELDS,
                              "%s is forgeable without breaking the seal" % field)
        finally:
            sys.path.pop(0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
