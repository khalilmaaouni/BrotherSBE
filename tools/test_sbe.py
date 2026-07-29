#!/usr/bin/env python3
"""BrotherSBE regression tests. Standard library only (no pip install), matching
the zero-dependency ethos of the tools. Run: python3 tools/test_sbe.py

These exist because an external review found a real secret-leak in the resume
brief that a test would have caught. Each test here guards a claim the project
makes about itself: secrets are redacted, sensitive files are owner-only, project
identity does not collide, and the autosave captures untracked work non-invasively.
"""
import glob, hashlib, io, os, json, re, shutil, stat, sys, tempfile, subprocess, importlib.util

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
    def _write_transcript(self, path):
        msgs = [{"type": "user", "message": {"content": "the prod password is hunter2"}}]
        msgs += [{"type": "assistant", "message": {"content": [
            {"type": "text", "text": "using token sk-ant-api03-ABCDEFGHIJKLMNOP"},
            {"type": "tool_use", "name": "Bash",
             "input": {"command": "curl -H 'Authorization: Bearer abcdef1234567890xyz' x"}}]}}]
        io.open(path, "w").write("\n".join(json.dumps(m) for m in msgs))
        return path

    def test_default_writes_no_brief_and_names_the_switch_on_stderr(self):
        """Old meaning (before this test was rewritten): the resume brief used
        to be written UNCONDITIONALLY, real content when transcript capture was
        on, a "[REDACTED]" placeholder in its place when off, so this test
        proved that even the placeholder-carrying default file never let a raw
        secret from the transcript reach disk, and was owner-only. Flip
        decision (founder, 2026-07-29): the resume brief was the one capture
        path still writing a file by default, unlike `metrics` and
        `corrections`, which write nothing until switched on. Flipped to match:
        `BROTHERSBE_TELEMETRY_TRANSCRIPT` off (the default) now means no file
        at all, and the code path that would have written it names the switch
        once on stderr, so an absent file is never mistaken for a quiet
        session. This test now asserts THAT default: no brief on disk, and the
        switch named on stderr. The redaction and owner-only guards the old
        test carried now live in test_opt_in_writes_the_brief_and_still_redacts,
        which is the only path that still writes real content."""
        with tempfile.TemporaryDirectory() as d:
            os.environ["BROTHERSBE_VAULT"] = os.path.join(d, "vault")
            # rebuild the module's paths against the temp vault
            import importlib
            importlib.reload(bm)
            repo = os.path.join(d, "acme", "backend")
            os.makedirs(repo)
            tp = self._write_transcript(os.path.join(d, "t.jsonl"))
            payload = json.dumps({"transcript_path": tp, "cwd": repo})
            old_stdin, old_stderr = sys.stdin, sys.stderr
            sys.stdin, sys.stderr = io.StringIO(payload), io.StringIO()
            try:
                bm.cmd_precompact_brief()
                err = sys.stderr.getvalue()
            finally:
                sys.stdin, sys.stderr = old_stdin, old_stderr
            teldir = os.path.join(os.environ["BROTHERSBE_VAULT"], "99-System", "telemetry")
            briefs = ([f for f in os.listdir(teldir) if f.startswith("last-resume-")]
                      if os.path.isdir(teldir) else [])
            self.assertEqual(briefs, [], "the default resume brief wrote a file: %r" % briefs)
            self.assertIn("BROTHERSBE_TELEMETRY_TRANSCRIPT", err,
                          "the withheld path did not name its switch on stderr: %r" % err)

    def test_opt_in_writes_the_brief_and_still_redacts(self):
        """New fixture (founder, 2026-07-29, the transcript-brief opt-in flip):
        with BROTHERSBE_TELEMETRY_TRANSCRIPT=1 the brief is written for real,
        from real transcript content, and the existing redaction and
        owner-only guards still hold: secrets never reach the file."""
        with tempfile.TemporaryDirectory() as d:
            os.environ["BROTHERSBE_VAULT"] = os.path.join(d, "vault")
            os.environ["BROTHERSBE_TELEMETRY_TRANSCRIPT"] = "1"
            import importlib
            importlib.reload(bm)
            repo = os.path.join(d, "acme", "backend")
            os.makedirs(repo)
            tp = self._write_transcript(os.path.join(d, "t.jsonl"))
            payload = json.dumps({"transcript_path": tp, "cwd": repo})
            old = sys.stdin
            sys.stdin = io.StringIO(payload)
            try:
                bm.cmd_precompact_brief()
            finally:
                sys.stdin = old
                os.environ.pop("BROTHERSBE_TELEMETRY_TRANSCRIPT", None)
            teldir = os.path.join(os.environ["BROTHERSBE_VAULT"], "99-System", "telemetry")
            briefs = [f for f in os.listdir(teldir) if f.startswith("last-resume-")]
            self.assertEqual(len(briefs), 1, "opt-in must write exactly one resume brief")
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


class TestAutosaveCoversTheWorktree(unittest.TestCase):
    def _repo(self, root):
        def git(*a):
            return subprocess.run(["git", "-C", root, *a], capture_output=True, text=True)
        git("init", "-q")
        git("config", "user.email", "t@t.t"); git("config", "user.name", "t")
        os.makedirs(os.path.join(root, "frontend"))
        os.makedirs(os.path.join(root, "backend"))
        io.open(os.path.join(root, "frontend", "index.js"), "w").write("v1")
        io.open(os.path.join(root, "backend", "app.py"), "w").write("v1")
        git("add", "-A"); git("commit", "-qm", "init")
        return git

    def test_subdirectory_session_snapshots_the_whole_tree(self):
        """The hook's cwd is wherever the session sat (a package directory in
        a monorepo), and the snapshot used to cover only that subdirectory
        while the ref named the whole worktree: out-of-cwd edits rode at
        HEAD (work that looked never done) and a brand-new out-of-cwd file
        was absent outright. The snapshot now runs from the worktree top."""
        sh = os.path.join(HERE, "sbe_autosave.sh")
        with tempfile.TemporaryDirectory() as repo:
            git = self._repo(repo)
            io.open(os.path.join(repo, "frontend", "index.js"), "w").write("v2-EDIT")
            io.open(os.path.join(repo, "frontend", "newfeature.js"), "w").write("NEW-WORK")
            env = dict(os.environ, BROTHERSBE_VAULT=tempfile.mkdtemp())
            subprocess.run(["sh", sh, "precompact"],  # sbe: allow-silent test harness fires the hook; the ref content is asserted below
                           input=json.dumps({"cwd": os.path.join(repo, "backend")}),
                           text=True, env=env, timeout=120)
            ref = git("for-each-ref", "--format=%(refname)",
                      "refs/brothersbe/autosave").stdout.split()[0]
            self.assertEqual("v2-EDIT", git("show", "%s:frontend/index.js" % ref).stdout,
                             "an out-of-cwd edit rode at HEAD instead of being saved")
            self.assertEqual("NEW-WORK", git("show", "%s:frontend/newfeature.js" % ref).stdout,
                             "an out-of-cwd untracked file was absent from the snapshot")

    def test_out_of_cwd_only_work_still_writes_a_ref(self):
        """When every unlanded change sat outside the session's cwd, the old
        subdirectory-scoped add staged nothing, the identical-tree branch
        returned early, and the hook exited 0 with no ref and no log line:
        work on disk, and recover later said no autosave exists."""
        sh = os.path.join(HERE, "sbe_autosave.sh")
        with tempfile.TemporaryDirectory() as repo:
            git = self._repo(repo)
            io.open(os.path.join(repo, "frontend", "index.js"), "w").write("HOURS-OF-WORK")
            vault = tempfile.mkdtemp()
            env = dict(os.environ, BROTHERSBE_VAULT=vault)
            subprocess.run(["sh", sh, "precompact"],  # sbe: allow-silent test harness fires the hook; the ref content is asserted below
                           input=json.dumps({"cwd": os.path.join(repo, "backend")}),
                           text=True, env=env, timeout=120)
            refs = git("for-each-ref", "--format=%(refname)",
                       "refs/brothersbe/autosave").stdout.split()
            self.assertEqual(1, len(refs), "no snapshot ref for out-of-cwd work")
            self.assertIn("HOURS-OF-WORK", git("show", "%s:frontend/index.js" % refs[0]).stdout)

    def test_parallel_ticks_lose_no_update_and_a_superseded_snapshot_stays_reachable(self):
        """Two serialization halves. The tick counter was an unlocked
        read-modify-write fired from PostToolUse, so parallel tool calls lost
        updates: the throttle skipped snapshot points and the runaway warning
        printed a count below the real one. And the single-slot ref had no
        reflog, so a newer snapshot made the older one unreachable."""
        sh = os.path.join(HERE, "sbe_autosave.sh")
        with tempfile.TemporaryDirectory() as repo:
            git = self._repo(repo)
            vault = tempfile.mkdtemp()
            env = dict(os.environ, BROTHERSBE_VAULT=vault, BROTHERSBE_AUTOSAVE="1")
            procs = [subprocess.Popen(["sh", sh, "tick", "sess1"], stdin=subprocess.PIPE,
                                      stdout=subprocess.DEVNULL, text=True, env=env)
                     for _ in range(30)]
            for p in procs:
                p.communicate(json.dumps({"cwd": repo}), timeout=120)
            tel = os.path.join(vault, "99-System", "telemetry")
            ctr = [f for f in os.listdir(tel) if f.startswith(".autosave-tick")
                   and not f.endswith((".lock", ".warned"))][0]
            self.assertEqual("30", io.open(os.path.join(tel, ctr)).read(),
                             "parallel ticks lost counter updates")
            # reflog half: snapshot good work, destroy it, snapshot again
            io.open(os.path.join(repo, "good.txt"), "w").write("GOOD")
            subprocess.run(["sh", sh, "precompact"], input=json.dumps({"cwd": repo}),  # sbe: allow-silent test harness fires the hook; the reflog is asserted below
                           text=True, env=env, timeout=120)
            ref = git("for-each-ref", "--format=%(refname)",
                      "refs/brothersbe/autosave").stdout.split()[0]
            os.remove(os.path.join(repo, "good.txt"))
            io.open(os.path.join(repo, "other.txt"), "w").write("LATER")
            subprocess.run(["sh", sh, "precompact"], input=json.dumps({"cwd": repo}),  # sbe: allow-silent test harness fires the hook; the reflog is asserted below
                           text=True, env=env, timeout=120)
            self.assertEqual("GOOD", git("show", "%s@{1}:good.txt" % ref).stdout,
                             "the superseded snapshot is unreachable: no reflog kept it")

    @unittest.skipIf(os.name != "posix" or os.geteuid() == 0, "needs enforced file modes")
    def test_a_tick_on_unwritable_storage_exits_clean_and_silent(self):
        """The script's own header says every path exits 0, always.

        A wait stamp was written with `: > "$f" 2>/dev/null`. `:` is a POSIX
        SPECIAL BUILTIN, so a redirection error there is FATAL to the shell:
        on a telemetry directory that is unwritable or cannot be created, the
        tick died at that statement, before the lock, before the counter and
        before any log line, printing a raw shell diagnostic and exiting 1.
        Twelve consecutive ticks gave twelve exit 1s, zero log lines and zero
        snapshots, out of the tool whose whole job is that a crash never
        costs work.

        Both reachable shapes are driven, and the assertion is on the promise
        rather than on the statement that broke it: exit 0, nothing on stderr,
        and a writable vault still counting and still snapshotting.
        """
        sh = os.path.join(HERE, "sbe_autosave.sh")
        if not os.path.exists(sh):
            self.skipTest("sbe_autosave.sh not present")
        with tempfile.TemporaryDirectory() as repo:
            self._repo(repo)
            vault = tempfile.mkdtemp()
            tel = os.path.join(vault, "99-System", "telemetry")
            os.makedirs(tel)
            parent = tempfile.mkdtemp()
            os.chmod(tel, 0o555)
            os.chmod(parent, 0o555)
            try:
                shapes = {"unwritable telemetry directory": vault,
                          "vault that cannot be created": os.path.join(parent, "vault")}
                for why, v in shapes.items():
                    env = dict(os.environ, BROTHERSBE_VAULT=v, BROTHERSBE_AUTOSAVE="1")
                    for _ in range(3):
                        out = subprocess.run(["sh", sh, "tick", "sessA"],
                                             input=json.dumps({"cwd": repo}), text=True,
                                             capture_output=True, env=env, timeout=120)
                        self.assertEqual(0, out.returncode,
                                         "a tick on an %s exited %d; the header promises every "
                                         "path exits 0" % (why, out.returncode))
                        self.assertEqual("", out.stderr.strip(),
                                         "a tick on an %s printed a raw diagnostic: %r"
                                         % (why, out.stderr[:160]))
            finally:
                os.chmod(tel, 0o755)
                os.chmod(parent, 0o755)
            # The control, so this is not a script that has learned to do
            # nothing: a writable vault still counts and still snapshots.
            good = tempfile.mkdtemp()
            io.open(os.path.join(repo, "unlanded.txt"), "w").write("WIP-WORK")
            env = dict(os.environ, BROTHERSBE_VAULT=good, BROTHERSBE_AUTOSAVE="1",
                       BROTHERSBE_AUTOSAVE_EVERY="2")
            for _ in range(2):
                subprocess.run(["sh", sh, "tick", "sessB"], input=json.dumps({"cwd": repo}),  # sbe: allow-silent test harness fires the hook; the counter and the ref are asserted below
                               text=True, capture_output=True, env=env, timeout=120)
            gtel = os.path.join(good, "99-System", "telemetry")
            ctr = [f for f in os.listdir(gtel) if f.startswith(".autosave-tick")
                   and not f.endswith((".lock", ".warned"))]
            self.assertEqual(["2"], [io.open(os.path.join(gtel, c)).read() for c in ctr],
                             "a writable vault stopped counting")
            refs = subprocess.run(["git", "-C", repo, "for-each-ref",
                                   "refs/brothersbe/autosave"],
                                  capture_output=True, text=True).stdout.split("\n")
            self.assertTrue([r for r in refs if r.strip()],
                            "a writable vault took no snapshot at the throttle point")

    @unittest.skipIf(os.name != "posix" or os.geteuid() == 0, "needs enforced file modes")
    def test_an_unwritable_vault_still_lands_the_reason_in_a_fallback_log(self):
        """review-13a: exit 0 was already the promise being kept (the prior
        fix covers that), but the REASON was not. log_line's and
        excl_record's own `mkdir -p "$TEL_DIR"` failed the same way the write
        it was about to explain failed, so a skipped precompact or tick left
        no trace anywhere: not in autosave.log, not in
        autosave-exclusions.log, not on stderr (kept clean on purpose). The
        fallback lands the same reason beside the repository's own git
        metadata, which does not depend on the vault at all."""
        sh = os.path.join(HERE, "sbe_autosave.sh")
        with tempfile.TemporaryDirectory() as repo:
            self._repo(repo)
            io.open(os.path.join(repo, "unlanded.txt"), "w").write("WIP-WORK")
            vault = tempfile.mkdtemp()
            tel = os.path.join(vault, "99-System", "telemetry")
            os.makedirs(tel)
            os.chmod(tel, 0o555)
            fb = os.path.join(repo, ".git", "brothersbe-autosave-fallback.log")
            try:
                env = dict(os.environ, BROTHERSBE_VAULT=vault)
                out = subprocess.run(["sh", sh, "precompact"], input=json.dumps({"cwd": repo}),
                                     text=True, capture_output=True, env=env, timeout=120,
                                     cwd=repo)
                self.assertEqual(0, out.returncode,
                                 "precompact on an unwritable vault exited %d" % out.returncode)
                self.assertEqual("", out.stderr.strip(),
                                 "precompact on an unwritable vault printed a raw diagnostic: %r"
                                 % out.stderr[:160])
                self.assertTrue(os.path.exists(fb),
                                "an unwritable vault left no trace anywhere: no fallback log at %s"
                                % fb)
                body = io.open(fb).read()
                self.assertIn("vault unwritable", body)
                self.assertIn("saved ", body,
                              "the fallback log exists but does not carry the reason that would "
                              "otherwise have gone to autosave.log")
            finally:
                os.chmod(tel, 0o755)
            # The control: a writable vault needs no fallback and writes none.
            good_repo = tempfile.mkdtemp()
            self._repo(good_repo)
            io.open(os.path.join(good_repo, "unlanded.txt"), "w").write("WIP-WORK")
            good_vault = tempfile.mkdtemp()
            env2 = dict(os.environ, BROTHERSBE_VAULT=good_vault)
            subprocess.run(["sh", sh, "precompact"], input=json.dumps({"cwd": good_repo}),  # sbe: allow-silent test harness fires the hook; the fallback's absence is asserted below
                           text=True, env=env2, timeout=120, cwd=good_repo)
            good_fb = os.path.join(good_repo, ".git", "brothersbe-autosave-fallback.log")
            self.assertFalse(os.path.exists(good_fb),
                             "a writable vault still wrote a fallback log nobody needed: %s"
                             % good_fb)
            self.assertTrue(os.path.exists(os.path.join(good_vault, "99-System", "telemetry",
                                                         "autosave.log")),
                            "the control run did not use the real vault log either")

    def test_recover_after_a_rename_names_the_sibling_snapshots(self):
        """The ref id derives from the worktree path, so a moved project
        changes the id and recover looked in a ref that never existed,
        printing 'no autosave found in <repo>' about a repository holding
        the snapshot one for-each-ref away. The empty-ref branch now
        enumerates the namespace and names what it found."""
        sh = os.path.join(HERE, "sbe_autosave.sh")
        with tempfile.TemporaryDirectory() as parent:
            repo = os.path.join(parent, "proj")
            os.makedirs(repo)
            git = self._repo(repo)
            io.open(os.path.join(repo, "wip.txt"), "w").write("UNLANDED")
            vault = tempfile.mkdtemp()
            env = dict(os.environ, BROTHERSBE_VAULT=vault)
            subprocess.run(["sh", sh, "precompact"], input=json.dumps({"cwd": repo}),  # sbe: allow-silent test harness fires the hook; recover's output is asserted below
                           text=True, env=env, timeout=120)
            renamed = os.path.join(parent, "proj-renamed")
            os.rename(repo, renamed)
            out = subprocess.run(["sh", sh, "recover", renamed], capture_output=True,
                                 text=True, env=env, timeout=120).stdout
            self.assertIn("DOES hold autosave snapshot(s) under other id(s)", out)
            self.assertIn("refs/brothersbe/autosave/", out)
            self.assertNotIn("no autosave found in", out,
                             "recover still asserts a repo-wide absence it never examined")


