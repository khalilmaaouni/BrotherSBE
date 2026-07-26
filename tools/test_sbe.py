#!/usr/bin/env python3
"""BrotherSBE regression tests. Standard library only (no pip install), matching
the zero-dependency ethos of the tools. Run: python3 tools/test_sbe.py

These exist because an external review found a real secret-leak in the resume
brief that a test would have caught. Each test here guards a claim the project
makes about itself: secrets are redacted, sensitive files are owner-only, project
identity does not collide, and the autosave captures untracked work non-invasively.
"""
import glob, io, os, json, re, stat, sys, tempfile, subprocess, importlib.util

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
            # The ref is namespaced per worktree; resolve it rather than
            # hardcoding an id the test would have to re-derive.
            refs = git("for-each-ref", "--format=%(refname)",
                       "refs/brothersbe/autosave").stdout.split()
            self.assertEqual(len(refs), 1, "expected one autosave ref, got %r" % refs)
            self.assertTrue(refs[0].startswith("refs/brothersbe/autosave/"),
                            "autosave ref is not namespaced per worktree: %r" % refs[0])
            shown = git("show", "%s:untracked_new.txt" % refs[0]).stdout
            self.assertIn("WIP-WORK", shown, "autosave did not capture the untracked file")
            # secret-shaped files must NOT enter the snapshot
            io.open(os.path.join(repo, ".env"), "w").write("SECRET=leak")
            subprocess.run(["sh", sh, "precompact"], input=json.dumps({"cwd": repo}),  # sbe: allow-silent test harness fires the hook; the snapshot ref it creates is asserted below
                           text=True, env=env)
            envobj = git("cat-file", "-e", "%s:.env" % refs[0])
            self.assertNotEqual(envobj.returncode, 0, ".env leaked into the autosave snapshot")


class TestAutosaveExclusions(unittest.TestCase):
    def test_excluded_tracked_files_ride_at_head_and_modern_keys_stay_out(self):
        """Two halves of one review finding. The exclusion list stopped at
        id_rsa/id_dsa, so a fresh id_ed25519 (ssh-keygen's default since
        OpenSSH 8.5) and an .envrc entered the snapshot as permanent git
        objects. And the snapshot was built in a fresh temp index, so a
        TRACKED file matching an exclusion vanished from the snapshot
        entirely, with its unsaved edit, while the comment said tracked files
        were unaffected. Now: the index is seeded from HEAD (excluded tracked
        files ride at their last-committed state), and the modern secret
        shapes stay out."""
        sh = os.path.join(HERE, "sbe_autosave.sh")
        with tempfile.TemporaryDirectory() as repo:
            def git(*a):
                return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True)
            git("init", "-q")
            git("config", "user.email", "t@t.t"); git("config", "user.name", "t")
            io.open(os.path.join(repo, ".env"), "w").write("SECRET=v1")
            io.open(os.path.join(repo, "app.py"), "w").write("print('hi')\n")
            git("add", "-A", "-f"); git("commit", "-qm", "init")
            io.open(os.path.join(repo, ".env"), "w").write("SECRET=v2-unsaved-edit")
            io.open(os.path.join(repo, "id_ed25519"), "w").write("PRIVATE KEY MATERIAL")
            io.open(os.path.join(repo, ".envrc"), "w").write("AWS_SECRET=hunter2")
            io.open(os.path.join(repo, "wip.txt"), "w").write("UNLANDED")
            vdir = tempfile.mkdtemp()
            env = dict(os.environ, BROTHERSBE_VAULT=vdir)
            subprocess.run(["sh", sh, "precompact"], input=json.dumps({"cwd": repo}),  # sbe: allow-silent test harness fires the hook; the ref content is asserted below
                           text=True, env=env)
            ref = git("for-each-ref", "--format=%(refname)",
                      "refs/brothersbe/autosave").stdout.split()[0]
            # tracked excluded file: present at its HEAD state, edit not captured
            shown = git("show", "%s:.env" % ref)
            self.assertEqual(shown.stdout, "SECRET=v1",
                             "tracked excluded file dropped or edit captured: %r" % shown.stdout)
            # modern secret shapes stay out
            for name in ("id_ed25519", ".envrc"):
                r = git("cat-file", "-e", "%s:%s" % (ref, name))
                self.assertNotEqual(r.returncode, 0, "%s leaked into the snapshot" % name)
            # the actual work is captured
            self.assertIn("UNLANDED", git("show", "%s:wip.txt" % ref).stdout)


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
        # The injected block says which version it came from, and that claim
        # tracks the VERSION file rather than a human's memory at cut time.
        version = io.open(os.path.join(HERE, "..", "VERSION")).read().strip()
        digest_head = io.open(os.path.join(HERE, "..", "DIGEST.md")).readline()
        self.assertIn("version %s" % version, digest_head,
                      "DIGEST.md header does not name the version in VERSION (%s)" % version)

    def test_the_law_file_stays_under_its_own_named_ceiling(self):
        """SKILL.md names a byte ceiling for itself in the What-is-not-law
        section, because the law file is the document most able to grow past
        the point where anyone reads it. The ceiling is read out of the text,
        not hardcoded here, so the claim and the assert cannot disagree; a law
        merges with or displaces an existing one rather than accreting."""
        body = io.open(os.path.join(HERE, "..", "SKILL.md")).read()
        m = re.search(r"SKILL\.md\s+stays under ([\d,]+) bytes", body)
        self.assertTrue(m, "SKILL.md no longer names its own byte ceiling")
        ceiling = int(m.group(1).replace(",", ""))
        size = os.path.getsize(os.path.join(HERE, "..", "SKILL.md"))
        self.assertLess(size, ceiling,
                        "SKILL.md is %d bytes, past its own %d ceiling; merge or displace "
                        "a law instead of accreting" % (size, ceiling))


