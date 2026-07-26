#!/usr/bin/env python3
"""BrotherSBE regression tests. Standard library only (no pip install), matching
the zero-dependency ethos of the tools. Run: python3 tools/test_sbe.py

These exist because an external review found a real secret-leak in the resume
brief that a test would have caught. Each test here guards a claim the project
makes about itself: secrets are redacted, sensitive files are owner-only, project
identity does not collide, and the autosave captures untracked work non-invasively.
"""
import io, os, json, re, stat, sys, tempfile, subprocess, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))

# Import sbe_telemetry as a module regardless of cwd.
spec = importlib.util.spec_from_file_location("sbe_telemetry", os.path.join(HERE, "sbe_telemetry.py"))
bm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bm)
sys.modules["sbe_telemetry"] = bm

import unittest


class TestRedaction(unittest.TestCase):
    def test_secret_shapes_are_masked(self):
        cases = [
            "the prod password is hunter2",
            "PROD_DB_PASSWORD=s3cr3tvalue",
            "sk-ant-api03-ABCDEFGHIJKLMNOP",
            "Authorization: Bearer abcdef1234567890xyz",
            "ssn 123-45-6789",
        ]
        for c in cases:
            clean, n = bm.redact(c)
            self.assertGreater(n, 0, "no redaction fired on: %s" % c)
            self.assertIn("[REDACTED]", clean)
        # a benign correction must survive intact
        clean, n = bm.redact("always use the staging bucket, never production")
        self.assertEqual(n, 0)
        self.assertIn("staging bucket", clean)


class TestResumeBrief(unittest.TestCase):
    def test_brief_redacts_and_is_owner_only(self):
        with tempfile.TemporaryDirectory() as d:
            os.environ["BROTHERSBE_VAULT"] = os.path.join(d, "vault")
            # rebuild the module's paths against the temp vault
            import importlib
            importlib.reload(bm)
            repo = os.path.join(d, "acme", "backend")
            os.makedirs(repo)
            tp = os.path.join(d, "t.jsonl")
            msgs = [{"type": "user", "message": {"content": "the prod password is hunter2"}}]
            msgs += [{"type": "assistant", "message": {"content": [
                {"type": "text", "text": "using token sk-ant-api03-ABCDEFGHIJKLMNOP"},
                {"type": "tool_use", "name": "Bash",
                 "input": {"command": "curl -H 'Authorization: Bearer abcdef1234567890xyz' x"}}]}}]
            io.open(tp, "w").write("\n".join(json.dumps(m) for m in msgs))
            payload = json.dumps({"transcript_path": tp, "cwd": repo})
            old = sys.stdin
            sys.stdin = io.StringIO(payload)
            try:
                bm.cmd_precompact_brief()
            finally:
                sys.stdin = old
            teldir = os.path.join(os.environ["BROTHERSBE_VAULT"], "99-System", "telemetry")
            briefs = [f for f in os.listdir(teldir) if f.startswith("last-resume-")]
            self.assertEqual(len(briefs), 1)
            path = os.path.join(teldir, briefs[0])
            body = io.open(path).read()
            for secret in ("hunter2", "sk-ant-api03-ABCDEFGHIJKLMNOP", "abcdef1234567890xyz"):
                self.assertNotIn(secret, body, "resume brief leaked: %s" % secret)
            self.assertIn("[REDACTED]", body)
            mode = stat.S_IMODE(os.stat(path).st_mode)
            self.assertEqual(mode, 0o600, "resume brief must be owner-only, got %o" % mode)


class TestProjectIdentity(unittest.TestCase):
    def test_same_basename_different_path_no_collision(self):
        a = bm._project_of("/tmp/client-a/backend")
        b = bm._project_of("/tmp/client-b/backend")
        self.assertNotEqual(a, b, "same-basename projects collided: %s == %s" % (a, b))
        self.assertEqual(a, bm._project_of("/tmp/client-a/backend"), "identity must be stable")