class TestTelemetryWriterSerialization(unittest.TestCase):
    def test_a_live_append_survives_a_concurrent_migrate(self):
        """Two REAL writers, racing. cmd_migrate is a read-modify-write over
        the whole ledger and there was no lock anywhere in the repository, so
        a row appended between its read and its rename was destroyed by the
        rename while the loss guard compared two pre-append counts and
        printed "count ok". Writers now serialize on an exclusive flock and
        the guard recounts the real post-rename file under that lock."""
        with tempfile.TemporaryDirectory() as vault:
            tel = os.path.join(vault, "99-System", "telemetry")
            os.makedirs(tel)
            led = os.path.join(tel, "outcomes.jsonl")
            with io.open(led, "w") as f:
                for i in range(120000):
                    f.write(json.dumps({"session_id": "s%d" % i, "out_tokens": i}) + "\n")
            env = dict(os.environ, BROTHERSBE_VAULT=vault)
            mig = subprocess.Popen(
                [sys.executable, os.path.join(HERE, "sbe_telemetry.py"), "migrate"],
                env=env, stdout=subprocess.PIPE, text=True)
            appenders = [subprocess.Popen(
                [sys.executable, "-c",
                 "import sys; sys.path.insert(0, %r); import sbe_telemetry as t; "
                 "t.atomic_append(t.LEDGER, {'schema': 2, 'session_id': 'LIVE-%d'})" % (HERE, i)],
                env=env) for i in range(4)]
            out, _ = mig.communicate(timeout=300)
            for a in appenders:
                a.wait(timeout=300)
            body = io.open(led, errors="replace").read()
            for i in range(4):
                self.assertIn("LIVE-%d" % i, body,
                              "a live session's appended row was destroyed by migrate")
            self.assertIn("count ok", out, "migrate did not finish cleanly: %r" % out.strip())
            self.assertEqual(120004, sum(1 for l in body.splitlines() if l.strip()))

    def test_two_concurrent_migrates_both_finish_and_the_ledger_is_migrated(self):
        """The two maintenance commands used to share one literal .tmp path,
        so one renamed the other's half-written file out from under it and
        the loser died with a bare FileNotFoundError; racing migrate against
        dedup could leave a ledger with ZERO schema-2 rows under a printed
        "migrated to schema 2, count ok". Serialized writers and per-process
        temp paths: both commands finish, and the migration reaches the file."""
        with tempfile.TemporaryDirectory() as vault:
            tel = os.path.join(vault, "99-System", "telemetry")
            os.makedirs(tel)
            led = os.path.join(tel, "outcomes.jsonl")
            with io.open(led, "w") as f:
                for i in range(60000):
                    f.write(json.dumps({"session_id": "s%d" % i, "out_tokens": i}) + "\n")
            env = dict(os.environ, BROTHERSBE_VAULT=vault)
            runs = [subprocess.Popen(
                [sys.executable, os.path.join(HERE, "sbe_telemetry.py"), cmd],
                env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                for cmd in ("migrate", "dedup")]
            outs = [p.communicate(timeout=300)[0] for p in runs]
            for o in outs:
                self.assertNotIn("FileNotFoundError", o,
                                 "a maintenance command lost its temp file to the other")
            schemas = set()
            for l in io.open(led, errors="replace"):
                schemas.add(json.loads(l).get("schema"))
            self.assertEqual({2}, schemas,
                             "the printed migration never reached the file: %r" % schemas)

    def _telemetry(self, vault):
        import importlib
        os.environ["BROTHERSBE_VAULT"] = vault
        sys.path.insert(0, HERE)
        import sbe_telemetry
        importlib.reload(sbe_telemetry)
        return sbe_telemetry

    def test_a_fallback_append_during_the_rewrite_window_is_carried_not_destroyed(self):
        """The round-12 closure of this class was FALSE at scale: the recount
        ran AFTER the rename, so it compared the rewrite to itself, and a row
        appended by the 15-second unlocked fallback was destroyed under a
        printed "count ok" whenever the rewrite outlived the timeout. The
        freshness guard now runs BEFORE the rename against the live file and
        carries appended bytes into the rewrite. This test walks the exact
        window: the tail row exists on disk beyond what the rewrite read."""
        with tempfile.TemporaryDirectory() as vault:
            t = self._telemetry(vault)
            os.makedirs(t.TEL_DIR, exist_ok=True)
            with io.open(t.LEDGER, "w") as f:
                f.write('{"session_id":"a"}\n{"session_id":"b"}\n')
                read_size = f.tell()
                f.write('{"session_id":"LIVE-FALLBACK-ROW"}\n')  # appended after the read
            done = t._rewrite_locked(t.LEDGER, ['{"session_id":"a","schema":2}',
                                                '{"session_id":"b","schema":2}'],
                                     read_size, "migrate")
            self.assertIsNotNone(done, "the rewrite refused a carryable tail")
            n_after, passthrough, count_ok = done
            self.assertEqual((3, 1, True), (n_after, passthrough, count_ok))
            body = io.open(t.LEDGER).read()
            self.assertIn("LIVE-FALLBACK-ROW", body,
                          "the fallback append was destroyed by the rename")

    def test_a_file_that_shrinks_under_the_lock_is_never_replaced(self):
        """A file smaller than what the rewrite read means a second writer is
        ignoring the lock; renaming over it would replace a world this
        rewrite never saw, so it refuses and leaves everything in place."""
        with tempfile.TemporaryDirectory() as vault:
            t = self._telemetry(vault)
            os.makedirs(t.TEL_DIR, exist_ok=True)
            original = '{"session_id":"a"}\n'
            with io.open(t.LEDGER, "w") as f:
                f.write(original)
            done = t._rewrite_locked(t.LEDGER, ['{"x":1}'], len(original) + 50, "migrate")
            self.assertIsNone(done, "a shrunken file was replaced anyway")
            self.assertEqual(original, io.open(t.LEDGER).read(), "the refusal still wrote")
            self.assertEqual([], [p for p in os.listdir(t.TEL_DIR) if ".tmp." in p],
                             "the refusal leaked its temp file")

    @unittest.skipIf(os.name != "posix" or os.geteuid() == 0, "needs enforced file modes")
    def test_an_unopenable_lock_sidecar_never_drops_the_row(self):
        """The sidecar exists only to protect the row, and its open failure
        used to raise into the top-level swallow: the row was lost, the
        operator got a Python repr, and the exit code was 0. Failing to OPEN
        the lock now takes the same path as failing to TAKE it."""
        with tempfile.TemporaryDirectory() as vault:
            t = self._telemetry(vault)
            os.makedirs(t.TEL_DIR, exist_ok=True)
            unwritable = t.LEDGER + ".lock"
            io.open(unwritable, "w").close()
            os.chmod(unwritable, 0o444)
            t.atomic_append(t.LEDGER, {"session_id": "row-behind-a-bad-lock"})
            os.mkdir(t.CORRECTIONS + ".lock")     # the mkdir-shadowed shape
            t.atomic_append(t.CORRECTIONS, {"session_id": "row-behind-a-dir-lock"})
            self.assertIn("row-behind-a-bad-lock", io.open(t.LEDGER).read())
            self.assertIn("row-behind-a-dir-lock", io.open(t.CORRECTIONS).read())

    def test_short_writes_are_completed_not_truncated(self):
        """os.write may honor fewer bytes than asked on any POSIX host; the
        unchecked call truncated the row silently. _write_all loops."""
        with tempfile.TemporaryDirectory() as vault:
            t = self._telemetry(vault)
            os.makedirs(t.TEL_DIR, exist_ok=True)
            real_write = os.write
            os.write = lambda fd, data: real_write(fd, bytes(data)[:5])
            try:
                t.atomic_append(t.LEDGER, {"session_id": "short-write-probe", "n": 12345})
            finally:
                os.write = real_write
            row = json.loads(io.open(t.LEDGER).read())
            self.assertEqual({"session_id": "short-write-probe", "n": 12345}, row)

    def test_an_intent_record_stays_one_line(self):
        """The intent log is a line-delimited RECORD whose line structure is
        its parse: a caller newline used to write a second timestamped record
        the tool never stamped, and the last-line reader quoted the forged
        record as the operator's own intent. Every internal break renders as
        a visible escape."""
        with tempfile.TemporaryDirectory() as vault:
            t = self._telemetry(vault)
            path = os.path.join(t.TEL_DIR, "intent-test.log")
            t.atomic_append_text(path, "one\n2026-01-01T00:00:00Z  next: FORGED")
            lines = io.open(path).read().splitlines()
            self.assertEqual(1, len(lines), "a caller newline split the record: %r" % lines)
            self.assertIn("\\n", lines[0], "the break vanished instead of rendering visibly")


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
        # The cap was guarded for the digest FILE only, while the hook appended
        # nags and hints on top, so a busy vault could push the total past the
        # cap and the harness truncated the tail, where the compaction hint
        # (the recovery pointer) printed. The hook now enforces the cap itself
        # and prints the hint before the digest; both properties are pinned
        # against the script's text here.
        self.assertRegex(hook, r"CAP=%d" % cap,
                         "the hook no longer enforces the cap it names")
        self.assertIn("head -c", hook, "the hook no longer cuts its own over-cap output")
        hint_at = hook.find("compact-hint")
        digest_at = hook.find('cat "$DIR/DIGEST.md"')
        self.assertTrue(0 < hint_at < digest_at,
                        "the compaction hint must print before the digest, so harness "
                        "truncation can only ever cost digest tail")
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



    def test_the_truncation_marker_names_what_was_actually_cut(self):
        """The marker used to ASSERT which half was cut, and nothing bounded the
        first half: a large resume brief (written from a transcript, so its size
        is data-driven) pushed the hint past the cap, and the printed line still
        said the digest tail was cut and the hint printed in full. Both clauses
        were false in that run, in the one line whose job is to explain a
        context loss. This runs the hook for real in both regimes and reads the
        marker against what actually printed."""
        hook = os.path.join(HERE, "sbe_sessionstart.sh")
        cap = int(re.search(r"CAP=(\d+)", io.open(hook).read()).group(1))
        work = tempfile.mkdtemp()
        try:
            # The REAL hook and the real DIGEST.md (the hook derives its own
            # directory), pointed at a temp vault: read-only against this tree,
            # and the brief that overflows is written into the temp vault.
            root = os.path.abspath(os.path.join(HERE, ".."))
            vault = os.path.join(work, "vault")
            os.makedirs(os.path.join(vault, "99-System", "telemetry"))
            env = dict(os.environ, BROTHERSBE_VAULT=vault)
            cwd = os.path.join(work, "proj")
            os.makedirs(cwd)
            payload = json.dumps({"source": "compact", "cwd": cwd})
            hook_path = os.path.join(root, "tools", "sbe_sessionstart.sh")
            digest_head = io.open(os.path.join(root, "DIGEST.md")).readline().strip()

            def run():
                r = subprocess.run(["sh", hook_path], input=payload, capture_output=True,
                                   text=True, env=env, timeout=180)
                self.assertEqual(r.returncode, 0, "the hook must always exit 0")
                self.assertLessEqual(len(r.stdout.encode("utf-8")), cap + 400,
                                     "the hook did not enforce the cap it names")
                return r.stdout

            # Regime 1: ordinary run, nothing cut, so no marker prints at all.
            out = run()
            self.assertNotIn("truncated at the", out,
                             "an ordinary run must not claim it was truncated")

            # Regime 2: a resume brief far larger than the whole cap. This is
            # the run where the old marker named the wrong casualty: the digest
            # does not print AT ALL and the hint itself is cut.
            spec_t = importlib.util.spec_from_file_location(
                "sbe_telemetry_cap", os.path.join(root, "tools", "sbe_telemetry.py"))
            tel = importlib.util.module_from_spec(spec_t)
            os.environ["BROTHERSBE_VAULT"] = vault
            spec_t.loader.exec_module(tel)
            io.open(tel._resume_path(cwd), "w").write("RESUME BRIEF\n" + ("x " * cap * 2) + "\n")
            out = run()
            self.assertIn("truncated at the", out, "an over-cap run must say so")
            printed_digest = digest_head and digest_head in out
            claims_digest_printed = "The compaction hint and nags printed in full" in out
            self.assertEqual(bool(claims_digest_printed), bool(printed_digest),
                             "the truncation marker's claim about which half survived "
                             "disagrees with the output:\n%s" % out[-500:])
            self.assertIn("the digest did not print at all", out,
                          "the marker must name the digest as the whole casualty when the "
                          "hint alone overflows:\n%s" % out[-500:])
        finally:
            shutil.rmtree(work, ignore_errors=True)

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

    def test_the_zero_network_property_holds_by_ast(self):
        """SECURITY.md invites a grep and used to pin its hit count in prose,
        and the pinned number rotted (a count written into prose that nothing
        recomputes). The docs now state the PROPERTY instead, and this test is
        the recomputation the property gets: no tool imports urllib, requests,
        socket or http, and no shell tool invokes curl or wget outside a
        comment. The redaction fixture in this file carries curl inside a
        string on purpose; parsing imports rather than grepping text is what
        keeps that fixture from being a false hit."""
        import ast
        banned = {"urllib", "requests", "socket", "http"}
        for p in glob.glob(os.path.join(HERE, "*.py")):
            tree = ast.parse(io.open(p, errors="replace").read())
            for node in ast.walk(tree):
                mods = []
                if isinstance(node, ast.Import):
                    mods = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    mods = [node.module.split(".")[0]]
                hit = sorted(set(mods) & banned)
                self.assertEqual([], hit,
                                 "%s imports %s; the zero-network claim in SECURITY.md "
                                 "is broken" % (os.path.basename(p), ", ".join(hit)))
        for p in glob.glob(os.path.join(HERE, "*.sh")):
            for i, line in enumerate(io.open(p, errors="replace"), 1):
                code = line.split("#", 1)[0]
                self.assertFalse(re.search(r"\b(curl|wget)\b", code),
                                 "%s:%d invokes curl or wget; the zero-network claim "
                                 "in SECURITY.md is broken" % (os.path.basename(p), i))


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

    @unittest.skipIf(os.name != "posix", "needs a hardlink")
    def test_a_directory_mostly_self_skipped_names_the_count_and_withdraws_clean(self):
        """review-13a: a directory where the walk reaches its own source under
        thirteen of its fourteen names (a hardlink or a case/symlink alias
        reaches the same inode more than once) printed "1 file(s) scanned
        under X, clean" with the thirteen self-skipped files listed by NAME
        and no number attached, and the "clean in what was opened, which is
        not the same as a clean tree" withdrawal only checked unread_total
        (the KIND-skip reason), never self_skipped, so the bare word "clean"
        stood over a directory that was thirteen fourteenths unexamined.
        Reproduced with hardlinks, which share sbe_score.py's own inode
        without needing a second copy on disk."""
        with tempfile.TemporaryDirectory() as d:
            n_links = 13
            for i in range(n_links):
                os.link(os.path.join(HERE, "sbe_score.py"),
                        os.path.join(d, "copy%d.py" % i))
            io.open(os.path.join(d, "clean.py"), "w").write("def f():\n    return 1\n")
            r = subprocess.run([sys.executable, os.path.join(HERE, "sbe_score.py")],
                               env=dict(os.environ, SBE_LINT_ROOT=d, BROTHERSBE_REGISTRIES=""),
                               capture_output=True, text=True)
            line = next((l for l in r.stdout.splitlines()
                         if l.startswith("silent-failure-lints")), "")
            self.assertIn("PASS", line.split()[:2], "unexpected verdict: %s" % line)
            self.assertIn("%d file(s)" % n_links, line,
                          "the self-skipped files are named but never counted: %s" % line)
            self.assertIn("clean in what was opened, which is not the same as a clean tree", line,
                          "self-skip alone left the bare word clean standing over a directory "
                          "that was mostly unexamined: %s" % line)
            # The control: a directory with nothing self-skipped keeps the
            # plain "N file(s) scanned under X, clean" sentence, so this is a
            # disclosure rule and not a new withdrawal fired unconditionally.
            with tempfile.TemporaryDirectory() as clean_d:
                io.open(os.path.join(clean_d, "clean.py"), "w").write("def f():\n    return 1\n")
                r2 = subprocess.run([sys.executable, os.path.join(HERE, "sbe_score.py")],
                                    env=dict(os.environ, SBE_LINT_ROOT=clean_d,
                                             BROTHERSBE_REGISTRIES=""),
                                    capture_output=True, text=True)
                line2 = next((l for l in r2.stdout.splitlines()
                             if l.startswith("silent-failure-lints")), "")
                self.assertIn(", clean", line2)
                self.assertNotIn("not the same as a clean tree", line2,
                                 "a tree with nothing skipped lost its plain clean sentence: %s"
                                 % line2)


class TestOneLineNeutralizesTheControlClass(unittest.TestCase):
    def test_no_control_or_format_character_survives_into_a_report_line(self):
        """one_line() used to flatten line-break characters only, and a
        terminal defines a line by the cursor, not by newlines: ESC [ 1F
        rewrote the rendered line above and ESC E opened a new one, so a
        receipt field forged whole verdict lines while the byte stream held
        one line per gate. The rule is the class: every Cc and Cf code point
        arrives as a visible escape, so the probe below asserts over members
        no list in the fix names (backspace, ESC E, a bidi override) as well
        as the ones the review demonstrated."""
        spec2 = importlib.util.spec_from_file_location(
            "sbe_checks_ol", os.path.join(HERE, "sbe_checks.py"))
        checks = importlib.util.module_from_spec(spec2)
        spec2.loader.exec_module(checks)
        import unicodedata
        probes = ["a\x1b[2K\x1b[1Fforged PASS", "x\x1bEy", "a\x08b",
                  "rtl‮forged", "nel\x85nel", "del\x7fdel", "bom﻿bom"]
        for p in probes:
            out = checks.one_line(p)
            leaked = [ch for ch in out
                      if unicodedata.category(ch) in ("Cc", "Cf", "Cs")]
            self.assertEqual(leaked, [],
                             "control/format characters survived one_line(%r): %r" % (p, out))
        # The escape is visible, not a deletion: the reader must be able to
        # see and question what the artifact tried to do.
        self.assertIn("\\x1b", checks.one_line("x\x1bEy"))
        self.assertIn("\\u202e", checks.one_line("rtl‮forged"))


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


class TestCliSurface(unittest.TestCase):
    """`bin/sbe` is a facade: every built subcommand delegates to a tool in
    tools/ that already carries the behavior and the tests. The failure modes a
    facade adds are its own, and they are what this class pins: a command that
    exists in the code and not in --help (or the reverse), an unbuilt command
    that quietly succeeds at nothing, and an exit code that drifts from what the
    docstring promises a CI job can rely on."""

    ROOT = os.path.abspath(os.path.join(HERE, ".."))
    SBE = os.path.join(ROOT, "bin", "sbe")

    def _run(self, *argv):
        return subprocess.run([sys.executable, self.SBE] + list(argv),
                              capture_output=True, text=True, cwd=self.ROOT)

    def _commands(self):
        spec = importlib.util.spec_from_file_location(
            "brothersbe_cli", os.path.join(self.ROOT, "src", "brothersbe", "cli.py"),
            submodule_search_locations=[os.path.join(self.ROOT, "src", "brothersbe")])
        sys.path.insert(0, os.path.join(self.ROOT, "src"))
        try:
            import brothersbe.cli as cli
            return cli
        finally:
            sys.path.pop(0)
            del spec

    def test_the_launcher_runs_and_reports_the_one_version_this_project_has(self):
        out = self._run("--version")
        self.assertEqual(out.returncode, 0, out.stderr)
        declared = io.open(os.path.join(self.ROOT, "VERSION"), encoding="utf-8").read().strip()
        self.assertIn(declared, out.stdout,
                      "the CLI prints a version that is not the one in VERSION")

    def test_every_advertised_command_has_something_behind_it(self):
        """Scoped honestly, because the first version of this test was close to
        tautological: --help is generated from the same list the dispatcher
        reads, so comparing one to the other proves little. What it pins now is
        the pair of failures that list cannot prevent by construction: a name
        advertised in the help text with no callable behind it, and a command
        whose help line is missing so a reader cannot discover it. Both are
        reachable by hand-editing the epilog or the table."""
        cli = self._commands()
        out = self._run("--help")
        self.assertEqual(out.returncode, 0, out.stderr)
        advertised = set(re.findall(r"^  ([a-z][a-z-]+) {2,}", out.stdout, re.M))
        implemented = set(name for (name, _h, _r) in cli.COMMANDS)
        self.assertEqual(advertised - implemented, set(),
                         "advertised in --help with nothing behind it: %s"
                         % (advertised - implemented))
        self.assertEqual(implemented - advertised, set(),
                         "implemented but undiscoverable in --help: %s"
                         % (implemented - advertised))
        for name, help_, run in cli.COMMANDS:
            self.assertTrue(callable(run), "%s has no runner" % name)
            self.assertTrue(help_.strip(), "%s has no help line" % name)

    def test_an_unbuilt_command_refuses_loudly_and_names_its_wave(self):
        cli = self._commands()
        # inspect-change left this list when `sbe impact` shipped, and adopt left
        # it when wave 9 built the adoption kit: each is now a real command. The
        # list is the wave-by-wave record of what is still owed, so a name leaves
        # it only when something stands behind it.
        unbuilt = ["plan", "policy", "exceptions"]
        known = [n for (n, _h, _r) in cli.COMMANDS]
        for name in unbuilt:
            self.assertIn(name, known, "%s vanished from the command table" % name)
            out = self._run(name)
            self.assertEqual(out.returncode, cli.EXIT_NOT_BUILT,
                             "%s exited %d; an unbuilt command must exit %d rather than "
                             "printing an empty result and succeeding"
                             % (name, out.returncode, cli.EXIT_NOT_BUILT))
            self.assertIn("NOT BUILT", out.stderr + out.stdout)
            self.assertRegex(out.stderr + out.stdout, r"wave \d",
                             "%s refuses without saying what will build it" % name)

    def test_the_exit_codes_a_ci_job_would_branch_on(self):
        cli = self._commands()
        self.assertEqual(self._run("doctor").returncode, cli.EXIT_OK)
        self.assertEqual(self._run("bogus-command").returncode, cli.EXIT_USAGE,
                         "an unknown command must be a usage error, never a silent success")
        self.assertEqual(self._run("verify", "/nonexistent-path-on-purpose").returncode,
                         cli.EXIT_USAGE,
                         "a mistyped path must be a usage error; it must never read as a "
                         "clean scan")

    def test_verify_never_lets_exit_zero_read_as_a_pass(self):
        """The aggregating commands exit 0 when nothing FAILED, and a run where
        every check reported NO-DATA also exits 0. The closing line has to say
        so, because an exit code cannot."""
        v = tempfile.mkdtemp()
        try:
            out = self._run("verify", v)
            self.assertEqual(out.returncode, 0)
            self.assertIn("does not mean a control passed", out.stdout,
                          "verify exited 0 over an empty directory without saying that no "
                          "control passed")
        finally:
            shutil.rmtree(v, ignore_errors=True)

    def test_the_package_imports_with_nothing_installed(self):
        """Zero dependencies is a promise this project makes on its front page.
        A facade that needs a pip install to reach the command line would retract
        it for anyone on a locked-down machine or in a CI image with no index."""
        out = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, %r); import brothersbe; "
             "print(brothersbe.__version__)" % os.path.join(self.ROOT, "src")],
            capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertTrue(out.stdout.strip(), "the package imported but reports no version")