class TestAuditableSurface(unittest.TestCase):
    def test_the_stated_line_count_tracks_the_tree(self):
        """SECURITY.md states the size of the auditable surface instead of only
        inviting the reader to measure it, because an invitation with no
        baseline is not a claim anyone can check. A stated number nothing
        recomputes goes stale silently; this test recomputes it and fails past
        15 percent drift, so the claim degrades loudly. It does not judge
        whether the surface is small, only that the stated figure is true."""
        body = io.open(os.path.join(HERE, "..", "SECURITY.md")).read()
        m = re.search(r"([\d,]+) lines measured", body)
        self.assertTrue(m, "SECURITY.md no longer states the measured line count")
        said = int(m.group(1).replace(",", ""))
        live = 0
        for p in glob.glob(os.path.join(HERE, "*.py")) + glob.glob(os.path.join(HERE, "*.sh")):
            live += sum(1 for _ in io.open(p, errors="replace"))
        drift = abs(live - said) / float(said)
        self.assertLessEqual(drift, 0.15,
                             "tools/ holds %d lines but SECURITY.md says %d (%.0f%% drift); "
                             "re-measure with `wc -l tools/*.py tools/*.sh` and update the "
                             "stated figure" % (live, said, drift * 100))


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


class TestLintSelfSkipThroughSymlink(unittest.TestCase):
    def test_a_symlinked_lint_root_is_the_same_tree(self):
        """The lint excludes its own source by PATH, and abspath does not
        resolve symlinks, so the same tree reached through a symlinked
        spelling (macOS /tmp vs /private/tmp, a bind mount) made the tool scan
        itself: the unwaivable gate FAILed an honest tree, naming four
        "defects" that were its own regex literals, and the self-skip
        disclosure vanished. Both spellings must produce the same verdict and
        both must carry the self-skip disclosure."""
        with tempfile.TemporaryDirectory() as d:
            link = os.path.join(d, "linked-tools")
            os.symlink(HERE, link)
            outputs = []
            for root in (HERE, link):
                r = subprocess.run([sys.executable, os.path.join(HERE, "sbe_score.py")],
                                   env=dict(os.environ, SBE_LINT_ROOT=root,
                                            BROTHERSBE_REGISTRIES=""),
                                   capture_output=True, text=True)
                line = next((l for l in r.stdout.splitlines()
                             if l.startswith("silent-failure-lints")), "")
                self.assertIn("own source was not scanned", line,
                              "self-skip disclosure missing for root %s: %s" % (root, line))
                outputs.append(line.split()[1])   # the verdict token
            self.assertEqual(outputs[0], outputs[1],
                             "one tree, two verdicts, depending on path spelling: %r" % outputs)


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