class TestAutosave(unittest.TestCase):
    def test_snapshot_captures_untracked_without_touching_tree(self):
        sh = os.path.join(HERE, "sbe_autosave.sh")
        if not os.path.exists(sh):
            self.skipTest("sbe_autosave.sh not present")
        with tempfile.TemporaryDirectory() as repo:
            def git(*a):
                return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True)
            git("init", "-q")
            git("config", "user.email", "t@t.t"); git("config", "user.name", "t")
            io.open(os.path.join(repo, "tracked.txt"), "w").write("v1")
            git("add", "-A"); git("commit", "-qm", "init")
            io.open(os.path.join(repo, "tracked.txt"), "w").write("v2")
            io.open(os.path.join(repo, "untracked_new.txt"), "w").write("WIP-WORK")
            before = git("status", "--porcelain").stdout
            before_head = git("rev-parse", "HEAD").stdout
            vdir = tempfile.mkdtemp()
            env = dict(os.environ, BROTHERSBE_VAULT=vdir)
            subprocess.run(["sh", sh, "precompact"], input=json.dumps({"cwd": repo}),  # sbe: allow-silent test harness fires the hook; the snapshot ref it creates is asserted below
                           text=True, env=env)
            # working tree and branch untouched
            self.assertEqual(before, git("status", "--porcelain").stdout)
            self.assertEqual(before_head, git("rev-parse", "HEAD").stdout)
            # ref created and it contains the untracked file
            ref = git("rev-parse", "-q", "--verify", "refs/brothersbe/autosave")
            self.assertEqual(ref.returncode, 0, "autosave ref was not created")
            shown = git("show", "refs/brothersbe/autosave:untracked_new.txt").stdout
            self.assertIn("WIP-WORK", shown, "autosave did not capture the untracked file")
            # secret-shaped files must NOT enter the snapshot
            io.open(os.path.join(repo, ".env"), "w").write("SECRET=leak")
            subprocess.run(["sh", sh, "precompact"], input=json.dumps({"cwd": repo}),  # sbe: allow-silent test harness fires the hook; the snapshot ref it creates is asserted below
                           text=True, env=env)
            envobj = git("cat-file", "-e", "refs/brothersbe/autosave:.env")
            self.assertNotEqual(envobj.returncode, 0, ".env leaked into the autosave snapshot")


class TestDigestCap(unittest.TestCase):
    def test_digest_fits_the_cap_the_hook_comment_names(self):
        """sbe_sessionstart.sh injects DIGEST.md into session context and its
        own comment names the injection cap. The digest once grew to 16 KB
        while that comment kept promising "we stay far under", so the file
        making the claim contradicted the file it claimed about. This test
        reads the cap out of the hook comment instead of hardcoding a second
        number, so the two cannot disagree again. It does not verify the
        harness's real cap: that figure is the hook comment's own claim."""
        hook = io.open(os.path.join(HERE, "sbe_sessionstart.sh")).read()
        m = re.search(r"(\d+)k char cap", hook)
        self.assertTrue(m, "hook comment no longer names its injection cap")
        cap = int(m.group(1)) * 1000
        size = os.path.getsize(os.path.join(HERE, "..", "DIGEST.md"))
        self.assertLess(size, cap,
                        "DIGEST.md is %d bytes but the hook comment promises a %d cap; "
                        "move the growth into LAWS-REFERENCE.md" % (size, cap))


class TestAutosaveRecover(unittest.TestCase):
    def test_recover_writes_nothing_into_the_source_worktree(self):
        """recover must check the snapshot out into a NEW worktree, never into
        the live one. The old mode printed an in-place `git restore` that could
        delete a tracked file the snapshot never captured; this test pins the
        replacement: source tree byte-identical before and after, no in-place
        restore command in the output, snapshot content present in the new
        worktree. It does not test permissions enforcement (platform-dependent,
        reported by the tool rather than promised)."""
        sh = os.path.join(HERE, "sbe_autosave.sh")
        if not os.path.exists(sh):
            self.skipTest("sbe_autosave.sh not present")
        with tempfile.TemporaryDirectory() as repo:
            def git(*a):
                return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True)
            git("init", "-q")
            git("config", "user.email", "t@t.t"); git("config", "user.name", "t")
            io.open(os.path.join(repo, "tracked.txt"), "w").write("v1")
            git("add", "-A"); git("commit", "-qm", "init")
            io.open(os.path.join(repo, "wip.txt"), "w").write("UNLANDED")
            vdir = tempfile.mkdtemp()
            env = dict(os.environ, BROTHERSBE_VAULT=vdir)
            subprocess.run(["sh", sh, "precompact"], input=json.dumps({"cwd": repo}),  # sbe: allow-silent test harness fires the hook; recover output is asserted below
                           text=True, env=env)
            # Simulate the loss the autosave exists for: the WIP file is gone.
            os.remove(os.path.join(repo, "wip.txt"))
            before_status = git("status", "--porcelain").stdout
            before_files = sorted(os.listdir(repo))
            r = subprocess.run(["sh", sh, "recover", repo], capture_output=True,
                               text=True, env=env)
            # Source worktree byte-identical: recover wrote nothing here.
            self.assertEqual(before_status, git("status", "--porcelain").stdout)
            self.assertEqual(before_files, sorted(os.listdir(repo)))
            # The data-loss path must be gone from the output, not merely warned about.
            self.assertNotIn("--worktree .", r.stdout, "in-place restore path resurfaced")
            self.assertIn("never touched", r.stdout)
            # The new worktree exists and contains the lost work.
            lines = [l.strip() for l in r.stdout.splitlines()]
            wt = next((l for l in lines if os.path.isdir(l)), "")
            self.assertTrue(wt, "recover did not print a recovery worktree path:\n%s" % r.stdout)
            body = io.open(os.path.join(wt, "wip.txt")).read()
            self.assertEqual(body, "UNLANDED")
            git("worktree", "remove", "--force", wt)