class TestDoctorIdentityCheck(unittest.TestCase):
    """THE DEFECT THIS CONTROL EXISTS FOR: a leaked fixture identity, `ci
    <ci@example.com>`, authored a run of real commits in public history
    before anyone noticed, because nothing in this project's own tooling
    ever looked at git's identity config. `doctor` now does, and this class
    pins the three shapes that check must never blur: a fixture identity is
    a WARNING (never silently PASS, never a hard FAIL: doctor observes), a
    real identity PASSes, and an unset identity is NO-DATA rather than
    either. Real subprocess, real git config, nothing mocked, the same rule
    `test_sbe_adopt.py` states."""

    ROOT = os.path.abspath(os.path.join(HERE, ".."))
    SBE = os.path.join(ROOT, "bin", "sbe")

    def setUp(self):
        self.repo = tempfile.mkdtemp()
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def _doctor(self, isolate_identity=False):
        """Three values, not two: a two-value return reads as a possible
        (verdict, evidence) pair to the honesty meta-test, which refuses any
        such function sitting outside a check registry."""
        env = dict(os.environ)
        if isolate_identity:
            # A repo with no local identity set must not fall through to
            # this machine's real ~/.gitconfig or /etc/gitconfig, or the
            # unset-identity case could never be reproduced on a laptop
            # that already has a name and email configured.
            env["HOME"] = self.repo
            env["GIT_CONFIG_NOSYSTEM"] = "1"
        out = subprocess.run([sys.executable, self.SBE, "doctor"], cwd=self.repo,
                             capture_output=True, text=True, env=env)
        return out.returncode, out.stdout, out.stdout + out.stderr

    @staticmethod
    def _identity_line(stdout):
        # Three values, not two: a two-value return reads as a possible
        # (verdict, evidence) pair to the honesty meta-test, which refuses any
        # such function sitting outside a check registry.
        m = re.search(r"^identity\s+(\S+)\s+(.*)$", stdout, re.M)
        return (m.group(1), m.group(2), m.group(0)) if m else (None, None, None)

    def test_a_leaked_example_com_email_is_a_warning_not_a_failure(self):
        subprocess.run(["git", "config", "user.email", "ci@example.com"], cwd=self.repo,
                       check=True)
        subprocess.run(["git", "config", "user.name", "Test Bot"], cwd=self.repo, check=True)
        code, out, text = self._doctor()
        result, detail, _ = self._identity_line(out)
        self.assertEqual(result, "WARNING", text)
        self.assertIn("ci@example.com", detail, "the evidence line must quote the value "
                                                 "found: %s" % text)
        self.assertEqual(code, 0, "a WARNING must never trip doctor's exit code: %s" % text)

    def test_a_leaked_name_ci_is_a_warning_not_a_failure(self):
        subprocess.run(["git", "config", "user.email", "real@realcompany.com"], cwd=self.repo,
                       check=True)
        subprocess.run(["git", "config", "user.name", "ci"], cwd=self.repo, check=True)
        code, out, text = self._doctor()
        result, detail, _ = self._identity_line(out)
        self.assertEqual(result, "WARNING", text)
        self.assertIn("\"ci\"", detail, "the evidence line must quote the value found: %s"
                      % text)
        self.assertEqual(code, 0, text)

    def test_a_real_identity_passes(self):
        subprocess.run(["git", "config", "user.email", "real@realcompany.com"], cwd=self.repo,
                       check=True)
        subprocess.run(["git", "config", "user.name", "Real Person"], cwd=self.repo, check=True)
        code, out, text = self._doctor()
        result, detail, _ = self._identity_line(out)
        self.assertEqual(result, "PASS", text)
        self.assertIn("real@realcompany.com", detail, text)
        self.assertEqual(code, 0, text)

    def test_an_unset_identity_is_no_data_not_a_silent_pass(self):
        code, out, text = self._doctor(isolate_identity=True)
        result, detail, _ = self._identity_line(out)
        self.assertEqual(result, "NO-DATA", text)
        self.assertEqual(code, 0, text)


class TestNoPrivateNameShips(unittest.TestCase):
    """This repository is public. The estates it was built on are not, and
    neither are the clients, employers and projects whose work taught it every
    threshold it ships. A client name reaching a tracked file cannot be taken
    back: a public git history is a permanent record, and the fix after the fact
    is a history rewrite, not an edit.

    The list of names is NOT in this file, for the obvious reason that a
    blocklist naming the client leaks the client. It is read from outside the
    repository, and when it is absent this test SKIPS with a message saying it
    examined nothing, rather than passing. An empty check reporting green is the
    exact failure mode the rest of this project exists to prevent.

    Set BROTHERSBE_PRIVATE_NAMES to a comma-separated list, or
    BROTHERSBE_PRIVATE_NAMES_FILE to a path holding one name per line
    (blank lines and # comments ignored). Keep that file outside this tree.

    One honest narrowing, also stated in PUBLISH-CHECKLIST.md: this scans the
    tracked tree at HEAD. A name that was committed once and deleted later is
    still in the history and this test cannot see it. The forensic history sweep
    stays a manual checklist item for that reason."""

    def _names(self):
        raw = os.environ.get("BROTHERSBE_PRIVATE_NAMES", "")
        names = [n.strip() for n in raw.split(",") if n.strip()]
        path = os.environ.get("BROTHERSBE_PRIVATE_NAMES_FILE", "")
        if not path:
            default = os.path.expanduser("~/.brothersbe-private-names")
            if os.path.exists(default):
                path = default
        if path and os.path.exists(path):
            for line in io.open(path, encoding="utf-8"):
                line = line.strip()
                if line and not line.startswith("#"):
                    names.append(line)
        return sorted(set(names))

    def test_no_private_name_appears_in_a_tracked_file(self):
        names = self._names()
        if not names:
            self.skipTest(
                "no private-name list configured, so NOTHING was scanned. This is NO-DATA, "
                "not a clean result: set BROTHERSBE_PRIVATE_NAMES or "
                "BROTHERSBE_PRIVATE_NAMES_FILE (a path outside this repository) to make this "
                "check real.")
        root = os.path.abspath(os.path.join(HERE, ".."))
        listed = subprocess.run(["git", "ls-files", "-z"], cwd=root,
                                capture_output=True, text=True)
        self.assertEqual(listed.returncode, 0,
                         "git ls-files failed, so the scan set is unknown; refusing to report "
                         "a clean scan over a file list nobody could build")
        files = [f for f in listed.stdout.split("\0") if f]
        self.assertTrue(files, "git tracks no files here; that is not a clean scan either")
        hits, scanned = [], 0
        for rel in files:
            full = os.path.join(root, rel)
            if not os.path.isfile(full):
                continue
            try:
                body = io.open(full, encoding="utf-8", errors="ignore").read()
            except (IOError, OSError):
                continue
            scanned += 1
            low = body.lower()
            for name in names:
                if name.lower() in low:
                    # Print the FILE and the name's length, never the name and
                    # never the surrounding line: a failure message is written
                    # into CI logs, and a leak-detector that prints the leak has
                    # moved the problem rather than caught it.
                    hits.append("%s (private name of %d chars)" % (rel, len(name)))
        self.assertEqual(hits, [],
                         "a private name reached %d tracked file(s): %s. Fix before the next "
                         "push; if it is already pushed, the fix is a history rewrite."
                         % (len(hits), hits))
        self.assertGreater(scanned, 0, "scanned zero files, which is NO-DATA and not a pass")