class TestHandoff(unittest.TestCase):
    def test_handoff_redacts_and_preserves(self):
        with tempfile.TemporaryDirectory() as v:
            base = os.path.join(v, "10-Projects", "demo", "Sessions")
            os.makedirs(base)
            proj = os.path.dirname(base)
            io.open(os.path.join(proj, "Overview.md"), "w").write(
                "builds X. the prod password is hunter2")
            io.open(os.path.join(base, "s.md"), "w").write("used DB_PASSWORD=s3cr3t here")
            env = dict(os.environ, BROTHERSBE_VAULT=v)
            with tempfile.TemporaryDirectory() as cwd:
                r = subprocess.run([sys.executable, os.path.join(HERE, "sbe_telemetry.py"),
                                    "handoff", "demo"], env=env, cwd=cwd,
                                   capture_output=True, text=True)
                out = os.path.join(cwd, "handoff-demo.md")
                self.assertTrue(os.path.exists(out), "handoff file not written")
                body = io.open(out).read()
                self.assertNotIn("hunter2", body)
                self.assertNotIn("s3cr3t", body)
                self.assertIn("builds X", body)
                self.assertIn("[REDACTED]", body)


class TestStrictMode(unittest.TestCase):
    def test_severity_decides_what_a_strict_run_blocks_on(self):
        """The severity each check declares at write time is what a FAIL does to
        the exit code, and nothing else: advisory runs exit 0 whatever they
        find, --strict blocks on gate severity, and soft severity blocks only
        under the opt-in --strict-soft. A vault with an active session but no
        session log forces a soft FAIL (vault-log-per-active-day); a bare
        except with no waiver forces a gate FAIL (silent-failure-lints)."""
        import datetime
        with tempfile.TemporaryDirectory() as v:
            teld = os.path.join(v, "99-System", "telemetry")
            os.makedirs(teld)
            now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            io.open(os.path.join(teld, "outcomes.jsonl"), "w").write(
                json.dumps({"schema": 2, "ts": now, "session_id": "x", "project": "p",
                            "tool_calls": 5, "api_msgs": 9}) + "\n")
            env = dict(os.environ, BROTHERSBE_VAULT=v, SBE_LINT_ROOT="")
            score = os.path.join(HERE, "sbe_score.py")
            advisory = subprocess.run([sys.executable, score], env=env,
                                      capture_output=True, text=True)
            strict = subprocess.run([sys.executable, score, "--strict"], env=env,
                                    capture_output=True, text=True)
            strict_soft = subprocess.run([sys.executable, score, "--strict", "--strict-soft"],
                                         env=env, capture_output=True, text=True)
            self.assertEqual(advisory.returncode, 0, "advisory mode must never block (exit 0)")
            self.assertEqual(strict.returncode, 0,
                             "--strict must not block on a soft-severity FAIL alone")
            self.assertIn("soft-severity", strict.stdout,
                          "--strict must NAME the soft FAILs it declined to block on")
            self.assertEqual(strict_soft.returncode, 1,
                             "--strict-soft must block on a soft-severity FAIL")
            # A gate-severity FAIL blocks under plain --strict: point the lint at
            # a tree holding an unwaived bare except.
            lintdir = os.path.join(v, "src")
            os.makedirs(lintdir)
            io.open(os.path.join(lintdir, "evil.py"), "w").write(
                "try:\n    f()\nexcept Exception:\n    pass\n")
            env2 = dict(env, SBE_LINT_ROOT=lintdir)
            strict_gate = subprocess.run([sys.executable, score, "--strict"], env=env2,
                                         capture_output=True, text=True)
            self.assertEqual(strict_gate.returncode, 1,
                             "--strict must exit nonzero on a gate-severity FAIL")
            self.assertIn("[severity: gate]", strict_gate.stdout,
                          "the verdict line must print the severity it declared")


if __name__ == "__main__":
    unittest.main(verbosity=2)