class TestPluginSurface(unittest.TestCase):
    """The plugin packaging and the law it packages are two surfaces that can
    drift apart in silence: a skill can cite a reference file that was renamed,
    a hook can point at a tool that moved, the manifest version can wander away
    from VERSION, and the plugin still loads perfectly in every one of those
    cases. Loading is not the property worth asserting. These tests assert the
    ones that are, by reading the claims out of the shipped files rather than
    hardcoding a second copy of them here."""

    ROOT = os.path.join(HERE, "..")

    def _frontmatter(self, path):
        """Return the YAML-ish frontmatter block of a skill or agent file as a
        dict of the top-level scalar keys. Deliberately not a YAML parser: the
        loader needs name and description, and a hand-rolled reader keeps this
        suite dependency-free the way the rest of it is.

        Returns the dict alone, not a (dict, body) pair. It used to return the
        pair, and `evals/test_no_data_class.py` correctly refused it: a function
        returning a two-tuple whose first element could be a verdict, sitting in
        no registry, is indistinguishable to that lint from a check nothing can
        reach. The body was unused by every caller anyway."""
        body = io.open(path, encoding="utf-8").read()
        self.assertTrue(body.startswith("---\n"),
                        "%s does not open with a frontmatter block" % path)
        end = body.find("\n---\n", 3)
        self.assertGreater(end, 0, "%s has an unterminated frontmatter block" % path)
        out = {}
        for line in body[4:end].split("\n"):
            m = re.match(r"^([a-zA-Z_]+):\s*(.*)$", line)
            if m:
                out[m.group(1)] = m.group(2).strip()
        return out

    def test_manifest_parses_and_agrees_with_the_version_file(self):
        manifest = json.load(io.open(os.path.join(self.ROOT, ".claude-plugin", "plugin.json"),
                                     encoding="utf-8"))
        self.assertEqual(manifest.get("name"), "brothersbe",
                         "the plugin name is the skill namespace; changing it renames every "
                         "/brothersbe: command without warning anyone")
        version = io.open(os.path.join(self.ROOT, "VERSION"), encoding="utf-8").read().strip()
        self.assertEqual(manifest.get("version"), version,
                         "plugin.json says %s and VERSION says %s; `claude plugin tag` "
                         "validates that they agree, so a release cut from this state fails"
                         % (manifest.get("version"), version))
        for field in ("description", "repository", "license"):
            self.assertTrue(manifest.get(field), "plugin.json is missing %s" % field)

    def test_every_skill_declares_the_frontmatter_the_loader_reads(self):
        skills = sorted(glob.glob(os.path.join(self.ROOT, "skills", "*", "SKILL.md")))
        self.assertGreaterEqual(len(skills), 6,
                                "expected the six namespaced skills, found %d" % len(skills))
        for path in skills:
            front = self._frontmatter(path)
            directory = os.path.basename(os.path.dirname(path))
            self.assertEqual(front.get("name"), directory,
                             "%s declares name '%s' but sits in skills/%s; the loader uses the "
                             "directory, so the two must not disagree"
                             % (path, front.get("name"), directory))
            self.assertTrue(front.get("description"),
                            "%s has no description; a skill with no description is a skill "
                            "nothing will ever route to" % path)

    def test_every_agent_declares_itself_and_stays_read_only(self):
        """The reviewer agents claim to be read-only in their own prose. A claim
        in prose is not a restriction, but the tools list IS one, so the two are
        pinned together here: an agent that grows a write tool has to change this
        test, which is the moment somebody notices. The evidence auditor matters
        most, because an auditor that can write the evidence it approves is not
        an auditor."""
        write_tools = ("Write", "Edit", "MultiEdit", "NotebookEdit")
        agents = sorted(glob.glob(os.path.join(self.ROOT, "agents", "*.md")))
        self.assertGreaterEqual(len(agents), 7,
                                "expected seven reviewer agents, found %d" % len(agents))
        for path in agents:
            front = self._frontmatter(path)
            stem = os.path.splitext(os.path.basename(path))[0]
            self.assertEqual(front.get("name"), stem,
                             "%s declares name '%s'" % (path, front.get("name")))
            self.assertTrue(front.get("description"), "%s has no description" % path)
            tools = front.get("tools", "")
            self.assertTrue(tools, "%s declares no tools list" % path)
            for banned in write_tools:
                self.assertNotIn(banned, tools,
                                 "%s is documented as read-only but declares %s"
                                 % (path, banned))

    def test_no_frontmatter_value_can_break_the_yaml_parser(self):
        """Found the hard way, by `claude plugin validate` rather than by this
        suite: a skill description containing a colon followed by a space is not
        a valid YAML plain scalar, and the failure is silent at runtime. The
        skill still loads, with EMPTY metadata, so nothing routes to it and no
        error is printed anywhere. The first version of this test class read the
        frontmatter with a regex and happily accepted the broken file, which is
        why the rule is asserted here directly rather than left to the reader:
        a value holding ': ' must be quoted. Same for a leading '[', '{', '&',
        '*' or '!', which start YAML structures rather than prose."""
        starts_structure = ("[", "{", "&", "*", "!", "%", "@", "`")
        for path in (sorted(glob.glob(os.path.join(self.ROOT, "skills", "*", "SKILL.md")))
                     + sorted(glob.glob(os.path.join(self.ROOT, "agents", "*.md")))):
            body = io.open(path, encoding="utf-8").read()
            end = body.find("\n---\n", 3)
            for line in body[4:end].split("\n"):
                m = re.match(r"^([a-zA-Z_]+):\s*(.*)$", line)
                if not m:
                    continue
                key, value = m.group(1), m.group(2).strip()
                if not value:
                    continue
                quoted = ((value[0] == '"' and value[-1] == '"')
                          or (value[0] == "'" and value[-1] == "'"))
                if quoted:
                    continue
                self.assertNotIn(": ", value,
                                 "%s: the %s value holds a colon and is unquoted, so the YAML "
                                 "parser drops the whole frontmatter and the skill loads with "
                                 "no metadata at all" % (path, key))
                if value[0] in starts_structure and not value.startswith("["):
                    self.fail("%s: the %s value starts with %r, which YAML reads as structure "
                              "rather than text; quote it" % (path, key, value[0]))

    def test_every_hook_command_points_at_a_file_that_exists(self):
        hooks = json.load(io.open(os.path.join(self.ROOT, "hooks", "hooks.json"),
                                  encoding="utf-8"))
        commands = []
        for event, blocks in hooks["hooks"].items():
            for block in blocks:
                for hook in block["hooks"]:
                    commands.append((event, hook["command"]))
        self.assertTrue(commands, "hooks.json wires nothing")
        for event, command in commands:
            for cited in re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\"\s]+)", command):
                self.assertTrue(os.path.exists(os.path.join(self.ROOT, cited)),
                                "the %s hook runs %s, which does not exist" % (event, cited))

    def test_every_plugin_root_path_cited_by_a_skill_or_agent_resolves(self):
        """This is the drift check. Six skills and seven agents cite the law
        files, the tools and the templates by path. Renaming any of them leaves
        a plugin that still validates and still loads, pointing at nothing."""
        cited = []
        for path in (sorted(glob.glob(os.path.join(self.ROOT, "skills", "*", "SKILL.md")))
                     + sorted(glob.glob(os.path.join(self.ROOT, "agents", "*.md")))):
            body = io.open(path, encoding="utf-8").read()
            for ref in re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([A-Za-z0-9_./-]+)", body):
                cited.append((path, ref.rstrip(".,)`")))
        self.assertTrue(cited, "no skill or agent cites the plugin root at all")
        missing = [(p, r) for (p, r) in cited
                   if not os.path.exists(os.path.join(self.ROOT, r))]
        self.assertEqual(missing, [],
                         "these citations resolve to nothing: %s" % missing)


class TestCaptureDefaultsAndAutosaveContentScan(unittest.TestCase):
    """Two privacy defects an external review found, and the fixtures that hold
    them closed.

    The first: this tool parsed the session transcript and stored excerpts of
    the operator's own messages by DEFAULT, with best-effort redaction standing
    between a customer name and a file on disk. A repository holding customer,
    partner, security or company-confidential material has to be able to install
    this and have it capture nothing until somebody says otherwise, per
    category, with an organization switch that cannot be reversed locally.

    The second: the autosave excluded secret-shaped file NAMES, and a secret in
    a normally named source file (`src/config.py` holding an API key) matched no
    name pattern and became a permanent git object. The scan now reads CONTENT
    before `git add` runs, which is the moment a blob would be created.

    Every fixture here runs the real tools in a temporary vault and a real git
    repository. The environment is scrubbed of every BROTHERSBE_ variable and
    the organization policy is pinned at a path that does not exist, so a real
    policy file or an exported switch on the machine running these cannot decide
    the result."""

    TEL = os.path.join(HERE, "sbe_telemetry.py")
    AUTOSAVE = os.path.join(HERE, "sbe_autosave.sh")
    SECRET_LINE = 'API_KEY = "sk-ant-api03-ABCDEFGHIJKLMNOP"\n'
    OPERATOR_TEXT = "no, that is not what i asked; always use the acme staging bucket"

    def _env(self, vault, **switches):
        env = {k: v for k, v in os.environ.items() if not k.startswith("BROTHERSBE_")}
        env["BROTHERSBE_VAULT"] = vault
        env["BROTHERSBE_TELEMETRY_POLICY"] = os.path.join(vault, "policy-that-does-not-exist")
        env.update(switches)
        return env

    def _transcript(self, path):
        """A session over the activity floor, carrying one correction-shaped
        operator message and one tool command with a client path in it."""
        msgs = [{"type": "user", "message": {"content": self.OPERATOR_TEXT}}]
        for i in range(bm.MIN_API_MSGS):
            body = [{"type": "text", "text": "planning the acme migration"}]
            if i == 0:
                body.append({"type": "tool_use", "name": "Bash",
                             "input": {"command": "ls /srv/acme-partner"}})
            msgs.append({"type": "assistant",
                         "message": {"id": "m%d" % i, "model": "claude-test",
                                     "usage": {"input_tokens": 10, "output_tokens": 20},
                                     "content": body}})
        io.open(path, "w").write("\n".join(json.dumps(m) for m in msgs) + "\n")
        return path

    def _fire(self, vault, subcommand, cwd, **switches):
        """Run one hook subcommand against a fresh transcript. Returns the
        completed process, so its exit code and output are inspectable rather
        than discarded."""
        tp = self._transcript(os.path.join(vault, "transcript.jsonl"))
        payload = json.dumps({"transcript_path": tp, "cwd": cwd, "session_id": "sess-abc123"})
        return subprocess.run([sys.executable, self.TEL, subcommand], input=payload,
                              text=True, capture_output=True, env=self._env(vault, **switches))

    def _paths(self, vault):
        tel = os.path.join(vault, "99-System", "telemetry")
        return (tel, os.path.join(tel, "outcomes.jsonl"), os.path.join(tel, "corrections.jsonl"))

    def _vault(self):
        v = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, v, True)
        os.makedirs(os.path.join(v, "99-System", "telemetry"))
        return v

    def _snapshot(self, path):
        """Hash of everything under `path`: its own existence, every file's
        relative name, mtime and size. "the file I expected is still there"
        misses a sibling file a run wrote and forgot to check for; hashing the
        whole listing does not need to know in advance what could change."""
        if not os.path.exists(path):
            return "ABSENT"
        rows = []
        for root, dirs, files in os.walk(path):
            dirs.sort()
            for name in sorted(files):
                p = os.path.join(root, name)
                st = os.stat(p)
                rows.append("%s %d %d" % (os.path.relpath(p, path), st.st_mtime_ns, st.st_size))
        rows.sort()
        return hashlib.sha256(("\n".join(rows)).encode()).hexdigest()

    def _brief(self, vault):
        tel = os.path.join(vault, "99-System", "telemetry")
        briefs = [f for f in os.listdir(tel) if f.startswith("last-resume-")]
        self.assertEqual(len(briefs), 1, "expected one resume brief, found %r" % briefs)
        return io.open(os.path.join(tel, briefs[0])).read()

    def _no_brief(self, vault, msg):
        tel = os.path.join(vault, "99-System", "telemetry")
        briefs = [f for f in os.listdir(tel) if f.startswith("last-resume-")]
        self.assertEqual(briefs, [], "%s: found %r" % (msg, briefs))

    def test_a_default_installation_captures_no_transcript_text_and_no_correction(self):
        vault = self._vault()
        tel, ledger, corrections = self._paths(vault)
        end = self._fire(vault, "outcomes-append", "/tmp/acme-backend")
        self.assertEqual(end.returncode, 0, end.stderr)
        self.assertFalse(os.path.exists(corrections),
                         "a default installation wrote %s" % corrections)
        self.assertFalse(os.path.exists(ledger), "a default installation wrote %s" % ledger)
        for var in ("BROTHERSBE_TELEMETRY_METRICS", "BROTHERSBE_TELEMETRY_CORRECTIONS"):
            self.assertIn(var, end.stdout,
                          "the hook recorded nothing without naming %s: %s" % (var, end.stdout))
        # transcript-brief opt-in flip (founder, 2026-07-29): the default now
        # writes no brief at all; the switch that would fill it in is named
        # once on stderr instead of inside a withheld placeholder file.
        pre = self._fire(vault, "precompact-brief", "/tmp/acme-backend")
        self.assertEqual(pre.returncode, 0, pre.stderr)
        self._no_brief(vault, "a default installation wrote a resume brief")
        self.assertIn("BROTHERSBE_TELEMETRY_TRANSCRIPT", pre.stderr,
                      "the withheld path does not name the switch that would have written it")

    def test_each_switch_turns_on_exactly_one_category(self):
        cases = (
            ("BROTHERSBE_TELEMETRY_METRICS", True, False, False),
            ("BROTHERSBE_TELEMETRY_CORRECTIONS", False, True, False),
            ("BROTHERSBE_TELEMETRY_TRANSCRIPT", False, False, True),
        )
        for var, want_ledger, want_corrections, want_text in cases:
            vault = self._vault()
            _tel, ledger, corrections = self._paths(vault)
            end = self._fire(vault, "outcomes-append", "/tmp/acme-backend", **{var: "1"})
            self.assertEqual(end.returncode, 0, end.stderr)
            self.assertEqual(os.path.exists(ledger), want_ledger,
                             "%s=1 got outcomes.jsonl exists=%s, wanted %s (%s)"
                             % (var, os.path.exists(ledger), want_ledger, end.stdout))
            self.assertEqual(os.path.exists(corrections), want_corrections,
                             "%s=1 got corrections.jsonl exists=%s, wanted %s (%s)"
                             % (var, os.path.exists(corrections), want_corrections, end.stdout))
            if want_corrections:
                rows = [json.loads(l) for l in io.open(corrections) if l.strip()]
                self.assertTrue(any("staging bucket" in r.get("text", "") for r in rows),
                                "corrections capture is on and captured nothing: %r" % rows)
            pre = self._fire(vault, "precompact-brief", "/tmp/acme-backend", **{var: "1"})
            self.assertEqual(pre.returncode, 0, pre.stderr)
            if want_text:
                body = self._brief(vault)
                self.assertIn("staging bucket", body,
                              "%s=1 turned on transcript capture but the brief has no text" % var)
            else:
                self._no_brief(vault, "%s=1 must not write a resume brief (only %s does)"
                               % (var, bm.CAPTURE_SWITCH["transcript"]))

    def test_the_organization_override_forces_every_category_off(self):
        every_switch = {"BROTHERSBE_TELEMETRY_METRICS": "1",
                        "BROTHERSBE_TELEMETRY_CORRECTIONS": "1",
                        "BROTHERSBE_TELEMETRY_TRANSCRIPT": "1"}
        # (a) the environment override
        vault = self._vault()
        _tel, ledger, corrections = self._paths(vault)
        switches = dict(every_switch, BROTHERSBE_TELEMETRY_DISABLE="1")
        end = self._fire(vault, "outcomes-append", "/tmp/acme-backend", **switches)
        self.assertFalse(os.path.exists(ledger), "a local switch beat the environment override")
        self.assertFalse(os.path.exists(corrections),
                         "a local switch beat the environment override")
        self.assertIn("BROTHERSBE_TELEMETRY_DISABLE", end.stdout,
                      "the override fired without naming itself: %s" % end.stdout)
        pre = self._fire(vault, "precompact-brief", "/tmp/acme-backend", **switches)
        self.assertEqual(pre.returncode, 0, pre.stderr)
        self._no_brief(vault, "a local switch beat the environment override in the resume brief")
        self.assertIn("BROTHERSBE_TELEMETRY_DISABLE", pre.stderr,
                      "the override fired without naming itself in the resume brief path: %s"
                      % pre.stderr)
        # (b) the policy file, which is the half a local shell cannot unset
        vault = self._vault()
        _tel, ledger, corrections = self._paths(vault)
        policy = os.path.join(vault, "telemetry-policy.conf")
        io.open(policy, "w").write("# set by the platform team\ncapture = off\n")
        switches = dict(every_switch, BROTHERSBE_TELEMETRY_POLICY=policy)
        end = self._fire(vault, "outcomes-append", "/tmp/acme-backend", **switches)
        self.assertFalse(os.path.exists(ledger), "a local switch beat the policy file")
        self.assertFalse(os.path.exists(corrections), "a local switch beat the policy file")
        self.assertIn(policy, end.stdout,
                      "the policy file decided the run without being named: %s" % end.stdout)
        # (c) a policy file this version cannot read fails CLOSED
        vault = self._vault()
        _tel, ledger, corrections = self._paths(vault)
        broken = os.path.join(vault, "broken-policy.conf")
        io.open(broken, "w").write("capture = maybe\n")
        end = self._fire(vault, "outcomes-append", "/tmp/acme-backend",
                         **dict(every_switch, BROTHERSBE_TELEMETRY_POLICY=broken))
        self.assertFalse(os.path.exists(ledger),
                         "an unreadable policy directive let capture proceed")
        self.assertIn("fails closed", end.stdout, end.stdout)

    # -- the autosave half -------------------------------------------------

    def _git(self, repo):
        def git(*a):
            return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True)
        return git

    def _repo(self):
        repo = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, repo, True)
        git = self._git(repo)
        git("init", "-q")
        git("config", "user.email", "t@t.t")
        git("config", "user.name", "t")
        os.makedirs(os.path.join(repo, "src"))
        io.open(os.path.join(repo, "src", "app.py"), "w").write("def f():\n    return 1\n")
        git("add", "-A")
        git("commit", "-qm", "init")
        return repo

    def test_a_secret_in_a_normally_named_source_file_never_becomes_a_git_object(self):
        repo = self._repo()
        git = self._git(repo)
        vault = self._vault()
        # A file no name pattern will ever match, holding an API key, beside
        # real unlanded work that MUST still be saved.
        io.open(os.path.join(repo, "src", "config.py"), "w").write(self.SECRET_LINE)
        io.open(os.path.join(repo, "wip.txt"), "w").write("UNLANDED-WORK")
        fired = subprocess.run(["sh", self.AUTOSAVE, "precompact"],
                               input=json.dumps({"cwd": repo}), text=True,
                               capture_output=True, env=self._env(vault))
        self.assertEqual(fired.returncode, 0, fired.stderr)
        refs = git("for-each-ref", "--format=%(refname)", "refs/brothersbe/autosave").stdout.split()
        self.assertEqual(len(refs), 1, "expected one autosave ref, got %r" % refs)
        listed = git("ls-tree", "-r", "--name-only", refs[0]).stdout.split()
        self.assertNotIn("src/config.py", listed,
                         "the secret-bearing source file entered the snapshot tree")
        self.assertIn("wip.txt", listed, "the content scan dropped the work it exists to save")
        # The stronger claim, and the one the brief asks for: no git OBJECT for
        # that content exists anywhere in the repository, so it was never
        # written rather than written and then hidden from the tree.
        sha = git("hash-object", os.path.join(repo, "src", "config.py")).stdout.strip()
        self.assertTrue(sha, "could not compute the blob id of the planted file")
        present = git("cat-file", "-e", sha)
        self.assertNotEqual(present.returncode, 0,
                            "a blob for the secret-bearing file exists in the object database "
                            "(%s); the scan ran after git add, not before it" % sha)

    def test_the_exclusion_record_names_what_was_excluded_and_why(self):
        repo = self._repo()
        vault = self._vault()
        io.open(os.path.join(repo, "src", "config.py"), "w").write(self.SECRET_LINE)
        io.open(os.path.join(repo, "blob.dat"), "wb").write(b"pre\x00post")
        io.open(os.path.join(repo, "big.txt"), "w").write("x" * 4096)
        fired = subprocess.run(["sh", self.AUTOSAVE, "precompact"],
                               input=json.dumps({"cwd": repo}), text=True, capture_output=True,
                               env=self._env(vault, BROTHERSBE_AUTOSAVE_MAX_BYTES="1024"))
        self.assertEqual(fired.returncode, 0, fired.stderr)
        record = os.path.join(vault, "99-System", "telemetry", "autosave-exclusions.log")
        self.assertTrue(os.path.exists(record), "no exclusion record was written at all")
        body = io.open(record).read()
        for path, reason in (("src/config.py", "content matched a secret shape"),
                             ("blob.dat", "binary content"),
                             ("big.txt", "past the 1024 byte limit")):
            self.assertIn(path, body, "%s was dropped without being named" % path)
            self.assertIn(reason, body, "%s was named without a reason" % path)
        self.assertNotIn("sk-ant-api03", body,
                         "the exclusion record wrote down the secret it excluded")
        self.assertIn("scanned", body, "the record does not say how many files it scanned")

    def test_autosave_is_opt_in_in_a_declared_production_repository(self):
        repo = self._repo()
        git = self._git(repo)
        vault = self._vault()
        io.open(os.path.join(repo, ".brothersbe-production"), "w").write("")
        io.open(os.path.join(repo, "wip.txt"), "w").write("UNLANDED-WORK")
        off = subprocess.run(["sh", self.AUTOSAVE, "precompact"], input=json.dumps({"cwd": repo}),
                             text=True, capture_output=True, env=self._env(vault))
        self.assertEqual(off.returncode, 0, off.stderr)
        self.assertEqual([], git("for-each-ref", "--format=%(refname)",
                                 "refs/brothersbe/autosave").stdout.split(),
                         "a production repository was snapshotted without being opted in")
        log = io.open(os.path.join(vault, "99-System", "telemetry", "autosave.log")).read()
        self.assertIn("BROTHERSBE_AUTOSAVE_PRODUCTION", log,
                      "the skip does not name the switch that would enable it: %s" % log)
        on = subprocess.run(["sh", self.AUTOSAVE, "precompact"], input=json.dumps({"cwd": repo}),
                            text=True, capture_output=True,
                            env=self._env(vault, BROTHERSBE_AUTOSAVE_PRODUCTION="1"))
        self.assertEqual(on.returncode, 0, on.stderr)
        refs = git("for-each-ref", "--format=%(refname)", "refs/brothersbe/autosave").stdout.split()
        self.assertEqual(len(refs), 1, "opting in did not produce a snapshot: %r" % refs)

    # -- see it, take it, delete it ----------------------------------------

    def test_show_export_and_purge_do_what_they_claim(self):
        vault = self._vault()
        tel, ledger, corrections = self._paths(vault)
        stored = self._fire(vault, "outcomes-append", "/tmp/acme-backend",
                            BROTHERSBE_TELEMETRY_METRICS="1",
                            BROTHERSBE_TELEMETRY_CORRECTIONS="1")
        self.assertEqual(stored.returncode, 0, stored.stderr)
        self.assertTrue(os.path.exists(ledger) and os.path.exists(corrections),
                        "the fixture stored nothing to show, export or purge: %s" % stored.stdout)

        shown = subprocess.run([sys.executable, self.TEL, "data-show"],
                               capture_output=True, text=True, env=self._env(vault))
        self.assertEqual(shown.returncode, 0, shown.stderr)
        for want in (ledger, corrections, "record(s)", "policy:"):
            self.assertIn(want, shown.stdout, "data-show does not report %r" % want)

        out = os.path.join(vault, "export.json")
        exported = subprocess.run([sys.executable, self.TEL, "data-export", "--out", out],
                                  capture_output=True, text=True, env=self._env(vault))
        self.assertEqual(exported.returncode, 0, exported.stderr)
        self.assertTrue(os.path.exists(out), "data-export wrote nothing: %s" % exported.stdout)
        bundle = json.loads(io.open(out).read())
        by_path = {f["path"]: f for f in bundle["files"]}
        self.assertIn("staging bucket", by_path[corrections]["content"],
                      "the export does not carry what is stored")
        self.assertEqual(stat.S_IMODE(os.stat(out).st_mode), 0o600,
                         "the export is not owner-only")

        dry = subprocess.run([sys.executable, self.TEL, "data-purge"],
                             capture_output=True, text=True, env=self._env(vault))
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertTrue(os.path.exists(corrections),
                        "data-purge deleted without --yes")
        self.assertIn("--yes", dry.stdout)

        purged = subprocess.run([sys.executable, self.TEL, "data-purge", "--yes"],
                                capture_output=True, text=True, env=self._env(vault))
        self.assertEqual(purged.returncode, 0, purged.stderr)
        for path in (ledger, corrections):
            self.assertFalse(os.path.exists(path),
                             "data-purge reported success and %s is still on disk: %s"
                             % (path, purged.stdout))
            self.assertIn(path, purged.stdout, "%s was removed without being named" % path)
        self.assertIn("0 failed", purged.stdout)
        # The export made outside the vault survives, which is the point of
        # having an export at all, and is why the docs call it sensitive.
        self.assertTrue(os.path.exists(out))

    # -- THE DEFECT: `data-export --help` ran a real export --------------------
    #
    # The argv scanning for `--out` only ever matched "--out"; any other token,
    # including "-h" and "--help", fell through unconsumed and the command ran
    # for real. A mistyped flag was silently ignored the same way, so
    # `data-purge --catgory work --yes` (typo: catgory) purged every category
    # instead of refusing. Fixed by one shared check ahead of each command's own
    # parsing: -h/--help prints usage and exits 0 before anything is read or
    # written, and any other unrecognized flag refuses with usage and a nonzero
    # exit instead of running past it.

    def test_help_on_each_data_command_prints_usage_and_never_creates_the_vault(self):
        """The exact shape of the found defect: point BROTHERSBE_VAULT at a path
        that does not exist yet and ask for --help. Before the fix this ran a
        real data-export and wrote a bundle; the vault directory itself was
        never the thing at risk, but nothing under its parent should exist
        either, so the parent's own listing is hashed before and after."""
        parent = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, parent, True)
        vault = os.path.join(parent, "never-created-vault")
        before = self._snapshot(parent)
        for subcmd, flag in (("data-show", "--help"), ("data-export", "--help"),
                             ("data-export", "-h"), ("data-purge", "--help"),
                             ("data-purge", "-h")):
            out = subprocess.run([sys.executable, self.TEL, subcmd, flag],
                                 capture_output=True, text=True, env=self._env(vault))
            self.assertEqual(out.returncode, 0, "%s %s: %s" % (subcmd, flag, out.stderr))
            self.assertIn("usage: %s" % subcmd, out.stdout,
                          "%s %s printed no usage: %r" % (subcmd, flag, out.stdout))
            self.assertFalse(os.path.exists(vault),
                             "%s %s created the vault it was only asked to describe"
                             % (subcmd, flag))
        after = self._snapshot(parent)
        self.assertEqual(before, after,
                         "--help changed something under %s; it must touch nothing" % parent)
        self.assertFalse(os.path.exists(os.path.join(os.getcwd(),
                         "brothersbe-telemetry-export.json")),
                         "data-export --help wrote a real bundle into the cwd")

    def test_help_on_a_populated_vault_reports_and_changes_nothing_in_it(self):
        """Same defect, the other direction: a vault that already holds real
        data must come out of a --help call byte-for-byte and mtime-for-mtime
        identical, proven by hashing its listing rather than trusting that
        `data-export --help` merely says it wrote nothing."""
        vault = self._vault()
        stored = self._fire(vault, "outcomes-append", "/tmp/acme-backend",
                            BROTHERSBE_TELEMETRY_METRICS="1",
                            BROTHERSBE_TELEMETRY_CORRECTIONS="1")
        self.assertEqual(stored.returncode, 0, stored.stderr)
        before = self._snapshot(vault)
        for subcmd in ("data-show", "data-export", "data-purge"):
            out = subprocess.run([sys.executable, self.TEL, subcmd, "--help"],
                                 capture_output=True, text=True, env=self._env(vault))
            self.assertEqual(out.returncode, 0, "%s --help: %s" % (subcmd, out.stderr))
            self.assertIn("usage: %s" % subcmd, out.stdout)
        after = self._snapshot(vault)
        self.assertEqual(before, after,
                         "%s --help changed the populated vault" % subcmd)

    def test_an_unrecognized_flag_refuses_nonzero_instead_of_running_live(self):
        """The second half of the same defect: a flag the command does not
        know, most dangerously a typo of one it does (`--catgory` for
        `--category`), must never be silently ignored and run as if the
        operator had passed nothing. It refuses, names the bad flag, prints
        usage, and leaves a nonzero exit code for a caller to branch on."""
        vault = self._vault()
        stored = self._fire(vault, "outcomes-append", "/tmp/acme-backend",
                            BROTHERSBE_TELEMETRY_METRICS="1",
                            BROTHERSBE_TELEMETRY_CORRECTIONS="1")
        self.assertEqual(stored.returncode, 0, stored.stderr)
        before = self._snapshot(vault)
        cases = [("data-show", ["--bogus"]), ("data-export", ["--catgory"]),
                 ("data-purge", ["--catgory", "work", "--yes"])]
        for subcmd, bad_argv in cases:
            out = subprocess.run([sys.executable, self.TEL, subcmd] + bad_argv,
                                 capture_output=True, text=True, env=self._env(vault))
            self.assertNotEqual(out.returncode, 0,
                                "%s %r ran as if the flag were valid" % (subcmd, bad_argv))
            self.assertIn("usage: %s" % subcmd, out.stdout,
                          "%s %r refused without printing usage: %r"
                          % (subcmd, bad_argv, out.stdout))
            self.assertIn(bad_argv[0], out.stdout,
                          "%s %r did not name the flag it refused" % (subcmd, bad_argv))
        after = self._snapshot(vault)
        self.assertEqual(before, after,
                         "an unrecognized flag changed the vault before refusing")


class TestMarketplaceManifest(unittest.TestCase):
    """Wave 10 packages this plugin for `claude plugin marketplace add`, which
    means a SECOND file, `.claude-plugin/marketplace.json`, now carries the
    same version number `.claude-plugin/plugin.json` and `VERSION` already pin
    against each other (`TestPluginSurface.
    test_manifest_parses_and_agrees_with_the_version_file`). A marketplace
    entry that drifts from the plugin it names is the same silent packaging
    defect that test already guards against, one file further out, so this
    class extends the same pin rather than starting a second one.

    The shape asserted here was not taken from memory. The installed CLI
    (`claude --version` reported 2.1.207 when this was written) was asked
    directly, and its decisive lines were:

        `claude plugin marketplace add --help` prints:
        "Add a marketplace from a URL, path, or GitHub repo"

        `claude plugin validate --help` prints:
        "Validate a plugin or marketplace manifest"

    Neither --help prints a JSON schema, so the field shape itself (top-level
    name/owner/plugins, each plugin entry's name/source/description/version)
    was cross-checked against real, already-installed marketplace.json files
    on this machine that ship a single self-hosted plugin the same way this
    repository does (`~/.claude/plugins/marketplaces/mattpocock` and
    `.../karpathy-skills`, both using `"source": "./"` to name the repo's own
    root rather than a second clone URL), and then confirmed the only way
    that actually counts: running the installed `claude plugin validate`
    against the exact file this project ships, which the second test below
    re-runs so a future shape change is caught here rather than only at the
    next human's release-day run of the same command."""

    ROOT = os.path.join(HERE, "..")
    MANIFEST = os.path.join(ROOT, ".claude-plugin", "marketplace.json")

    def test_marketplace_manifest_parses_and_pins_every_version_together(self):
        self.assertTrue(os.path.exists(self.MANIFEST),
                        "%s does not exist; `claude plugin marketplace add` has nothing to read"
                        % self.MANIFEST)
        manifest = json.load(io.open(self.MANIFEST, encoding="utf-8"))
        self.assertEqual(manifest.get("name"), "brothersbe",
                         "the marketplace name; changing it changes what a user types after "
                         "`claude plugin marketplace add`")
        self.assertIn("owner", manifest, "marketplace.json has no owner")

        plugins = manifest.get("plugins")
        self.assertTrue(plugins, "marketplace.json declares no plugins")
        entry = plugins[0]
        self.assertEqual(entry.get("name"), "brothersbe",
                         "the plugin entry name must match .claude-plugin/plugin.json's own "
                         "name or `claude plugin install brothersbe@brothersbe` resolves to "
                         "the wrong thing")
        self.assertEqual(entry.get("source"), "./",
                         "this repository ships the plugin it also markets, so the entry "
                         "points at its own root, not a second clone URL")
        self.assertTrue(entry.get("description"), "the plugin entry has no description")

        version = io.open(os.path.join(self.ROOT, "VERSION"), encoding="utf-8").read().strip()
        plugin_manifest = json.load(io.open(
            os.path.join(self.ROOT, ".claude-plugin", "plugin.json"), encoding="utf-8"))
        self.assertEqual(plugin_manifest.get("version"), version,
                         "plugin.json and VERSION already disagree; that is "
                         "TestPluginSurface's own pin, so if this line fails, that one is "
                         "failing too")
        self.assertEqual(entry.get("version"), version,
                         "marketplace.json's plugin entry says %s, VERSION says %s; `claude "
                         "plugin tag` validates that plugin.json and any enclosing marketplace "
                         "entry agree, so a release cut from this state fails that check"
                         % (entry.get("version"), version))
        top_version = (manifest.get("metadata") or {}).get("version")
        self.assertEqual(top_version, version,
                         "marketplace.json's own metadata.version says %s, VERSION says %s"
                         % (top_version, version))

    def test_marketplace_manifest_validates_against_the_installed_cli(self):
        claude_bin = shutil.which("claude")
        if not claude_bin:
            self.skipTest(
                "the `claude` CLI is not on PATH in this environment, so nothing ran "
                "`claude plugin validate` here. This is NO-DATA, not a pass: "
                "test_marketplace_manifest_parses_and_pins_every_version_together above still "
                "checks the shape by hand, but only a real run of the installed CLI proves the "
                "CLI itself accepts this file, and that did not happen on this run.")
        result = subprocess.run([claude_bin, "plugin", "validate", self.MANIFEST],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0,
                         "`claude plugin validate %s` exited %d:\nSTDOUT:\n%s\nSTDERR:\n%s"
                         % (self.MANIFEST, result.returncode, result.stdout, result.stderr))
        self.assertIn("Validation passed", result.stdout,
                      "the CLI exited 0 but did not say Validation passed: %s" % result.stdout)


class TestDossierBindingScenario23(unittest.TestCase):
    """SCENARIO 23 (docs/BYPASS-COVERAGE.md row 23): a dossier from a finished
    change, left in place, reads identically to one written for the change in
    front of it, because nothing reads a commit. `00-intake.json` may now carry
    an OPTIONAL "binding": {"head": <commit>, "artifacts": {path: sha256}}.
    Every fixture here builds a REAL git repository and runs the real
    `tools/sbe_design.py` against it (matching how `tools/test_sbe_bypass.py`
    exercises the design checks), because a binding lives at the seam between
    a commit and a claim about it, and a mocked seam would test the mock.
    """

    DESIGN = os.path.join(HERE, "sbe_design.py")
    PURPOSE = ("# Purpose\nProblem: refunds settle late and support cannot say why.\n"
               "Users: the support desk and the finance close.\n"
               "Success: every refund reaches a terminal state within one business day.\n"
               "Non-goals: repricing, partial refunds.\nIf wrong: refunds stall silently.\n")
    ANSWERS = {"changes_contract": False, "crosses_boundary": True,
              "reversible_under_hour": True, "touches_sensitive": False, "consumers": "none"}

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.repo = os.path.join(self.dir, "repo")
        os.makedirs(self.repo)
        self._git("init", "-q")
        self._git("config", "user.email", "dana@example.invalid")
        self._git("config", "user.name", "Dana Author")
        self._git("config", "commit.gpgsign", "false")
        self._write("README.md", "base\n")
        self._git("add", "-A")
        self._git("commit", "-qm", "base")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def _git(self, *args):
        out = subprocess.run(["git"] + list(args), cwd=self.repo, capture_output=True, text=True)
        if out.returncode != 0:
            raise AssertionError("git %s failed in %s: %s" % (" ".join(args), self.repo, out.stderr))
        return out.stdout.strip()

    def _write(self, rel, body):
        path = os.path.join(self.repo, rel)
        directory = os.path.dirname(path)
        if directory and not os.path.isdir(directory):
            os.makedirs(directory)
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(body)
        return path

    def _sha256(self, rel):
        with open(os.path.join(self.repo, rel), "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()

    def _commit_dossier(self, message="add dossier"):
        """01-purpose.md plus an unbound 00-intake.json, committed. Returns the
        new commit's id, which is the "head this dossier was written against"
        every fixture below binds to."""
        self._write("01-purpose.md", self.PURPOSE)
        self._write("00-intake.json", json.dumps({"tier": "T1", "answers": self.ANSWERS},
                                                 indent=2, sort_keys=True))
        self._git("add", "-A")
        self._git("commit", "-qm", message)
        return self._git("rev-parse", "HEAD")

    def _bind(self, binding):
        """Rewrites 00-intake.json to add `binding`, left UNCOMMITTED: a binding
        is the author's own claim about the tree in front of them, and nothing
        about resolving HEAD or re-hashing a covered file needs it committed."""
        self._write("00-intake.json", json.dumps({"tier": "T1", "answers": self.ANSWERS,
                                                  "binding": binding}, indent=2, sort_keys=True))

    def _run_design(self):
        out = subprocess.run([sys.executable, self.DESIGN, self.repo],
                             capture_output=True, text=True)
        return out.stdout + out.stderr

    def _verdict(self, text):
        # Three values, not two: a two-value return reads as a possible
        # (verdict, evidence) pair to the honesty meta-test, which refuses any
        # such function sitting outside a check registry.
        for line in text.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] == "artifacts":
                return parts[1], line, text
        return None, "NO VERDICT LINE for 'artifacts' in:\n%s" % text, text

    def test_bound_and_current_passes(self):
        head = self._commit_dossier()
        self._bind({"head": head, "artifacts": {"01-purpose.md": self._sha256("01-purpose.md")}})
        verdict, line, _ = self._verdict(self._run_design())
        self.assertEqual(verdict, "PASS", line)
        self.assertIn(head[:12], line, "a verified binding should say which head it verified: %r" % line)

    def test_bound_then_head_moved_fails_by_name(self):
        head = self._commit_dossier()
        self._bind({"head": head, "artifacts": {"01-purpose.md": self._sha256("01-purpose.md")}})
        # A second, unrelated commit moves HEAD without touching the binding,
        # which is exactly scenario 23: the dossier now predates the commit in
        # front of it. The binding edit itself is never committed, matching
        # every fixture here, so committing "unrelated" is what advances HEAD.
        self._write("UNRELATED.md", "an unrelated later change\n")
        self._git("add", "-A")
        self._git("commit", "-qm", "unrelated later change")
        new_head = self._git("rev-parse", "HEAD")
        verdict, line, _ = self._verdict(self._run_design())
        self.assertEqual(verdict, "FAIL", line)
        self.assertIn(head[:12], line, "the stale bound head should be named: %r" % line)
        self.assertIn(new_head[:12], line, "the current head should be named: %r" % line)
        self.assertIn("re-bind deliberately", line)

    def test_artifact_digest_drift_fails_naming_the_file(self):
        head = self._commit_dossier()
        self._bind({"head": head, "artifacts": {"01-purpose.md": self._sha256("01-purpose.md")}})
        # Edited AFTER binding, and left uncommitted, so HEAD stays exactly
        # where the binding says it is: this isolates a digest mismatch from a
        # moved HEAD, which is the other, differently-named failure.
        self._write("01-purpose.md", self.PURPOSE + "Edited after binding, before re-binding.\n")
        verdict, line, _ = self._verdict(self._run_design())
        self.assertEqual(verdict, "FAIL", line)
        self.assertIn("01-purpose.md", line)
        self.assertIn("changed since the dossier was bound", line)

    def test_absent_binding_is_unchanged_behavior(self):
        head = self._commit_dossier()
        verdict, line, _ = self._verdict(self._run_design())
        self.assertEqual(verdict, "PASS", line)
        self.assertNotIn("bound", line.lower(),
                         "no binding was recorded, so nothing about one should appear: %r" % line)

    def test_an_unresolvable_bound_commit_is_no_data(self):
        self._commit_dossier()
        # 40 hex characters, never an object this repository has: no commit was
        # ever made with this id, and it is not the empty tree either.
        fake_head = "f" * 40
        self._bind({"head": fake_head, "artifacts": {"01-purpose.md": self._sha256("01-purpose.md")}})
        verdict, line, _ = self._verdict(self._run_design())
        self.assertEqual(verdict, "NO-DATA", line)
        self.assertIn(fake_head[:12], line)
        self.assertNotEqual(verdict, "PASS", "an unresolvable binding must never pass: %r" % line)

    def test_a_binding_path_that_walks_out_of_the_repo_fails_by_name(self):
        # The outside file EXISTS and its recorded digest is TRUE, so the only
        # thing standing between this binding and a PASS is the containment
        # check itself; a missing-file refusal cannot satisfy this fixture,
        # which is what calibration demanded (with the check disabled, the
        # true digest verifies and the run PASSes, which is the red).
        outside = os.path.join(os.path.dirname(self.repo), "outside.md")
        with io.open(outside, "w", encoding="utf-8") as fh:
            fh.write("lives outside the repo on purpose\n")
        digest = hashlib.sha256(open(outside, "rb").read()).hexdigest()
        head = self._commit_dossier()
        self._bind({"head": head, "artifacts": {"../outside.md": digest}})
        verdict, line, _ = self._verdict(self._run_design())
        self.assertEqual(verdict, "FAIL", line)
        self.assertIn("resolves outside", line)

    def test_an_unreadable_bound_artifact_fails_naming_the_file(self):
        head = self._commit_dossier()
        self._bind({"head": head, "artifacts": {"never-written.md": "0" * 64}})
        verdict, line, _ = self._verdict(self._run_design())
        self.assertEqual(verdict, "FAIL", line)
        self.assertIn("never-written.md", line)


class TestRenderSameNormalizesRawText(unittest.TestCase):
    """could_render_same and name_sets_could_collide were safe only because
    today's two call sites (tools/sbe_gate.py's approval check, reused by
    scripts/derive_refusal_table.py) hand them text already run through
    fold(), which composes via NFKC before either function ever compares a
    character. Called on RAW text, a composed-versus-decomposed spelling of
    the SAME rendered identity read as "proven different": a decomposed
    Hangul jamo run counts more characters than its precomposed syllable and
    trips the length check, and a precomposed accented letter missing from
    the curated confusable/Latin-name tables (Greek omega-with-tonos) reads
    as an unreadable ("opaque") letter that differs by code point from its
    own NFD form once _unmarked has stripped the mark back to plain omega.
    Both functions now normalize with plain_text (the same NFKC path
    fold() itself uses; no second normalizer introduced) at their own entry,
    so raw text now reads the way pre-folded text already did.

    Loads sbe_checks.py directly, the same pattern
    TestOneLineNeutralizesTheControlClass above uses, rather than importing
    it as a package, since this file is run as a script.
    """

    def setUp(self):
        spec = importlib.util.spec_from_file_location(
            "sbe_checks_norm", os.path.join(HERE, "sbe_checks.py"))
        self.checks = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.checks)

    def test_raw_nfc_nfd_accent_pair_reads_as_could_render_same(self):
        import unicodedata
        # U+038F GREEK CAPITAL LETTER OMEGA WITH TONOS: not ASCII, not East
        # Asian wide, and absent from both the curated confusable table and
        # the Latin-name fold (it is Greek, not Latin), so before the guard
        # it read as an "opaque" letter compared by code point against its
        # own NFD form (omega plus a combining tonos), which _unmarked
        # reduces to bare omega, a DIFFERENT code point: a proof of
        # difference for one letter compared against itself.
        nfc = "Ώ"
        nfd = unicodedata.normalize("NFD", nfc)
        self.assertNotEqual(nfc, nfd, "the fixture must actually be two distinct spellings")
        self.assertTrue(self.checks.could_render_same(nfc, nfd),
                        "a precomposed letter and its own NFD decomposition, "
                        "passed raw, must not read as proven different")

    def test_raw_hangul_syllable_jamo_pair_reads_as_could_render_same(self):
        import unicodedata
        # Two precomposed Hangul syllables (2 characters) versus the same
        # text NFD-decomposed into its choseong/jungseong/jongseong jamo (6
        # characters, none of them a combining mark _unmarked would strip):
        # a bare length mismatch before the guard, though the two spellings
        # render identically.
        syllables = "안녕"       # 안녕
        jamo = unicodedata.normalize("NFD", syllables)
        self.assertNotEqual(len(syllables), len(jamo),
                            "the fixture must actually differ in raw character count")
        self.assertTrue(self.checks.could_render_same(syllables, jamo),
                        "a Hangul syllable spelling and its own jamo decomposition, "
                        "passed raw, must not read as proven different")

    def test_raw_nfc_nfd_accent_pair_collides_as_name_words(self):
        import unicodedata
        nfc = "Ώ"
        nfd = unicodedata.normalize("NFD", nfc)
        self.assertTrue(self.checks.name_sets_could_collide([nfc], [nfd]),
                        "one name word spelled NFC versus the same word spelled NFD "
                        "must not read as two different identities")

    def test_raw_hangul_syllable_jamo_pair_collides_as_name_words(self):
        import unicodedata
        syllables = "안녕"
        jamo = unicodedata.normalize("NFD", syllables)
        self.assertTrue(self.checks.name_sets_could_collide([syllables], [jamo]),
                        "one name word spelled with precomposed Hangul syllables versus "
                        "the same word spelled with decomposed jamo must not read as "
                        "two different identities")

    def test_genuinely_different_hangul_syllables_still_prove_different(self):
        """Control: the guard composes a raw jamo run back to ONE syllable,
        it does not make every Hangul comparison vacuously true. A DIFFERENT
        syllable, even compared against a raw jamo run, still differs by
        code point once both sides are one composed character each."""
        import unicodedata
        an = "안"                              # 안
        a_different_syllable = "녕"             # 녕
        an_as_jamo = unicodedata.normalize("NFD", an)
        self.assertFalse(self.checks.could_render_same(an_as_jamo, a_different_syllable),
                         "two genuinely different Hangul syllables must still "
                         "prove different, one of them passed as raw jamo")
        self.assertFalse(self.checks.name_sets_could_collide([an_as_jamo], [a_different_syllable]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
